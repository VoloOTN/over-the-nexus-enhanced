"""Booster-pack unlock conditions as an editable table.

Every pack's unlock rule lives in a jump table in **overlay 1** at
``0x02145124 + pack_id*4``; each slot branches to a small "arm" that evaluates
one condition and falls through either to the loop tail (locked) or to a set-bit
tail (unlocked).  See ``notes/booster-pack-unlock-findings.md`` for the full
reverse-engineering write-up.

Edit :data:`CHANGES` below (uncomment a pack, change its numbers) and run::

    python -m otn_enhanced.system.pack_unlock_conditions

Only the packs present in ``CHANGES`` are touched; everything else keeps its
stock rule.  There is also a JSON workflow if you would rather edit data than
code::

    python -m ... pack_unlock_conditions dump  packs.json
    #  ... edit packs.json ...
    python -m ... pack_unlock_conditions apply packs.json

and ``show`` prints the stock table.

What can be changed
-------------------
Arms are variable-length code blocks packed back-to-back, so every edit here is
**size-neutral**:

* ``Always()`` / ``Never()`` / ``SameAs(n)``  - rewrite the jump-table slot only
* ``StoryFlag.flag_id``                       - rewrites the arm's literal-pool word
* ``DuelsWon.wins``                           - rewrites a ``cmp r0, #imm``
* ``CountUnlocked.need``                      - rewrites a ``cmp r0, #imm``
* ``CardPercent.percent``                     - rewrites a ``cmp r0, #imm``
* ``BeatDuelists.wins``                       - rewrites ``mov r2, #imm``
* ``BeatDuelists.ids``                        - rewrites the id array in place,
  **same length or shorter**, and updates ``mov r1, #n``

Changing a pack to a structurally different rule (say story-flag -> duels-won)
would need a differently sized arm and is refused; use ``Always``/``Never``/
``SameAs`` instead.  Arms and id-lists shared between packs (1-4 and 32-34 share
arms) are detected and refused rather than silently editing a neighbour.

Duelist ids are the roster ids 0x00-0x70; ids >= 0x71 are the CPU-duel roster.
``name(id)`` resolves them via arm9 ``0x020AA7D4`` -> ``bin2/game_text_e.bin``.
"""
from __future__ import annotations

import json
import shutil
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import ndspy.rom
from capstone import CS_ARCH_ARM, CS_MODE_ARM, Cs

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_pack_conditions.nds"

# ---------------------------------------------------------------------------
# Overlay 1 geometry (EU / BYYP)
# ---------------------------------------------------------------------------
OVERLAY_ID = 1
OV1_BASE = 0x02141700
JUMP_TABLE = 0x02145124          # slot for pack n is JUMP_TABLE + n*4
LOOP_TAIL = 0x02145D8C           # condition failed -> next pack
PLAIN_SET = 0x02145218           # unconditional set-bit arm
SET_TAIL = 0x02145BC0            # condition passed (+ "new pack" notify)
SET_TAIL2 = 0x02145D88           # inline set-bit tail used by the count-bits arms
FIRST_PACK, LAST_PACK = 1, 60

FN_FLAG = 0x0201B36C             # event_flag_get(id)
FN_COUNTER = 0x0202F6EC          # counter_get(idx); idx 1 == duels won
FN_SOLO = 0x02144F08             # all_of(ids, n, min_wins)  master+id*4+0x2EC
FN_TAG = 0x02144F4C              # same, tag array           master+f(id)*4+0x75C
FN_ANY_SOLO = 0x02144FA0         # beaten at least once (solo)
FN_ANY_TAG = 0x02144FD0          # beaten at least once (tag)

DUELIST_NAME_TABLE = 0x020AA7D4  # arm9 u16: duelist id -> game-text index


# ---------------------------------------------------------------------------
# Condition types
# ---------------------------------------------------------------------------
class Condition:
    """Base class.  ``sites`` is patch-site bookkeeping filled in by the reader.

    Deliberately *not* a dataclass: keeping ``sites`` out of the field list lets
    every subclass take positional arguments (``StoryFlag(0x4E40)``) and keeps it
    out of ``__eq__``, so an untouched round-trip compares equal and writes
    nothing.
    """

    sites: dict = {}

    def __post_init__(self):
        self.sites = {}
        self.validate()

    def validate(self):
        pass


def _check_imm(value, what):
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{what} must be a non-negative int, got {value!r}")
    try:
        _encode_imm(value)
    except ValueError as e:
        raise ValueError(f"{what}: {e}") from None


@dataclass
class Always(Condition):
    pass


@dataclass
class Never(Condition):
    pass


@dataclass
class SameAs(Condition):
    """Use another pack's rule verbatim (rewrites this pack's table slot)."""
    pack: int

    def validate(self):
        if not FIRST_PACK <= self.pack <= LAST_PACK:
            raise ValueError(f"SameAs pack {self.pack} outside {FIRST_PACK}..{LAST_PACK}")


@dataclass
class StoryFlag(Condition):
    flag_id: int

    def validate(self):
        if not 0 <= self.flag_id <= 0xFFFF:
            raise ValueError(f"story flag {self.flag_id:#x} out of range")


@dataclass
class DuelsWon(Condition):
    wins: int

    def validate(self):
        _check_imm(self.wins, "DuelsWon.wins")


@dataclass
class BeatDuelists(Condition):
    mode: str                       # "solo" | "tag"
    ids: list                       # ints, or (a, b) pairs when mode == "tag"
    wins: int = 3

    def validate(self):
        if self.mode not in ("solo", "tag"):
            raise ValueError(f"mode must be 'solo' or 'tag', got {self.mode!r}")
        if not isinstance(self.ids, list) or not self.ids:
            raise ValueError("BeatDuelists.ids must be a non-empty list")
        for e in self.ids:
            if self.mode == "tag":
                if not (isinstance(e, (tuple, list)) and len(e) == 2
                        and all(isinstance(x, int) and 0 <= x <= 0xFFFF for x in e)):
                    raise ValueError(f"tag entry {e!r} must be a (id, id) pair")
            elif not (isinstance(e, int) and 0 <= e <= 0xFFFF):
                raise ValueError(f"duelist id {e!r} out of range")
        _check_imm(self.wins, "BeatDuelists.wins")
        _check_imm(len(self.ids), "BeatDuelists list length")


@dataclass
class BeatEveryDuelist(Condition):
    mode: str = "solo"

    def validate(self):
        if self.mode not in ("solo", "tag"):
            raise ValueError(f"mode must be 'solo' or 'tag', got {self.mode!r}")


@dataclass
class CountUnlocked(Condition):
    """Count of unlocked duelists in a roster >= ``need``.

    ``id_lo``/``id_hi``/``bitfield`` are read back from the ROM for context and
    are not editable (the loop bounds are baked into the arm's instructions).
    """
    need: int
    id_lo: int = 0
    id_hi: int = 0
    bitfield: int = 0

    def validate(self):
        _check_imm(self.need, "CountUnlocked.need")


@dataclass
class CardPercent(Condition):
    percent: int = 95

    def validate(self):
        if not 0 <= self.percent <= 100:
            raise ValueError(f"CardPercent must be 0..100, got {self.percent}")
        _check_imm(self.percent, "CardPercent.percent")


@dataclass
class Compound(Condition):
    """Several clauses AND-ed together (e.g. pack 37)."""
    parts: list = field(default_factory=list)

    def validate(self):
        for p in self.parts:
            if not isinstance(p, Condition):
                raise ValueError(f"Compound part {p!r} is not a Condition")


@dataclass
class Unknown(Condition):
    arm: int = 0
    note: str = ""


# ---------------------------------------------------------------------------
# The edit table.  Uncomment a pack and change its numbers; anything left
# commented out keeps its stock rule.  Values below are the stock ones.
# ---------------------------------------------------------------------------
CHANGES: dict = {
    #  1: Always(),
    #  2: Always(),
    #  3: Always(),
    #  4: Always(),
    #  5: StoryFlag(0x4E40),                                            # story progress
    #  6: DuelsWon(50),                                                 # duels won
    #  7: StoryFlag(0x4E41),                                            # story progress
    #  8: BeatDuelists('solo', [0x30, 0x66, 0x65, 0x62, 0x67, 0x63, 0x64], wins=3), # Bronson, Minegishi, Jemma, Virgil, Seluga, Clint, Scotch
    #  9: StoryFlag(0x4E42),                                            # story progress
    # 10: DuelsWon(100),                                                # duels won
    # 11: StoryFlag(0x4E43),                                            # story progress
    # 12: BeatDuelists('solo', [0x0F, 0x3B, 0x0E, 0x1F, 0x39, 0x08], wins=3), # Reimi, Lilie, Hayakawa, Masaki, Gordon, Kuroe
    # 13: StoryFlag(0x4E44),                                            # story progress
    # 14: DuelsWon(200),                                                # duels won
    # 15: StoryFlag(0x4E45),                                            # story progress
    # 16: BeatDuelists('solo', [0x15, 0x12, 0x24, 0x3D, 0x23, 0x28, 0x2C, 0x14, 0x29], wins=3), # Rossi, Kazuhiro, Honda, Yagiura, Helio, Angie, Nelson, Figaro, Corse
    # 17: StoryFlag(0x4E46),                                            # story progress
    # 18: BeatDuelists('solo', [0x0D, 0x06, 0x02, 0x0B, 0x0A], wins=3),  # Randsborg, Hunter Pace, Lenny, Larry, Lug
    # 19: StoryFlag(0x4E47),                                            # story progress
    # 20: BeatDuelists('solo', [0x2B, 0x4F, 0x50], wins=3),             # Lazar, Sherry LeBlanc, Elsworth
    # 21: StoryFlag(0x4E48),                                            # story progress
    # 22: StoryFlag(0x4E49),                                            # story progress
    # 23: StoryFlag(0x4E4A),                                            # story progress
    # 24: StoryFlag(0x4E4B),                                            # story progress
    # 25: BeatDuelists('solo', [0x3A, 0x31], wins=3),                   # Torunka, Regulus
    # 26: StoryFlag(0x4E4C),                                            # story progress
    # 27: StoryFlag(0x4E4D),                                            # story progress
    # 28: BeatDuelists('solo', [0x56, 0x55, 0x4E, 0x57, 0x54], wins=3), # Nico, West, Kalin Kessler, Sergio, Barbara
    # 29: StoryFlag(0x4E4E),                                            # story progress
    # 30: Compound([BeatDuelists('solo', [0x44, 0x45, 0x46, 0x47, 0x49, 0x4A], wins=3),
    #               BeatDuelists('tag',  [(0x46, 0x44), (0x47, 0x45)], wins=3)]),
    #                                                                   # Yusei x2, Jack x2, Crow x2 AND tag Jack+Yusei x2
    # 31: Compound([BeatDuelists('solo', [0x5E, 0x5F, 0x60], wins=3),
    #               BeatDuelists('tag',  [(0x5E, 0x5F)], wins=3)]),     # Harald, Dragan, Brave AND tag Harald+Dragan
    # 32: Always(),
    # 33: Always(),
    # 34: Always(),
    # 35: Compound([BeatDuelists('solo', [0x2D, 0x6E, 0x61], wins=3),
    #               BeatDuelists('tag',  [(0x2D, 0x61)], wins=3)]),     # Carly, Mina, Stephanie AND tag Carly+Stephanie
    # 36: Compound([BeatDuelists('solo', [0x5B, 0x5C, 0x5D], wins=3),
    #               BeatDuelists('tag',  [(0x5C, 0x5B)], wins=3)]),     # Hermann, Nicolas, Hans AND tag Nicolas+Hermann
    # 37: Compound([BeatDuelists('solo', [0x03, 0x37, 0x38, 0x6B, 0x6A], wins=3),
    #               BeatDuelists('tag',  [(0x38, 0x03), (0x6A, 0x6B)], wins=3),
    #               StoryFlag(0x27E0)]),                                # Trudge, Akiza x2, Luna, Leo AND tags AND story flag
    # 38: BeatDuelists('solo', [0x05, 0x6D, 0x53, 0x51, 0x52], wins=3), # Facility Chief, Syd, Lawton, Ramon, Malcolm
    # 39: Compound([BeatEveryDuelist('solo'), BeatEveryDuelist('tag')]), # every duelist, solo and tag
    # 40: BeatDuelists('solo', [0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E], wins=3), # Narumi, Salida Noula, Grammy, Alina Noula, Iranami, Globe, Lagoon Noula, Oscar, Kalisse Noula
    # 41: StoryFlag(0x4E55),                                            # story progress
    # 42: Compound([BeatDuelists('solo', [0x3F, 0x40, 0x41, 0x42, 0x43], wins=3),
    #               BeatDuelists('tag',  [(0x40, 0x42), (0x41, 0x43)], wins=3)]),
    #                                                                   # Klaus, Toru x2, Misaki x2 AND tag Toru+Misaki x2
    # 43: StoryFlag(0x4E4F),                                            # story progress
    # 44: StoryFlag(0x4E50),                                            # story progress
    # 45: StoryFlag(0x4E51),                                            # story progress
    # 46: BeatDuelists('solo', [0x71, 0x72, 0x73, 0x74, 0x75, 0x76], wins=3), # first 6 CPU duels: Moja, Cherry Inmato, Hypnocorn, Naturia Cherries, Wattmole, Tiki Soul
    # 47: CountUnlocked(36),                                            # CPU duelists (ids 0x71-0xAC) unlocked
    # 48: CountUnlocked(48),                                            # CPU duelists (ids 0x71-0xAC) unlocked
    # 49: CountUnlocked(7),                                             # duelists 0x00-0x13 unlocked
    # 50: CountUnlocked(12),                                            # duelists 0x00-0x13 unlocked
    # 51: CountUnlocked(16),                                            # duelists 0x00-0x13 unlocked
    # 52: CountUnlocked(12),                                            # duelists 0xD5-0xE8 unlocked
    # 53: CountUnlocked(16),                                            # duelists 0xD5-0xE8 unlocked
    # 54: CountUnlocked(8),                                             # duelists 0x14-0x1D unlocked
    # 55: CountUnlocked(9),                                             # duelists 0x14-0x1D unlocked
    # 56: StoryFlag(0x27E0),                                            # story progress
    # 57: StoryFlag(0x4E52),                                            # story progress
    # 58: StoryFlag(0x4E53),                                            # story progress
    # 59: StoryFlag(0x4E54),                                            # story progress
    60: Always(),                                                     # All at Random: open from the start (stock CardPercent(95))
}


# ---------------------------------------------------------------------------
# Duelist names (optional -- needs the extracted bin2 text files)
# ---------------------------------------------------------------------------
def name(duelist_id: int) -> str:
    """Resolve a duelist id to its English name, or ``?0xNN?`` if unavailable."""
    from otn_enhanced.rom import stock
    try:
        a9 = stock.arm9()
        idx = open("scratch/bin2/game_indx_e.bin", "rb").read()
        txt = open("scratch/bin2/game_text_e.bin", "rb").read()
    except OSError:
        return f"?0x{duelist_id:02X}?"
    off = DUELIST_NAME_TABLE - 0x02000000 + duelist_id * 2
    if off + 2 > len(a9):
        return f"?0x{duelist_id:02X}?"
    i = struct.unpack_from("<H", a9, off)[0]
    if i * 4 + 4 > len(idx):
        return f"?0x{duelist_id:02X}?"
    o = struct.unpack_from("<I", idx, i * 4)[0]
    if o >= len(txt):
        return f"?0x{duelist_id:02X}?"
    return txt[o:txt.index(b"\x00", o)].decode("latin-1", "replace") or f"?0x{duelist_id:02X}?"


# ---------------------------------------------------------------------------
# Overlay 1 load / save
# ---------------------------------------------------------------------------
def _load_ov1(rom):
    ov = rom.loadArm9Overlays([OVERLAY_ID])[OVERLAY_ID]
    if ov.ramAddress != OV1_BASE:
        raise AssertionError(
            f"overlay 1 loads at {ov.ramAddress:#010x}, expected {OV1_BASE:#010x} "
            "-- this is not the EU (BYYP) ROM these addresses were derived from")
    return ov, bytearray(ov.data)


def _save_ov1(rom, ov, data, out):
    ov.data = bytes(data)
    ov.ramSize = len(data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed
    tbl = rom.arm9OverlayTable
    e = OVERLAY_ID * 32
    struct.pack_into("<I", tbl, e + 0x08, len(data))
    flags = struct.unpack_from("<I", tbl, e + 0x1C)[0] >> 24
    struct.pack_into("<I", tbl, e + 0x1C, (flags << 24) | (len(compressed) & 0xFFFFFF))
    rom.saveToFile(str(out))


# ---------------------------------------------------------------------------
# ARM helpers
# ---------------------------------------------------------------------------
def _encode_imm(value: int) -> int:
    """Return ARM data-processing imm12 (rot<<8 | imm8) for *value*."""
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError(f"{value} out of range for an ARM immediate")
    for rot in range(0, 32, 2):
        v = ((value << rot) | (value >> (32 - rot))) & 0xFFFFFFFF if rot else value
        if v <= 0xFF:
            return ((rot // 2) << 8) | v
    raise ValueError(f"{value:#x} is not encodable as an ARM immediate "
                     "(needs an 8-bit value at an even rotation)")


def _branch(frm: int, to: int) -> int:
    delta = to - (frm + 8)
    if delta % 4:
        raise ValueError("unaligned branch")
    imm = delta // 4
    if not -(1 << 23) <= imm < (1 << 23):
        raise ValueError("branch out of range")
    return 0xEA000000 | (imm & 0xFFFFFF)


class _Ov1:
    """Byte-level view of decompressed overlay 1."""

    def __init__(self, data: bytearray):
        self.d = data
        self.md = Cs(CS_ARCH_ARM, CS_MODE_ARM)

    def _o(self, addr: int) -> int:
        off = addr - OV1_BASE
        if not 0 <= off < len(self.d) - 3:
            raise ValueError(f"{addr:#010x} outside overlay 1")
        return off

    def u32(self, addr): return struct.unpack_from("<I", self.d, self._o(addr))[0]
    def set_u32(self, addr, v): struct.pack_into("<I", self.d, self._o(addr), v & 0xFFFFFFFF)
    def contains(self, addr): return OV1_BASE <= addr < OV1_BASE + len(self.d) - 3

    def branch_target(self, addr):
        m = self.u32(addr) & 0xFFFFFF
        if m & 0x800000:
            m -= 0x1000000
        return addr + 8 + m * 4

    def disasm(self, addr, nbytes=0x400):
        off = self._o(addr)
        return list(self.md.disasm(bytes(self.d[off:off + nbytes]), addr))

    def arm_body(self, addr):
        """Instructions of one arm.

        An arm ends at its first unconditional ``B`` **or** on reaching one of the
        shared tails.  Both bounds are needed and getting either wrong is silent:
        pack 60's arm is ~0x1A4 bytes (a short window truncated it before its
        threshold ``cmp``, reading as 0%) and it is the one arm with no
        terminating ``B`` -- it falls through into ``SET_TAIL2``, so a
        bounds-only fix ran past into another function and read as a story flag.
        """
        out = []
        for ins in self.disasm(addr):
            if ins.address in (SET_TAIL, SET_TAIL2, LOOP_TAIL, PLAIN_SET) and out:
                break
            out.append(ins)
            if ins.mnemonic == "b":
                break
        return out


def _litaddr(ins):
    return ins.address + 8 + int(ins.op_str.split("[pc, #")[1].rstrip("]"), 0)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def _parse_arm(ov: _Ov1, arm: int, depth: int = 0):
    if arm == PLAIN_SET:
        return Always()
    if arm == LOOP_TAIL:
        return Never()
    if depth > 2:
        return Unknown(arm, "trampoline nesting too deep")

    ins = ov.arm_body(arm)
    if len(ins) == 1 and ins[0].mnemonic == "b":
        return _parse_arm(ov, ov.branch_target(arm), depth + 1)

    regs, parts, pending_cmp = {"r6": 1}, [], None
    for i in ins:
        m, o = i.mnemonic, i.op_str
        if m == "ldr" and "[pc, #" in o:
            la = _litaddr(i)
            regs[o.split(",")[0]] = ov.u32(la)
            regs["_lit_" + o.split(",")[0]] = la
        elif m == "mov" and ", #" in o:
            regs[o.split(",")[0]] = int(o.split("#")[1], 0)
            regs["_at_" + o.split(",")[0]] = i.address
        elif m == "mov":
            a, b = [x.strip() for x in o.split(",")]
            if b in regs:
                regs[a] = regs[b]
                regs["_at_" + a] = i.address
        elif m == "cmp" and o.startswith("r0, #"):
            pending_cmp = (i.address, int(o.split("#")[1], 0))
        elif m in ("bl", "blx"):
            t = int(o.strip("#"), 0)
            if t == FN_FLAG:
                c = StoryFlag(regs.get("r0", 0))
                c.sites = {"lit": regs.get("_lit_r0")}
                parts.append(c)
            elif t == FN_COUNTER:
                parts.append(("_counter", regs.get("r0", 0)))
            elif t in (FN_SOLO, FN_TAG):
                lst, n, k = regs.get("r0"), regs.get("r1"), regs.get("r2")
                if lst is None or n is None or not ov.contains(lst):
                    parts.append(Unknown(arm, "unresolved duelist list"))
                    continue
                if t == FN_SOLO:
                    ids = [ov.u32(lst + j * 4) for j in range(n)]
                else:
                    ids = [tuple(struct.unpack_from("<2H", ov.d, ov._o(lst + j * 4)))
                           for j in range(n)]
                c = BeatDuelists("solo" if t == FN_SOLO else "tag", ids, k)
                c.sites = {"list": lst, "capacity": n,
                           "n_at": regs.get("_at_r1"), "wins_at": regs.get("_at_r2")}
                parts.append(c)
            elif t == FN_ANY_SOLO:
                parts.append(BeatEveryDuelist("solo"))
            elif t == FN_ANY_TAG:
                parts.append(BeatEveryDuelist("tag"))

    out = []
    for p in parts:
        if isinstance(p, tuple) and p[0] == "_counter":
            if pending_cmp is None:
                out.append(Unknown(arm, "counter without threshold"))
            else:
                c = DuelsWon(pending_cmp[1])
                c.sites = {"cmp": pending_cmp[0]}
                out.append(c)
        else:
            out.append(p)

    if not out:
        # count-set-bits arms (47-55) and the card-percentage arm (60).  The
        # threshold is the `cmp r0, #imm` whose next instruction bails out to the
        # loop tail -- plain `cmp r0, #0` guards inside the loop body must not be
        # mistaken for it.
        ldr4 = [i for i in ins if i.mnemonic == "ldr" and "[r4," in i.op_str]
        movs = [i for i in ins if i.mnemonic == "mov" and i.op_str.startswith("r1, #")]
        cmp1 = [i for i in ins if i.mnemonic == "cmp" and i.op_str.startswith("r1, #")]
        cmps = []
        for k, i in enumerate(ins[:-1]):
            if i.mnemonic != "cmp" or not i.op_str.startswith("r0, #"):
                continue
            nxt = ins[k + 1]
            if nxt.mnemonic in ("blt", "beq", "bls", "bmi") and \
                    int(nxt.op_str.strip("#"), 0) == LOOP_TAIL:
                cmps.append(i)
        if ldr4 and cmps:
            need = cmps[-1]
            c = CountUnlocked(int(need.op_str.split("#")[1], 0),
                              int(movs[0].op_str.split("#")[1], 0) if movs else 0,
                              int(cmp1[0].op_str.split("#")[1], 0) - 1 if cmp1 else 0,
                              0x2000 + int(ldr4[0].op_str.split("#")[1].rstrip("]"), 0))
            c.sites = {"cmp": need.address}
            return c
        if cmps:
            c = CardPercent(int(cmps[-1].op_str.split("#")[1], 0))
            c.sites = {"cmp": cmps[-1].address}
            return c
        return Unknown(arm, f"unrecognised arm ({len(ins)} instructions)")

    return out[0] if len(out) == 1 else Compound(out)


def read_conditions(src: str | Path = SRC) -> dict:
    """Return ``{pack_id: Condition}`` for all 60 packs."""
    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    _, data = _load_ov1(rom)
    ov = _Ov1(data)

    arms = {p: ov.branch_target(JUMP_TABLE + p * 4)
            for p in range(FIRST_PACK, LAST_PACK + 1)}
    shared = {}
    for p, a in arms.items():
        shared.setdefault(a, []).append(p)

    conds = {}
    for p in range(FIRST_PACK, LAST_PACK + 1):
        c = _parse_arm(ov, arms[p])
        c.sites = dict(c.sites or {})
        c.sites.update(arm=arms[p], slot=JUMP_TABLE + p * 4,
                       shared_with=[q for q in shared[arms[p]] if q != p])
        conds[p] = c
    return conds


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _patch_imm(ov: _Ov1, addr: int, value: int):
    ov.set_u32(addr, (ov.u32(addr) & ~0xFFF) | _encode_imm(value))


def _apply_clause(ov: _Ov1, pid: int, old: Condition, new: Condition, lists_used: dict):
    if type(new) is not type(old):
        raise NotImplementedError(
            f"pack {pid}: cannot change {type(old).__name__} -> {type(new).__name__} "
            "in place (the replacement arm would not be the same size). Use "
            "Always()/Never()/SameAs(other_pack), or edit the existing rule's numbers.")

    if isinstance(new, StoryFlag):
        if new.flag_id != old.flag_id:
            ov.set_u32(old.sites["lit"], new.flag_id)
            return f"pack {pid}: story flag {old.flag_id:#06x} -> {new.flag_id:#06x}"
    elif isinstance(new, DuelsWon):
        if new.wins != old.wins:
            _patch_imm(ov, old.sites["cmp"], new.wins)
            return f"pack {pid}: duels won {old.wins} -> {new.wins}"
    elif isinstance(new, CountUnlocked):
        if new.need != old.need:
            _patch_imm(ov, old.sites["cmp"], new.need)
            return f"pack {pid}: duelists needed {old.need} -> {new.need}"
    elif isinstance(new, CardPercent):
        if new.percent != old.percent:
            _patch_imm(ov, old.sites["cmp"], new.percent)
            return f"pack {pid}: card completion {old.percent}% -> {new.percent}%"
    elif isinstance(new, BeatDuelists):
        msgs = []
        if new.wins != old.wins:
            ov.set_u32(old.sites["wins_at"], 0xE3A02000 | _encode_imm(new.wins))
            msgs.append(f"wins {old.wins} -> {new.wins}")
        if [tuple(x) if isinstance(x, (tuple, list)) else x for x in new.ids] != \
           [tuple(x) if isinstance(x, (tuple, list)) else x for x in old.ids]:
            lst, cap = old.sites["list"], old.sites["capacity"]
            if lists_used.get(lst, pid) != pid:
                raise ValueError(
                    f"pack {pid}: duelist list {lst:#010x} is shared with pack "
                    f"{lists_used[lst]} -- refusing to edit it")
            if len(new.ids) > cap:
                raise ValueError(
                    f"pack {pid}: {len(new.ids)} duelists requested but the list at "
                    f"{lst:#010x} only holds {cap}; same length or shorter only")
            for j, v in enumerate(new.ids):
                if new.mode == "tag":
                    struct.pack_into("<2H", ov.d, ov._o(lst + j * 4), v[0], v[1])
                else:
                    ov.set_u32(lst + j * 4, v)
            if len(new.ids) != len(old.ids):
                ov.set_u32(old.sites["n_at"], 0xE3A01000 | _encode_imm(len(new.ids)))
            lists_used[lst] = pid
            msgs.append(f"ids {old.ids} -> {list(new.ids)}")
        if msgs:
            return f"pack {pid}: " + "; ".join(msgs)
    return None


def _apply_one(ov: _Ov1, pid: int, old: Condition, new: Condition, lists_used: dict):
    if new == old:
        return None
    slot = old.sites["slot"]

    if isinstance(new, Always) and not isinstance(old, Always):
        ov.set_u32(slot, _branch(slot, PLAIN_SET))
        return f"pack {pid}: -> ALWAYS"
    if isinstance(new, Never) and not isinstance(old, Never):
        ov.set_u32(slot, _branch(slot, LOOP_TAIL))
        return f"pack {pid}: -> NEVER"
    if isinstance(new, SameAs):
        ov.set_u32(slot, _branch(slot, ov.branch_target(JUMP_TABLE + new.pack * 4)))
        return f"pack {pid}: -> same rule as pack {new.pack}"

    if old.sites.get("shared_with"):
        raise ValueError(
            f"pack {pid}: its arm at {old.sites['arm']:#010x} is shared with packs "
            f"{old.sites['shared_with']} -- editing it would change them too. "
            "Give this pack its own rule with SameAs()/Always()/Never() instead.")

    if isinstance(old, Compound):
        if not isinstance(new, Compound) or len(new.parts) != len(old.parts):
            raise NotImplementedError(
                f"pack {pid}: a compound rule's clause list cannot be resized in "
                f"place ({len(old.parts)} clauses). Edit the numbers inside "
                "`.parts`, or use Always()/Never()/SameAs().")
        msgs = [m for m in (_apply_clause(ov, pid, o, n, lists_used)
                            for o, n in zip(old.parts, new.parts)) if m]
        return "; ".join(msgs) if msgs else None

    return _apply_clause(ov, pid, old, new, lists_used)


def apply_conditions(conditions: dict, src: str | Path = SRC,
                     out: str | Path = OUT) -> list:
    """Apply *conditions* (``{pack_id: Condition}``) on top of the stock rules."""
    src, out = str(src), str(out)
    if src != out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out)

    stock = read_conditions(src)
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov_obj, data = _load_ov1(rom)
    ov = _Ov1(data)

    changes, lists_used = [], {}
    for pid in sorted(conditions):
        if pid not in stock:
            raise KeyError(f"pack {pid} is out of range {FIRST_PACK}..{LAST_PACK}")
        msg = _apply_one(ov, pid, stock[pid], conditions[pid], lists_used)
        if msg:
            changes.append(msg)

    if not changes:
        print("  no differences from stock -- nothing written")
        return changes
    _save_ov1(rom, ov_obj, ov.d, out)
    for m in changes:
        print("  " + m)
    print(f"  wrote -> {out}")
    return changes


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------
def _to_jsonable(c: Condition):
    d = {"type": type(c).__name__}
    for k, v in vars(c).items():
        if k == "sites":
            continue
        if k == "parts":
            d[k] = [_to_jsonable(p) for p in v]
        elif k == "ids":
            d[k] = [list(x) if isinstance(x, tuple) else x for x in v]
        else:
            d[k] = v
    return d


_TYPES = {t.__name__: t for t in (Always, Never, SameAs, StoryFlag, DuelsWon,
                                  BeatDuelists, BeatEveryDuelist, CountUnlocked,
                                  CardPercent, Compound, Unknown)}


def _from_jsonable(d):
    kw = {k: v for k, v in d.items() if k != "type"}
    if "parts" in kw:
        kw["parts"] = [_from_jsonable(p) for p in kw["parts"]]
    if "ids" in kw:
        kw["ids"] = [tuple(x) if isinstance(x, list) else x for x in kw["ids"]]
    return _TYPES[d["type"]](**kw)


def dump_json(path, src: str | Path = SRC):
    blob = {str(p): _to_jsonable(c) for p, c in sorted(read_conditions(src).items())}
    Path(path).write_text(json.dumps(blob, indent=2))
    print(f"  wrote {len(blob)} pack conditions -> {path}")


def apply_json(path, src: str | Path = SRC, out: str | Path = OUT):
    blob = json.loads(Path(path).read_text())
    return apply_conditions({int(p): _from_jsonable(d) for p, d in blob.items()},
                            src=src, out=out)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def main(src: str = SRC, out: str = OUT, *, write_text=None) -> None:
    del write_text                      # accepted for apply-all-patches uniformity
    if not CHANGES:
        # Still produce *out*: in the apply-all chain every step must hand the
        # next one a ROM, and a no-op step that wrote nothing would break it
        # anywhere src is not already the output file.
        if str(src) != str(out):
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(src), str(out))
        print("  CHANGES is empty -- uncomment a pack in CHANGES to edit it")
        return
    apply_conditions(CHANGES, src=src, out=out)


def verify(*, out: str | Path = OUT) -> bool:
    conds = read_conditions(out)
    bad = [p for p, c in conds.items() if isinstance(c, Unknown)]
    print(f"  [{'OK ' if not bad else 'BAD'}] parsed {len(conds)} packs"
          + (f", unrecognised: {bad}" if bad else ""))
    return not bad


def show(src: str | Path = SRC, names: bool = True):
    for p, c in sorted(read_conditions(src).items()):
        extra = (f"   (arm shared with {c.sites['shared_with']})"
                 if c.sites.get("shared_with") else "")
        line = f"  pack {p:2d}  {c}{extra}"
        if names and isinstance(c, BeatDuelists) and c.mode == "solo":
            line += "\n            " + ", ".join(name(i) for i in c.ids)
        print(line)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "dump":
        dump_json(sys.argv[2] if len(sys.argv) > 2 else "pack_conditions.json")
    elif cmd == "apply":
        apply_json(sys.argv[2] if len(sys.argv) > 2 else "pack_conditions.json")
    elif cmd == "show":
        show()
    else:
        main(SRC, OUT)

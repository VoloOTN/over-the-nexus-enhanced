"""SHARED SS-commit stamp: "when this card is Special Summoned FROM THE HAND, post a
turn-log node (and optionally take damage)".

Lifted 2026-09-14 out of unknown_synchron (CAVE_UNKSYN_STAMP, in-game confirmed
2026-09-02) because Assault Synchron needs a second arm and the site is two 4-byte BLs.

THE SITES.  `BL 0x02244D08` at both SS-commit routines, 0x022692F2 (A) and 0x022693A0 (C).
r0 = side at both; the return value is dead (the next instruction is `ldrh r0,[r4,#0xE]`);
the caller's r4 holds the summon descriptor 0x02298A28 and must survive.  The sites are
reached ONLY for Special Summons (GDB 2026-07-12).  T.G. Warwolf owns the adjacent
`BL 0x021A25A0` in the same routines -- a different call.  0x02244D08 itself is Chain
Energy's summon cost (0x021CF924 pay LP), so an LP change here is native.

THE ARMS ARE DATA, NOT CODE.  A zero-terminated table at CAVE_SSCOMMIT_TABLE of
{u16 cid, u16 kind, u32 damage}.  Each owner calls register() with its own row, so a card
that is not in the build adds no behaviour (a static arm list would ship Assault's arm in
every chain ROM through Unknown Synchron's step).

For desc[+0x0A] == 0x0B (hand) and desc[+0x0E] == row.cid:
    0x021D2584(side, cid, kind, 0)                 turn-log post
    if damage: 0x021CFB8C(side, damage, 0, cid)    "take N damage" (source = you)
then always replay `BL 0x02244D08(side)`.

Registered:
    0x181C Unknown Synchron   kind 5 (once per Duel), no damage
    0x13AE Assault Synchron   kind 1 (once per turn), 700 damage

Equivalence with the retired stub: `uv run python -m scratch.ss_commit_equiv`.
IN-GAME CONFIRMED BY USER 2026-09-14: both rows work and Unknown Synchron's once-per-Duel did not
regress (rom_assault_synchron.nds sha256 fbbf1701...fdf67bf).
DUEL-ONLY in the ov5 cave. register(..., ov3=True) on a ROM with no hook yet puts the stub + table in the
ov3 pool (cave3.CAVE3_SSCOMMIT_HOOK / _TABLE; needs step 0) so the stamp also runs in puzzles; every later
register()/ok() FOLLOWS THE LIVE BL at SITES[0], so all arms share one home. ov3 home in-game confirmed by user 2026-10-08, normal duel AND puzzle ('All good ... There rest are good to ship'); SHIPPED (via Unknown Synchron).
"""
from __future__ import annotations

import struct

from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import ov5_cave
from otn_enhanced.rom.overlay_io import RAM_BASE

SITES = (0x022692F2, 0x022693A0)
DISPLACED = 0x02244D08
SUMMON_DESC = 0x02298A28
DESC_SRC_ZONE = 0x0A
DESC_CID = 0x0E
ZONE_HAND = 0x0B
TURNLOG_POST = 0x021D2584        # (side, cid, kind, 0)
DAMAGE = 0x021CFB8C              # (target side, amount, side-xor flag, source cid)

HOOK = ov5_cave.CAVE_SSCOMMIT_HOOK
TABLE = ov5_cave.CAVE_SSCOMMIT_TABLE
HOOK_RESERVE = 0x50
TABLE_BYTES = 0x40               # 7 rows + zero terminator


def _bl(src: int, dst: int) -> tuple[int, int]:
    from otn_enhanced.effects.common import thumb_bl
    return struct.unpack("<2H", thumb_bl(src, dst))


def stub(base: int = HOOK, table: int = TABLE) -> bytes:
    a = EffectBuilder()
    (a
     .insn("PUSH", "{R4, R5, R6, LR}")
     .insn("ADD", "R4, R0, #0x0")                       # r4 = side
     .ldr_const(5, SUMMON_DESC)
     .insn("LDRH", f"R0, [R5, #0x{DESC_SRC_ZONE:X}]")
     .insn("CMP", f"R0, #0x{ZONE_HAND:X}")
     .insn("BNE", "replay")                             # not from the hand
     .insn("LDRH", f"R6, [R5, #0x{DESC_CID:X}]")        # r6 = summoned cid
     .ldr_const(5, table)
     .label("scan")
     .insn("LDRH", "R0, [R5, #0x0]")
     .insn("CMP", "R0, #0x0")
     .insn("BEQ", "replay")
     .insn("CMP", "R0, R6")
     .insn("BEQ", "hit")
     .insn("ADD", "R5, #0x8")                           # 2-operand imm8 (thumb-add-sub-imm3-footgun)
     .insn("B", "scan")
     .label("hit")
     .insn("ADD", "R0, R4, #0x0")
     .insn("ADD", "R1, R6, #0x0")
     .insn("LDRH", "R2, [R5, #0x2]")                    # kind
     .insn("MOV", "R3, #0x0")
     .bl(TURNLOG_POST)
     .insn("LDR", "R1, [R5, #0x4]")                     # damage
     .insn("CMP", "R1, #0x0")
     .insn("BEQ", "replay")
     .insn("ADD", "R0, R4, #0x0")
     .insn("MOV", "R2, #0x0")
     .insn("ADD", "R3, R6, #0x0")
     .bl(DAMAGE)
     .label("replay")
     .insn("ADD", "R0, R4, #0x0")
     .bl(DISPLACED)
     .insn("POP", "{R4, R5, R6, PC}"))
    code = a.assemble(base)
    assert len(code) <= HOOK_RESERVE, f"ss-commit stub {len(code)} B > 0x{HOOK_RESERVE:X}"
    assert_thumb1_only(code, base)
    return code


TABLE3_BYTES = 0x20              # ov3 pool table: 3 rows + zero terminator


def _homes():
    from otn_enhanced.effects import cave3
    return {"ov5": (HOOK, TABLE, TABLE_BYTES), "ov3": (cave3.CAVE3_SSCOMMIT_HOOK, cave3.CAVE3_SSCOMMIT_TABLE, TABLE3_BYTES)}


def live_home(ov) -> str | None:
    """'ov3' / 'ov5' = where the BL at SITES[0] points, None = native (no hook yet)."""
    cur = struct.unpack_from("<2H", ov, SITES[0] - RAM_BASE)
    return next((k for k, (hook, _, _) in _homes().items() if cur == _bl(SITES[0], hook)), None)


def _read(rom, ov, addr: int, n: int) -> bytes:
    from otn_enhanced.effects import cave3
    return cave3.read_code(rom, ov, addr, n)


def rows(rom, ov=None) -> list[tuple[int, int, int]]:
    _, table, size = _homes()[(live_home(ov) if ov is not None else None) or "ov5"]
    data = _read(rom, ov, table, size) if ov is not None else ov5_cave.read_cave(rom, TABLE, TABLE_BYTES)
    out = []
    for i in range(0, len(data), 8):
        cid, kind, dmg = struct.unpack_from("<HHI", data, i)
        if cid == 0:
            break
        out.append((cid, kind, dmg))
    return out


def register(rom, ov: bytearray, cid: int, kind: int, damage: int = 0, ov3: bool = False) -> None:
    """Install the stub + both hooks (idempotent) and append this card's row.

    The home is the LIVE one if a hook is already installed (all arms share it); otherwise ov3=True
    picks the ov3 pool, else the ov5 cave."""
    home = live_home(ov) or ("ov3" if ov3 else "ov5")
    if ov3 and home != "ov3":
        print(f"S ss-commit hook already lives in {home}: ov3=True ignored, row joins the live table")
    hook, table, size = _homes()[home]
    blob = stub(hook, table)
    if home == "ov3":
        from otn_enhanced.effects import cave3
        cave3.put(ov, hook, blob)
    elif ov5_cave.read_cave(rom, HOOK, len(blob)) != blob:
        ov5_cave.install_cave(rom, HOOK, blob, reserve=HOOK_RESERVE)

    have = rows(rom, ov) if live_home(ov) else []
    if (cid, kind, damage) not in have:
        assert cid not in [c for c, _, _ in have], f"ss-commit table already has 0x{cid:04X}"
        assert (len(have) + 2) * 8 <= size, "ss-commit table is full"
        row, data = table + len(have) * 8, struct.pack("<HHI", cid, kind, damage)
        if home == "ov3":
            o = row - RAM_BASE
            assert bytes(ov[o:o + 16]) == bytes(16), f"ov3 ss-commit table row @0x{row:08X} not zero"
            ov[o:o + 8] = data
        else:
            ov5_cave.install_cave(rom, row, data, reserve=8)

    for site in SITES:
        want, cur = _bl(site, hook), struct.unpack_from("<2H", ov, site - RAM_BASE)
        if cur != want:
            assert cur == _bl(site, DISPLACED), (
                f"SS-commit site 0x{site:08X} = {cur[0]:04X} {cur[1]:04X}: not the native "
                f"BL 0x{DISPLACED:08X} -- another patch owns it")
            struct.pack_into("<2H", ov, site - RAM_BASE, *want)
    print(f"S ss-commit hook @0x{hook:08X} ({home}): rows {[(hex(c), k, d) for c, k, d in rows(rom, ov)]}")


def ok(rom, ov: bytes, cid: int, kind: int, damage: int = 0) -> bool:
    """Hook + row check against the LIVE home (ov5 cave or ov3 pool)."""
    home = live_home(ov)
    if home is None:
        return False
    hook, table, _ = _homes()[home]
    blob = stub(hook, table)
    return (_read(rom, ov, hook, len(blob)) == blob
            and all(struct.unpack_from("<2H", ov, s - RAM_BASE) == _bl(s, hook) for s in SITES)
            and (cid, kind, damage) in rows(rom, ov))

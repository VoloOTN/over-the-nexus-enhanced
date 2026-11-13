"""The SHARED virtual GY-action rows: one 16-row table, the four GY sites, a REGISTER of cids.

WHY THIS MODULE EXISTS
======================
The GY-action registry 0x0228DDF8 (60 rows, unsorted, cannot grow) has no family-C phantom left
(otn-virtual-gy-action-row).  Revolution Synchron added a virtual row 60 through four 4-byte BL hooks
(GY_SITES); the stub generators below were generalised to N rows (formerly in magicians_rod); dragon_rulers took the
sites over with a 6-row table at CAVE_RUL_GYROWS (0x60 B) and sekkas_light appended the 6th row.
That table is FULL, and every Infernoble Knight that equips itself from the GY needs a row (user decision
2026-10-20: "a" = lift into a shared module, the summon_trigger_hook / c79_trigger_hook structure).

WHAT IT DOES
============
The rows already in the ROM are read LIVE from CAVE_RUL_GYROWS (Revolution's row 60 first, then the
Rulers, then Sekka's Light -- the same row indices as before, so nothing those cards see changes) and the
ARMS register is appended.  Table + the four stubs (the generators below, byte-for-byte the shapes that are
in-game confirmed for Revolution / the Rulers / Sekka's Light) go to NEW ov5 slots, and the four sites are
re-pointed from the Rulers' stubs to ours.  The Rulers' own table and stubs are left in place untouched
(dead code once the sites move), so their verify()'s ov5 checks still hold.

Adding a card is one entry in ARMS (max MAX_ROWS rows in all).

REGISTERED CARDS
    0x13A3  Robotic Knight -> Infernoble Knight Ogier C3   in-game confirmed by user 2026-10-20 (infernoble)
    0x139A  Wolf Axwielder -> Infernoble Knight Maugis C3  in-game confirmed by user 2026-10-20 (infernoble)
    0x1E04  Tune Warrior -> Infernoble Knight Oliver C3    in-game confirmed by user 2026-10-20 (infernoble)
    0x0FC1  Beaver Warrior -> Infernoble Knight Turpin      in-game confirmed by user 2026-10-20 (infernoble)
    0x0FE6  Tiger Axe -> Infernoble Knight Ricciardetto C1   in-game confirmed by user 2026-10-20 (infernoble)
    0x0FDD  Giant Flea -> Block Dragon C1 GY half            in-game confirmed by user 2026-11-09 (block_dragon); the table is now FULL (16/16)

DUEL-ONLY: everything lives in the ov5 cave, which overlay 41 evicts in the puzzle editor.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.cards import revolution_synchron as rev
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.effects.timing_class_hook import _bl

# --- the GY-action hook sites and the shared stub generators (moved here from the deleted magicians_rod) ---
GY_FAMILY = (0x0E, 0x0224C591, 0x0224C6C1)
GY_SITES = ((rev.H4_SITE, rev.H4_STOCK), (rev.H5_SITE, rev.H5_STOCK),
            (rev.H6_SITE, rev.H6_STOCK), (rev.H7_SITE, rev.H7_STOCK))


def gyfetch_stub(base: int, table: int) -> bytes:
    """Replaces `ldr r1,=0x0228DDF8 ; lsls r0,r6,#4`: rows >= 60 read the virtual table."""
    b = EffectBuilder()
    b.insn("CMP", "R6, #0x3C")
    b.insn("BGE", "virt")
    b.ldr_const(1, rev.GYREG_BASE)
    b.insn("LSL", "R0, R6, #0x4")
    b.insn("BX", "LR")
    b.label("virt")
    b.insn("LSL", "R1, R6, #0x4")
    b.ldr_const(0, (table - rev.GYREG_BASE - 0x3C0) & 0xFFFFFFFF)
    b.insn("ADD", "R0, R0, R1")
    b.ldr_const(1, rev.GYREG_BASE)
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def gyexit_stub(base: int, n: int) -> bytes:
    """The enumerator's loop exit (reached with r6 >= 60): replay rows 60..60+n-1, then exit natively."""
    b = EffectBuilder()
    b.insn("CMP", f"R6, #0x{0x3C + n:X}")
    b.insn("BGE", "rest")
    b.ldr_const(0, rev.ENUM_LOOP_HEAD | 1)
    b.insn("BX", "R0")
    b.label("rest")
    b.insn("MOV", "R6, #0x3C")
    b.ldr_const(0, rev.ENUM_POST_EXIT)
    b.insn("LDR", "R1, [R0, #0x34]")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def _cid_tests(b: EffectBuilder, reg: int, cids: list, hit: str, miss: str) -> None:
    """`ldr r0,=cid ; cmp reg,r0` per cid; the LAST cid's value is left in r0 on a miss."""
    for i, cid in enumerate(cids):
        b.ldr_const(0, cid)
        b.insn("CMP", f"R{reg}, R0")
        b.insn("BNE", miss) if i == len(cids) - 1 else b.insn("BEQ", hit)


def gypost_stub(base: int, cids: list) -> bytes:
    """post-by-cid exit: r4 = rows walked, r5 = cid, r6/r7 = the post's r0/r2.  The LAST cid is
    compared last so a miss leaves r0 == that cid -- exactly what Revolution's shipped stub does."""
    b = EffectBuilder()
    b.insn("CMP", "R4, #0x3C")
    b.insn("BLT", "out")
    _cid_tests(b, 5, cids, "post", "out")
    b.label("post")
    b.insn("ADD", "R0, R6, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.insn("ADD", "R2, R7, #0x0")
    b.bl(rev.GY_POST & ~1)
    b.label("out")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


def gyhas_stub(base: int, cids: list) -> bytes:
    """has-row not-found exit: r0 = the queried cid.  The LAST cid compared last (r1 == it on a miss)."""
    b = EffectBuilder()
    for c in cids:
        b.ldr_const(1, c)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "yes")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R3, R4, R5, PC}")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R3, R4, R5, PC}")
    return b.assemble(base, pad="nop")


MAX_ROWS = 16
ROWS, FETCH, EXIT, POST, HAS = O5.CAVE_GYV_ROWS, O5.CAVE_GYV_FETCH, O5.CAVE_GYV_EXIT, O5.CAVE_GYV_POST, O5.CAVE_GYV_HAS
RESERVES = {ROWS: 0x100, FETCH: 0x20, EXIT: 0x20, POST: 0xC0, HAS: 0xB0}
STUBS = (FETCH, EXIT, POST, HAS)
# GYV2 layout (pantheism): the table and the has-row stub relocated for a 17th row; FETCH / EXIT / POST stay in place (regenerated).  Used with install(..., layout=GYV2).
GYV2 = {"ROWS": (O5.CAVE_GYV2_ROWS, 0x180), "HAS": (O5.CAVE_GYV2_HAS, 0x100), "POST": (O5.CAVE_GYV2_POST, 0x120), "MAX": 24}
# The Monarch cards' Graveyard effects (installed by their modules with layout=GYV2; every one of them passes the WHOLE tuple, so the table is the same whichever installs last).
MONARCH_ARMS: tuple[tuple[int, str], ...] = (
    (0x1923, "Pantheism of the Monarchs C3 (GY ignition)"),
    (0x14C3, "Frost Blast of the Monarchs C2 (GY ignition)"),
    (0x1DCD, "The Monarchs Revolt C5 (GY: Special Summon an 800/1000 monster from the hand)"),
    (0x0FE2, "Eidos the Underworld Squire E2 (GY: banish this card, Special Summon an 800/1000 monster from the GY)"),
    (0x0DE4, "Strike of the Monarchs S4 (GY: banish this card, declare an Attribute)"),
    (0x1313, "Erebus the Underworld Monarch E2 (GY: discard a Monarch S/T, add a 2400+/1000 monster from the GY)"),
    (0x14CF, "The Prime Monarch GY half (GY: banish another Monarch S/T, Special Summon this card as a monster)"),
)                   # site order == GY_SITES order (H4, H5, H6, H7)
RUL_STUBS = (O5.CAVE_RUL_GYFETCH, O5.CAVE_RUL_GYEXIT, O5.CAVE_RUL_GYPOST, O5.CAVE_RUL_GYHAS)
RUL_ROWS, RUL_ROWS_LEN = O5.CAVE_RUL_GYROWS, 0x60

ARMS: tuple[tuple[int, str], ...] = (
    (0x13A3, "Robotic Knight -> Infernoble Knight Ogier C3 (in-game confirmed by user 2026-10-20)"),
    (0x139A, "Wolf Axwielder -> Infernoble Knight Maugis C3 (in-game confirmed by user 2026-10-20)"),
    (0x1E04, "Tune Warrior -> Infernoble Knight Oliver C3 (in-game confirmed by user 2026-10-20)"),
    (0x0FC1, "Beaver Warrior -> Infernoble Knight Turpin C2-GY / C3 (in-game confirmed by user 2026-10-20)"),
    (0x0FE6, "Tiger Axe -> Infernoble Knight Ricciardetto C1 from the GY (in-game confirmed by user 2026-10-20)"),
    (0x0FD4, "Griffore -> Infernoble Knight Astolfo C2 (banish from the GY) (in-game confirmed by user 2026-10-21)"),
    (0x0FEB, "Thousand Dragon -> Infernoble Knight Captain Roland C2 (GY Quick Effect)"),
    (0x1118, "Labyrinth Tank -> Infernoble Knight Captain Oliver C2 (GY SS + equip)"),
    (0x16DB, "Big Burn -> The Continuing Epic of Charles E2 (banish from the GY)"),
    (0x0FDD, "Giant Flea -> Block Dragon C1 GY half (in-game confirmed by user 2026-11-09)"),   # 16/16: the next GY card needs MAX_ROWS raised
)


def base_rows(rom) -> list[tuple]:
    """The rows the shipped chain already owns, read live from the Rulers' table (Revolution's row first)."""
    raw = O5.read_cave(rom, RUL_ROWS, RUL_ROWS_LEN)
    out = []
    for i in range(RUL_ROWS_LEN // 16):
        r = struct.unpack_from("<4I", raw, i * 16)
        if r[1:] != tuple(GY_FAMILY):
            break
        out.append(r)
    assert out and out[0] == tuple(rev.GYREG_ROW), "Revolution Synchron's row 60 is not first -- not a chain ROM?"
    return out


def rows(rom, arms: tuple = ARMS, max_rows: int = MAX_ROWS) -> list[tuple]:
    have = base_rows(rom)
    extra = [(cid,) + tuple(GY_FAMILY) for cid, _ in arms if cid not in [r[0] for r in have]]
    out = have + extra
    assert len(out) <= max_rows, f"{len(out)} virtual GY rows > {max_rows}"
    return out


def compare_order(rs: list[tuple]) -> list[int]:
    """Revolution's cid LAST, so a miss leaves r0 / r1 == it (the proven generalisation)."""
    cids = [r[0] for r in rs]
    return cids[1:] + cids[:1]


def blobs(rom, arms: tuple = ARMS, layout: dict | None = None) -> list[tuple[int, bytes, bool]]:
    rs = rows(rom, arms, layout["MAX"] if layout else MAX_ROWS)
    cids = compare_order(rs)
    rows_addr = layout["ROWS"][0] if layout else ROWS
    has_addr = layout["HAS"][0] if layout else HAS
    post_addr = layout["POST"][0] if layout and "POST" in layout else POST
    return [(rows_addr, b"".join(struct.pack("<4I", *r) for r in rs), False),
            (FETCH, gyfetch_stub(FETCH, rows_addr), True),
            (EXIT, gyexit_stub(EXIT, len(rs)), True),
            (post_addr, gypost_stub(post_addr, cids), True),
            (has_addr, gyhas_stub(has_addr, cids), True)]


def _rewrite(rom, addr: int, blob: bytes, reserves: dict | None = None) -> None:
    reserve = (reserves or RESERVES)[addr]
    assert len(blob) <= reserve, f"GYV {addr:#x}: {len(blob)} B > reserve {reserve:#x}"
    if O5.read_cave(rom, addr, reserve) == blob + bytes(reserve - len(blob)):
        return
    ov5 = O5._load_ov5_decompressed(rom)
    data = bytearray(ov5.data)
    if len(data) == O5.OV5_NATIVE_LEN:              # first cave write into a stock-length ov5
        O5.install_cave(rom, addr, blob, reserve=reserve)
        return
    o = addr - O5.OV5_RAM_BASE
    data[o:o + reserve] = blob + bytes(reserve - len(blob))
    O5._save_ov5(rom, ov5, bytes(data))


def install(rom, ov: bytearray, arms: tuple = ARMS, layout: dict | None = None) -> None:
    """Table + stubs into ov5, then re-point the four sites (Rulers' stubs -> ours). Idempotent.  layout=GYV2 relocates the table and the has-row stub."""
    reserves = dict(RESERVES)
    stubs = list(STUBS)
    if layout:
        reserves[layout["ROWS"][0]] = layout["ROWS"][1]
        reserves[layout["HAS"][0]] = layout["HAS"][1]
        stubs[3] = layout["HAS"][0]
        if "POST" in layout:
            reserves[layout["POST"][0]] = layout["POST"][1]
            stubs[2] = layout["POST"][0]
    for addr, blob, code in blobs(rom, arms, layout):
        if code:
            effect_verify.assert_thumb1_only(blob, addr)
        _rewrite(rom, addr, blob, reserves)
        print(f"GYV ov5 {addr:#010x}: {len(blob)} B / {reserves[addr]:#x}")
    for (site, _stock), rul, ours, old_ours in zip(GY_SITES, RUL_STUBS, stubs, STUBS):
        o = site - RAM_BASE
        cur = bytes(ov[o:o + 4])
        assert cur in (_bl(site, rul), _bl(site, ours), _bl(site, old_ours)),             f"GYV site {site:#x} = {cur.hex()}: not Dragon Rulers' stub BL -- who owns it?"
        ov[o:o + 4] = _bl(site, ours)
        print(f"GYV bl @{site:#010x} -> {ours:#010x}")


def _stubs(layout: dict | None) -> tuple:
    return (FETCH, EXIT, layout["POST"][0] if layout and "POST" in layout else POST, layout["HAS"][0] if layout else HAS)


def live(ov) -> tuple[dict | None, tuple]:
    """(layout, arms) the ROM was LAST installed with: the Monarch cards move it to GYV2 with MONARCH_ARMS."""
    def at(stubs):
        return all(bytes(ov[s - RAM_BASE:s - RAM_BASE + 4]) == _bl(s, a) for (s, _), a in zip(GY_SITES, stubs))
    return (GYV2, ARMS + MONARCH_ARMS) if at(_stubs(GYV2)) else (None, ARMS)


def installed(rom, ov) -> bool:
    """True when the four sites point at our stubs, in either layout (used by the Rulers / Revolution verify tolerance)."""
    return any(all(bytes(ov[s - RAM_BASE:s - RAM_BASE + 4]) == _bl(s, a) for (s, _), a in zip(GY_SITES, _stubs(lay)))
               for lay in (None, GYV2))


def verify(rom, ov, check, arms: tuple = ARMS) -> None:
    layout, live_arms = live(ov)                 # check what is actually installed, not the pre-Monarch layout
    for addr, blob, _code in blobs(rom, live_arms, layout):
        check(O5.read_cave(rom, addr, len(blob)) == blob, f"GYV ov5 {addr:#x} ({len(blob)} B) byte-exact")
    check(installed(rom, ov), "GYV the four GY sites BL our stubs")
    rs = rows(rom, live_arms, layout["MAX"] if layout else MAX_ROWS)
    assert all(a in live_arms for a in arms), "a caller's arm is missing from the live GYV arm set"
    check(rs[0] == tuple(rev.GYREG_ROW), "GYV row 60 is still Revolution Synchron's")
    for cid, _ in arms:
        check(sum(r[0] == cid for r in rs) == 1, f"GYV exactly one virtual row for {cid:#06x}")

"""find_event_handler PRE-DISPATCH hook: lets a card own a VIRTUAL effect record next to a real one of the same table.

find_event_handler 0x0224A118 binary-searches the table selected by desc[+5] and returns the LEFTMOST record of the cid, so a card cannot have two cls2 records (a leave trigger and a hand
ignition, Tessera).  The existing miss-tail front (Gearfried's H1 @0x0224A86A) only fires when NO record exists.  This hook sits at the function's first dispatch step:

    0x0224A122  ldrb r0,[r4,#5]          r0 = class, r4 = desc, [sp] = cid (str r0,[sp] @0x0224A120)
    0x0224A124  cmp r0,#3 ; bhi 0x0224A174     <-- HOOK SITE (4 B): bl stub

The stub is entered with the function's frame (push {r1-r7,lr}) still on the stack: on a hit it loads r0 = &virtual record and `pop {r1-r7,pc}` straight out of the host; otherwise it
replays `cmp r0,#3 ; bhi` (BX LR resumes 0x0224A128, a miss for class > 3 jumps to 0x0224A174).  ENTRIES = (cid, class, zone, vrec address): matched on desc[+5] == class, desc[+3] == zone,
desc[+4] == 0 (Gearfried's hand-effect lookup: class 2, zone 0xB).  DUEL-ONLY (ov5 cave).
"""
from __future__ import annotations

from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target  # noqa: F401

SITE = 0x0224A124
NATIVE = bytes.fromhex("032825d8")            # cmp r0,#3 ; bhi 0x0224A174
FAR = 0x0224A174
RESERVE = 0x100                               # 0x90 -> 0xC0 -> 0x100 (2026-11-12; 7 entries: Tessera, Strike, Erebus, Ehther, Prime, Eidos E3, Masterplan C2)

ENTRIES: list[tuple[int, int, int, int, str, bool]] = []   # (cid, class, zone, vrec, note, any_sub): filled by the cards at compile time (unshipped test cards only)


def register(cid: int, vrec: int, note: str, cls: int = 2, zone: int = 0xB, any_sub: bool = False) -> None:
    """any_sub: skip the desc[+4] == 0 test (the GY-action descriptor builder 0x0224C590 loads desc[+4] from state; use only for a cid that owns
    NO real record of this class, so every lookup of (cid, class, zone) is this effect)."""
    if all(e[0] != cid or e[1] != cls or e[2] != zone for e in ENTRIES):
        ENTRIES.append((cid, cls, zone, vrec, note, any_sub))


def stub(base: int) -> bytes:
    assert ENTRIES, "no pre-dispatch entries registered"
    b = EffectBuilder()
    b.insn("LDR", "R1, [SP, #0x0]")
    for i, (cid, cls, zone, vrec, _, any_sub) in enumerate(ENTRIES):
        nxt = f"n{i}"
        b.insn("CMP", f"R0, #0x{cls:X}")
        b.insn("BNE", nxt)
        b.ldr_const(2, cid)
        b.insn("CMP", "R1, R2")
        b.insn("BNE", nxt)
        b.insn("LDRB", "R3, [R4, #0x3]")
        b.insn("CMP", f"R3, #0x{zone:X}")
        b.insn("BNE", nxt)
        if not any_sub:
            b.insn("LDRB", "R3, [R4, #0x4]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BNE", nxt)
        b.ldr_const(0, vrec)
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        b.label(nxt)
    b.insn("CMP", "R0, #0x3")
    b.insn("BHI", "far")
    b.insn("BX", "LR")
    b.label("far")
    b.ldr_const(3, FAR | 1)
    b.insn("BX", "R3")
    return b.assemble(base, pad="nop")


def install(rom, view) -> None:
    """Write the stub into ov5 (idempotent) and point the 4-byte site at it."""
    base = ov5_cave.CAVE_PF_STUB
    blob = stub(base)
    effect_verify.assert_thumb1_only(blob, base)
    assert len(blob) <= RESERVE, f"prefind stub {len(blob)} B > {RESERVE:#x}"
    if ov5_cave.read_cave(rom, base, len(blob)) != blob:
        if any(ov5_cave.read_cave(rom, base, RESERVE)):
            ov5 = ov5_cave._load_ov5_decompressed(rom)
            data = bytearray(ov5.data)
            off = base - ov5_cave.OV5_RAM_BASE
            data[off:off + RESERVE] = bytes(RESERVE)
            ov5_cave._save_ov5(rom, ov5, bytes(data))
        ov5_cave.install_cave(rom, base, blob, reserve=RESERVE)
    cur = bytes(view.blob(SITE, 4))
    want = common_bl(SITE, base)
    assert cur in (NATIVE, want), f"prefind site {SITE:#x} is {cur.hex()}, expected native {NATIVE.hex()}"
    view.write(SITE, want)


def verify(rom, view, check) -> None:
    base = ov5_cave.CAVE_PF_STUB
    blob = stub(base)
    check(bytes(view.blob(SITE, 4)) == common_bl(SITE, base), f"prefind site 0x{SITE:08X} -> stub 0x{base:08X}")
    check(ov5_cave.read_cave(rom, base, len(blob)) == blob, f"prefind stub byte-exact ({len(blob)} B, entries {[hex(e[0]) for e in ENTRIES]})")

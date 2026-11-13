"""Disguise, the Copycat Hero (0x111E, donor Monster Tamer) + Cursed Copycat Noble Arms (0x10E3, donor Cyber Shield).

Both whole cards, one module (user 2026-11-04). SINGLE-CARD TEST ROM ONLY: layered on the chain ROM, NOT in
steps.STEPS / SHIPPED. Design, proofs and rulings: notes/disguise-copycat-hero-findings.md.

Disguise   C1 cls2 hand SS (Oliver shape)      + ARM9 H4 hand-offer front
           C2 cls1 NS/SS "You can" search      + c79 arm, timing-class arm, never-miss front, virtual criteria row
           C3 cls3 ignition (Copy Plant shape) : riders {0x1D43, 2, name} + {0x1EC1, 2, Level}
Noble Arms N0 equip-target arm 0x021D7A7C -> default arm (any monster); grant row[17] zeroed
           N1 stat front 0x021B7088: +200 ATK/DEF per face-up Equip Spell (field) + GY
           N2 cls3 ignition: Warrior lock, native Deck-SS 0x02206CAC (virtual row), relink 0x021C4BF0, destroy
Virtual criteria rows use their own namespace (index 0xFF00|j): an H2 front names them, an H3 front maps them to
CAVE_DC_ROWS (the Rulers window 0x023A6BF0..0x023A9BB0 has no free 0x40 grid point).

    uv run python _build_disguise_copycat.py
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R4
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS1, CLS2, CLS3, Compiled, Row, card, card_props
from otn_enhanced.effects import cave3 as C3
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

DISGUISE, NOBLE_ARMS = 0x111E, 0x10E3
KEY_C2 = 0x711E
C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_disguise_copycat.nds"

# --- natives (all Thumb, odd) ------------------------------------------------------------------------------
DECK_TO_HAND, HAS_CANDIDATE, NAMED_DECK_H = 0x02207EF5, 0x021F0821, 0x0223D075
COPY_PLANT_TSEL, RET2 = 0x02234D81, 0x0224A115            # Copy Plant's +14 target step; `movs r0,#2 ; bx lr`
DECK_WORKER, TAG_YOU_CAN = 0x0223BC3D, 0x021E51E5
H3_RESUME = 0x02243F71
for _v in (DECK_TO_HAND, HAS_CANDIDATE, NAMED_DECK_H, COPY_PLANT_TSEL, RET2, DECK_WORKER, TAG_YOU_CAN, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

# --- shared sites and the owner each must hold BEFORE us (chain ROM 2026-11-04) -------------------------------
_DN = O5.dc_next()                                         # front -> fall-through (single source, ov5_cave)
H2_SITE, H2_PREV = 0x02243F24, _DN[O5.CAVE_DC_H2]           # Sacred Sword's front
H3_SITE, H3_PREV = 0x02243F62, _DN[O5.CAVE_DC_H3]           # Dragon Rulers' H3
MISS_SITE, MISS_PREV = 0x021EE10C, _DN[O5.CAVE_DC_MISS]     # Infernoble Arms never-miss front
STAT_SITE, STAT_PREV = 0x021B7088, _DN[O5.CAVE_DC_N1_FRONT] # Captain Oliver's stat front
H4_SITE, H4_PREV = 0x02023566, _DN[O5.CAVE_DC_H4]           # ARM9, Roland's hand-offer front
EQ_ARM, EQ_ARM_STOCK, EQ_DEFAULT = 0x021D7A7C, 0xF64B, 0x021D7FA4   # Cyber Shield's Harpie gate (bl 0x02022E98 hi)
GRANT_BASE, GRANT_COUNT = 0x0226DFB0, 94                    # equip ATK/DEF table {cid, atk, def} x6; 0x10E3 = +500/0


def _grant_row(view) -> int:
    hits = [GRANT_BASE + 6 * i for i in range(GRANT_COUNT) if view.u16(GRANT_BASE + 6 * i) == NOBLE_ARMS]
    assert len(hits) == 1, f"Cyber Shield owns {len(hits)} grant rows"
    return hits[0]

S = {n: getattr(O5, f"CAVE_DC_{n}") for n in (
    "ROWS", "C3_FILT", "C3_COND", "C3_COST", "C3_RES", "C1_COND", "C1_RES", "C2_COND", "C2_SLOT4", "H2", "H3", "MISS",
    "H4", "N1_FRONT", "N1_COUNT", "N2_COND", "N2_COST", "N2_RES", "N2_H", "N2_CB")}
RESERVE = {"ROWS": 0x40, "C3_FILT": 0x50, "C3_COND": 0x70, "C3_COST": 0x30, "C3_RES": 0x90, "C1_COND": 0xE0,
           "C1_RES": 0x50, "C2_COND": 0x30, "C2_SLOT4": 0x30, "H2": 0x30, "H3": 0x30, "MISS": 0x20, "H4": 0x20,
           "N1_FRONT": 0x40, "N1_COUNT": 0xA0, "N2_COND": 0xC0, "N2_COST": 0x30, "N2_RES": 0x1B0, "N2_H": 0x30,
           "N2_CB": 0x20}

# --- table records -------------------------------------------------------------------------------------------
C3_REC = (DISGUISE, S["C3_RES"] | 1, S["C3_FILT"] | 1, S["C3_COND"] | 1, S["C3_COST"] | 1, COPY_PLANT_TSEL)
C1_REC = (DISGUISE, 0, S["C1_RES"] | 1, 0, S["C1_COND"] | 1, RET2, RET2)
C2_REC = (DISGUISE, 0, DECK_TO_HAND, 0, S["C2_COND"] | 1, S["C2_SLOT4"] | 1, 0)
N2_REC = (NOBLE_ARMS, S["N2_RES"] | 1, 0, S["N2_COND"] | 1, S["N2_COST"] | 1, 0)
C3_PHANTOM, C1_PHANTOM, C2_PHANTOM, N2_PHANTOM = 0x0E88, 0x1B19, 0x0E9F, 0x14C5
ROW_C2 = (DISGUISE, NOBLE_ARMS, NAMED_DECK_H, 0x00000004)          # Remus' named Deck pick: aux = the target cid
ROW_N2 = (NOBLE_ARMS, 0xFFFF, S["N2_H"] | 1, 0x00000000)           # word + [+0xC] excluded cid written at runtime
ROWS_BLOB = struct.pack("<HHII", *ROW_C2) + bytes(4) + struct.pack("<HHII", *ROW_N2) + bytes(4) + bytes(0x20)


def _c(src: str, slot: str, stub: str) -> bytes:
    blob = compile_c(C_DIR / src, S[slot], {"STUB": stub, "ROWS": f"0x{S['ROWS']:08X}"})
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


# --- hand-written fronts (registers / frames the C ABI cannot express) ---------------------------------------
def h2_front() -> bytes:
    """criteria resolver miss tail (r5 = cid; Tenki / SSS shape): ours -> 0xFF00 | j, else the previous front."""
    b = EffectBuilder()
    for j, cid in enumerate((DISGUISE, NOBLE_ARMS)):
        b.ldr_const(0, cid)
        b.insn("CMP", "R5, R0")
        b.insn("BEQ", f"j{j}")
    b.bl(H2_PREV)
    for j in range(2):
        b.label(f"j{j}")
        b.insn("MOV", "R0, #0xFF")
        b.insn("LSL", "R0, R0, #0x8")
        if j:
            b.insn("ADD", f"R0, #0x{j:X}")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    return _asm(b, "H2")


def h3_front() -> bytes:
    """invoker row compute (r6 = index): high byte 0xFF -> r0 = CAVE_DC_ROWS + (r6 & 0xFF) * 0x10, r3 = [r0+4], resume
    0x02243F70 (Rulers' H3 contract); else tail-jump to Rulers' H3 with lr intact (r0 is dead there)."""
    b = EffectBuilder()
    b.insn("LSR", "R0, R6, #0x8")
    b.insn("CMP", "R0, #0xFF")
    b.insn("BNE", "prev")
    b.insn("LSL", "R0, R6, #0x18")
    b.insn("LSR", "R0, R0, #0x14")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _asm(b, "H3")


def miss_front() -> bytes:
    """miss-timing node (r3 = cid; Arms' AR_MISS shape): Disguise -> return with Z set (never miss), else previous."""
    b = EffectBuilder()
    b.ldr_const(1, DISGUISE)
    b.insn("CMP", "R3, R1")
    b.insn("BEQ", "ret")
    b.ldr_const(1, MISS_PREV | 1)
    b.insn("BX", "R1")
    b.label("ret")
    b.insn("BX", "LR")
    return _asm(b, "MISS")


def h4_front() -> bytes:
    """ARM9 0x02023566 BL (r0 = cid; Turpin's T_H4 shape): Disguise -> 1 (hand effect offered), else previous."""
    b = EffectBuilder()
    b.ldr_const(3, DISGUISE)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "prev")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, H4_PREV | 1)
    b.insn("BX", "R3")
    return _asm(b, "H4")


def n1_front() -> bytes:
    """BL over `ldr r1,=0x0226DFB0 ; adds r0,r5,#0` @0x021B7088 (recompute 0x021B44C0; r5 = equip cid; frame: [sp+0x7C]
    equip side, [sp+0xB0] ATK acc, [sp+0xAC] DEF acc). Noble Arms -> both += 200 x Equip Spells of its controller.
    Then tail-jump to Captain Oliver's front (which replays the pair) with every register and lr restored."""
    b = EffectBuilder()
    b.insn("PUSH", "{R2, R3, R4, R6, R7, LR}")
    b.ldr_const(1, NOBLE_ARMS)
    b.insn("CMP", "R5, R1")
    b.insn("BNE", "prev")
    b.insn("LDR", "R0, [SP, #0x94]")
    b.ldr_const(3, S["N1_COUNT"] | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R1, [SP, #0xC8]")
    b.insn("ADD", "R1, R1, R0")
    b.insn("STR", "R1, [SP, #0xC8]")
    b.insn("LDR", "R1, [SP, #0xC4]")
    b.insn("ADD", "R1, R1, R0")
    b.insn("STR", "R1, [SP, #0xC4]")
    b.label("prev")
    b.insn("POP", "{R2, R3, R4, R6, R7}")
    b.insn("POP", "{R0}")
    b.insn("MOV", "LR, R0")
    b.ldr_const(0, STAT_PREV | 1)
    b.insn("BX", "R0")
    return _asm(b, "N1_FRONT")


def n2_handler() -> bytes:
    """criteria handler (r0 = &row, r1 = side, r2 = param; Ogier C2H shape): Deck worker 0x0223BC3C with [sp] = row word,
    [sp+4] = flags 2, r2 = N2_CB, r3 = row[+0xC] (the callback's [sp+4] = excluded cid)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R2, R0, #0x0")
    b.insn("LDR", "R0, [R2, #0x8]")
    b.insn("STR", "R0, [SP, #0x0]")
    b.insn("MOV", "R0, #0x2")
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("LDRH", "R3, [R2, #0xC]")
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R2, #0x0]")
    b.ldr_const(2, S["N2_CB"] | 1)
    b.ldr_const(4, DECK_WORKER)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return _asm(b, "N2_H")


def n2_callback() -> bytes:
    """worker callback ([sp] = &card word, [sp+4] = excluded cid; Ogier's c2cb): keep iff cid != excluded."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("LDR", "R1, [SP, #0x4]")
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "no")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    return _asm(b, "N2_CB")


def c2_cond() -> bytes:
    """cls1 +0C (Shadow Mist shape): KEY_C2 not posted -> RotA's candidate count over the virtual row, else 0."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.insn("MOV", "R1, #0xB")
    b.ldr_const(2, KEY_C2)
    b.insn("MOV", "R3, #0x1")
    b.ldr_const(6, dsl._TURNLOG_QUERY_ODD)
    b.insn("BLX", "R6")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "used")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.ldr_const(6, HAS_CANDIDATE)
    b.insn("BLX", "R6")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("used")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, PC}")
    return _asm(b, "C2_COND")


# --- shared registers: the C2 arms live in c79_trigger_hook.ARMS and timing_class_hook.ARMS (installed by earlier
# steps); the fronts' fall-throughs are ov5_cave.dc_next(), which owners' checks step over with dc_skip / ik_walk. ----


def _exits(base: int, blob: bytes) -> set[int]:
    """Every BL target and every odd (Thumb) pool literal in an assembled front, even-ised."""
    from otn_enhanced.asm.thumb_disasm import decode_thumb
    out = {i.branch_target for i in decode_thumb(blob, base) if i.mnemonic == "BL"}
    out |= {w & ~1 for (w,) in struct.iter_unpack("<I", blob[:len(blob) & ~3]) if w & 1}
    return out


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


@dataclass(frozen=True)
class disguise_whole_card:
    def compile(self, view, cid) -> Compiled:
        assert cid == DISGUISE
        stubs = (
            (S["ROWS"], ROWS_BLOB, "virtual criteria rows (C2 j0, N2 j1, N2 scratch j2)"),
            (S["C3_FILT"], _c("disguise_c3.c", "C3_FILT", "FILT"), "C3 +08 filter"),
            (S["C3_COND"], _c("disguise_c3.c", "C3_COND", "COND"), "C3 +0C cond"),
            (S["C3_COST"], _c("disguise_c3.c", "C3_COST", "COST"), "C3 +10 cost (OPT)"),
            (S["C3_RES"], _c("disguise_c3.c", "C3_RES", "RES"), "C3 +04 riders"),
            (S["C1_COND"], _c("disguise_c1.c", "C1_COND", "COND"), "C1 +0C hand cond"),
            (S["C1_RES"], _c("disguise_c1.c", "C1_RES", "RES"), "C1 +04 hand SS"),
            (S["C2_COND"], c2_cond(), "C2 +0C"),
            (S["C2_SLOT4"], dsl._hopt_you_can_stub(S["C2_SLOT4"], KEY_C2), "C2 +10 You can + OPT"),
            (S["H2"], h2_front(), "H2 front"),
            (S["H3"], h3_front(), "H3 front"),
            (S["MISS"], miss_front(), "never-miss front"),
            (S["H4"], h4_front(), "ARM9 H4 front"))
        rows = (Row(CLS3, C3_REC, C3_PHANTOM), Row(CLS2, C1_REC, C1_PHANTOM), Row(CLS1, C2_REC, C2_PHANTOM))

        def install(rom, view):
            _front_at(view, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(view, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            _front_at(view, MISS_SITE, MISS_PREV, S["MISS"], "miss-timing node")
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (common_bl(H4_SITE, H4_PREV), common_bl(H4_SITE, S["H4"])), \
                f"ARM9 H4 site {H4_SITE:#x} is not Roland's front"
            d[a:a + 4] = common_bl(H4_SITE, S["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            from otn_enhanced.effects import c79_trigger_hook as c79
            from otn_enhanced.effects import timing_class_hook as tch
            def reaches(t, want):                  # noble_knight_medraut's H2/H3 fronts may sit AHEAD of ours
                nxt = O5.dc_next()
                while t != want and t in nxt:
                    t = nxt[t]
                return t == want
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3"), (MISS_SITE, "MISS")):
                c.ok(reaches(ov3_bl_target(view.buf, site), S[slot]), f"bl @{site:#x} -> {slot} front")
            c.ok(DISGUISE in [a[0] for a in c79.ARMS], "0x111E registered in c79_trigger_hook.ARMS")
            slot = c79.where()[0]                 # the stub moves to a bigger slot as later cards add arms
            c.ok(code_reaches(rom, c79.SITE, slot), "c79 verdict reaches the shared stub")
            blob = c79.stub(slot)
            c.ok(O5.read_cave(rom, slot, len(blob)) == blob, "shared c79 stub carries the 0x111E arm")
            c.ok(tch.ARMS[0][0] == DISGUISE, "0x111E arm PREPENDED in timing_class_hook.ARMS")
            blob = tch.stub(O5.CAVE_TIMINGHOOK)
            c.ok(O5.read_cave(rom, O5.CAVE_TIMINGHOOK, len(blob)) == blob, "shared timing stub carries the 0x111E arm")
            built = {S["H2"]: h2_front(), S["H3"]: h3_front(), S["MISS"]: miss_front(), S["H4"]: h4_front(),
                     S["N1_FRONT"]: n1_front()}
            for front, prev in O5.dc_next().items():      # the owners' map must match each front's real fall-through
                if front not in built:
                    continue                                # not ours (noble_knight_medraut proves its own)
                c.ok(prev in _exits(front, built[front]), f"dc_next {front:#x} -> {prev:#x} is an exit of that front")
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            c.ok(bytes(sec.data[a:a + 4]) in {common_bl(H4_SITE, f) for f in O5.dc_ahead_of(S["H4"])},   # Gearfried's / Block Dragon's fronts may sit ahead
                 "ARM9 bl @0x02023566 -> H4 front")

        return Compiled(stubs, rows, installs=(install,), checks=(check,))


@dataclass(frozen=True)
class noble_arms_whole_card:
    def compile(self, view, cid) -> Compiled:
        assert cid == NOBLE_ARMS
        stubs = (
            (S["N1_COUNT"], _c("disguise_na.c", "N1_COUNT", "N1COUNT"), "N1 count"),
            (S["N1_FRONT"], n1_front(), "N1 stat front"),
            (S["N2_COND"], _c("disguise_na.c", "N2_COND", "N2COND"), "N2 +0C"),
            (S["N2_COST"], _c("disguise_na.c", "N2_COST", "N2COST"), "N2 +10 (OPT)"),
            (S["N2_RES"], _c("disguise_na.c", "N2_RES", "N2RES"), "N2 +04 Deck-SS wrapper"),
            (S["N2_H"], n2_handler(), "N2 criteria handler"),
            (S["N2_CB"], n2_callback(), "N2 worker callback"))
        rows = (Row(CLS3, N2_REC, N2_PHANTOM),)
        eq_b = 0xE000 | (((EQ_DEFAULT - (EQ_ARM + 4)) >> 1) & 0x7FF)

        def install(rom, view):
            assert view.u16(EQ_ARM) in (EQ_ARM_STOCK, eq_b), f"equip arm {EQ_ARM:#x} = {view.u16(EQ_ARM):#06x}"
            view.pack(EQ_ARM, "<H", eq_b)
            g = _grant_row(view)
            row = struct.unpack("<Hhh", view.blob(g, 6))
            assert row in ((NOBLE_ARMS, 500, 0), (NOBLE_ARMS, 0, 0)), f"grant row {row}"
            view.pack(g, "<Hhh", NOBLE_ARMS, 0, 0)
            _front_at(view, STAT_SITE, STAT_PREV, S["N1_FRONT"], "equip stat site")

        def check(c, rom, view):
            c.eq(view.u16(EQ_ARM), eq_b, "N0: Harpie-only arm -> b default (any monster)")
            c.eq(struct.unpack("<Hhh", view.blob(_grant_row(view), 6)), (NOBLE_ARMS, 0, 0), "N1: Cyber Shield +500 row zeroed")
            t, nxt = ov3_bl_target(view.buf, STAT_SITE), O5.dc_next()      # Gearfried's front may sit ahead of ours
            while t != S["N1_FRONT"] and t in nxt:
                t = nxt[t]
            c.eq(t, S["N1_FRONT"], "bl @0x021B7088 -> N1 front")

        return Compiled(stubs, rows, installs=(install,), checks=(check,))


DISGUISE_SPEC = card(DISGUISE, disguise_whole_card())
NOBLE_ARMS_SPEC = card(NOBLE_ARMS, noble_arms_whole_card())
DISGUISE_PROPS = card_props("LIGHT", "Warrior", level=4, atk=1400, defense=1200, card_type="Tuner Monster")

_main_d, _verify_d = dsl.make(DISGUISE_SPEC, DISGUISE_PROPS, out=OUT)
_main_n, _verify_n = dsl.make(NOBLE_ARMS_SPEC, None, out=OUT)


def main(write_text: bool = True, src: str = CHAIN, out: str = OUT) -> None:
    _main_d(write_text=write_text, src=src, out=out)
    _main_n(write_text=write_text, src=out, out=out)


def verify(out: str = OUT) -> bool:
    a = _verify_d(out)
    b = _verify_n(out)
    return a is not False and b is not False

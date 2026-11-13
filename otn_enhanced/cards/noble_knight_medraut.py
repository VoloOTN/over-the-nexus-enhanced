"""Noble Knight Medraut (0x0FD9, donor Armored Lizard), built OFF Disguise / Cursed Copycat Noble Arms.

SINGLE-CARD TEST ROM ONLY (user rule): layered on the chain ROM, which already carries disguise_copycat; NOT in
steps.STEPS / SHIPPED. Design, proofs, rulings: notes/noble-knight-medraut-findings.md.

  C1  "treated as a Normal Monster while face-up"   donor is a Normal Monster; the type is flipped to Effect only so the
                                                    ignition record can exist (DECLARED LIMIT, not a quiet deviation).
  C2  "while equipped with a Noble Arms Equip Spell: DARK, Level +1"
        Level getter 0x021B807C   BL @0x021B88BA (replaces `ldr r0,[sp,#0x24] ; adds r1,r4,r0`)  -> CAVE_MK_LVL
        attr  getter 0x021B8E48   BL @0x021B927E (replaces `ldr r0,[sp,#8] ; cmp r0,#0`)        -> CAVE_MK_ATTR
        both call CAVE_MK_ACT(side, zone) = mk_active (C): Medraut in a monster zone, present, equipped with Noble Arms.
  C3  cls3 ignition (Disguise C3 / Noble Arms N2 shapes): +08 own face-up Equip Spell, +14 Copy Plant's target step,
        +04 native Deck-SS machine 0x02206CAC wrapped (destroy the picked Equip Spell if a monster arrived),
        Deck pick = virtual criteria row 0xFF10 (fronts AHEAD of Disguise's H2/H3), Defense Position = BL @0x02206E70 front.

    uv run python _build_noble_knight_medraut.py
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS3, Compiled, Row, card, card_props
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

MEDRAUT = 0x0FD9
C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_noble_knight_medraut.nds"

# "Noble Knight" == "Infernoble Knight" here (user, infernoble.py KNIGHTS = tuple(STATS)); Medraut is not in the list.
KNIGHTS = (0x13A3, 0x139A, 0x1E04, 0x0FC1, 0x1E05, 0x0FE6, 0x0FDB, 0x0FD4, 0x160B, 0x0FEB, 0x1118, 0x17EF, 0x1002)
IDX = 0xFF10                                    # virtual criteria index: DC's namespace (0xFF00|j, j <= 1) never reaches 0x10

# --- natives (Thumb, odd) ------------------------------------------------------------------------------------
COPY_PLANT_TSEL, DECK_WORKER, H3_RESUME = 0x02234D81, 0x0223BC3D, 0x02243F71
POS_SITE, POS_STOCK_TARGET, POS_FALLTHRU = 0x02206E70, 0x02022E14, 0x02022E15
LVL_SITE, LVL_STOCK = 0x021B88BA, bytes.fromhex("09982118")      # ldr r0,[sp,#0x24] ; adds r1,r4,r0
ATTR_SITE, ATTR_STOCK = 0x021B927E, bytes.fromhex("02980028")    # ldr r0,[sp,#8] ; cmp r0,#0
H2_SITE, H3_SITE = 0x02243F24, 0x02243F62
for _v in (COPY_PLANT_TSEL, DECK_WORKER, H3_RESUME, POS_FALLTHRU):
    assert _v & 1, f"{_v:#x}: blx/bx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_MK_{n}") for n in (
    "ROWS", "FILT", "COND", "COST", "RES", "ACT", "H", "CB", "H2", "H3", "LVL", "ATTR", "POS")}
RESERVE = {"ROWS": 0x20, "FILT": 0x60, "COND": 0x110, "COST": 0x30, "RES": 0x100, "ACT": 0xC0, "H": 0x30, "CB": 0xC0, "H2": 0x30, "H3": 0x30, "LVL": 0x30, "ATTR": 0x40, "POS": 0x20}
DC_H2, DC_H3 = O5.CAVE_DC_H2, O5.CAVE_DC_H3

C3_REC = (MEDRAUT, S["RES"] | 1, S["FILT"] | 1, S["COND"] | 1, S["COST"] | 1, COPY_PLANT_TSEL)
C3_PHANTOM = 0x0E73
ROW = (MEDRAUT, 0xFFFF, S["H"] | 1, 0x00000002)                   # word: monster; the callback does the Knight test
ROWS_BLOB = struct.pack("<HHII", *ROW) + bytes(4) + bytes(0x10)    # row + scratch (+0x10 loc, +0x12 mask)


def _c(stub: str) -> bytes:
    blob = compile_c(C_DIR / "medraut.c", S[stub], {"STUB": stub, "ROWS": f"0x{S['ROWS']:08X}"})
    assert len(blob) <= RESERVE[stub], f"{stub}: {len(blob):#x} B > {RESERVE[stub]:#x}"
    return blob


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


# --- hand-written fronts (registers / frames the C ABI cannot express) ----------------------------------------
def h2_front() -> bytes:
    """criteria resolver miss tail (r5 = cid; Disguise's H2 shape): Medraut -> index 0xFF10 and pop the caller's frame,
    else BL onward to Disguise's front (the chain ends in a front that pops, so control never comes back here)."""
    b = EffectBuilder()
    b.ldr_const(0, MEDRAUT)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(DC_H2)
    return _asm(b, "H2")


def h3_front() -> bytes:
    """invoker row compute (r6 = index): 0xFF10 -> r0 = CAVE_MK_ROWS, r3 = [r0+4], resume 0x02243F70 (the same contract as
    Disguise's H3); else tail-jump to Disguise's H3 with lr intact."""
    b = EffectBuilder()
    b.ldr_const(0, IDX)
    b.insn("CMP", "R6, R0")
    b.insn("BNE", "prev")
    b.ldr_const(0, S["ROWS"])
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, DC_H3 | 1)
    b.insn("BX", "R0")
    return _asm(b, "H3")


def lvl_front() -> bytes:
    """BL over `ldr r0,[sp,#0x24] ; adds r1,r4,r0` inside the Level getter (frame: [sp]=side, [sp+4]=zone, r4 = delta):
    r1 = r4 + [sp+0x24] + (1 if Medraut is active). Only r0/r1 are written, as the stock pair did."""
    b = EffectBuilder()
    b.insn("PUSH", "{R2, LR}")
    b.insn("LDR", "R0, [SP, #0x8]")
    b.insn("LDR", "R1, [SP, #0xC]")
    b.ldr_const(3, S["ACT"] | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R1, [SP, #0x2C]")
    b.insn("ADD", "R1, R1, R0")
    b.insn("ADD", "R1, R1, R4")
    b.insn("POP", "{R2, PC}")
    return _asm(b, "LVL")


def attr_front() -> bytes:
    """BL over `ldr r0,[sp,#8] ; cmp r0,#0` inside the attribute getter (frame: [sp]=side, [sp+4]=zone, [sp+0x4C]=result):
    active -> result := 2 (DARK); then replay the pair so the following `beq` sees the stock flags."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, LR}")
    b.insn("LDR", "R0, [SP, #0x10]")
    b.insn("LDR", "R1, [SP, #0x14]")
    b.ldr_const(3, S["ACT"] | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "keep")
    b.insn("MOV", "R0, #0x2")
    b.insn("STR", "R0, [SP, #0x5C]")
    b.label("keep")
    b.insn("LDR", "R0, [SP, #0x18]")
    b.insn("CMP", "R0, #0x0")
    b.insn("POP", "{R1, R2, R3, PC}")
    return _asm(b, "ATTR")


def pos_front() -> bytes:
    """BL @0x02206E70 (Deck-SS chassis; r0 = source cid, r7 = 2 = player chooses). Medraut -> r7 := 1 (face-up Defense) and
    'not in the Attack list' (r0 = 0); every other cid -> the stock list search 0x02022E14 untouched."""
    b = EffectBuilder()
    b.ldr_const(3, MEDRAUT)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "prev")
    b.insn("MOV", "R7, #0x1")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, POS_FALLTHRU)
    b.insn("BX", "R3")
    return _asm(b, "POS")


def handler() -> bytes:
    """criteria handler (r0 = &row, r1 = side, r2 = param; Noble Arms N2's shape): Deck worker with [sp] = row word,
    [sp+4] = 2, r2 = CB, r3 = row[+0xC] (unused by our callback)."""
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
    b.ldr_const(2, S["CB"] | 1)
    b.ldr_const(4, DECK_WORKER)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return _asm(b, "H")


def callback() -> bytes:
    """worker callback ([sp] = &candidate card word): keep iff cid is a Knight and not Medraut."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.ldr_const(1, MEDRAUT)
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "no")
    for c in KNIGHTS:
        b.ldr_const(1, c)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "yes")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    return _asm(b, "CB")


def _exits(base: int, blob: bytes) -> set[int]:
    """Every BL target and every odd (Thumb) pool literal in an assembled front, even-ised."""
    from otn_enhanced.asm.thumb_disasm import decode_thumb
    out = {i.branch_target for i in decode_thumb(blob, base) if i.mnemonic == "BL"}
    out |= {w & ~1 for (w,) in struct.iter_unpack("<I", blob[:len(blob) & ~3]) if w & 1}
    return out


@dataclass(frozen=True)
class medraut_whole_card:
    def compile(self, view, cid) -> Compiled:
        assert cid == MEDRAUT
        stubs = (
            (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFF10 + scratch"),
            (S["FILT"], _c("FILT"), "C3 +08 own face-up Equip Spell"),
            (S["COND"], _c("COND"), "C3 +0C"),
            (S["COST"], _c("COST"), "C3 +10 (OPT)"),
            (S["RES"], _c("RES"), "C3 +04 Deck-SS wrapper + destroy"),
            (S["ACT"], _c("ACT"), "mk_active(side, zone)"),
            (S["H"], handler(), "criteria handler (Deck worker)"),
            (S["CB"], callback(), "worker callback (Knights)"),
            (S["H2"], h2_front(), "H2 front"),
            (S["H3"], h3_front(), "H3 front"),
            (S["LVL"], lvl_front(), "Level getter front (+1)"),
            (S["ATTR"], attr_front(), "attribute getter front (DARK)"),
            (S["POS"], pos_front(), "Deck-SS position front (Defense)"))
        rows = (Row(CLS3, C3_REC, C3_PHANTOM),)

        def _bl_over(view, site, stock, mine, what):
            cur = bytes(view.blob(site, 4))
            assert cur in (stock, common_bl(site, mine)), f"{what} @{site:#x} is {cur.hex()}, expected {stock.hex()}"
            view.write(site, common_bl(site, mine))

        def install(rom, view):
            for site, prev, mine, what in ((H2_SITE, DC_H2, S["H2"], "criteria miss tail"),
                                           (H3_SITE, DC_H3, S["H3"], "criteria row compute")):
                cur = ov3_bl_target(view.buf, site)
                assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected Disguise's {prev:#x}"
                view.write(site, common_bl(site, mine))
            _bl_over(view, LVL_SITE, LVL_STOCK, S["LVL"], "Level getter")
            _bl_over(view, ATTR_SITE, ATTR_STOCK, S["ATTR"], "attribute getter")
            cur = ov3_bl_target(view.buf, POS_SITE)
            assert cur in (POS_STOCK_TARGET, S["POS"]), f"Deck-SS list search @{POS_SITE:#x} calls {cur:#x}"
            view.write(POS_SITE, common_bl(POS_SITE, S["POS"]))

        def check(c, rom, view):
            for site, slot, prev in ((H2_SITE, "H2", DC_H2), (H3_SITE, "H3", DC_H3)):
                t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()          # Gearfried's front may sit ahead of ours
                while t != S[slot] and t in nxt:
                    t = nxt[t]
                c.eq(t, S[slot], f"bl @{site:#x} -> Medraut {slot} front")
                c.eq(O5.dc_next()[S[slot]], prev, f"dc_next {slot}: Medraut front falls through to Disguise's")
            c.ok(DC_H2 in _exits(S["H2"], h2_front()), "H2 front exits to Disguise's H2")
            c.ok(DC_H3 in {e & ~1 for e in _exits(S["H3"], h3_front())}, "H3 front exits to Disguise's H3")
            c.eq(ov3_bl_target(view.buf, LVL_SITE), S["LVL"], "Level getter site -> LVL front")
            c.eq(ov3_bl_target(view.buf, ATTR_SITE), S["ATTR"], "attribute getter site -> ATTR front")
            c.eq(ov3_bl_target(view.buf, POS_SITE), S["POS"], "Deck-SS list-search site -> POS front")
            c.eq(O5.CAVE_MK_ROWS, S["ROWS"], "row slot")

        return Compiled(stubs, rows, installs=(install,), checks=(check,))


SPEC = card(MEDRAUT, medraut_whole_card())
PROPS = card_props("LIGHT", "Warrior", level=4, atk=1700, defense=1000, card_type="Effect Monster")

_main, _verify = dsl.make(SPEC, PROPS, out=OUT)


def main(write_text: bool = True, src: str = CHAIN, out: str = OUT) -> None:
    _main(write_text=write_text, src=src, out=out)


def verify(out: str = OUT) -> bool:
    return _verify(out) is not False

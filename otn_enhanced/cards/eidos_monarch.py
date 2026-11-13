"""Eidos the Underworld Monarch (DARK / Spellcaster / Level 6 / 2400 / 1000) on Whiptail Crow 0x1230.  TEST ROM, NOT SHIPPED, nothing in-game confirmed.
E1 (N-or-SS "You can" trigger): Deck OR GY -> hand through a custom resolver over virtual row 0xFFD4 (Monarch set code 0x6D or ATK 2800 / DEF 1000; GY half added 2026-11-12).
E2 (declare an Attribute): cls3 + Genex Ally Changer's attribute rider.  E3 (2026-11-12): a front at the head of the summon dispatch posts to the GY copies on an own Tribute Summon of
a 2400+/1000 monster; virtual cls2 GY record (prefind_hook) -> menu: add to hand / Special Summon.  See notes/eidos-monarch-findings.md."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS1, CLS3, LIST_106, LIST_30, Compiled, Row, card_props
from otn_enhanced.effects import c79_trigger_hook, ov5_cave as O5, prefind_hook
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

EM = 0x1230
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_eidos_monarch.nds"
C_DIR = Path(__file__).resolve().parent / "c"

ENUM_DECK = 0x0223BC3D
ATK_GET, DEF_GET = 0x0202AC49, 0x0202AC29
IDX_DECK = 0xFFD4
WORD_MONSTER = 0x00000002
TAG_YOU_CAN = 0x021E51E5
CLS1_PHANTOM, CLS3_PHANTOM = 0x0EA7, 0x0E57
GENEX_FILTER, GENEX_SELECTOR = 0x021DB1D9, 0x02236ECD
DECK_TO_HAND = 0x02207EF5
HAS_SET_CODE = 0x020240D9
WORD_ANY_CARD = 0x0000000E
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (ENUM_DECK, ATK_GET, DEF_GET, TAG_YOU_CAN, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_EM_{n}") for n in ("COND", "COST", "COND3", "COST3", "RES3", "PRED", "DECKH", "ROWS", "H2", "H3", "GYH", "RES1", "TRIGF", "POST", "COND3G", "RES3G", "VREC3")}
RESERVE = {"COND": 0x60, "COST": 0x30, "COND3": 0x30, "COST3": 0x30, "RES3": 0x40, "PRED": 0x60, "DECKH": 0x30, "ROWS": 0x10, "H2": 0x20, "H3": 0x30, "GYH": 0x50, "RES1": 0x100, "TRIGF": 0x20, "POST": 0x80, "COND3G": 0xA0, "RES3G": 0x100, "VREC3": 0x20}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_EM_H2], _DN[O5.CAVE_EM_H3]
ROWS_BLOB = struct.pack("<HHII", EM, 0xFFFF, S["GYH"] | 1, WORD_ANY_CARD) + bytes(4)        # E1: Deck AND GY (CAVE_EM_GYH, 2026-11-12); the old Deck-only DECKH stub stays installed but unreferenced
assert len(ROWS_BLOB) == 0x10 and struct.unpack_from("<I", ROWS_BLOB, 4)[0], "a virtual row's handler is missing (blx 0 = freeze)"
CLS3_REC = (EM, S["RES3"] | 1, GENEX_FILTER, S["COND3"] | 1, S["COST3"] | 1, GENEX_SELECTOR)
CLS1_REC = (EM, 0, S["RES1"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)      # +04 was the Deck-only native 0x02207EF5 until 2026-11-12
CLS1_STOCK_OLD = (EM, 0, DECK_TO_HAND, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)
# E3 "If you Tribute Summon a monster with 2400 or more ATK and 1000 DEF, while this card is in your GY: You can add this card to your hand or Special Summon it."
TRIG_SITE, TRIG_PREV = 0x02265D2A, 0x022391CC      # summon dispatch 0x02265CF8 head: `bl 0x022391CC(event, ctx)` (r6 = event, r7 = ctx, every event)
GY_ZONE = 0x0E
DLG_HAND, DLG_SS = 603, 604                        # dlg_text labels appended by cards/erebus.py (PF_LABELS[7:9])
VREC3_BLOB = struct.pack("<HH5I", EM, 0, S["RES3G"] | 1, 0, S["COND3G"] | 1, TAG_YOU_CAN, 0).ljust(RESERVE["VREC3"], bytes(1))   # T.G. Warwolf's trigger shape: +10 = the "You can" tag


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "eidos_monarch.c", S[slot], {"STUB": stub, "PRED_ADDR": f"0x{S['PRED'] | 1:08X}", "L_HAND": str(DLG_HAND), "L_SS": str(DLG_SS)}), slot)


def trigf_stub() -> bytes:
    """Over `bl 0x022391CC` @0x02265D2A (head of the summon dispatch, r6 = event, r7 = ctx): replay it, then for event 7 (a Normal-type summon) call CAVE_EM_POST(ctx)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.bl(TRIG_PREV)
    b.insn("CMP", "R6, #0x7")
    b.insn("BNE", "out")
    b.insn("ADD", "R0, R7, #0x0")
    b.ldr_const(3, S["POST"] | 1)
    b.insn("BLX", "R3")
    b.label("out")
    b.insn("POP", "{R4, PC}")
    return _fit(b.assemble(S["TRIGF"], pad="nop"), "TRIGF")


def pred_stub() -> bytes:
    """Deck predicate (the enumerator's stack arg [sp] -> the card word pointer): a "Monarch" card (set code 0x6D) or ATK 2800 and DEF 1000."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("MOV", "R1, #0x6D")
    b.ldr_const(3, HAS_SET_CODE)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "yes")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, DEF_GET)
    b.insn("BLX", "R3")
    b.insn("MOV", "R1, #0xFA")
    b.insn("LSL", "R1, R1, #0x2")                          # 1000
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "no")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, ATK_GET)
    b.insn("BLX", "R3")
    b.ldr_const(1, 2800)
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "no")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    return _fit(b.assemble(S["PRED"], pad="nop"), "PRED")


def deckh_stub() -> bytes:
    """Deck row handler (row r0, side r1): 0x0223CAB4's body (Deck Special Summon, type 0xA) with the custom predicate."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0x2")
    b.insn("MOV", "R2, #0x0")
    b.insn("STR", "R2, [SP, #0x8]")
    b.insn("LDR", "R2, [R3, #0x8]")
    b.insn("STR", "R2, [SP, #0x0]")
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R3, #0x0]")
    b.ldr_const(2, S["PRED"] | 1)
    b.insn("ADD", "R3, SP, #0x8")
    b.ldr_const(4, ENUM_DECK)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return _fit(b.assemble(S["DECKH"], pad="nop"), "DECKH")


def h2_front() -> bytes:
    """criteria miss tail (r5 = cid): 0x1123 -> the Deck row; pop the caller's frame.  Others: BL onward."""
    b = EffectBuilder()
    b.ldr_const(0, EM)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX_DECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX_DECK)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x1")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _fit(b.assemble(S["H3"], pad="nop"), "H3")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class eidos_the_underworld_monarch:
    cid: int = EM

    def blobs(self):
        return {"COND": (S["COND"], _c("EM_COND", "COND"), "cls1 +0C cond (C)"),
                "COST": (S["COST"], _c("EM_COST", "COST"), "cls1 +14 cost (C)"),
                "COND3": (S["COND3"], _c("EM_COND3", "COND3"), "E2 cls3 +0C cond (C)"),
                "COST3": (S["COST3"], _c("EM_COST3", "COST3"), "E2 cls3 +10 cost (C)"),
                "RES3": (S["RES3"], _c("EM_RES3", "RES3"), "E2 cls3 +04 resolver (C)"),
                "PRED": (S["PRED"], pred_stub(), "Deck predicate"), "DECKH": (S["DECKH"], deckh_stub(), "Deck row handler"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFFD4"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "GYH": (S["GYH"], _c("EM_GYH", "GYH"), "E1 row handler: Deck + GY (C)"),
                "RES1": (S["RES1"], _c("EM_RES1", "RES1"), "E1 cls1 +04 resolver: Deck or GY -> hand (C)"),
                "TRIGF": (S["TRIGF"], trigf_stub(), "summon-dispatch front: event 7 -> E3 poster"),
                "POST": (S["POST"], _c("EM_POST", "POST"), "E3 poster: own Tribute Summon of a 2400+/1000 monster -> GY post (C)"),
                "COND3G": (S["COND3G"], _c("EM_COND3G", "COND3G"), "E3 virtual cls2 GY +0C cond (C)"),
                "RES3G": (S["RES3G"], _c("EM_RES3G", "RES3G"), "E3 virtual cls2 +04 resolver (C)"),
                "VREC3": (S["VREC3"], VREC3_BLOB, "E3 virtual cls2 GY record (data)")}

    def compile(self, view=None) -> Compiled:
        c79_trigger_hook.register_extra(EM, "Whiptail Crow -> Eidos the Underworld Monarch (Monarch set test ROM, not shipped)")
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "VREC3"):
                assert_thumb1_only(blob, addr)
        prefind_hook.register(EM, S["VREC3"], "Eidos the Underworld Monarch E3 GY trigger", cls=2, zone=GY_ZONE, any_sub=True)
        group = TN.GROUPS[0]

        def install(rom, v):
            for lst in (LIST_30, LIST_106):
                assert EM not in v.keys(lst.base, count=lst.count, stride=2), f"donor is in {lst.label}"
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            group.install(rom, v)
            from otn_enhanced.effects.common import find as _find
            i1 = _find(v, CLS1, EM)
            if i1 is not None and tuple(v.unpack(CLS1.addr(i1), CLS1.fmt)) == CLS1_STOCK_OLD:
                v.pack(CLS1.addr(i1), CLS1.fmt, *CLS1_REC)           # an older Eidos build already inserted the Deck-only record: repoint its +04 in place
            _front_at(v, TRIG_SITE, TRIG_PREV, S["TRIGF"], "summon-dispatch head bl 0x022391CC")
            prefind_hook.install(rom, v)
            c79_trigger_hook.install(rom)
            c79_trigger_hook.apply(v.buf)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Eidos Monarch {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            c79_trigger_hook.verify(v.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            group.check(c, rom, v)
            from otn_enhanced.effects.common import rows as _rows
            c.ok([r for r in _rows(v, CLS1) if r[0] == EM] == [CLS1_REC], "cls1 record under 0x1230 -> the Deck-or-GY resolver")
            c.eq(ov3_bl_target(v.buf, TRIG_SITE), S["TRIGF"], "summon-dispatch head BL @0x02265D2A -> Eidos E3 front")
            prefind_hook.verify(rom, v, lambda ok, msg: c.ok(bool(ok), msg))

        return Compiled(tuple(blobs.values()), rows=(Row(CLS1, CLS1_REC, CLS1_PHANTOM), Row(CLS3, CLS3_REC, CLS3_PHANTOM)), installs=(install,), checks=(check,))


SPEC = eidos_the_underworld_monarch()
PROPS = card_props("DARK", "Spellcaster", level=6, atk=2400, defense=1000, card_type="Effect Monster")
main, verify = dsl.make(SPEC, PROPS, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

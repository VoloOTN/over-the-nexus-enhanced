"""Eidos the Underworld Squire (DARK / Spellcaster / Level 2 / 800 / 1000) on Great White 0x0FE2.  Single-card / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "If this card is Normal or Special Summoned: During your Main Phase this turn, you can Tribute Summon 1 monster, in addition to your Normal Summon/Set.  (You can only gain this
     effect once per turn.)  You can banish this card from your Graveyard, then target 1 monster with 800 ATK and 1000 DEF in your Graveyard, except "Eidos the Underworld Squire";
     Special Summon it in Defense Position, also you cannot Special Summon monsters from the Extra Deck for the rest of this turn.  You can only use this effect of "Eidos the
     Underworld Squire" once per turn."

Clauses  E1 N-or-SS trigger: gain one extra Tribute Summon this turn (once per turn).  E2 (GY) banish this card, target an 800/1000 monster in the GY (not Eidos), Special Summon it in
         Defense Position.  E3 Extra Deck Special Summon lock for the rest of the turn.  E4 E2 once per turn.
Design   * E1: cls1 {RES, 0, COND, 0, 0} over cls1 phantom 0x0E8F (Windrose's mandatory-trigger shape) on the shared N-or-SS hook (a 7th arm: c79_trigger_hook.where() moves the stub to a 0x80 slot).
           RES posts the kind-1 node of Double Summon (0x1C33), the engine's granter-free "Normal Summon 1 monster in addition" (ns_counter 0x021B9514 reads it).
           KNOWN DEVIATION (a bug until the user says otherwise): the grant is not restricted to Tribute Summons and is not "immediate".
         * E2: cls2 {PB-family resolver 0x02207529 via RES2, 0, COND2, COST2 (native self-banish), 0x02235605} over cls2 phantom 0x0E12 + the 20th virtual GY-action row
           (gy_vrow_hook MONARCH_ARMS).  The target row = virtual criteria row 0xFFD2 (GY Special Summon enumerator 0x0223C4E8 with a custom ATK 800 / DEF 1000 / not-Eidos predicate).
           Defense Position: a front on `bl 0x02204730` @0x022075D2 (r2 = 1), chained behind Restoration's in the combined ROM.  E3: Revolt's Extra Deck lock key 0x5DCD.
         * ATK / DEF tests use the PRINTED values (cid getters): a KNOWN GAP versus current values.

    uv run python -m otn_enhanced.cards.eidos_squire
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS1, CLS2, LIST_106, LIST_30, Compiled, Row, card_props
from otn_enhanced.effects import c79_trigger_hook, gy_vrow_hook as gyv, ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

ES = 0x0FE2
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_eidos_squire.nds"
C_DIR = Path(__file__).resolve().parent / "c"

ENUM_GY = 0x0223C4E9                                   # GY walker wrapper, Thumb entry
ATK_GET, DEF_GET = 0x0202AC49, 0x0202AC29
IDX_GY = 0xFFD2
WORD_PB = 0x00010002                                   # Premature Burial's own row word (monster, GY)
PB_RESOLVER, PB_SELECTOR = 0x02207529, 0x02235605
CLS1_PHANTOM, CLS2_PHANTOM = 0x0E8F, 0x0E12
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
POS_SITE, POS_NATIVE = 0x022075D2, 0x02204730
for _v in (ENUM_GY, ATK_GET, DEF_GET, PB_RESOLVER, PB_SELECTOR, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_ES_{n}") for n in ("COND", "RES", "COND2", "COST2", "RES2", "PRED", "GYH", "ROWS", "H2", "H3", "POS")}
RESERVE = {"COND": 0x30, "RES": 0x30, "COND2": 0x40, "COST2": 0x30, "RES2": 0x30, "PRED": 0x40, "GYH": 0x30, "ROWS": 0x10, "H2": 0x20, "H3": 0x30, "POS": 0x20}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_ES_H2], _DN[O5.CAVE_ES_H3]
POS_PREV = O5.CAVE_RS_POS if O5.combo() else POS_NATIVE        # Restoration's front sits at the same site in the combined ROM
ROWS_BLOB = struct.pack("<HHII", ES, 0xFFFF, S["GYH"] | 1, WORD_PB) + bytes(4)
assert len(ROWS_BLOB) == 0x10 and struct.unpack_from("<I", ROWS_BLOB, 4)[0], "a virtual row's handler is missing (blx 0 = freeze)"
CLS1_REC = (ES, 0, S["RES"] | 1, 0, S["COND"] | 1, 0, 0)
CLS2_REC = (ES, 0, S["RES2"] | 1, 0, S["COND2"] | 1, S["COST2"] | 1, PB_SELECTOR)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "eidos_squire.c", S[slot], {"STUB": stub}), slot)


def pred_stub() -> bytes:
    """GY predicate (the enumerator's stack arg [sp] -> the card word pointer): DEF 1000 and ATK 800 and cid != Eidos the Underworld Squire."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(1, ES)
    b.insn("CMP", "R4, R1")
    b.insn("BEQ", "no")
    b.ldr_const(3, DEF_GET)
    b.insn("BLX", "R3")
    b.insn("MOV", "R1, #0xFA")
    b.insn("LSL", "R1, R1, #0x2")                          # 1000
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "no")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, ATK_GET)
    b.insn("BLX", "R3")
    b.insn("MOV", "R1, #0x32")
    b.insn("LSL", "R1, R1, #0x4")                          # 800
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "no")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    return _fit(b.assemble(S["PRED"], pad="nop"), "PRED")


def gyh_stub() -> bytes:
    """GY row handler (row r0, side r1): 0x0223C9D0's body (GY Special Summon, type 8) with the custom predicate and a zero key list."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0x8")
    b.insn("MOV", "R2, #0x0")
    b.insn("STR", "R2, [SP, #0x8]")
    b.insn("LDR", "R2, [R3, #0x8]")
    b.insn("STR", "R2, [SP, #0x0]")
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R3, #0x0]")
    b.ldr_const(2, S["PRED"] | 1)
    b.insn("ADD", "R3, SP, #0x8")
    b.ldr_const(4, ENUM_GY)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return _fit(b.assemble(S["GYH"], pad="nop"), "GYH")


def h2_front() -> bytes:
    """criteria miss tail (r5 = cid): 0x0FE2 -> the GY row; pop the caller's frame.  Others: BL onward."""
    b = EffectBuilder()
    b.ldr_const(0, ES)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX_GY)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX_GY)
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


def pos_front() -> bytes:
    """Replaces `bl 0x02204730` (r0 = desc, r1 = 1, r2 = position) in the PB resolver: Eidos -> Defense (1).  Tail-calls the previous owner so LR still returns into the resolver."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0}")
    b.insn("LDRH", "R0, [R0, #0x0]")
    b.ldr_const(3, ES)
    b.insn("CMP", "R0, R3")
    b.insn("POP", "{R0}")
    b.insn("BNE", "go")
    b.insn("MOV", "R2, #0x1")
    b.label("go")
    b.ldr_const(3, POS_PREV | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["POS"], pad="nop"), "POS")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class eidos_the_underworld_squire:
    cid: int = ES

    def blobs(self):
        return {"COND": (S["COND"], _c("ES_COND", "COND"), "cls1 +0C cond (C)"),
                "RES": (S["RES"], _c("ES_RES", "RES"), "cls1 +04 resolver (C)"),
                "COND2": (S["COND2"], _c("ES_COND2", "COND2"), "cls2 +0C cond (C)"),
                "COST2": (S["COST2"], _c("ES_COST2", "COST2"), "cls2 +10 cost (C)"),
                "RES2": (S["RES2"], _c("ES_RES2", "RES2"), "cls2 +04 resolver (C)"),
                "PRED": (S["PRED"], pred_stub(), "GY predicate"), "GYH": (S["GYH"], gyh_stub(), "GY row handler"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFFD2"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "POS": (S["POS"], pos_front(), "Defense Position front")}

    def compile(self, view=None) -> Compiled:
        c79_trigger_hook.register_extra(ES, "Great White -> Eidos the Underworld Squire (Monarch set test ROM, not shipped)")
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS",):
                assert_thumb1_only(blob, addr)

        def install(rom, v):
            first = struct.unpack("<H", bytes(v.blob(ENUM_GY & ~1, 2)))[0]
            assert (first >> 8) in (0xB4, 0xB5), f"GY enumerator {ENUM_GY:#x} does not start with a push ({first:#06x}): a wrong function address (blx into garbage = freeze)"
            for lst in (LIST_30, LIST_106):
                assert ES not in v.keys(lst.base, count=lst.count, stride=2), f"donor is in {lst.label}"
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            _front_at(v, POS_SITE, POS_PREV, S["POS"], "PB resolver position call")
            gyv.install(rom, v.buf, arms=gyv.ARMS + gyv.MONARCH_ARMS, layout=gyv.GYV2)
            c79_trigger_hook.install(rom)
            c79_trigger_hook.apply(v.buf)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Eidos {slot} front")
            c.eq(ov3_bl_target(v.buf, POS_SITE), S["POS"], "PB resolver position call -> the Eidos POS front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            c.ok(struct.unpack_from("<I", O5.read_cave(rom, S["ROWS"], 0x10), 4)[0] != 0, "the virtual row has a handler")
            for lst in (LIST_30, LIST_106):
                c.ok(ES not in v.keys(lst.base, count=lst.count, stride=2), f"donor in NEITHER {lst.label} -- so the leave-mask lookup is reached")
            c79_trigger_hook.verify(v.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            c.ok(struct.pack("<H", ES) in O5.read_cave(rom, gyv.GYV2["ROWS"][0], gyv.GYV2["ROWS"][1]), "the virtual GY-action table (GYV2) names Eidos")

        return Compiled(tuple(blobs.values()), rows=(Row(CLS1, CLS1_REC, CLS1_PHANTOM), Row(CLS2, CLS2_REC, CLS2_PHANTOM)), installs=(install,), checks=(check,))


SPEC = eidos_the_underworld_squire()
PROPS = card_props("DARK", "Spellcaster", level=2, atk=800, defense=1000, card_type="Effect Monster")
main, verify = dsl.make(SPEC, PROPS, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

"""Tessera the Primal Squire (LIGHT / Warrior / Level 1 / 800 / 1000) on Toon Alligator 0x1123.  Single-card / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "You can reveal 1 "Monarch" Spell/Trap in your hand; Special Summon this card from your hand.  During your Main Phase, you can: Immediately after this effect resolves, Tribute
     Summon 1 monster.  If this card is sent to the GY: You can Special Summon 1 monster with 800 ATK/1000 DEF from your Deck, also you cannot Special Summon from the Extra Deck for
     the rest of this turn.  You can only use each effect of "Tessera the Primal Squire" once per turn."

Clauses  T1 hand ignition: reveal a Monarch Spell/Trap, Special Summon this card from the hand.  T2 Main Phase ignition: Tribute Summon 1 monster immediately after it resolves.
         T3 sent to the GY: "You can" Special Summon an 800/1000 monster from the Deck + Extra Deck lock for the turn.  T4 each effect once per turn.
STATUS   T1 IS NOT BUILT (a hand-ignition effect needs Immortal Phoenix Gearfried's machinery: a virtual cls2 hand record via a find_event_handler front + the ARM9 hand-offer front +
         a reveal cost over a hand row; the cls2 table also allows ONE record per cid and T3 owns it).  T2 and T3 are built.  See notes/tessera-findings.md.
Design   * T2: cls3 {RES3, 0, COND3, COST3, 0} over cls3 phantom 0x0E20 (Mystic Piper's vanilla ignition shape).  RES3 posts the kind-1 node of Double Summon (0x1C33), the engine's
           granter-free "Normal Summon 1 monster in addition".  KNOWN DEVIATION (a bug until the user says otherwise): the extra summon is not restricted to Tribute Summons and
           is not "immediate"; the ignition is assumed to be a FIELD effect (the printed text does not say where it is activated from).
         * T3: cls2 {RES, 0, COND, native "You can" 0x021E51E5, 0} over cls2 phantom 0x0EC9 + a leave-mask row {0x1123, 0x0800} over leave phantom 0x0E4B (Gravekeeper's Recruiter's
           recipe).  RES stamps the node and the Extra Deck lock (Revolt's key 0x5DCD) then runs the native Deck-SS machine (0x02206CAD, position = the player's choice) over virtual
           criteria row 0xFFD3 (Deck-SS enumerator + a custom ATK 800 / DEF 1000 predicate).  ATK / DEF tests use PRINTED values: a KNOWN GAP versus current values.

    uv run python -m otn_enhanced.cards.tessera
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS2, CLS3, LEAVE_MASK, LIST_106, LIST_30, Compiled, Row, card_props
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

TS = 0x1123
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_tessera.nds"
C_DIR = Path(__file__).resolve().parent / "c"

ENUM_DECK = 0x0223BC3D
ATK_GET, DEF_GET = 0x0202AC49, 0x0202AC29
IDX_DECK = 0xFFD3
WORD_MONSTER = 0x00000002
TAG_YOU_CAN = 0x021E51E5
CLS3_PHANTOM, CLS2_PHANTOM, LEAVE_PHANTOM = 0x0E20, 0x0EC9, 0x0E4B
MASK_SENT_TO_GY = 0x0800
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (ENUM_DECK, ATK_GET, DEF_GET, TAG_YOU_CAN, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_TS_{n}") for n in ("COND3", "COST3", "RES3", "COND", "RES", "PRED", "DECKH", "ROWS", "H2", "H3")}
RESERVE = {"COND3": 0x30, "COST3": 0x30, "RES3": 0x30, "COND": 0x70, "RES": 0x40, "PRED": 0x40, "DECKH": 0x30, "ROWS": 0x10, "H2": 0x20, "H3": 0x30}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_TS_H2], _DN[O5.CAVE_TS_H3]
ROWS_BLOB = struct.pack("<HHII", TS, 0xFFFF, S["DECKH"] | 1, WORD_MONSTER) + bytes(4)
assert len(ROWS_BLOB) == 0x10 and struct.unpack_from("<I", ROWS_BLOB, 4)[0], "a virtual row's handler is missing (blx 0 = freeze)"
CLS3_REC = (TS, S["RES3"] | 1, 0, S["COND3"] | 1, S["COST3"] | 1, 0)
CLS2_REC = (TS, 0, S["RES"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, 0)
LEAVE_REC = (TS, MASK_SENT_TO_GY)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "tessera.c", S[slot], {"STUB": stub}), slot)


def pred_stub() -> bytes:
    """Deck predicate (the enumerator's stack arg [sp] -> the card word pointer): DEF 1000 and ATK 800."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0x0")
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


def deckh_stub() -> bytes:
    """Deck row handler (row r0, side r1): 0x0223CAB4's body (Deck Special Summon, type 0xA) with the custom predicate."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0xA")
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
    b.ldr_const(0, TS)
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


class tessera_the_primal_squire:
    cid: int = TS

    def blobs(self):
        return {"COND3": (S["COND3"], _c("TS_COND3", "COND3"), "cls3 +0C cond (C)"),
                "COST3": (S["COST3"], _c("TS_COST3", "COST3"), "cls3 +10 cost (C)"),
                "RES3": (S["RES3"], _c("TS_RES3", "RES3"), "cls3 +04 resolver (C)"),
                "COND": (S["COND"], _c("TS_COND", "COND"), "cls2 +0C cond (C)"),
                "RES": (S["RES"], _c("TS_RES", "RES"), "cls2 +04 resolver (C)"),
                "PRED": (S["PRED"], pred_stub(), "Deck predicate"), "DECKH": (S["DECKH"], deckh_stub(), "Deck row handler"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFFD3"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key != "ROWS":
                assert_thumb1_only(blob, addr)

        def install(rom, v):
            first = struct.unpack("<H", bytes(v.blob(ENUM_DECK & ~1, 2)))[0]
            assert (first >> 8) in (0xB4, 0xB5), f"Deck enumerator {ENUM_DECK:#x} does not start with a push ({first:#06x}): a wrong function address (blx into garbage = freeze)"
            for lst in (LIST_30, LIST_106):
                assert TS not in v.keys(lst.base, count=lst.count, stride=2), f"donor is in {lst.label}"
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Tessera {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            c.ok(struct.unpack_from("<I", O5.read_cave(rom, S["ROWS"], 0x10), 4)[0] != 0, "the virtual row has a handler")
            for lst in (LIST_30, LIST_106):
                c.ok(TS not in v.keys(lst.base, count=lst.count, stride=2), f"donor in NEITHER {lst.label} -- so the leave-mask lookup is reached")

        return Compiled(tuple(blobs.values()), rows=(Row(CLS3, CLS3_REC, CLS3_PHANTOM), Row(CLS2, CLS2_REC, CLS2_PHANTOM), Row(LEAVE_MASK, LEAVE_REC, LEAVE_PHANTOM)),
                        installs=(install,), checks=(check,))


SPEC = tessera_the_primal_squire()
PROPS = card_props("LIGHT", "Warrior", level=1, atk=800, defense=1000, card_type="Effect Monster")
main, verify = dsl.make(SPEC, PROPS, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

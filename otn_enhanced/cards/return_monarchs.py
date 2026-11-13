"""Return of the Monarchs (Continuous Spell) on Vengeful Bog Spirit 0x14A1.  Single-card TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "You cannot Special Summon monsters from the Extra Deck.  When you Tribute Summon a monster: You can activate 1 of these effects;
     * Add, from your Deck to your hand, 1 monster with 2400 ATK and 1000 DEF with a different name from that Tribute Summoned monster.
     * Add, from your Deck to your hand, 1 monster with 2800 ATK and 1000 DEF with a different name from that Tribute Summoned monster.
     The Tribute Summoned monster must be face-up on the field to activate and to resolve this effect.  You can only use this effect of
     "Return of the Monarchs" once per turn."

Clauses  C1 Extra Deck Special Summon lock (edlock.c: a face-up Return, shared with March).  C2 trigger on a Tribute Summon of ANY monster.
         C3 add a 2400/1000 or 2800/1000 monster with a different name.  C4 summoned monster face-up at activation and resolution.  C5 once per turn.
Design   (notes/monarch-megas-findings.md Session 23)
  * The donor owns no cls row; its one code reference (ov3 literal @0x021A4988, 'monsters cannot attack the turn they are Summoned') is repointed
    to a dead phantom (March's Kishido recipe).  cls0 activation row (tiny stubs) + cls1 row (Darlingtonia / Ophrys shape) over free phantoms.
  * TRIGGER (UNPROVEN, the measured risk): the summon-event dispatcher 0x02265768 only posts an event for the SUMMONED card's cid.  A BL hook over
    `cmp r5,#0 ; beq` @0x02265C70 answers 'hit' for a Tribute Summon when the summoner has a face-up Return and has not used the node, recording
    (side, zone, cid); a front over `bl 0x021D3168` @0x02265CA8 then swaps the event's cid for Return's, so Return's cls1 record answers.
    A native trigger wins when both apply (a Monarch's own Tribute trigger suppresses Return's on that summon): a known gap.
  * C3 with no prompt: 'activate 1 of these effects' = add a monster that is 2400/1000 OR 2800/1000 and not the summoned monster's name; one Deck picker
    shows both.  Deck row = virtual row 0xFF70 {0x14A1, 0xFFFF, handler, monster}; the handler is 0x0223CAF4 with a custom predicate (stat getters,
    same-name test).  H2/H3 fronts sit AHEAD of Block Dragon's.

    uv run python _build_return_monarchs.py
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import march as M
from otn_enhanced.dsl import CLS0, CLS1, Compiled, Row
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

RET = 0x14A1
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_return_monarchs.nds"
C_DIR = Path(__file__).resolve().parent / "c"

CLS0_PHANTOM, CLS1_PHANTOM = 0x0E2A, 0x130F
BOG_LIT, BOG_PHANTOM = 0x021A4988, 0x261B           # ov3 pool literal = 0x14A1 (the donor's attack gate); 0x261B is no card and in no ov3 literal
TAG_YOU_CAN = 0x021E51E5
HAND_ODD, PRED_ODD = None, None
SAME_NAME, ATK_GET, DEF_GET, ENUM_DECK = 0x02022E99, 0x0202AC49, 0x0202AC29, 0x0223BC3D
H3_RESUME = 0x02243F71
IDX = 0xFF70
WORD_MONSTER = 0x00000002
H2_SITE, H3_SITE = 0x02243F24, 0x02243F62
TRIG_SITE, POST_SITE = 0x02265C70, 0x02265CA8
TRIG_STOCK = bytes.fromhex("002d2dd0")                # cmp r5,#0 ; beq 0x02265CD0
POST_NATIVE = 0x021D3168

S = {n: getattr(O5, f"CAVE_RT_{n}") for n in ("TINY", "COND", "COST", "RES", "TEST", "TRIG", "POST", "PRED", "HAND", "ROWS", "DATA", "H2", "H3")}
RESERVE = {"TINY": 0x10, "COND": 0x80, "COST": 0x30, "RES": 0x80, "TEST": 0x90, "TRIG": 0x40, "POST": 0x30, "PRED": 0x60, "HAND": 0x30,
           "ROWS": 0x10, "DATA": 0x20, "H2": 0x40, "H3": 0x30}
for _v in (TAG_YOU_CAN, SAME_NAME, ATK_GET, DEF_GET, ENUM_DECK, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_RT_H2], _DN[O5.CAVE_RT_H3]
ROWS_BLOB = struct.pack("<HHII", RET, 0xFFFF, S["HAND"] | 1, WORD_MONSTER) + bytes(4)
CLS0_REC = (RET, S["TINY"] + 8 | 1, 0, S["TINY"] | 1, S["TINY"] + 4 | 1, 0)
CLS1_REC = (RET, 0, S["RES"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _asm(b: EffectBuilder, slot: str) -> bytes:
    return _fit(b.assemble(S[slot], pad="nop"), slot)


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "return_monarchs.c", S[slot], {"STUB": stub, "DATA": f"0x{S['DATA']:08X}"}), slot)


def pred_stub() -> bytes:
    """Deck-search predicate, entered by the enumerator with its stack arguments at [sp] (-> card word pointer) and [sp+4]:
    DEF == 1000, ATK in {2400, 2800}, and not the same name as the Tribute Summoned monster (DATA+0xC)."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, DEF_GET)
    b.insn("BLX", "R3")
    b.insn("MOV", "R1, #0xFA")
    b.insn("LSL", "R1, R1, #0x2")
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "no")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, ATK_GET)
    b.insn("BLX", "R3")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("MOV", "R1, #0x96")
    b.insn("LSL", "R1, R1, #0x4")
    b.insn("CMP", "R5, R1")
    b.insn("BEQ", "atk")
    b.insn("MOV", "R1, #0xAF")
    b.insn("LSL", "R1, R1, #0x4")
    b.insn("CMP", "R5, R1")
    b.insn("BNE", "no")
    b.label("atk")
    b.ldr_const(1, S["DATA"] + 0xC)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, SAME_NAME)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "no")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    return _asm(b, "PRED")


def hand_stub() -> bytes:
    """Row handler (row r0, side r1): 0x0223CAF4's body with the custom predicate and no set-code list element."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0x2")
    b.insn("MOV", "R2, #0x0")                      # the predicate ignores the list element (0x0223CAF4 passes the row's aux here)
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
    return _asm(b, "HAND")


def h2_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, RET)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _asm(b, "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX)
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
    return _asm(b, "H3")


def trig_blob() -> bytes:
    return _fit(compile_c(C_DIR / "return_trig.S", S["TRIG"], {"TEST": f"0x{S['TEST'] | 1:08X}"}), "TRIG")


def post_blob() -> bytes:
    return _fit(compile_c(C_DIR / "return_post.S", S["POST"], {"DATA": f"0x{S['DATA']:08X}", "RETURN": f"0x{RET:X}"}), "POST")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


@dataclass(frozen=True)
class return_of_the_monarchs:
    cid: int = RET

    def blobs(self):
        return {"TINY": (S["TINY"], M.tiny_stubs(S["TINY"]), "cls0 cond / cost / res"),
                "COND": (S["COND"], _c("R_COND", "COND"), "cls1 +0C cond (C)"),
                "COST": (S["COST"], _c("R_COST", "COST"), "cls1 +14 cost (C)"),
                "RES": (S["RES"], _c("R_RES", "RES"), "cls1 +04 resolver (C)"),
                "TEST": (S["TEST"], _c("R_TEST", "TEST"), "trigger test leaf (C)"),
                "TRIG": (S["TRIG"], trig_blob(), "BL hook over the dispatcher verdict"),
                "POST": (S["POST"], post_blob(), "event-post front (cid swap)"),
                "PRED": (S["PRED"], pred_stub(), "Deck-search predicate"),
                "HAND": (S["HAND"], hand_stub(), "virtual row handler"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFF70"),
                "DATA": (S["DATA"], bytes(0x20), "DATA: swap flag, side, zone, summoned cid (ships clear)"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "LOCK": (O5.CAVE_MA_LOCK, compile_c(C_DIR / "edlock.c", O5.CAVE_MA_LOCK), "ED_LOCK(side) (C; face-up March or Return)"),
                "HS": (O5.CAVE_MA_HS, M.hs_stub(O5.CAVE_MA_HS, O5.CAVE_MA_LOCK, 4, M.IS_SYNCHRO), "Synchro legality front"),
                "HF": (O5.CAVE_MA_HF, M.hs_stub(O5.CAVE_MA_HF, O5.CAVE_MA_LOCK, 7, M.IS_FUSION), "Fusion legality front"),
                "HE": (O5.CAVE_MA_HE, M.he_stub(O5.CAVE_MA_HE, O5.CAVE_MA_LOCK), "SS engine Extra Deck backstop")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        res = dict(RESERVE, **{k: M.RESERVES[k] for k in ("LOCK", "HS", "HF", "HE")})
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= res[key], f"{key}: {len(blob):#x} B > {res[key]:#x}"
            if key not in ("DATA", "ROWS"):
                assert_thumb1_only(blob, addr)
        lock_sites = ((M.HS_SITE, M.IS_SYNCHRO, O5.CAVE_MA_HS, "can_synchro_summon is_synchro test"),
                      (M.HF_SITE, M.IS_FUSION, O5.CAVE_MA_HF, "can_fusion_summon is_fusion test"),
                      (M.HE_SITE, M.FREE_ZONE, O5.CAVE_MA_HE, "SS engine free-zone check"))

        def install(rom, v):
            assert v.u32(BOG_LIT) in (RET, BOG_PHANTOM), f"Vengeful Bog Spirit literal @{BOG_LIT:#x} = {v.u32(BOG_LIT):#x}"
            v.pack(BOG_LIT, "<I", BOG_PHANTOM)
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            cur = bytes(v.blob(TRIG_SITE, 4))
            assert cur in (TRIG_STOCK, common_bl(TRIG_SITE, S["TRIG"])), f"dispatcher verdict site {TRIG_SITE:#x} = {cur.hex()}"
            v.write(TRIG_SITE, common_bl(TRIG_SITE, S["TRIG"]))
            _front_at(v, POST_SITE, POST_NATIVE, S["POST"], "summon-event post")
            for site, prev, mine, what in lock_sites:
                cur2 = ov3_bl_target(v.buf, site)
                assert cur2 in (prev, mine), f"{what} @{site:#x} calls {cur2:#x}, expected {prev:#x} (native) or ours"
                v.write(site, common_bl(site, mine))

        def check(c, rom, v):
            c.eq(v.u32(BOG_LIT), BOG_PHANTOM, "Vengeful Bog Spirit's attack-gate literal -> phantom")
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Return {slot} front")
            c.eq(bytes(v.blob(TRIG_SITE, 4)), common_bl(TRIG_SITE, S["TRIG"]), "dispatcher verdict site -> TRIG stub")
            c.eq(ov3_bl_target(v.buf, POST_SITE), S["POST"], "summon-event post -> POST front")
            for site, prev, mine, what in lock_sites:
                c.ok(code_reaches(rom, site, mine), f"{what} @{site:#x} reaches the lock front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), (Row(CLS0, CLS0_REC, CLS0_PHANTOM), Row(CLS1, CLS1_REC, CLS1_PHANTOM)),
                        installs=(install,), checks=(check,))


SPEC = return_of_the_monarchs()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

"""Edea the Heavenly Squire (LIGHT / Warrior / Level 1 / 800 / 1000) on Gokibore 0x0FDC.  Single-card / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "If this card is Normal or Special Summoned: You can Special Summon 1 monster with 800 ATK and 1000 DEF from your Deck in Defense Position, except "Edea the Heavenly
     Squire", also you cannot Special Summon monsters from the Extra Deck for the rest of this turn.  If this card is sent to the Graveyard: You can target 1 of your banished
     "Monarch" Spell/Trap Cards; add it to your hand.  You can only use each effect of "Edea the Heavenly Squire" once per turn."

Clauses  C1 trigger (Normal or Special Summon), "You can".  C2 Special Summon 1 800/1000 monster from the Deck in Defense Position, not Edea.  C3 Extra Deck Special Summon lock
         for the rest of the turn.  C4 trigger (sent to the GY), "You can", target 1 banished "Monarch" Spell/Trap; add it to the hand.  C5 each effect once per turn.
Design   * C1: cls1 {RES, 0, COND, native "You can" 0x021E51E5, COST} over cls1 phantom 0x0E8A (Predaplant Ophrys's shape); the trigger rides the SHARED N-or-SS hook
           (c79_trigger_hook, 6th arm; MONARCH_COMBO re-homes nothing, the 0x50 slot is exactly full).  RES replays the native Deck Special Summon machine's default arm
           (0x02206CAC) with the Defense Position argument, then posts the Extra Deck lock node (Revolt's key 0x5DCD, already tested by edlock.c).
         * C4: cls2 {add-target resolver 0x02208181 via RES2, 0, COND2, "You can", off-field picker 0x02235605 via SEL2} over cls2 phantom 0x0E64 (Laval Lancelord's shape) +
           a leave-MASK row {0x0FDC, 0x0800 (sent to the GY)} over leave phantom 0x0E2D (Gravekeeper's Recruiter's recipe; field-origin only).
         * Two virtual criteria rows under the one cid: 0xFFD0 Deck (Deck-SS enumerator + a custom ATK 800 / DEF 1000 / not-Edea predicate), 0xFFD1 banished set-code 0x6D
           Spell|Trap (the 0x0223FBA0 thunk with add-to-hand type 8).  H2 chooses by DATA mode (every C1 entry clears it, every C2 entry sets it).
         * ATK / DEF tests use the PRINTED values (cid getters): a KNOWN GAP versus current values.

    uv run python -m otn_enhanced.cards.edea
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS1, CLS2, LEAVE_MASK, LIST_106, LIST_30, Compiled, Row, card_props
from otn_enhanced.effects import c79_trigger_hook, ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

ED = 0x0FDC
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_edea.nds"
C_DIR = Path(__file__).resolve().parent / "c"

ENUM_DECK, ENUM_BAN = 0x0223BC3D, 0x0223C6AD          # Deck enumerator / off-field (banished) picker, Thumb entries
SETCODE_PRED = 0x0223C825                              # has_set_code callback of the native set-code thunks (key = row aux)
ATK_GET, DEF_GET = 0x0202AC49, 0x0202AC29
IDX_DECK, IDX_BAN = 0xFFD0, 0xFFD1
WORD_MONSTER, WORD_SPELL_TRAP = 0x00000002, 0x0000000C
TAG_YOU_CAN = 0x021E51E5
ADD_TARGET, PICK_OFF = 0x02208181, 0x02235605
CLS1_PHANTOM, CLS2_PHANTOM, LEAVE_PHANTOM = 0x0E8A, 0x0E64, 0x0E2D
MASK_SENT_TO_GY = 0x0800
STATE = 0x0229AAFC
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (ENUM_DECK, ENUM_BAN, SETCODE_PRED, ATK_GET, DEF_GET, TAG_YOU_CAN, H3_RESUME, ADD_TARGET, PICK_OFF):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_ED_{n}") for n in ("COND", "COST", "RES", "COND2", "RES2", "SEL2", "PRED", "DECKH", "BANH", "ROWS", "DATA", "H2", "H3")}
RESERVE = {"COND": 0x80, "COST": 0x20, "RES": 0x120, "COND2": 0x40, "RES2": 0x40, "SEL2": 0x20, "PRED": 0x40, "DECKH": 0x30, "BANH": 0x30, "ROWS": 0x20,
           "DATA": 0x10, "H2": 0x30, "H3": 0x30}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_ED_H2], _DN[O5.CAVE_ED_H3]
ROWS_BLOB = (struct.pack("<HHII", ED, 0xFFFF, S["DECKH"] | 1, WORD_MONSTER) + bytes(4)
             + struct.pack("<HHII", ED, TN.MONARCH_SET, S["BANH"] | 1, WORD_SPELL_TRAP) + bytes(4))
assert len(ROWS_BLOB) == 0x20 and all(struct.unpack_from("<I", ROWS_BLOB, 0x10 * i + 4)[0] for i in range(2)), "a virtual row's handler is missing (blx 0 = freeze)"
CLS1_REC = (ED, 0, S["RES"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)
CLS2_REC = (ED, 0, S["RES2"] | 1, 0, S["COND2"] | 1, TAG_YOU_CAN, S["SEL2"] | 1)
LEAVE_REC = (ED, MASK_SENT_TO_GY)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "edea.c", S[slot], {"STUB": stub, "DATA": f"0x{S['DATA']:08X}"}), slot)


def pred_stub() -> bytes:
    """Deck predicate (the enumerator's stack arg [sp] -> the card word pointer): DEF 1000 and ATK 800 and cid != Edea."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(1, ED)
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


def deckh_stub() -> bytes:
    """Deck row handler (row r0, side r1): 0x0223CAB4's body (Deck Special Summon, type 0xA) with the custom predicate in place of the set-code callback."""
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


def banh_stub() -> bytes:
    """Banished row handler (row r0, side r1): 0x0223FBA0's body (banished set-code picker, key = the row's aux) with the add-to-hand type 0x8 (0x0223DB24's)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R2, R0, #0x0")
    b.insn("LDRH", "R0, [R2, #0x2]")
    b.insn("ADD", "R3, SP, #0x8")
    b.insn("STR", "R0, [SP, #0x8]")                        # key list: the set-code index
    b.insn("LDR", "R0, [R2, #0x8]")
    b.insn("STR", "R0, [SP, #0x0]")                        # the row's word
    b.insn("MOV", "R0, #0x8")
    b.insn("STR", "R0, [SP, #0x4]")                        # type 8 = add / return
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R2, #0x0]")
    b.ldr_const(2, SETCODE_PRED)
    b.ldr_const(4, ENUM_BAN)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return _fit(b.assemble(S["BANH"], pad="nop"), "BANH")


def h2_front() -> bytes:
    """criteria miss tail (r5 = cid): 0x0FDC -> the Deck row (mode 0) or the banished row (mode 1); pop the caller's frame.  Others: BL onward."""
    b = EffectBuilder()
    b.ldr_const(0, ED)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, S["DATA"])
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "ban")
    b.ldr_const(0, IDX_DECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("ban")
    b.ldr_const(0, IDX_BAN)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX_DECK)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x2")
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


class edea_the_heavenly_squire:
    cid: int = ED

    def blobs(self):
        return {"COND": (S["COND"], _c("ED_COND", "COND"), "cls1 +0C cond (C)"),
                "COST": (S["COST"], _c("ED_COST", "COST"), "cls1 +14 cost (C)"),
                "RES": (S["RES"], _c("ED_RES", "RES"), "cls1 +04 resolver (C)"),
                "COND2": (S["COND2"], _c("ED_COND2", "COND2"), "cls2 +0C cond (C)"),
                "RES2": (S["RES2"], _c("ED_RES2", "RES2"), "cls2 +04 resolver (C)"),
                "SEL2": (S["SEL2"], _c("ED_SEL2", "SEL2"), "cls2 +14 selector (C)"),
                "PRED": (S["PRED"], pred_stub(), "Deck predicate"),
                "DECKH": (S["DECKH"], deckh_stub(), "Deck row handler"), "BANH": (S["BANH"], banh_stub(), "banished row handler"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFFD0 / 0xFFD1"),
                "DATA": (S["DATA"], bytes(0x10), "DATA: criteria mode (ships clear)"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "MON": (O5.CAVE_TN_MON, TN.MON_BLOB, "'Monarch' set code 0x6D list (shared with Tenacity)")}

    def compile(self, view=None) -> Compiled:
        c79_trigger_hook.register_extra(ED, "Gokibore -> Edea the Heavenly Squire (Monarch set test ROM, not shipped)")
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "MON", "DATA"):
                assert_thumb1_only(blob, addr)
        group = TN.GROUPS[0]
        assert group.setcode == TN.MONARCH_SET

        def install(rom, v):
            for what, addr in (("Deck enumerator", ENUM_DECK), ("banished picker", ENUM_BAN)):
                first = struct.unpack("<H", bytes(v.blob(addr & ~1, 2)))[0]
                assert (first >> 8) in (0xB4, 0xB5), f"{what} {addr:#x} does not start with a push ({first:#06x}): a wrong function address (blx into garbage = freeze)"
            for lst in (LIST_30, LIST_106):
                assert ED not in v.keys(lst.base, count=lst.count, stride=2), f"donor is in {lst.label}"
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            group.install(rom, v)
            c79_trigger_hook.install(rom)
            c79_trigger_hook.apply(v.buf)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Edea {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            rows = O5.read_cave(rom, S["ROWS"], 0x20)
            c.ok(all(struct.unpack_from("<I", rows, 0x10 * i + 4)[0] for i in range(2)), "both virtual rows have a handler")
            for lst in (LIST_30, LIST_106):
                c.ok(ED not in v.keys(lst.base, count=lst.count, stride=2), f"donor in NEITHER {lst.label} -- so the leave-mask lookup is reached")
            c79_trigger_hook.verify(v.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            group.check(c, rom, v)

        return Compiled(tuple(blobs.values()), rows=(Row(CLS1, CLS1_REC, CLS1_PHANTOM), Row(CLS2, CLS2_REC, CLS2_PHANTOM), Row(LEAVE_MASK, LEAVE_REC, LEAVE_PHANTOM)),
                        installs=(install,), checks=(check,))


SPEC = edea_the_heavenly_squire()
PROPS = card_props("LIGHT", "Warrior", level=1, atk=800, defense=1000, card_type="Effect Monster")
main, verify = dsl.make(SPEC, PROPS, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

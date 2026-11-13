"""Tour Guide From the Underworld (0x0FC2, on Rock Ogre Grotto #1). DARK / Fiend / Level 3 / 1000 / 600.

    "When this card is Normal Summoned: You can Special Summon 1 Level 3 Fiend monster from your hand or Deck,
     but negate its effects, also it cannot be used as Synchro Material."
"""
from __future__ import annotations

import sys

from otn_enhanced import dsl
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.effects.common import Table
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.dsl import CLS1, CRITERIA_1389, Compiled, LIST_CODE7, RIDER_ATTACH, Row


NEGATE_KEYS = Table(0x0226FAB4, 0x23, 2, "<H", label="negate reader key set")           # the node is only HONOURED for members


_CHARGER_ENGINE, _CHARGER_COND, _WHEN_TAG = 0x02206F41, 0x021F0419, 0x021E51E5


_CHARGER_SET_CODE = 0x000E       # criteria `b`: makes the count probe advance


_PER_CANDIDATE = 0x00000002      # criteria fl; bit 0x20 (self exclusion) MUST stay CLEAR or a second copy is unsummonable


_GET_RACE, _GET_LEVEL = 0x0202ABB8, 0x0202ABD8


_HAND_BUILDER, _DECK_BUILDER = 0x0223C16C, 0x0223BC3C


_SS_TAIL = 0x02235604            # native tail of the Explorer-arm: opens the selection dialog, attaches the negate node


_SS_ENGINE, _SS_ENGINE_NATIVE = 0x0226925C, bytes.fromhex("f8b5051c0e1c171c009344f72dfb")


_REVIVAL = Table(0x0226DBBC, 0x82, 2, "<H", label="revival list")


_EXPLORER = 0x229E               # the donor-of-old; must stay a real card


_PRED_SITE, _PRED_NATIVE = 0x0224829E, bytes.fromhex("0e1c071c")


_DENY_KEYS = ((0x02248560, 0x0000225E, 4, "key1 Cherry Inmato"),
              (0x0224851C, 0x3515, 2, "key2 ADD R5,#0x15"),
              (0x0224857A, 0x3D5B, 2, "key4 SUB R5,#0x5B (dead once key3 moves)"),
              (0x022485B0, 0x000024B5, 4, "key5 Vylon Element"),
              (0x022485A6, 0xD101, 2, "key5 set-code exception"))


_DENY_KEY3, _DENY_KEY3_NATIVE = 0x02248564, 0x0000237A


def _race_level_filter(race: int, level: int, addr: int) -> bytes:
    """Candidate filter: race == `race` (implies a monster) and level == `level`."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("LDR", "R0, [SP, #8]")
    b.insn("LDR", "R0, [R0, #0]")
    b.insn("LSL", "R0, R0, #18")
    b.insn("LSR", "R0, R0, #18")
    b.insn("ADD", "R4, R0, #0")
    b.bl(_GET_RACE)
    b.if_ne(R0, race, "no")
    b.insn("ADD", "R0, R4, #0")
    b.bl(_GET_LEVEL)
    b.if_ne(R0, level, "no")
    b.insn("MOV", "R0, #1")
    b.insn("POP", "{R4, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0")
    b.insn("POP", "{R4, PC}")
    return b.assemble(addr, pad="nop")[:0x26]       # poolless: drop the 4-align pad


def _hand_then_deck_selector(addr: int, filt: int) -> bytes:
    """OTN's native dual-zone selector re-authored: enumerate HAND (zone 2) then DECK (zone 0xA) through `filt`."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
    b.insn("ADD", "R5, R0, #0")
    b.insn("MOV", "R0, #2")
    b.insn("ADD", "R4, R1, #0")
    b.raw(0x5E29)                                   # ldsh r1,[r5,r0] (no LDRSH in the encoder)
    b.ldr_const(6, filt | 1)
    b.insn("ADD", "R7, SP, #8")
    b.insn("STR", "R1, [SP, #8]")
    b.insn("LDR", "R1, [R5, #8]")
    b.insn("ADD", "R2, R6, #0")
    b.insn("STR", "R1, [SP, #0]")
    b.insn("STR", "R0, [SP, #4]")                   # hand zone
    b.insn("LDRH", "R1, [R5, #0]")
    b.insn("ADD", "R0, R4, #0")
    b.insn("ADD", "R3, R7, #0")
    b.bl(_HAND_BUILDER)
    b.insn("LDR", "R0, [R5, #8]")
    b.insn("LDRH", "R1, [R5, #0]")
    b.insn("STR", "R0, [SP, #0]")
    b.insn("MOV", "R0, #10")
    b.insn("STR", "R0, [SP, #4]")                   # deck zone
    b.insn("ADD", "R0, R4, #0")
    b.insn("ADD", "R2, R6, #0")
    b.insn("ADD", "R3, R7, #0")
    b.bl(_DECK_BUILDER)
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
    return b.assemble(addr, pad="nop")


def _negate_tail(addr: int) -> bytes:
    """cls1 +14: BL the native tail, return 1. The summon + the negate node {key = this cid, kind 3} complete natively."""
    b = EffectBuilder()
    b.insn("PUSH", "{R2,R4,R5,LR}")
    b.insn("MOV", "R5, R0")
    b.insn("MOV", "R4, R1")
    b.bl(_SS_TAIL)
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R2,R4,R5,PC}")
    return b.assemble(addr)


@dataclass(frozen=True)
class normal_summon_special_summon_negated:
    """'When Normal Summoned: you can Special Summon 1 Level <level> <race> monster from your hand or Deck, but
    negate its effects.' code-7 membership + cls1 (Charger summon engine + WHEN tag + negate tail) + a criteria row
    on the hand+Deck selector. The negate needs BOTH lists: the rider list (without it no node is attached at all)
    and the negate-reader key set (without it the node is attached and ignored). Donor must stay out of the revival
    list (that is the from-GY recipe). `phantoms` = (code-7, cls1, criteria, rider, negate-keys) cids dropped.
    `slots` = (filter, selector, negate tail)."""
    race: int
    level: int
    slots: tuple[int, int, int]
    phantoms: tuple[int, int, int, int, int]

    def compile(self, view, cid) -> Compiled:
        filt, sel, neg = self.slots
        blobs = (_race_level_filter(self.race, self.level, filt), _hand_then_deck_selector(sel, filt), _negate_tail(neg))
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        stubs = tuple(zip(self.slots, blobs, ("race/level filter", "hand+Deck selector", "negate tail")))
        p7, p1, pc, pr, pn = self.phantoms
        rows_ = (Row(LIST_CODE7, (cid,), p7),
                 Row(CLS1, (cid, 0, _CHARGER_ENGINE, 0, _CHARGER_COND, _WHEN_TAG, neg | 1), p1),
                 Row(CRITERIA_1389, (cid, _CHARGER_SET_CODE, sel | 1, _PER_CANDIDATE), pc),
                 Row(RIDER_ATTACH, (cid,), pr),
                 Row(NEGATE_KEYS, (cid,), pn))

        def install(rom, view):
            assert view.blob(_SS_ENGINE, len(_SS_ENGINE_NATIVE)) == _SS_ENGINE_NATIVE, "SS engine is hooked: build from a clean ROM"
            assert view.blob(_PRED_SITE, 4) == _PRED_NATIVE, "Synchro-material predicate is hooked: build from a clean ROM"

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb

            def bls(blob, a):
                return [i.branch_target for i in decode_thumb(blob, a) if i.mnemonic == "BL"]
            c.eq(bls(blobs[0], filt), [_GET_RACE, _GET_LEVEL], "filter BLs -> get_race, get_level")
            c.eq(bls(blobs[1], sel), [_HAND_BUILDER, _DECK_BUILDER], "selector BLs -> hand builder, deck builder")
            rev = view.keys(_REVIVAL.base, count=_REVIVAL.count, stride=2)
            c.ok(cid not in rev and _EXPLORER in rev, "donor stays OUT of the revival list")
            c.eq(_PER_CANDIDATE & 0x20, 0, "criteria fl bit 0x20 CLEAR, so a second copy is summonable")

        return Compiled(stubs, rows_, installs=(install,), checks=(check,))


@dataclass(frozen=True)
class cannot_be_synchro_material:
    """'It cannot be used as Synchro Material' with NO exception: Synchro-material deny key 3 retargeted at this
    cid (the negate node and the embargo rider are the same object). Price: key 4 derives from key 3 by `SUB #0x5B`,
    so the two cards the old key 3/4 pair denied (Necro Linker 0x237A, Wiseman's Chalice 0x231F) lose their riders;
    keys 1/2/5 must stay native (key 5 is Vylon Element's)."""

    def compile(self, view, cid) -> Compiled:
        def native_keys_ok(v):
            for addr, want, width, who in _DENY_KEYS:
                got = v.u32(addr) if width == 4 else v.u16(addr)
                assert got == want, f"{who} @0x{addr:08X} is 0x{got:X}, expected native 0x{want:X}"

        def install(rom, view):
            cur = view.u32(_DENY_KEY3)
            assert cur in (_DENY_KEY3_NATIVE, cid), f"deny-key pool @0x{_DENY_KEY3:08X} = 0x{cur:08X}, not native"
            view.set_u32(_DENY_KEY3, cid)
            native_keys_ok(view)

        def check(c, rom, view):
            c.eq(view.u32(_DENY_KEY3), cid, f"deny key 3 @0x{_DENY_KEY3:08X} -> 0x{cid:04X}")
            try:
                native_keys_ok(view)
                c.ok(True, "deny keys 1/2/4/5 + key 5's gate native (Vylon Element keeps her rider)")
            except AssertionError as exc:
                c.ok(False, f"other deny keys native: {exc}")

        return Compiled(installs=(install,), checks=(check,))



CID = DONOR_CID = 0x0FC2   # DONOR_CID: read by KB proofs (archetype_setcode_tables, steam_synchron)
FIEND = 3

SPEC = dsl.card(
    CID,
    normal_summon_special_summon_negated(
        race=FIEND, level=3,
        slots=(cave3.CAVE3_TG_FILTER, cave3.CAVE3_TG_SELECTOR, cave3.CAVE3_TG_NEGATE),
        phantoms=(0x0E7E, 0x0E1B, 0x0E2E, 0x0E4B, 0x0E57)),
    cannot_be_synchro_material())

main, verify = dsl.make(SPEC, dsl.card_props("DARK", "Fiend", 3, 1000, 600),
                        out="data/over_the_nexus/working/rom_tour_guide.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

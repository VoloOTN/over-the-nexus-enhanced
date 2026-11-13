"""Junk Servant (EARTH / Warrior / Level 4 / 1500 / 1000) on Neo Aqua Madoor 0x17CE.

    "If you control a "Junk" monster, you can Special Summon this card (from your hand)."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import archetype_member, card, card_props, special_summon_self_from_hand, SetCodeTable, _CAN_SS
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from dataclasses import dataclass


_FIELD_SETCODE_COUNT = 0x021ACFE8   # (side, thunk, exclude, faceup_only) -> count, monster zones 0..4 only


@dataclass(frozen=True)
class controls_faceup_archetype_monster:
    """'If you control a face-up <archetype> monster' -- canSS(side) && 0x021ACFE8(side, thunk, -1, 1) != 0.
    Clone of the native Six Samurai leaf 0x0225F7A0; r2 = -1 (outside 0..0xA) means exclude nothing, and the
    counter only walks monster zones, so a Spell in the archetype never satisfies it. UNVERIFIED here."""
    thunk: int      # has_set_code[n] thunk (Thumb, LSB set)
    calls = frozenset({_CAN_SS, _FIELD_SETCODE_COUNT})

    def lower_cond(self, b):
        b.prologue(save=[R4])
        b.insn("ADD", "R4, R0, #0x0")        # r4 = side
        b.call_addr(_CAN_SS)
        b.if_eq(R0, 0, "no")
        b.insn("ADD", "R0, R4, #0x0")
        b.ldr_const(1, self.thunk)
        b.insn("MOV", "R2, #0x0")
        b.insn("MVN", "R2, R2")              # r2 = -1
        b.insn("MOV", "R3, #0x1")            # faceup_only
        b.bl(_FIELD_SETCODE_COUNT)
        b.if_eq(R0, 0, "no")
        b.epilogue(ret=1)
        b.label("no")
        b.epilogue(ret=0)


JUNK_TABLE = SetCodeTable("Junk", 0x0209C842, 13, (0x02023E64,), (0x02023E60,))



JUNK_THUNK = 0x02023E5D     # has_set_code[0x50]

SPEC = card(
    0x17CE,
    special_summon_self_from_hand(when=controls_faceup_archetype_monster(JUNK_THUNK), slot=cave3.CAVE3_JS_SSCOND),
    archetype_member(JUNK_TABLE, phantom=0x2500))

PROPS = card_props("EARTH", "Warrior", level=4, atk=1500, defense=1000)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_junk_servant.nds")



def add_junk_member(out_path: str, insert_cid: int, phantom_cid: int) -> None:
    """Kept for junk_speeder: join the "Junk" set-code table in place, dropping `phantom_cid`."""
    archetype_member(JUNK_TABLE, phantom=phantom_cid).compile(None, insert_cid).posts[0](out_path)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

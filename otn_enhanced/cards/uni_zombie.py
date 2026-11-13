"""Uni-Zombie (DARK / Zombie / Tuner / Level 3 / 1300 / 0) on Illusionist Faceless Mage 0x0FD0.

    "You can target 1 face-up monster on the field; discard 1 card, and if you do, increase that target's Level by 1.
     You can target 1 face-up monster on the field; monsters you control cannot attack for the rest of this turn,
     except Zombie monsters, also send 1 Zombie monster from your Deck to the Graveyard, and if you do, increase that
     target's Level by 1. You can only use each effect of "Uni-Zombie" once per turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS3, CRITERIA, Compiled, Row, _CHAIN_POP, _CHAIN_PUSH, _RES_STATE, _UI_RESULT, _in_ov5
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import struct


_UZ_TL_QUERY, _UZ_TL_POST, _UZ_MISF_QUERY = 0x021A14E9, 0x021D2585, 0x021A1431


_UZ_PARAM, _UZ_CRIT_COUNT, _UZ_OFFER_GATE = 0x02234E79, 0x02243FE1, 0x021F06E9


_UZ_PROMPT = 0x0219ABB5


_UZ_DECK_SEND_RES, _UZ_TGT_HAS, _UZ_TGT_GET, _UZ_REVALIDATE = 0x02208DD5, 0x022349B1, 0x02234905, 0x0224A925


_UZ_RIDER_WRITE, _UZ_DISCARD, _UZ_RACE_MASK = 0x021C479D, 0x022598A1, 0x021B8D91


_UZ_ATK_SITE, _UZ_ATK_SITE_STOCK = 0x021A4BC8, bytes.fromhex("fcf732fc")


_HAND_COUNT_WORD = 0x0229ACA0


@dataclass(frozen=True)
class two_ignitions_target_level_up:
    """Uni-Zombie: 'You can target 1 face-up monster on the field; discard 1 card, and if you do, increase that target's
    Level by 1. You can target 1 face-up monster on the field; monsters you control cannot attack for the rest of this turn,
    except <race> monsters, also send 1 <race> monster from your Deck to the GY, and if you do, increase that target's
    Level by 1. You can only use each effect once per turn.'  User rulings: C1 NOT activatable with an empty hand; C2 NOT
    activatable with no <race> in the Deck.
      B  ONE cls3 record: +04 RES (desc[+0x18]==2 -> C2 else C1), +08 0x021DB1D9 (Ice Master's slot2: 0x021D6E40 mask 0x414
         'face-up monster on the field'), +0C COND (desc[+7] != 0 post-cost or MASK != 0, then the generic offer gate),
         +10 COST (phase [0x0229AAFC+0x7C]: 0 'Use which effect?' prompt, 1 desc[+0x18] = choice+1 and post that effect's
         once-per-turn node), +14 0x02234D81 (slot5 thunk, prompt 0x6F). A second cls3 record is reachable only through
         the per-cid option switch whose default is mask 0, so one record with its own prompt (Ape / Accel pattern).
      C  criteria {cid, 0xFFFF, Deck, <race> word} over a phantom.
      D  RES C1: 0x80 hand > 0 -> chain push + effect discard -> 0x7F; 0x7F Level +1 -> chain pop. C2: 0x80 posts the lock
         node (side, 0x4000|cid, kind 1), then the native deck-send resolver runs every phase and re-enters at 0x7C ONLY
         after a successful send, where we write Level +1 and return 0x64. Level +1 = 0x021C479D(side, zone, 0x22EB, 3,
         [sp] 1) (dispatch.level_rider_key_is_a_selector).
      E  ATTACK LOCK: the can-attack gate 0x021A4670 asks Misfortune's turn-log node at `bl 0x021A1430` @0x021A4BC8; that
         BL -> an ov3 stub keeping Misfortune's answer and also denying while (side, 0x4000|cid, kind 1) is posted and the
         attacker's live race mask lacks the race bit. ov3 on purpose: every attack in every mode runs this gate.
    ov5 slots = (mask, cond, cost, res); `atk` is an ov3 pool slot."""
    slot2: int                     # +08 slot2
    slot5: int                     # +14
    zombie_word: int               # criteria word (race << 3 in the top byte)
    race_bit: int                  # live race-mask bit that stays allowed (4 = Zombie)
    slots: tuple[int, int, int, int]
    atk: int
    phantoms: tuple[int, int]      # (cls3, criteria)

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import thumb_bl  # noqa: F401
        mask_s, cond_s, cost_s, res_s = self.slots
        ph3, phc = self.phantoms
        lock_key = 0x4000 | cid
        assert not _in_ov5(self.atk) and all(_in_ov5(a) for a in self.slots)
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("MOV", "R6, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, 1, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "c2")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.ldr_const(1, 0xB3C)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, _HAND_COUNT_WORD)
        b.insn("LDR", "R0, [R1, R0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "c2")
        b.insn("MOV", "R6, #0x1")
        b.label("c2")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, 2, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "out")
        b.call_addr(_UZ_PARAM, R5, via=R4)
        b.insn("ADD", "R2, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.insn("LDRB", "R1, [R5, #0x6]")
        b.insn("EOR", "R0, R1")
        b.call_addr(_UZ_CRIT_COUNT, R0, cid, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "out")
        b.insn("MOV", "R0, #0x2")
        b.insn("ORR", "R6, R0")
        b.label("out")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        mb = b.assemble(mask_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "gate")
        b.call_addr(mask_s, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.label("gate")
        b.call_addr(_UZ_OFFER_GATE, R4, via=R3)
        b.label("out")
        b.insn("POP", "{R4, PC}")
        cb = b.assemble(cond_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("SUB", "SP, #0xC")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(5, _RES_STATE)
        b.insn("LDR", "R0, [R5, #0x7C]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "pick")
        b.call_addr(mask_s, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "abort")
        b.insn("MOV", "R1, #0x4")
        b.insn("ORR", "R0, R1")
        b.insn("STR", "R0, [SP, #0x8]")
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [SP, #0x4]")
        b.ldr_const(0, 0x01AC)
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("ADD", "R0, R4, #0x0")
        b.ldr_const(1, 0x0103)
        b.ldr_const(2, 0x00EB)
        b.call_addr(_UZ_PROMPT, R0, R1, R2, 0x01F3, via=R5)
        b.ldr_const(5, _RES_STATE)
        b.insn("MOV", "R0, #0x1")
        b.insn("STR", "R0, [R5, #0x7C]")
        b.insn("MOV", "R0, #0x0")
        b.insn("B", "out")
        b.label("abort")
        b.insn("MOV", "R0, #0x0")
        b.insn("SUB", "R0, #0x1")
        b.insn("B", "out")
        b.label("pick")
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [R5, #0x7C]")
        b.ldr_const(0, _UI_RESULT)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("ADD", "R2, R0, #0x1")
        b.insn("STRH", "R2, [R4, #0x18]")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call("turnlog_post", R0, cid, R2, 0, via=R5)
        b.insn("MOV", "R0, #0x1")
        b.label("out")
        b.insn("ADD", "SP, #0xC")
        b.insn("POP", "{R4, R5, PC}")
        kb = b.assemble(cost_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(5, _RES_STATE)
        b.insn("LDR", "R5, [R5, #0x70]")
        b.insn("LDRH", "R0, [R4, #0x18]")
        b.insn("CMP", "R0, #0x2")
        b.insn("BEQ", "c2")
        b.insn("CMP", "R5, #0x80")
        b.insn("BEQ", "c1_discard")
        b.insn("CMP", "R5, #0x7F")
        b.insn("BNE", "zero")
        b.bl_label("level_up")
        b.call_addr(_CHAIN_POP, via=R3)
        b.label("zero")
        b.insn("MOV", "R0, #0x0")
        b.insn("B", "out")
        b.label("c1_discard")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.ldr_const(1, 0xB3C)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, _HAND_COUNT_WORD)
        b.insn("LDR", "R0, [R1, R0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "zero")
        b.call_addr(_CHAIN_PUSH, via=R3)
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_UZ_DISCARD, R0, 1, 0, 0, via=R6)
        b.insn("MOV", "R0, #0x7F")
        b.insn("B", "out")
        b.label("c2")
        b.insn("CMP", "R5, #0x7C")
        b.insn("BEQ", "c2_level")
        b.insn("CMP", "R5, #0x80")
        b.insn("BNE", "native")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, lock_key, 1, via=R6)
        b.label("native")
        b.call_addr(_UZ_DECK_SEND_RES, R4, via=R3)
        b.insn("B", "out")
        b.label("c2_level")
        b.bl_label("level_up")
        b.insn("MOV", "R0, #0x64")
        b.label("out")
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("level_up")
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("ADD", "R6, R4, #0x0")
        b.call_addr(_UZ_TGT_HAS, R6, 0, 0, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "lu_out")
        b.call_addr(_UZ_TGT_GET, R6, 0, via=R3)
        b.insn("LSL", "R4, R0, #0x18")
        b.insn("LSR", "R4, R4, #0x18")
        b.insn("LSL", "R5, R0, #0x10")
        b.insn("LSR", "R5, R5, #0x18")
        b.insn("CMP", "R5, #0x5")
        b.insn("BGE", "lu_out")
        b.call_addr(_UZ_REVALIDATE, R6, R4, R5, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "lu_out")
        b.insn("MOV", "R0, #0x1")
        b.insn("STR", "R0, [SP, #0x0]")
        b.call_addr(_UZ_RIDER_WRITE, R4, R5, 0x22EB, 3, via=R6)
        b.label("lu_out")
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, PC}")
        rb = b.assemble(res_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.call_addr(_UZ_MISF_QUERY, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "out")
        b.insn("ADD", "R0, R5, #0x0")
        b.turnlog_query(R0, lock_key, 1, via=R6)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.call_addr(_UZ_RACE_MASK, R5, R4, via=R3)
        b.insn("MOV", f"R1, #{self.race_bit}")
        b.insn("AND", "R0, R1")
        b.insn("BEQ", "deny")
        b.insn("MOV", "R0, #0x0")
        b.insn("B", "out")
        b.label("deny")
        b.insn("MOV", "R0, #0x1")
        b.label("out")
        b.insn("POP", "{R4, R5, R6, PC}")
        ab = b.assemble(self.atk, pad="nop")
        blobs = (mb, cb, kb, rb)
        for blob, addr in list(zip(blobs, self.slots)) + [(ab, self.atk)]:
            assert_thumb1_only(blob, addr)
        patched = _shim_bl_enc(_UZ_ATK_SITE, self.atk)
        assert _shim_bl_enc(_UZ_ATK_SITE, _UZ_MISF_QUERY & ~1) == _UZ_ATK_SITE_STOCK, "BL encoder disagrees with the stock site"

        def install(rom, view):
            cur = view.blob(_UZ_ATK_SITE, 4)
            assert cur in (_UZ_ATK_SITE_STOCK, patched), f"attack-gate site @{_UZ_ATK_SITE:#x} is {cur.hex()}"
            view.write(_UZ_ATK_SITE, patched)

        def check(c, rom, view):
            c.eq(view.blob(_UZ_ATK_SITE, 4), patched, f"attack-gate BL @{_UZ_ATK_SITE:#x} -> the ov3 stub")

        names = ("mask", "cond", "cost", "resolver")
        return Compiled(tuple(zip(self.slots, blobs, names)) + ((self.atk, ab, "attack gate"),),
                        (Row(CLS3, (cid, res_s | 1, self.slot2, cond_s | 1, cost_s | 1, self.slot5), ph3),
                         Row(CRITERIA, (cid, 0xFFFF, 0x0223CAD9, self.zombie_word), phc)),
                        installs=(install,), checks=(check,))


def _shim_bl_enc(src: int, dst: int) -> bytes:
    off = (dst - (src + 4)) >> 1
    assert -0x200000 <= off < 0x200000
    return struct.pack("<HH", 0xF000 | ((off >> 11) & 0x7FF), 0xF800 | (off & 0x7FF))



SPEC = card(
    0x0FD0,
    two_ignitions_target_level_up(
        slot2=0x021DB1D9, slot5=0x02234D81, zombie_word=0x10000002, race_bit=4,
        slots=(ov5_cave.CAVE_UZ_MASK, ov5_cave.CAVE_UZ_COND, ov5_cave.CAVE_UZ_COST, ov5_cave.CAVE_UZ_RES),
        atk=cave3.CAVE3_UZ_ATK, phantoms=(0x0E39, 0x0E41)))

PROPS = card_props("DARK", "Zombie", level=3, atk=1300, defense=0, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_uni_zombie.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

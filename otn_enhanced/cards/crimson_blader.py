"""Crimson Blader (FIRE / Warrior / Synchro Effect / Level 8 / 2800 / 2600) on Crimson Sunbird 0x1179.

    1 Tuner + 1 or more non-Tuner monsters
    If this card destroys an opponent's monster by battle and sends it to the Graveyard: Your opponent cannot
    Normal or Special Summon Level 5 or higher monsters during their next turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_prop_copied_from_template, card_props, fusion_recipe_blanked, CLS1, Compiled, Row
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.effects.common import Table
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
import struct


BATTLE_DESTROY_FLAGS = Table(0x0226EA64, 0x6E, 4, "<HH", label="attacker-side battle-destruction row")


_CB_FLAGS_POOL, _CB_FLAGS_COUNT_IMM = 0x021CAB90, 0x021CAAF4        # sole literal of the table / `movs r2,#0x6E`


_CB_DUEL_STATE, _CB_TURN_PLAYER_OFF = 0x0229DD14, 0x34


_CB_NODE_QUERY_LEVEL, _CB_LEVEL_OF_ZONE, _CB_WORM_BAIT = 0x021A14E9, 0x021B8065, 0x2146


_CB_ARM1 = (0x021AF176, 0x021AF198, bytes.fromhex("134a281c0b210123f2f7b3f9002808d0281c311c08f06bffc01e012801d80020f8bd"))


_CB_ARM2 = (0x021BA1E8, 0x021BA206, bytes.fromhex("08b5c91e012908d8054a0b210123e7f777f9002801d0002008bd012008bd"))


@dataclass(frozen=True)
class battle_destroy_opponent_cannot_summon_level_or_higher:
    """'If this card destroys an opponent's monster by battle and sends it to the Graveyard: Your opponent cannot Normal
    or Special Summon Level N or higher monsters during their next turn.'
      trigger  row {cid, mask} in the attacker-side battle-destruction table 0x0226EA64 (mask 0x000F = opponent's
               monster, to the GY); count `movs r2,#0x6E` and the sole pool literal asserted.
      lock     cls1 {lock stub} (Hydro Genex's shape): posts the family-1 summon-lock node on the OPPONENT with a
               per-turn countdown picked by the turn player (kind 0x11 own turn, 0x21 opponent's turn: the trigger
               fires on either turn and the node must outlive the opponent's next turn start).
      read     Worm Bait 0x2146's two enforcement arms (Normal per hand slot @0x021AF176, the Special (side, Level)
               predicate @0x021BA1E8) are replaced IN PLACE by thunks to one ov5 gate that answers BOTH locks --
               Worm Bait's own rule must stay in the gate, these arms ARE its implementation. The two AI planner arms
               are deliberately not built: the CPU may propose a refused Level-N+ summon."""
    mask: int
    level: int
    lock_kind: int
    lock: int
    gate: int
    phantoms: tuple[int, int]        # (flags row, cls1)

    def compile(self, view, cid) -> Compiled:
        php, ph1 = self.phantoms
        assert self.level == 5          # the gate's `cmp r5,#5 ; blt allow`
        own, opp = self.lock_kind | (1 << 4), self.lock_kind | (2 << 4)
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R1, [R4, #0x2]")
        b.ldr_const(0, _CB_DUEL_STATE)
        b.insn("LDR", f"R0, [R0, #0x{_CB_TURN_PLAYER_OFF:X}]")
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "own")
        b.insn("MOV", f"R2, #0x{opp:X}")
        b.insn("B", "post")
        b.label("own")
        b.insn("MOV", f"R2, #0x{own:X}")
        b.label("post")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R0, R0, R1")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.call("turnlog_post", R0, R1, R2, 0, via=R4)
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        lock = b.assemble(self.lock, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.insn("ADD", "R6, R3, #0x0")
        b.insn("MOV", "R0, #0x1")                           # flag 1: r1 is a hand slot, resolve the Level
        b.insn("AND", "R0, R6")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "have_level")
        b.call_addr(_CB_LEVEL_OF_ZONE, R4, R5, via=R2)
        b.insn("ADD", "R5, R0, #0x0")
        b.label("have_level")
        b.insn("MOV", "R0, #0x2")                           # flag 2: skip the Worm Bait arm
        b.insn("AND", "R0, R6")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "crimson")
        b.insn("CMP", "R5, #0x3")
        b.insn("BLT", "crimson")
        b.insn("CMP", "R5, #0x4")
        b.insn("BGT", "crimson")
        b.insn("ADD", "R0, R4, #0x0")
        b.turnlog_query(R0, _CB_WORM_BAIT, 1, via=R6)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "deny")
        b.label("crimson")
        b.insn("CMP", f"R5, #0x{self.level:X}")
        b.insn("BLT", "allow")
        b.insn("ADD", "R0, R4, #0x0")
        b.turnlog_query(R0, cid, 1, via=R6)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "deny")
        b.label("allow")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("deny")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        gate = b.assemble(self.gate, pad="nop")
        for blob, addr in ((lock, self.lock), (gate, self.gate)):
            assert_thumb1_only(blob, addr)
        for a_ in (_CB_NODE_QUERY_LEVEL, _CB_LEVEL_OF_ZONE):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"

        def arm1() -> bytes:
            addr, end, _ = _CB_ARM1
            b = EffectBuilder()
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("MOV", "R2, #0x0")
            b.insn("MOV", "R3, #0x1")
            head = b.assemble(addr, pad="nop")
            call = common_bl(addr + len(head), self.gate)
            b = EffectBuilder()
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "allow")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("allow")
            tail = b.assemble(addr + len(head) + len(call), pad="nop")
            blob = head + call + tail
            assert len(blob) <= end - addr
            return blob + b"\xc0\x46" * ((end - addr - len(blob)) // 2)

        def arm2() -> bytes:
            addr, end, _ = _CB_ARM2
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("MOV", "R2, #0x0")
            b.insn("MOV", "R3, #0x0")
            head = b.assemble(addr, pad="nop")
            call = common_bl(addr + len(head), self.gate)
            b = EffectBuilder()
            b.insn("POP", "{R4, PC}")
            tail = b.assemble(addr + len(head) + len(call), pad="nop")
            blob = head + call + tail
            assert len(blob) <= end - addr
            return blob + b"\xc0\x46" * ((end - addr - len(blob)) // 2)

        arms = ((arm1(), _CB_ARM1), (arm2(), _CB_ARM2))
        assert view.u32(_CB_FLAGS_POOL) == BATTLE_DESTROY_FLAGS.base, "flags-table literal moved"
        assert view.blob(_CB_FLAGS_COUNT_IMM, 2) == bytes.fromhex("6e22"), "flags-table count immediate drifted"
        assert BATTLE_DESTROY_FLAGS.count == 0x6E

        def install(rom, view):
            for blob, (addr, end, stock) in arms:
                assert_thumb1_only(blob, addr)
                cur = view.blob(addr, end - addr)
                if cur == blob:
                    continue
                assert cur == stock, f"arm @{addr:#x} is neither stock nor ours -- another patch moved it"
                view.write(addr, blob)

        def check(c, rom, view):
            for lst, n in ((0x02275AB8, 16), (0x02275AD8, 21), (0x02248280, 2)):
                c.ok(cid not in view.unpack(lst, f"<{n}H"), f"donor absent from Synchro exception list {lst:#x}")
            c.eq(view.u32(_CB_FLAGS_POOL), BATTLE_DESTROY_FLAGS.base, "flags-table literal still points at the table")
            c.eq(view.blob(_CB_FLAGS_COUNT_IMM, 2), bytes.fromhex("6e22"), "flags-table count immediate unchanged")
            for blob, (addr, end, _s) in arms:
                c.eq(view.blob(addr, end - addr), blob, f"enforcement arm @{addr:#x} installed")
            c.ok(struct.pack("<I", _CB_WORM_BAIT) in gate, "Worm Bait 0x2146 rule preserved in the gate")
            c.ok(struct.pack("<I", cid) in gate and struct.pack("<I", _CB_NODE_QUERY_LEVEL) in gate,
                 "gate holds the donor key and the node query")

        return Compiled(((self.lock, lock, "lock-node poster"), (self.gate, gate, "summon gate")),
                        (Row(BATTLE_DESTROY_FLAGS, (cid, self.mask), php),
                         Row(CLS1, (cid, 0, self.lock | 1, 0, 0, 0, 0), ph1)),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x1179,
    fusion_recipe_blanked(row=31, stock=(0x1179, 0x1023, 0x1178, 0)),
    battle_destroy_opponent_cannot_summon_level_or_higher(
        mask=0x000F, level=5, lock_kind=1, lock=ov5_cave.CAVE_CB_LOCK, gate=ov5_cave.CAVE_CB_GATE,
        phantoms=(0x0E9C, 0x1197)),
    card_prop_copied_from_template(ref_cid=0x23FE, card_type="Synchro Effect Monster",
                                   donor_genre=0x0000000020200000, new_genre=0x0000001000200000))

PROPS = card_props("FIRE", "Warrior", level=8, atk=2800, defense=2600, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_crimson_blader.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

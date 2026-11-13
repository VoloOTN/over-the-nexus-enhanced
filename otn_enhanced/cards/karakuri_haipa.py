"""Karakuri Muso mdl 818 "Haipa" (EARTH / Machine / Level 4 / 2100 / 1100) on Saggi the Dark Clown 0x0FC8.

    This card must attack if able. When this face-up Attack Position card is selected as an attack target, change it to
    Defense Position. If this card attacks, it is changed to Defense Position at the end of the Battle Phase.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import KARAKURI_TABLE, archetype_member, card, card_props, CLS1, Compiled, Row
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
from otn_enhanced.effects.common import rows


@dataclass(frozen=True)
class must_attack_if_able:
    """'This card must attack if able.' Two ordered compare chains (0x0224D250 / 0x0224D530) read the zone's cid through
    the SAME getter `bl 0x021A36EC` and accept exactly the monsters that print the clause (Berserk Gorilla, the five
    STBL Karakuri 0x2388..0x238C via a five-entry jump table, Saizan, Kuick). A donor is reached by REMAPPING its cid
    onto Nisamu 0x2388 at the getter: both `bl` sites go to one stub (same ABI, r0 side / r1 zone in, cid out) whose
    admit list is SHARED -- the sites are single-site, so another Karakuri donor joins `admit`, never a second stub."""
    slot: int
    admit: tuple                    # cids remapped onto `accepted`
    sites: tuple                    # (site, stock bytes) -- the two `bl getter`
    getter: int = 0x021A36EC
    accepted: int = 0x2388

    def compile(self, view, cid) -> Compiled:
        assert cid in self.admit
        a = EffectBuilder()
        a.prologue()
        a.call_addr(self.getter)                    # r0 = the real cid
        for c_ in self.admit:
            a.ldr_const(int(R1), c_)
            a.insn("CMP", "R0, R1")
            a.insn("BEQ", "hit")
        a.insn("B", "out")
        a.label("hit")
        a.ldr_const(int(R0), self.accepted)         # remap: answer "Nisamu"
        a.label("out")
        a.insn("POP", "{PC}")
        blob = a.assemble(self.slot)
        assert_thumb1_only(blob, self.slot)
        assert len(blob) <= 0x30

        def install(rom, view):
            for site, stock in self.sites:
                cur, want = view.blob(site, 4), common_bl(site, self.slot)
                if cur != want:
                    assert cur == stock, f"{site:#010x} is not the stock `bl {self.getter:#010x}`: {cur.hex()}"
                    view.write(site, want)

        def check(c, rom, view):
            for site, _s in self.sites:
                c.eq(view.blob(site, 4), common_bl(site, self.slot), f"must-attack hook {site:#010x} -> {self.slot:#010x}")
            c.eq(self.admit, (cid, 0x0FFD), "must-attack admit list (0x0FFD = ninishi's donor must stay listed)")

        return Compiled(((self.slot, blob, "must-attack remap stub"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class change_to_defense_when_selected_as_attack_target:
    """'When this face-up Attack Position card is selected as an attack target, change it to Defense Position.' cls1
    {position-change resolver, 0, 'is face-up Attack Position' gate} cloned from `template` (Black Stego, byte-identical
    on all five STBL Karakuri), over a phantom. The record alone is NOT enough: the code-0x13 event is posted to only 26
    hardcoded cids, so the donor also joins the SHARED ov3 attack-target admit list (effects/atktgt_gate)."""
    template: int
    resolver: int
    condition: int
    phantom: int

    def compile(self, view, cid) -> Compiled:
        assert any(r[0] == self.template and r[2:] == (self.resolver, 0, self.condition, 0, 0)
                   for r in rows(view, CLS1)), "the position-change template record drifted"

        def install(rom, view):
            from otn_enhanced.effects import atktgt_gate
            atktgt_gate.install(view.buf, cid)

        def check(c, rom, view):
            from otn_enhanced.effects import atktgt_gate
            c.ok(atktgt_gate.hooked(view.buf) and cid in atktgt_gate.admitted(view.buf),
                 f"{cid:#06x} is in the SHARED ov3 attack-target admit list (clause 2 receives the event)")

        return Compiled((), (Row(CLS1, (cid, 0, self.resolver, 0, self.condition, 0, 0), self.phantom),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class end_of_battle_phase_flip_to_defense_without_lock:
    """'If this card attacks, it is changed to Defense Position at the end of the Battle Phase.' The end-of-Battle-Phase
    sweep 0x02252EC0 has three arms: A flips + attaches the position LOCK, B flips with NO lock (Destiny HERO Dasher,
    Transforming Sphere, Gem-Knight Aquamarine: exactly the printed no-lock cards), C flips face-down. The stub replaces
    `adds r5,r0,#0 ; ldr r0,[pc]` at the sweep's tree head (donor-cid-agnostic: the tree's `>0x21FC` leaf is only
    reached for larger cids) and sends the donor to Arm B."""
    slot: int
    hook: int
    stock: bytes
    resume_pivot: int               # what the displaced `ldr r0,[pc,#0x148]` loaded
    arm_b: int
    arm_b_members: tuple            # Arm B's native membership, asserted intact

    def compile(self, view, cid) -> Compiled:
        a = EffectBuilder()
        (a
         .insn("MOV", "R5, R0")                     # displaced: r5 = cid (flags dead: the next insn is a CMP)
         .ldr_const(int(R0), cid)
         .insn("CMP", "R5, R0")
         .insn("BEQ", "armb")
         .ldr_const(int(R0), self.resume_pivot)     # displaced: r0 = 0x1CAB
         .insn("BX", "LR")                          # -> the `cmp r5,r0` the displaced pair fed, native tree
         .label("armb")
         .ldr_const(int(R0), self.arm_b | 1)        # Thumb bit
         .insn("BX", "R0"))
        blob = a.assemble(self.slot)
        assert_thumb1_only(blob, self.slot)
        assert len(blob) <= 0x30

        def install(rom, view):
            cur, want = view.blob(self.hook, 4), common_bl(self.hook, self.slot)
            if cur != want:
                assert cur == self.stock, f"{self.hook:#010x} is not the stock `adds r5,r0,#0 ; ldr r0,[pc]`: {cur.hex()}"
                view.write(self.hook, want)

        def check(c, rom, view):
            c.eq(view.blob(self.hook, 4), common_bl(self.hook, self.slot), f"BP-flip hook {self.hook:#010x} -> {self.slot:#010x}")
            # Arm B must still be the no-lock arm: the position primitive, then the common tail WITHOUT Arm A's lock attach.
            c.eq(view.u16(self.arm_b + 0x1A), 0xE7E9, f"Arm B {self.arm_b:#010x} still `b 0x02253068` (skips the position LOCK)")

        return Compiled(((self.slot, blob, "BP-flip stub"),), installs=(install,), checks=(check,))



DONOR_CID = 0x0FC8
# Cids remapped onto Nisamu 0x2388 at the cid getter: the donors that PRINT "must attack if able". SHARED with ninishi
# (0x0FFD, Dark Chimera): the two hook sites are single-site, so another Karakuri donor joins this list.
MUSTATK_ADMIT = (DONOR_CID, 0x0FFD)

SPEC = card(
    DONOR_CID,
    change_to_defense_when_selected_as_attack_target(
        template=0x1A78, resolver=0x0220C6B1, condition=0x021F4D4D, phantom=0x0ECC),     # template: Black Stego
    must_attack_if_able(cave3.CAVE3_HAIPA_MUSTATK, MUSTATK_ADMIT,
                        sites=((0x0224D254, bytes.fromhex("56f74afa")), (0x0224D534, bytes.fromhex("56f7daf8")))),
    end_of_battle_phase_flip_to_defense_without_lock(
        cave3.CAVE3_HAIPA_BPFLIP, hook=0x02252F9A, stock=bytes.fromhex("051c5248"), resume_pivot=0x1CAB,
        arm_b=0x02253078, arm_b_members=(0x1A61, 0x21FC, 0x22D0)),
    archetype_member(KARAKURI_TABLE, phantom=0x2445))

PROPS = card_props("EARTH", "Machine", level=4, atk=2100, defense=1100)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_karakuri_haipa.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

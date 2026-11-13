"""Assault Synchron (DARK / Machine / Tuner / Level 2 / 700 / 0) on Shapesnatch 0x13AE.

    "During your Main Phase: You can Special Summon this card from your hand, then take 700 damage. If a face-up
     Dragon Synchro Monster(s) you control is Tributed or banished: You can banish this card from your GY, then
     target 1 of those monsters; Special Summon it. You can only use each effect of "Assault Synchron" once per turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, CLS2, CRITERIA, Compiled, Row, _AS_CANSS, _AS_DUEL_STATE, _AS_OFFFIELD_PICKER, _AS_REVIVE_RESOLVER, _AS_TURNLOG_QUERY
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass


_AS_RACE, _AS_IS_SYNCHRO, _AS_GY_POSTER, _AS_GY_INDEX = 0x0202ABB8, 0x02023050, 0x021D3648, 0x021A2510


_AS_GY_BANISH_COST, _AS_YOU_CAN_BODY = 0x021E5708, 0x021E50DC


_AS_GY_BUILDER, _AS_BANISHED_BUILDER = 0x0223C4E8, 0x0223C6AC


_AS_LEAVE_SITE, _AS_LEAVE_SITE_BYTES = 0x021C93D0, bytes.fromhex("11980028")   # ldr r0,[sp,#0x44] ; cmp r0,#0


_AS_LEAVE_CODE, _AS_REF_KEY_BASE = 0x1D, 0x4000


@dataclass(frozen=True)
class hand_special_summon_main_phase_take_damage:
    """'During your Main Phase: You can Special Summon this card from your hand, then take N damage. Once per turn.'
    A hand-menu summon PROCEDURE (not a chain-link effect): the shared hand-SS trampoline offers it, its condition
    stub `slot` (ov5) = turn-log (side, 0x0B, cid, kind) clear && it is your turn && phase in {2, 4} && canSS(side);
    the damage rides the shared SS-commit hook row (cid, kind, N), which posts the once-per-turn node first."""
    slot: int
    damage: int
    kind: int = 1

    def compile(self, view, cid) -> Compiled:
        a = EffectBuilder()
        a.prologue(save=[R4])
        a.insn("ADD", "R4, R0, #0x0")                       # r4 = side
        a.turnlog_query(R0, cid, self.kind)                 # r0 still = side
        (a
         .insn("CMP", "R0, #0x0")
         .insn("BNE", "no")                                 # already used this turn
         .ldr_const(1, _AS_DUEL_STATE)
         .insn("LDR", "R0, [R1, #0x34]")
         .insn("CMP", "R0, R4")
         .insn("BNE", "no")                                 # not your turn
         .insn("LDR", "R0, [R1, #0x48]")
         .insn("CMP", "R0, #0x2")
         .insn("BEQ", "main")
         .insn("CMP", "R0, #0x4")
         .insn("BNE", "no")                                 # not Main Phase 1/2
         .label("main")
         .insn("ADD", "R0, R4, #0x0")
         .bl(_AS_CANSS)                                     # return canSS(side)
         .insn("POP", "{R4, PC}")
         .label("no"))
        a.epilogue(ret=0)
        code = a.assemble(self.slot)
        assert_thumb1_only(code, self.slot)

        def install(rom, view):
            from otn_enhanced.effects import ss_commit_hook, tg_table
            tg_table.register_tg_handss(rom, view.buf, cid, self.slot)
            ss_commit_hook.register(rom, view.buf, cid, self.kind, self.damage)

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            from otn_enhanced.effects import ss_commit_hook, tg_table
            fins = decode_thumb(code, self.slot, overlay_data=bytes(view.buf), ram_base=view.base)
            c.eq([i.branch_target for i in fins if i.mnemonic == "BL"], [_AS_TURNLOG_QUERY, _AS_CANSS],
                 "condition BLs: turn-log query, canSS")
            c.ok(tg_table.tg_handss_ok(rom, bytearray(view.buf), cid), "registered with the hand-SS trampoline")
            c.ok(ss_commit_hook.ok(rom, view.buf, cid, self.kind, self.damage),
                 f"SS-commit row ({cid:#06x}, kind {self.kind}, {self.damage} damage) + hooks")

        return Compiled(((self.slot, code, "hand-SS condition"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class dragon_synchro_tributed_or_banished_revive_from_gy:
    """'If a face-up Dragon Synchro Monster(s) you control is Tributed or banished: You can banish this card from your
    GY, then target 1 of those monsters; Special Summon it. Once per turn.'
      hook   4-byte BL over `ldr r0,[sp,#0x44]; cmp r0,#0` at the leave dispatcher's bystander-chain head: left the
             field && face-up && yours && (Tribute bit [sp+0xC]&0x1000 || dest 0xF) && Dragon && Synchro -> remember it
             as turn-log node (side, 0x4000 | ref, kind 1) (main RAM: ov5 runtime state is wiped mid-duel), then post
             the GY poster with the departed ref (low 9 bits of desc[+0x20]) cleared so the miss-timing walk returns 0.
      cls2   {revive, 0, COND, COST, picker}; COND runs at ADMISSION (code 0x1D, zone 0xE, kind-2 clear, still in GY
             -> 2; it cannot need the target, the trigger-event log is empty then); COST = 'You can' body 0x021E50DC
             (re-runs COND), on Yes stamp kind 2 then banish this card from the GY (0x021E5708).
      crit   {cid, 0xFFFF, handler, 0x00010002}: GY + banished builders with PRED = Dragon && Synchro && node posted."""
    hook: int
    cond: int
    cost: int
    crit: int
    pred: int
    phantoms: tuple[int, int]        # (cls2, criteria)
    kind: int = 2

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import ss_commit_hook
        kind = self.kind
        a = EffectBuilder()                                 # leave hook: BL'd from the site with the dispatcher's sp
        (a
         .insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
         .insn("LDR", "R0, [SP, #0x4C]")                    # [sp+0x2C] left the field
         .insn("CMP", "R0, #0x0")
         .insn("BEQ", "done")
         .insn("LDR", "R0, [SP, #0xB4]")                    # [sp+0x94] was face-up
         .insn("CMP", "R0, #0x0")
         .insn("BEQ", "done")
         .insn("LDR", "R0, [SP, #0xB8]")                    # [sp+0x98] controller == r6: you control it
         .insn("CMP", "R0, R6")
         .insn("BNE", "done")
         .insn("LDR", "R0, [SP, #0x2C]")                    # [sp+0xC] reason flags
         .insn("MOV", "R1, #0x1")
         .insn("LSL", "R1, R1, #12")
         .insn("TST", "R0, R1")
         .insn("BNE", "why_ok")                             # Tributed
         .insn("LDR", "R0, [SP, #0x220]")                   # [sp+0x200] leave word
         .insn("LSL", "R0, R0, #9")
         .insn("LSR", "R0, R0, #28")
         .insn("CMP", "R0, #0xF")
         .insn("BNE", "done")                               # not banished
         .label("why_ok")
         .insn("ADD", "R0, R4, #0x0")
         .bl(_AS_RACE)
         .insn("CMP", "R0, #0x1")
         .insn("BNE", "done")                               # not a Dragon
         .insn("ADD", "R0, R4, #0x0")
         .bl(_AS_IS_SYNCHRO)
         .insn("CMP", "R0, #0x0")
         .insn("BEQ", "done")
         .insn("LDR", "R1, [SP, #0xBC]")                    # remember it: turn-log node key 0x4000 | ref
         .insn("MOV", "R0, #0x40")                          #   ([sp+0x9C] = the leaving card's ref)
         .insn("LSL", "R0, R0, #8")
         .insn("ORR", "R1, R0")
         .insn("ADD", "R0, R6, #0x0")
         .insn("MOV", "R2, #0x1")                           # kind 1: freed by the engine at end of turn
         .insn("MOV", "R3, #0x0")
         .bl(ss_commit_hook.TURNLOG_POST)
         .insn("ADD", "R0, R6, #0x0")
         .ldr_const(1, cid)
         .insn("LDR", "R2, [SP, #0x3C]")                    # [sp+0x1C] leave event code
         .insn("LDR", "R3, [SP, #0x220]")                   # [sp+0x200] leave word, low 9 bits (ref) cleared
         .insn("LSR", "R3, R3, #9")                         #   so the miss-timing test 0x021EE0E0 returns 0
         .insn("LSL", "R3, R3, #9")                         #   (desc[+0x20] & 0x1FF == 0 -> never misses)
         .bl(_AS_GY_POSTER)
         .label("done")
         .insn("LDR", "R0, [SP, #0x64]")                    # replay: ldr r0,[sp,#0x44] ; cmp r0,#0
         .insn("CMP", "R0, #0x0")                           # flags for the native beq @0x021C93D4
         .insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}"))
        hook = a.assemble(self.hook)

        a = EffectBuilder()                                 # cls2 +0C: runs at admission
        a.prologue(save=[R4])
        (a
         .insn("ADD", "R4, R0, #0x0")                       # desc
         .insn("LDRB", "R0, [R4, #0x4]")
         .insn("CMP", f"R0, #0x{_AS_LEAVE_CODE:X}")
         .insn("BNE", "no")
         .insn("LDRB", "R0, [R4, #0x3]")
         .insn("CMP", "R0, #0xE")
         .insn("BNE", "no")                                 # posted to the GY copy
         .insn("LDRB", "R0, [R4, #0x2]"))
        a.turnlog_query(R0, cid, kind)
        (a
         .insn("CMP", "R0, #0x0")
         .insn("BNE", "no")                                 # effect 2 used this turn
         .insn("LDRB", "R0, [R4, #0x2]")
         .insn("LDRH", "R1, [R4, #0xC]")
         .bl(_AS_GY_INDEX)
         .insn("CMP", "R0, #0x0")
         .insn("BLT", "no")                                 # no longer in the GY
         .insn("MOV", "R0, #0x2")                           # activatable; the target is chosen later (slot5)
         .insn("POP", "{R4, PC}")
         .label("no"))
        a.epilogue(ret=0)
        cond = a.assemble(self.cond)

        a = EffectBuilder()                                 # cls2 +10: Accel Synchro Stardust Dragon C1's slot4 shape
        a.prologue(save=[R4])
        (a
         .insn("ADD", "R4, R0, #0x0")
         .bl(_AS_YOU_CAN_BODY)
         .insn("CMP", "R0, #0x1")
         .insn("BNE", "out")                                # not accepted (yet): pass the phase result on
         .insn("LDRB", "R0, [R4, #0x2]"))
        a.turnlog_post(R0, cid, kind)
        (a
         .insn("ADD", "R0, R4, #0x0")
         .bl(_AS_GY_BANISH_COST)                            # returns 1
         .label("out")
         .insn("POP", "{R4, PC}"))
        cost = a.assemble(self.cost)

        a = EffectBuilder()                                 # criteria handler: GY + banished builders
        (a
         .insn("PUSH", "{R4, R5, R6, LR}")
         .insn("SUB", "SP, #0x8")
         .insn("ADD", "R5, R0, #0x0")                       # criteria row
         .insn("ADD", "R6, R1, #0x0")                       # side
         .insn("LDR", "R0, [R5, #0x8]")
         .insn("STR", "R0, [SP, #0x0]")
         .insn("MOV", "R0, #0x8")                           # GY flags (Mezuki / Infernity Reflector)
         .insn("STR", "R0, [SP, #0x4]")
         .insn("ADD", "R0, R6, #0x0")
         .insn("LDRH", "R1, [R5, #0x0]")
         .ldr_const(2, self.pred | 1)
         .insn("MOV", "R3, #0x0")
         .bl(_AS_GY_BUILDER)
         .insn("ADD", "R4, R0, #0x0")
         .insn("LDR", "R0, [R5, #0x8]")
         .insn("STR", "R0, [SP, #0x0]")
         .insn("MOV", "R0, #0xC")                           # banished flags (Miraculous Descent / D.D.R.)
         .insn("STR", "R0, [SP, #0x4]")
         .insn("ADD", "R0, R6, #0x0")
         .insn("LDRH", "R1, [R5, #0x0]")
         .ldr_const(2, self.pred | 1)
         .insn("MOV", "R3, #0x0")
         .bl(_AS_BANISHED_BUILDER)
         .insn("ADD", "R0, R0, R4")
         .insn("ADD", "SP, #0x8")
         .insn("POP", "{R4, R5, R6, PC}"))
        crit = a.assemble(self.crit)

        a = EffectBuilder()                                 # target predicate, blx'd by the builders
        (a                                                  # with [caller sp] = card-word pointer
         .insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
         .insn("LDR", "R4, [SP, #0x18]")                    # card-word pointer
         .insn("LDR", "R0, [R4, #0x0]")
         .insn("LSL", "R0, R0, #18")
         .insn("LSR", "R0, R0, #18")
         .bl(_AS_RACE)
         .insn("CMP", "R0, #0x1")
         .insn("BNE", "no")
         .insn("LDR", "R0, [R4, #0x0]")
         .insn("LSL", "R0, R0, #18")
         .insn("LSR", "R0, R0, #18")
         .bl(_AS_IS_SYNCHRO)
         .insn("CMP", "R0, #0x0")
         .insn("BEQ", "no")
         .insn("LDR", "R7, [R4, #0x0]")                     # ref = (w>>14 & 1) + ((w>>23 & 0xFF) << 1)
         .insn("LSL", "R5, R7, #17")
         .insn("LSR", "R5, R5, #31")                        # r5 = the card's side
         .insn("LSL", "R7, R7, #1")
         .insn("LSR", "R7, R7, #24")
         .insn("LSL", "R7, R7, #1")
         .insn("ADD", "R7, R5, R7")
         .insn("MOV", "R2, #0x40")                          # did the hook post (side, 0x4000 | ref, kind 1)?
         .insn("LSL", "R2, R2, #8")
         .insn("ORR", "R2, R7")
         .insn("ADD", "R0, R5, #0x0")
         .insn("MOV", "R1, #0xB")
         .insn("MOV", "R3, #0x1")
         .bl(_AS_TURNLOG_QUERY)
         .insn("CMP", "R0, #0x0")
         .insn("BNE", "yes")
         .label("no")
         .insn("MOV", "R0, #0x0")
         .insn("POP", "{R3, R4, R5, R6, R7, PC}")
         .label("yes")
         .insn("MOV", "R0, #0x1")
         .insn("POP", "{R3, R4, R5, R6, R7, PC}"))
        pred = a.assemble(self.pred)
        stubs = ((self.hook, hook, "leave hook"), (self.cond, cond, "C2 condition"), (self.cost, cost, "C2 cost"),
                 (self.crit, crit, "criteria handler"), (self.pred, pred, "target predicate"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        bl = common_bl(_AS_LEAVE_SITE, self.hook)

        def install(rom, view):
            cur = view.blob(_AS_LEAVE_SITE, 4)
            assert cur in (_AS_LEAVE_SITE_BYTES, bl), f"{_AS_LEAVE_SITE:#010x} = {cur.hex()} -- someone else hooked it"
            view.write(_AS_LEAVE_SITE, bl)

        def check(c, rom, view):
            from otn_enhanced.cards import sakitama
            # sakitama (ships later) fronts this site and tail-jumps into the hook; look through its front.
            c.eq(sakitama.unfronted(bytes(view.buf), _AS_LEAVE_SITE), bl,
                 f"{_AS_LEAVE_SITE:#010x} = BL {self.hook:#010x} (directly or via Sakitama's front)")

        ph2, phc = self.phantoms
        return Compiled(stubs,
                        (Row(CLS2, (cid, 0, _AS_REVIVE_RESOLVER, 0, self.cond | 1, self.cost | 1, _AS_OFFFIELD_PICKER), ph2),
                         Row(CRITERIA, (cid, 0xFFFF, self.crit | 1, 0x00010002), phc)),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x13AE,
    hand_special_summon_main_phase_take_damage(ov5_cave.CAVE_ASSAULT_SSCOND, damage=700),
    dragon_synchro_tributed_or_banished_revive_from_gy(
        hook=ov5_cave.CAVE_ASSAULT_LEAVEHOOK, cond=ov5_cave.CAVE_ASSAULT_C2COND, cost=ov5_cave.CAVE_ASSAULT_C2COST,
        crit=ov5_cave.CAVE_ASSAULT_C2CRIT, pred=ov5_cave.CAVE_ASSAULT_C2PRED, phantoms=(0x0E19, 0x0EAD)),
    archetype_member(SetCodeTable("Synchron", 0x0209C968, 15, (0x02023E24,), (0x02023E20,)), phantom=0x1E4E))

PROPS = card_props("DARK", "Machine", level=2, atk=700, defense=0, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_assault_synchron.nds")


def _synchron_list(out: str) -> list[int]:       # revolution_synchron reads the Synchron table through this
    import ndspy.rom
    from otn_enhanced.effects import common
    return list(common.view(ndspy.rom.NintendoDSRom.fromFile(out)).unpack(0x0209C968, "<15H"))


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

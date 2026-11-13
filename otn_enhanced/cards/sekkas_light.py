"""Sekka's Light on Stop Defense 0x10E6 (Normal Spell, keep-cid).

    If you have no Spells/Traps in your GY: Draw 2 cards, also, for the rest of this Duel after you activate this card,
    you cannot activate Spell/Trap Cards or effects, except "Sekka's Light". You can banish this card from your GY; reveal
    1 monster in your hand, shuffle it into the Deck, then, draw 1 card. You can only use each effect of "Sekka's Light"
    once per turn.

Depends on dragon_rulers (its virtual GY row table is rewritten), so it must follow Dragon Rulers in steps.STEPS.
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS0, CLS2, Compiled, Edit, Row
from otn_enhanced.effects import cave3, ov5_cave as O5
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from otn_enhanced.effects.common import ov3_bl_target as common_bl_target
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class draw_two_then_lock_spell_trap_activation_with_graveyard_reveal_and_draw:
    """'If you have no Spells/Traps in your GY: Draw 2 cards, also, for the rest of this Duel after you activate this card, you
    cannot activate Spell/Trap Cards or effects, except this card. You can banish this card from your GY; reveal 1 monster in
    your hand, shuffle it into the Deck, then, draw 1 card. You can only use each effect once per turn.' (donor: a Normal Spell)
      A  the donor's only cls0 record rewritten in place {RES, 0, COND, COST, 0}: COND = [menu check: kind-1 node absent AND no
         S/T in own GY] AND the native can-draw-2 tail; COST posts kind 1 (HOPT) + kind 5 (duel-long lock) at activation so the
         lock holds even if the draw is negated; RES = the generic draw resolver shape for 2.
      B  the lock = ONE ov3 front on all three BLs to the activation-prohibited predicate 0x021ECDA4 (the 0x021EDA2E funnel, the
         0x021D6B5C AI cleaner, the 0x021FC116 Rainbow Ruins probe): stock || (kind-5 node on the activating player && cid != the
         donor && not a monster). These gates run for EVERY card -> ov3, never ov5.
      C  cls2 {GYRES, 0, GYCOND, GYCOST, 0} over a phantom + the 6th Dragon Rulers virtual GY row (shared N-row stubs, Revolution
         Synchron's cid kept LAST). GYRES = the resolution-time hand pick with its own callback (own hand + monster): prompt 0x155,
         arm the select, pick + reveal, hand->Deck, shuffle, draw 1. GYCOST = native banish-self + kind-2 HOPT stamp.
    DEPENDS on dragon_rulers: it rewrites Rulers' ov5 GY row table and the exit/post/has stubs (read through the dragon_rulers
    module), so it must run after Dragon Rulers in STEPS."""
    cls0_stock: tuple
    lock_slot: int
    cond: int
    cost: int
    res: int
    hasmon: int
    gycond: int
    gycost: int
    cb: int
    gyres: int
    cls2_phantom: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import gy_vrow_hook as gyv
        PLAYER, STRIDE, STATE, ACT_DESC, PICK_IDX = 0x0229AC94, 0xB3C, 0x0229AAFC, 0x0229A9FC, 0x0229DE14
        TLQ, TLP, COPY_EXEMPT, CAN_DRAW, DRAW = 0x021A14E9, 0x021D2585, 0x021D2B89, 0x021BAE31, 0x021D12F5
        IS_SPELL, IS_TRAP, IS_MONSTER, BANISH_SELF = 0x02022FC9, 0x02022FDD, 0x02029E61, 0x021E5709
        PROMPT, MSG_REVEAL, SELECT, SELECT_DONE, REVEAL, HAND_TO_DECK, SHUFFLE = 0x0219A819, 0x155, 0x0224B9F1, 0x0224BBB1, 0x021D2599, 0x021C6989, 0x021D26CD
        PREDICATE, LOCK_SITES = 0x021ECDA4, (0x021EDA2E, 0x021D6B5C, 0x021FC116)
        K1, K2, K_LOCK = 1, 2, 5

        def side(b, dst, desc):
            b.insn("LDRB", f"R{dst}, [R{desc}, #0x2]")
            b.insn("LDRB", "R0, [R%d, #0x6]" % desc)
            b.insn("EOR", f"R{dst}, R0")

        def call3(b, addr):
            b.ldr_const(3, addr)
            b.insn("BLX", "R3")

        def post(b, kinds):
            for k in kinds:
                b.insn("ADD", "R0, R5, #0x0")
                b.ldr_const(1, cid)
                b.insn("MOV", f"R2, #0x{k:X}")
                b.insn("MOV", "R3, #0x0")
                b.ldr_const(4, TLP)
                b.insn("BLX", "R4")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.bl(PREDICATE)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "out")
        b.insn("LDRH", "R0, [R4, #0x0]")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "zero")
        b.bl(IS_MONSTER & ~1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "zero")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRB", "R1, [R4, #0x6]")
        b.insn("EOR", "R0, R1")
        b.insn("MOV", "R1, #0xB")
        b.ldr_const(2, cid)
        b.insn("MOV", f"R3, #0x{K_LOCK:X}")
        b.bl(TLQ & ~1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        b.label("zero")
        b.insn("MOV", "R0, #0x0")
        b.label("out")
        b.insn("POP", "{R4, PC}")
        lock = b.assemble(self.lock_slot, pad="nop")

        b = EffectBuilder()          # cls0 +0C: menu check only (desc[+7] == 0): kind-1 node absent, no S/T in own GY; always can draw 2
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        side(b, 5, 4)
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "draw")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0xB")
        b.ldr_const(2, cid)
        b.insn("MOV", f"R3, #0x{K1:X}")
        b.ldr_const(6, TLQ)
        b.insn("BLX", "R6")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R0, R5")
        b.ldr_const(1, STRIDE)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, PLAYER)
        b.insn("ADD", "R6, R0, R1")
        b.insn("LDR", "R7, [R6, #0x14]")
        b.ldr_const(1, 0x55C)
        b.insn("ADD", "R6, R6, R1")
        b.label("gy")
        b.insn("CMP", "R7, #0x0")
        b.insn("BEQ", "draw")
        b.insn("SUB", "R7, #0x1")
        b.insn("LSL", "R0, R7, #0x2")
        b.insn("LDR", "R0, [R6, R0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R4, R0, #0x12")
        b.insn("ADD", "R0, R4, #0x0")
        call3(b, IS_SPELL)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("ADD", "R0, R4, #0x0")
        call3(b, IS_TRAP)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("B", "gy")
        b.label("draw")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x2")
        call3(b, CAN_DRAW)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()          # cls0 +10: stamp HOPT kind 1 + the duel-long lock kind 5 (skipped in a replay)
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        call3(b, COPY_EXEMPT)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        side(b, 5, 4)
        post(b, (K1, K_LOCK))
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, PC}")
        cost = b.assemble(self.cost, pad="nop")

        b = EffectBuilder()          # cls0 +04: draw 2 (0x022065B8 shape without its per-cid count table)
        b.insn("PUSH", "{R4, LR}")
        side(b, 4, 0)
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("MOV", "R1, #0x2")
        call3(b, DRAW)
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        res = b.assemble(self.res, pad="nop")

        b = EffectBuilder()          # (side) -> 1 iff side's hand holds a monster
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.ldr_const(1, STRIDE)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, PLAYER)
        b.insn("ADD", "R4, R0, R1")
        b.insn("LDR", "R5, [R4, #0xC]")
        b.ldr_const(1, 0x124)
        b.insn("ADD", "R4, R4, R1")
        b.label("loop")
        b.insn("CMP", "R5, #0x0")
        b.insn("BEQ", "none")
        b.insn("SUB", "R5, #0x1")
        b.insn("LSL", "R0, R5, #0x2")
        b.insn("LDR", "R0, [R4, R0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        call3(b, IS_MONSTER)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "loop")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, PC}")
        b.label("none")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        hasmon = b.assemble(self.hasmon, pad="nop")

        b = EffectBuilder()          # cls2 +0C: menu check -> kind-2 node absent; always a monster in hand
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        side(b, 5, 4)
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "hand")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0xB")
        b.ldr_const(2, cid)
        b.insn("MOV", f"R3, #0x{K2:X}")
        b.ldr_const(4, TLQ)
        b.insn("BLX", "R4")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.label("hand")
        b.insn("ADD", "R0, R5, #0x0")
        call3(b, self.hasmon | 1)
        b.insn("POP", "{R4, R5, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        gycond = b.assemble(self.gycond, pad="nop")

        b = EffectBuilder()          # cls2 +10: native banish-self, then stamp HOPT kind 2 (skipped in a replay)
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        call3(b, BANISH_SELF)
        b.insn("ADD", "R0, R4, #0x0")
        call3(b, COPY_EXEMPT)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        side(b, 5, 4)
        post(b, (K2,))
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, PC}")
        gycost = b.assemble(self.gycost, pad="nop")

        b = EffectBuilder()          # 0x0224B9F0 filter (side, zone, idx) -> 0x800: acting player's own HAND and a monster
        b.insn("PUSH", "{R4, LR}")
        b.ldr_const(3, ACT_DESC)
        b.insn("LDR", "R3, [R3, #0x50]")
        b.insn("LDRB", "R4, [R3, #0x2]")
        b.insn("LDRB", "R3, [R3, #0x6]")
        b.insn("EOR", "R4, R3")
        b.insn("CMP", "R0, R4")
        b.insn("BNE", "no")
        b.insn("CMP", "R1, #0xB")
        b.insn("BNE", "no")
        b.insn("MOV", "R3, #0x1")
        b.insn("AND", "R0, R3")
        b.ldr_const(3, STRIDE)
        b.insn("MUL", "R0, R3")
        b.ldr_const(3, PLAYER + 0x124)
        b.insn("ADD", "R0, R0, R3")
        b.insn("LSL", "R2, R2, #0x2")
        b.insn("LDR", "R0, [R0, R2]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        call3(b, IS_MONSTER)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("MOV", "R0, #0x2")
        b.insn("LSL", "R0, R0, #0xA")
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cb = b.assemble(self.cb, pad="nop")

        b = EffectBuilder()          # cls2 +04, phase [STATE+0x70]; [STATE+0x74] = picked hand index
        pop = "{R4, R5, R6, R7, PC}"
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        side(b, 5, 4)
        b.ldr_const(6, STATE)
        b.insn("LDR", "R0, [R6, #0x70]")
        for ph in (0x80, 0x7F, 0x7E, 0x7D, 0x7C, 0x7B):
            b.insn("CMP", f"R0, #0x{ph:X}")
            b.insn("BEQ", f"p{ph:x}")
        b.insn("B", "zero")
        b.label("p80")
        b.insn("ADD", "R0, R5, #0x0")
        call3(b, self.hasmon | 1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "zero")
        b.insn("ADD", "R0, R5, #0x0")
        b.ldr_const(1, MSG_REVEAL)
        call3(b, PROMPT)
        b.insn("MOV", "R0, #0x7F")
        b.insn("POP", pop)
        b.label("p7f")
        b.insn("ADD", "R0, R5, #0x0")
        b.ldr_const(1, cid)
        b.insn("MOV", "R2, #0x0")
        b.ldr_const(3, self.cb | 1)
        b.ldr_const(7, SELECT)
        b.insn("BLX", "R7")
        b.insn("MOV", "R0, #0x7E")
        b.insn("POP", pop)
        b.label("p7e")
        call3(b, SELECT_DONE)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "picked")
        b.insn("MOV", "R0, #0x7F")
        b.insn("POP", pop)
        b.label("picked")
        b.ldr_const(0, PICK_IDX)
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("STR", "R0, [R6, #0x74]")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R1, R5")
        b.ldr_const(2, STRIDE)
        b.insn("MUL", "R1, R2")
        b.ldr_const(2, PLAYER + 0x124)
        b.insn("ADD", "R1, R1, R2")
        b.insn("LSL", "R0, R0, #0x2")
        b.insn("LDR", "R2, [R1, R0]")
        b.insn("LSL", "R0, R2, #0x11")
        b.insn("LSR", "R0, R0, #0x1F")
        b.insn("LSL", "R2, R2, #0x1")
        b.insn("LSR", "R2, R2, #0x18")
        b.insn("LSL", "R2, R2, #0x1")
        b.insn("ADD", "R1, R0, R2")
        b.insn("STRH", "R1, [R4, #0x14]")
        b.insn("ADD", "R0, R5, #0x0")
        call3(b, REVEAL)
        b.insn("MOV", "R0, #0x7D")
        b.insn("POP", pop)
        b.label("p7d")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDR", "R1, [R6, #0x74]")
        b.insn("MOV", "R2, #0x0")
        call3(b, HAND_TO_DECK)
        b.insn("MOV", "R0, #0x7C")
        b.insn("POP", pop)
        b.label("p7c")
        call3(b, SHUFFLE)
        b.insn("MOV", "R0, #0x7B")
        b.insn("POP", pop)
        b.label("p7b")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x1")
        call3(b, DRAW)
        b.label("zero")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", pop)
        gyres = b.assemble(self.gyres, pad="nop")
        stubs = ((self.lock_slot, lock, "S/T lock front"), (self.cond, cond, "cls0 cond"), (self.cost, cost, "cls0 cost"),
                 (self.res, res, "cls0 res"), (self.hasmon, hasmon, "hand has monster"), (self.gycond, gycond, "GY cond"),
                 (self.gycost, gycost, "GY cost"), (self.cb, cb, "hand select callback"), (self.gyres, gyres, "GY resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        gy_row = (cid,) + tuple(gyv.GY_FAMILY)
        patched = (cid, self.res | 1, 0, self.cond | 1, self.cost | 1, 0)

        def gy_blobs(with_me):
            from otn_enhanced.cards import dragon_rulers as rul
            rul.EXTRA_GY_ROWS = []              # Rulers' own rows only (its verify() may have read ours)
            rws = rul._gy_rows() + ([gy_row] if with_me else [])
            cids = [r[0] for r in rws]
            if rul.REV_PRESENT:
                cids = cids[1:] + cids[:1]       # Revolution's cid LAST
            table = b"".join(struct.pack("<4I", *r) for r in rws)
            return [(ov5_cave.CAVE_RUL_GYROWS, 0x60, table),
                    (ov5_cave.CAVE_RUL_GYFETCH, 0x20, gyv.gyfetch_stub(ov5_cave.CAVE_RUL_GYFETCH, ov5_cave.CAVE_RUL_GYROWS)),
                    (ov5_cave.CAVE_RUL_GYEXIT, 0x20, gyv.gyexit_stub(ov5_cave.CAVE_RUL_GYEXIT, len(rws))),
                    (ov5_cave.CAVE_RUL_GYPOST, 0x60, gyv.gypost_stub(ov5_cave.CAVE_RUL_GYPOST, cids)),
                    (ov5_cave.CAVE_RUL_GYHAS, 0x50, gyv.gyhas_stub(ov5_cave.CAVE_RUL_GYHAS, cids))]

        def install(rom, view):
            from otn_enhanced.cards import dragon_rulers as rul
            for site in LOCK_SITES:
                cur = common_bl_target(view.buf, site)
                assert cur in (PREDICATE, self.lock_slot), f"site {site:#x} calls {cur:#x}, not the predicate"
                view.write(site, common_bl(site, self.lock_slot))
            rul.REV_PRESENT = rul._rev_present(rom)
            assert rul.REV_PRESENT, "Revolution Synchron's virtual GY row missing -- not a chain ROM?"
            for (a, r, old), (_a, _r, new) in zip(gy_blobs(False), gy_blobs(True)):
                if a != ov5_cave.CAVE_RUL_GYROWS:
                    assert_thumb1_only(new, a)
                assert len(new) <= r, f"{a:#x}: {len(new):#x} B > reserve {r:#x}"
                cur = ov5_cave.read_cave(rom, a, r)
                if cur[:len(new)] == new and not any(cur[len(new):]):
                    continue
                assert cur[:len(old)] == old and not any(cur[len(old):]), f"ov5 {a:#x} is not Dragon Rulers' stock blob"
                ov5 = ov5_cave._load_ov5_decompressed(rom)
                data = bytearray(ov5.data)
                o = a - ov5_cave.OV5_RAM_BASE
                data[o:o + r] = new + bytes(r - len(new))
                ov5_cave._save_ov5(rom, ov5, bytes(data))

        def check(c, rom, view):
            from otn_enhanced.cards import dragon_rulers as rul
            rul.REV_PRESENT = rul._rev_present(rom)
            c.ok(all(code_reaches(rom, s, self.lock_slot) for s in LOCK_SITES), "all 3 predicate BLs reach the lock front")
            c.ok(all(ov5_cave.read_cave(rom, a, len(bl)) == bl for a, _r, bl in gy_blobs(True)),
                 "virtual GY rows + stubs (Rulers' rows kept, this card appended)")

        return Compiled(stubs,
                        (Row(CLS2, (cid, 0, self.gyres | 1, 0, self.gycond | 1, self.gycost | 1, 0), self.cls2_phantom),),
                        (Edit(CLS0, cid, self.cls0_stock, patched),),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x10E6,
    draw_two_then_lock_spell_trap_activation_with_graveyard_reveal_and_draw(
        cls0_stock=(0x10E6, 0x022076A5, 0x021D883D, 0, 0, 0x02234E01),     # Stop Defense's only record
        lock_slot=cave3.CAVE3_SEKKA_LOCK, cond=O5.CAVE_SEKKA_COND, cost=O5.CAVE_SEKKA_COST, res=O5.CAVE_SEKKA_RES,
        hasmon=O5.CAVE_SEKKA_HASMON, gycond=O5.CAVE_SEKKA_GYCOND, gycost=O5.CAVE_SEKKA_GYCOST, cb=O5.CAVE_SEKKA_CB,
        gyres=O5.CAVE_SEKKA_GYRES, cls2_phantom=0x1B47))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_sekkas_light.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

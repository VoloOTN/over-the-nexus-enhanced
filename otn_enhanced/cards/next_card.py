"""NEXT on Return Soul 0x1B22 (Normal Trap, keep-cid).

    Special Summon any number of monsters with different names from your hand and/or GY, in Defense Position, that are
    all "Neo-Spacian" monsters or "Elemental HERO Neos", but negate their effects. You can only activate 1 "NEXT" per turn.
    If you control no cards, you can activate this card from your hand.

(The 'no Extra Deck Summon except Fusion' clause is dropped by user decision.)
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.cards.neo_space_connector import NSC_CIDS, _assert_filter_source      # the live Neo-Spacian list + Neos
from otn_enhanced.dsl import card, CLS0, CRITERIA, Compiled, Edit
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from otn_enhanced.effects.common import ov3_bl_target as common_bl_target
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class trap_summon_group_monsters_from_hand_and_gy_negated_once_per_turn_from_hand_if_no_cards:
    """'Special Summon any number of monsters with different names from your hand and/or GY, in Defense Position, that are all
    <group> monsters, but negate their effects. You can only activate 1 per turn. If you control no cards, you can activate this
    card from your hand.' (donor: a Normal Trap; the 'extra Deck Summon' clause was dropped by user decision.)
      A  cls0 rewritten in place {RES, 0, COND, COST, 0}: COND = turn node clear (skipped on the desc[+7] re-check) AND a free
         Monster Zone AND a listed cid in own hand / GY (a DIRECT scan of the cid table); COST posts the turn node at activation;
         RES = Giant Germ's resolver shape, ONE summon per phase re-entry: 0x80 SS gates / clear USED / any candidate? else
         message 0x0D -> 0x7A; 0x7F message -> 0x7E picker -> 0x7D readback, set the picked cid's USED bit, commit (position 1 =
         DEF) -> 0x7C free zone && candidates left -> Yes/No after each -> 0x7B -> again or end (clear USED, 0x64, stop).
      B  criteria row {cid, 0xFFFF, CRIT, 0x00010002} rewritten in place: CRIT = hand builder + GY builder in one buffer.
      P  PRED: cid in the table AND its USED bit clear (USED = u32 runtime mask in the ov5 data blob, TABLE = the cid list).
      N  C2 = the native Level Modulation recipe: two lists are full, so each `bl` (0x021EE418 negate reader, 0x02268090 summon
         kind-2 poster) gets a donor pre-check hosted in the donor's own DEAD native cond (0x18 B) / criteria handler (0x20 B) in
         ov3, tail-calling the bl's CURRENT target (stock bsearch; in the chain Obedience Schooled's stubs).
      H  C5 = a Trap-from-hand gate: the site in 0x021EC93C's hand-Trap path becomes `bl HANDGATE ; adds r4,r0,#0 ; b ret`;
         HANDGATE (ov3: it runs for every Trap in hand) redoes Delta Crow's arm verbatim and adds donor && 'you control no
         cards' (Gorz's count)."""
    group: tuple
    data: int
    pred: int
    crit: int
    cond: int
    cost: int
    res: int
    handgate: int
    cls0_stock: tuple
    crit_stock: tuple
    word: int
    hosts: dict                  # ov3 host -> (reserve, stock sha256[:16])
    hooks: tuple                 # ((site, host, label), ...)

    def compile(self, view, cid) -> Compiled:
        import hashlib
        N = len(self.group)
        HAND_B, GY_B, ONCE, COPYX, FREE_ZONE = 0x0223C16D, 0x0223C4E9, 0x021F6DD9, 0x021D2B89, 0x021AD871
        GATE_B, GATE_C, CANDS, MSG, PICKER, READBACK, SS_COMMIT = 0x021B9ECD, 0x021B9ED9, 0x02243FA9, 0x0219A819, 0x0219C431, 0x0219C511, 0x0226925D
        YESNO, CLEANUP, PHASE, UI = 0x0219AAB9, 0x0225BF31, 0x0229AAFC, 0x0229DD94
        PLAYER, STRIDE, HAND_COUNT, HAND_ARRAY, GY_COUNT, GY_ARRAY = 0x0229AC94, 0xB3C, 0xC, 0x124, 0x14, 0x55C
        SITE, RET = 0x021ECAA0, 0x021ECAB6
        SITE_STOCK = bytes.fromhex("29885a48814206d1a8785949c0f780fa032800d10124")
        DELTA_CROW, BLACKWING_THUNK, COUNT_SET, COUNT_CARDS, BSEARCH = 0x201C, 0x02023D09, 0x021ACFB0, 0x021ACF28, 0x02022E14
        USED, TABLE = self.data, self.data + 4
        pred_p = self.pred | 1
        data = struct.pack("<I", 0) + struct.pack(f"<{N}H", *self.group)

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDR", "R0, [SP, #0x8]")
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.ldr_const(3, TABLE)
        b.insn("MOV", "R2, #0x0")
        b.label("loop")
        b.insn("LDRH", "R1, [R3, R2]")
        b.insn("CMP", "R1, R0")
        b.insn("BEQ", "hit")
        b.insn("ADD", "R2, #0x2")
        b.insn("CMP", f"R2, #0x{2 * N:X}")
        b.insn("BLT", "loop")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        b.label("hit")
        b.insn("LSR", "R2, R2, #0x1")
        b.ldr_const(3, USED)
        b.insn("LDR", "R3, [R3, #0x0]")
        b.insn("LSR", "R3, R2")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R3, R0")
        b.insn("BNE", "no")
        b.insn("POP", "{R4, PC}")
        pred = b.assemble(self.pred, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R4, R1, #0x0")
        b.insn("MOV", "R0, #0xE")
        b.insn("STR", "R0, [SP, #0x8]")
        b.insn("ADD", "R7, SP, #0x8")
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.ldr_const(2, pred_p)
        b.call_addr(HAND_B, R0, R1, R2, R7, via=R6)
        b.ldr_const(0, 0x10002)
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x8")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.ldr_const(2, pred_p)
        b.call_addr(GY_B, R0, R1, R2, 0, via=R6)
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        crit = b.assemble(self.crit, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "zones")
        b.call_addr(ONCE, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.label("zones")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRB", "R1, [R4, #0x6]")
        b.insn("EOR", "R0, R1")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(FREE_ZONE, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.ldr_const(5, PLAYER)
        b.insn("CMP", "R4, #0x0")
        b.insn("BEQ", "side0")
        b.ldr_const(1, STRIDE)
        b.insn("ADD", "R5, R5, R1")
        b.label("side0")
        b.insn("LDR", f"R6, [R5, #0x{HAND_COUNT:X}]")
        b.ldr_const(7, HAND_ARRAY)
        b.insn("ADD", "R7, R5, R7")
        b.bl_label("scan")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.insn("LDR", f"R6, [R5, #0x{GY_COUNT:X}]")
        b.ldr_const(7, GY_ARRAY)
        b.insn("ADD", "R7, R5, R7")
        b.bl_label("scan")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("scan")
        b.insn("CMP", "R6, #0x0")
        b.insn("BLE", "snone")
        b.insn("LDR", "R0, [R7, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.ldr_const(3, TABLE)
        b.insn("MOV", "R2, #0x0")
        b.label("tloop")
        b.insn("LDRH", "R1, [R3, R2]")
        b.insn("CMP", "R1, R0")
        b.insn("BEQ", "shit")
        b.insn("ADD", "R2, #0x2")
        b.insn("CMP", f"R2, #0x{2 * N:X}")
        b.insn("BLT", "tloop")
        b.insn("ADD", "R7, #0x4")
        b.insn("SUB", "R6, #0x1")
        b.insn("B", "scan")
        b.label("shit")
        b.insn("MOV", "R0, #0x1")
        b.insn("BX", "LR")
        b.label("snone")
        b.insn("MOV", "R0, #0x0")
        b.insn("BX", "LR")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(COPYX, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.turnlog_post(R0, R1, 1, via=R4)
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        cost = b.assemble(self.cost, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R6, [R5, #0x2]")
        b.insn("LDRB", "R0, [R5, #0x6]")
        b.insn("EOR", "R6, R0")
        b.ldr_const(4, PHASE)
        b.insn("LDR", "R4, [R4, #0x70]")
        for ph, lab in ((0x80, "ph80"), (0x7F, "ph7f"), (0x7E, "ph7e"), (0x7D, "ph7d"), (0x7C, "ph7c"), (0x7B, "ph7b"), (0x7A, "ph7a")):
            b.insn("CMP", f"R4, #0x{ph:X}")
            b.insn("BEQ", lab)
        b.insn("B", "stop")
        b.label("ph80")
        for gate in (FREE_ZONE, GATE_B, GATE_C):
            b.call_addr(gate, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
        b.bl_label("clear")
        b.bl_label("count")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "again")
        b.call_addr(MSG, R6, 0xD, via=R3)
        b.insn("MOV", "R0, #0x7A")
        b.insn("B", "ret")
        b.label("ph7f")
        b.call_addr(MSG, R6, 0x30, via=R3)
        b.insn("MOV", "R0, #0x7E")
        b.insn("B", "ret")
        b.label("ph7e")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("MOV", "R1, #0x6")
        b.insn("LDRH", "R2, [R5, #0x0]")
        b.call_addr(PICKER, R0, R1, R2, 0, via=R7)
        b.insn("MOV", "R0, #0x7D")
        b.insn("B", "ret")
        b.label("ph7d")
        b.call_addr(READBACK, via=R7)
        b.insn("ADD", "R7, R0, #0x0")
        b.insn("LDR", "R0, [R7, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.ldr_const(3, TABLE)
        b.insn("MOV", "R2, #0x0")
        b.label("mloop")
        b.insn("LDRH", "R1, [R3, R2]")
        b.insn("CMP", "R1, R0")
        b.insn("BEQ", "mark")
        b.insn("ADD", "R2, #0x2")
        b.insn("CMP", f"R2, #0x{2 * N:X}")
        b.insn("BLT", "mloop")
        b.insn("B", "commit")
        b.label("mark")
        b.insn("LSR", "R2, R2, #0x1")
        b.insn("MOV", "R1, #0x1")
        b.insn("LSL", "R1, R2")
        b.ldr_const(3, USED)
        b.insn("LDR", "R2, [R3, #0x0]")
        b.insn("ORR", "R2, R1")
        b.insn("STR", "R2, [R3, #0x0]")
        b.label("commit")
        b.insn("LDRH", "R0, [R5, #0x0]")
        b.insn("LSL", "R0, R0, #0x10")
        b.insn("STR", "R0, [SP, #0x0]")
        b.call_addr(SS_COMMIT, R6, R7, 1, 1, via=R7)
        b.insn("MOV", "R0, #0x7C")
        b.insn("B", "ret")
        b.label("ph7c")
        b.call_addr(FREE_ZONE, R6, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "finish")
        b.bl_label("count")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "finish")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x35")
        b.insn("LDRH", "R2, [R5, #0xC]")
        b.call_addr(YESNO, via=R3)
        b.insn("MOV", "R0, #0x7B")
        b.insn("B", "ret")
        b.label("ph7b")
        b.ldr_const(0, UI)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "finish")
        b.label("again")
        b.insn("MOV", "R0, #0x7F")
        b.insn("B", "ret")
        b.label("ph7a")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R0, R0, R6")
        b.call_addr(CLEANUP, via=R3)
        b.label("finish")
        b.bl_label("clear")
        b.insn("MOV", "R0, #0x64")
        b.insn("B", "ret")
        b.label("stop")
        b.insn("MOV", "R0, #0x0")
        b.label("ret")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("clear")
        b.ldr_const(3, USED)
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [R3, #0x0]")
        b.insn("BX", "LR")
        b.label("count")
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.call_addr(CANDS, R0, R1, 0, via=R3)
        b.insn("POP", "{R4, PC}")
        res = b.assemble(self.res, pad="nop")

        def precheck(base, tail):
            b = EffectBuilder()
            b.ldr_const(3, cid)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "miss")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("miss")
            b.ldr_const(3, tail | 1)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")

        def stub_tail(buf, host):
            n = len(precheck(host, BSEARCH))
            return struct.unpack_from("<I", buf, host - 0x02141700 + n - 4)[0] & ~1

        b = EffectBuilder()          # bl'd from SITE with r5 = desc, r4 = the permission so far; returns the new permission
        b.insn("PUSH", "{LR}")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.ldr_const(0, DELTA_CROW)
        b.insn("CMP", "R1, R0")
        b.insn("BNE", "nxt")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.ldr_const(1, BLACKWING_THUNK)
        b.bl(COUNT_SET)
        b.insn("CMP", "R0, #0x3")
        b.insn("BEQ", "yes")
        b.insn("B", "keep")
        b.label("nxt")
        b.ldr_const(0, cid)
        b.insn("CMP", "R1, R0")
        b.insn("BNE", "keep")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.bl(COUNT_CARDS)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "keep")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{PC}")
        b.label("keep")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("POP", "{PC}")
        handgate = b.assemble(self.handgate, pad="nop")
        b_off = (RET - (SITE + 6 + 4)) >> 1
        assert 0 <= b_off < 0x400
        site_new = common_bl(SITE, self.handgate) + struct.pack("<HH", 0x1C04, 0xE000 | b_off)

        stubs = ((self.data, data, "cid table + USED word"), (self.pred, pred, "PRED"), (self.crit, crit, "criteria handler"),
                 (self.cond, cond, "COND"), (self.cost, cost, "COST"), (self.res, res, "RES"),
                 (self.handgate, handgate, "hand-activation gate"))
        for addr, blob, what in stubs:
            if addr != self.data:
                assert_thumb1_only(blob, addr)
        for a_ in (HAND_B, GY_B, ONCE, COPYX, FREE_ZONE, GATE_B, GATE_C, CANDS, MSG, PICKER, READBACK, SS_COMMIT, YESNO, CLEANUP):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        cls0_new = (cid, self.res | 1, 0, self.cond | 1, self.cost | 1, 0)
        crit_new = (cid, 0xFFFF, self.crit | 1, self.word)

        def install(rom, view):
            for site, host, label in self.hooks:
                reserve, sha = self.hosts[host]
                cur = common_bl_target(view.buf, site)
                if cur == host:
                    tail = stub_tail(view.buf, host)                 # idempotent re-run
                else:
                    body = view.blob(host, reserve)
                    assert hashlib.sha256(body).hexdigest()[:16] == sha, f"{label}: ov3 host {host:#x} is not stock"
                    tail = cur
                assert tail not in self.hosts, f"{label}: tail {tail:#x} would loop"
                blob = precheck(host, tail)
                assert_thumb1_only(blob, host)
                assert len(blob) <= reserve, f"{label}: {len(blob)} B > {reserve:#x}"
                view.write(host, blob + bytes(reserve - len(blob)))
                view.write(site, common_bl(site, host))
            cur = view.blob(SITE, len(SITE_STOCK))
            assert cur == SITE_STOCK or cur[:len(site_new)] == site_new, f"hand-gate site @{SITE:#x} not stock: {cur.hex()}"
            view.write(SITE, site_new)

        def check(c, rom, view):
            for site, host, label in self.hooks:
                c.ok(code_reaches(rom, site, host), f"{label}: bl @{site:#x} reaches {host:#x}")
                tail = stub_tail(view.buf, host)
                reserve = self.hosts[host][0]
                pc = precheck(host, tail)
                c.ok(tail not in self.hosts and view.blob(host, reserve) == pc + bytes(reserve - len(pc)),
                     f"{label}: precheck installed, tail {tail:#x}")
            c.eq(view.blob(SITE, 8), site_new, f"hand-gate site @{SITE:#x} = bl front ; adds r4,r0 ; b ret")

        return Compiled(stubs, (),
                        (Edit(CLS0, cid, self.cls0_stock, cls0_new), Edit(CRITERIA, cid, self.crit_stock, crit_new)),
                        installs=(install,), checks=(check,))



NEGR, EPL = 0x021FBC94, 0x0223F8E4      # ov3 hosts: Return Soul's own dead native cond / criteria handler

SPEC = card(
    0x1B22,
    trap_summon_group_monsters_from_hand_and_gy_negated_once_per_turn_from_hand_if_no_cards(
        group=NSC_CIDS, data=ov5_cave.CAVE_NEXT_DATA, pred=ov5_cave.CAVE_NEXT_PRED, crit=ov5_cave.CAVE_NEXT_CRIT,
        cond=ov5_cave.CAVE_NEXT_COND, cost=ov5_cave.CAVE_NEXT_COST, res=ov5_cave.CAVE_NEXT_RES,
        handgate=cave3.CAVE3_NEXT_HANDGATE,
        cls0_stock=(0x1B22, 0x022197B9, 0, 0x021FBC95, 0, 0x02235701),
        crit_stock=(0x1B22, 0xFFFF, 0x0223F8E5, 0x00010002), word=0x00010002,
        hosts={NEGR: (0x18, "6003fd1cfdf83a43"), EPL: (0x20, "fd51549802e1ac27")},
        hooks=((0x021EE418, NEGR, "N  negate reader list 0x0226FAB4"),
               (0x02268090, EPL, "N  summon kind-2 poster list 0x0228F708"))))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_next.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

"""Obedience Schooled on Abyssal Designator 0x17F4 (Normal Spell, keep-cid).

    If you control no monsters: Special Summon 3 Level 2 or lower Beast-Type Effect Monsters with different names from
    your Deck. Their effects are negated, and they are destroyed during the End Phase. If you activate this card, you
    cannot Special Summon for the rest of this turn, except Beast-Type monsters. You can only activate 1 "Obedience
    Schooled" per turn.
"""
import struct
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS0, CRITERIA, Compiled, Edit
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from otn_enhanced.effects.common import ov3_bl_target as common_bl_target
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave


@dataclass(frozen=True)
class special_summon_three_beasts_negated_destroyed_at_end_phase:
    """'If you control no monsters: Special Summon 3 Level 2 or lower Beast-Type Effect Monsters with different names
    from your Deck. Their effects are negated, and they are destroyed during the End Phase. If you activate this card, you
    cannot Special Summon for the rest of this turn, except Beast-Type monsters.' (donor: a Normal Spell)
      cls0 + criteria row + LP-cost row rewritten IN PLACE (the donor's 1000 LP cost is zeroed: the getter is reachable from
      generic code). ov5: PRED (Effect Monster, name not already picked), HANDLER (native Deck handler + PRED, the param packs
      the names already summoned), COND (canSS, no monsters, 3 greedy distinct-name COUNTs), RES (pick / exclude / summon loop).
      C3 = the native Level Modulation recipe: the summon-event prologue posts a kind-2 node {key = SOURCE cid} iff the source
      is in list 0x0228F708 (bl @0x02268090), the negate reader honours it iff its key is in 0x0226FAB4 (bl @0x021EE418), and
      End-Phase registry fn 0x02254E95 destroys monsters carrying the node (row 249). Both lists are full and each bl already
      goes to a later card's chain stub, so each gets a donor pre-check that tail-calls the current target.
      C4 = Baby Raccoon Ponpoko's recipe: COST posts the turn-log node once per activation; LOCK replaces `bl 0x021BA1E8` @0x021BA368
      inside the SS-only gate 0x021BA258: deny iff the node exists and the cid is not a Beast.
      ov3 host (puzzle-safe): the donor's own selector body, dead once the cls0 rewrite drops its only pointer."""
    cls0_native: tuple
    crit_native: tuple
    word: int                        # Beast, Lv<=2, monster
    lp_row: int
    pred: int
    handler: int
    cond: int
    res: int
    host: int                        # ov3 dead body start; stubs at +0 / +0x18 / +0x30 / +0x70
    host_end: int
    host_sha16: str
    neg_target: int                  # current target of the negate-reader bl
    epl_target: int                  # current target of the summon kind-2 list bl
    registry_row: int
    registry_native: tuple
    n: int = 3

    def compile(self, view, cid) -> Compiled:
        import hashlib
        N, SHIFT = self.n, 14
        CARD_TYPE, SAME_NAME, DECK_B, COUNT, CAND = 0x0202ABF9, 0x02022E99, 0x0223BC3D, 0x02243FA9, 0x02299458
        MAY_SS, FREE_ZONE, MON_COUNT, STATE = 0x021AD871, 0x021B9ECD, 0x021ACF69, 0x0229AAFC
        MESSAGE, PICKER, READBACK, CPUSH, CPOP = 0x0219A819, 0x0219C431, 0x0219C511, 0x021D28A5, 0x021D2965
        SUMMON, SHUFFLE, MSG_SS = 0x02269315, 0x021D269D, 0x11D
        SS_LEVEL, NODE_QUERY, BEAST = 0x021BA1E8, 0x021A1431, 11
        negr, epl, lock, cost_a = self.host, self.host + 0x18, self.host + 0x30, self.host + 0x70
        reserve3 = {negr: 0x18, epl: 0x18, lock: 0x40, cost_a: 0x20}

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("LDR", "R0, [SP, #0x10]")
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R4, R0, #0x12")
        b.insn("LDR", "R0, [SP, #0x14]")
        b.insn("LDR", "R5, [R0, #0x0]")
        b.call_addr(CARD_TYPE, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("CMP", "R0, #0xF")
        b.insn("BEQ", "no")
        b.insn("MOV", "R6, #0x0")
        b.label("lp")
        b.insn("LSL", "R1, R5, #0x12")
        b.insn("LSR", "R1, R1, #0x12")
        b.insn("CMP", "R1, #0x0")
        b.insn("BEQ", "nx")
        b.call_addr(SAME_NAME, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.label("nx")
        b.insn("LSR", f"R5, R5, #0x{SHIFT:X}")
        b.insn("ADD", "R6, #0x1")
        b.insn("CMP", "R6, #0x2")
        b.insn("BLT", "lp")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        pred = b.assemble(self.pred, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("SUB", "SP, #0x10")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("STR", "R2, [SP, #0x8]")
        b.insn("LDR", "R0, [R4, #0x8]")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0xA")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R1, #0x0")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.ldr_const(2, self.pred | 1)
        b.insn("ADD", "R3, SP, #0x8")
        b.call_addr(DECK_B, via=R4)
        b.insn("ADD", "SP, #0x10")
        b.insn("POP", "{R4, PC}")
        handler = b.assemble(self.handler, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.insn("LDRB", "R5, [R4, #0x2]")
        b.insn("LDRB", "R0, [R4, #0x6]")
        b.insn("EOR", "R5, R0")
        b.call_addr(MAY_SS, R5, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.call_addr(MON_COUNT, R5, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("MOV", "R6, #0x0")
        b.insn("MOV", "R7, #0x0")
        b.label("lp")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.call_addr(COUNT, R0, R1, R6, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "no")
        b.insn("CMP", f"R7, #0x{N - 1:X}")
        b.insn("BGE", "yes")
        b.ldr_const(0, CAND)
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.insn("CMP", "R7, #0x0")
        b.insn("BEQ", "first")
        b.insn("LSL", f"R0, R0, #0x{SHIFT:X}")
        b.label("first")
        b.insn("ORR", "R6, R0")
        b.insn("ADD", "R7, #0x1")
        b.insn("B", "lp")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        cond = b.assemble(self.cond, pad="nop")

        def param(b, reg):
            b.insn("LDRH", f"R{reg}, [R4, #0x16]")
            b.insn("LSL", f"R{reg}, R{reg}, #0x{SHIFT:X}")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.insn("ORR", f"R{reg}, R0")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("STR", "R1, [SP, #0x0]")
        b.insn("LDRB", "R5, [R4, #0x2]")
        b.insn("LDRB", "R0, [R4, #0x6]")
        b.insn("EOR", "R5, R0")
        b.ldr_const(6, STATE)
        b.insn("LDR", "R0, [R6, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BEQ", "p80")
        b.insn("CMP", "R0, #0x7F")
        b.insn("BEQ", "p7f")
        b.insn("CMP", "R0, #0x7E")
        b.insn("BEQ", "p7e")
        b.insn("CMP", "R0, #0x7D")
        b.insn("BEQ", "p7d")
        b.insn("CMP", "R0, #0x78")
        b.insn("BEQ", "p78")
        b.insn("MOV", "R0, #0x0")
        b.insn("B", "ret")
        b.label("p80")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDR", "R1, [SP, #0x0]")
        b.call_addr(CPUSH, via=R3)
        b.insn("MOV", "R0, #0x0")
        b.insn("STRH", "R0, [R4, #0x14]")
        b.insn("STRH", "R0, [R4, #0x16]")
        b.insn("STRH", "R0, [R4, #0x1A]")
        b.insn("MOV", "R0, #0x7F")
        b.insn("B", "ret")
        b.label("p7f")
        b.insn("LDRH", "R0, [R4, #0x1A]")
        b.insn("CMP", f"R0, #0x{N:X}")
        b.insn("BGE", "to78")
        b.call_addr(MAY_SS, R5, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "to78")
        b.call_addr(FREE_ZONE, R5, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "to78")
        param(b, 7)
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.call_addr(COUNT, R0, R1, R7, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "to78")
        b.call_addr(MESSAGE, R5, MSG_SS, via=R3)
        b.insn("MOV", "R0, #0x7E")
        b.insn("B", "ret")
        b.label("to78")
        b.insn("MOV", "R0, #0x78")
        b.insn("B", "ret")
        b.label("p7e")
        param(b, 7)
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x6")
        b.insn("LDRH", "R2, [R4, #0x0]")
        b.call_addr(PICKER, R0, R1, R2, R7, via=R6)
        b.insn("MOV", "R0, #0x7D")
        b.insn("B", "ret")
        b.label("p7d")
        b.call_addr(READBACK, via=R3)
        b.insn("ADD", "R7, R0, #0x0")
        b.insn("LDR", "R0, [R7, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.insn("LDRH", "R1, [R4, #0x1A]")
        b.insn("CMP", "R1, #0x0")
        b.insn("BNE", "second")
        b.insn("STRH", "R0, [R4, #0x14]")
        b.insn("B", "count")
        b.label("second")
        b.insn("STRH", "R0, [R4, #0x16]")
        b.label("count")
        b.insn("ADD", "R1, #0x1")
        b.insn("STRH", "R1, [R4, #0x1A]")
        b.insn("LDRH", "R3, [R4, #0x0]")
        b.insn("LSL", "R3, R3, #0x10")
        b.call_addr(SUMMON, R5, R7, 1, via=R6)
        b.insn("MOV", "R0, #0x7F")
        b.insn("B", "ret")
        b.label("p78")
        b.call_addr(SHUFFLE, R5, via=R3)
        b.call_addr(CPOP, via=R3)
        b.insn("MOV", "R0, #0x0")
        b.label("ret")
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.pred, pred, "PRED"), (self.handler, handler, "HANDLER"), (self.cond, cond, "COND"), (self.res, res, "RES"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)

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

        b = EffectBuilder()                  # LOCK: replaces `bl 0x021BA1E8` (caller's r5 = cid, r7 = side)
        b.insn("PUSH", "{R4, LR}")
        b.call_addr(SS_LEVEL, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.call_addr(NODE_QUERY, R7, 0xB, cid, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "allow")
        b.call("get_race", R5, via=R3)
        b.insn("CMP", f"R0, #0x{BEAST:X}")
        b.insn("BEQ", "allow")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        b.label("allow")
        b.insn("MOV", "R0, #0x1")
        b.label("out")
        b.insn("POP", "{R4, PC}")
        lock_blob = b.assemble(lock, pad="nop")
        b = EffectBuilder()                  # COST: post the turn-log node {0xB, cid, kind 1} once per activation
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.turnlog_post(R0, R1, 1, via=R4)
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        cost_blob = b.assemble(cost_a, pad="nop")
        ov3_blobs = ((negr, precheck(negr, self.neg_target)), (epl, precheck(epl, self.epl_target)),
                     (lock, lock_blob), (cost_a, cost_blob))
        for a, blob in ov3_blobs:
            assert len(blob) <= reserve3[a], f"ov3 stub @{a:#x} {len(blob):#x} > {reserve3[a]:#x}"
            assert_thumb1_only(blob, a)
        hooks = ((0x021EE418, self.neg_target, negr), (0x02268090, self.epl_target, epl), (0x021BA368, SS_LEVEL, lock))
        cls0_patched = (cid, self.res | 1, 0, self.cond | 1, cost_a | 1, 0)
        crit_patched = (cid, 0xFFFF, self.handler | 1, self.word)

        def install(rom, view):
            host = view.blob(self.host, self.host_end - self.host)
            if not all(view.blob(a, len(blob)) == blob for a, blob in ov3_blobs):
                assert hashlib.sha256(host).hexdigest()[:16] == self.host_sha16, "ov3 host is not the stock dead body"
                view.write(self.host, bytes(self.host_end - self.host))
                for a, blob in ov3_blobs:
                    view.write(a, blob)
            for site, native, stub in hooks:
                cur = common_bl_target(view.buf, site)
                if cur != stub:
                    assert cur == native, f"bl @{site:#010x} -> {cur:#010x}, expected {native:#010x}"
                    view.write(site, common_bl(site, stub))
            cur = tuple(view.unpack(self.registry_row, "<II"))
            if cur != (0x02254E95, cid):
                assert cur == self.registry_native, f"End-Phase row = {[hex(x) for x in cur]}"
                view.pack(self.registry_row, "<II", 0x02254E95, cid)
            lp = tuple(view.unpack(self.lp_row, "<Hh"))
            if lp != (cid, 0):
                assert lp == (cid, 1000), f"LP-cost row = {lp}"
                view.pack(self.lp_row, "<Hh", cid, 0)

        def check(c, rom, view):
            from otn_enhanced.asm import effect_verify
            c.eq(tuple(view.unpack(self.lp_row, "<Hh")), (cid, 0), "LP-cost row zeroed")
            c.ok(all(view.blob(a, len(blob)) == blob for a, blob in ov3_blobs), "ov3 stubs in the dead selector body")
            c.ok(all(code_reaches(rom, s, stub) for s, _n, stub in hooks), "hook bls reach the stubs (directly or through later fronts)")
            c.eq(tuple(view.unpack(self.registry_row, "<II")), (0x02254E95, cid), "End-Phase registry row 249")

        return Compiled(stubs, (), (Edit(CLS0, cid, self.cls0_native, cls0_patched),
                                    Edit(CRITERIA, cid, self.crit_native, crit_patched)),
                        installs=(install,), checks=(check,))



OV3_HOST = 0x02237D8C
LOCK = OV3_HOST + 0x30          # infernoble fronts this stub

SPEC = card(
    0x17F4,
    special_summon_three_beasts_negated_destroyed_at_end_phase(
        cls0_native=(0x17F4, 0x0221C955, 0, 0x021F8515, 0x021E4D81, 0x02237D8D),
        crit_native=(0x17F4, 0xFFFF, 0x0223E821, 0x2),
        word=0x58880002,                                    # Beast (11 << 27), Lv<=2, monster
        lp_row=0x0226F254,
        pred=ov5_cave.CAVE_OS_PRED, handler=ov5_cave.CAVE_OS_HANDLER, cond=ov5_cave.CAVE_OS_COND, res=ov5_cave.CAVE_OS_RES,
        host=OV3_HOST, host_end=0x02237E54, host_sha16="1893131e86dddfda",
        neg_target=0x02223490,                              # Norden's ov3 '0x1127 ? 1 : bsearch'
        epl_target=ov5_cave.CAVE_PTER_NOATK,                # Petiteranodon's ov5 '0x0FE1 ? 1 : bsearch'
        registry_row=0x0228E1E0 + 249 * 8, registry_native=(0x02253EC9, 0x0E8C)))

_dsl_main, _dsl_verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_obedience_schooled.nds")

# CPU play hook (2026-11-06; same defect as That Grass Looks Greener). The donor Abyssal Designator's ov5 CPU row
# {0x0003D7F4, 0x02323D21} keeps the donor's own evaluator, which returns 1 only if the OPPONENT controls a monster AND
# ai[side] >= 0. The CPU is only able to play this card with NO monsters of its own, which is exactly when ai[side] is
# negative (-1600..-2800 traced) or the opponent is empty, so it returned 0 on every call (~20 calls, 5 duels) and the
# CPU never enqueued the card (notes/obedience-schooled-findings.md). 0x023107C1 is `movs r0,#1 ; bx lr` (the always-true
# evaluator of 145 stock rows); the card's own cond/cost still gate the play.
_AI_ROW = 0x02395EEC
_AI_ROW_ID, _AI_EVAL_OLD, _AI_EVAL_NEW = 0x0003D7F4, 0x02323D21, 0x023107C1


def _ai_row_off():
    return _AI_ROW - ov5_cave.OV5_RAM_BASE


def _patch_ai_row(out):
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = ov5_cave._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    off = _ai_row_off()
    got = struct.unpack_from("<2I", data, off)
    assert got in ((_AI_ROW_ID, _AI_EVAL_OLD), (_AI_ROW_ID, _AI_EVAL_NEW)), f"ov5 AI row @{_AI_ROW:#x} is {got}"
    struct.pack_into("<I", data, off + 4, _AI_EVAL_NEW)
    ov5_cave._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)


def main(write_text=False, src=dsl.SRC, out="data/over_the_nexus/working/rom_obedience_schooled.nds"):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out="data/over_the_nexus/working/rom_obedience_schooled.nds"):
    ok = _dsl_verify(out)
    import ndspy.rom
    ov = ov5_cave._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    got = struct.unpack_from("<2I", bytes(ov.data), _ai_row_off())
    good = got == (_AI_ROW_ID, _AI_EVAL_NEW)
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row {_AI_ROW:#x} = {got[0]:#x}, {got[1]:#x} (want evaluator {_AI_EVAL_NEW:#x})")
    return bool(ok) and good


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

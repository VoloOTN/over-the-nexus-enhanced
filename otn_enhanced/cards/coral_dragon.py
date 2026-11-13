"""Coral Dragon (WATER / Dragon / Synchro Tuner Effect / Level 6 / 2400 / 500) on B. Skull Dragon 0x107F.

    1 Tuner + 1+ non-Tuner monsters
    Once per turn: You can discard 1 card, then target 1 card your opponent controls; destroy it.
    If this Synchro Summoned card is sent from the field to the GY: You can draw 1 card.
    You can only use this effect of "Coral Dragon" once per turn.

Whole card: C0 (identity) + C1 (discard + destroy ignition) + C2 (the draw).
Status: whole card in-game confirmed by user 2026-11-09 ("All confirmed. Ship"); SHIPPED to steps.STEPS (step 118, after block_dragon).  See notes/coral-dragon-findings.md.

C2 is Cyber Phoenix 0x1A07's optional "destroyed and sent to GY: draw" shape (cls2 {draw 0x022065B9, 0, 0x021F069D, 0x021E51E5, 0}
+ draw-count row) armed by a leave-MASK row {cid, 0x0805} (you control it + left the field + to the GY, any cause), with ONE
non-native part: the +0C condition is gated on the departing card having been Synchro Summoned.
"""
import os
import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import (CLS2, CLS3, DRAW_COUNT, LEAVE_MASK, LIST_30, LIST_106, Compiled, Row, _template, card, card_prop_copied_from_template,
                              card_props, fusion_recipe_blanked)
from otn_enhanced.cards.life_stream_dragon import set_code_slot_to_phantom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass

DONOR = 0x107F                      # B. Skull Dragon (effectless Fusion, Lv9)
_PHOENIX = 0x1A07                   # Cyber Phoenix: the optional draw record being transplanted
_DRAW_RES, _DRAW_COND, _OPTIONAL = 0x022065B9, 0x021F069D, 0x021E51E5
_GY_INDEX = 0x021A2510              # (side, card ref u16) -> index in that side's GY array, -1 if absent
_GY_ARRAY = 0x0229AC94 + 0x55C      # player base + GY array offset; stride 0xB3C per side, 4 B per entry (KB 0x021E5709)
_MASK_SENT_TO_GY = 0x0805           # 0x0001 you control it | 0x0004 left the field | 0x0800 destination is the GY (Pinch Hopper's value)
_MASK_COUNT_SITE = 0x021C8108       # `movs r2,#0x98` -- must NOT change
PHANTOMS = dict(cls2=0x1B46, draw=0x1AE9, mask=0x194A, cls3=0x1BCE)      # one per table; registered in check_allocations.PHANTOM_CLAIMS


# SS-commit sites (shared with ss_commit_hook.py): `BL <head>` at both Special-Summon commit routines; r0 = side, r4 = the summon descriptor 0x02298A28 (must survive),
# r1-r3 dead, the return value dead.  desc[+0xA] = source zone (0x0B hand; 0x0C assumed Extra Deck), desc[+0xC] = packed ref (idx<<1|side), desc[+0xE] = cid.
_SS_SITES = (0x02267A38, 0x0226878A, 0x02268B7C)       # the three `BL 0x02265768` (summon-event evaluator) callers: codes 7 Normal, 9 Synchro/Fusion/Ritual, 8 other Special Summon
_SS_NATIVE = 0x02265768
_SUMMON_DESC = 0x02298A28
_ZONE_EXTRA = 0x0C
_MISS_NODE, _MISS_NATIVE = 0x021EE10C, bytes.fromhex("133a934231d0c0e0")     # `subs r2,#0x13 ; cmp r3,r2 ; beq ; b` (shadow_mist.MISS_NODE_NATIVE)


def _ss_front_stub(base: int, prev_head: int) -> bytes:
    """BL'd from both SS-commit sites.  Records, per packed card ref, whether the donor's LAST Special Summon came from the Extra Deck (= a Synchro Summon):
    set the ref's bit when desc[+0xA] == 0x0C, clear it for any other source (Monster Reborn / Call of the Haunted ... from the GY).  Then replays the previous head."""
    mark, dbg = ov5_cave.CAVE_CORAL_MARK, ov5_cave.CAVE_CORAL_DBG2
    a = EffectBuilder()
    a.insn("PUSH", "{R5, R6, LR}")
    a.insn("ADD", "R6, R0, #0x0")                 # r6 = side (replayed below)
    a.ldr_const(5, _SUMMON_DESC)
    a.insn("LDRH", "R1, [R5, #0xE]")
    a.ldr_const(2, DONOR)
    a.insn("CMP", "R1, R2")
    a.insn("BNE", "replay")
    a.insn("LDRH", "R1, [R5, #0xC]")              # packed ref
    a.ldr_const(2, 0x1FF)
    a.insn("AND", "R1, R2")
    a.insn("LSR", "R2, R1, #0x3")                 # byte
    a.ldr_const(3, mark)
    a.insn("ADD", "R2, R2, R3")                   # r2 = &byte
    a.insn("MOV", "R3, #0x7")
    a.insn("AND", "R1, R3")
    a.insn("MOV", "R3, #0x1")
    a.insn("LSL", "R3, R1")                       # r3 = bit mask
    a.insn("LDRB", "R1, [R2, #0x0]")
    a.insn("LDRH", "R0, [R5, #0xA]")              # source zone
    a.insn("CMP", "R0, #0x%X" % _ZONE_EXTRA)
    a.insn("BNE", "clear")
    a.insn("ORR", "R1, R3")
    a.insn("B", "store")
    a.label("clear")
    a.insn("BIC", "R1, R3")
    a.label("store")
    a.insn("STRB", "R1, [R2, #0x0]")
    a.ldr_const(2, dbg)                           # debug record {cid, src zone, ref, count}
    a.insn("LDRH", "R1, [R5, #0xE]")
    a.insn("STR", "R1, [R2, #0x0]")
    a.insn("LDRH", "R1, [R5, #0xA]")
    a.insn("STR", "R1, [R2, #0x4]")
    a.insn("LDRH", "R1, [R5, #0xC]")
    a.insn("STR", "R1, [R2, #0x8]")
    a.insn("LDR", "R1, [R2, #0xC]")
    a.insn("ADD", "R1, #0x1")
    a.insn("STR", "R1, [R2, #0xC]")
    a.label("replay")
    a.insn("ADD", "R0, R6, #0x0")
    a.ldr_const(1, prev_head | 1)                 # previous head, an inline literal (odd = Thumb)
    a.insn("BLX", "R1")
    a.insn("POP", "{R5, R6, PC}")
    code = a.assemble(base)
    assert_thumb1_only(code, base)
    assert len(code) <= 0x70, f"SS front {len(code):#x} B > 0x70"
    return code


def _miss_front_stub(base: int, prev_head: int) -> bytes:
    """BL'd from the miss-timing node 0x021EE10C (r3 = cid; Z = accept = never miss).  The donor never misses its timing ('If ... You can' = Synchro material / Tribute
    must still offer it); every other cid goes to the previous head, or replays the two displaced stock ops when the node is still stock (PREV slot 0)."""
    a = EffectBuilder()
    a.ldr_const(1, DONOR)
    a.insn("CMP", "R3, R1")
    a.insn("BEQ", "ret")
    if prev_head:
        a.ldr_const(1, prev_head | 1)             # previous head, an inline literal
        a.insn("BX", "R1")                        # previous head tail-returns to the node's caller (LR intact)
    a.insn("SUB", "R2, #0x13")                    # the two displaced stock ops (stock node only)
    a.insn("CMP", "R3, R2")
    a.label("ret")
    a.insn("BX", "LR")
    code = a.assemble(base)
    assert_thumb1_only(code, base)
    assert len(code) <= 0x30, f"miss front {len(code):#x} B > 0x30"
    return code


def _cond_stub(base: int) -> bytes:
    """cls2 +0C: offer the draw only if THIS card instance (desc[+0xC] = packed ref) was last Special Summoned from the Extra Deck = Synchro Summoned (_ss_front_stub's
    bitmap), then the native draw condition.  Bit 15 of the card word is NOT usable: it means 'properly summoned' and survives Monster Reborn (user test 2026-11-09).
    Writes {calls, ref, marker byte, marker bit} to CAVE_CORAL_DBG."""
    dbg, mark = ov5_cave.CAVE_CORAL_DBG, ov5_cave.CAVE_CORAL_MARK
    a = EffectBuilder()
    a.insn("PUSH", "{R4, LR}")
    a.insn("ADD", "R4, R0, #0x0")                 # r4 = desc
    a.ldr_const(2, dbg)
    a.insn("LDR", "R1, [R2, #0x0]")
    a.insn("ADD", "R1, #0x1")
    a.insn("STR", "R1, [R2, #0x0]")               # calls++
    a.insn("LDRH", "R1, [R4, #0xC]")
    a.ldr_const(3, 0x1FF)
    a.insn("AND", "R1, R3")                       # ref
    a.insn("STR", "R1, [R2, #0x4]")
    a.insn("LSR", "R3, R1, #0x3")                 # byte
    a.ldr_const(0, mark)
    a.insn("ADD", "R3, R3, R0")
    a.insn("LDRB", "R3, [R3, #0x0]")              # marker byte
    a.insn("STR", "R3, [R2, #0x8]")
    a.insn("MOV", "R0, #0x7")
    a.insn("AND", "R1, R0")
    a.insn("LSR", "R3, R1")                       # byte >> bit
    a.insn("MOV", "R0, #0x1")
    a.insn("AND", "R3, R0")                       # the marker bit
    a.insn("STR", "R3, [R2, #0xC]")
    a.insn("CMP", "R3, #0x0")
    a.insn("BEQ", "fail")
    a.insn("ADD", "R0, R4, #0x0")
    a.bl(_DRAW_COND & ~1)                         # native draw condition (Thumb fn at 0x021F069C)
    a.insn("POP", "{R4, PC}")
    a.label("fail")
    a.insn("MOV", "R0, #0x0")
    a.insn("POP", "{R4, PC}")
    code = a.assemble(base)
    assert_thumb1_only(code, base)
    assert len(code) <= 0x70, f"cond stub {len(code):#x} B > its 0x70 slot"
    return code



_VERIFY_ROM = None      # set by verify() below: the ROM whose PREV slot holds the heads our fronts displaced


def _heads(view):
    """(SS-evaluator head, miss-node head or 0 = stock) as the view has them now."""
    ss = {ov3_bl_target(view.buf, site) for site in _SS_SITES}
    assert len(ss) == 1, f"the three SS-evaluator callers call different heads {[hex(x) for x in ss]}"
    ss_head = ss.pop()
    if view.blob(_MISS_NODE, 8) == _MISS_NATIVE:
        return ss_head, 0
    return ss_head, ov3_bl_target(view.buf, _MISS_NODE)


@dataclass(frozen=True)
class synchro_summoned_sent_to_gy_draw:
    """'If this Synchro Summoned card is sent from the field to the GY: You can draw 1 card.' (see module docstring)"""
    count: int = 1

    def compile(self, view, cid) -> Compiled:
        slots_native = (_DRAW_RES, 0, _DRAW_COND, _OPTIONAL, 0)
        hi = _template(view, CLS2, _PHOENIX, slots_native)[1]
        assert _template(view, DRAW_COUNT, _PHOENIX)[1] == self.count, "template draws a different count"
        assert view.u16(_MASK_COUNT_SITE) == 0x2200 | LEAVE_MASK.count, "leave-mask count immediate moved"
        for lst in (LIST_30, LIST_106):     # either list arms the dispatcher and the mask table is then skipped
            assert cid not in view.keys(lst.base, count=lst.count, stride=2), f"donor is in {lst.label}"
        cond, ssf, miss = ov5_cave.CAVE_CORAL_C2COND, ov5_cave.CAVE_CORAL_SSF, ov5_cave.CAVE_CORAL_MISS
        ss_head, miss_head = _heads(view)
        if ss_head == ssf or miss_head == miss:     # already installed (verify / re-run): the displaced heads live in the ROM's PREV slot
            assert _VERIFY_ROM, 'coral_dragon fronts are installed but no ROM path was given to recover the previous heads'
            import ndspy.rom
            prev = struct.unpack('<II', ov5_cave.read_cave(ndspy.rom.NintendoDSRom.fromFile(_VERIFY_ROM), ov5_cave.CAVE_CORAL_PREV, 8))
            ss_head, miss_head = prev[0] & ~1, prev[1] & ~1
        stubs = ((cond, _cond_stub(cond), "C2 cls2 +0C: Synchro-Summoned marker + native draw cond"),
                 (ssf, _ss_front_stub(ssf, ss_head), "C2 SS-commit front: Extra-Deck summon marker"),
                 (miss, _miss_front_stub(miss, miss_head), "C2 never-miss front (IF effect)"),
                 (ov5_cave.CAVE_CORAL_DBG, bytes(0x10), "debug scratch (zero)"),
                 (ov5_cave.CAVE_CORAL_DBG2, bytes(0x10), "SS-commit debug record (zero)"),
                 (ov5_cave.CAVE_CORAL_MARK, bytes(0x40), "Extra-Deck-summon bitmap (zero)"))
        rows_ = (Row(CLS2, (cid, hi, _DRAW_RES, 0, cond | 1, _OPTIONAL, 0), PHANTOMS["cls2"]),
                 Row(DRAW_COUNT, (cid, self.count), PHANTOMS["draw"]),
                 Row(LEAVE_MASK, (cid, _MASK_SENT_TO_GY), PHANTOMS["mask"]))

        def install(rom, view):
            ss_head, miss_head = _heads(view)
            if ss_head != ssf and miss_head != miss:        # first install: remember what we displaced
                ov5_cave.install_cave(rom, ov5_cave.CAVE_CORAL_PREV,
                                      struct.pack("<II", ss_head | 1, (miss_head | 1) if miss_head else 0), reserve=0x10)
            for site in _SS_SITES:
                if ov3_bl_target(view.buf, site) != ssf:
                    view.write(site, common_bl(site, ssf))
            if miss_head != miss:
                view.write(_MISS_NODE, common_bl(_MISS_NODE, miss))

        def check(c, rom, view):
            for lst in (LIST_30, LIST_106):
                c.ok(cid not in view.keys(lst.base, count=lst.count, stride=2), f"donor in NEITHER {lst.label}")
            c.eq(view.u16(_MASK_COUNT_SITE), 0x2200 | LEAVE_MASK.count, "leave-mask count immediate unchanged")
            for site in _SS_SITES:
                c.eq(ov3_bl_target(view.buf, site), ssf, f"SS-commit site {site:#x} -> Coral's front")
            c.eq(ov3_bl_target(view.buf, _MISS_NODE), miss, f"miss-timing node {_MISS_NODE:#x} -> Coral's never-miss front")
            prev = struct.unpack("<II", ov5_cave.read_cave(rom, ov5_cave.CAVE_CORAL_PREV, 8))
            c.ok(bool(prev[0] & 1) and prev[0] != (ssf | 1), f"previous SS-commit head recorded ({prev[0]:#x})")
            c.ok(prev[1] == 0 or (bool(prev[1] & 1) and prev[1] != (miss | 1)), f"previous miss-node head recorded ({prev[1]:#x}; 0 = stock)")

        return Compiled(stubs, rows_, installs=(install,), checks=(check,))


# ---- C1: "Once per turn: You can discard 1 card, then target 1 card your opponent controls; destroy it." ----------------------
# cls3 record = XYZ-Dragon Cannon 0x15B4's target/destroy slots (res 0x02204899, filter 0x021DE7C9 "cards your opponent controls" -- the
# same two Grapha C2 ships, in-game confirmed -- picker 0x02234DA5) + Chiron the Mage's once-per-turn discard cost/cond shape with the
# discard mode = ANY card.  Native cond/cost 0x021F024D / 0x021E4ECD are NOT reusable: they take the discard COUNT from 0x021E4C60, a
# per-cid table that returns 0 for an unlisted cid (= a free effect).
_C1_RES, _C1_FILTER, _C1_PICKER = 0x02204899, 0x021DE7C9, 0x02234DA5
_OPT_TAG, _OPT_STAMP, _HAS_NODE = 0x0FB6, 0x021E5060, 0x021A1430
_IN_COST_SIM, _HAND_HAS = 0x021D2BC8, 0x021EFF30
_DISCARD_REQ = 0x0225991C           # (side, count, r2, r3): r2 = r3 = 0 -> mode 0 (no card-kind filter), flags 0x10 (disasm 0x02259934)
_C1_NATIVE = {0x15B4: (_C1_RES, _C1_FILTER, 0x021F0221, 0x021E4EA5, _C1_PICKER)}


def _c1_cond_stub(base: int) -> bytes:
    """cls3 +0C: not yet used this turn (OPT node 0x0FB6 on desc[2]/desc[3], as Chiron's 0x021F01C0 / 0x021F024C) AND the hand has a card
    to discard (0x021EFF30(side, 1, excluded = desc[+0xC], mode 0), the call native 0x021F0220 makes with the cid-keyed count)."""
    a = EffectBuilder()
    dbg = ov5_cave.CAVE_CORAL_DBG1
    a.insn("PUSH", "{R3, R4, R5, LR}")
    a.insn("ADD", "R5, R0, #0x0")
    a.ldr_const(4, dbg)
    a.insn("LDR", "R3, [R4, #0x0]")
    a.insn("ADD", "R3, #0x1")
    a.insn("STR", "R3, [R4, #0x0]")               # cond calls++
    if os.environ.get("CORAL_C1_DIAG") == "cond1":   # DIAGNOSTIC ROM ONLY: offer unconditionally, to tell 'CPU never asks' from 'cond says no'
        a.insn("B", "yes")
    a.insn("LDRB", "R0, [R5, #0x2]")
    a.insn("LDRB", "R1, [R5, #0x3]")
    a.ldr_const(2, _OPT_TAG)
    a.bl(_HAS_NODE)
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "no")                           # already used this turn
    a.insn("ADD", "R0, R5, #0x0")                 # 0x021D2BC8 takes the DESC in r0 (it reads desc[4]); r0 was the tag-query result -> data abort (freeze)
    a.bl(_IN_COST_SIM)
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "yes")
    a.insn("LDRB", "R0, [R5, #0x2]")
    a.insn("MOV", "R1, #0x1")
    a.insn("LDRH", "R2, [R5, #0xC]")
    a.insn("MOV", "R3, #0x0")
    a.bl(_HAND_HAS)
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "yes")
    a.label("no")
    a.insn("MOV", "R0, #0x0")
    a.insn("POP", "{R3, R4, R5, PC}")
    a.label("yes")
    a.ldr_const(4, dbg)
    a.insn("LDR", "R3, [R4, #0x4]")
    a.insn("ADD", "R3, #0x1")
    a.insn("STR", "R3, [R4, #0x4]")               # cond yes++
    a.insn("MOV", "R0, #0x1")
    a.insn("POP", "{R3, R4, R5, PC}")
    code = a.assemble(base)
    assert_thumb1_only(code, base)
    assert len(code) <= 0x60, f"C1 cond {len(code):#x} B > 0x60"
    return code


def _c1_cost_stub(base: int) -> bytes:
    """cls3 +10: Chiron's 0x021E8FD4 with the discard mode changed from 'Spell' (r3 = 1) to 'any card' (r3 = 0)."""
    a = EffectBuilder()
    a.insn("PUSH", "{R4, LR}")
    a.insn("ADD", "R4, R0, #0x0")
    a.ldr_const(2, ov5_cave.CAVE_CORAL_DBG1)
    a.insn("LDR", "R3, [R2, #0x8]")
    a.insn("ADD", "R3, #0x1")
    a.insn("STR", "R3, [R2, #0x8]")               # cost calls++
    a.bl(_OPT_STAMP)
    a.insn("LDRB", "R0, [R4, #0x2]")
    a.insn("MOV", "R1, #0x1")
    a.insn("MOV", "R2, #0x0")
    a.insn("MOV", "R3, #0x0")
    a.bl(_DISCARD_REQ)
    a.insn("MOV", "R0, #0x1")
    a.insn("POP", "{R4, PC}")
    code = a.assemble(base)
    assert_thumb1_only(code, base)
    assert len(code) <= 0x40, f"C1 cost {len(code):#x} B > 0x40"
    return code


@dataclass(frozen=True)
class discard_destroy_opponent_card_once_per_turn:
    """'Once per turn: You can discard 1 card, then target 1 card your opponent controls; destroy it.'"""

    def compile(self, view, cid) -> Compiled:
        for k, v in _C1_NATIVE.items():                  # the donor cls3 slots we borrow, asserted at build
            r = _template(view, CLS3, k)
            assert tuple(r[1:]) == v, f"cls3 template {k:#x} drifted: {[hex(x) for x in r[1:]]}"
        assert view.u32(0x021F0278) == _OPT_TAG, "OPT tag literal moved"
        cond, cost = ov5_cave.CAVE_CORAL_C1COND, ov5_cave.CAVE_CORAL_C1COST
        stubs = ((cond, _c1_cond_stub(cond), "C1 cls3 +0C: OPT tag absent and a card to discard"),
                 (cost, _c1_cost_stub(cost), "C1 cls3 +10: stamp OPT tag, discard 1 card (any)"),
                 (ov5_cave.CAVE_CORAL_DBG1, bytes(0x10), "C1 debug counters (zero)"))
        return Compiled(stubs, (Row(CLS3, (cid, _C1_RES, _C1_FILTER, cond | 1, cost | 1, _C1_PICKER), PHANTOMS["cls3"]),))


SPEC = card(
    DONOR,
    fusion_recipe_blanked(row=16, stock=(DONOR, 0x0FBC, 0x0FF8, 0)),                   # Summoned Skull + Red-Eyes B. Dragon
    set_code_slot_to_phantom(base=0x0209CF90, count=42, index=3, phantom=0x10AB),      # no longer an "Archfiend" (sorted dup of the phantom beside it)
    discard_destroy_opponent_card_once_per_turn(),
    synchro_summoned_sent_to_gy_draw(),
    card_prop_copied_from_template(ref_cid=0x239E, card_type="Synchro Tuner Effect Monster",
                                   donor_genre=0x0000000020200000, new_genre=0x0000001800200000))

PROPS = card_props("WATER", "Dragon", level=6, atk=2400, defense=500, card_type="Synchro Tuner Effect Monster")

main, _verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_coral_dragon.nds")


def verify(out: str = "data/over_the_nexus/working/rom_coral_dragon.nds"):
    global _VERIFY_ROM
    _VERIFY_ROM = out
    return _verify(out)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

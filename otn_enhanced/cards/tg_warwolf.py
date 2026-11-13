"""T.G. Warwolf (DARK / Beast-Warrior / Level 3 / 1200 / 0) on Hitotsu-Me Giant 0x0FA9.

    When a Level 4 or lower monster(s) is Special Summoned (except during the Damage Step): You can Special Summon
    this card from your hand. Once per turn, during the End Phase, if this card is in the GY because it was destroyed
    on the field and sent there this turn: You can add 1 "T.G." monster from your Deck to your hand, except
    "T.G. Warwolf".
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import TG_SETCODE, TG_TABLE, archetype_member, card, card_props, CLS2, CLS2_ALWAYS_ELIGIBLE, CLS2_DELAYED_END_PHASE, CLS2_SEARCH_RESOLVER, CRITERIA_PAST_SENTINEL, Compiled, POP_DECK_ZONE, POP_FLAGS, REG_ENDPHASE_RESOLVER, Row, _HAS_SETCODE, _deck_search_wrapper
from otn_enhanced.effects import cave3
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
from dataclasses import dataclass
from otn_enhanced.effects.common import insert_sorted
from otn_enhanced.effects.common import rows
import struct


def _bl_hook(view, site: int, native: tuple, target: int, what: str) -> None:
    """Install a 4-byte BL over two displaced halfwords, guarded and idempotent."""
    cur = view.unpack(site, "<2H")
    want = struct.unpack("<2H", common_bl(site, target))
    if cur == want:
        return
    assert cur == native, f"{what} @{site:#010x} = {cur[0]:04X} {cur[1]:04X} (expected native {native[0]:04X} {native[1]:04X})"
    view.pack(site, "<2H", *want)


_TGW_SS_LOOKUP, _TGW_SUMMON_DESC, _TGW_CID_LEVEL = 0x021A25A0, 0x02298A28, 0x0202ABD8


_TGW_REG_HELPER, _TGW_ENUM_POOLVAL, _TGW_COMMIT = 0x021D36C0, 0x0229C294, 0x021D3168


_TGW_HANDSS_RES, _TGW_WHEN_TAG = 0x02206ABD, 0x021E51E5


@dataclass(frozen=True)
class special_summoned_low_level_monster_offers_hand_summon:
    """'When a Level N or lower monster(s) is Special Summoned (except during the Damage Step): You can Special Summon
    this card from your hand.' Three pieces, none sufficient alone:
      A  arm hook: BL over BOTH SS-commit lookups (0x022692E8 / 0x02269396) replays the displaced call then sets a
         runtime LATCH word when the summoned cid's Level is 1..N. (Only Special Summons reach these sites, so there is
         deliberately NO genuine-SS descriptor test: the old `[desc+0x10]&0x10` test never armed.)
      B  cls2 {generic hand-SS resolver, 0, cond = latch gate, WHEN tag, 0}: matters only at RESOLUTION.
      C  enumeration registration: the hardcoded per-summon cid dispatch 0x02265CF8 must register the donor through
         0x021D36C0(side, cid, event, ctx) or it is never OFFERED; hooked at the CONVERGENCE point 0x02266394 (the
         earlier 0x02266390 is skipped for a kind-0xB summon).
    The latch is a 4-byte runtime word in the ov3 pool (unproven as RAM until in-game)."""
    arm: int
    cond: int
    enum: int
    latch: int
    max_level: int
    arm_sites: tuple                 # ((site, native halfword pair), ...)
    enum_site: int
    enum_native: tuple
    phantom: int                     # cls2

    def compile(self, view, cid) -> Compiled:
        b = EffectBuilder()
        b.prologue(save=[R4, R5, R6, R7])
        b.call_addr(_TGW_SS_LOOKUP)
        b.insn("ADD", "R6, R0, #0x0")            # keep the helper's result for the return
        b.ldr_const(2, _TGW_SUMMON_DESC)
        b.insn("LDRH", "R0, [R2, #0xE]")         # summoned cid
        b.if_eq(R0, 0, "exit")
        b.call_addr(_TGW_CID_LEVEL)
        b.if_eq(R0, 0, "exit")                   # Level 0 == not a monster
        b.insn("CMP", f"R0, #0x{self.max_level:X}")
        b.insn("BGT", "exit")
        b.ldr_const(1, self.latch)
        b.insn("MOV", "R0, #0x1")
        b.insn("STR", "R0, [R1, #0x0]")
        b.label("exit")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        arm = b.assemble(self.arm)

        b = EffectBuilder()
        b.prologue(save=[R4, R5])
        b.ldr_const(1, self.latch)
        b.insn("LDR", "R0, [R1, #0x0]")
        b.if_eq(R0, 0, "no")
        b.epilogue(ret=1)
        b.label("no")
        b.epilogue(ret=0)
        cond = b.assemble(self.cond)

        b = EffectBuilder()                      # R4 = summon descriptor, R6 = event, R7 = ctx at the convergence point
        b.prologue(save=[R4, R5, R6, R7])
        b.ldr_const(4, _TGW_SUMMON_DESC)
        b.insn("LDRH", "R1, [R4, #0xC]")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R0, R1")                  # responding side
        b.ldr_const(1, cid)
        b.insn("ADD", "R2, R6, #0x0")
        b.insn("ADD", "R3, R7, #0x0")
        b.call_addr(_TGW_REG_HELPER)
        b.ldr_const(0, _TGW_ENUM_POOLVAL)        # replay: LDR R0,=0x0229C294
        b.insn("LDR", "R1, [R0, #0x78]")         # replay: LDR R1,[R0,#0x78]
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        enum = b.assemble(self.enum)
        for blob, addr in ((arm, self.arm), (cond, self.cond), (enum, self.enum)):
            assert_thumb1_only(blob, addr)

        def install(rom, view):
            for site, native in self.arm_sites:
                _bl_hook(view, site, native, self.arm, "arm hook")
            _bl_hook(view, self.enum_site, self.enum_native, self.enum, "enum-reg hook")

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            for site, _n in self.arm_sites:
                c.eq(view.unpack(site, "<2H"), struct.unpack("<2H", common_bl(site, self.arm)), f"arm hook @{site:#010x}")
            c.eq(view.unpack(self.enum_site, "<2H"), struct.unpack("<2H", common_bl(self.enum_site, self.enum)),
                 f"enum-reg hook @{self.enum_site:#010x} (the convergence point)")
            bls = lambda blob, addr: {i.branch_target for i in decode_thumb(blob, addr, overlay_data=bytes(view.buf),
                                                                           ram_base=view.base) if i.mnemonic == "BL"}
            c.eq(bls(arm, self.arm), {_TGW_SS_LOOKUP, _TGW_CID_LEVEL}, "arm stub replays the SS lookup and calls cid_level")
            c.eq(bls(enum, self.enum), {_TGW_REG_HELPER}, "enum-reg stub registers the donor and replays the displaced LDRs")
            c.eq(bls(cond, self.cond), set(), "cond stub is a pure arm-latch gate (no BLs)")
            c.eq(view.blob(self.latch, 4), bytes(4), "arm latch ships as 0")

        return Compiled(((self.arm, arm, "E1 arm stub"), (self.cond, cond, "E1 cond stub"),
                         (self.enum, enum, "E1 enum-reg stub"), (self.latch, bytes(4), "E1 arm latch")),
                        (Row(CLS2, (cid, 0, _TGW_HANDSS_RES, 0, self.cond | 1, _TGW_WHEN_TAG, 0), self.phantom),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class end_phase_search_under_swapped_cid:
    """'Once per turn, during the End Phase, if this card is in the GY because it was destroyed on the field and sent
    there this turn: You can add 1 <archetype> monster from your Deck to your hand, except this card.' for a donor that
    ALSO owns a cls2 record for another effect: find_event_handler returns the LEFTMOST same-cid cls2 record, so two
    records on one cid collide whatever their order. The effects' COMMIT paths are separate, so a 4-byte BL over this
    one's COMMIT (`bl 0x021D3168` in the Darksoul walker) rewrites the packed descriptor's cid donor -> `swapped`, and
    the cls2 + populate records live under that phantom: each effect owns a single-record cid. Registry row: a spare
    End-Phase row's cid is repointed at the donor KEEPING resolver 0x02254221; the shared on-destruction arming
    trampoline arms the donor. Filter and wrapper are add_from_deck_end_phase's."""
    set_code: int
    swapped: int
    slots: tuple[int, int, int]      # (filter, wrapper, cid-swap stub), ov3 pool
    commit_site: int
    commit_native: tuple
    reg_row: int
    reg_phantom: int
    phantoms: tuple[int, int]        # (cls2, populate)

    def compile(self, view, cid) -> Compiled:
        filt, wrap, walk = self.slots
        fb = EffectBuilder()
        fb.prologue(save=[R3])
        fb.insn("LDR", "R0, [SP, #0x8]")
        fb.insn("LDR", "R0, [R0, #0x0]")
        fb.insn("LSL", "R0, R0, #0x12")
        fb.insn("LSR", "R0, R0, #0x12")
        fb.ldr_const(1, cid)
        fb.insn("CMP", "R0, R1")
        fb.insn("BEQ", "reject")
        fb.insn("MOV", f"R1, #0x{self.set_code:X}")
        fb.call_addr(_HAS_SETCODE)
        fb.if_eq(R0, 0, "reject")
        fb.epilogue(ret=1)
        fb.label("reject")
        fb.epilogue(ret=0)
        filt_blob = fb.assemble(filt)
        wrap_blob = _deck_search_wrapper(filt).assemble(wrap)
        b = EffectBuilder()      # R0 = packed descriptor (low 14 bits = cid), R5 = the ACTING CID (not R1), R4/R5 walker state
        b.prologue(save=[R0, R1, R2, R4, R5, R6, R7])
        b.ldr_const(6, cid)
        b.insn("CMP", "R5, R6")
        b.insn("BNE", "replay")
        b.insn("LSR", "R0, R0, #0xE")            # drop the low 14 bits
        b.insn("LSL", "R0, R0, #0xE")            # cid field cleared
        b.ldr_const(6, self.swapped)
        b.insn("ORR", "R0, R6")                  # cid field = the phantom
        b.insn("STR", "R0, [SP, #0x0]")          # persist for the replay
        b.label("replay")
        b.insn("LDR", "R0, [SP, #0x0]")
        b.insn("LDR", "R1, [SP, #0x4]")
        b.insn("LDR", "R2, [SP, #0x8]")
        b.call_addr(_TGW_COMMIT)
        b.insn("POP", "{R0, R1, R2, R4, R5, R6, R7, PC}")
        walk_blob = b.assemble(walk)
        stubs = ((filt, filt_blob, "except-self filter"), (wrap, wrap_blob, "deck-search wrapper"),
                 (walk, walk_blob, "COMMIT cid-swap stub"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        ph2, php = self.phantoms
        cls2_rec = (self.swapped, 0, CLS2_SEARCH_RESOLVER, 0, CLS2_ALWAYS_ELIGIBLE, CLS2_DELAYED_END_PHASE, 0)
        pop_rec = (self.swapped, POP_DECK_ZONE, wrap | 1, POP_FLAGS)

        def install(rom, view):
            from otn_enhanced.effects.tg_table import arm_tg_leave_trigger
            _bl_hook(view, self.commit_site, self.commit_native, walk, "E2 COMMIT cid-swap hook")
            res, cur = view.unpack(self.reg_row, "<IH")
            if not (res == REG_ENDPHASE_RESOLVER and cur == cid):
                assert res == REG_ENDPHASE_RESOLVER and cur == self.reg_phantom, (
                    f"registry row @{self.reg_row:#010x} = res {res:#010x} cid {cur:#06x}")
                view.set_u16(self.reg_row + 4, cid)          # the cid only; keep the resolver
            insert_sorted(view, CLS2, cls2_rec, drop=ph2, quiet=True)
            insert_sorted(view, CRITERIA_PAST_SENTINEL, pop_rec, drop=php, quiet=True)
            arm_tg_leave_trigger(rom, view.buf, cid, ov3=True)

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            from otn_enhanced.effects.tg_table import CAVE_TG_ARM_OK
            c.eq(view.unpack(self.reg_row, "<IH"), (REG_ENDPHASE_RESOLVER, cid), "E2 registry row stolen, resolver kept")
            c2 = rows(view, CLS2)
            c.ok(any((r[0] & 0xFFFF) == self.swapped and r[2] == CLS2_SEARCH_RESOLVER for r in c2),
                 f"E2 cls2 SEARCH record lives under phantom {self.swapped:#06x}")
            c.ok(any(r[0] == self.swapped for r in rows(view, CRITERIA_PAST_SENTINEL)),
                 f"E2 populate record lives under phantom {self.swapped:#06x}")
            c.ok(not any((r[0] & 0xFFFF) == cid and r[2] == CLS2_SEARCH_RESOLVER for r in c2),
                 f"{cid:#06x} carries NO SEARCH cls2 record -- E1/E2 decoupled (find_event_handler returns the LEFTMOST)")
            c.ok(CAVE_TG_ARM_OK(rom, view.buf, cid), "shared on-destruction arming, cid registered")
            c.eq(view.unpack(self.commit_site, "<2H"), struct.unpack("<2H", common_bl(self.commit_site, walk)),
                 f"E2 COMMIT cid-swap hook @{self.commit_site:#010x}")
            c.ok(any(r[0] == self.swapped and (r[2] & ~1) == wrap for r in rows(view, CRITERIA_PAST_SENTINEL)),
                 f"E2 populate row -> wrapper {wrap:#010x}")
            pools = set(struct.unpack_from(f"<{len(walk_blob) // 4}I", walk_blob, 0))
            fins = decode_thumb(walk_blob, walk, overlay_data=bytes(view.buf), ram_base=view.base)
            c.ok({i.branch_target for i in fins if i.mnemonic == "BL"} == {_TGW_COMMIT} and cid in pools and self.swapped in pools,
                 f"cid-swap stub swaps {cid:#06x}->{self.swapped:#06x} and replays COMMIT")

        return Compiled(stubs, installs=(install,), checks=(check,))



SPEC = card(
    0x0FA9,
    special_summoned_low_level_monster_offers_hand_summon(
        arm=cave3.CAVE3_TGW_ARMHOOK, cond=cave3.CAVE3_TGW_E1COND, enum=cave3.CAVE3_TGW_ENUMREG,
        latch=cave3.CAVE3_TGW_ARMLATCH, max_level=4,
        arm_sites=((0x022692E8, (0xF739, 0xF95A)), (0x02269396, (0xF739, 0xF903))),
        enum_site=0x02266394, enum_native=(0x48C6, 0x6F81), phantom=0x2352),
    end_phase_search_under_swapped_cid(
        set_code=TG_SETCODE, swapped=0x2511,
        slots=(cave3.CAVE3_TGW_FILTER, cave3.CAVE3_TGW_WRAPPER, cave3.CAVE3_TGW_E2SEARCH),
        commit_site=0x022541E0, commit_native=(0xF77E, 0xFFC2),
        reg_row=0x0228E480, reg_phantom=0x2347, phantoms=(0x234D, 0x234A)),
    archetype_member(TG_TABLE, phantom=0x2513))

POP_PHANTOM = 0x234A        # the populate row E2 consumes (a KB proof asserts it)

PROPS = card_props("DARK", "Beast-Warrior", level=3, atk=1200, defense=0)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_tg_warwolf.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

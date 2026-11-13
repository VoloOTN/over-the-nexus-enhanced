"""T.G. Hyper Librarian (DARK / Spellcaster / Level 5 / 2400 / 1800 / Synchro) on Amphibious Bugroth 0x1225.

    "1 Tuner + 1+ non-Tuner monsters
     If a monster is Synchro Summoned: Draw 1 card. This card must be face-up on the field to activate
     and to resolve this effect."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import TG_TABLE, archetype_member, card, card_props, fusion_to_synchro_effect, CLS2, Compiled, HOOK_RESERVE, RES_RESERVE, Row, _in_ov5
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
import struct


_SUMMON_DESC = 0x02298A28       # global summon descriptor: +0xC packed ref, +0xE cid, +0x10 bit0 = proper summon


_CARD_TYPE_CODE = 0x0202ABF8    # (cid) -> 5-bit card-type code; Synchro = 17/18/19 (NOT 0x020232AC: that accepts Fusion)


_DRAW_PRIM = 0x021D12F4


_REG_PRIM = 0x021D3168          # register a field responder -> chain link


_ENUM_REPLAY = 0x02265470       # the call the enumeration hook displaces


_ENUM_HOOK_SITE = 0x02265D00    # BL _ENUM_REPLAY inside the summon-responder enumeration master 0x02265CF8


_ENUM_HOOK_NATIVE = (0xF7FF, 0xFBB6)


_PLAYER_STRIDE, _ZONE_ARRAY = 0xB3C, 0x0229AC94 + 0x34


_RESP_CONST = (2 << 21) | (9 << 25)     # responder category 2, trigger-type 9


_RESOLVE_PHASE, _RESOLVE_RETURN = 0x80, 0x7F


_ALWAYS_ELIGIBLE = 0x0224A115


@dataclass(frozen=True)
class synchro_summoned_draw:
    """'If a monster is Synchro Summoned: Draw 1 card. This card must be face-up on the field to activate and
    to resolve this effect.' Mandatory chain link: a hook in the summon-responder enumeration (post-placement)
    registers a cls2 responder for every OTHER face-up copy; the resolver re-checks face-up at resolve.
    `slots` = (hook, resolver, latch, scratch) ov3 pool addresses (latch/scratch are zero RAM words);
    `phantom` = the cls2 cid dropped (count-neutral)."""
    count: int
    slots: tuple[int, int, int, int]
    phantom: int

    def compile(self, view, cid) -> Compiled:
        assert self.count == 1 and not any(_in_ov5(a) for a in self.slots)
        hook, res, latch, scratch = self.slots
        blobs = (_synchro_hook(cid, hook, latch, scratch), _chain_draw_resolver(cid, res))
        for blob, addr in zip(blobs, (hook, res)):
            assert_thumb1_only(blob, addr)
        assert len(blobs[0]) <= HOOK_RESERVE and len(blobs[1]) <= RES_RESERVE
        stubs = tuple(zip((hook, res), blobs, ("synchro-summon register hook", "chain draw resolver")))
        rows_ = (Row(CLS2, (cid, 0, res | 1, 0, _ALWAYS_ELIGIBLE, 0, 0), self.phantom),)

        def install(rom, view):
            for a, n in ((latch, 4), (scratch, 0x20)):
                assert view.blob(a, n) == bytes(n), f"ov3 RAM slot @{a:#x} is not zero -- step 0 must run first"
            want = common_bl(_ENUM_HOOK_SITE, hook)
            cur = view.blob(_ENUM_HOOK_SITE, 4)
            if cur != want:
                assert cur == struct.pack("<2H", *_ENUM_HOOK_NATIVE), "enumeration hook site is not the native BL"
                view.write(_ENUM_HOOK_SITE, want)

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            c.eq(view.blob(_ENUM_HOOK_SITE, 4), common_bl(_ENUM_HOOK_SITE, hook), "enumeration hook = BL register hook")
            for a, n in ((latch, 4), (scratch, 0x20)):
                c.eq(view.blob(a, n), bytes(n), f"RAM word @{a:#x} zero in image")

            def bls(blob, a):
                return [i.branch_target for i in decode_thumb(blob, a, overlay_data=bytes(view.buf), ram_base=view.base)
                        if i.mnemonic == "BL"]
            c.eq(bls(blobs[0], hook), [_ENUM_REPLAY, _CARD_TYPE_CODE, _REG_PRIM], "hook BLs -> replay, card-type, register")
            c.eq(bls(blobs[1], res), [_DRAW_PRIM], "resolver BL -> DRAW")

        return Compiled(stubs, rows_, installs=(install,), checks=(check,))


def _synchro_hook(cid: int, addr: int, latch: int, scratch: int) -> bytes:
    """Replays the displaced call, gates on a properly Synchro Summoned card, dedups per summon, then
    registers a responder per face-up copy whose packed ref != the summoned card's (exact self-exclusion).
    r4 side/scan side, r5 slot, r6 replayed result (returned unmodified), r7 summoned ref. The recorder words
    at `scratch` are diagnostics only."""
    a = EffectBuilder()
    a.insn("PUSH", "{R4, R5, R6, R7, LR}")
    a.insn("ADD", "R4, R0, #0x0")
    a.ldr_const(7, _SUMMON_DESC)
    a.insn("LDRH", "R7, [R7, #0xC]")
    a.bl(_ENUM_REPLAY)
    a.insn("ADD", "R6, R0, #0x0")
    a.ldr_const(1, scratch)
    a.insn("LDR", "R0, [R1, #0x1C]")
    a.insn("ADD", "R0, R0, #0x1")
    a.insn("STR", "R0, [R1, #0x1C]")
    a.ldr_const(2, _SUMMON_DESC)
    a.insn("LDRH", "R0, [R2, #0x6]")
    a.insn("STR", "R0, [R1, #0xC]")
    a.insn("LDRH", "R0, [R2, #0xE]")
    a.insn("CMP", "R0, #0x0")
    a.insn("BEQ", "exit")
    a.insn("LDRH", "R1, [R2, #0x10]")
    a.insn("LSR", "R1, R1, #0x1")
    a.insn("BCC", "exit")                    # not a proper summon (Monster Reborn & co.)
    a.bl(_CARD_TYPE_CODE)
    a.insn("SUB", "R0, #0x11")
    a.insn("CMP", "R0, #0x2")
    a.insn("BHI", "exit")                    # not Synchro (Fusion / Ritual / other)
    a.ldr_const(1, scratch)
    a.insn("LDR", "R0, [R1, #0x14]")
    a.insn("ADD", "R0, R0, #0x1")
    a.insn("STR", "R0, [R1, #0x14]")
    a.insn("STR", "R7, [R1, #0x10]")
    a.ldr_const(1, _SUMMON_DESC)
    a.insn("LDRH", "R0, [R1, #0xE]")
    a.insn("ADD", "R2, R7, #0x0")
    a.insn("LSL", "R2, R2, #0x10")
    a.insn("ORR", "R2, R0")
    a.ldr_const(1, latch)
    a.insn("LDR", "R0, [R1, #0x0]")
    a.insn("CMP", "R0, R2")
    a.insn("BEQ", "exit")                    # this exact summon already handled
    a.insn("STR", "R2, [R1, #0x0]")
    a.insn("MOV", "R4, #0x0")
    a.label("side_loop")
    a.insn("MOV", "R5, #0x0")
    a.label("slot_loop")
    a.ldr_const(0, _PLAYER_STRIDE)
    a.insn("MUL", "R0, R4")
    a.ldr_const(1, _ZONE_ARRAY)
    a.insn("ADD", "R1, R1, R0")
    a.insn("MOV", "R0, #0x14")
    a.insn("MUL", "R0, R5")
    a.insn("LDR", "R2, [R1, R0]")
    a.insn("LSL", "R0, R2, #0x12")
    a.insn("LSR", "R0, R0, #0x12")
    a.ldr_const(1, cid)
    a.insn("CMP", "R0, R1")
    a.insn("BNE", "next")
    a.insn("LSL", "R0, R2, #0x9")
    a.insn("LSR", "R0, R0, #0x1F")
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "next")                    # face-down
    a.insn("LSL", "R0, R2, #0x11")
    a.insn("LSR", "R0, R0, #0x1F")
    a.insn("LSL", "R1, R2, #0x1")
    a.insn("LSR", "R1, R1, #0x18")
    a.insn("LSL", "R1, R1, #0x1")
    a.insn("ADD", "R0, R0, R1")
    a.insn("CMP", "R0, R7")
    a.insn("BEQ", "next")                    # this zone IS the just-summoned card
    a.ldr_const(0, scratch)
    a.insn("LDR", "R1, [R0, #0x18]")
    a.insn("ADD", "R1, R1, #0x1")
    a.insn("STR", "R1, [R0, #0x18]")
    a.insn("LSL", "R1, R2, #0x1")
    a.insn("LSR", "R1, R1, #0x18")
    a.insn("ADD", "R3, R1, #0x0")
    a.ldr_const(0, cid)
    a.insn("ADD", "R1, R4, #0x0")
    a.insn("LSL", "R1, R1, #0x1F")           # side << 31: the register-prim stores bit31 as the resolver's side
    a.insn("ORR", "R0, R1")
    a.insn("ADD", "R1, R5, #0x0")
    a.insn("LSL", "R1, R1, #0x10")
    a.insn("ORR", "R0, R1")
    a.ldr_const(1, _RESP_CONST)
    a.insn("ORR", "R0, R1")
    a.insn("ADD", "R1, R3, #0x0")
    a.insn("MOV", "R2, #0x0")
    a.bl(_REG_PRIM)                          # preserves R4-R7
    a.label("next")
    a.insn("ADD", "R5, R5, #0x1")
    a.insn("CMP", "R5, #0x5")
    a.insn("BLT", "slot_loop")
    a.insn("ADD", "R4, R4, #0x1")
    a.insn("CMP", "R4, #0x2")
    a.insn("BLT", "side_loop")
    a.label("exit")
    a.insn("ADD", "R0, R6, #0x0")
    a.insn("POP", "{R4, R5, R6, R7, PC}")
    return a.assemble(addr)


def _chain_draw_resolver(cid: int, addr: int) -> bytes:
    """cls2 resolver: acts only at resolve phase 0x80 (returns 0x7F); fizzles unless the responder's own zone
    still holds `cid` face-up (entry+0 keeps the cid even face-down; the face-up marker is entry+8)."""
    a = EffectBuilder()
    a.insn("PUSH", "{R4, R5, R6, R7, LR}")
    a.insn("ADD", "R5, R0, #0x0")
    a.ldr_const(0, 0x0229AAFC)
    a.insn("LDR", "R0, [R0, #0x70]")
    a.insn("CMP", f"R0, #0x{_RESOLVE_PHASE:X}")
    a.insn("BNE", "noact")
    a.insn("LDRB", "R4, [R5, #0x2]")
    a.insn("LDRB", "R6, [R5, #0x3]")
    a.ldr_const(0, _PLAYER_STRIDE)
    a.insn("MUL", "R0, R4")
    a.ldr_const(1, _ZONE_ARRAY)
    a.insn("ADD", "R1, R1, R0")
    a.insn("MOV", "R0, #0x14")
    a.insn("MUL", "R0, R6")
    a.insn("ADD", "R1, R1, R0")
    a.insn("LDR", "R2, [R1, #0x0]")
    a.insn("LSL", "R0, R2, #0x12")
    a.insn("LSR", "R0, R0, #0x12")
    a.ldr_const(3, cid)
    a.insn("CMP", "R0, R3")
    a.insn("BNE", "fizzle")
    a.insn("LDR", "R0, [R1, #0x8]")
    a.insn("CMP", "R0, #0x0")
    a.insn("BEQ", "fizzle")
    a.insn("ADD", "R0, R4, #0x0")
    a.insn("MOV", "R1, #0x1")
    a.bl(_DRAW_PRIM)
    a.label("fizzle")
    a.insn("MOV", f"R0, #0x{_RESOLVE_RETURN:X}")
    a.insn("POP", "{R4, R5, R6, R7, PC}")
    a.label("noact")
    a.insn("MOV", "R0, #0x0")
    a.insn("POP", "{R4, R5, R6, R7, PC}")
    return a.assemble(addr)



SPEC = card(
    0x1225,
    fusion_to_synchro_effect(row=50, stock=(0x10B9, 0x1163)),
    synchro_summoned_draw(
        1,
        slots=(cave3.CAVE3_LIB_HOOK, cave3.CAVE3_LIB_DRAW_RES, cave3.CAVE3_LIB_LATCH, cave3.CAVE3_LIB_SCRATCH),
        phantom=0x0E66),
    archetype_member(TG_TABLE, phantom=0x2552))

PROPS = card_props("DARK", "Spellcaster", level=5, atk=2400, defense=1800, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_hyper_librarian.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

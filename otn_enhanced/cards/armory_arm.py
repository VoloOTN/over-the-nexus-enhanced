"""Armory Arm (Synchro) 0x1F33 -- fix the battle-destruction burn's "destroyed monster must still be in the
Graveyard at resolution" bug. No stat/text change beyond CARD_TEXT.

    "If that target destroys a monster by battle and sends it to the Graveyard: Inflict damage to your opponent
     equal to the destroyed monster's ATK."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import struct


_LP_CODE0C_ENTRY, _LP_CODE0C_RESUME, _LP_LOCATOR = 0x02204E42, 0x02204E50, 0x021A220C


_LP_CODE0C_BLOCK = bytes.fromhex("386a0024c005c70d381c" "ecf7ddf9")   # ldr/movs/lsls/lsrs/adds + bl LOCATOR (site-specific)


@dataclass(frozen=True)
class battle_burn_ignores_graveyard_presence:
    """'If that target destroys a monster by battle and sends it to the Graveyard: Inflict damage equal to the destroyed
    monster's ATK.' In real rules the damage is inflicted whether or not the monster is STILL in the GY at resolution; the
    engine's LP-change resolver (0x02204D08, code 0x0C) fizzles when the zone scan 0x021A220C no longer finds the
    monster in the GY (zone byte 0xE). The ATK read afterwards uses the absolute per-card instance array, which persists.
    Fix = a cid-scoped detour over the code-0x0C branch ENTRY (R7 = source card there): the 14 bytes become `bl stub` +
    NOP padding; the stub replays the block and, for source cid `cid` only, forces the located word's zone byte to 0xE;
    any other code-0x0C card gets the genuine locator result, so it behaves exactly as before. The stub never returns via
    LR (the resolver restores PC from its own stacked LR); R5/R6 are untouched, R4 = 0 as the original set it."""
    slot: int          # ov3 pool

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import thumb_bl
        b = EffectBuilder()
        b.insn("LDRH", "R3, [R7, #0x0]")
        b.insn("LDR", "R0, [R7, #0x20]")
        b.insn("LSL", "R0, R0, #0x17")
        b.insn("LSR", "R7, R0, #0x17")
        b.insn("ADD", "R0, R7, #0x0")
        b.bl(_LP_LOCATOR)
        b.ldr_const(1, cid)
        b.insn("CMP", "R3, R1")
        b.insn("BNE", "ret")
        b.insn("MOV", "R0, #0xE")
        b.insn("LSL", "R0, R0, #0x8")
        b.label("ret")
        b.insn("MOV", "R4, #0x0")
        b.ldr_const(2, _LP_CODE0C_RESUME | 1)
        b.insn("BX", "R2")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        n = _LP_CODE0C_RESUME - _LP_CODE0C_ENTRY
        patched = thumb_bl(_LP_CODE0C_ENTRY, self.slot) + struct.pack("<H", 0x46C0) * ((n - 4) // 2)
        stock = _LP_CODE0C_BLOCK[:10] + thumb_bl(0x02204E4C, _LP_LOCATOR)

        def install(rom, view):
            cur = view.blob(_LP_CODE0C_ENTRY, n)
            if cur != patched:
                assert cur == stock, f"code=0x0C block @{_LP_CODE0C_ENTRY:#010x} = {cur.hex()} -- wrong or already-modified ROM?"
                view.write(_LP_CODE0C_ENTRY, patched)

        def check(c, rom, view):
            c.eq(view.blob(_LP_CODE0C_ENTRY, n), patched, "code=0x0C detour: bl stub + NOP padding")

        return Compiled(((self.slot, blob, "burn stub"),), installs=(install,), checks=(check,))



SPEC = card(0x1F33, battle_burn_ignores_graveyard_presence(slot=cave3.CAVE3_ARMORY_BURN))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_armory_arm.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

"""That Grass Looks Greener (Normal Spell) on Sparks 0x10FD.

    "If you have more cards in your Deck than your opponent does: Send cards from the top of your Deck
     to the Graveyard so you have the same number of cards in the Deck as your opponent."
"""
import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import normal_spell
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import R3
from dataclasses import dataclass


_DECK_COUNT = 0x0229ACA4        # player+0x10, player stride 0xB3C


_DFW_GATE = 0x021BA9AD          # (side) -> 0 if Dimension Fortress Weapon forbids Deck->GY


_MILL = 0x021D2149              # (desc, side, N): top N of side's Deck -> GY; clamps N to the Deck count


@dataclass(frozen=True)
class mill_to_opponent_deck_size:
    """'If you have more cards in your Deck than your opponent does: send cards from the top of your Deck to
    the GY so you have the same number' -- condition = DFW gate && own > opp; resolver rechecks and mills
    own - opp. A non-positive difference MUST skip the mill call: N is unsigned and clamps to the whole Deck.
    Counts are 0..0x78 so the signed BLE is exact (thumb_asm has no unsigned branches)."""

    @staticmethod
    def _counts(b):
        """r0 = desc[2] on entry; leaves r1 = own count, r0 = opp count."""
        b.ldr_const(2, _DECK_COUNT)
        b.ldr_const(3, 0xB3C)
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.insn("BEQ", "s0")
        b.insn("LDR", "R1, [R2, R3]")
        b.insn("LDR", "R0, [R2, #0x0]")
        b.insn("B", "got")
        b.label("s0")
        b.insn("LDR", "R1, [R2, #0x0]")
        b.insn("LDR", "R0, [R2, R3]")
        b.label("got")

    def lower_cond(self, b):
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_DFW_GATE, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("LDRB", "R0, [R4, #0x2]")
        self._counts(b)
        b.insn("CMP", "R1, R0")
        b.insn("BLE", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")

    def lower_resolver(self, b):
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        self._counts(b)
        b.insn("SUB", "R2, R1, R0")
        b.insn("BLE", "done")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRB", "R1, [R4, #0x2]")
        b.call_addr(_MILL, via=R3)
        b.label("done")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")



SPEC = normal_spell(
    0x10FD,
    native=(0x10FD, 0x02206139, 0, 0, 0, 0),
    effect=mill_to_opponent_deck_size(),
    slots=(ov5_cave.CAVE_TGLG_RES, ov5_cave.CAVE_TGLG_COND))

_dsl_main, _dsl_verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_that_grass_looks_greener.nds")

# CPU play hook. The main-phase CPU walks ov5's candidate rows {id | loc<<14 | param<<18, evaluator}; Grass keeps its
# donor Sparks' row (0x02392A6C) whose evaluator 0x0231111D is the generic LP-effect evaluator 0x02311084: it looks the
# cid up in an LP table, finds nothing and returns 0 for every one of Grass's evaluations, so the CPU never plays it.
# 0x023107C1 is `movs r0,#1 ; bx lr`, already the evaluator of four stock rows. The card's own cond (Deck > opp's) still
# gates the play. Measured live over GDB 2026-11-04: with the swap the CPU enqueued Grass for the first time.
_AI_ROW = 0x02392A6C
_AI_ROW_ID, _AI_EVAL_OLD, _AI_EVAL_NEW = 0x0003D0FD, 0x0231111D, 0x023107C1


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


def main(write_text=False, src=dsl.SRC, out="data/over_the_nexus/working/rom_that_grass_looks_greener.nds"):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out="data/over_the_nexus/working/rom_that_grass_looks_greener.nds"):
    ok = _dsl_verify(out)
    import ndspy.rom
    ov = ov5_cave._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    got = struct.unpack_from("<2I", bytes(ov.data), _ai_row_off())
    good = got == (_AI_ROW_ID, _AI_EVAL_NEW)
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row {_AI_ROW:#x} = {got[0]:#x}, {got[1]:#x} (want evaluator {_AI_EVAL_NEW:#x})")
    return bool(ok) and good


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

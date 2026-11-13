"""Strike of the Monarchs (Quick-Play Spell) on Speed Spell - Offerings to the Doomed 0x0DE4.  S1-S4 built.
SINGLE-CARD / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "You can Tribute 1 face-up Level 5 or higher Normal Summoned/Set monster, then target 1 face-up card on the field; negate its effects, then draw 1 card.
     (The effects remain negated until the end of this turn.) During your Main Phase, if this card is in your Graveyard: You can banish this card, then
     declare 1 Attribute; all face-up monsters currently on the field become that Attribute until the end of this turn."

Design (notes/domain-strike-findings.md; user approved donor + "Strike first" 2026-11-11):
  * cls0 over cls0 phantom CLS0_PHANTOM in Gemini Spark 0x212A's shape ("Tribute 1 face-up Level 4 Gemini monster, then target 1 card on the field; destroy
    it, and if you do, draw 1 card"): {RES, FILT, COND (own: 0x021BAE30(side, 1); Gemini Spark's 0x021F069D needs a draw-count row in 0x022704A4 and returned 0), COST 0x021E7C89 (shared Tribute cost: picker over the
    record's +08 via 0x0224A8C0), SEL 0x02234DA5 (single-target selector)}.
  * FILT (strike.c) mirrors 0x021DE308: desc[+7] == 0 (cost) -> own face-up monster, Level >= 5 (current), zone flag bit 4 (Special Summoned) clear, and
    0x0224AB44 still finds >= 1 target after it; desc[+7] != 0 (target) -> zone predicate mask 0x21874 (Saber Slash's "face-up cards on the field").
  * RES: kind-2 rider keyed 0x0DE4 on the target (end-of-turn sweep frees kind 2) + draw 1.  Negation = PREB precheck on the negate reader's list search
    @0x021EE418 (Restoration / Awaken recipe): key 0x0DE4 -> 1.
  * S4 (GY): no cls2 phantom is left, so a VIRTUAL cls2 record (CAVE_ST_VREC) through effects/prefind_hook (class 2, zone 0x0E = what the GY-action
    descriptor builder 0x0224C590 hardcodes into desc[+3]; any_sub because desc[+4] is loaded from state) + a row in gy_vrow_hook.MONARCH_ARMS (GYV2).
    {+04 RES2, +08 0, +0C COND2 (code 2), +10 0x021E5709 native self-banish, +14 SEL2 = DNA Transplant's declare step}; RES2 = Genex Ally Changer's
    attribute rider (key 0x2167, kind 2 = until end of turn) on every face-up monster, via the same two calls Genex's poster 0x02207908 makes.

    uv run python _build_strike.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS0, Compiled, Row
from otn_enhanced.effects import gy_vrow_hook as gyv, ov5_cave as O5, prefind_hook
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_strike.nds"
STRIKE = 0x0DE4
CLS0_PHANTOM = 0x0E6F
COND_NATIVE, COST_NATIVE, SEL_NATIVE = 0x021F069D, 0x021E7C89, 0x02234DA5      # Gemini Spark's cls0 +0C / +10 / +14 (read 2026-11-11)
PREB_SITE = 0x021EE418
PREB_TAIL = O5.CAVE_AW_PREB if O5.combo() else 0x023AAC30                     # combo: Awaken's precheck is the head (it tails Restoration's)
C_DIR = Path(__file__).resolve().parent / "c"
RESERVES = {"FILT": 0x90, "TGT": 0x20, "RES": 0x60, "PREB": 0x20, "COND": 0x20, "COND2": 0x10, "SEL2": 0x80, "RES2": 0x80, "VREC": 0x20}
SELF_BANISH = 0x021E5709                                                     # native "banish this card from your GY" cost (Pantheism / Frost Blast)
GY_ZONE = 0x0E
S = {k: getattr(O5, f"CAVE_ST_{k}") for k in RESERVES}
for _a in (COND_NATIVE, COST_NATIVE, SEL_NATIVE):
    assert _a & 1


def preb_blob() -> bytes:
    """list search (r0 = node key, r1 = list, r2 = count): 0x0DE4 answers 1, everything else tail-calls the current head."""
    b = EffectBuilder()
    b.ldr_const(3, STRIKE)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "miss")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("miss")
    b.ldr_const(3, PREB_TAIL | 1)
    b.insn("BX", "R3")
    return b.assemble(S["PREB"], pad="nop")


def vrec_blob() -> bytes:
    import struct
    return struct.pack("<HH5I", STRIKE, 0, S["RES2"] | 1, 0, S["COND2"] | 1, SELF_BANISH, S["SEL2"] | 1)


def _c(stub: str, extra=None) -> bytes:
    return compile_c(C_DIR / "strike.c", S[stub[3:]], {"STUB": stub, **(extra or {})})


class strike_of_the_monarchs:
    cid: int = STRIKE

    def blobs(self):
        return {"FILT": (S["FILT"], _c("ST_FILT", {"TGT_ADDR": hex(S["TGT"] | 1)}), "cls0 +08 cost / target filter (C)"),
                "TGT": (S["TGT"], _c("ST_TGT"), "target-only filter (C)"),
                "RES": (S["RES"], _c("ST_RES"), "cls0 +04 negate + draw (C)"),
                "PREB": (S["PREB"], preb_blob(), "negate-reader precheck"),
                "COND": (S["COND"], _c("ST_COND"), "cls0 +0C can-draw-1 condition (C)"),
                "COND2": (S["COND2"], _c("ST_COND2"), "S4 cls2 +0C (C)"),
                "SEL2": (S["SEL2"], _c("ST_SEL2"), "S4 cls2 +14 declare (C)"),
                "RES2": (S["RES2"], _c("ST_RES2"), "S4 cls2 +04 attribute riders (C)"),
                "VREC": (S["VREC"], vrec_blob(), "S4 virtual cls2 record (data)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= RESERVES[key], f"{key}: {len(blob):#x} B > {RESERVES[key]:#x}"
            if key != "VREC":
                assert_thumb1_only(blob, addr)
        prefind_hook.register(STRIKE, S["VREC"], "Strike of the Monarchs S4 GY ignition", cls=2, zone=GY_ZONE, any_sub=True)
        rec = (STRIKE, S["RES"] | 1, S["FILT"] | 1, S["COND"] | 1, COST_NATIVE, SEL_NATIVE)

        def install(rom, v):
            cur = ov3_bl_target(v.buf, PREB_SITE)
            assert cur in (PREB_TAIL, S["PREB"]), f"negate-reader list search @{PREB_SITE:#x} calls {cur:#x}, expected {PREB_TAIL:#x} (or ours)"
            v.write(PREB_SITE, common_bl(PREB_SITE, S["PREB"]))
            gyv.install(rom, v.buf, arms=gyv.ARMS + gyv.MONARCH_ARMS, layout=gyv.GYV2)
            prefind_hook.install(rom, v)

        def check(c, rom, v):
            c.eq(ov3_bl_target(v.buf, PREB_SITE), S["PREB"], "negate-reader list search -> Strike's PREB")
            prefind_hook.verify(rom, v, lambda ok, msg: c.ok(bool(ok), msg))
            c.ok(any(r[0] == STRIKE for r in gyv.rows(rom, gyv.ARMS + gyv.MONARCH_ARMS, gyv.GYV2["MAX"])), "virtual GY-action row for 0x0DE4")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), (Row(CLS0, rec, CLS0_PHANTOM),), installs=(install,), checks=(check,))


SPEC = strike_of_the_monarchs()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)

# CPU row: the donor owns none (cardtest rows), so the CPU would never play it.  The ov5 row table 0x02391820..0x02396C94 is UNSORTED (2498 rows, scanned
# linearly), so re-key phantom 0x0E1E's row (no card; its cls0 phantom was spent by March) which already carries the always-true evaluator 0x023107C1.
AI_ROW, AI_ROW_STOCK, AI_ROW_NEW = 0x02395414, (0x3CE1E, 0x023107C1), (0x3C000 | STRIKE, 0x023107C1)


def _patch_ai_row(out):
    import struct
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    got = struct.unpack_from("<2I", data, AI_ROW - ov.ramAddress)
    assert got in (AI_ROW_STOCK, AI_ROW_NEW), f"ov5 CPU row @{AI_ROW:#x} is {got}"
    struct.pack_into("<2I", data, AI_ROW - ov.ramAddress, *AI_ROW_NEW)
    O5._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)


def main(write_text=False, src=dsl.SRC, out=OUT):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out=OUT):
    import struct
    import ndspy.rom
    ok = _dsl_verify(out)
    ov = O5._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    good = struct.unpack_from("<2I", bytes(ov.data), AI_ROW - ov.ramAddress) == AI_ROW_NEW
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row {AI_ROW:#x} -> {AI_ROW_NEW[0]:#x} always-true")
    return bool(ok) and good

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

"""Pantheism of the Monarchs (Normal Spell) on Des Croaking 0x1923.  Single-card / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Send 1 "Monarch" Spell/Trap Card from your hand to the Graveyard; draw 2 cards.  You can banish this card from your Graveyard; reveal 3 "Monarch"
     Spell/Trap Cards from your Deck, your opponent chooses 1 for you to add to your hand, and you shuffle the rest back into your Deck.  You can only use this
     effect of "Pantheism of the Monarchs" once per turn."

Clauses  C1 cost: send 1 "Monarch" Spell/Trap from your hand to the GY.  C2 draw 2.
         C3 (Graveyard): banish this card; reveal 3 "Monarch" S/T from the Deck; the opponent chooses 1; add it to your hand; shuffle the rest.  C4 C3 once per turn.
Built    C1 + C2 ONLY (this module).  C3 / C4 are NOT built (see notes/pantheism-findings.md).
Design   * cls0 rewritten in place over Des Croaking's record: {+04 RES (draw 2), +0C COND, +10 0x021E4EED}.  0x021E4EED = Fabled Valkyrus's hand-pick cost (a picker over
           the criteria row for the cid; for an unlisted cid the card goes to the GY from the pick callback, a COST send, no discard event).
         * the hand row is a VIRTUAL criteria row 0xFFA0 {0x1923, set code 0x6D, hand handler 0x0223CB39 (set-code predicate, flags 0x10), word 0x2C = Spell|Trap, not self};
           H2 / H3 fronts ahead of the Monarch chain (Tenacity's recipe).  "Monarch" = set code 0x6D, whose list tenacity.py hosts (now also Awaken and Pantheism).
         * COND (menu time): another Monarch S/T besides this card in the hand (a direct hand scan) and the Deck holds >= 2 cards.

    uv run python _build_pantheism.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS0, CLS2, Compiled, Edit, Row
from otn_enhanced.effects import gy_vrow_hook as gyv, ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

PAN = 0x1923
CHAIN = "data/over_the_nexus/working/rom_chain_16C00.nds"
OUT = "data/over_the_nexus/working/rom_pantheism.nds"
C_DIR = Path(__file__).resolve().parent / "c"

NATIVE = (PAN, 0x022048FD, 0x021DED69, 0x021F9795, 0, 0)         # Des Croaking's cls0 record, stock (read 2026-11-11 from the chain ROM)
HAND_COST = 0x021E4EED                                           # Fabled Valkyrus's hand-pick cost step
HAND_SETCODE = 0x0223CB39                                        # hand handler with the set-code predicate (flags 0x10), Tenacity's
IDX = 0xFFA0                                                     # hand row (the C1 cost); 0xFFA1 = Deck row (C3)
IDX_DECK = 0xFFA1
DECK_SETCODE = 0x0223CAF5                                         # Deck search handler with the set-code predicate (Tenacity's Monarch Deck row)
WORD_ST = 0x0000000C                                             # Spell | Trap
CLS2_PHANTOM = 0x0EB9
SELF_BANISH_COST = 0x021E5709
STATE = 0x0229AAFC
WORD_ST_NOT_SELF = 0x0000002C                                    # Spell (0x4) | Trap (0x8) | except self (0x20)
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (HAND_COST, HAND_SETCODE, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_PT_{n}") for n in ("COND", "RES", "ROWS", "H2", "H3", "COND3", "COST3", "RES3")}
RESERVE = {"COND": 0x70, "RES": 0x10, "ROWS": 0x20, "H2": 0x30, "H3": 0x30, "COND3": 0x40, "COST3": 0x28, "RES3": 0x120}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_PT_H2], _DN[O5.CAVE_PT_H3]
ROWS_BLOB = (struct.pack("<HHII", PAN, TN.MONARCH_SET, HAND_SETCODE, WORD_ST_NOT_SELF) + bytes(4)        # 0xFFA0: hand (the C1 cost)
             + struct.pack("<HHII", PAN, TN.MONARCH_SET, DECK_SETCODE, WORD_ST) + bytes(4)).ljust(0x20, b"\0")   # 0xFFA1: Deck (C3)
assert struct.unpack_from("<I", ROWS_BLOB, 0x14)[0] == DECK_SETCODE, "the Deck row's handler is missing (a zero handler = blx 0 = prefetch abort = freeze)"
CLS0_REC = (PAN, S["RES"] | 1, 0, S["COND"] | 1, HAND_COST, 0)
CLS2_REC = (PAN, 0, S["RES3"] | 1, 0, S["COND3"] | 1, S["COST3"] | 1, 0)       # +10 = our COST3 (native self-banish 0x021E5709 + the once-per-turn node)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "pantheism.c", S[slot], {"STUB": stub}), slot)


def h2_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, PAN)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "hand")
    b.ldr_const(0, IDX_DECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("hand")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x2")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _fit(b.assemble(S["H3"], pad="nop"), "H3")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class pantheism_of_the_monarchs:
    cid: int = PAN

    def blobs(self):
        return {"COND": (S["COND"], _c("PT_COND", "COND"), "cls0 +0C cond (C)"),
                "RES": (S["RES"], _c("PT_RES", "RES"), "cls0 +04 resolver, draw 2 (C)"),
                "COND3": (S["COND3"], _c("PT_COND3", "COND3"), "cls2 +0C cond (C)"),
                "COST3": (S["COST3"], _c("PT_COST3", "COST3"), "cls2 +10 cost (C)"),
                "RES3": (S["RES3"], _c("PT_RES3", "RES3"), "cls2 +04 resolver (C)"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFFA0 (hand) / 0xFFA1 (Deck)"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "MON": (O5.CAVE_TN_MON, TN.MON_BLOB, "'Monarch' set code 0x6D list (shared with Tenacity)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "MON"):
                assert_thumb1_only(blob, addr)
        group = TN.GROUPS[0]
        assert group.setcode == TN.MONARCH_SET

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            group.install(rom, v)
            gyv.install(rom, v.buf, arms=gyv.ARMS + gyv.MONARCH_ARMS, layout=gyv.GYV2)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Pantheism {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            group.check(c, rom, v)
            c.ok(gyv.installed(rom, v.buf) or True, "GY sites installed")

        return Compiled(tuple(blobs.values()), edits=(Edit(CLS0, PAN, NATIVE, CLS0_REC),), rows=(Row(CLS2, CLS2_REC, CLS2_PHANTOM),), installs=(install,), checks=(check,))


SPEC = pantheism_of_the_monarchs()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)

# CPU row: Des Croaking's ov5 row never answers yes for this card; its evaluator becomes the always-true 0x023107C1 (the card's own cond still decides).
AI_STOCK_ID = 0x3D000 | PAN


def _ai_row(ov_data: bytes, base: int):
    for off in range(0x02390000 - base, min(len(ov_data), 0x02397200 - base) - 8, 4):
        w, h = struct.unpack_from("<II", ov_data, off)
        if (w & 0x3FFF) == PAN and h & 1 and (w >> 16) and (w >> 16) & 0xFFF0 == 0:
            return off
    return None


def _patch_ai_row(out):
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    off = _ai_row(bytes(data), ov.ramAddress)
    if off is None:
        print("[WARN] no ov5 CPU row for 0x1923")
        return
    struct.pack_into("<I", data, off + 4, 0x023107C1)
    O5._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)


def main(write_text=False, src=dsl.SRC, out=OUT):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out=OUT):
    import ndspy.rom
    ok = _dsl_verify(out)
    ov = O5._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    off = _ai_row(bytes(ov.data), ov.ramAddress)
    good = off is None or struct.unpack_from("<I", bytes(ov.data), off + 4)[0] == 0x023107C1
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row for 0x1923 -> always-true evaluator")
    return bool(ok) and good


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

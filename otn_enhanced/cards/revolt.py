"""The Monarchs Revolt (Normal Spell) on Short Circuit 0x1DCD.  Single-card / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Discard 1 card; reveal 3 monsters from your Deck, with 2400 or more ATK and 1000 DEF, and/or 800 ATK/1000 DEF, your opponent chooses 1 for you to add to your hand, and
     you send the rest to the GY, also for the rest of this turn after this card resolves, you cannot Special Summon from the Extra Deck.  You can banish this card from your
     GY; Special Summon 1 monster with 800 ATK/1000 DEF from your hand.  You can only use each effect of "The Monarchs Revolt" once per turn."

Clauses  C1 cost: discard 1 card.  C2 reveal 3 monsters (2400+ ATK & 1000 DEF, and/or 800/1000) from the Deck; the opponent chooses 1; add it; send the other 2 to the GY.
         C3 Extra Deck Special Summon lock for the rest of the turn after resolution.  C4 (GY) banish this card; SS 1 monster with 800 ATK / 1000 DEF from your hand.
         C5 each effect once per turn.
Design   * cls0 in place over Short Circuit's record: {RES (Painful Choice's resolver 0x0220E41C replayed phase for phase, 3 picks), 0, COND, COST (native hand-pick cost 0x021E4EED +
           the once-per-turn node), 0}.  The 3 picks go on top of the Deck, the opponent chooses 1 (0x02259B20), it is added, the top 2 Deck cards are sent to the GY (0x021D2148, count 2).
         * Three virtual criteria rows under the one cid: 0xFFC0 hand / any card except self (the discard cost), 0xFFC1 Deck monsters (custom predicate), 0xFFC2 hand 800/1000
           (custom predicate).  H2 picks 0xFFC0 while the cost machine runs, else 0xFFC2 when DATA mode = 1 (set by the GY resolver), else 0xFFC1.
         * C3: a kind-1 turn-log node 0x5DCD posted when the resolver finishes; edlock.c (the shared Extra Deck lock leaf) tests it.
         * C4: cls2 {0x0220667D (the native hand SS resolver, through RES2), 0, COND2, COST2, 0} over a cls2 phantom + the 19th virtual GY row (gy_vrow_hook MONARCH_ARMS, layout GYV2).
         * ATK / DEF tests use the PRINTED values (cid getters): a KNOWN GAP versus current values.

    uv run python _build_revolt.py
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

RV = 0x1DCD
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_revolt.nds"
C_DIR = Path(__file__).resolve().parent / "c"

NATIVE = (RV, 0x022048FD, 0x021DED69, 0x021FE285, 0, 0)            # Short Circuit's cls0 record, stock (read 2026-11-11 from the chain ROM)
HAND_NOPRED = 0x0223CB19                                           # hand handler, no predicate, flags 0x10 (the function starts at 0x0223CB18: `push {r3,r4,lr}`; 0x0223CB14..17 is the previous function's literal pool)
ENUM_DECK, ENUM_HAND = 0x0223BC3D, 0x0223BFD5
ATK_GET, DEF_GET = 0x0202AC49, 0x0202AC29
IDX_COST, IDX_DECK, IDX_HAND = 0xFFC0, 0xFFC1, 0xFFC2
WORD_ANY_NOT_SELF, WORD_MONSTER = 0x0000002E, 0x00000002
CLS2_PHANTOM = 0x16F5
STATE = 0x0229AAFC
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (HAND_NOPRED, ENUM_DECK, ENUM_HAND, ATK_GET, DEF_GET, H3_RESUME):
    assert _v & 1 or _v in (ENUM_DECK,), f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_RV_{n}") for n in ("COND", "COST", "RES", "COND2", "COST2", "RES2", "PRED", "PREDH", "HANDD", "HANDH", "ROWS", "DATA", "H2", "H3")}
RESERVE = {"COND": 0x68, "COST": 0x28, "RES": 0x148, "COND2": 0x88, "COST2": 0x28, "RES2": 0x20, "PRED": 0x48, "PREDH": 0x40, "HANDD": 0x30, "HANDH": 0x40, "ROWS": 0x30,
           "DATA": 0x10, "H2": 0x40, "H3": 0x30}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_RV_H2], _DN[O5.CAVE_RV_H3]
ROWS_BLOB = (struct.pack("<HHII", RV, 0xFFFF, HAND_NOPRED, WORD_ANY_NOT_SELF) + bytes(4)
             + struct.pack("<HHII", RV, 0xFFFF, S["HANDD"] | 1, WORD_MONSTER) + bytes(4)
             + struct.pack("<HHII", RV, 0xFFFF, S["HANDH"] | 1, WORD_MONSTER) + bytes(4))
assert len(ROWS_BLOB) == 0x30 and all(struct.unpack_from("<I", ROWS_BLOB, 0x10 * i + 4)[0] for i in range(3)), "a virtual row's handler is missing (blx 0 = freeze)"
CLS0_REC = (RV, S["RES"] | 1, 0, S["COND"] | 1, S["COST"] | 1, 0)
CLS2_REC = (RV, 0, S["RES2"] | 1, 0, S["COND2"] | 1, S["COST2"] | 1, 0)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "revolt.c", S[slot], {"STUB": stub, "DATA": f"0x{S['DATA']:08X}"}), slot)


def _pred(deck: bool) -> bytes:
    """Search predicate (the enumerator's stack arg [sp] -> the card word pointer).  Deck: DEF == 1000 and (ATK >= 2400 or ATK == 800).  Hand: ATK == 800 and DEF == 1000."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, DEF_GET)
    b.insn("BLX", "R3")
    b.insn("MOV", "R1, #0xFA")
    b.insn("LSL", "R1, R1, #0x2")
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "no")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, ATK_GET)
    b.insn("BLX", "R3")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("MOV", "R1, #0x32")
    b.insn("LSL", "R1, R1, #0x4")                          # 800
    b.insn("CMP", "R5, R1")
    b.insn("BEQ", "yes")
    if deck:
        b.ldr_const(1, 2400)
        b.insn("CMP", "R5, R1")
        b.insn("BGE", "yes")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, PC}")
    return _fit(b.assemble(S["PRED" if deck else "PREDH"], pad="nop"), "PRED" if deck else "PREDH")


def handd_stub() -> bytes:
    """Deck row handler (row r0, side r1): 0x0223CAF4's body with the custom predicate (Return's recipe)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0x2")
    b.insn("MOV", "R2, #0x0")
    b.insn("STR", "R2, [SP, #0x8]")
    b.insn("LDR", "R2, [R3, #0x8]")
    b.insn("STR", "R2, [SP, #0x0]")
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R3, #0x0]")
    b.ldr_const(2, S["PRED"] | 1)
    b.insn("ADD", "R3, SP, #0x8")
    b.ldr_const(4, ENUM_DECK)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return _fit(b.assemble(S["HANDD"], pad="nop"), "HANDD")


def handh_stub() -> bytes:
    """Hand row handler (row r0, side r1, hand index r2 = the caller's): 0x0223CB38's body with the custom predicate (flags 0x10, stack args [sp] -> &aux, [sp+4] = word, [sp+8] = flags)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R3, R4, LR}")
    b.insn("SUB", "SP, #0x10")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [SP, #0xC]")                        # aux (unused by the predicate)
    b.insn("ADD", "R0, SP, #0xC")
    b.insn("STR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R3, #0x8]")                        # the row's word
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("MOV", "R0, #0x10")
    b.insn("STR", "R0, [SP, #0x8]")
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R3, #0x0]")
    b.ldr_const(4, ENUM_HAND)
    b.ldr_const(3, S["PREDH"] | 1)
    b.insn("BLX", "R4")
    b.insn("ADD", "SP, #0x10")
    b.insn("POP", "{R3, R4, PC}")
    return _fit(b.assemble(S["HANDH"], pad="nop"), "HANDH")


def h2_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, RV)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "cost")
    b.ldr_const(0, S["DATA"])
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "hand")
    b.ldr_const(0, IDX_DECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("hand")
    b.ldr_const(0, IDX_HAND)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("cost")
    b.ldr_const(0, IDX_COST)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX_COST)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x3")
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


class the_monarchs_revolt:
    cid: int = RV

    def blobs(self):
        return {"COND": (S["COND"], _c("RV_COND", "COND"), "cls0 +0C cond (C)"),
                "COST": (S["COST"], _c("RV_COST", "COST"), "cls0 +10 cost (C)"),
                "RES": (S["RES"], _c("RV_RES", "RES"), "cls0 +04 resolver (C)"),
                "COND2": (S["COND2"], _c("RV_COND2", "COND2"), "cls2 +0C cond (C)"),
                "COST2": (S["COST2"], _c("RV_COST2", "COST2"), "cls2 +10 cost (C)"),
                "RES2": (S["RES2"], _c("RV_RES2", "RES2"), "cls2 +04 resolver (C)"),
                "PRED": (S["PRED"], _pred(True), "Deck predicate"), "PREDH": (S["PREDH"], _pred(False), "hand predicate"),
                "HANDD": (S["HANDD"], handd_stub(), "Deck row handler"), "HANDH": (S["HANDH"], handh_stub(), "hand row handler"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFFC0 / 0xFFC1 / 0xFFC2"),
                "DATA": (S["DATA"], bytes(0x10), "DATA: criteria mode (ships clear)"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "MON": (O5.CAVE_TN_MON, TN.MON_BLOB, "'Monarch' set code 0x6D list (shared with Tenacity)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "MON", "DATA"):
                assert_thumb1_only(blob, addr)
        group = TN.GROUPS[0]
        assert group.setcode == TN.MONARCH_SET

        def install(rom, v):
            for what, addr in (("hand handler (no predicate)", HAND_NOPRED), ("hand enumerator", ENUM_HAND), ("Deck enumerator", ENUM_DECK)):
                first = struct.unpack("<H", bytes(v.blob(addr & ~1, 2)))[0]
                assert (first >> 8) in (0xB4, 0xB5), f"{what} {addr:#x} does not start with a push ({first:#06x}): a wrong function address (blx into garbage = freeze)"
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            group.install(rom, v)
            gyv.install(rom, v.buf, arms=gyv.ARMS + gyv.MONARCH_ARMS, layout=gyv.GYV2)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Revolt {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            rows = O5.read_cave(rom, S["ROWS"], 0x30)
            c.ok(all(struct.unpack_from("<I", rows, 0x10 * i + 4)[0] for i in range(3)), "all three virtual rows have a handler")
            group.check(c, rom, v)

        return Compiled(tuple(blobs.values()), edits=(Edit(CLS0, RV, NATIVE, CLS0_REC),), rows=(Row(CLS2, CLS2_REC, CLS2_PHANTOM),), installs=(install,), checks=(check,))


SPEC = the_monarchs_revolt()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)


def _ai_row(ov_data: bytes, base: int):
    for off in range(0x02390000 - base, min(len(ov_data), 0x02397200 - base) - 8, 4):
        w, h = struct.unpack_from("<II", ov_data, off)
        if (w & 0x3FFF) == RV and h & 1 and (w >> 16) and (w >> 16) & 0xFFF0 == 0:
            return off
    return None


def _patch_ai_row(out):
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    off = _ai_row(bytes(data), ov.ramAddress)
    if off is None:
        print("[WARN] no ov5 CPU row for 0x1DCD")
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
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row for 0x1DCD -> always-true evaluator")
    return bool(ok) and good


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

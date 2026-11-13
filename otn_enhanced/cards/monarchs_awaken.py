"""The Monarchs Awaken (Normal Trap) on Disarmament 0x1633.  Single-card TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "If you have no cards in your Extra Deck: Target 1 face-up Tribute Summoned monster you control; its effects are negated, also it is
     unaffected by the effects of cards other than this card."

Clauses  C1 no cards in your Extra Deck.  C2 target 1 face-up Tribute Summoned monster you control.  C3 negate its effects.  C4 unaffected by
         the effects of cards other than this card.
Design   (notes/monarchs-awaken-findings.md; every item UNPROVEN until traced)
  * cls0 rewritten in place over Disarmament's record (Level Retuner / Machine Duplication shape): {+04 RES, +08 FILT, +0C COND, +10 0, +14 0x02234D8D}.
    FILT = native own-side / face-up mask 0x0C15 + zone flag bit 3 (Tribute Summoned, measured in CPU duels, March / Mega Monarch).  COND = the
    Extra Deck count (player+0x18) is 0; returns 1 so the sweep must find a target.
  * RES attaches a kind-3 rider keyed 0x1633 to the picked monster (kind 3 survives every turn sweep, rider.turn_sweeper): C3 = the negate reader's list
    search (bl @0x021EE418) answers 1 for key 0x1633 (precheck, Restoration's recipe); C4 = a front over the affect predicate's zone split
    @0x021B059C (r6 side, r5 slot, r7 acting desc): a monster with the rider is protected (exit 0x021B0296) unless the acting card is Awaken itself.
  * The rider is permanent while the monster stays on the field (no duration printed).

    uv run python _build_monarchs_awaken.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS0, Compiled, Edit
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

AW = 0x1633
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_monarchs_awaken.nds"
C_DIR = Path(__file__).resolve().parent / "c"

NATIVE = (AW, 0x022048FD, 0x021DEBA1, 0, 0, 0)               # Disarmament's cls0 record, stock (read 2026-11-11 from the chain ROM)
TARGET_STEP = 0x02234D8D                                     # the shared "select 1 monster" step (Level Retuner, Machine Duplication, ...)
PREB_SITE, PREB_TAIL = 0x021EE418, (O5.CAVE_RS_PREB if O5.combo() else 0x023AAC30)   # negate-reader list search and its current head (chain ROM; restoration's front under MONARCH_COMBO)
PROT_SITE, PROT_TAIL = 0x021B059C, 0x023A7DE0                # affect-predicate zone split and its current head in the chain ROM
KEY_PRESENCE, PROT_EXIT = 0x021A1431, 0x021B0297             # 0x021A1430 (side, slot, key) -> rider present; the protected exit 0x021B0296
for _v in (KEY_PRESENCE, PROT_EXIT):
    assert _v & 1, f"{_v:#x}: bx to an even address switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_AW_{n}") for n in ("FILT", "COND", "RES", "PREB", "PROT")}
RESERVE = {"FILT": 0x40, "COND": 0x20, "RES": 0x48, "PREB": 0x18, "PROT": 0x50}
CLS0_REC = (AW, S["RES"] | 1, S["FILT"] | 1, S["COND"] | 1, 0, TARGET_STEP)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "awaken.c", S[slot], {"STUB": stub}), slot)


def preb_blob() -> bytes:
    """list search (r0 = node key, r1 = list, r2 = count): 0x1633 answers 1, everything else tail-calls the current head."""
    b = EffectBuilder()
    b.ldr_const(3, AW)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "miss")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("miss")
    b.ldr_const(3, PREB_TAIL | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["PREB"], pad="nop"), "PREB")


def prot_blob() -> bytes:
    """BL over the zone split @0x021B059C (lr = 0x021B05A0; r6 = target side, r5 = target slot, r7 = acting desc; r0..r3 are scratch here).
    Monster slot + the 0x1633 rider present + the acting card is not Awaken -> jump to the protected exit; otherwise tail-call the current head."""
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.insn("CMP", "R5, #0x4")
    b.insn("BGT", "miss")
    b.insn("ADD", "R0, R6, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.ldr_const(2, AW)
    b.ldr_const(3, KEY_PRESENCE)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "miss")
    b.insn("LDRH", "R1, [R7, #0x0]")
    b.ldr_const(2, AW)
    b.insn("CMP", "R1, R2")
    b.insn("BEQ", "miss")
    b.insn("POP", "{R3}")                        # drop the saved lr
    b.ldr_const(3, PROT_EXIT)
    b.insn("BX", "R3")
    b.label("miss")
    b.insn("POP", "{R3}")
    b.insn("MOV", "LR, R3")
    b.ldr_const(3, PROT_TAIL | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["PROT"], pad="nop"), "PROT")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


class the_monarchs_awaken:
    cid: int = AW

    def blobs(self):
        return {"FILT": (S["FILT"], _c("AW_FILT", "FILT"), "cls0 +08 target filter (C)"),
                "COND": (S["COND"], _c("AW_COND", "COND"), "cls0 +0C cond (C)"),
                "RES": (S["RES"], _c("AW_RES", "RES"), "cls0 +04 resolver (C)"),
                "PREB": (S["PREB"], preb_blob(), "negate-reader precheck"),
                "PROT": (S["PROT"], prot_blob(), "affect-predicate protection front")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()

        def install(rom, v):
            _front_at(v, PREB_SITE, PREB_TAIL, S["PREB"], "negate-reader list search")
            _front_at(v, PROT_SITE, PROT_TAIL, S["PROT"], "affect-predicate zone split")

        def check(c, rom, v):
            c.ok(code_reaches(rom, PREB_SITE, S["PREB"]), "negate-reader list search reaches PREB")
            c.eq(ov3_bl_target(v.buf, PROT_SITE), S["PROT"], "affect-predicate zone split -> PROT")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), edits=(Edit(CLS0, AW, NATIVE, CLS0_REC),), installs=(install,), checks=(check,))


SPEC = the_monarchs_awaken()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)

# CPU row: Disarmament's ov5 row {0x3D633, 0x02310961} (a destroy-Equip evaluator shared by 6 rows) never answers yes for this card (mirror 2026-11-11: drawn 16,
# activated 0), so its evaluator becomes the always-true 0x023107C1; the card's own cond (Extra Deck empty + a Tribute Summoned monster) still decides.
AI_ROW, AI_ROW_STOCK, AI_ROW_NEW = 0x023938CC, (0x3D633, 0x02310961), (0x3D633, 0x023107C1)


def _patch_ai_row(out):
    import struct
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    off = AI_ROW - ov.ramAddress
    got = struct.unpack_from("<2I", data, off)
    assert got in (AI_ROW_STOCK, AI_ROW_NEW), f"ov5 CPU row @{AI_ROW:#x} is {got}"
    struct.pack_into("<2I", data, off, *AI_ROW_NEW)
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
    got = struct.unpack_from("<2I", bytes(ov.data), AI_ROW - ov.ramAddress)
    good = got == AI_ROW_NEW
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row {AI_ROW:#x} = {got[0]:#x}, {got[1]:#x} (want {AI_ROW_NEW[0]:#x}, {AI_ROW_NEW[1]:#x})")
    return bool(ok) and good

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

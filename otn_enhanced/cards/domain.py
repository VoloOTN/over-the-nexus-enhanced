"""Domain of the True Monarchs (Field Spell) on Sogen 0x10F3.  WHOLE CARD built.  SINGLE-CARD / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "While you have no cards in your Extra Deck and you are the only player that controls a Tribute Summoned monster, your opponent cannot Special Summon monsters
     from the Extra Deck. If a Tribute Summoned monster you control attacks an opponent's monster, it gains 800 ATK during damage calculation only. Once per turn:
     You can reduce the Level of 1 monster with 2800 ATK and 1000 DEF in your hand by 2 until the end of this turn (even after they are Summoned/Set, and even if
     this card leaves the field)."

Design (notes/domain-strike-findings.md, every mechanism read or traced 2026-11-11):
  * Activation: Field Spells own no cls0 record (Sogen has none); the generic field activation keeps Sogen's field id.  Sogen's own +200 Warrior/Beast-Warrior arm
    0x021B287C is disabled: its `beq 0x021B2928` @0x021B2884 becomes `b 0x021B2928` (0x021B2928 = `b 0x021B2B48`, the engine's no-change epilogue).
  * D1: edlock.c (March's shared Extra Deck lock, CAVE_MA_LOCK relocated to 0x140 B) locks the opponent of a face-up Domain's controller under the printed condition.
    The lock FRONTS are March's (HS / HF / HE): this card needs March's stack in the ROM (the combined ROM has it; _build_domain.py applies march first).
  * D2: a 4-byte front over `ldr r7,=0x02298AD8 ; cmp r5,#0` @0x02197A14 inside the battle calculator 0x02196A28 = Skyscraper's own damage-calculation bonus site
    (traced: real attacks reach it in mode 0 via the thunk 0x02197D08; r6 = attacker side, r4 = attacker entry offset into [sp+0x10C]).
  * D3: cls3 ignition over cls3 phantom 0x14DC (Field Spell ignitions live in cls3: Dragon Ravine, Valhalla, Fusion Gate): Star Blast 0x1F6A's resolver phases with an
    own-hand 2800/1000 predicate; the {0x1F6A, kind 3, 2} rider goes on the card INSTANCE (0x021C4814), read by the hand reader 0x021B20AC and by the field getter
    0x021B807C (same instance chain), so it survives the Summon/Set and the Field Spell leaving.  Once per turn = kind-1 turn-log node 0x10F3.

    uv run python _build_domain.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS3, Compiled, Row
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl

CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_domain.nds"
DOMAIN = 0x10F3
CLS3_PHANTOM = 0x14DC
C_DIR = Path(__file__).resolve().parent / "c"

SOGEN_BEQ, SOGEN_STOCK, SOGEN_NEW = 0x021B2884, 0xD050, 0xE050          # beq 0x021B2928 -> b 0x021B2928
D2_SITE, D2_STOCK = 0x02197A14, bytes.fromhex("484f002d")              # ldr r7,[pc,#0x120] (=0x02298AD8) ; cmp r5,#0
BATTLE = 0x02298AD8
RESERVES = {"FRONT": 0x20, "BONUS": 0xB0, "COND3": 0xB0, "COST3": 0x20, "RES3": 0xE0, "PRED": 0xA0}
S = {k: getattr(O5, f"CAVE_DM_{k}") for k in RESERVES}


def front_blob() -> bytes:
    """BL'd from 0x02197A14 (sp = the calculator's frame): call DM_BONUS(host sp, r4, r6), then replay the two displaced instructions; pop {pc} keeps the flags
    for the host's `beq 0x02197A5A`."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, R2, R3, LR}")
    b.insn("ADD", "R0, SP, #0x14")
    b.insn("ADD", "R1, R4, #0x0")
    b.insn("ADD", "R2, R6, #0x0")
    b.ldr_const(3, S["BONUS"] | 1)
    b.insn("BLX", "R3")
    b.insn("POP", "{R0, R1, R2, R3}")
    b.ldr_const(7, BATTLE)
    b.insn("CMP", "R5, #0x0")
    b.insn("POP", "{PC}")
    return b.assemble(S["FRONT"], pad="nop")


def _c(stub: str, slot: str, extra=None) -> bytes:
    return compile_c(C_DIR / "domain.c", S[slot], {"STUB": stub, **(extra or {})})


class domain_of_the_true_monarchs:
    cid: int = DOMAIN

    def blobs(self):
        return {"FRONT": (S["FRONT"], front_blob(), "D2 battle-calculator front"),
                "BONUS": (S["BONUS"], _c("DM_BONUS", "BONUS"), "D2 +800 (C)"),
                "COND3": (S["COND3"], _c("DM_COND3", "COND3"), "D3 cls3 +0C (C)"),
                "COST3": (S["COST3"], _c("DM_COST3", "COST3"), "D3 cls3 +10 (C)"),
                "RES3": (S["RES3"], _c("DM_RES3", "RES3", {"PRED_ADDR": hex(S["PRED"] | 1)}), "D3 cls3 +04 (C)"),
                "PRED": (S["PRED"], _c("DM_PRED", "PRED"), "D3 picker predicate (C)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= RESERVES[key], f"{key}: {len(blob):#x} B > {RESERVES[key]:#x}"
            assert_thumb1_only(blob, addr)
        rec = (DOMAIN, S["RES3"] | 1, 0, S["COND3"] | 1, S["COST3"] | 1, 0)

        def install(rom, v):
            cur = v.unpack(SOGEN_BEQ, "<H")[0]
            assert cur in (SOGEN_STOCK, SOGEN_NEW), f"Sogen arm @{SOGEN_BEQ:#x} = {cur:#06x}"
            v.pack(SOGEN_BEQ, "<H", SOGEN_NEW)
            cur = bytes(v.blob(D2_SITE, 4))
            assert cur in (D2_STOCK, common_bl(D2_SITE, S["FRONT"])), f"D2 site @{D2_SITE:#x} = {cur.hex()}"
            v.write(D2_SITE, common_bl(D2_SITE, S["FRONT"]))

        def check(c, rom, v):
            c.eq(v.unpack(SOGEN_BEQ, "<H")[0], SOGEN_NEW, "Sogen's +200 arm disabled (beq -> b 0x021B2928)")
            c.eq(bytes(v.blob(D2_SITE, 4)), common_bl(D2_SITE, S["FRONT"]), "battle calculator @0x02197A14 -> Domain's D2 front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), (Row(CLS3, rec, CLS3_PHANTOM),), installs=(install,), checks=(check,))


SPEC = domain_of_the_true_monarchs()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

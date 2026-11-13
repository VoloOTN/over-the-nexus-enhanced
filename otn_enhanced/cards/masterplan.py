"""The Monarchs Masterplan (Normal Spell) on Speed Spell - Faustian Bargain 0x0D6A.  TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Send 1 "Monarch" Spell/Trap from your Deck to the GY, except "The Monarchs Masterplan".  If this card is banished: You can target 1 face-up monster your opponent controls; add 1 monster with the
     same Attribute that has 2400 ATK/1000 DEF, from your Deck or GY to your hand, then you can apply this effect. * Immediately after this effect resolves, Normal Summon 1 "Zaborg the Thunder Monarch",
     "Mobius the Frost Monarch", "Thestalos the Firestorm Monarch", "Granmarg the Rock Monarch", "Raiza the Storm Monarch", or "Caius the Shadow Monarch".  You can only use this effect of "The Monarchs
     Masterplan" once per turn."

BUILT: clause 1 + (2026-11-12 session 2) clause 2, the banished trigger (c/masterplan.c): fronts on the Dragon Rulers' banish gates post for 0x0D6A, a virtual cls2 record for the
banished zone 0xF (prefind_hook) runs the effect; the opponent's monster is CHOSEN AT RESOLUTION (KNOWN DEVIATION: not targeted at activation); the optional Normal Summon is Cry Havoc!'s
machine restricted to the six named Monarchs through escalation's predicate front.
Clause 1:  cls0 {Foolish Burial's resolver 0x02208DD5 (send 1 card from the Deck to the GY through the criteria row), 0, its cond 0x021F0B19, 0, 0} over cls0 phantom 0x0E30 +
a virtual Deck row 0xFFD6 {Monarch set code 0x6D, Deck set-code add handler 0x0223CAF5 (type 2, the same flags as Foolish Burial's 0x0223CAD9), Spell|Trap|except self 0x2C}.
See notes/masterplan-findings.md.
"""
from __future__ import annotations

import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS0, Compiled, Row
from pathlib import Path

from otn_enhanced.asm.cc import compile_c
from otn_enhanced.effects import ov5_cave as O5, prefind_hook
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

MP = 0x0D6A
OUT = "data/over_the_nexus/working/rom_masterplan.nds"
IDX = 0xFFD6
FB_RES, FB_COND = 0x02208DD5, 0x021F0B19
DECK_SETCODE, WORD = 0x0223CAF5, 0x0000002C
CLS0_PHANTOM = 0x0E30
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
S = {n: getattr(O5, f"CAVE_MP_{n}") for n in ("ROWS", "H2", "H3", "COND2", "RES2", "TGTH", "ADDH", "APRED", "NSPRED", "DATA", "VREC", "H6F", "H7F")}
RESERVE = {"ROWS": 0x30, "H2": 0x50, "H3": 0x30, "COND2": 0x140, "RES2": 0x280, "TGTH": 0x130, "ADDH": 0x50, "APRED": 0x50, "NSPRED": 0x70, "DATA": 0x10, "VREC": 0x20, "H6F": 0x20, "H7F": 0x30}
IDX_TGT, IDX_ADD = 0xFFD7, 0xFFD8
MODE_ADDR = O5.CAVE_MP_DATA
C_DIR = Path(__file__).resolve().parent / "c"
H6_SITE, H6_PREV = 0x021C71C8, 0x021F105C     # GY -> banished gate (Cyber Ouroboros' compare, Z=1 = post); chain head = the Dragon Rulers' cave3 H6
H7_SITE, H7_PREV = 0x021D1B98, 0x021F1A0C     # 0x021D1300's banish override switch (r5 = cid, [sp+0x30] = dest); chain head = the Rulers' H7
H7_LEAF = 0x021D1D3E                            # the dest == 0xF banish leaf
BANISHED = 0x0F
TAG_YOU_CAN = 0x021E51E5
DLG_NS = 605                                    # "Normal Summon a Monarch." (dlg_text label appended by cards/erebus.py)
VREC_BLOB = struct.pack("<HH5I", MP, 0, S["RES2"] | 1, 0, S["COND2"] | 1, TAG_YOU_CAN, 0).ljust(RESERVE["VREC"], bytes(1))
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_MP_H2], _DN[O5.CAVE_MP_H3]
ROWS_BLOB = (struct.pack("<HHII", MP, TN.MONARCH_SET, DECK_SETCODE, WORD) + bytes(4)
             + struct.pack("<HHII", MP, 0xFFFF, S["TGTH"] | 1, 0x2) + bytes(4)
             + struct.pack("<HHII", MP, 0xFFFF, S["ADDH"] | 1, 0x2) + bytes(4))
CLS0_REC = (MP, FB_RES, 0, FB_COND, 0, 0)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "masterplan.c", S[slot], {"STUB": stub, "MPDATA": f"0x{S['DATA']:08X}", "APRED_ADDR": f"0x{S['APRED'] | 1:08X}", "L_NS": str(DLG_NS)}), slot)


def h2_front():
    """criteria miss tail (r5 = cid): 0x0D6A -> row 0xFFD6 (C1), 0xFFD7 (MODE 8, C2 targets) or 0xFFD8 (MODE 9, C2 adds); pops the caller's frame.  Others: BL onward."""
    b = EffectBuilder()
    b.ldr_const(0, MP)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, MODE_ADDR)
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x8")
    b.insn("BEQ", "tgt")
    b.insn("CMP", "R0, #0x9")
    b.insn("BEQ", "add")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("tgt")
    b.ldr_const(0, IDX_TGT)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("add")
    b.ldr_const(0, IDX_ADD)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front():
    """invoker row compute: rows 0xFFD6..0xFFD8 read their handler from ROWS."""
    b = EffectBuilder()
    b.ldr_const(0, IDX)
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


def h6_front():
    """GY -> banished gate (replaces `ldr r1,=0x1CF6 ; cmp r0,r1`; r0 = cid live after, r1 dead; Z=1 = post the banish event): 0x0D6A -> Z=1; else the Rulers' H6 (LR intact)."""
    b = EffectBuilder()
    b.ldr_const(1, MP)
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "prev")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(1, H6_PREV | 1)
    b.insn("BX", "R1")
    return _fit(b.assemble(S["H6F"], pad="nop"), "H6F")


def h7_front():
    """0x021D1300's override switch (replaces `ldr r1,=0x1D98 ; cmp r5,r1`; r5 = cid, [sp+0x30] = destination): 0x0D6A going to 0xF -> the banish leaf 0x021D1D3E; else the Rulers' H7."""
    b = EffectBuilder()
    b.ldr_const(1, MP)
    b.insn("CMP", "R5, R1")
    b.insn("BNE", "prev")
    b.insn("LDR", "R1, [SP, #0x30]")
    b.insn("CMP", "R1, #0xF")
    b.insn("BNE", "prev")
    b.ldr_const(1, H7_LEAF | 1)
    b.insn("BX", "R1")
    b.label("prev")
    b.ldr_const(1, H7_PREV | 1)
    b.insn("BX", "R1")
    return _fit(b.assemble(S["H7F"], pad="nop"), "H7F")


def _front_at(view, site, prev, mine, what):
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site, slot):
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class masterplan_c1:
    cid = MP

    def blobs(self):
        return {"ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFFD6..0xFFD8"), "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "COND2": (S["COND2"], _c("MP_COND", "COND2"), "C2 virtual cls2 +0C cond (C)"),
                "RES2": (S["RES2"], _c("MP_RES", "RES2"), "C2 +04 resolver (C)"),
                "TGTH": (S["TGTH"], _c("MP_TGTH", "TGTH"), "row 0xFFD7 handler (C)"),
                "ADDH": (S["ADDH"], _c("MP_ADDH", "ADDH"), "row 0xFFD8 handler (C)"),
                "APRED": (S["APRED"], _c("MP_APRED", "APRED"), "row 0xFFD8 predicate (C)"),
                "NSPRED": (S["NSPRED"], _c("MP_NSPRED", "NSPRED"), "Cry Havoc! hand predicate: named Monarchs (C)"),
                "DATA": (S["DATA"], bytes(RESERVE["DATA"]), "C2 DATA (ship clear)"),
                "VREC": (S["VREC"], VREC_BLOB, "C2 virtual cls2 record (banished zone)"),
                "H6F": (S["H6F"], h6_front(), "GY->banished gate front"),
                "H7F": (S["H7F"], h7_front(), "banish override switch front")}

    def compile(self, view=None):
        blobs = self.blobs()
        prefind_hook.register(MP, S["VREC"], "The Monarchs Masterplan C2 banished trigger", cls=2, zone=BANISHED, any_sub=True)
        group = TN.GROUPS[0]

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            group.install(rom, v)
            _front_at(v, H6_SITE, H6_PREV, S["H6F"], "GY->banished gate")
            _front_at(v, H7_SITE, H7_PREV, S["H7F"], "banish override switch")
            prefind_hook.install(rom, v)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Masterplan {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            group.check(c, rom, v)
            c.eq(ov3_bl_target(v.buf, H6_SITE), S["H6F"], "GY->banished gate -> Masterplan front")
            c.eq(ov3_bl_target(v.buf, H7_SITE), S["H7F"], "banish override switch -> Masterplan front")
            prefind_hook.verify(rom, v, lambda ok, msg: c.ok(bool(ok), msg))

        return Compiled(tuple(blobs.values()), rows=(Row(CLS0, CLS0_REC, CLS0_PHANTOM),), installs=(install,), checks=(check,))


SPEC = masterplan_c1()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)

# CPU row: a Spell donor with no ov5 CPU row is never played by the CPU (cardtest rows).  Repurpose the card-less phantom row 0x02391B28 (cid 0x0EA9) as {0x3C000 | cid, always-true 0x023107C1};
# the card's own cond (Foolish Burial's) still decides.
AI_ROW, AI_ROW_STOCK, AI_ROW_NEW = 0x02391B28, (0x3CEA9, 0x023113A9), (0x3C000 | MP, 0x023107C1)


def _patch_ai_row(out):
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    got = struct.unpack_from("<2I", data, AI_ROW - ov.ramAddress)
    assert got in (AI_ROW_STOCK, AI_ROW_NEW, (0x3DD6A, 0x023107C1)), f"ov5 CPU row @{AI_ROW:#x} is {got}"
    struct.pack_into("<2I", data, AI_ROW - ov.ramAddress, *AI_ROW_NEW)
    O5._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)


def main(write_text=False, src=dsl.SRC, out=OUT):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out=OUT):
    import ndspy.rom
    ok = _dsl_verify(out)
    ov = O5._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    good = struct.unpack_from("<2I", bytes(ov.data), AI_ROW - ov.ramAddress) == AI_ROW_NEW
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row {AI_ROW:#x} -> always-true evaluator")
    return bool(ok) and good

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

"""Restoration of the Monarchs (Equip Spell) on Burning Spear 0x12EE.  Single-card TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Activate this card by targeting 1 monster in your GY with 2400 ATK/1000 DEF, or 2800 ATK/1000 DEF; Special Summon it in Defense
     Position, but negate its effects, also equip it with this card.  When this card leaves the field, destroy that monster.  The equipped
     monster can be treated as 2 Tributes for a Tribute Summon.  You can only activate 1 "Restoration of the Monarchs" per turn."

Clauses  C1 target a 2400/1000 or 2800/1000 monster in the GY.  C2 Special Summon it in Defense Position, effects negated.  C3 equip it.
         C4 this card leaves -> destroy that monster.  C5 the equipped monster counts as 2 Tributes.  C6 once per turn.
Design   (notes/restoration-findings.md; every item is UNPROVEN until traced)
  * Premature Burial's family resolver 0x02207528 does C2 (minus position/negate), C3 (type 3 -> equip link 0x021C4A5C) and, with the cid in the
    leave-cleanup list 0x0226E940, C4.  cls0 {0x02207529, 0, COND, COST, 0x02235605} over a cls0 phantom (Burning Spear owns no cls record).
  * C1: virtual criteria row 0xFF80 = {0x12EE, set 0x6C, 0x0223C9ED (GY Special Summon + set-code predicate), 0x00010002}; set code 0x6C = Tenacity's
    22-cid 2400/1000 / 2800/1000 list, installed here by tenacity's own group object (idempotent).  H2/H3 fronts ahead of Block Dragon's.
  * Defense Position: front over `bl 0x02204730` @0x022075D2: for cid 0x12EE r2 = 1 (the mode Soul Resurrection 0x17B7 uses).
  * Negate: the summon prologue posts a kind-3 node {key = SOURCE cid} for sources in list 0x0228F750 (bl @0x02268074) and the negate reader
    honours any node of kind < 6 whose key is in 0x0226FAB4 (bl @0x021EE418).  Kind 3 survives every turn sweep (rider.turn_sweeper).  Both lists
    are full, so each bl gets a precheck (0x12EE ? 1 : tail), as Obedience Schooled / NEXT did.  The leave list 0x0226E940 is full too: its search bl
    @0x021CB3BC shares the poster's chain head 0x02223490, so ONE precheck (PREA) serves both.
  * C5: front over `adds r5,r3,#0 ; adds r6,r1,#0` @0x021AE14A (the native double-Tribute predicate, Mega Monarch's M0 site): TRUE when the own candidate
    is the equip target of a face-up Restoration.  A combined ROM with mega_monarch needs the two fronts chained.
  * Burning Spear's equip stat row (+400/-200, row @0x0226E070) is zeroed.  C6: kind-1 turn-log node 0x12EE posted by the cost.

    uv run python _build_restoration.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS0, Compiled, Row
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

RES_CID = 0x12EE
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_restoration.nds"
C_DIR = Path(__file__).resolve().parent / "c"

CLS0_PHANTOM = 0x0E2B
PB_RESOLVER, PB_TARGET = 0x02207529, 0x02235605         # Premature Burial's cls0 +04 / +14 (0x02235605 = the generic target step)
IDX = 0xFF80
GY_SS_SETCODE = 0x0223C9ED                              # GY Special Summon thunk with the set-code predicate (flags 8); odd = Thumb
WORD_PB = 0x00010002                                    # Premature Burial's criteria word
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
POS_SITE, POS_NATIVE = 0x022075D2, 0x02204730           # bl 0x02204730(desc, 1, position) in the PB resolver, phase 0x80
PREA_SITES = (0x021CB3BC, 0x02268074)                   # leave-cleanup list search / kind-3 summon poster list
PREA_TAIL = 0x02223490                                  # their current chain head in the chain ROM (Norden's shared stub)
PREB_SITE, PREB_TAIL = 0x021EE418, 0x023AAC30           # negate-reader list search, current head (an ov5 precheck of a later card)
TRIB_SITE, TRIB_STOCK = 0x021AE14A, bytes.fromhex("1d1c0e1c")   # adds r5,r3,#0 ; adds r6,r1,#0
EQUIP_ROW = 0x0226E070                                  # equip ATK/DEF row for 0x12EE: (cid, +400, -200)
EQUIP_STOCK = (RES_CID, 0x190, -0xC8)

S = {n: getattr(O5, f"CAVE_RS_{n}") for n in ("COND", "COST", "POS", "PREA", "PREB", "ROWS", "H2", "H3", "TRIBW", "TRIB")}
RESERVE = {"COND": 0x40, "COST": 0x20, "POS": 0x30, "PREA": 0x18, "PREB": 0x18, "ROWS": 0x10, "H2": 0x28, "H3": 0x30, "TRIBW": 0x30, "TRIB": 0x60}
for _v in (GY_SS_SETCODE, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_RS_H2], _DN[O5.CAVE_RS_H3]
ROWS_BLOB = struct.pack("<HHII", RES_CID, TN.REVEAL_SET, GY_SS_SETCODE, WORD_PB) + bytes(4)
CLS0_REC = (RES_CID, PB_RESOLVER, 0, S["COND"] | 1, S["COST"] | 1, PB_TARGET)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _asm(b: EffectBuilder, slot: str) -> bytes:
    return _fit(b.assemble(S[slot], pad="nop"), slot)


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "restoration.c", S[slot], {"STUB": stub}), slot)


def pos_front() -> bytes:
    """Replaces `bl 0x02204730` (r0 = desc, r1 = 1, r2 = position) in the PB resolver: Restoration -> Defense (1).  Tail-calls the native function
    so LR still returns into the resolver."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0}")
    b.insn("LDRH", "R0, [R0, #0x0]")
    b.ldr_const(3, RES_CID)
    b.insn("CMP", "R0, R3")
    b.insn("POP", "{R0}")
    b.insn("BNE", "go")
    b.insn("MOV", "R2, #0x1")
    b.label("go")
    b.ldr_const(3, POS_NATIVE | 1)
    b.insn("BX", "R3")
    return _asm(b, "POS")


def precheck(slot: str, tail: int) -> bytes:
    """`bl 0x02022E14`-shaped list search (r0 = cid, r1 = list, r2 = count): Restoration answers 1, everything else tail-calls the current head."""
    b = EffectBuilder()
    b.ldr_const(3, RES_CID)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "miss")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("miss")
    b.ldr_const(3, tail | 1)
    b.insn("BX", "R3")
    return _asm(b, slot)


def h2_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, RES_CID)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _asm(b, "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x1")
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
    return _asm(b, "H3")


def trib_front(tail: int | None = None) -> bytes:
    """BL over `adds r5,r3,#0 ; adds r6,r1,#0` @0x021AE14A inside the host `push {r3-r7,lr}` (r0 player, r1 summoned cid, r2 candidate side, r3 slot;
    r4-r7 free).  Hit -> return TRUE straight out of the host; miss -> replay the displaced pair."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, R2, R3, LR}")
    b.insn("ADD", "R1, R2, #0")                  # leaf(player, side, slot)
    b.insn("ADD", "R2, R3, #0")
    b.ldr_const(4, S["TRIB"] | 1)
    b.insn("BLX", "R4")
    b.insn("ADD", "R7, R0, #0")
    b.insn("POP", "{R0, R1, R2, R3, R4}")        # r4 = the hook's return address
    b.insn("CMP", "R7, #0x0")
    b.insn("BNE", "hit")
    if tail is None:
        b.insn("ADD", "R5, R3, #0")              # the displaced pair
        b.insn("ADD", "R6, R1, #0")
        b.insn("BX", "R4")
    else:                                        # MONARCH_COMBO: mega_monarch's M0 front (hook return in r4, r5/r6 free) replays the pair itself
        b.insn("MOV", "LR, R4")
        b.ldr_const(5, tail | 1)
        b.insn("BX", "R5")
    b.label("hit")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    return _asm(b, "TRIBW")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class restoration_of_the_monarchs:
    cid: int = RES_CID

    def blobs(self):
        return {"COND": (S["COND"], _c("RS_COND", "COND"), "cls0 +0C cond (C)"),
                "COST": (S["COST"], _c("RS_COST", "COST"), "cls0 +10 cost (C)"),
                "POS": (S["POS"], pos_front(), "Defense Position front"),
                "PREA": (S["PREA"], precheck("PREA", PREA_TAIL), "leave-list / kind-3 poster precheck"),
                "PREB": (S["PREB"], precheck("PREB", PREB_TAIL), "negate-reader precheck"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFF80"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "TRIBW": (S["TRIBW"], trib_front(O5.CAVE_MM_M0 if O5.combo() else None), "double-Tribute front"),
                "TRIB": (S["TRIB"], _c("RS_TRIB", "TRIB"), "double-Tribute leaf (C)"),
                "REV": (O5.CAVE_TN_REV, TN.REV_BLOB, "set code 0x6C list (shared with Tenacity)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "REV"):
                assert_thumb1_only(blob, addr)
        group = TN.GROUPS[1]
        assert group.setcode == TN.REVEAL_SET

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            _front_at(v, POS_SITE, POS_NATIVE, S["POS"], "PB resolver position call")
            for site in PREA_SITES:
                _front_at(v, site, PREA_TAIL, S["PREA"], "list search")
            _front_at(v, PREB_SITE, PREB_TAIL, S["PREB"], "negate-reader list search")
            cur = bytes(v.blob(TRIB_SITE, 4))
            assert cur in (TRIB_STOCK, common_bl(TRIB_SITE, S["TRIBW"])) or (O5.combo() and cur == common_bl(TRIB_SITE, O5.CAVE_MM_M0)), f"double-Tribute site {TRIB_SITE:#x} = {cur.hex()}"
            v.write(TRIB_SITE, common_bl(TRIB_SITE, S["TRIBW"]))
            row = tuple(v.unpack(EQUIP_ROW, "<Hhh"))
            assert row in (EQUIP_STOCK, (RES_CID, 0, 0)), f"equip stat row @{EQUIP_ROW:#x} = {row}"
            v.pack(EQUIP_ROW, "<Hhh", RES_CID, 0, 0)
            group.install(rom, v)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Restoration {slot} front")
            c.ok(code_reaches(rom, POS_SITE, S["POS"]), "PB resolver position call reaches POS front")
            for site in PREA_SITES:
                c.eq(ov3_bl_target(v.buf, site), S["PREA"], f"list search @{site:#x} -> PREA")
            c.ok(code_reaches(rom, PREB_SITE, S["PREB"]), "negate-reader list search reaches PREB")
            c.ok(code_reaches(rom, TRIB_SITE, S["TRIBW"]), "double-Tribute site reaches TRIBW")
            c.eq(tuple(v.unpack(EQUIP_ROW, "<Hhh")), (RES_CID, 0, 0), "Burning Spear equip stat row zeroed")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            group.check(c, rom, v)

        return Compiled(tuple(blobs.values()), (Row(CLS0, CLS0_REC, CLS0_PHANTOM),), installs=(install,), checks=(check,))


SPEC = restoration_of_the_monarchs()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)

# CPU row: Burning Spear (an Equip Spell) owns no ov5 CPU row, so the CPU never offers it (cardtest rows, 2026-11-11).  Repurpose the card-less
# phantom row 0x0239292C (cid 0x1695, shared evaluator 0x02321E15) as {0x12EE | 0x3D000, always-true 0x023107C1}; the card's own cond (COND) still decides.
AI_ROW, AI_ROW_STOCK, AI_ROW_NEW = 0x0239292C, (0x3D695, 0x02321E15), (0x3D000 | RES_CID, 0x023107C1)


def _ai_off(ov) -> int:
    return AI_ROW - ov.ramAddress


def _patch_ai_row(out):
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    got = struct.unpack_from("<2I", data, _ai_off(ov))
    assert got in (AI_ROW_STOCK, AI_ROW_NEW), f"ov5 CPU row @{AI_ROW:#x} is {got}"
    struct.pack_into("<2I", data, _ai_off(ov), *AI_ROW_NEW)
    O5._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)


def main(write_text=False, src=dsl.SRC, out=OUT):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out=OUT):
    ok = _dsl_verify(out)
    import ndspy.rom
    ov = O5._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    got = struct.unpack_from("<2I", bytes(ov.data), _ai_off(ov))
    good = got == AI_ROW_NEW
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row {AI_ROW:#x} = {got[0]:#x}, {got[1]:#x} (want {AI_ROW_NEW[0]:#x}, {AI_ROW_NEW[1]:#x})")
    return bool(ok) and good

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

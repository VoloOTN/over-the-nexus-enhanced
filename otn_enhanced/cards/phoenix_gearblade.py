"""Phoenix Gearblade (0x10EA, donor Invigoration, Equip Spell) -- layered on Immortal Phoenix Gearfried.

SINGLE-CARD TEST ROM ONLY: NOT in steps.STEPS / SHIPPED.  Findings and proofs: notes/phoenix-gearblade-findings.md.

Printed text (user-supplied 2026-11-06):
  C1 Equip only to a Warrior or FIRE monster.            -> equip-legality arm 0x021D7F62 (STAGE 1)
  C2 It gains 300 ATK.                                    -> grant row {0x10EA, +300, 0}            (STAGE 1)
  C3 End of the Damage Step, if the equipped monster attacked: You can send this card to the GY; this Battle Phase each
     of your Warrior / FIRE monsters can make a second attack.                                       (STAGE 2)
       trigger  : EoDS walker front @0x02252210 routes 0x10EA to the ATTACKER-only post arm 0x0225225C
       effect   : cls1 {RES snapshot riders, COND, COST 'You can' + send self}, over phantom 0x17EA
       2nd atk  : double-attack tail front @0x021A3F20 reads the rider key 0x10EA
  C4 Sent to the GY / banished to activate a monster effect: You can add this card to your hand (HOPT).  (STAGE 3, unbuilt)

    uv run python _build_phoenix_gearblade.py
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.data import card_text
from otn_enhanced.dsl import CLS1, CLS2, Compiled, Row, card
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

GEARBLADE = 0x10EA
C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_phoenix_gearblade.nds"

# --- STAGE 1: equip gate + stat ----------------------------------------------------------------------------------
EQ_SITE = 0x021D7F66                    # `movs r2,#5 ; b 0x021D7C76` = Invigoration's EARTH test (attribute index 5)
EQ_EPILOGUE = 0x021D817B                # `add sp,#0x1c ; pop {r4-r7,pc}` entered with r0 = verdict (odd = Thumb)
ATTR_HELPER = 0x021B938C                # (r0 = side, r1 = zone, r2 = attribute index) -> 1 iff that attribute; FIRE = 4
GRANT_BASE, GRANT_COUNT = 0x0226DFB0, 94
S_EQ = O5.CAVE_PG_EQ
RESERVE_EQ = 0x40

# --- STAGE 2: C3 --------------------------------------------------------------------------------------------------
EOD_SITE, EOD_STOCK = 0x02252210, bytes.fromhex("4a488642")   # ldr r0,[pc,#0x128] (= 0x1C8C) ; cmp r6,r0   (flags feed bgt/bge @0x02252214)
EOD_LIT_1C8C = 0x1C8C
EOD_ARM = 0x0225225D                    # attacker-only post arm: `ldr r0,[sp,#4] ; cmp r0,#0 ; beq skip ; b 0x02252390` (odd = Thumb)
DA_SITE, DA_STOCK = 0x021A3F20, bytes.fromhex("01272a1c")      # movs r7,#1 ; adds r2,r5,#0   (tail after every rider link missed)
RIDER_QUERY = 0x021A1430                # (r0 = side, r1 = zone, r2 = key) -> node ptr / 0
C3_PHANTOM = 0x17EA                     # cls1 record[416]; the ONLY hit for this cid in ov3 + ARM9 (donor_scan, 2026-11-06)
RET2 = 0x0224A115                       # `movs r0,#2 ; bx lr`  (target-declaration step: none)
assert EOD_ARM & 1 and RET2 & 1, "blx/bx to an even literal switches to ARM state -> freeze"

# --- STAGE 3: C4 (sent to the GY / banished as the COST of a MONSTER effect -> add this card to your hand, hard OPT) ---
LEAVE_SITE, LEAVE_STOCK_PAIR = 0x021C8216, None      # BL (4 B) over `movs r1,#0x77 ; lsls r1,r1,#6`; the chain head is Hauteclere's front
SWORD_ACCEPT = 0x021C9335                            # Sword of Dark Rites' accept arm: `movs r0,#1` -> tail 0x021C93CE stores the post flag [sp+0x18]
IS_MONSTER = 0x02029E61                              # ARM9 (cid) -> bool (engine_syms is_monster), Thumb
ACTING_DESC_PTR = 0x0229A9FC + 0x50                  # [..] = the acting descriptor (stale between activations: ALWAYS combine with the r2 == 0 test)
REASON_MASK = 0x02001000                             # [sp+0xC]: 0x1000 Tributed, 0x02000000 an Equip lost its equip target
KEY_C4 = 0x50EA
C4_PHANTOM = 0x14E7                                  # cls2 record[99]; claimed only by populate_table (allocation ledger), no card
C4_SLOTS = ("C4_COND", "C4_COST", "C4_RES", "LEAVE")
VALID_SITE, VALID_STOCK = 0x021EE05A, bytes.fromhex("20498842")   # ldr r1,[pc,#0x80] (= 0x021E6FF5) ; cmp r0,r1  (r0 = record +10 cost slot; beq @0x021EE05E -> valid)
VALID_LIT_COST = 0x021E6FF5
S = {n: getattr(O5, f"CAVE_PG_{n}") for n in ("C3_COND", "C3_COST", "C3_RES", "EOD", "DA", "VALID",
                                               "C4_COND", "C4_COST", "C4_RES", "LEAVE", "DBG", "MISS")}
DIAG = False      # DIAGNOSTIC BUILD: the leave front / C4 cond / C4 res write raw observations to CAVE_PG_DBG (read from a savestate). Set False to ship.
DBG_ADDR = S["DBG"]
RESERVE = {"C3_COND": 0x60, "C3_COST": 0x60, "C3_RES": 0xA0, "EOD": 0x30, "DA": 0x40, "VALID": 0x20,
           "C4_COND": 0xB0, "C4_COST": 0x40, "C4_RES": 0xC0, "LEAVE": 0xE0, "DBG": 0x40, "MISS": 0x20}
C3_REC = (GEARBLADE, 0, S["C3_RES"] | 1, 0, S["C3_COND"] | 1, S["C3_COST"] | 1, RET2)
C4_REC = (GEARBLADE, 0, S["C4_RES"] | 1, 0, S["C4_COND"] | 1, S["C4_COST"] | 1, RET2)


def _asm(b: EffectBuilder, slot_addr: int, reserve: int, what: str) -> bytes:
    blob = b.assemble(slot_addr, pad="nop")
    assert_thumb1_only(blob, slot_addr)
    assert len(blob) <= reserve, f"{what}: {len(blob):#x} B > {reserve:#x}"
    return blob


def eq_stub() -> bytes:
    """BL target replacing `movs r2,#5 ; b helper`.  Entry: r6 = side, [sp+4] = zone, [sp+0x10] = candidate race mask; sp is the
    legality function's own frame (the BL pushes nothing).  Verdict -> r0, then `bx` to the function epilogue 0x021D817A."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x10]")
    b.insn("MOV", "R1, #0x1")
    b.insn("LSL", "R1, R1, #0xF")
    b.insn("TST", "R0, R1")
    b.insn("BNE", "yes")
    b.insn("ADD", "R0, R6, #0x0")
    b.insn("LDR", "R1, [SP, #0x4]")
    b.insn("MOV", "R2, #0x4")
    b.bl(ATTR_HELPER)
    b.ldr_const(1, EQ_EPILOGUE)
    b.insn("BX", "R1")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.ldr_const(1, EQ_EPILOGUE)
    b.insn("BX", "R1")
    return _asm(b, S_EQ, RESERVE_EQ, "eq stub")


def eod_front() -> bytes:
    """BL over `ldr r0,=0x1C8C ; cmp r6,r0` @0x02252210 (r6 = the equip's cid; flags feed `bgt/bge` @0x02252214).
    Gearblade -> branch to the ATTACKER-only post arm 0x0225225C (r0 is dead there); else replay the pair and return with the flags."""
    b = EffectBuilder()
    b.ldr_const(0, GEARBLADE)
    b.insn("CMP", "R6, R0")
    b.insn("BEQ", "go")
    b.ldr_const(0, EOD_LIT_1C8C)
    b.insn("CMP", "R6, R0")
    b.insn("BX", "LR")
    b.label("go")
    b.ldr_const(0, EOD_ARM)
    b.insn("BX", "R0")
    return _asm(b, S["EOD"], RESERVE["EOD"], "EoDS front")


def da_front() -> bytes:
    """BL over `movs r7,#1 ; adds r2,r5,#0` @0x021A3F20, the tail of the double-attack function (frame `push {r3-r7,lr}`;
    r5 = side, r6 = zone; r3 is dead).  Rider key 0x10EA present -> return 1 through the function epilogue; else replay the pair."""
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("ADD", "R1, R6, #0x0")
    b.ldr_const(2, GEARBLADE)
    b.bl(RIDER_QUERY)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "miss")
    b.insn("POP", "{R3}")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.insn("POP", "{R3}")
    b.insn("MOV", "LR, R3")
    b.insn("MOV", "R7, #0x1")
    b.insn("ADD", "R2, R5, #0x0")
    b.insn("BX", "LR")
    return _asm(b, S["DA"], RESERVE["DA"], "double-attack front")


def valid_front() -> bytes:
    """BL over `ldr r1,=0x021E6FF5 ; cmp r0,r1` @0x021EE05A, the default arm of 0x021EDE48 ('is this effect still valid', run right
    before the resolver).  For a Spell/Equip whose source card has LEFT its zone (the instance-ref compare @0x021EDFB8 fails) the
    check walks a cid tree; the default arm accepts only when the record's +10 cost slot == 0x021E6FF5 or desc[+5] == 2 (cls2).
    Gearblade's cls1 effect sends ITSELF as the cost, so it was rejected after paying (traces E/F 2026-11-06).  Accept our cost
    stub too: Z is set when r0 == CAVE_PG_C3_COST | 1; otherwise replay the original compare.  The caller's `beq` (valid) follows."""
    b = EffectBuilder()
    b.ldr_const(1, S["C3_COST"] | 1)
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "ok")
    b.ldr_const(1, VALID_LIT_COST)
    b.insn("CMP", "R0, R1")
    b.label("ok")
    b.insn("BX", "LR")
    return _asm(b, S["VALID"], RESERVE["VALID"], "validity front")


def leave_front() -> bytes:
    """BL @0x021C8216 (leave switch; r4 = cid; the dispatcher's own frame is live: [sp+8] = ACTING cid (0 = cost / rule),
    [sp+0xC] = reason bits, [sp+0x90] destroyed, [sp+0x44] by battle, [sp+0x200] = packed leave word, dest = bits 19..22).
    Gearblade going to the GY (0xE) or banished (0xF) with NO acting cid, no tribute / equip-loss / destroy / battle reason and the
    ACTING descriptor being a MONSTER (the cost of a monster effect) -> Sword of Dark Rites' accept arm; anything else tail-jumps to
    the Arms chain head (Hauteclere), lr intact.  Reads happen after `push {r0,r2,r3}` so every dispatcher offset is +0xC."""
    b = EffectBuilder()
    b.ldr_const(1, GEARBLADE)
    b.insn("CMP", "R4, R1")
    b.insn("BNE", "next")
    b.insn("PUSH", "{R0, R2, R3}")
    if DIAG:          # raw breadcrumbs: [DBG+0] dest, +4 acting cid ([sp+8]), +8 reason, +0xC destroyed, +0x10 battle, +0x14 acting desc ptr,
        #               +0x18 acting desc cid, +0x1C = 1 once ANY cid-matching leave passed the front, +0x20 hit counter
        b.ldr_const(0, DBG_ADDR)
        b.insn("LDR", "R1, [SP, #0x20C]")
        b.insn("LSL", "R1, R1, #0x9")
        b.insn("LSR", "R1, R1, #0x1C")
        b.insn("STR", "R1, [R0, #0x0]")
        b.insn("LDR", "R1, [SP, #0x14]")
        b.insn("STR", "R1, [R0, #0x4]")
        b.insn("LDR", "R1, [SP, #0x18]")
        b.insn("STR", "R1, [R0, #0x8]")
        b.insn("LDR", "R1, [SP, #0x9C]")
        b.insn("STR", "R1, [R0, #0xC]")
        b.insn("LDR", "R1, [SP, #0x50]")
        b.insn("STR", "R1, [R0, #0x10]")
        b.ldr_const(1, ACTING_DESC_PTR)
        b.insn("LDR", "R1, [R1, #0x0]")
        b.insn("STR", "R1, [R0, #0x14]")
        b.insn("CMP", "R1, #0x0")
        b.insn("BEQ", "dbgskip")
        b.insn("LDRH", "R1, [R1, #0x0]")
        b.insn("STR", "R1, [R0, #0x18]")
        b.label("dbgskip")
        b.insn("LDR", "R1, [R0, #0x20]")
        b.insn("ADD", "R1, #0x1")
        b.insn("STR", "R1, [R0, #0x20]")
    b.insn("LDR", "R1, [SP, #0x20C]")
    b.insn("LSL", "R1, R1, #0x9")
    b.insn("LSR", "R1, R1, #0x1C")
    b.insn("CMP", "R1, #0xE")
    b.insn("BEQ", "dest")
    b.insn("CMP", "R1, #0xF")
    b.insn("BNE", "bad")
    b.label("dest")
    b.insn("LDR", "R1, [SP, #0x14]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BNE", "bad")
    b.insn("LDR", "R1, [SP, #0x18]")
    b.ldr_const(2, REASON_MASK)
    b.insn("TST", "R1, R2")
    b.insn("BNE", "bad")
    b.insn("LDR", "R1, [SP, #0x9C]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BNE", "bad")
    b.insn("LDR", "R1, [SP, #0x50]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BNE", "bad")
    b.ldr_const(1, ACTING_DESC_PTR)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BEQ", "bad")
    b.insn("LDRH", "R0, [R1, #0x0]")
    b.insn("PUSH", "{LR}")
    b.ldr_const(1, IS_MONSTER)
    b.insn("BLX", "R1")
    b.insn("POP", "{R1}")
    b.insn("MOV", "LR, R1")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "bad")
    b.insn("POP", "{R0, R2, R3}")
    b.ldr_const(1, SWORD_ACCEPT)
    b.insn("BX", "R1")
    b.label("bad")
    b.insn("POP", "{R0, R2, R3}")
    b.label("next")
    b.ldr_const(1, O5.CAVE_IK_HA_LEAVE | 1)
    b.insn("BX", "R1")
    return _asm(b, S["LEAVE"], RESERVE["LEAVE"], "C4 leave front")


MISS_SITE = 0x021EE10C


def miss_front() -> bytes:
    """BL'd from the miss-timing node 0x021EE10C (r3 = cid; Disguise's shape): Gearblade -> return with Z set (the 'If ... You can'
    trigger never misses timing: user, 2026-11-06 'it said I missed the timing'), else tail-jump to Disguise's front."""
    b = EffectBuilder()
    b.ldr_const(1, GEARBLADE)
    b.insn("CMP", "R3, R1")
    b.insn("BEQ", "ret")
    b.ldr_const(1, O5.CAVE_DC_MISS | 1)
    b.insn("BX", "R1")
    b.label("ret")
    b.insn("BX", "LR")
    return _asm(b, S["MISS"], 0x20, "never-miss front")


def _c(slot: str, stub: str) -> bytes:
    defs = {"STUB": stub}
    if DIAG:
        defs["DBG"] = f"0x{DBG_ADDR:08X}"
    blob = compile_c(C_DIR / "gearblade.c", S[slot], defs)
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


def _grant_row(view) -> int:
    hits = [GRANT_BASE + 6 * i for i in range(GRANT_COUNT) if view.u16(GRANT_BASE + 6 * i) == GEARBLADE]
    assert len(hits) == 1, f"Invigoration owns {len(hits)} grant rows"
    return hits[0]


@dataclass(frozen=True)
class gearblade_stage1:
    """C1 + C2: equip gate and +300 ATK."""
    def compile(self, view, cid) -> Compiled:
        assert cid == GEARBLADE
        stubs = ((S_EQ, eq_stub(), "C1 equip gate: Warrior or FIRE"),)
        new_bl = common_bl(EQ_SITE, S_EQ)

        def install(rom, view):
            if view.blob(EQ_SITE, 4) != new_bl:
                assert view.u16(EQ_SITE) == 0x2205, f"equip arm @{EQ_SITE:#x} is not `movs r2,#5` ({view.u16(EQ_SITE):#06x})"
                assert view.u16(EQ_SITE + 2) & 0xF800 == 0xE000, "arm tail is not an unconditional B"
            view.write(EQ_SITE, new_bl)
            g = _grant_row(view)
            row = struct.unpack("<Hhh", view.blob(g, 6))
            assert row in ((GEARBLADE, 400, -200), (GEARBLADE, 300, 0)), f"grant row {row}"
            view.pack(g, "<Hhh", GEARBLADE, 300, 0)

        def check(c, rom, view):
            c.eq(ov3_bl_target(view.buf, EQ_SITE), S_EQ, "C1: arm @0x021D7F66 -> Warrior|FIRE stub")
            c.eq(struct.unpack("<Hhh", view.blob(_grant_row(view), 6)), (GEARBLADE, 300, 0), "C2: grant row +300/0")
            c.ok(O5.read_cave(rom, S_EQ, len(eq_stub())) == eq_stub(), "C1 stub bytes in ov5")
            ok, msg = card_text.check_rom_text(c.out, GEARBLADE)
            c.ok(ok, msg)

        return Compiled(stubs, (), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class gearblade_stage2:
    """C3: EoDS trigger, cls1 effect (You can / send self / snapshot riders), second-attack link."""
    def compile(self, view, cid) -> Compiled:
        assert cid == GEARBLADE
        stubs = (
            (S["C3_COND"], _c("C3_COND", "C3COND"), "C3 +0C cond"),
            (S["C3_COST"], _c("C3_COST", "C3COST"), "C3 +10 You can + send self"),
            (S["C3_RES"], _c("C3_RES", "C3RES"), "C3 +04 snapshot riders"),
            (S["EOD"], eod_front(), "EoDS walker front"),
            (S["DA"], da_front(), "double-attack tail front"),
            (S["VALID"], valid_front(), "effect-still-valid front"))
        rows = (Row(CLS1, C3_REC, C3_PHANTOM),)
        eod_bl, da_bl = common_bl(EOD_SITE, S["EOD"]), common_bl(DA_SITE, S["DA"])
        valid_bl = common_bl(VALID_SITE, S["VALID"])

        def install(rom, view):
            assert view.blob(EOD_SITE, 4) in (EOD_STOCK, eod_bl), f"EoDS site {EOD_SITE:#x} = {view.blob(EOD_SITE, 4).hex()}"
            assert view.blob(DA_SITE, 4) in (DA_STOCK, da_bl), f"double-attack site {DA_SITE:#x} = {view.blob(DA_SITE, 4).hex()}"
            assert view.blob(VALID_SITE, 4) in (VALID_STOCK, valid_bl), f"validity site {VALID_SITE:#x} = {view.blob(VALID_SITE, 4).hex()}"
            view.write(EOD_SITE, eod_bl)
            view.write(DA_SITE, da_bl)
            view.write(VALID_SITE, valid_bl)

        def check(c, rom, view):
            c.eq(ov3_bl_target(view.buf, EOD_SITE), S["EOD"], "C3: bl @0x02252210 -> EoDS front")
            c.eq(ov3_bl_target(view.buf, DA_SITE), S["DA"], "C3: bl @0x021A3F20 -> double-attack front")
            c.eq(ov3_bl_target(view.buf, VALID_SITE), S["VALID"], "C3: bl @0x021EE05A -> validity front")
            for slot, blob in (("EOD", eod_front()), ("DA", da_front()), ("VALID", valid_front()), ("C3_COND", _c("C3_COND", "C3COND")),
                               ("C3_COST", _c("C3_COST", "C3COST")), ("C3_RES", _c("C3_RES", "C3RES"))):
                c.ok(O5.read_cave(rom, S[slot], len(blob)) == blob, f"C3 {slot} stub bytes in ov5")

        return Compiled(stubs, rows, installs=(install,), checks=(check,))


@dataclass(frozen=True)
class gearblade_stage3:
    """C4: cost-sent / cost-banished by a monster effect -> cls2 'You can add this card to your hand' (hard OPT)."""
    def compile(self, view, cid) -> Compiled:
        assert cid == GEARBLADE
        stubs = (
            (S["C4_COND"], _c("C4_COND", "C4COND"), "C4 +0C cond"),
            (S["C4_COST"], dsl._hopt_you_can_stub(S["C4_COST"], KEY_C4), "C4 +10 You can + hard OPT"),
            (S["C4_RES"], _c("C4_RES", "C4RES"), "C4 +04 add to hand"),
            (S["LEAVE"], leave_front(), "C4 leave front"),
            (S["DBG"], bytes(RESERVE["DBG"]), "C4 diagnostic breadcrumbs (DATA)"),
            (S["MISS"], miss_front(), "C4 never-miss front"))
        assert len(stubs[1][1]) <= RESERVE["C4_COST"]
        rows = (Row(CLS2, C4_REC, C4_PHANTOM),)
        mine = common_bl(LEAVE_SITE, S["LEAVE"])

        def install(rom, view):
            cur = ov3_bl_target(view.buf, LEAVE_SITE)
            assert cur in (O5.CAVE_IK_HA_LEAVE, S["LEAVE"]), \
                f"leave site {LEAVE_SITE:#x} -> {cur:#x}; expected the Arms chain head {O5.CAVE_IK_HA_LEAVE:#x}"
            view.write(LEAVE_SITE, mine)
            mcur = ov3_bl_target(view.buf, MISS_SITE)
            assert mcur in (O5.CAVE_DC_MISS, S["MISS"]), f"miss node {MISS_SITE:#x} -> {mcur:#x}; expected Disguise's front {O5.CAVE_DC_MISS:#x}"
            view.write(MISS_SITE, common_bl(MISS_SITE, S["MISS"]))

        def check(c, rom, view):
            t, nxt = ov3_bl_target(view.buf, MISS_SITE), O5.dc_next()      # a later owner's front (predaplant) may sit ahead of ours
            while t != S["MISS"] and t in nxt:
                t = nxt[t]
            c.eq(t, S["MISS"], "C4: bl @0x021EE10C -> never-miss front")
            c.ok(O5.read_cave(rom, S["MISS"], len(miss_front())) == miss_front(), "C4 MISS stub bytes in ov5")
            c.eq(ov3_bl_target(view.buf, LEAVE_SITE), S["LEAVE"], "C4: bl @0x021C8216 -> leave front")
            c.eq(O5.ik_walk(S["LEAVE"]), O5.ik_walk(O5.CAVE_IK_HA_LEAVE), "C4: leave front steps into the Arms chain")
            for slot, blob in (("C4_COND", _c("C4_COND", "C4COND")), ("C4_COST", stubs[1][1]), ("C4_RES", _c("C4_RES", "C4RES")),
                               ("LEAVE", leave_front())):
                c.ok(O5.read_cave(rom, S[slot], len(blob)) == blob, f"C4 {slot} stub bytes in ov5")

        return Compiled(stubs, rows, installs=(install,), checks=(check,))


SPEC = card(GEARBLADE, gearblade_stage1(), gearblade_stage2(), gearblade_stage3())
_main, _verify = dsl.make(SPEC, None, out=OUT)


def main(write_text: bool = True, src: str = CHAIN, out: str = OUT) -> None:
    _main(write_text=write_text, src=src, out=out)


def verify(out: str = OUT) -> bool:
    return _verify(out) is not False

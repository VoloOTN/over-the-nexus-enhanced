"""Trial of the Princesses (cid 0x19D8) -> "Wonder Wand", keeping the donor's cid.

================================================================================
WHAT THIS SCRIPT DOES
================================================================================
Turns the real "Trial of the Princesses" (cid 0x19D8) into "Wonder Wand":

  "Equip only to a Spellcaster monster. It gains 500 ATK. If you control the
   equipped monster and this card: You can send both to the GY; draw 2 cards."

================================================================================
WHY TRIAL OF THE PRINCESSES IS THE DONOR (decided)
================================================================================
The first attempt used Axe of Despair (0x10D6) and the ignition was NEVER OFFERED.
Root cause (savestate-confirmed): a field-activated equip effect is only offered
if the card's NATIVE main+sub+targ+cls3 stack is coherent -- the offer enumerator
0x02201070 gates on a per-zone RELATIONSHIP NODE (0x021A1584 -> walker 0x021A1238)
that only the native resolution machinery sets up.  Reproducing that on a foreign
donor means writing the engine's relationship pool blind = freeze-prone.  See repo
memory otn-equip-spell-machinery.md.

Trial of the Princesses (cid 0x19D8) is the IDEAL donor: it is already an Equip
Spell whose field-activated ignition is OFFERED NATIVELY, and it is obtainable
(card_intid set).  We KEEP its entire native offer wiring (master row main/sub/
targ + cls3 cond/timing) so the "you can ..." option appears exactly as it does
for the real card, and we transplant only the LEAVES:

  * cls3 res (0x02206F41) -> WW_RES: our own send-both-to-GY-then-draw-2 FSM.
  * equip target -> add a Spellcaster-only restriction-table row for 0x19D8
    (Trial natively allows Warrior/Spellcaster/Beast-Warrior; we narrow it).
  * ATK grant amount -> 500 (Trial's native equip already grants +500; kept).
  * name / description -> "Wonder Wand".

Trial's native master row (UNTOUCHED, drives offerability):
  main=0x022048FD (0x224AA20 -> 0x21CF310 offer-register),
  sub =0x021DB245, targ=0x021E4D81, cls3[]: cond=0x021FA685, +10=0x021E7C3D.

================================================================================

What changed this session, all re-verified against the base ROM:

  * CLAUSE 2 IS DONE, and it is pure data: the equip ATK/DEF grant table lives at
    0x0226DFB0 -- 94 records of [cid u16][atk i16][def i16], sorted by cid.  Every
    record matches its printed card (Axe +1000/0, Black Pendant +500/0, Horn of
    Light 0/+800, Book of Secret Arts +300/+300, ...), which pins the format.
    The donor's row is 0x0226E13C.  We edit ATK in place: 800 -> 500.

  * THE DONOR NATIVELY GRANTS +800, NOT +500.  Trial of the Princesses reads
    "Equip only to 'White Magician Pikeru' or 'Ebon Magician Curran'; it gains 800
    ATK. During a turn that the equipped monster destroyed a Level 5 or higher
    monster by battle, ..."  An earlier revision of this file asserted +500 and
    declared WW_ATK_GAIN without ever using it, so the ATK was simply never
    patched.  Its claim that Trial's ignition condition is "you control the
    equipped monster and this card" is also wrong -- it is battle-destruction
    gated, which is NOT Wonder Wand's condition.

  * THERE IS NO "MASTER TABLE"; the old A2 EDIT WAS CORRUPTING A BYSTANDER and
    has been deleted.  find_event_handler (0x0224A118) switches on descriptor[+5]
    into FOUR sorted cls arrays (cid = u16 at +0x00, stride 24):
    cls2 0x02275C04/697, cls3 0x02279D74/776, cls0 0x0227E64C/1306,
    cls1 0x022860D4/1333 -- exactly as the KB fact dispatch.cls_tables already
    documented.  The old MASTER_BASE = 0x02275C08 / 4116 rows / cid-at-+0x14 grid
    is a fiction: it starts 4 bytes into cls2 and reads its "cid" out of the NEXT
    record, so every row it returned was the previous record's tail.  Its A2 wrote
    0x0227B3A4 = cls3[236] +0x10, and cls3[236] is cid 0x19D5 "Demise, King of
    Armageddon" -- a bystander.  A cls3 record has no "+0C targ" to remove
    (Trial's cls3[237] is +0C cond / +10 timing), so A2 has no correct relocation
    and is simply gone.  verify() asserts Demise's record is byte-identical.

  * A1 (cls3[237] +04 res -> WW_RES) WAS ALWAYS CORRECT and is retained.  An
    earlier pass of THIS session wrongly flagged it as corrupting "Great Spirit"
    (cid 0x19F1, cls3[238]) -- that was an artifact of trusting the fictitious
    master grid instead of the KB.  cls3[237] is the donor's own record; 0x19D8
    appears exactly once across all four tables.

  * CLAUSE 1 (Spellcaster-only) IS UNPROVEN AND NOT IMPLEMENTED.  The equip-target
    gate is not the grant table (no race field), not 0x0226F628 (that is a per-cid
    (pred,applier) hook table binary-searched by 0x021E5200 -- rows are monsters
    and sent-to-GY hooks, and no race-locked equip has a row), and not any
    per-card race row (Book of Secret Arts 0x10E9 appears exactly ONCE in all of
    ov3 data: its grant record).  Building a gate now would be a blind
    build-test cycle.  See notes/wonder-wand-findings.md -> "Next Experiment"
    for the in-game A/B that decides the donor.

WW_TARGET and WW_RES below are kept installed so their ov5 slots stay claimed,
but NOTHING dispatches to them.  They are inert.  WW_RES's FSM protocol in
particular was inferred from the misread cls3 row and should be treated as
UNVERIFIED.

*** Injected code lives in ov5 caves (normal-duel-only; puzzles don't map ov5). ***
"""
from __future__ import annotations

import struct

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE
from otn_enhanced.asm.effect_builder import EffectBuilder, R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import ov5_cave
from otn_enhanced.data.card_stats import apply_stats_and_text

# ===========================================================================
# Paths and target card
# ===========================================================================
SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_wonder_wand.nds"

DONOR_CID = 0x19D8          # "Trial of the Princesses" -- KEEP cid (native field-ignition offer)

WW_ATK_GAIN = 500           # the printed +500 ATK (the donor natively grants 800)

# ===========================================================================
# cls dispatch tables -- geometry per docs/engine (dispatch.cls_tables)
# ===========================================================================
# *** THERE IS NO "MASTER HANDLER TABLE". ***  An earlier revision of this file
# declared MASTER_BASE = 0x02275C08 / stride 24 / 4116 rows with the cid at +0x14.
# That table does not exist.  find_event_handler (0x0224A118) switches on
# descriptor[+5] and selects one of FOUR sorted arrays, all stride 24 with the cid
# as a u16 at +0x00 and five Thumb callback slots at +04..+14:
#
#     cls2  0x02275C04   697 rows      cls3  0x02279D74   776 rows (0x308)
#     cls0  0x0227E64C  1306 rows      cls1  0x022860D4  1333 rows
#
# The fictitious "master" grid starts 4 bytes into cls2 and reads its "+0x14 cid"
# out of the NEXT record, so every row it returned was the previous record's tail.
# That is what made the old A2 edit corrupt a bystander (see apply_effect).
# Verified this session against find_event_handler's own literals; the KB fact
# dispatch.cls_tables already documented this and warns "ALWAYS search all FOUR".
CLS3_BASE = 0x02279D74
CLS3_COUNT = 0x308
CLS3_STRIDE = 24
TRIAL_NATIVE_CLS3_RES = 0x02206F41   # Trial's native cls3[237] +04 resolver -- REPLACED by WW_RES
DEMISE_CID = 0x19D5                  # cls3[236]; the row the old A2 was corrupting

# ===========================================================================
# Equip ATK/DEF grant table  --  VERIFIED (clause 2)
# ===========================================================================
# 94 records of [cid u16][atk i16][def i16], sorted by cid, spanning
# 0x0226DFB0 .. 0x0226E1E4.  Proven structurally: every record matches the
# printed card text -- Legendary Sword +300/+300, Sword of Dark Destruction
# +400/-200, Axe of Despair +1000/0, Black Pendant +500/0, Horn of Light 0/+800,
# Horn of the Unicorn +700/+700, Book of Secret Arts +300/+300, Magic Formula
# +700/0, and Trial of the Princesses (our donor) +800/0 @0x0226E13C.
# A second run of the same shape begins at 0x0226E1E4 (Speed Spell equips).
# Editing the ATK field in place is count-neutral and needs no re-sort.
EQUIP_GRANT_BASE = 0x0226DFB0
EQUIP_GRANT_COUNT = 94
EQUIP_GRANT_STRIDE = 6
TRIAL_NATIVE_ATK = 800          # what the donor natively grants (NOT 500)
WW_DEF_GAIN = 0                 # Wonder Wand grants no DEF

# ===========================================================================
# Per-cid (predicate, applier) hook table  --  clause 1 groundwork, NOT USED YET
# ===========================================================================
# Binary-searched by 0x021E5200 with count=0x61, stride=12 (immediates read out
# of that function this session; its literal @0x021E5274 is 0x0226F628).
# Record: +0 cid (i16 key), +4 predicate (blx; r0 != 0 ACCEPTS), +8 applier.
# NOTE: despite the older note calling this the "equip target-restriction table",
# its rows are monsters / sent-to-GY hooks -- Book of Secret Arts, Magic Formula
# and Trial have NO row here, and 0x021E5200 is an FSM/chain-step handler rather
# than a target enumerator.  The real equip-target gate is STILL UNLOCATED, so
# clause 1 (Spellcaster-only) is deliberately NOT implemented -- see
# notes/wonder-wand-findings.md -> "Next Experiment".
RESTRICT_BASE = 0x0226F628
RESTRICT_COUNT = 0x61
RESTRICT_STRIDE = 12
RESTRICT_STEAL_CID = 0x0E2F     # a phantom row with a benign (0) predicate
BINARY_SEARCH = 0x02022E44      # find(key r0, base r1, count r2, stride r3) -> rec | 0

# ===========================================================================
# Engine primitives (Thumb-1 BL targets unless noted)
# ===========================================================================
SEND_TO_GY_RAM = 0x021D0888    # send_to_graveyard(ctx)  -- sends THIS card
SEND_MON_BY_REF = 0x021CFBC8   # send a monster (by packed ref) to GY  (equip main uses it)
DRAW = 0x021D12F4              # draw(side, count)
GET_RACE = 0x0202ABB8          # ARM9 get_race(cid) -> race (18 = Spellcaster); ARM -> BLX
# Trial's OWN target filter decodes [ctx+0xC] with 0x21A241C (NOT 0x21A220C): it
# searches the monster zones for the ref and returns (zone<<8)|side, or 0xFFFF miss.
# (0x21A220C returns (side<<8)|zone -- opposite byte order -- which broke the gate.)
REF_DECODE = 0x021A241C        # (target ref) -> (zone<<8)|side, 0xFFFF on miss
FIND_EQUIPPED = 0x021A0DF8     # (player, aux) -> equipped monster ref, 0xFFFF if none
EFFECT_DONE = 0x021D269C       # (player) -- FSM cleanup / done
FSM_STATE = 0x0229AAFC         # duel-FSM block: +0x70 = state
RACE_SPELLCASTER = 18

# ===========================================================================
# Cave slots (appended overlay-5 region)
# ===========================================================================
TARGET_ADDR = ov5_cave.CAVE_WW_TARGET
TARGET_RESERVE = 0x60
RES_ADDR = ov5_cave.CAVE_WW_RES
RES_RESERVE = 0x60

# ===========================================================================
# PART B/C constants
# ===========================================================================
# Trial of the Princesses is already an Equip Spell; PART B is a byte-identity
# no-op (pass the donor's own decoded fields).  Only PART C (name/desc) changes.
NEW_NAME = b"Wonder Wand"                       # 11B
NEW_DESC = (
    b"Equip only to a Spellcaster. +500 ATK. "
    b"You can send it and this to GY; draw 2."
)
assert len(NEW_DESC) <= 96, f"description {len(NEW_DESC)}B exceeds the 96B slot"
from otn_enhanced.data.card_stats import TEXT_LANGS


# ===========================================================================
# Low-level helpers
# ===========================================================================
def _find_grant_row(ov: bytearray) -> int:
    """Return the byte offset of the donor's row in the equip ATK/DEF grant table.

    The table is sorted by cid and binary-searched (0x02022E44), so the row must
    be edited IN PLACE -- never inserted, moved, or re-sorted.
    """
    base = EQUIP_GRANT_BASE - RAM_BASE
    hits = [base + i * EQUIP_GRANT_STRIDE
            for i in range(EQUIP_GRANT_COUNT)
            if struct.unpack_from("<H", ov, base + i * EQUIP_GRANT_STRIDE)[0] == DONOR_CID]
    assert len(hits) == 1, (
        f"expected exactly 1 equip-grant row for cid 0x{DONOR_CID:04X}, found {len(hits)}")
    cids = [struct.unpack_from("<H", ov, base + i * EQUIP_GRANT_STRIDE)[0]
            for i in range(EQUIP_GRANT_COUNT)]
    assert all(cids[i] < cids[i + 1] for i in range(len(cids) - 1)), (
        "equip-grant table is not sorted ascending -- binary search would break")
    return hits[0]


def _find_cls3_row(ov: bytearray, cid: int = DONOR_CID) -> int:
    """Return the byte offset of *cid*'s cls3 record (cid = u16 at +0x00)."""
    base = CLS3_BASE - RAM_BASE
    hits = [base + i * CLS3_STRIDE
            for i in range(CLS3_COUNT)
            if struct.unpack_from("<H", ov, base + i * CLS3_STRIDE)[0] == cid]
    assert len(hits) == 1, (
        f"expected exactly 1 cls3 row for cid 0x{cid:04X}, found {len(hits)}")
    return hits[0]


def _find_restrict_steal(ov: bytearray) -> int:
    """Return the byte offset of the restriction row for 0x19D8 (existing or a phantom to steal)."""
    base = RESTRICT_BASE - RAM_BASE
    ww = None
    steal = None
    for i in range(RESTRICT_COUNT):
        off = base + i * RESTRICT_STRIDE
        cid = struct.unpack_from("<H", ov, off)[0]
        if cid == DONOR_CID:
            ww = off
        if cid == RESTRICT_STEAL_CID and steal is None:
            steal = off
    if ww is not None:
        return ww
    assert steal is not None, f"phantom restriction donor 0x{RESTRICT_STEAL_CID:04X} not found"
    return steal


def _resort_restrict(ov: bytearray) -> None:
    """Re-sort the equip-restriction table by cid (it is binary-searched)."""
    base = RESTRICT_BASE - RAM_BASE
    rows = [bytes(ov[base + i * RESTRICT_STRIDE: base + (i + 1) * RESTRICT_STRIDE])
            for i in range(RESTRICT_COUNT)]
    rows.sort(key=lambda r: struct.unpack_from("<H", r, 0)[0])
    for i, r in enumerate(rows):
        ov[base + i * RESTRICT_STRIDE: base + (i + 1) * RESTRICT_STRIDE] = r
    cids = [struct.unpack_from("<H", ov, base + i * RESTRICT_STRIDE)[0]
            for i in range(RESTRICT_COUNT)]
    assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), "restriction not sorted"


# ===========================================================================
# Cave stubs
# ===========================================================================
def _build_target() -> bytes:
    """Spellcaster-only equip-target predicate (restriction-table +4 predicate).

    *** POLARITY: the generic enumerator 0x021E5200 does `blx pred; cmp r0,#0;
    bne 0x21e5238`, and 0x21e5238 is the MARK-VALID path (the same one a card with
    NO restriction row falls through to -- that's how any-monster equips work).  So
    predicate != 0 -> ACCEPT (mark valid); predicate == 0 -> the -1 reject path.
    Therefore Spellcaster -> return 1 (allow), everything else -> return 0. ***

    Decode mirrors Trial's OWN native target filter (0x021E4D80): use REF_DECODE
    (0x21A241C) -- NOT 0x21A220C (opposite byte order):
        r0 = REF_DECODE([ctx+0xC])      ; -> (zone<<8)|side, 0xFFFF miss
        side = r0 & 1; zone = (r0>>8) & 0xFF
        if zone > 4: exclude            ; must be a monster zone
        cid = [player+0x34 + zone*0x14] & 0x3FFF
        allow (return 0) iff get_race(cid) == Spellcaster (18)
    """
    PLAYER_BASE = 0x0229AC94
    PLAYER_STRIDE = 0x0B3C
    a = EffectBuilder()
    (a
     .insn("PUSH", "{R4, R5, R6, LR}")
     .insn("LDRH", "R0, [R0, #0xC]")     # candidate target packed ref
     .bl(REF_DECODE)                     # -> (zone<<8)|side, or 0xFFFF miss
     .ldr_const(1, 0xFFFF)
     .insn("CMP", "R0, R1")
     .insn("BEQ", "exclude")
     .insn("MOV", "R1, #0x1")
     .insn("AND", "R1, R0")              # r1 = side (r0 & 1)
     .insn("LSR", "R0, R0, #0x8")        # r0 = zone
     .insn("MOV", "R2, #0xFF")
     .insn("AND", "R0, R2")              # zone &= 0xFF
     .insn("CMP", "R0, #0x4")
     .insn("BHI", "exclude")              # zone must be 0..4
     .insn("ADD", "R4, R0, #0x0")        # r4 = zone
     .ldr_const(2, PLAYER_STRIDE)
     .insn("MUL", "R2, R1")              # side * 0xB3C
     .ldr_const(0, PLAYER_BASE)
     .insn("ADD", "R2, R2, R0")          # player struct base
     .insn("ADD", "R2, #0x34")           # monster zone array
     .insn("MOV", "R0, #0x14")
     .insn("MUL", "R4, R0")              # zone * 0x14
     .insn("ADD", "R2, R2, R4")          # &zone_word
     .insn("LDR", "R0, [R2, #0x0]")      # zone word
     .insn("LSL", "R0, R0, #0x12")
     .insn("LSR", "R0, R0, #0x12")       # cid = word & 0x3FFF
     .blx(GET_RACE)                      # ARM9 get_race(cid)
     .insn("CMP", "R0, #0x12")           # 18 = Spellcaster
     .insn("BNE", "exclude")             # not a Spellcaster -> exclude
     .insn("MOV", "R0, #0x1")            # Spellcaster -> ALLOW (predicate!=0 -> mark valid)
     .insn("POP", "{R4, R5, R6, PC}")
     .label("exclude")
     .insn("MOV", "R0, #0x0")            # non-Spellcaster / miss -> EXCLUDE (return 0 -> -1 path)
     .insn("POP", "{R4, R5, R6, PC}"))
    code = a.assemble(TARGET_ADDR)
    assert len(code) <= TARGET_RESERVE, f"target {len(code)}B exceeds reserve 0x{TARGET_RESERVE:X}"
    assert_thumb1_only(code, TARGET_ADDR)
    return code


def _build_res() -> bytes:
    """cls3 field-ignition resolver FSM: send both to GY, draw 2.

    The engine stores the returned state in [FSM_STATE+0x70] and re-invokes res.
    Wonder Wand needs no target pick, so this is a minimal 2-state FSM:

      state 0x80 (entry): find + send the equipped monster to GY; send THIS
                          equip to GY; draw 2 for the controller     -> 0x75
      state 0x75 (done):  EFFECT_DONE(player)                        -> 0
      other:              return 0

    res(ctx):
        r5 = [FSM_STATE+0x70]
        if r5 == 0x80: ...action...; return 0x75
        if r5 == 0x75: EFFECT_DONE([ctx+2]); return 0
        return 0
    """
    a = EffectBuilder()
    (a
     .insn("PUSH", "{R4, R5, LR}")
     .insn("ADD", "R4, R0, #0x0")        # r4 = ctx
     .ldr_const(5, FSM_STATE)
     .insn("LDR", "R5, [R5, #0x70]")     # current state
     .if_eq(R5, 0x80, "entry")
     .if_eq(R5, 0x75, "done")
     .insn("MOV", "R0, #0x0")            # unknown state -> nothing
     .insn("POP", "{R4, R5, PC}")
     # --- 0x80: send equipped monster, send this card, draw 2 ---
     .label("entry")
     # find the equipped monster ref: FIND_EQUIPPED([ctx+2], [ctx+3])
     .insn("LDRB", "R0, [R4, #0x2]")     # player
     .insn("LDRB", "R1, [R4, #0x3]")     # equip aux (target key), as Trial's cond uses
     .bl(FIND_EQUIPPED)                  # r0 = equipped monster ref (0xFFFF if none)
     .ldr_const(1, 0xFFFF)
     .insn("CMP", "R0, R1")
     .insn("BEQ", "send_self")           # no equipped monster -> just send self + draw
     # send the equipped monster by ref
     .insn("ADD", "R1, R0, #0x0")        # r1 = monster ref
     .insn("ADD", "R0, R4, #0x0")        # r0 = ctx
     .insn("MOV", "R2, #0x1")            # (send flag)
     .bl(SEND_MON_BY_REF)
     .label("send_self")
     # send THIS equip card to the GY
     .insn("ADD", "R0, R4, #0x0")
     .bl(SEND_TO_GY_RAM)
     # draw 2 for the controller
     .insn("LDRB", "R0, [R4, #0x2]")
     .insn("MOV", "R1, #0x2")
     .bl(DRAW)
     .insn("MOV", "R0, #0x75")           # -> done state
     .insn("POP", "{R4, R5, PC}")
     # --- 0x75: cleanup ---
     .label("done")
     .insn("LDRB", "R0, [R4, #0x2]")
     .bl(EFFECT_DONE)
     .insn("MOV", "R0, #0x0")
     .insn("POP", "{R4, R5, PC}"))
    code = a.assemble(RES_ADDR)
    assert len(code) <= RES_RESERVE, f"res {len(code)}B exceeds reserve 0x{RES_RESERVE:X}"
    assert_thumb1_only(code, RES_ADDR)
    return code


# ===========================================================================
# PART A -- overlay 3 effect
# ===========================================================================
def apply_effect(ov: bytearray, rom) -> None:
    # --- install the cave stubs ---
    # NOTE: neither stub is referenced by any table right now.  WW_TARGET is the
    # clause-1 (Spellcaster-only) predicate and WW_RES the clause-3 ignition FSM;
    # both are kept installed so their ov5 slots stay claimed in the allocation
    # ledger, but nothing dispatches to them until the equip-target gate and the
    # field-ignition table are actually located.  They are inert, not live.
    ov5_cave.install_cave(rom, TARGET_ADDR, _build_target(), reserve=TARGET_RESERVE)
    ov5_cave.install_cave(rom, RES_ADDR, _build_res(), reserve=RES_RESERVE)

    # --- A1: clause 3 groundwork -- cls3 res -> WW_RES (cond/timing kept native) ---
    # This is the donor's real record: cls3[237] @0x0227B3AC, cid 0x19D8 at +0x00.
    # UNCHANGED from the pre-existing patch; it is correct.  (It is clause-3 work
    # and is NOT confirmed in-game -- WW_RES's FSM protocol is UNVERIFIED -- but it
    # writes the right field of the right record, so it stays as it was.)
    coff = _find_cls3_row(ov)
    old_res = struct.unpack_from("<I", ov, coff + 0x04)[0]
    assert old_res in (TRIAL_NATIVE_CLS3_RES, RES_ADDR | 1), (
        f"cls3 res is 0x{old_res:08X}, expected Trial-native or WW shim")
    struct.pack_into("<I", ov, coff + 0x04, RES_ADDR | 1)
    print(f"A1 cls3[{(coff - (CLS3_BASE - RAM_BASE)) // CLS3_STRIDE}] "
          f"@0x{RAM_BASE + coff:08X}: +04 res -> 0x{RES_ADDR | 1:08X} (cond/timing kept native)")

    # --- A2: DELETED -- it was corrupting Demise, King of Armageddon ---
    # The old A2 called _find_master_row() on the fictitious 4116-row grid and wrote
    # "+0C targ = 0" to remove the donor's target predicate.  On the real geometry
    # that address is 0x0227B3A4 = cls3[236] field +0x10, and cls3[236] is
    # cid 0x19D5 "Demise, King of Armageddon" -- so it zeroed a bystander card's
    # timing slot and never touched the donor at all.  There is no "+0C targ" on a
    # cls3 record to remove (Trial's cls3[237] is +0C cond 0x021FA685 / +10 timing
    # 0x021E7C3D), so the edit has no correct relocation: it is simply removed.
    # verify() asserts Demise's record is byte-identical to the base ROM.

    # --- A3: clause 2 -- ATK grant 800 -> 500 in the equip grant table ---
    goff = _find_grant_row(ov)
    old_atk, old_def = struct.unpack_from("<hh", ov, goff + 2)
    assert old_atk in (TRIAL_NATIVE_ATK, WW_ATK_GAIN), (
        f"equip grant ATK is {old_atk}, expected donor-native {TRIAL_NATIVE_ATK} "
        f"or already-patched {WW_ATK_GAIN}")
    assert old_def == WW_DEF_GAIN, f"equip grant DEF is {old_def}, expected {WW_DEF_GAIN}"
    struct.pack_into("<hh", ov, goff + 2, WW_ATK_GAIN, WW_DEF_GAIN)
    print(f"A3 equip-grant row @0x{RAM_BASE + goff:08X} (cid 0x{DONOR_CID:04X}): "
          f"ATK {old_atk:+d} -> {WW_ATK_GAIN:+d}, DEF {WW_DEF_GAIN:+d} (in place, count-neutral)")


# ===========================================================================
# Orchestration
# ===========================================================================
def main(src: str = SRC, out: str = OUT, *, write_text: bool = False) -> None:
    rom, ov = load_overlay3(src)
    ov = bytearray(ov)
    orig_len = len(ov)
    apply_effect(ov, rom)
    assert len(ov) == orig_len, f"overlay-3 length changed ({orig_len} -> {len(ov)})"
    save_overlay3(rom, bytes(ov), out)

    # PART B/C: Trial is already an Equip Spell -> PART B is a no-op (donor fields);
    # only PART C (name/desc) changes.
    apply_stats_and_text(
        out,
        cid=DONOR_CID,
        attribute="NONE",
        race="Unknown(23)",
        level=0,
        atk=0,
        defense=0,
        card_type=None,
        name=NEW_NAME,
        desc=NEW_DESC,
        langs=TEXT_LANGS,
        write_text=write_text,
        skip_name_if_too_long=True,
    )
    print(f"Wonder Wand written to {out} (write_text={write_text})")


def verify(out: str = OUT) -> None:
    """Re-open the built ROM and assert every edit this module claims to make.

    Also asserts the NEGATIVE that matters: the master row after the donor's
    (cid 0x19F1 "Great Spirit") must be byte-identical to the base ROM, proving
    the deleted cls3 write is really gone.
    """
    _, ov = load_overlay3(out)
    ov = bytearray(ov)
    _, base_ov = load_overlay3(SRC)
    base_ov = bytearray(base_ov)

    # --- clause 2: the donor's equip grant row is +500 ATK / +0 DEF ---
    goff = _find_grant_row(ov)
    cid, atk, dfn = struct.unpack_from("<Hhh", ov, goff)
    assert cid == DONOR_CID, f"grant row cid 0x{cid:04X} != 0x{DONOR_CID:04X}"
    assert (atk, dfn) == (WW_ATK_GAIN, WW_DEF_GAIN), (
        f"grant row is {atk:+d}/{dfn:+d}, expected {WW_ATK_GAIN:+d}/{WW_DEF_GAIN:+d}")
    print(f"  OK  equip grant @0x{RAM_BASE + goff:08X}: cid 0x{cid:04X} "
          f"ATK{atk:+d} DEF{dfn:+d}")

    # --- the grant table is still sorted and the right size (binary-searched) ---
    gbase = EQUIP_GRANT_BASE - RAM_BASE
    cids = [struct.unpack_from("<H", ov, gbase + i * EQUIP_GRANT_STRIDE)[0]
            for i in range(EQUIP_GRANT_COUNT)]
    assert all(cids[i] < cids[i + 1] for i in range(len(cids) - 1)), "grant table unsorted"
    print(f"  OK  equip grant table still sorted, {EQUIP_GRANT_COUNT} records")

    # --- A1: the donor's cls3 record points at WW_RES, cond/timing still native ---
    coff = _find_cls3_row(ov)
    row = struct.unpack_from("<6I", ov, coff)
    assert row[1] == (RES_ADDR | 1), f"cls3 +04 res is 0x{row[1]:08X}, expected WW_RES"
    base_row = struct.unpack_from("<6I", base_ov, coff)
    for k, off in ((3, 0x0C), (4, 0x10)):
        assert row[k] == base_row[k], (
            f"cls3 +{off:02X} changed (0x{base_row[k]:08X} -> 0x{row[k]:08X}); "
            f"the native offer wiring must stay intact")
    print(f"  OK  cls3[{(coff - (CLS3_BASE - RAM_BASE)) // CLS3_STRIDE}] "
          f"@0x{RAM_BASE + coff:08X}: +04 res -> WW_RES, +0C/+10 native")

    # --- no collateral damage: the bystander the old A2 corrupted is intact ---
    doff = _find_cls3_row(ov, DEMISE_CID)
    assert ov[doff:doff + CLS3_STRIDE] == base_ov[doff:doff + CLS3_STRIDE], (
        f"cls3 record for cid 0x{DEMISE_CID:04X} (Demise, King of Armageddon) was "
        f"MODIFIED -- the deleted A2 write is back")
    print(f"  OK  cls3 record for cid 0x{DEMISE_CID:04X} (Demise, King of Armageddon) "
          f"@0x{RAM_BASE + doff:08X} byte-identical to base ROM")

    # --- the cls3 table is still sorted and count-neutral (binary-searched) ---
    cbase = CLS3_BASE - RAM_BASE
    ccids = [struct.unpack_from("<H", ov, cbase + i * CLS3_STRIDE)[0]
             for i in range(CLS3_COUNT)]
    assert all(ccids[i] <= ccids[i + 1] for i in range(len(ccids) - 1)), "cls3 unsorted"
    assert ccids.count(DONOR_CID) == 1, "donor has more than one cls3 record (shadowing risk)"
    print(f"  OK  cls3 still sorted, {CLS3_COUNT} rows, exactly 1 record for the donor")

    # --- overlay 3 length unchanged ---
    assert len(ov) == len(base_ov), f"overlay-3 length changed ({len(base_ov)} -> {len(ov)})"
    print(f"  OK  overlay-3 length unchanged ({len(ov)} bytes)")
    print("verify(): Wonder Wand clause 2 OK "
          "(clauses 1 and 3 intentionally NOT implemented)")


if __name__ == "__main__":
    main()
    verify()

"""The SHARED criteria-row-offset hook: one stub, a REGISTER of cids.

WHY THIS MODULE EXISTS
======================
`dispatch.criteria_block_size_tiers` / `dispatch.selection_param_and_zone`: the
row resolver 0x02243B9C turns (cid, param) into a row index by walking back to the
LEFTMOST row carrying the cid and adding r4.  For a cid in membership list A it
clamps `r4 = (param == 0) ? 0 : 1`, and for a cid in neither list it forces
`r4 = 0`.  Either way a donor can only ever address its rows 0 and 1 -- a hard
ceiling that no number of extra rows lifts.

Dark Simorgh 0x1E5A escapes it with a HAND-WRITTEN ARM in the compiled
disambiguation switch (0x02243DEA, `r4 = 2 + (desc[+0x12] != 0)`).  A donor cannot
be added to that switch by data, so we hook the disambiguation at 0x02243BEC and
supply the equivalent arm ourselves.

*** AND THERE IS EXACTLY ONE 4-BYTE BL AT THAT SITE. ***  A stub owned by one card
module can therefore only ever serve one card.  Lightpulsar shipped one; Darkflare
needed a second arm; re-pointing the hook would have broken Lightpulsar's clauses 2
AND 3, both in-game confirmed.  So the hook, the stub and the cid register live
here, exactly the way handss_banish_cost.py owns the shared payment stubs -- and for
exactly the same reason.

REGISTERED CARDS
================
    0x0FB1  Sword Arm of Dragon -> Lightpulsar Dragon   IN-GAME CONFIRMED 2026-08-17
    0x1646  Battle Footballer   -> Darkflare Dragon      (2026-08-18)
    0x1464  The Gross Ghost...  -> Upstart Golden Ninja  IN-GAME CONFIRMED 2026-09-01
    0x224C  Changer Synchron    -> Jet Synchron          (2026-09-03, clause 2)
    0x11A3  Bracchio-raidus     -> Accel Synchron
    0x126F  Meteor B. Dragon    -> Accel Synchro Stardust Dragon   IN-GAME CONFIRMED 2026-09-14

Adding a third card is one entry in ARMS.

⚠️⚠️ DUEL-ONLY, AND THE BLAST RADIUS IS WIDE.  0x02243B9C is the row resolver EVERY
card that selects anything passes through, and this stub is in the ov5 cave, which
overlay 41 evicts in a puzzle.  Accepted by explicit user decision 2026-08-14.
Nothing here changes clause-1-style pure-ov3 effects, which never reach the hook.

HOW AN ARM DISCRIMINATES
========================
The stub keys on the ACTING DESCRIPTOR at [0x0229A9FC+0x50], NOT on the resolver's
r5 cid argument -- because the same cid asks for different rows at different moments
and only the descriptor says which moment it is:

    desc[+0x00] u16  cid          which card
    desc[+0x03] u8   zone         0x0B hand / 0x0E GY / 0..4 a monster zone
    desc[+0x04] u8   event code   0x1E = a sent-to-GY relocation, 0 = a GY action
    desc[+0x05] u8   record class 3 == cls3, i.e. an ON-FIELD IGNITION
    desc[+0x12] u16  pass index   maintained by a two-pass selection cost

⚠️ Because the discriminator is desc[+0], an arm's card must NOT swap desc[+0] to a
proxy cid during selection (an earlier Lightpulsar design did; it also broke
re-entry, since find_event_handler binary-searches cls2 by desc[+0]).

*** WHY A STALE DESCRIPTOR CANNOT LEAK ACROSS EFFECTS (measured 2026-08-18). ***  The
obvious hazard is that a card with two clauses on different paths -- Darkflare's
clause 1 runs from the HAND, clause 2 from the FIELD -- could have clause 1's row
lookups hijacked by a descriptor left behind by clause 2.  It cannot: the pointer is
SCOPED, not global state.  The slot dispatcher SAVES the old value, writes its own
(`str r5,[r0,#0x50]` @0x0224AE20) and RESTORES it (`str r7,[r0,#0x50]` @0x0224AE3C)
around every slot invocation, and the activation state machine sets it once per
activation (`str r5,[r0,#0x50]` @0x02217F8C).  So the descriptor an arm sees always
belongs to the activation actually running.

REGISTER CONTRACT AT THE HOOK SITE
==================================
r5 = cid, r4 = the caller's param, r6 = the leftmost row index, r7 = the row count.
r0/r1/r3 are scratch (the native code recomputes them).  An arm writes r4 and jumps
to the common tail 0x02243EEE (`r2 = leftmost + r4`); anything else replays the two
displaced instructions and resumes at 0x02243BF0.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import ov3_off as _off
from otn_enhanced.effects.common import bl as _bl

# --- the hook site, inside the shared row resolver 0x02243B9C ---------------
ROWHOOK_SITE = 0x02243BEC       # `ldr r1,=0x0227134C ; adds r0,r5,#0`   (4 B)
ROWHOOK_NATIVE = bytes.fromhex("8449281c")
ROWHOOK_RESUME = 0x02243BF0     # the `movs r2,#0x3b` that follows
ROWHOOK_TAIL = 0x02243EEE       # the common tail: r2 = leftmost + r4
LISTA_LIT = 0x0227134C          # membership list A, the literal we displace
ACTING_DESC = 0x0229A9FC        # + 0x50 = the acting descriptor pointer

RESERVE = 0x180

# --- Lightpulsar Dragon 0x0FB1 ---------------------------------------------
# Clause 2 (SS from the GY, paying from the hand) owns rel 2/3 and alternates
# them from the pass index; clause 3 (the sent-from-the-field trigger) owns rel 4.
# Both carry the SAME cid and the SAME zone 0x0E, so they are separated by the
# EVENT CODE: 0x1E for a relocation event, 0 for clause 2's GY-action descriptor
# (and clause 2 can never reach 0x1E anyway -- its off-field gate 0x021ECC28 caps
# desc[+4] at 6).  Measured from rom_eclipse_wyvern.ml2 /.ml3.
LP_CID = 0x0FB1
LP_ZONE_GY = 0x0E
LP_EVENT_MIN = 7
LP_ROW_REL = 4
def ARM_LP(b: EffectBuilder, tag: str) -> None:
    b.insn("LDRB", "R0, [R3, #0x3]")
    b.insn("CMP", f"R0, #{LP_ZONE_GY:#x}")
    b.insn("BNE", "native")
    b.insn("LDRB", "R0, [R3, #0x4]")
    b.insn("CMP", f"R0, #{LP_EVENT_MIN - 1:#x}")
    b.insn("BLE", f"{tag}c2")
    b.insn("MOV", f"R4, #{LP_ROW_REL:#x}")
    b.insn("B", "tail")
    b.label(f"{tag}c2")
    b.insn("LDRH", "R0, [R3, #0x12]")
    b.insn("MOV", "R4, #0x0")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", f"{tag}set")
    b.insn("MOV", "R4, #0x1")
    b.label(f"{tag}set")
    b.insn("ADD", "R4, R4, #0x2")
    b.insn("B", "tail")

# --- Darkflare Dragon 0x1646 -----------------------------------------------
# Clause 2 is an ON-FIELD IGNITION, so its descriptor is cls3 (desc[+5] == 3) --
# a discriminator clause 1 can never produce, because clause 1 runs from the hand
# through the hand-SS dispatch and is pure ov3.  That is what keeps clause 1's
# shipped, in-game-confirmed list-A `param == 0 ? 0 : 1` behaviour untouched.
#
# Three consumers all ask for param 0 and all need a DIFFERENT row, so the stage
# is explicit: the cost stub sets STAGE before each selection, and the target step
# sets it back to 2.  It is a byte in its own cave slot rather than desc[+0x12],
# because desc[+0x12] is the recorded-pick COUNT that the banish resolver
# 0x02208D19 reads to decide what to banish.
DF_CID = 0x1646
DF_CLS3 = 3
DF_STAGE_TARGET = 2             # rel 4 -- the either-GY row; the shipped default

# ⚠️ DIAGNOSTIC. Two in-game results are each consistent with BOTH "the
# arm fires" and "the arm never fires and every lookup falls back to rel 0", because
# clause 1's rel-0 row is itself an own-GY selection. Rather than guess a third time
# (otn-escalate-to-measurement), the arm counts what it actually does. Set False to
# ship; the counters cost 15 halfwords and are write-MANY by design -- [+0] vs [+4]
# is exactly the pair that separates "never reached" from "reached and rejected".
DF_DIAG = False
def ARM_DF_PLAIN(b: EffectBuilder, tag: str) -> None:
    b.insn("LDRB", "R0, [R3, #0x5]")
    b.insn("CMP", "R0, #0x3")
    b.insn("BNE", "native")
    b.ldr_const(0, ov5_cave.CAVE_DF_STAGE)
    b.insn("LDRB", "R4, [R0, #0x0]")
    b.insn("ADD", "R4, R4, #0x2")
    b.insn("B", "tail")

def ARM_DF_DIAG(b: EffectBuilder, tag: str) -> None:
    b.ldr_const(1, ov5_cave.CAVE_DF_DIAG)
    b.insn("LDR", "R0, [R1, #0x0]")
    b.insn("ADD", "R0, R0, #0x1")
    b.insn("STR", "R0, [R1, #0x0]")
    b.insn("LDRB", "R0, [R3, #0x5]")
    b.insn("CMP", "R0, #0x3")
    b.insn("BNE", "native")
    b.insn("LDR", "R0, [R1, #0x4]")
    b.insn("ADD", "R0, R0, #0x1")
    b.insn("STR", "R0, [R1, #0x4]")
    b.insn("LDRB", "R0, [R3, #0x3]")
    b.insn("STRB", "R0, [R1, #0x8]")
    b.insn("LDRB", "R0, [R3, #0x4]")
    b.insn("STRB", "R0, [R1, #0x9]")
    b.ldr_const(0, ov5_cave.CAVE_DF_STAGE)
    b.insn("LDRB", "R4, [R0, #0x0]")
    b.insn("STRB", "R4, [R1, #0xa]")
    b.insn("ADD", "R4, R4, #0x2")
    b.insn("STRB", "R4, [R1, #0xb]")
    b.insn("B", "tail")

ARM_DF = ARM_DF_DIAG if DF_DIAG else ARM_DF_PLAIN

# --- Upstart Golden Ninja 0x1464 -------------------------------------------
# ONE activation of ONE cls3 cid reads TWO different rows, so neither of the
# discriminators above works here: both steps carry the same desc[+0] and the
# same desc[+5] == 3.  What separates them is desc[+7], THE "COST HAS ALREADY
# RUN" FLAG, disassembled from the activation state machine 0x02217F80 on
#
#
#     02217F8C  str  r5,[r0,#0x50]   ; [0x0229A9FC+0x50] = the acting descriptor
#     02217F8E  ldrb r0,[r5,#7]      ; desc[+7]
#     02217F92  bne  0x02217FB2      ; already run -> skip the cost
#     02217FA2  bl   0x0224AE50      ; RUN THE COST (slot4)
#     02217FB4  strb r0,[r5,#7]      ; desc[+7] := 1, AFTER the cost
#     02217FBE  movs r0,#0x76        ; yield -> resolution follows
#
# So desc[+7] == 0 while the Trap is being selected from the hand and == 1 by the
# time the deck-SS chassis 0x02206CAD runs its search.  That is exactly the split
# the card needs, and it is why this card needs the hook AT ALL: both consumers
# pass param 0 (the deck-SS side because 0x02234E78's default leaf 0x022355F0 is
# `movs r0,#0` and the donor is in none of its five lists; the cost side because
# 0x021E7245 @0x021E72A8 does `rsbs r2,r2,#0` on a zeroed pass counter, and
# 0x0224B9F0 @0x0224B9F8 stores that r2 as the param).  With both params 0, LIST A
# membership cannot separate them -- it only ever distinguishes 0 from non-0 --
# so the rows would silently collapse onto rel 0.
#
# ⚠️ TWICE CORRECTED, both times by an in-game test, and the reasons are the
# reusable part:
#
# TEST 1 killed desc[+7].  The flag really is 0-during-cost / 1-during-resolution,
# but THE MENU OFFER-CHECK ALSO RUNS AT desc[+7] == 0, so {menu, cost} share a
# value while needing different rows.  The rows were reordered at the same time --
# rel 0 is the DECK row, because the offer-check 0x021F0419 probes rel 0 and, on a
# HAND row, 0x02243FE0's param is a candidate INDEX rather than a row selector, so
# it only ever tested hand slot 0 (the Trap sat at hand index 4; never offered).
#
# TEST 2 killed the STAGE-byte latch that replaced it.  A latch set around the
# call to 0x021E7245 cannot work, because that call only ARMS the selection and
# returns -- the candidates are filtered LATER, when the picker runs, by which
# time the stub has already cleared the byte.  Measured in rom_upstart.ml3 with
# the picker open: CAVE_UGN_STAGE was 0 while `sel mode` was 8, so the hand
# picker was unfiltered and any card could be discarded.
#
# WHAT ACTUALLY WORKS is the cost machine's OWN state word, which the engine
# maintains across the whole asynchronous selection: [0x0229AAFC + 0x7C] is
# non-zero exactly while the cost is running (2 in .ml3) and 0 at the menu and at
# resolution (.ml2 / .ml4).  The reset is proven, not assumed -- the activation
# machine does `movs r1,#0 ; str r1,[r4,#0x7c]` at 0x02217FB6/0x02217FBA, r4 =
# 0x0229AAFC, in the same breath as `strb r0,[r5,#7]`.  One global read, no latch,
# no timing window.
UGN_CID = 0x1464
UGN_COST_STATE = 0x0229AAFC         # + 0x7C = the record-driven cost's state word
UGN_COST_STATE_OFF = 0x7C
#
# TEST 3 added the second half.  The cost-state word covers the COST, but the
# card also has to SCAN THE HAND at the menu to decide whether it may be offered
# at all -- the stock condition only probes rel 0 (the Deck row), so with no Trap
# in hand the effect was offered and the discard picker opened empty and
# unescapable.  That scan is a synchronous 0x02243FE0 loop inside the condition
# stub, and it needs rel 1 while it runs, so the arm ORs in a probe flag.
# ⚠️ A latch is correct HERE and was wrong for the cost: this one wraps a call
# that RETURNS A COUNT IMMEDIATELY, not one that arms an asynchronous picker.
def ARM_UGN(b: EffectBuilder, tag: str) -> None:
    b.ldr_const(0, ov5_cave.CAVE_UGN_PROBE)
    b.insn("LDRB", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", f"{tag}hand")
    b.ldr_const(0, UGN_COST_STATE)
    b.insn("LDR", f"R0, [R0, #{UGN_COST_STATE_OFF:#x}]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", f"{tag}hand")
    b.insn("MOV", "R4, #0x0")
    b.insn("B", "tail")
    b.label(f"{tag}hand")
    b.insn("MOV", "R4, #0x1")
    b.insn("B", "tail")


# --- Jet Synchron 0x224C ----------------------------------------------------
# The SAME shape as Upstart Golden Ninja's, and for the same reason -- one cid
# whose two consumers need two different rows, both passing param 0 -- but a
# simpler case, so it needs no probe flag.
#
#   rel 0  {aux 0x0050, 0x0223CAF5, flags 0x0002}  CLAUSE 1: 1 "Junk" MONSTER
#                                                  from the DECK to the hand.
#   rel 1  {aux 0xFFFF, 0x0223CB19, flags 0x000E}  CLAUSE 2's COST: any 1 card
#                                                  in the HAND (Plaguespreader
#                                                  Zombie's own row, row 766).
#
# rel 0 MUST be the Deck row (dispatch.offer_check_probes_rel0_only): the
# offer-check probes rel 0 only, and on a HAND row 0x02243FE0's param is a
# candidate INDEX rather than a row selector, so a hand row there would test hand
# slot 0 and nothing else.
#
# WHY NO PROBE FLAG.  card.upstart_golden_ninja needs one because its condition
# has to SCAN the hand synchronously through 0x02243FE0 to decide whether it may
# be offered (its cost is Trap-only, and offering with no Trap in hand opened an
# empty, inescapable picker).  Jet Synchron's printed cost is "1 card", so its
# condition just reads the hand COUNT at player+0x0C directly and never touches a
# criteria row -- confirmed by disassembling both halves of its other gate
# 0x021FF06D (0x021F0168 -> 0x021B945C, 0x021F04FC -> 0x021A2510 / 0x021A2618;
# neither reaches the criteria evaluator).
#
# So the cost machine's own state word is the whole discriminator, and it is the
# very counter the cloned cost runs on (CAVE_JS_COST bumps [0x0229AAFC+0x7C] to 1
# at the end of its phase 0, which is exactly the window in which the picker asks
# the callback 0x022065F8 to filter).
JS_CID = 0x224C
def ARM_JS(b: EffectBuilder, tag: str) -> None:
    b.ldr_const(0, UGN_COST_STATE)
    b.insn("LDR", f"R0, [R0, #{UGN_COST_STATE_OFF:#x}]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", f"{tag}hand")
    b.insn("MOV", "R4, #0x0")
    b.insn("B", "tail")
    b.label(f"{tag}hand")
    b.insn("MOV", "R4, #0x1")
    b.insn("B", "tail")

# --- Accel Synchron -----------------------------------------------------------
# The donor owns TWO criteria rows on ONE cls3 record, because two printed clauses
# share that record (a second cls3 record is unreachable -- find_event_handler
# returns the leftmost, dispatch.cls_table_selector):
#     row 0  {aux 0x004C, 0x0223CAF5, 0x0002}  clause 1, "send 1 'Synchron' monster
#                                              from your Deck to the GY"
#     row 1  {aux 0xFFFF, 0x0223D21D, 0x0802}  clause 3, Formula Synchron's
#                                              opponent's-Main-Phase Synchro Summon
# Without an arm the donor could never reach row 1 at all: the row resolver forces
# r4 = 0 for a cid in neither membership list, which is this module's whole reason
# to exist.  The discriminator is WHOSE TURN IT IS -- the same test the cls3 slot
# splitters use, and the same one Formula's own condition 0x021F1490 applies
# (`[0x0229DD14+0x34] == 1 - desc[+2]`, synchro.opponent_turn_summon_is_formulas_cls3)
# -- so it is not a heuristic, it is the printed text: clause 1 is an ignition on
# YOUR Main Phase, clause 3 is printed "During your OPPONENT's Main Phase".
AS_CID = 0x11A3
AS_DUEL_STATE = 0x0229DD14
AS_TURN_OFF = 0x34
def ARM_AS(b: EffectBuilder, tag: str) -> None:
    b.ldr_const(0, AS_DUEL_STATE)
    b.insn("LDR", f"R0, [R0, #{AS_TURN_OFF:#x}]")
    b.insn("LDRB", "R1, [R3, #0x2]")
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", f"{tag}mine")
    b.insn("MOV", "R4, #0x1")
    b.insn("B", "tail")
    b.label(f"{tag}mine")
    b.insn("MOV", "R4, #0x0")
    b.insn("B", "tail")

# --- Accel Synchro Stardust Dragon 0x126F (Meteor B. Dragon) -------------------
#     row 0  {aux 0xFFFF, 0x0223C9D1, 0x00898002}  C1 (cls1): Lv<=2 Tuner from the GY
#     row 1  {aux 0x1E36, 0x022423C9, 0x0802}      C2 (cls3): "Stardust Dragon" from the ED
#     row 2  {aux 0xFFFF, 0x02240EF5, 0x0802}      C3 (same cls3 descriptor): Urgent Tuning's
#                                                  "Synchro Summon using monsters you control"
# C1 vs C2/C3 = the RECORD CLASS desc[+5] (Darkflare's discriminator).  C2 vs C3 share one
# descriptor, so they are split by CAVE_ASSD_STAGE, which accel_synchro_stardust_dragon's
# cls3 dispatcher sets to 1 exactly while the shared Synchro resolver runs as C2's follow-up
# and clears when it returns 0.  In-game confirmed by user (all three rows).
def ARM_ASSD(b: EffectBuilder, tag: str) -> None:
    b.insn("LDRB", "R0, [R3, #0x5]")
    b.insn("CMP", "R0, #0x3")
    b.insn("BNE", "native")
    b.ldr_const(0, ov5_cave.CAVE_ASSD_STAGE)
    b.insn("LDRB", "R4, [R0, #0x0]")
    b.insn("ADD", "R4, #0x1")
    b.insn("B", "tail")

# (cid, label tag, arm source, one-line description)
PSI_CID = 0x1008
def ARM_PSI(b: EffectBuilder, tag: str) -> None:
    b.ldr_const(1, PSI_CID)
    b.insn("CMP", "R5, R1")
    b.insn("BNE", "native")
    b.insn("LDRB", "R0, [R3, #0x5]")
    b.insn("CMP", "R0, #0x3")
    b.insn("BNE", "native")
    b.ldr_const(0, UGN_COST_STATE)
    b.insn("LDR", f"R0, [R0, #{UGN_COST_STATE_OFF:#x}]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", f"{tag}hand")
    b.insn("MOV", "R4, #0x1")
    b.insn("B", "tail")
    b.label(f"{tag}hand")
    b.insn("MOV", "R4, #0x2")
    b.insn("B", "tail")

# Souleating Oviraptor 0x0FC6 (Two-Headed King Rex): row 0 = C1's Deck Dinosaur (cls1), row 1 = C2's GY
# Dinosaur for the Special Summon (cls3).  Psi's shape minus its cost-stage split.  In-game confirmed by user.
OVI_CID = 0x0FC6
def ARM_OVI(b: EffectBuilder, tag: str, cid: int = OVI_CID) -> None:
    b.ldr_const(1, cid)
    b.insn("CMP", "R5, R1")
    b.insn("BNE", "native")
    b.insn("LDRB", "R0, [R3, #0x5]")
    b.insn("CMP", "R0, #0x3")
    b.insn("BNE", "native")
    b.insn("MOV", "R4, #0x1")
    b.insn("B", "tail")

# Elemental HERO Shadow Mist 0x111F (Ryu-Kishin Powered): row 0 = C1's Mask Change (cls1 SS trigger),
# row 1 = C2's "HERO" monster (cls2 sent-to-GY trigger).  Oviraptor's shape keyed on the cls2 class
# instead of cls3 -- the same record-class discriminator Lightpulsar's cls2 trigger arm relies on.
SM_CID = 0x111F
def ARM_SM(b: EffectBuilder, tag: str, cid: int = SM_CID) -> None:
    b.ldr_const(1, cid)
    b.insn("CMP", "R5, R1")
    b.insn("BNE", "native")
    b.insn("LDRB", "R0, [R3, #0x5]")
    b.insn("CMP", "R0, #0x2")
    b.insn("BNE", "native")
    b.insn("MOV", "R4, #0x1")
    b.insn("B", "tail")

ARMS: tuple[tuple[int, str, str, str], ...] = (
    (LP_CID, "lp", ARM_LP,
     "Lightpulsar: zone GY, event > 6 -> rel 4, else rel 2 + (desc[+0x12] != 0)"),
    (DF_CID, "df", ARM_DF,
     "Darkflare: a cls3 (on-field) descriptor -> rel 2 + STAGE"),
    (UGN_CID, "ugn", ARM_UGN,
     "Upstart Golden Ninja: cost running OR hand-scan probing -> rel 1 (Hand/Trap), else rel 0 (Deck)"),
    (JS_CID, "js", ARM_JS,
     "Jet Synchron: cost running -> rel 1 (any card in Hand), else rel 0 (Junk from Deck)"),
    (AS_CID, "as", ARM_AS,
     "Accel Synchron: opponent's turn -> rel 1 (clause 3), else rel 0 (clause 1 Deck)"),
    (0x126F, "assd", ARM_ASSD,
     "Accel Synchro Stardust Dragon: cls3 -> rel 1 + STAGE (C2 Stardust / C3 Synchro), else rel 0 (C1)"),
    (PSI_CID, "psi", ARM_PSI,
     "Psi-Reflector (in-game confirmed 2026-09-15): row cid 0x1008 and cls3 -> cost running ? rel 2 (AMA in "
     "hand) : rel 1 (group monster in GY); else rel 0 (C1 Deck search)"),
    (OVI_CID, "ovi", ARM_OVI,
     "Souleating Oviraptor: row cid 0x0FC6 and cls3 -> rel 1 (C2 GY Dinosaur); else rel 0 (C1 Deck)"),
    (SM_CID, "sm", ARM_SM,
     "Elemental HERO Shadow Mist: row cid 0x111F and cls2 -> rel 1 (C2 HERO); else rel 0 (C1 Mask Change)"),
)






def stub(base: int, arms: tuple = ARMS) -> bytes:
    """Build the shared stub: read the acting descriptor, then try each arm.

    Each arm's body is a callable ``body(b, tag)`` emitting into the builder (labels ``native`` / ``tail`` are
    defined at the end of the stub)."""
    b = EffectBuilder()
    b.ldr_const(3, ACTING_DESC)
    b.insn("LDR", "R3, [R3, #0x50]")
    b.insn("CMP", "R3, #0x0")
    b.insn("BEQ", "native")
    for i, (cid, tag, body, _doc) in enumerate(arms):
        nxt = f"{arms[i + 1][1]}arm" if i + 1 < len(arms) else "native"
        b.label(f"{tag}arm")
        b.insn("LDRH", "R0, [R3, #0x0]")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BNE", nxt)
        body(b, tag)
    b.label("native")
    b.ldr_const(1, LISTA_LIT)
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(3, ROWHOOK_RESUME | 1)
    b.insn("BX", "R3")
    b.label("tail")
    b.ldr_const(3, ROWHOOK_TAIL | 1)
    b.insn("BX", "R3")
    return b.assemble(base, pad="nop")


def stage_blob() -> bytes:
    """The STAGE byte's shipped value: 2 == the either-GY target row."""
    return struct.pack("<I", DF_STAGE_TARGET)


def apply(ov: bytearray, *, quiet: bool = False) -> None:
    """Install the 4-byte overlay-3 hook. Idempotent and order-independent."""
    want = _bl(ROWHOOK_SITE, ov5_cave.CAVE_ROWHOOK)
    cur = bytes(ov[_off(ROWHOOK_SITE):_off(ROWHOOK_SITE) + 4])
    if cur == want:
        if not quiet:
            print("R row-disambiguation hook: already installed (idempotent)")
        return
    assert cur == ROWHOOK_NATIVE, (
        f"R the hook site 0x{ROWHOOK_SITE:08X} is {cur.hex()}, expected the native "
        f"{ROWHOOK_NATIVE.hex()} or our BL -- another patch owns it")
    ov[_off(ROWHOOK_SITE):_off(ROWHOOK_SITE) + 4] = want
    if not quiet:
        print(f"R row-disambiguation hooked @0x{ROWHOOK_SITE:08X} -> ov5 "
              f"0x{ov5_cave.CAVE_ROWHOOK:08X} ({len(ARMS)} registered cids)")


def install(rom, *, quiet: bool = False) -> None:
    """Write the shared stub and the STAGE byte into ov5.

    Read-back-and-skip, because ov5_cave.install_cave() asserts its destination is
    all-zero and would raise on the second card patch in a chained ROM.
    """
    blob = stub(ov5_cave.CAVE_ROWHOOK)
    effect_verify.assert_thumb1_only(blob, ov5_cave.CAVE_ROWHOOK)   # ARMv5TE = Thumb-1 ONLY
    assert len(blob) <= RESERVE, f"R row hook is {len(blob)} B > the {RESERVE:#x} reserve"
    for addr, b, reserve, what in ((ov5_cave.CAVE_ROWHOOK, blob, RESERVE, "stub"),
                                   (ov5_cave.CAVE_DF_STAGE, stage_blob(), 4, "STAGE byte")):
        if ov5_cave.read_cave(rom, addr, len(b)) == b:
            if not quiet:
                print(f"R shared row-hook {what} @0x{addr:08X}: already installed (idempotent)")
            continue
        ov5_cave.install_cave(rom, addr, b, reserve=reserve)
        if not quiet:
            print(f"R shared row-hook {what} -> ov5 0x{addr:08X} ({len(b)} B)")
    if not quiet:
        for cid, _tag, _body, doc in ARMS:
            print(f"R   arm 0x{cid:04X}: {doc}")


def verify(ov: bytearray, check, *, rom=None) -> bool:
    """Assert the shared hook, using the caller's `check(cond, msg)`.

    Pass *rom* to also pin the ov5 blob -- lightpulsar's own verify() never
    loaded ov5, so for a year only the 4-byte BL was ever checked.
    """
    ok = True
    ok &= check(bytes(ov[_off(ROWHOOK_SITE):_off(ROWHOOK_SITE) + 4])
                == _bl(ROWHOOK_SITE, ov5_cave.CAVE_ROWHOOK)
                or ov5_cave.ik_tail(ov, _off(ROWHOOK_SITE), ROWHOOK_SITE) == ov5_cave.CAVE_ROWHOOK,   # via the Infernoble row fronts
                f"R the row-disambiguation hook @0x{ROWHOOK_SITE:08X} -> the SHARED stub "
                f"0x{ov5_cave.CAVE_ROWHOOK:08X}")

    def u16(ram: int) -> int:
        return struct.unpack_from("<H", ov, _off(ram))[0]

    ok &= check(u16(ROWHOOK_RESUME) == 0x223B,
                f"R the resume point 0x{ROWHOOK_RESUME:08X} is still `movs r2,#0x3b`")
    # the common tail we jump into: `ldr r2,[pc,#..] ; ...` -- pinned by its first
    # halfword so a future patch cannot move it out from under every arm.
    ok &= check(u16(ROWHOOK_TAIL) == struct.unpack_from(
                    "<H", ov, _off(ROWHOOK_TAIL))[0],
                f"R the common tail 0x{ROWHOOK_TAIL:08X} is the jump target")
    ok &= check(u16(0x02243DEA) == 0x2001 and u16(0x02243E54) == 0x1C8C,
                "R Dark Simorgh's own switch arm (the model for every arm) is unmodified")
    ok &= check(u16(0x02243BFA) == 0x2C00,
                "R the list-A `cmp r4,#0` param clamp is unmodified (clause-1 paths)")

    if rom is not None:
        blob = stub(ov5_cave.CAVE_ROWHOOK)
        ok &= check(ov5_cave.read_cave(rom, ov5_cave.CAVE_ROWHOOK, len(blob)) == blob,
                    f"R the shared stub is present in ov5 @0x{ov5_cave.CAVE_ROWHOOK:08X} "
                    f"({len(blob)} B, arms {', '.join(f'0x{c:04X}' for c, *_ in ARMS)})")
        ok &= check(ov5_cave.read_cave(rom, ov5_cave.CAVE_DF_STAGE, 4) == stage_blob(),
                    f"R the STAGE byte ships as {DF_STAGE_TARGET} "
                    f"@0x{ov5_cave.CAVE_DF_STAGE:08X}")
    return ok

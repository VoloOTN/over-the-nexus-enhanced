"""The SHARED timing-class hook: one stub, a REGISTER of cids.

WHY THIS MODULE EXISTS
======================
`timing.class_is_the_slot4_literal`: the WHEN-vs-IF classifier 0x0224AF7C reads a
cls record's +0x10 as a **RAW LITERAL** and never calls it --

    0x0224AF8E  bl 0x0224A118            find_event_handler -> r0 = the record
    0x0224AF96  ldr r0,[r0,#0x10]        the raw tag
    0x0224AF98  cmp r0,#0
    0x0224AF9A  bne ...                  +0x10 == 0        -> class 0
    0x0224AFA0  cmp r0,=0x021E51E5       the "You can" tag -> class 2
    0x0224AFAA  cmp r0,=0x021E50DD                         -> class 1
    ...         a long chain of known tags, all            -> class 1
                anything else            -> NO CLASS AT ALL, trigger dropped silently

-- so a card whose two clauses SHARE ONE cls2 record, and whose second clause
needs a real cost function at +0x10, loses its first clause's timing class. That
failure is silent: in-game the engine simply says nothing when the trigger fires
(measured for Lightpulsar 2026-08-17), or reports "missed the timing".

The fix is to displace `ldr r0,[r0,#0x10] ; cmp r0,#0` at 0x0224AF96 into a stub
that replays the load and, **for a registered cid in a registered window only**,
substitutes a value the classifier recognises, then replays the `cmp` so the
caller's own `bne` at 0x0224AF9A gets correct flags. Every other card reaches the
chain with its real tag, untouched.

*** AND THERE IS EXACTLY ONE 4-BYTE BL AT THAT SITE. ***  A stub owned by one card
module can therefore only ever serve one card.  Lightpulsar shipped one; Jet
Synchron needed a second arm; re-pointing the hook would have broken Lightpulsar's
clause 3, which is in-game confirmed.  So the hook, the stub and the cid register
live here, exactly the way criteria_row_hook.py owns the row-offset hook and
handss_banish_cost.py owns the shared payment stubs -- and for exactly the same
reason.  This module IS criteria_row_hook.py's structure, deliberately.

REGISTERED CARDS
================
    0x0FB1  Sword Arm of Dragon -> Lightpulsar Dragon   IN-GAME CONFIRMED 2026-08-17
    0x224C  Changer Synchron    -> Jet Synchron          (2026-09-03, clause 2)
    0x23EB  Ignition Beast Volcannon -> Jet Warrior
    0x126F  Meteor B. Dragon    -> Accel Synchro Stardust Dragon   IN-GAME CONFIRMED 2026-09-14

Adding a third card is one entry in ARMS.

⚠️⚠️ DUEL-ONLY.  The classifier runs for every triggered effect in the game and
this stub is in the ov5 cave, which overlay 41 evicts in a puzzle
(`mem.ov5_ov41_share_base`).  Accepted by explicit user decision 2026-08-14 for
Lightpulsar and again 2026-09-03 for Jet Synchron.

REGISTER CONTRACT AT THE HOOK SITE
==================================
r0 = the cls RECORD (find_event_handler's return), r4 = the DESCRIPTOR
(0x0224AF7E did `adds r4,r0,#0`).  r1/r2/r3 are free scratch -- the classifier
rebuilds r1 from its own literal pool on every arm of the chain.  An arm returns
with r0 = the tag the classifier should see; the shared tail replays `cmp r0,#0`
and `bx lr`.

DESCRIPTOR FIELDS AN ARM MAY KEY ON (dispatch.cls_table_selector):
    desc[+0x00] u16  cid
    desc[+0x03] u8   zone        0x0E = sent TO THE GRAVEYARD (the DESTINATION)
    desc[+0x04] u8   event code  0x17 battle-destroyed / 0x1D non-battle leave /
                                 0x1E relocation; a GY-ACTION descriptor is capped
                                 at <= 6 by the off-field gate 0x021ECC28
                                 (dispatch.gy_action_offer_caps_the_event_code)
    desc[+0x05] u8   record class -- never 0 or 3 here, the classifier returns at
                                 0x0224AF8A for those before reaching this site
"""
from __future__ import annotations

import re
import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import ov3_off as _off
from otn_enhanced.effects.common import bl as _bl

# --- the hook site, inside the WHEN-vs-IF classifier 0x0224AF7C -------------
TIMING_SITE = 0x0224AF96        # `ldr r0,[r0,#0x10] ; cmp r0,#0`   (4 B)
TIMING_NATIVE = bytes.fromhex("00690028")
TIMING_CLASSIFIER = 0x0224AF7C
TAG_YOU_CAN = 0x021E51E5        # the costless optional "You can" tag -> class 2
TAG_CLASS0 = 0x00000000         # +0x10 == 0                          -> class 0

RESERVE = 0x200                 # was 0x100 at CAVE_TIMINGHOOK_OLD until (full)

# The window both arms use: the descriptor's zone is the DESTINATION zone, so
# 0x0E means "sent TO THE GRAVEYARD", and `event > 6` separates every leave /
# relocation code (0x17 / 0x1D / 0x1E) from every activation code.  The upper
# bound is not an assumption: dispatch.gy_action_offer_caps_the_event_code proves
# the off-field gate 0x021ECC28 refuses any GY-action descriptor above 6, so a
# stale event code cannot leak a GY ignition into this window.
ZONE_GY = 0x0E
EVENT_MIN = 7

# --- Lightpulsar Dragon 0x0FB1 ---------------------------------------------
# Moved here VERBATIM from lightpulsar._stub_timing; the body
# is byte-identical, only its host changed.  Clause 2 needs a real cost function
# at +0x10 (CAVE_LP_C2COST), so without this the card lands in no class at all.
#
# ⚠️ WHAT THIS ACTUALLY DOES IS MEASURED, NOT INFERRED (in-game):
# WITHOUT the hook the game says NOTHING when Lightpulsar is used as Synchro
# Material; WITH it the game correctly reports "missed the timing".  So class 0
# does NOT mean "cannot miss the timing" -- it means the effect is a PROPERLY
# CLASSIFIED trigger, after which the engine applies the miss-timing rule to it.
LP_CID = 0x0FB1
ARM_LP = f"""
        ldrb    r1, [r4, #0x3]
        cmp     r1, #{ZONE_GY:#x}
        bne     out
        ldrb    r1, [r4, #0x4]
        cmp     r1, #{EVENT_MIN - 1:#x}
        ble     out
        movs    r0, #0x0
        b       out
"""

# --- Jet Synchron 0x224C ----------------------------------------------------
# Clause 1 ("if this card is sent to the GY as Synchro Material: you can add 1
# 'Junk' monster from your Deck to your hand") SHIPPED with +0x10 == 0x021E51E5
# and is.  Clause 2 is a GY ignition
# with a hand-send COST, which must occupy the same +0x10, so the arm restores
# exactly the literal clause 1 was confirmed with -- the minimum change from a
# known-good state, and a different substitution from Lightpulsar's on purpose.
#
# The window is the same one clause 1's slot dispatchers use, so the timing class
# and the action can never disagree about which clause is running.
JET_CID = 0x224C
ARM_JET = f"""
        ldrb    r1, [r4, #0x3]
        cmp     r1, #{ZONE_GY:#x}
        bne     out
        ldrb    r1, [r4, #0x4]
        cmp     r1, #{EVENT_MIN - 1:#x}
        ble     out
        ldr     r0, ={TAG_YOU_CAN:#x}
        b       out
"""

# --- Jet Warrior 0x23EB -----------------------------------------------------
# Jet Warrior's two clauses live in DIFFERENT records -- clause 1 in cls1[1279]
# @0x0228D8BC, clause 2 in cls2[643] @0x0227984C -- and BOTH carry a cave pointer
# in +0x10 (0x0239E981 and 0x0239EA21 respectively; each wraps its own activation
# procedure so clause 3 can stamp the turn log at ACTIVATION rather than in the
# resolver, per dispatch.once_per_turn_must_stamp_at_activation).  So both need a
# substituted tag or they land in no class at all.
#
# ⚠️⚠️ THIS ARM WAS UNCONDITIONAL UNTIL AND THAT WAS THE BUG.
# Its old comment claimed "one unconditional arm is correct for every descriptor
# that reaches here with this cid".  It is not.  The GY-ACTION OFFER descriptor
# also reaches here with this cid, and the offer path at 0x021EDC72 is the ONE
# call site of the five that tests `== 2` specifically:
#
#     0x021EDC72  bl 0x0224AF7C
#     0x021EDC76  cmp r0,#2 ; beq 0x021EDC84 -> movs r0,#1 = OFFER, unconditional
#     0x021EDC88  ...else bl 0x0224AD94, which is what runs +0C and +08
#
# Tagging the offer descriptor class 2 therefore SHORT-CIRCUITS the card's own
# condition slot: clause 2 was offered, and resolved for free, on a board with no
# legal Tribute.  Measured and A/B-confirmed over the user's savestates
# (scratch/jw_offer_trace.py, scratch/jw_offer_ab.py): with the arm
# firing the offer path returns 1 and never reaches +0C; with it suppressed the
# same board returns 0 via blx +0C.  See notes/jet-warrior-findings.md C21/C22.
#
# THE DISCRIMINATOR IS CLOSED, NOT CHOSEN.  0x0224AF7C reads +0x10 out of the
# record that find_event_handler 0x0224A118 returns, and find_event_handler picks
# WHICH TABLE to search from desc[+5] (jump table @0x0224A134: class 1 -> cls1
# base 0x022860D4, class 2 -> cls2 base 0x02275C04).  So the classifier is
# looking at clause 1's cls1 record if and only if desc[+5] == 1, and at
# clause 2's cls2 record if and only if desc[+5] == 2.  Gating on desc[+5] == 1
# hands the tag to exactly the descriptor whose record needs it.
#
# Falling through leaves clause 2 at class 0 -- which is what Blackwing -
# Zephyros 0x241C and Grapha have (their cls2 +0x10 is 0x021EB1B1, equally absent
# from the classifier's literal chain), and Grapha's GY offer is in-game
# confirmed by the user to be correctly withheld when its cost cannot
# be paid.  Class 0 is the CORRECT class for a GY ignition here.
JW_CID = 0x23EB
JW_CLS1_CLASS = 1               # desc[+5] for clause 1's cls1 record
ARM_JW = f"""
        ldrb    r1, [r4, #0x5]
        cmp     r1, #{JW_CLS1_CLASS:#x}
        bne     out
        ldr     r0, ={TAG_YOU_CAN:#x}
        b       out
"""

# --- Elemental HERO Shadow Mist 0x111F (Ryu-Kishin Powered) ------------------
# BOTH records carry the cave CAVE_SM_SLOT4 in +0x10 (the shared once-per-turn stamp): cls1 = C1
# "If this card is Special Summoned: You can", cls2 = C2 "If this card is sent to the GY: You can".
# Each replaced a native 0x021E51E5 (Gearframe / Cross Porter 0x1D97), so both get class 2 back.
# Shadow Mist has NO GY ignition, so Jet Warrior's GY-offer short-circuit cannot arise here.
SM_CID = 0x111F
ARM_SM = f"""
        ldrb    r1, [r4, #0x5]
        cmp     r1, #0x1
        beq     smtag
        cmp     r1, #0x2
        bne     out
      smtag:
        ldr     r0, ={TAG_YOU_CAN:#x}
        b       out
"""

# --- Overtex Qoatlus 0x10A5 (Prevent Rat): the cls2 record (C3) only -> class 2 ---------------------
ARM_OQ = f"""
        ldrb    r1, [r4, #0x5]
        cmp     r1, #0x2
        bne     out
        ldr     r0, ={TAG_YOU_CAN:#x}
        b       out
"""


# Infernoble family arms (infernoble). PREPENDED to ARMS: every arm's `bne out` targets the stub's far end,
# so APPENDING one pushes an early arm (ARM_JW) past Thumb-1's +-256 B conditional range; a prepended arm uses an
# unconditional `b out` (+-2 KB) for its own exit and leaves every existing distance unchanged.
ARM_IKM = f"""
        ldrb    r1, [r4, #0x3]
        cmp     r1, #0xe
        bne     ikmskip
        ldrb    r1, [r4, #0x4]
        cmp     r1, #6
        ble     ikmskip
        ldr     r0, ={TAG_YOU_CAN:#x}
      ikmskip:
        b       out
"""
ARM_RO = f"""
        ldrb    r1, [r4, #0x3]
        cmp     r1, #0xe
        bne     roskip
        ldr     r0, ={TAG_YOU_CAN:#x}
      roskip:
        b       out
"""
ARM_BR = ARM_RO.replace("roskip", "brskip")
# Disguise, the Copycat Hero 0x111E (Monster Tamer), C2 "If this card is Normal or Special Summoned: You can add ..."
# -- cls1 +10 is CAVE_DC_C2_SLOT4 wrapping 0x021E51E5 (Psi-Reflector's shape), so class 2 for desc[+5] == 1. PREPENDED,
# so its own exit is an unconditional `b out`.
ARM_DC = f"""
        ldrb    r1, [r4, #0x5]
        cmp     r1, #0x1
        bne     dcskip
        ldr     r0, ={TAG_YOU_CAN:#x}
      dcskip:
        b       out
"""

# (cid, label tag, arm source, one-line description)
ARMS: tuple[tuple[int, str, str, str], ...] = (
    (0x111E, "dc", ARM_DC,
     f"Disguise, the Copycat Hero: desc[+5] == 1 (C2's cls1 record) -> tag 0x{TAG_YOU_CAN:08X} (class 2); PREPENDED"),
    (0x160B, "ikbr", ARM_BR,
     f"Bradamante: zone GY (C2 list106 battle trigger) -> tag 0x{TAG_YOU_CAN:08X} (class 2); PREPENDED"),
    (0x0FDB, "ikro", ARM_RO,
     f"Infernoble Knight - Roland: zone GY (C2 End-Phase search, event 6) -> tag 0x{TAG_YOU_CAN:08X} (class 2); "
     f"the hand C1 keeps its class -- PREPENDED like Maugis"),
    (0x139A, "ikm", ARM_IKM,
     f"Infernoble Knight Maugis: zone GY, event > 6 (C2 sent-to-GY) -> tag 0x{TAG_YOU_CAN:08X} (class 2); "
     f"its C3 GY offer keeps class 0"),
    (LP_CID, "lp", ARM_LP,
     "Lightpulsar: zone GY, event > 6 -> tag 0 (class 0, a real WHEN trigger)"),
    (JET_CID, "jet", ARM_JET,
     f"Jet Synchron: zone GY, event > 6 -> tag 0x{TAG_YOU_CAN:08X} (class 2, 'You can')"),
    (JW_CID, "jw", ARM_JW,
     f"Jet Warrior: desc[+5] == {JW_CLS1_CLASS} (clause 1's cls1 record) -> tag "
     f"0x{TAG_YOU_CAN:08X} (class 2); every other class falls through to the raw "
     f"+10, so the clause-2 GY offer keeps class 0 and its +0C is consulted"),
    # Accel Synchro Stardust Dragon 0x126F (Meteor B. Dragon), C1 "If this card is Synchro
    # Summoned: You can ..." -- the SAME shape as Jet Warrior clause 1 (cls1 +10 = a cave
    # stamp wrapping the "You can" body), so ARM_JW verbatim.  Its C2/C3 record is cls3, which
    # the classifier returns on before this site.  In-game confirmed by user.
    (0x126F, "assd", ARM_JW,
     f"Accel Synchro Stardust Dragon: desc[+5] == 1 (C1's cls1 record) -> tag "
     f"0x{TAG_YOU_CAN:08X} (class 2)"),
    # Psi-Reflector 0x1008 (Clown Zombie), C1 "If this card is Normal or Special Summoned: You can
    # add ..." -- cls1 +10 is CAVE_PSI_SLOT4 wrapping the "You can" tag 0x021E51E5 it replaced, so
    # ARM_JW restores exactly the class the stock Gearframe record had.  In-game confirmed by user.
    (0x1008, "psi", ARM_JW,
     f"Psi-Reflector: desc[+5] == 1 (C1's cls1 record) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Souleating Oviraptor 0x0FC6 (Two-Headed King Rex), C1 -- Psi-Reflector's C1 shape exactly.
    # In-game confirmed by user (Psi-Reflector re-tested in the same ROM: no regression).
    (0x0FC6, "ovi", ARM_JW,
     f"Souleating Oviraptor: desc[+5] == 1 (C1's cls1 record) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    (SM_CID, "sm", ARM_SM,
     f"Elemental HERO Shadow Mist: desc[+5] == 1 or 2 (C1 cls1 / C2 cls2) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Masked HERO Dark Law 0x1160 (Aqua Dragon), C3 -- cls1 +10 is CAVE_DL_SLOT4 wrapping 0x021E51E5 +
    # the per-copy 0x0FB6 stamp: Psi-Reflector's shape, ARM_JW.  In-game confirmed by user.
    (0x1160, "dl", ARM_JW,
     f"Masked HERO Dark Law: desc[+5] == 1 (C3's cls1 record) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Animadorned Archosaur 0x1297 (Swordsman of Landstar) -- cls1 +10 is CAVE_ARCH_SLOT4 wrapping
    # 0x021E51E5: Oviraptor C1's shape, ARM_JW.  In-game confirmed by user.
    (0x1297, "arch", ARM_JW,
     f"Animadorned Archosaur: desc[+5] == 1 (cls1) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Overtex Qoatlus 0x10A5 (Prevent Rat) C3 -- cls2 +10 is CAVE_OQ_C3SLOT4 wrapping 0x021E51E5 ("You can" on
    # the sent-to-GY-by-effect trigger).  Its C2 record is cls3 (returns before this site).  In-game confirmed
    # by user.
    (0x10A5, "oq", ARM_OQ,
     f"Overtex Qoatlus: desc[+5] == 2 (C3 cls2) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Grandsoil the Elemental Lord 0x1110 (Millennium Shield), C3 -- cls1 +10 is CAVE_GS_SLOT4 wrapping 0x021E51E5:
    # Oviraptor C1's shape, ARM_JW. The 11th arm overflowed the 0x100 home -> re-homed (0x200).
    # In-game confirmed by user.
    (0x1110, "gs", ARM_JW,
     f"Grandsoil: desc[+5] == 1 (C3 cls1) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Pyrorex the Elemental Lord 0x181F (Harpie Girl), C3 -- cls1 +10 is CAVE_PX_SLOT4 (Grandsoil's slot4 shape),
    # ARM_JW (292 / 0x200 B). Execution proof scratch/pyrorex_equiv.py (only 0x181F changes, == 0x1110).
    # In-game confirmed by user.
    (0x181F, "px", ARM_JW,
     f"Pyrorex: desc[+5] == 1 (C3 cls1) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    # Neo Space Connector 0x1106 (Kanan the Swordmistress), C1 -- cls1 +10 is CAVE_NSC_SLOT4 wrapping 0x021E51E5:
    # Oviraptor C1's shape, ARM_JW (312 / 0x200 B). Execution proof scratch/nsc_equiv.py (only 0x1106 changes,
    # == 0x0FC6). Whole card.
    (0x1106, "nsc", ARM_JW,
     f"Neo Space Connector: desc[+5] == 1 (C1 cls1) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
    (0x13A3, "ik", ARM_JW,
     f"Infernoble Knight Ogier: desc[+5] == 1 (C2 cls1) -> tag 0x{TAG_YOU_CAN:08X} (class 2)"),
)






def _emit_arm(b: EffectBuilder, text: str) -> None:
    """Feed one arm body (the ARM_* text constants, a public interface) into the builder."""
    for line in text.splitlines():
        line = line.strip()
        while ":" in line:                       # `name:` alone or leading a line
            name, line = line.split(":", 1)
            b.label(name.strip())
            line = line.strip()
        if not line:
            continue
        mn, _, ops = line.partition(" ")
        ops = re.sub(r"\br(\d)\b", r"R\1", ops.strip())
        if mn == "ldr" and "=" in ops:
            rd, _, val = ops.partition("=")
            b.ldr_const(int(rd.strip().rstrip(",").strip()[1:]), int(val.strip(), 0))
        else:
            b.insn({"movs": "MOV", "adds": "ADD", "subs": "SUB"}.get(mn, mn.upper()), ops)


def stub(base: int, arms: tuple = ARMS) -> bytes:
    """Build the shared stub: replay the load, then try each arm by cid."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [R0, #0x10]")
    for i, (cid, tag, body, _doc) in enumerate(arms):
        nxt = f"{arms[i + 1][1]}arm" if i + 1 < len(arms) else "out"
        b.label(f"{tag}arm")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.ldr_const(2, cid)
        b.insn("CMP", "R1, R2")
        b.insn("BNE", nxt)
        _emit_arm(b, body)
    b.label("out")
    b.insn("CMP", "R0, #0x0")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def apply(ov: bytearray, *, quiet: bool = False) -> None:
    """Install the 4-byte overlay-3 hook. Idempotent and order-independent."""
    want = _bl(TIMING_SITE, ov5_cave.CAVE_TIMINGHOOK)
    cur = bytes(ov[_off(TIMING_SITE):_off(TIMING_SITE) + 4])
    if cur == want:
        if not quiet:
            print("T timing-class hook: already installed (idempotent)")
        return
    assert cur == TIMING_NATIVE, (
        f"T the classifier site 0x{TIMING_SITE:08X} is {cur.hex()}, expected the native "
        f"`ldr r0,[r0,#0x10] ; cmp r0,#0` ({TIMING_NATIVE.hex()}) or our BL -- "
        f"another patch owns it")
    ov[_off(TIMING_SITE):_off(TIMING_SITE) + 4] = want
    if not quiet:
        print(f"T timing class hooked @0x{TIMING_SITE:08X} -> ov5 "
              f"0x{ov5_cave.CAVE_TIMINGHOOK:08X} ({len(ARMS)} registered cids)")


def install(rom, *, quiet: bool = False) -> None:
    """Write the shared stub into ov5.

    Read-back-and-skip, because ov5_cave.install_cave() asserts its destination is
    all-zero and would raise on the second card patch in a chained ROM.
    """
    blob = stub(ov5_cave.CAVE_TIMINGHOOK)
    effect_verify.assert_thumb1_only(blob, ov5_cave.CAVE_TIMINGHOOK)  # ARMv5TE = Thumb-1 ONLY
    assert len(blob) <= RESERVE, f"T timing hook is {len(blob)} B > the {RESERVE:#x} reserve"
    if ov5_cave.read_cave(rom, ov5_cave.CAVE_TIMINGHOOK, len(blob)) == blob:
        if not quiet:
            print(f"T shared timing stub @0x{ov5_cave.CAVE_TIMINGHOOK:08X}: "
                  f"already installed (idempotent)")
        return
    ov5_cave.install_cave(rom, ov5_cave.CAVE_TIMINGHOOK, blob, reserve=RESERVE)
    if not quiet:
        print(f"T shared timing stub -> ov5 0x{ov5_cave.CAVE_TIMINGHOOK:08X} ({len(blob)} B)")
        for cid, _tag, _body, doc in ARMS:
            print(f"T   arm 0x{cid:04X}: {doc}")


def verify(ov: bytearray, check, *, rom=None) -> bool:
    """Assert the shared hook, using the caller's `check(cond, msg)`.

    Pass *rom* to also pin the ov5 blob, not merely the 4-byte BL.
    """
    ok = True
    ok &= check(bytes(ov[_off(TIMING_SITE):_off(TIMING_SITE) + 4])
                == _bl(TIMING_SITE, ov5_cave.CAVE_TIMINGHOOK),
                f"T the classifier's +10 read @0x{TIMING_SITE:08X} -> the SHARED stub "
                f"0x{ov5_cave.CAVE_TIMINGHOOK:08X}")

    def u16(ram: int) -> int:
        return struct.unpack_from("<H", ov, _off(ram))[0]

    def u32(ram: int) -> int:
        return struct.unpack_from("<I", ov, _off(ram))[0]

    ok &= check(u16(TIMING_CLASSIFIER) == 0xB510,
                f"T the classifier 0x{TIMING_CLASSIFIER:08X} is unmoved")
    # the `bne` our replayed `cmp` feeds, and the class-2 comparand the Jet arm
    # substitutes -- if either moves, an arm silently produces the wrong class.
    ok &= check(u16(TIMING_SITE + 4) == 0xD101,
                f"T the classifier's own `bne` @0x{TIMING_SITE + 4:08X} is unmodified")
    ok &= check(u32(0x0224B02C) == TAG_YOU_CAN,
                f"T the class-2 comparand is still 0x{TAG_YOU_CAN:08X}")

    if rom is not None:
        blob = stub(ov5_cave.CAVE_TIMINGHOOK)
        ok &= check(ov5_cave.read_cave(rom, ov5_cave.CAVE_TIMINGHOOK, len(blob)) == blob,
                    f"T the shared stub is present in ov5 @0x{ov5_cave.CAVE_TIMINGHOOK:08X} "
                    f"({len(blob)} B, arms {', '.join(f'0x{c:04X}' for c, *_ in ARMS)})")
    return ok

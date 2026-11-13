"""The SHARED summon-rider hook: one stub, a REGISTER of cids.

WHY THIS MODULE EXISTS
======================
`rider.banish_marker_attach_site`: "but banish it when it leaves the field" is a
family-1 attached node `{key 0x1E15, kind 3, param 0}`, and
`rider.banish_marker_is_cid_blind_to_the_destination` proves the node ALONE is
sufficient for any cid -- the predicate 0x021B0950 tests the four marker keys
with no cid in scope, and its caller 0x021CCBDA rewrites the destination zone
0x0E (graveyard) to 0x0F (banished).

But the ENGINE's attach is cid-keyed: the summon-event handler 0x02267A6C
dispatches opcode 0x14 through a per-cid switch rooted at 0x022680A8 whose input
is `ldrh r2,[r4,#0x12]`, and only Plaguespreader Zombie 0x1EA9 and Quillbolt
Hedgehog 0x1E15 reach the granting arm 0x02268542.  Every donor we care about
falls through to the DEFAULT leaf:

    0x02268660  movs r3,#3
    0x02268662  bl   0x021C479C        ; the shared attach
    0x02268666  ldrh r0,[r4,#0xe]      ; <- THE DEFAULT LEAF, our hook site
    0x02268668  ldr  r6,[pc,#0x54]     ;    (literal 0x000014FC)
    0x0226866A  cmp  r0,r6             ; <- consumes both displaced instructions

*** AND THERE IS EXACTLY ONE 4-BYTE BL AT THAT SITE. ***  A stub owned by one card
module can therefore only ever serve one card.  jet_synchron shipped one
(CAVE_JS_RIDER) and is in-game confirmed; Jet Warrior needed a second arm, and
re-pointing the hook would have broken it.  So the hook, the stub and the cid
register live here, exactly the way timing_class_hook.py owns the timing-class
hook and criteria_row_hook.py owns the row-offset hook -- and for the same
reason.  This module IS timing_class_hook.py's structure, deliberately.

REGISTERED CARDS
================
    0x224C  Changer Synchron -> Jet Synchron   IN-GAME CONFIRMED 2026-09-03
    0x23EB  Ignition Beast Volcannon -> Jet Warrior   (2026-09-07, clause 2)

Adding a third card is one entry in ARMS -- and that card must first be shown to
reach the DEFAULT leaf, with `scratch/summon_event_sim.py`.  A cid with its own
dedicated arm never arrives here at all.

⚠️ EVERY ARM NEEDS A ONE-SHOT BYTE.  Event opcode 0x14 is a general "a card
arrived on the field" event -- five sites post it (0x02261542, 0x022618E6,
0x02265078, 0x02265602, 0x022656A4) -- and the engine's own arm 0x02268542 has no
gate, so it grants Plaguespreader the rider on ANY summon, a Normal Summon
included.  A printed rider that belongs to ONE of a card's summons must therefore
be gated on a byte that only THAT clause sets.  ⚠️ The byte is cleared HERE, by
the consumer, and never by the setter: the commit 0x0226925C can finish after the
setting resolver has returned, which is the timing window that killed
card.upstart_golden_ninja's first STAGE latch.

⚠️⚠️ DUEL-ONLY.  The summon-event handler runs for every summon in the game and
this stub is in the ov5 cave, which overlay 41 evicts in a puzzle
(`mem.ov5_ov41_share_base`).  Accepted by explicit user decision 2026-09-03 for
Jet Synchron and again 2026-09-07 for Jet Warrior.

REGISTER RULES AT THIS SITE, read off the following code
========================================================
r4 is the handler's GLOBAL event record 0x02298A28 and MUST survive.  r0 and r6
are both redefined by the two displaced instructions, so they are free -- and r6
must therefore NOT appear in the POP list, or the pop would undo the replayed
literal.  r5 and r7 may be live and are saved.  `pop {..., pc}` is the
Thumb-1-legal return (thumb-pop-into-lr-footgun); the `blx` clobbering lr is safe
because lr is already on the stack.  The `push {r3}` is how the 5th argument
reaches 0x021C479C, which reads it at [sp+8] behind its own `push {r4, lr}`.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import ov3_off as _off
from otn_enhanced.effects.common import bl as _bl

# --- the hook site, the DEFAULT leaf of the summon-event per-cid switch -----
RIDER_SITE = 0x02268666          # `ldrh r0,[r4,#0xe] ; ldr r6,[pc,#0x54]`  (4 B)
RIDER_NATIVE = bytes.fromhex("e089154e")
RIDER_RESUME = 0x0226866A        # the `cmp r0,r6` that consumes the replayed pair
RIDER_R6_LITERAL = 0x000014FC    # what the displaced `ldr r6,[pc,#0x54]` loads

# --- the node -------------------------------------------------------------
RIDER_ATTACH = 0x021C479D        # (side, slot, key, kind, [sp] = param)
RIDER_KEY = 0x1E15               # ⚠️ a MARKER CONSTANT, not a reference to Quillbolt
RIDER_KIND = 3                   # family 1: the walker 0x021A1430 compares node@+0
                                 #   against the key directly, and rider.turn_sweeper's
                                 #   kind-3 arm frees only 0x18D9 / 0x1F6A, so it survives

# --- the global event record ----------------------------------------------
RIDER_EVENT = 0x02298A28
RIDER_EVENT_SIDE_OFF = 0x02
RIDER_EVENT_SLOT_OFF = 0x04
RIDER_EVENT_CID_OFF = 0x12

RESERVE = 0x80

# (cid, label tag, one-shot arm byte, one-line description)
ARMS: tuple[tuple[int, str, int, str], ...] = (
    (0x224C, "js", ov5_cave.CAVE_JS_ARM,
     "Jet Synchron: clause 2's resolver arm sets the byte before tail-jumping "
     "into the GY self-Special-Summon"),
    (0x23EB, "jw", ov5_cave.CAVE_JW_ARM,
     "Jet Warrior: clause 2's Defense-Position stub CAVE_JW_C2_POS sets the byte "
     "at the SS commit -- cid-scoped AND inside the GY self-SS resolver, so a "
     "Synchro Summon of Jet Warrior can never arm it"),
    (0x106E, "dr", ov5_cave.CAVE_DR_ARM,
     "Dragunity Remus: C3a's GY self-Summon resolver sets the byte at phase 0x80, "
     "inside the desc[+3] == 0x0E branch -- so ONLY the Graveyard revive riders. A "
     "Normal Summoned Remus, or one Special Summoned any other way, correctly still "
     "goes to the Graveyard. Reaching the DEFAULT leaf was MEASURED 2026-09-21 with "
     "scratch/summon_event_sim: 0x106E -> 0x02268666, with Plaguespreader 0x1EA9 -> "
     "0x02268546 (dedicated arm) and Changer Synchron 0x224C -> 0x02268666 as the "
     "two controls that prove the walk separates"),
    (0x0FC1, "tp", ov5_cave.CAVE_IK_T_ARM,
     "Infernoble Knight Turpin: C2's GY self-SS resolver sets the byte at phase 0x80 (0x0FC1 reaches "
     "the default leaf, scratch/summon_event_sim walk 2026-10-20)"),
)


# LATCH ARMS -- cid-BLIND riders, served by a PREFIX stub in front of the shared one.
# A card whose rider lands on a monster it SUMMONS (not on itself) cannot key on the
# arriving cid, so it sets a one-shot byte and the prefix fires on "byte set AND the
# event's SOURCE cid [r4+0x12] == its own cid", attaching ITS OWN key.  ⚠️ [r4+0x12] is
# the SUMMONING EFFECT's cid and [r4+0xE] the summoned card's (savestate
# rom_brilliant_fusion.ml5, KB summon.event_record_0x12_is_the_source_cid) -- the ARMS
# above key on +0x12 too, which is correct only because those cards summon THEMSELVES.
# The shared stub has no room (104 of 0x80 B, CAVE_JW_ARM directly behind it), so the
# prefix lives in CAVE_RIDERLATCH and the hook BL points there ONLY when latch arms
# are registered; the prefix tail-jumps to CAVE_RIDERHOOK with lr intact.  With no
# latch arms, every byte this module writes is exactly what it wrote before.
# (tag, one-shot arm byte, node key, source cid, one-line description)
# Used by Brilliant Fusion.
# This is the single source of truth: every owner (Jet Synchron, Jet Warrior, Remus, Brilliant Fusion) calls
# install/apply/verify with this default, so the hook points at CAVE_RIDERLATCH whatever the build order.
LATCH_ARMS: tuple[tuple[str, int, int, int, str], ...] = (
    ("bf", ov5_cave.CAVE_BF_ARM, 0x1F64, 0x21D5,
     "Brilliant Fusion: CAVE_BF_DECKGY sets the byte while moving Deck materials "
     "(phase 0x63, strictly before the commit in phase 0x32); the event's SOURCE cid "
     "[ev+0x12] is 0x21D5 (build 1 wrongly compared it with the Fusion target); "
     "key 0x1F64 = ATK/DEF 0"),
)
LATCH_RESERVE = 0x50






def _attach(b: EffectBuilder, key: int) -> None:
    """Push the 5th arg (param 0), call the shared attach {side, slot, key, kind 3}."""
    b.insn("MOV", "R3, #0x0")
    b.insn("PUSH", "{R3}")
    b.insn("LDRH", f"R0, [R4, #{RIDER_EVENT_SIDE_OFF:#x}]")
    b.insn("LDRH", f"R1, [R4, #{RIDER_EVENT_SLOT_OFF:#x}]")
    b.ldr_const(2, key)
    b.insn("MOV", f"R3, #{RIDER_KIND:#x}")
    b.ldr_const(7, RIDER_ATTACH)
    b.insn("BLX", "R7")
    b.insn("POP", "{R3}")


def _replay(b: EffectBuilder) -> None:
    """The two displaced instructions, then the Thumb-1-legal return."""
    b.insn("LDRH", "R0, [R4, #0xe]")
    b.ldr_const(6, RIDER_R6_LITERAL)
    b.insn("POP", "{R4, R5, R7, PC}")


def stub(base: int, arms: tuple = ARMS) -> bytes:
    """Build the shared stub: pick this cid's one-shot byte, consume it, attach.

    Each arm compares the event record's cid and, on a match, loads ITS OWN
    one-shot byte address into r0 and falls into the shared consume-and-attach
    tail.  A cid matching no arm branches straight to the replay, which is the
    native behaviour for every other card in the game.
    """
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R7, LR}")
    b.insn("LDRH", f"R1, [R4, #{RIDER_EVENT_CID_OFF:#x}]")
    for i, (cid, tag, armbyte, _doc) in enumerate(arms):
        nxt = f"{arms[i + 1][1]}arm" if i + 1 < len(arms) else "replay"
        b.label(f"{tag}arm")
        b.ldr_const(5, cid)
        b.insn("CMP", "R1, R5")
        b.insn("BNE", nxt)
        b.ldr_const(0, armbyte)
        b.insn("B", "consume")
    b.label("consume")
    b.insn("LDRB", "R1, [R0, #0x0]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BEQ", "replay")
    b.insn("MOV", "R1, #0x0")
    b.insn("STRB", "R1, [R0, #0x0]")
    _attach(b, RIDER_KEY)
    b.label("replay")
    _replay(b)
    return b.assemble(base, pad="nop")


def latch_stub(base: int, latch_arms: tuple = LATCH_ARMS) -> bytes:
    """The cid-blind PREFIX: per latch arm, "byte set AND the event's source cid [r4+0x12]
    == the arm's cid" -> consume, attach {key, kind 3}, replay, return; else tail-jump
    to the shared stub.  Entered by the hook BL, so lr = RIDER_RESUME|1 and r4 = the
    event record.  The miss path touches only r0-r2 (r0/r6 are redefined by the replay,
    r1 is clobbered by the shared stub anyway, r2 only after a byte was found set --
    the same r0-r3 the native attach path at 0x02268662 clobbers).  A cid MISMATCH
    leaves the byte set: the setter's own card clears it at its next activation."""
    b = EffectBuilder()
    for i, (tag, armbyte, key, cid, _doc) in enumerate(latch_arms):
        nxt = f"{latch_arms[i + 1][0]}latch" if i + 1 < len(latch_arms) else "shared"
        b.label(f"{tag}latch")
        b.ldr_const(0, armbyte)
        b.insn("LDRB", "R1, [R0, #0x0]")
        b.insn("CMP", "R1, #0x0")
        b.insn("BEQ", nxt)
        b.insn("LDRH", f"R1, [R4, #{RIDER_EVENT_CID_OFF:#x}]")
        b.ldr_const(2, cid)
        b.insn("CMP", "R1, R2")
        b.insn("BNE", nxt)
        b.insn("MOV", "R1, #0x0")
        b.insn("STRB", "R1, [R0, #0x0]")
        b.insn("PUSH", "{R4, R5, R7, LR}")
        _attach(b, key)
        _replay(b)
    b.label("shared")
    b.ldr_const(0, ov5_cave.CAVE_RIDERHOOK | 1)
    b.insn("BX", "R0")
    return b.assemble(base, pad="nop")


def _hook_target(latch_arms: tuple) -> int:
    return ov5_cave.CAVE_RIDERLATCH if latch_arms else ov5_cave.CAVE_RIDERHOOK


def apply(ov: bytearray, *, quiet: bool = False, latch_arms: tuple = LATCH_ARMS) -> None:
    """Install the 4-byte overlay-3 hook. Idempotent and order-independent."""
    want = _bl(RIDER_SITE, _hook_target(latch_arms))
    cur = bytes(ov[_off(RIDER_SITE):_off(RIDER_SITE) + 4])
    if cur == want:
        if not quiet:
            print("R summon-rider hook: already installed (idempotent)")
        return
    ours = {_bl(RIDER_SITE, ov5_cave.CAVE_RIDERHOOK), _bl(RIDER_SITE, ov5_cave.CAVE_RIDERLATCH)}
    assert cur == RIDER_NATIVE or cur in ours, (
        f"R the summon-event default leaf 0x{RIDER_SITE:08X} is {cur.hex()}, expected the "
        f"native `ldrh r0,[r4,#0xe] ; ldr r6,[pc,#0x54]` ({RIDER_NATIVE.hex()}) or our BL "
        f"-- another patch owns it")
    ov[_off(RIDER_SITE):_off(RIDER_SITE) + 4] = want
    if not quiet:
        print(f"R summon rider hooked @0x{RIDER_SITE:08X} -> ov5 "
              f"0x{_hook_target(latch_arms):08X} ({len(ARMS)} registered cids, "
              f"{len(latch_arms)} latch arms)")


def install(rom, *, quiet: bool = False, latch_arms: tuple = LATCH_ARMS) -> None:
    """Write the shared stub into the ov5 cave, and every arm's one-shot byte."""
    blob = stub(ov5_cave.CAVE_RIDERHOOK)
    assert len(blob) <= RESERVE, (
        f"R the shared rider stub is {len(blob)} B, over its 0x{RESERVE:X} reserve")
    effect_verify.assert_thumb1_only(blob, ov5_cave.CAVE_RIDERHOOK)
    if ov5_cave.read_cave(rom, ov5_cave.CAVE_RIDERHOOK, len(blob)) != blob:
        ov5_cave.install_cave(rom, ov5_cave.CAVE_RIDERHOOK, blob, reserve=RESERVE)
        if not quiet:
            print(f"R shared rider stub -> ov5 0x{ov5_cave.CAVE_RIDERHOOK:08X} "
                  f"({len(blob)} B, arms {', '.join(f'0x{c:04X}' for c, *_ in ARMS)})")
    elif not quiet:
        print(f"R shared rider stub @0x{ov5_cave.CAVE_RIDERHOOK:08X}: unchanged (idempotent)")

    # every arm's one-shot byte ships CLEAR -- a stale 1 would rider the next summon
    clear = struct.pack("<I", 0)
    for cid, tag, armbyte, _doc in ARMS:
        if ov5_cave.read_cave(rom, armbyte, 4) != clear:
            ov5_cave.install_cave(rom, armbyte, clear, reserve=4)
            if not quiet:
                print(f"R  one-shot byte for 0x{cid:04X} -> ov5 0x{armbyte:08X} (4 B, clear)")

    if not latch_arms:
        return
    pre = latch_stub(ov5_cave.CAVE_RIDERLATCH, latch_arms)
    assert len(pre) <= LATCH_RESERVE, (
        f"R the latch prefix is {len(pre)} B, over its 0x{LATCH_RESERVE:X} reserve")
    effect_verify.assert_thumb1_only(pre, ov5_cave.CAVE_RIDERLATCH)
    if ov5_cave.read_cave(rom, ov5_cave.CAVE_RIDERLATCH, len(pre)) != pre:
        ov5_cave.install_cave(rom, ov5_cave.CAVE_RIDERLATCH, pre, reserve=LATCH_RESERVE)
        if not quiet:
            print(f"R latch prefix -> ov5 0x{ov5_cave.CAVE_RIDERLATCH:08X} ({len(pre)} B, "
                  f"arms {', '.join(t for t, *_ in latch_arms)})")
    for tag, armbyte, _key, _cid, _doc in latch_arms:
        if ov5_cave.read_cave(rom, armbyte, 4) != clear:
            ov5_cave.install_cave(rom, armbyte, clear, reserve=4)
            if not quiet:
                print(f"R  latch byte '{tag}' -> ov5 0x{armbyte:08X} (4 B, clear)")


def verify(rom, ov: bytes, check, latch_arms: tuple = LATCH_ARMS) -> None:
    """Assert the shared hook and every arm's one-shot byte. Call from each owner."""
    blob = stub(ov5_cave.CAVE_RIDERHOOK)
    check(bytes(ov[_off(RIDER_SITE):_off(RIDER_SITE) + 4])
          == _bl(RIDER_SITE, _hook_target(latch_arms))
          or ov5_cave.ik_tail(ov, _off(RIDER_SITE), RIDER_SITE) == _hook_target(latch_arms),   # via the Infernoble latch fronts
          f"R the summon-event default leaf @0x{RIDER_SITE:08X} -> "
          f"0x{_hook_target(latch_arms):08X} ({'latch prefix' if latch_arms else 'the SHARED stub'})")
    if latch_arms:
        pre = latch_stub(ov5_cave.CAVE_RIDERLATCH, latch_arms)
        check(ov5_cave.read_cave(rom, ov5_cave.CAVE_RIDERLATCH, len(pre)) == pre,
              f"R the latch prefix is present in ov5 @0x{ov5_cave.CAVE_RIDERLATCH:08X}")
        for tag, armbyte, _key, _cid, _doc in latch_arms:
            check(ov5_cave.read_cave(rom, armbyte, 4) == struct.pack("<I", 0),
                  f"R the latch byte '{tag}' @0x{armbyte:08X} ships CLEAR")
    check(ov5_cave.read_cave(rom, ov5_cave.CAVE_RIDERHOOK, len(blob)) == blob,
          f"R the shared rider stub is present in ov5 @0x{ov5_cave.CAVE_RIDERHOOK:08X} "
          f"({len(blob)} B, arms {', '.join(f'0x{c:04X}' for c, *_ in ARMS)})")
    clear = struct.pack("<I", 0)
    for cid, _tag, armbyte, _doc in ARMS:
        check(ov5_cave.read_cave(rom, armbyte, 4) == clear,
              f"R the one-shot byte for 0x{cid:04X} @0x{armbyte:08X} ships CLEAR")

"""The SHARED proper-Summon trigger hook: one stub, a REGISTER of cids.

WHY THIS MODULE EXISTS
======================
`summon.trigger_is_a_membership_list`: "If this card is Synchro / Fusion / Ritual
Summoned" is not a record predicate.  0x02265768 posts the event with the cls
selector HARD-CODED to 1, and whether a card gets the event at all is decided by
membership of ONE sorted u16 array, the proper-SS list 0x0228F6C0:

    0x022658FC  bl ...                   Orient Dragon's own hook
    0x02265900  cmp r0,#0                the membership verdict   <-- HOOK SITE (4 B)
    0x02265902  beq 0x02265910           not a member -> no trigger
    0x02265904  ...                      member: r5 = [0x02298A28+0x10] & 1, the
                                         "was this a PROPER summon" test
    0x02265910  ...                      the non-member path

That list holds **36 cids, every one a real card** -- there is no phantom to drop
for a count-neutral insert (`summon.synchro_trigger_list_has_no_phantom`) -- and
the membership lists on either side of it are packed flush at 0x0228F6BE and
0x0228F708, so it cannot be grown in place either.  A donor that is not already a
member can therefore only acquire the trigger from a stub at this site.

*** AND THERE IS EXACTLY ONE 4-BYTE SITE. ***  Accel Synchro Stardust Dragon
shipped one single-arm stub here (CAVE_ASSD_TRIG, in-game confirmed by the user
2026-09-14).  Junk Speeder's 2026-09-22 re-donor onto a vanilla Fusion monster
needed a second arm, and re-pointing the hook would have broken the confirmed
card.  So the hook, the stub and the cid register live here, exactly the way
timing_class_hook.py owns the WHEN/IF classifier site and criteria_row_hook.py
owns the row-offset site -- and for exactly the same reason.  This module IS
timing_class_hook.py's structure, deliberately.

REGISTERED CARDS
================
    0x126F  Meteor B. Dragon           -> Accel Synchro Stardust Dragon
                                          IN-GAME CONFIRMED 2026-09-14 (as CAVE_ASSD_TRIG),
                                          and RE-CONFIRMED 2026-09-22 from this two-arm stub
    0x120B  Twin-Headed Thunder Dragon -> Junk Speeder   IN-GAME CONFIRMED 2026-09-22

⚠️ BOTH arms were confirmed in the SAME duel session (user, 2026-09-22:
"confirmed all works"), which is the measurement that matters for a shared site:
adding the second arm did NOT displace the first.  Keep doing that — when you add
an arm, re-test every cid already in ARMS, not only the new one
(otn-shared-hook-lift-prove-by-execution).

Adding a card is one entry in ARMS.

⚠️⚠️ DUEL-ONLY.  This runs on every summon and the stub is in the ov5 cave, which
overlay 41 evicts in a puzzle (`mem.ov5_ov41_share_base`).  The same trade the
user accepted for Orient Dragon, Jet Warrior and Accel Synchro Stardust Dragon.

REGISTER CONTRACT AT THE HOOK SITE
==================================
r0 = the membership-search verdict (non-zero = the cid is in the list), r4 = the
summoned card's record, whose +0xE is its cid.  The stub replays the `cmp`
semantics by CHOOSING THE RETURN ADDRESS rather than setting flags: a hit returns
to `lr` (0x02265904, the member path), a miss adds the 0xC byte gap and returns to
0x02265910.  That is what makes the displaced `cmp ; beq` pair recoverable in 4
bytes, and it is the shape Accel Synchro Stardust Dragon's confirmed stub used
verbatim -- only the number of cid compares changed.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import ov3_off as _off
from otn_enhanced.effects.common import bl as _bl

# --- the hook site, after the proper-SS list search -------------------------
TRIG_SITE = 0x02265900          # `cmp r0,#0 ; beq 0x02265910`   (4 B)
TRIG_NATIVE = bytes.fromhex("002805d0")
TRIG_MEMBER = 0x02265904        # == lr, the address the BL returns to
TRIG_NONMEMBER = 0x02265910
LIST_LITERAL = 0x02265A30       # the pool slot holding 0x0228F6C0, the list base
TRIGGER_LIST = 0x0228F6C0

RESERVE = 0x60

# (cid, one-line description).  Order is irrelevant -- the arms are a pure OR.
ARMS: tuple[tuple[int, str], ...] = (
    (0x126F, "Meteor B. Dragon -> Accel Synchro Stardust Dragon "
             "(in-game confirmed 2026-09-14, re-confirmed from this stub 2026-09-22)"),
    (0x120B, "Twin-Headed Thunder Dragon -> Junk Speeder "
             "(re-donor, in-game confirmed by user 2026-09-22)"),
    (0x18FA, "Steam Gyroid -> Life Stream Dragon (2026-09-29; ov3 home in-game confirmed by user 2026-10-08)"),
)






def stub(base: int, arms: tuple = ARMS, skip: int = TRIG_NONMEMBER - TRIG_MEMBER) -> bytes:
    """Build the shared stub: native verdict, else any registered cid.

    `skip` = non-member address - member address at the hooked `cmp r0,#0 ; beq` pair
    (c79_trigger_hook reuses this stub at its own site with skip 2)."""
    b = EffectBuilder()
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "hit")
    b.insn("LDRH", "R0, [R4, #0xe]")
    for cid, _doc in arms:
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "hit")
    b.insn("MOV", "R0, #0x0")
    b.insn("PUSH", "{LR}")
    b.insn("POP", "{R1}")
    b.insn("ADD", f"R1, #{skip:#x}")
    b.insn("BX", "R1")
    b.label("hit")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def _home3() -> int:
    from otn_enhanced.effects import cave3
    return cave3.CAVE3_SUMMONTRIG


def live_home(ov) -> int | None:
    """The stub address the live BL at TRIG_SITE reaches (ov5 cave or ov3 pool), None = native."""
    cur = bytes(ov[_off(TRIG_SITE):_off(TRIG_SITE) + 4])
    hit = next((h for h in (ov5_cave.CAVE_SUMMONTRIG, _home3()) if cur == _bl(TRIG_SITE, h)), None)
    if hit is None:                      # Captain Roland's Infernoble front chained ahead: follow it to its tail
        t = ov5_cave.ik_tail(ov, _off(TRIG_SITE), TRIG_SITE)
        hit = t if t in (ov5_cave.CAVE_SUMMONTRIG, _home3()) else None
    return hit


def apply(ov: bytearray, *, quiet: bool = False, ov3: bool = False) -> None:
    """Install the 4-byte overlay-3 hook. Idempotent and order-independent.

    ov3=True (or a hook already in the ov3 pool) writes the stub to cave3.CAVE3_SUMMONTRIG (needs step 0)
    and points the site there -- REPOINTING an ov5 hook if one exists: ARMS is static, so every arm keeps
    working and the ov5 copy is left dead. install(rom, ov=ov) then skips the ov5 write."""
    home = _home3() if ov3 or live_home(ov) == _home3() else ov5_cave.CAVE_SUMMONTRIG
    if home == _home3():
        from otn_enhanced.effects import cave3
        blob = stub(home)
        assert len(blob) <= RESERVE, f"S summon-trigger hook is {len(blob)} B > the {RESERVE:#x} reserve"
        cave3.put(ov, home, blob)
    want = _bl(TRIG_SITE, home)
    cur = bytes(ov[_off(TRIG_SITE):_off(TRIG_SITE) + 4])
    if cur == want:
        if not quiet:
            print("S summon-trigger hook: already installed (idempotent)")
        return
    assert cur == TRIG_NATIVE or (home == _home3() and cur == _bl(TRIG_SITE, ov5_cave.CAVE_SUMMONTRIG)), (
        f"S the membership verdict 0x{TRIG_SITE:08X} is {cur.hex()}, expected the native "
        f"`cmp r0,#0 ; beq` ({TRIG_NATIVE.hex()}) or our BL -- another patch owns it")
    assert struct.unpack_from("<I", ov, _off(LIST_LITERAL))[0] == TRIGGER_LIST, \
        f"S 0x{TRIG_SITE:08X} no longer follows the proper-SS list search"
    ov[_off(TRIG_SITE):_off(TRIG_SITE) + 4] = want
    if not quiet:
        print(f"S summon trigger hooked @0x{TRIG_SITE:08X} -> "
              f"0x{home:08X} ({len(ARMS)} registered cids)")


def install(rom, *, quiet: bool = False, ov=None) -> None:
    """Write the shared stub into ov5 (skipped when *ov* is given and its hook lives in the ov3 pool).

    Read-back-and-skip, because ov5_cave.install_cave() asserts its destination is
    all-zero and would raise on the second card patch in a chained ROM.
    """
    if ov is not None and live_home(ov) == _home3():
        return
    blob = stub(ov5_cave.CAVE_SUMMONTRIG)
    effect_verify.assert_thumb1_only(blob, ov5_cave.CAVE_SUMMONTRIG)   # ARMv5TE = Thumb-1 ONLY
    assert len(blob) <= RESERVE, f"S summon-trigger hook is {len(blob)} B > the {RESERVE:#x} reserve"
    if ov5_cave.read_cave(rom, ov5_cave.CAVE_SUMMONTRIG, len(blob)) == blob:
        if not quiet:
            print(f"S shared summon-trigger stub @0x{ov5_cave.CAVE_SUMMONTRIG:08X}: "
                  f"already installed (idempotent)")
        return
    # An older stub (fewer ARMS) in a chained ROM: this slot is ours, so clear it rather than
    # weaken install_cave's free-slot guard (junk_speeder._reinstall_tuner_gate's pattern).
    if any(ov5_cave.read_cave(rom, ov5_cave.CAVE_SUMMONTRIG, RESERVE)):
        ov5 = ov5_cave._load_ov5_decompressed(rom)
        data = bytearray(ov5.data)
        off = ov5_cave.CAVE_SUMMONTRIG - ov5_cave.OV5_RAM_BASE
        data[off:off + RESERVE] = bytes(RESERVE)
        ov5_cave._save_ov5(rom, ov5, bytes(data))
    ov5_cave.install_cave(rom, ov5_cave.CAVE_SUMMONTRIG, blob, reserve=RESERVE)
    if not quiet:
        print(f"S shared summon-trigger stub -> ov5 0x{ov5_cave.CAVE_SUMMONTRIG:08X} "
              f"({len(blob)} B)")
        for cid, doc in ARMS:
            print(f"S   arm 0x{cid:04X}: {doc}")


def verify(ov: bytearray, check, *, rom=None) -> bool:
    """Assert the shared hook, using the caller's `check(cond, msg)`."""
    ok = True
    home = live_home(ov)
    ok &= check(home is not None,
                f"S the membership verdict @0x{TRIG_SITE:08X} -> the SHARED stub "
                f"({'none' if home is None else f'0x{home:08X}'})")
    home = home or ov5_cave.CAVE_SUMMONTRIG
    ok &= check(struct.unpack_from("<I", ov, _off(LIST_LITERAL))[0] == TRIGGER_LIST,
                f"S the site still follows the proper-SS list 0x{TRIGGER_LIST:08X} search")
    if rom is not None:
        from otn_enhanced.effects import cave3
        blob = stub(home)
        ok &= check(cave3.read_code(rom, ov, home, len(blob)) == blob,
                    f"S the shared stub is present @0x{home:08X} "
                    f"({len(blob)} B, arms {', '.join(f'0x{c:04X}' for c, _ in ARMS)})")
    return ok

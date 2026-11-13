"""The SHARED half of the "Special Summon by banishing from your GY" pipeline.

WHY THIS MODULE EXISTS
======================
"You can Special Summon this card (from your hand) by banishing N <filter>
monsters from your GY" is not one edit, it is a PIPELINE, and the stages are
split between per-card structures and TWO SHARED CODE HOOKS:

    stage                                    where                        per-card?
    ---------------------------------------  ---------------------------  ---------
    legality  (may this card do it at all)   hand-SS BST dead arm          yes
    count     (how many per pass)            0x0225CF28 branch             yes
    filter    (what may be banished)         criteria rows + list A        yes
    procedure (is there a cost at all)       registry 0x0228F158 row       yes
    PAYMENT   (actually select and banish)   dispatch 1 root 0x02262962    *** NO ***
                                             dispatch 2 root 0x02262C24    *** NO ***

The two payment dispatches have exactly ONE 4-byte BL hook each, so a stub that
hardcodes a single donor cid can only ever serve one card. That is why the donor
register lives here instead of inside one card's module: whichever patch runs
first writes stubs covering EVERY registered donor, and the next one finds them
already byte-correct. The write is idempotent and order-independent, so a
single-card test ROM and the full chain produce identical bytes.

notes/darkflare-dragon-findings.md asked for exactly this on 2026-08-05 --
*"build the routing stub to take a LIST of cids, not one"* -- and Lightpulsar
shipped single-cid stubs anyway; this module is that correction.

REGISTERED DONORS
=================
    0x0FB1  Sword Arm of Dragon -> Lightpulsar Dragon   IN-GAME CONFIRMED 2026-08-13
    0x1646  Battle Footballer   -> Darkflare Dragon      (2026-08-17)

Adding a third card is one line here plus that card's own four per-card stages.

THE HOST: 126 B OF PROVABLY-DEAD OVERLAY-3 CODE
===============================================
The stubs live at 0x0225F240..0x0225F2BE (mem.ov3_handss_dead_run), two leaves
that were reachable ONLY from two dead dispatch arms. It is ov3 CODE, not BSS, so
unlike the ov3_cave.py BSS windows the engine's BSS clear does not wipe it -- and
being ov3 it is resident in puzzles too, unlike the ov5 cave.

*** THE CAVE MUST STAY UNREACHABLE. *** The two arms that used to branch into it
have to point somewhere else. "Somewhere else" is the reject leaf for an unclaimed
arm -- but an arm a card has ROUTED (Darkflare took 0x0225E88E) points at a real
leaf instead, which serves the same purpose. So the invariant this module applies
and checks is the one that actually matters:

    NO ARM MAY BRANCH INTO [CAVE, CAVE + CAVE_LEN).

(An earlier version of lightpulsar asserted the strictly stronger "the arm
points at the reject leaf", which would have made Darkflare's routing look like a
collision when it is not one.)

REGISTER DISCIPLINE
===================
Both stubs clobber only r2, a scratch compare register in both dispatches, loaded
from the pool at 0x0226296C / 0x02262C26 and never an argument -- EXCEPT on
dispatch 2's `bgt` path, where 0x02262C5E does `adds r1,r2,#0` and needs
r2 == 0x1BC8. Stub 2 therefore replays the displaced `ldr`/`cmp` and returns via
`push {r2}` / `pop {pc}`, preserving both r2 and the compare's flags.
(`pop {pc}` is deliberate -- cf. thumb.pop_into_lr: Thumb-1 POP can load PC but
never LR.)

*** DO NOT hook dispatch 2's shared completion arm 0x02262CA4 instead of its root:
    0x02262C8C's own "both passes done" path branches THERE, so a cid test at
    0x02262CA4 sends the donor back to 0x02262C8C forever. An early draft of
    lightpulsar had exactly that bug. ***
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects.common import ov3_off as _off
from otn_enhanced.effects.common import bl as _bl

# ---------------------------------------------------------------------------
# THE REGISTER -- every cid whose summon cost is "banish from your GY, LIGHT+DARK
# style", i.e. every cid routed to the payment handler 0x0226292D by a row in the
# summon-procedure registry.  Order is irrelevant (the stub tests them all), but
# keep it ascending for readability.
# ---------------------------------------------------------------------------
DONOR_CIDS: tuple[int, ...] = (
    0x0FB1,     # Sword Arm of Dragon -> Lightpulsar Dragon
    0x1646,     # Battle Footballer   -> Darkflare Dragon
)

# ---------------------------------------------------------------------------
# the ov3 dead run that hosts the stubs
# ---------------------------------------------------------------------------
CAVE = 0x0225F240
CAVE_LEN = 0x0225F2BE - 0x0225F240          # 126

# the two arms that were the ONLY references into the cave, with the leaf each
# natively branched to (both leaves are inside the cave)
DEAD_ARMS = ((0x0225E692, 0x0225F26E), (0x0225E88E, 0x0225F240))
REJECT_LEAF = 0x0225FF96

# ---------------------------------------------------------------------------
# dispatch 1 -- how many cards must be selected this pass
# ---------------------------------------------------------------------------
PAY1_HOOK = 0x0226298C              # was `beq 0x02262A52` + `b 0x02262AAE`
PAY1_NECRO = 0x02262A52             # Dark Necrofear 0x1466's arm -- must be preserved
PAY1_FAMILY = 0x02262A5A            # the LIGHT+DARK "select 2" arm
PAY1_DEFAULT = 0x02262AAE           # the do-nothing default
PAY1_NECRO_CID = 0x1466

# ---------------------------------------------------------------------------
# dispatch 2 -- the two-pass driver (this is what makes the DARK pass happen)
# ---------------------------------------------------------------------------
PAY2_HOOK = 0x02262C26              # was `ldr r2,=0x1BC8` + `cmp r0,r2`
PAY2_FAMILY = 0x02262C8C            # [rec+0x28] += 1 ; if old index 0 -> [rec+0x24] = 4
PAY2_RESUME = 0x02262C2A            # the displaced instructions' continuation
PAY2_BASE_CID = 0x1BC8              # the literal the displaced `ldr` fetched






def bl_target(ov: bytearray, src: int) -> int:
    """Decode the BL halfword pair at *src* back to its absolute target."""
    w1, w2 = struct.unpack_from("<HH", ov, _off(src))
    off = ((w1 & 0x7FF) << 12) | ((w2 & 0x7FF) << 1)
    if off & (1 << 22):
        off -= (1 << 23)
    return src + 4 + off


def stub_pay1(base: int, cids: tuple[int, ...] = DONOR_CIDS) -> bytes:
    """Dispatch 1: route every registered donor to the two-card select arm.

    Dark Necrofear is tested FIRST and forwarded to its own arm, because the
    instruction pair this stub displaces was that card's `beq`.
    """
    b = EffectBuilder()
    b.ldr_const(2, PAY1_NECRO_CID)
    b.insn("CMP", "R0, R2")
    b.insn("BEQ", "necro")
    for cid in cids:
        b.ldr_const(2, cid)
        b.insn("CMP", "R0, R2")
        b.insn("BEQ", "donor")
    b.ldr_const(2, PAY1_DEFAULT | 1)
    b.insn("BX", "R2")
    b.label("necro")
    b.ldr_const(2, PAY1_NECRO | 1)
    b.insn("BX", "R2")
    b.label("donor")
    b.ldr_const(2, PAY1_FAMILY | 1)
    b.insn("BX", "R2")
    return b.assemble(base, pad="nop")


def stub_pay2(base: int, cids: tuple[int, ...] = DONOR_CIDS) -> bytes:
    """Dispatch 2: route every registered donor to the two-pass driver.

    The fall-through path replays the displaced `ldr r2,=0x1BC8 ; cmp r0,r2` so
    the native code resumes with both r2 and the flags intact.
    """
    b = EffectBuilder()
    for cid in cids:
        b.ldr_const(2, cid)
        b.insn("CMP", "R0, R2")
        b.insn("BEQ", "family")
    b.ldr_const(2, PAY2_RESUME | 1)
    b.insn("PUSH", "{R2}")
    b.ldr_const(2, PAY2_BASE_CID)
    b.insn("CMP", "R0, R2")
    b.insn("POP", "{PC}")
    b.label("family")
    b.ldr_const(2, PAY2_FAMILY | 1)
    b.insn("BX", "R2")
    return b.assemble(base, pad="nop")


def layout(cids: tuple[int, ...] = DONOR_CIDS) -> tuple[bytes, int, bytes]:
    """Lay the two stubs out back to back, halfword-aligned.

    Returns (pay1_blob, pay2_base, pay2_blob).
    """
    a = stub_pay1(CAVE, cids)
    if (CAVE + len(a)) % 2:
        a += struct.pack("<H", 0x46C0)                  # nop
    b_base = CAVE + len(a)
    b = stub_pay2(b_base, cids)
    if (b_base + len(b)) % 2:
        b += struct.pack("<H", 0x46C0)
    return a, b_base, b


def apply(ov: bytearray, cids: tuple[int, ...] = DONOR_CIDS, *, quiet: bool = False) -> int:
    """Install the shared payment side. Idempotent and order-independent.

    Returns the pay-2 stub's base address (callers print it).
    """
    # (1) no arm may branch INTO the cave. An arm still pointing at its native
    #     dead leaf is retargeted at the reject leaf; an arm a card has already
    #     routed somewhere outside the cave is left exactly as it is.
    for site, native_leaf in DEAD_ARMS:
        tgt = bl_target(ov, site)
        if not (CAVE <= tgt < CAVE + CAVE_LEN):
            continue                                    # already safe (reject, or routed)
        assert tgt == native_leaf, (
            f"D arm @0x{site:08X} branches to 0x{tgt:08X}, inside the cave but not its "
            f"native leaf 0x{native_leaf:08X} -- the cave layout has changed")
        ov[_off(site):_off(site) + 4] = _bl(site, REJECT_LEAF)
    if not quiet:
        print(f"D shared: no arm branches into the ov3 cave 0x{CAVE:08X}"
              f"..0x{CAVE + CAVE_LEN:08X}")

    # (2) the stubs
    a, b_base, b = layout(cids)
    used = (b_base + len(b)) - CAVE
    assert used <= CAVE_LEN, (
        f"E the payment stubs need {used} B but the dead run is only {CAVE_LEN} B "
        f"(donors: {[hex(c) for c in cids]})")
    for blob, at in ((a, CAVE), (b, b_base)):
        effect_verify.assert_thumb1_only(blob, at)      # ARMv5TE = Thumb-1 ONLY
        ov[_off(at):_off(at) + len(blob)] = blob
    if not quiet:
        print(f"E shared payment stubs @0x{CAVE:08X}: pay-1 {len(a)} B, pay-2 {len(b)} B "
              f"@0x{b_base:08X} ({used}/{CAVE_LEN} B) -- donors "
              f"{', '.join(f'0x{c:04X}' for c in cids)}")

    # (3) the two 4-byte hooks, at the dispatch ROOTS (never the shared arms)
    for site, target, label in ((PAY1_HOOK, CAVE, "pay-1 (select count)"),
                                (PAY2_HOOK, b_base, "pay-2 (two-pass driver)")):
        want = _bl(site, target)
        if bytes(ov[_off(site):_off(site) + 4]) != want:
            ov[_off(site):_off(site) + 4] = want
            if not quiet:
                print(f"F {label} dispatch hooked @0x{site:08X} -> 0x{target:08X}")
    return b_base


def verify(ov: bytearray, check, cids: tuple[int, ...] = DONOR_CIDS) -> bool:
    """Assert the shared payment side, using the caller's `check(cond, msg)`."""
    ok = True
    a, b_base, b = layout(cids)
    used = (b_base + len(b)) - CAVE

    for site, _native in DEAD_ARMS:
        tgt = bl_target(ov, site)
        ok &= check(not (CAVE <= tgt < CAVE + CAVE_LEN),
                    f"D arm @0x{site:08X} -> 0x{tgt:08X}, outside the cave "
                    f"(the stubs stay unreachable except through the hooks)")

    ok &= check(bytes(ov[_off(CAVE):_off(CAVE) + len(a)]) == a,
                f"E pay-1 stub present @0x{CAVE:08X} ({len(a)} B, "
                f"{len(cids)} donor{'s' if len(cids) != 1 else ''})")
    ok &= check(bytes(ov[_off(b_base):_off(b_base) + len(b)]) == b,
                f"E pay-2 stub present @0x{b_base:08X} ({len(b)} B)")
    ok &= check(used <= CAVE_LEN, f"E both pay stubs fit the dead run ({used}/{CAVE_LEN} B)")
    ok &= check(bytes(ov[_off(PAY1_HOOK):_off(PAY1_HOOK) + 4]) == _bl(PAY1_HOOK, CAVE),
                f"F pay-1 dispatch hooked @0x{PAY1_HOOK:08X}")
    ok &= check(bytes(ov[_off(PAY2_HOOK):_off(PAY2_HOOK) + 4]) == _bl(PAY2_HOOK, b_base),
                f"F pay-2 dispatch hooked @0x{PAY2_HOOK:08X}")

    # the arms the stubs jump INTO must still be what we think they are
    def u16(ram: int) -> int:
        return struct.unpack_from("<H", ov, _off(ram))[0]

    ok &= check(u16(PAY1_FAMILY) == 0x8D20 and u16(PAY1_FAMILY + 2) == 0x2502,
                "F pay-1 family arm is still `ldrh r0,[r4,#0x28] ; movs r5,#2`")
    ok &= check(u16(PAY2_FAMILY) == 0x8D21 and u16(PAY2_FAMILY + 2) == 0x1C48,
                "F pay-2 family arm is still the pass-index increment")
    ok &= check(u16(PAY2_RESUME) == 0xDC18,
                "F pay-2 resume point is still `bgt 0x02262C5E` (r2 must survive)")
    return ok

"""The SHARED deck-send phase-0x7C hook: one stub, a REGISTER of cids.

WHY THIS MODULE EXISTS
======================
``dispatch.post_send_followup_phase``: the shared deck-send resolver 0x02208DD4 is
a 9-phase state machine (jump table @0x02208DFA, phases 0x78..0x80):

    0x80 activate -> 0x7F select -> 0x7E count -> 0x7D send-loop -> done -> 0x7C

Phase **0x7C** is the POST-SEND FOLLOW-UP: the place to hang whatever must happen
after the cards have actually reached the GY.  Every deck-sending card reaches it;
the gate at **0x02208F42** is the in-phase cid FILTER, a 20-byte three-cid compare
tree ending in ``bne 0x02209046`` ("nothing to do").

*** AND THERE IS EXACTLY ONE GATE AT THAT SITE. ***  A stub owned by one card
module can therefore only ever serve one card.  ``dragon_shrine`` shipped
first and installed its own gate pointing at ``CAVE_DS_FOLLOW``, whose stub
re-dispatched the three native cids itself.  Accel Synchron clause 2 needs the same
phase.  Re-pointing the gate a second time would have broken Dragon Shrine's
clause 2, and either module's ``GATE_STOCK`` assert would have aborted the chain
build depending on the order.

So the gate, the dispatcher stub and the cid register live HERE, exactly the way
``criteria_row_hook.py`` owns the criteria-row-offset hook and
``handss_banish_cost.py`` owns the shared payment stubs -- and for exactly the same
reason.  See ``tool.shared_hook_lift_prove_by_execution``.

REGISTERED CARDS
================
    0x14C1  The Puppet Magic... -> Dragon Shrine    clause 2  (lifted 2026-09-03)
    0x11A3  Bracchio-raidus     -> Accel Synchron   clause 2  (2026-09-03)

Adding a card is one entry in :data:`ARMS` plus its own cave slot.

⚠️ Adding an arm changes the dispatcher's instruction layout, so EVERY other arm's
offsets move.  Run ``uv run python -m scratch.followhook_equiv`` after
any change to :data:`ARMS` and assert that no already-shipped cid -- the three
native owners included -- changes which exit it takes.

⚠️ DUEL-ONLY.  The dispatcher lives in the ov5 cave, which overlay 41 evicts in a
puzzle, so every registered card's phase-0x7C clause is normal-duel-only.  The
NATIVE cids are unaffected in a puzzle only because the gate itself is ov3 -- but
the gate now jumps into ov5, so in a puzzle the jump target is not resident.  This
is the same accepted trade every ov5 hook in this repo makes (``prefer-ov5-cave``);
it is called out here because this hook sits on a path THREE stock cards use.

REGISTER CONTRACT AT THE HOOK SITE
==================================
The gate is reached by a ``bx`` from inside the resolver, NOT a call: the
resolver's own frame (``push {r1-r7,lr}`` at 0x02208DD4) is still live.

    r4 = the event descriptor      (r4[+0] u16 cid, [+2] side, [+3] zone, [+6] side-xor)
    r5 = the phase-state block     ([+0x74] send count, [+0x78] prompt mode)
    LR is FREE to clobber -- the return address is on the stack.

An arm's body is entered with r4/r5 intact and must exit either by jumping back
into native code or by replicating the resolver's own epilogue
``pop {r1,r2,r3,r4,r5,r6,r7,pc}`` with the next phase code in r0.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects.ov5_cave import CAVE_FOLLOWHOOK, CAVE_DS_FOLLOW, CAVE_AS_FOLLOW
from otn_enhanced.effects.common import ov3_off as _off

# ---- the shared ov3 site ------------------------------------------------------
GATE_ADDR = 0x02208F42          # `ldrh r1,[r4]` -- first insn of the stock gate
GATE_LEN = 0x14                 # through 0x02208F55 (the `bne 0x02209046`)
GATE_NATIVE_BODY = 0x02208F56   # the shared body the three native cids fall into
GATE_EXIT = 0x02209046          # `movs r0,#0x64 ; pop {...}` -- nothing to do

# The three stock owners of phase 0x7C.  Power Baton / Venom Shot / 0x1DC2.
NATIVE_FOLLOW_CIDS = (0x0DBF, 0x1C15, 0x1DC2)

# stock bytes of the gate, read from the committed ov3 oracle and asserted before
# the overwrite so a drifted engine aborts the build instead of corrupting it
GATE_STOCK = bytes.fromhex("21884f48814205d04f48814202d04e48814277d1")

# what the gate becomes: `ldr r0,[pc,#4] ; bx r0 ; nop ; .word CAVE_FOLLOWHOOK|1`
GATE_PATCHED = struct.pack("<HHHI", 0x4801, 0x4700, 0x46C0, CAVE_FOLLOWHOOK | 1)

# ---- the cid register ---------------------------------------------------------
DS_CID = 0x14C1                 # Dragon Shrine   (dragon_shrine, clause 2)
AS_CID = 0x11A3                 # Accel Synchron  (accel_synchron, clause 2)

#: (cid, body address in the ov5 cave, owner) -- ORDER IS THE DISPATCH ORDER.
ARMS: list[tuple[int, int, str]] = [
    (DS_CID, CAVE_DS_FOLLOW, "dragon_shrine"),
    (AS_CID, CAVE_AS_FOLLOW, "accel_synchron"),
]


def build_dispatcher(arms: list[tuple[int, int, str]] | None = None) -> bytes:
    """The shared phase-0x7C dispatcher.

        cid = desc[+0]
        if cid in NATIVE_FOLLOW_CIDS: goto 0x02208F56    ; the stock body
        for (arm_cid, body) in ARMS:
            if cid == arm_cid: goto body                 ; that card's clause
        goto 0x02209046                                  ; nothing to do

    r0/r1 are dead on every native path (the stock gate itself clobbers r1 with
    ``ldrh r1,[r4]``), so both are free scratch here.
    """
    arms = ARMS if arms is None else arms
    a = EffectBuilder()
    a.insn("LDRH", "R0, [R4, #0x0]")            # r0 = cid
    for i, cid in enumerate(NATIVE_FOLLOW_CIDS):
        a.ldr_const(1, cid)
        a.insn("CMP", "R0, R1")
        a.insn("BEQ", "native")
    for i, (cid, body, _owner) in enumerate(arms):
        a.ldr_const(1, cid)
        a.insn("CMP", "R0, R1")
        a.insn("BNE", f"not{i}")
        a.ldr_const(0, body | 1)
        a.insn("BX", "R0")
        a.label(f"not{i}")
    a.ldr_const(0, GATE_EXIT | 1)
    a.insn("BX", "R0")
    a.label("native")
    a.ldr_const(0, GATE_NATIVE_BODY | 1)
    a.insn("BX", "R0")
    code = a.assemble(CAVE_FOLLOWHOOK)
    assert_thumb1_only(code, CAVE_FOLLOWHOOK)
    return code




def apply_gate(ov: bytearray) -> None:
    """Repoint the resolver's phase-0x7C gate at the shared dispatcher.

    Idempotent, and safe to call from every registered card's ``main()`` -- the
    first caller installs it, the rest see it already installed.
    """
    at = _off(GATE_ADDR)
    if bytes(ov[at:at + len(GATE_PATCHED)]) == GATE_PATCHED:
        print(f"  phase-0x7C gate already -> CAVE_FOLLOWHOOK {CAVE_FOLLOWHOOK:#010x}"
              " -- skipped (idempotent)")
        return
    if bytes(ov[at:at + len(GATE_STOCK)]) != GATE_STOCK:
        raise SystemExit(
            f"phase-0x7C gate @{GATE_ADDR:#010x} is neither stock nor ours: "
            f"{bytes(ov[at:at + GATE_LEN]).hex()}\n"
            "  (a card module must NOT install its own gate here -- register an "
            "arm in deck_send_follow_hook.ARMS instead)")
    ov[at:at + len(GATE_PATCHED)] = GATE_PATCHED
    print(f"  phase-0x7C gate @{GATE_ADDR:#010x} -> CAVE_FOLLOWHOOK "
          f"({CAVE_FOLLOWHOOK | 1:#010x}), {len(ARMS)} arm(s): "
          + ", ".join(f"{c:#06x} {o}" for c, _b, o in ARMS))


def verify_gate(ov3: bytes) -> bool:
    """True iff the gate points at the shared dispatcher."""
    at = _off(GATE_ADDR)
    return bytes(ov3[at:at + len(GATE_PATCHED)]) == GATE_PATCHED

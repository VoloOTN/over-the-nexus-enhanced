"""Stage: booster-pack unlock conditions (overlay 1 jump table).

Reuses the overlay-1 plumbing of ``system.unlock_all_packs``; this stage differs in
rewriting the *per-pack* arms so a single pack (60) can be left unlocked alone.
"""
from __future__ import annotations

import struct

from otn_enhanced.system.unlock_all_packs import (
    OV1_BASE, _branch as _arm_branch, _load_ov1 as _load, _save_ov1,
)

#: ``addls pc, pc, r0, lsl #2`` -- the dispatch that indexes the jump table.
PACK_DISPATCH = 0x0214511C
PACK_DISPATCH_WORD = 0x908FF100
#: Slot for pack *n* is ``PACK_JUMP_TABLE + n * 4``; every slot is a plain ARM B.
PACK_JUMP_TABLE = 0x02145124
#: Unconditional set-bit arm.  Deliberately not 0x02145BC0 -- that tail also
#: fires the "new pack unlocked!" notifier, which would pop 60 times per visit.
PACK_SET_BIT = 0x02145218
#: Loop tail: condition failed, bit left clear, pack stays locked.
PACK_LOOP_TAIL = 0x02145D8C
FIRST_PACK, LAST_PACK = 1, 60

PACK_MODE_STOCK = "stock"
PACK_MODE_ALL = "all"
PACK_MODE_ONLY_LAST = "only60"



def _load_ov1(rom):
    try:
        return _load(rom)
    except AssertionError as exc:       # system module asserts; callers expect ValueError
        raise ValueError(str(exc)) from None


def stage_packs(rom, cfg, log) -> int:
    """Rewrite the overlay-1 pack-unlock jump table.  Returns slots written."""
    if cfg.pack_mode == PACK_MODE_STOCK:
        return 0

    ov, data = _load_ov1(rom)

    # The dispatch must be intact, or the jump table is not where we think.
    got = struct.unpack_from("<I", data, PACK_DISPATCH - OV1_BASE)[0]
    if got != PACK_DISPATCH_WORD:
        raise ValueError(
            f"overlay 1 {PACK_DISPATCH:#010x} holds {got:#010x}, expected "
            f"{PACK_DISPATCH_WORD:#010x} (addls pc, pc, r0, lsl #2)"
        )

    written = 0
    for pack in range(FIRST_PACK, LAST_PACK + 1):
        addr = PACK_JUMP_TABLE + pack * 4
        off = addr - OV1_BASE
        current = struct.unpack_from("<I", data, off)[0]
        # Structural guard: every stock slot is an unconditional ARM B.
        if current >> 24 != 0xEA:
            raise ValueError(
                f"pack {pack} slot {addr:#010x} holds {current:#010x}, "
                "which is not an unconditional ARM branch"
            )
        if cfg.pack_mode == PACK_MODE_ALL:
            target = PACK_SET_BIT
        else:
            target = PACK_SET_BIT if pack == LAST_PACK else PACK_LOOP_TAIL
        struct.pack_into("<I", data, off, _arm_branch(addr, target))
        written += 1

    if cfg.pack_mode == PACK_MODE_ALL:
        log(f"  packs {FIRST_PACK}-{LAST_PACK} -> always unlocked")
    else:
        log(f"  pack {LAST_PACK} -> unlocked, packs {FIRST_PACK}-{LAST_PACK - 1} -> locked")

    if not cfg.dry_run:
        _save_ov1(rom, ov, bytes(data))
    return written

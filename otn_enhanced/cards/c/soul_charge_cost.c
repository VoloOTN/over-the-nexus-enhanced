/* Soul Charge cost (CAVE_SC_COST): unless 0x021D2B88 says so, log (side, cid, kind 1) and the follow-up node
 * (side, 0x0EBD, 1, desc halfword +0xC). Returns 1. a1-a3 pass through to 0x021D2B88 (arity bounded at 4). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    if (!fn_021D2B88((u32)e, a1, a2, a3)) {
        turnlog_post(e->controller, e->cid, 1, 0);
        turnlog_post(e->controller, 0x0EBD, 1, *(const u16 *)((const u8 *)e + 0xC));
    }
    return 1;
}

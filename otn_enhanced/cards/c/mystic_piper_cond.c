/* Mystic Piper once-per-turn condition (CAVE3_PIPER_COND): before the cost ran (ctx +7 == 0), refuse if already
 * logged this turn (slot 0xB, kind 1); otherwise the vanilla ignition check 0x021F06E8. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (!e->cost_ran && turnlog_query(e->controller, 0xB, e->cid, 1))
        return 0;
    return can_take_ignition((u32)e);
}

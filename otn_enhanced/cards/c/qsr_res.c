/* Shooting Quasar Dragon negate resolver (CAVE3_QSR_RES): unless 0x021D2B88 says so, log (side, cid, kind 1)
 * for once-per-turn; then run the native negate resolver 0x022062F8 on (ctx, a1). a2/a3 pass through to
 * 0x021D2B88 (arity bounded at 4). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    if (!fn_021D2B88((u32)e, a1, a2, a3))
        turnlog_post(e->controller, e->cid, 1, 0);
    return negate_resolver((u32)e, a1);
}

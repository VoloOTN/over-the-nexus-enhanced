/* Masked HERO Dark Law slot 4 (CAVE_DL_SLOT4): the "You can" tag 0x021E51E4(ctx, a1); when it answers 1, run the
 * per-copy rider 0x021E5060(ctx). Returns the tag's answer. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = you_can_tag(e, a1);
    if (r == 1)
        fn_021E5060((u32)e);
    return r;
}

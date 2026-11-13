/* Life Stream Dragon resolver (CAVE3_LSD_RES): in resolver phase 0x80 (word 0x0229AAFC + 0x70), set the
 * controller's LP to 4000 and return 0x7F (phase protocol); else 0. */
#include "engine.h"

#define RESOLVER_PHASE (*(volatile u32 *)(0x0229AAFC + 0x70))

ENTRY int entry(EffectCtx *e)
{
    if (RESOLVER_PHASE != 0x80)
        return 0;
    set_lp(e->controller, 4000);
    return 0x7F;
}

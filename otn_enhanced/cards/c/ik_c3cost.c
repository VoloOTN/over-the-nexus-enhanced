/* Infernoble Knight Ogier C3 cost (CAVE_IK_C3COST, cls2 +10): log (side, 0x13A3, kind 1) for once-per-turn. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, 0x13A3, 1, 0);
    return 1;
}

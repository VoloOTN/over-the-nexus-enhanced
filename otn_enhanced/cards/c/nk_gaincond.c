/* Nikitama gain condition (CAVE_NK_GAINCOND): 2 once the cost ran or while the gain node 0x3E52 is not logged this
 * turn (slot 0xB, kind 1); else 0. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (!e->cost_ran && turnlog_query(e->controller, 0xB, 0x3E52, 1))
        return 0;
    return 2;
}

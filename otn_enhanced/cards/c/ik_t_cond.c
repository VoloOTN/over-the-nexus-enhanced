/* Infernoble Turpin condition (CAVE_IK_T_COND): clear the halfword at +0x18 when desc+3 == 0xE, then 2 if
 * CAVE_IK_T_LEGAL(desc) passes, else 0. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (e->race == 0xE)
        *(volatile u16 *)((u32)e + 0x18) = 0;
    return slot_CAVE_IK_T_LEGAL((u32)e) ? 2 : 0;
}

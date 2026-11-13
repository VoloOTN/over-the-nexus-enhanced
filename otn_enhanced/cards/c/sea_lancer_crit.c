/* Sea Lancer criteria (CAVE3_SL_CRIT): the criteria registrar 0x0223C6AC over side a1 for desc's cid, predicate
 * 0x0223C791, list 0x021DED78; on the stack desc[+8] and 8. */
#include "engine.h"

ENTRY int entry(const u8 *d, u32 side)
{
    return criteria_registrar(side, *(const u16 *)d, 0x0223C791, 0x021DED78, *(const u32 *)(d + 8), 8);
}

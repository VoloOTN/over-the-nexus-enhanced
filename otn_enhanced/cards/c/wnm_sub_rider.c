/* W Nebula Meteorite sub-rider (CAVE3_WNM_SUB_RIDER): if the zone predicate (mask 0x15) passes for (a0, side a1,
 * zone a2), return CAVE3_WNM_CHECK(cid of that monster-row slot), else 0. Row = 0x0229ACC8 + side * 0xB3C + zone * 20. */
#include "engine.h"

ENTRY int entry(u32 a0, u32 a1, u32 a2)
{
    if (!zone_predicate(a0, a1, a2, 0x15))
        return 0;
    u32 w = *(volatile u32 *)(0x0229ACC8 + (a1 & 1) * 0xB3C + a2 * 20);
    return slot_CAVE3_WNM_CHECK(CID(w));
}

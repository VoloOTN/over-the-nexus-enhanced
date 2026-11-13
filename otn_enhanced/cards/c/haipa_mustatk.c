/* Karakuri Haipa must-attack (CAVE3_HAIPA_MUSTATK): the cid in zone (a0, a1) (0x021A36EC), with the two
 * Karakuri cids 0x0FC8 / 0x0FFD reported as 0x2388. */
#include "engine.h"

ENTRY u32 entry(u32 a0, u32 a1)
{
    u32 cid = zone_cid_at(a0, a1);
    return cid == 0x0FC8 || cid == 0x0FFD ? 0x2388 : cid;
}

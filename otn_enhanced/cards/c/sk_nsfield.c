/* Sakitama NS field check (CAVE3_SK_NSFIELD): for its node 0x3E50, 0 if (side, 0xB, 0x13E5, kind 1) is logged this
 * turn, else -1; anything else goes to Scrap Raptor's check (CAVE3_SR_NSFIELD, the next link). */
#include "engine.h"

ENTRY int entry(u32 side, u32 cid)
{
    if (cid != 0x3E50)
        return slot_CAVE3_SR_NSFIELD(side, cid);
    return turnlog_query(side, 0xB, 0x13E5, 1) ? 0 : -1;
}

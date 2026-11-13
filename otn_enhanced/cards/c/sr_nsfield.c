/* Scrap Raptor NS field check (CAVE3_SR_NSFIELD): for Scrap Raptor (0x0FF6), 0 if (side, 0xB, 0x0FF6, kind 1) is
 * logged this turn, else -1; any other cid goes to the shared NS field check (CAVE3_NS_FIELD). The old stub's
 * compare left 0x0FF6 in r2, so both calls get it as their third argument. */
#include "engine.h"

#define SCRAP_RAPTOR 0x0FF6

ENTRY int entry(u32 side, u32 cid)
{
    if (cid != SCRAP_RAPTOR)
        return slot_CAVE3_NS_FIELD(side, cid, SCRAP_RAPTOR);
    return turnlog_query(side, 0xB, SCRAP_RAPTOR, 1) ? 0 : -1;
}

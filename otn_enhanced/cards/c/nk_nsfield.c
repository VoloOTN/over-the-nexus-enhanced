/* Nikitama NS field check (CAVE3_NK_NSFIELD): for its node 0x3E51, 0 if (side, 0xB, 0x3E52, kind 1) is logged this
 * turn, else -1; anything else goes to Sakitama's check (CAVE3_SK_NSFIELD, the next link). */
#include "engine.h"

ENTRY int entry(u32 side, u32 cid)
{
    if (cid != 0x3E51)
        return slot_CAVE3_SK_NSFIELD(side, cid);
    return turnlog_query(side, 0xB, 0x3E52, 1) ? 0 : -1;
}

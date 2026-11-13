/* Safe Zone target filter (CAVE3_SZ_FILTER): the zone predicate with mask 0xC94. */
#include "engine.h"

ENTRY int entry(u32 a0, u32 a1, u32 a2)
{
    return zone_predicate(a0, a1, a2, 0xC94);
}

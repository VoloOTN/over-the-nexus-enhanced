/* W Nebula Meteorite sub-activation filter (CAVE3_WNM_SUB_ACT): the zone predicate with mask 0x118. */
#include "engine.h"

ENTRY int entry(u32 a0, u32 a1, u32 a2)
{
    return zone_predicate(a0, a1, a2, 0x118);
}

/* Windrose the Elemental Lord AI class (CAVE_WR_AICLASS): the native summon-restriction class
 * (0x020231C8, KB dispatch.summon_restriction_classifier), forced to 2 for its own cid (0x190B). */
#include "engine.h"

#define WINDROSE 0x190B

ENTRY int entry(u32 cid)
{
    int r = summon_restriction_class(cid);
    return cid == WINDROSE ? 2 : r;
}

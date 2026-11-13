/* W Nebula Meteorite check (CAVE3_WNM_CHECK): 1 iff cid is a monster, 0x0202ABC8(cid) == 1 and its race is 0x14. */
#include "engine.h"

ENTRY int entry(u32 cid)
{
    return is_monster(cid) && fn_0202ABC8(cid) == 1 && get_race(cid) == 0x14;
}

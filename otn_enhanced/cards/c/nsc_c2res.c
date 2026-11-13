/* Neo Space Connector C2 resolver (CAVE_NSC_C2RES): Special Summon from the pick, (a0, 1, 1) -> 0x02204730. */
#include "engine.h"

ENTRY int entry(u32 a0)
{
    ss_from_pick(a0, 1, 1);
    return 0;
}

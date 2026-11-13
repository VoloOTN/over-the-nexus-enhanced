/* Sakitama cost (CAVE_SK_COST): from zone 0xB (desc +3), first 0x021D2598(side, desc halfword +0xC) and log kind 1;
 * otherwise kind 2. Logs (side, 0x13E5, kind). Returns 1. */
#include "engine.h"

ENTRY int entry(u8 *d)
{
    u32 kind = 2;
    if (d[3] == 0xB) {
        fn_021D2598(d[2], *(const u16 *)(d + 0xC));
        kind = 1;
    }
    turnlog_post(d[2], 0x13E5, kind, 0);
    return 1;
}

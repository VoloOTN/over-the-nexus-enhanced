/* Dragunity Remus C3a splitter (CAVE_DR_C3_MAIN): desc byte +3 == 0xE goes to the DR C3 Special Summon stub (CAVE_DR_C3_SS);
 * anything else to the native Deck resolver 0x02207EF4 (reads r0-r3; a2/a3 pass through). */
#include "engine.h"

ENTRY int entry(u8 *d, u32 a1, u32 a2, u32 a3)
{
    if (d[3] == 0xE)
        return slot_CAVE_DR_C3_SS((u32)d, a1);
    return deck_resolver((u32)d, a1, a2, a3);
}

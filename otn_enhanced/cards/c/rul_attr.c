/* Dragon Rulers attribute (CAVE_RUL_ATTR): the Ruler record for this card (CAVE_RUL_KBASE), its attribute =
 * byte +0x23 & 7; 0 if there is no record. */
#include "engine.h"

ENTRY u32 entry(u32 a0)
{
    const u8 *k = (const u8 *)slot_CAVE_RUL_KBASE(a0);
    return k ? k[0x23] & 7 : 0;
}

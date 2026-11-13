/* Shooting Quasar Dragon Extra Deck select (CAVE3_QSR_EXSEL): enumerate side a1's Extra Deck (0x0223BE40, 6 args)
 * for desc's cid with filter 0x0223C6F1. key = desc's signed halfword +2 if > 0, else desc's cid; on the stack
 * desc[+8] and 2. */
#include "engine.h"

ENTRY int entry(const u8 *d, u32 side)
{
    s32 key = *(const s16 *)(d + 2);
    if (key <= 0)
        key = *(const u16 *)d;
    return extra_deck_enum(side, *(const u16 *)d, 0x0223C6F1, &key, *(const u32 *)(d + 8), 2);
}

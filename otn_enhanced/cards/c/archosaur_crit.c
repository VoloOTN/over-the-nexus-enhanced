/* Animadorned Archosaur criteria (CAVE_ARCH_CRIT): walk side a1's Deck (0x0223BC3C, 6 args) for desc's cid with
 * filter 0x023A2AF1, no key (r3 = NULL), and on the stack desc[+8] and 2. */
#include "engine.h"

ENTRY int entry(const u8 *d, u32 side)
{
    return deck_walker(side, *(const u16 *)d, 0x023A2AF1, 0, *(const u32 *)(d + 8), 2);
}

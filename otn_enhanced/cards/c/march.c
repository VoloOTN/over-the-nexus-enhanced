/* March of the Monarchs (Continuous Spell, donor Kishido Spirit 0x15EC).
 *   "Tribute Summoned monsters you control cannot be targeted by, or destroyed by, card effects. You cannot Special Summon monsters from the Extra Deck."
 * This leaf answers "does March protect the monster at (side, zone)?": a face-up monster whose zone flag word has bit 3 (Tribute Summoned, measured in CPU duels
 * 2026-11-10: 0x410108 -> 0x108 on Level 5-6 Tribute Summons, clear on Level <= 4 Normal and on Special Summons), while its controller has a face-up March in the
 * Spell/Trap zones 5..9.  Callers: the effect-destruction survive-check front and the targeting-link front (cards/march.py). */
#include "disguise.h"

#define MARCH        0x15EC
#define ZONE_FLAGS(s, z)  (*(volatile u32 *)(ZONE_REC(s, z) + 0x10))      /* zone word + 0x44 */
#define TRIBUTE_SUMMONED  0x8

ENTRY int entry(u32 side, u32 zone)
{
    u32 z;
    if (zone > 4 || !ZONE_FACEUP(side, zone))
        return 0;
    if (!CID(ZONE_WORD(side, zone)))
        return 0;
    if (!(ZONE_FLAGS(side, zone) & TRIBUTE_SUMMONED))
        return 0;
    for (z = 5; z <= 9; z++) {
        if (ZONE_FACEUP(side, z) && CID(ZONE_WORD(side, z)) == MARCH)
            return 1;
    }
    return 0;
}

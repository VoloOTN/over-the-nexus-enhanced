/* Extra Deck Special Summon lock: "does side currently have a card that says 'You cannot Special Summon monsters from the Extra Deck'?"
 * March of the Monarchs (0x15EC) face-up in side's Spell/Trap zones 5..9, OR The Monarchs Stormforth (0x1328) activated by side this turn (a kind-1 turn-log node
 * posted by its cost; cleared at the end of the turn, like every kind-1 HOPT node).  Return of the Monarchs (0x14A1) face-up joined 2026-11-10.
 * Callers (cards/march.py, cards/stormforth.py): the is_synchro / is_fusion tests inside can_synchro_summon / can_fusion_summon and the SS engine's free-zone check. */
#include "disguise.h"

#define MARCH 0x15EC
#define RETURN 0x14A1
#define STORMFORTH 0x1328
#define REVOLT_LOCK 0x5DCD                               /* kind-1 turn-log key (donor Short Circuit 0x1DCD | 0x4000) */
#define TLQ ((int (*)(u32, u32, u32, u32))0x021A14E9)     /* turn-log query (side, 0xB, key, kind) -> nonzero if posted this turn */

/* Domain of the True Monarchs (0x10F3, Field zone 10): locks the OPPONENT of its controller while that controller has an empty Extra Deck and is the only player
 * that controls a face-up Tribute Summoned monster (zone flag word bit 3). */
#define DOMAIN 0x10F3
#define ZONE_FLAGS(s, z)  (*(volatile u32 *)(ZONE_REC(s, z) + 0x10))
static int has_tribute_summoned(u32 s)
{
    u32 z;
    for (z = 0; z <= 4; z++) {
        if (ZONE_FACEUP(s, z) && CID(ZONE_WORD(s, z)) && (ZONE_FLAGS(s, z) & 0x8))
            return 1;
    }
    return 0;
}

ENTRY int entry(u32 side)
{
    u32 z, opp = (side & 1) ^ 1;
    if (ZONE_FACEUP(opp, 10) && CID(ZONE_WORD(opp, 10)) == DOMAIN && *(volatile u32 *)(PLAYER(opp) + 0x18) == 0
        && has_tribute_summoned(opp) && !has_tribute_summoned(side))
        return 1;
    for (z = 5; z <= 9; z++) {
        if (ZONE_FACEUP(side, z) && (CID(ZONE_WORD(side, z)) == MARCH || CID(ZONE_WORD(side, z)) == RETURN))
            return 1;
    }
    if (TLQ(side, 0xB, REVOLT_LOCK, 1))                /* The Monarchs Revolt: posted when it resolves, "for the rest of this turn" */
        return 1;
    return TLQ(side, 0xB, STORMFORTH, 1) != 0;
}

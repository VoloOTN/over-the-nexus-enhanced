/* Thestalos the Mega Monarch (0x127B, donor Red Archery Girl) cls1 +04.  A clone of Thestalos the Firestorm Monarch's resolver 0x0221D150 (phase 0x80: the
 * opponent's hand is looked at and one card discarded through 0x022599C8; phase 0x7F: Monster Card -> original Level x 100 damage) with Level x 200, plus the
 * Mega's FIRE rider: "Tribute Summoned by Tributing a FIRE monster: also inflict 1000 damage after that".  The FIRE latch is mega_monarch's CAVE_MM_FLAG (bit = 1 << Attribute,
 * set by the Tribute-payment capture front; FIRE = 4).  Build with -DFLAG=<CAVE_MM_FLAG address>.  Design: notes/thestalos-mega-findings.md. */
#include "disguise.h"

#define STATE         0x0229AAFC          /* +0x70 resolver phase */
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define PICK_INDEX    (*(volatile u16 *)(0x0229DE94 + 6))     /* the discarded card's index in the global card table, read by the native phase 0x7F */
#define CARD_TABLE(i) (*(volatile u32 *)(0x0229C33C + (i) * 8))
#define FIRE_BIT      (1u << 4)

typedef void (*fn3)(u32, u32, u32);
typedef int (*fn3i)(u32, u32, u32);
#define LOOK_AND_DISCARD ((fn3)0x022599C8)    /* (opponent side, 1, 1): show the hand, pick 1 to discard */
#define DAMAGE           ((fn3i)0x021CFBC8)   /* (desc, side to hurt, amount) */

ENTRY int entry(EffectCtx *e)
{
    u32 phase = *(volatile u32 *)(STATE + 0x70);
    u32 opp = 1 - e->controller;
    if (phase == 0x80) {
        if (HAND_COUNT(opp) == 0)
            return 0;
        LOOK_AND_DISCARD(opp, 1, 1);
        return 0x7F;
    }
    if (phase == 0x7F) {
        u32 cid = CARD_TABLE(PICK_INDEX) & 0x3FFF;
        volatile u32 *latch = (volatile u32 *)FLAG;
        if (is_monster(cid))
            DAMAGE((u32)e, opp, cid_level(cid) * 200);
        if (*latch & FIRE_BIT) {
            *latch = 0;
            DAMAGE((u32)e, opp, 1000);
        }
        return 0;
    }
    return 0;
}

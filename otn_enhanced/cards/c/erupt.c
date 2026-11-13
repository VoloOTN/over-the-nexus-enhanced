/* The Monarchs Erupt (Continuous Trap, donor Respect Play 0x135E).  Build with -DSTUB=ER_COND|ER_TEST.
 *   "Activate this card only if you have no cards in your Extra Deck and control a Tribute Summoned monster. Negate the effects of all face-up
 *    monsters on the field, while those monsters are face-up on the field, except Tribute Summoned monsters'. ..."
 * Tribute Summoned = zone flag word (zone word + 0x44 - 0x34) bit 3 (measured in CPU duels 2026-11-10, march.c).  Extra Deck count = player + 0x18.
 * Design + proofs: notes/erupt-findings.md. */
#include "disguise.h"

#define ER_COND 1
#define ER_TEST 2
#define ER_EP   3

#define ERUPT             0x135E
#define ZONE_FLAGS(s, z)  (*(volatile u32 *)(ZONE_REC(s, z) + 0x10))      /* zone word + 0x44 */
#define TRIBUTE_SUMMONED  0x8
#define ED_COUNT(side)    (*(volatile u32 *)(PLAYER(side) + 0x18))

static inline int is_tribute_summoned(u32 side, u32 zone)
{
    return ZONE_FACEUP(side, zone) && CID(ZONE_WORD(side, zone)) && (ZONE_FLAGS(side, zone) & TRIBUTE_SUMMONED);
}

#if STUB == ER_COND
/* cls0 +0C: E1, own Extra Deck empty and an own face-up Tribute Summoned monster. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, z;
    (void)a1;
    if (ED_COUNT(side))
        return 0;
    for (z = 0; z <= 4; z++) {
        if (is_tribute_summoned(side, z))
            return 1;
    }
    return 0;
}

#elif STUB == ER_EP
/* E3: replaces the fn of End-Phase registry row 277 {0x02255959, cid 0} (the generic maintenance walker).  Section walker 0x022566F8 calls
 * fn(side, cid) once per pass; 0 = call again, nonzero = done.  Pass 0 ([0x0229DD94] = 0, [0x0229AB7C+0x18] = 0) is the turn player's.
 * During the turn player's pass: a face-up own Erupt and no own face-up Tribute Summoned monster -> queue it to the GY (0x021CF6B8, NAST's send;
 * the move runs after we return 0, like the walker's own maintenance destroy) and ask to be called again.  Everything else: the native walker. */
#define WALKER   ((int (*)(u32, u32))0x02255959)
#define SEND_GY  ((void (*)(void *, u32, u32))0x021CF6B9)
#define TURN     (*(volatile u32 *)(0x0229DD14 + 0x34))
#define TOGGLE   (*(volatile u32 *)0x0229DD94)
#define ROUND2   (*(volatile u32 *)(0x0229AB7C + 0x18))
#define PENDING  (*(volatile u32 *)(0x0229C294 + 0x7C))

ENTRY int entry(u32 side, u32 cid)
{
    u32 z, d[9];
    if (cid == 0 && side == TURN && TOGGLE == 0 && ROUND2 == 0) {
        for (z = 0; z <= 4; z++) {
            if (is_tribute_summoned(side, z))
                return WALKER(side, cid);
        }
        for (z = 5; z <= 9; z++) {
            if (ZONE_FACEUP(side, z) && CID(ZONE_WORD(side, z)) == ERUPT && !(PENDING & (1u << ((side & 1) * 16 + z)))) {
                for (cid = 0; cid < 9; cid++)
                    d[cid] = 0;
                d[0] = ERUPT | ((side & 1) << 16) | (5u << 24);   /* {cid, side, 5 = not a monster} as 0x021CF31C builds it */
                d[1] = 0x24;
                SEND_GY(d, side & 1, z);
                return 0;
            }
        }
        cid = 0;
    }
    return WALKER(side, cid);
}

#elif STUB == ER_TEST
/* E2: (side, zone) -> 1 if a face-up Erupt negates the monster there (face-up, not Tribute Summoned).  Called after the native 0x021EE3DC said 0. */
ENTRY int entry(u32 side, u32 zone)
{
    u32 s, z;
    side &= 1;
    if (zone > 4 || !ZONE_FACEUP(side, zone) || !CID(ZONE_WORD(side, zone)))
        return 0;
    if (ZONE_FLAGS(side, zone) & TRIBUTE_SUMMONED)
        return 0;
    for (s = 0; s <= 1; s++) {
        for (z = 5; z <= 9; z++) {
            if (ZONE_FACEUP(s, z) && CID(ZONE_WORD(s, z)) == ERUPT)
                return 1;
        }
    }
    return 0;
}
#endif

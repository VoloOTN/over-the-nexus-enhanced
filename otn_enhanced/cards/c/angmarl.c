/* Angmarl the Fiendish Monarch (0x14D8, donor The Dragon Dwelling in the Cave).  Build with -DSTUB=AG_COND|AG_COST|AG_RES -DDATA=<ov5 data address>.
 *   "When this card is Tribute Summoned: You can banish 1 Spell Card from your Graveyard; add 1 card with the same name as the banished Spell Card from your Deck to your hand."
 * cls1 {+04 RES, +0C COND, +10 the native "You can" prompt, +14 COST}.  COST drives the native banish cost 0x021E5319 (Survival Instinct's: criteria row -> GY picker ->
 * banish exactly 1 for an unlisted cid) over the virtual GY row 0xFF90 (word 0x4 = Spell); RES remembers the cid just banished (last entry of the banished list), then runs
 * the native Deck -> hand resolver over the virtual Deck row 0xFF91 whose predicate keeps only cards with that name.  DATA +0 = the banished cid.
 * Design + UNPROVEN list: notes/angmarl-findings.md. */
#include "disguise.h"

#define AG_COND 1
#define AG_COST 2
#define AG_RES  3

#define STATE          0x0229AAFC          /* +0x70 resolver phase, +0x7C cost step */
#define AG_CID         (*(volatile u32 *)(DATA + 0x0))
#define BAN_COUNT(s)   (*(volatile u32 *)(PLAYER(s) + 0x1C))
#define BAN_CID(s, i)  (*(volatile u32 *)(PLAYER(s) + 0x7B4 + 4 * (i)) & 0x3FFF)
#define SPELL_CARD     13                  /* 0x0202ABF8's card_type >> 1: Spell Card (27 >> 1) */

typedef int (*fn2)(u32, u32);
typedef int (*fn1)(u32);
#define BANISH_COST   ((fn2)0x021E5319)    /* Survival Instinct's cost: pick from the GY by the criteria row, banish it */
#define DECK_TO_HAND  ((fn2)0x02207EF5)    /* native Deck -> hand resolver */
#define CARD_TYPE     ((fn1)0x0202ABF9)

#if STUB == AG_COND
/* +0C: a Spell Card in your Graveyard (the cost's only requirement).  >= 2 = activatable unconditionally. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n = GY_COUNT(side);
    for (i = 0; i < n; i++) {
        u32 cid = GY_CID(side, i);
        if (cid && CARD_TYPE(cid) == SPELL_CARD)
            return 2;
    }
    return 0;
}

#elif STUB == AG_COST
/* +14 (after the "You can" prompt said yes): the native banish cost.  0 = pending, 1 = done, < 0 = abort (the picker was cancelled). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    return BANISH_COST((u32)e, a1);
}

#elif STUB == AG_RES
/* +04: phase 0x80 first remembers the cid that was just banished; every phase then runs the native Deck -> hand resolver. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller, n;
    if (*(volatile u32 *)(STATE + 0x70) == 0x80) {
        n = BAN_COUNT(side);
        AG_CID = n ? BAN_CID(side, n - 1) : 0;
    }
    return DECK_TO_HAND((u32)e, a1);
}

#else
#error "build with -DSTUB=AG_COND|AG_COST|AG_RES -DDATA=<addr>"
#endif

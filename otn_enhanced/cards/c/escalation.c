/* Escalation of the Monarchs (Continuous Trap, donor Enervating Mist 0x1800).  Build with -DSTUB=ES_COND|ES_COST|ES_PRED.
 *   "Once per turn, during your opponent's Main Phase or your opponent's Battle Phase, you can: Immediately after this effect resolves, Tribute Summon 1 monster."
 * cls3 {+04 0x0220D80D (Cry Havoc!'s resolver: the native "Normal Summon from the hand as an effect" machine; it asks 0x0220D7B4(acting cid) for a per-cid hand predicate and then
 *   runs the engine's own summon state machine, which does the Tribute selection), +0C ES_COND, +10 ES_COST (the once-per-turn turn-log node)}.  ES_PRED is that predicate
 *   (a front on 0x0220D7B4's three BL sites hands it out for this cid): a hand monster of Level 5 or higher, mask 0x10 (= "can be Summoned"; 0x40 would be "can be Set").
 * Design + UNPROVEN list: notes/escalation-findings.md. */
#include "disguise.h"

#define ES_COND 1
#define ES_COST 2
#define ES_PRED 3
#define ES_PRED_EH 4

#define ESCALATION    0x1800
#define PHASEBASE     0x0229DD14           /* +0x34 turn player, +0x48 phase (0 Draw, 1 Standby, 2 Main 1, 3 Battle, 4 Main 2, 5 End) */
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_WORD(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)))
#define TURN_PLAYER   (*(volatile u32 *)(PHASEBASE + 0x34))
#define PHASE         (*(volatile u32 *)(PHASEBASE + 0x48))

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
#define CID_LEVEL     ((fn1)0x0202ABD9)    /* (cid) -> printed Level */
#define CAN_SUMMON    ((fn2)0x0225D6D5)    /* (side, card ref) -> 0x10 when that hand card can be Summoned right now (Tributes included) */

static inline u32 ref_of(u32 w)
{
    return (((w << 1) >> 24) << 1) + ((w << 17) >> 31);
}

#if STUB == ES_PRED_EH
/* Ehther E2's hand predicate (the same resolver, keyed on Ehther 0x1312): only Ehther himself, mask 0x10 (Summon). */
ENTRY int entry(u32 side, u32 zone, u32 idx)
{
    if (zone != 0x0B)
        return 0;
    return (HAND_WORD(side & 1, idx) & 0x3FFF) == 0x1312 ? 0x10 : 0;
}

#elif STUB == ES_PRED
/* r7(side, zone, index) from the native resolver: only hand cards (zone 0xB) of Level 5 or higher count; everything else 0. */
ENTRY int entry(u32 side, u32 zone, u32 idx)
{
    if (zone != 0x0B)
        return 0;
    return CID_LEVEL(HAND_WORD(side & 1, idx) & 0x3FFF) >= 5 ? 0x10 : 0;
}

#elif STUB == ES_COND
/* cls3 +0C: once per turn, during the OPPONENT's Main or Battle Phase, with a hand monster that can be Tribute Summoned right now. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, i, n;
    if (e->cost_ran)
        return 2;
    if (TURN_PLAYER == side)
        return 0;
    if (PHASE < 2 || PHASE > 4)
        return 0;
    if (opt_used(e, ESCALATION))
        return 0;
    n = HAND_COUNT(side);
    for (i = 0; i < n; i++) {
        u32 w = HAND_WORD(side, i);
        if (CID_LEVEL(w & 0x3FFF) >= 5 && (CAN_SUMMON(side, ref_of(w)) & 0x10))
            return 2;
    }
    return 0;
}

#elif STUB == ES_COST
/* cls3 +10: stamp the once-per-turn node (kind 1) when the effect is activated. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    turnlog_post(e->controller, ESCALATION, 1, 0);
    return 1;
}

#else
#error "build with -DSTUB=ES_COND|ES_COST|ES_PRED"
#endif

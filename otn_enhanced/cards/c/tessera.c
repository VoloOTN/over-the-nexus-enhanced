/* Tessera the Primal Squire (0x1123, donor Toon Alligator).  Build with -DSTUB=TS_COND3|TS_COST3|TS_RES3|TS_COND|TS_RES.
 *   T1 "You can reveal 1 "Monarch" Spell/Trap in your hand; Special Summon this card from your hand."           -- NOT BUILT (hand-ignition machinery, see notes/tessera-findings.md)
 *   T2 "During your Main Phase, you can: Immediately after this effect resolves, Tribute Summon 1 monster."     -- cls3 ignition; grants Double Summon's extra summon (KNOWN DEVIATION)
 *   T3 "If this card is sent to the GY: You can Special Summon 1 monster with 800 ATK/1000 DEF from your Deck, also you cannot Special Summon from the Extra Deck for the rest of this turn."
 *   Each effect once per turn.
 * T2 = cls3 {RES3, 0, COND3, COST3, 0}: COND = once per turn + the vanilla ignition check 0x021F06E8; COST stamps the node; RES3 posts the kind-1 node of Double Summon (0x1C33).
 * T3 = cls2 leave record {RES, 0, COND, "You can" 0x021E51E5, 0} + a leave-mask row {0x1123, 0x0800}; RES stamps the node and the Extra Deck lock at the first phase, then runs the native Deck
 * Special Summon machine (0x02206CAC; the position is the player's choice) over the virtual Deck row 0xFFD3 (ATK 800 / DEF 1000, any name).
 * Design + UNPROVEN list: notes/tessera-findings.md. */
#include "disguise.h"

#define TS_COND3 1
#define TS_COST3 2
#define TS_RES3  3
#define TS_COND  4
#define TS_RES   5

#define TESSERA   0x1123
#define DOUBLE_SUMMON 0x1C33
#define KEY_OPT2  0x1123                  /* kind-1 turn-log keys (slot 0xB): T2 used / T3 used; the Extra Deck lock reuses Revolt's key (edlock.c tests it) */
#define KEY_OPT3  0x5123
#define KEY_LOCK  0x5DCD
#define STATE     0x0229AAFC

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
#define GATE1       ((fn1)0x021AD871)     /* the native Deck-SS machine's three Special Summon gates (nonzero = allowed) */
#define GATE2       ((fn1)0x021B9ECD)
#define GATE3       ((fn1)0x021B9ED9)
#define DECK_SS_RES ((fn2)0x02206CAD)     /* the native 'Special Summon 1 monster from your Deck' machine (Predaplant Ophrys's resolver) */

static inline u32 eff_side(EffectCtx *e) { return (e->controller ^ e->slot_phase) & 1; }

#if STUB == TS_COND3
/* cls3 +0C: once per turn (menu time only), then the vanilla ignition check. */
ENTRY int entry(EffectCtx *e)
{
    if (opt_used(e, KEY_OPT2))
        return 0;
    return can_take_ignition((u32)e);
}

#elif STUB == TS_COST3
/* cls3 +10: stamp the once-per-turn node (cost step 0 only: the cost may be re-entered). */
ENTRY int entry(EffectCtx *e)
{
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, KEY_OPT2, 1, 0);
    return 1;
}

#elif STUB == TS_RES3
/* cls3 +04: post Double Summon's kind-1 node = one extra Normal Summon/Set this turn. */
ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, DOUBLE_SUMMON, 1, 0);
    return 0;
}

#elif STUB == TS_COND
/* cls2 +0C (sent to the GY): once per turn, a legal Special Summon, and an 800/1000 monster in the Deck (the Deck row through the criteria matcher).  2 = unconditional. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = eff_side(e);
    if (opt_used(e, KEY_OPT3))
        return 0;
    if (!GATE1(side) || !GATE2(side) || !GATE3(side))
        return 0;
    if (criteria_count(side, TESSERA, 0, 0) < 1)
        return 0;
    return 2;
}

#elif STUB == TS_RES
/* cls2 +04: stamp the once-per-turn node and the Extra Deck lock at the first phase, then the native Deck Special Summon machine. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (*(volatile u32 *)(STATE + 0x70) == 0x80) {
        turnlog_post(e->controller, KEY_OPT3, 1, 0);
        turnlog_post(e->controller, KEY_LOCK, 1, 0);
    }
    return DECK_SS_RES((u32)e, a1);
}

#else
#error "build with -DSTUB=TS_COND3|TS_COST3|TS_RES3|TS_COND|TS_RES"
#endif

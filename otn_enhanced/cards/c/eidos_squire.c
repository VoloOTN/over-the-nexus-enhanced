/* Eidos the Underworld Squire (0x0FE2, donor Great White).  Build with -DSTUB=ES_COND|ES_RES|ES_COND2|ES_COST2|ES_RES2.
 *   E1 "If this card is Normal or Special Summoned: During your Main Phase this turn, you can Tribute Summon 1 monster, in addition to your Normal Summon/Set.
 *       (You can only gain this effect once per turn.)"
 *   E2 "You can banish this card from your Graveyard, then target 1 monster with 800 ATK and 1000 DEF in your Graveyard, except 'Eidos the Underworld Squire'; Special Summon it in
 *       Defense Position, also you cannot Special Summon monsters from the Extra Deck for the rest of this turn.  You can only use this effect of 'Eidos the Underworld Squire' once per turn."
 * E1 = cls1 {RES, 0, COND, 0, 0} (a mandatory trigger on the shared N-or-SS hook); RES posts the kind-1 node of DOUBLE SUMMON (0x1C33), the engine's granter-free "Normal Summon 1 monster in
 * addition" grant (ns_counter 0x021B9514).  KNOWN DEVIATION: the grant is not restricted to Tribute Summons and is not "immediate".
 * E2 = cls2 GY ignition {Premature Burial's family resolver 0x02207529 via RES2, 0, COND2, COST2, 0x02235605} + a virtual GY-action row; the Defense Position comes from the POS front.
 * Design + UNPROVEN list: notes/eidos-squire-findings.md. */
#include "disguise.h"

#define ES_COND  1
#define ES_RES   2
#define ES_COND2 3
#define ES_COST2 4
#define ES_RES2  5

#define EIDOS     0x0FE2
#define DOUBLE_SUMMON 0x1C33
#define KEY_OPT1  0x0FE2                  /* kind-1 turn-log keys (slot 0xB): E1 gained this turn / E2 used; the Extra Deck lock reuses Revolt's key (edlock.c tests it) */
#define KEY_OPT2  0x5FE2
#define KEY_LOCK  0x5DCD
#define STATE     0x0229AAFC

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
#define PB_RESOLVER  ((fn2)0x02207529)    /* Premature Burial / Call of the Haunted / Soul Resurrection: Special Summon the targeted GY monster */
#define PB_COND      ((fn2)0x021F03B5)    /* their cond: a free zone + a GY candidate through the criteria row */
#define SELF_BANISH  ((fn1)0x021E5709)

#if STUB == ES_COND
/* cls1 +0C: gain the extra summon once per turn.  2 = unconditional. */
ENTRY int entry(EffectCtx *e)
{
    return opt_used(e, KEY_OPT1) ? 0 : 2;
}

#elif STUB == ES_RES
/* cls1 +04: stamp the once-per-turn node and post Double Summon's node (kind 1 = the grant is available). */
ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, KEY_OPT1, 1, 0);
    turnlog_post(e->controller, DOUBLE_SUMMON, 1, 0);
    return 0;
}

#elif STUB == ES_COND2
/* cls2 +0C: once per turn clear, then the native GY-Special-Summon condition (a free zone and an 800/1000 candidate in the GY, through the virtual row). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (opt_used(e, KEY_OPT2))
        return 0;
    return PB_COND((u32)e, a1);
}

#elif STUB == ES_COST2
/* cls2 +10: the native self-banish, then the once-per-turn node (cost step 0 only: the cost may be re-entered). */
ENTRY int entry(EffectCtx *e)
{
    int r = SELF_BANISH((u32)e);
    if (r > 0)
        turnlog_post(e->controller, KEY_OPT2, 1, 0);
    return r;
}

#elif STUB == ES_RES2
/* cls2 +04: the Extra Deck lock at the first phase (nothing in the Extra Deck is summoned by this effect), then the native resolver. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (*(volatile u32 *)(STATE + 0x70) == 0x80)
        turnlog_post(e->controller, KEY_LOCK, 1, 0);
    return PB_RESOLVER((u32)e, a1);
}

#else
#error "build with -DSTUB=ES_COND|ES_RES|ES_COND2|ES_COST2|ES_RES2"
#endif

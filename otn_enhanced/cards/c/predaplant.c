/* Predaplant Darlingtonia Cobra (0x0FED) + Predaplant Ophrys Scorpio (0x17CF). Build with -DSTUB=D_COND|D_COST|O_COND|O_COST|O_RES.
 * Defines supplied by cards/predaplant.py: PROBE (ov5 data byte), plus the keys below.
 * Notes / proofs: notes/predaplant-darlingtonia-ophrys-findings.md.  Every claim marked ASSUMED there is untested in-game. */
#include "engine.h"

#define D_COND 1
#define D_COST 2
#define O_COND 3
#define O_COST 4
#define O_RES  5

#define SLOT        0x0B              /* turn-log slot used by every cid-keyed log post (disguise.h TURNLOG_SLOT) */
#define KEY_O       0x57CF              /* Ophrys: once per turn (cid-keyed: the printed OPT covers every copy)      */
#define KEY_ARM     0x7FED              /* Ophrys resolver stamps this (kind 1, this turn): "an Ophrys is summoning"  */
#define KEY_D       0x0FED              /* Darlingtonia: once per DUEL (kind 5 is never swept, dispatch.turnlog_once_per_duel) */
#define SUMMON_DESC 0x02298A28          /* summon.descriptor_0x02298A28: +0x0A = source zone (0x0B hand, 0x0D Deck, 0x0E GY)   */
#define STATE       0x0229AAFC          /* +0x70 resolver phase, +0x7C cost step                                       */
#define PLAYER(s)   (0x0229AC94 + ((s) & 1) * 0xB3C)

typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
#define HAS_CANDIDATE ((fn2)0x021F0821)  /* Shadow Mist's have_target: candidate count of rel 0               */
#define PROBE_FN      ((fn3)0x02243FE1)  /* (side, cid, hand index) candidate probe 0x02243FE0 (Upstart)       */
#define HAND_COST     ((fn2)0x021E7245)  /* native "send N from hand", N = 1 for the default arm               */
#define DECK_SS_RES   ((fn2)0x02206CAD)  /* counter.deck_ss_resolver                                           */

#if STUB == D_COND
/* Darlingtonia cls1 +0C: per-Duel clear, an Ophrys stamped this turn, the summon came FROM THE DECK, a target exists. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    if (turnlog_query(d[2], SLOT, KEY_D, 5))
        return 0;
    if (!turnlog_query(d[2], SLOT, KEY_ARM, 1))
        return 0;
    if (*(volatile u16 *)(SUMMON_DESC + 0x0A) != 0x0D)
        return 0;
    return HAS_CANDIDATE((u32)e, a1);
}

#elif STUB == D_COST
/* Darlingtonia cls1 +14 (after the native "You can" prompt said yes): stamp the per-Duel use. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    turnlog_post(e->controller, KEY_D, 5, 0);
    return 1;
}

#elif STUB == O_COND
/* Ophrys cls1 +0C (Upstart Golden Ninja's scan, adapted): OPT clear, a monster in hand (rel 1 probed per hand slot with the
 * PROBE byte raised so the shared row hook hands out rel 1), and a Deck target (rel 0). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    u32 side = (d[2] ^ d[6]) & 1;
    u32 n, i;
    int found = 0;
    volatile u8 *probe = (volatile u8 *)PROBE;
    if (turnlog_query(d[2], SLOT, KEY_O, 1))
        return 0;
    n = *(volatile u32 *)(PLAYER(side) + 0x0C);        /* hand count, ram.container_for_zone_code */
    for (i = 0; i < n; i++) {
        *probe = 1;
        found = PROBE_FN(side, e->cid, i);
        *probe = 0;
        if (found)
            break;
    }
    if (!found)
        return 0;
    return HAS_CANDIDATE((u32)e, a1);
}

#elif STUB == O_COST
/* Ophrys cls1 +14: stamp the OPT once (cost step 0, the activation moment), then the native hand send. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, KEY_O, 1, 0);
    return HAND_COST((u32)e, a1);
}

#elif STUB == O_RES
/* Ophrys cls1 +04: phase 0x80 stamps "an Ophrys summons" for Darlingtonia's gate, then the native Deck Special Summon. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (*(volatile u32 *)(STATE + 0x70) == 0x80)
        turnlog_post(e->controller, KEY_ARM, 1, 0);
    return DECK_SS_RES((u32)e, a1);
}

#else
#error "build with -DSTUB=D_COND|D_COST|O_COND|O_COST|O_RES"
#endif

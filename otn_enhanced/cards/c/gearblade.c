/* Phoenix Gearblade (0x10EA, donor Invigoration). Facts / design: notes/phoenix-gearblade-findings.md.
 *   C3  cls1 {+04 RES, +0C COND, +10 COST, +14 RET2}: posted by the End-of-Damage-Step walker's ATTACKER-only arm 0x0225225C
 *       (module front @0x02252210), so the equipped monster is the attacker of this battle.
 *       COST = native 'You can' prompt, then send THIS card to the GY with the zeroed-cid mover (a cost send, no tribute bit).
 *       RES  = snapshot: a kind-2 / duration-0 rider keyed 0x10EA on each Warrior / FIRE monster you control (freed by the
 *              end-of-turn sweep); the double-attack tail front (module) reads it.
 * Build with -DSTUB=C3COND|C3COST|C3RES. */
#include "disguise.h"

#define GB        0x10EA
#define ATTR_FIRE 4

#ifdef DBG
#define DBGW(o) (*(volatile u32 *)(DBG + (o)))   /* diagnostic breadcrumb words (module CAVE_PG_DBG) */
#endif
#define KEY_C4    0x50EA         /* C4 hard once-per-turn: posted on Yes by the cost stub (dsl._hopt_you_can_stub) */
#define RES_PHASE (*(volatile u32 *)(0x0229AAFC + 0x70))
#define BAN_COUNT(side)  (*(volatile u32 *)(PLAYER(side) + 0x1C))
#define BAN_CID(side, i) (*(volatile u32 *)(PLAYER(side) + 0x7B4 + 4 * (i)) & 0x3FFF)

#define C3COND 1
#define C3COST 2
#define C3RES  3
#define C4COND 4
#define C4RES  5

#if STUB == C3COND
/* +0C: >= 2 = activatable unconditionally. The post only comes from the attacker arm, so there is nothing else to test;
 * Gearblade itself is still on the field (the event is queued for it). */
ENTRY int entry(EffectCtx *e)
{
    (void)e;
    return 2;
}

#elif STUB == C3COST
/* +10: 'You can' Yes/No (declining is free); on Yes send this card to the GY. cost_settled = the engine replaying a finished
 * cost (Mystic Piper rule): do not run it twice. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r;
    u8 *d = (u8 *)e;
    if (cost_settled((u32)e, 0, 0, 0))
        return 1;
    r = you_can_tag(e, a1);
    if (r == 1)
        send_zeroed_cid((u32)e, d[2], d[3]);
    return r;
}

#elif STUB == C3RES
/* +04: one phase. Your face-up monsters in zones 0..4 that are Warrior (race bit 15) or currently FIRE get the rider. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, z;
    for (z = 0; z <= 4; z++) {
        if (!zone_active(side, z) || !ZONE_FACEUP(side, z))
            continue;
        if (race_bit_test(side, z, RACE_WARRIOR) || (cur_attribute(side, z, 0) & 7) == ATTR_FIRE)
            rider_attach(side, z, GB, KIND_UNTIL_EP, 0);
    }
    return 0;
}
#elif STUB == C4COND
/* C4 cls2 +0C: hard once-per-turn clear (menu time) and THIS card is in its controller's GY or banished pile. 2 = unconditional. */
/* The leave event is posted from INSIDE the move (the card may not be in its destination list yet), so the pile scan is NOT done here:
 * only the hard OPT is tested; the resolver (phase 0x80, later) re-finds the card in the GY / banished pile and does nothing if absent. */
ENTRY int entry(EffectCtx *e)
{
    int used = opt_used(e, KEY_C4);
    int r = used ? 0 : 2;
#ifdef DBG
    DBGW(0x24) = DBGW(0x24) + 1;            /* cond calls */
    DBGW(0x28) = (u32)r;                    /* last verdict */
    DBGW(0x34) = e->controller;             /* side the cond was asked for */
    DBGW(0x1C) = used;                      /* opt_used result */
    DBGW(0x38) = GY_COUNT(e->controller);   /* GY count at cond time */
    DBGW(0x3C) = BAN_COUNT(e->controller);  /* banished count at cond time */
#endif
    return r;
}

#elif STUB == C4RES
/* C4 cls2 +04, the native add-target protocol (0x02208180): phase 0x80 opens the chain context, moves the card, returns 0x7F;
 * phase 0x7F closes it and returns 0.  The mover wants a POINTER to the card word inside its list (KB gy_to_hand / ban_to_hand). */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n;
#ifdef DBG
    DBGW(0x2C) = DBGW(0x2C) + 1;            /* resolver calls */
    DBGW(0x30) = RES_PHASE;                 /* last phase */
#endif
    if (RES_PHASE != 0x80) {
        chain_close();
        return 0;
    }
    chain_open();
    n = GY_COUNT(side);
    for (i = 0; i < n; i++) {
        if (GY_CID(side, i) == GB) {
            gy_to_hand((u32)e, side, PLAYER(side) + 0x55C + 4 * i);
            return 0x7F;
        }
    }
    n = BAN_COUNT(side);
    for (i = 0; i < n; i++) {
        if (BAN_CID(side, i) == GB) {
            ban_to_hand((u32)e, side, PLAYER(side) + 0x7B4 + 4 * i);
            return 0x7F;
        }
    }
    chain_close();
    return 0;
}
#else
#error "build with -DSTUB=C3COND|C3COST|C3RES|C4COND|C4RES"
#endif

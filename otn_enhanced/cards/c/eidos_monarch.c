/* Eidos the Underworld Monarch (0x1230, donor Whiptail Crow).  Build with -DSTUB=EM_COND|EM_COST|EM_COND3|EM_COST3|EM_RES3.
 *   E1 "If this card is Normal or Special Summoned: You can add 1 "Monarch" Spell/Trap or 1 monster with 2800 ATK/1000 DEF from your Deck or GY to your hand."
 * cls1 {native Deck -> hand 0x02207EF5, 0, COND, "You can" 0x021E51E5, COST} on the shared N-or-SS hook.  BUILT: the DECK half only (the native Deck -> hand resolver cannot move a GY card).
 * E2 (declare an Attribute) and E3 (GY recursion on a Tribute Summon) are NOT built.  Notes: notes/eidos-monarch-findings.md. */
#include "disguise.h"

#define EM_COND 1
#define EM_COST 2
#define EM_COND3 3
#define EM_COST3 4
#define EM_RES3  5

#define EIDOS_M   0x1230
#define KEY_OPT1  0x1230
#define KEY_OPT2  0x5230
#define GENEX     0x2167                  /* Genex Ally Changer: the attribute riders are keyed by its cid (cur_attribute 0x021B8E48 arm 0x021B90B6) */
#define STATE     0x0229AAFC
typedef int (*fn4)(u32, u32, u32, u32);
#define POST_RIDER ((fn4)0x02207909)       /* (desc, kind | duration << 4, param, 0): attach a rider keyed by desc cid to the desc target */

/* 2026-11-12: E1 GY half + E3 */
#define EM_GYH    6
#define EM_RES1   7
#define EM_POST   8
#define EM_COND3G 9
#define EM_RES3G  10
#define KEY_OPT3  0x9230
typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn6)(u32, u32, u32, u32, u32, u32);
typedef int (*fn7)(u32, u32, u32, u32, u32, u32, u32);
#define RES_PHASE     (*(volatile u32 *)(STATE + 0x70))
#define GYW(s, i)     (*(volatile u32 *)(PLAYER(s) + 0x55C + 4 * (i)))
#define ZFLAGS(s, z)  (*(volatile u32 *)(0x0229ACD8 + ((s) & 1) * 0xB3C + (z) * 0x14))   /* zone flag word: bit 3 = Tribute Summoned */
#define SUM_SIDE      (*(volatile u16 *)(0x02298A28 + 0x2))   /* the summon record the summon dispatch 0x02265CF8 reads (r4): +2 side, +4 zone, +0xE cid */
#define SUM_ZONE      (*(volatile u16 *)(0x02298A28 + 0x4))
#define SUM_CID       (*(volatile u16 *)(0x02298A28 + 0xE))
#define PICK_LIST     0x02299458
#define PICK_ZONE     0x02299908
#define PICK_COUNT    (*(volatile u32 *)(0x0229DD94 + 0x34))
#define MENU_ANSWER   (*(volatile u32 *)(0x0229DD94 + 0x34))
#define COUNT_FILL    ((fn3)0x02243FA9)
#define OPEN_PICKER   ((fn4)0x0219C431)
#define PICK_FETCH    ((u32 *(*)(u32))0x0219C94D)
#define DECK_WALK     ((fn6)0x0223BC3D)            /* (side, cid, cb, &aux, word, 2) */
#define GY_ENUM       ((fn6)0x0223C4E9)            /* (side, cid, cb, &aux, word, 0x10000 = plain GY) */
#define GY2HAND       ((fn3)0x021C7039)            /* (desc, side, &GY word) */
#define DECK2HAND     ((fn2)0x021C72CD)            /* (side, &card word): the native add-to-hand resolver's Deck -> hand mover */
#define SHUFFLE       ((fn1)0x021D269D)
#define CHAIN_OPEN    ((int (*)(void))0x021D28A5)
#define CHAIN_CLOSE   ((int (*)(void))0x021D2965)
#define GY_POST       ((fn4)0x021D3649)            /* (side, cid, code, word): post to every copy of cid in that player's GY */
#define ATK_GET       ((fn1)0x0202AC49)
#define DEF_GET       ((fn1)0x0202AC29)
#define MENU          ((fn7)0x0219ABB5)
#define SS_ROOM       ((fn2)0x021B9EC1)
#define GY_SELF_SS    ((fn2)0x0220731D)

#if STUB == EM_COND
/* once per turn, a Deck candidate through the virtual Deck row.  2 = unconditional. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = (e->controller ^ e->slot_phase) & 1;
    if (opt_used(e, KEY_OPT1))
        return 0;
    return criteria_count(side, EIDOS_M, 0, 0) >= 1 ? 2 : 0;
}

#elif STUB == EM_COST
/* after the native "You can" prompt said yes: stamp the node at cost step 0. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, KEY_OPT1, 1, 0);
    return 1;
}

#elif STUB == EM_COND3
/* E2 cls3 +0C: once per turn (menu time), then the vanilla ignition check. */
ENTRY int entry(EffectCtx *e)
{
    if (opt_used(e, KEY_OPT2))
        return 0;
    return can_take_ignition((u32)e);
}

#elif STUB == EM_COST3
ENTRY int entry(EffectCtx *e)
{
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, KEY_OPT2, 1, 0);
    return 1;
}

#elif STUB == EM_RES3
/* E2 cls3 +04: Genex Ally Changer's attribute rider on the selected monster with the declared Attribute (desc +0x16, stored by his selector 0x02236ECD), KIND 3 = permanent (no duration printed). */
ENTRY int entry(EffectCtx *e)
{
    u16 *cid = (u16 *)e;
    u32 attr = *(volatile u16 *)((u8 *)e + 0x16);
    *cid = GENEX;
    POST_RIDER((u32)e, 3, attr, 0);
    *cid = EIDOS_M;
    return 0;
}

#elif STUB == EM_GYH
/* E1 row 0xFFD4 handler (row r0, side r1), 2026-11-12: Deck AND GY candidates ("from your Deck or GY") with the Monarch / 2800-1000 predicate (PRED_ADDR). */
ENTRY int entry(u32 *row, u32 side)
{
    u32 aux = 0, cid = *(u16 *)row, word = row[2];
    return DECK_WALK(side, cid, PRED_ADDR, (u32)&aux, word, 2) + GY_ENUM(side, cid, PRED_ADDR, (u32)&aux, word, 0x10000);
}

#elif STUB == EM_RES1
/* E1 cls1 +04 (replaces the Deck-only native 0x02207EF5): 0x80 list picker over row 0xFFD4 (Deck + GY), 0x7F move the pick to the hand -- a GY card with the GY -> hand
 * mover 0x021C7038 (pointer into the GY list), a Deck card with the native search's own Deck -> hand mover 0x021C72CC -- 0x64 shuffle the Deck (Deck picks only). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, *p, w, zc, i, n;
    (void)a1;
    switch (RES_PHASE) {
    case 0x80:
        if (COUNT_FILL(side, EIDOS_M, 0) <= 0)
            return 0;
        OPEN_PICKER(side, 7, EIDOS_M, 0);
        return 0x7F;
    case 0x7F:
        if ((s32)PICK_COUNT <= 0)
            return 0;
        p = PICK_FETCH(1);
        w = *p;
        zc = *(volatile u16 *)(PICK_ZONE + 2 * (((u32)p - PICK_LIST) >> 2));
        if (((zc >> 1) & 0x1F) == 0xE) {
            n = GY_COUNT(side);
            for (i = 0; i < n; i++)
                if (GYW(side, i) == w) {
                    CHAIN_OPEN();
                    GY2HAND((u32)e, side, (u32)&GYW(side, i));
                    CHAIN_CLOSE();
                    break;
                }
            return 0;
        }
        CHAIN_OPEN();
        DECK2HAND(side, (u32)p);
        CHAIN_CLOSE();
        return 0x64;
    case 0x64:
        SHUFFLE(side);
        return 0;
    default:
        return 0;
    }
}

#elif STUB == EM_POST
/* E3 poster, called from the summon-dispatch front (CAVE_EM_TRIGF) for a Normal-type summon event (r6 == 7) with r0 = the event ctx (r7): when the monster just summoned
 * was TRIBUTE Summoned (zone flag bit 3) and is printed 2400+ ATK / 1000 DEF, post the event to the summoner's Eidos copies in the GY (0x021D3648, Assault Synchron's GY
 * poster).  Printed ATK / DEF (cid getters): KNOWN GAP versus current values, as for every Monarch card. */
ENTRY void entry(u32 ctx)
{
    u32 side = SUM_SIDE & 1, z = SUM_ZONE, cid = SUM_CID;
    if (z > 4 || !(ZFLAGS(side, z) & 8))
        return;
    if (DEF_GET(cid) != 1000 || (s32)ATK_GET(cid) < 2400)
        return;
    GY_POST(side, EIDOS_M, 7, ctx);
}

#elif STUB == EM_COND3G
/* E3 virtual cls2 (GY) +0C: in the GY, once per turn (key 0x9230), the summon that posted it is still an own Tribute Summon of a 2400+/1000 monster. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, z = SUM_ZONE, cid = SUM_CID;
    if (e->cost_ran)
        return 2;
    if (e->race != 0xE || opt_used(e, KEY_OPT3))
        return 0;
    if ((SUM_SIDE & 1) != side || z > 4 || !(ZFLAGS(side, z) & 8) || DEF_GET(cid) != 1000 || (s32)ATK_GET(cid) < 2400)
        return 0;
    return 2;
}

#elif STUB == EM_RES3G
/* E3 +04: 0x80 stamp the once-per-turn key, menu "Add it to your hand." / "Special Summon it." (dlg ids L_HAND / L_SS; the second only with a free Monster Zone);
 * 0x7F answer 0 -> GY -> hand (0x021C7038 on this card's GY entry, found by its instance ref desc[+0xC]); answer 1 -> the native GY self-SS resolver 0x0220731D (position: the
 * player chooses, nothing printed). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, ref, i, n, w;
    switch (RES_PHASE) {
    case 0x80:
        turnlog_post(side, KEY_OPT3, 1, 0);
        MENU((u32)e, 0x103, L_HAND, SS_ROOM(side, 0) ? L_SS : 0, 0, 0, SS_ROOM(side, 0) ? 3 : 1);
        return 0x7F;
    case 0x7F:
        if (MENU_ANSWER == 1)
            return GY_SELF_SS((u32)e, a1);
        ref = *(volatile u16 *)((u8 *)e + 0xC);
        n = GY_COUNT(side);
        for (i = 0; i < n; i++) {
            w = GYW(side, i);
            if ((((w << 1) >> 24) << 1) + ((w << 17) >> 31) == ref) {
                CHAIN_OPEN();
                GY2HAND((u32)e, side, (u32)&GYW(side, i));
                CHAIN_CLOSE();
                break;
            }
        }
        return 0;
    default:
        return 0;
    }
}

#else
#error "build with -DSTUB=EM_COND|EM_COST|EM_COND3|EM_COST3|EM_RES3|EM_GYH|EM_RES1|EM_POST|EM_COND3G|EM_RES3G"
#endif

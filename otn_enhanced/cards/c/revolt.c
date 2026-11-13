/* The Monarchs Revolt (0x1DCD, donor Short Circuit).  Build with -DSTUB=RV_COND|RV_COST|RV_RES|RV_COND2|RV_COST2|RV_RES2 -DDATA=<ov5 data address>.
 *   C1 (Normal Spell): "Discard 1 card; reveal 3 monsters from your Deck, with 2400 or more ATK and 1000 DEF, and/or 800 ATK/1000 DEF, your opponent chooses 1 for you to add to your
 *       hand, and you send the rest to the GY, also for the rest of this turn after this card resolves, you cannot Special Summon from the Extra Deck."
 *   C2 (Graveyard): "You can banish this card from your GY; Special Summon 1 monster with 800 ATK/1000 DEF from your hand."  Each effect once per turn.
 * cls0 {RES, 0, COND, COST (native hand-pick cost 0x021E4EED, then the once-per-turn node), 0}; cls2 {native hand-SS resolver 0x0220667D via RES2, 0, COND2, COST2, 0}.
 * RES = Painful Choice's resolver 0x0220E41C phase for phase with 3 picks (picker code 9) over the Deck row 0xFFC1, the opponent choosing, the other 2 sent to the GY
 * (0x021D2148 with count 2), then the Extra Deck lock node is posted.  DATA +0 = the criteria "mode" read by the H2 front (0 = Deck row, 1 = hand 800/1000 row).
 * Design + UNPROVEN list: notes/revolt-findings.md. */
#include "disguise.h"

#define RV_COND  1
#define RV_COST  2
#define RV_RES   3
#define RV_COND2 4
#define RV_COST2 5
#define RV_RES2  6

#define REVOLT       0x1DCD
#define KEY_OPT1     0x1DCD               /* kind-1 turn-log keys (slot 0xB): effect 1 used / Extra Deck lock / effect 2 used */
#define KEY_LOCK     0x5DCD
#define KEY_OPT2     0x6DCD
#define STATE        0x0229AAFC
#define MODE         (*(volatile u32 *)(DATA + 0x0))
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_CID(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)) & 0x3FFF)

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn4)(u32, u32, u32, u32);
#define ATK_GET      ((fn1)0x0202AC49)
#define DEF_GET      ((fn1)0x0202AC29)
#define HAND_COST    ((fn2)0x021E4EED)     /* Fabled Valkyrus's hand-pick cost: picker over the hand row, the card goes to the GY from the pick callback */
#define SELF_BANISH  ((fn1)0x021E5709)
#define HAND_SS      ((fn2)0x0220667D)     /* native 'Special Summon 1 monster from your hand' resolver (Ancient Rules / Battle Instinct ...) */
#define CAN_ACT      ((fn1)0x021BA9AD)
#define SHOW_MSG     ((fn2)0x0219A819)
#define PICKER       ((fn4)0x0219C431)     /* (side, code, cid, param): code 9 = pick 3 */
#define SHOW_PICKS   ((fn2)0x021D2265)
#define OPP_CHOOSE   ((fn3)0x02259B21)
#define POST_EVENT   ((fn4)0x021C3BC9)
#define CHAIN_OPEN   ((int (*)(void))0x021D28A5)
#define CHAIN_CLOSE  ((int (*)(void))0x021D2965)
#define CARD_REF     ((fn1)0x021A25E9)
#define ADD_TO_HAND  ((fn2)0x021C72CD)
#define SHUFFLE      ((fn1)0x021D269D)
#define SEND_TOP     ((fn3)0x021D2149)     /* (desc, side, count): send the top `count` cards of the Deck to the GY */
#define PICK_BLOCK   0x0229DE94

#if STUB == RV_COND
/* cls0 +0C (menu time): the once-per-turn node is clear, another card is in the hand (the cost), and the Deck holds >= 3 matching monsters (the Deck row through the criteria matcher). */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller;
    if (e->cost_ran)
        return 2;
    if (turnlog_query(side, 0x0B, KEY_OPT1, 1))
        return 0;
    if (HAND_COUNT(side) < 2)
        return 0;
    MODE = 0;
    if (criteria_count(side, REVOLT, 0, 0) < 3)
        return 0;
    return 2;
}

#elif STUB == RV_COST
/* cls0 +10: the native hand-pick cost (0 = pending, 1 = done), then stamp the once-per-turn node. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = HAND_COST((u32)e, a1);
    if (r > 0)
        turnlog_post(e->controller, KEY_OPT1, 1, 0);
    return r;
}

#elif STUB == RV_RES
/* cls0 +04: Painful Choice's phases with 3 picks and the rest sent to the GY, then the Extra Deck lock. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, phase = *(volatile u32 *)(STATE + 0x70);
    u32 opp = 1 - side;
    switch (phase) {
    case 0x80:
        MODE = 0;
        if (!CAN_ACT(side))
            return 0;
        if (criteria_count(side, REVOLT, 0, 0) < 3)
            return 0;
        SHOW_MSG(side, 0x33);
        return 0x7F;
    case 0x7F:
        PICKER(side, 9, REVOLT, 0);
        return 0x7E;
    case 0x7E:
        SHOW_PICKS(side, 0xD);
        return 0x7D;
    case 0x7D:
        OPP_CHOOSE(opp, REVOLT, 0);
        return 0x7C;
    case 0x7C:
        POST_EVENT(8 | (opp ? 0x8000 : 0), 0, *(volatile u16 *)(PICK_BLOCK + 6), 0);
        return 0x7B;
    case 0x7B:
        CHAIN_OPEN();
        ADD_TO_HAND(side, CARD_REF(*(volatile u16 *)(PICK_BLOCK + 8)));
        return 0x7A;
    case 0x7A:
        SEND_TOP((u32)e, side, 2);                 /* the other 2 picks are the top 2 cards of the Deck */
        CHAIN_CLOSE();
        return 0x64;
    case 0x64:
        SHUFFLE(side);
        turnlog_post(side, KEY_LOCK, 1, 0);        /* "for the rest of this turn after this card resolves, you cannot Special Summon from the Extra Deck" */
        return 0x63;
    default:
        return 0;
    }
}

#elif STUB == RV_COND2
/* cls2 +0C (menu time): the once-per-turn node is clear and an 800 ATK / 1000 DEF monster is in the hand (printed values).  2 = unconditional. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n = HAND_COUNT(side);
    if (e->cost_ran)
        return 2;
    if (turnlog_query(side, 0x0B, KEY_OPT2, 1))
        return 0;
    for (i = 0; i < n; i++) {
        u32 cid = HAND_CID(side, i);
        if (cid && ATK_GET(cid) == 800 && DEF_GET(cid) == 1000)
            return 2;
    }
    return 0;
}

#elif STUB == RV_COST2
/* cls2 +10: the native self-banish, then the once-per-turn node. */
ENTRY int entry(EffectCtx *e)
{
    int r = SELF_BANISH((u32)e);
    if (r > 0)
        turnlog_post(e->controller, KEY_OPT2, 1, 0);
    return r;
}

#elif STUB == RV_RES2
/* cls2 +04: select the hand 800/1000 row, then the native hand Special Summon resolver (it asks for the monster through the criteria row). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    MODE = 1;
    return HAND_SS((u32)e, a1);
}

#else
#error "build with -DSTUB=RV_COND|RV_COST|RV_RES|RV_COND2|RV_COST2|RV_RES2 -DDATA=<addr>"
#endif

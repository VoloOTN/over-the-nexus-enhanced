/* Pantheism of the Monarchs (0x1923, donor Des Croaking).  Build with -DSTUB=PT_COND|PT_RES|PT_COND3|PT_COST3|PT_RES3.
 *   C1+C2 (Normal Spell): "Send 1 "Monarch" Spell/Trap Card from your hand to the Graveyard; draw 2 cards."
 * cls0 {+04 RES, +0C COND, +10 0x021E4EED (Fabled Valkyrus's hand-pick cost: picker over the virtual hand row 0xFFA0, the card goes to the GY from the pick callback)}.
 *   C3 (Graveyard, cls2 + a virtual GY-action row): "banish this card from your GY; reveal 3 "Monarch" S/T from your Deck, your opponent chooses 1 for you to add to your
 *   hand, shuffle the rest back."  RES3 replays Painful Choice's resolver 0x0220E41C phase for phase with Power Tool Dragon's pick-3 picker code (9) and WITHOUT the final
 *   "send the rest to the GY" (0x021D2148): the 3 picks are put on top of the Deck, the opponent chooses 1 (0x02259B20), it goes to the hand, the Deck is shuffled.
 * Design + UNPROVEN list: notes/pantheism-findings.md. */
#include "disguise.h"

#define PT_COND 1
#define PT_RES  2
#define PT_COND3 3
#define PT_COST3 4
#define PT_RES3  5

#define PANTHEISM     0x1923
#define MONARCH_SET   0x6D                /* tenacity's "Monarch" set code */
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_CID(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)) & 0x3FFF)
#define DECK_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0x10))

typedef int (*fn_set)(u32, u32);
typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn4)(u32, u32, u32, u32);
#define STATE        0x0229AAFC
#define SELF_BANISH  ((fn1)0x021E5709)     /* the native cls2 +10 cost "banish this card from your GY" */
#define CAN_ACT      ((fn1)0x021BA9AD)     /* Painful Choice phase 0x80 gate, (side) */
#define SHOW_MSG     ((fn2)0x0219A819)     /* (side, message) */
#define PICKER       ((fn4)0x0219C431)     /* (side, code, cid, param): code 9 = pick 3 (Power Tool Dragon), 0xB = pick 5 (Painful Choice) */
#define SHOW_PICKS   ((fn2)0x021D2265)     /* (side, 0xD): put the picks on top of the Deck for the reveal */
#define OPP_CHOOSE   ((fn3)0x02259B21)     /* (chooser side, cid, 0): the opponent selects 1 of the shown cards */
#define POST_EVENT   ((fn4)0x021C3BC9)     /* (flags | 8, 0, chosen index, 0) */
#define CHAIN_OPEN   ((int (*)(void))0x021D28A5)
#define CHAIN_CLOSE  ((int (*)(void))0x021D2965)
#define CARD_REF     ((fn1)0x021A25E9)
#define ADD_TO_HAND  ((fn2)0x021C72CD)     /* (side, ref): Deck -> hand */
#define SHUFFLE      ((fn1)0x021D269D)
#define PICK_BLOCK   0x0229DE94            /* +6 chosen index, +8 candidate */
#define PAN_OPT_KEY  0x1923
#define HAS_SET_CODE ((fn_set)0x020240D9)  /* (cid, set code) -> 1/0 */

#if STUB == PT_COND
/* +0C (menu time only): another "Monarch" Spell/Trap Card is in your hand (this card itself is still in the hand at the menu: it must not be the only one) and
 * the Deck holds at least 2 cards.  1 = activatable. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n = HAND_COUNT(side), found = 0;
    if (e->cost_ran)
        return 2;
    if (DECK_COUNT(side) < 2)
        return 0;
    for (i = 0; i < n; i++)
        if (HAS_SET_CODE(HAND_CID(side, i), MONARCH_SET))
            found++;
    return found >= 2 ? 2 : 0;
}

#elif STUB == PT_RES
/* +04: draw 2 cards (the cost already sent the Monarch card to the GY). */
ENTRY int entry(EffectCtx *e)
{
    draw(e->controller, 2);
    return 0;
}

#elif STUB == PT_COND3
/* cls2 +0C: once per turn (menu time) and at least 3 "Monarch" Spell/Trap Cards in the Deck (the Deck row 0xFFA1 through the criteria matcher). 2 = unconditional. */
ENTRY int entry(EffectCtx *e)
{
    if (opt_used(e, PAN_OPT_KEY))
        return 0;
    if (criteria_count(e->controller, PANTHEISM, 0, 0) < 3)
        return 0;
    return 2;
}

#elif STUB == PT_COST3
/* cls2 +10: the native self-banish, then the once-per-turn node (a kind-1 turn-log node keyed on the cid; the C1 cost posts none). */
ENTRY int entry(EffectCtx *e)
{
    int r = SELF_BANISH((u32)e);
    if (r > 0)
        turnlog_post(e->controller, PAN_OPT_KEY, 1, 0);
    return r;
}

#elif STUB == PT_RES3
/* cls2 +04: Painful Choice's phases with 3 picks, the opponent choosing, the rest left on the Deck and shuffled. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, phase = *(volatile u32 *)(STATE + 0x70);
    u32 opp = 1 - side;
    switch (phase) {
    case 0x80:
        if (!CAN_ACT(side))
            return 0;
        if (criteria_count(side, PANTHEISM, 0, 0) < 3)
            return 0;
        SHOW_MSG(side, 0x33);
        return 0x7F;
    case 0x7F:
        PICKER(side, 9, PANTHEISM, 0);
        return 0x7E;
    case 0x7E:
        SHOW_PICKS(side, 0xD);
        return 0x7D;
    case 0x7D:
        OPP_CHOOSE(opp, PANTHEISM, 0);
        return 0x7C;
    case 0x7C:
        POST_EVENT(8 | (opp ? 0x8000 : 0), 0, *(volatile u16 *)(PICK_BLOCK + 6), 0);
        return 0x7B;
    case 0x7B:
        CHAIN_OPEN();
        ADD_TO_HAND(side, CARD_REF(*(volatile u16 *)(PICK_BLOCK + 8)));
        return 0x7A;
    case 0x7A:
        CHAIN_CLOSE();
        return 0x64;
    case 0x64:
        SHUFFLE(side);
        return 0x63;
    default:
        return 0;
    }
}

#else
#error "build with -DSTUB=PT_COND|PT_RES|PT_COND3|PT_COST3|PT_RES3"
#endif

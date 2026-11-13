/* Erebus the Underworld Monarch (0x1313, donor Man-Eating Treasure Chest).  Build with -DSTUB=EB_COND|EB_COST|EB_RES|EB_PRED|EB_ROWH -DDATA=<ov5 data address>.
 * E1 "If this card is Tribute Summoned: You can send 2 "Monarch" Spell/Trap Cards with different names from your hand and/or Deck to the GY, and if you do, shuffle 1 card from
 *     your opponent's hand (at random), GY, or their side of the field into the Deck."
 *   BUILT: the cost (2 Monarch S/T, different cids, hand and/or Deck) + the opponent-GY half of the shuffle.  NOT BUILT: the opponent's hand (random) and field halves.
 * cls1 {+04 RES, +0C COND, +10 0x021E51E5 ("You can"), +14 COST}.  COST is a step machine on [STATE+0x7C] (1..5; step 0 only advances so no criteria lookup runs while the
 * step word is 0, because the H2 front reads that word to choose the cost row vs the effect row).  The cost row's HANDLER fills the engine's candidate list itself: the
 * hand test 0x0223BFD4 once per hand index, then the Deck walker 0x0223BC3C, both with our predicate (Monarch set code, a different cid than the first pick), so the list
 * picker (0x0219C430, 1 card) shows hand and Deck cards together.  Each entry's zone is in the table at 0x02299908 (bit 1.. = zone code 0xB hand / 0xD Deck).
 * Design + UNPROVEN list: notes/erebus-findings.md. */
#include "disguise.h"

#define EB_COND 1
#define EB_COST 2
#define EB_RES  3
#define EB_PRED 4
#define EB_ROWH 5
#define EB_COND2 6
#define EB_COST2 7
#define EB_RES2  8
#define EB_PRED2 9
#define EB_GYH   10
#define EH_RES   11
#define EH_DH    12
#define PM_COND  13
#define PM_COST  14
#define PM_RES   15
#define EH2_COND 16
#define EH2_COST 17
#define FM_COND  18
#define FM_COST  19
#define FM_RES   20
#define FM_LOCK  21
#define FM_TRIB  22
#define EB_FROWH 23
#define EB_RES2X 24
#define PM2_COND 25
#define PM2_COST 26
#define PM_OPT2  0x54CF            /* The Prime Monarch GY half: its own once-per-turn key (C1 uses 0x14CF) */
#define SS_ROOM  ((fn2)0x021B9EC1) /* (side, 0): the GY self-SS resolver 0x0220731D's own first room check */
#define PM_PRED  27
#define PM_GYH   28

#define EREBUS        0x1313
#define MONARCH_SET   0x6D
#define STATE         0x0229AAFC          /* +0x70 resolver phase, +0x7C cost step */
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_WORD(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)))
#define DECK_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0x10))
#define DECKW(s, i)   (*(volatile u32 *)(PLAYER(s) + 0x304 + 4 * (i)))
#define GYW(s, i)     (*(volatile u32 *)(PLAYER(s) + 0x55C + 4 * (i)))
#define FIRST         (*(volatile u32 *)(DATA + 0x0))     /* the first pick's cid (0 = none yet) */
#define MODE          (*(volatile u32 *)(DATA + 0x4))     /* H2 row selector: 0 = E1, 2 = E2 cost (hand row), 3 = E2 target (GY monster row) */
#define PICK_LIST     0x02299458                         /* candidate words, one per list entry */
#define PICK_ZONE     0x02299908                         /* candidate halfwords: bit0 side, bits 1..5 zone code */
#define PICK_COUNT    (*(volatile u32 *)(0x0229DD94 + 0x34))
#define ZONE_HAND     0x0B
#define ADD_CAND      ((fn3)0x02243B2D)    /* (side, zone code, index): append one card to the candidate list; field zones use their own index 0..10 */
#define RNG_SEED      (*(volatile u32 *)(0x0229DD14 + 0x28))   /* the engine's synchronised shuffle seed */
#define ZONE_DECK     0x0D

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn4)(u32, u32, u32, u32);
typedef int (*fn6)(u32, u32, u32, u32, u32, u32);
typedef int (*fn7)(u32, u32, u32, u32, u32, u32, u32);
#define HAS_SET_CODE  ((fn2)0x020240D9)
#define CARD_TYPE     ((fn1)0x0202ABF9)
#define COUNT_FILL    ((fn3)0x02243FA9)          /* (side, cid, param): fill the candidate list through the criteria row, returns the count */
#define PROMPT        ((fn2)0x0219A819)
#define OPEN_PICKER   ((fn4)0x0219C431)          /* (side, mode = count + 6, cid, param) */
#define PICK_FETCH    ((u32 *(*)(u32))0x0219C94D)
#define DECK_TO_GY    ((fn4)0x021D21B1)          /* (side, ref, cid, 0) */
#define HAND_TO_GY    ((fn2)0x021C6DB5)          /* (side, hand index) */
#define RETURN_TO_DECK ((fn4)0x021C6A0D)         /* (desc, owner side, card ref, 1): Pot of Avarice's mover, any zone -> Deck (read 2026-11-12) */
#define HAND_TEST     ((fn7)0x0223BFD5)          /* (side, cid, hand index, cb, &aux, word, 0x10): test one hand card, adds it to the list when it passes */
#define DECK_WALK     ((fn6)0x0223BC3D)          /* (side, cid, cb, &aux, word, 2): every Deck card that passes */
#define SHUFFLE       ((fn1)0x021D269D)
#define CHAIN_OPEN    ((int (*)(void))0x021D28A5)
#define CHAIN_CLOSE   ((int (*)(void))0x021D2965)
#define SHOW_MSG      ((fn2)0x0219A819)
#define HAND_COST     ((fn2)0x021E4EED)          /* Fabled Valkyrus's hand-pick cost: picker over the hand row, the card goes to the GY from the pick callback */
#define GY_TO_HAND    ((fn2)0x02208181)          /* cls2 resolver: add the recorded GY target(s) to the hand */
#define GY_ENUM       ((fn6)0x0223C4E9)          /* (side, cid, cb, &aux, word, flags): the GY walker (flags 0x10000 = plain GY, 8 = GY Special Summon) */
#define ATK_GET       ((fn1)0x0202AC49)
#define DEF_GET       ((fn1)0x0202AC29)
#define OPT_KEY       0x1313
#define PRIME         0x14CF
#define EHTHER        0x1312
#define FMON          0x249B               /* The First Monarch (donor Tiki Soul, a native Trap Monster) */
#define GENEX         0x2167               /* Genex Ally Changer: the attribute riders are keyed by its cid (cur_attribute 0x021B8E48) */
#define FM_ATTR       (*(volatile u32 *)(DATA + 0x8))   /* the declared Attribute */
#define FM_STAGE      (*(volatile u32 *)(DATA + 0xC))   /* cost machine stage: 0 discard, 1 declare */
#define SEL_PHASE     (*(volatile u32 *)0x0229AB7C)
#define DECLARE       ((void (*)(u32, u32, u32, u32))0x02259A9D)   /* DNA Transplant's declare step (side, cid, 1, 0xFF) */
#define ANSWER        (*(volatile u16 *)(0x0229DE94 + 8))
#define PHASEBASE     0x0229DD14           /* +0x34 turn player, +0x48 phase (2 Main 1, 3 Battle, 4 Main 2, 5 End) */
#define TURN_PLAYER   (*(volatile u32 *)(PHASEBASE + 0x34))
#define PHASE         (*(volatile u32 *)(PHASEBASE + 0x48))
#define CAN_SUMMON    ((fn2)0x0225D6D5)    /* (side, card ref) -> 0x10 when that hand card can be Summoned right now (Tributes included) */
#define BANISH_COST   ((fn2)0x021E5319)    /* Survival Instinct's cost: pick from the GY by the criteria row, banish exactly 1 for an unlisted cid */

static inline int is_monarch_st(u32 cid)
{
    u32 t;
    if (!cid || !HAS_SET_CODE(cid, MONARCH_SET))
        return 0;
    t = CARD_TYPE(cid);
    return t == 13 || t == 14;               /* Spell Card (27 >> 1) / Trap Card (29 >> 1) */
}

/* 0x10000 | the GY index of the descriptor's own card (desc[+0xC] = its instance ref, the value the GY self-SS resolver hands to 0x021A220C), 0x1FFFF if not found.
 * A GY word's ref = ((w << 1 >> 24) << 1) + (w << 17 >> 31) (the RETURN_TO_DECK decoding). */
static inline u32 pm_self_tag(EffectCtx *e)
{
    u32 side = e->controller & 1, ref = *(volatile u16 *)((u8 *)e + 0xC), i, n = GY_COUNT(side), w;
    for (i = 0; i < n; i++) {
        w = GYW(side, i);
        if ((((w << 1) >> 24) << 1) + ((w << 17) >> 31) == ref)
            return 0x10000 | i;
    }
    return 0x1FFFF;
}

#if STUB == EB_COND
/* +0C: at least 2 "Monarch" Spell/Trap Cards with different cids across hand + Deck.  (Used at the menu and again once the cost ran: always yes then.) */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n, first = 0;
    if (e->cost_ran)
        return 2;
    MODE = 0;
    n = HAND_COUNT(side);
    for (i = 0; i < n + DECK_COUNT(side); i++) {
        u32 cid = (i < n ? HAND_WORD(side, i) : DECKW(side, i - n)) & 0x3FFF;
        if (!is_monarch_st(cid))
            continue;
        if (!first)
            first = cid;
        else if (cid != first)
            return 2;
    }
    return 0;
}

#elif STUB == EB_PRED
/* The list predicate (called by the hand test and the Deck walker with the card word pointer at [sp]): a Monarch Spell/Trap whose cid is not the first pick's. */
ENTRY int entry(u32 side, u32 zone, u32 idx, u32 cid, u32 *cardword, u32 *aux)
{
    u32 c = *cardword & 0x3FFF;
    (void)side; (void)zone; (void)idx; (void)cid; (void)aux;
    if (!is_monarch_st(c))
        return 0;
    return FIRST == 0 || c != FIRST;
}

#elif STUB == EB_ROWH
/* The cost row's handler (row r0, side r1): fill the list from the hand (one test per hand index) and the Deck.  Returns the number of candidates. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 aux = (u32)(s32)(*(s16 *)((u8 *)row + 2)), word = row[2], cid = *(u16 *)row, i, n = 0, hn = HAND_COUNT(side);
    for (i = 0; i < hn; i++)
        n += HAND_TEST(side, cid, i, PRED_ADDR, (u32)&aux, word, 0x10);
    n += DECK_WALK(side, cid, PRED_ADDR, (u32)&aux, word, 2);
    return n;
}

#elif STUB == EB_COST
/* +14: 0 = pending, 1 = paid, < 0 = abort. */
static int pay_pick(u32 side)
{
    u32 *p, w, idx, zone, ref, i, hn;
    if ((s32)PICK_COUNT <= 0)
        return -1;
    p = PICK_FETCH(1);
    w = *p;
    idx = ((u32)p - PICK_LIST) >> 2;
    zone = (*(volatile u16 *)(PICK_ZONE + 2 * idx) >> 1) & 0x1F;
    FIRST = w & 0x3FFF;
    if (zone == ZONE_HAND) {
        hn = HAND_COUNT(side);
        for (i = 0; i < hn; i++)
            if (HAND_WORD(side, i) == w)
                return HAND_TO_GY(side, i), 0;
        return -1;
    }
    ref = (((w << 1) >> 24) << 1) + ((w << 17) >> 31);
    DECK_TO_GY(side, ref, w & 0x3FFF, 0);
    return 0;
}

ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller, cid = e->cid, step = *(volatile u32 *)(STATE + 0x7C);
    (void)a1;
    switch (step) {
    case 0:
        FIRST = 0;
        MODE = 0;
        *(volatile u32 *)(STATE + 0x7C) = 1;
        return 0;
    case 1:
    case 4:
        if (COUNT_FILL(side, cid, 0) <= 0)
            return -1;
        PROMPT(side, 0x0D);
        *(volatile u32 *)(STATE + 0x7C) = step + 1;
        return 0;
    case 2:
    case 5:
        OPEN_PICKER(side, 7, cid, 0);
        *(volatile u32 *)(STATE + 0x7C) = step + 1;
        return 0;
    case 3:
        if (pay_pick(side) < 0)
            return -1;
        *(volatile u32 *)(STATE + 0x7C) = 4;
        return 0;
    default:                                  /* 6: second pick resolved */
        if (pay_pick(side) < 0)
            return -1;
        FIRST = 0;
        return 1;
    }
}

#elif STUB == EB_RES
/* +04: phases like Painful Choice's: 0x80 gate + message, 0x7F the opponent-GY list picker (1 card), 0x7E move it to the Deck, 0x64 shuffle the opponent's Deck. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller, opp = 1 - side, phase = *(volatile u32 *)(STATE + 0x70), *p, w, ref;
    (void)a1;
    switch (phase) {
    case 0x80:
        if (!GY_COUNT(opp))
            return 0;
        SHOW_MSG(side, 0x33);
        return 0x7F;
    case 0x7F:
        OPEN_PICKER(side, 7, e->cid, 0);
        return 0x7E;
    case 0x7E:
        if ((s32)PICK_COUNT <= 0)
            return 0;
        p = PICK_FETCH(1);
        w = *p;
        ref = (((w << 1) >> 24) << 1) + ((w << 17) >> 31);
        CHAIN_OPEN();
        RETURN_TO_DECK((u32)e, opp, ref, 1);
        CHAIN_CLOSE();
        return 0x64;
    case 0x64:
        SHUFFLE(opp);
        return 0x63;
    default:
        return 0;
    }
}

#elif STUB == EB_COND2
/* E2 cls2 +0C (virtual record): either player's Main Phase, once per turn, a "Monarch" Spell/Trap in the hand to discard, a monster with 2400+ ATK and 1000 DEF in the GY to add. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n, ok = 0;
    if (e->cost_ran)
        return 2;
    MODE = 0;
    if (PHASE != 2 && PHASE != 4)                   /* \"either player's Main Phase\": the speed-2 front offers it in every phase, so the phase is tested here */
        return 0;
    if (opt_used(e, OPT_KEY))
        return 0;
    n = HAND_COUNT(side);
    for (i = 0; i < n; i++)
        if (is_monarch_st(HAND_WORD(side, i) & 0x3FFF))
            ok = 1;
    if (!ok)
        return 0;
    MODE = 3;                                       /* the GY monster row 0xFFE3 counts the 2400+/1000 monsters */
    n = criteria_count(side, EREBUS, 0, 0);
    MODE = 0;
    return n ? 2 : 0;
}

#elif STUB == EB_COST2
/* E2 cls2 +10: discard 1 "Monarch" Spell/Trap from the hand (the native hand-pick cost over the hand row 0xFFE2, MODE 2), then stamp the once-per-turn node and move to the target phase (MODE 3). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r;
    if (MODE != 2)
        MODE = 2;
    r = HAND_COST((u32)e, a1);
    if (r > 0) {
        turnlog_post(e->controller, OPT_KEY, 1, 0);
        MODE = 3;
    } else if (r < 0) {
        MODE = 0;
    }
    return r;
}

#elif STUB == EB_RES2
/* E2 cls2 +04: back to MODE 0, then the native "add the recorded GY target to the hand" resolver. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    MODE = 0;
    return GY_TO_HAND((u32)e, a1);
}

#elif STUB == EB_PRED2
/* GY predicate: ATK >= 2400 and DEF == 1000 (printed values). */
ENTRY int entry(u32 side, u32 zone, u32 idx, u32 cid, u32 *cardword, u32 *aux)
{
    u32 c = *cardword & 0x3FFF;
    (void)side; (void)zone; (void)idx; (void)cid; (void)aux;
    return DEF_GET(c) == 1000 && (s32)ATK_GET(c) >= 2400;
}

#elif STUB == EB_GYH
/* Row 0xFFE3 handler (row r0, side r1): the plain GY walker with the 2400+/1000 predicate. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 aux = 0;
    return GY_ENUM(side, *(u16 *)row, PRED2_ADDR, (u32)&aux, row[2], 0x10000);
}

#elif STUB == EH_RES
/* Ehther cls1 +04: "Special Summon 1 monster with 2400 or more ATK and 1000 DEF from your Deck" = the native Deck-SS machine over the Deck row 0xFFE5. The summon's source cid
 * (Ehther) is what the summon-rider list front turns into the kind-2 node the End-Phase "return to the hand" row looks for. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    return deck_ss((u32)e, a1);
}

#elif STUB == EH_DH
/* Row 0xFFE5 handler (row r0, side r1): the Deck walker with the 2400+/1000 predicate. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 aux = 0;
    return DECK_WALK(side, *(u16 *)row, PRED2_ADDR, (u32)&aux, row[2], 2);
}

#elif STUB == PM_COND
/* The Prime Monarch cls3 +0C: once per turn, at least 2 "Monarch" Spell/Trap Cards in your Graveyard. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    if (e->cost_ran)
        return 2;
    if (e->race < 5)                                /* desc[+3] = zone: a monster zone means the GY half Special Summoned it -- no Trap effect there */
        return 0;
    if (opt_used(e, PRIME))
        return 0;
    MODE = 0;                                       /* row 0xFFE6 (the resolver's own count, so cond and resolver agree) */
    return criteria_count(e->controller & 1, PRIME, 0, 0) >= 2 ? 2 : 0;
}

#elif STUB == PM_COST
/* cls3 +10: stamp the once-per-turn node. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    turnlog_post(e->controller, PRIME, 1, 0);
    return 1;
}

#elif STUB == PM_RES
/* cls3 +04: phases like Pantheism's: 0x80 gate, 0x7F pick 2 Monarch Spell/Traps from the GY (list picker mode 8 over the GY row 0xFFE6), 0x7E return both to the Deck with
 * Pot of Avarice's mover 0x021C6A0C, 0x64 shuffle, 0x63 draw 1. (Selection at resolution, not at activation: the printed "target" is NOT implemented.) */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, phase = *(volatile u32 *)(STATE + 0x70), i, n, refs[2], *p, w;
    (void)a1;
    switch (phase) {
    case 0x80:
        if (criteria_count(side, PRIME, 0, 0) < 2)
            return 0;
        SHOW_MSG(side, 0x5E);
        return 0x7F;
    case 0x7F:
        OPEN_PICKER(side, 8, PRIME, 0);
        return 0x7E;
    case 0x7E:
        n = PICK_COUNT;
        if ((s32)n <= 0)
            return 0;
        if (n > 2)
            n = 2;
        for (i = 0; i < n; i++) {
            p = PICK_FETCH(i + 1);
            w = *p;
            refs[i] = (((w << 1) >> 24) << 1) + ((w << 17) >> 31);
        }
        CHAIN_OPEN();
        for (i = 0; i < n; i++)
            RETURN_TO_DECK((u32)e, side, refs[i], 1);
        CHAIN_CLOSE();
        return 0x64;
    case 0x64:
        SHUFFLE(side);
        return 0x63;
    case 0x63:
        draw(side, 1);
        return 0;
    default:
        return 0;
    }
}

#elif STUB == EH2_COND
/* Ehther E2 (virtual cls2, hand): during the OPPONENT's Main Phase, Ehther in the hand can be Tribute Summoned right now, a "Monarch" Spell/Trap is in the GY (counted through
 * the GY row 0xFFE7 with MODE 4). 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, i, n, k;
    if (e->cost_ran)
        return 2;
    MODE = 0;
    if (TURN_PLAYER == side || (PHASE != 2 && PHASE != 4))
        return 0;
    MODE = 4;
    k = criteria_count(side, EHTHER, 0, 0);
    MODE = 0;
    if (!k)
        return 0;
    n = HAND_COUNT(side);
    for (i = 0; i < n; i++) {
        u32 w = HAND_WORD(side, i);
        if ((w & 0x3FFF) == EHTHER && (CAN_SUMMON(side, (((w << 1) >> 24) << 1) + ((w << 17) >> 31)) & 0x10))
            return 2;
    }
    return 0;
}

#elif STUB == EH2_COST
/* Ehther E2 cost: banish 1 "Monarch" Spell/Trap from the GY (the native GY banish cost over the GY row 0xFFE7, MODE 4). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r;
    MODE = 4;
    r = BANISH_COST((u32)e, a1);
    if (r != 0)
        MODE = 0;
    return r;
}

#elif STUB == FM_COND
/* The First Monarch E1 (cls1 trigger, "If Summoned this way: You can discard 1 card, then declare 1 Attribute"): a card in the hand to discard. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1;
    if (e->cost_ran)
        return 2;
    MODE = 0;
    return HAND_COUNT(side) ? 2 : 0;
}

#elif STUB == FM_COST
/* cls1 +14: stage 0 = the native hand-pick discard over the hand row 0xFFE8 (MODE 5), stage 1 = DNA Transplant's declare-an-Attribute step; the answer is kept in DATA+8.
 * 0 = pending, 1 = paid, < 0 = abort. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1;
    int r;
    if (MODE != 5) {
        MODE = 5;
        FM_STAGE = 0;
        FM_ATTR = 0;
    }
    if (FM_STAGE == 0) {
        r = HAND_COST((u32)e, a1);
        if (r < 0) {
            MODE = 0;
            return r;
        }
        if (r > 0) {
            FM_STAGE = 1;
            SEL_PHASE = 0;
        }
        return 0;
    }
    if (SEL_PHASE == 0) {
        DECLARE(side, FMON, 1, 0xFF);
        SEL_PHASE = 1;
        return 0;
    }
    FM_ATTR = ANSWER;
    SEL_PHASE = 0;
    MODE = 0;
    FM_STAGE = 0;
    return 1;
}

#elif STUB == FM_RES
/* cls1 +04: the declared Attribute becomes permanent on The First Monarch (the Genex attribute rider, kind 3 = no duration printed). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, z, attr = FM_ATTR;
    (void)a1;
    if (!attr)
        return 0;
    for (z = 0; z <= 4; z++)
        if (ZONE_FACEUP(side, z) && CID(ZONE_WORD(side, z)) == FMON)
            rider_attach(side, z, GENEX, 3, attr);
    FM_ATTR = 0;
    return 0;
}

#elif STUB == FM_LOCK
/* The First Monarch: "If this card was Summoned this way, you cannot Special Summon monsters, except monsters with this card's Attribute."  (side, card word at the SS engine's
 * free-zone check) -> 1 when a face-up First Monarch of that side is in a Monster Zone and the card's base Attribute differs from the First Monarch's CURRENT Attribute. */
ENTRY int entry(u32 side, u32 cardword)
{
    u32 z, attr = ((fn1)0x0202ABC9)(cardword & 0x3FFF);
    side &= 1;
    for (z = 0; z <= 4; z++)
        if (ZONE_FACEUP(side, z) && CID(ZONE_WORD(side, z)) == FMON && (u32)cur_attribute(side, z, 0) != attr)
            return 1;
    return 0;
}

#elif STUB == FM_TRIB
/* "can be treated as 2 Tributes for the Tribute Summon of a monster with the same Attribute as this card": (player, summoned cid, candidate side, candidate slot) -> 1. */
ENTRY int entry(u32 player, u32 summoned, u32 cside, u32 slot)
{
    if (cside != player || slot > 4)
        return 0;
    if (!ZONE_FACEUP(cside, slot) || CID(ZONE_WORD(cside, slot)) != FMON)
        return 0;
    return (u32)cur_attribute(cside, slot, 0) == ((fn1)0x0202ABC9)(summoned & 0x3FFF);
}

#elif STUB == EB_FROWH
/* Erebus E1 effect row 0xFFE1 handler (row r0, side r1): the OPPONENT's Graveyard (plain GY walker) and every card on their field (zones 0..10, each added with its own zone index). */
ENTRY int entry(u32 *row, u32 side)
{
    u32 opp = (side & 1) ^ 1, z, n = GY_ENUM(opp, *(u16 *)row, 0, 0, row[2], 0x10000);
    for (z = 0; z <= 10; z++) {
        if (CID(ZONE_WORD(opp, z))) {
            ADD_CAND(opp, z, 0);
            n++;
        }
    }
    return n;
}

#elif STUB == EB_RES2X
/* cls1 +04 v2, phases like Painful Choice's: 0x80 gate (anything in the opponent's GY / field / hand) + message, 0x7F the list picker over the GY + field row (only when it has
 * candidates), 0x7E return the picked card to the Deck -- or, when the player CANCELS the picker (or there were no candidates), a RANDOM card from the opponent's hand --
 * 0x64 shuffle the opponent's Deck.  (The printed "opponent's hand (at random), Graveyard, or their side of the field" choice is a picker + cancel here, not a menu.) */
static u32 field_count(u32 opp)
{
    u32 z, n = 0;
    for (z = 0; z <= 10; z++)
        if (CID(ZONE_WORD(opp, z)))
            n++;
    return n;
}

ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, opp = side ^ 1, phase = *(volatile u32 *)(STATE + 0x70), gf, *p, w, ref, hn;
    (void)a1;
    gf = GY_COUNT(opp) + field_count(opp);
    hn = HAND_COUNT(opp);
    switch (phase) {
    case 0x80:
        if (!gf && !hn)
            return 0;
        SHOW_MSG(side, 0x33);
        return 0x7F;
    case 0x7F:
        if (gf)
            OPEN_PICKER(side, 7, e->cid, 0);
        return 0x7E;
    case 0x7E:
        if (gf && (s32)PICK_COUNT > 0) {
            p = PICK_FETCH(1);
            w = *p;
        } else if (hn) {
            w = HAND_WORD(opp, (((RNG_SEED ^ (RNG_SEED >> 16)) & 0xFFFF) * hn) >> 16);          /* no division: libgcc's is not Thumb-1 */
        } else {
            return 0;
        }
        ref = (((w << 1) >> 24) << 1) + ((w << 17) >> 31);
        CHAIN_OPEN();
        RETURN_TO_DECK((u32)e, opp, ref, 1);
        CHAIN_CLOSE();
        return 0x64;
    case 0x64:
        SHUFFLE(opp);
        return 0x63;
    default:
        return 0;
    }
}

#elif STUB == PM2_COND
/* The Prime Monarch GY half (virtual cls2, GY): your Main Phase, once per turn, room for a Special Summon, another "Monarch" Spell/Trap in the GY to banish (row 0xFFE9,
 * MODE 6; "other" = not THIS card's GY index, so a 2nd copy of The Prime Monarch is a legal cost). 2 = yes.
 * The Special Summon itself is the native GY self-SS resolver 0x0220731D; the stat tree gives 0x14CF Fairy / LIGHT / 5 / 1000 / 2400 (cards/first_monarch.py). */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, n;
    if (e->cost_ran)
        return 2;
    MODE = 0;
    if (TURN_PLAYER != side || (PHASE != 2 && PHASE != 4))
        return 0;
    if (opt_used(e, PM_OPT2))
        return 0;
    if (!SS_ROOM(side, 0))
        return 0;
    MODE = 6;
    FIRST = pm_self_tag(e);
    n = criteria_count(side, PRIME, 0, 0);
    FIRST = 0;
    MODE = 0;
    return n ? 2 : 0;
}

#elif STUB == PM_PRED
/* Row 0xFFE9 predicate: a "Monarch" Spell/Trap that is not the source card (FIRST = 0x10000 | its GY index while MODE 6 runs). */
ENTRY int entry(u32 side, u32 zone, u32 idx, u32 cid, u32 *cardword, u32 *aux)
{
    (void)side; (void)zone; (void)cid; (void)aux;
    return FIRST != (0x10000 | idx) && is_monarch_st(*cardword & 0x3FFF);
}

#elif STUB == PM_GYH
/* Row 0xFFE9 handler (row r0, side r1): the plain GY walker with PM_PRED. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 aux = 0;
    return GY_ENUM(side, *(u16 *)row, PMPRED_ADDR, (u32)&aux, row[2], 0x10000);
}

#elif STUB == PM2_COST
/* cost: banish 1 other "Monarch" Spell/Trap from the GY (native GY banish over row 0xFFE9, MODE 6), then stamp the once-per-turn key. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r;
    MODE = 6;
    FIRST = pm_self_tag(e);
    r = BANISH_COST((u32)e, a1);
    if (r != 0) {
        MODE = 0;
        FIRST = 0;
    }
    if (r > 0)
        turnlog_post(e->controller, PM_OPT2, 1, 0);
    return r;
}

#else
#error "build with -DSTUB=EB_COND|EB_COST|EB_RES|EB_PRED|EB_ROWH|EB_COND2|EB_COST2|EB_RES2|EB_PRED2|EB_GYH -DDATA=<addr> -DPRED_ADDR=<addr> -DPRED2_ADDR=<addr>"
#endif

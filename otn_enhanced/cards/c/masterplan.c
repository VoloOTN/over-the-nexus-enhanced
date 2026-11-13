/* The Monarchs Masterplan (0x0D6A, donor Speed Spell - Faustian Bargain) -- C2, the banished trigger (2026-11-12).  TEST ROM, NOT SHIPPED, nothing in-game confirmed.
 *   "If this card is banished: You can target 1 face-up monster your opponent controls; add 1 monster with the same Attribute that has 2400 ATK/1000 DEF, from your Deck or GY to
 *    your hand, then you can apply this effect.  * Immediately after this effect resolves, Normal Summon 1 "Zaborg the Thunder Monarch", "Mobius the Frost Monarch", "Thestalos the
 *    Firestorm Monarch", "Granmarg the Rock Monarch", "Raiza the Storm Monarch", or "Caius the Shadow Monarch".  You can only use this effect of "The Monarchs Masterplan" once per turn."
 * Banish -> the Dragon Rulers' banish gates (GY 0x021C71C8 / other 0x021D1B98) get fronts posting for 0x0D6A; virtual cls2 record for the banished zone 0xF (prefind_hook).
 * Rows (masterplan.py H2 / H3): 0xFFD6 C1 (MODE 0), 0xFFD7 opponent targets (MODE 8), 0xFFD8 Deck + GY adds of the chosen Attribute (MODE 9).
 * KNOWN DEVIATION: the opponent's monster is CHOSEN AT RESOLUTION (list picker), not targeted at activation.  The optional Normal Summon = Cry Havoc!'s effect-Normal-Summon machine
 * 0x0220D80D (Escalation's), restricted by MP_NSPRED through Escalation's predicate-lookup front.
 * Build with -DSTUB=... -DMPDATA=<data> -DAPRED_ADDR=<MP_APRED|1> -DL_NS=<dlg id>. */
#include "disguise.h"

#define MP_COND   1
#define MP_RES    2
#define MP_TGTH   3
#define MP_ADDH   4
#define MP_APRED  5
#define MP_NSPRED 6

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn4)(u32, u32, u32, u32);
typedef int (*fn6)(u32, u32, u32, u32, u32, u32);
typedef int (*fn7)(u32, u32, u32, u32, u32, u32, u32);

#define MPLAN         0x0D6A
#define KEY_OPT       0x8D6A
#define STATE         0x0229AAFC
#define RES_PHASE     (*(volatile u32 *)(STATE + 0x70))
#define MODE          (*(volatile u32 *)(MPDATA + 0x0))   /* H2 row selector: 0 C1, 8 targets, 9 adds */
#define ATTR          (*(volatile u32 *)(MPDATA + 0x4))   /* the chosen monster's current Attribute */
#define DELEG         (*(volatile u32 *)(MPDATA + 0x8))   /* 1 while the resolver is handed to the Normal Summon machine */
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_WORD(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)))
#define DECK_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0x10))
#define DECKW(s, i)   (*(volatile u32 *)(PLAYER(s) + 0x304 + 4 * (i)))
#define GYW(s, i)     (*(volatile u32 *)(PLAYER(s) + 0x55C + 4 * (i)))
#define PICK_LIST     0x02299458
#define PICK_ZONE     0x02299908
#define PICK_COUNT    (*(volatile u32 *)(0x0229DD94 + 0x34))
#define MENU_ANSWER   (*(volatile u32 *)(0x0229DD94 + 0x34))
#define ADD_CAND      ((fn3)0x02243B2D)
#define COUNT_FILL    ((fn3)0x02243FA9)
#define OPEN_PICKER   ((fn4)0x0219C431)
#define PICK_FETCH    ((u32 *(*)(u32))0x0219C94D)
#define DECK_WALK     ((fn6)0x0223BC3D)
#define GY_ENUM       ((fn6)0x0223C4E9)
#define GY2HAND       ((fn3)0x021C7039)
#define DECK2HAND     ((fn2)0x021C72CD)
#define SHUFFLE       ((fn1)0x021D269D)
#define CHAIN_OPEN    ((int (*)(void))0x021D28A5)
#define CHAIN_CLOSE   ((int (*)(void))0x021D2965)
#define ATK_GET       ((fn1)0x0202AC49)
#define DEF_GET       ((fn1)0x0202AC29)
#define BASE_ATTR     ((fn1)0x0202ABC9)
#define MENU          ((fn7)0x0219ABB5)
#define NS_MACHINE    ((fn2)0x0220D80D)            /* Cry Havoc!'s effect-Normal-Summon resolver (phases from 0x80) */
#define CAN_SUMMON    ((fn2)0x0225D6D5)            /* (side, card ref) & 0x10 = can be Summoned now */

static inline int is_2400_1000(u32 cid)
{
    return DEF_GET(cid) == 1000 && (s32)ATK_GET(cid) == 2400;
}

/* a monster with 2400 ATK / 1000 DEF and Attribute `a` in side's Deck or GY */
static inline int has_add(u32 side, u32 a)
{
    u32 i, n, c;
    n = DECK_COUNT(side);
    for (i = 0; i < n; i++) {
        c = DECKW(side, i) & 0x3FFF;
        if (is_2400_1000(c) && (u32)BASE_ATTR(c) == a)
            return 1;
    }
    n = GY_COUNT(side);
    for (i = 0; i < n; i++) {
        c = GY_CID(side, i);
        if (is_2400_1000(c) && (u32)BASE_ATTR(c) == a)
            return 1;
    }
    return 0;
}

/* a face-up opponent monster at zone z whose Attribute has an add candidate */
static inline int tgt_ok(u32 side, u32 z)
{
    u32 opp = side ^ 1;
    return CID(ZONE_WORD(opp, z)) && ZONE_FACEUP(opp, z) && has_add(side, (u32)cur_attribute(opp, z, 0));
}

static inline int is_named(u32 c)
{
    return c == 0x174D || c == 0x17E2 || c == 0x182E || c == 0x185F || c == 0x1BCD || c == 0x1D5C;
}

#if STUB == MP_COND
/* virtual cls2 (banished zone 0xF) +0C: once per turn, a face-up opposing monster with a same-Attribute 2400/1000 monster in the Deck or GY. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, z;
    if (e->cost_ran)
        return 2;
    if (e->race != 0xF || opt_used(e, KEY_OPT))
        return 0;
    for (z = 0; z <= 4; z++)
        if (tgt_ok(side, z))
            return 2;
    return 0;
}

#elif STUB == MP_TGTH
/* Row 0xFFD7 handler (row, side): the opponent's face-up monsters that have a same-Attribute add candidate. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 z, n = 0;
    (void)row;
    side &= 1;
    for (z = 0; z <= 4; z++)
        if (tgt_ok(side, z)) {
            ADD_CAND(side ^ 1, z, 0);
            n++;
        }
    return n;
}

#elif STUB == MP_APRED
/* Row 0xFFD8 predicate: 2400 ATK / 1000 DEF and base Attribute == ATTR. */
ENTRY int entry(u32 side, u32 zone, u32 idx, u32 cid, u32 *cardword, u32 *aux)
{
    u32 c = *cardword & 0x3FFF;
    (void)side; (void)zone; (void)idx; (void)cid; (void)aux;
    return is_2400_1000(c) && (u32)BASE_ATTR(c) == ATTR;
}

#elif STUB == MP_ADDH
/* Row 0xFFD8 handler: Deck + GY candidates with MP_APRED. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 aux = 0, cid = *(u16 *)row, word = row[2];
    return DECK_WALK(side, cid, APRED_ADDR, (u32)&aux, word, 2) + GY_ENUM(side, cid, APRED_ADDR, (u32)&aux, word, 0x10000);
}

#elif STUB == MP_NSPRED
/* Cry Havoc!'s per-cid hand predicate for 0x0D6A (Escalation's front routes it here): r7(side, zone, index) -> 0x10 for one of the six named Monarchs in the hand. */
ENTRY int entry(u32 side, u32 zone, u32 idx)
{
    if (zone != 0x0B)
        return 0;
    return is_named(HAND_WORD(side & 1, idx) & 0x3FFF) ? 0x10 : 0;
}

#elif STUB == MP_RES
/* +04: 0x80 stamp once-per-turn, pick the opponent's monster (row 0xFFD7); 0x7F read its Attribute, pick the add (row 0xFFD8, Deck + GY); 0x7E move it to the hand (+ shuffle for
 * a Deck pick) and, when a named Monarch in the hand can be Normal Summoned, ask "Normal Summon a Monarch." / "Do not activate effect."; 0x7D yes -> hand the resolver to Cry Havoc!'s
 * Normal Summon machine from its phase 0x80 (DELEG). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, *p, w, zc, i, n, ok;
    int r;
    if (DELEG) {
        r = NS_MACHINE((u32)e, a1);
        if (r == 0)
            DELEG = 0;
        return r;
    }
    switch (RES_PHASE) {
    case 0x80:
        turnlog_post(side, KEY_OPT, 1, 0);
        MODE = 8;
        n = COUNT_FILL(side, MPLAN, 0);
        if (!n) {
            MODE = 0;
            return 0;
        }
        OPEN_PICKER(side, 7, MPLAN, 0);
        return 0x7F;
    case 0x7F:
        MODE = 0;
        if ((s32)PICK_COUNT <= 0)
            return 0;
        p = PICK_FETCH(1);
        zc = *(volatile u16 *)(PICK_ZONE + 2 * (((u32)p - PICK_LIST) >> 2));
        ATTR = (u32)cur_attribute(zc & 1, (zc >> 1) & 0x1F, 0);
        MODE = 9;
        n = COUNT_FILL(side, MPLAN, 0);
        if (!n) {
            MODE = 0;
            return 0;
        }
        OPEN_PICKER(side, 7, MPLAN, 0);
        return 0x7E;
    case 0x7E:
        MODE = 0;
        if ((s32)PICK_COUNT <= 0)
            return 0;
        p = PICK_FETCH(1);
        w = *p;
        zc = *(volatile u16 *)(PICK_ZONE + 2 * (((u32)p - PICK_LIST) >> 2));
        CHAIN_OPEN();
        if (((zc >> 1) & 0x1F) == 0xE) {
            n = GY_COUNT(side);
            for (i = 0; i < n; i++)
                if (GYW(side, i) == w) {
                    GY2HAND((u32)e, side, (u32)&GYW(side, i));
                    break;
                }
        } else {
            DECK2HAND(side, (u32)p);
            SHUFFLE(side);
        }
        CHAIN_CLOSE();
        ok = 0;
        n = HAND_COUNT(side);
        for (i = 0; i < n; i++) {
            w = HAND_WORD(side, i);
            if (is_named(w & 0x3FFF) && (CAN_SUMMON(side, (((w << 1) >> 24) << 1) + ((w << 17) >> 31)) & 0x10))
                ok = 1;
        }
        if (!ok)
            return 0;
        MENU((u32)e, 0x103, L_NS, 0x1AC, 0, 0, 3);
        return 0x7D;
    case 0x7D:
        if (MENU_ANSWER != 0)
            return 0;
        DELEG = 1;
        return 0x80;
    default:
        return 0;
    }
}

#else
#error "build with -DSTUB=MP_COND|MP_RES|MP_TGTH|MP_ADDH|MP_APRED|MP_NSPRED"
#endif

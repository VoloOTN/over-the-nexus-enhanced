/* Block Dragon (0x0FDD, donor Giant Flea). Facts / design: notes/block-dragon-findings.md.
 *   C1  hand cls2 (VIRTUAL record): COND here; COST + picker + handler are hand-written asm in the module (Double Evolution
 *       Pill's in-game-confirmed protocol, 3 picks); RES is the native hand self-SS resolver 0x02206ABD.
 * Build with -DSTUB=C1COND. */
#include "disguise.h"

#define BD           0x0FDD
#define HAND_ZONE    0x0B
#define GY_ZONE      0x0E
#define ATTR_EARTH   5            /* engine numbering LIGHT 1 DARK 2 WATER 3 FIRE 4 EARTH 5 WIND 6 (fusion_material.yaml) */
#define HAND_COUNT(side) (*(volatile u32 *)(PLAYER(side) + 0x0C))
#define HAND_WORD(side, i) (*(volatile u32 *)(PLAYER(side) + 0x124 + 4 * (i)))

#define C1COND 1

static inline int is_earth_monster(u32 cid)
{
    return cid && is_monster(cid) && fn_0202ABC8(cid) == ATTR_EARTH;
}

/* EARTH monsters in side's hand and GY, THIS CARD INCLUDED (it is an EARTH monster in the hand). */
static inline u32 count_earth(u32 side)
{
    u32 n = 0, i, cnt;
    cnt = HAND_COUNT(side);
    for (i = 0; i < cnt; i++) {
        if (is_earth_monster(CID(HAND_WORD(side, i))))
            n++;
    }
    cnt = GY_COUNT(side);
    for (i = 0; i < cnt; i++) {
        if (is_earth_monster(GY_CID(side, i)))
            n++;
    }
    return n;
}

#if STUB == C1COND
/* hand only; a free Monster Zone; the 3 cards to banish must be OTHER than this card, and this card is itself an EARTH monster in
 * the hand, so the pool (hand + GY, this card included) must hold >= 4. */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    if (d[3] != HAND_ZONE && d[3] != GY_ZONE)       /* the hand record and the GY record share this gate */
        return 0;
    if (!fn_021AD870(d[2], 0, 0))
        return 0;
    if (count_earth(d[2]) < 4)
        return 0;
    return 2;
}
#endif

#define C2 4
#if STUB == C2
/* C2: "Rock monsters you control cannot be destroyed, except by battle."  Hook = the survive check 0x021CC028's default exit (r0 side, r1 zone,
 * r2 = the destroyed card's cid), proven 2026-11-09 to be reached by card-effect destruction (mode 0x10003) and NOT by battle (mode 0x7).
 * 1 = this card survives.  The destroyed card must be a face-up Rock in a Monster Zone and its controller must have a face-up Block Dragon
 * (Block Dragon itself qualifies: it is a Rock). */
#define RACE_ROCK 6
ENTRY int entry(u32 side, u32 zone, u32 cid)
{
    u32 z;
    if (zone > 4 || !ZONE_FACEUP(side, zone))
        return 0;
    if (get_race(cid) != RACE_ROCK)
        return 0;
    for (z = 0; z <= 4; z++) {
        if (ZONE_FACEUP(side, z) && zone_cid_at(side, z) == BD)
            return 1;
    }
    return 0;
}
#endif

/* ======================================================================================================================
 * C3: "If this card is sent from the field to the GY: You can add up to 3 Rock monsters from your Deck to your hand, whose total Levels
 *      equal 8. You can only use this effect of 'Block Dragon' once per turn."
 * Blueprint = Eva (in-game confirmed): virtual cls2 record {RES, 0, COND, native 'You can', COST}, leave-mask row, never-miss front,
 * picker loop in RES with the native add-to-hand mover.  State in the cls2 descriptor (scratch confirmed free by Eva + BD C1):
 *   +0x12 remaining Level  +0x14 / +0x16 refs of the picks made (0xFFFF none)  +0x18 magic 0xC3C3 (state valid)  +0x1A picks made
 * The candidate predicate keeps a Rock only if a completion to exactly the remaining total still exists with the picks left.
 * ====================================================================================================================== */
#define C3COND 5
#define C3COST 6
#define C3PRED 7
#define C3_KIND   1
#define C3_MAGIC  0xC3C3
#define NONE_REF  0xFFFF
#define ROCK      6
#define ACT_DESC  (*(volatile u32 *)(0x0229A9FC + 0x50))
#define DECK_N(side)    (*(volatile u32 *)(0x0229ACA4 + ((side) & 1) * 0xB3C))
#define DECK_W(side, i) (*(volatile u32 *)(PLAYER(side) + 0x304 + 4 * (i)))

static inline u32 ref_of(u32 w)
{
    return ((w >> 14) & 1) + (((w << 1) >> 24) << 1);
}

/* can the remaining total r be reached with at most k more distinct Rocks?  cnt[l] = Rocks of Level l still free. */
static __attribute__((unused)) int f(u8 *cnt, u32 r, u32 k)
{
    u32 l;
    if (r == 0)
        return 1;
    if (k == 0)
        return 0;
    for (l = 1; l <= 8 && l <= r; l++) {
        if (cnt[l]) {
            int ok;
            cnt[l]--;
            ok = f(cnt, r - l, k - 1);
            cnt[l]++;
            if (ok)
                return 1;
        }
    }
    return 0;
}

/* Rocks in side's Deck by Level, skipping up to three refs. */
static __attribute__((unused)) int feas(u32 side, u32 r, u32 k, u32 ref1, u32 ref2, u32 skip)
{
    u8 cnt[9];
    u32 i, n = DECK_N(side);
    for (i = 0; i < 9; i++) {
        cnt[i] = 0;
        __asm__ volatile("");           /* keep the loop a loop: no memset in a freestanding stub */
    }
    for (i = 0; i < n; i++) {
        u32 w = DECK_W(side, i), c = CID(w), ref = ref_of(w), l;
        if (!c || ref == ref1 || ref == ref2 || ref == skip)
            continue;
        if (!is_monster(c) || get_race(c) != ROCK)
            continue;
        l = cid_level(c);
        if (l >= 1 && l <= 8 && cnt[l] < 255)
            cnt[l]++;
    }
    return f(cnt, r, k);
}

#if STUB == C3COND
/* +0C (desc, arg): the cost already ran -> pass; else once per turn not yet used AND the Deck holds a legal selection (1-3 Rocks, total Level 8). */
ENTRY int entry(EffectCtx *e)
{
    u32 side;
    if (e->cost_ran)
        return 1;
    if (turnlog_query(e->controller, 0x0B, e->cid, C3_KIND))
        return 0;
    side = e->controller ^ e->slot_phase;
    return feas(side, 8, 3, NONE_REF, NONE_REF, NONE_REF);
}
#endif

#if STUB == C3COST
/* +14: stamp the once-per-turn lock (only a Yes reaches the cost) and open the pick state. */
ENTRY int entry(EffectCtx *e)
{
    volatile u16 *d = (volatile u16 *)e;
    turnlog_post(e->controller, e->cid, C3_KIND, 0);
    d[0x12 / 2] = 8;
    d[0x14 / 2] = NONE_REF;
    d[0x16 / 2] = NONE_REF;
    d[0x18 / 2] = C3_MAGIC;
    d[0x1A / 2] = 0;
    return 1;
}
#endif

#if STUB == C3PRED
/* Deck-builder candidate filter (r0 side, r1 zone, r2 idx, r3 row cid, [sp] &card word, [sp+4] list): keep a Rock only if the effect can
 * still finish at exactly Level 8 with it.  Outside the running C3 (menu-time counts) the state is the fresh one: total 8, 3 picks. */
ENTRY int entry(u32 side, u32 zone, u32 idx, u32 rowcid, volatile u32 *wp, u32 list)
{
    volatile u16 *d = (volatile u16 *)ACT_DESC;
    u32 w = *wp, c = CID(w), r = 8, k = 3, ref1 = NONE_REF, ref2 = NONE_REF, l;
    if (d && d[0] == BD && d[0x18 / 2] == C3_MAGIC) {
        r = d[0x12 / 2];
        k = 3 - d[0x1A / 2];
        ref1 = d[0x14 / 2];
        ref2 = d[0x16 / 2];
    }
    if (!c || !is_monster(c) || get_race(c) != ROCK || ref_of(w) == ref1 || ref_of(w) == ref2)
        return 0;
    l = cid_level(c);
    if (l < 1 || l > r || k == 0)
        return 0;
    return feas(side, r - l, k - 1, ref1, ref2, ref_of(w));
}
#endif

/* Domain of the True Monarchs (Field Spell, donor Sogen 0x10F3).  Build with -DSTUB=DM_BONUS|DM_COND3|DM_COST3|DM_RES3|DM_PRED.
 *   "While you have no cards in your Extra Deck and you are the only player that controls a Tribute Summoned monster, your opponent cannot Special Summon
 *    monsters from the Extra Deck. If a Tribute Summoned monster you control attacks an opponent's monster, it gains 800 ATK during damage calculation
 *    only. Once per turn: You can reduce the Level of 1 monster with 2800 ATK and 1000 DEF in your hand by 2 until the end of this turn (even after they
 *    are Summoned/Set, and even if this card leaves the field)."
 * D1 lives in edlock.c.  Proofs: notes/domain-strike-findings.md. */
#include "disguise.h"

#define DM_BONUS 1
#define DM_COND3 2
#define DM_COST3 3
#define DM_RES3  4
#define DM_PRED  5

#define DOMAIN            0x10F3
#define FIELD_ZONE        10
#define ZONE_FLAGS(s, z)  (*(volatile u32 *)(ZONE_REC(s, z) + 0x10))      /* zone word + 0x44 */
#define TRIBUTE_SUMMONED  0x8
#define BATTLE            0x02298AD8                                      /* +0 attacker side, +2 direct-attack flag, +8 attacker zone (s16) */
#define HAND_COUNT(s)     (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_WORD(s, i)   (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)))
#define IS_MONSTER        ((int (*)(u32))0x02029E61)
#define ATK_GET           ((int (*)(u32))0x0202AC49)                      /* printed ATK by cid */
#define DEF_GET           ((int (*)(u32))0x0202AC29)                      /* printed DEF by cid */
#define STAR_BLAST_KEY    0x1F6A                                          /* hand + field Level DELTA rider key (0x021B20AC / 0x021B807C) */

static inline int domain_faceup(u32 side)
{
    return ZONE_FACEUP(side, FIELD_ZONE) && CID(ZONE_WORD(side, FIELD_ZONE)) == DOMAIN;
}

static inline int is_2800_1000(u32 cid)
{
    return cid && IS_MONSTER(cid) && ATK_GET(cid) == 2800 && DEF_GET(cid) == 1000;
}

#if STUB == DM_BONUS
/* D2, called by the 0x02197A14 front inside the battle calculator 0x02196A28 (real battles: mode 0 via the thunk 0x02197D08): host = the calculator's sp,
 * off = r4 (attacker entry offset into host+0x10C), side = r6 (attacker side).  Skyscraper's +1000 is added at the same point with the same scaling. */
ENTRY void entry(u8 *host, u32 off, u32 side)
{
    volatile signed char *bs = (volatile signed char *)BATTLE;
    u32 zone = (u32)(*(volatile s16 *)(BATTLE + 8)), i;
    s32 bonus = 800, sh = *(volatile s32 *)(host + 0xF4);
    side &= 1;
    if (bs[2] != 0 || zone > 4)                          /* direct attack: "attacks an opponent's monster" only */
        return;
    if (!domain_faceup(side))
        return;
    if (!ZONE_FACEUP(side, zone) || !(ZONE_FLAGS(side, zone) & TRIBUTE_SUMMONED))
        return;
    for (i = 0; (s32)i < -sh; i++)                       /* 0x02197A26..0x02197A44: doubled per negative step, halved (rounding up) per positive step */
        bonus <<= 1;
    for (i = 0; (s32)i < sh; i++)
        bonus = (bonus + 1) >> 1;
    *(volatile s32 *)(host + 0x10C + off) += bonus;
}

#elif STUB == DM_PRED
/* Picker predicate pred(side, zone, index) for the D3 resolver (Star Blast's 0x0222B398 shape): own hand card with printed 2800 ATK / 1000 DEF -> 0x800. */
ENTRY int entry(u32 side, u32 zone, u32 idx)
{
    u8 *desc = *(u8 **)(0x0229A9FC + 0x50);
    if (side != (u32)(desc[2] ^ desc[6]) || zone != 0xB || idx >= HAND_COUNT(side))
        return 0;
    return is_2800_1000(CID(HAND_WORD(side, idx))) ? 0x800 : 0;
}

#elif STUB == DM_COND3
/* cls3 +0C: once per turn (menu check), a 2800/1000 monster in your hand, then the vanilla ignition check (Mystic Piper's recipe). */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, i, n = HAND_COUNT(side), ok = 0;
    if (!e->cost_ran && turnlog_query(e->controller, 0xB, DOMAIN, 1))
        return 0;
    for (i = 0; i < n; i++) {
        if (is_2800_1000(CID(HAND_WORD(side, i)))) {
            ok = 1;
            break;
        }
    }
    if (!ok && !e->cost_ran)
        return 0;
    return can_take_ignition((u32)e);
}

#elif STUB == DM_COST3
/* cls3 +10: stamp the once-per-turn node on the first cost step. */
ENTRY int entry(EffectCtx *e)
{
    if (*(volatile u32 *)(0x0229AAFC + 0x7C) == 0)
        turnlog_post(e->controller, DOMAIN, 1, 0);
    return 1;
}

#elif STUB == DM_RES3
#ifndef PRED_ADDR
#error "pass -DPRED_ADDR=<DM_PRED slot | 1>"
#endif
/* cls3 +04, Star Blast 0x0222B3E4's phases: 0x80 opens the picker over the predicate; 0x7F takes the pick, reveals it and attaches the {0x1F6A, kind 3,
 * value 2} Level rider to the card INSTANCE (0x021C4814), which both the hand reader and the field getter honour. */
#define PHASE      (*(volatile u32 *)(0x0229AAFC + 0x70))
#define MSG        ((void (*)(u32, u32))0x0219A819)
#define PICK_OPEN  ((void (*)(u32, u32, u32, u32))0x0224B9F1)
#define PICK_DONE  ((int (*)(void))0x0224BBB1)
#define REVEAL     ((void (*)(u32, u32))0x021D2599)
#define INST_RIDER ((void (*)(u32, u32, u32, u32))0x021C4815)
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, zone, pside, idx, w, ref;
    if (PHASE == 0x80) {
        MSG(side, 0x6F);
        PICK_OPEN(side, DOMAIN, 0, PRED_ADDR);
        return 0x7F;
    }
    if (PHASE == 0x7F) {
        if (!PICK_DONE())
            return 0x80;
        zone = *(volatile u32 *)(0x0229DD94 + 0x7C);
        pside = *(volatile u32 *)(0x0229DD94 + 0x78) & 1;
        idx = *(volatile u32 *)0x0229DE14;
        if (zone != 0xB || idx >= HAND_COUNT(pside))
            return 0;
        w = HAND_WORD(pside, idx);
        ref = ((w >> 14) & 1) + (((w >> 23) & 0xFF) << 1);
        REVEAL(pside, ref);
        INST_RIDER(ref, STAR_BLAST_KEY, 3, 2);
        return 0;
    }
    return 0;
}

#else
#error "build with -DSTUB=DM_BONUS|DM_COND3|DM_COST3|DM_RES3|DM_PRED"
#endif

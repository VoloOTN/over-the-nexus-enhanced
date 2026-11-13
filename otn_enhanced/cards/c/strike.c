/* Strike of the Monarchs (Quick-Play Spell, donor Speed Spell - Offerings to the Doomed 0x0DE4).  Build with -DSTUB=ST_FILT|ST_TGT|ST_RES.
 *   "You can Tribute 1 face-up Level 5 or higher Normal Summoned/Set monster, then target 1 face-up card on the field; negate its effects, then draw 1
 *    card. (The effects remain negated until the end of this turn.) ..."
 * Shape = Gemini Spark 0x212A's cls0 {RES, +08 0x021DE309, COND 0x021F069D, COST 0x021E7C89, SEL 0x02234DA5}: ONE +08 filter serves the Tribute cost
 * (desc[+7] == 0) and the target selection (desc[+7] != 0), exactly as 0x021DE308 does.  Design + proofs: notes/domain-strike-findings.md. */
#include "disguise.h"

#define ST_FILT 1
#define ST_TGT  2
#define ST_RES  3
#define ST_COND 4
#define ST_COND2 5
#define ST_SEL2  6
#define ST_RES2  7

#define STRIKE            0x0DE4
#define ZONE_FLAGS(s, z)  (*(volatile u32 *)(ZONE_REC(s, z) + 0x10))      /* zone word + 0x44 */
#define SPECIAL_SUMMONED  0x10                                           /* flag bit 4 (monarch-megas Session 5: SS 0x110 / 0x440110, NS 0x410100) */
#define MASK_OWN_FACEUP_MONSTER 0x0C15                                    /* Awaken / Battle-Scarred's own-side face-up monster mask */
#define MASK_FACEUP_CARD  0x21874                                         /* Saber Slash 0x209C: "face-up cards on the field" */
#define COUNT_LEFT ((int (*)(u32, u32, u32))0x0224AB45)                   /* (desc, filter, excluded loc zone<<8|side) -> candidates left */

#if STUB == ST_FILT
#ifndef TGT_ADDR
#error "pass -DTGT_ADDR=<ST_TGT slot | 1>"
#endif
/* cls0 +08 (desc, side, zone).  Cost phase: an own face-up Level 5+ monster that was not Special Summoned, provided a target is left after Tributing it.
 * Target phase: any face-up card on the field. */
ENTRY int entry(u8 *desc, u32 side, u32 zone)
{
    if (desc[7])
        return zone_predicate((u32)desc, side, zone, MASK_FACEUP_CARD);
    if (zone > 4 || !zone_predicate((u32)desc, side, zone, MASK_OWN_FACEUP_MONSTER))
        return 0;
    if (ZONE_FLAGS(side, zone) & SPECIAL_SUMMONED)
        return 0;
    if (level_of_zone(side, zone) < 5)
        return 0;
    return COUNT_LEFT((u32)desc, TGT_ADDR, ((zone & 0xFF) << 8) | (side & 0xFF)) >= 1;
}

#elif STUB == ST_TGT
/* The target filter alone (handed to the candidate counter by ST_FILT's cost branch). */
ENTRY int entry(u8 *desc, u32 side, u32 zone)
{
    return zone_predicate((u32)desc, side, zone, MASK_FACEUP_CARD);
}

#elif STUB == ST_COND
/* cls0 +0C.  Gemini Spark's 0x021F069C asks the per-cid draw-count table 0x022704A4 (0x0DE4 is not in it -> always 0: CPU trace 2026-11-11 saw no
 * FILT call in 3 duels), then 0x021BAE30(desc[2] ^ desc[6], n).  Same tail with n = 1. */
#define CAN_DRAW ((int (*)(u32, u32))0x021BAE31)
ENTRY int entry(u8 *desc)
{
    return CAN_DRAW(desc[2] ^ desc[6], 1);
}

#elif STUB == ST_COND2
/* S4 virtual cls2 +0C (the GY-action enumerator only offers it from the GY).  Code 2 = activatable with no target sweep.  Also no Deck-out issue. */
ENTRY int entry(EffectCtx *e)
{
    (void)e;
    return 2;
}

#elif STUB == ST_SEL2
/* S4 virtual cls2 +14: "declare 1 Attribute" — DNA Transplant 0x171F's selector 0x022378E4 without its on-field self check:
 * phase [0x0229AB7C] 0 -> picker 0x02259A9C(side, cid, 1, 0xFF); 1 -> append the answer [0x0229DE94+8] to desc (+0x12 count / +0x14 values, 0x022345F4)
 * and announce it (0x021C3BC8(8 | side<<15, 4, attr, 0), DNA's own call); then 1 = done. */
#define SEL_PHASE   (*(volatile u32 *)0x0229AB7C)
#define DECLARE     ((void (*)(u32, u32, u32, u32))0x02259A9D)
#define ANSWER      (*(volatile u16 *)(0x0229DE94 + 8))
#define APPEND      ((void (*)(u32, u32))0x022345F5)
#define ENGINE_CMD  ((void (*)(u32, u32, u32, u32))0x021C3BC9)
ENTRY int entry(u8 *desc)
{
    u32 side = desc[2], attr;
    if (SEL_PHASE == 0) {
        DECLARE(side, *(u16 *)desc, 1, 0xFF);
        SEL_PHASE = SEL_PHASE + 1;
        return 0;
    }
    if (SEL_PHASE == 1) {
        attr = ANSWER;
        APPEND((u32)desc, attr);
        ENGINE_CMD((8 | (side ? 0x8000 : 0)) & 0xFFFF, 4, attr & 0xFFFF, 0);
        SEL_PHASE = SEL_PHASE + 1;
        return 0;
    }
    return 1;
}

#elif STUB == ST_RES2
/* S4 virtual cls2 +04, one phase: every face-up monster on the field gets Genex Ally Changer's Attribute rider (key 0x2167, read by cur_attribute
 * 0x021B8E48) with the declared Attribute (desc +0x14), KIND 2 = until the end of this turn.  Same calls Genex's poster 0x02207908 makes for kind < 6:
 * skip a monster that is unaffected (0x021AFCBC(desc, side, zone) != 0), else rider_attach(side, zone, key, kind, value). */
#define GENEX       0x2167
#define UNAFFECTED  ((int (*)(u32, u32, u32))0x021AFCBD)
ENTRY int entry(u8 *desc)
{
    u32 s, z, attr = *(volatile u16 *)(desc + 0x14);
    if (*(volatile u16 *)(desc + 0x12) == 0)
        return 0;
    for (s = 0; s <= 1; s++) {
        for (z = 0; z <= 4; z++) {
            if (!ZONE_FACEUP(s, z) || !CID(ZONE_WORD(s, z)))
                continue;
            if (UNAFFECTED((u32)desc, s, z))
                continue;
            rider_attach(s, z, GENEX, KIND_UNTIL_EP, attr);
        }
    }
    return 0;
}

#elif STUB == ST_RES
/* cls0 +04, one phase: the target must still be legal; it gets a kind-2 rider keyed 0x0DE4 (kind 2 = freed by the end-of-turn sweep 0x0219F9E0),
 * which the negate reader honours through the module's PREB precheck; then draw 1. */
ENTRY int entry(EffectCtx *e)
{
    u32 loc, ts, tz;
    if (!pick_validate((u32)e, 0, &loc))
        return 0;
    ts = loc & 0xFF;
    tz = (loc >> 8) & 0xFF;
    if (!revalidate((u32)e, ts, tz))
        return 0;
    rider_attach(ts, tz, STRIKE, KIND_UNTIL_EP, 0);
    draw(e->controller, 1);
    return 0;
}

#else
#error "build with -DSTUB=ST_FILT|ST_TGT|ST_RES|ST_COND|ST_COND2|ST_SEL2|ST_RES2"
#endif

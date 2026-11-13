/* Frost Blast of the Monarchs (0x14C3, donor Double Snare).  Build with -DSTUB=FB_COND|FB_COND2|FB_COST2.
 *   C1 (Normal Spell): "If you control a monster with 2400 or more ATK and 1000 DEF: Target 1 Set card on the field; destroy it."
 *      cls0 {+04 0x02204899 (native 'destroy target 0'), +08 0x021DFD1D (Granmarg the Rock Monarch's 'Set card' filter), +0C FB_COND, +14 0x02234DA5 (single-target selector)}.
 *   C2 (Graveyard): "You can banish this card and 1 "Monarch" Spell/Trap Card from your Graveyard, then target 1 Set card on the field; destroy it."
 *      cls2 {+04 0x02204899, +08 0x021DFD1D, +0C FB_COND2, +10 FB_COST2, +14 0x02234DA5} + a virtual GY-action row.
 * UNPROVEN list and the printed-vs-current ATK/DEF gap: notes/frostblast-findings.md. */
#include "disguise.h"

#define FB_COND  1
#define FB_COND2 2
#define FB_COST2 3

#define FROSTBLAST    0x14C3
#define MONARCH_SET   0x6D
#define HAND_DUMMY    0
typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
#define ATK_GET       ((fn1)0x0202AC49)     /* printed ATK by cid (Return's predicate uses it) */
#define DEF_GET       ((fn1)0x0202AC29)     /* printed DEF by cid */
#define HAS_SET_CODE  ((fn2)0x020240D9)
#define BANISH_COST   ((fn2)0x021E5319)     /* Survival Instinct's native banish cost: the GY row picks 1, exactly 1 for an unlisted cid */
#define SELF_BANISH   ((fn1)0x021E5709)     /* native "banish this card from your GY" */

#if STUB == FB_COND
/* cls0 +0C: you control a face-up monster with ATK >= 2400 and DEF == 1000 (PRINTED values: the cid getters; the printed text says "ATK" / "DEF").  1 = activatable if the
 * +08 sweep finds a Set card. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, z;
    for (z = 0; z <= 4; z++) {
        u32 cid;
        if (!ZONE_FACEUP(side, z))
            continue;
        cid = CID(ZONE_WORD(side, z));
        if (cid && ATK_GET(cid) >= 2400 && DEF_GET(cid) == 1000)
            return 1;
    }
    return 0;
}

#elif STUB == FB_COND2
/* cls2 +0C (menu time): another "Monarch" Spell/Trap Card is in your Graveyard.  1 = activatable if the +08 sweep finds a Set card. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller, i, n = GY_COUNT(side), seen_self = 0;
    if (e->cost_ran)
        return 1;
    for (i = 0; i < n; i++) {
        u32 cid = GY_CID(side, i);
        if (cid == FROSTBLAST && !seen_self) {      /* this card itself (one copy) does not count as the other Monarch card */
            seen_self = 1;
            continue;
        }
        if (cid && HAS_SET_CODE(cid, MONARCH_SET))
            return 1;
    }
    return 0;
}

#elif STUB == FB_COST2
/* cls2 +10: the native banish cost for 1 other Monarch Spell/Trap from the GY (virtual GY row), then banish this card.  0 = pending, 1 = done, < 0 = abort. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = BANISH_COST((u32)e, a1);
    if (r > 0)
        SELF_BANISH((u32)e);
    return r;
}

#else
#error "build with -DSTUB=FB_COND|FB_COND2|FB_COST2"
#endif

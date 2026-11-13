/* Edea the Heavenly Squire (0x0FDC, donor Gokibore).  Build with -DSTUB=ED_COND|ED_COST|ED_RES|ED_COND2|ED_RES2|ED_SEL2 -DDATA=<ov5 data address>.
 *   C1 "If this card is Normal or Special Summoned: You can Special Summon 1 monster with 800 ATK and 1000 DEF from your Deck in Defense Position, except 'Edea the Heavenly
 *       Squire', also you cannot Special Summon monsters from the Extra Deck for the rest of this turn."
 *   C2 "If this card is sent to the Graveyard: You can target 1 of your banished 'Monarch' Spell/Trap Cards; add it to your hand."  Each effect once per turn.
 * C1 = cls1 {RES, 0, COND, native "You can" prompt 0x021E51E5, COST} on the shared N-or-SS hook; RES replays the native Deck Special Summon machine's DEFAULT arm (0x02206CAC, phases
 * 0x80 .. 0x78) but with the Defense Position argument (the native default lets the player choose), then posts the Extra Deck lock node (key 0x5DCD, the one edlock.c tests).
 * C2 = cls2 leave record {native add-target resolver 0x02208181 via RES2, 0, COND2, "You can", the native off-field picker 0x02235605 via SEL2}; the banished-Monarch row is
 * chosen by DATA mode 1, which every C2 entry point sets (and every C1 entry point clears).  Design + UNPROVEN list: notes/edea-findings.md. */
#include "disguise.h"

#define ED_COND  1
#define ED_COST  2
#define ED_RES   3
#define ED_COND2 4
#define ED_RES2  5
#define ED_SEL2  6

#define EDEA      0x0FDC
#define KEY_OPT1  0x0FDC                  /* kind-1 turn-log keys (slot 0xB): effect 1 used / effect 2 used; the Extra Deck lock reuses Revolt's key (edlock.c tests it) */
#define KEY_OPT2  0x5FDC
#define KEY_LOCK  0x5DCD
#define STATE     0x0229AAFC
#define MODE      (*(volatile u32 *)(DATA + 0x0))

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn4)(u32, u32, u32, u32);
typedef int (*fn5)(u32, u32, u32, u32, u32);
#define GATE1       ((fn1)0x021AD871)     /* the native Deck-SS machine's three Special Summon gates (nonzero = allowed) */
#define GATE2       ((fn1)0x021B9ECD)
#define GATE3       ((fn1)0x021B9ED9)
#define PARAM       ((fn1)0x02234E79)     /* row_param_provider */
#define COUNT       ((fn3)0x02243FA9)     /* (side, cid, param): number of matching candidates */
#define SHOW_MSG    ((fn2)0x0219A819)
#define PICKER      ((fn4)0x0219C431)     /* (side, code, cid, param): code 6 = pick 1 from the Deck */
#define POS_LOC     ((int (*)(void))0x0219C511)
#define SUMMON      ((fn5)0x0226925D)     /* (side, loc, 1, position, (cid << 16) | 0): position 0 Attack, 1 Defense, 2 the player chooses */
#define SHOW_OPP    ((fn1)0x0225BF31)
#define SHUFFLE     ((fn1)0x021D269D)
#define ADD_TARGET  ((fn2)0x02208181)     /* native 'add the targeted card to your hand' resolver (Laval Lancelord / Dimensional Alchemist) */
#define PICK_OFF    ((fn2)0x02235605)     /* native off-field target picker (+14 selector) */
#define PROBE       ((fn1)0x021F05A9)     /* criteria_probe: the Laval Lancelord cond */

/* the criteria side of a probe is desc[+2] ^ desc[+6] (dispatch.criteria_probe_side_is_xor) */
static inline u32 eff_side(EffectCtx *e) { return (e->controller ^ e->slot_phase) & 1; }

static inline int can_summon(u32 side) { return GATE1(side) && GATE2(side) && GATE3(side); }

#if STUB == ED_COND
/* cls1 +0C: once per turn, a legal Special Summon, and a Deck monster with 800 ATK / 1000 DEF (not Edea).  2 = unconditional. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = eff_side(e);
    if (opt_used(e, KEY_OPT1))
        return 0;
    if (!can_summon(side))
        return 0;
    MODE = 0;
    if (criteria_count(side, EDEA, 0, 0) < 1)
        return 0;
    return 2;
}

#elif STUB == ED_COST
/* cls1 +14 (after the native "You can" prompt said yes): stamp the once-per-turn node at cost step 0. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, KEY_OPT1, 1, 0);
    return 1;
}

#elif STUB == ED_RES
/* cls1 +04: the native Deck Special Summon machine's default arm, with Defense Position, then the Extra Deck lock. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = eff_side(e), cid = e->cid;
    (void)a1;
    switch (*(volatile u32 *)(STATE + 0x70)) {
    case 0x80:
        MODE = 0;
        if (!can_summon(side))
            return 0;
        if (!COUNT(side, cid, PARAM((u32)e))) {
            SHOW_MSG(side, 0x0D);
            return 0x7B;
        }
        return 0x7F;
    case 0x7F:
        SHOW_MSG(side, 0x30);
        return 0x7E;
    case 0x7E:
        PICKER(side, 6, cid, PARAM((u32)e));
        return 0x7C;
    case 0x7C:
        SUMMON(side, POS_LOC(), 1, 1, cid << 16);
        return 0x78;
    case 0x7B:
        SHOW_OPP(1 - side);
        return 0x78;
    case 0x78:
        SHUFFLE(side);
        turnlog_post(e->controller, KEY_LOCK, 1, 0);
        return 0x64;
    default:
        return 0;
    }
}

#elif STUB == ED_COND2
/* cls2 +0C: once per turn clear and a banished Monarch Spell/Trap exists (the native criteria probe over the banished row). */
ENTRY int entry(EffectCtx *e)
{
    MODE = 1;
    if (opt_used(e, KEY_OPT2))
        return 0;
    return PROBE((u32)e);
}

#elif STUB == ED_RES2
/* cls2 +04: stamp the once-per-turn node at the first phase, then the native add-target resolver. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    MODE = 1;
    if (*(volatile u32 *)(STATE + 0x70) == 0x80)
        turnlog_post(e->controller, KEY_OPT2, 1, 0);
    return ADD_TARGET((u32)e, a1);
}

#elif STUB == ED_SEL2
/* cls2 +14: the native off-field target picker over the banished row. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    MODE = 1;
    return PICK_OFF((u32)e, a1);
}

#else
#error "build with -DSTUB=ED_COND|ED_COST|ED_RES|ED_COND2|ED_RES2|ED_SEL2 -DDATA=<addr>"
#endif

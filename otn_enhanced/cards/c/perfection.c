/* Monarchic Perfection (0x12F6, donor Call of the Grave converted to a Continuous Trap).  TEST ROM, NOT SHIPPED, nothing in-game confirmed.
 * Build with -DSTUB=PF_COND|PF_COST|PF_RES|PF_FROWH -DEBDATA=<erebus DATA> -DPFDATA=<perfection DATA> -DL0..L5,LMORE=<dlg_text ids>.
 *
 * "Once per Chain, if your opponent Special Summons a monster(s), and you control a Tribute Summoned monster (except during the Damage Step): You can banish 1 "Monarch"
 *  Spell/Trap from your GY, then activate 1 of these effects (but you can only use each effect of "Monarchic Perfection" once per turn); [six effects]"
 *
 * Trigger: Everliving Underworld Cannon's poster (bl 0x022443C8 @0x0226658A) is fronted to post event 5 for 0x12F6 too (cards/erebus.py PF_TRIG).
 * cls1 {+04 PF_RES, +0C PF_COND, +10 0x021E51E5 ("You can"), +14 PF_COST}.  Rows (erebus.py ROWS, picked by its H2 front): 0xFFEA = GY "Monarch" S/T (the cost,
 * MODE 7), 0xFFEB = field candidates for the chosen effect (PF_FROWH, any other MODE).
 * The six-way choice = the native four-option menu 0x0219ABB4 twice: page 1 = effects 1-3 + "Show other effects.", page 2 = effects 4-6 (labels appended to dlg_text).
 * KNOWN DEVIATIONS: "once per Chain" and "except during the Damage Step" are not enforced; targets are chosen at resolution (the printed effects do not target, so this matches). */
#include "disguise.h"

#define PF_COND  1
#define PF_COST  2
#define PF_RES   3
#define PF_FROWH 4

typedef int (*fn1)(u32);
typedef int (*fn2)(u32, u32);
typedef int (*fn3)(u32, u32, u32);
typedef int (*fn4)(u32, u32, u32, u32);
typedef int (*fn7)(u32, u32, u32, u32, u32, u32, u32);

#define PERF          0x12F6
#define MONARCH_SET   0x6D
#define STATE         0x0229AAFC          /* +0x70 resolver phase */
#define RES_PHASE     (*(volatile u32 *)(STATE + 0x70))
#define MODE          (*(volatile u32 *)(EBDATA + 0x4))   /* erebus.py's H2 row selector: 7 = Perfection's cost row */
#define CHOICE        (*(volatile u32 *)(PFDATA + 0x0))   /* 0..5 = the chosen effect */
#define PAGE          (*(volatile u32 *)(PFDATA + 0x4))
#define MASK          (*(volatile u32 *)(PFDATA + 0x8))   /* the usable-effect mask computed at phase 0x80 */
#define FLAGS(s, z)   (*(volatile u32 *)(0x0229ACD8 + ((s) & 1) * 0xB3C + (z) * 0x14))   /* zone flag word: bit 3 = Tribute Summoned */
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define PICK_LIST     0x02299458
#define PICK_ZONE     0x02299908
#define PICK_COUNT    (*(volatile u32 *)(0x0229DD94 + 0x34))
#define MENU_ANSWER   (*(volatile u32 *)(0x0229DD94 + 0x34))  /* 0-based (effect_dispatch_tables: 0x0219ABB4 is a four-option menu) */
#define RNG_SEED      (*(volatile u32 *)(0x0229DD14 + 0x28))
#define ADD_CAND      ((fn3)0x02243B2D)
#define COUNT_FILL    ((fn3)0x02243FA9)
#define OPEN_PICKER   ((fn4)0x0219C431)
#define PICK_FETCH    ((u32 *(*)(u32))0x0219C94D)
#define HAND_TO_GY    ((fn2)0x021C6DB5)            /* (side, hand index) */
#define BANISH_COST   ((fn2)0x021E5319)
#define MENU          ((fn7)0x0219ABB5)            /* (desc, prompt, label0, label1, [sp] label2, [sp+4] label3, [sp+8] mask) */
#define TO_DECK_TOP   ((fn3)0x021CF591)            /* (desc, side, zone): Phoenix Wing Wind Blast's 'place on top of the Deck' (resolver 0x022049C8) */
#define FIELD_BANISH  ((fn3)0x021CF43D)            /* (desc, side, zone): Dark Core's field banish */
#define HAS_SET_CODE  ((fn2)0x020240D9)
#define KEY(i)        (0x52F6 + 0x1000 * (i))      /* once per turn, per effect */

/* Is (s, z) a legal pick for effect `c`? 0 monster, 1 Spell/Trap (S/T zones + Field), 3 face-down card, 4 / 5 any card on the field. */
static inline int pf_ok(u32 c, u32 s, u32 z)
{
    if (!CID(ZONE_WORD(s, z)))
        return 0;
    switch (c) {
    case 0: return z <= 4;
    case 1: return z >= 5;
    case 3: return !ZONE_FACEUP(s, z);
    default: return 1;
    }
}

static inline u32 pf_count(u32 c)
{
    u32 s, z, n = 0;
    for (s = 0; s <= 1; s++)
        for (z = 0; z <= 10; z++)
            n += pf_ok(c, s, z);
    return n;
}

/* bit i = effect i is unused this turn and has something to act on */
static inline u32 pf_mask(u32 side)
{
    u32 i, m = 0;
    for (i = 0; i < 6; i++) {
        if (turnlog_query(side, TURNLOG_SLOT, KEY(i), TURNLOG_KIND))
            continue;
        if (i == 2 ? HAND_COUNT(side ^ 1) != 0 : pf_count(i) != 0)
            m |= 1u << i;
    }
    return m;
}

static inline void pf_page(u32 e, u32 m, u32 page)
{
    PAGE = page;
    if (page == 1)
        MENU(e, 0x103, (m & 1) ? L0 : 0, (m & 2) ? L1 : 0, (m & 4) ? L2 : 0, (m & 0x38) ? LMORE : 0, (m & 7) | ((m & 0x38) ? 8 : 0));
    else
        MENU(e, 0x103, (m & 8) ? L3 : 0, (m & 0x10) ? L4 : 0, (m & 0x20) ? L5 : 0, 0, (m >> 3) & 7);
}

#if STUB == PF_COND
/* cls1 +0C: face-up in a Spell/Trap Zone, you control a face-up Tribute Summoned monster, a "Monarch" S/T in your GY (row 0xFFEA, MODE 7), at least one usable effect. 2 = yes. */
ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller & 1, z, n;
    if (e->cost_ran)
        return 2;
    MODE = 0;
    if (e->race < 5 || e->race > 9 || !ZONE_FACEUP(side, e->race))
        return 0;
    for (z = 0; z <= 4; z++)
        if (CID(ZONE_WORD(side, z)) && ZONE_FACEUP(side, z) && (FLAGS(side, z) & 8))
            break;
    if (z > 4 || !pf_mask(side))
        return 0;
    MODE = 7;
    n = criteria_count(side, PERF, 0, 0);
    MODE = 0;
    return n ? 2 : 0;
}

#elif STUB == PF_COST
/* cls1 +14: banish 1 "Monarch" Spell/Trap from the GY (Survival Instinct's native GY banish over row 0xFFEA). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r;
    MODE = 7;
    r = BANISH_COST((u32)e, a1);
    if (r != 0)
        MODE = 0;
    return r;
}

#elif STUB == PF_FROWH
/* Row 0xFFEB handler (row r0, side r1): every field card (both sides, zones 0..10) that the chosen effect may act on. */
ENTRY int entry(u32 *row, u32 side)
{
    u32 s, z, n = 0, c = CHOICE;
    (void)row; (void)side;
    for (s = 0; s <= 1; s++)
        for (z = 0; z <= 10; z++)
            if (pf_ok(c, s, z)) {
                ADD_CAND(s, z, 0);
                n++;
            }
    return n;
}

#elif STUB == PF_RES
/* cls1 +04: 0x80 menu page 1 (or page 2 when only effects 4-6 are usable); 0x7F / 0x7E read the answer ("Show other effects." opens page 2 -> 0x7E), stamp that effect's
 * once-per-turn key, effect 3 discards at once, else open the list picker (1 card; 2 for effect 2 when 2+ exist); 0x7D act on the pick(s). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u32 side = e->controller & 1, opp = side ^ 1, m, ans, n, i, *p, zc;
    (void)a1;
    switch (RES_PHASE) {
    case 0x80:
        MODE = 0;
        MASK = m = pf_mask(side);
        if (!m)
            return 0;
        pf_page((u32)e, m, (m & 7) ? 1 : 2);
        return 0x7F;
    case 0x7F:
    case 0x7E:
        ans = MENU_ANSWER;
        if (PAGE == 1 && ans == 3) {
            pf_page((u32)e, MASK, 2);
            return 0x7E;
        }
        CHOICE = PAGE == 1 ? ans : ans + 3;
        if (CHOICE > 5)
            return 0;
        turnlog_post(side, KEY(CHOICE), 1, 0);
        if (CHOICE == 2) {
            n = HAND_COUNT(opp);
            if (n)
                HAND_TO_GY(opp, (((RNG_SEED ^ (RNG_SEED >> 16)) & 0xFFFF) * n) >> 16);   /* no division: libgcc's is not Thumb-1 */
            return 0;
        }
        n = COUNT_FILL(side, PERF, 0);
        if (!n)
            return 0;
        OPEN_PICKER(side, (CHOICE == 1 && n >= 2) ? 8 : 7, PERF, 0);
        return 0x7D;
    case 0x7D:
        n = PICK_COUNT;
        if ((s32)n <= 0)
            return 0;
        if (n > 2)
            n = 2;
        for (i = 0; i < n; i++) {
            p = PICK_FETCH(i + 1);
            zc = *(volatile u16 *)(PICK_ZONE + 2 * (((u32)p - PICK_LIST) >> 2));
            if (CHOICE == 4)
                TO_DECK_TOP((u32)e, zc & 1, (zc >> 1) & 0x1F);
            else if (CHOICE == 5)
                FIELD_BANISH((u32)e, zc & 1, (zc >> 1) & 0x1F);
            else
                destroy_at((u32)e, zc & 1, (zc >> 1) & 0x1F);
        }
        return 0;
    default:
        return 0;
    }
}

#else
#error "build with -DSTUB=PF_COND|PF_COST|PF_RES|PF_FROWH"
#endif

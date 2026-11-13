/* Noble Knight Medraut (0x0FD9, donor Armored Lizard):
 *   C1 "treated as a Normal Monster while face-up"     -- donor is a Normal Monster; type flipped to Effect only so
 *                                                         the ignition record can exist (declared limit).
 *   C2/C3 "While equipped with a Noble Arms Equip Spell ... becomes DARK and its Level is increased by 1"
 *                                                       -- fronts on the Level getter / attribute getter call ACT.
 *   C4 "Once per turn, if you control no other monsters: You can Special Summon 1 Noble Knight monster from your Deck in
 *       Defense Position, except Medraut, and if you do, destroy 1 Equip Spell you control."
 *       cls3 {0x0FD9, RES, FILT, COND, COST, 0x02234D81}: +08/+14 pick the Equip Spell AT ACTIVATION (declared
 *       deviation: the printed text does not target), +04 wraps the native Deck-SS machine 0x02206CAC.
 * -DSTUB=FILT|COND|COST|RES|ACT, -DROWS=<CAVE_MK_ROWS> (row j0 at +0, scratch at +0x10: u16 target loc, u8 MZ mask). */
#include "medraut.h"

#define FILT 1
#define COND 2
#define COST 3
#define RES  4
#define ACT  5

#define RES_PHASE   (*(volatile u32 *)(0x0229AAFC + 0x70))
#define SCR_LOC     (*(volatile u16 *)(ROWS + 0x10))
#define SCR_MASK    (*(volatile u8 *)(ROWS + 0x12))
#define PH_CHK      0x90
#define PH_DESTROY  0x91

#if STUB == ACT
ENTRY int entry(u32 side, u32 zone)
{
    return mk_active(side, zone);
}

#elif STUB == FILT
/* +08 (desc, side, zone): your own face-up Equip Spell in S/T zones 5..9. */
ENTRY int entry(u8 *desc, u32 side, u32 zone)
{
    if (side != desc[2] || zone < 5 || zone > 9 || !zone_active(side, zone))
        return 0;
    return is_equip_spell(CID(ZONE_WORD(side, zone)));
}

#elif STUB == COND
/* +0C: OPT clear, this Medraut equipped with Noble Arms, it is the only monster you control, >= 1 Knight in the Deck. */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    u32 z, n = 0;
    if (opt_used(e, KEY_MK) || !mk_active(d[2], d[3]))
        return 0;
    for (z = 0; z <= 4; z++)
        if (CID(ZONE_WORD(d[2], z)))
            n++;
    if (n != 1)
        return 0;
    return fn_021F0820((u32)e);
}

#elif STUB == COST
ENTRY int entry(EffectCtx *e)
{
    if (!fn_021D2B88((u32)e, 0, 0, 0))
        turnlog_post(e->controller, KEY_MK, TURNLOG_KIND, 0);
    return 1;
}

#elif STUB == RES
static u32 mz_mask(u32 side)
{
    u32 m = 0, z;
    for (z = 0; z <= 4; z++)
        if (CID(ZONE_WORD(side, z)))
            m |= 1u << z;
    return m;
}

/* Phases (RES_PHASE): 0x80 stash the picked Equip Spell + own MZ occupancy, then the native Deck-SS machine
 * (picker 0x7E ... commit 0x7C ending 0x78). After the commit: 0x90 "did a monster arrive?" -> 0x91 destroy -> 0x78. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    u32 phase = RES_PHASE, side = d[2] ^ d[6], loc, r, ts, tz;

    if (phase == 0x80) {
        acting_zone_check((u32)e);
        desc_fill_from_locator((u32)e);
        SCR_LOC = pick_validate((u32)e, 0, &loc) ? (loc & 0xFFFF) : 0xFFFF;
        SCR_MASK = mz_mask(side);
    } else if (phase == PH_CHK) {
        return (mz_mask(side) & ~SCR_MASK) ? PH_DESTROY : 0x78;
    } else if (phase == PH_DESTROY) {
        loc = SCR_LOC;
        ts = loc & 0xFF;
        tz = loc >> 8;
        if (loc != 0xFFFF && ts == d[2] && tz >= 5 && tz <= 9 && revalidate((u32)e, ts, tz))
            destroy_at((u32)e, ts, tz);
        return 0x78;
    }
    r = deck_ss((u32)e, a1);
    if (phase == 0x7C && r == 0x78)
        return PH_CHK;
    return r;
}
#else
#error "build with -DSTUB=FILT|COND|COST|RES|ACT"
#endif

/* Cursed Copycat Noble Arms (0x10E3, donor Cyber Shield) -- N1 count + N2 ignition.
 *   N1 "The equipped monster gains 200 ATK/DEF for each Equip Spell in your field and GY."
 *   N2 "While this card is equipped to a Warrior monster: You can activate this effect; you cannot Special Summon for
 *       the rest of this turn, except Warrior monsters, also Special Summon 1 Warrior monster with the same Attribute
 *       and Level as the equipped monster but a different name from your Deck, and if you do, equip it with this card,
 *       then destroy the monster this card was equipped to."  (once per turn, KEY_N2; user ruling: CURRENT values)
 * N2 = cls3 {0x10E3, RES, 0, COND, COST, 0}. RES wraps the native Deck-SS machine 0x02206CAC (KB counter_engine
 * 0x02206CD2): our 0x80 prologue, the native phases, and two private phases after its 0x7C commit.
 * -DSTUB=N1COUNT|N2COND|N2COST|N2RES, -DROWS=<CAVE_DC_ROWS>. */
#include "disguise.h"

#define N1COUNT 1
#define N2COND  2
#define N2COST  3
#define N2RES   4

#define RES_PHASE   (*(volatile u32 *)(0x0229AAFC + 0x70))
#define LOCK_KEY    0x4FE6           /* Ricciardetto's Warrior-only lock node (its front at 0x021BA368 reads it) */
/* CAVE_DC_ROWS layout: j=0 Disguise C2 row, j=1 this card's Deck row {cid, 0xFFFF, handler, word} + [+0xC] = the
 * excluded (holder's current) cid, j=2 scratch: [+0] old holder loc, [+2] own MZ occupancy mask before the Summon. */
#define N2_ROW      (ROWS + 0x10)
#define ROW_WORD    (*(volatile u32 *)(N2_ROW + 0x8))
#define ROW_EXCL    (*(volatile u16 *)(N2_ROW + 0xC))
#define SCR_HOLDER  (*(volatile u16 *)(ROWS + 0x20))
#define SCR_MASK    (*(volatile u8 *)(ROWS + 0x22))

#define PH_RELINK   0x90
#define PH_DESTROY  0x91

#if STUB == N1COUNT
/* r0 = the equip card's controller -> 200 x (Equip Spells face-up in its S/T zones + in its GY). */
ENTRY u32 entry(u32 side)
{
    return count_equip_spells(side) * 200;
}

#else
/* holder of the equip card at (side, zone): its zone<<8|side, or 0xFFFF */
static __attribute__((unused)) u32 holder_of(u8 *d)
{
    return equip_target_of(d[2], d[3]) & 0xFFFF;
}

/* Deck row word = Warrior | holder's CURRENT Attribute | holder's CURRENT Level (==) | real card; exclude its name. */
static __attribute__((unused)) int fill_row(u32 hs, u32 hz)
{
    u32 attr = cur_attribute(hs, hz, 0) & 7;
    u32 lvl = level_of_zone(hs, hz) & 0xF;
    if (!attr || !lvl)
        return 0;
    ROW_WORD = (RACE_WARRIOR << 27) | (attr << 24) | (lvl << 18) | 0x0002;
    ROW_EXCL = zone_card_resolve(hs, hz);
    return 1;
}

static __attribute__((unused)) int warrior_holder(u8 *d, u32 *hs, u32 *hz)
{
    u32 loc = holder_of(d);
    if (loc == 0xFFFF)
        return 0;
    *hs = loc & 0xFF;
    *hz = (loc >> 8) & 0xFF;
    return *hz <= 4 && race_bit_test(*hs, *hz, RACE_WARRIOR);
}

static __attribute__((unused)) u32 mz_mask(u32 side)
{
    u32 m = 0, z;
    for (z = 0; z <= 4; z++)
        if (CID(ZONE_WORD(side, z)))
            m |= 1u << z;
    return m;
}

#if STUB == N2COND
/* +0C: OPT clear (menu time), equipped to a Warrior, a free Monster Zone, >= 1 Deck match (RotA's counter 0x021F0820
 * over this card's row, which fill_row has just pointed at the current holder). */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    u32 hs, hz;
    if (opt_used(e, KEY_N2))
        return 0;
    if (!warrior_holder(d, &hs, &hz))
        return 0;
    if (!fn_021AD870(d[2], 0, 0))
        return 0;
    if (!fill_row(hs, hz))
        return 0;
    return fn_021F0820((u32)e);
}

#elif STUB == N2COST
ENTRY int entry(EffectCtx *e)
{
    if (!fn_021D2B88((u32)e, 0, 0, 0))
        turnlog_post(e->controller, KEY_N2, TURNLOG_KIND, 0);
    return 1;
}

#elif STUB == N2RES
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    u32 phase = RES_PHASE, side = d[2] ^ d[6], hs, hz, r, m, z, z_new;

    if (phase == 0x80) {
        turnlog_post(d[2], LOCK_KEY, TURNLOG_KIND, 0);         /* "also": the lock applies whatever happens next */
        if (!warrior_holder(d, &hs, &hz) || !fill_row(hs, hz))
            return 0;
        SCR_HOLDER = (hz << 8) | hs;
        SCR_MASK = mz_mask(side);
    } else if (phase == PH_RELINK) {
        m = mz_mask(side) & ~SCR_MASK;
        for (z_new = 5, z = 0; z <= 4; z++)
            if (m & (1u << z))
                z_new = z;
        if (z_new > 4)
            return 0x78;                                       /* nothing was Summoned: no equip, no destroy */
        equip_relink((d[3] << 8) | d[2], (z_new << 8) | side);  /* Equip Shot's 0x021C4BF0 */
        return PH_DESTROY;
    } else if (phase == PH_DESTROY) {
        hs = SCR_HOLDER & 0xFF;
        hz = SCR_HOLDER >> 8;
        if (hz <= 4 && CID(ZONE_WORD(hs, hz)))
            destroy_at((u32)e, hs, hz);
        return 0x78;
    }
    r = deck_ss((u32)e, a1);
    if (phase == 0x7C && r == 0x78)
        return PH_RELINK;                                      /* committed: relink + destroy, then the native shuffle */
    return r;
}
#endif
#endif

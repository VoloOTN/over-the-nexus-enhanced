/* CPU hand Special Summons (cpu_hand_ss): Block Dragon (3 EARTH) and the four big Dragon Rulers (2 monsters of their attribute and/or Dragons).
 * CPUL = may the CPU's hand loop offer the summon; PAY = the CPU's cost, as a summon-procedure registry handler.  Facts: notes/block-dragon-findings.md. */
#include "disguise.h"

#define HAND_COUNT(side) (*(volatile u32 *)(PLAYER(side) + 0x0C))
#define HAND_WORD(side, i) (*(volatile u32 *)(PLAYER(side) + 0x124 + 4 * (i)))

#define PAY  2
#define CPUL 3
/* CPU-only hand Special Summon by banishing: Block Dragon (3 EARTH) and the four big Dragon Rulers (2 monsters of their attribute and/or Dragons). */
#define RACE_DRAGON 1
static inline u32 rule(u32 cid, u32 *attr, u32 *dragon)    /* returns the number to banish, 0 = not ours */
{
    *dragon = 1;
    switch (cid) {
    case 0x0FDD: *attr = 5; *dragon = 0; return 3;       /* Block Dragon */
    case 0x17CD: *attr = 5; return 2;                    /* Redox   EARTH */
    case 0x115F: *attr = 3; return 2;                    /* Tidal   WATER */
    case 0x1145: *attr = 4; return 2;                    /* Blaster FIRE  */
    case 0x1125: *attr = 6; return 2;                    /* Tempest WIND  */
    }
    return 0;
}
static inline int matches(u32 cid, u32 attr, u32 dragon)
{
    return cid && is_monster(cid) && (fn_0202ABC8(cid) == attr || (dragon && get_race(cid) == RACE_DRAGON));
}

#if STUB == CPUL
/* r0 side, r1 cid -> -1 not one of ours, else 0/1: may the CPU's hand loop offer this card's Special Summon.
 * A free Monster Zone and enough monsters in hand + GY (THE CARD ITSELF MATCHES, so need + 1). */
ENTRY int entry(u32 side, u32 cid)
{
    u32 attr, dragon, need = rule(cid, &attr, &dragon), n = 0, i, cnt;
    if (!need)
        return -1;
    if (!fn_021AD870(side, 0, 0))
        return 0;
    cnt = HAND_COUNT(side);
    for (i = 0; i < cnt; i++)
        n += matches(CID(HAND_WORD(side, i)), attr, dragon);
    cnt = GY_COUNT(side);
    for (i = 0; i < cnt; i++)
        n += matches(GY_CID(side, i), attr, dragon);
    return n > need;
}
#endif

#if STUB == PAY
/* Summon-procedure registry handler (0 = call again, nonzero = done), reached by the generic summon commit 0x02264DBC for the cids
 * rule() names.  A HUMAN seat already paid through its virtual cls2 cost -> done at once.  A CPU seat has no picker to drive, so it
 * pays here: one banish per call (the native payment machine's own pacing), GY first then hand, never the summoned card itself
 * (its ref is rec[+0xC]).  rec 0x02298A28: +2 side, +0xC card ref, +0xE cid, +0x24 state, +0x26 picks made. */
#define REC          0x02298A28
#define IS_CPU(side) (*(volatile u32 *)(0x02299114 + 8 + (side) * 4))
ENTRY int entry(void)
{
    volatile u16 *rec = (volatile u16 *)REC;
    u32 side = rec[1];
    u32 attr, dragon, need = rule(rec[0xE / 2], &attr, &dragon);
    u32 i, self, pass;

    if (!IS_CPU(side))
        return 1;
    if (rec[0x24 / 2] == 0) {        /* first call */
        rec[0x26 / 2] = 0;
        rec[0x24 / 2] = 2;
        return 0;
    }
    if (rec[0x26 / 2] >= need) {
        rec[0x24 / 2] = 3;
        return 1;
    }
    self = fn_021A25A0(side, rec[0xC / 2]);
    for (pass = 0; pass < 2; pass++) {                  /* GY first, then the hand; descending so a banish never shifts what is left to visit */
        u32 base = PLAYER(side) + (pass ? 0x124 : 0x55C);
        for (i = pass ? HAND_COUNT(side) : GY_COUNT(side); i-- > 0;) {
            if (pass && i == self)
                continue;
            if (matches(CID(*(volatile u32 *)(base + 4 * i)), attr, dragon)) {
                if (pass)
                    hand_banish(side, i);
                else
                    gy_banish(side, base + 4 * i, 0);
                rec[0x26 / 2]++;
                return 0;
            }
        }
    }
    rec[0x24 / 2] = 3;                /* nothing left to pay with (the legality gate said enough): finish */
    return 1;
}
#endif


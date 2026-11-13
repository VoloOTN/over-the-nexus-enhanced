/* Immortal Phoenix Gearfried (0x0FC7, donor Judge Man). Facts / design: notes/immortal-phoenix-gearfried-findings.md.
 *   C1  hand cls2 (VIRTUAL record): COND / RES here (Disguise C1 shape), COST + picker are hand-written asm in the module.
 *   C2  cls1, start of the Damage Step: FILT / COND / (RES is asm).
 *   C3  cls3 quick negate: COST wrapper here, FILT / COND are asm.
 * Build with -DSTUB=C1COND|C1RES|C2FILT|C2COND|C3COST. */
#include "disguise.h"

#define GF           0x0FC7
#define KEY_GF1      0x5FC7           /* C1: hand Special Summon (stamped at resolution, Oliver rule) */
#define KEY_GF3      0x6FC7           /* C3: quick negate (stamped when the cost completes)           */
#define KEY_GF2      0x7FC7           /* C2: Damage Step equip                                        */
#define HAND_ZONE    0x0B
#define RES_PHASE    (*(volatile u32 *)(0x0229AAFC + 0x70))
#define BATTLE       ((volatile u8 *)0x02298AD8)   /* [+1] DEFENDER side (Tyranno _defender, in-game), [+5] must be 0 */

#define C1COND 1
#define C1RES  2
#define C2FILT 3
#define C2COND 4
#define C3COST 5

#if STUB == C1COND
/* hand only; OPT clear at menu time; a free Monster Zone; >= 1 Equip Spell (face-up in S/T 5..9, or in the GY). */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    if (d[3] != HAND_ZONE)
        return 0;
    if (opt_used(e, KEY_GF1))
        return 0;
    if (!fn_021AD870(d[2], 0, 0))
        return 0;
    if (!count_equip_spells(d[2]))
        return 0;
    return 2;
}

#elif STUB == C1RES
/* phase 0x80 re-checks + stamps the OPT at resolution, then the native hand self-SS resolver does the Summon. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    if (RES_PHASE == 0x80) {
        if (turnlog_query(d[2], TURNLOG_SLOT, KEY_GF1, TURNLOG_KIND))
            return 0;
        turnlog_post(d[2], KEY_GF1, TURNLOG_KIND, 0);
    }
    return handss_res((u32)e, a1);
}

#elif STUB == C2FILT
/* +08 (desc, side, zone): any face-up monster on the field (mask 0xC14 = either side, face-up monster), except Gearfried. */
ENTRY int entry(u8 *desc, u32 side, u32 zone)
{
    if (!zone_predicate((u32)desc, side, zone, 0xC14))
        return 0;
    return !(side == desc[2] && zone == desc[3]);
}

#elif STUB == C2COND
/* +0C: OPT clear; a normal (non-replay) battle; Gearfried's controller is the ATTACKER; no monster already equipped to it. */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    u32 me = ((u32)d[3] << 8) | d[2], s, z;
    if (opt_used(e, KEY_GF2))
        return 0;
    if (BATTLE[5] != 0)
        return 0;
    if ((((u32)BATTLE[1] ^ 1) & 1) != d[2])
        return 0;
    for (s = 0; s <= 1; s++) {
        for (z = 5; z <= 9; z++) {
            u32 cid = zone_cid_at(s, z);
            if (cid && is_monster(cid) && (equip_target_of(s, z) & 0xFFFF) == me)
                return 0;
        }
    }
    return 1;
}

#elif STUB == C3COST
/* +10: the native field cost sends the picked Equip Card to the GY (record +08 = filter); the OPT is stamped once it
 * completes. cost_settled = the engine replaying a finished cost (Mystic Piper rule): do not stamp / re-run. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r;
    if (cost_settled((u32)e, 0, 0, 0))
        return 1;
    r = field_cost_machine((u32)e, a1);
    if (r == 1)
        turnlog_post(e->controller, KEY_GF3, TURNLOG_KIND, 0);
    return r;
}
#else
#error "build with -DSTUB=C1COND|C1RES|C2FILT|C2COND|C3COST"
#endif

/* Disguise, the Copycat Hero -- C3:
 *   "While this card is equipped with an Equip Card: You can target 1 non-Tuner Warrior monster on the field with a
 *    Level; this card's Level, also its name, become the same as that monster's until the End Phase."
 *   (once per turn, its own key KEY_C3)
 * One cls3 record {0x111E, RES, FILT, COND, COST, 0x02234D81 (Copy Plant's target-select step, prompt 0x6F)}.
 * Mirrors Copy Plant 0x1EC1 (cls3[438]): filter arm 0x021DAC78, resolver leaf 0x02208602, rider tail 0x0220878A.
 * Build with -DSTUB=FILT|COND|COST|RES. */
#include "disguise.h"

#define FILT 1
#define COND 2
#define COST 3
#define RES  4

#if STUB == FILT
/* +08 (desc, side, zone) -> 1 = legal target. Copy Plant's arm: mask 0xC14 (either side, face-up monster), then
 * the race test unless desc[8] != 0. Disguise adds: Warrior instead of Plant, and not a Tuner. "With a Level" holds
 * for every monster in this game (no Xyz). */
ENTRY int entry(u8 *desc, u32 side, u32 zone)
{
    if (!zone_predicate((u32)desc, side, zone, 0xC14))
        return 0;
    if (desc[8])
        return 1;
    if (!race_bit_test(side, zone, RACE_WARRIOR))
        return 0;
    return !is_tuner_rt(side, zone);
}

#elif STUB == COND
/* +0C: menu-time hard OPT, and this card is equipped with an Equip Card. 1 = offer if the +08 sweep finds a target. */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    if (opt_used(e, KEY_C3))
        return 0;
    return is_equipped(d[2], d[3]);
}

#elif STUB == COST
/* +10: stamp the OPT at activation; skipped when the engine replays the cost (0x021D2B88, Tenki's cost). */
ENTRY int entry(EffectCtx *e)
{
    if (!fn_021D2B88((u32)e, 0, 0, 0))
        turnlog_post(e->controller, KEY_C3, TURNLOG_KIND, 0);
    return 1;
}

#elif STUB == RES
/* +04: Copy Plant's resolver shape. Riders go on THIS card's zone: {0x1D43, kind 2, target's current cid} renames
 * it, {0x1EC1, kind 2, target's current Level} sets its Level; both are freed by the end-of-turn sweep. */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    u32 loc, ts, tz, lvl, name;

    if (!acting_zone_check((u32)e))
        return 0;
    desc_fill_from_locator((u32)e);
    if (!pick_validate((u32)e, 0, &loc))
        return 0;
    ts = loc & 0xFF;
    tz = (loc >> 8) & 0xFF;
    if (!revalidate((u32)e, ts, tz))
        return 0;
    lvl = level_of_zone(ts, tz);
    name = zone_card_resolve(ts, tz);
    if (!lvl || !name)
        return 0;
    rider_attach(d[2], d[3], NAME_KEY, KIND_UNTIL_EP, name);
    rider_attach(d[2], d[3], LEVEL_KEY, KIND_UNTIL_EP, lvl);
    return 0;
}
#else
#error "build with -DSTUB=FILT|COND|COST|RES"
#endif

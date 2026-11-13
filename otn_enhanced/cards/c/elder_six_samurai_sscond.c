/* Elder of the Six Samurai hand-SS condition (CAVE3_ELDER_SSCOND). Entry r0 is a SIDE, not a ctx.
 * 1 iff gate 0x021AD870 passes, this side's count 0x021ACF68 is 0 and the opponent's is not.
 * a1/a2 pass through: 0x021AD870 reads r0 and r2 (c_callee_audit.arg_regs). */
#include "engine.h"

ENTRY int entry(u32 side, u32 a1, u32 a2)
{
    if (!fn_021AD870(side, a1, a2))
        return 0;
    if (count_live_slots(side))
        return 0;
    return count_live_slots(1 - side) != 0;
}

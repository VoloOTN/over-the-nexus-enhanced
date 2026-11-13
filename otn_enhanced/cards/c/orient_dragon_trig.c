/* Orient Dragon (CAVE3_OD_TRIG): its own cid (0x0FCB) answers 1; any other cid goes to the native lookup
 * 0x02022E14 (reads r0-r2, c_callee_audit.arg_regs). Same shape as gates_of_dark_world.c. */
#include "engine.h"

#define ORIENT_DRAGON 0x0FCB

ENTRY u32 entry(u32 cid, u32 a1, u32 a2)
{
    if (cid == ORIENT_DRAGON)
        return 1;
    return fn_02022E14(cid, a1, a2);
}

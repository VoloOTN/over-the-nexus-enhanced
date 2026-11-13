/* Gates of Dark World (OV3_DEAD_021B2A4C): for its own cid (0x1C8B) the answer is a1; any other cid goes
 * to the native lookup 0x02022E14, which reads r0-r2 (c_callee_audit.arg_regs). */
#include "engine.h"

#define GATES_OF_DARK_WORLD 0x1C8B

ENTRY u32 entry(u32 cid, u32 a1, u32 a2)
{
    if (cid == GATES_OF_DARK_WORLD)
        return a1;
    return fn_02022E14(cid, a1, a2);
}

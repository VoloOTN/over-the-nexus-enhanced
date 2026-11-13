/* Junk Servant hand-SS condition (CAVE3_JS_SSCOND): gate 0x021AD870 (reads r0, r2; a1/a2 pass through), then
 * 0x021ACFE8(side, filter 0x02023E5D, -1, 1) != 0. */
#include "engine.h"

ENTRY int entry(u32 side, u32 a1, u32 a2)
{
    if (!fn_021AD870(side, a1, a2))
        return 0;
    return fn_021ACFE8(side, 0x02023E5D, 0xFFFFFFFF, 1) != 0;
}

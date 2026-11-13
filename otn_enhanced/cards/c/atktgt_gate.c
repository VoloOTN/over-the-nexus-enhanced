/* Attack-target gate (CAVE3_ATKTGT_GATE): the native cid 0x021A37D8 (args pass through; it reads r0, r1, r3);
 * a cid on the zero-terminated list at 0x021DEFFC (CAVE3_ATKTGT_LIST) is reported as 0x1CB1. */
#include "engine.h"

ENTRY u32 entry(u32 a0, u32 a1, u32 a2, u32 a3)
{
    u32 cid = fn_021A37D8(a0, a1, a2, a3);
    const volatile u16 *p;
    for (p = (const volatile u16 *)0x021DEFFC; *p; p++)
        if (*p == cid)
            return 0x1CB1;
    return cid;
}

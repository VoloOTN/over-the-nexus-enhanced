/* Dragon Rulers H4 (CAVE3_RUL_H4): the native lookup 0x02022E14 (reads r0-r2) if it answers, else 1 iff the
 * Ruler key finder (CAVE3_RUL_FINDK) finds this cid (it returns -1 for "not found"). */
#include "engine.h"

ENTRY int entry(u32 cid, u32 a1, u32 a2)
{
    int r = fn_02022E14(cid, a1, a2);
    if (r)
        return r;
    return slot_CAVE3_RUL_FINDK(cid) != -1;
}

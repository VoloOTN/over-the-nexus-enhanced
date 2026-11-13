/* T.G. Warwolf arm hook (CAVE3_TGW_ARMHOOK): pass 0x021A25A0(a0, a1) through, and set the arm latch
 * (CAVE3_TGW_ARMLATCH) when the cid at 0x02298A28+0xE is a monster of Level 1..4. */
#include "engine.h"

#define WATCHED_CID (*(volatile u16 *)(0x02298A28 + 0xE))
#define TGW_ARMLATCH (*(volatile u32 *)0x021DAFF0)

ENTRY u32 entry(u32 a0, u32 a1)
{
    u32 r = fn_021A25A0(a0, a1);
    u32 cid = WATCHED_CID;
    if (cid) {
        int lv = cid_level(cid);
        if (lv && lv <= 4)
            TGW_ARMLATCH = 1;
    }
    return r;
}

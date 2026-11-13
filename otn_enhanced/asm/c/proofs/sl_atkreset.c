/* Shim proof: CAVE3_SL_ATKRESET (Sea Lancer E3 flag reset, BL site 0x021B44EC) as C + SPLICE_SHIM. */
#include "engine.h"

#define SL_ATKFLAG ((volatile u32 *)0x021BA0F4)   /* CAVE3_SL_ATKFLAG */

void sl_atkreset(Regs *r, u32 *frame)
{
    r->r[4] = 0;
    frame[0xB0 / 4] = 0;
    *SL_ATKFLAG = 0;
    r->r[3] = (u32)SL_ATKFLAG;   /* the old stub left r3 = &flag; kept until the site proves r3 dead */
}

/* T.G. Warwolf E1 condition (CAVE3_TGW_E1COND): 1 iff the arm latch (CAVE3_TGW_ARMLATCH) is set. */
#include "engine.h"

#define TGW_ARMLATCH (*(volatile u32 *)0x021DAFF0)

ENTRY int entry(void)
{
    return TGW_ARMLATCH != 0;
}

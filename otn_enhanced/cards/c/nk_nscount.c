/* Nikitama NS count (CAVE3_NK_NSCOUNT): 0 while 0x02261F84 holds Nikitama's node 0x3E51, else Sakitama's
 * count (CAVE3_SK_NSCOUNT, the next link of the chain). */
#include "engine.h"

#define NS_CID (*(volatile u32 *)0x02261F84)

ENTRY int entry(u32 a0)
{
    if (NS_CID == 0x3E51)
        return 0;
    return slot_CAVE3_SK_NSCOUNT(a0);
}

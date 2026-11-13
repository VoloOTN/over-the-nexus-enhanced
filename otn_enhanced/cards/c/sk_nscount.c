/* Sakitama NS count (CAVE3_SK_NSCOUNT): 0 while 0x02261F84 holds Sakitama's node 0x3E50, else Scrap Raptor's
 * count (CAVE3_SR_NSCOUNT, the next link of the chain). */
#include "engine.h"

#define NS_CID (*(volatile u32 *)0x02261F84)

ENTRY int entry(u32 a0)
{
    if (NS_CID == 0x3E50)
        return 0;
    return slot_CAVE3_SR_NSCOUNT(a0);
}

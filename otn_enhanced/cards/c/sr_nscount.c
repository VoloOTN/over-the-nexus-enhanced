/* Scrap Raptor NS count (CAVE3_SR_NSCOUNT): 0 while the word at 0x02261F84 holds Scrap Raptor's cid, else the
 * native Normal Summon counter 0x021B9514 (KB summon.normal_summon_counter_and_has_summoned, reads r0). */
#include "engine.h"

#define SCRAP_RAPTOR 0x0FF6
#define NS_CID (*(volatile u32 *)0x02261F84)

ENTRY int entry(u32 a0)
{
    if (NS_CID == SCRAP_RAPTOR)
        return 0;
    return ns_counter(a0);
}

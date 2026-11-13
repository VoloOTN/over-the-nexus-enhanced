/* Dragon Rulers H5 (CAVE3_RUL_H5): post each cid of the zero-terminated list at 0x0221AE78 to the End-Phase
 * registry (0x02253F88); 0 as soon as one post fails, 1 when the whole list went in. */
#include "engine.h"

ENTRY int entry(u32 a0)
{
    const volatile u16 *p;
    for (p = (const volatile u16 *)0x0221AE78; *p; p++)
        if (!endphase_post(a0, *p))
            return 0;
    return 1;
}

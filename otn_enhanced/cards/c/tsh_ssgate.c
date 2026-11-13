/* Thunder Sea Horse SS gate (CAVE_TSH_SSGATE): the attached-key check 0x021A1430 for (a0, a1, a2), or else for
 * (a0, 0xB, 0x0FEC). */
#include "engine.h"

ENTRY int entry(u32 a0, u32 a1, u32 a2)
{
    int r = key_presence(a0, a1, a2);
    return r ? r : key_presence(a0, 0xB, 0x0FEC);
}

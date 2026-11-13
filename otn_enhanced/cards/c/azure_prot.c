/* Azure-Eyes Silver Dragon C2 protection query (CAVE_AZURE_PROT): the attached-key check 0x021A1430 for (a0, a1, a2), or else for
 * (a0, a1, 0x1E9C). */
#include "engine.h"

ENTRY int entry(u32 a0, u32 a1, u32 a2)
{
    int r = key_presence(a0, a1, a2);
    return r ? r : key_presence(a0, a1, 0x1E9C);
}

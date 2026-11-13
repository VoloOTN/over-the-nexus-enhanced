/* Infernoble Knight Oliver hand helper (CAVE_IK_O_HANDH): 0x0223BFD4 (7 args) over side a1 for desc's cid, a2 passed
 * through, callback 0x023A8131; on the stack 0x1E04, desc[+8] and 0x11. */
#include "engine.h"

ENTRY int entry(const u8 *d, u32 side, u32 a2)
{
    return fn_0223BFD4(side, *(const u16 *)d, a2, 0x023A8131, 0x1E04, *(const u32 *)(d + 8), 0x11);
}

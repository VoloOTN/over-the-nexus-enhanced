/* Shim proof: CAVE3_SK_NSMATCH (Sakitama site 4 match front, 0x0226515C) as C + FRONT_SHIM.
 * r0 == K: return to the engine with r1 = K. Otherwise tail-jump to native (r1 = native, as before). */
#include "engine.h"

#define K 0x3E50

int sk_nsmatch(Regs *r, u32 *frame)
{
    (void)frame;
    r->r[1] = K;
    return r->r[0] != K;
}

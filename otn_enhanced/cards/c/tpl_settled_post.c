/* Template: cost. Unless the cost-settled predicate 0x021D2BC8 says so, log (side, cid, KIND). Returns 1.
 * Per slot (c_forms.Form.defines): KIND.
 * The old stubs call it as `ldr r3,=0x021D2BC9; blx r3`, so its r3 is its own address. Its nested call reaches the
 * ITCM routine behind 0x0202ABF8, so whether r3 is read can't be bounded: pass the identical value,
 * (u32)cost_settled (the .thumb_set symbol is the address with the Thumb bit). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2)
{
    if (!cost_settled((u32)e, a1, a2, (u32)cost_settled))
        turnlog_post(e->controller, e->cid, KIND, 0);
    return 1;
}

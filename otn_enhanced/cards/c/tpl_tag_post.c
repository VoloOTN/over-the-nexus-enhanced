/* Template: "You can" slot 4. TAG(ctx, a1); when it answers 1, log (side, LOG_CID, KIND). Returns TAG's answer.
 * Per slot (c_forms.Form.defines): TAG (you_can_tag or costless_you_can), LOG_CID, KIND. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = TAG(e, a1);
    if (r == 1)
        turnlog_post(e->controller, LOG_CID, KIND, 0);
    return r;
}

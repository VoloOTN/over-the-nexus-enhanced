/* Template: once-per-turn condition. 0 if (side, 0xB, LOG_CID, KIND) is logged this turn, else NEXT.
 * Per slot (c_forms.Form.defines): LOG_CID, KIND, and NEXT, an expression over e / a1 such as fn_021F0820((u32)e). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    if (turnlog_query(e->controller, 0xB, LOG_CID, KIND))
        return 0;
    return NEXT;
}

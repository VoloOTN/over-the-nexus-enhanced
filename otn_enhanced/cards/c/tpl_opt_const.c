/* Template: once-per-turn condition with a fixed answer. 0 if (side, 0xB, LOG_CID, KIND) is logged this turn, else
 * RET. Per slot (c_forms.Form.defines): LOG_CID, KIND, RET. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    return turnlog_query(e->controller, 0xB, LOG_CID, KIND) ? 0 : RET;
}

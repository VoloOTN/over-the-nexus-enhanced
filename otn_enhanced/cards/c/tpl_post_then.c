/* Template: cost. Log (side, LOG_CID, KIND), then return THEN (e.g. tribute_tag((u32)e)).
 * Per slot (c_forms.Form.defines): LOG_CID, KIND, THEN. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, LOG_CID, KIND, 0);
    return THEN;
}

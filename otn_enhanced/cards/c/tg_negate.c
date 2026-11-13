/* T.G. negate (CAVE3_TG_NEGATE): run 0x02235604 (KB dispatch.offfield_picker_sequence) on r0, report done. */
#include "engine.h"

ENTRY int entry(u32 a0)
{
    fn_02235604(a0);
    return 1;
}

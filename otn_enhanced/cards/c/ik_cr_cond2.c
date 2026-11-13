/* Infernoble Captain Roland cls2 +0C (CAVE_IK_CR_COND2): 2 iff zone byte +3 == 0x10 and event byte +4 == 6
 * (the End-Phase rider walker), else 0. Raw offsets: these bytes are not the effect ctx's race/trigger here. */
#include "engine.h"

ENTRY int entry(const u8 *d)
{
    return d[3] == 0x10 && d[4] == 6 ? 2 : 0;
}

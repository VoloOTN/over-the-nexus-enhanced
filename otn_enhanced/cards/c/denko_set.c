/* Denko Sekka cannot-Set gate (CAVE3_DENKO_SET): the native set-code check 0x020235F0 if it answers, else the
 * Denko lock (CAVE3_DENKO_LOCK, which reads no arguments). */
#include "engine.h"

ENTRY int entry(u32 a0)
{
    int r = fn_020235F0(a0);
    return r ? r : slot_CAVE3_DENKO_LOCK();
}

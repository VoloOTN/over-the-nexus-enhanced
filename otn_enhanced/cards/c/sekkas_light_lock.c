/* Sekka's Light S/T lock (CAVE3_SEKKA_LOCK), C port of the cards/sekkas_light.py stub.
 * Nonzero = blocked: the native activation-prohibited verdict, else "a non-Sekka Spell/Trap while
 * Sekka's Light (0x10E6) is logged this turn". a1-a3 pass straight through: the native predicate's
 * arity is bounded at 4 (c_callee_audit.arg_regs), and the old stub left them untouched. */
#include "engine.h"

#define SEKKAS_LIGHT 0x10E6

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    int r = activation_prohibited((u32)e, a1, a2, a3);
    if (r)
        return r;
    if (e->cid == SEKKAS_LIGHT || is_monster(e->cid))
        return 0;
    return turnlog_query(e->controller ^ ((u8 *)e)[6], 0xB, SEKKAS_LIGHT, 5) != 0;
}

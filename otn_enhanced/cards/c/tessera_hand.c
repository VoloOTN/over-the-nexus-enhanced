/* Tessera the Primal Squire T1 (0x1123): "You can reveal 1 "Monarch" Spell/Trap in your hand; Special Summon this card from your hand."  Once per turn.
 * A VIRTUAL cls2 hand record reached through effects/prefind_hook.py (find_event_handler pre-dispatch), offered by an ARM9 H4 front, shaped like Immortal Phoenix Gearfried C1:
 * COND = hand only + OPT + a free zone + a Monarch Spell/Trap in the hand; COST = the native reveal cost 0x021EAAA1 over the virtual hand row 0xFFD5 (Psi-Reflector C2's UI path);
 * RES = stamp the node, then the native hand self-SS resolver.  Build with -DSTUB=T1_COND|T1_COST|T1_RES.  Notes: notes/tessera-findings.md. */
#include "disguise.h"

#define T1_COND 1
#define T1_COST 2
#define T1_RES  3

#define TESSERA   0x1123
#define KEY_OPT1  0x7123
#define HAND_ZONE 0x0B
#define MONARCH_SET 0x6D
#define HAND_COUNT(s) (*(volatile u32 *)(PLAYER(s) + 0xC))
#define HAND_CID(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)) & 0x3FFF)
#define HAS_SET_CODE ((int (*)(u32, u32))0x020240D9)
#define RES_PHASE (*(volatile u32 *)(0x0229AAFC + 0x70))

#if STUB == T1_COND
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    u32 side = d[2], i, n = HAND_COUNT(side);
    if (d[3] != HAND_ZONE)
        return 0;
    if (opt_used(e, KEY_OPT1))
        return 0;
    if (!fn_021AD870(side, 0, 0))
        return 0;
    for (i = 0; i < n; i++)
        if (HAS_SET_CODE(HAND_CID(side, i), MONARCH_SET))
            return 2;
    return 0;
}

#elif STUB == T1_COST
ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    (void)a2;
    return reveal_cost((u32)e, a1, (u32)reveal_cost, a3);
}

#elif STUB == T1_RES
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    if (RES_PHASE == 0x80) {
        if (turnlog_query(d[2], TURNLOG_SLOT, KEY_OPT1, TURNLOG_KIND))
            return 0;
        turnlog_post(d[2], KEY_OPT1, TURNLOG_KIND, 0);
    }
    return handss_res((u32)e, a1);
}

#else
#error "build with -DSTUB=T1_COND|T1_COST|T1_RES"
#endif

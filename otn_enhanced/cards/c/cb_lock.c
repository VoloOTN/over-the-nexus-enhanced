/* Crimson Blader stage A lock (CAVE_CB_LOCK, cls1 +04): post (opponent, cid, kind, 0) to the turn log, kind 0x11 if the turn player
 * (word 0x0229DD14 + 0x34) is the controller, else 0x21. Returns 0. */
#include "engine.h"

#define TURN_PLAYER (*(volatile u32 *)(0x0229DD14 + 0x34))

ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller;
    turnlog_post(1 - side, e->cid, TURN_PLAYER == side ? 0x11 : 0x21, 0);
    return 0;
}

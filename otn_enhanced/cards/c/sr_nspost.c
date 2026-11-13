/* Scrap Raptor NS post (CAVE3_SR_NSPOST): forward a turn-log post, with kind 2 for Scrap Raptor's own cid. */
#include "engine.h"

#define SCRAP_RAPTOR 0x0FF6

ENTRY void entry(u32 side, u32 cid, u32 kind)
{
    turnlog_post(side, cid, cid == SCRAP_RAPTOR ? 2 : kind, 0);
}

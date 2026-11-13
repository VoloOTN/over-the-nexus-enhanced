/* Mystic Piper's resolver: "draw and reveal 1 card. If that card is a Level 1 Monster Card, draw 1 more card."
 * C port of the DSL lowering in cards/mystic_piper.py (draw_and_reveal + if_(revealed.is_level(1), draw(1))). */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    u32 side = e->controller;
    u32 cid;

    reveal_top(side);
    cid = CID(DECK_TOP(side));   /* before the draw: draws are queued */
    draw(side, 1);
    if (is_monster(cid) && cid_level(cid) == 1) {
        draw(side, 1);
    }
    return 0;
}

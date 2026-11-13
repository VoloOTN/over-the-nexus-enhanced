/* "Draw 2 cards" resolver, shared by Sekka's Light (CAVE_SEKKA_RES) and Sacred Sword of Seven Stars
 * (CAVE_SSS_RES): the drawing side is controller ^ ctx[+6]. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    draw(e->controller ^ ((u8 *)e)[6], 2);
    return 0;
}

/* Block Dragon C3 PROBE (scratch tool, never shipped): calls the engine's hand-add mover 0x021C72CC(side, word*) ONCE on the real Deck top card
 * from a custom caller, then tracks THAT card (matched on cid + ref bits) over later visits.  Scratch block 0x023AE480 (24 words):
 *   [0] state (0 idle, 1 called, 2 done)  [1] side  [2] top word  [3] mover return  [4] deck count  [5] hand count (before the call)
 *   [6 + 3*k ..] checkpoint k (k = 0..3 at visits 2, 10, 30, 58): hand count, deck count, flags (bit0 card in hand, bit1 card still in Deck)
 *   [18] visit counter
 * Build with -DSTUB=PROBE. */
#include "engine.h"

#define SCR         ((volatile u32 *)0x023AE480)
#define PLAYER(s)   (0x0229AC94 + ((s) & 1) * 0xB3C)
#define HANDN(s)    (*(volatile u32 *)(PLAYER(s) + 0x0C))
#define HANDW(s, i) (*(volatile u32 *)(PLAYER(s) + 0x124 + 4 * (i)))
#define DECKN(s)    (*(volatile u32 *)(0x0229ACA4 + ((s) & 1) * 0xB3C))
#define DECKW(s, i) (*(volatile u32 *)(PLAYER(s) + 0x304 + 4 * (i)))
#define DECKTOP(s)  (0x0229AF98 + ((s) & 1) * 0xB3C)
#define MOVER       ((int (*)(u32, u32))0x021C72CD)
#define KEY         0x7F807FFF

#if STUB == PROBE
ENTRY void entry(u32 side)
{
    u32 v = SCR[0], n, i, f, k, top;
    if (v == 0) {
        SCR[0] = 1;
        SCR[1] = side;
        SCR[2] = *(volatile u32 *)DECKTOP(side);
        SCR[3] = (u32)MOVER(side, DECKTOP(side));
    } else if (v == 1) {
        n = ++SCR[18];
        k = (n == 3) ? 0 : (n == 58) ? 1 : 9;
        if (k > 1)
            return;
        side = SCR[1];
        top = SCR[2] & KEY;
        f = 0;
        for (i = 0; i < HANDN(side); i++)
            if ((HANDW(side, i) & KEY) == top)
                f |= 1;
        SCR[6 + 3 * k] = HANDN(side);
        SCR[7 + 3 * k] = DECKN(side);
        SCR[8 + 3 * k] = f;
        if (k == 1)
            SCR[0] = 2;
    }
}
#endif

/* Ninishi position resolver (CAVE3_NIN_POSRES): if the acting zone still holds the card (0x021D2C1C), refresh the
 * descriptor (0x021D2D18) and toggle its position: 0x021C5324(desc, side, zone, 0, 1) -- the 5th arg on the stack. */
#include "engine.h"

ENTRY int entry(u8 *d)
{
    if (acting_zone_check((u32)d)) {
        desc_fill_from_locator((u32)d);
        change_position((u32)d, d[2], d[3], 0, 1);
    }
    return 0;
}

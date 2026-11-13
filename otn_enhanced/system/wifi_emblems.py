"""Make the 7 Wi-Fi-only emblems attainable offline by piggybacking them on an
offline emblem in the same row (findings: notes/emblems-findings.md).

Emblem bits live at byte[0x0212406C + 0xDD + row], bit = column. Every award site
is `ldrb r1,[base,#row]; orr r1,r1,#bit; strb r1,[base,#row]; bl notify`, so
widening the `orr` immediate at one offline site sets the Wi-Fi bits in the same
store. Only the trigger emblem's pop-up shows.

    trigger (offline)                    also grants                         site
    Thrifty Goblin   row2 bit 0x10      Bronze/Silver/Gold Medal 0xE0       ov3 0x02182028
    Treasure Chest   row3 bit 0x08      Simple/Prestigious Medal 0x03       ov1 0x0214625C
    Dark Magician Girl row4 bit 0x40    Guard Robot / ? emblem   0x30       ov3 0x021441C0

Re-fire behaviour (matters for existing saves):
  * Thrifty Goblin (ov3 0x02181FD4) and DMG (ov3 0x02144198) do NOT test their own
    bit first -- they re-run whenever the condition holds (Thrifty after a duel at
    100% bonus; DMG on any Structure-Deck win once all 15 are cleared).
  * Treasure Chest (ov1 0x021461F8) skips when its own bit is already set, so a save
    that already owns Treasure Chest never reaches the widened orr.

No cave, no phantom cid: three ARM immediate words in place.
STATUS: AWAITING IN-GAME TEST.
"""
from __future__ import annotations

import struct

import ndspy.rom

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_wifi_emblems.nds"

# (overlay, address, stock word, patched word)
SITES = [
    (3, 0x02182028, 0xE3811010, 0xE38110F0),  # orr r1,r1,#0x10 -> #0xF0  (row 2)
    (1, 0x0214625C, 0xE3811008, 0xE381100B),  # orr r1,r1,#0x08 -> #0x0B  (row 3)
    (3, 0x021441C0, 0xE3811040, 0xE3811070),  # orr r1,r1,#0x40 -> #0x70  (row 4)
]


def _overlays(rom):
    return rom.loadArm9Overlays(sorted({ov for ov, *_ in SITES}))


def _word(ov, addr: int) -> int:
    return struct.unpack_from("<I", ov.data, addr - ov.ramAddress)[0]


def main(write_text: bool = False, src: str = SRC, out: str = OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    ovs = _overlays(rom)
    data = {k: bytearray(o.data) for k, o in ovs.items()}
    for ovid, addr, old, new in SITES:
        got = _word(ovs[ovid], addr)
        assert got in (old, new), f"ov{ovid} 0x{addr:08X} = {got:08X}, expected {old:08X}"
        struct.pack_into("<I", data[ovid], addr - ovs[ovid].ramAddress, new)
    for ovid, ov in ovs.items():
        ov.data = bytes(data[ovid])
        compressed = ov.save(compress=ov.compressed)
        rom.files[ov.fileID] = compressed
        # ramSize is unchanged; refresh the compressed size in the overlay table
        e = ovid * 32
        flags = struct.unpack_from("<I", rom.arm9OverlayTable, e + 0x1C)[0] >> 24
        struct.pack_into("<I", rom.arm9OverlayTable, e + 0x1C,
                         (flags << 24) | (len(compressed) & 0xFFFFFF))
    rom.saveToFile(out)
    print(f"wifi emblems: {len(SITES)} orr immediates widened; wrote {out}")


def verify(out: str = OUT) -> None:
    ovs = _overlays(ndspy.rom.NintendoDSRom.fromFile(out))
    for ovid, addr, _old, new in SITES:
        got = _word(ovs[ovid], addr)
        assert got == new, f"ov{ovid} 0x{addr:08X} = {got:08X}, expected {new:08X}"


if __name__ == "__main__":
    main()
    verify()

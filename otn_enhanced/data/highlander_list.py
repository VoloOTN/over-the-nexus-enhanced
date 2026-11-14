"""Turn the built-in "List - September, 2008" entry into "Highlander": every card limited to 1.

get_limit (arm9 Thumb 0x0202AD9C) returned a hard-coded 3 for any card not on the list.
Its tail 0x0202ADBC..0x0202ADE4 is rewritten in place (same size) so that the "unlisted"
answer -- and the No Banlist answer (flags bit0, no_banlist_mode) -- is

    3 - header[+7]

header+7 is the high byte of the flags halfword: 0 in every stock limit*.bin, 0 after the
idx 1/2 stamps (strh flags = 1/2), so every existing list -- built-in or saved -- still
yields 3. Flag readers test bit0 / bit1 of the low byte only.

limit200809.bin (menu idx 6, via extra_banlists) gets count = 0 and header+7 = 2, so
every card is unlisted -> 1 copy, Forbidden cards included. Its name text 0x524
("List - September, 2008") is overwritten in place with "Highlander".

MUST run after no_banlist_mode and extra_banlists.
"""
from __future__ import annotations

import struct
from pathlib import Path

import capstone
import ndspy.code
import ndspy.rom

from otn_enhanced.rom.pac import build_modified_pac, parse_pac

SRC = "data/over_the_nexus/working/rom_extra_banlists_test.nds"
OUT = "data/over_the_nexus/working/rom_highlander_test.nds"

ARM9 = 0x02000000
TAIL = 0x0202ADBC
# stock tail with no_banlist_mode's `movs r0,#3` @0x0202ADD0
OLD_TAIL = bytes.fromhex("0ee06800085a83049b0c9e4207d1e288d20701d0032070bd0004800f70bd6d1c9542eedb032070bd")
NEW_TAIL = struct.pack("<20H",
    0xE00C,  # adbc b     0x0202ADD8          (loop condition)
    0x0068,  # adbe lsls  r0, r5, #1
    0x5A08,  # adc0 ldrh  r0, [r1, r0]
    0x0483,  # adc2 lsls  r3, r0, #0x12
    0x0C9B,  # adc4 lsrs  r3, r3, #0x12
    0x429E,  # adc6 cmp   r6, r3
    0xD105,  # adc8 bne   0x0202ADD6          (next)
    0x88E2,  # adca ldrh  r2, [r4, #6]
    0x07D2,  # adcc lsls  r2, r2, #0x1f
    0xD105,  # adce bne   0x0202ADDC          (bit0 -> cap)
    0x0400,  # add0 lsls  r0, r0, #0x10
    0x0F80,  # add2 lsrs  r0, r0, #0x1e       (entry >> 14)
    0xBD70,  # add4 pop   {r4, r5, r6, pc}
    0x1C6D,  # add6 adds  r5, r5, #1
    0x4295,  # add8 cmp   r5, r2
    0xDBF0,  # adda blt   0x0202ADBE
    0x79E1,  # addc ldrb  r1, [r4, #7]        (cap: 3 - header[+7])
    0x2003,  # adde movs  r0, #3
    0x1A40,  # ade0 subs  r0, r0, r1
    0xBD70,  # ade2 pop   {r4, r5, r6, pc}
)
WANT = [
    "b #0x202add8", "lsls r0, r5, #1", "ldrh r0, [r1, r0]", "lsls r3, r0, #0x12",
    "lsrs r3, r3, #0x12", "cmp r6, r3", "bne #0x202add6", "ldrh r2, [r4, #6]",
    "lsls r2, r2, #0x1f", "bne #0x202addc", "lsls r0, r0, #0x10", "lsrs r0, r0, #0x1e",
    "pop {r4, r5, r6, pc}", "adds r5, r5, #1", "cmp r5, r2", "blt #0x202adbe",
    "ldrb r1, [r4, #7]", "movs r0, #3", "subs r0, r0, r1", "pop {r4, r5, r6, pc}",
]

BIN_PAC, BIN2_PAC = "Data_arc_pac/bin.pac", "Data_arc_pac/bin2.pac"
LIST_FILE = "limit200809.bin"
CAP_BYTE = 2                         # 3 - 2 = 1 copy of every card
TEXT_ID = 0x524
OLD_TEXT, NEW_TEXT = b"List - September, 2008", b"Highlander"
NUL = b"\x00"


def _check_tail(code: bytes) -> None:
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    got = [f"{i.mnemonic} {i.op_str}" for i in md.disasm(code, TAIL)]
    assert got == WANT, got


def _main_section(rom):
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    return mc, next(s for s in mc.sections if s.ramAddress == rom.arm9RamAddress)


def _pac_file(rom, pac, name):
    blob = bytes(rom.getFileByName(pac))
    ar = parse_pac(blob, pac)
    i = next(k for k, f in enumerate(ar.files) if f.get_clean_name() == name)
    f = ar.files[i]
    return blob, i, bytearray(blob[f.address:f.address + f.size])


def _text(rom):
    blob, ti, txt = _pac_file(rom, BIN2_PAC, "game_text_e.bin")
    _, _, idx = _pac_file(rom, BIN2_PAC, "game_indx_e.bin")
    off = struct.unpack_from("<I", idx, TEXT_ID * 4)[0]
    return blob, ti, txt, off


def apply(rom) -> None:
    _check_tail(NEW_TAIL)
    mc, sec = _main_section(rom)
    d = bytearray(sec.data)
    o = TAIL - ARM9
    cur = bytes(d[o:o + len(NEW_TAIL)])
    if cur != NEW_TAIL:
        assert cur == OLD_TAIL, "get_limit tail is not stock+no_banlist -- run no_banlist_mode first"
        d[o:o + len(NEW_TAIL)] = NEW_TAIL
        sec.data = bytes(d)
        rom.arm9 = mc.save()

    blob, i, lim = _pac_file(rom, BIN_PAC, LIST_FILE)
    if not (lim[0:2] == b"\x00\x00" and lim[7] == CAP_BYTE):
        assert lim[4:8] == bytes(4), f"{LIST_FILE} header +4..+7 not zero: {lim[:8].hex()}"
        lim[0:2] = b"\x00\x00"       # count 0: every card unlisted
        lim[7] = CAP_BYTE
        rom.setFileByName(BIN_PAC, build_modified_pac(blob, BIN_PAC, {i: bytes(lim)}))

    blob, ti, txt, off = _text(rom)
    cur = bytes(txt[off:txt.index(NUL, off)])
    if cur != NEW_TEXT:
        assert cur == OLD_TEXT, f"text 0x{TEXT_ID:X} = {cur!r}"
        txt[off:off + len(OLD_TEXT)] = NEW_TEXT.ljust(len(OLD_TEXT), NUL)
        rom.setFileByName(BIN2_PAC, build_modified_pac(blob, BIN2_PAC, {ti: bytes(txt)}))


def main(write_text=None, src=SRC, out=OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    apply(rom)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    print(f"  wrote -> {out}")


def verify(out=OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(out))
    _, sec = _main_section(rom)
    code = bytes(sec.data[TAIL - ARM9:TAIL - ARM9 + len(NEW_TAIL)])
    assert code == NEW_TAIL, "get_limit tail not patched"
    _check_tail(code)
    _, _, lim = _pac_file(rom, BIN_PAC, LIST_FILE)
    assert lim[0:2] == b"\x00\x00" and lim[6:8] == bytes([0, CAP_BYTE]), lim[:8].hex()
    for name in ("limit200609.bin", "limit200703.bin", "limit200709.bin", "limit200909.bin", "limit201009.bin"):
        _, _, other = _pac_file(rom, BIN_PAC, name)
        assert other[7] == 0, f"{name} header+7 = {other[7]} (would cap below 3)"
    _, _, txt, off = _text(rom)
    assert bytes(txt[off:txt.index(NUL, off)]) == NEW_TEXT, "label not renamed"
    print("  [OK] Highlander list patched")


if __name__ == "__main__":
    main()
    verify()

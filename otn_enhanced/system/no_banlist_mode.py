"""Turn the built-in "Treat Ltd as Forb" Forbidden/Limited mode into "No Banlist".

Duelist Menu -> Forbidden/Limited Card List offers three built-in entries, all
built from limit201009.bin by load_list (arm9 Thumb @0x0202AC90). For entry
index 1 it stamps the list header in RAM (0x02121E94):
    +2 name id  = 0x53  (text 0x514+0x53 = 0x567 "Treat Ltd as Forb")
    +6 flags    = 1
get_limit (@0x0202AD9C) returns 0 copies for any listed card when flags bit0 is
set, else entry>>14; an unlisted card returns 3. Bit0 is read nowhere else (the
other flag readers 0x0201B10A / ov 0x02152DF0 / 0x021531C4 test only bit1, the
"Up to 1 Forb Card" mode). Proven 2026-10-05 from the default_list.mln /
limited_is_forbidden.mln savestate pair (the per-card copy array at 0x021FD1F0
goes {3:3964,1:67,0:47,2:18} -> {3:3964,0:132}).

Patch:
    0x0202ADD0  movs r0,#0 -> movs r0,#3   bit0 => every listed card allowed 3
    text 0x567 (game_text_e.bin) "Treat Ltd as Forb" -> "No Banlist", in place
"""
from __future__ import annotations

import struct
from pathlib import Path

import ndspy.code
import ndspy.rom

from otn_enhanced.rom.pac import build_modified_pac, parse_pac

SRC = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_no_banlist_test.nds"

ARM9 = 0x02000000
EDITS = {  # ram addr: (native, patched)
    0x0202ADD0: (b"\x00\x20", b"\x03\x20"),
}

BIN2_PAC = "Data_arc_pac/bin2.pac"
TEXT_ID = 0x567
OLD_TEXT, NEW_TEXT = b"Treat Ltd as Forb", b"No Banlist"
NUL = b"\x00"


def _text(rom):
    """Return (blob, text_file_index, idx, txt) for game_indx_e / game_text_e."""
    blob = bytes(rom.getFileByName(BIN2_PAC))
    ar = parse_pac(blob, BIN2_PAC)
    by = {f.get_clean_name(): i for i, f in enumerate(ar.files)}
    fi, ti = ar.files[by["game_indx_e.bin"]], by["game_text_e.bin"]
    ft = ar.files[ti]
    return blob, ti, blob[fi.address:fi.address + fi.size], bytearray(blob[ft.address:ft.address + ft.size])


def _label(idx, txt) -> bytes:
    off = struct.unpack_from("<I", idx, TEXT_ID * 4)[0]
    return bytes(txt[off:txt.index(NUL, off)])


def _rename(rom) -> None:
    blob, ti, idx, txt = _text(rom)
    cur = _label(idx, txt)
    if cur == NEW_TEXT:
        return
    assert cur == OLD_TEXT, f"text 0x{TEXT_ID:X} = {cur!r} -- wrong base ROM?"
    off = struct.unpack_from("<I", idx, TEXT_ID * 4)[0]
    txt[off:off + len(OLD_TEXT)] = NEW_TEXT.ljust(len(OLD_TEXT), NUL)  # shorter: in place
    rom.setFileByName(BIN2_PAC, build_modified_pac(blob, BIN2_PAC, {ti: bytes(txt)}))


def _main_section(rom):
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    return mc, next(s for s in mc.sections if s.ramAddress == rom.arm9RamAddress)


def apply(rom) -> None:
    mc, sec = _main_section(rom)
    d = bytearray(sec.data)
    for addr, (old, new) in EDITS.items():
        o = addr - ARM9
        cur = bytes(d[o:o + 2])
        if cur == new:
            continue
        assert cur == old, f"arm9 @0x{addr:08X} = {cur.hex()}, expected {old.hex()} -- wrong base ROM?"
        d[o:o + 2] = new
    sec.data = bytes(d)
    rom.arm9 = mc.save()
    _rename(rom)


def main(write_text=None, src=SRC, out=OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    apply(rom)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    print(f"  wrote -> {out}")


def verify(out=OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(out))
    _, sec = _main_section(rom)
    for addr, (_, new) in EDITS.items():
        o = addr - ARM9
        assert sec.data[o:o + 2] == new, f"arm9 @0x{addr:08X} not patched"
    _, _, idx, txt = _text(rom)
    assert _label(idx, txt) == NEW_TEXT, "label not renamed"
    print("  [OK] no-banlist mode patched")


if __name__ == "__main__":
    main()
    verify()

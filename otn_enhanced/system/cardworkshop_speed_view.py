"""CardWorkshop's CPU speed-up and View Mode (tools/wc2011/w11fast.py, BlueKitkallos, MIT).

Applies `w11fast.apply` with only the speed patches and View Mode (plus the cut-in and fade
tweaks that ride with View Mode); its card/text/duel fixes and SE-room change are left out.
Needs the CardWorkshop checkout at CW_COMMIT (env CARDWORKSHOP, default ../CardWorkshop) and
Arm GNU Toolchain cc.GCC_VERSION (env ARM_TOOLCHAIN); both are pinned and checked, because either
one changes the ROM bytes. Setup: docs/SETUP.md.

Runs before ov3 compaction: w11fast asserts its own stock before-images, and compaction then
asserts its runs are still stock, so an overlap fails the build instead of shipping.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys
from pathlib import Path

import ndspy.code

REPO = Path(__file__).resolve().parents[2]
CW = Path(os.environ.get("CARDWORKSHOP", REPO.parent / "CardWorkshop"))
CW_COMMIT = "3934f5cc3a54986666ababffc929ad083a82275c"  # pinned: github.com/BlueKitkallos/CardWorkshop

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_cw_speed_view.nds"


def _check_pins() -> None:
    from otn_enhanced.asm import cc
    head = subprocess.run(["git", "-C", str(CW), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(CW), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.strip()
    assert head == CW_COMMIT and not dirty, (
        f"{CW}: CardWorkshop at {head or 'no git checkout'}{' (modified)' if dirty else ''}, need a clean "
        f"{CW_COMMIT} -- see docs/SETUP.md")
    assert cc.GCC_VERSION in cc._run([cc._tool("gcc"), "--version"]), \
        f"arm-none-eabi-gcc is not {cc.GCC_VERSION} -- see docs/SETUP.md"
    os.environ["ARM_TOOLCHAIN"] = str(cc.TOOLCHAIN)  # w11fast reads it at import


def _cw():
    _check_pins()
    for p in (CW / "tools", CW / "tools" / "wc2011"):  # w11fast imports w11speed, game, carddb
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    ours = sys.modules.pop("pac", None)  # our otn_enhanced/rom/pac.py shadows CardWorkshop's tools/pac.py
    try:
        import game  # binds CardWorkshop's pac at import; w11fast imports it lazily
        import w11fast
        import w11speed
    finally:
        if ours is not None:
            sys.modules["pac"] = ours
    return w11fast, w11speed


def main(src: str = SRC, out: str = OUT) -> None:
    w11fast, w11speed = _cw()
    r = w11speed.Rom11(src)
    w11fast.apply(r, card_fixes=False, text_fixes=False, duel_fixes=False, sound=False)
    # Rom11.save forces ov.compressed; write back like overlay_io.save_overlay3 so the build
    # session keeps each overlay's own compression flag.
    r.code.sections[0].data = bytes(r.arm9.d)
    for data, ram in r.extra:
        r.code.sections.append(ndspy.code.MainCodeFile.Section(data, ram, 0, implicit=False))
    r.rom.arm9 = r.code.save()
    tbl = r.rom.arm9OverlayTable
    for i, img in r.ov.items():
        ov = r.ovs[i]
        if bytes(img.d) == bytes(ov.data):
            continue
        ov.data = bytes(img.d)
        packed = ov.save(compress=ov.compressed)
        r.rom.files[ov.fileID] = packed
        flags = struct.unpack_from("<I", tbl, i * 32 + 0x1C)[0] >> 24
        struct.pack_into("<I", tbl, i * 32 + 0x1C, (flags << 24) | (len(packed) & 0xFFFFFF))
    r.rom.saveToFile(out)
    print(f"CardWorkshop speed + View Mode -> {out}")


def verify(out: str = OUT) -> None:
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    code = ndspy.code.MainCodeFile(rom.arm9, rom.arm9RamAddress)
    assert struct.unpack_from("<I", code.sections[0].data, 0x02051E30 - rom.arm9RamAddress)[0] < 0x023E0000, \
        "arena top not lowered: View Mode code missing"
    assert struct.unpack_from("<H", code.sections[0].data, 0x02029C0C - rom.arm9RamAddress)[0] == 0x4778, \
        "card-prop lookup not trampolined: speed code missing"
    print("CardWorkshop speed + View Mode verify OK")


if __name__ == "__main__":
    main()
    verify()

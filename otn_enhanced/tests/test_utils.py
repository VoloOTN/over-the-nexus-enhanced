"""One runnable check per util: does it reproduce what `finished_patches/` already ships?

    uv run python -m otn_enhanced.tests.test_utils

Plain asserts, no framework. These are equivalence checks, not unit tests: each one calls the
ORIGINAL copy in `finished_patches/` and asserts the new util agrees. That is what stops this
package drifting from the bytes that are already in a working ROM.
"""
from __future__ import annotations

import struct

from otn_enhanced.effects import common
from otn_enhanced.effects.common import ARM9_BASE, OV3_BASE, Ov


def test_bl_matches_shipped_copies() -> None:
    """thumb.bl must equal the `_bl` copies actually used to build the shipped ROM."""
    from otn_enhanced.effects import criteria_row_hook
    from otn_enhanced.cards import darkflare as darkflare
    from otn_enhanced.effects.common import thumb_bl

    cases = [
        (0x02243BEC, 0x022C5900),   # forward, far    (a real criteria-row hook site)
        (0x0224C026, 0x022C6000),   # forward, far    (the hand-SS trampoline site)
        (0x022C5900, 0x02204D08),   # backward        (cave -> native resolver)
        (0x02141704, 0x02141708),   # minimal forward
    ]
    for src, dst in cases:
        want = criteria_row_hook._bl(src, dst)
        assert common.bl(src, dst) == want, f"bl(0x{src:08X}, 0x{dst:08X})"
        assert darkflare._bl(src, dst) == want, "darkflare._bl disagrees"
        assert thumb_bl(src, dst) == want, "boggart_knight._thumb_bl disagrees"
        assert len(want) == 4

    # a BL is two halfwords with the F000/F800 prefixes, and must round-trip through the decoder
    for src, dst in cases:
        buf = bytearray(0x20)
        buf[0x10:0x14] = common.bl(src, dst)
        assert common.bl_target(buf, src, src - 0x10) == dst

    try:
        common.bl(0x02000000, 0x02800000)          # +8 MB, well past +-4 MB
    except AssertionError:
        pass
    else:
        raise AssertionError("bl accepted an out-of-range branch")


def test_b_bcond_ldrpc_match_shipped() -> None:
    from otn_enhanced.cards import darkflare as darkflare, white_dragon_ninja as wdn

    assert common.b(0x02141704, 0x02141710) == darkflare._b(0x02141704, 0x02141710)
    assert common.bcond(0x02141704, 0x02141710, common.NE) == wdn._bcond(0x02141704, 0x02141710, 1)
    assert common.bcond(0x02141704, 0x02141700, common.EQ) == wdn._bcond(0x02141704, 0x02141700, 0)
    assert common.ldr_pc(0x02141704, 3, 0x02141710) == wdn._ldr_pc(0x02141704, 3, 0x02141710)

    # the (at+4)&~3 rounding is the subtle half: a 2-aligned site and a 4-aligned site
    # loading the SAME word encode different immediates
    assert common.ldr_pc(0x02141702, 0, 0x02141708) != common.ldr_pc(0x02141704, 0, 0x02141708)


def test_blx_target_guard() -> None:
    assert common.assert_blx_target(0x0221CD29) == 0x0221CD29
    try:
        common.assert_blx_target(0x0221CD28)       # the even address off a disassembly listing
    except AssertionError as exc:
        assert "bit 0 CLEAR" in str(exc)
    else:
        raise AssertionError("assert_blx_target accepted an even literal -- freeze not caught")


def test_ov_reads_and_bounds() -> None:
    buf = bytearray(0x100)
    struct.pack_into("<H", buf, 0x10, 0x1F18)     # "<" means no padding: the u32 would land
    struct.pack_into("<I", buf, 0x14, 0x0A550002)  # at 0x12, so write it explicitly at 0x14
    o = Ov(buf)

    assert o.off(OV3_BASE + 0x10) == 0x10
    assert o.u16(OV3_BASE + 0x10) == 0x1F18
    assert o.u32(OV3_BASE + 0x14) == 0x0A550002
    assert o.unpack(OV3_BASE + 0x10, "<H")[0] == 0x1F18
    assert o.blob(OV3_BASE + 0x10, 2) == b"\x18\x1f"
    assert o.end == OV3_BASE + 0x100

    o.set_u16(OV3_BASE + 0x10, 0x1463)
    assert o.u16(OV3_BASE + 0x10) == 0x1463
    assert buf is o.buf, "Ov must wrap, not copy"

    # the whole reason this class exists: a below-base address must RAISE, not wrap to the end
    for bad in (OV3_BASE - 4, OV3_BASE + 0x100, ARM9_BASE):
        try:
            o.u16(bad)
        except IndexError:
            pass
        else:
            raise AssertionError(f"0x{bad:08X} should be out of range")

    try:
        o.write(OV3_BASE + 0xFE, b"\x00" * 8)     # overlay 3 can never grow
    except IndexError:
        pass
    else:
        raise AssertionError("write past the end was allowed")


def test_ov_keys_matches_shipped_helper() -> None:
    """Ov.keys must agree with the `_keys` copied into 7 modules, on the real criteria table."""
    from otn_enhanced.rom.overlay_io import load_overlay3
    from otn_enhanced.cards import grapha

    rom, raw = load_overlay3("data/over_the_nexus/working/rom.nds")
    o = Ov(bytearray(raw))

    # geometry per jet_synchron.py:220-224 -- 1388 x 12 B, sorted by the u16 cid at +0
    base, count, stride = 0x022713C4, 0x56C, 12
    mine = o.keys(base, count=count, stride=stride)
    theirs = grapha._keys(o.buf, base, count, stride, False)
    assert mine == theirs, "Ov.keys disagrees with grapha._keys on the criteria registry"
    assert mine == sorted(mine), "criteria registry is not sorted -- wrong base/stride or ROM"
    assert len(mine) == 0x56C

    rows = o.rows(base, count=count, stride=stride, fmt="<HHII")
    assert [r[0] for r in rows] == mine, "Ov.rows and Ov.keys disagree on the leading key"


def test_arm9_edit_roundtrips_and_aborts_cleanly() -> None:
    """arm9_edit must write back through MainCodeFile, and write NOTHING on an exception."""
    import ndspy.rom

    from otn_enhanced.effects import common

    rom = ndspy.rom.NintendoDSRom.fromFile("data/over_the_nexus/working/rom.nds")

    secs = common.sections(rom)
    assert secs[ARM9_BASE] == 0xAF120, f"unexpected arm9 main section size {secs[ARM9_BASE]:#x}"
    assert 0x01FF8000 in secs, "the ITCM section is missing -- wrong ROM?"

    # the same section both shipped idioms select
    assert rom.arm9RamAddress == ARM9_BASE

    probe = 0x0209CB48                       # the T.G. set-code list (tg_table.py)
    original = common.view(rom).u16(probe)

    with common.arm9_edit(rom) as a9:
        a9.set_u16(probe, 0xBEEF)
    assert common.view(rom).u16(probe) == 0xBEEF, "arm9_edit did not write back"

    # an exception mid-edit must leave the ROM as it was, not half-patched
    try:
        with common.arm9_edit(rom) as a9:
            a9.set_u16(probe, 0xDEAD)
            raise RuntimeError("simulated mid-edit failure")
    except RuntimeError:
        pass
    assert common.view(rom).u16(probe) == 0xBEEF, "a failed edit was written back anyway"

    with common.arm9_edit(rom) as a9:          # put it back
        a9.set_u16(probe, original)
    assert common.view(rom).u16(probe) == original


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

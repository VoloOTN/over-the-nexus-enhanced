"""Expand the duel card-effect code space by appending to OVERLAY 5 and shrinking
the duel heap — Yu-Gi-Oh! WC2011 Over the Nexus (EU BYYP, working/rom.nds).

WHY THIS WORKS (proven 2026-06-09, see scratch/crossref_ov3_ov5.py):
  Overlay 3 (the card-effect engine) and OVERLAY 5 are CO-RESIDENT during every
  duel: ov3 makes 140 BL/BLX + 23 pointer references INTO ov5, and ov5 makes 274
  function-pointer references back into ov3.  ov5 is dense Thumb CODE (it is
  effectively "overlay 3, part 2").  ov5 ends at RAM 0x0239A120, which is EXACTLY
  the base of the duel heap/arena.  So:

    * Appending bytes to the END of ov5 places them at RAM 0x0239A120+, resident
      in every duel, with NO new overlay and NO loader hook (ov5 already loads).
    * Those bytes are within Thumb BL range (+-4MB) of both ov3 and ov5, so new
      handler code / tables there are directly callable from the effect engine.
    * To make room we raise the duel arena-lo so the heap starts ABOVE the grown
      ov5.  The arena-lo is a SINGLE arm9 literal:
          arm9 decompressed offset 0x51ED8  (RAM pool 0x02051ED8)  = 0x0239A120
      read by GetArenaLo(region) @0x02051E50 (region 1 -> ldr r0,[0x02051ED8]).
      It is the ONLY occurrence of 0x0239A120 in arm9 (single source of truth).

This tool is INTENTIONALLY INCREMENTAL so each change is independently testable
in melonDS before relying on it:

  mode="shrink_only"  (EXP1, safest foundation, no overlay change):
      Raise arena-lo by SHRINK bytes; change nothing else.  The region
      [0x0239A120 .. +SHRINK] becomes dead/reserved.  TEST: game boots + a full
      duel plays normally  =>  the literal is authoritative AND the duel heap has
      at least SHRINK bytes of slack.

  mode="append"  (EXP2/EXP3, the real expansion):
      Grow ov5 by SHRINK bytes (append PAYLOAD, zero/sig-padded to SHRINK) AND
      raise arena-lo by SHRINK, so the grown ov5 ends exactly at the new heap
      base (no gap).  Default PAYLOAD = a recognizable signature so you can read
      RAM 0x0239A120 in melonDS and confirm the space is loaded & resident.

  mode="exec"  (EXP3 execution proof, IN-GAME CONFIRMED 2026-06-09):
      Append a tiny Thumb-1 pass-through stub at 0x0239A120 and hook
      find_event_handler (hot, runs every duel) to BL into it.  If the duel
      plays normally, ov3 successfully EXECUTES code in the appended region.
      *** The ARM9 is ARMv5TE (Thumb-1 ONLY) -- injected code must never use
      Thumb-2 (B.W/MOVW/MOVT/CBZ); see _assert_thumb1. ***

USAGE:
    python -m otn_enhanced.tools.overlay5_expand --mode shrink_only --shrink 0x4000
    python -m otn_enhanced.tools.overlay5_expand --mode append      --shrink 0x4000
    python -m otn_enhanced.tools.overlay5_expand --mode exec         --shrink 0x4000
    python -m otn_enhanced.tools.overlay5_expand --verify   (re-check the last OUT)
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import ndspy.rom
import ndspy.codeCompression

# ---------------------------------------------------------------------------
# ROMs
# ---------------------------------------------------------------------------
SRC = "data/over_the_nexus/working/rom.nds"
OUT_SHRINK = "data/over_the_nexus/working/rom_ov5exp_shrink.nds"
OUT_APPEND = "data/over_the_nexus/working/rom_ov5exp_append.nds"
OUT_EXEC = "data/over_the_nexus/working/rom_ov5exp_exec.nds"
# ---------------------------------------------------------------------------
# Proven constants (EU BYYP working/rom.nds)
# ---------------------------------------------------------------------------
OVERLAY5_ID = 5
OV5_RAM_BASE = 0x022C5900           # ov5 load address (= ov3 footprint ceiling)
OV5_RAM_END = 0x0239A120            # ov5 end (decompressed) == duel arena-lo
ARENA_LO_VALUE = 0x0239A120         # the duel heap base literal (before-guard)
ARENA_LO_ARM9_OFF = 0x51ED8         # arm9 DECOMPRESSED offset of that literal
ARENA_HI_VALUE = 0x023E0000         # duel arena top (heap ceiling; for slack math)

SIGNATURE = b"OV5XPAND_v1_OTN!"     # 16 bytes; repeated to fill the payload

ALIGN = 0x20                        # keep arena-lo / ov5-end 0x20-aligned

# ---------------------------------------------------------------------------
# EXP3 "exec" proof constants (overlay 3, decompressed; RAM base 0x02141700)
# ---------------------------------------------------------------------------
# *** ISA NOTE (critical): the NDS ARM9 is ARM946E-S = ARMv5TE = THUMB-1 ONLY.
# It does NOT implement Thumb-2 (B.W, MOVW, MOVT, CBZ, ...).  Emitting any of
# those = undefined instruction = freeze.  (capstone's default mode decodes
# Thumb-2 and will silently "validate" illegal bytes -- do NOT trust it; use
# _assert_thumb1 below.)  All injected code here is pure Thumb-1: 32-bit consts
# come from `ldr rX,[pc,#imm]` literal pools and long branches use ARMv4T BL.
#
# IN-GAME PROVEN: `find_event_handler` 0x0224A118 runs on ~every
# duel event in every mode.  We hook it AT 0x0224A11A -- just AFTER its
# `push {r1-r7,lr}` (so LR is already saved) -- replacing the two 16-bit insns
# `adds r4,r0,#0 ; ldrh r0,[r4]` (041c2088) with an ARMv4T `BL` into a Thumb-1
# stub at the start of the appended ov5 region.  The stub replays those two
# insns and returns -- a pass-through that PROVES ov3 executes appended-region
# code (the duel plays normally instead of freezing).
OV3_ID = 3
OV3_RAM_BASE = 0x02141700
EXEC_HOOK_RAM = 0x0224A11A           # inside find_event_handler, after its push
EXEC_HOOK_OFF = EXEC_HOOK_RAM - OV3_RAM_BASE
EXEC_HOOK_ORIG = bytes.fromhex("041c2088")     # adds r4,r0,#0 ; ldrh r0,[r4]
EXEC_RETURN_RAM = 0x0224A11E         # resume after the 4 replaced bytes


# ---------------------------------------------------------------------------
# Thumb-1 (ARMv4T / ARMv5TE-legal) encoders + legality guard.  NO Thumb-2.
# ---------------------------------------------------------------------------
_THUMB2_BANNED = {
    "movw", "movt", "b.w", "bl.w", "cbz", "cbnz", "it", "tbb", "tbh",
    "ldr.w", "str.w", "add.w", "sub.w", "mov.w", "ldrh.w", "strh.w",
}


def _enc_bl(pc: int, target: int) -> bytes:
    """ARMv4T BL (two 16-bit halfwords). Legal on ARMv5TE. Range +-4MB."""
    off = target - (pc + 4)
    assert -(1 << 22) <= off < (1 << 22), f"BL out of range: {off:#x}"
    hi = 0xF000 | ((off >> 12) & 0x7FF)
    lo = 0xF800 | ((off >> 1) & 0x7FF)
    return bytes([hi & 0xFF, hi >> 8, lo & 0xFF, lo >> 8])


def _assert_thumb1(code: bytes, base: int, label: str = "code") -> None:
    """Disassemble *code* and assert every instruction is Thumb-1-legal.

    Guards against accidentally emitting Thumb-2 (which freezes on ARMv5TE).
    Skipped silently if capstone is unavailable.
    """
    try:
        import capstone
    except Exception:
        return
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    for ins in md.disasm(code, base):
        assert ins.mnemonic not in _THUMB2_BANNED, (
            f"{label}: illegal Thumb-2 insn {ins.mnemonic} @0x{ins.address:08X} "
            f"({ins.bytes.hex()}) -- would freeze on ARMv5TE"
        )


def _build_exec_stub() -> bytes:
    """Thumb-1 pass-through stub for the appended region (proves execution).

    push {lr} ; <replay the 2 displaced insns> ; pop {pc}
    """
    stub = bytes.fromhex("00b5") + EXEC_HOOK_ORIG + bytes.fromhex("00bd")
    _assert_thumb1(stub, OV5_RAM_END, "exec stub")
    return stub


# ---------------------------------------------------------------------------
# ARM9 helper: raise the duel arena-lo by *shrink* bytes
# ---------------------------------------------------------------------------
def _raise_arena_lo(rom: "ndspy.rom.NintendoDSRom", shrink: int) -> int:
    """Add *shrink* to the duel arena-lo literal in arm9.  Returns the new value."""
    dec = bytearray(ndspy.codeCompression.decompress(bytes(rom.arm9)))
    cur = struct.unpack_from("<I", dec, ARENA_LO_ARM9_OFF)[0]
    assert cur == ARENA_LO_VALUE, (
        f"arm9 @0x{ARENA_LO_ARM9_OFF:X}: expected arena-lo 0x{ARENA_LO_VALUE:08X}, "
        f"found 0x{cur:08X} -- wrong base ROM?"
    )
    new_lo = cur + shrink
    assert new_lo < ARENA_HI_VALUE, "shrink too large: would invert the heap"
    struct.pack_into("<I", dec, ARENA_LO_ARM9_OFF, new_lo)
    rom.arm9 = ndspy.codeCompression.compress(bytes(dec), True)  # isArm9=True -> BLZ footer
    return new_lo


# ---------------------------------------------------------------------------
# Overlay-5 helper: append *payload* (padded to *shrink*) at ov5's end
# ---------------------------------------------------------------------------
def _grow_overlay5(rom: "ndspy.rom.NintendoDSRom", payload: bytes, shrink: int) -> None:
    """Append *payload* (zero-padded up to *shrink* bytes) to overlay 5."""
    assert len(payload) <= shrink, "payload longer than the reserved shrink window"
    ov = rom.loadArm9Overlays([OVERLAY5_ID])[OVERLAY5_ID]
    old = bytes(ov.data)
    assert ov.ramAddress == OV5_RAM_BASE, f"ov5 base 0x{ov.ramAddress:08X} unexpected"
    assert ov.ramAddress + len(old) == OV5_RAM_END, (
        f"ov5 end 0x{ov.ramAddress + len(old):08X} != expected 0x{OV5_RAM_END:08X}"
    )
    block = bytearray(shrink)
    block[: len(payload)] = payload
    new_data = old + bytes(block)

    ov.data = new_data
    ov.ramSize = len(new_data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed

    # propagate ramSize + compressed size into the overlay table (ndspy won't)
    tbl = rom.arm9OverlayTable
    entry = OVERLAY5_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(new_data))
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    struct.pack_into("<I", tbl, entry + 0x1C,
                     ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


# ---------------------------------------------------------------------------
# Overlay-3 helper: detour find_event_handler into the appended-region stub
# ---------------------------------------------------------------------------
def _hook_overlay3_exec(rom: "ndspy.rom.NintendoDSRom") -> None:
    """Replace the 4 bytes at EXEC_HOOK_RAM with an ARMv4T `BL` into the stub."""
    ov = rom.loadArm9Overlays([OV3_ID])[OV3_ID]
    dec = bytearray(ov.data)
    cur = bytes(dec[EXEC_HOOK_OFF:EXEC_HOOK_OFF + 4])
    assert cur == EXEC_HOOK_ORIG, (
        f"ov3 @0x{EXEC_HOOK_OFF:X}: expected {EXEC_HOOK_ORIG.hex()} "
        f"(adds r4,r0,#0; ldrh r0,[r4]), found {cur.hex()} -- wrong base ROM?"
    )
    bl = _enc_bl(EXEC_HOOK_RAM, OV5_RAM_END)   # call the stub at the appended start
    _assert_thumb1(bl, EXEC_HOOK_RAM, "exec hook BL")
    dec[EXEC_HOOK_OFF:EXEC_HOOK_OFF + 4] = bl

    ov.data = bytes(dec)
    ov.ramSize = len(dec)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed
    tbl = rom.arm9OverlayTable
    entry = OV3_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(dec))
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    struct.pack_into("<I", tbl, entry + 0x1C,
                     ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def main(*, mode: str = "shrink_only", shrink: int = 0x4000,
         payload: bytes | None = None, src: str | Path = SRC,
         out: str | Path | None = None) -> str:
    """Build an expanded ROM.

    mode="shrink_only": only raise arena-lo (EXP1).
    mode="append":      grow ov5 by *shrink* (payload sig-padded) + raise arena-lo (EXP2).
    mode="exec":        grow ov5 with an LP-detour trampoline at its start + hook
                        overlay 3's starting-LP build to call it + raise arena-lo
                        (EXP3 — proves ov3 EXECUTES code in the appended region; a
                        regular duel then starts both players at EXEC_LP_VALUE).
    """
    assert shrink % ALIGN == 0, f"shrink must be a multiple of 0x{ALIGN:X}"
    if out is None:
        out = {"shrink_only": OUT_SHRINK, "append": OUT_APPEND, "exec": OUT_EXEC}[mode]

    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))

    if mode == "append":
        if payload is None:
            payload = (SIGNATURE * ((shrink // len(SIGNATURE)) or 1))[:shrink]
        _grow_overlay5(rom, payload, shrink)
    elif mode == "exec":
        stub = _build_exec_stub()
        _grow_overlay5(rom, stub, shrink)    # Thumb-1 pass-through stub at OV5_RAM_END
        _hook_overlay3_exec(rom)             # BL find_event_handler -> stub

    new_lo = _raise_arena_lo(rom, shrink)

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))

    print(f"  mode          : {mode}")
    print(f"  shrink        : 0x{shrink:X} ({shrink} bytes, {shrink/1024:.1f} KB)")
    print(f"  arena-lo      : 0x{ARENA_LO_VALUE:08X} -> 0x{new_lo:08X}")
    print(f"  duel heap     : 0x{new_lo:08X}..0x{ARENA_HI_VALUE:08X} "
          f"(0x{ARENA_HI_VALUE-new_lo:X} = {(ARENA_HI_VALUE-new_lo)//1024} KB left)")
    if mode in ("append", "exec"):
        print(f"  ov5 grown     : 0x{OV5_RAM_BASE:08X}..0x{OV5_RAM_END+shrink:08X} "
              f"(+0x{shrink:X}); new space @0x{OV5_RAM_END:08X}")
    if mode == "append":
        print(f"  signature     : {SIGNATURE!r} (read RAM 0x{OV5_RAM_END:08X} in melonDS)")
    if mode == "exec":
        print(f"  ov3 exec hook : 0x{EXEC_HOOK_RAM:08X} (in find_event_handler) "
              f"-> BL 0x{OV5_RAM_END:08X} (Thumb-1 stub)")
        print(f"  PROOF (visual): the duel plays normally (no freeze) => ov3 EXECUTES "
              f"the Thumb-1 stub in the appended ov5 region")
    print(f"  wrote -> {out}")
    return str(out)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
def verify(out: str | Path, *, mode: str, shrink: int) -> bool:
    """Re-open *out* and confirm the arena-lo + (for append) ov5 size & signature,
    and that overlay 3 is byte-identical to the source (untouched)."""
    rom = ndspy.rom.NintendoDSRom.fromFile(str(out))
    src = ndspy.rom.NintendoDSRom.fromFile(SRC)
    ok = True

    arm9 = ndspy.codeCompression.decompress(bytes(rom.arm9))
    lo = struct.unpack_from("<I", arm9, ARENA_LO_ARM9_OFF)[0]
    good = lo == ARENA_LO_VALUE + shrink
    ok &= good
    print(f"    arena-lo = 0x{lo:08X} (expect 0x{ARENA_LO_VALUE+shrink:08X})  "
          f"{'OK' if good else 'FAIL'}")

    # overlay 3: untouched for shrink/append; for exec it carries the LP hook only
    ov3_out = bytes(rom.loadArm9Overlays([3])[3].data)
    ov3_src = bytes(src.loadArm9Overlays([3])[3].data)
    if mode == "exec":
        # exactly the 4 hook bytes differ, replaced by a Thumb-1 BL into the stub
        diffs = [i for i in range(min(len(ov3_out), len(ov3_src))) if ov3_out[i] != ov3_src[i]]
        expect_bl = _enc_bl(EXEC_HOOK_RAM, OV5_RAM_END)
        good = (len(ov3_out) == len(ov3_src)
                and diffs == list(range(EXEC_HOOK_OFF, EXEC_HOOK_OFF + 4))
                and bytes(ov3_out[EXEC_HOOK_OFF:EXEC_HOOK_OFF + 4]) == expect_bl)
        ok &= good
        print(f"    ov3 exec hook only ({len(diffs)} bytes @0x{EXEC_HOOK_OFF:X}): "
              f"{'OK' if good else 'FAIL'}")
        _assert_thumb1(bytes(ov3_out[EXEC_HOOK_OFF:EXEC_HOOK_OFF + 4]), EXEC_HOOK_RAM, "ov3 hook")
    else:
        good = ov3_out == ov3_src
        ok &= good
        print(f"    overlay 3 unchanged: {'OK' if good else 'FAIL'}")

    ov5 = rom.loadArm9Overlays([OVERLAY5_ID])[OVERLAY5_ID]
    ov5_data = bytes(ov5.data)
    base_len = OV5_RAM_END - OV5_RAM_BASE
    src_ov5 = bytes(src.loadArm9Overlays([OVERLAY5_ID])[OVERLAY5_ID].data)
    if mode in ("append", "exec"):
        good = len(ov5_data) == base_len + shrink
        ok &= good
        print(f"    ov5 size = 0x{len(ov5_data):X} (expect 0x{base_len+shrink:X})  "
              f"{'OK' if good else 'FAIL'}")
        good = ov5_data[:base_len] == src_ov5
        ok &= good
        print(f"    ov5 original content preserved: {'OK' if good else 'FAIL'}")
        if mode == "append":
            sig = ov5_data[base_len: base_len + len(SIGNATURE)]
            good = sig == SIGNATURE
            ok &= good
            print(f"    ov5 signature @end = {sig!r}  {'OK' if good else 'FAIL'}")
        else:  # exec: Thumb-1 stub at the appended start
            expect_stub = _build_exec_stub()
            got = ov5_data[base_len: base_len + len(expect_stub)]
            good = got == expect_stub
            ok &= good
            print(f"    ov5 stub @0x{OV5_RAM_END:08X} = {got.hex()}  "
                  f"{'OK' if good else 'FAIL'}")
            _assert_thumb1(got, OV5_RAM_END, "ov5 stub")
    else:
        good = len(ov5_data) == base_len
        ok &= good
        print(f"    ov5 size unchanged = 0x{len(ov5_data):X}  {'OK' if good else 'FAIL'}")

    print(f"  VERIFY {'PASS' if ok else 'FAIL'}")
    return ok


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append to ov5 + shrink duel heap.")
    p.add_argument("--mode", choices=["shrink_only", "append", "exec"], default="shrink_only")
    p.add_argument("--shrink", default="0x4000",
                   help="bytes to shrink the heap by (multiple of 0x20)")
    p.add_argument("--verify", action="store_true", help="verify the matching OUT ROM")
    return p.parse_args(argv)


if __name__ == "__main__":
    ns = _parse(sys.argv[1:])
    shrink = int(ns.shrink, 0)
    out = {"shrink_only": OUT_SHRINK, "append": OUT_APPEND, "exec": OUT_EXEC}[ns.mode]
    if ns.verify:
        verify(out, mode=ns.mode, shrink=shrink)
    else:
        main(mode=ns.mode, shrink=shrink)
        verify(out, mode=ns.mode, shrink=shrink)

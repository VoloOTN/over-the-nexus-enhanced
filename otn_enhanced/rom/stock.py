"""Stock game images, read from the user's own dumps -- never committed.

Replaces the old ``otn_enhanced/reference_files/`` binaries.

NDS, from the base ROM ``data/over_the_nexus/working/rom.nds``:
  * :func:`arm9` -- decompressed ARM9 main section (base 0x02000000); byte-identical
    to the old ``arm9.bin``.
  * :func:`ov3`  -- overlay 3 (base 0x02141700); byte-identical to the old
    ``nds_overlay_3.bin``.
  * :func:`bin2` -- a file from ``Data_arc_pac/bin2.pac`` (``card_prop.bin``,
    ``card_indx_e.bin``, ``card_name_e.bin``, ``card_desc_e.bin``).  Same framing
    as the old ``nds_*.bin`` copies; the old ``card_prop``/``desc`` copies were stale.

3DS, from a local extract at ``3ds_extract/partition0`` (see CLAUDE.md):
  * :func:`threeds` -- e.g. ``threeds(CODE_3DS)`` (old ``3ds_overlay_3.bin``),
    ``threeds(CARD_3DS + "CARD_Prop.bin")`` (old ``3ds_card_prop.bin``).

Missing source -> ``FileNotFoundError``; callers that can degrade should catch it.
"""
from __future__ import annotations

import functools
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_ROM = ROOT / "data" / "over_the_nexus" / "working" / "rom.nds"
EXTRACT_3DS = ROOT / "3ds_extract" / "partition0"
CODE_3DS = "exefs/code_dec.bin"
CARD_3DS = "romfs/duel/card/"


@functools.lru_cache(maxsize=1)
def _rom():
    if not BASE_ROM.exists():
        raise FileNotFoundError(f"base ROM not found: {BASE_ROM}")
    import ndspy.rom
    return ndspy.rom.NintendoDSRom.fromFile(str(BASE_ROM))


@functools.lru_cache(maxsize=1)
def arm9() -> bytes:
    return bytes(_rom().loadArm9().sections[0].data)


@functools.lru_cache(maxsize=1)
def ov3() -> bytes:
    return bytes(_rom().loadArm9Overlays([3])[3].data)


@functools.lru_cache(maxsize=None)
def bin2(name: str) -> bytes:
    from otn_enhanced.rom.pac_inplace import parse_pac_v1
    pac = bytes(_rom().getFileByName("Data_arc_pac/bin2.pac"))
    arch = parse_pac_v1(pac)
    entry = arch.by_name(name)
    if entry is None:
        raise FileNotFoundError(f"{name} not in bin2.pac")
    return bytes(arch.payload(pac, entry))


def threeds(rel: str) -> bytes:
    return (EXTRACT_3DS / rel).read_bytes()


if __name__ == "__main__":
    assert len(arm9()) == 717088 and len(ov3()) == 1387744
    assert len(bin2("card_prop.bin")) == 34448 and len(bin2("card_indx_e.bin")) == 34456
    print("stock images OK")

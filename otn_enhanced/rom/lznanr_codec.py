"""Decoder / encoder for lznanr (NITRO) compressed NDS graphics resources.

Binary layout
=============
lznanr files are LZ-compressed (typically LZ11) NDS **NITRO** containers.
After decompression the payload uses the standard NITRO generic header
followed by one or more type-specific sections.

NITRO Generic Header (16 bytes)
-------------------------------
Offset  Size  Description
------  ----  -----------
0       4     Magic (e.g. ``RGCN`` for NCGR, ``RLCN`` for NCLR, …)
4       2     BOM  ``0xFEFF`` (little-endian)
6       2     Version (typically ``0x0100`` or ``0x0101``)
8       4     Total file size
12      2     Header size (16)
14      2     Number of sections

Each section starts with a 4-byte ASCII tag and 4-byte little-endian size.

Supported format types
----------------------
===========  =======  ============================  ===================
Magic (LE)   Format   Name                          Primary section tag
===========  =======  ============================  ===================
``RGCN``     NCGR     Character Graphic Resource    ``RAHC`` (CHAR)
``RLCN``     NCLR     Colour Resource (palette)     ``TTLP`` (PLTT)
``RECN``     NCER     Cell Resource (sprites)       ``KBEC`` (CEBK)
``RNAN``     NANR     Animation Resource            ``KNBA`` (ABNK)
``RCSN``     NSCR     Screen Resource (tilemap)     ``NRCS`` (SCRN)
``RCMN``     NMCR     Multi-Cell Resource           ``KBCM`` (MCBK)
``RAMN``     NMAR     Multi-Animation Resource      ``KNBA`` (ABNK)
``NTBG``     NTBG     (custom background – delegate to lz5bg_codec)
===========  =======  ============================  ===================

NCGR – ``RAHC`` (CHAR) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u16  height_tiles  (0xFFFF = unspecified / linear)
+2   u16  width_tiles   (0xFFFF = unspecified / linear)
+4   u32  bpp_flag      (3 = 4 bpp, 4 = 8 bpp)
+8   u32  mapping_type
+12  u32  flags
+16  u32  data_size     (byte count of tile pixel data)
+20  u32  padding
+24  …    tile pixel data

NCLR – ``TTLP`` (PLTT) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u32  bpp_flag      (3 = 4 bpp, 4 = 8 bpp)
+4   u32  padding
+8   u32  data_size     (byte count of palette data)
+12  u32  colour_offset (offset from section body start to first colour)
+16  …    BGR555 palette entries (2 bytes each)

NSCR – ``NRCS`` (SCRN) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u16  screen_width   (pixels)
+2   u16  screen_height  (pixels)
+4   u16  padding1
+6   u16  padding2
+8   u32  data_size
+12  …    tilemap entries (2 bytes each, same format as NTBG BGDT tilemap)

NCER – ``KBEC`` (CEBK) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u16  num_cells
+2   u16  cell_type       (0 = OAM-style, 1 = extended)
+4   u32  cell_data_offset
+8   u32  mapping_mode
+12  …    cell definition data

NANR – ``KNBA`` (ABNK) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u16  num_animations
+2   u16  num_frames
+4   u16  unknown
+6   u16  padding
+8   u32  anim_data_offset
+12  u32  frame_data_offset
+16  u32  frame_result_offset
+20  …    animation / frame data

``LBAL`` (LABL) section
~~~~~~~~~~~~~~~~~~~~~~~
Offset table of u32 followed by null-terminated ASCII label strings.

``TXEU`` (UEXT) section
~~~~~~~~~~~~~~~~~~~~~~~~
User extension block (usually 4 bytes of zeroes).
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import struct
from typing import Any

from PIL import Image

from otn_enhanced.rom.lz_compression import compress, decompress
from otn_enhanced.rom.nitro_common import _bgr555_to_rgb, _rgb_to_bgr555, _decode_tile_4bpp, _decode_tile_8bpp, _encode_tile_4bpp, _encode_tile_8bpp, _build_char_section, _build_generic_section, _render_nclr_palette, _colour_distance_sq, _map_to_palette, _quantize_image  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NDS NITRO format name mapping
# ---------------------------------------------------------------------------

# Magic bytes (LE in file) → human-friendly format name
MAGIC_TO_FORMAT: dict[bytes, str] = {
    b"RGCN": "NCGR",
    b"RLCN": "NCLR",
    b"RECN": "NCER",
    b"RNAN": "NANR",
    b"RCSN": "NSCR",
    b"RCMN": "NMCR",
    b"RAMN": "NMAR",
    b"NTBG": "NTBG",
    b"BCA0": "BCA0",
}

# Section tags (LE) → display name
TAG_DISPLAY: dict[bytes, str] = {
    b"RAHC": "CHAR",
    b"TTLP": "PLTT",
    b"PMCP": "PCMP",
    b"KBEC": "CEBK",
    b"KNBA": "ABNK",
    b"NRCS": "SCRN",
    b"KBCM": "MCBK",
    b"LBAL": "LABL",
    b"TXEU": "UEXT",
    b"KRMN": "NMRK",
    b"KNAL": "LANK",
}


# ---------------------------------------------------------------------------
# Low-level NDS helpers (shared with lz5bg_codec but kept standalone)
# ---------------------------------------------------------------------------

def _detect_compression_type(raw: bytes) -> int:
    """Detect the LZ compression type from the first byte of compressed data."""
    if len(raw) == 0:
        return 0x11
    header = raw[0]
    if header in (0x10, 0x11, 0x50):
        return header
    return 0x11


# ---------------------------------------------------------------------------
# Generic NITRO container parser
# ---------------------------------------------------------------------------

def _parse_nitro_header(data: bytes) -> dict[str, Any]:
    """Parse the 16-byte NITRO generic header."""
    if len(data) < 16:
        raise ValueError(f"Data too short for NITRO header ({len(data)} bytes)")
    magic = data[:4]
    bom = struct.unpack_from("<H", data, 4)[0]
    version = struct.unpack_from("<H", data, 6)[0]
    file_size = struct.unpack_from("<I", data, 8)[0]
    header_size = struct.unpack_from("<H", data, 12)[0]
    num_sections = struct.unpack_from("<H", data, 14)[0]
    return {
        "magic": magic,
        "format": MAGIC_TO_FORMAT.get(magic, magic.decode("ascii", errors="replace")),
        "bom": bom,
        "version": version,
        "file_size": file_size,
        "header_size": header_size,
        "num_sections": num_sections,
    }


def _walk_sections(data: bytes, header_size: int, num_sections: int) -> list[dict[str, Any]]:
    """Walk sections and return a list of ``{tag, offset, size}`` dicts."""
    sections: list[dict[str, Any]] = []
    offset = header_size
    for _ in range(num_sections):
        if offset + 8 > len(data):
            break
        tag = data[offset:offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        sections.append({"tag": tag, "offset": offset, "size": size})
        offset += size
    return sections


# ---------------------------------------------------------------------------
# Section-specific parsers (decode)
# ---------------------------------------------------------------------------

def _parse_char_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NCGR CHAR (RAHC) section."""
    body_off = offset + 8
    if body_off + 24 > len(data):
        return {"error": "CHAR section truncated"}
    height_tiles = struct.unpack_from("<H", data, body_off)[0]
    width_tiles = struct.unpack_from("<H", data, body_off + 2)[0]
    bpp_flag = struct.unpack_from("<I", data, body_off + 4)[0]
    mapping_type = struct.unpack_from("<I", data, body_off + 8)[0]
    flags = struct.unpack_from("<I", data, body_off + 12)[0]
    data_size = struct.unpack_from("<I", data, body_off + 16)[0]
    padding = struct.unpack_from("<I", data, body_off + 20)[0]

    bpp = 4 if bpp_flag == 3 else (8 if bpp_flag == 4 else bpp_flag)
    bytes_per_tile = 32 if bpp == 4 else 64
    num_tiles = data_size // bytes_per_tile if bytes_per_tile else 0

    tile_data_start = body_off + 24
    tile_data = data[tile_data_start:tile_data_start + data_size]

    return {
        "height_tiles": height_tiles,
        "width_tiles": width_tiles,
        "bpp_flag": bpp_flag,
        "bpp": bpp,
        "mapping_type": f"0x{mapping_type:08X}",
        "flags": f"0x{flags:08X}",
        "data_size": data_size,
        "padding": f"0x{padding:08X}",
        "num_tiles": num_tiles,
        "tile_data_b64": base64.b64encode(tile_data).decode("ascii"),
    }


def _parse_pltt_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NCLR PLTT (TTLP) section."""
    body_off = offset + 8
    if body_off + 16 > len(data):
        return {"error": "PLTT section truncated"}
    bpp_flag = struct.unpack_from("<I", data, body_off)[0]
    pad = struct.unpack_from("<I", data, body_off + 4)[0]
    data_size = struct.unpack_from("<I", data, body_off + 8)[0]
    colour_offset = struct.unpack_from("<I", data, body_off + 12)[0]

    bpp = 4 if bpp_flag == 3 else (8 if bpp_flag == 4 else bpp_flag)
    num_colours = data_size // 2

    # Parse all colours
    pal_start = body_off + colour_offset
    colours: list[list[int]] = []
    for i in range(num_colours):
        pos = pal_start + i * 2
        if pos + 2 > len(data):
            break
        val = struct.unpack_from("<H", data, pos)[0]
        colours.append(list(_bgr555_to_rgb(val)))

    return {
        "bpp_flag": bpp_flag,
        "bpp": bpp,
        "padding": f"0x{pad:08X}",
        "data_size": data_size,
        "colour_offset": colour_offset,
        "num_colours": num_colours,
        "colours_rgb": colours,
    }


def _parse_pcmp_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NCLR PCMP section."""
    body_off = offset + 8
    result: dict[str, Any] = {}
    if body_off + 4 <= len(data):
        result["num_palettes"] = struct.unpack_from("<H", data, body_off)[0]
        result["padding"] = struct.unpack_from("<H", data, body_off + 2)[0]
    if body_off + 8 <= len(data):
        result["palette_index"] = struct.unpack_from("<I", data, body_off + 4)[0]
    return result


def _parse_cebk_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NCER CEBK (KBEC) section."""
    body_off = offset + 8
    if body_off + 12 > len(data):
        return {"error": "CEBK section truncated"}
    num_cells = struct.unpack_from("<H", data, body_off)[0]
    cell_type = struct.unpack_from("<H", data, body_off + 2)[0]
    cell_data_offset = struct.unpack_from("<I", data, body_off + 4)[0]
    mapping_mode = struct.unpack_from("<I", data, body_off + 8)[0]

    # Read raw cell data for preservation
    cell_body = data[body_off + 12:offset + size]

    return {
        "num_cells": num_cells,
        "cell_type": cell_type,
        "cell_data_offset": f"0x{cell_data_offset:08X}",
        "mapping_mode": f"0x{mapping_mode:08X}",
        "cell_data_b64": base64.b64encode(cell_body).decode("ascii"),
    }


def _parse_abnk_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NANR/NMAR ABNK (KNBA) section."""
    body_off = offset + 8
    if body_off + 20 > len(data):
        return {"error": "ABNK section truncated"}
    num_anims = struct.unpack_from("<H", data, body_off)[0]
    num_frames = struct.unpack_from("<H", data, body_off + 2)[0]
    unknown = struct.unpack_from("<H", data, body_off + 4)[0]
    pad = struct.unpack_from("<H", data, body_off + 6)[0]
    anim_offset = struct.unpack_from("<I", data, body_off + 8)[0]
    frame_offset = struct.unpack_from("<I", data, body_off + 12)[0]
    frame_data_offset = struct.unpack_from("<I", data, body_off + 16)[0]

    # Preserve all animation/frame data
    anim_body = data[body_off + 20:offset + size]

    return {
        "num_animations": num_anims,
        "num_frames": num_frames,
        "unknown": unknown,
        "padding": pad,
        "anim_data_offset": f"0x{anim_offset:08X}",
        "frame_data_offset": f"0x{frame_offset:08X}",
        "frame_result_offset": f"0x{frame_data_offset:08X}",
        "anim_data_b64": base64.b64encode(anim_body).decode("ascii"),
    }


def _parse_scrn_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NSCR SCRN (NRCS) section."""
    body_off = offset + 8
    if body_off + 12 > len(data):
        return {"error": "SCRN section truncated"}
    scr_w = struct.unpack_from("<H", data, body_off)[0]
    scr_h = struct.unpack_from("<H", data, body_off + 2)[0]
    pad1 = struct.unpack_from("<H", data, body_off + 4)[0]
    pad2 = struct.unpack_from("<H", data, body_off + 6)[0]
    data_size = struct.unpack_from("<I", data, body_off + 8)[0]

    map_start = body_off + 12
    map_data = data[map_start:map_start + data_size]

    return {
        "screen_width": scr_w,
        "screen_height": scr_h,
        "padding1": pad1,
        "padding2": pad2,
        "data_size": data_size,
        "tilemap_data_b64": base64.b64encode(map_data).decode("ascii"),
    }


def _parse_mcbk_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NMCR MCBK (KBCM) section."""
    body_off = offset + 8
    body = data[body_off:offset + size]
    return {
        "data_b64": base64.b64encode(body).decode("ascii"),
    }


def _parse_labl_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse LABL section – label name table."""
    body_off = offset + 8
    body_size = size - 8
    if body_size <= 0:
        return {"labels": []}
    body = data[body_off:body_off + body_size]

    # Read offset table
    offsets: list[int] = []
    pos = 0
    while pos + 4 <= len(body):
        str_off = struct.unpack_from("<I", body, pos)[0]
        if str_off >= len(body):
            break
        offsets.append(str_off)
        pos += 4
        # Heuristic: stop when we reach the string data region
        if len(offsets) > 0 and pos >= offsets[0]:
            break

    labels: list[str] = []
    for str_off in offsets:
        end = body.find(b"\x00", str_off)
        if end < 0:
            end = len(body)
        labels.append(body[str_off:end].decode("ascii", errors="replace"))

    return {"labels": labels}


def _parse_uext_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse UEXT (TXEU) section."""
    body_off = offset + 8
    body = data[body_off:offset + size]
    return {"data_hex": body.hex()}


def _parse_generic_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Fallback parser for unknown sections."""
    body_off = offset + 8
    body = data[body_off:offset + size]
    return {"data_b64": base64.b64encode(body).decode("ascii")}


# Section tag → parser
_SECTION_PARSERS: dict[bytes, Any] = {
    b"RAHC": _parse_char_section,
    b"TTLP": _parse_pltt_section,
    b"PMCP": _parse_pcmp_section,
    b"KBEC": _parse_cebk_section,
    b"KNBA": _parse_abnk_section,
    b"NRCS": _parse_scrn_section,
    b"KBCM": _parse_mcbk_section,
    b"LBAL": _parse_labl_section,
    b"TXEU": _parse_uext_section,
}


# ---------------------------------------------------------------------------
# JSON decode – public API
# ---------------------------------------------------------------------------

def decode_lznanr(raw: bytes) -> dict[str, Any]:
    """Decompress and parse an lznanr file into a structured dict.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lznanr data from a PAC archive.

    Returns
    -------
    dict
        Structured representation of the NITRO container.

    Raises
    ------
    ValueError
        If the data cannot be decompressed or parsed.
    """
    try:
        data = decompress(raw)
    except Exception as exc:
        raise ValueError(f"LZ decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)
    sections_raw = _walk_sections(data, hdr["header_size"], hdr["num_sections"])

    sections_out: list[dict[str, Any]] = []
    for sec in sections_raw:
        tag = sec["tag"]
        parser = _SECTION_PARSERS.get(tag, _parse_generic_section)
        parsed = parser(data, sec["offset"], sec["size"])
        sections_out.append({
            "tag": tag.decode("ascii", errors="replace"),
            "tag_display": TAG_DISPLAY.get(tag, tag[::-1].decode("ascii", errors="replace")),
            "offset": sec["offset"],
            "size": sec["size"],
            "parsed": parsed,
        })

    return {
        "format": hdr["format"],
        "magic": hdr["magic"].decode("ascii", errors="replace"),
        "bom": f"0x{hdr['bom']:04X}",
        "version": f"0x{hdr['version']:04X}",
        "file_size": hdr["file_size"],
        "header_size": hdr["header_size"],
        "num_sections": hdr["num_sections"],
        "compression_type": f"0x{_detect_compression_type(raw):02X}",
        "decompressed_size": len(data),
        "sections": sections_out,
    }


def decode_lznanr_to_json(raw: bytes) -> str:
    """Decompress, parse, and return a JSON string for an lznanr file."""
    result = decode_lznanr(raw)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# JSON encode – public API
# ---------------------------------------------------------------------------

def _build_pltt_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild PLTT (TTLP) section from parsed dict."""
    colours_rgb = parsed["colours_rgb"]
    bpp_flag = parsed["bpp_flag"]
    pad = int(parsed["padding"], 16) if isinstance(parsed["padding"], str) else parsed["padding"]
    colour_offset = parsed["colour_offset"]

    pal_data = bytearray(len(colours_rgb) * 2)
    for i, (r, g, b) in enumerate(colours_rgb):
        struct.pack_into("<H", pal_data, i * 2, _rgb_to_bgr555(r, g, b))

    data_size = len(pal_data)
    sub_header = bytearray(colour_offset)
    struct.pack_into("<I", sub_header, 0, bpp_flag)
    struct.pack_into("<I", sub_header, 4, pad)
    struct.pack_into("<I", sub_header, 8, data_size)
    struct.pack_into("<I", sub_header, 12, colour_offset)

    section_size = 8 + len(sub_header) + len(pal_data)
    header = bytearray(8)
    header[0:4] = b"TTLP"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + sub_header + pal_data)


def _build_pcmp_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild PCMP section."""
    num_pal = parsed.get("num_palettes", 0)
    pad = parsed.get("padding", 0)
    pal_idx = parsed.get("palette_index", 0)

    body = bytearray(8)
    struct.pack_into("<H", body, 0, num_pal)
    struct.pack_into("<H", body, 2, pad)
    struct.pack_into("<I", body, 4, pal_idx)

    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = b"PMCP"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + body)


def _build_cebk_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild CEBK (KBEC) section."""
    num_cells = parsed["num_cells"]
    cell_type = parsed["cell_type"]
    cell_data_offset = int(parsed["cell_data_offset"], 16) if isinstance(parsed["cell_data_offset"], str) else parsed["cell_data_offset"]
    mapping_mode = int(parsed["mapping_mode"], 16) if isinstance(parsed["mapping_mode"], str) else parsed["mapping_mode"]
    cell_data = base64.b64decode(parsed["cell_data_b64"])

    sub_header = bytearray(12)
    struct.pack_into("<H", sub_header, 0, num_cells)
    struct.pack_into("<H", sub_header, 2, cell_type)
    struct.pack_into("<I", sub_header, 4, cell_data_offset)
    struct.pack_into("<I", sub_header, 8, mapping_mode)

    section_size = 8 + len(sub_header) + len(cell_data)
    header = bytearray(8)
    header[0:4] = b"KBEC"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + sub_header + cell_data)


def _build_abnk_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild ABNK (KNBA) section."""
    num_anims = parsed["num_animations"]
    num_frames = parsed["num_frames"]
    unknown = parsed.get("unknown", 0)
    pad = parsed.get("padding", 0)
    anim_off = int(parsed["anim_data_offset"], 16) if isinstance(parsed["anim_data_offset"], str) else parsed["anim_data_offset"]
    frame_off = int(parsed["frame_data_offset"], 16) if isinstance(parsed["frame_data_offset"], str) else parsed["frame_data_offset"]
    frame_res = int(parsed["frame_result_offset"], 16) if isinstance(parsed["frame_result_offset"], str) else parsed["frame_result_offset"]
    anim_body = base64.b64decode(parsed["anim_data_b64"])

    sub_header = bytearray(20)
    struct.pack_into("<H", sub_header, 0, num_anims)
    struct.pack_into("<H", sub_header, 2, num_frames)
    struct.pack_into("<H", sub_header, 4, unknown)
    struct.pack_into("<H", sub_header, 6, pad)
    struct.pack_into("<I", sub_header, 8, anim_off)
    struct.pack_into("<I", sub_header, 12, frame_off)
    struct.pack_into("<I", sub_header, 16, frame_res)

    section_size = 8 + len(sub_header) + len(anim_body)
    header = bytearray(8)
    header[0:4] = b"KNBA"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + sub_header + anim_body)


def _build_scrn_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild SCRN (NRCS) section."""
    scr_w = parsed["screen_width"]
    scr_h = parsed["screen_height"]
    pad1 = parsed.get("padding1", 0)
    pad2 = parsed.get("padding2", 0)
    map_data = base64.b64decode(parsed["tilemap_data_b64"])

    sub_header = bytearray(12)
    struct.pack_into("<H", sub_header, 0, scr_w)
    struct.pack_into("<H", sub_header, 2, scr_h)
    struct.pack_into("<H", sub_header, 4, pad1)
    struct.pack_into("<H", sub_header, 6, pad2)
    struct.pack_into("<I", sub_header, 8, len(map_data))

    section_size = 8 + len(sub_header) + len(map_data)
    header = bytearray(8)
    header[0:4] = b"NRCS"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + sub_header + map_data)


def _build_mcbk_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild MCBK (KBCM) section."""
    body = base64.b64decode(parsed["data_b64"])
    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = b"KBCM"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + body)


def _build_labl_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild LABL section from labels list."""
    labels: list[str] = parsed.get("labels", [])
    if not labels:
        # Empty LABL
        section_size = 8
        header = bytearray(8)
        header[0:4] = b"LBAL"
        struct.pack_into("<I", header, 4, section_size)
        return bytes(header)

    # Build offset table + string data
    num_labels = len(labels)
    offset_table_size = num_labels * 4
    string_data = bytearray()
    offsets: list[int] = []
    for lbl in labels:
        offsets.append(offset_table_size + len(string_data))
        string_data.extend(lbl.encode("ascii", errors="replace"))
        string_data.append(0)  # null terminator

    body = bytearray(offset_table_size)
    for i, off in enumerate(offsets):
        struct.pack_into("<I", body, i * 4, off)
    body.extend(string_data)

    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = b"LBAL"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + body)


def _build_uext_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild UEXT (TXEU) section."""
    body = bytes.fromhex(parsed.get("data_hex", "00000000"))
    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = b"TXEU"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + body)


_SECTION_BUILDERS: dict[str, Any] = {
    "CHAR": _build_char_section,
    "PLTT": _build_pltt_section,
    "PCMP": _build_pcmp_section,
    "CEBK": _build_cebk_section,
    "ABNK": _build_abnk_section,
    "SCRN": _build_scrn_section,
    "MCBK": _build_mcbk_section,
    "LABL": _build_labl_section,
    "UEXT": _build_uext_section,
}


def encode_lznanr_from_json(json_str: str) -> bytes:
    """Encode a JSON string back into LZ-compressed NITRO binary.

    Parameters
    ----------
    json_str : str
        JSON text produced by ``decode_lznanr_to_json`` (possibly edited).

    Returns
    -------
    bytes
        LZ-compressed NITRO data ready to patch into a PAC archive.
    """
    obj = json.loads(json_str)
    magic_str: str = obj["magic"]
    bom = int(obj.get("bom", "0xFEFF"), 16)
    version = int(obj.get("version", "0x0100"), 16)
    header_size = obj.get("header_size", 16)
    comp_type = int(obj.get("compression_type", "0x11"), 16)

    # Rebuild sections
    section_bytes: list[bytes] = []
    for sec in obj["sections"]:
        tag_display = sec["tag_display"]
        parsed = sec["parsed"]
        builder = _SECTION_BUILDERS.get(tag_display)
        if builder:
            section_bytes.append(builder(parsed))
        else:
            section_bytes.append(_build_generic_section(sec["tag"], parsed))

    body = b"".join(section_bytes)
    total_size = header_size + len(body)

    # Build NITRO header
    hdr = bytearray(header_size)
    hdr[0:4] = magic_str.encode("ascii", errors="replace")[:4].ljust(4, b"\x00")
    struct.pack_into("<H", hdr, 4, bom)
    struct.pack_into("<H", hdr, 6, version)
    struct.pack_into("<I", hdr, 8, total_size)
    struct.pack_into("<H", hdr, 12, header_size)
    struct.pack_into("<H", hdr, 14, len(section_bytes))

    nitro_data = bytes(hdr) + body
    compressed = compress(nitro_data, comp_type)
    logger.info(
        "encode_lznanr: %s → %d bytes NITRO → %d bytes compressed (0x%02X)",
        magic_str, len(nitro_data), len(compressed), comp_type,
    )
    return compressed


# ---------------------------------------------------------------------------
# Image rendering – NCGR tile sheets
# ---------------------------------------------------------------------------

def _render_ncgr_tiles(
    data: bytes,
    char_section: dict[str, Any],
    palette: list[tuple[int, int, int]] | None = None,
) -> Image.Image:
    """Render NCGR tile data as a tile-sheet image.

    Parameters
    ----------
    data : bytes
        Decompressed NITRO file data.
    char_section : dict
        Parsed CHAR section from ``_parse_char_section``.
    palette : list of (R, G, B) or None
        Optional palette.  If *None*, a greyscale ramp is used.
    """
    tile_data = base64.b64decode(char_section["tile_data_b64"])
    bpp = char_section["bpp"]
    num_tiles = char_section["num_tiles"]
    width_tiles = char_section["width_tiles"]
    height_tiles = char_section["height_tiles"]

    if num_tiles == 0:
        raise ValueError("NCGR has no tile data")

    bytes_per_tile = 32 if bpp == 4 else 64
    decode_tile = _decode_tile_4bpp if bpp == 4 else _decode_tile_8bpp

    # Determine grid layout
    if width_tiles not in (0, 0xFFFF) and height_tiles not in (0, 0xFFFF):
        # Explicit dimensions
        cols = width_tiles
        rows = height_tiles
    else:
        # Linear tiles — arrange in a reasonable grid
        cols = min(num_tiles, 16)
        rows = math.ceil(num_tiles / cols)

    # Build palette
    max_idx = 16 if bpp == 4 else 256
    if palette is None:
        # Greyscale ramp
        pal = [(i * 255 // (max_idx - 1), i * 255 // (max_idx - 1), i * 255 // (max_idx - 1)) for i in range(max_idx)]
    else:
        pal = list(palette)
        while len(pal) < max_idx:
            pal.append((0, 0, 0))

    img = Image.new("RGBA", (cols * 8, rows * 8), (0, 0, 0, 0))
    px = img.load()

    for t in range(min(num_tiles, cols * rows)):
        t_off = t * bytes_per_tile
        if t_off + bytes_per_tile > len(tile_data):
            break
        tile = decode_tile(tile_data, t_off)
        tx = t % cols
        ty = t // cols

        for py_pos in range(8):
            for px_pos in range(8):
                ci = tile[py_pos][px_pos]
                if ci < len(pal):
                    r, g, b = pal[ci]
                    a = 0 if ci == 0 else 255
                    px[tx * 8 + px_pos, ty * 8 + py_pos] = (r, g, b, a)

    return img


def decode_lznanr_to_png(
    raw: bytes,
    palette_raw: bytes | None = None,
) -> bytes:
    """Render an lznanr NCGR/NCLR file as a PNG image.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lznanr data.
    palette_raw : bytes or None
        Optional compressed NCLR data to use as palette for NCGR rendering.

    Returns
    -------
    bytes
        PNG image data.
    """
    try:
        data = decompress(raw)
    except Exception as exc:
        raise ValueError(f"LZ decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)
    sections = _walk_sections(data, hdr["header_size"], hdr["num_sections"])

    fmt = hdr["format"]

    # --- NCGR: render tile sheet ---
    if fmt == "NCGR":
        char_sec = None
        for sec in sections:
            if sec["tag"] == b"RAHC":
                char_sec = _parse_char_section(data, sec["offset"], sec["size"])
                break
        if char_sec is None:
            raise ValueError("NCGR file has no CHAR section")

        palette = None
        if palette_raw is not None:
            palette = _extract_palette_from_nclr(palette_raw)

        img = _render_ncgr_tiles(data, char_sec, palette)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # --- NCLR: render palette swatch ---
    if fmt == "NCLR":
        pltt_sec = None
        for sec in sections:
            if sec["tag"] == b"TTLP":
                pltt_sec = _parse_pltt_section(data, sec["offset"], sec["size"])
                break
        if pltt_sec is None:
            raise ValueError("NCLR file has no PLTT section")

        img = _render_nclr_palette(pltt_sec["colours_rgb"], pltt_sec["bpp"])
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # --- NTBG: delegate to lz5bg_codec ---
    if fmt == "NTBG":
        from otn_enhanced.rom.lz5bg_codec import decode_lz5bg_to_png
        return decode_lz5bg_to_png(raw)

    raise ValueError(f"Cannot render {fmt} as image (only NCGR, NCLR, NTBG supported)")


def _extract_palette_from_nclr(palette_raw: bytes) -> list[tuple[int, int, int]]:
    """Extract (R,G,B) palette list from compressed NCLR data."""
    try:
        data = decompress(palette_raw)
    except Exception as exc:
        raise ValueError(f"NCLR decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)
    sections = _walk_sections(data, hdr["header_size"], hdr["num_sections"])

    for sec in sections:
        if sec["tag"] == b"TTLP":
            parsed = _parse_pltt_section(data, sec["offset"], sec["size"])
            return [tuple(c) for c in parsed["colours_rgb"]]

    raise ValueError("NCLR has no PLTT section")


def decode_lznanr_to_base64(
    raw: bytes,
    palette_raw: bytes | None = None,
) -> str:
    """Return a ``data:image/png;base64,…`` URI for NCGR/NCLR rendering."""
    png_bytes = decode_lznanr_to_png(raw, palette_raw=palette_raw)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# Image encode – NCGR from PNG
# ---------------------------------------------------------------------------

def encode_lznanr(png_data: bytes, original_raw: bytes) -> bytes:
    """Encode a PNG image back into an NCGR lznanr file.

    Uses the original compressed data as a structural template.

    Parameters
    ----------
    png_data : bytes
        PNG image data (the replacement image).
    original_raw : bytes
        The original compressed lznanr NCGR data from the PAC archive.

    Returns
    -------
    bytes
        LZ-compressed NCGR data.

    Raises
    ------
    ValueError
        If the original is not NCGR or dimensions don't match.
    """
    comp_type = _detect_compression_type(original_raw)

    try:
        orig_data = decompress(original_raw)
    except Exception as exc:
        raise ValueError(f"Cannot decompress original: {exc}") from exc

    orig_hdr = _parse_nitro_header(orig_data)
    if orig_hdr["format"] != "NCGR":
        raise ValueError(f"encode_lznanr only supports NCGR, got {orig_hdr['format']}")

    orig_sections = _walk_sections(orig_data, orig_hdr["header_size"], orig_hdr["num_sections"])

    # Find CHAR section
    char_parsed = None
    char_sec_idx = None
    for i, sec in enumerate(orig_sections):
        if sec["tag"] == b"RAHC":
            char_parsed = _parse_char_section(orig_data, sec["offset"], sec["size"])
            char_sec_idx = i
            break

    if char_parsed is None:
        raise ValueError("Original NCGR has no CHAR section")

    bpp = char_parsed["bpp"]
    num_tiles = char_parsed["num_tiles"]
    width_tiles = char_parsed["width_tiles"]
    height_tiles = char_parsed["height_tiles"]

    # Determine expected image dimensions
    if width_tiles not in (0, 0xFFFF) and height_tiles not in (0, 0xFFFF):
        cols = width_tiles
        rows = height_tiles
    else:
        cols = min(num_tiles, 16)
        rows = math.ceil(num_tiles / cols)

    expected_w = cols * 8
    expected_h = rows * 8

    # Open replacement image
    img = Image.open(io.BytesIO(png_data)).convert("RGBA")
    if img.size != (expected_w, expected_h):
        raise ValueError(
            f"Image dimensions {img.size[0]}×{img.size[1]} don't match "
            f"expected {expected_w}×{expected_h}"
        )

    max_colours = 16 if bpp == 4 else 256
    encode_tile = _encode_tile_4bpp if bpp == 4 else _encode_tile_8bpp
    bytes_per_tile = 32 if bpp == 4 else 64

    # Try to get original palette from image (greyscale ramp)
    # For lossless round-trips, map back using the greyscale ramp
    pal = [(i * 255 // (max_colours - 1), i * 255 // (max_colours - 1), i * 255 // (max_colours - 1)) for i in range(max_colours)]
    _, pixel_indices = _quantize_image(img, max_colours, original_palette=pal)

    # Re-encode tiles
    new_tile_data = bytearray()
    for t in range(num_tiles):
        tx = t % cols
        ty = t // cols
        block: list[list[int]] = []
        for py_pos in range(8):
            row: list[int] = []
            for px_pos in range(8):
                iy = ty * 8 + py_pos
                ix = tx * 8 + px_pos
                if iy < len(pixel_indices) and ix < len(pixel_indices[iy]):
                    row.append(pixel_indices[iy][ix])
                else:
                    row.append(0)
            block.append(row)
        new_tile_data.extend(encode_tile(block))

    # Rebuild the NCGR with new tile data — update CHAR section
    result = decode_lznanr(original_raw)
    for sec in result["sections"]:
        if sec["tag_display"] == "CHAR":
            sec["parsed"]["tile_data_b64"] = base64.b64encode(bytes(new_tile_data)).decode("ascii")
            sec["parsed"]["data_size"] = len(new_tile_data)
            break

    return encode_lznanr_from_json(json.dumps(result))


def encode_lznanr_ncgr_with_palette(
    png_data: bytes,
    original_raw: bytes,
    palette_raw: bytes,
) -> bytes:
    """Encode a PNG into NCGR using an external NCLR palette for colour mapping.

    Parameters
    ----------
    png_data : bytes
        PNG image data.
    original_raw : bytes
        Original compressed NCGR data (template).
    palette_raw : bytes
        Compressed NCLR data to use for palette mapping.

    Returns
    -------
    bytes
        LZ-compressed NCGR data.
    """
    comp_type = _detect_compression_type(original_raw)

    try:
        orig_data = decompress(original_raw)
    except Exception as exc:
        raise ValueError(f"Cannot decompress original: {exc}") from exc

    orig_hdr = _parse_nitro_header(orig_data)
    if orig_hdr["format"] != "NCGR":
        raise ValueError(f"Expected NCGR, got {orig_hdr['format']}")

    orig_sections = _walk_sections(orig_data, orig_hdr["header_size"], orig_hdr["num_sections"])

    char_parsed = None
    for sec in orig_sections:
        if sec["tag"] == b"RAHC":
            char_parsed = _parse_char_section(orig_data, sec["offset"], sec["size"])
            break
    if char_parsed is None:
        raise ValueError("Original NCGR has no CHAR section")

    bpp = char_parsed["bpp"]
    num_tiles = char_parsed["num_tiles"]
    width_tiles = char_parsed["width_tiles"]
    height_tiles = char_parsed["height_tiles"]

    if width_tiles not in (0, 0xFFFF) and height_tiles not in (0, 0xFFFF):
        cols = width_tiles
        rows = height_tiles
    else:
        cols = min(num_tiles, 16)
        rows = math.ceil(num_tiles / cols)

    expected_w = cols * 8
    expected_h = rows * 8

    img = Image.open(io.BytesIO(png_data)).convert("RGBA")
    if img.size != (expected_w, expected_h):
        raise ValueError(
            f"Image dimensions {img.size[0]}×{img.size[1]} don't match "
            f"expected {expected_w}×{expected_h}"
        )

    max_colours = 16 if bpp == 4 else 256
    encode_tile = _encode_tile_4bpp if bpp == 4 else _encode_tile_8bpp

    # Use the NCLR palette for colour mapping
    nclr_palette = _extract_palette_from_nclr(palette_raw)
    _, pixel_indices = _quantize_image(img, max_colours, original_palette=nclr_palette)

    new_tile_data = bytearray()
    for t in range(num_tiles):
        tx = t % cols
        ty = t // cols
        block: list[list[int]] = []
        for py_pos in range(8):
            row: list[int] = []
            for px_pos in range(8):
                iy = ty * 8 + py_pos
                ix = tx * 8 + px_pos
                if iy < len(pixel_indices) and ix < len(pixel_indices[iy]):
                    row.append(pixel_indices[iy][ix])
                else:
                    row.append(0)
            block.append(row)
        new_tile_data.extend(encode_tile(block))

    result = decode_lznanr(original_raw)
    for sec in result["sections"]:
        if sec["tag_display"] == "CHAR":
            sec["parsed"]["tile_data_b64"] = base64.b64encode(bytes(new_tile_data)).decode("ascii")
            sec["parsed"]["data_size"] = len(new_tile_data)
            break

    return encode_lznanr_from_json(json.dumps(result))

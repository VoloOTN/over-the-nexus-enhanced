"""Decoder / encoder for lzncer (NCER) compressed NDS cell resources.

Binary layout
=============
lzncer files are LZ-compressed (typically LZ11) NDS **NCER** (NITRO Cell
Resource) containers.  After decompression the payload is a standard NITRO
generic header followed by a **KBEC** (CEBK) section and optionally
**LBAL** (LABL) and **TXEU** (UEXT) sections.

NCER files define *cells* (sprites) that reference tiles stored in a
companion NCGR and are coloured using a companion NCLR palette.

NITRO Generic Header (16 bytes)
-------------------------------
Offset  Size  Description
------  ----  -----------
0       4     Magic ``RECN``  (LE for NCER)
4       2     BOM  ``0xFEFF`` (little-endian)
6       2     Version (typically ``0x0100`` or ``0x0101``)
8       4     Total file size
12      2     Header size (16)
14      2     Number of sections

NCER – ``KBEC`` (CEBK) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u16  num_cells
+2   u16  cell_type       (0 = OAM-style, 1 = extended)
+4   u32  cell_data_offset
+8   u32  mapping_mode
+12  …    cell definition data

Each cell definition (OAM-style, cell_type=0) at offset
``cell_data_offset + cell_index * 8``:
  +0  u32  OAM offset  (byte offset into OAM data block)
  +4  u16  num_OAMs
  +6  u16  attributes

OAM entries are 6 bytes each:
  +0  u16  OBJ Attribute 0  (Y, shape, mode flags)
  +2  u16  OBJ Attribute 1  (X, size, flip flags)
  +4  u16  OBJ Attribute 2  (tile index, priority, palette)

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
import struct
from typing import Any

from otn_enhanced.rom.lz_compression import compress, decompress
from otn_enhanced.rom.nitro_common import _detect_compression_type, _parse_nitro_header, _parse_uext_section, _parse_generic_section, _build_uext_section, _build_generic_section  # noqa: F401

logger = logging.getLogger(__name__)


def _walk_sections(
    data: bytes, header_size: int, num_sections: int,
) -> list[dict[str, Any]]:
    """Walk sections and return a list of ``{tag, offset, size}`` dicts."""
    sections: list[dict[str, Any]] = []
    offset = header_size
    for _ in range(num_sections):
        if offset + 8 > len(data):
            break
        tag = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        sections.append({"tag": tag, "offset": offset, "size": size})
        offset += size
    return sections


# ---------------------------------------------------------------------------
# CEBK (KBEC) section parser — detailed cell/OAM parsing
# ---------------------------------------------------------------------------

# NDS OAM shape/size → (width, height) in pixels
_OAM_SIZES: dict[tuple[int, int], tuple[int, int]] = {
    # (shape, size) → (w, h)
    (0, 0): (8, 8),
    (0, 1): (16, 16),
    (0, 2): (32, 32),
    (0, 3): (64, 64),
    (1, 0): (16, 8),
    (1, 1): (32, 8),
    (1, 2): (32, 16),
    (1, 3): (64, 32),
    (2, 0): (8, 16),
    (2, 1): (8, 32),
    (2, 2): (16, 32),
    (2, 3): (32, 64),
}


def _parse_oam_entry(attr0: int, attr1: int, attr2: int) -> dict[str, Any]:
    """Parse a single 6-byte OAM entry into a structured dict."""
    # Attribute 0
    y = attr0 & 0xFF
    if y >= 128:
        y -= 256  # signed
    rotation_scaling = bool(attr0 & 0x0100)
    obj_disable = bool(attr0 & 0x0200) if not rotation_scaling else False
    double_size = bool(attr0 & 0x0200) if rotation_scaling else False
    obj_mode = (attr0 >> 10) & 0x3
    mosaic = bool(attr0 & 0x1000)
    bpp8 = bool(attr0 & 0x2000)  # 0 = 4bpp, 1 = 8bpp
    shape = (attr0 >> 14) & 0x3

    # Attribute 1
    x = attr1 & 0x1FF
    if x >= 256:
        x -= 512  # signed 9-bit
    if rotation_scaling:
        rs_param = (attr1 >> 9) & 0x1F
        h_flip = False
        v_flip = False
    else:
        rs_param = None
        h_flip = bool(attr1 & 0x1000)
        v_flip = bool(attr1 & 0x2000)
    size = (attr1 >> 14) & 0x3

    # Attribute 2
    tile_index = attr2 & 0x3FF
    priority = (attr2 >> 10) & 0x3
    palette_num = (attr2 >> 12) & 0xF

    # Derive pixel dimensions
    w, h = _OAM_SIZES.get((shape, size), (8, 8))

    result: dict[str, Any] = {
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "shape": shape,
        "size": size,
        "tile_index": tile_index,
        "priority": priority,
        "palette_num": palette_num,
        "h_flip": h_flip,
        "v_flip": v_flip,
        "bpp8": bpp8,
        "obj_mode": obj_mode,
        "mosaic": mosaic,
        "rotation_scaling": rotation_scaling,
        "attr0": f"0x{attr0:04X}",
        "attr1": f"0x{attr1:04X}",
        "attr2": f"0x{attr2:04X}",
    }
    if rotation_scaling:
        result["double_size"] = double_size
        result["rs_param"] = rs_param
    else:
        result["obj_disable"] = obj_disable
    return result


def _build_oam_attrs(oam: dict[str, Any]) -> tuple[int, int, int]:
    """Rebuild the three u16 OAM attributes from a parsed OAM dict.

    If the raw ``attr0``/``attr1``/``attr2`` hex values are present they are
    used directly for lossless round-trips.  Otherwise the fields are packed.
    """
    # Prefer raw attrs for lossless round-trip
    if "attr0" in oam and "attr1" in oam and "attr2" in oam:
        a0 = int(oam["attr0"], 16) if isinstance(oam["attr0"], str) else oam["attr0"]
        a1 = int(oam["attr1"], 16) if isinstance(oam["attr1"], str) else oam["attr1"]
        a2 = int(oam["attr2"], 16) if isinstance(oam["attr2"], str) else oam["attr2"]
        return a0, a1, a2

    # Reconstruct from decoded fields
    y = oam["y"] & 0xFF
    rotation_scaling = oam.get("rotation_scaling", False)
    obj_mode = oam.get("obj_mode", 0) & 0x3
    mosaic = oam.get("mosaic", False)
    bpp8 = oam.get("bpp8", False)
    shape = oam.get("shape", 0) & 0x3

    a0 = y
    if rotation_scaling:
        a0 |= 0x0100
        if oam.get("double_size", False):
            a0 |= 0x0200
    else:
        if oam.get("obj_disable", False):
            a0 |= 0x0200
    a0 |= (obj_mode << 10)
    if mosaic:
        a0 |= 0x1000
    if bpp8:
        a0 |= 0x2000
    a0 |= (shape << 14)

    x = oam["x"] & 0x1FF
    size_val = oam.get("size", 0) & 0x3
    a1 = x
    if rotation_scaling:
        rs_param = oam.get("rs_param", 0) & 0x1F
        a1 |= (rs_param << 9)
    else:
        if oam.get("h_flip", False):
            a1 |= 0x1000
        if oam.get("v_flip", False):
            a1 |= 0x2000
    a1 |= (size_val << 14)

    tile_index = oam.get("tile_index", 0) & 0x3FF
    priority = oam.get("priority", 0) & 0x3
    palette_num = oam.get("palette_num", 0) & 0xF
    a2 = tile_index | (priority << 10) | (palette_num << 12)

    return a0, a1, a2


def _parse_cebk_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NCER CEBK (KBEC) section with detailed cell/OAM breakdown."""
    body_off = offset + 8
    if body_off + 12 > len(data):
        return {"error": "CEBK section truncated"}

    num_cells = struct.unpack_from("<H", data, body_off)[0]
    cell_type = struct.unpack_from("<H", data, body_off + 2)[0]
    cell_data_offset = struct.unpack_from("<I", data, body_off + 4)[0]
    mapping_mode = struct.unpack_from("<I", data, body_off + 8)[0]

    # The cell data area starts at body_off + 12 + cell_data_offset
    # But typically cell_data_offset is 0 and cell table is immediately after
    cell_table_start = body_off + 12 + cell_data_offset

    # Each cell entry is 8 bytes: [u32 oam_offset, u16 num_oams, u16 attrs]
    cells: list[dict[str, Any]] = []
    # OAM data starts after the cell table
    oam_block_start = cell_table_start + num_cells * 8

    for ci in range(num_cells):
        entry_off = cell_table_start + ci * 8
        if entry_off + 8 > len(data):
            break
        oam_byte_offset = struct.unpack_from("<I", data, entry_off)[0]
        num_oams = struct.unpack_from("<H", data, entry_off + 4)[0]
        cell_attrs = struct.unpack_from("<H", data, entry_off + 6)[0]

        oams: list[dict[str, Any]] = []
        for oi in range(num_oams):
            oam_off = oam_block_start + oam_byte_offset + oi * 6
            if oam_off + 6 > len(data):
                break
            attr0 = struct.unpack_from("<H", data, oam_off)[0]
            attr1 = struct.unpack_from("<H", data, oam_off + 2)[0]
            attr2 = struct.unpack_from("<H", data, oam_off + 4)[0]
            oams.append(_parse_oam_entry(attr0, attr1, attr2))

        cells.append({
            "index": ci,
            "oam_byte_offset": f"0x{oam_byte_offset:08X}",
            "num_oams": num_oams,
            "cell_attrs": f"0x{cell_attrs:04X}",
            "oams": oams,
        })

    # Preserve any trailing data after parsed cells+OAMs for lossless round-trip
    # Calculate the end of the OAM block
    max_oam_end = oam_block_start
    for cell in cells:
        oam_off_val = int(cell["oam_byte_offset"], 16)
        cell_oam_end = oam_block_start + oam_off_val + cell["num_oams"] * 6
        if cell_oam_end > max_oam_end:
            max_oam_end = cell_oam_end

    section_end = offset + size
    trailing = data[max_oam_end:section_end]
    trailing_b64 = base64.b64encode(trailing).decode("ascii") if trailing else ""

    return {
        "num_cells": num_cells,
        "cell_type": cell_type,
        "cell_data_offset": f"0x{cell_data_offset:08X}",
        "mapping_mode": f"0x{mapping_mode:08X}",
        "cells": cells,
        "trailing_data_b64": trailing_b64,
    }


def _parse_labl_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse LABL section – label name table."""
    body_off = offset + 8
    body_size = size - 8
    if body_size <= 0:
        return {"labels": []}
    body = data[body_off : body_off + body_size]

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


_SECTION_PARSERS: dict[bytes, Any] = {
    b"KBEC": _parse_cebk_section,
    b"LBAL": _parse_labl_section,
    b"TXEU": _parse_uext_section,
}

# Tag display names (LE tag → human name)
TAG_DISPLAY: dict[bytes, str] = {
    b"KBEC": "CEBK",
    b"LBAL": "LABL",
    b"TXEU": "UEXT",
}


# ---------------------------------------------------------------------------
# JSON decode – public API
# ---------------------------------------------------------------------------

def decode_lzncer(raw: bytes) -> dict[str, Any]:
    """Decompress and parse an lzncer file into a structured dict.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lzncer data from a PAC archive.

    Returns
    -------
    dict
        Structured representation of the NCER container with cell/OAM data.

    Raises
    ------
    ValueError
        If the data cannot be decompressed or is not an NCER file.
    """
    try:
        data = decompress(raw)
    except Exception as exc:
        raise ValueError(f"LZ decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)

    if hdr["magic"] != b"RECN":
        raise ValueError(
            f"Not an NCER file (magic={hdr['magic']!r}, "
            f"expected b'RECN')"
        )

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
        "format": "NCER",
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


def decode_lzncer_to_json(raw: bytes) -> str:
    """Decompress, parse, and return a JSON string for an lzncer file."""
    result = decode_lzncer(raw)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Section builders (encode)
# ---------------------------------------------------------------------------

def _build_cebk_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild CEBK (KBEC) section from parsed dict with cell/OAM data."""
    num_cells = parsed["num_cells"]
    cell_type = parsed["cell_type"]
    cell_data_offset = (
        int(parsed["cell_data_offset"], 16)
        if isinstance(parsed["cell_data_offset"], str)
        else parsed["cell_data_offset"]
    )
    mapping_mode = (
        int(parsed["mapping_mode"], 16)
        if isinstance(parsed["mapping_mode"], str)
        else parsed["mapping_mode"]
    )
    cells = parsed.get("cells", [])

    # Build the OAM data block and cell table simultaneously
    cell_table = bytearray(num_cells * 8)
    oam_block = bytearray()

    for ci, cell in enumerate(cells):
        oam_byte_offset = len(oam_block)
        oams = cell.get("oams", [])
        num_oams = len(oams)
        cell_attrs = (
            int(cell["cell_attrs"], 16)
            if isinstance(cell.get("cell_attrs", 0), str)
            else cell.get("cell_attrs", 0)
        )

        # Pack cell table entry
        entry_off = ci * 8
        struct.pack_into("<I", cell_table, entry_off, oam_byte_offset)
        struct.pack_into("<H", cell_table, entry_off + 4, num_oams)
        struct.pack_into("<H", cell_table, entry_off + 6, cell_attrs)

        # Pack OAM entries
        for oam in oams:
            a0, a1, a2 = _build_oam_attrs(oam)
            oam_entry = bytearray(6)
            struct.pack_into("<H", oam_entry, 0, a0)
            struct.pack_into("<H", oam_entry, 2, a1)
            struct.pack_into("<H", oam_entry, 4, a2)
            oam_block.extend(oam_entry)

    # Trailing data (for lossless round-trip)
    trailing = base64.b64decode(parsed.get("trailing_data_b64", ""))

    # Sub-header: 12 bytes
    sub_header = bytearray(12)
    struct.pack_into("<H", sub_header, 0, num_cells)
    struct.pack_into("<H", sub_header, 2, cell_type)
    struct.pack_into("<I", sub_header, 4, cell_data_offset)
    struct.pack_into("<I", sub_header, 8, mapping_mode)

    body = bytes(sub_header) + bytes(cell_table) + bytes(oam_block) + trailing

    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = b"KBEC"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header) + body


def _build_labl_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild LABL section from labels list."""
    labels: list[str] = parsed.get("labels", [])
    if not labels:
        section_size = 8
        header = bytearray(8)
        header[0:4] = b"LBAL"
        struct.pack_into("<I", header, 4, section_size)
        return bytes(header)

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
    return bytes(header) + bytes(body)


_SECTION_BUILDERS: dict[str, Any] = {
    "CEBK": _build_cebk_section,
    "LABL": _build_labl_section,
    "UEXT": _build_uext_section,
}


# ---------------------------------------------------------------------------
# JSON encode – public API
# ---------------------------------------------------------------------------

def encode_lzncer_from_json(json_str: str) -> bytes:
    """Encode a JSON string back into LZ-compressed NCER binary.

    Parameters
    ----------
    json_str : str
        JSON text produced by ``decode_lzncer_to_json`` (possibly edited).

    Returns
    -------
    bytes
        LZ-compressed NCER data ready to patch into a PAC archive.
    """
    obj = json.loads(json_str)
    magic_str: str = obj.get("magic", "RECN")
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
        "encode_lzncer: NCER → %d bytes decompressed → %d bytes compressed (0x%02X)",
        len(nitro_data), len(compressed), comp_type,
    )
    return compressed

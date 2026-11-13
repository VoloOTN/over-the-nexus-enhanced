"""Decoder / encoder for lzncgr (NCGR) compressed NDS character graphic resources.

Binary layout
=============
lzncgr files are LZ-compressed (typically LZ11) NDS **NCGR** (NITRO Character
Graphic Resource) containers.  After decompression the payload is a standard
NITRO generic header followed by a **RAHC** (CHAR) section and optionally
**LBAL** (LABL) and **TXEU** (UEXT) sections.

NCGR files store tiled pixel data (8×8 tiles) used for sprite and background
graphics.  They are typically paired with an NCLR palette file for colouring.

NITRO Generic Header (16 bytes)
-------------------------------
Offset  Size  Description
------  ----  -----------
0       4     Magic ``RGCN``  (LE for NCGR)
4       2     BOM  ``0xFEFF`` (little-endian)
6       2     Version (typically ``0x0100`` or ``0x0101``)
8       4     Total file size
12      2     Header size (16)
14      2     Number of sections

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
from otn_enhanced.rom.nitro_common import _bgr555_to_rgb, _rgb_to_bgr555, _decode_tile_4bpp, _decode_tile_8bpp, _encode_tile_4bpp, _encode_tile_8bpp, _build_char_section, _colour_distance_sq, _map_to_palette, _quantize_image, _detect_compression_type, _parse_nitro_header, _parse_uext_section, _parse_generic_section, _build_uext_section, _build_generic_section  # noqa: F401

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level NDS helpers
# ---------------------------------------------------------------------------

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
# Section parsers
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
    tile_data = data[tile_data_start : tile_data_start + data_size]

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


def _parse_labl_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse LABL section – label name table."""
    body_off = offset + 8
    body_size = size - 8
    if body_size <= 0:
        return {"labels": []}
    body = data[body_off : body_off + body_size]

    offsets: list[int] = []
    pos = 0
    while pos + 4 <= len(body):
        str_off = struct.unpack_from("<I", body, pos)[0]
        if str_off >= len(body):
            break
        offsets.append(str_off)
        pos += 4
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
    b"RAHC": _parse_char_section,
    b"LBAL": _parse_labl_section,
    b"TXEU": _parse_uext_section,
}

# Tag display names (LE tag → human name)
TAG_DISPLAY: dict[bytes, str] = {
    b"RAHC": "CHAR",
    b"LBAL": "LABL",
    b"TXEU": "UEXT",
}


# ---------------------------------------------------------------------------
# JSON decode – public API
# ---------------------------------------------------------------------------

def decode_lzncgr(raw: bytes) -> dict[str, Any]:
    """Decompress and parse an lzncgr file into a structured dict.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lzncgr data from a PAC archive.

    Returns
    -------
    dict
        Structured representation of the NCGR container with tile data.

    Raises
    ------
    ValueError
        If the data cannot be decompressed or is not an NCGR file.
    """
    try:
        data = decompress(raw)
    except Exception as exc:
        raise ValueError(f"LZ decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)

    if hdr["magic"] != b"RGCN":
        raise ValueError(
            f"Not an NCGR file (magic={hdr['magic']!r}, "
            f"expected b'RGCN')"
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
        "format": "NCGR",
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


def decode_lzncgr_to_json(raw: bytes) -> str:
    """Decompress, parse, and return a JSON string for an lzncgr file."""
    result = decode_lzncgr(raw)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Section builders (encode)
# ---------------------------------------------------------------------------

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
        string_data.append(0)

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
    "CHAR": _build_char_section,
    "LABL": _build_labl_section,
    "UEXT": _build_uext_section,
}


# ---------------------------------------------------------------------------
# JSON encode – public API
# ---------------------------------------------------------------------------

def encode_lzncgr_from_json(json_str: str) -> bytes:
    """Encode a JSON string back into LZ-compressed NCGR binary.

    Parameters
    ----------
    json_str : str
        JSON text produced by ``decode_lzncgr_to_json`` (possibly edited).

    Returns
    -------
    bytes
        LZ-compressed NCGR data ready to patch into a PAC archive.
    """
    obj = json.loads(json_str)
    magic_str: str = obj.get("magic", "RGCN")
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
        "encode_lzncgr: NCGR → %d bytes decompressed → %d bytes compressed (0x%02X)",
        len(nitro_data), len(compressed), comp_type,
    )
    return compressed


# ---------------------------------------------------------------------------
# Image rendering – NCGR tile sheets
# ---------------------------------------------------------------------------

def _render_ncgr_tiles(
    char_section: dict[str, Any],
    palette: list[tuple[int, int, int]] | None = None,
) -> Image.Image:
    """Render NCGR tile data as a tile-sheet image.

    Parameters
    ----------
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
        cols = width_tiles
        rows = height_tiles
    else:
        cols = min(num_tiles, 16)
        rows = math.ceil(num_tiles / cols)

    # Build palette
    max_idx = 16 if bpp == 4 else 256
    if palette is None:
        pal = [
            (i * 255 // (max_idx - 1), i * 255 // (max_idx - 1), i * 255 // (max_idx - 1))
            for i in range(max_idx)
        ]
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


# ---------------------------------------------------------------------------
# Image decode – public API
# ---------------------------------------------------------------------------

def decode_lzncgr_to_png(
    raw: bytes,
    palette_raw: bytes | None = None,
) -> bytes:
    """Render an lzncgr NCGR file as a PNG tile-sheet image.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lzncgr data.
    palette_raw : bytes or None
        Optional compressed NCLR data to use as palette.  If *None* a
        greyscale ramp is used.

    Returns
    -------
    bytes
        PNG image data.
    """
    parsed = decode_lzncgr(raw)

    char_parsed = None
    for sec in parsed["sections"]:
        if sec["tag_display"] == "CHAR":
            char_parsed = sec["parsed"]
            break
    if char_parsed is None:
        raise ValueError("NCGR file has no CHAR section")

    palette = None
    if palette_raw is not None:
        palette = _extract_palette_from_nclr(palette_raw)

    img = _render_ncgr_tiles(char_parsed, palette)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def decode_lzncgr_to_base64(
    raw: bytes,
    palette_raw: bytes | None = None,
) -> str:
    """Return a ``data:image/png;base64,…`` URI for the NCGR tile sheet."""
    png_bytes = decode_lzncgr_to_png(raw, palette_raw=palette_raw)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _extract_palette_from_nclr(palette_raw: bytes) -> list[tuple[int, int, int]]:
    """Extract (R, G, B) palette list from compressed NCLR data.

    Tries the dedicated lznclr codec first, then falls back to raw parsing.
    """
    try:
        from otn_enhanced.rom.lznclr_codec import extract_palette
        return extract_palette(palette_raw)
    except Exception:
        pass

    # Fallback: decompress and parse inline
    try:
        data = decompress(palette_raw)
    except Exception as exc:
        raise ValueError(f"NCLR decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)
    sections = _walk_sections(data, hdr["header_size"], hdr["num_sections"])

    for sec in sections:
        if sec["tag"] == b"TTLP":
            body_off = sec["offset"] + 8
            if body_off + 16 > len(data):
                raise ValueError("PLTT section truncated")
            bpp_flag = struct.unpack_from("<I", data, body_off)[0]
            data_size = struct.unpack_from("<I", data, body_off + 8)[0]
            colour_offset = struct.unpack_from("<I", data, body_off + 12)[0]

            num_colours = data_size // 2
            pal_start = body_off + colour_offset
            colours: list[tuple[int, int, int]] = []
            for i in range(num_colours):
                pos = pal_start + i * 2
                if pos + 2 > len(data):
                    break
                val = struct.unpack_from("<H", data, pos)[0]
                colours.append(_bgr555_to_rgb(val))
            return colours

    raise ValueError("NCLR has no PLTT section")


# ---------------------------------------------------------------------------
# Image encode – NCGR from PNG
# ---------------------------------------------------------------------------

def encode_lzncgr(png_data: bytes, original_raw: bytes) -> bytes:
    """Encode a PNG image back into an NCGR lzncgr file.

    Uses the original compressed data as a structural template.

    Parameters
    ----------
    png_data : bytes
        PNG image data (the replacement image).
    original_raw : bytes
        The original compressed lzncgr NCGR data from the PAC archive.

    Returns
    -------
    bytes
        LZ-compressed NCGR data.

    Raises
    ------
    ValueError
        If the original is not NCGR or dimensions don't match.
    """
    result = decode_lzncgr(original_raw)

    char_parsed = None
    for sec in result["sections"]:
        if sec["tag_display"] == "CHAR":
            char_parsed = sec["parsed"]
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

    # Default greyscale ramp for lossless round-trips
    pal = [
        (i * 255 // (max_colours - 1), i * 255 // (max_colours - 1), i * 255 // (max_colours - 1))
        for i in range(max_colours)
    ]
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

    # Update CHAR section in the parsed result
    for sec in result["sections"]:
        if sec["tag_display"] == "CHAR":
            sec["parsed"]["tile_data_b64"] = base64.b64encode(bytes(new_tile_data)).decode("ascii")
            sec["parsed"]["data_size"] = len(new_tile_data)
            break

    return encode_lzncgr_from_json(json.dumps(result))


def encode_lzncgr_with_palette(
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
    result = decode_lzncgr(original_raw)

    char_parsed = None
    for sec in result["sections"]:
        if sec["tag_display"] == "CHAR":
            char_parsed = sec["parsed"]
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

    for sec in result["sections"]:
        if sec["tag_display"] == "CHAR":
            sec["parsed"]["tile_data_b64"] = base64.b64encode(bytes(new_tile_data)).decode("ascii")
            sec["parsed"]["data_size"] = len(new_tile_data)
            break

    return encode_lzncgr_from_json(json.dumps(result))

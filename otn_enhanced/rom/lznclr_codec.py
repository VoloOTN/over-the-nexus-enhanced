"""Decoder / encoder for lznclr (NCLR) compressed NDS palette resources.

Binary layout
=============
lznclr files are LZ-compressed (typically LZ11) NDS **NCLR** (NITRO Colour
Resource) containers.  After decompression the payload is a standard NITRO
generic header followed by a **TTLP** (PLTT) section and optionally a
**PMCP** (PCMP) section.

NITRO Generic Header (16 bytes)
-------------------------------
Offset  Size  Description
------  ----  -----------
0       4     Magic ``RLCN``  (LE for NCLR)
4       2     BOM  ``0xFEFF`` (little-endian)
6       2     Version (typically ``0x0100`` or ``0x0101``)
8       4     Total file size
12      2     Header size (16)
14      2     Number of sections

NCLR – ``TTLP`` (PLTT) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u32  bpp_flag      (3 = 4 bpp, 4 = 8 bpp)
+4   u32  padding
+8   u32  data_size     (byte count of palette data)
+12  u32  colour_offset (offset from section body start to first colour)
+16  …    BGR555 palette entries (2 bytes each)

NCLR – ``PMCP`` (PCMP) section layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+0   u16  num_palettes
+2   u16  padding
+4   u32  palette_index
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
from otn_enhanced.rom.nitro_common import _bgr555_to_rgb, _rgb_to_bgr555, _build_generic_section, _render_nclr_palette, _detect_compression_type, _parse_nitro_header, _parse_generic_section  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NDS colour helpers
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
# PLTT (TTLP) section parser
# ---------------------------------------------------------------------------

def _parse_pltt_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse NCLR PLTT (TTLP) section."""
    body_off = offset + 8  # skip tag + size
    if body_off + 16 > len(data):
        return {"error": "PLTT section truncated"}

    bpp_flag = struct.unpack_from("<I", data, body_off)[0]
    pad = struct.unpack_from("<I", data, body_off + 4)[0]
    data_size = struct.unpack_from("<I", data, body_off + 8)[0]
    colour_offset = struct.unpack_from("<I", data, body_off + 12)[0]

    bpp = 4 if bpp_flag == 3 else (8 if bpp_flag == 4 else bpp_flag)
    num_colours = data_size // 2

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
    """Parse NCLR PCMP (PMCP) section."""
    body_off = offset + 8
    result: dict[str, Any] = {}
    if body_off + 4 <= len(data):
        result["num_palettes"] = struct.unpack_from("<H", data, body_off)[0]
        result["padding"] = struct.unpack_from("<H", data, body_off + 2)[0]
    if body_off + 8 <= len(data):
        result["palette_index"] = struct.unpack_from("<I", data, body_off + 4)[0]
    return result


_SECTION_PARSERS: dict[bytes, Any] = {
    b"TTLP": _parse_pltt_section,
    b"PMCP": _parse_pcmp_section,
}

# Tag display names (LE tag → human name)
TAG_DISPLAY: dict[bytes, str] = {
    b"TTLP": "PLTT",
    b"PMCP": "PCMP",
}


# ---------------------------------------------------------------------------
# JSON decode – public API
# ---------------------------------------------------------------------------

def decode_lznclr(raw: bytes) -> dict[str, Any]:
    """Decompress and parse an lznclr file into a structured dict.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lznclr data from a PAC archive.

    Returns
    -------
    dict
        Structured representation of the NCLR container with palette data.

    Raises
    ------
    ValueError
        If the data cannot be decompressed or is not an NCLR file.
    """
    try:
        data = decompress(raw)
    except Exception as exc:
        raise ValueError(f"LZ decompression failed: {exc}") from exc

    hdr = _parse_nitro_header(data)

    if hdr["magic"] != b"RLCN":
        raise ValueError(
            f"Not an NCLR file (magic={hdr['magic']!r}, "
            f"expected b'RLCN')"
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
        "format": "NCLR",
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


def decode_lznclr_to_json(raw: bytes) -> str:
    """Decompress, parse, and return a JSON string for an lznclr file."""
    result = decode_lznclr(raw)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Section builders (encode)
# ---------------------------------------------------------------------------

def _build_pltt_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild PLTT (TTLP) section from parsed dict."""
    colours_rgb = parsed["colours_rgb"]
    bpp_flag = parsed["bpp_flag"]
    pad = (
        int(parsed["padding"], 16)
        if isinstance(parsed["padding"], str)
        else parsed["padding"]
    )
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
    """Rebuild PCMP (PMCP) section."""
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


_SECTION_BUILDERS: dict[str, Any] = {
    "PLTT": _build_pltt_section,
    "PCMP": _build_pcmp_section,
}


# ---------------------------------------------------------------------------
# JSON encode – public API
# ---------------------------------------------------------------------------

def encode_lznclr_from_json(json_str: str) -> bytes:
    """Encode a JSON string back into LZ-compressed NCLR binary.

    Parameters
    ----------
    json_str : str
        JSON text produced by ``decode_lznclr_to_json`` (possibly edited).

    Returns
    -------
    bytes
        LZ-compressed NCLR data ready to patch into a PAC archive.
    """
    obj = json.loads(json_str)
    magic_str: str = obj.get("magic", "RLCN")
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
        "encode_lznclr: NCLR → %d bytes decompressed → %d bytes compressed (0x%02X)",
        len(nitro_data), len(compressed), comp_type,
    )
    return compressed


# ---------------------------------------------------------------------------
# Image rendering – palette swatch
# ---------------------------------------------------------------------------

def decode_lznclr_to_png(raw: bytes) -> bytes:
    """Render an lznclr NCLR palette as a PNG swatch image.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lznclr data.

    Returns
    -------
    bytes
        PNG image data.

    Raises
    ------
    ValueError
        If the data cannot be decompressed or is not a valid NCLR.
    """
    parsed = decode_lznclr(raw)

    pltt_parsed = None
    for sec in parsed["sections"]:
        if sec["tag_display"] == "PLTT":
            pltt_parsed = sec["parsed"]
            break
    if pltt_parsed is None:
        raise ValueError("NCLR file has no PLTT section")

    img = _render_nclr_palette(pltt_parsed["colours_rgb"], pltt_parsed["bpp"])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def decode_lznclr_to_base64(raw: bytes) -> str:
    """Return a ``data:image/png;base64,…`` URI for the NCLR palette swatch."""
    png_bytes = decode_lznclr_to_png(raw)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# Image encode – NCLR palette from PNG swatch
# ---------------------------------------------------------------------------

def encode_lznclr(png_data: bytes, original_raw: bytes) -> bytes:
    """Encode a PNG palette swatch back into an NCLR lznclr file.

    Reads colours from the swatch image (one 16×16 cell per colour, arranged
    in rows of 16) and replaces the palette data in the original NCLR
    structure.

    Parameters
    ----------
    png_data : bytes
        PNG image data (the replacement palette swatch).
    original_raw : bytes
        The original compressed lznclr NCLR data from the PAC archive.

    Returns
    -------
    bytes
        LZ-compressed NCLR data.

    Raises
    ------
    ValueError
        If the original is not a valid NCLR.
    """
    # Parse the original to use as structural template
    result = decode_lznclr(original_raw)

    pltt_sec = None
    for sec in result["sections"]:
        if sec["tag_display"] == "PLTT":
            pltt_sec = sec
            break
    if pltt_sec is None:
        raise ValueError("Original NCLR has no PLTT section")

    original_num_colours = pltt_sec["parsed"]["num_colours"]

    # Open the replacement swatch image
    img = Image.open(io.BytesIO(png_data)).convert("RGB")
    w, h = img.size
    px = img.load()

    cell = 16  # each colour swatch is 16×16
    cols_per_row = 16

    cols = w // cell
    rows = h // cell

    # Sample the centre of each cell to extract the colour
    new_colours: list[list[int]] = []
    for row in range(rows):
        for col in range(cols):
            cx = col * cell + cell // 2
            cy = row * cell + cell // 2
            if cx < w and cy < h:
                r, g, b = px[cx, cy]
                new_colours.append([r, g, b])

    # Ensure we have the right number of colours
    while len(new_colours) < original_num_colours:
        new_colours.append([0, 0, 0])
    new_colours = new_colours[:original_num_colours]

    # Update the palette in the parsed structure
    pltt_sec["parsed"]["colours_rgb"] = new_colours
    pltt_sec["parsed"]["data_size"] = len(new_colours) * 2

    return encode_lznclr_from_json(json.dumps(result))


# ---------------------------------------------------------------------------
# Palette extraction helper (for use by other codecs)
# ---------------------------------------------------------------------------

def extract_palette(raw: bytes) -> list[tuple[int, int, int]]:
    """Extract the (R, G, B) palette list from compressed NCLR data.

    Parameters
    ----------
    raw : bytes
        Compressed lznclr data.

    Returns
    -------
    list of (R, G, B) tuples
        Palette colours in order.
    """
    parsed = decode_lznclr(raw)
    for sec in parsed["sections"]:
        if sec["tag_display"] == "PLTT":
            return [tuple(c) for c in sec["parsed"]["colours_rgb"]]
    raise ValueError("NCLR has no PLTT section")

"""Helpers shared verbatim by the Nitro graphics codecs (lz5bg/lznanr/lzncer/lzncgr/lznclr)."""
from __future__ import annotations

import base64
import math
import struct
from typing import Any

from PIL import Image

def _bgr555_to_rgb(value: int) -> tuple[int, int, int]:
    """Convert a 16-bit NDS BGR555 colour to an (R, G, B) tuple (0-255)."""
    r = (value & 0x1F) << 3
    g = ((value >> 5) & 0x1F) << 3
    b = ((value >> 10) & 0x1F) << 3
    return (r, g, b)


def _decode_tile_4bpp(data: bytes, offset: int) -> list[list[int]]:
    """Decode one 8×8 tile at 4 bits-per-pixel (32 bytes) → pixel indices."""
    rows: list[list[int]] = []
    for r in range(8):
        row: list[int] = []
        for c in range(4):
            b = data[offset + r * 4 + c]
            row.append(b & 0x0F)
            row.append((b >> 4) & 0x0F)
        rows.append(row)
    return rows


def _rgb_to_bgr555(r: int, g: int, b: int) -> int:
    """Convert an (R, G, B) tuple (0-255) to a 16-bit NDS BGR555 value."""
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def _encode_tile_4bpp(indices: list[list[int]]) -> bytes:
    """Encode an 8×8 grid of palette indices into 32 bytes (4 bpp)."""
    out = bytearray(32)
    for r in range(8):
        for c in range(4):
            lo = indices[r][c * 2] & 0x0F
            hi = (indices[r][c * 2 + 1] & 0x0F) << 4
            out[r * 4 + c] = lo | hi
    return bytes(out)


def _encode_tile_8bpp(indices: list[list[int]]) -> bytes:
    """Encode an 8×8 grid of palette indices into 64 bytes (8 bpp)."""
    out = bytearray(64)
    for r in range(8):
        for c in range(8):
            out[r * 8 + c] = indices[r][c] & 0xFF
    return bytes(out)


def _colour_distance_sq(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> int:
    """Squared Euclidean distance between two RGB colours."""
    return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2


def _decode_tile_8bpp(data: bytes, offset: int) -> list[list[int]]:
    """Decode one 8×8 tile at 8 bits-per-pixel (64 bytes) → pixel indices."""
    rows: list[list[int]] = []
    for r in range(8):
        rows.append([data[offset + r * 8 + c] for c in range(8)])
    return rows


def _build_char_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild CHAR (RAHC) section from parsed dict."""
    tile_data = base64.b64decode(parsed["tile_data_b64"])
    bpp_flag = parsed["bpp_flag"]
    height_tiles = parsed["height_tiles"]
    width_tiles = parsed["width_tiles"]
    mapping = int(parsed["mapping_type"], 16) if isinstance(parsed["mapping_type"], str) else parsed["mapping_type"]
    flags = int(parsed["flags"], 16) if isinstance(parsed["flags"], str) else parsed["flags"]
    padding = int(parsed["padding"], 16) if isinstance(parsed["padding"], str) else parsed["padding"]

    sub_header = bytearray(24)
    struct.pack_into("<H", sub_header, 0, height_tiles)
    struct.pack_into("<H", sub_header, 2, width_tiles)
    struct.pack_into("<I", sub_header, 4, bpp_flag)
    struct.pack_into("<I", sub_header, 8, mapping)
    struct.pack_into("<I", sub_header, 12, flags)
    struct.pack_into("<I", sub_header, 16, len(tile_data))
    struct.pack_into("<I", sub_header, 20, padding)

    section_size = 8 + len(sub_header) + len(tile_data)
    header = bytearray(8)
    header[0:4] = b"RAHC"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + sub_header + tile_data)


def _build_generic_section(tag_str: str, parsed: dict[str, Any]) -> bytes:
    """Rebuild an unknown section from base64 data."""
    body = base64.b64decode(parsed.get("data_b64", ""))
    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = tag_str.encode("ascii", errors="replace")[:4].ljust(4, b"\x00")
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header + body)


# Tag display → builder


def _render_nclr_palette(
    colours_rgb: list[list[int]],
    bpp: int,
) -> Image.Image:
    """Render an NCLR palette as a swatch image.

    Each colour is drawn as a 16×16 square.  For 4 bpp palettes (up to 16
    colours per row), multiple palette rows are stacked vertically.
    """
    num_colours = len(colours_rgb)
    if num_colours == 0:
        raise ValueError("NCLR has no colours")

    cols_per_row = 16
    num_rows = math.ceil(num_colours / cols_per_row)
    cell = 16  # pixels per swatch

    img = Image.new("RGB", (cols_per_row * cell, num_rows * cell), (32, 32, 32))
    px = img.load()

    for i, (r, g, b) in enumerate(colours_rgb):
        cx = (i % cols_per_row) * cell
        cy = (i // cols_per_row) * cell
        for dy in range(cell):
            for dx in range(cell):
                px[cx + dx, cy + dy] = (r, g, b)

    return img


# ---------------------------------------------------------------------------
# Image decode – public API
# ---------------------------------------------------------------------------


def _map_to_palette(
    img: Image.Image,
    palette: list[tuple[int, int, int]],
) -> list[list[int]]:
    """Map each pixel to the nearest palette index.  Index 0 = transparent."""
    w, h = img.size
    rgba = img.convert("RGBA")
    rgba_px = rgba.load()
    usable_pal = palette[1:]

    pixel_indices: list[list[int]] = []
    for y in range(h):
        row: list[int] = []
        for x in range(w):
            r, g, b, a = rgba_px[x, y]
            if a < 128:
                row.append(0)
            else:
                best_idx = 0
                best_dist = float("inf")
                for pi, pc in enumerate(usable_pal, start=1):
                    d = _colour_distance_sq((r, g, b), pc)
                    if d < best_dist:
                        best_dist = d
                        best_idx = pi
                        if d == 0:
                            break
                row.append(best_idx)
        pixel_indices.append(row)
    return pixel_indices


def _quantize_image(
    img: Image.Image,
    max_colours: int,
    original_palette: list[tuple[int, int, int]] | None = None,
) -> tuple[list[tuple[int, int, int]], list[list[int]]]:
    """Quantize an RGBA image.  Reuses *original_palette* when provided."""
    if original_palette is not None:
        pal = list(original_palette)
        while len(pal) < max_colours:
            pal.append((0, 0, 0))
        pal = pal[:max_colours]
        indices = _map_to_palette(img, pal)
        return pal, indices

    # Fresh quantization
    w, h = img.size
    rgba = img.convert("RGBA")
    rgb_img = Image.new("RGB", (w, h), (0, 0, 0))
    alpha_mask: list[list[bool]] = []
    rgba_px = rgba.load()
    rgb_px = rgb_img.load()
    for y in range(h):
        row: list[bool] = []
        for x in range(w):
            r, g, b, a = rgba_px[x, y]
            transparent = a < 128
            row.append(transparent)
            if not transparent:
                rgb_px[x, y] = (r, g, b)
        alpha_mask.append(row)

    usable = max(max_colours - 1, 1)
    quant = rgb_img.quantize(colors=usable, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    quant_palette_flat = quant.getpalette()
    if quant_palette_flat is None:
        raise ValueError("Quantization produced no palette")
    quant_px = quant.load()

    palette: list[tuple[int, int, int]] = [(0, 0, 0)]
    for i in range(usable):
        idx = i * 3
        if idx + 2 < len(quant_palette_flat):
            palette.append((quant_palette_flat[idx], quant_palette_flat[idx + 1], quant_palette_flat[idx + 2]))
        else:
            palette.append((0, 0, 0))
    while len(palette) < max_colours:
        palette.append((0, 0, 0))

    pixel_indices: list[list[int]] = []
    for y in range(h):
        row_idx: list[int] = []
        for x in range(w):
            if alpha_mask[y][x]:
                row_idx.append(0)
            else:
                row_idx.append(int(quant_px[x, y]) + 1)
        pixel_indices.append(row_idx)

    return palette[:max_colours], pixel_indices


def _detect_compression_type(raw: bytes) -> int:
    """Detect the LZ compression type from the first byte of compressed data."""
    if len(raw) == 0:
        return 0x11
    header = raw[0]
    if header in (0x10, 0x11, 0x50):
        return header
    return 0x11


# ---------------------------------------------------------------------------
# NITRO container helpers
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
        "bom": bom,
        "version": version,
        "file_size": file_size,
        "header_size": header_size,
        "num_sections": num_sections,
    }


def _parse_uext_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Parse UEXT (TXEU) section."""
    body_off = offset + 8
    body = data[body_off : offset + size]
    return {"data_hex": body.hex()}


def _parse_generic_section(data: bytes, offset: int, size: int) -> dict[str, Any]:
    """Fallback parser for unknown/extra sections."""
    body_off = offset + 8
    body = data[body_off : offset + size]
    return {"data_b64": base64.b64encode(body).decode("ascii")}


# Tag → parser mapping


def _build_uext_section(parsed: dict[str, Any]) -> bytes:
    """Rebuild UEXT (TXEU) section."""
    body = bytes.fromhex(parsed.get("data_hex", "00000000"))
    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = b"TXEU"
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header) + body


def _build_generic_section(tag_str: str, parsed: dict[str, Any]) -> bytes:
    """Rebuild an unknown section from base64 data."""
    body = base64.b64decode(parsed.get("data_b64", ""))
    section_size = 8 + len(body)
    header = bytearray(8)
    header[0:4] = tag_str.encode("ascii", errors="replace")[:4].ljust(4, b"\x00")
    struct.pack_into("<I", header, 4, section_size)
    return bytes(header) + body


# Tag display → builder



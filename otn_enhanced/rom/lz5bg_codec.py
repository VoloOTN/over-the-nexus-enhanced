"""Decoder for lz5bg (NTBG) compressed background / sprite graphics files.

Binary layout
=============
lz5bg files are LZ-compressed (typically LZ11 with header byte 0x11, despite
the "lz5" in the extension).  After decompression the payload is an **NTBG**
container with the following structure:

NTBG Header (16 bytes)
----------------------
Offset  Size  Description
------  ----  -----------
0       4     Magic ``NTBG``
4       2     BOM  ``0xFEFF`` (little-endian)
6       2     Version (observed ``0x0100``)
8       4     Total file size
12      2     Header size (always 16)
14      2     Number of sections

Sections
--------
Each section starts with a 4-byte ASCII tag and 4-byte little-endian size.

**PALT** – Palette (BGR555 colours)
  +8   u32   Number of palette entries (16 = 4 bpp, 256 = 8 bpp)
  +12  2*N   Palette entries in NDS BGR555 format

**BGDT** – Background tile data (tiled background)
  +8   u8    Bit-depth flag  (0 = 4 bpp, 1 = 8 bpp)
  +9   u8    0xFF
  +10  u16   Always 2
  +12  u32   Tilemap size in bytes  (width_tiles × height_tiles × 2)
  +16  u16   Width  in 8-pixel tiles
  +18  u16   Height in 8-pixel tiles
  +20  u16   (duplicate width)
  +22  u16   (usually 1)
  +24  u32   Character (tile pixel) data size in bytes
  [tilemap_data]  →  width×height 16-bit entries
  [char_data]     →  tile pixel data

**OBJD** – Object / sprite tile data (linear tiles, no tilemap)
  +8   u32   Flags
  +12  u32   Offset-table size in bytes (N × 4)
  +16  u16   Cell columns
  +18  u16   Cell rows
  +20  u32   Padding (0)
  +24  u16   (duplicate columns)
  +26  u16   (duplicate rows)
  +28  u32   Character data size in bytes
  +32  u32   Padding (0)
  [offset_table]  →  u32[N]  byte offsets per cell
  [char_data]     →  tile pixel data

**DFPL** – Default palette (optional, ignored for rendering)
"""

from __future__ import annotations

import io
import logging
import math
import struct
from typing import Any

from PIL import Image

from otn_enhanced.rom.lz_compression import compress, decompress
from otn_enhanced.rom.nitro_common import _bgr555_to_rgb, _decode_tile_4bpp, _rgb_to_bgr555, _encode_tile_4bpp, _encode_tile_8bpp, _colour_distance_sq  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Low-level NDS helpers
# ---------------------------------------------------------------------------

def _decode_tile_8bpp(data: bytes, offset: int) -> list[list[int]]:
    """Decode one 8×8 tile at 8 bits-per-pixel (64 bytes) → pixel indices."""
    rows: list[list[int]] = []
    for r in range(8):
        rows.append([data[offset + r * 8 + c] for c in range(8)])
    return rows


# ---------------------------------------------------------------------------
# NTBG section parsers
# ---------------------------------------------------------------------------

def _parse_ntbg_sections(data: bytes) -> dict[bytes, tuple[int, int]]:
    """Walk the NTBG header and return ``{tag: (offset, size)}``."""
    if data[:4] != b"NTBG":
        raise ValueError(f"Not an NTBG file (magic={data[:4]!r})")
    header_size = struct.unpack_from("<H", data, 12)[0]
    num_sections = struct.unpack_from("<H", data, 14)[0]
    sections: dict[bytes, tuple[int, int]] = {}
    offset = header_size
    for _ in range(num_sections):
        if offset + 8 > len(data):
            break
        tag = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        sections[tag] = (offset, size)
        offset += size
    return sections


def _parse_palette(data: bytes, palt_offset: int) -> list[tuple[int, int, int]]:
    """Parse a PALT section → list of (R, G, B) tuples."""
    if palt_offset + 12 > len(data):
        raise ValueError("PALT section truncated (no colour count)")
    num_colours = struct.unpack_from("<I", data, palt_offset + 8)[0]
    palette: list[tuple[int, int, int]] = []
    for i in range(num_colours):
        pos = palt_offset + 12 + i * 2
        if pos + 2 > len(data):
            break
        val = struct.unpack_from("<H", data, pos)[0]
        palette.append(_bgr555_to_rgb(val))
    return palette


# ---------------------------------------------------------------------------
# BGDT renderer  (tiled background with tilemap)
# ---------------------------------------------------------------------------

def _render_bgdt(
    data: bytes,
    palette: list[tuple[int, int, int]],
    bgdt_offset: int,
) -> Image.Image:
    """Render a BGDT section to a PIL RGBA image."""
    if bgdt_offset + 28 > len(data):
        raise ValueError("BGDT section header truncated")
    bpp_flag = data[bgdt_offset + 8]
    bpp = 8 if bpp_flag else 4
    tilemap_size = struct.unpack_from("<I", data, bgdt_offset + 12)[0]
    w_tiles = struct.unpack_from("<H", data, bgdt_offset + 16)[0]
    h_tiles = struct.unpack_from("<H", data, bgdt_offset + 18)[0]
    char_size = struct.unpack_from("<I", data, bgdt_offset + 24)[0]

    tm_start = bgdt_offset + 28
    ch_start = tm_start + tilemap_size

    if w_tiles == 0 or h_tiles == 0:
        raise ValueError("BGDT has zero dimensions")

    bytes_per_tile = 64 if bpp == 8 else 32
    decode_tile = _decode_tile_8bpp if bpp == 8 else _decode_tile_4bpp

    # Parse tilemap
    tilemap: list[tuple[int, bool, bool, int]] = []
    for i in range(w_tiles * h_tiles):
        pos = tm_start + i * 2
        if pos + 2 > len(data):
            tilemap.append((0, False, False, 0))
            continue
        entry = struct.unpack_from("<H", data, pos)[0]
        tilemap.append((
            entry & 0x3FF,          # tile index
            bool(entry & 0x400),    # horizontal flip
            bool(entry & 0x800),    # vertical flip
            (entry >> 12) & 0xF,    # palette row (4 bpp only)
        ))

    img = Image.new("RGBA", (w_tiles * 8, h_tiles * 8), (0, 0, 0, 0))
    px = img.load()

    for ty in range(h_tiles):
        for tx in range(w_tiles):
            tile_idx, hflip, vflip, pal_row = tilemap[ty * w_tiles + tx]
            tile_off = ch_start + tile_idx * bytes_per_tile
            if tile_off + bytes_per_tile > len(data):
                continue
            tile = decode_tile(data, tile_off)
            pal_base = pal_row * 16 if bpp == 4 else 0

            for py in range(8):
                for ppx in range(8):
                    sy = (7 - py) if vflip else py
                    sx = (7 - ppx) if hflip else ppx
                    ci = tile[sy][sx]
                    ai = pal_base + ci
                    if ai < len(palette):
                        r, g, b = palette[ai]
                        a = 0 if ci == 0 else 255
                        px[tx * 8 + ppx, ty * 8 + py] = (r, g, b, a)

    return img


# ---------------------------------------------------------------------------
# OBJD renderer  (linear tile sheet – no tilemap)
# ---------------------------------------------------------------------------

_OBJD_BASE_HEADER = 24  # bytes before the offset table

def _render_objd(
    data: bytes,
    palette: list[tuple[int, int, int]],
    objd_offset: int,
    objd_size: int,
) -> Image.Image:
    """Render an OBJD section as a tile-sheet image."""
    if objd_offset + 32 > len(data):
        raise ValueError("OBJD section header truncated")
    bpp = 4 if len(palette) <= 16 else 8
    bytes_per_tile = 32 if bpp == 4 else 64
    decode_tile = _decode_tile_4bpp if bpp == 4 else _decode_tile_8bpp

    # Read char data size and offset table size from sub-header
    offset_tbl_sz = struct.unpack_from("<I", data, objd_offset + 12)[0]
    char_data_size = struct.unpack_from("<I", data, objd_offset + 28)[0]

    # Cell dimensions from sub-header
    w_cells = struct.unpack_from("<H", data, objd_offset + 16)[0]
    h_cells = struct.unpack_from("<H", data, objd_offset + 18)[0]

    sub_header_size = _OBJD_BASE_HEADER + offset_tbl_sz
    ch_start = objd_offset + 8 + sub_header_size  # 8 for magic+size

    num_tiles = char_data_size // bytes_per_tile
    if num_tiles == 0:
        raise ValueError("OBJD has no tile data")

    num_cells = max(w_cells * h_cells, 1)
    tiles_per_cell = num_tiles // num_cells if num_cells else num_tiles

    # Determine per-cell tile grid (approximate square)
    cell_cols = int(math.ceil(math.sqrt(tiles_per_cell)))
    cell_rows = int(math.ceil(tiles_per_cell / cell_cols)) if cell_cols else 1

    img_w = w_cells * cell_cols * 8
    img_h = h_cells * cell_rows * 8
    if img_w == 0 or img_h == 0:
        # Fallback: flat strip
        img_w = min(num_tiles, 16) * 8
        img_h = math.ceil(num_tiles / min(num_tiles, 16)) * 8

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    px = img.load()

    tile_idx = 0
    for cy in range(h_cells):
        for cx in range(w_cells):
            for lt in range(tiles_per_cell):
                if tile_idx >= num_tiles:
                    break
                toff = ch_start + tile_idx * bytes_per_tile
                if toff + bytes_per_tile > len(data):
                    tile_idx += 1
                    continue
                tile = decode_tile(data, toff)

                local_tx = lt % cell_cols
                local_ty = lt // cell_cols
                abs_px_x = (cx * cell_cols + local_tx) * 8
                abs_px_y = (cy * cell_rows + local_ty) * 8

                for py in range(8):
                    for ppx in range(8):
                        ci = tile[py][ppx]
                        if ci < len(palette):
                            r, g, b = palette[ci]
                            a = 0 if ci == 0 else 255
                            dx = abs_px_x + ppx
                            dy = abs_px_y + py
                            if 0 <= dx < img_w and 0 <= dy < img_h:
                                px[dx, dy] = (r, g, b, a)
                tile_idx += 1

    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decode_lz5bg(raw: bytes) -> Image.Image:
    """Decompress and render an lz5bg file to a PIL ``Image``.

    Parameters
    ----------
    raw : bytes
        The raw (compressed) lz5bg data as extracted from a PAC archive.

    Returns
    -------
    PIL.Image.Image
        RGBA image of the rendered graphics.

    Raises
    ------
    ValueError
        If the data cannot be decompressed or parsed.
    """
    # --- decompress --------------------------------------------------------
    try:
        data = decompress(raw)
    except Exception as exc:
        raise ValueError(f"LZ decompression failed: {exc}") from exc

    if data[:4] != b"NTBG":
        raise ValueError(f"Not an NTBG file after decompression (magic={data[:4].hex()})")

    # --- parse sections ----------------------------------------------------
    sections = _parse_ntbg_sections(data)

    if b"PALT" not in sections:
        raise ValueError("NTBG file has no PALT section")
    palette = _parse_palette(data, sections[b"PALT"][0])

    # --- render ------------------------------------------------------------
    if b"BGDT" in sections:
        off, _sz = sections[b"BGDT"]
        return _render_bgdt(data, palette, off)

    if b"OBJD" in sections:
        off, sz = sections[b"OBJD"]
        return _render_objd(data, palette, off, sz)

    raise ValueError(
        f"NTBG file has neither BGDT nor OBJD (sections: "
        f"{[k.decode('ascii','replace') for k in sections]})"
    )


def decode_lz5bg_to_png(raw: bytes) -> bytes:
    """Decompress and render an lz5bg file, returning **PNG bytes**.

    This is the primary entry-point for integrating with the Dash app or
    other tooling that needs a rendered image in a portable format.
    """
    img = decode_lz5bg(raw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def decode_lz5bg_to_base64(raw: bytes) -> str:
    """Return a ``data:image/png;base64,…`` URI for direct embedding."""
    import base64

    png_bytes = decode_lz5bg_to_png(raw)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ===================================================================
# Encoder – PNG → NTBG → LZ-compressed lz5bg
# ===================================================================

def _map_to_palette(
    img: Image.Image,
    palette: list[tuple[int, int, int]],
) -> list[list[int]]:
    """Map each pixel in *img* to the nearest palette index.

    Index 0 is treated as transparent.  A pixel maps to 0 if it is
    transparent (alpha < 128) **or** if its colour is exactly ``palette[0]``;
    every other pixel is matched to the closest colour in ``palette[1:]``.

    That second rule is what makes decode -> encode lossless.  ``decode_lz5bg``
    renders index 0 as its literal palette colour on an opaque image, so
    without it every transparent pixel comes back opaque and gets re-matched
    against ``palette[1:]`` -- measured on Forest (field.pac file 61) as 23808
    of 49152 pixels turning (248,0,248) into (144,96,176), while every other
    pixel round-tripped exactly.  It also gives callers a way to author
    transparency with no alpha channel, using the template's own index-0
    colour as the key.
    """
    w, h = img.size
    rgba = img.convert("RGBA")
    rgba_px = rgba.load()
    transparent_key = palette[0] if palette else None

    # Pre-compute palette lookup (skip index 0 = transparent)
    usable_pal = palette[1:]  # indices 1..N

    pixel_indices: list[list[int]] = []
    for y in range(h):
        row: list[int] = []
        for x in range(w):
            r, g, b, a = rgba_px[x, y]
            if a < 128 or (r, g, b) == transparent_key:
                row.append(0)
            else:
                # Find closest palette entry
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
    """Quantize an RGBA image to *max_colours* and return (palette, pixel_indices).

    If *original_palette* is provided the original colours are re-used and each
    pixel is mapped to the nearest entry (lossless for true round-trips).
    Otherwise a fresh palette is derived via median-cut quantization.

    Index 0 is reserved for transparent pixels.  The returned palette always has
    exactly *max_colours* entries (padded with black if necessary).

    ``pixel_indices`` is a row-major grid: ``pixel_indices[y][x]``.
    """
    # ------------------------------------------------------------------
    # Fast path: reuse the original palette when available
    # ------------------------------------------------------------------
    if original_palette is not None:
        pal = list(original_palette)
        while len(pal) < max_colours:
            pal.append((0, 0, 0))
        pal = pal[:max_colours]
        indices = _map_to_palette(img, pal)
        return pal, indices

    # ------------------------------------------------------------------
    # Slow path: fresh quantization
    # ------------------------------------------------------------------
    w, h = img.size
    rgba = img.convert("RGBA")

    # Build (R, G, B) image with transparent pixels mapped to a sentinel
    rgb_img = Image.new("RGB", (w, h), (0, 0, 0))
    alpha_mask: list[list[bool]] = []  # True = transparent
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

    # Quantize to (max_colours - 1) so index 0 stays transparent
    usable = max(max_colours - 1, 1)
    quant = rgb_img.quantize(colors=usable, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    quant_palette_flat = quant.getpalette()  # [R,G,B, R,G,B, ...]
    if quant_palette_flat is None:
        raise ValueError("Quantization produced no palette")

    quant_px = quant.load()

    # Build final palette: index 0 = transparent (black)
    palette: list[tuple[int, int, int]] = [(0, 0, 0)]
    for i in range(usable):
        idx = i * 3
        if idx + 2 < len(quant_palette_flat):
            palette.append((quant_palette_flat[idx], quant_palette_flat[idx + 1], quant_palette_flat[idx + 2]))
        else:
            palette.append((0, 0, 0))

    # Pad to max_colours
    while len(palette) < max_colours:
        palette.append((0, 0, 0))

    # Build index grid – transparent pixels → 0, others → quantised + 1
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


def _build_palt_section(palette: list[tuple[int, int, int]]) -> bytes:
    """Build a PALT section from an RGB palette list."""
    num_colours = len(palette)
    # Section: tag(4) + size(4) + num_colours(4) + entries(2*N)
    data_size = 12 + num_colours * 2
    buf = bytearray(data_size)
    buf[0:4] = b"PALT"
    struct.pack_into("<I", buf, 4, data_size)
    struct.pack_into("<I", buf, 8, num_colours)
    for i, (r, g, b) in enumerate(palette):
        struct.pack_into("<H", buf, 12 + i * 2, _rgb_to_bgr555(r, g, b))
    return bytes(buf)


def _build_bgdt_section(
    pixel_indices: list[list[int]],
    bpp: int,
    w_tiles: int,
    h_tiles: int,
) -> bytes:
    """Build a BGDT section from pixel indices, de-duplicating tiles.

    Identical 8x8 blocks share one entry in the character data, and the tilemap's
    H/V flip bits are used so a block that is the mirror of an existing tile
    costs nothing either.

    De-duplication is not an optimisation here, it is a correctness requirement.
    A naive one-tile-per-cell 256x192 background is 768 tiles / 49152 bytes, and
    that drew the top of the picture correctly, then black, then a band of
    garbage, in game on 2026-09-07.  De-duplicated output (388..397 tiles, the
    same range as the 65 stock field backgrounds) works.

    ⚠️ The exact limit is NOT known -- it is somewhere in 398..768 and was never
    measured.  397 is not a hardware cap but a structural ceiling of the canvas:
    372 of the 768 cells in a field background are entirely transparent and
    collapse to one tile, leaving 396 that can differ.
    """
    encode_tile = _encode_tile_4bpp if bpp == 4 else _encode_tile_8bpp
    bytes_per_tile = 32 if bpp == 4 else 64

    def _flip(block: list[list[int]], h: bool, v: bool) -> list[list[int]]:
        rows = block[::-1] if v else block
        return [r[::-1] if h else r for r in rows]

    # Build tiles and tilemap
    tilemap_entries: list[int] = []
    tile_data = bytearray()
    seen: dict[bytes, int] = {}
    for ty in range(h_tiles):
        for tx in range(w_tiles):
            # Extract 8×8 block
            block: list[list[int]] = []
            for py in range(8):
                row: list[int] = []
                for px in range(8):
                    iy = ty * 8 + py
                    ix = tx * 8 + px
                    if iy < len(pixel_indices) and ix < len(pixel_indices[iy]):
                        row.append(pixel_indices[iy][ix])
                    else:
                        row.append(0)
                block.append(row)

            # The decoder reads a stored tile through the flip bits, and a flip
            # is its own inverse, so the tile to look for under flags (h, v) is
            # simply the block flipped the same way.
            entry = None
            for h, v in ((False, False), (True, False), (False, True), (True, True)):
                key = encode_tile(_flip(block, h, v))
                idx = seen.get(key)
                if idx is not None:
                    entry = (idx & 0x3FF) | (0x400 if h else 0) | (0x800 if v else 0)
                    break
            if entry is None:
                key = encode_tile(block)
                idx = len(seen)
                seen[key] = idx
                tile_data.extend(key)
                entry = idx & 0x3FF
            tilemap_entries.append(entry)

    if len(seen) > 0x3FF:
        raise ValueError(
            f"{len(seen)} unique tiles exceeds the 10-bit tilemap index limit")

    tilemap_size = w_tiles * h_tiles * 2
    char_data_size = len(tile_data)

    # BGDT sub-header: 20 bytes (offsets +8 to +27)
    sub_header = bytearray(20)
    sub_header[0] = 0 if bpp == 4 else 1      # bpp_flag
    sub_header[1] = 0xFF
    struct.pack_into("<H", sub_header, 2, 2)   # always 2
    struct.pack_into("<I", sub_header, 4, tilemap_size)
    struct.pack_into("<H", sub_header, 8, w_tiles)
    struct.pack_into("<H", sub_header, 10, h_tiles)
    struct.pack_into("<H", sub_header, 12, w_tiles)  # duplicate
    struct.pack_into("<H", sub_header, 14, 1)         # usually 1
    struct.pack_into("<I", sub_header, 16, char_data_size)

    # Tilemap bytes
    tilemap_bytes = bytearray(tilemap_size)
    for i, entry in enumerate(tilemap_entries):
        struct.pack_into("<H", tilemap_bytes, i * 2, entry)

    # Full section: tag(4) + size(4) + sub_header(20) + tilemap + char_data
    section_size = 8 + len(sub_header) + len(tilemap_bytes) + len(tile_data)
    buf = bytearray(8)
    buf[0:4] = b"BGDT"
    struct.pack_into("<I", buf, 4, section_size)
    return bytes(buf + sub_header + tilemap_bytes + tile_data)


def _build_objd_section(
    pixel_indices: list[list[int]],
    bpp: int,
    original_data: bytes,
    objd_offset: int,
) -> bytes:
    """Build an OBJD section from pixel indices, preserving original metadata.

    This re-uses the original OBJD sub-header (flags, cell dims, offset table)
    and only replaces the character (tile pixel) data.
    """
    encode_tile = _encode_tile_4bpp if bpp == 4 else _encode_tile_8bpp
    bytes_per_tile = 32 if bpp == 4 else 64

    # Read original sub-header fields
    offset_tbl_sz = struct.unpack_from("<I", original_data, objd_offset + 12)[0]
    w_cells = struct.unpack_from("<H", original_data, objd_offset + 16)[0]
    h_cells = struct.unpack_from("<H", original_data, objd_offset + 18)[0]
    orig_char_size = struct.unpack_from("<I", original_data, objd_offset + 28)[0]

    # Preserve sub-header bytes verbatim (from +8 to end of offset table)
    sub_header_size = _OBJD_BASE_HEADER + offset_tbl_sz
    sub_header = original_data[objd_offset + 8 : objd_offset + 8 + sub_header_size]

    # Compute tile layout (same as decoder)
    num_tiles_orig = orig_char_size // bytes_per_tile
    num_cells = max(w_cells * h_cells, 1)
    tiles_per_cell = num_tiles_orig // num_cells if num_cells else num_tiles_orig
    cell_cols = int(math.ceil(math.sqrt(tiles_per_cell)))
    cell_rows = int(math.ceil(tiles_per_cell / cell_cols)) if cell_cols else 1

    # Re-encode tiles in the same order as the decoder reads them
    tile_data = bytearray()
    tile_idx = 0
    for cy in range(h_cells):
        for cx in range(w_cells):
            for lt in range(tiles_per_cell):
                if tile_idx >= num_tiles_orig:
                    break
                local_tx = lt % cell_cols
                local_ty = lt // cell_cols
                abs_px_x = (cx * cell_cols + local_tx) * 8
                abs_px_y = (cy * cell_rows + local_ty) * 8

                block: list[list[int]] = []
                for py in range(8):
                    row: list[int] = []
                    for ppx in range(8):
                        iy = abs_px_y + py
                        ix = abs_px_x + ppx
                        if iy < len(pixel_indices) and ix < len(pixel_indices[iy]):
                            row.append(pixel_indices[iy][ix])
                        else:
                            row.append(0)
                    block.append(row)
                tile_data.extend(encode_tile(block))
                tile_idx += 1

    # Patch the char_data_size in the sub-header copy
    sub_header_mut = bytearray(sub_header)
    struct.pack_into("<I", sub_header_mut, 20, len(tile_data))  # offset 28 - 8 = 20

    section_size = 8 + len(sub_header_mut) + len(tile_data)
    buf = bytearray(8)
    buf[0:4] = b"OBJD"
    struct.pack_into("<I", buf, 4, section_size)
    return bytes(buf + sub_header_mut + tile_data)


def _build_dfpl_section(original_data: bytes, dfpl_offset: int, dfpl_size: int) -> bytes:
    """Preserve a DFPL section verbatim from the original."""
    return bytes(original_data[dfpl_offset : dfpl_offset + dfpl_size])


def _detect_compression_type(raw: bytes) -> int:
    """Detect the LZ compression type from the first byte of compressed data."""
    if len(raw) == 0:
        return 0x11  # default to LZ11
    header = raw[0]
    if header in (0x10, 0x11, 0x50):
        return header
    return 0x11  # default


def _palette_for_new_art(
    img: Image.Image,
    max_colours: int,
    transparent_key: tuple[int, int, int],
) -> list[tuple[int, int, int]]:
    """Build a fresh palette for artwork that is NOT the template's own picture.

    Index 0 is pinned to *transparent_key* (the template's index-0 colour) and
    the remaining slots are chosen from the opaque pixels only, so the ~48% of a
    field background that is transparent does not eat palette entries.

    Colours are picked on the BGR555 lattice via card_art_codec's
    ``_lattice_palette``: the DS only displays 5 bits per channel, so an 8-bit
    median cut hands back representatives that collapse onto each other when
    snapped, which posterises smooth artwork (learned on the 64x64 card art).
    """
    from otn_enhanced.rom.card_art_codec import _lattice_palette  # local: numpy dep

    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    opaque = [
        (r, g, b)
        for y in range(h)
        for x in range(w)
        for (r, g, b, a) in (px[x, y],)
        if a >= 128 and (r, g, b) != transparent_key
    ]
    if not opaque:
        raise ValueError("image is entirely transparent")

    import numpy as np

    pal = [transparent_key]
    pal += _lattice_palette(np.array(opaque, dtype=np.float64), max_colours - 1)
    while len(pal) < max_colours:
        pal.append((0, 0, 0))
    return pal[:max_colours]


def encode_lz5bg(png_data: bytes, original_raw: bytes,
                 rebuild_palette: bool = False) -> bytes:
    """Encode a PNG image back into lz5bg format using the original as a template.

    The original compressed lz5bg data is used to determine:
    - compression type (LZ10/LZ11/LZ5)
    - NTBG section layout (which sections, order)
    - bit depth (4 bpp / 8 bpp)
    - image dimensions

    The replacement PNG is quantized to fit the original palette constraints
    and must match the original image dimensions.

    Parameters
    ----------
    png_data : bytes
        PNG image data (the replacement image).
    original_raw : bytes
        The original compressed lz5bg data from the PAC archive.

    Returns
    -------
    bytes
        LZ-compressed NTBG data ready to be patched into the PAC.

    Raises
    ------
    ValueError
        If the image dimensions don't match or the original cannot be parsed.
    """
    # --- detect compression type from original ---
    comp_type = _detect_compression_type(original_raw)
    logger.info("encode_lz5bg: detected compression type 0x%02X", comp_type)

    # --- decompress original to use as template ---
    try:
        orig_data = decompress(original_raw)
    except Exception as exc:
        raise ValueError(f"Cannot decompress original lz5bg: {exc}") from exc

    if orig_data[:4] != b"NTBG":
        raise ValueError("Original is not an NTBG file after decompression")

    sections = _parse_ntbg_sections(orig_data)

    # --- extract original palette (used for lossless round-trips) ---
    original_palette: list[tuple[int, int, int]] | None = None
    if b"PALT" in sections:
        original_palette = _parse_palette(orig_data, sections[b"PALT"][0])

    # --- open replacement image ---
    img = Image.open(io.BytesIO(png_data)).convert("RGBA")

    # --- determine bpp and expected dimensions from original ---
    if b"BGDT" in sections:
        bgdt_off, _bgdt_sz = sections[b"BGDT"]
        bpp_flag = orig_data[bgdt_off + 8]
        bpp = 8 if bpp_flag else 4
        w_tiles = struct.unpack_from("<H", orig_data, bgdt_off + 16)[0]
        h_tiles = struct.unpack_from("<H", orig_data, bgdt_off + 18)[0]
        expected_w, expected_h = w_tiles * 8, h_tiles * 8
        section_type = "BGDT"
    elif b"OBJD" in sections:
        objd_off, _objd_sz = sections[b"OBJD"]
        # Determine bpp from original palette size
        if b"PALT" in sections:
            palt_off, _palt_sz = sections[b"PALT"]
            num_colours = struct.unpack_from("<I", orig_data, palt_off + 8)[0]
            bpp = 4 if num_colours <= 16 else 8
        else:
            bpp = 4
        # Compute expected image size (same logic as decoder)
        offset_tbl_sz = struct.unpack_from("<I", orig_data, objd_off + 12)[0]
        w_cells = struct.unpack_from("<H", orig_data, objd_off + 16)[0]
        h_cells = struct.unpack_from("<H", orig_data, objd_off + 18)[0]
        char_data_size = struct.unpack_from("<I", orig_data, objd_off + 28)[0]
        bytes_per_tile = 32 if bpp == 4 else 64
        num_tiles = char_data_size // bytes_per_tile
        num_cells = max(w_cells * h_cells, 1)
        tiles_per_cell = num_tiles // num_cells if num_cells else num_tiles
        cell_cols = int(math.ceil(math.sqrt(tiles_per_cell)))
        cell_rows = int(math.ceil(tiles_per_cell / cell_cols)) if cell_cols else 1
        expected_w = w_cells * cell_cols * 8
        expected_h = h_cells * cell_rows * 8
        section_type = "OBJD"
    else:
        raise ValueError("Original NTBG has neither BGDT nor OBJD – cannot encode")

    # --- validate dimensions ---
    if img.size != (expected_w, expected_h):
        raise ValueError(
            f"Image dimensions {img.size[0]}×{img.size[1]} don't match "
            f"original {expected_w}×{expected_h}"
        )

    max_colours = 16 if bpp == 4 else 256
    logger.info(
        "encode_lz5bg: %s %d bpp, %d×%d px, %d max colours",
        section_type, bpp, expected_w, expected_h, max_colours,
    )

    # --- choose the palette ---------------------------------------------
    # Default: reuse the template's palette, which makes a true round trip
    # lossless.  For REPLACEMENT art that is the wrong thing to do -- the new
    # picture gets mapped onto the old card's colours (a Pyramid of Light
    # background came back in Forest's greens) -- so rebuild_palette derives a
    # fresh one from the new image instead, keeping index 0 as the template's
    # transparent colour.
    if rebuild_palette and original_palette:
        original_palette = _palette_for_new_art(img, max_colours, original_palette[0])
    palette, pixel_indices = _quantize_image(img, max_colours, original_palette=original_palette)

    # --- rebuild NTBG sections ---
    section_bytes: list[bytes] = []

    # Preserve original section order
    ordered_sections = sorted(sections.items(), key=lambda kv: kv[1][0])
    for tag, (off, sz) in ordered_sections:
        if tag == b"PALT":
            section_bytes.append(_build_palt_section(palette))
        elif tag == b"BGDT":
            section_bytes.append(_build_bgdt_section(pixel_indices, bpp, w_tiles, h_tiles))
        elif tag == b"OBJD":
            section_bytes.append(_build_objd_section(pixel_indices, bpp, orig_data, off))
        elif tag == b"DFPL":
            section_bytes.append(_build_dfpl_section(orig_data, off, sz))
        else:
            # Preserve unknown sections verbatim
            section_bytes.append(bytes(orig_data[off : off + sz]))

    # --- build NTBG header ---
    body = b"".join(section_bytes)
    header_size = 16
    total_size = header_size + len(body)
    num_sections_val = len(section_bytes)

    ntbg_header = bytearray(header_size)
    ntbg_header[0:4] = b"NTBG"
    struct.pack_into("<H", ntbg_header, 4, 0xFEFF)  # BOM
    struct.pack_into("<H", ntbg_header, 6, 0x0100)  # version
    struct.pack_into("<I", ntbg_header, 8, total_size)
    struct.pack_into("<H", ntbg_header, 12, header_size)
    struct.pack_into("<H", ntbg_header, 14, num_sections_val)

    ntbg_data = bytes(ntbg_header) + body

    # --- compress ---
    compressed = compress(ntbg_data, comp_type)
    logger.info(
        "encode_lz5bg: NTBG=%d bytes → compressed=%d bytes (type=0x%02X)",
        len(ntbg_data), len(compressed), comp_type,
    )
    return compressed


def encode_lz5bg_from_png_bytes(png_data: bytes, original_raw: bytes) -> bytes:
    """Convenience alias for ``encode_lz5bg``."""
    return encode_lz5bg(png_data, original_raw)

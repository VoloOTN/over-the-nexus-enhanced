"""Card-art NTBG (re)encoders for Over the Nexus card.pac / BattleMonster pacs.

Three on-disk image formats are produced here, each round-tripped against the
original NITRO background ("NTBG") so the engine renders them unchanged:

  * 32x32 full-card thumbnail  (card.pac file1) -- 8 bpp OBJD, uses the atlas-wide
        SHARED palette stored only in image[0]; index 0 renders transparent.
        ``encode_card_thumb_32x32`` -> NTBG bytes (caller LZ10-compresses).
  * 64x64 cropped artwork       (card.pac file3) -- 4 bpp BGDT with a 256-colour
        PALT split into 16 sub-palette rows + a DFPL table; EVERY image in the
        atlas is exactly 2820 bytes (fixed stride), so the encoder asserts that.
        Only rows 0-14 and, WITHIN each row, only indices 1-15 may be used: index
        0 is transparent in 4 bpp BG hardware, so colouring it punches holes in
        the art. ``encode_card_art_64x64`` -> 2820 NTBG bytes (uncompressed).
  * 256x96 battle sprite        (BattleMonster{1,2,3}.pac) -- 4 bpp BGDT, 16 sub-
        palette rows, index 0 = transparent (green chroma key in the palette),
        32x12 tile map with tile de-duplication.
        ``encode_battle_sprite_256x96`` -> NTBG bytes (caller LZ11-compresses).

The 4 bpp encoders do content-aware sub-palette quantisation: tiles are clustered
into 16 groups, each group gets its own 16-colour palette (median-cut over the
group's pixels), and every tile is then remapped to its group's palette. The
per-tile palette row is written into the tile-map entry (bits 12-15); the DFPL
section is ignored by the renderer and is rebuilt per-tile only when its entry
count matches the tile count, else preserved.

All of that runs ON THE BGR555 LATTICE, which matters more than it looks. The DS
shows 5 bits per channel, so quantising in 8-bit RGB and only converting at write
time means the encoder optimises for colours the hardware never displays: palette
entries that were distinct in 8-bit silently merge (a "16-colour" row rendering as
~11, i.e. banding on smooth art), and pixels get matched against pre-conversion
colours. Source pixels and palette candidates are therefore snapped to the lattice
up front, rows are deduped and refilled rather than padded with duplicates, and the
5-bit conversion rounds to nearest instead of truncating (truncation is biased
downward and darkens everything). Tile grouping is likewise seeded by k-means on
tile mean colour but then refined by Lloyd iteration on true per-tile quantisation
error, since a tile spanning two regions has a mean belonging to neither.

The 8 bpp thumbnail reuses the shared-palette helpers from ``lz5bg_codec``.
"""
from __future__ import annotations

import struct

import numpy as np
from PIL import Image

from otn_enhanced.rom.lz5bg_codec import _parse_ntbg_sections, _map_to_palette, _build_objd_section

_NROWS = 16            # 4 bpp -> 16 palette rows
# NDS green chroma key used by the battle sprites: BGR555 green == 31, i.e. the
# MAXIMUM green. Written in bit-replicated display space (255), not in the older
# `<<3` space (248) -- under round-to-nearest 248 would quantise to 30, which is a
# different hardware colour and would break the key.
_TRANS_GREEN = (0, 255, 0)
_REFINE_ITERS = 5      # Lloyd passes over the tile->sub-palette assignment
_REFILL_ROWS = False   # A/B toggle: refill deduped rows to ncol distinct colours
_REFINE_TILES = True   # A/B toggle: Lloyd-refine the tile->sub-palette grouping


def _to5(v: int) -> int:
    """8-bit channel -> 5-bit, rounded to nearest (NOT truncated).

    ``v >> 3`` only ever rounds down, which both darkens every colour and makes
    two 8-bit colours <8 apart collapse onto the same hardware colour.
    """
    return (int(v) * 31 + 127) // 255


def _rgb_to_bgr555(r: int, g: int, b: int) -> int:
    return _to5(r) | (_to5(g) << 5) | (_to5(b) << 10)


def _snap_rgb(c) -> tuple[int, int, int]:
    """Snap one RGB colour onto the BGR555 lattice, as the DS would display it."""
    return tuple(int((q << 3) | (q >> 2)) for q in (_to5(c[0]), _to5(c[1]), _to5(c[2])))


def _snap_rgb_array(arr: np.ndarray) -> np.ndarray:
    """Vectorised ``_snap_rgb`` over an ``(..., 3)`` array of 8-bit channels.

    5->8 bit expansion replicates the top bits (``(q<<3)|(q>>2)``) rather than
    using a bare ``<<3``, so 31 maps to 255 and white stays white.
    """
    q = np.clip((arr.astype(int) * 31 + 127) // 255, 0, 31)
    return (q << 3) | (q >> 2)


def _kmeans(points: np.ndarray, k: int, iters: int = 24, seed: int = 0):
    """Cluster RGB points into k groups; returns (labels, centroids)."""
    rng = np.random.default_rng(seed)
    if len(points) <= k:
        pad = np.tile(points[-1], (k - len(points), 1)) if len(points) else np.zeros((k, 3))
        cent = np.vstack([points, pad]).astype(float)
        return np.arange(len(points)) % k, cent
    cent = points[rng.choice(len(points), size=k, replace=False)].astype(float)
    labels = np.zeros(len(points), dtype=int)
    for _ in range(iters):
        d = ((points[:, None, :] - cent[None, :, :]) ** 2).sum(2)
        labels = d.argmin(1)
        for j in range(k):
            m = labels == j
            if m.any():
                cent[j] = points[m].mean(0)
    return labels, cent


def _median_cut(pixels: np.ndarray, ncol: int):
    """Return up to ncol representative RGB colours via PIL median-cut."""
    if len(pixels) == 0:
        return [(0, 0, 0)]
    im = Image.new("RGB", (len(pixels), 1))
    im.putdata([tuple(int(c) for c in p) for p in pixels])
    q = im.quantize(colors=max(1, min(ncol, 256)),
                    method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()
    used = sorted(set(q.getdata()))
    return [(pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]) for i in used][:ncol]


def _lattice_palette(pixels: np.ndarray, ncol: int) -> list[tuple[int, int, int]]:
    """Pick exactly *ncol* DISTINCT BGR555-lattice colours representing *pixels*.

    Median-cut works in 8-bit RGB, but the DS only shows the 5-bit lattice, so the
    representatives are snapped before being accepted.  Snapping collapses colours
    that were within ~8 units of each other, and filling the freed slot with a
    duplicate would simply waste it -- which is what posterises smooth artwork.
    So on collapse we re-cut at a finer granularity and keep taking new distinct
    lattice colours until the row is genuinely full.  Coarser cuts are consumed
    first, so the most representative colours still win the early slots.
    """
    if len(pixels) == 0:
        return [(0, 0, 0)] * ncol
    out: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    reqs = (ncol, ncol * 2, ncol * 4, 256) if _REFILL_ROWS else (ncol,)
    for req in reqs:
        for c in _median_cut(pixels, req):
            sc = _snap_rgb(c)
            if sc not in seen:
                seen.add(sc)
                out.append(sc)
                if len(out) == ncol:
                    return out
    # fewer distinct lattice colours than slots: pad with duplicates (a smooth
    # region legitimately using <ncol colours must NOT be forced to invent more,
    # or nearest-neighbour scatters the extras as speckle across the gradient)
    while len(out) < ncol:
        out.append(out[-1] if out else (0, 0, 0))
    return out


def _ntbg_sections(buf: bytes) -> dict[bytes, tuple[int, int]]:
    off = struct.unpack_from("<H", buf, 12)[0]
    nsec = struct.unpack_from("<H", buf, 14)[0]
    secs, q = {}, off
    for _ in range(nsec):
        tag = buf[q:q + 4]
        sz = struct.unpack_from("<I", buf, q + 4)[0]
        secs[tag] = (q, sz)
        q += sz
    return secs


def _encode_bgdt_subpalette(img: Image.Image, w_tiles: int, h_tiles: int,
                            template_ntbg: bytes, *, transparent: bool,
                            fixed_size: int | None, dedup: bool | None = None,
                            usable_rows: int = _NROWS,
                            reserve_index0: bool | None = None) -> bytes:
    """Encode *img* as a 4 bpp BGDT NTBG with up to ``usable_rows`` sub-palettes.

    Reuses the template's 20-byte BGDT sub-header (and DFPL/PALT layout) so the
    output matches the engine's expected structure. ``fixed_size`` (when given)
    asserts the exact output length (used for the fixed-stride 64x64 atlas, which
    forbids dedup).

    ``reserve_index0`` keeps per-row palette index 0 out of the art, so each row
    carries 15 opaque colours at indices 1-15. On NDS 4 bpp BG tiles, **index 0 is
    transparent in hardware whatever colour the palette holds there** -- so any
    pixel written as 0 punches a hole in the picture. It defaults to
    ``transparent`` (which additionally writes the chroma key into that reserved
    slot), but the opaque 64x64 card art must reserve it too: measured on the
    stock atlas, 0 of 4306 arts use index 0 in a single pixel, and every row's
    index 0 holds BGR555 0 as a dead placeholder.

    ``usable_rows`` caps how many of the 16 hardware sub-palette banks the encoder
    may assign tiles to. The PALT section always holds all 16 banks (256 entries),
    but the card-art engine RESERVES the top bank (row 15) for the card-frame/UI
    palette in the zoom view -- every one of the 4306 stock arts uses only rows
    0-14, and a tile written into row 15 renders with whatever the engine left in
    that bank, i.e. blocky garbage colours in-game (invisible to a decoder that
    reads the PALT we wrote). So card art passes ``usable_rows=15``.
    """
    if dedup is None:
        dedup = fixed_size is None
    if reserve_index0 is None:
        reserve_index0 = transparent
    W, H = w_tiles * 8, h_tiles * 8
    rgba = img.convert("RGBA").resize((W, H), Image.LANCZOS)
    arr = np.asarray(rgba).astype(int)
    rgb, alpha = arr[:, :, :3], arr[:, :, 3]
    # Snap the source onto the BGR555 lattice up front: from here on the source
    # pixels, the palette candidates and the nearest-neighbour match targets all
    # live in the same colour space -- the one the hardware actually displays.
    rgb = _snap_rgb_array(rgb)
    ntiles = w_tiles * h_tiles
    cols_opaque = 15 if reserve_index0 else 16
    first = 1 if reserve_index0 else 0

    tiles_rgb, tiles_alpha, means = [], [], np.zeros((ntiles, 3))
    for ty in range(h_tiles):
        for tx in range(w_tiles):
            ti = ty * w_tiles + tx
            blk = rgb[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8, :].reshape(-1, 3)
            al = alpha[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8].reshape(-1)
            tiles_rgb.append(blk)
            tiles_alpha.append(al)
            op = blk[al >= 128]
            means[ti] = op.mean(0) if len(op) else np.zeros(3)

    # k-means on each tile's MEAN colour is only an initial guess: a tile straddling
    # two distinct regions has a mean that exists nowhere in the tile, so grouping by
    # it yields a palette fitted to neither half (the blocky 8x8 artefacts). Refine
    # below against the cost that actually matters -- per-tile quantisation error.
    labels, _ = _kmeans(means, usable_rows, seed=0)

    allpix = np.concatenate(tiles_rgb).astype(float)         # (ntiles*64, 3)
    allmask = np.concatenate(tiles_alpha) >= 128
    npx = allpix.shape[0] // ntiles

    def build_palettes(lbl: np.ndarray) -> dict[int, list[tuple[int, int, int]]]:
        out = {}
        for g in range(usable_rows):
            gpix = [tiles_rgb[t][tiles_alpha[t] >= 128]
                    for t in range(ntiles) if lbl[t] == g]
            gpix = (np.vstack(gpix) if gpix and sum(len(x) for x in gpix)
                    else np.zeros((1, 3), dtype=int))
            out[g] = _lattice_palette(gpix, cols_opaque)
        return out

    def tile_costs(gc: dict[int, list[tuple[int, int, int]]]) -> np.ndarray:
        """(ntiles, usable_rows) summed squared error of each tile under each palette."""
        cost = np.zeros((ntiles, usable_rows))
        for g in range(usable_rows):
            cols = np.asarray(gc[g], dtype=float)
            d = ((allpix[:, None, :] - cols[None, :, :]) ** 2).sum(2).min(1)
            cost[:, g] = np.where(allmask, d, 0.0).reshape(ntiles, npx).sum(1)
        return cost

    group_cols = build_palettes(labels)
    for _ in range(_REFINE_ITERS if _REFINE_TILES else 0):
        cost = tile_costs(group_cols)
        new_labels = cost.argmin(1)
        # A palette that wins no tiles would be dead weight; hand it the tile that
        # currently fits worst, so all usable rows stay meaningful (the tile-map at
        # the bottom writes a group index for every tile regardless).
        for g in range(usable_rows):
            if not (new_labels == g).any():
                worst = int(cost[np.arange(ntiles), new_labels].argmax())
                new_labels[worst] = g
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        group_cols = build_palettes(labels)

    # PALT always holds all 16 hardware banks (256 entries); rows >= usable_rows are
    # left black and reserved (the card-art engine uses row 15 for the frame/UI).
    palette = [(0, 0, 0)] * (_NROWS * 16)
    for g in range(usable_rows):
        if transparent:
            palette[g * 16] = _TRANS_GREEN
        for c in range(cols_opaque):
            palette[g * 16 + first + c] = group_cols[g][c]

    tile_idx = []
    for t in range(ntiles):
        cols = np.array(group_cols[int(labels[t])], dtype=float)
        d = ((tiles_rgb[t].astype(float)[:, None, :] - cols[None, :, :]) ** 2).sum(2)
        nearest = d.argmin(1) + first
        if transparent:
            nearest = np.where(tiles_alpha[t] < 128, 0, nearest)
        tile_idx.append(nearest.astype(int))

    secs = _ntbg_sections(template_ntbg)

    # PALT (256 colours)
    palt = bytearray(524)
    palt[0:4] = b"PALT"
    struct.pack_into("<I", palt, 4, 524)
    struct.pack_into("<I", palt, 8, 256)
    for i, (r, g, b) in enumerate(palette):
        struct.pack_into("<H", palt, 12 + i * 2, _rgb_to_bgr555(r, g, b))

    # BGDT: reuse 20-byte sub-header; new tile-map + (deduped) char data
    bgdt_off = secs[b"BGDT"][0]
    sub = bytearray(template_ntbg[bgdt_off + 8:bgdt_off + 8 + 20])

    def tile_bytes(t: int) -> bytes:
        idxs = tile_idx[t]
        tb = bytearray(32)
        for r in range(8):
            for c in range(4):
                tb[r * 4 + c] = (idxs[r * 8 + c * 2] & 0xF) | ((idxs[r * 8 + c * 2 + 1] & 0xF) << 4)
        return bytes(tb)

    uniq, chardata, char_of = {}, bytearray(), []
    for t in range(ntiles):
        tb = tile_bytes(t)
        if dedup:
            ci = uniq.get(tb)
            if ci is None:
                ci = len(uniq)
                uniq[tb] = ci
                chardata.extend(tb)
        else:
            ci = t
            chardata.extend(tb)
        char_of.append(ci)

    tilemap = bytearray(ntiles * 2)
    for t in range(ntiles):
        tilemap[t * 2:t * 2 + 2] = struct.pack("<H", (char_of[t] & 0x3FF) | ((int(labels[t]) & 0xF) << 12))
    struct.pack_into("<H", sub, 4, len(tilemap))
    struct.pack_into("<I", sub, 16, len(chardata))
    bgdt_body = bytes(sub) + bytes(tilemap) + bytes(chardata)
    bgdt = bytearray(8)
    bgdt[0:4] = b"BGDT"
    struct.pack_into("<I", bgdt, 4, 8 + len(bgdt_body))
    bgdt = bytes(bgdt) + bgdt_body

    # DFPL: rebuild per-tile only when its count matches the tile count
    dfpl_off, dfpl_sz = secs[b"DFPL"]
    dfpl = bytearray(template_ntbg[dfpl_off:dfpl_off + dfpl_sz])
    if struct.unpack_from("<I", dfpl, 8)[0] == ntiles:
        for t in range(ntiles):
            dfpl[12 + t] = int(labels[t]) & 0xFF

    body = bytes(palt) + bytes(bgdt) + bytes(dfpl)
    header = bytearray(16)
    header[0:4] = b"NTBG"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 8, 16 + len(body))
    struct.pack_into("<H", header, 12, 16)
    struct.pack_into("<H", header, 14, 3)
    out = bytes(header) + body
    if fixed_size is not None and len(out) != fixed_size:
        raise ValueError(f"encoded {len(out)} bytes != required {fixed_size}")
    return out


def encode_card_art_64x64(img: Image.Image, template_ntbg: bytes) -> bytes:
    """Encode 64x64 cropped artwork -> exactly 2820-byte NTBG (stored uncompressed).

    Two hardware/engine reservations, both measured against the stock atlas and
    both mandatory (see ``_encode_bgdt_subpalette``):

      * rows 0-14 only -- the zoom-view engine reserves sub-palette bank 15 for the
        card frame/UI, so tiles placed there render as blocky garbage in-game
        (0/4306 stock arts use row 15);
      * index 0 of every row is left unused -- it is transparent in hardware on a
        4 bpp BG tile, so art written there shows up as see-through holes
        (0/4306 stock arts, and 0 of 17.6M stock pixels, use index 0).

    That leaves 15 rows x 15 colours = 225 usable colours, exactly what stock uses.
    """
    return _encode_bgdt_subpalette(img, 8, 8, template_ntbg, transparent=False,
                                   fixed_size=2820, usable_rows=15,
                                   reserve_index0=True)


def encode_battle_sprite_256x96(img: Image.Image, template_ntbg: bytes) -> bytes:
    """Encode a 256x96 battle sprite -> NTBG bytes (caller LZ11-compresses)."""
    return _encode_bgdt_subpalette(img, 32, 12, template_ntbg, transparent=True, fixed_size=None)


def _break_index0_collision(img: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Nudge fully-opaque pixels that exactly equal ``palette[0]`` off that colour.

    ``_map_to_palette`` colour-keys any pixel matching ``palette[0]`` to index 0
    REGARDLESS of alpha (needed elsewhere for lossless decode->encode roundtrips),
    and index 0 always renders transparent on hardware. An opaque source pixel
    that happens to land exactly on the template's index-0 colour -- e.g. the
    synchro 32x32 template's white stat-box, which is literally
    ``shared_palette[0]`` -- would silently vanish in-game. Bumping the pixel by 1
    breaks the exact-match shortcut so it instead nearest-matches a real palette
    entry (the shared card-thumb palette carries an opaque duplicate of that
    colour at another index), invisible to the eye and correct on hardware.
    """
    if not palette:
        return img
    key = palette[0]
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a >= 128 and (r, g, b) == key:
                px[x, y] = (r, g if g < 255 else g - 1, b, a) if r == 255 else (r + 1, g, b, a)
    return img


def encode_card_thumb_32x32(img: Image.Image, template_ntbg: bytes,
                            shared_palette: list[tuple[int, int, int]]) -> bytes:
    """Encode a 32x32 full-card thumbnail -> NTBG bytes (caller LZ10-compresses).

    8 bpp OBJD using the atlas-wide *shared_palette* (index 0 transparent). The
    template's OBJD sub-header is reused verbatim via ``lz5bg_codec``.
    """
    img = img.convert("RGBA").resize((32, 32), Image.LANCZOS)
    img = _break_index0_collision(img, shared_palette)
    pix = _map_to_palette(img, shared_palette)
    objd = _build_objd_section(pix, 8, template_ntbg, _parse_ntbg_sections(template_ntbg)[b"OBJD"][0])
    header = bytearray(16)
    header[0:4] = b"NTBG"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 8, 16 + len(objd))
    struct.pack_into("<H", header, 12, 16)
    struct.pack_into("<H", header, 14, 1)
    return bytes(header) + objd

def encode_card_thumb_64x64(img: Image.Image, template_ntbg: bytes,
                            shared_palette: list[tuple[int, int, int]]) -> bytes:
    """Encode a 64x64 full-card thumbnail -> NTBG bytes (caller LZ10-compresses).

    8 bpp OBJD using the atlas-wide *shared_palette* (index 0 transparent). The
    template's OBJD sub-header is reused verbatim via ``lz5bg_codec``.
    """
    img = img.convert("RGBA").resize((64, 64), Image.LANCZOS)
    img = _break_index0_collision(img, shared_palette)
    pix = _map_to_palette(img, shared_palette)
    objd = _build_objd_section(pix, 8, template_ntbg, _parse_ntbg_sections(template_ntbg)[b"OBJD"][0])
    header = bytearray(16)
    header[0:4] = b"NTBG"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 8, 16 + len(objd))
    struct.pack_into("<H", header, 12, 16)
    struct.pack_into("<H", header, 14, 1)
    return bytes(header) + objd
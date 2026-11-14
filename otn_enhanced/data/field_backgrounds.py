"""Give every converted Field Spell its duel background.

bulk_card_props converts a card into a Field Spell (card_prop +
card_intid).  It then lands in the field zone correctly, and freezes on
activation: the background loader formats
``/Duel2D/field/duel_field_magic%04d_P.LZ5bg`` from the cid (ov3 ARM,
0x02170F50), and a converted card has no such file.  The name-table scan runs
off the end of field.pac's header, ``strlen`` (0x02016C84) takes a data abort,
and the ARM9 abort vector is ``b .`` -- which presents as a hang.  Every one of
the game's 65 stock Field Spells has a background; only Speed World 0xDAC does
not, and it never reaches this path.

So this module appends one file per entry in ``CARDS`` to
``Data_arc_pac/duel2d/field.pac``, each composed from that card's own 64x64
card art (card.pac file3) blown up over the 256x192 background canvas.  They
are soft -- 64x64 is the largest art the ROM has for these cards -- but each is
the card's own picture.

Three properties are measured from the STOCK backgrounds on every build and
enforced per card, because each was a real in-game failure first:

  * <= the stock tile budget (397), or the picture draws black then garbage;
  * inside the stock luminance envelope, or the duel field is unreadable;
  * the duel field's zone grid stamped back on, or there is no field at all.

To add a card: convert it in bulk_card_props (COPY_FROM
REFERENCE_FIELD_SPELL_CID), then add its cid here.  Nothing else is needed --
the archive is rebuilt from scratch and grows its own name/table chunks.

field.pac format (decoded 2026-09-07, validated against every .pac in the ROM):

  * Name area: N chunks of 0x200.  Each chunk starts ``00 00 <N>`` and then
    packs entries ``<u8 name_len><u8 xor_of_name_bytes><name>`` until the next
    entry would not fit.  The XOR checksum holds for all 65 field.pac names and
    for every name in all 25 other archives that parse this way.
  * File table: starts at ``N * 0x200``, also in 0x200 chunks, each with an
    8-byte head, then ``(u32 rel_addr, u32 size)`` pairs -- 63 per chunk.  A
    chunk that is full and continues is headed ``00 00 FF FF``; the LAST table
    chunk is headed ``00 00 <entry count>``.  Confirmed on 25 archives.
  * ``rel_addr`` is relative to the data base, which is the first 0x200
    boundary after the table.  Files are 0x200-aligned and stored in index
    order; file k carries name k.

Adding a 66th name needs a 5th name chunk, which pushes the table to 0xA00 and
the data base from 0xC00 to 0xE00, so the archive is rebuilt wholesale and every
rel_addr recomputed.  The new entry is APPENDED (index 65) so that no existing
file's index changes -- anything that looks a file up positionally rather than
by name keeps working.
"""
from __future__ import annotations

import functools
import io
import struct

import ndspy.rom
from PIL import Image

from otn_enhanced.rom.extract_card_images import ntbg_to_image
from otn_enhanced.rom.lz5bg_codec import decode_lz5bg, encode_lz5bg

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_test.nds"

FIELD_PAC = "Data_arc_pac/duel2d/field.pac"
CARD_PAC = "Data_arc_pac/card.pac"

BIN2_PAC = "Data_arc_pac/bin2.pac"

# Every card that bulk_card_props converts INTO a Field Spell needs a
# background here, or activating it is a hard freeze (see the module docstring).
#
# A cid whose background already exists is REPLACED in place rather than
# appended -- that is the case for a donor that was already a Field Spell, where
# the stock background still shows the DONOR's picture.  Colosseum 0x1C8B is the
# donor for The Gates of Dark World, and card_art already swaps its 64x64
# artwork, so regenerating its background here picks the new art up for free.
# ⚠️ That is why this step MUST run after "Card art" in the chain (41 < 45).
CARDS: dict[int, str] = {
    0x12BE: "Toon World",
    0x1C8B: "The Gates of Dark World (donor Colosseum)",
    0x10F5: "The Seal of Orichalcos",
    0x1346: "Noble Arms Museum",
    0x10F3: "Domain of the True Monarchs",
}

TEMPLATE_INDEX = 61           # Forest 0x10F0 -- supplies bpp, sections and the gap mask
INTID_BASE_CID = 0x0D48       # card_intid.bin is indexed by (cid - 0xD48)


def field_name(cid: int) -> bytes:
    """The filename ov3 formats for a Field Spell's background.

    `/Duel2D/field/duel_field_magic%04d_P.LZ5bg` at 0x0229207C, formatted with
    the cid, looked up case-insensitively against field.pac's name table.
    """
    return b"duel_field_magic%04d_p.lz5bg" % cid

# card.pac file3 geometry (shared with card_art)
H_F3START = 0x59
CARD_DATA_BASE = 0x200
ART64_STRIDE = 2820

GAP = (248, 0, 248)           # palette index 0 of every field background
CHUNK = 0x200
TBL_PER_CHUNK = (CHUNK - 8) // 8


def _xor(name: bytes) -> int:
    return functools.reduce(lambda a, c: a ^ c, name, 0)


def char_tiles(blob: bytes) -> int:
    """Number of 8x8 tiles in a background's BGDT character data.

    ⚠️ CORRECTION.  An earlier version of this note called 397 "a FIXED
    character-data budget" the game enforces.  That is NOT proven.  397 is a
    STRUCTURAL CEILING of the canvas: of the 768 8x8 cells in 256x192, **372 are
    entirely transparent** and collapse to one shared tile, leaving 396 that can
    differ -- so 396 + 1 = 397 is simply what an image needs when every non-gap
    cell is unique.  That is why five stock backgrounds sit exactly on it, and
    why two of ours do too.

    What IS established: an un-deduplicated 768-tile encode drew black and
    garbage in game (2026-09-07), and de-duplicated output at 388..397 tiles
    works (Pyramid of Light, confirmed by the user).  The real limit is
    somewhere in 398..768 and has never been measured.  This check therefore
    means "no worse than the busiest stock background", which is a sound bound
    to hold to, not a measured hardware cap.
    """
    from otn_enhanced.rom.lz_compression import decompress
    from otn_enhanced.rom.lz5bg_codec import _parse_ntbg_sections

    d = decompress(blob)
    off = _parse_ntbg_sections(d)[b"BGDT"][0]
    return struct.unpack_from("<I", d, off + 24)[0] // 64


def stock_tile_budget(names: list[bytes], payloads: list[bytes]) -> int:
    return max(char_tiles(p) for n, p in zip(names, payloads) if n != b"fl_icon.lz5bg")


def parse_field_pac(blob: bytes) -> tuple[list[bytes], list[bytes]]:
    """Return (names, file_payloads), index-aligned."""
    nchunk = blob[2]
    names: list[bytes] = []
    for ci in range(nchunk):
        base = ci * CHUNK
        assert blob[base:base + 2] == b"\x00\x00" and blob[base + 2] == nchunk, \
            f"chunk {ci} head is not 00 00 {nchunk:02X}"
        i = base + 3
        while i + 2 < base + CHUNK:
            ln = blob[i]
            if ln == 0:
                break
            nm = blob[i + 2:i + 2 + ln]
            assert _xor(nm) == blob[i + 1], f"checksum mismatch on {nm!r}"
            names.append(nm)
            i += 2 + ln

    tbl = nchunk * CHUNK
    entries: list[tuple[int, int]] = []
    off = tbl
    while True:
        head = blob[off:off + 4]
        last = head[2:4] != b"\xff\xff"
        count = head[2] if last else TBL_PER_CHUNK
        for k in range(count):
            entries.append(struct.unpack_from("<II", blob, off + 8 + 8 * k))
        off += CHUNK
        if last:
            break
    assert len(entries) == len(names), f"{len(entries)} table entries vs {len(names)} names"

    data_base = off
    return names, [blob[data_base + a:data_base + a + s] for a, s in entries]


def build_field_pac(names: list[bytes], payloads: list[bytes]) -> bytes:
    """Rebuild field.pac from scratch, choosing the chunk counts that fit."""
    assert len(names) == len(payloads)

    # how many 0x200 name chunks do these names need?
    def pack_names(nchunk: int) -> bytes | None:
        chunks = [bytearray(b"\x00\x00" + bytes([nchunk])) for _ in range(nchunk)]
        ci = 0
        for nm in names:
            entry = bytes([len(nm), _xor(nm)]) + nm
            while ci < nchunk and len(chunks[ci]) + len(entry) > CHUNK:
                ci += 1
            if ci == nchunk:
                return None
            chunks[ci] += entry
        return b"".join(bytes(c).ljust(CHUNK, b"\x00") for c in chunks)

    nchunk = 1
    while True:
        header = pack_names(nchunk)
        if header is not None:
            break
        nchunk += 1

    ntbl = (len(payloads) + TBL_PER_CHUNK - 1) // TBL_PER_CHUNK
    data_base = (nchunk + ntbl) * CHUNK

    # lay the payloads out 0x200-aligned, in index order
    entries: list[tuple[int, int]] = []
    cursor = 0
    for p in payloads:
        entries.append((cursor, len(p)))
        cursor += (len(p) + CHUNK - 1) & ~(CHUNK - 1)

    table = bytearray()
    for c in range(ntbl):
        part = entries[c * TBL_PER_CHUNK:(c + 1) * TBL_PER_CHUNK]
        last = c == ntbl - 1
        table += b"\x00\x00" + (bytes([len(part), 0]) if last else b"\xff\xff") + b"\x00" * 4
        for a, s in part:
            table += struct.pack("<II", a, s)
        table = table.ljust((c + 1) * CHUNK, b"\x00")

    out = bytearray(header + bytes(table))
    assert len(out) == data_base
    for (a, s), p in zip(entries, payloads):
        out = out.ljust(data_base + a, b"\x00")
        out[data_base + a:data_base + a + s] = p
    return bytes(out.ljust(data_base + cursor, b"\x00"))


def luminance_stats(img: Image.Image) -> tuple[float, float]:
    """(mean luminance, fraction brighter than 200) over the opaque pixels."""
    lum = [0.299 * r + 0.587 * g + 0.114 * b
           for (r, g, b) in img.convert("RGB").get_flattened_data() if (r, g, b) != GAP]
    return sum(lum) / len(lum), sum(1 for v in lum if v > 200) / len(lum)


def stock_luminance_envelope(names: list[bytes], payloads: list[bytes]) -> tuple[float, float]:
    """(brightest mean-luminance, worst bright-fraction) across the stock backgrounds.

    The target is the BRIGHTEST stock background, not the median.  Toning to the
    median (92) was a belt-and-braces reaction to the duel field being invisible,
    but that turned out to be the missing zone grid, not the brightness -- so
    once derive_field_furniture() puts the grid back, the art can sit at the top
    of the range the game's own backgrounds occupy (42..137) rather than the
    middle of it.  The bright-fraction cap still binds independently.
    """
    stats = [luminance_stats(decode_lz5bg(p))
             for n, p in zip(names, payloads) if n != b"fl_icon.lz5bg"]
    return max(s[0] for s in stats), max(s[1] for s in stats)


def brightest_legal_scale(compose, worst_bright: float, max_mean: float) -> float:
    """Largest linear scale whose COMPOSED background still sits inside stock.

    Maximising brightness is a search over the finished picture, not the raw art:
    the zone grid is stamped after toning and is itself mid-bright, so scaling
    the art to a target mean overshoots once the grid lands (137 -> 145).

    The binding constraint is the bright-pixel fraction, not the mean.  The
    pyramid face is blown out to near-white, so a scale that puts the MEAN at
    the brightest stock background still leaves 38.6% of pixels above 200
    against a stock worst of 13.9%.  Solve on the fraction and the mean follows.
    """
    lo, hi = 0.05, 1.0                       # lo must be feasible, hi may not be
    for _ in range(14):
        k = (lo + hi) / 2
        mean, bright = luminance_stats(compose(k))
        if bright <= worst_bright and mean <= max_mean:
            lo = k
        else:
            hi = k
    return lo


def tone_to_stock(img: Image.Image, target_mean: float) -> Image.Image:
    """Scale *img* down until its mean luminance matches the stock median.

    The duel field's mat and zone outlines are drawn to read against a mid-dark
    background.  Every stock field background has a mean luminance of 42..137
    (median 92) with at most 13.9% of pixels above 200; Pyramid of Light's card
    art, blown up, came out at 159 with 45.8% above 200 and the user could not
    see the duel field at all.

    A LINEAR scale, not gamma: the pyramid face is blown out to near-white, and
    255 ** g is 255 for every gamma, so a gamma curve cannot pull the highlights
    down at all -- it bottomed out at mean 113 with 27.8% still above 200.
    """
    lo, hi = 0.05, 1.0
    for _ in range(24):
        k = (lo + hi) / 2
        lut = [min(255, round(v * k)) for v in range(256)]
        if luminance_stats(img.point(lut * 3))[0] > target_mean:
            hi = k
        else:
            lo = k
    k = (lo + hi) / 2
    return img.point([min(255, round(v * k)) for v in range(256)] * 3)


# A pixel counts as field furniture when its colour barely moves across the 64
# stock backgrounds.  The split is sharply bimodal -- 5299 pixels at sd<5 rising
# only to 6474 by sd<30 -- so anywhere on that plateau gives the same mask.
FURNITURE_SD = 20.0

# The zone bezels have a LIT edge -- a bright gold/white line along the bottom
# and left of every zone -- and it does NOT survive the variance test, because
# its colour follows the scene (gold in Forest, blue elsewhere).  Its spread
# across backgrounds is 51.5, no better than the 49.8 of open scenery, so no sd
# threshold can separate it: the curve jumps straight from 6796 pixels at sd<40
# to 23615 at sd<60.  What is fixed is the GEOMETRY, so the highlights are
# recovered structurally instead -- grow the frame mask by BEZEL_DILATE and keep
# only the pixels that are genuinely bright in the median background.
#
# ⚠️ BEZEL_LUMA is tuned by eye against the stock frames, not derived: the frame
# median luminance (72) and the scenery median (70) are too close to separate
# anything, so there is no statistic to solve for.  140 is roughly double both
# and cleanly isolates the highlights; 120 and 160 look near-identical.
BEZEL_DILATE = 2
BEZEL_LUMA = 140.0


def derive_field_furniture(names: list[bytes], payloads: list[bytes]):
    """Return (mask, rgb) for the duel field's zone grid, from the stock art.

    THE ZONE GRID IS PAINTED INTO EVERY BACKGROUND -- it is not a separate
    overlay asset and it is not part of the transparent mask.  Replacing all of
    a background's opaque pixels with new art therefore deletes the field, which
    is what happened here: the user reported "I cannot see the duel field now".

    It cannot be recovered by intersecting the backgrounds either -- each one
    tints its own frame, so only 879 opaque pixels are byte-identical across all
    64.  What does isolate it is the per-pixel spread: the furniture is
    near-constant, the scenery is not.  ~24% of the opaque area sits under
    FURNITURE_SD and renders as exactly the 5x2 zone grid on both screens.
    """
    import numpy as np

    stack = np.stack([
        np.array(decode_lz5bg(p).convert("RGB"), np.float32)
        for n, p in zip(names, payloads) if n != b"fl_icon.lz5bg"
    ])
    gap = (stack[0] == np.array(GAP, np.float32)).all(-1)
    opaque = ~gap
    spread = stack.std(axis=0).mean(axis=-1)
    mask = opaque & (spread < FURNITURE_SD)

    median = np.median(stack, axis=0)

    # add the lit bezel edges back: grow the frame, keep only the bright ring
    grown = mask.copy()
    for _ in range(BEZEL_DILATE):
        nxt = grown.copy()
        nxt[1:, :] |= grown[:-1, :]
        nxt[:-1, :] |= grown[1:, :]
        nxt[:, 1:] |= grown[:, :-1]
        nxt[:, :-1] |= grown[:, 1:]
        grown = nxt
    luma = (0.299 * median[..., 0] + 0.587 * median[..., 1] + 0.114 * median[..., 2])
    mask |= (grown & opaque & ~mask & (luma > BEZEL_LUMA))

    return mask, median.round().astype(np.uint8)


def art_index(rom: ndspy.rom.NintendoDSRom, cid: int) -> int:
    """card.pac 64x64 atlas index for *cid*, read from card_intid.bin.

    The atlas is indexed by the card_prop RECORD index counting the 8-byte
    header as record 0 -- i.e. one MORE than the header-relative index, which is
    exactly what card_intid's low 14 bits hold (carddata.card_intid_field_and_
    monster_bits).  Reading it from there rather than recomputing it is what
    stops the off-by-one that first handed us a completely different card's art.
    """
    from otn_enhanced.rom.pac import parse_pac

    blob = bytes(rom.files[rom.filenames.idOf(BIN2_PAC)])
    archive = parse_pac(blob, BIN2_PAC)
    f = next(x for x in archive.files if x.get_clean_name().lower() == "card_intid.bin")
    intid = blob[f.address:f.address + f.size]
    return struct.unpack_from("<H", intid, (cid - INTID_BASE_CID) * 2)[0] & 0x3FFF


def card_canvas(rom: ndspy.rom.NintendoDSRom, cid: int, gap_mask) -> Image.Image:
    """A card's own 64x64 artwork, fitted to the VISIBLE part of the canvas.

    Not a crop, and not a stretch across the full 256x192 either.  Only about
    half the canvas is ever on screen: the opaque region is x 40..215, y 16..175,
    and it is split into two bands (y 16..87 and y 104..175) by a 16-row dead
    strip -- the gap between the DS's two screens.  Stretching art over the whole
    canvas therefore throws the picture's centre into that dead strip and its
    left and right edges off-screen entirely, which is why Toon World and Vylon
    Element still "seemed cropped" after the crop was removed: their subjects are
    centred, unlike Pyramid of Light's full-width triangle.

    Fitting to the opaque bounding box instead loses nothing but the screen gap,
    and 176x160 from a 64x64 source is only a 1.1:1 distortion.  It also matches
    what the stock backgrounds do -- one continuous scene running across both
    screens, rather than the same picture repeated on each.

    The geometry is measured from the transparent mask, never hardcoded.
    """
    import numpy as np
    card = bytes(rom.files[rom.filenames.idOf(CARD_PAC)])
    base = CARD_DATA_BASE + struct.unpack_from("<I", card, H_F3START)[0]
    off = base + art_index(rom, cid) * ART64_STRIDE
    assert struct.unpack_from("<I", card, off + 8)[0] == ART64_STRIDE, "unexpected 64x64 stride"
    r = ntbg_to_image(card[off:off + ART64_STRIDE])
    art = (r[0] if isinstance(r, tuple) else r).convert("RGB")
    assert art.size == (64, 64), f"card art is {art.size}, expected 64x64"

    ys, xs = np.where(~gap_mask)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    canvas = Image.new("RGB", (256, 192), (0, 0, 0))
    canvas.paste(art.resize((x1 - x0 + 1, y1 - y0 + 1), Image.LANCZOS), (x0, y0))
    return canvas


def compose_background(art: Image.Image, gap_mask, scale: float = 1.0,
                       furniture: tuple | None = None) -> Image.Image:
    """Tone the scenery, stamp the duel field's zone grid, punch the gaps."""
    import numpy as np

    canvas = art.point([min(255, round(v * scale)) for v in range(256)] * 3)
    arr = np.array(canvas, np.uint8)
    if furniture is not None:
        mask, rgb = furniture
        arr[mask] = rgb[mask]
    arr[gap_mask] = GAP
    return Image.fromarray(arr)


def gap_mask_of(template: bytes):
    import numpy as np

    return (np.array(decode_lz5bg(template).convert("RGB"), np.uint8) ==
            np.array(GAP, np.uint8)).all(-1)


def main(src: str = SRC, out: str = OUT, *, cids=None) -> None:
    """Build every background in CARDS, or only *cids*."""
    if cids is not None and not set(cids) <= set(CARDS):
        raise ValueError(f"cids not in CARDS: {sorted(map(hex, set(cids) - set(CARDS)))}")
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    fid = rom.filenames.idOf(FIELD_PAC)
    names, payloads = parse_field_pac(bytes(rom.files[fid]))
    print(f"field.pac: {len(names)} files")

    # Rebuild every configured card on every run: a cid already in the archive is
    # a donor whose stock background shows the DONOR's art, and must be replaced,
    # not skipped.  Regenerating is idempotent, so this is also safe to re-run.
    todo = [(c, n) for c, n in CARDS.items() if cids is None or c in cids]

    # measured once from the STOCK art, then shared by every card
    template = payloads[TEMPLATE_INDEX]
    max_mean, worst_bright = stock_luminance_envelope(names, payloads)
    budget = stock_tile_budget(names, payloads)
    furniture = derive_field_furniture(names, payloads)
    gaps = gap_mask_of(template)
    print(f"  field furniture: {int(furniture[0].sum())} pixels restored from the stock grid")
    print(f"  envelope: mean <= {max_mean:.0f}, <= {worst_bright:.1%} above 200, "
          f"<= {budget} tiles")

    new_names, new_payloads = [], []
    for cid, label in todo:
        name = field_name(cid)
        art = card_canvas(rom, cid, gaps)

        def _compose(k, art=art):
            return compose_background(art, gaps, scale=k, furniture=furniture)

        scale = brightest_legal_scale(_compose, worst_bright, max_mean)
        canvas = _compose(scale)
        mean, bright = luminance_stats(canvas)
        buf = io.BytesIO()
        canvas.save(buf, "PNG")
        blob = encode_lz5bg(buf.getvalue(), template, rebuild_palette=True)
        tiles = char_tiles(blob)
        print(f"  {label} 0x{cid:04X} -> {name.decode()} (xor 0x{_xor(name):02X}): "
              f"scale {scale:.3f}, mean {mean:.0f}, {bright:.1%} above 200, "
              f"{tiles} tiles, {len(blob)} bytes")

        if bright > worst_bright or mean > max_mean:
            raise SystemExit(
                f"{label}: art is outside the stock envelope (mean {mean:.0f}, "
                f"{bright:.1%} above 200); the duel field would be hard to read")
        if tiles > budget:
            raise SystemExit(
                f"{label}: character data is {tiles} tiles, over the stock budget "
                f"of {budget}; the background would draw black/garbage in game")
        if name in names:
            # a donor that was already a Field Spell: overwrite its payload and
            # keep its index, so nothing that looks a file up positionally moves
            payloads[names.index(name)] = blob
            print(f"      replaced in place at index {names.index(name)}")
        else:
            new_names.append(name)
            new_payloads.append(blob)

    new = build_field_pac(names + new_names, payloads + new_payloads)
    print(f"  field.pac {len(bytes(rom.files[fid]))} -> {len(new)} bytes "
          f"({len(names)} -> {len(names) + len(new_names)} files)")
    rom.files[fid] = bytearray(new)
    rom.saveToFile(out)
    print(f"  wrote {out}")


def verify(out: str = OUT) -> bool:
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    names, payloads = parse_field_pac(bytes(rom.files[rom.filenames.idOf(FIELD_PAC)]))
    ok = True

    added = {field_name(cid) for cid in CARDS}
    missing = [f"{CARDS[cid]} ({field_name(cid).decode()})"
               for cid in CARDS if field_name(cid) not in names]
    if missing:
        print(f"FAIL missing background(s): {', '.join(missing)}")
        return False
    print(f"PASS all {len(CARDS)} card backgrounds present in {len(names)} files: "
          + ", ".join(f"{CARDS[cid]}@{names.index(field_name(cid))}" for cid in CARDS))

    budget = max(char_tiles(p) for n, p in zip(names, payloads)
                 if n != b"fl_icon.lz5bg" and n not in added)
    for cid in CARDS:
        tiles = char_tiles(payloads[names.index(field_name(cid))])
        if tiles > budget:
            print(f"FAIL {CARDS[cid]}: {tiles} tiles > stock budget {budget}")
            ok = False
        else:
            print(f"PASS {CARDS[cid]}: {tiles} tiles (stock budget {budget})")

    # every file, old and new, must still decode to a 256x192 image
    for k, p in enumerate(payloads):
        if names[k] == b"fl_icon.lz5bg":
            continue
        try:
            size = decode_lz5bg(p).size
        except Exception as exc:
            print(f"FAIL file {k} ({names[k].decode()}) will not decode: {exc}")
            ok = False
            continue
        if size != (256, 192):
            print(f"FAIL file {k} ({names[k].decode()}) is {size}")
            ok = False
    if ok:
        print(f"PASS all {len(payloads)} files decode")

    # the pre-existing files must be byte-identical and keep their index
    stock = ndspy.rom.NintendoDSRom.fromFile(SRC)
    s_names, s_payloads = parse_field_pac(bytes(stock.files[stock.filenames.idOf(FIELD_PAC)]))
    if names[:len(s_names)] != s_names:
        print("FAIL existing names moved or changed")
        return False

    # a configured cid that was ALREADY in the archive is a donor whose background
    # we deliberately replace; every other stock file must be untouched
    replaced = {k for k in range(len(s_names)) if s_names[k] in added}
    collateral = [k for k in range(len(s_payloads))
                  if k not in replaced and payloads[k] != s_payloads[k]]
    if collateral:
        print(f"FAIL stock payloads changed at {collateral[:5]} (not configured for replacement)")
        ok = False
    else:
        print(f"PASS {len(s_names) - len(replaced)} untouched stock files are byte-identical "
              f"and still at their old index")
    for k in sorted(replaced):
        if payloads[k] == s_payloads[k]:
            print(f"FAIL {s_names[k].decode()} (index {k}) was NOT replaced -- "
                  "it still holds the donor's background")
            ok = False
        else:
            print(f"PASS {s_names[k].decode()} (index {k}) replaced in place, "
                  f"{len(s_payloads[k])} -> {len(payloads[k])} bytes")
    return ok


if __name__ == "__main__":
    main()
    verify()

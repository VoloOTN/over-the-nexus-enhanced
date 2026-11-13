"""Extract Yu-Gi-Oh! WC2011 (Over the Nexus) card/monster assets from rom.nds.

Three asset families are exported:

  * Card artwork      -> Data_arc_pac/card.pac
        Packed LZ-compressed NITRO "NTBG" images, two atlases:
        24x32 thumbnails and 64x64 full artwork (indexed by internal card id).
        PNGs are named ``{konami_id:04X}_{card_name}.png`` (see --no-names).

  * Battle/field sprites -> Data_arc_pac/duel2d/BattleMonster{1,2,3}.pac
        One LZ-NTBG image per (monster-graphic-id, facing).  ``_l`` = player
        side, ``_r`` = opponent side.  -> PNG.

  * 3D monster models -> Data_arc_pac/monmodel.pac
        146 LZ11-compressed NARC archives, each holding a monster's geometry +
        animations as proprietary "YI**" container sub-files (YIMD model,
        YICA/YIMA/YITA/YIVA animations -- NOT standard NSBMD, version "2211").
        Sub-files are exported verbatim as ``.bin`` (openable for further RE,
        not directly a glTF/OBJ without decoding the custom format).

Usage:
    python -m otn_enhanced.rom.extract_card_images \
        --rom data/over_the_nexus/working/rom.nds \
        --out data/over_the_nexus/working/extracted_png \
        --models-out data/over_the_nexus/working/extracted_models
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys

import ndspy.rom
import ndspy.narc

# Allow running both as a module and as a script.
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from lz5bg_codec import _parse_ntbg_sections, _parse_palette, _render_bgdt, _render_objd  # noqa: E402
from pac import parse_format_v1  # noqa: E402

MAX_IMG_BYTES = 0x40000  # NTBG card/sprite images are well under 256 KB


# ---------------------------------------------------------------------------
# Length-aware LZ10/LZ11 decoder (returns consumed bytes; guards bogus sizes)
# ---------------------------------------------------------------------------

def lz_decode(data: bytes, p: int, max_size: int = MAX_IMG_BYTES):
    """Decode an LZ10/LZ11 stream at ``data[p]``; return ``(out, consumed)``.

    Raises ``ValueError`` quickly if the header is not LZ or claims an
    implausibly large output (used to reject non-image data while scanning).
    """
    start = p
    typ = data[p]
    if typ not in (0x10, 0x11):
        raise ValueError("not LZ")
    size = int.from_bytes(data[p + 1:p + 4], "little")
    p += 4
    if size == 0:
        size = int.from_bytes(data[p:p + 4], "little")
        p += 4
    if size == 0 or size > max_size:
        raise ValueError("implausible size")
    out = bytearray()
    n = len(data)
    while len(out) < size:
        if p >= n:
            raise ValueError("truncated")
        flags = data[p]; p += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                if typ == 0x11:
                    b0 = data[p]; b1 = data[p + 1]
                    ind = b0 >> 4
                    if ind == 0:
                        length = (((b0 & 0xF) << 4) | (b1 >> 4)) + 0x11
                        disp = ((b1 & 0xF) << 8) | data[p + 2]
                        p += 3
                    elif ind == 1:
                        b2 = data[p + 2]
                        length = (((b0 & 0xF) << 12) | (b1 << 4) | (b2 >> 4)) + 0x111
                        disp = ((b2 & 0xF) << 8) | data[p + 3]
                        p += 4
                    else:
                        length = ind + 1
                        disp = ((b0 & 0xF) << 8) | b1
                        p += 2
                else:
                    b0 = data[p]; b1 = data[p + 1]
                    length = (b0 >> 4) + 3
                    disp = ((b0 & 0xF) << 8) | b1
                    p += 2
                src = len(out) - disp - 1
                if src < 0:
                    raise ValueError("bad backref")
                for _ in range(length):
                    out.append(out[src]); src += 1
            else:
                out.append(data[p]); p += 1
    return bytes(out), p - start


# ---------------------------------------------------------------------------
# NTBG -> PIL image (operates on already-decompressed bytes)
# ---------------------------------------------------------------------------

def ntbg_to_image(buf: bytes, fallback_palette=None):
    """Render an NTBG buffer to a PIL image.

    Some atlases (e.g. card.pac) store the palette only in the *first* image
    and leave the rest palette-less; pass the previously parsed palette via
    ``fallback_palette`` so those still render.
    """
    if buf[:4] != b"NTBG":
        raise ValueError("not NTBG")
    sections = _parse_ntbg_sections(buf)
    if b"PALT" in sections:
        palette = _parse_palette(buf, sections[b"PALT"][0])
    elif fallback_palette is not None:
        palette = fallback_palette
    else:
        raise ValueError("no PALT")
    if b"BGDT" in sections:
        return _render_bgdt(buf, palette, sections[b"BGDT"][0]), palette
    if b"OBJD" in sections:
        off, sz = sections[b"OBJD"]
        return _render_objd(buf, palette, off, sz), palette
    raise ValueError("no BGDT/OBJD")


# ---------------------------------------------------------------------------
# ROM helpers
# ---------------------------------------------------------------------------

def walk(folder, prefix=""):
    for i, name in enumerate(folder.files):
        yield (prefix + name, folder.firstID + i)
    for sub_name, sub in folder.folders:
        yield from walk(sub, prefix + sub_name + "/")


# ---------------------------------------------------------------------------
# Card name / konami-id mapping (card-art index -> (cid, name))
# ---------------------------------------------------------------------------

_INVALID_FN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_name(name: str, maxlen: int = 60) -> str:
    """Make a card name safe for a filename (Windows-compatible)."""
    name = _INVALID_FN.sub("", name).strip()
    name = re.sub(r"\s+", "_", name)
    name = name.strip("._")  # no leading/trailing dots or underscores
    return name[:maxlen]


def load_card_name_map(rom, p2id) -> dict | None:
    """Return ``{card_art_index: (cid, name)}`` from bin2.pac.

    The card-art atlases are indexed 1:1 with ``card_prop.bin`` (entry 0 is a
    blank/dummy).  For index ``i``:
      * ``cid``  = low-14 bits of ``card_prop`` entry ``i``;
      * ``name`` = the English name at ``card_name_e[ card_indx_e[i*8] ]``.
    Returns ``None`` if bin2.pac cannot be parsed (extraction then falls back
    to plain numeric filenames).
    """
    try:
        bin2 = bytes(rom.files[p2id["Data_arc_pac/bin2.pac"]])
        arc = parse_format_v1(bin2, "bin2.pac")
        files = {f.name: f for f in arc.files}

        def blob(fname: bytes) -> bytes:
            f = files[fname]
            return bin2[f.address:f.address + f.size]

        prop = blob(b"card_prop.bin")
        names = blob(b"card_name_e.bin")
        indx = blob(b"card_indx_e.bin")
    except Exception:
        return None

    def name_at(noff: int) -> str:
        end = names.find(b"\x00", noff)
        raw = names[noff:end if end >= 0 else None]
        try:
            return raw.decode("shift-jis")
        except UnicodeDecodeError:
            return raw.decode("latin-1", "replace")

    out: dict[int, tuple[int, str]] = {}
    n = len(prop) // 8
    for i in range(n):
        cid = struct.unpack_from("<Q", prop, i * 8)[0] & 0x3FFF
        name = ""
        rec = i * 8
        if rec + 4 <= len(indx):
            noff = struct.unpack_from("<I", indx, rec)[0]
            if noff < len(names):
                name = name_at(noff)
        out[i] = (cid, name)
    return out


def _card_art_filename(idx: int, name_map: dict | None) -> str:
    """Build a card-art PNG stem for atlas index ``idx``."""
    if name_map and idx in name_map:
        cid, name = name_map[idx]
        safe = sanitize_name(name)
        if safe:
            return f"{cid:04X}_{safe}"
        return f"{cid:04X}"
    return f"{idx:04d}"


# ---------------------------------------------------------------------------
# Graphics-PAC (per-file) parser: BattleMonster*, pack, etc.
# ---------------------------------------------------------------------------

PAC_BLOCK = 0x200
PAC_CHUNK = 63          # offset-table entries per 0x200 chunk


def graphics_pac_layout(data: bytes):
    """Exact layout of a per-file graphics PAC -> ``[(name, abs_offset, size, slot)]``.

    * Name header: ``data[2]`` = number of 0x200 name blocks (0 = one short block
      whose end is the u16 at ``data[0]``). Each block holds records
      ``{u8 len, u8 xor-hash, name[len]}`` from block+3 until a 0 length byte.
    * Offset table at ``names_end``: chunks of up to 63 entries, each chunk
      ``{u16 0, u16 count (0xFFFF = more chunks follow), u32 0}`` + ``{u32 rel_off,
      u32 size}`` x n, one chunk per 0x200 block.
    * Data starts at the first 0x200 boundary after the table; ``rel_off`` is
      relative to it. ``slot`` = absolute file offset of the entry's 8-byte record.

    The previous heuristic parser searched for the first ``FF FF`` (the count
    of the first chunk), started one record late, and paired every name with the
    NEXT entry's data (notes/battle-sprite-findings.md).
    """
    nblocks = data[2]
    names_end = struct.unpack_from("<H", data, 0)[0] if nblocks == 0 else nblocks * PAC_BLOCK
    names = []
    for b in range(max(1, nblocks)):
        p = b * PAC_BLOCK + 3
        while p < min(names_end, (b + 1) * PAC_BLOCK) and data[p] != 0:
            n = data[p]
            names.append(data[p + 2:p + 2 + n].decode("latin1"))
            p += 2 + n
    n = len(names)
    slots = [names_end + (i // PAC_CHUNK) * PAC_BLOCK + 8 + (i % PAC_CHUNK) * 8 for i in range(n)]
    last = slots[-1] + 8 if n else names_end
    base = (last + PAC_BLOCK - 1) & ~(PAC_BLOCK - 1)
    out = []
    for nm, slot in zip(names, slots):
        rel, size = struct.unpack_from("<II", data, slot)
        out.append((nm, base + rel, size, slot))
    return out


def parse_graphics_pac(data: bytes):
    """Return ordered ``[(name, offset, size)]`` for a per-file graphics PAC."""
    return [(nm, off, size) for nm, off, size, _slot in graphics_pac_layout(data)]


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def extract_battle(data: bytes, label: str, out_dir: str) -> int:
    files = parse_graphics_pac(data)
    os.makedirs(out_dir, exist_ok=True)
    good = bad = 0
    for name, off, size in files:
        stem = name.rsplit(".", 1)[0]
        try:
            buf, _ = lz_decode(data, off)
            img, _pal = ntbg_to_image(buf)
            img.save(os.path.join(out_dir, stem + ".png"))
            good += 1
        except Exception:
            bad += 1
    print(f"  {label}: {good} PNG written, {bad} failed")
    return good


def extract_card_art(data: bytes, out_root: str, name_map: dict | None = None) -> int:
    """Extract both card-art atlases from card.pac.

    card.pac holds three internal files:
      1. ``card_5bg24x32.bin`` – 4306 LZ10-compressed NTBG thumbnails packed
         back-to-back from 0x200; only the first carries the shared palette.
      2. ``card_5bg24x32_idx.bin`` – u32 offset table (skipped).
      3. ``card_5bg64x64.bin`` – 4306 *uncompressed* NTBG full-art images, each
         self-contained (own PALT), walked via the NTBG total-size field.

    When ``name_map`` is supplied (index -> (cid, name)), files are named
    ``{cid:04X}_{name}.png``; otherwise ``{index:04d}.png``.
    """
    n = len(data)
    total = 0

    # --- file 1: LZ-compressed thumbnail atlas ---------------------------
    sub32 = os.path.join(out_root, "card_art_32x32")
    os.makedirs(sub32, exist_ok=True)
    p = 0x200
    palette = None
    idx = 0
    while p < n and data[p] in (0x10, 0x11):
        try:
            buf, consumed = lz_decode(data, p)
        except Exception:
            break
        if buf[:4] != b"NTBG":
            break
        try:
            img, pal = ntbg_to_image(buf, fallback_palette=palette)
            if pal is not None and palette is None:
                palette = pal
            img.save(os.path.join(sub32, _card_art_filename(idx, name_map) + ".png"))
            total += 1
        except Exception:
            pass
        idx += 1
        p += consumed
    print(f"  card_5bg24x32: {idx} thumbnails -> {sub32}")

    # --- file 3: uncompressed 64x64 NTBG atlas ---------------------------
    # Find its start: first 0x200-aligned raw 'NTBG' magic after the thumbnails.
    f3 = None
    q = (p + 0x1FF) & ~0x1FF
    while q + 4 <= n:
        if data[q:q + 4] == b"NTBG":
            f3 = q
            break
        q += 0x200
    if f3 is not None:
        sub64 = os.path.join(out_root, "card_art_64x64")
        os.makedirs(sub64, exist_ok=True)
        idx = 0
        pal64 = None
        p = f3
        while p + 16 <= n and data[p:p + 4] == b"NTBG":
            size = struct.unpack_from("<I", data, p + 8)[0]
            if size < 16 or p + size > n:
                break
            buf = data[p:p + size]
            try:
                img, pal = ntbg_to_image(buf, fallback_palette=pal64)
                if pal is not None:
                    pal64 = pal
                img.save(os.path.join(sub64, _card_art_filename(idx, name_map) + ".png"))
                total += 1
            except Exception:
                pass
            idx += 1
            p += size
        print(f"  card_5bg64x64: {idx} full-art images -> {sub64}")

    return total


def extract_models(data: bytes, out_dir: str) -> int:
    """Extract monster 3D model + animation binaries from monmodel.pac.

    Each model is an LZ11-compressed NARC.  Its sub-files are proprietary
    "YI**" containers (NOT standard NSBMD), self-named inside the NARC:
      ``_mdl.bin`` (YIMD geometry), ``_mdlanm.bin`` (YICA skeletal anim),
      ``_matanm.bin`` (YIMA), ``_texanm.bin`` (YITA), ``_visanm.bin`` (YIVA).
    They are written verbatim under those names (e.g. ``m8865_mdl.bin``).
    NARCs are located by scanning 0x200-aligned offsets (the PAC's own table is
    non-standard); 146 models -> 364 sub-files.
    """
    os.makedirs(out_dir, exist_ok=True)
    n = len(data)
    models = files = 0
    p = 0x1000
    while p < n:
        if data[p] in (0x10, 0x11):
            out = None
            try:
                out, consumed = lz_decode(data, p, max_size=0x400000)
            except Exception:
                out = None
            if out and out[:4] == b"NARC":
                try:
                    narc = ndspy.narc.NARC(out)
                    names = getattr(narc.filenames, "files", [])
                    for i, fdata in enumerate(narc.files):
                        nm = (str(names[i]) if i < len(names)
                              else f"model{models:03d}_{i}.bin")
                        with open(os.path.join(out_dir, nm), "wb") as fh:
                            fh.write(fdata)
                        files += 1
                    models += 1
                except Exception:
                    pass
                p = (p + consumed + 0x1FF) & ~0x1FF
                continue
        p += 0x200
    print(f"  monmodel: {models} models -> {files} sub-files in {out_dir}")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rom", default="data/over_the_nexus/working/rom.nds")
    ap.add_argument("--out", default="data/over_the_nexus/working/extracted_png")
    ap.add_argument("--models-out",
                    default="data/over_the_nexus/working/extracted_models")
    ap.add_argument("--skip-card-art", action="store_true")
    ap.add_argument("--skip-battle", action="store_true")
    ap.add_argument("--skip-models", action="store_true")
    ap.add_argument("--no-names", action="store_true",
                    help="name card-art PNGs by numeric index instead of "
                         "konami id + card name")
    args = ap.parse_args()

    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom)
    p2id = {p: fid for p, fid in walk(rom.filenames)}

    grand = 0
    if not args.skip_battle:
        print("Battle/field sprites:")
        for k in (1, 2, 3):
            tgt = f"Data_arc_pac/duel2d/BattleMonster{k}.pac"
            data = bytes(rom.files[p2id[tgt]])
            grand += extract_battle(
                data, f"BattleMonster{k}",
                os.path.join(args.out, "battle_monsters"))

    if not args.skip_card_art:
        print("Card artwork:")
        name_map = None if args.no_names else load_card_name_map(rom, p2id)
        if name_map:
            print(f"  loaded {len(name_map)} card names from bin2.pac")
        data = bytes(rom.files[p2id["Data_arc_pac/card.pac"]])
        grand += extract_card_art(data, args.out, name_map)

    if not args.skip_models:
        print("3D monster models:")
        data = bytes(rom.files[p2id["Data_arc_pac/monmodel.pac"]])
        extract_models(data, os.path.join(args.models_out, "monster_models"))

    print(f"\nDONE: {grand} PNG files written under {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

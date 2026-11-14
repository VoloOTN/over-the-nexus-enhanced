"""Battle (attack) sprites: replace the 256x96 cut-out in duel2d/BattleMonster{1,2,3}.pac for every
card in card_art.CARDS that has a ``<base>_character_256x96.png`` (the user's pick per card, 2026-11-13).

Loader (ov3 0x0218C448, KB battle_sprite.path_loader): pac 1 if cid < 6400, 2 if < 8000, else 3. It tries
``<cid>_<L|R>`` first, suffix = table 0x02293794[side] = "L" for side 0, "R" for side 1; then the plain
``<cid>.lz5bg``, drawn MIRRORED on side 0. So R = plain orientation and L = mirror. A cid with side files gets
both written (R as-is, L mirrored); a cid with neither file is skipped (a name insert is unproven).

Each touched pac is repacked whole: names and table layout unchanged, data re-laid in table order at 0x200
alignment with each entry's offset/size rewritten. Repacking an unchanged pac is byte-identical to stock
(asserted on every run), which proves the layout rule. AWAITING IN-GAME TEST.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import ndspy.rom
from PIL import Image, ImageOps

from otn_enhanced.data.card_art import CARDS
from otn_enhanced.rom import card_art_codec, lz_compression
from otn_enhanced.rom.card_art_codec import encode_battle_sprite_256x96
from otn_enhanced.rom.extract_card_images import graphics_pac_layout
from otn_enhanced.rom.lz_compression import compress, decompress

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_battle_sprite.nds"
BLOCK = 0x200
CACHE = Path("data/over_the_nexus/working/battle_sprite_cache")   # gitignored; safe to delete
# The cache key includes the encoder + LZ source, so editing either invalidates it.
_CODE_KEY = b"".join(Path(m.__file__).read_bytes() for m in (card_art_codec, lz_compression))


def pac_path(cid: int) -> str:
    return f"Data_arc_pac/duel2d/BattleMonster{3 if cid >= 8000 else 1 if cid < 6400 else 2}.pac"


def repack(data: bytes, new: dict[str, bytes]) -> bytes:
    """Re-lay *data*'s entries in table order at 0x200 alignment, swapping in *new* {name: stream}."""
    layout = graphics_pac_layout(data)
    out = bytearray(data[:min(off for _, off, _, _ in layout)])   # names + offset table + pad
    base = len(out)
    for name, off, size, slot in layout:
        blob = new.get(name, data[off:off + size])
        struct.pack_into("<II", out, slot, len(out) - base, len(blob))
        out += blob + bytes(-len(blob) % BLOCK)
    return bytes(out)


def jobs(cids=None) -> list:
    return [c for c in CARDS if (cids is None or c.cid in cids) and c.png("character_256x96").is_file()]


def streams(data: bytes, card) -> dict[str, bytes]:
    """{entry name: new LZ11 stream} for *card* in its pac *data* ({} if the cid has no file)."""
    layout = {nm: (off, size) for nm, off, size, _ in graphics_pac_layout(data)}
    img = Image.open(card.png("character_256x96")).convert("RGBA")
    names = {f"{card.cid}_r.lz5bg": img, f"{card.cid}_l.lz5bg": ImageOps.mirror(img)}
    if not set(names) <= set(layout):
        names = {f"{card.cid}.lz5bg": img}
    if not set(names) <= set(layout):
        return {}
    out = {}
    for nm, im in names.items():
        off, size = layout[nm]
        tmpl = decompress(data[off:off + size])
        if b"DFPL" not in tmpl:   # 8bpp stock entry: borrow the pac's first 4bpp header instead
            tmpl = next(t for t in (decompress(data[o:o + s]) for o, s in layout.values()) if b"DFPL" in t)
        out[nm] = _encode(im, tmpl)
    return out


def _encode(im: Image.Image, tmpl: bytes) -> bytes:
    """LZ11 stream for *im* on *tmpl*, cached by content (the encoder is deterministic and ~2.5 s each)."""
    key = hashlib.sha256(im.tobytes() + tmpl + _CODE_KEY).hexdigest()
    path = CACHE / f"{key}.lz"
    if path.is_file():
        return path.read_bytes()
    blob = compress(encode_battle_sprite_256x96(im, tmpl), 0x11)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return blob


def main(src: str = SRC, out: str = OUT, *, cids=None) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    by_pac: dict[str, list] = {}
    for c in jobs(cids):
        by_pac.setdefault(pac_path(c.cid), []).append(c)
    for path, cards in sorted(by_pac.items()):
        fid = rom.filenames.idOf(path)
        data = bytes(rom.files[fid])
        assert repack(data, {}) == data, f"{path}: identity repack differs -- layout rule broken"
        new = {}
        for c in cards:
            s = streams(data, c)
            print(f"  {c.cid:#06x} {c.folder}: " + (", ".join(s) if s else "SKIPPED (no sprite file for this cid)"))
            new.update(s)
        rom.files[fid] = repack(data, new)
    rom.saveToFile(out)


def verify(out: str = OUT, src: str = SRC) -> None:
    """Every replaced entry decodes to its pick (opaque mask >= 97% equal, R as-is / L mirrored); every
    other entry of the three pacs is byte-identical to *src* (stock: nothing else edits these pacs)."""
    import numpy as np
    from otn_enhanced.rom.lz5bg_codec import decode_lz5bg
    rom, ref = ndspy.rom.NintendoDSRom.fromFile(out), ndspy.rom.NintendoDSRom.fromFile(src)
    want = {}
    for c in jobs():
        img = Image.open(c.png("character_256x96")).convert("RGBA")
        for nm, im in ((f"{c.cid}.lz5bg", img), (f"{c.cid}_r.lz5bg", img), (f"{c.cid}_l.lz5bg", ImageOps.mirror(img))):
            want[(pac_path(c.cid), nm)] = im
    n = 0
    for k in (1, 2, 3):
        path = f"Data_arc_pac/duel2d/BattleMonster{k}.pac"
        a, b = (bytes(r.files[r.filenames.idOf(path)]) for r in (ref, rom))
        la, lb = graphics_pac_layout(a), graphics_pac_layout(b)
        assert [e[0] for e in la] == [e[0] for e in lb], f"{path}: names changed"
        for (nm, oa, sa, _), (_, ob, sb, _) in zip(la, lb):
            if (path, nm) in want:
                got = np.asarray(decode_lz5bg(b[ob:ob + sb]).convert("RGBA"))[:, :, 3] >= 128
                exp = np.asarray(want[(path, nm)])[:, :, 3] >= 128
                assert (got == exp).mean() >= 0.97, f"{path}:{nm} decodes to a different mask"
                n += 1
            else:
                assert a[oa:oa + sa] == b[ob:ob + sb], f"{path}:{nm} changed"
    print(f"battle_sprites verify: OK ({n} entries replaced, all others identical to {src})")


if __name__ == "__main__":
    main()
    verify()

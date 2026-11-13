"""Generate the ROM-ready card-art images from a single card render.

Given ONE input card image (a standard portrait Yu-Gi-Oh! card render, e.g. a
YGOProDeck 813x1185 picture), this produces the image set the OTN card-art
injector consumes:

  {name}_32x32.png            ROM thumb: the real card-frame template with the
                               art dropped into its illustration window
  {name}_64x64.png            cropped artwork (illustration only), 64x64
  {name}_artwork_full.png     cropped artwork at full resolution (no resize)
  {name}_character.png        full-res artwork with the background removed (isnet mask)
  {name}_character_256x96.png character scaled to the 256x96 battle-sprite canvas

The crop geometry is expressed as fractions of the whole image, so it is
resolution-independent for the standard card layout:

  card outer edge : L=0.036 R=0.963 T=0.022 B=0.965  (trims the render's margin)
  artwork window  : L=0.125 R=0.873 T=0.188 B=0.708  (just inside the silver frame)

The 32x32 thumb uses the SAME plain-border templates the game ships
(card_arts/template_frames/{effect,fusion,synchro,spell,trap}_32x32.png) rather than
shrinking the whole card render — that shrink method produced illegible thumbs.
Pass --frame to pick the template (must match the card's actual frame type).

Background removal runs the ``isnet-general-use`` model directly with the optional
``onnxruntime`` package (``uv run --extra bgremove ...``) and reads the model from
``$U2NET_HOME`` or ``~/.u2net/isnet-general-use.onnx`` (rembg's cache location and file).
If either is missing the two character outputs are skipped with a note (the 32x32 /
64x64 / full-art outputs are produced regardless).

The cut-out is deliberately SOFT (2026-11-04): the old rembg alpha-matting call
(erode 3, foreground threshold 240, mask post-processing) ate thin parts such as
weapons, hands and capes. Now the raw model mask is grown slightly, cut at a low
threshold, and only detached specks are removed on the final 256x96 sprite.

Usage:
    python -m otn_enhanced.tools.make_card_art CARD.png --frame effect
    python -m otn_enhanced.tools.make_card_art CARD.jpg --out-dir art/ --name My_Card --frame synchro
    python -m otn_enhanced.tools.make_card_art CARD.png --no-character   # skip background removal
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

# --- crop geometry (fractions of the whole image), standard card layout --------
CARD_BOX = (0.036, 0.963, 0.022, 0.965)   # L, R, T, B — whole card (no outer margin)
ART_BOX = (0.125, 0.873, 0.188, 0.708)    # L, R, T, B — illustration window
SPRITE_W, SPRITE_H = 256, 96              # battle-sprite canvas

# --- 32x32 ROM-thumb templates (stock plain-border frames) ---------------------
TEMPLATE_DIR = Path("data/over_the_nexus/card_arts/template_frames")
FRAME_TYPES = ("effect", "fusion", "synchro", "spell", "trap", "ritual")
THUMB_HOLE = (5, 4, 27, 26)  # x0, y0, x1, y1 — illustration window inside the template

# soft cut-out settings (tuned 2026-11-04 on all 123 implemented arts)
_MODEL_FILE = "isnet-general-use.onnx"
_MODEL_SIZE = 1024
_MODEL_MEAN = (0.485, 0.456, 0.406)       # rembg's isnet preprocessing (std 1.0)
MASK_CUTOFF = 48                          # mask value (0..255) counted as foreground
MASK_GROW = 0.008                         # grow the mask by this fraction of the art's short side
SPECK_FRAC, SPECK_MIN_PX = 0.02, 40       # 256x96 blobs smaller than max(40 px, 2%) are dropped


def _crop_frac(img: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    """Crop *img* to a (L, R, T, B) box given as fractions of its size."""
    w, h = img.size
    left, right, top, bottom = box
    return img.crop((int(left * w), int(top * h), int(right * w), int(bottom * h)))


def make_thumb_32x32(art_full: Image.Image, frame: str) -> Image.Image:
    """Stock plain-border *frame* template with the art dropped into its window."""
    if frame not in FRAME_TYPES:
        raise ValueError(f"frame must be one of {FRAME_TYPES}, got {frame!r}")
    template = Image.open(TEMPLATE_DIR / f"{frame}_32x32.png").convert("RGBA")
    x0, y0, x1, y1 = THUMB_HOLE
    s = min(art_full.size)
    l, t = (art_full.width - s) // 2, (art_full.height - s) // 2
    art = art_full.convert("RGBA").crop((l, t, l + s, t + s)).resize((x1 - x0, y1 - y0), Image.LANCZOS)
    out = template.copy()
    out.paste(art, (x0, y0))
    return out


def make_art_full(card: Image.Image) -> Image.Image:
    """Cropped illustration at full resolution (no resize)."""
    return _crop_frac(card, ART_BOX)


def make_art_64x64(art_full: Image.Image) -> Image.Image:
    """Cropped illustration resized to 64x64 RGBA."""
    return art_full.resize((64, 64), Image.LANCZOS).convert("RGBA")


def make_character_256x96(character: Image.Image) -> Image.Image:
    """Trim a transparent character to content, scale to 96px tall, centre on 256x96.

    Bottom-aligned vertically (feet on the ground), matching the battle sprites.
    """
    img = character.convert("RGBA")
    bbox = img.getbbox()
    content = img.crop(bbox) if bbox else img

    scale = SPRITE_H / content.height
    new_w = max(1, round(content.width * scale))
    if new_w > SPRITE_W:                       # guard very wide art
        scale = SPRITE_W / content.width
        new_w = SPRITE_W
    new_h = max(1, round(content.height * scale))
    resized = content.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (SPRITE_W, SPRITE_H), (0, 0, 0, 0))
    canvas.paste(resized, ((SPRITE_W - new_w) // 2, SPRITE_H - new_h))
    return drop_specks(canvas)


def drop_specks(img: Image.Image, frac: float = SPECK_FRAC, min_px: int = SPECK_MIN_PX) -> Image.Image:
    """Clear 8-connected opaque blobs (alpha >= 128, the encoder's cutoff) smaller than
    max(*min_px*, *frac* of all opaque pixels). The largest blob is always kept."""
    arr = np.array(img.convert("RGBA"))
    solid = arr[:, :, 3] >= 128
    h, w = solid.shape
    label = np.zeros((h, w), np.int32)
    sizes = [0]
    for y, x in zip(*np.nonzero(solid)):
        if label[y, x]:
            continue
        n = len(sizes)
        label[y, x] = n
        queue, count = deque([(y, x)]), 0
        while queue:
            cy, cx = queue.popleft()
            count += 1
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < h and 0 <= nx < w and solid[ny, nx] and not label[ny, nx]:
                        label[ny, nx] = n
                        queue.append((ny, nx))
        sizes.append(count)
    if len(sizes) == 1:
        return img
    keep = np.array([s >= max(min_px, frac * sum(sizes)) for s in sizes])
    keep[int(np.argmax(sizes))] = True
    keep[0] = False
    arr[:, :, 3] = np.where(keep[label], arr[:, :, 3], 0)
    return Image.fromarray(arr)


_session = None


def _model_path() -> Path:
    return Path(os.environ.get("U2NET_HOME", Path.home() / ".u2net")) / _MODEL_FILE


def _soft_mask(art: Image.Image) -> Image.Image:
    """Raw isnet foreground mask (L, 0..255) at *art*'s size: no matting, no erode."""
    rgb = art.convert("RGB")
    x = np.asarray(rgb.resize((_MODEL_SIZE, _MODEL_SIZE), Image.LANCZOS), np.float32) / 255.0
    x = (x - np.array(_MODEL_MEAN, np.float32)).transpose(2, 0, 1)[None]
    pred = _session.run(None, {_session.get_inputs()[0].name: x})[0][0, 0]
    pred = (pred - pred.min()) / (pred.max() - pred.min() + 1e-8)
    return Image.fromarray((pred * 255).astype(np.uint8)).resize(rgb.size, Image.LANCZOS)


def _remove_background(art_full: Image.Image):
    """Return *art_full* with a soft-cut background removed, or None if onnxruntime or
    the model file is missing."""
    global _session
    if _session is None:
        try:
            import onnxruntime as ort
        except ImportError:
            return None
        if not _model_path().is_file():
            return None
        _session = ort.InferenceSession(str(_model_path()), providers=["CPUExecutionProvider"])
    mask = _soft_mask(art_full)
    k = max(3, round(min(art_full.size) * MASK_GROW) | 1)
    mask = mask.filter(ImageFilter.MaxFilter(k))
    alpha = np.where(np.asarray(mask) >= MASK_CUTOFF, 255, 0).astype(np.uint8)
    # drop pin-prick noise before scaling (a 5x5 neighbourhood must be >= 1/4 foreground)
    near = np.asarray(Image.fromarray(alpha).filter(ImageFilter.BoxBlur(2))) >= 64
    out = art_full.convert("RGBA")
    out.putalpha(Image.fromarray(np.where(near, alpha, 0).astype(np.uint8)))
    return out


def make_card_art(input_path: str | Path, out_dir: str | Path | None = None,
                  name: str | None = None, *, frame: str = "effect",
                  do_character: bool = True) -> list[Path]:
    """Produce the card-art image set for one input card render.

    ``frame`` picks the 32x32 thumb template and must match the card's actual
    frame type (effect/fusion/synchro/spell/trap).

    Returns the list of written file paths. ``out_dir`` defaults to the input's
    folder and ``name`` to the input's filename stem.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    out_dir = Path(out_dir) if out_dir else input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    base = name or input_path.stem

    card = Image.open(input_path).convert("RGB")
    written: list[Path] = []

    def save(img: Image.Image, suffix: str) -> None:
        p = out_dir / f"{base}_{suffix}.png"
        img.save(p)
        written.append(p)

    art_full = make_art_full(card)
    save(make_thumb_32x32(art_full, frame), "32x32")
    save(art_full, "artwork_full")
    save(make_art_64x64(art_full), "64x64")

    if do_character:
        character = _remove_background(art_full)
        if character is None:
            print(f"  [skip] character outputs — needs onnxruntime (uv run --extra bgremove) "
                  f"and the model at {_model_path()}", file=sys.stderr)
        else:
            save(character, "character")
            save(make_character_256x96(character), "character_256x96")

    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input card image (PNG/JPG, standard portrait render)")
    ap.add_argument("--out-dir", default=None, help="output folder (default: input's folder)")
    ap.add_argument("--name", default=None, help="output basename (default: input filename stem)")
    ap.add_argument("--frame", default="effect", choices=FRAME_TYPES,
                    help="32x32 thumb template — must match the card's real frame type (default: effect)")
    ap.add_argument("--no-character", action="store_true",
                    help="skip the background-removed character + 256x96 sprite outputs")
    args = ap.parse_args(argv)

    written = make_card_art(args.input, args.out_dir, args.name, frame=args.frame,
                            do_character=not args.no_character)
    for p in written:
        print(f"  wrote {p}")
    print(f"done: {len(written)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

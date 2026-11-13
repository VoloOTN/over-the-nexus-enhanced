"""Extract all YDQ puzzle files from an NDS save (.sav) file.

Scans the save file for YDQ magic bytes (0x59 0x51), decodes each match,
strips the SAV-specific tail bytes (keeping only the 0x00 terminator), and
writes one clean .ydq file per unique puzzle found.

Usage
-----
    uv run python -m otn_enhanced.rom.extract_ydq_from_sav  rom.sav  out/
    uv run python -m otn_enhanced.rom.extract_ydq_from_sav  rom.sav  out/  --keep-duplicates
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import sys
from pathlib import Path

from otn_enhanced.rom.ydq_codec import decode_ydq, encode_ydq

# YDQ magic bytes
_YDQ_MAGIC = bytes([0x59, 0x51])

# The puzzle name string is stored at ydq_offset - 0x38 as a null-terminated
# ASCII string (observed layout in Over the Nexus SAV files).
_NAME_REL_OFFSET = 0x38


def _read_puzzle_name(sav_data: bytes, ydq_offset: int) -> str | None:
    """Try to read the null-terminated puzzle name preceding the YDQ entry."""
    name_start = ydq_offset - _NAME_REL_OFFSET
    if name_start < 0:
        return None
    end = sav_data.find(b"\x00", name_start)
    if end == -1 or end == name_start:
        return None
    raw = sav_data[name_start:end]
    try:
        name = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    # Sanity-check: printable ASCII only
    if not all(32 <= ord(c) < 127 for c in name):
        return None
    return name


def _safe_filename(name: str) -> str:
    """Convert a puzzle name to a safe filename stem."""
    safe = "".join(c if (c.isalnum() or c in " _-") else "_" for c in name)
    return safe.strip().replace(" ", "_")


def _clean_encode(decoded: dict) -> bytes:
    """Re-encode a decoded YDQ payload with just a single 0x00 terminator tail."""
    clean = dict(decoded)
    clean["tail_b64"] = base64.b64encode(b"\x00").decode("ascii")
    return encode_ydq(clean)


def extract_from_sav(
    sav_data: bytes,
    *,
    keep_duplicates: bool = False,
) -> list[tuple[int, str | None, bytes]]:
    """Return a list of (offset, puzzle_name, clean_ydq_bytes) for every YDQ found.

    Duplicate payloads (same canonical bytes after re-encoding) are suppressed
    unless *keep_duplicates* is True.
    """
    results: list[tuple[int, str | None, bytes]] = []
    seen: set[str] = set()

    pos = 0
    while True:
        idx = sav_data.find(_YDQ_MAGIC, pos)
        if idx == -1:
            break

        # Try to decode from here; give a generous window (4 KB) so the parser
        # has enough bytes even if the puzzle is near the end of a slot.
        window = sav_data[idx : idx + 4096]
        try:
            decoded = decode_ydq(window)
        except Exception:
            pos = idx + 1
            continue

        clean = _clean_encode(decoded)
        digest = hashlib.sha256(clean).hexdigest()

        if keep_duplicates or digest not in seen:
            seen.add(digest)
            name = _read_puzzle_name(sav_data, idx)
            results.append((idx, name, clean))

        pos = idx + 1

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract YDQ puzzle files from an NDS .sav file."
    )
    parser.add_argument("sav", help="Path to the .sav file")
    parser.add_argument("outdir", help="Output directory for .ydq files")
    parser.add_argument(
        "--keep-duplicates",
        action="store_true",
        help="Write duplicate puzzles (same content at different offsets) as separate files",
    )
    parser.add_argument(
        "--prefix",
        default="puzzle",
        help="Filename prefix for output files (default: puzzle)",
    )
    args = parser.parse_args()

    sav_path = Path(args.sav)
    if not sav_path.is_file():
        print(f"Error: {sav_path} not found", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sav_data = sav_path.read_bytes()
    print(f"SAV size: {len(sav_data):,} bytes")

    results = extract_from_sav(sav_data, keep_duplicates=args.keep_duplicates)

    if not results:
        print("No YDQ puzzles found.")
        sys.exit(0)

    print(f"Found {len(results)} unique YDQ puzzle(s):")
    used_stems: set[str] = set()
    for i, (offset, name, ydq_bytes) in enumerate(results):
        if name:
            stem = _safe_filename(name)
            # Avoid collisions when keep_duplicates is set
            if stem in used_stems:
                stem = f"{stem}_{i + 1:02d}"
        else:
            stem = f"{args.prefix}_{i + 1:02d}"
        used_stems.add(stem)
        out_path = out_dir / f"{stem}.ydq"
        out_path.write_bytes(ydq_bytes)
        label = f'  name="{name}"' if name else ""
        print(f"  [{i + 1:2d}] offset=0x{offset:06x}  {len(ydq_bytes):3d} bytes{label}  -> {out_path}")

    print(f"\nDone. {len(results)} file(s) written to {out_dir}/")


if __name__ == "__main__":
    main()

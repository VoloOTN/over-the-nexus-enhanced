"""Bake the ROM's Forbidden/Limited lists into ``data/banlists.json``.

The six lists are static data — they ship inside the ROM and never change — but
reading one meant opening the whole NDS image with ndspy, locating ``bin.pac``,
parsing the archive and decoding an entry: **0.24s on every single invocation**,
and a hard dependency on having the ROM present just to know that Pot of Greed is
Forbidden.

Regenerate after replacing the base ROM::

    uv run python -m otn_enhanced.deckgen.bake_banlists

The baked file records the source ROM's SHA-1 so a mismatch is visible rather
than silent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "deckgen.banlists.v1"
DATA_PATH = Path(__file__).resolve().parent / "data" / "banlists.json"

#: Copy limit implied by each section name in the decoded list.
_SECTIONS = {"Forbidden": 0, "Limited": 1, "Semi-Limited": 2}


def extract() -> dict:
    """Pull every ``limit*.bin`` out of the ROM in a single pass."""
    import ndspy.rom

    from otn_enhanced.deckgen.cache import sha1_file
    from otn_enhanced.deckgen.cardpool import ROM_PATH, _iter_paths
    from otn_enhanced.rom.limit_codec import decode_limit
    from otn_enhanced.rom.pac import parse_pac

    rom = ndspy.rom.NintendoDSRom.fromFile(str(ROM_PATH))
    path = next(p for p in _iter_paths(rom.filenames) if p.lower().endswith("bin.pac"))
    raw = bytes(rom.files[rom.filenames.idOf(path)])
    archive = parse_pac(raw, path)

    lists: dict[str, dict[str, list[int]]] = {}
    for entry in archive.files:
        name = entry.get_clean_name()
        if not name.lower().startswith("limit") or not name.lower().endswith(".bin"):
            continue
        text, _ = decode_limit(raw[entry.address : entry.address + entry.size])
        data = json.loads(text)
        lists[name[:-4]] = {
            section: sorted(int(c) for c in data.get(section, []))
            for section in _SECTIONS
        }
    return {
        "schema": SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_rom": str(ROM_PATH),
        "source_sha1": sha1_file(ROM_PATH),
        "lists": dict(sorted(lists.items())),
    }


def main() -> int:
    payload = extract()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {DATA_PATH}")
    for name, sections in payload["lists"].items():
        counts = ", ".join(f"{len(v)} {k.lower()}" for k, v in sections.items())
        print(f"  {name:14} {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Decompile every card effect handler in overlay0003 into pseudo-Python.

Usage::

    uv run python -m otn_enhanced.tools.decompile_all \
        data/over_the_nexus/working/rom.nds \
        data/over_the_nexus/decompiled

The output directory is populated with one ``cards/<id>_<name>.py`` per
non-empty handler-table entry, plus an ``__init__.py`` that maps Konami
IDs to the corresponding modules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from otn_enhanced.rom.overlay_io import load_overlay3
from otn_enhanced.tools.effect_decompile import iter_handler_entries, lift_card_module
from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME


def _safe_name(s: str) -> str:
    keep: list[str] = []
    for ch in s:
        if ch.isalnum():
            keep.append(ch)
        elif keep and keep[-1] != "_":
            keep.append("_")
    name = "".join(keep).strip("_")
    return name or "Unnamed"


def main(argv: list[str] | None = None) -> int:
    sys.setrecursionlimit(20000)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("rom", type=Path, help="Input .nds ROM or raw overlay0003 binary")
    p.add_argument("out_dir", type=Path, help="Output directory")
    p.add_argument("--limit", type=int, default=0,
                   help="Stop after N cards (debug)")
    args = p.parse_args(argv)

    if args.rom.suffix.lower() == ".nds":
        _, overlay = load_overlay3(args.rom)
    else:
        overlay = args.rom.read_bytes()

    cards_dir = args.out_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    registry: list[tuple[int, str, str]] = []  # (id, module_name, card_name)
    n_ok = 0
    n_fail = 0

    for entry in iter_handler_entries(overlay):
        cid = entry["card_id"]
        name = KONAMI_ID_TO_CARD_NAME.get(cid, f"Unknown_{cid:04X}")
        mod_name = f"c{cid:05d}_i{entry['index']:04d}_{_safe_name(name)}"
        out_path = cards_dir / f"{mod_name}.py"

        try:
            text = lift_card_module(overlay, entry)
        except Exception as exc:  # noqa: BLE001
            n_fail += 1
            text = (f'"""Card 0x{cid:04X} ({name}) — lift failed."""\n'
                    f"# {type(exc).__name__}: {exc}\n")

        out_path.write_text(text, encoding="utf-8")
        registry.append((cid, mod_name, name))
        n_ok += 1
        if args.limit and n_ok >= args.limit:
            break

    # Empty package marker for cards/
    (cards_dir / "__init__.py").write_text("", encoding="utf-8")

    # Top-level __init__.py with a registry
    init_lines = [
        '"""Decompiled card effects from overlay0003 (Over the Nexus)."""',
        "",
        "# Map Konami ID -> (module_name, card_name)",
        "REGISTRY: dict[int, tuple[str, str]] = {",
    ]
    for cid, mod, name in registry:
        nm = name.replace("\\", "\\\\").replace("'", "\\'")
        init_lines.append(f"    0x{cid:04X}: ({mod!r}, '{nm}'),")
    init_lines.append("}")
    init_lines.append("")
    (args.out_dir / "__init__.py").write_text("\n".join(init_lines),
                                              encoding="utf-8")

    print(f"Wrote {n_ok} card modules ({n_fail} failed) to {cards_dir}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

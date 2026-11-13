"""Generate the curated effect registry from overlay0003.

Produces three normalised JSON files under this package's ``data/`` dir:

* ``primitives.json`` — every distinct call target across all handlers (the
  engine subroutines / ARM9 routines), each with its address, a curated name
  where one is known, call frequency, and a few example callers.  This is the
  superset behind :data:`otn_enhanced.asm.effect_builder.PRIMITIVES`.
* ``handlers.json`` — every distinct handler function: address, byte size,
  ordered call targets, literal-pool constants, referenced Konami card ids,
  and the (card, slot) pairs that use it.
* ``cards.json`` — every handler-table entry (card): Konami id, name, table
  index, and the per-slot handler addresses.

Primitive names are merged from the curated :mod:`primitive_names` table
(confidence tiers ``known`` / ``proven``).  Handlers additionally carry
*advisory* ``themes`` inferred from the effect text of the cards that use them
(:mod:`infer_names`) — surfaced as separate metadata, never as a routine's real
name.  ``cards_text.json`` holds the ``cid -> {name, desc}`` join behind the
themes.

Usage::

    uv run python -m otn_enhanced.tools.effect_registry.gen_registry \\
        data/over_the_nexus/working/rom.nds
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from otn_enhanced.rom.overlay_io import load_overlay3
from otn_enhanced.tools.effect_extract import HANDLER_SLOT_NAMES, RAM_BASE
from otn_enhanced.tools.effect_decompile import iter_handler_entries
from otn_enhanced.asm.effect_shim import collect_handler_addrs, lift_handler_to_builder
from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME
from otn_enhanced.tools.effect_registry.primitive_names import PRIMITIVE_NAMES
from otn_enhanced.tools.effect_registry.infer_names import handler_themes, load_card_text

DATA_DIR = Path(__file__).parent / "data"


def _primitive_meta(target: int) -> tuple[str | None, str | None, str | None]:
    """Return ``(name, signature, confidence)`` for a call target from the
    curated table, or ``(None, None, None)`` if it is not named."""
    entry = PRIMITIVE_NAMES.get(target)
    if entry is None:
        return None, None, None
    return entry.name, entry.signature, entry.confidence


def _extract_handler(overlay: bytes, addr: int, sorted_addrs: list[int]) -> dict:
    """Structural facts for the distinct handler at *addr*."""
    builder = lift_handler_to_builder(overlay, addr, sorted_addrs=sorted_addrs)
    calls: list[int] = []
    pool: list[int] = []
    for kind, value in builder._ops:
        if kind in ("bl", "blx"):
            calls.append(value)
        elif kind == "pool":
            pool.append(value)
    card_refs = sorted({v for v in pool if v in KONAMI_ID_TO_CARD_NAME})
    return {
        "addr": addr,
        "size": builder.size,
        "calls": calls,
        "pool": pool,
        "card_refs": card_refs,
    }


def build_registry(overlay: bytes) -> dict[str, list]:
    """Return the registry tables (primitives, handlers, cards, cards_text)."""
    sorted_addrs = collect_handler_addrs(overlay)
    overlay_len = len(overlay)
    card_text = load_card_text()        # {cid: (name, english_desc)} — verified join

    # --- cards + which handler each slot points at ---------------------
    cards: list[dict] = []
    used_by: dict[int, list[tuple[int, str]]] = {}   # handler addr -> [(cid, slot)]
    for entry in iter_handler_entries(overlay):
        cid = entry["card_id"]
        slots: dict[str, int] = {}
        for slot in HANDLER_SLOT_NAMES:
            ptr = entry[slot]
            if not ptr:
                continue
            addr = ptr & ~1
            slots[slot] = addr
            used_by.setdefault(addr, []).append((cid, slot))
        cards.append({
            "cid": cid,
            "name": KONAMI_ID_TO_CARD_NAME.get(cid, f"Unknown_{cid:04X}"),
            "index": entry["index"],
            "slots": slots,
        })

    # --- distinct handlers --------------------------------------------
    handlers: list[dict] = []
    call_freq: dict[int, int] = {}
    call_callers: dict[int, list[int]] = {}
    for addr in sorted_addrs:
        if not (0 <= addr - RAM_BASE < overlay_len):
            continue
        h = _extract_handler(overlay, addr, sorted_addrs)
        used = sorted(used_by.get(addr, []))
        h["used_by"] = [{"cid": c, "slot": s} for c, s in used]
        # Advisory: themes from the effect text of the cards that use this handler.
        themes, evidence = handler_themes([c for c, _ in used], card_text)
        h["themes"] = themes
        h["theme_evidence"] = evidence
        handlers.append(h)
        for tgt in h["calls"]:
            call_freq[tgt] = call_freq.get(tgt, 0) + 1
            callers = call_callers.setdefault(tgt, [])
            if addr not in callers:
                callers.append(addr)

    # --- primitives (every distinct call target) ----------------------
    primitives: list[dict] = []
    for target in sorted(call_freq):
        off = target - RAM_BASE
        in_overlay = 0 <= off < overlay_len
        name, signature, confidence = _primitive_meta(target)
        primitives.append({
            "addr": target,
            "name": name,
            "signature": signature,
            "confidence": confidence,
            "location": "overlay" if in_overlay else "arm9",
            "overlay_offset": off if in_overlay else None,
            "call_count": call_freq[target],
            "example_callers": sorted(call_callers[target])[:5],
        })
    primitives.sort(key=lambda p: (-p["call_count"], p["addr"]))

    cards_text = [{"cid": cid, "name": nm, "desc": ds}
                  for cid, (nm, ds) in sorted(card_text.items())]

    return {"primitives": primitives, "handlers": handlers,
            "cards": cards, "cards_text": cards_text}


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom", type=Path,
                   help="Input .nds ROM or raw decompressed overlay0003 binary")
    p.add_argument("--out-dir", type=Path, default=DATA_DIR,
                   help=f"Output directory (default: {DATA_DIR})")
    args = p.parse_args(argv)

    if args.rom.suffix.lower() == ".nds":
        _, overlay = load_overlay3(args.rom)
    else:
        overlay = args.rom.read_bytes()

    reg = build_registry(overlay)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    named = sum(1 for x in reg["primitives"] if x["name"])
    themed = sum(1 for h in reg["handlers"] if h["themes"])
    meta = {
        "ram_base": RAM_BASE,
        "counts": {k: len(v) for k, v in reg.items()},
        "named_primitives": named,
        "themed_handlers": themed,
    }
    for table in ("primitives", "handlers", "cards", "cards_text"):
        _write_json(args.out_dir / f"{table}.json", reg[table])
    _write_json(args.out_dir / "meta.json", meta)

    print(f"registry -> {args.out_dir}", file=sys.stderr)
    for k, v in reg.items():
        print(f"  {k}: {len(v)}", file=sys.stderr)
    print(f"  named primitives: {named}/{len(reg['primitives'])} "
          f"| themed handlers: {themed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

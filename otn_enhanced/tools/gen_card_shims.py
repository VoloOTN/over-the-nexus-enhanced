"""Generate one importable Python shim per card effect in overlay0003.

Each handler-table entry becomes a module under ``<out_dir>/cards/`` whose
``build_<slot>(base) -> bytes`` functions re-emit that card's Thumb-1 effect
handlers as relocatable code (see :mod:`otn_enhanced.asm.effect_shim`).  The
modules are human-readable by card *name* and carry the annotated assembly and
pseudo-Python decompilation in each function's docstring.

Usage::

    uv run python -m otn_enhanced.tools.gen_card_shims \\
        data/over_the_nexus/working/rom.nds \\
        data/over_the_nexus/shims

The input may be a ``.nds`` ROM (overlay0003 is extracted automatically) or a
raw decompressed overlay binary such as
one written out from :func:`otn_enhanced.rom.stock.ov3`.

The output directory mirrors :mod:`otn_enhanced.tools.decompile_all`: a
``cards/`` package plus a top-level ``__init__.py`` mapping Konami IDs to
modules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from otn_enhanced.rom.overlay_io import load_overlay3
from otn_enhanced.tools.effect_extract import HANDLER_SLOT_NAMES, RAM_BASE, annotate_instructions
from otn_enhanced.tools.effect_decompile import iter_handler_entries, lift_function
from otn_enhanced.asm.effect_shim import collect_handler_addrs, handler_extent, lift_handler_to_builder
from otn_enhanced.asm.thumb_disasm import decode_thumb
from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME
from otn_enhanced.tools.effect_registry import EffectRegistry, load_registry


def _call_resolver(reg: EffectRegistry | None):
    """Return ``callable(addr) -> str | None`` naming a call target via *reg*.

    Names are suffixed with their confidence so a reader can tell a verified
    routine (``draw[proven]``) from the registry's address-only fallbacks.
    """
    if reg is None:
        return None

    def resolve(addr: int) -> str | None:
        prim = reg.primitive(addr)
        if prim is None or prim.name is None:
            return None
        return f"{prim.name}[{prim.confidence}]"

    return resolve


def _safe_name(s: str) -> str:
    """Turn a card name into a filesystem/identifier-safe token."""
    keep: list[str] = []
    for ch in s:
        if ch.isalnum():
            keep.append(ch)
        elif keep and keep[-1] != "_":
            keep.append("_")
    return "".join(keep).strip("_") or "Unnamed"


def _annotated_asm(overlay: bytes, func_addr: int,
                   sorted_addrs: list[int]) -> list[str]:
    """Return annotated-assembly comment lines for the handler at *func_addr*."""
    file_off = func_addr - RAM_BASE
    size = handler_extent(overlay, func_addr, sorted_addrs)
    insns = decode_thumb(overlay[file_off:file_off + size], func_addr,
                         overlay_data=overlay, ram_base=RAM_BASE)
    annotate_instructions(insns, overlay)
    lines: list[str] = []
    for ins in insns:
        asm = f"{ins.mnemonic:<8s}{ins.operands}" if ins.operands else ins.mnemonic
        cmt = f"  ; {ins.comment}" if ins.comment else ""
        lines.append(f"    0x{ins.addr:08X}: {asm}{cmt}")
    return lines


def _docsafe(line: str) -> str:
    """Neutralise embedded triple-quotes so the line is safe inside a docstring."""
    return line.replace('"""', "'''")


def _build_fn_source(slot: str, func_addr: int, overlay: bytes,
                     sorted_addrs: list[int],
                     reg: EffectRegistry | None) -> list[str]:
    """Render a ``build_<slot>`` function (builder calls + decompiled docstring)."""
    builder = lift_handler_to_builder(overlay, func_addr, sorted_addrs=sorted_addrs)
    file_off = func_addr - RAM_BASE
    resolve = _call_resolver(reg)

    out: list[str] = []
    out.append(f"def build_{slot}(base: int = 0x{func_addr:08X}) -> bytes:")
    out.append('    """' + f"{slot} — RAM 0x{func_addr:08X} (ov+0x{file_off:06X}), "
               f"{builder.size} bytes.")
    out.append("")
    out.append("    Calling build(base) re-emits this handler relocated to *base*;")
    out.append(f"    build(0x{func_addr:08X}) reproduces the original overlay bytes.")
    # Named engine routines this handler calls (registry), in call order.
    if resolve is not None:
        called = []
        for kind, value in builder._ops:
            if kind in ("bl", "blx"):
                nm = resolve(value)
                if nm and nm not in called:
                    called.append(nm)
        if called:
            out.append("")
            out.append(f"    Calls: {', '.join(called)}")
    out.append("")
    out.append("    Decompiled pseudo-Python:")
    try:
        for ln in lift_function(overlay, func_addr, slot).splitlines():
            out.append(f"        {_docsafe(ln)}" if ln else "")
    except Exception as exc:  # noqa: BLE001
        out.append(f"        # (lift failed: {type(exc).__name__}: {exc})")
    out.append("")
    out.append("    Annotated assembly:")
    for ln in _annotated_asm(overlay, func_addr, sorted_addrs):
        out.append(f"    {_docsafe(ln)}")
    out.append('    """')
    out.append("    s = StubBuilder()")
    out.extend(builder.render_python("s", resolve_call=resolve))
    out.append("    return s.build(base)")
    return out


def _card_summary(entry: dict, reg: EffectRegistry) -> tuple[list[str], list[str]]:
    """Return ``(themes, named_primitives)`` across the card's effect handlers."""
    themes: list[str] = []
    prims: list[str] = []
    seen_addr: set[int] = set()
    for slot in HANDLER_SLOT_NAMES:
        ptr = entry.get(slot)
        if not ptr:
            continue
        addr = ptr & ~1
        if addr in seen_addr:
            continue
        seen_addr.add(addr)
        h = reg.handlers.get(addr)
        if h is None:
            continue
        for t in h.themes:
            if t not in themes:
                themes.append(t)
        for tgt in h.calls:
            prim = reg.primitive(tgt)
            if prim and prim.name and prim.name not in prims:
                prims.append(prim.name)
    return sorted(themes), prims


def _card_module_source(overlay: bytes, entry: dict,
                        sorted_addrs: list[int],
                        reg: EffectRegistry | None) -> str:
    """Render the full source of one card's shim module."""
    cid = entry["card_id"]
    name = KONAMI_ID_TO_CARD_NAME.get(cid, f"Unknown_{cid:04X}")

    out: list[str] = []
    out.append('"""')
    out.append(f"Effect shim — {name}")
    out.append("")
    out.append(f"  Konami ID : 0x{cid:04X} ({cid})")
    out.append(f"  Table idx : {entry['index']}")
    if reg is not None:
        themes, prims = _card_summary(entry, reg)
        out.append(f"  Themes    : {', '.join(themes) if themes else '(none inferred)'}")
        out.append(f"  Uses      : {', '.join(prims) if prims else '(no named routines)'}")
    out.append("")
    out.append("Relocatable Thumb-1 re-emission of this card's effect handlers,")
    out.append("decompiled from overlay0003. Engine-routine names + themes are from")
    out.append("otn_enhanced.tools.effect_registry (themes are advisory — see WRITING_EFFECTS.md).")
    out.append('"""')
    out.append("from __future__ import annotations")
    out.append("")
    out.append("from otn_enhanced.asm.effect_shim import StubBuilder")
    out.append("")
    out.append(f"KONAMI_ID = 0x{cid:04X}")
    out.append(f"CARD_NAME = {name!r}")
    out.append("")

    seen: dict[int, str] = {}   # handler addr -> first slot name that built it
    handlers: dict[str, str] = {}  # slot -> build fn name
    for slot in HANDLER_SLOT_NAMES:
        ptr = entry[slot]
        if not ptr:
            continue
        addr = ptr & ~1
        if addr in seen:
            handlers[slot] = f"build_{seen[addr]}"
            continue
        seen[addr] = slot
        handlers[slot] = f"build_{slot}"
        out.extend(_build_fn_source(slot, addr, overlay, sorted_addrs, reg))
        out.append("")

    out.append("HANDLERS = {")
    for slot, fn in handlers.items():
        out.append(f"    {slot!r}: {fn},")
    out.append("}")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    sys.setrecursionlimit(20000)
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom", type=Path,
                   help="Input .nds ROM or raw decompressed overlay0003 binary")
    p.add_argument("out_dir", type=Path, nargs="?",
                   default=Path("data/over_the_nexus/shims"),
                   help="Output directory (default: data/over_the_nexus/shims)")
    p.add_argument("--limit", type=int, default=0, help="Stop after N cards (debug)")
    p.add_argument("--no-registry", action="store_true",
                   help="Skip effect_registry annotation (addresses only)")
    args = p.parse_args(argv)

    if args.rom.suffix.lower() == ".nds":
        _, overlay = load_overlay3(args.rom)
    else:
        overlay = args.rom.read_bytes()

    reg: EffectRegistry | None = None
    if not args.no_registry:
        try:
            reg = load_registry()
            _ = reg.primitives        # force-load; FileNotFoundError if not generated
        except FileNotFoundError:
            print("warning: effect_registry data not found; emitting addresses only "
                  "(run gen_registry first for named routines)", file=sys.stderr)
            reg = None

    sorted_addrs = collect_handler_addrs(overlay)
    cards_dir = args.out_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    registry: list[tuple[int, str, str]] = []  # (cid, module_name, card_name)
    n_ok = n_fail = 0
    for entry in iter_handler_entries(overlay):
        cid = entry["card_id"]
        name = KONAMI_ID_TO_CARD_NAME.get(cid, f"Unknown_{cid:04X}")
        mod_name = f"c{cid:05d}_i{entry['index']:04d}_{_safe_name(name)}"
        out_path = cards_dir / f"{mod_name}.py"
        try:
            text = _card_module_source(overlay, entry, sorted_addrs, reg)
            n_ok += 1
        except Exception as exc:  # noqa: BLE001
            n_fail += 1
            text = (f'"""Card 0x{cid:04X} ({name}) — shim generation failed."""\n'
                    f"# {type(exc).__name__}: {exc}\n")
        out_path.write_text(text, encoding="utf-8")
        registry.append((cid, mod_name, name))
        if args.limit and (n_ok + n_fail) >= args.limit:
            break

    (cards_dir / "__init__.py").write_text("", encoding="utf-8")

    init_lines = [
        '"""Effect shims generated from overlay0003 (Over the Nexus)."""',
        "",
        "# Map Konami ID -> (module_name, card_name)",
        "REGISTRY: dict[int, tuple[str, str]] = {",
    ]
    for cid, mod, name in registry:
        nm = name.replace("\\", "\\\\").replace("'", "\\'")
        init_lines.append(f"    0x{cid:04X}: ({mod!r}, '{nm}'),")
    init_lines.append("}")
    init_lines.append("")
    (args.out_dir / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")

    print(f"Wrote {n_ok} shim modules ({n_fail} failed) to {cards_dir}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

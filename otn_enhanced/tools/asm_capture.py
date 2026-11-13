"""Run the full build with thumb_asm.asm instrumented; dump every call (caller, base, resolved text, bytes).

    uv run python -m otn_enhanced.tools.asm_capture <out.nds> <calls.json>

Feeds asm_probe.py. The build output must still hash identically: the wrapper only records.
"""
import json
import sys

from otn_enhanced.asm import thumb_asm


def main(argv: list[str] | None = None) -> int:
    out_rom, out_json = (sys.argv[1:] if argv is None else argv)[:2]
    real, calls = thumb_asm.asm, []

    def traced(base, source, symbols=None):
        out = real(base, source, symbols)
        f = sys._getframe(1)
        calls.append({"module": f.f_globals.get("__name__"), "func": f.f_code.co_name, "line": f.f_lineno,
                      "base": base, "source": source, "symbols": symbols, "hex": out.hex()})
        return out

    thumb_asm.asm = traced                      # before the build imports any card, so they bind the wrapper
    try:
        from otn_enhanced import build
        rc = build.main(["--out", out_rom])
    finally:
        thumb_asm.asm = real
    with open(out_json, "w") as f:
        json.dump(calls, f)
    print("captured", len(calls), "asm() calls; build rc", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

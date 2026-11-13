"""Lower an `asm()` function that splices a macro helper, leaving a call to the (hand-ported) helper in its place.

    uv run python -m otn_enhanced.tools.port_helper_markers <module> <out.py>

`stub_port` skips an `asm()` block whose f-string holds a line like `{_player('r4', 'r2', 'r1')}` or `{body}`. This tool
swaps each such line for a one-line marker (`movs r5,#0x71`, `#0x72`, ...), lets `stub_port.convert_source` lower the whole
module, then turns each lowered marker back into `_helper(b, R4, R2, ...)` (`{body}` / `{tail}` become the bare words
BODY / TAIL for you to write). The result goes to <out.py>; it does NOT touch the card module: check it, copy it over,
then hand-port the helper itself as `def _helper(b: EffectBuilder, ...)` (HOWTO "Hand-porting a macro helper").

Run `stub_port <module> --apply` first so the golden rows exist and the other blocks are converted.
Not handled (do by hand): a placeholder inline after a label (`st3:{f()}`), helpers that take non-register strings other
than labels, text built by a function that is not a single `{name(args)}` line.
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from otn_enhanced.tools.stub_port import convert_source


def _arg(a: str) -> str:
    a = a.strip()
    return a[1:-1].upper() if re.fullmatch(r'["\']r\d["\']', a) else a


def main(module: str, out: str) -> None:
    mod = importlib.import_module(f"otn_enhanced.cards.{module}")
    src = Path(mod.__file__).read_text(encoding="utf-8")
    calls: list[str] = []

    def marker(m):
        calls.append(m.group(1))
        return f"        movs r5,#{0x70 + len(calls)}"     # r5, not r0-r3: a marker before a literal call is absorbed as an argument

    masked = re.sub(r"^\s*\{([A-Za-z_]\w*\([^)]*\)|tail|body)\}$", marker, src, flags=re.M)
    print(len(calls), calls)
    new, results = convert_source(masked, vars(mod))
    for r in results:
        print(r.func, r.ok, r.reason)
    for i, c in enumerate(calls, 1):
        pat = re.compile(r'(\w+)\.insn\("MOV", "R5, #0x%X"\)' % (0x70 + i))   # the builder is `b`, or `prog` if `b` is taken
        found = pat.findall(new)
        assert len(found) == 1, (hex(0x70 + i), found)
        if c in ("tail", "body"):
            rep = c.upper()
        else:
            name, args = c[:c.index("(")], c[c.index("(") + 1:-1]
            rep = f"{name}({', '.join([found[0]] + [_arg(a) for a in args.split(',') if a.strip()])})"
        new = pat.sub(lambda m: rep, new)
    Path(out).write_text(new, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

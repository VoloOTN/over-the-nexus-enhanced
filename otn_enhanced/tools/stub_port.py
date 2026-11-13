"""Convert text-assembler blocks (`asm(base, f\"\"\"...\"\"\")`) into EffectBuilder code, checked against golden bytes.

    uv run python -m otn_enhanced.tools.stub_port cards.soul_charge            # report only
    uv run python -m otn_enhanced.tools.stub_port cards.soul_charge --apply    # rewrite the file

Each `asm()` call is lowered line by line: labels, `ldr rN,=X`, `bl X`, branches and plain instructions become
`b.label` / `b.ldr_const` / `b.bl` / `b.insn`; f-string placeholders stay the original Python expressions. The
four turn-log shapes become `b.turnlog_query` / `b.turnlog_post`. The call site becomes
`b.assemble(base, pad="nop")`, so the bytes cannot move. A block is skipped, with a reason, when it cannot be
lowered exactly (a placeholder that splices whole lines, a `bl` to an unknown form, ...).

`--apply` writes the file, then compares every converted function the golden data covers; any mismatch restores
the original file. Converted functions that take only `base` are added to `tests/golden_ported.json`.
"""
from __future__ import annotations

import ast
import collections
import importlib
import inspect
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.asm.effect_builder import PRIMITIVES
from otn_enhanced.tools.asm_probe import BRANCHES, FLAGGED, _fix_operands, load_calls

_PRIM_BY_ADDR = {p.addr: (name, p) for name, p in PRIMITIVES.items()}

PKG = Path(__file__).resolve().parents[1]
QUERY_LIT, POST_LIT = 0x021A14E9, 0x021D2585          # turn-log routines | 1, as stubs write them
_TOKEN = re.compile(r"@@(\d+)@@")


class Unsupported(Exception):
    pass


@dataclass
class Result:
    func: str
    line: int
    ok: bool
    reason: str = ""
    ops: int = 0
    idioms: int = 0
    note: str = ""


# ------------------------------------------------------------------ text -> ops

def _split_text(arg: ast.expr, src: str) -> tuple[str, list[str]]:
    """The asm text with each placeholder replaced by @@n@@, and the placeholders' expression sources."""
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value, []
    if not isinstance(arg, ast.JoinedStr):
        raise Unsupported("text is not a literal or f-string")
    out, exprs = [], []
    for v in arg.values:
        if isinstance(v, ast.Constant):
            out.append(v.value)
            continue
        if v.conversion != -1 or (v.format_spec and any(not isinstance(x, ast.Constant) for x in v.format_spec.values)):
            raise Unsupported("placeholder with a conversion or dynamic format")
        out.append(f"@@{len(exprs)}@@")
        exprs.append(ast.get_source_segment(src, v.value))
    return "".join(out), exprs


def _value(text: str, exprs: list[str], ns: dict):
    """(python source, int or None) for `0x@@n@@`, `@@n@@` or an integer literal; else Unsupported."""
    m = re.fullmatch(r"(?:0[xX])?@@(\d+)@@", text)
    if m:
        e = exprs[int(m.group(1))]
        try:
            v = eval(e, ns)
        except Exception:
            v = None
        return e, v if isinstance(v, int) else None
    if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", text):
        return text, int(text, 0)
    raise Unsupported(f"unhandled value {text!r}")


def _lower(text: str, exprs: list[str], ns: dict) -> list[tuple]:
    ops: list[tuple] = []
    for raw in text.splitlines():
        line = raw.split(";")[0].split("//")[0].strip()
        while line:
            m = re.match(r"^([A-Za-z_]\w*):\s*", line)
            if not m:
                break
            ops.append(("label", m.group(1)))
            line = line[m.end():].strip()
        if not line:
            continue
        mnem, _, rest = line.partition(" ")
        mnem = mnem.lower()
        if "@@" in mnem or _TOKEN.fullmatch(line):
            raise Unsupported("a placeholder splices whole lines of assembly")
        args = ([rest.strip()] if (mnem in ("push", "pop") or rest.strip().startswith("{"))
                else ([o.strip() for o in rest.split(",")] if rest.strip() else []))
        if mnem == "ldr" and len(args) >= 2 and args[1].startswith("="):
            rd = re.fullmatch(r"r([0-7])", args[0].lower())
            if not rd:
                raise Unsupported("ldr into a high register")
            src, val = _value(args[1][1:].strip(), exprs, ns)
            ops.append(("ldrc", int(rd.group(1)), src, val))
        elif mnem == "bl" and len(args) == 1:
            if re.fullmatch(r"[A-Za-z_]\w*", args[0]):
                ops.append(("bllabel", args[0]))
            else:
                src_, val_ = _value(args[0], exprs, ns)
                ops.append(("bl", src_, val_))
        elif mnem in BRANCHES and len(args) == 1:
            if not re.fullmatch(r"[A-Za-z_]\w*", args[0]):
                raise Unsupported("branch to a computed target")
            ops.append(("insn", mnem.upper(), args[0]))
        elif mnem == "blx":
            ops.append(("insn", "BLX", args[0].upper()))
        else:
            operands = _fix_operands(args)
            if mnem in ("push", "pop"):
                operands = re.sub(r"\s*,\s*", ", ", operands)         # {R4, LR}, as hand-written builder code has it
            ops.append(("insn", FLAGGED.get(mnem, mnem.upper()), operands))
    return ops


# ------------------------------------------------------------------ turn-log idioms

def _imm(op, reg: str):
    """K for `MOV <reg>, #K` (as python source), else None."""
    if op[0] != "insn" or op[1] != "MOV":
        return None
    m = re.fullmatch(rf"{reg}, #(0x[0-9A-F]+|\d+|@@\d+@@)", op[2])
    return m.group(1) if m else None


def _kind_src(k: str, exprs: list[str]) -> str:
    t = _TOKEN.fullmatch(k)
    if t:
        return exprs[int(t.group(1))]
    v = int(k, 0)
    return str(v) if v < 10 else k


def _query(win: list[tuple]):
    """(ops consumed, cid source, kind) for [MOV R1,#0xB] [ldr R2,=X or R2 preset] [MOV R3,#K], else None."""
    k = _imm(win[-1], "R3") if win else None
    if k is None:
        return None
    if len(win) >= 3 and win[-2][0] == "ldrc" and win[-2][1] == 2 and _imm(win[-3], "R1") in ("0xB", "11"):
        return 3, win[-2][2], k
    if len(win) >= 2 and _imm(win[-2], "R1") in ("0xB", "11"):
        return 2, "R2", k
    return None


def _post(win: list[tuple]):
    """(ops consumed, cid source, kind) for [ldr R1,=X or R1 preset] [MOV R2,#K] [MOV R3,#0], else None."""
    if len(win) < 2 or _imm(win[-1], "R3") not in ("0x0", "0"):
        return None
    k = _imm(win[-2], "R2")
    if k is None:
        return None
    if len(win) >= 3 and win[-3][0] == "ldrc" and win[-3][1] == 1:
        return 3, win[-3][2], k
    return 2, "R1", k


def _idioms(ops: list[tuple], exprs: list[str]) -> tuple[list[tuple], int]:
    """Replace the proven turn-log call shapes (argument setup + `ldr rS,=ADDR|1 ; blx rS`) with one idiom call."""
    out, n, i = list(ops), 0, 1
    while i < len(out):
        j = i - 1
        if (out[i][0] == "insn" and out[i][1] == "BLX" and out[j][0] == "ldrc"
                and out[j][3] in (QUERY_LIT, POST_LIT) and out[j][1] >= 4 and out[i][2] == f"R{out[j][1]}"):
            query = out[j][3] == QUERY_LIT
            found = (_query if query else _post)(out[:j])
            if found:
                take, cid, kind = found
                name = "turnlog_query" if query else "turnlog_post"
                call = f"b.{name}(R0, {cid}, {_kind_src(kind, exprs)}, via=R{out[j][1]})"
                out[j - take:i + 1] = [("idiom", call)]
                n += 1
                i = j - take + 1
        i += 1
    return out, n


def _setup(op: tuple, exprs: list[str]):
    """(register, argument source) when *op* is exactly what EffectBuilder's argument marshalling emits."""
    if op[0] == "insn" and op[1] == "ADD":
        m = re.fullmatch(r"R([0-3]), R([0-7]), #0x0", op[2])
        if m and int(m.group(2)) > int(m.group(1)):          # marshalling refuses to read a register it already wrote
            return int(m.group(1)), f"R{m.group(2)}"
    elif op[0] == "insn" and op[1] == "MOV":
        m = re.fullmatch(r"R([0-3]), #(0x[0-9A-F]+|\d+|@@\d+@@)", op[2])
        if m:
            return int(m.group(1)), _kind_src(m.group(2), exprs)
    elif op[0] == "ldrc" and op[1] <= 3 and op[3] is not None and op[3] > 0xFF:   # marshalling uses MOV up to 0xFF
        return op[1], op[2]
    return None


def _calls(ops: list[tuple], exprs: list[str]) -> tuple[list[tuple], int]:
    """Rewrite `[arg setup] ldr rN,=ADDR ; blx rN` and `[arg setup] bl ADDR` as one `b.call` / `b.call_addr`."""
    out, n, i = list(ops), 0, 0
    while i < len(out):
        op = out[i]
        if op[0] == "insn" and op[1] == "BLX" and i and out[i - 1][0] == "ldrc" \
                and op[2] == f"R{out[i - 1][1]}" and out[i - 1][3] is not None:
            via, target, val, head = out[i - 1][1], out[i - 1][2], out[i - 1][3], i - 1
        elif op[0] == "bl":
            via, target, val, head = None, op[1], op[2], i
        else:
            i += 1
            continue
        args, k, prev = {}, head, 4
        while k and (s := _setup(out[k - 1], exprs)) and s[0] < prev:
            args[s[0]], prev, k = s[1], s[0], k - 1
        top = max(args, default=-1)
        if via is not None and via <= top:                    # the call register would clobber an argument
            i += 1
            continue
        arg_list = [args.get(p, f"R{p}") for p in range(top + 1)]   # a position set earlier is passed as itself
        tail = f", via=R{via}" if via is not None else ""
        prim = _PRIM_BY_ADDR.get(val & ~1) if val is not None else None
        arm = via is not None and not val & 1
        if prim and (via is None or arm == prim[1].arm):
            call = f'b.call("{prim[0]}"' + "".join(f", {a}" for a in arg_list) + f"{tail})"
        else:
            tgt = re.sub(r"\s*\|\s*1$", "", target)
            if re.fullmatch(r"0[xX][0-9a-fA-F]+", tgt):
                tgt = f"0x{int(tgt, 16) & ~1:08X}"
            call = f"b.call_addr({tgt}" + "".join(f", {a}" for a in arg_list) + tail + (", arm=True" if arm else "") + ")"
        out[k:i + 1] = [("idiom", call)]
        n += 1
        i = k + 1
    return out, n


# ------------------------------------------------------------------ ops -> python

def _fstring_operands(operands: str, exprs: list[str]) -> str:
    if not _TOKEN.search(operands):
        return json.dumps(operands)
    parts = []
    for piece in re.split(r"(@@\d+@@)", operands):
        t = _TOKEN.fullmatch(piece)
        if not t:
            parts.append(piece.replace("{", "{{").replace("}", "}}"))
        elif parts and parts[-1].endswith(("#", "#0x")):         # `#{X}` or `#0x{X:X}`
            prefix = "" if parts[-1].endswith("0x") else "0x"
            parts.append(prefix + "{" + exprs[int(t.group(1))] + ":X}")
        else:
            raise Unsupported("a placeholder outside an immediate")
    return 'f"' + "".join(parts).replace('"', '\\"') + '"'


def _render(ops: list[tuple], exprs: list[str], name: str) -> list[str]:
    out = []
    for op in ops:
        k = op[0]
        if k == "label":
            out.append(f'{name}.label("{op[1]}")')
        elif k == "ldrc":
            out.append(f"{name}.ldr_const({op[1]}, {op[2]})")
        elif k == "bl":
            out.append(f"{name}.bl({op[1]})")
        elif k == "bllabel":
            out.append(f'{name}.bl_label("{op[1]}")')
        elif k == "idiom":
            out.append(op[1].replace("b.", f"{name}.", 1))
        else:
            out.append(f'{name}.insn("{op[1]}"' + (f", {_fstring_operands(op[2], exprs)})" if op[2] else ")"))
    return out


# ------------------------------------------------------------------ source rewrite

def _is_text(n: ast.AST) -> bool:
    return isinstance(n, ast.JoinedStr) or (isinstance(n, ast.Constant) and isinstance(n.value, str))


def _resolve_text(arg: ast.expr, fnode, tree: ast.Module, call: ast.Call):
    """(text node, assignment to delete or None, note) behind `asm(base, <arg>)`.

    A name resolves through its single local assignment from a literal (deleted when this call was its only use)
    or a single module-level literal (kept: other code may import it).
    """
    if _is_text(arg):
        return arg, None, ""
    if not isinstance(arg, ast.Name):
        raise Unsupported("text is not a literal or f-string")
    hit = lambda s: isinstance(s, ast.Assign) and len(s.targets) == 1 and getattr(s.targets[0], "id", None) == arg.id  # noqa: E731
    local = [s for s in ast.walk(fnode) if hit(s)]
    if local:
        uses = [n for n in ast.walk(fnode) if isinstance(n, ast.Name) and n.id == arg.id and isinstance(n.ctx, ast.Load)]
        rebound = [n for n in ast.walk(fnode) if isinstance(n, ast.AugAssign) and getattr(n.target, "id", None) == arg.id]
        if len(local) == 1 and not rebound and _is_text(local[0].value) and local[0].end_lineno < call.lineno:
            return local[0].value, (local[0] if len(uses) == 1 else None), ""
        raise Unsupported("text variable is not a single literal")
    glob = [s for s in tree.body if hit(s)]
    if len(glob) == 1 and _is_text(glob[0].value):
        return glob[0].value, None, f"{arg.id} is no longer used here; delete it if nothing else imports it"
    raise Unsupported("text variable is not a single literal")


def convert_source(src: str, ns: dict) -> tuple[str, list[Result]]:
    """Rewrite every convertible `asm()` call in *src*; *ns* supplies constants for idiom recognition."""
    b = src.encode("utf-8")
    starts = [0] + [i + 1 for i, c in enumerate(b) if c == 10]
    off = lambda line, col: starts[line - 1] + col                                   # noqa: E731
    tree = ast.parse(src)
    parent = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    edits, results, needed = [], [], set()
    stmt_calls: dict = {}
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "asm"]
    for call in sorted(calls, key=lambda c: (c.lineno, c.col_offset)):
        fn, node = "<module>", call
        stmt = None
        while node in parent:
            node = parent[node]
            if isinstance(node, (ast.Lambda, ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp)):
                stmt = None
                break
            if stmt is None and isinstance(node, ast.stmt):
                stmt = node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = node.name
                break
        res = Result(fn, call.lineno, False)
        results.append(res)
        drop = None
        try:
            if stmt is None or fn == "<module>":
                raise Unsupported("not directly inside a function statement")
            if len(call.args) != 2 or call.keywords:
                raise Unsupported("asm() with symbols or keywords")
            if stmt_calls.setdefault(stmt, call) is not call:
                raise Unsupported("two asm() calls in one statement")
            used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            name = "b" if "b" not in used else "prog"
            text_node, drop, res.note = _resolve_text(call.args[1], node, tree, call)
            text, exprs = _split_text(text_node, src)
            ops = _lower(text, exprs, ns)
            ops, res.idioms = _idioms(ops, exprs)
            ops, n_calls = _calls(ops, exprs)
            res.idioms += n_calls
            lines = _render(ops, exprs, name)
            res.ops = len(ops)
        except Unsupported as e:
            res.reason = str(e)
            continue
        base_src = ast.get_source_segment(src, call.args[0])
        ind = " " * stmt.col_offset
        body = [f"{ind}{name} = EffectBuilder()"] + [f"{ind}{x}" for x in lines]
        edits.append((off(stmt.lineno, 0), off(stmt.lineno, 0), ("\n".join(body) + "\n").encode()))
        edits.append((off(call.lineno, call.col_offset), off(call.end_lineno, call.end_col_offset),
                      f'{name}.assemble({base_src}, pad="nop")'.encode()))
        if drop is not None:                         # the text variable's only use was this call
            edits.append((off(drop.lineno, 0), off(drop.end_lineno + 1, 0), b""))
        idiom_calls = " ".join(o[1] for o in ops if o[0] == "idiom")
        needed |= {"EffectBuilder"} | set(re.findall(r"\bR[0-7]\b", idiom_calls))   # registers named by idiom calls
        res.ok = True
    if not edits:
        return src, results
    for s, e, new in sorted(edits, reverse=True):
        b = b[:s] + new + b[e:]
    return _add_imports(b.decode("utf-8"), needed, still_uses_asm=len(calls) > sum(r.ok for r in results)), results


def _add_imports(src: str, names: set[str], still_uses_asm: bool) -> str:
    tree = ast.parse(src)
    mod = "otn_enhanced.asm.effect_builder"
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module == mod:
            have = {a.name for a in n.names}
            allnames = sorted(have | names, key=lambda x: (x != "EffectBuilder", x))
            lines = src.split("\n")
            lines[n.lineno - 1:n.end_lineno] = [f"from {mod} import {', '.join(allnames)}"]
            src = "\n".join(lines)
            break
    else:
        last = max((n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))), key=lambda n: n.end_lineno)
        lines = src.split("\n")
        lines.insert(last.end_lineno, f"from {mod} import {', '.join(sorted(names, key=lambda x: (x != 'EffectBuilder', x)))}")
        src = "\n".join(lines)
    return src


# ------------------------------------------------------------------ CLI

def _golden_rows(dotted: str) -> list[dict]:
    return [r for r in load_calls(str(PKG / "tests" / "golden_asm.json.gz")) if r["module"] == dotted]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    apply = "--apply" in argv
    status = 0
    for target in (a for a in argv if not a.startswith("--")):
        dotted = target if target.startswith("otn_enhanced.") else f"otn_enhanced.{target}"
        mod = importlib.import_module(dotted)
        path = Path(mod.__file__)
        old = path.read_text(encoding="utf-8")
        new, results = convert_source(old, vars(mod))
        ok = [r for r in results if r.ok]
        print(f"{dotted}: {len(ok)}/{len(results)} asm() blocks convertible, "
              f"{sum(r.idioms for r in ok)} turn-log idiom(s)")
        for r in results:
            print(f"   {'ok  ' if r.ok else 'SKIP'} {r.func}:{r.line}"
                  + (f"  ({r.ops} ops, {r.idioms} idioms)" if r.ok else f"  -- {r.reason}")
                  + (f"  [{r.note}]" if r.note else ""))
        if not apply or not ok:
            continue
        path.write_text(new, encoding="utf-8", newline="\n")
        try:
            orig = {n: f for n, f in vars(mod).items() if inspect.isfunction(f)}
            importlib.invalidate_caches()
            mod = importlib.reload(mod)
            checked, bad, rows = 0, [], []
            blocks = collections.Counter(r.func for r in results)
            for g in _golden_rows(dotted):
                f = getattr(mod, g["func"], None)
                if f is None or g["func"] not in {r.func for r in ok} or blocks[g["func"]] != 1:
                    continue              # a function with several asm() blocks returns more than one row's bytes
                if len(inspect.signature(f).parameters) != 1:     # golden rows do not record other arguments,
                    continue                                       # even defaulted ones: the build proves these
                if orig[g["func"]](g["base"]).hex() != g["hex"]:
                    continue              # the function post-processes the asm() bytes: its golden row is not its output
                checked += 1
                if f(g["base"]).hex() != g["hex"]:
                    bad.append(f"{g['func']} @0x{g['base']:08X}")
                rows.append({"module": dotted, "func": g["func"], "base": g["base"], "hex": g["hex"]})
            if bad:
                raise AssertionError(f"bytes changed: {bad}")
        except BaseException as e:
            path.write_text(old, encoding="utf-8", newline="\n")
            print(f"   RESTORED {path.name}: {type(e).__name__}: {e}")
            status = 1
            continue
        gp = PKG / "tests" / "golden_ported.json"
        have = json.loads(gp.read_text(encoding="utf-8"))
        keys = {(r["module"], r["func"], r["base"]) for r in have}
        have += [r for r in rows if (r["module"], r["func"], r["base"]) not in keys]
        gp.write_text(json.dumps(have, indent=1), encoding="utf-8")
        print(f"   applied; {checked} stub(s) byte-identical to golden and added to golden_ported.json; "
              f"{len(ok) - len({r['func'] for r in rows})} converted function(s) not golden-checkable (build proves them)")
    return status


if __name__ == "__main__":
    raise SystemExit(main())

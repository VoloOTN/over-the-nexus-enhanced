"""Load ``docs/engine/*.yaml`` facts and run their proof snippets.

The KB YAML is emitted by :mod:`author_facts` in a deliberately *regular*
subset (a top-level list of flat mappings, each ending in a ``proof: |`` block
literal), so it parses with PyYAML when available and with a small vendored
fallback parser otherwise — the runner must work on a clean checkout that has
no third-party YAML installed.
"""
from __future__ import annotations

import struct  # noqa: F401  (available to proof snippets)
from dataclasses import dataclass, field
from pathlib import Path

from otn_enhanced.knowledge.env import Env
from otn_enhanced.knowledge.helpers import Helpers, Skip

DOCS_ENGINE = Path(__file__).resolve().parents[1] / "docs" / "engine"


@dataclass
class Fact:
    id: str
    claim: str
    subsystem: str
    confidence: str                 # VERIFIED | ANCHORED | UNVERIFIED
    proof: str | None = None
    address: int | None = None
    oracle: str | None = None
    sources: list = field(default_factory=list)
    next_experiment: str | None = None
    corrected_by: str | None = None
    file: str = ""


@dataclass
class Result:
    fact: Fact
    status: str                     # PASS | FAIL | UNVERIFIED
    message: str = ""


# ---------------------------------------------------------------------------
# YAML loading (PyYAML if present, else a fallback for our own schema)
# ---------------------------------------------------------------------------
def _scalar(v: str):
    v = v.strip()
    if v == "" or v == "~" or v == "null":
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].encode().decode("unicode_escape") if v[0] == '"' else v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_scalar(x) for x in inner.split(",")] if inner else []
    low = v.lower()
    if low.startswith("0x"):
        try:
            return int(v, 16)
        except ValueError:
            return v
    if v.lstrip("-").isdigit():
        return int(v)
    return v


def _fallback_parse(text: str) -> list[dict]:
    """Parse the regular ``- key: value`` + trailing ``proof: |`` block subset."""
    items: list[dict] = []
    lines = text.splitlines()
    i = 0
    cur: dict | None = None
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if raw.startswith("- "):                        # new list item
            cur = {}
            items.append(cur)
            raw = "  " + raw[2:]                          # normalise to a 2-indent key
        if cur is None:
            i += 1
            continue
        body = raw[2:]                                   # drop the 2-space item indent
        key, _, val = body.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "|":                                   # block literal (proof)
            block: list[str] = []
            i += 1
            while i < len(lines):
                bl = lines[i]
                if bl.strip() == "":
                    block.append("")
                    i += 1
                    continue
                if bl.startswith("    "):                 # 4-space block indent
                    block.append(bl[4:])
                    i += 1
                else:
                    break
            cur[key] = "\n".join(block).rstrip() + "\n"
            continue
        cur[key] = _scalar(val)
        i += 1
    return items


def _load_yaml(text: str) -> list[dict]:
    try:
        import yaml
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "facts" in data:
            return data["facts"]
        return data or []
    except ModuleNotFoundError:
        return _fallback_parse(text)


def load_facts(subsystem: str | None = None) -> list[Fact]:
    facts: list[Fact] = []
    for path in sorted(DOCS_ENGINE.glob("*.yaml")):
        if path.name == "allocations.yaml":
            continue                                     # the slot ledger, not a fact set
        for d in _load_yaml(path.read_text(encoding="utf-8")):
            if not isinstance(d, dict) or "id" not in d:
                continue
            f = Fact(
                id=d["id"],
                claim=d.get("claim", ""),
                subsystem=d.get("subsystem", path.stem),
                confidence=d.get("confidence", "UNVERIFIED"),
                proof=d.get("proof"),
                address=d.get("address"),
                oracle=d.get("oracle"),
                sources=d.get("sources") or [],
                next_experiment=d.get("next_experiment"),
                corrected_by=d.get("corrected_by"),
                file=path.name,
            )
            if subsystem and f.subsystem != subsystem:
                continue
            facts.append(f)
    return facts


# ---------------------------------------------------------------------------
# Proof execution
# ---------------------------------------------------------------------------
def run_fact(fact: Fact, env: Env, h: Helpers) -> Result:
    if not fact.proof or not fact.proof.strip():
        return Result(fact, "UNVERIFIED", "no proof (narrative / needs experiment)")
    ns = {"env": env, "h": h, "Skip": Skip, "struct": struct,
          "addr": fact.address, "AssertionError": AssertionError}
    try:
        exec(compile(fact.proof, f"<proof {fact.id}>", "exec"), ns)
    except Skip as e:
        return Result(fact, "UNVERIFIED", str(e))
    except AssertionError as e:
        return Result(fact, "FAIL", str(e) or "assertion failed")
    except Exception as e:                               # a broken proof is a FAIL
        return Result(fact, "FAIL", f"{type(e).__name__}: {e}")
    return Result(fact, "PASS", "")


def run_all(env: Env, facts: list[Fact]) -> list[Result]:
    h = Helpers(env)
    return [run_fact(f, env, h) for f in facts]

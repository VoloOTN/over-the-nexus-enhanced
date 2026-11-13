"""Run the ground-truth assertions in ``data/golden.toml``.

This is the gate on the economy model.  Coefficients are free to move as long as
Smashing Ground stays 0.00, Share the Pain stays −1.00, Dark Hole's floor stays
0.00 with a gross ceiling of 5.00, and Rekindling still asks for FIRE monsters
with 200 DEF and *no* level restriction.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.deckgen import cardpool
from otn_enhanced.deckgen.economy import economy
from otn_enhanced.deckgen.model import Card, ParsedCard
from otn_enhanced.deckgen.params import Params, default

GOLDEN_TOML = Path(__file__).resolve().parent / "data" / "golden.toml"


@dataclass
class Failure:
    card: str
    field: str
    expected: object
    actual: object

    def __str__(self) -> str:
        return f"{self.card}: {self.field} expected {self.expected!r}, got {self.actual!r}"


def _check_wants(name: str, pc: ParsedCard, spec: dict) -> list[Failure]:
    out: list[Failure] = []
    preds = [p for p, _ in pc.wants]
    if not any(k.startswith("want_") for k in spec):
        return out
    if not preds:
        return [Failure(name, "wants", "at least one predicate", [])]

    def any_pred(fn) -> bool:
        return any(fn(p) for p in preds)

    if "want_attribute" in spec:
        want = frozenset(spec["want_attribute"])
        if not any_pred(lambda p: p.attribute == want):
            out.append(Failure(name, "want_attribute", sorted(want), [sorted(p.attribute) if p.attribute else None for p in preds]))
    if "want_def" in spec:
        n = spec["want_def"]
        if not any_pred(lambda p: p.def_ is not None and p.def_[1] == n):
            out.append(Failure(name, "want_def", n, [p.def_ for p in preds]))
    if "want_atk" in spec:
        n = spec["want_atk"]
        if not any_pred(lambda p: p.atk is not None and p.atk[1] == n):
            out.append(Failure(name, "want_atk", n, [p.atk for p in preds]))
    if "want_level" in spec:
        n = spec["want_level"]
        if not any_pred(lambda p: p.level is not None and p.level[1] == n):
            out.append(Failure(name, "want_level", n, [p.level for p in preds]))
    if "want_archetype" in spec:
        a = spec["want_archetype"]
        if not any_pred(lambda p: (p.archetype or "").lower() == a.lower()):
            out.append(Failure(name, "want_archetype", a, [p.archetype for p in preds]))
    if spec.get("want_level_absent"):
        offenders = [p.raw for p in preds if p.level is not None]
        if offenders:
            out.append(Failure(name, "want_level_absent", "no level key", offenders))
    return out


def run(
    cards: list[Card] | None = None,
    parsed: dict[int, ParsedCard] | None = None,
    p: Params | None = None,
) -> list[Failure]:
    """Return every golden-test failure; an empty list means the model is sound."""
    from otn_enhanced.deckgen.text.parse import load_parsed

    if cards is None or parsed is None:
        cards, parsed, _ = load_parsed()
    p = p or default()

    spec_all = tomllib.loads(GOLDEN_TOML.read_text(encoding="utf-8"))
    failures: list[Failure] = []

    for name, specs in spec_all.items():
        spec = specs[0] if isinstance(specs, list) else specs
        try:
            card = cardpool.find(cards, name)
        except KeyError as exc:
            failures.append(Failure(name, "lookup", "present in pool", str(exc)))
            continue
        pc = parsed[card.cid]
        econ = economy(card, pc, p)
        tol = float(spec.get("tol", 0.15))

        for field in ("exp", "min", "max", "gross_max"):
            if field in spec:
                actual = getattr(econ, field)
                if abs(actual - float(spec[field])) > tol:
                    failures.append(
                        Failure(name, field, f"{float(spec[field]):+.2f}+-{tol}", f"{actual:+.2f}")
                    )
        if "context_sensitive" in spec and econ.context_sensitive != spec["context_sensitive"]:
            failures.append(
                Failure(name, "context_sensitive", spec["context_sensitive"], econ.context_sensitive)
            )
        for tag in spec.get("tags", []):
            if tag not in pc.tags:
                failures.append(Failure(name, f"tag {tag}", "present", sorted(pc.tags)))
        failures.extend(_check_wants(name, pc, spec))

    return failures


def main() -> int:
    failures = run()
    if not failures:
        spec = tomllib.loads(GOLDEN_TOML.read_text(encoding="utf-8"))
        print(f"golden: all {len(spec)} cards pass")
        return 0
    print(f"golden: {len(failures)} FAILURE(S)")
    for f in failures:
        print(f"  {f}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

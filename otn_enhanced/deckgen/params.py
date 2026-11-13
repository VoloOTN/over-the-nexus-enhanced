"""Load ``data/params.toml`` — the single source of every tunable coefficient."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
PARAMS_TOML = DATA_DIR / "params.toml"


@dataclass(frozen=True)
class BoardState:
    """A board the card is being evaluated against."""

    own_mon: float
    opp_mon: float
    own_st: float
    opp_st: float

    def count(self, side: str, card_class: str | None) -> float:
        """How many cards of *card_class* the given side has on the field."""
        spell_trap = card_class in ("spell", "trap")
        if side == "opponent":
            return self.opp_st if spell_trap else self.opp_mon
        if side == "you":
            return self.own_st if spell_trap else self.own_mon
        return (self.opp_st + self.own_st) if spell_trap else (self.opp_mon + self.own_mon)


class Params:
    """Dotted read-only access to the parameter table."""

    def __init__(self, raw: dict[str, Any]):
        self._raw = raw
        # Resolved-path memo.  deckscore.score reads ~30 coefficients and runs
        # tens of thousands of times per build, so this was 3.2M splits and dict
        # walks (4.6s of a 164s profile) to re-derive constants.  Safe because a
        # Params is immutable in practice: training._with deep-copies _raw and
        # constructs a NEW Params rather than mutating one.
        self._cache: dict[str, Any] = {}

    def __getitem__(self, path: str) -> Any:
        try:
            return self._cache[path]
        except KeyError:
            pass
        node: Any = self._raw
        for part in path.split("."):
            node = node[part]
        self._cache[path] = node
        return node

    def get(self, path: str, default: Any = None) -> Any:
        try:
            return self[path]
        except (KeyError, TypeError):
            return default

    def table(self, name: str) -> dict[str, Any]:
        return dict(self._raw.get(name, {}))

    @property
    def boards(self) -> dict[str, BoardState]:
        return {k: BoardState(**v) for k, v in self._raw["board"].items()}

    def with_profile(self, name: str) -> "Params":
        """This table with ``[profile.<name>]`` overrides applied.

        A profile is a *sparse* override of dotted paths, not a second copy of
        the table::

            [profile.randomised]
            "power.w_staple" = 0.0

        It exists because the model has two genuinely different feature sets.
        On a stock ROM, per-cid tournament play rate is real evidence and is the
        largest single signal.  After a randomiser run that lookup is invalid —
        the cid no longer holds the card that earned the statistic — and
        ``score_pool`` falls back to per-*tag* rates.  Those are a different
        feature with a different scale, but they were being read through
        coefficients fitted for the per-cid one.  A profile is where the
        coefficients fitted for the fallback live.

        Returns *self* when the profile does not exist, so callers need no
        branch.
        """
        overrides = (self._raw.get("profile") or {}).get(name)
        if not overrides:
            return self
        import copy

        raw = copy.deepcopy(self._raw)
        for path, value in overrides.items():
            node, parts = raw, path.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
        return Params(raw)

    @classmethod
    def load(cls, path: Path = PARAMS_TOML) -> "Params":
        return cls(tomllib.loads(path.read_text(encoding="utf-8")))


_DEFAULT: Params | None = None


def default() -> Params:
    """The process-wide parameter set, loaded once."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Params.load()
    return _DEFAULT

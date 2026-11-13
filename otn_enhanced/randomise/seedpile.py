"""The deck seed pile: loading, validating, and whether deckgen can run at all."""
from __future__ import annotations

import json
import os
import re

from otn_enhanced.randomise.cardprop import ATTRIBUTES, RACES

DECKGEN_UNAVAILABLE = (
    "deckgen is not available here (its card pool inputs or data files are missing) "
    "-- run from the repo checkout with `uv run` to generate decks"
)


class SeedPileError(Exception):
    """The seed pile exists but could not be used.  Reported, never a traceback."""


def load_seed_pile(path: str) -> list[dict]:
    """Read the flat seed pile.  Every deck draws from it at random.

    A missing file is simply an empty pile.  A malformed one raises
    :class:`SeedPileError` with the parser's line and column, because a stray
    trailing comma in a hand-edited JSON file is by far the likeliest failure and
    a bare ``JSONDecodeError`` traceback is a poor way to say so.
    """
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        raise SeedPileError(
            f"{path} is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}). "
            "A trailing comma after the last entry is the usual cause."
        ) from None
    pile = payload.get("seed_pile", []) if isinstance(payload, dict) else payload
    if not isinstance(pile, list):
        raise SeedPileError(f"{path}: 'seed_pile' must be a list")

    good: list[dict] = []
    for i, recipe in enumerate(pile):
        if not isinstance(recipe, dict):
            raise SeedPileError(f"{path}: seed_pile[{i}] is not an object")
        seeds = [s for s in (recipe.get("seed") or []) if isinstance(s, str) and s.strip()]
        if not seeds:
            # An entry with no usable card name (e.g. "seed": [""]) is a
            # half-finished line, not a request to build from nothing.
            continue
        good.append({**recipe, "seed": seeds})
    return good


def deckgen_available() -> bool:
    """Can deckgen actually *run* here -- not merely be imported.

    The distinction matters in a PyInstaller bundle: its analysis pulls the
    deckgen modules in as code whether or not their ``.toml`` / ``.json`` / ``.pkl``
    data came along.  Reporting "available" on the strength of the import alone
    turned a clean "this needs the repo" message into a FileNotFoundError for
    ``deckgen/data/params.toml`` much later on.  ``resources.available()`` checks
    for the data files themselves, so a bundle that *does* ship them reports true.
    """
    try:
        import otn_enhanced.deckgen.search  # noqa: F401
        from otn_enhanced.deckgen import resources
    except Exception:
        return False
    return resources.available()


def deckgen_missing() -> list[str]:
    """Which deckgen data files are absent, for a precise message."""
    try:
        from otn_enhanced.deckgen import resources
    except Exception:
        return ["the otn_enhanced.deckgen package itself"]
    return resources.missing()


#: Keys a seed-pile recipe may carry.  Anything else is almost certainly a typo
#: (``allowed_type`` for ``allowed_types``), which would otherwise be ignored in
#: silence and produce a deck that quietly disregarded the constraint.
RECIPE_KEYS = frozenset({
    "seed", "size", "banlist", "allowed_types", "allowed_attributes",
    "beam", "candidates", "lam",
})

_NAME_PUNCT = re.compile(r"[^a-z0-9]+")


def _name_key(name: str) -> str:
    """Fold a card name for comparison.

    Deliberately close to deckgen's ``namematch.normalize``: drop non-ASCII (which
    also neutralises the Shift-JIS mojibake in the ROM's name table), lowercase,
    and collapse punctuation.  Only used for the standalone check; when deckgen is
    importable its own resolver is the authority.
    """
    ascii_only = name.encode("ascii", "ignore").decode("ascii")
    return _NAME_PUNCT.sub(" ", ascii_only.lower()).strip()


def validate_seed_pile(pile: list[dict], cid2name: dict[int, str],
                       cards=None) -> list[str]:
    """Check every recipe in the seed pile, returning a list of problems.

    Seed card names are the point of this: a typo only surfaces once deckgen has
    loaded its pool and reached that recipe, which on a 305-deck run can be twenty
    minutes in.  When *cards* (deckgen's pool) is supplied the names are resolved
    with ``cardpool.find``, which is authoritative and suggests near-matches;
    otherwise they are checked against the ROM's own name table, which is a subset
    of what deckgen accepts, so a miss is reported as unrecognised rather than
    wrong.
    """
    problems: list[str] = []
    rom_names = {_name_key(n) for n in cid2name.values() if n}
    races = {r.lower() for r in RACES.values() if r != "NONE"}
    attrs = {a.lower() for a in ATTRIBUTES.values() if a != "NONE"}

    find = None
    limits_named = None
    monster_filter = None
    if cards is not None:
        try:
            from otn_enhanced.deckgen.cardpool import find as _find
            from otn_enhanced.deckgen.constraints import Limits, MonsterFilter
            find, limits_named = _find, Limits.named
            monster_filter = MonsterFilter.parse
        except Exception:
            find = None

    for i, recipe in enumerate(pile):
        where = f"seed_pile[{i}]"

        unknown = sorted(set(recipe) - RECIPE_KEYS - {k for k in recipe if k.startswith("_")})
        if unknown:
            problems.append(f"{where}: unknown key(s) {unknown} "
                            f"-- valid keys are {sorted(RECIPE_KEYS)}")

        for name in recipe.get("seed", []):
            if find is not None:
                try:
                    find(cards, name)
                except KeyError as exc:
                    problems.append(f"{where}: {exc}".replace("\n", " "))
                except Exception as exc:  # noqa: BLE001
                    problems.append(f"{where}: seed {name!r} failed to resolve: {exc}")
            elif _name_key(name) not in rom_names:
                problems.append(
                    f"{where}: seed {name!r} is not a card name in this ROM "
                    "(it may still be a deckgen alias -- load the pool to confirm)")

        size = recipe.get("size", 40)
        if not isinstance(size, int) or not 40 <= size <= 60:
            problems.append(f"{where}: size {size!r} must be an integer 40..60")

        for key in ("allowed_types", "allowed_attributes"):
            if key in recipe and not isinstance(recipe[key], list):
                problems.append(f"{where}: {key} must be a list")

        if monster_filter is not None:
            # deckgen's own canonicaliser is the authority, and it is more
            # permissive than a literal table: it accepts "Winged-Beast" for
            # "Winged Beast" and "Sea-Serpent" for "Sea Serpent".  Rejecting those
            # here would send you chasing problems that are not problems.
            try:
                monster_filter(cards,
                               races=recipe.get("allowed_types"),
                               attributes=recipe.get("allowed_attributes"))
            except ValueError as exc:
                problems.append(f"{where}: {exc}")
        else:
            for key, vocab, label in (("allowed_types", races, "Type/Race"),
                                      ("allowed_attributes", attrs, "Attribute")):
                for v in recipe.get(key) or []:
                    if not isinstance(v, str) or v.lower().replace("-", " ") not in {
                            w.replace("-", " ") for w in vocab}:
                        problems.append(
                            f"{where}: {v!r} does not look like a {label} in this ROM "
                            "(deckgen may still accept it -- load the pool to confirm)")

        banlist = recipe.get("banlist", "none")
        if not isinstance(banlist, str):
            problems.append(f"{where}: banlist must be a string")
        elif banlist.lower() not in ("none", "off", "") and limits_named is not None:
            try:
                limits_named(banlist)
            except Exception as exc:  # noqa: BLE001 -- message lists the valid names
                problems.append(f"{where}: banlist {banlist!r}: {exc}")

    return problems

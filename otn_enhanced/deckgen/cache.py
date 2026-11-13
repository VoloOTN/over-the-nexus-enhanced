"""Cached build artifacts with source-hash invalidation.

Every expensive stage (pool build, text parse, scoring) writes a JSON envelope::

    {"schema": "deckgen.cards.v1",
     "built_at": "2026-07-27T12:00:00",
     "sources": {"<path>": "<sha1>", ...},
     "data": ...}

A cached artifact is reused only when every recorded source still hashes to the
same value, so editing ``params.toml`` or re-extracting the ROM invalidates
exactly the stages that depend on it and nothing else.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from otn_enhanced.deckgen import resources

#: Resolved through :mod:`resources` so the same code works in a checkout and in
#: a PyInstaller bundle.  In a checkout these are exactly the paths deckgen has
#: always used.
REPO_ROOT = resources.root()
CACHE_DIR = resources.cache_dir()
DATA_DIR = resources.package_data_dir()


def sha1_file(path: str | Path) -> str:
    """Return the SHA-1 of *path*, or ``"missing"`` when it does not exist."""
    p = Path(path)
    if not p.exists():
        return "missing"
    h = hashlib.sha1()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_map(paths: Iterable[str | Path]) -> dict[str, str]:
    """Hash every path in *paths*, keyed by its repo-relative form."""
    out: dict[str, str] = {}
    for p in paths:
        p = Path(p)
        try:
            key = str(p.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:  # outside the repo — key on the absolute path
            key = str(p)
        out[key] = sha1_file(p)
    return out


def load(schema: str, sources: dict[str, str]) -> Any | None:
    """Return the cached payload for *schema*, or ``None`` if stale/absent.

    When :func:`resources.trust_cache` is set (a bundle), the source SHA-1s are
    not compared: a bundle ships the caches without the 35 MB of inputs they were
    built from, so every hash would read ``"missing"``, the cache would look stale,
    and the rebuild would fail for want of those same inputs.  The schema is still
    checked, so a genuinely wrong artifact is still rejected.
    """
    path = CACHE_DIR / f"{schema}.json"
    if not path.exists():
        return None
    try:
        env = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if env.get("schema") != schema:
        return None
    if not resources.trust_cache() and env.get("sources") != sources:
        return None
    return env.get("data")


def store(schema: str, sources: dict[str, str], data: Any) -> Path:
    """Write *data* under *schema* and return the artifact path."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{schema}.json"
    env = {
        "schema": schema,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": sources,
        "data": data,
    }
    path.write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
    return path


### Pickle artifacts.
###
### JSON cannot round-trip a ParsedCard without a hand-written codec for Clause,
### Predicate and Count — which is why the parse stage originally cached only its
### *report* and re-parsed 4,076 cards on every single invocation.  That was
### "well under a second" when the comment was written and is **9.2 seconds**
### now, the largest single cost in starting the tool up.
###
### Pickle is safe here precisely because of the source-hash envelope: any edit
### to the parser or to the model dataclasses changes a recorded hash and the
### artifact is discarded, so a stale pickle cannot outlive the code that wrote
### it.  Treat these files as build output, never as an interchange format.


def load_pickle(schema: str, sources: dict[str, str]) -> Any | None:
    """Return the cached pickle payload for *schema*, or ``None`` if stale."""
    import pickle

    path = CACHE_DIR / f"{schema}.pkl"
    if not path.exists():
        return None
    try:
        env = pickle.loads(path.read_bytes())
    except Exception:  # noqa: BLE001 — a corrupt cache must never be fatal
        return None
    if not isinstance(env, dict) or env.get("schema") != schema:
        return None
    # Same reasoning as load(): a bundle ships caches without their sources.
    if not resources.trust_cache() and env.get("sources") != sources:
        return None
    return env.get("data")


def store_pickle(schema: str, sources: dict[str, str], data: Any) -> Path:
    """Write *data* under *schema* as a pickle envelope."""
    import pickle

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{schema}.pkl"
    env = {
        "schema": schema,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": sources,
        "data": data,
    }
    path.write_bytes(pickle.dumps(env, protocol=pickle.HIGHEST_PROTOCOL))
    return path


def cached(
    schema: str,
    sources: Iterable[str | Path],
    build: Callable[[], Any],
    *,
    force: bool = False,
) -> Any:
    """Return the cached payload for *schema*, building it via *build* if stale."""
    smap = source_map(sources)
    if not force:
        hit = load(schema, smap)
        if hit is not None:
            return hit
    data = build()
    store(schema, smap, data)
    return data

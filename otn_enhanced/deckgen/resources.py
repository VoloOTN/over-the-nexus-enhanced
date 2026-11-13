"""Where deckgen's data lives — the one place that answers it.

deckgen used to resolve every data file against the repo root, computed as
``Path(__file__).resolve().parents[2]``.  That is correct in a checkout and wrong
everywhere else, which is what stopped deckgen working inside a PyInstaller
bundle: the modules were collected as code, their ``.toml`` / ``.json`` / ``.pkl``
data was not, and the failure surfaced far downstream as a missing
``deckgen/data/params.toml``.

This module makes the layout **relocatable**.  In a checkout it returns exactly
the paths deckgen has always used, so repo behaviour is unchanged.  Frozen, it
resolves against the bundle instead.

Two modes
=========

**Checkout** — the full pipeline.  ``load_pool`` reads the ROM and the ~35 MB of
sources under ``scratch/``, SHA-1 stamps them, and caches the result.

**Bundled** — cache-only.  A bundle ships the ~7 MB of built caches and *not* the
35 MB of sources, so the SHA-1 check cannot be satisfied and must not be
attempted: with the sources absent every hash reads ``"missing"``, the cache looks
stale, and the rebuild fails for want of the very files being hashed.  Pointing it
at the user's ROM does not rescue it either — a different or already-patched ROM
hashes differently, so it goes stale again.  So when :func:`trust_cache` is true,
:func:`cache.load` skips validation and takes the bundled cache at its word.  That
is sound because in a bundle the cache *is* the shipped data; validation exists to
catch a cache that has fallen behind its inputs during development, and a bundle
has no inputs to fall behind.

⚠️ A bundled pool therefore describes the ROM it was baked from.  Randomising card
properties moves stats out from under the cids deckgen scored, which is what
``cardpool.is_randomised`` detects and the ``randomised`` scoring profile exists
to handle; it is not made better or worse by bundling.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: Repo layout: this file is <root>/otn_enhanced/deckgen/resources.py
_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]


def frozen() -> bool:
    """True when running from a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False))


def root() -> Path:
    """The directory data paths are resolved against.

    ``sys._MEIPASS`` when frozen — PyInstaller unpacks a onefile bundle there and
    ``--add-data`` targets are relative to it — otherwise the checkout root.
    """
    if frozen():
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return Path(base)
        return Path(sys.executable).parent
    return _CHECKOUT_ROOT


def trust_cache() -> bool:
    """Should a cached artifact be used without validating its sources?

    Only when there is no way to rebuild it: a bundle that ships built caches but
    not their inputs.  A bundle that *does* ship the inputs (see
    :func:`can_build_pool`) keeps the normal staleness check, which is what lets a
    randomised ROM correctly invalidate the pool and rebuild it.

    Getting this wrong is silent and serious: trusting a shipped pool while pointed
    at a randomised ROM hands back the stock Attribute/Type/Level/ATK/DEF for every
    cid, and every generated deck is built around cards that are not in play.
    """
    return frozen() and not can_build_pool()


# ---------------------------------------------------------------------------
# The data files, by role
# ---------------------------------------------------------------------------

def cache_dir() -> Path:
    """Built artifacts: the pool, parsed text, match index, mined counts.

    Frozen, this must be somewhere **writable and stable** — not ``_MEIPASS``,
    which a one-file bundle unpacks afresh on every launch and deletes on exit, so
    a cache written there is thrown away and the ~26 s rebuild is paid every run.
    A per-user app-data directory keeps it across runs, which pays off whenever the
    same seed and ROM are used twice.
    """
    if frozen():
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
        if base:
            return Path(base) / "OTN-Randomiser" / "deckgen-cache"
        return Path.home() / ".cache" / "otn-randomiser" / "deckgen-cache"
    return root() / "data" / "deckgen" / "cache"


def package_data_dir() -> Path:
    """``params.toml`` / ``aliases.toml``, which live inside the package."""
    return Path(__file__).resolve().parent / "data"


def wiki_categories() -> Path:
    return root() / "data" / "deckgen" / "wiki_categories.json"


def konami_tsv() -> Path:
    return root() / "otn_enhanced" / "rom" / "konami_id_to_card_name.tsv"


def rom_path() -> Path:
    """The ROM the pool is built from.

    Only read when the pool is actually (re)built, which a bundle never does.
    Overridable via :func:`set_rom_path` so a caller can point the build at a
    specific ROM instead of the repo's working copy.
    """
    return _rom_override or (root() / "data" / "over_the_nexus" / "working" / "rom.nds")


def ygopro_cache() -> Path:
    return root() / "scratch" / "ygoprodeck_cache.json"


def cid_to_name() -> Path:
    return root() / "scratch" / "cid_to_name.json"


_rom_override: Path | None = None


def set_rom_path(path: str | Path | None) -> None:
    """Point the pool build at *path* instead of the repo's working ROM."""
    global _rom_override
    _rom_override = Path(path) if path else None


def formatlibrary_decks() -> Path:
    """Tournament decklists, mined for the copy-count priors."""
    return root() / "scratch" / "formatlibrary_decks.json"


def pool_build_inputs() -> list[Path]:
    """Every file needed to rebuild the pool and its dependents from a ROM.

    The chain matters here.  Only ``deckgen.cards.v1.json`` is stamped on the ROM,
    but ``parsed`` is stamped on the pool, ``matchindex`` on ``parsed``, and
    ``mined`` on the pool too — so pointing at a different ROM invalidates *all* of
    them and every one of these inputs is consulted.  Bundling the built caches
    instead would be pointless; they are the first thing thrown away.
    """
    return [ygopro_cache(), cid_to_name(), formatlibrary_decks(),
            wiki_categories(), konami_tsv(),
            package_data_dir() / "aliases.toml",
            package_data_dir() / "params.toml"]


def can_build_pool() -> bool:
    """Are the inputs present to (re)build the card pool from a given ROM?

    Distinct from :func:`available`, which only asks whether a *pre-built* pool can
    be loaded.  Anything that randomises card properties must rebuild, because the
    pool stores each card's Attribute/Type/Level/ATK/DEF against its cid — so a pool
    built from another ROM describes cards that are not in play.
    """
    return all(p.exists() for p in pool_build_inputs())


def missing_pool_inputs() -> list[str]:
    """Which pool-build inputs are absent, for a useful error message."""
    return [str(p) for p in pool_build_inputs() if not p.exists()]


#: Always needed, cache or no cache.
_ESSENTIAL = ("params.toml",)


def _essentials() -> list[Path]:
    return [package_data_dir() / n for n in _ESSENTIAL] + [konami_tsv()]


def available() -> bool:
    """Can deckgen actually run here?

    Importable is not the same as runnable: PyInstaller collects the modules
    whether or not their data came with them.  Runnable means the package data is
    present **and** there is either a pre-built pool to load or the inputs to build
    one.  Requiring a pre-built pool would be wrong for a bundle that ships the
    inputs instead — the caches are created on first use, so demanding them up
    front reported "unavailable" for a build that works perfectly.
    """
    if not all(p.exists() for p in _essentials()):
        return False
    return can_build_pool() or (cache_dir() / "deckgen.cards.v1.json").exists()


def missing() -> list[str]:
    """Which required data files are absent, for a useful error message."""
    out = [str(p) for p in _essentials() if not p.exists()]
    if not can_build_pool() and not (cache_dir() / "deckgen.cards.v1.json").exists():
        out.append(f"a pool to load ({cache_dir() / 'deckgen.cards.v1.json'}) "
                   f"or the inputs to build one")
        out.extend(missing_pool_inputs())
    return out

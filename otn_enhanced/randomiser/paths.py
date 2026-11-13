"""Where the randomiser's companion files live."""
from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory to resolve companion files (deck_seeds.json) against.

    Under PyInstaller ``--onefile`` the bundle is unpacked into a temp directory
    and ``__file__`` points inside it, so a ``__file__``-relative default would
    look for the seed pile in a folder the user cannot see.  When frozen, resolve
    against the executable's own directory instead.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def default_seed_pile() -> str:
    return str(app_dir() / "deck_seeds.json")

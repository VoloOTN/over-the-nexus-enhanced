"""In-memory ROM session: the whole reason this build takes 40 s instead of 30 min.

THE PROBLEM
-----------
The old chain hands every patch a file path. Each of the 55 steps therefore:

    fromFile(129 MB) -> decompress ov3 -> edit -> RECOMPRESS ov3 -> saveToFile(129 MB)

and the next step immediately decompresses what the last one compressed. Measured on this
machine: one ov3 recompression is 12.7 s, one ov5 recompression 8.6 s, and the chain does
**48 of the former and 88 of the latter** -- about 23 of the ~30 minutes, spent in
``ndspy._lzCommon.compress`` (pure Python, no C extension).

Every one of those compressions is an identity function on the buffer that matters, because
``decompress(compress(x)) == x``. So we do them **twice, at the end**, instead of 136 times.

THE MECHANISM
-------------
Four monkeypatches, installed for the duration of one build, then removed:

1. ``NintendoDSRom.loadArm9Overlays`` -- for the session ROM only, return the *same*
   ``Overlay`` instances every call. ndspy re-parses the overlay from ``rom.files`` on every
   call and ``Overlay.__init__`` decompresses eagerly, so without this the deferral below
   would be undone by the next load.

2. ``ndspy.code.Overlay.save`` -- for a session overlay asked to compress: mark it dirty,
   skip the compression, return ``b""``. Callers then store that in ``rom.files`` and write a
   compressed-size of 0 into the overlay table. Both are harmless *because of hook 1*: nothing
   reads them back mid-build. Crucially this must NOT touch ``ov.compressed``/``ov.flags`` --
   finalize needs the original flag to know whether to compress at all.

3. ``NintendoDSRom.fromFile`` / ``saveToFile`` / ``shutil.copyfile`` -- for the session path
   only, serve the live ROM and swallow the write. Any OTHER path falls through to the real
   implementation, because verify and diagnostic code legitimately loads reference ROMs to
   compare against (e.g. shooting_quasar.py:1842-1911).

4. :meth:`Session.finalize` -- one real compress per dirty overlay, replaying the overlay-table
   writeback that all 13 compression sites in this repo perform verbatim, then one real save.

WHY THE OUTPUT IS BYTE-IDENTICAL
--------------------------------
* Removing identity round-trips leaves the final decompressed ov3/ov5/ov1 buffers bit-identical.
* ``codeCompression.compress`` is deterministic, so identical input gives identical output.
* The table writeback below is copied character-for-character from ``overlay_io.save_overlay3``
  / ``ov5_cave._save_ov5`` / ``pack_unlock_conditions._save_ov1`` / ``wifi_timers``,
  which are already identical to each other.
* ``NintendoDSRom.save()`` derives the 129 MB layout from file contents and sizes only, and is
  the same code path the old chain used.

This is an argument, not a proof. The proof is ``build.py --compare``, which sha256s this
build against one produced by the untouched old chain.

WHAT WOULD BREAK IT
-------------------
A patch module that BRANCHES on ``ov.compressed``, ``ov.compressedSize`` or the overlay table
rather than on ``ov.data``. None does today -- every idempotency guard in the stack reads
``ov.data`` (tg_table.py:212,219,360,368,517,526; ov5_cave.install_cave). ``ov3_cave.geometry()``
does read the table, but is only ever called by ``_build_ov3_canary.py``, never in the chain.
:func:`assert_no_table_readers` re-checks that claim on every build so it cannot rot silently.
"""
from __future__ import annotations

import shutil
import struct
from pathlib import Path

import ndspy.code
import ndspy.rom

_real_from_file = ndspy.rom.NintendoDSRom.fromFile
_real_save_to_file = ndspy.rom.NintendoDSRom.saveToFile
_real_load_overlays = ndspy.rom.NintendoDSRom.loadArm9Overlays
_real_ov_save = ndspy.code.Overlay.save
_real_copyfile = shutil.copyfile
_real_copy = shutil.copy


def _same(a, b) -> bool:
    """True if two paths name the same file (case-insensitive on Windows)."""
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, ValueError):
        return False


class Session:
    """One in-memory ROM that every patch step reads and writes.

    ``work_path`` is the path the patch modules *think* they are reading and writing; it never
    has to exist on disk. ``defer`` False keeps the per-step compression (the old, slow
    behaviour) while still holding the ROM in memory -- used by ``--strict`` to separate a
    deferral bug from a caching bug when a hash diverges.
    """

    def __init__(self, src: str | Path, work_path: str | Path, *, defer: bool = True):
        self.src = str(src)
        self.rom = _real_from_file(self.src)
        self.work_path = str(work_path)
        self.defer = defer
        self.overlays: dict[int, ndspy.code.Overlay] = {}
        self.dirty: set[int] = set()
        self._installed = False

    def normalise(self) -> None:
        """Restore the types a fresh ``fromFile`` guarantees: every buffer a ``bytearray``.

        THIS IS NOT COSMETIC. ndspy's loader produces 127 **bytearrays**, but ~20 patch modules
        assign immutable ``bytes`` back into ``rom.files[fid]`` (``bytes(pac_data)``,
        ``build_modified_pac(...)``, a compressed overlay). In the old chain that never mattered,
        because the next step re-read the ROM from disk and got fresh bytearrays. Holding the ROM
        in memory removes that laundering step -- and
        ``bulk_card_props.py:209`` mutates its bin2.pac entry IN PLACE::

            old_rom.files[fid][addr:addr + len(data)] = data

        which is a ``TypeError`` on ``bytes``. It is the only in-place ``rom.files`` mutation in
        the repo, and it is why step 45 died on the first full run.

        Converting only what is not already a bytearray keeps this at roughly the cost of the
        one or two files a step actually touched. It changes types, never bytes.
        """
        files = self.rom.files
        for i, f in enumerate(files):
            if not isinstance(f, bytearray):
                files[i] = bytearray(f)
        if not isinstance(self.rom.arm9, bytearray):
            self.rom.arm9 = bytearray(self.rom.arm9)
        if not isinstance(self.rom.arm9OverlayTable, bytearray):
            self.rom.arm9OverlayTable = bytearray(self.rom.arm9OverlayTable)

    # -- hook 1: one Overlay object per id, for the life of the build -------------------
    def _load_overlays(self, ids=None):
        n = len(self.rom.arm9OverlayTable) // 32
        want = list(range(n)) if ids is None else [i for i in range(n) if i in ids]
        missing = [i for i in want if i not in self.overlays]
        if missing:
            self.overlays.update(_real_load_overlays(self.rom, missing))
        return {i: self.overlays[i] for i in want}

    def _owns(self, ov) -> bool:
        return any(ov is o for o in self.overlays.values())

    def _oid(self, ov) -> int:
        return next(i for i, o in self.overlays.items() if o is ov)

    # -- hook 2: defer the compression -------------------------------------------------
    def _ov_save(self, ov, *, compress: bool = False) -> bytes:
        if not (self.defer and compress and self._owns(ov)):
            return _real_ov_save(ov, compress=compress)
        ov.ramSize = len(ov.data)      # the real save does this too; harmless and closer to it
        self.dirty.add(self._oid(ov))
        return b""                     # deliberately obviously-wrong: nothing may read it back

    # -- install / remove --------------------------------------------------------------
    def __enter__(self) -> "Session":
        s = self

        def from_file(cls, path, *a, **kw):
            if _same(path, s.work_path):
                return s.rom
            return _real_from_file(path, *a, **kw)

        def save_to_file(rom, path, *a, **kw):
            if rom is s.rom and _same(path, s.work_path):
                return None
            return _real_save_to_file(rom, path, *a, **kw)

        def load_overlays(rom, ids=None):
            if rom is s.rom:
                return s._load_overlays(ids)
            return _real_load_overlays(rom, ids)

        def ov_save(ov, *, compress=False):
            return s._ov_save(ov, compress=compress)

        def copyfile(src, dst, *a, **kw):
            if _same(dst, s.work_path):
                return dst                     # the session ROM already holds this content
            return _real_copyfile(src, dst, *a, **kw)

        def copy(src, dst, *a, **kw):
            if _same(dst, s.work_path):
                return dst
            return _real_copy(src, dst, *a, **kw)

        ndspy.rom.NintendoDSRom.fromFile = classmethod(from_file)
        ndspy.rom.NintendoDSRom.saveToFile = save_to_file
        ndspy.rom.NintendoDSRom.loadArm9Overlays = load_overlays
        ndspy.code.Overlay.save = ov_save
        shutil.copyfile = copyfile
        shutil.copy = copy
        self._installed = True

        # bulk_card_props.py:204-207 does a RAW `open(src,'rb')` / `open(out,'wb')` copy
        # that bypasses every hook above, so the work path has to be a real file or it raises
        # FileNotFoundError. Its content is never read back -- the module takes all its actual
        # data from the ROM object and then calls saveToFile, which is a no-op here -- so seeding
        # it with the clean ROM is safe. Materialised deliberately rather than depending on a
        # leftover from an earlier run, which is what was happening.
        work = Path(self.work_path)
        work.parent.mkdir(parents=True, exist_ok=True)
        self._made_work_file = not work.exists()
        if self._made_work_file:
            _real_copyfile(self.src, self.work_path)
        return self

    def __exit__(self, *exc) -> None:
        ndspy.rom.NintendoDSRom.fromFile = _real_from_file
        ndspy.rom.NintendoDSRom.saveToFile = _real_save_to_file
        ndspy.rom.NintendoDSRom.loadArm9Overlays = _real_load_overlays
        ndspy.code.Overlay.save = _real_ov_save
        shutil.copyfile = _real_copyfile
        shutil.copy = _real_copy
        self._installed = False
        if getattr(self, "_made_work_file", False):
            Path(self.work_path).unlink(missing_ok=True)   # scratch, never an output

    # -- hook 4: pay the compression cost once ----------------------------------------
    def finalize(self, out_path: str | Path) -> int:
        """Compress every dirty overlay once, write the ROM, return its byte length.

        The three writes per overlay below are lifted verbatim from overlay_io.save_overlay3
        (and are identical in ov5_cave._save_ov5, pack_unlock_conditions._save_ov1 and
        wifi_timers._patch_overlay3). ndspy does not propagate ramSize or the compressed
        size back into the overlay table on its own; without this the loader copies the wrong
        byte count and the game dies on first overlay use.
        """
        tbl = self.rom.arm9OverlayTable
        for oid in sorted(self.dirty):
            ov = self.overlays[oid]
            data = bytes(ov.data)
            compressed = _real_ov_save(ov, compress=ov.compressed)
            self.rom.files[ov.fileID] = compressed
            e = oid * 32
            struct.pack_into("<I", tbl, e + 0x08, len(data))
            flags = struct.unpack_from("<I", tbl, e + 0x1C)[0] >> 24
            struct.pack_into("<I", tbl, e + 0x1C, (flags << 24) | (len(compressed) & 0xFFFFFF))
        self.dirty.clear()

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _real_save_to_file(self.rom, str(out_path))
        return out_path.stat().st_size

    def snapshot(self) -> dict:
        """Byte-level state, for equiv.py's A/B diff. Cheap: no compression, no file I/O."""
        return {
            "arm9": bytes(self.rom.arm9),
            "overlays": {i: bytes(o.data) for i, o in self.overlays.items()},
            "files": {i: bytes(f) for i, f in enumerate(self.rom.files)
                      if i not in {o.fileID for o in self.overlays.values()}},
        }


def assert_no_table_readers() -> list[str]:
    """Fail the build if a patch module starts BRANCHING on overlay-table / compression state.

    The deferral is only sound while every module's idempotency guard reads ``ov.data``. This
    greps for the two shapes that would break it -- a read of ``arm9OverlayTable`` that is not
    a ``pack_into`` writeback, and a use of ``.compressedSize`` -- and returns the offending
    lines. Cheap enough to run on every build, which is the point: prose does not stop rot.
    """
    import re

    pkg = Path(__file__).resolve().parent
    allowed = {"ov3_cave.py"}            # geometry(); only _build_ov3_canary.py calls it
    bad: list[str] = []
    for py in sorted(p for d in ("cards", "system", "data", "effects") for p in (pkg / d).glob("*.py")):
        if py.name in allowed:
            continue
        for n, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "compressedSize" in line:
                bad.append(f"{py.name}:{n}: reads .compressedSize -- {line.strip()}")
            if "arm9OverlayTable" in line and "pack_into" not in line:
                nxt = line.strip()
                if not re.match(r"^(tbl|_?t)\s*=", nxt) and "unpack_from" not in nxt:
                    bad.append(f"{py.name}:{n}: non-writeback table use -- {nxt}")
    return bad

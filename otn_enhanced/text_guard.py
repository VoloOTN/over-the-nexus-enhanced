"""Name the step that clobbers a card's printed text, the moment it happens.

Several steps write card names/descriptions and a few have silently overwritten a card that
an earlier step had already finished (T.G.'s ``force_name_in_place`` did exactly that). Once a
card has its full printed text, no later step may change it -- so this checks after every step
and names the culprit, instead of leaving you to find it in the final ROM.

Lifted from ``apply_all_patches._check_card_text`` (line 2172), with two changes:
  * it reads the LIVE in-memory ROM instead of re-opening a 129 MB file 55 times;
  * it hashes bin2.pac first and skips the parse entirely when the archive did not change,
    which is most steps -- turning ~13 s of re-parsing into under a second.
"""
from __future__ import annotations

import hashlib
import struct

from otn_enhanced.data import card_text as _ct
from otn_enhanced.rom.pac import parse_format_v1


def _bin2_fid(rom) -> int:
    def walk(folder, prefix=""):
        for f in folder.files:
            yield prefix + f
        for name, sub in folder.folders:
            yield from walk(sub, prefix + name + "/")

    return rom.filenames.idOf(next(p for p in walk(rom.filenames) if p.lower().endswith("bin2.pac")))


class TextGuard:
    """Remembers the last-seen good text per (cid, lang) and reports the step that broke it."""

    def __init__(self) -> None:
        self.seen: dict[tuple[int, str], tuple[bytes, bytes]] = {}
        self._digest: str | None = None

    def check(self, rom, step_no: int, step_name: str) -> str | None:
        """Return an error message if *step* clobbered finished text, else None."""
        try:
            bin2 = bytes(rom.files[_bin2_fid(rom)])
        except Exception as exc:                      # never let the guard break a build
            return None if self._digest else f"[card-text guard disabled: {exc}]"

        digest = hashlib.sha256(bin2).hexdigest()
        if digest == self._digest:
            return None                               # archive untouched -- nothing can have moved
        self._digest = digest

        arc = parse_format_v1(bin2, "bin2.pac")
        files = {f.get_clean_name().lower(): f for f in arc.files}

        def raw(name: str) -> bytes:
            f = files[name]
            return bin2[f.address:f.address + f.size]

        prop = raw("card_prop.bin")
        for cid in _ct.CARD_TEXT:
            try:
                entry = _ct.prop_index(prop, cid)
            except KeyError:
                continue
            for lang in _ct.LANGS:
                idx, names, descs = raw(f"card_indx_{lang}.bin"), raw(f"card_name_{lang}.bin"), raw(f"card_desc_{lang}.bin")
                n_off, d_off = struct.unpack_from("<II", idx, entry * 8)
                got = (names[n_off:names.find(b"\x00", n_off)], descs[d_off:descs.find(b"\x00", d_off)])
                key = (cid, lang)
                if got == _ct.resolve(cid, lang):
                    self.seen[key] = got
                elif key in self.seen:
                    was, now = self.seen[key], got
                    return (f"*** STEP {step_no} ({step_name}) CLOBBERED CARD TEXT ***\n"
                            f"    cid {cid:#06x} lang '{lang}'\n"
                            f"    was:  name {was[0]!r} desc {len(was[1])}B\n"
                            f"    now:  name {now[0]!r} desc {len(now[1])}B\n"
                            f"    want: name {_ct.resolve(cid, lang)[0]!r}")
        return None

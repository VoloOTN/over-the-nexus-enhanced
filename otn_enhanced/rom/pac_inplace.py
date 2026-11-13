"""In-place PAC readers/writers for the two layouts the randomiser touches.

``pac.py`` is the general unpack/repack path.  These never move an entry: v1
(``bin2.pac``, ``deck.pac``) and v2 (``puzzle.pac``) are patched where they sit, so
nothing downstream (address tables, neighbouring entries) has to be rebuilt.
Unlike ``pac.PACFile`` the entries here remember the file-table slot they came
from, which :func:`write_v1_grow` needs to update a size word.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field


@dataclass
class PacEntry:
    """One inner file of a PAC archive."""

    name: str
    address: int          # absolute offset into the PAC blob
    size: int
    table_offset: int     # absolute offset of this entry's 8-byte table slot


@dataclass
class PacArchive:
    fmt: str
    entries: list[PacEntry] = field(default_factory=list)

    def by_name(self, name: str) -> PacEntry | None:
        low = name.lower()
        for e in self.entries:
            if e.name.lower() == low:
                return e
        return None

    def payload(self, data: bytes, entry: PacEntry) -> bytes:
        return data[entry.address:entry.address + entry.size]


_LINEBREAK_BYTES = frozenset(range(0x0A, 0x19))
_INVALID_NAME_CHARS = '<>:"/\\|?*'


def _clean_name(raw: bytes) -> str:
    """Match pac.PACFile.get_clean_name so entries resolve by the same names."""
    try:
        name = raw.decode("shift-jis").split("\x00", 1)[0]
    except (UnicodeDecodeError, LookupError):
        name = raw.decode("utf-8", errors="replace").split("\x00", 1)[0]
    name = "".join(c for c in name if c.isprintable())
    return "".join(c for c in name if c not in _INVALID_NAME_CHARS)


def parse_pac_v1(data: bytes) -> PacArchive:
    """Parse the v1 "marker" format used by bin2.pac and deck.pac.

    Layout: linebreak-delimited filenames, a ``0xFFFF`` marker on a 16-byte
    boundary, then an 8-byte-per-entry file table of ``[u32 rel_addr][u32 size]``.

    The table is **not** a uniform stride: some entries are followed by an extra
    8-byte "after" field whose size word is zero.  deck.pac has 4 of these and
    bin2.pac has 2, so an entry's table slot must be recorded as it is found, not
    computed as ``index * 8``.
    """
    names_begin = -1
    for i in range(0, len(data) - 1, 2):
        if data[i] == 0xFF and data[i + 1] == 0xFF:
            names_begin = i - (i % 16)
            break
    if names_begin < 0:
        raise ValueError("not a v1 PAC: no 0xFFFF marker found")

    header = data[:names_begin]

    third = -1
    for i in range(names_begin, len(data) - 8):
        if (i % 16) == (names_begin % 16) and int.from_bytes(data[i:i + 8], "little") == 0:
            third = i
            break
    if third < 0:
        raise ValueError("not a v1 PAC: file table has no terminator")

    table = data[names_begin:third]
    data_begin = ((third + 0x1FF) // 0x200) * 0x200

    # --- filenames out of the header, split on the linebreak bytes ---
    names: list[bytes] = []
    start = 0
    skip = False
    for i, byte in enumerate(header):
        if skip:
            skip = False
            continue
        if byte in _LINEBREAK_BYTES:
            names.append(header[start:i])
            start = i + 2
            skip = True
    last = len(header) - 1
    while last - 3 >= 0 and header[last - 3] == 0x00:
        last -= 1
    names.append(header[start:last])
    names = [n for n in names if b"." in n]

    # --- file table ---
    archive = PacArchive(fmt="v1")
    for off in range(8, len(table) - 7, 8):
        if len(archive.entries) >= len(names):
            break
        size = int.from_bytes(table[off + 4:off + 8], "little")
        if size == 0:
            # An "after" continuation slot -- its size word is zero.
            continue
        rel = int.from_bytes(table[off:off + 4], "little")
        archive.entries.append(PacEntry(
            name=_clean_name(names[len(archive.entries)]),
            address=data_begin + rel,
            size=size,
            table_offset=names_begin + off,
        ))
    if len(archive.entries) != len(names):
        raise ValueError(
            f"v1 PAC mismatch: {len(names)} names but {len(archive.entries)} table entries"
        )
    return archive


def parse_pac_v2(data: bytes) -> PacArchive:
    """Parse the v2 "simple" format used by puzzle.pac.

    Filenames are plain ASCII ``*.ydq`` / ``*.ydc`` in the first page, then an
    ``[u32 count][u32 0]`` header followed by 8-byte entries carrying a u16 size
    at +2 and a u16 offset at +6.
    """
    names = [m.group().decode("ascii") for m in re.finditer(rb"[a-zA-Z0-9_]+\.yd[cq]", data[:0x1000])]
    if not names:
        raise ValueError("not a v2 PAC: no .ydq/.ydc filenames found")

    table_off = -1
    for pos in range(0x100, min(0x400, len(data) - 8), 8):
        if (int.from_bytes(data[pos:pos + 4], "little") == len(names)
                and int.from_bytes(data[pos + 4:pos + 8], "little") == 0):
            table_off = pos
            break
    if table_off < 0:
        raise ValueError("not a v2 PAC: could not locate the file table")

    start = table_off + 8
    archive = PacArchive(fmt="v2")
    last_end = 0x200
    for idx, name in enumerate(names):
        slot = start + idx * 8
        size = int.from_bytes(data[slot + 2:slot + 4], "little")
        offset = int.from_bytes(data[slot + 6:slot + 8], "little")
        if size == 0:
            continue
        if offset == 0 and archive.entries:
            offset = last_end
        if offset == 0:
            continue
        archive.entries.append(PacEntry(name=name, address=offset, size=size,
                                        table_offset=slot))
        last_end = ((offset + size + 0x1FF) // 0x200) * 0x200
    return archive


def write_same_size(pac: bytearray, entry: PacEntry, payload: bytes) -> None:
    """Overwrite an entry's bytes without moving anything."""
    if len(payload) != entry.size:
        raise ValueError(
            f"{entry.name}: expected {entry.size} bytes, got {len(payload)}"
        )
    pac[entry.address:entry.address + entry.size] = payload


def write_v1_grow(pac: bytearray, archive: PacArchive, entry: PacEntry,
                  payload: bytes) -> None:
    """Replace a v1 entry whose size changed, without moving any entry.

    Every address in the archive stays put; only this entry's payload and the
    size word in its table slot change.  The new payload must fit in the gap
    before the next entry (deck.pac aligns entries to 512 bytes and leaves at
    least 358 bytes of slack, so real decks fit comfortably).
    """
    later = [e.address for e in archive.entries if e.address > entry.address]
    bound = min(later) if later else len(pac)
    room = bound - entry.address
    if len(payload) > room:
        raise ValueError(
            f"{entry.name}: {len(payload)} bytes will not fit the {room}-byte block"
        )
    padded = payload + bytes(room - len(payload))
    pac[entry.address:bound] = padded
    struct.pack_into("<I", pac, entry.table_offset + 4, len(payload))
    entry.size = len(payload)

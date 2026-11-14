"""Edit card_prop / name / description inside bin2.pac, and find the archive in a ROM."""
from __future__ import annotations

import struct

import ndspy.rom

from otn_enhanced.data import card_text as _card_text
from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
from otn_enhanced.rom.pac import build_modified_pac, parse_pac

TEXT_LANGS = "efgisjkr"      # language suffixes present in bin2.pac (e=EN f=FR g=DE i=IT s=ES j=JP k=KR r=??)


def read_cstr(buf: bytes, start: int) -> bytes:
    """Return the NUL-terminated string (without the terminator) at *start* in *buf*."""
    end = buf.index(b"\x00", start)  # find the first 0x00 terminator at/after start
    return buf[start:end]            # slice out the raw string bytes (the slot's logical length)


def iter_paths(folder, prefix=""):
    """Yield every file path inside an ndspy filename folder tree (used to find bin2.pac)."""
    for f in getattr(folder, "files", []) or []:                # files directly under this folder
        yield f"{prefix}{f}"                                    # emit the file's full path
    folders = getattr(folder, "folders", []) or []              # sub-folders (dict OR list across ndspy versions)
    items = folders.items() if isinstance(folders, dict) else folders  # normalise to (name, folder) pairs
    for item in items:                                          # walk each sub-folder
        if isinstance(item, tuple) and len(item) >= 2:          # guard against unexpected shapes
            yield from iter_paths(item[1], prefix=f"{prefix}{item[0]}/")  # recurse with extended path prefix


def rebuild_v1_pac(original: bytes, archive, new_bytes_by_addr: dict) -> bytes:
    """Rebuild a v1 (marker-format) PAC, substituting/growing inner files.

    *new_bytes_by_addr* maps an inner file's ORIGINAL address (as parsed from
    *original*) to its replacement bytes (which may differ in length). The file
    table is recomputed and the original inter-file padding is preserved, so a
    grown blob simply shifts later files forward. Keyed by address so duplicate
    clean-names are safe; unchanged files keep their exact original bytes.
    """
    files_in_order = archive.files                          # file-table order (must be preserved byte-for-byte)
    sorted_by_addr = archive.get_files_sorted_by_address()  # data-layout order (ascending address)

    def fbytes(f):                                          # replacement-or-original bytes for inner file *f*
        return new_bytes_by_addr.get(f.address, original[f.address:f.address + f.size])

    # First pass: compute each file's NEW relative address, preserving original padding.
    new_rel_addr: dict = {}                                 # original address -> new (table-relative) address
    cur = sorted_by_addr[0].address - archive.file_data_beginning_address  # relative addr of the first data file
    for i, f in enumerate(sorted_by_addr):                  # walk files in data order
        new_rel_addr[f.address] = cur                       # record this file's new relative address
        nsize = len(fbytes(f))                              # its (possibly new) size
        if i + 1 < len(sorted_by_addr):                     # not the last file?
            pad = sorted_by_addr[i + 1].address - (f.address + f.size)  # original gap to the next file
            cur += nsize + pad                              # advance past data + preserved padding
        else:                                               # last file
            cur += nsize                                    # advance past its data only

    out = bytearray()                                       # the rebuilt PAC bytes accumulate here
    out += original[0:archive.file_names_beginning]         # copy header (filenames region) up to the 0xFFFF marker
    if len(archive.file_names) >= 8:                        # the marker + 8-byte table header
        out += archive.file_names[0:8]                      # copy it verbatim
    for f in files_in_order:                                # rewrite the file table in ORIGINAL order
        out += new_rel_addr[f.address].to_bytes(4, "little")  # +0 new relative address
        out += len(fbytes(f)).to_bytes(4, "little")           # +4 new size
        if f.after != -1:                                   # v1 'after' field present for this entry?
            out += f.after.to_bytes(8, "little")            # copy it (8 bytes) to keep the table shape
    if len(archive.file_names) > 0:                         # any trailing bytes after the 8-aligned table?
        end_bit = len(archive.file_names) - (len(archive.file_names) % 8)  # last 8-aligned boundary
        if end_bit < len(archive.file_names):               # there are leftover bytes
            out += archive.file_names[end_bit:]             # copy them verbatim
    if archive.third < archive.file_data_beginning_address:  # padding between table and first file's data
        out += original[archive.third:archive.file_data_beginning_address]  # copy it verbatim

    for i, f in enumerate(sorted_by_addr):                  # write file data in data-layout order
        if i > 0:                                           # preserve inter-file padding before this file
            prev = sorted_by_addr[i - 1]                    # previous file in data order
            ps, pe = prev.address + prev.size, f.address    # original padding span [ps, pe)
            if pe > ps:                                     # there is padding
                out += original[ps:pe]                      # copy the original padding bytes
        out += fbytes(f)                                    # write the (possibly grown) file data

    last = sorted_by_addr[-1]                               # last file in data order
    tail = last.address + last.size                         # byte just past the last original file
    if tail < len(original):                                # any trailing data after the last file?
        out += original[tail:]                              # copy it verbatim
    return bytes(out)                                       # finished rebuilt PAC


# ===========================================================================
# PARTS B & C — visible stats + name/description, edited inside bin2.pac
# ===========================================================================
def apply_stats_and_text(
    out_path: str,
    *,
    cid: int,
    attribute: str,
    race: str,
    level: int,
    atk: int,
    defense: int,
    card_type: str = None,
    name: bytes,
    desc: bytes,
    langs: str,
    write_text: bool = True,
    skip_name_if_too_long: bool = False,
) -> None:
    """Apply PART B (card_prop stats) and, if *write_text*, PART C (name/desc).

    Re-opens the already-patched ROM at *out_path* and edits bin2.pac. Stats are a
    same-size bitfield edit. Name and description are written IN-PLACE (never grown):
    if a string fits the card's original slot it overwrites it + re-NULs; if a desc
    is too long for a language's slot it is SKIPPED (original kept) to avoid the
    fixed-size-buffer overflow that blanks text and freezes rendering.
    """
    rom2 = ndspy.rom.NintendoDSRom.fromFile(out_path)            # re-open the ROM to edit a packed file
    pac_path = next((p for p in iter_paths(rom2.filenames)
                     if p.lower().endswith("bin2.pac")), None)   # locate the bin2.pac archive path
    if pac_path is None:                                         # bail clearly if it's missing
        raise RuntimeError("bin2.pac not found in ROM")
    fid = rom2.filenames.idOf(pac_path)                          # resolve the archive's file id in the ROM
    orig_pac = bytes(rom2.files[fid])                            # ORIGINAL bin2.pac bytes (inner addresses are relative to this)
    archive = parse_pac(orig_pac, pac_path)                      # parse the archive -> inner files + their offsets

    modified: dict = {}                                          # original inner-file address -> replacement bytes

    def _orig(f) -> bytes:                                       # original bytes of inner file *f*
        return orig_pac[f.address:f.address + f.size]

    # -----------------------------------------------------------------
    # PART B — set the visible stats in card_prop.bin (same size)
    # -----------------------------------------------------------------
    cpf = next((f for f in archive.files
                if f.get_clean_name().lower() == "card_prop.bin"), None)  # locate card_prop.bin
    if cpf is None:                                             # bail clearly if it's absent
        raise RuntimeError("card_prop.bin not found in bin2.pac")
    cp = bytearray(_orig(cpf))                                  # mutable copy of card_prop.bin
    entry_count = (cpf.size - 8) // 8                           # number of 8-byte records (after the 8-byte header)

    target_idx = None                                           # will hold the target card's record index
    for i in range(entry_count):                               # scan every card_prop record
        off = 8 + i * 8                                         # byte offset of record i (skip 8-byte header)
        val = int.from_bytes(cp[off:off + 8], "little")        # read the 8-byte record as a u64
        if (val & ((1 << 14) - 1)) == cid:                     # low 14 bits hold the card id
            target_idx = i                                     # found the target's record
            break                                              # stop scanning
    if target_idx is None:                                     # bail clearly if the card id is missing
        raise RuntimeError(f"card_id 0x{cid:04X} not found in card_prop.bin")

    toff = 8 + target_idx * 8                                   # byte offset of the target record
    old = int.from_bytes(cp[toff:toff + 8], "little")          # raw u64 before edit (for logging)
    fields = GC.decode_entry(bytes(cp[toff:toff + 8]))         # decode the bitfield into named fields
    print(f"\nBEFORE: raw=0x{old:016X}  "
          f"lvl={fields['level']} attr={fields['attribute']} race={fields['race']} "
          f"atk={fields['real_atk']} def={fields['real_def']} type={fields['card_type']}")

    fields["attribute_encoded"] = GC.attribute_reverse[attribute]  # set attribute (name -> encoded value)
    fields["race"] = race                                          # set race/type
    fields["level"] = level                                        # set Level
    fields["atk_encoded"] = atk // GC.layout.atk_divisor           # set ATK (stored divided)
    fields["def_encoded"] = defense // GC.layout.def_divisor       # set DEF (stored divided)
    if card_type is not None:
        fields["card_type_encoded"] = card_type                                # set card type

    cp[toff:toff + 8] = GC.encode_entry(fields)                # re-encode and splice the record back in
    new = int.from_bytes(cp[toff:toff + 8], "little")          # raw u64 after edit (for logging)
    chk = GC.decode_entry(bytes(cp[toff:toff + 8]))            # decode again to verify what we wrote
    print(f"AFTER : raw=0x{new:016X}  "
          f"lvl={chk['level']} attr={chk['attribute']} race={chk['race']} "
          f"atk={chk['real_atk']} def={chk['real_def']} type={chk['card_type']}")
    modified[cpf.address] = bytes(cp)                          # queue card_prop.bin for the rebuild
    card_index = target_idx                                   # the record index is the key into every per-card table

    # -----------------------------------------------------------------
    # PART C — set the card NAME and DESCRIPTION in every language
    # -----------------------------------------------------------------
    for L in (langs if write_text else ""):                   # skip the whole text pass when write_text is False
        idxf = next((f for f in archive.files
                     if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)  # per-language index table
        namef = next((f for f in archive.files
                      if f.get_clean_name().lower() == f"card_name_{L}.bin"), None)  # per-language name blob
        descf = next((f for f in archive.files
                      if f.get_clean_name().lower() == f"card_desc_{L}.bin"), None)  # per-language desc blob
        if not (idxf and namef and descf):                    # skip any language that is absent
            print(f"  [{L}] missing name/desc/index file -> skipped")
            continue

        name_blob = bytearray(modified.get(namef.address, _orig(namef)))  # working name blob
        desc_blob = bytearray(modified.get(descf.address, _orig(descf)))  # working desc blob
        idx_buf = bytearray(modified.get(idxf.address, _orig(idxf)))      # working index table

        # ---- PREFERRED PATH: full printed text from card_text.CARD_TEXT -----
        # Cards listed there get their REAL name and description at any length up
        # to the stock ~110 B / ~1196 B ceiling, by re-emitting the blob in index
        # order. The caller's `name`/`desc` arguments are IGNORED for those cards:
        # card_text.py is the single source of card text.
        # ⚠️ NEVER go back to appending. The deck editor derives its description
        # read length from the gap to the next card_indx entry; an appended string
        # leaves a NEGATIVE gap, and that dumped ~39.6 KB of raw
        # bin2.pac over a NitroSDK thread block and hard-froze the ARM9.
        if cid in _card_text.CARD_TEXT:
            entry = card_index + 1                            # boggart's scan is +8-based; card_text's is not
            assert struct.unpack_from("<H", cp, entry * 8)[0] & 0x3FFF == cid, \
                f"card_prop entry {entry} is not cid 0x{cid:04X}"
            new_idx, new_names, new_descs = _card_text.rebuild_blobs(
                bytes(idx_buf), bytes(name_blob), bytes(desc_blob),
                {entry: _card_text.resolve(cid, L)})
            _card_text.assert_gaps_ok(new_idx, new_names, new_descs, where=f"[{L}]")
            modified[namef.address] = new_names
            modified[descf.address] = new_descs
            modified[idxf.address] = new_idx

            # A rename moves the card in the deck editor's A-Z list, so card_sort2
            # (position -> card), its inverse card_sort, and the kana1/kana2 jump-bar
            # letters move with it. j/k/r are left alone (kana/hangul collation).
            if L in _card_text.SORTED_LANGS:
                srt = {}
                for base in ("card_sort2", "card_sort", "card_kana1", "card_kana2"):
                    fh = next((f for f in archive.files
                               if f.get_clean_name().lower() == f"{base}_{L}.bin"), None)
                    if fh is None:
                        break
                    srt[base] = (fh, modified.get(fh.address, _orig(fh)))
                if len(srt) == 4:
                    s2, s1, k1, k2 = _card_text.rebuild_sort(
                        new_idx, new_names, srt["card_sort2"][1],
                        srt["card_kana1"][1], srt["card_kana2"][1], {entry})
                    for base, blob in (("card_sort2", s2), ("card_sort", s1),
                                       ("card_kana1", k1), ("card_kana2", k2)):
                        modified[srt[base][0].address] = blob
            n, d = _card_text.resolve(cid, L)
            print(f"  [{L}] name {n!r} ({len(n)}B); desc {len(d)}B "
                  f"(card_text, rebuilt in index order)")
            continue

        # ---- LEGACY PATH: strictly in-place, for cards not in card_text ------
        rec = 8 + card_index * 8                              # this card's [name_off u32][desc_off u32] record (8-byte header)
        old_name_off = struct.unpack_from("<I", idx_buf, rec)[0]  # current name offset into the name blob
        old_name = read_cstr(bytes(name_blob), old_name_off)     # current name bytes (defines the slot length)

        # NAME: prefer IN-PLACE overwrite when the new name fits the original slot
        # (keeps the blob byte-stable). Only append + repoint if it genuinely won't fit.
        if len(name) <= len(old_name):                        # fits the original slot?
            name_blob[old_name_off:old_name_off + len(name)] = name  # overwrite in place
            name_blob[old_name_off + len(name)] = 0           # re-NUL-terminate
            new_name_off = old_name_off                       # offset unchanged -> no index edit needed
            name_note = f"in-place @0x{old_name_off:X} ({len(name)}/{len(old_name)}B)"
        elif skip_name_if_too_long:                           # don't grow the blob -> keep original name in place
            new_name_off = old_name_off                       # offset unchanged (name untouched)
            name_note = f"name SKIPPED (need {len(name)}B > {len(old_name)}B slot; original kept)"
        else:                                                 # too long -> append at the blob's end and repoint
            new_name_off = len(name_blob)                     # append point
            name_blob += name + b"\x00"                       # write name + terminator
            struct.pack_into("<I", idx_buf, rec, new_name_off)  # repoint the index table's name offset
            name_note = f"append (off 0x{old_name_off:X}->0x{new_name_off:X})"

        # DESCRIPTION: write strictly IN-PLACE inside the card's original slot --
        # NEVER grow the desc blob (the engine reads it into a fixed-size buffer).
        old_desc_off = struct.unpack_from("<I", idx_buf, rec + 4)[0]  # this card's existing desc offset
        old_desc = read_cstr(bytes(desc_blob), old_desc_off)        # original desc bytes (defines the slot size)
        if len(desc) <= len(old_desc):                        # fits within the original slot?
            desc_blob[old_desc_off:old_desc_off + len(desc)] = desc  # overwrite text in place
            desc_blob[old_desc_off + len(desc)] = 0           # NUL-terminate (engine stops reading here)
            desc_note = f"in-place @0x{old_desc_off:X} ({len(desc)}/{len(old_desc)}B)"
        else:                                                 # too long -> keep the original desc untouched
            desc_note = f"SKIPPED (need {len(desc)}B > {len(old_desc)}B slot; original kept)"

        modified[namef.address] = bytes(name_blob)            # queue the name blob
        modified[descf.address] = bytes(desc_blob)            # queue the desc blob
        modified[idxf.address] = bytes(idx_buf)               # queue the (possibly repointed) index table
        print(f"  [{L}] name {old_name!r}->{name!r} ({name_note}); "
              f"desc {desc_note}")                            # per-language confirmation

    # Route through pac.build_modified_pac: its repacker keeps every inner file on
    # its 0x200 boundary when a file changes size. The local _rebuild_v1_pac below
    # preserves the GAP LENGTH instead and knocks 90/99 files off their boundary.
    by_addr = {f.address: i for i, f in enumerate(archive.files)}
    new_pac = build_modified_pac(orig_pac, pac_path,
                                 {by_addr[a]: b for a, b in modified.items()})
    rom2.files[fid] = new_pac                                 # store the rebuilt archive back into the ROM
    rom2.saveToFile(out_path)                                 # write the final combined ROM to disk
    print(f"\nbin2.pac {len(orig_pac):,}B -> {len(new_pac):,}B ({len(new_pac) - len(orig_pac):+,}B)")
    print(f"wrote card_prop{' + name/desc' if write_text else ''} edits -> {out_path}")


# ---------------------------------------------------------------------------
# PARTS A + B -- bin2.pac, both records written IN PLACE
# ---------------------------------------------------------------------------
def find_pac(rom):
    pac_path = next((p for p in iter_paths(rom.filenames)
                     if p.lower().endswith("bin2.pac")), None)
    if pac_path is None:
        raise RuntimeError("bin2.pac not found in ROM")
    fid = rom.filenames.idOf(pac_path)
    orig = bytes(rom.files[fid])
    return fid, orig, parse_pac(orig, pac_path)


# elbow: reborn_tengu keeps its own 4-argument _place_string. This is the 6-argument original that the
# Dark World cards still call; unify when those cards are rewritten.
def place_string(pac_data: bytearray, file_base: int, file_size: int,
                  old_off: int, new_bytes: bytes, pad_cursor: dict) -> int | None:
    """Write *new_bytes* for the string at *old_off*, keeping the file the SAME size.

    Fits in the old slot -> written in place.  Otherwise relocated into the file's
    trailing zero padding (the file never grows -- the engine copies these blobs
    into fixed-size buffers, see donor.name_slot_floor).  Returns the new
    file-relative offset, or None if there is no room, in which case the caller
    leaves the donor's own text alone for that language.
    """
    old_str = read_cstr(pac_data, file_base + old_off)
    if len(new_bytes) <= len(old_str):
        slot = len(old_str)
        abs_off = file_base + old_off
        pac_data[abs_off:abs_off + slot + 1] = new_bytes + b"\x00" * (slot + 1 - len(new_bytes))
        return old_off
    # *** RELOCATION DISABLED -- see notes/card-text-blob-findings.md. ***
    # This used to scavenge the file's "trailing zero padding" by walking BACK from
    # the end over NUL bytes. On a blob re-emitted in index order by
    # card_text.rebuild_blobs, a language whose trailing entries are empty strings
    # (Korean) is a long NUL run, so that walk strides back over real strings and
    # lands on ANOTHER CARD'S TERMINATOR -- snoww fused Snoww's Korean name
    # onto Ninishi's. Growing/relocating is no longer needed by anything: every
    # renamed card gets its full printed text from card_text.apply_to_rom, which
    # re-emits the whole blob in index order.
    return None                                            # doesn't fit -- keep the donor's text

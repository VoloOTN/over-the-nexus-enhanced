"""Self-check for the card-text blob rewriter.

Run:  uv run python -m otn_enhanced.tests.test_card_text

Guards the invariant a hard freeze taught us on 2026-09-08: every card_indx entry
must ascend, and its gap to the next entry must equal that string's own 4-aligned
length, because the deck editor derives its description read length from that gap.
"""
from __future__ import annotations

import struct
import sys

import ndspy.rom

from otn_enhanced.data import card_text as ct
from otn_enhanced.rom.pac import parse_format_v1

ROM = "data/over_the_nexus/working/rom.nds"


def _iter(folder, prefix=""):
    for name in folder.files:
        yield prefix + name
    for sub_name, sub in folder.folders:
        yield from _iter(sub, prefix + sub_name + "/")


def main() -> int:
    rom = ndspy.rom.NintendoDSRom.fromFile(ROM)
    bin2 = bytes(rom.files[rom.filenames.idOf(
        next(p for p in _iter(rom.filenames) if p.lower().endswith("bin2.pac")))])
    arc = parse_format_v1(bin2, "bin2.pac")
    F = {f.get_clean_name().lower(): f for f in arc.files}

    def raw(n):
        f = F[n]
        return bin2[f.address:f.address + f.size]

    prop = raw("card_prop.bin")
    for lang in ct.LANGS:
        idx, names, descs = (raw(f"card_indx_{lang}.bin"),
                             raw(f"card_name_{lang}.bin"), raw(f"card_desc_{lang}.bin"))

        # 1. Stock already satisfies the invariant.
        ct.assert_gaps_ok(idx, names, descs, where=f"stock {lang}")

        # 2. The rewriter is the IDENTITY on stock -- if this fails it is changing
        #    more than the cards it was asked to change (it caught the dropped
        #    4-byte blob prefix).
        assert ct.rebuild_blobs(idx, names, descs, {}) == (idx, names, descs), \
            f"{lang}: rebuild_blobs is not the identity on stock"

        # 3. Every card in CARD_TEXT applies, and the result still holds.
        over = {}
        for cid in ct.CARD_TEXT:
            over[ct.prop_index(prop, cid)] = ct.resolve(cid, lang)
        n_idx, n_names, n_descs = ct.rebuild_blobs(idx, names, descs, over)
        ct.assert_gaps_ok(n_idx, n_names, n_descs, where=f"rewritten {lang}")

        for cid in ct.CARD_TEXT:
            e = ct.prop_index(prop, cid)
            n_off, d_off = struct.unpack_from("<II", n_idx, e * 8)
            want_n, want_d = ct.resolve(cid, lang)
            assert ct._cstr(n_names, n_off) == want_n, f"{lang} {cid:#06x} name"
            assert ct._cstr(n_descs, d_off) == want_d, f"{lang} {cid:#06x} desc"

        # 4. Untouched cards keep their exact strings.
        touched = set(over)
        for i in range(len(idx) // 8 - 1):
            if i in touched:
                continue
            o_n, o_d = struct.unpack_from("<II", idx, i * 8)
            n_n, n_d = struct.unpack_from("<II", n_idx, i * 8)
            assert ct._cstr(names, o_n) == ct._cstr(n_names, n_n), f"{lang} card {i} name"
            assert ct._cstr(descs, o_d) == ct._cstr(n_descs, n_d), f"{lang} card {i} desc"

        note = ""
        if lang in ct.SORTED_LANGS:
            s2b, k1b, k2b = (raw(f"card_sort2_{lang}.bin"),
                             raw(f"card_kana1_{lang}.bin"), raw(f"card_kana2_{lang}.bin"))
            s1b = raw(f"card_sort_{lang}.bin")
            count = len(s2b) // 2
            s2 = list(struct.unpack(f"<{count}H", s2b))

            # card_sort is exactly the inverse permutation of card_sort2.
            inv = [0] * count
            for pos, c in enumerate(s2):
                inv[c] = pos
            assert list(struct.unpack(f"<{count}H", s1b)) == inv, \
                f"{lang}: card_sort is not inverse(card_sort2)"

            # No renames -> the tables come back byte-identical.
            assert ct.rebuild_sort(idx, names, s2b, k1b, k2b, set()) == (s2b, s1b, k1b, k2b), \
                f"{lang}: rebuild_sort is not the identity with no changes"

            # After the rename the list is still sorted, and stays a permutation.
            n_s2, n_s1, n_k1, n_k2 = ct.rebuild_sort(n_idx, n_names, s2b, k1b, k2b, set(over))
            order = list(struct.unpack(f"<{count}H", n_s2))
            assert sorted(order) == list(range(count)), f"{lang}: card_sort2 is not a permutation"
            def _inversions(order_, idx_, names_):
                ks = []
                for c in order_:
                    o = struct.unpack_from("<II", idx_, c * 8)[0]
                    ks.append(ct.sort_key(names_[o:names_.find(b'\x00', o)]))
                return [i for i in range(len(ks) - 1) if ks[i] > ks[i + 1]]

            # g and s carry inversions in STOCK -- cards whose name starts with
            # typographic punctuation, which this collation does not model. The
            # honest invariant is that resorting does not make the order WORSE.
            stock_bad = _inversions(s2, idx, names)
            bad = _inversions(order, n_idx, n_names)
            assert len(bad) <= len(stock_bad), (
                f"{lang}: resort added inversions ({len(stock_bad)} -> {len(bad)})")
            stock_note = (f", {len(stock_bad)} pre-existing stock inversion(s) preserved"
                          if stock_bad else "")
            n_inv = list(struct.unpack(f"<{count}H", n_s1))
            assert all(n_inv[c] == p for p, c in enumerate(order)), f"{lang}: inverse broken"
            note = "; A-Z resorted, inverse consistent" + stock_note

        print(f"OK  {lang}: identity on stock; {len(ct.CARD_TEXT)} cards applied; "
              f"name {len(names):,}->{len(n_names):,} desc {len(descs):,}->{len(n_descs):,}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

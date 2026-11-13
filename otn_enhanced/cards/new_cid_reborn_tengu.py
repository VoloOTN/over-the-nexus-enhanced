"""Reborn Tengu as a BRAND-NEW card at its Konami cid 0x25E3 -- no donor consumed.

    "If this face-up card leaves the field: Special Summon 1 "Reborn Tengu" from your Deck."
    (WIND / Beast-Warrior / Level 4 / 1700 / 600 / Effect Monster, passcode 10028593)

EXPERIMENT -- single-card ROM only, NOT in steps.STEPS. Built on top of the ov3-compaction step
(rom_ov3_compact.nds). The shipped donor version (reborn_tengu, The Portrait's Secret 0x1463)
is deliberately NOT applied here, so 0x1463 stays a vanilla Normal Monster and the phantoms that
patch spends are still free. Evidence for every edit: notes/new-cid-card-findings.md.

PARTS
  A  arm9   cid_to_intid 0x02029E1C upper bound 0x24E9 -> 0x25E4 (the ONLY cid-range bound)
  B  arm9   global card count [0x0209D474] 0x10D2 -> 0x10D3 (list builders / password lookup),
            pack-list loop 0x0202A75C likewise, and new_card_save: record 4306's owned count + flags
            live in the unused bits 6/7 of the flag bytes (starts at 0 copies; buy it from pack 1).
  C  bin2   one new record (index 4306) appended to every per-card file; card_intid grown to
            cover 0x25E3; Konami's own 3DS rows for prop / genre / pass
  D  card   card.pac: one appended 32x32 thumb + index entry + 64x64 tile
  E  ov3    leave-mask row + cls2 record + criteria row (same wiring as the shipped donor card,
            native ov3 handler 0x0223D075 -> pure data, works in puzzles)
"""
from __future__ import annotations

import struct
from pathlib import Path

import ndspy.rom
from PIL import Image

from otn_enhanced.rom.pac import build_modified_pac, parse_format_v1
from otn_enhanced.rom.lz_compression import compress, decompress
from otn_enhanced.rom.lz5bg_codec import _parse_ntbg_sections, _parse_palette
from otn_enhanced.rom.card_art_codec import encode_card_art_64x64, encode_card_thumb_32x32
from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3
from otn_enhanced.data import card_text as ct
from otn_enhanced.cards import new_card_save
from otn_enhanced.data.extra_banlists import _save_overlay
from otn_enhanced.data.card_art import (
    DATA_BASE,
    ART64_STRIDE,
    H_F1SIZE,
    H_F2START,
    H_F2SIZE,
    H_F3START,
    H_F3SIZE,
)
from otn_enhanced.effects.common import arm9_edit, view as arm9_view
from otn_enhanced.effects.common import Ov
from otn_enhanced.effects.common import insert_sorted, rows
from otn_enhanced.cards import reborn_tengu as rt

SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"
OUT = "data/over_the_nexus/working/rom_new_cid_tengu.nds"
BIN2, CARD_PAC = "Data_arc_pac/bin2.pac", "Data_arc_pac/card.pac"
DS3 = Path("3ds_extract/partition0/romfs/duel/card")
ART = Path("data/over_the_nexus/card_arts/implemented/reborn tengu")

NEW_CID = 0x25E3            # Konami's cid (3DS CARD_Prop record 4748)
OLD_COUNT = 0x10D2          # 4306 records incl. the all-zero header record 0
NEW_IDX = OLD_COUNT         # the new card's record index
CID_BEGIN, OLD_END = 0x0D48, 0x24E9
NEW_END = NEW_CID + 1

LIT_CID_END = 0x02029E44    # `ldr r1,[pc]` literal in cid_to_intid 0x02029E1C
GLOBAL_COUNT = 0x0209D474   # arm9 .data u32
LIT_PACK_LOOP = 0x0202A75C  # pack-list builder 0x0202A608's own record-loop bound (single ldr user 0x0202A734)
PACK_ROW = bytes([0, 0, 0, 1, 0, 0, 0, 0])   # rarity_1 0 (Common), pack_1 = 1, pack_2 = 0
# ov8 banlist-limit sort cache 0x021FD1F0 is a FIXED 0x10D2-byte buffer. Its fill 0x02155B98 reads the
# record count through the pool word SORT_FILL_COUNT_PTR (= &0x0209D474); point it at the buffer-size
# literal next to it instead, so the fill stops at 4306 whatever the card count. New cards then sort by
# the (read-only) bytes past the buffer in "sort by limit" mode -- cosmetic, accepted by the user.
SORT_FILL_COUNT_PTR = 0x02155BF0
SORT_SIZE_LIT = 0x02155BEC

TEMPLATE_CID = 0x1463       # The Portrait's Secret (Lv4): art template + pwcost/kana stand-in
NAME = "Reborn Tengu"
DESC = 'If this face-up card leaves the field: Special Summon 1 "Reborn Tengu" from your Deck.'
PASSCODE = 10028593

# PART E -- the shipped module's geometry, re-keyed to the new cid.
MASK_NEW = (NEW_CID, rt.MASK_LEAVES_FIELD)
CLS2_NEW = (NEW_CID, rt.RES_RESOLVER, 0, rt.RES_CONDITION, 0, 0)
POP_NEW = (NEW_CID, NEW_CID, rt.NATIVE_HANDLER, rt.POP_FLAGS)

U16_FILES = ("card_kana.bin", "card_kana2.bin", "card_pwcost.bin")


def _ds3_row(name: str, width: int) -> bytes:
    """Reborn Tengu's row in a 3DS CARD_* file (record i of every file is the same card)."""
    prop = (DS3 / "CARD_Prop.bin").read_bytes()
    i = next(i for i in range(len(prop) // 8)
             if struct.unpack_from("<H", prop, i * 8)[0] & 0x3FFF == NEW_CID)
    return (DS3 / name).read_bytes()[i * width:(i + 1) * width]


def _bin2(rom):
    fid = rom.filenames.idOf(BIN2)
    data = bytes(rom.files[fid])
    arc = parse_format_v1(data, BIN2)
    by = {f.get_clean_name().lower(): (i, data[f.address:f.address + f.size])
          for i, f in enumerate(arc.files)}
    return fid, data, by


# -- PART C ----------------------------------------------------------------------------------
def build_bin2(rom) -> None:
    fid, data, by = _bin2(rom)
    raw = {n: b for n, (_, b) in by.items()}
    prop = raw["card_prop.bin"]
    assert len(prop) == OLD_COUNT * 8, "card_prop is not the stock 4306 records"
    tmpl = ct.prop_index(prop, TEMPLATE_CID)
    repl: dict[int, bytes] = {}

    def put(n, b):
        repl[by[n][0]] = b

    new_prop = _ds3_row("CARD_Prop.bin", 8)
    assert struct.unpack_from("<H", new_prop)[0] & 0x3FFF == NEW_CID
    put("card_prop.bin", prop + new_prop)
    put("card_genre.bin", raw["card_genre.bin"] + _ds3_row("CARD_Genre.bin", 8))
    put("card_pack.bin", raw["card_pack.bin"] + PACK_ROW)
    pw = _ds3_row("CARD_Pass.bin", 4)
    assert struct.unpack("<I", pw)[0] == PASSCODE
    put("card_pass.bin", raw["card_pass.bin"] + pw)
    for n in U16_FILES:
        put(n, raw[n] + raw[n][tmpl * 2:tmpl * 2 + 2])

    # card_intid: u16 per cid from 0xD48; grow to cover NEW_CID, gap cids -> 0 (= record 0).
    intid = raw["card_intid.bin"]
    assert len(intid) == (OLD_END - CID_BEGIN) * 2
    intid += bytes((NEW_CID - OLD_END) * 2) + struct.pack("<H", 0x8000 | NEW_IDX)   # b15 = monster
    put("card_intid.bin", intid)

    for L in ct.LANGS:
        idx, names, descs = (raw[f"card_indx_{L}.bin"], raw[f"card_name_{L}.bin"],
                             raw[f"card_desc_{L}.bin"])
        assert len(idx) == (OLD_COUNT + 1) * 8
        # one more entry before the sentinel; rebuild_blobs then lays both blobs out in index
        # order with the stock 4-aligned gaps and rewrites the sentinel.
        idx = idx[:-8] + idx[-8:] + idx[-8:]
        enc = ct.ENCODING[L]
        idx, names, descs = ct.rebuild_blobs(idx, names, descs,
                                             {NEW_IDX: (NAME.encode(enc), DESC.encode(enc))})
        ct.assert_gaps_ok(idx, names, descs, where=f"[{L}] new cid")
        put(f"card_indx_{L}.bin", idx)
        put(f"card_name_{L}.bin", names)
        put(f"card_desc_{L}.bin", descs)

        s2 = raw[f"card_sort2_{L}.bin"] + struct.pack("<H", NEW_IDX)        # appended = last
        k1 = raw[f"card_kana1_{L}.bin"] + bytes(2)
        k2 = raw[f"card_kana2_{L}.bin"] + bytes(2)
        if L in ct.SORTED_LANGS:          # A-Z place it properly where the collation is known
            s2, s1, k1, k2 = ct.rebuild_sort(idx, names, s2, k1, k2, {NEW_IDX})
        else:                             # j/k/r: last position, same as the other modules
            s1 = raw[f"card_sort_{L}.bin"] + struct.pack("<H", OLD_COUNT)
        put(f"card_sort2_{L}.bin", s2)
        put(f"card_sort_{L}.bin", s1)
        put(f"card_kana1_{L}.bin", k1)
        put(f"card_kana2_{L}.bin", k2)

    rom.files[fid] = build_modified_pac(data, BIN2, repl)
    print(f"C  bin2.pac: {len(repl)} files grew by one record (idx {NEW_IDX}, cid {NEW_CID:#06x})")


# -- PART D ----------------------------------------------------------------------------------
def build_card_pac(rom, tmpl_idx: int) -> None:
    fid = rom.filenames.idOf(CARD_PAC)
    card = bytes(rom.files[fid])
    u = lambda o: struct.unpack_from("<I", card, o)[0]
    f1z, f2s, f2z, f3s, f3z = (u(H_F1SIZE), u(H_F2START), u(H_F2SIZE), u(H_F3START), u(H_F3SIZE))
    n = f2z // 4 - 1
    assert n == OLD_COUNT and f3z == OLD_COUNT * ART64_STRIDE, (n, f3z)
    idx = [u(DATA_BASE + f2s + k * 4) for k in range(n + 1)]
    streams = [card[DATA_BASE + idx[k]:DATA_BASE + idx[k + 1]] for k in range(n)]
    assert idx[n] == f1z

    buf0 = decompress(streams[0])
    pal = _parse_palette(buf0, _parse_ntbg_sections(buf0)[b"PALT"][0])
    thumb = Image.open(ART / "Reborn_Tengu_32x32.png").convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
    streams.append(compress(encode_card_thumb_32x32(thumb, decompress(streams[tmpl_idx]), pal), 0x10))

    t64 = card[DATA_BASE + f3s + tmpl_idx * ART64_STRIDE:][:ART64_STRIDE]
    big = Image.open(ART / "Reborn_Tengu_64x64.png").convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    tile = encode_card_art_64x64(big, t64)
    assert len(tile) == ART64_STRIDE

    file1 = b"".join(streams)
    new_idx, acc = [], 0
    for s in streams:
        new_idx.append(acc)
        acc += len(s)
    new_idx.append(acc)
    file2 = struct.pack(f"<{len(new_idx)}I", *new_idx)
    file3 = card[DATA_BASE + f3s:DATA_BASE + f3s + f3z] + tile

    nf2s = (len(file1) + 0x1FF) & ~0x1FF
    nf3s = (nf2s + len(file2) + 0x1FF) & ~0x1FF
    out = bytearray(card[:DATA_BASE])
    for off, v in ((H_F1SIZE, len(file1)), (H_F2START, nf2s), (H_F2SIZE, len(file2)),
                   (H_F3START, nf3s), (H_F3SIZE, len(file3))):
        struct.pack_into("<I", out, off, v)
    out += file1
    out += bytes(DATA_BASE + nf2s - len(out)) + file2
    out += bytes(DATA_BASE + nf3s - len(out)) + file3
    out += bytes(-len(out) % 0x200)
    rom.files[fid] = bytes(out)
    print(f"D  card.pac: {n + 1} thumbs / 64x64 tiles (art from {ART})")


def main(src: str = SRC, out: str = OUT) -> None:
    # E -- overlay 3 (writes the ROM), then reopen for the file edits.
    rom, ovb = load_overlay3(src)
    v = Ov(bytearray(ovb))
    assert v.u32(rt.NATIVE_FILTER_LIT) == rt.YUBEL_FILTER, "0x0223D075 is not the Deck selector"
    assert NEW_CID not in v.keys(rt.LIST30_BASE, count=rt.LIST30_COUNT, stride=2)
    assert NEW_CID not in v.keys(rt.LIST106_BASE, count=rt.LIST106_COUNT, stride=2)
    assert v.u16(rt.MASK_COUNT_SITE) == 0x2200 | rt.MASK.count
    assert rt._res_switch_leaf(v, NEW_CID) == rt.RES_DEFAULT_ARM
    insert_sorted(v, rt.MASK, MASK_NEW, drop=rt.DROP_PHANTOM)
    insert_sorted(v, rt.CLS2, CLS2_NEW, drop=rt.DROP_PHANTOM)
    insert_sorted(v, rt.POP, POP_NEW, drop=rt.POP_DROP_PHANTOM)
    save_overlay3(rom, bytes(v.buf), out)

    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    with arm9_edit(rom) as a9:                                           # A + B
        assert a9.u32(LIT_CID_END) == OLD_END and a9.u32(GLOBAL_COUNT) == OLD_COUNT
        assert a9.u32(LIT_PACK_LOOP) == OLD_COUNT
        a9.set_u32(LIT_CID_END, NEW_END)
        a9.set_u32(GLOBAL_COUNT, OLD_COUNT + 1)
        a9.set_u32(LIT_PACK_LOOP, OLD_COUNT + 1)
        new_card_save.apply(a9, n_new=1)
    print(f"A  cid_to_intid bound {OLD_END:#x} -> {NEW_END:#x};  B  card count + pack loop -> {OLD_COUNT + 1}, "
          f"save planes in flag bits 6/7")

    ov8 = rom.loadArm9Overlays([8])[8]
    o8 = bytearray(ov8.data)
    at = lambda a: a - ov8.ramAddress
    assert struct.unpack_from("<I", o8, at(SORT_FILL_COUNT_PTR))[0] == GLOBAL_COUNT
    assert struct.unpack_from("<I", o8, at(SORT_SIZE_LIT))[0] == OLD_COUNT
    struct.pack_into("<I", o8, at(SORT_FILL_COUNT_PTR), SORT_SIZE_LIT)
    _save_overlay(rom, 8, ov8, o8)
    print("B  ov8 limit-sort cache fill capped at 4306 (pool 0x02155BF0 -> 0x02155BEC)")

    _, _, by = _bin2(rom)
    tmpl_idx = ct.prop_index(by["card_prop.bin"][1], TEMPLATE_CID)
    build_bin2(rom)
    build_card_pac(rom, tmpl_idx)
    rom.saveToFile(out)
    print(f"wrote {out}")


def verify(out: str = OUT) -> bool:
    ok = True

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")

    rom, ovb = load_overlay3(out)
    v = Ov(bytearray(ovb))
    check([r for r in rows(v, rt.MASK) if r[0] == NEW_CID] == [MASK_NEW], "E mask row {0x25E3, 0x000C}")
    check([r for r in rows(v, rt.CLS2) if r[0] == NEW_CID] == [CLS2_NEW], "E one cls2 record, mandatory")
    check([r for r in rows(v, rt.POP) if r[0] == NEW_CID] == [POP_NEW], "E one criteria row, native 0x0223D075")
    check(rows(v, rt.CLS2)[rt.CLS2.count - 1][0] == NEW_CID, "E cls2: 0x25E3 is the last in-range row (lower_bound finds it)")

    a9 = arm9_view(rom)
    check(a9.u32(LIT_CID_END) == NEW_END and a9.u32(0x02029E40) == CID_BEGIN, "A cid bound 0xD48..0x25E3")
    check(a9.u32(GLOBAL_COUNT) == OLD_COUNT + 1, "B global card count 4307")
    check(a9.u32(LIT_PACK_LOOP) == OLD_COUNT + 1, "B pack-list builder loops 4307 records")
    check(new_card_save.applied(a9), "B save accessors rewritten: new records stored in flag bits 6/7")
    ov8 = rom.loadArm9Overlays([8])[8]
    u8 = lambda a: struct.unpack_from("<I", ov8.data, a - ov8.ramAddress)[0]
    check(u8(SORT_FILL_COUNT_PTR) == SORT_SIZE_LIT and u8(SORT_SIZE_LIT) == OLD_COUNT,
          "B ov8 limit-sort cache fill reads its count from the 0x10D2 size literal")

    fid, data, by = _bin2(rom)
    arc = parse_format_v1(data, BIN2)
    check(all(f.address % 0x200 == 0 for f in arc.files), "C bin2.pac: every inner file 0x200-aligned")
    raw = {n: b for n, (_, b) in by.items()}
    N = OLD_COUNT + 1
    for n, w in (("card_prop.bin", 8), ("card_genre.bin", 8), ("card_pack.bin", 8),
                 ("card_pass.bin", 4), *((x, 2) for x in U16_FILES)):
        check(len(raw[n]) == N * w, f"C {n} = {N} records")
    prop = raw["card_prop.bin"]
    check(ct.prop_index(prop, NEW_CID) == NEW_IDX, "C card_prop[4306] is cid 0x25E3")
    from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
    f = GC.decode_entry(prop[NEW_IDX * 8:][:8])
    check((f["attribute"], f["race"], f["level"], f["real_atk"], f["real_def"], f["card_type"])
          == ("WIND", "Beast-Warrior", 4, 1700, 600, "Effect Monster"), f"C prop = {f['attribute']} {f['race']} Lv{f['level']} {f['real_atk']}/{f['real_def']}")
    check(struct.unpack_from("<I", raw["card_pass.bin"], NEW_IDX * 4)[0] == PASSCODE, "C passcode 10028593")
    check(raw["card_pack.bin"][NEW_IDX * 8:] == PACK_ROW, "C card_pack: pack_1 = 1, Common")
    intid = raw["card_intid.bin"]
    check(len(intid) == (NEW_END - CID_BEGIN) * 2
          and struct.unpack_from("<H", intid, (NEW_CID - CID_BEGIN) * 2)[0] == 0x8000 | NEW_IDX,
          "C card_intid[0x25E3] = monster | 4306")
    check(raw["card_intid.bin"][:(OLD_END - CID_BEGIN) * 2] ==
          _bin2(ndspy.rom.NintendoDSRom.fromFile(SRC))[2]["card_intid.bin"][1], "C stock intid prefix unchanged")
    for L in ct.LANGS:
        idx, names = raw[f"card_indx_{L}.bin"], raw[f"card_name_{L}.bin"]
        no = struct.unpack_from("<I", idx, NEW_IDX * 8)[0]
        s2 = struct.unpack(f"<{N}H", raw[f"card_sort2_{L}.bin"])
        s1 = struct.unpack(f"<{N}H", raw[f"card_sort_{L}.bin"])
        good = (len(idx) == (N + 1) * 8 and ct._cstr(names, no) == NAME.encode(ct.ENCODING[L])
                and sorted(s2) == list(range(N)) and all(s1[c] == p for p, c in enumerate(s2)))
        check(good, f"C [{L}] name, indx sentinel, sort permutation + inverse")

    card = bytes(rom.files[rom.filenames.idOf(CARD_PAC)])
    u = lambda o: struct.unpack_from("<I", card, o)[0]
    check(u(H_F2SIZE) == (N + 1) * 4 and u(H_F3SIZE) == N * ART64_STRIDE, "D card.pac: 4307 thumbs + tiles")
    print(f"{'ALL PASS' if ok else 'FAILURES'}")
    return ok


if __name__ == "__main__":
    main()
    print()
    verify()

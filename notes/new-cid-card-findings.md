# Adding a BRAND-NEW card (new cid) — findings (session 2026-10-27)

Goal: add Reborn Tengu as a NEW card at its Konami cid **0x25E3** (from the 3DS,
see notes/reborn-tengu-normal-donor-findings.md) instead of consuming a donor.
Base ROM: `data/over_the_nexus/working/rom_ov3_compact.nds` (stock + ov3 compaction step).

## STATUS AT END OF SESSION (2026-10-27) -- read this first; details below are chronological

**Shelved by the user** ("i dont think we need it"). Nothing is in `steps.STEPS`; nothing committed.

Code:
* `otn_enhanced/cards/new_cid_reborn_tengu.py` -- builds `rom_new_cid_tengu.nds`
  from rom_ov3_compact.nds; `verify()` 32 checks. Last build sha256 `2aae37ae...cb331ce`.
* `otn_enhanced/cards/new_card_save.py` -- in-place arm9 save-accessor rewrite (flag bits 6/7);
  `python -m otn_enhanced.cards.new_card_save` = emulator proof (0 failures).

What a new cid needs (the recipe):
1. arm9 `cid_to_intid` bound literal 0x02029E44 (the ONLY cid-range bound in code).
2. One appended record in all 64 per-card bin2.pac files + card_intid grown to cover the cid;
   one appended thumb + index + 64x64 tile in card.pac. 3DS CARD_* rows are layout-identical.
3. Global card count 0x0209D474 (+N) for the deck editor / lists; pack-list loop literal 0x0202A75C (+N).
4. Save: new_card_save (count + flags in flag bits 6/7, <= 128 cards).
5. ov8 limit-sort cache: pool 0x02155BF0 -> 0x02155BEC (fill capped at 4306; cosmetic sort-by-limit position).
6. ov3 effect rows keyed to the new cid (count-neutral; new max cid lands as the last in-range row).

In-game status:
* **Confirmed by user 2026-10-27** (build 01bfd9d9...): deck editor listing, pack-1 openings, normal
  duel, puzzle, every leave-the-field route ("It appears in the deck editor, it worked in a puzzle AND it
  worked in all modes of leaving the field to trigger its effect!").
* Save-planes build (a49fac20...): user said "Okay that worked." -- WHICH checks (0 copies / obtain /
  persists after reload) was asked and never answered => treat as AWAITING SPECIFIC CONFIRMATION.
* Sort-cache cap build (2aae37ae...): AWAITING IN-GAME TEST.

Capacity with everything above: **128 new cards** (save planes), except a ~100%-collection save
overflows the deck-editor trunk list past **75** new cards (unbounded writes into editor+0x11D48,
symptom unknown). Effect rows: migrating an existing donor card costs 0 phantoms (re-key); a
brand-new card needing criteria / leave-mask / sel0 rows has 0 spare phantoms -> virtual rows.

Open if resumed:
* Trunk-list >75 risk: trace what fills/reads editor+0x11D48 (static), or add a bound in the 3 builders.
* Sort cache with correct keys for N > 2: relocation canary into 0x0227D328..0x022C5900 (zero in all
  3 deck-editor savestates, not proven free) -- 4 pool/size words once proven.
* Shipping means REPLACING patch_reborn_tengu (same phantoms) and returning 0x1463 to vanilla.
* Moving other donor cards: per-card audit of donor-cid literals in their code (stubs, trees, trampolines).

## Confirmed (this session)

* **bin2.pac card files, per-card shape** (measured from rom_ov3_compact.nds, `s_cardnum.inc`):
  `DEF_ALLCARD_BEGIN 3400 (0xD48)`, `DEF_ALLCARD_END 9448+1 (0x24E9)`, `DEF_ALLCARD_NUM 4233`,
  `DEF_ALLTOKEN_NUM 72`, `DEF_ALLDATA_NUM 4306`, `DEF_ALLLINK_NUM 1903`.
  | file | size | shape |
  |---|---|---|
  | card_prop / card_pack / card_genre | 34448 | 4306 x 8 B, record 0 = all-zero header, sorted by cid |
  | card_indx_<L> (x8) | 34456 | 4307 x {u32 name_off, u32 desc_off}; last = sentinel (blob sizes) |
  | card_name_<L> / card_desc_<L> | var | NUL-terminated strings |
  | card_pass | 17224 | 4306 x u32 |
  | card_sort*_<L>, card_kana*, card_pwcost | 8612 | 4306 x u16 |
  | card_intid | 12098 | u16[6049] indexed `cid-0xD48`; low14 = prop record idx, b15 monster, b14 field |
  | card_link | 7612 | 1903 x u32 (not per-card) |
* card_prop max cid = 0x24E8; **0x25E3 is not present**, and lies outside the intid span.
* **The bin2 card files are loaded with dynamic sizes.** arm9 0x020297C4 loads CARD_Prop
  (+0x38), CARD_IntID (+0x3C), +0x30, CARD_Indx_# (+8), CARD_Name_# (+4), CARD_Sort_# (+0xC)
  into `[0x02121A5C+0x10]` via the generic file loader 0x020168E8 (no size argument). The duel
  path 0x02029CE0 loads IntID then caches only the cards in the 4 decks (0x020B8C18, stride
  0xC0, main/+0x84/+0xA2) through 0x02029C0C. Matches the 2026-09-08 note: no blob size is
  hardcoded. => appending rows to the files is safe for the LOADER.
* **The ONLY cid-range bound in code is arm9 0x02029E1C** (`cid_to_intid`): literals
  `0x0D48 @0x02029E40` and `0x24E9 @0x02029E44`; out of range returns 0 (= record 0, the header).
  Proven by a whole-image literal scan (arm9 + all overlays) for 0x24E9/0x24E8/0x0D48/0x17A1:
  every other 0x24E8 / 0x0D48 / 0x17A1 hit is a CARD cid used as a literal (cmp-equality in a
  switch, or a data-row cid), not a bound — disassembled each referencing site.
  * One secondary range: ov3 0x0218BF24 checks `0xED9 <= r1 <= 0x24E8`, returns 1 when out of
    range, else indexes a bitset at 0x02293A4C by `cid-0xED9`. Semantics unknown (see OQ).
* **Card-count literal 0x10D2 (4306)**: arm9 0x0202A75C, 0x0202AF3C, 0x0202AFC0, 0x0202B14C,
  0x0202B188, 0x0202B360, 0x0202B49C, + global u32 @0x0209D474; ov1 0x02146078; ov8 0x02155BEC,
  0x0216AFA0; ov10 0x0214E570, 0x021557F0; ov18 0x0214D884, 0x0215A07C; ov31 0x02165670,
  0x02180AD0. 0x10D1 at arm9 0x0202DE1C. (every site's literal referenced by a pc-rel ldr)
* **SAVE LAYOUT (master = 0x0212406C)**, from arm9 0x0202AF60 / 0x0202B0F8 / 0x0202B154:
  * `master+0x906 + idx/2` = **owned-count nibble** per card_prop record idx (even idx = low nibble),
    capped at 9 by 0x0202AFCC. 4306 nibbles end exactly at master+0x116E.
  * `master+0x116F + idx` = **per-card flag byte** (bits set by 0x0202B0F8(cid,bit,on), read by
    0x0202B154). 4306 bytes end at master+0x2240.
  * All accessors guard `idx < 0x10D2` (literal) — so with the literal unchanged a 4307th record
    is silently "not owned" / flags read as 1.
  * Savestate rom_all_patches.ml1 (RAM @file+0x24): master+0x2241..0x2245 = 00 (padding before
    the next field), so flags[4306] would land in padding. BUT count-nibble[4306] =
    master+0x116F low nibble = **flags[0]** (record 0 = header; it reads 0x07 in the savestate
    because invalid cids map to idx 0). => a 4307th card's owned-count ALIASES flags[0].
* **=> DO NOT bump the save-accessor literals.** With them unchanged: count getter 0x0202AEF8
  returns **9** for idx >= 0x10D2 (`movs r0,#9` @0x0202AF38), setter 0x0202AF60 is a no-op,
  flag getter 0x0202B154 returns 1, flag setter 0x0202B0F8 is a no-op. So record 4306 reads as
  "owned x9" and touches NO save byte. (Not a full fix: it can never be bought/lost.)
* **Global card count `[0x0209D474]` = 0x10D2** is what the LIST builders loop on (refs: arm9
  0x0202A368 card_link walk, 0x0202A77C password lookup over card_pass, 0x0202B0A4 flag-clear
  (also guarded by the literal); ov8 x7 deck editor; another ov 0x0215F2C0/0x02174A2C/0x021751E8/
  0x02175650/0x02175C94.. list UIs). Audited each referencing site:
  * dynamic `count*4` heap allocs (0x02174A2C) or plain `idx -> 0x02029E9C -> per-card accessor`
    loops -> safe at 4307.
  * **ov8 0x02155B98 writes `buf[idx]` for idx 1..count-1 into a FIXED 0x10D2-byte BSS buffer
    0x021FD1F0**. buf[4306] = 0x021FE2C2; the next referenced ov8 object is at 0x021FE2C4 (literal
    scan of all images for 0x021FD100..0x021FE400). => 2 bytes of alignment padding: ONE (or two)
    extra cards fit, no more.
  * ov8 deck-editor lists at editor+0xDA00 etc are fixed 0x4348 B = 4306 x {u16 cid,u8,u8}; they hold
    only qualifying cards (owned / limited); record 0 never qualifies, so 4305 + 1 new = 4306 fits.
  * ov8 0x02152354 loop is `ble` (1..count INCLUSIVE) -- stock already reads one record past the end;
    unchanged behaviour class at 4307.
  * 0x0x21A4 heap buffer (ov8 0x02155CB8) is the card_link "related cards" list -- bounded by matches.
* **0x02029E9C (idx -> cid)** reads the loaded CARD_Prop buffer `[+0x38] + idx*8` (or the duel
  cache 0x02029C0C, a 0x12D-entry BST keyed by record idx that reads CARD_Prop by file offset
  idx*8 through 0x02016A48) -> an appended record is reachable everywhere.
* **Per-card resources by cid in ov3**: BattleMonster sprite (`Duel2D/BattleMonster%d/%d_%s.LZ5bg`,
  0x0218C448) is existence-checked (0x02016C00) with two fallbacks -> missing sprite is safe.
  BattleEffect.bin byte (0x0218BF24) is range-checked 0xED9..0x24E8 and defaults to 1 outside.
  `/card128/%04d`, `/duel3d/%04d#` are NOT per-card (player/field UI, index 0..4).
* **card.pac**: file1 = 4306 LZ10 32x32 thumbs, file2 = 4307 u32 index (sentinel), file3 = 4306 x
  2820 B 64x64 tiles; indexed by card_prop RECORD index. A new record needs one appended entry in
  each (header size fields at 0x4D/0x51/0x55/0x59/0x5D, rel 0x200).
* **cls2 lookup find_event_handler 0x0224A118 is a lower_bound over [0,count) then reads row[lo]**
  (lo may == count). A key larger than every row lands on the LAST in-range row if that row is it,
  so inserting 0x25E3 as the new max inside [0,count) is found; row[count] (0x24E8) is never needed.

* **3DS rows are directly reusable.** 3DS CARD_Prop decodes under the NDS ERA2 layout byte-identically
  for shared real cards (0x1463, 0x0FD6 identical). Reborn Tengu = 3DS record 4748, prop
  `e3a52a1e83111800` = WIND / Beast-Warrior / Lv4 / 1700 / 600 / Effect. CARD_Pass equal for 3822/3822
  shared cards; Tengu's = 10028593 (= ygoprodeck id). CARD_Genre equal for only 2131/3822 (bits evolved).
* **BUILT: `patch_new_cid_reborn_tengu.py` -> `rom_new_cid_tengu.nds`** (from rom_ov3_compact.nds),
  sha256 `6ec9dc6f5551c3b712f9e6983bd1efd7a1662088257e358370dc1790ebb0e5d6`. verify(): 29/29 PASS.
  Whole-ROM diff vs base: arm9 = 0x02029E44 (0x24E9->0x25E4) + 0x0209D474 (0x10D2->0x10D3) + the
  usual MainCodeFile module-param bytes @0x02000B9C; overlay 3 only; files bin2.pac + card.pac only.
  ov3: mask row @151, cls2 @696 (last in-range row), criteria @1386; phantoms 0x14E9 (mask+cls2)
  and 0x1452 (criteria) dropped -- the SAME phantoms patch_reborn_tengu spends.
* KB: carddata.card_count_global, save.per_card_counts_and_flags,
  carddata.new_cid_needs_only_one_code_bound, deckedit.fixed_card_byte_buffer -- all VERIFIED, PASS.

**IN-GAME CONFIRMED by user 2026-10-27** on rom_new_cid_tengu.nds sha256 01bfd9d9...3067f5 (the
pack-1 rebuild). User's words: "Okay the card effect works perfectly! No bugs there AND it appears
in pack openings!" and "It appears in the deck editor, it worked in a puzzle AND it worked in all
modes of leaving the field to trigger its effect!" => a brand-new cid above 0x24E8 is PROVEN
workable: deck editor, pack openings, normal duel, puzzle, every leave route.

## Deliberate deviations (state before testing)

* Always "owned x9" (save literals untouched by design); the password 10028593 resolves to it but
  adding copies is a no-op.
* **2026-10-27 rebuild (user request): in PACK 1, Common** (card_pack row `00 00 00 01 00 00 00 00`)
  + pack-list builder 0x0202A608's own loop literal 0x0202A75C 0x10D2 -> 0x10D3 (single ldr user
  0x0202A734). Rebuilt sha256 `01bfd9d9744fab7e424e53be716cbbdf61fc82e67e819ed94bce106d2f3067f5`,
  verify 31/31 PASS. Appears in pack openings -- in-game confirmed by user 2026-10-27. The owned
  count stays 9 (setter 0x0202AF60 ignores idx >= 0x10D2) -- not separately reported.
* Not counted by the collection-% loops (ov1 emblem 95%, ov10, ov18, ov31 use their own 0x10D2 literal).
* Text is English in all 8 languages; pwcost + kana copied from 0x1463; j/k/r A-Z puts it last.
  Genre = the 3DS row (0x28), whose bit meanings are only ~56% NDS-compatible -> editor search only.
* No 2D battle sprite: the BattleMonster loader falls back (existence-checked).
* **Cannot coexist with the shipped patch_reborn_tengu in the chain** (same phantoms, two Reborn
  Tengus). Shipping this = REPLACING that patch and giving 0x1463 back. Not wired into STEPS.

## Ruled Out

* **Bumping the save-accessor 0x10D2 literals**: record 4306's count nibble would land on
  master+0x116F = flags[0] (alias). Leaving them gives a clean "owned x9, writes nothing".
* "Only append rows to the card_*.bin files": necessary but NOT sufficient for a cid > 0x24E8 --
  cid_to_intid maps it to record 0 (the blank header). One arm9 literal is also required. A cid
  <= 0x24E8 that is absent from card_prop needs only the rows + its intid entry -- no code edit.
* Scaled count constants: 0x4348 (ov8/ov10/ov31 list capacities), 0x21A4 (card_link list) -- all
  bounded by qualifying cards, not by the record count.

## Open Questions

* (Superseded -- see STATUS at the top: save storage and the sort-cache overflow were both solved later.)
* Does any code assume card_intid ends at 0x24E8 by reading its size? (Static: none found.)

## Scaling to ~100 new cards -- investigation 2026-10-27 (static + .sav census)

### Confirmed
* **Save file (64 KB) layout** = block table arm9 0x020ABD1C, two copies x 6 blocks (stride 0x18):
  copy0 {0x80 FAT_, 0x480, 0x8500 SYS_, 0xEB70, 0xF350, 0xF680 RPG_}, copy1 {0x680, 0xA80, 0xB838,
  0xEF60, 0xF4E8, 0xFB2C}. SYS (= RAM master 0x0212406C) is 0x3338 B (literal 0x0202C818/0x0202D224;
  checksummed body 0x3334 from +4, literals 0x0202C304/0x0202C380) and its two copies are ADJACENT
  (0x8500+0x3338 = 0xB838, 0xB838+0x3338 = 0xEB70). => SYS cannot simply grow.
* **Every access to the per-card save arrays is in arm9 0x0202AEF8..0x0202B49C**: whole-image literal
  scan for 0x906 / 0x116F / master+0x906 / master+0x116F / 0x10D2+0x9D finds only those sites
  (master+0x900 literals elsewhere are the u16 field master+0x904). All guard `idx < 0x10D2`.
* **74 dead save slots**: the "unownable" list arm9 0x0209D34C (0x4A cids, checked by cntadd
  0x0202AFCC so their counts are never written) = 72 Tokens + 0xD48 + 0xDAC. Token RECORD indices are
  CONTIGUOUS 173..244 (0xD48 = 1, 0xDAC = 60). Count nibble AND flag byte are 0 for all 74 in every
  .sav on disk (5 files x 2 SYS copies).
* **Flag bits 6/7 are unused**: wrappers exist only for bits 0..5 (0x0202B058..0x0202B0F4: get0/set1/get1/
  set2/get2/get3/clr3all/set4/get4/set5); direct writers mask 0xF7 / OR 2 (preserve 6/7); census of every
  flag byte in every .sav: bits 3,5,6,7 never set. => 2 spare bits x 4306 records = 8612 bits.
* **Deck editor trunk list** (ov8 builders 0x02154360 / 0x02154498 / 0x02154570) writes {u16 cid, u8 count}
  for EVERY card with count > 0 or flag bit0, unbounded, into editor+0xDA00; the next list is at
  +0x11D48 => capacity 0x4348/4 = 4306. Ownable stock cards = 4305 - 74 = 4231 => a 100%-collection
  save overflows once N_new > 75. `editor+0xDA00` is formed by 15 `add rX, base, #0xDA00` sites
  (+5 list-copy sites using 0x4348); editor struct = 0x1D948 B (7 literal refs), fields to +0x1D942.
* **ov8 0x021FD1F0 buffer is a SORT-KEY CACHE**: buf[idx] = 0x0202AD60(cid) filled by 0x02155B98 (8 call
  sites); read only by the list sort comparators (e.g. 0x02156234 `ldrb r0,[r7, idx]`).

### Ruled out (user challenge 2026-10-27, confirmed by disassembly)
* **ONE-WAY token-slot reuse is unsafe.** Duel code writes save flags for field cards: ov3
  0x0214A3F0 calls set2 0x0202B07C(cid, 1) for any zone index < 0x10 (monster zones included);
  0x02148EC0 for zones 5..9; 0x02149118 / 0x0214AD70 / 0x0217E2EC (set1) with other cids. A Token on
  the field can therefore reach its own save slot; the all-zero census is not proof it never does.
  => the remap must be TWO-WAY: token record idx 173..244 -> out-of-range behaviour (writes no-op,
  count 0, flags clear) AND new idx 4306+k -> 173+k. Same hook points, +2 instructions.
  Flag bits 6/7 remain the zero-collision alternative store.

### Save store for new cards = flag bits 6/7 "planes" (user chose 2026-10-27) -- BUILT + EMULATED
* Layout: new card k = record 0x10D2 + k (k < 128). Field bit j (0..3 count, 4+b = flag bit b) lives at
  byte `FLG + 1 + j*64 + (k>>1)`, bit `6 + (k&1)` (FLG = master+0x116F) -> host records 1..640, bits 6/7.
  Clear-all-bit-3 = AND 0x3F over plane 7's 64 bytes.
* **In place, no cave**: arm9 regions rewritten at their ORIGINAL entry points, each the same length:
  A cntget_idx 0x0202AEF8 (72/80 B), B cntset 0x0202AF60 (100/108), D clear-bit3 0x0202B0A0 (44/52),
  C flagset 0x0202B0F8 + flag_addr + nf_ptr + flagget @0x0202B154 (144/152). New internal entries:
  flagset_idx 0x0202B10A, flag_addr 0x0202B126, nf_ptr 0x0202B13C. The two inline bit-1 sites
  0x0202B32E (idx in r4) / 0x0202B474 (r5) become `adds r0,rX,#0; movs r1,#1; movs r2,#1; bl flagset_idx`.
* ⚠️ TOOL FOOTGUN found: ThumbAssembler sizes `insn("BL", "<label>")` as 2 bytes but emits 4, so every
  later label is off by 2 (flagget landed at 0x0202B156, calls hit `adds r1,#4`). Use `a.bl(addr)` with
  a two-pass label resolve. Caught by the emulator test before any ROM was built.
* **PROOF (scratch/thumbemu over arm9 + a real SYS block from rom_all_patches.sav + the new intid)**:
  400 random stock ops (get/set/add/sub/flagget/flagset/clear) -> getter returns and the WHOLE SYS
  block byte-identical stock vs patched; EXHAUSTIVE count + flag bits 0..5 for all 4305 stock cards
  identical; inline-site replacement == stock OR 2; new card 0x25E3: set 7/get 7, add caps 9, sub,
  flags 0..5 set/clear; 128 k x 6 bits isolation; clear-all clears plane 7 only; stock bits 0..5 and
  every stock count nibble untouched. 0 failures. Now in-repo: `otn_enhanced/cards/
  new_card_save.py` (`apply(a9, n_new)`, stock-SHA1-guarded; `python -m ...new_card_save` re-runs the
  emulator proof -> 0 failures). Block 0x0202AEF8..0x0202B4A0 is byte-identical in rom_all_patches.nds,
  so no shipped patch touches it.
* **REBUILT rom_new_cid_tengu.nds with the save planes** (2026-10-27), sha256
  `a49fac20447d6c53e1be379c8bf041224cf4ba1331f3cfff0b51909c39723204`, verify 31/31 PASS,
  assert_thumb1_only OK on all 6 blobs, arm9 diff = 410 bytes, all inside the intended regions.
  Behaviour change vs the confirmed build: Reborn Tengu now starts at **0 copies** (real ownership)
  and must be pulled from pack 1 or entered by password 10028593. AWAITING IN-GAME TEST.

### Phantom census (2026-10-27, rom.nds vs rom_all_patches.nds; phantom = row cid with no card_prop record,
### "unclaimed" = not in check_allocations.PHANTOM_CLAIMS)
| table (find_event_handler sel / base) | rows | phantoms stock -> chain | unclaimed in chain |
|---|---|---|---|
| sel0 0x02275C04 | 697 | 67 -> 23 | 0 |
| sel1 0x0227E64C | 1306 | 79 -> 75 | 38 |
| sel2 0x022860D4 | 1333 | 141 -> 104 | 44 |
| sel3 0x02279D74 | 776 | 80 -> 55 | 20 |
| criteria 0x022713C4 | 1388 | 90 -> 4 | 0 |
| leave-mask 0x0226EC1C | 152 | 22 -> 10 | 0 |
* => brand-new cards that need a criteria / leave-mask / sel0 row have NO spare phantoms left. The
  existing escape hatch is VIRTUAL rows/records (Dragon Rulers: hook the lookup miss paths -- find_event_handler
  miss 0x0224A86A, criteria resolver miss tail 0x02243F24; Tenki / Sacred Sword / Infernoble chain the same).
* **Migrating an already-implemented donor card to a new cid costs ZERO phantoms**: its rows already exist and
  are just re-keyed (count-neutral re-sort). The per-card cost is every cid LITERAL in its code (cave stubs,
  per-cid compare trees, trampolines) -- needs a per-card audit, not table space.

### Sort-key cache 0x021FD1F0 (ov8)
* Fill 0x02155B98: memset(buf, 0, 0x10D2) then buf[idx] = 0x0202AD60(cid) for idx 1..[0x0209D474]-1.
  Readers: three `ldrb r?, [buf, idx]` in the sort comparators (0x02156228/0x02156234 via pool 0x02156320,
  0x0215682C via pool 0x02156938), only in the "sort by limit" mode (flag 0x100).
* 0x0202AD60 = BANLIST LIMIT lookup (0x0202AD9C -> 0x0202AC90, which can load a file and scans the
  limit list): far too expensive per comparison -> "compute it directly" is RULED OUT.
* RAM above ov8 in the deck editor (3 ov8-resident states: default_list.mln, limited_is_forbidden.mln,
  rom_highlander_test.ml1): 0x02221FE0..0x0227D327 holds data matching NO overlay image (live or stale,
  undecidable from snapshots); 0x0227D328..0x022C5900 (~290 KB) all zero in all three. No overlay that can
  co-reside with ov8 maps there; no code literal points at 0x02221FE0. NOT PROVEN FREE.
* Options: (1) DATA-ONLY: repoint the fill loop's count literal 0x02155BF0 (=&global 0x0209D474) at
  0x02155BEC (which holds 0x10D2) -> the fill never writes past 4306; new cards' limit-sort key reads the
  bytes after the buffer (garbage, read-only) -> cosmetic mis-sort in that one sort mode, no overflow at any
  count. (2) Relocate the cache (pools 0x02155BE8 / 0x02156320 / 0x02156938 + size 0x02155BEC) into a grown
  ov8 BSS -- needs a canary run to prove the region above ov8 is free.

* **BUILT option 1 (user choice 2026-10-27)** in patch_new_cid_reborn_tengu: ov8 pool 0x02155BF0
  0x0209D474 -> 0x02155BEC. Rebuilt rom_new_cid_tengu.nds sha256
  `2aae37ae853ae5da48a103838fb9c82cc1d3a9f3ad05fe12ff7e1c59fcb331ce`, verify ALL PASS (32 checks);
  overlays differing vs base = 3 and 8; ov8 diff = exactly that word (3 bytes), same length.
  Accepted deviation: new cards' position in "sort by limit" mode follows the bytes past the buffer.
  AWAITING IN-GAME TEST.

* **The object right after the sort cache (0x021FE2C4) IS THE DECK-EDITOR STRUCT** (static, ov8 BSS):
  it is `this` for the editor init 0x02150F7C (ov8 0x0214CAC4 `ldr r0,=0x021FE2C4 ; bl 0x02150F7C`) and
  teardown 0x02151258 (0x0214CB70); init memsets 0x1D948 B (0x02150F88) then calls the cache fill
  0x02155B98 (0x02150FB0). So an UNCAPPED fill past 4308 records writes limit values (0..3) into the
  editor struct's first bytes right after they were zeroed. Struct = 0x021FE2C4..0x0221BC0C, so the
  trunk list is 0x0220BCC4 and the next list 0x0221000C (static, not heap -- corrects "heap alloc").

### Verdict per limit (as first written -- 1 and 2 were later RESOLVED: save = flag bits 6/7 in place,
### sort cache = one-word cap; see STATUS at the top)
1. **Save storage** -- ABATABLE for 72 cards cleanly: remap idx 4306+k -> 173+k (token slots) at the
   accessor guards; pure arithmetic (contiguous), full count+flag fidelity, dead in every save. Up to 100+:
   cards beyond 72 can live in flag bits 6/7 (5 host bytes per card) -- more code, same hook points.
   BLOCKER: the hook code needs an ALWAYS-RESIDENT home (menus, not just duels): ov5/ov3 are not
   resident in the deck editor; the arm9 static-cave canary froze on duel entry (ov3-cave-findings
   round 3b-v2). Candidate: rewrite the accessor block 0x0202AEF8..0x0202B49C IN PLACE more compactly
   (count get/set each carry duplicated even/odd paths) -- not yet measured.
2. **ov8 sort-key cache** -- ABATABLE: 3 pointer literals (0x02155BE8, 0x02156320, 0x02156938) + size
   0x02155BEC. Needs a >= 0x10D2+N byte region free while the editor runs (e.g. ov8 BSS grown past
   0x02221FE0) -- unproven without a deck-editor savestate. Alternative: make the comparators call
   0x0202AD60 directly (no buffer).
3. **Trunk list capacity (NEW)** -- hard. N <= 75 is safe for every save; N > 75 overflows only on a
   ~100% collection. Fixes: relocate the list (15+5 ov8 sites; 0x1D948+ is not an ARM imm, so each
   needs a 2-insn rewrite) or a bound-check in the 3 builders (truncates the list instead of overflowing).

## Next Experiment (only if the work is resumed)

On the latest `rom_new_cid_tengu.nds` (2aae37ae...):
1. Save planes: existing save shows Reborn Tengu at 0 copies and every other card's count unchanged;
   pull one from pack 1 (or password 10028593); count rises and survives save + reload; "NEW" marker.
2. Sort cache: deck editor in every sort mode incl. "sort by limit" -- no freeze, Reborn Tengu listed.
(The original 1-3 -- editor listing, leave-field effect, puzzle -- are confirmed; see STATUS.)

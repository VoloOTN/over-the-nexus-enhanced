# card_name_e / card_desc_e — how to get more text space

## RESOLVED — in-game confirmed by user 2026-09-08

Two confirmations, both from the user in this session:

- Three-card build (`rom_textgrow.nds`): *"That works!"*
- All-45-card build (`rom_cardtext.nds`): *"Looks good in deck editor and in-duels!"*

**THE RULE: never append a string past a blob's end. Re-emit the blob IN INDEX
ORDER.** The deck editor derives its description read length from the gap to the
next `card_indx` entry, so an appended string leaves a negative gap and the read
runs away — full teardown under *IN-GAME TEST 1* below.

Shipping path: text lives in
[card_text.py](../otn_enhanced/data/card_text.py) (45 cards x 8
languages, `None` = fall back to English); build with
[_build_card_text.py](../_build_card_text.py). KB fact:
`text.desc_length_is_the_index_gap` (VERIFIED, PASSes against stock).
It corrects `donor.name_slot_floor` and `donor.name_blob_has_no_slack`, whose
"the engine copies the blob into a fixed-size buffer" reason was wrong.

Encodings, measured by round-tripping every stock name blob: **e/f/g/i/s =
latin-1, j = cp932, k = cp949, r = cp932**. ⚠️ **`_r` IS NOT RUSSIAN** — it is
Japanese with ruby markup (`$R<kanji>(<furigana>)`; entry 254 is
`$R剣龍(ソード・ドラゴン)`).


Investigation 2026-09-08. Everything below was measured **this session** against
`data/over_the_nexus/working/rom.nds` (EU `BYYP`), scripts in the session
scratchpad.

## Confirmed

**Structure.** `card_indx_<L>.bin` is 34456 B = **4307 × {u32 name_off, u32
desc_off}** into `card_name_<L>.bin` / `card_desc_<L>.bin`. Entry 4306 is an end
sentinel: its `name_off`/`desc_off` equal the two blobs' exact file sizes
(0x14AA0 = 84640 and 0xC8794 = 821140 for English). 4306 real cards, matching
`card_prop.bin`. Same shape on the 3DS (`CARD_Indx_E.bin`, 5888 entries).

**Offsets are free-form.** All 8 languages: every offset is 4-byte aligned and
strictly increasing today, but nothing in the format requires either. Two cards
may legally share one offset; order need not match card index.

**Length is NUL-scanned, not `offs[i+1] - offs[i]`.** Proven by shipped,
in-game-confirmed patches: Boggart Knight writes `"XXS - Boggart"` (13 B) into a
longer slot and Maiden writes a 45 B desc into a 51 B slot — both re-NUL-terminate
and leave the delta larger than the string, and both render correctly. So freeing
padding / reordering / deduping is safe for the consumer.

**657 B descriptions already render.** Longest English desc in the stock ROM is
657 B (Manga Ryu-Ran 0x127D, and Toon Mermaid / Toon Summoned Skull /
Blue-Eyes Toon Dragon). Mean is 188 B, 205 cards are ≥400 B. The 51 B / 116 B
"budgets" in patch modules are **donor slot sizes, not engine limits**.

**No blob size is hardcoded anywhere in code.** Scanned ARM9 + all 50 overlays
for u32 == any of {821140, 84640, 34456, 34448, 1517140, 4306, 4307}: the only
hits are `4306` (card count, 9 sites) and one `4307` that is a false positive
(a pool literal 0x10D3 inside an ov3 cid switch at 0x021D7658). There is **no
size constant behind the KB's "the engine copies the blob into a fixed-size
buffer" claim** — see *Open Questions*.

**bin2.pac layout invariant: every inner file starts on a 0x200 boundary.**
99 files, all addresses ≡ 0 mod 0x200; the 98 inter-file gaps are 8–496 B of
**pure zeros** (never ≥0x200), i.e. padding sized exactly to reach the next
boundary. `file_data_beginning_address` = 0xC00, 10 trailing bytes after the
last file.

### ⚠️ THE BUG — why growing a blob froze the game

`patch_boggart_knight._rebuild_v1_pac` and `otn_enhanced.rom.pac.repack_pac`
both preserve the **gap length** between files, not the **0x200 boundary**:

```python
original_padding = next_file.address - (pac_file.address + pac_file.size)
current_addr += new_size + original_padding      # <-- keeps the gap, loses the boundary
```

Measured: growing `card_desc_e.bin` by 101 B and rebuilding puts **90 of 99
inner files at addresses ≡ 101 (mod 0x200) — i.e. at ODD addresses**. A `u32`
read of `card_indx_*.bin` from an odd address is a misaligned ARM load
(rotated garbage), and the cart/DMA path wants 512 B sectors. This is the
mechanism behind patch_boggart_knight's note that appending
`"XX-Saber Boggart Knight"` "correlated with a freeze when selecting the card":
the freeze was not the name blob, it was every file that got shifted off its
boundary.

Seven modules carry a private copy of `_rebuild_v1_pac` (boggart_knight,
dragon_shrine, shiens_dojo, safe_zone, tg_table, vylon_element,
w_nebula_meteorite, infernity_barrier) plus `pac.repack_pac`; **all of them only
ever write same-size replacements today, so the bug is dormant** and none of the
shipped ROMs are affected.

### FIXED 2026-09-08 in `otn_enhanced/rom/pac.py.py` (`repack_pac`)

The layout pass now rounds each new address up to the archive's own boundary
(derived from the original file addresses, so a PAC that was never 0x200-aligned
is still reproduced as it was), and the data pass emits padding sized to the new
address — reusing the original gap bytes when the length is unchanged, so an
untouched PAC still round-trips byte-for-byte.

Only `repack_pac` was touched. `build_modified_pac` short-circuits every
same-size edit through its in-place fast path *before* reaching `repack_pac`, so
**no existing caller's output changes**; only size-changing edits reach the new
code. The seven private copies in patch modules were deliberately left alone
(scope discipline — they are dormant, and sweeping a change across shipped
patches is what broke the 33-patch donor migration).

Self-check: `.venv-1/Scripts/python.exe -m otn_enhanced.tests.test_pac_alignment`

```
OK  99 inner files, boundary 0x200
OK  no-op repack byte-identical (10,974,720 B)
OK  +102 B growth -> 10,974,720 B, all files still 0x200-aligned
```

It asserts (a) the stock 0x200 invariant and that every gap is pure zeros,
(b) a same-size replacement reproduces bin2.pac byte-for-byte, (c) a **+102 B**
(deliberately not a multiple of 0x200) growth of `card_desc_e.bin` leaves all 99
inner files 0x200-aligned and every untouched inner file byte-identical.

**Free headroom before bin2.pac's total size changes at all** (growth absorbed
by the gap that already follows the file): `card_desc_e.bin` **+108 B**,
`card_name_e.bin` **+352 B**. Past that the archive grows in 0x200 steps.

STATUS: **AWAITING IN-GAME TEST.** The rebuilder is proven correct at the
archive level; nothing here has been run in melonDS, and Open Question 1 below
(is the blob's RAM buffer sized from the PAC table?) is still unanswered.

### The budget you already have without growing anything

Tight-repack of the blob (dedupe identical strings, keep the ROM's own 4-byte
alignment, keep the file size unchanged), bytes freed:

| lang | name | desc |
|------|------|------|
| e | 400 | **9 644** |
| f | 460 | 10 704 |
| g | 496 | 10 832 |
| i | 428 | 9 864 |
| s | 444 | 9 840 |
| j | 444 | 8 648 |
| k | 2 648 | 9 184 |
| r | 684 | 15 072 |

Dropping to 1-byte packing (no alignment) roughly: name ≈ 6.8 KB, desc ≈ 16 KB
per language — but that makes offsets unaligned, which is unproven (see below),
so 4-align is the safe number.

**9 644 free bytes in `card_desc_e.bin` at zero layout risk** ≈ 60 cards' worth
of full printed text at ~150 B extra each. Names are already tight: only 400 B
at 4-align.

## Ruled Out

- "The desc slot is an engine limit." No — 657 B ships stock; the limit is the
  donor's own string length, which is an artifact of writing in place.
- "The spare `card_indx` entry is a free slot." It is the end sentinel
  (`name_off`/`desc_off` == file size). Confirms the existing KB fact
  `donor.name_blob_has_no_slack`.
- "There are unreferenced strings to steal." No. Every byte that is not
  4-byte alignment padding is reachable from some index entry: UNREACHABLE is
  6456 B (name_e) / 6460 B (desc_e), and that is exactly the padding.
  Trailing zero padding is 2–4 B in every language except Korean (~2065 B).
- "Growing the blob is inherently unsafe." Not shown. What was actually unsafe
  is the rebuilder's alignment handling.

## ANSWERED — the blobs are NEVER loaded into RAM

Scan of `data/over_the_nexus/working/normal_duel.mln` and `puzzle.mln` (RAM base
auto-detected at file offset 0x24 by matching an ov3 signature):

- `card_indx_e.bin`, `card_name_e.bin`, `card_desc_e.bin` — **none resident**,
  not even their first 64 bytes.
- Of 3957 names ≥10 B, exactly **4 are resident** — and they are the cards on
  screen (Red-Eyes Darkness Metal Dragon, Gladiator Beast Gyzarus, Don Zaloog,
  Amazoness Queen).
- Exactly **one full description** is resident, at RAM 0x02111C7C: a 265 B
  string (Red-Eyes Darkness Metal Dragon's), with the tail of a previous string
  still visible at 0x02111D88 — a reused scratch arena, overwritten per card.

So the engine seeks and reads **one string at a time** from the cart. **Blob file
size is not a RAM constraint at all**, and the KB's "the engine copies the blob
into a fixed-size buffer" (in `donor.name_slot_floor`) is **WRONG** — it was
inferred from the Boggart freeze, which the alignment bug above fully explains.

⚠️ CAVEAT: both savestates are duels. The deck-editor / card-list path is
unmeasured, and Boggart's freeze was "when selecting the card" (a menu).

### The per-card ceiling, proven by stock data

Longest string shipped in the stock ROM, per language:

| lang | max name | max desc |
|------|---------:|---------:|
| e | 47 | 657 |
| f | 60 | 827 |
| g | 62 | 829 |
| i | 59 | 792 |
| s | 57 | 788 |
| j | 64 | 684 |
| k | 38 | 680 |
| r | **110** | **1196** |

Russian ships a **1196 B description** and a **110 B name** and renders them, so
the render buffers are ≥1197 / ≥111 B. Any real printed card text (~300 B) fits
with room to spare. **The 51 B / 116 B "budgets" in the patch modules are donor
slot sizes and nothing else.**

### ROM-level headroom

- Stock `rom.nds` is 134,217,728 B = exactly the cart size for capacity byte
  0x0A; `used rom size` (header +0x80) is 129,320,960 → **4,896,768 B of trailing
  padding**. Current `rom_all_patches.nds` is 129,593,992 B → **~4.4 MB spare**.
- End-to-end test: grew **both** `card_desc_e.bin` and `card_name_e.bin` by
  **64 KB each** (bin2.pac 10,974,720 → 11,105,792), rebuilt the ROM, reopened
  it: all 99 inner files still 0x200-aligned, `card_desc_e.bin` = 886,676 B at
  0x10F600, capacity byte unchanged at 0x0A, used size 129,452,032.
- ndspy trims the trailing padding on save (output 129,452,168 B, not 128 MB).
  That is the **existing** behaviour — every shipped ROM in
  `data/over_the_nexus/working/` is already ~129.5 MB and in-game confirmed — so
  it is the status quo, not a new risk.

## THE `_place_string` CORRUPTION — root cause, fixed 2026-09-08

Caught by the new per-step guard in `apply_all_patches.main()` (`_check_card_text`,
which re-reads the ROM after every step and aborts naming the culprit). Chain
step 30, `patch_snoww`:

```
*** STEP 30 (... -> Snoww, Unlight of Dark World) CLOBBERED CARD TEXT ***
    cid 0x245b lang 'k'
    was:  name b'Karakuri Komachi mdl 224 "Ninishi"'                             desc 325B
    now:  name b'Karakuri Komachi mdl 224 "Ninishi"Snoww, Unlight of Dark World' desc 452B
```

**Mechanism.** `_place_string`, when a name does not fit its slot, relocates into
the file's "trailing zero padding" — located by walking **backwards from the file
end over NUL bytes**. On a stock blob that stops after 2–4 B and safely returns
`None`. On a blob re-emitted in index order, a language whose trailing entries are
empty strings (Korean) is one long NUL run, so the walk strides back over real
strings and returns a cursor sitting on **another card's NUL terminator**.

**Fixed at the definition, in all three copies** (`patch_reborn_tengu`,
`patch_grapha`, `patch_snoww`): relocation now always returns `None`. Not guarded
at the 5 call sites, deliberately — `patch_conscription_c3` and
`patch_zeta_reticulant` also use it and are NOT in `CARD_TEXT`, so a call-site
guard would leave them able to corrupt a neighbour. Nothing is lost: the KB
already recorded this fallback as effectively dead (stock blobs carry 2–4 B of
trailing padding), and every renamed card now gets its text from
`card_text.apply_to_rom`.

⚠️ Also cost three chain builds: restoring `k` to `TEXT_LANGS` in the two Jet
modules tripped **three** separate asserts encoding "Korean slots are 0 B"
(`patch_jet_warrior` `min(NAME_SLOTS)`, its `DESC_LADDER._desc_for` `SystemExit`,
and `patch_jet_synchron`'s `assert "k" not in TEXT_LANGS`), discovered one per
28-minute build. **Grep the whole family of guards before changing what a module
writes.** Cleanup handoff: `PROMPT_card_text_slot_cleanup.md`.

## A-Z SORT TABLES (2026-09-08) — sort mechanism reported OK in-game

Renaming a card also has to move it in the deck editor's alphabetical list.
Four tables, all 4306 x u16, measured from stock:

- `card_sort2_<L>[position] = card index` — the A-Z order
- `card_sort_<L>[card index] = position` — **exactly the inverse permutation**,
  verified in all 8 languages
- `card_kana1_<L>[card] / card_kana2_<L>[card]` = first / second character of
  the name (the A-Z jump bar)

**COLLATION** (fitted to stock): decode cp1252, expand ligatures
(`ß`→ss, `œ`→oe, `æ`→ae), lowercase, fold accents, drop `-` and `'`, KEEP
spaces. Reproduces **e / f / i exactly** — 0 inversions, 0 of 4306 positions
differ. ⚠️ Wrong guesses that cost time: punctuation is NOT ignored (`"A" Cell`
sorts before `4-Starred` because `"` is 0x22), and `-` is NOT reranked — it is
*removed*.

**g has 1 pre-existing inversion and s has 3**, all on names starting with
typographic punctuation (`„A“-Zellen`, `¡Huracán!`, `¿Bajada?`) that this key
does not model. So `resort()` INSERTS into the existing permutation rather than
rebuilding it: every untouched card keeps its exact stock position and those
anomalies are preserved rather than "corrected".

⚠️ **j / k / r are NOT re-sorted** (kana/hangul collation, 1400-1800 inversions
under this key). Those cards keep their old slot. Guessing would be a silent
regression that cannot be validated from here.

### IN-GAME CONFIRMED by user 2026-09-08

Two reports, verbatim, in order:

1. On an intermediate build: *"So far the sorting looks good and not causing
   issues"* (provisional).
2. On the final artifact (sha256 `c92dcafb…`, 55/55, 0 clobbers):
   ***"Looks good all the cards are sorted!"*** — full sign-off.

KB fact: `text.sort_tables_follow_the_name` (VERIFIED, closed structural proof
against stock; 446 facts / 408 PASS / 0 FAIL).

### Measured effect on the chain ROM

| ROM | English inversions |
|---|---:|
| stock `rom.nds` | 0 |
| `rom_all_patches.PRE_SORT.nds` (before this work) | **45** (one per renamed card) |
| current build | **2** |

⚠️ Do NOT compare a chain ROM's inversion count against STOCK — every renamed
card is an inversion until it is resorted, so stock's 0 is not the baseline.

### Known defects in the current build (all pre-existing, none from the resort)

1. **The 2 remaining inversions are cards this module never knew about.**
   `CARD_TEXT` was harvested from `_verify_all_patches.SHIPPED` (46 modules),
   but `apply_all_patches` runs **55** steps. Missing renamers:
   `patch_karakuri_haipa` ("Karakuri Haipa", cid 0x167E),
   `patch_metal_armored_bug` ("MetalArm Bug", cid 0x0FD8),
   `patch_wonder_wand` ("Wonder Wand"). Also unchecked:
   `patch_regulus`, `patch_conscription_c3`, `patch_vylon_element`.
   FIX: harvest from `apply_all_patches`, not `_verify_all_patches`.
2. **Jet Synchron 0x224C / Jet Warrior 0x23EB have NO Korean text** — both
   modules set `TEXT_LANGS = "efgijrs"` with a comment that the donor's Korean
   slots are 0 B. That constraint is OBSOLETE (the blob is re-emitted in index
   order, so slot size no longer matters). FIX: restore `k`.
3. **Ninishi 0x245B's Korean description is missing its NUL terminator** — it
   reads 452 B: its own correct 325 B text immediately followed by a Dark World
   card's text. Some later step writes the Korean desc blob in place without
   re-terminating. NOT yet traced. English is correct.

## ⚠️ CORRECTION — misalignment is NOT what froze Boggart

Measured while building the test ROM: **`rom_all_patches.nds` already ships with
87 of its 99 bin2.pac inner files off their 0x200 boundary, and 82 of them not
even 4-byte aligned** (first: `card_desc_s.bin` @0x1FAC13, mod 0x200 = 19). Its
pac is 10,974,932 B, +212 over stock, and the name blobs are already grown:
f +19, g +32, i +19, j +56, k +86 (e/s/r unchanged) — some shipped patch appends
a name in exactly the languages whose slot is too short, via one of the buggy
private `_rebuild_v1_pac` copies. `rom_cardart.nds` and stock are clean.

**That ROM is in-game confirmed for many cards.** So archive misalignment is
evidently survivable — consistent with the DS reading cart files through a
sector-buffered file API rather than by pointer arithmetic. Retract the earlier
claim in this note that the alignment bug "fully explains" the Boggart freeze:
**the cause of that freeze is unknown again.** The alignment fix stands as
correctness/hygiene (it restores the format's own invariant), not as the
explanation.

Consequence for `repack_pac`: the boundary must NOT be derived from the input
archive. Deriving read the already-damaged chain pac as "1-byte aligned" and
tight-packed it, *shrinking* bin2.pac by 12,522 B. It is now flatly 0x200 for
`v1_marker` (which is the format's own rule — see `parse_format_v1`'s
`fileDataBeginningAddress` rounding), so repacking a damaged v1 pac **re-aligns**
it back toward stock.

## Test ROM built 2026-09-08 — AWAITING IN-GAME TEST

`_build_text_growth_test.py` → `data/over_the_nexus/working/rom_textgrow.nds`
(129,600,136 B, cap byte 0x0A, used 129,600,000 of 134,217,728).
Source: `rom_all_patches.nds`. Changes **text only** — no effect, no stats, no code.

| card | donor | prop idx | name | desc |
|------|-------|---------:|-----:|-----:|
| Lightpulsar Dragon | Sword Arm of Dragon 0x0FB1 | 254 | 18 B | 88 → **359 B** |
| XX-Saber Darksoul | Deep Diver 0x1CE6 | 2569 | 9 → **17 B** | 98 → **161 B** |
| T.G. Rush Rhino | Dash Warrior 0x22E6 | 3926 | 12 → **15 B** | 68 → **278 B** |

All 8 languages get the English text (same convention as every existing patch).
bin2.pac 10,974,932 → 10,981,376 (+6,444). Verified: 99 inner files 0x200-aligned
(so this build also **repairs** the 87 that were off), all 24 new strings read
back through `card_indx_<L>`, every other card's offsets unchanged, blob bodies
byte-identical up to the append point.

⚠️ Confound to keep in mind: this ROM both grows the blobs **and** re-aligns the
87 files the chain build had knocked off. If it misbehaves, rebuild from stock
`rom.nds` to separate the two.

⚠️ Text is verbatim modern wording from `ygoprodeck_cache.json` ("GY",
"banishing"). The ROM's era says "Graveyard" / "removed from play".

## IN-GAME TEST 1 — FAILED (user, 2026-09-08)

User's exact words: *"See .ml3, the rom freezes when I selected lightpulsar dragon,
plus the text box displayed no text."* Confirmed by the user: **deck editor**,
game does not respond to any input, `rom_textgrow.ml3` is the frozen state.
They did not get to check Darksoul or Rush Rhino.

### Proven from the frozen savestate (`rom_textgrow.ml3`, RAM0 = file 0x24)

1. **It is an ARM9 data abort.** melonDS `ARM9` section (registers are
   `word[4+i]`, CPSR `word[20]`): CPSR = **0x20000097** → ABT mode, ARM state,
   IRQs disabled. PC = **0xFFFF0108**, CurInstr/NextInstr = `0xEAFFFFFE` =
   `b .` — spinning forever in the abort handler, and **SP = 0** in abort mode,
   so the handler cannot even recover. That is the hard hang.
2. **Faulting instruction: `0x0205113C  ldr r1, [r0, #0x64]` with R0 = 0x28.**
   It sits in this ARM9 list walk:
   ```
   0x02051124  ldr  r0, [pc, #0x20]   ; -> 0x0212E7C4
   0x02051128  ldr  r0, [r0, #0x24]   ; head
   0x0205112c  b    0x2051134
   0x02051130  ldr  r0, [r0, #0x68]   ; next
   0x02051134  cmp  r0, #0
   0x02051138  bxeq lr
   0x0205113c  ldr  r1, [r0, #0x64]   ; <<< ABORT
   0x02051140  cmp  r1, #1
   0x02051144  bne  0x2051130
   ```
3. **The walk reproduces exactly, offline, from the savestate:**
   head `[0x0212E7C4+0x24]` = 0x0213D6A8 → 0x0213AE10 → **0x02128E58** → **0x28**
   → unmapped → abort. Nodes 0 and 1 are well-formed (`+0x64` flag, `+0x68` next,
   `+0x6C` count = 3 then 6).
4. **0x02128E58 is not a node — it is `card_pack.bin` data** (matches that file
   at inner offset 0x46D4). `card_pack.bin` is resident at **0x02124784**, and
   only **29,811 of its 34,448 bytes match** — a short/partial load. So node1's
   `next` points into a data buffer.
5. **The heap is NOT corrupted.** Block header is 16 B `{u16 magic 0x5544 "DU",
   u16 flags, u32 size, u32 prev, u32 next}` — ⚠️ the magic's high half is a
   FLAGS field, non-zero on plenty of live blocks; checking the full word gives
   a false "corruption" hit. Walking with the mask: **71 blocks, clean chain,
   no absurd sizes.**
6. **The deck editor DOES load `card_indx_e` and `card_name_e` wholesale**, and
   at their **grown** sizes — `card_indx_e` 34,456 B at 0x022F21B8,
   `card_name_e` **84,696 B** (the grown size) at 0x022FA860, both fully
   contiguous, each in a `DU` block whose recorded size matches. So the name
   growth did **not** overflow its buffer. `card_desc_e` is **not** resident even
   in the deck editor.
7. **Appending broke offset monotonicity for exactly the 3 edited cards.** Every
   stock `card_indx` offset is strictly increasing; after appending, indices
   254 / 2569 / 3926 have negative deltas to the next entry —
   Lightpulsar (254): name **-78,268**, desc **-779,884**.

### Ruled out by this state

- Heap smash from growing the name blob (5, 6).
- A fixed-size buffer sized to the stock blob (6 — the block is 84,696 B).

### MECHANISM — PROVEN, and it was neither V1-in-the-abstract nor V2

8. **Lightpulsar's 359 B description WAS read correctly** — it is in RAM at
   0x02122118. The read is not the problem; its **length** is.
9. **The read ran 38,844 bytes past the end of `card_desc_e.bin`.** RAM from
   0x02122118 matches the raw bin2.pac from 0x1D7F94 for **39,647 bytes** —
   straight through the end of the desc blob and on into `card_kana1_r.bin`,
   `card_pack.bin`, … (bin2.pac is one NDS file, so a seek+read past an inner
   file's end just keeps going).
10. **That is why `card_pack.bin` looked "resident but short".** It was never
    loaded: `card_pack` sits at pac 0x1DA600, which is 0x266C past the read
    start 0x1D7F94 — and the bytes appear in RAM at 0x02124784, exactly 0x266C
    past 0x02122118. Same delta. It is spill from the runaway read.
11. **The runaway read destroyed an OSThread control block.** The "nodes" at
    0x0213D6A8 / 0x0213AE10 begin with 0x8000009F — a saved CPSR — so this is
    the NitroSDK thread queue, and 0x02051124 walks it. A third thread's block
    lived at **0x02128E58**, inside the 0x02122118–0x0212BC17 spill, and was
    overwritten with `card_pack` bytes. Its `+0x68` then read 0x28 → abort.
12. **Read length comes from the index gap.** A normal card's read is exactly
    its own string (entry 1416: gap 132, 81 B present); a 0x200-aligned bulk
    slice reads 512 B. Lightpulsar's gap was **-779,884** → runaway.

**Names behave differently from descriptions, and that is the key asymmetry:**
`card_name_<L>.bin` is loaded **whole** into a `DU` heap block and read by
offset + NUL scan, so a bad gap is harmless. `card_desc_<L>.bin` is **never
resident** and is read per-card with a **gap-derived length**, so a bad gap is
fatal.

### ⚠️ `rom_all_patches.nds` ALREADY carries this defect

Stock `rom.nds` has **zero** non-ascending entries in any language. The shipped
chain ROM has, in `card_indx`:

| lang | name non-ascending | desc non-ascending |
|---|---:|---:|
| e | 0 | 0 |
| f | 1 (254) | 0 |
| g | 2 (254, 292) | 0 |
| i | 1 (254) | 0 |
| s | 0 | 0 |
| j | 3 (254, 292, 841) | 0 |
| **k** | 5 (254, 292, 841, 1286, 4282) | **4** |
| r | 0 | 0 |

Index **254 is Sword Arm of Dragon — Lightpulsar's own donor**: a shipped patch
already appends the name where the donor slot is too short. Those are harmless
(names are NUL-scanned) — **but Korean has 4 non-ascending DESC entries, which
is the fatal shape.** It has never been hit because the user plays English.
19–42 entries per language also have gap > padded length (a shorter name written
in place); harmless, and the rebuild reclaims that slack.

## IN-GAME TEST 2 — built 2026-09-08, AWAITING IN-GAME TEST

Same three cards, same text. `_build_text_growth_test.py` now **re-emits each
blob in index order** (`_rebuild`) instead of appending, so every entry's gap
equals its own 4-aligned length — exactly the stock invariant. On a stock blob
the rebuild is the byte-for-byte identity.

`rom_textgrow.nds` = 129,596,552 B, cap byte 0x0A, used 129,596,416 of
134,217,728. bin2.pac 10,974,932 → 10,977,792 (+2,860). Verified: 99 inner files
0x200-aligned; **all 4307 index entries ascend with gap == padded length in all
8 languages**; 3 cards × 8 languages read back; all 4303 other cards' strings
unchanged.

Side effect: this build also **repairs** the pre-existing disorder above,
including Korean's 4 bad desc entries.

## Open Questions

1. Is 4-byte offset alignment actually required, or just the packer's
   convention? Both NDS and 3DS builds are 100% 4-aligned. Unproven either way;
   costs ~6 KB per blob to assume it is required. Moot if the blob just grows.
2. Does the deck editor / card-list path load more than one string at a time?
   Only duel savestates were available. Would need a savestate taken in the
   deck editor.

## Next Experiment

One duel / one menu visit:

The size-preserving repack is now the *fallback*, not the plan — growing is
proven safe at the archive and ROM level and there is ~4.4 MB of room.

1. Build a test ROM that grows `card_desc_e.bin` (and `card_name_e.bin` if
   names need it), appends the full printed text for a handful of
   already-shipped cards, and repoints their `desc_off`/`name_off` in
   `card_indx_e.bin`. Keep each string ≤ ~1196 B / ≤ ~110 B.
2. In-game, check **both** paths, because only the duel path is measured:
   the in-duel card-info window **and** the deck editor / card list (that is
   where Boggart's freeze appeared).
3. If it renders in both, the donor `DESC_SLOT_MIN` / name-floor asserts in
   `patch_maiden_eyes_of_blue`, `patch_azure_eyes`, `patch_accel_synchron` etc.
   can be retired and those cards can ship their real printed text.

KB follow-up (not yet written): `donor.name_slot_floor`'s "the engine copies the
blob into a fixed-size buffer" justification is disproven and needs correcting,
keeping the old claim as UNVERIFIED with `corrected_by:` per the KB rules. The
*rule* it states (in-place writes are capped by the donor's own slot across all
eight languages) stays true for in-place writes.

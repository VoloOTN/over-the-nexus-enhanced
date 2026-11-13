# Kuribandit — findings

Printed text (scratch/ygoprodeck_cache.json, id 16404809; Lv3 DARK Fiend 1000/700):
> "During the End Phase, if this card was Normal Summoned this turn: You can Tribute this card; excavate the top 5 cards of your Deck, you can add 1 excavated Spell/Trap to your hand, also send the remaining cards to the GY."

- C1 End Phase + Normal Summoned this turn, optional — IN SCOPE
- C2 cost: Tribute this card — IN SCOPE
- C3 excavate 5 → may add 1 excavated Spell/Trap → rest to GY — IN SCOPE
(user chose "whole effect" in one session, 2026-09-14)

User decisions 2026-09-14: donor **Torike 0x0FD5**; optional add = Yes/No dialog before the picker;
Deck < 5 = cannot activate. Single-card ROM only (not in the chain).

Status: **ALL CLAUSES IN-GAME CONFIRMED BY USER 2026-09-14** on Build 2 (`rom_kuribandit.nds` sha256 `84724d8018139e1216e7aa65806913d364fc7a7ed59ce0cb5a3e89239e12c865`).
User, verbatim: *"Works perfectly, Ship it!"* — shipping approved 2026-09-14.

## Build 1 (2026-09-14)
- `python -m otn_enhanced.cards.kuribandit --text` → `data/over_the_nexus/working/rom_kuribandit.nds`
  sha256 `3ec241b1d4997c7676f1a0eb5491ce41097bb3e2a5d96c02a614a3ae5c0e3af4`
- `--verify` 12/12 PASS. card_prop read back: Effect Monster / DARK / Fiend / Lv3 / 1000 / 700.
- Edits: cls1 phantom 0x1441 @166 dropped, `{0x0FD5, 0x0239EFC1, 0, 0x0239EF71, 0x021E50DD, 0x021E50CD}` @58;
  criteria phantom 0x0E34 @23 dropped, `{0x0FD5, 0xFFFF, 0x02242F09, 0x0000000C}` @69; registry row 188 @0x0228E7C0 cid 0x1A1F → 0x0FD5.
- Slots: `CAVE_KURIBANDIT_COND` 0x0239EF70 (0x50, 68 B), `CAVE_KURIBANDIT_RES` 0x0239EFC0 (0xE0, 212 B), CAVE_FREE → 0x0239F0A0.
  Claims: donor_cid 0x0FD5, cls1_table 0x1441, populate_table 0x0E34, registry_row 0x1A1F. `check_allocations`: OK.
- Both stubs disassembled after build: BLs 0x0222FD90 / 0x02243FE0 / 0x0219A6F4 / 0x0219A798 / 0x0219A818 / 0x0219C430 / 0x021D2148;
  pools 0x0229AAFC, 0xB3C, 0x0229AC94, 0x107, 0x0229DD94 (cond: 0xB3C, 0x0229ACA4, 0x0229ACD8). No POP-into-LR, no BLX.
- NOT in the chain, NOT in SHIPPED. `card_text.CARD_TEXT[0x0FD5]` added (shared data — the fast build's `--compare`
  vs rom_baseline will differ until a deliberate re-baseline, same as Cardcar D's pre-ship state).

### Known compromises to raise with the user (not accepted deviations — bugs until they say otherwise)
- The "add a card?" dialog reuses prompt 0x107 (the generic "activate <card>?" text), so it will read like a second activation prompt.
- PoD's `0x021D2D40 == 0x12DA` side-flip branch is not replicated in the build phase (undecoded).

## Confirmed (2026-09-14, disassembly of rom.nds this session)
- Kuribandit absent from NDS (`scratch/cid_to_name.json`) AND 3DS (`threeds_lookup "Kuribandit"` → no match).
  No card in either build does "excavate the top N … rest to GY" (ygoprodeck regex sweep: Altergeist Pixiel,
  Chaos Ruler, World Legacy Survivor only; none present).
- **End-Phase timing is an effect-registry row.** Genex Neutron 0x1E9F ("during the End Phase, if this card was
  Normal Summoned this turn: You can …") owns registry row 72 @0x0228E420 = `{0x02253F89, 0x1E9F}`. Same poster on
  Worm Linx 0x1F1E (73), Brain Crusher 0x1726 (75), Jurrac Dino 0x2173 (91), Simorgh 0x1A40 (96), Jenis 0x1E2B (97).
  Neutron's ONLY other ov3 references are its criteria row [762] and cls1[893] (u16 scan of ov3).
- Neutron cls1[893] @0x0228B48C = `{+04 0x02207EF5, +08 0, +0C 0x021FEDDD, +10 0x021E50DD, +14 0}`.
- Neutron cond 0x021FEDDC: zone word `0x0229ACD8 + (side&1)*0xB3C + slot*0x14` bit 16 → else 0; then `bl 0x021F0820`.
- **0x021F0820 is a CANDIDATE-COUNT gate**: `0x021BAD70(side^desc6)` → min k = 1 (3 for 0x1FC9/0x2410, 2 for 0x2049) →
  `0x02243FE0(side, cid, 0x02234E78(desc)) >= k`. So Neutron's cond cannot be reused: it would gate on hidden Deck contents.
- Timing classifier 0x0224AF7C tag chain (ov3 literals): class 2 0x021E51E5; class 1 0x021E50DD, 0x021E5201,
  0x021E780D, 0x021E88F5, 0x021E91DD, 0x021E9A21, 0x021E986D, 0x021EAD71, 0x021E7969, 0x021E9215, 0x021E9589,
  0x021E88A9 (+desc[0x20]). None of these tag bodies calls the tribute primitive 0x021CF658.
- Tribute slot 0x021E50CC = `0x021CF658(desc[2], desc[3]); return 1` — NOT a classifier tag.
- Tag body 0x021E50DC: sub-step 0 runs slot3 (0x0224AD94), sets prompt 0x107 (0x0219A6F4), names card (0x0219A798),
  opens dialog 0x0219A818(side,1); sub-step 1 reads the answer `[0x0229DD94+0x34]` (0 → 0x021D3828 cancel, else 0x021CF834, return 1).
- **Trigger/chain activation machine runs slot4 then slot5**: slot4 invoker call @0x021D4582 (gated desc[+7]),
  `str r1,[r5,#0x7c]` sub-step reset @0x021D45B6, slot5 getter @0x021D4626 / invoker @0x021D466E (gated desc[+8]).
- **Pot of Duality 0x2321** cls0[1208] @0x0228578C `{0x0222FD91, 0, 0x02203259, 0x021E8E75, 0}`; criteria [1228]
  `{0x2321, 0xFFFF, 0x02242F09, 0x0000000E}`. Resolver jump table (`add pc` base 0x0222FDCE, halfwords @0x0222FDCC):
  0x7C→0x0222FEFE (0x0219C510 pick → 0x021C72D8(side, ref, 1) add → 0x64), 0x7D→0x0222FEEE (0x0219C430(side, 6, cid, desc[+0x12]) → 0x7C),
  0x7E→0x0222FE5E (per-card excavate/reveal loop), 0x7F→0x0222FE34 (queue 0x58 show), 0x80→0x0222FDD6 (copy top 3 Deck refs
  from player+0x304 into desc[+0x14..], count desc[+0x12], bound player+0x10, `cmp r4,#3` @0x0222FE26). 0x64→0x0222FF10 shuffle 0x021D269C.
- PoD criteria handler 0x02242F08 = `0x0223BC3C(side, cid, 0, 0, [sp]=word, [sp+4]= 2 | param<<25)`; 0x0223BC3C is the Deck enumerator (KB).
- Picker 0x0219C430(side, code, cid, param) enumerates via 0x02243FA8(side, cid, param) (the cid's criteria row).
- **0x021D2148(desc, side, N) = send top N of Deck to GY**: 27 ov3 callers incl. Needlebug Nest, Solar Recharge,
  Warm Worm (r2=3), Painful Choice (r2=4), Lightsworns (r2=2/4), Tuning (r2=1), Magical Merchant (r2=1).
- Magical Merchant 0x161F cls1[296] resolver 0x0221821D (top-card loop; 0x02029E60(cid) != 0 → mill 1 & loop; else add).
- Donors: `donor_scan --free --level 3` CLEAN list; Torike 0x0FD5 has no hits in finished_patches / check_allocations / allocations.yaml / notes.
- Phantom candidates (no card_prop row, rom_baseline): End-Phase registry rows already on 0x02253F89: 154 `0x19C0`
  (also in criteria [406] — avoid), 188 `0x1A1F`, 198 `0x1337`. cls1 single-row phantoms incl. `0x1441`. Criteria phantoms incl. `0x0E34`.

- **PROVEN: `param<<25` = top-N limit.** Deck enumerator 0x0223BC3C: `r4 = [sp+0x6C]` flags; @0x0223BCA6
  `movs r0,#0xFE ; lsls r0,#0x18 ; ands r0,r4 ; beq ; lsrs r1,r0,#0x19 ; ldr r0,[sp,#0x14] (deck count
  [0x0229ACA4+side*0xB3C]) ; cmp r0,r1 ; blo ; str r1,[sp,#0x14]` → count = min(deck, N); loop @0x0223BD00 walks
  `[0x0229AC94 + side*0xB3C + 0x304 + i*4]` for i < count — the exact array/indices PoD's 0x80 builder copies.
  So criteria row on handler 0x02242F09 with param 5 = "cards among the top 5".

## Ruled Out
- Reusing Neutron's cond 0x021FEDDD verbatim: its 0x021F0820 tail needs >=1 criteria candidate (hidden info).
- Tribute in +10: 0x021E50CD is not a classifier tag → trigger silently dropped (KB timing.class_is_the_slot4_literal).
- A native excavate-5 / rest-to-GY card to transplant: none in NDS or 3DS.

## In-game test of Build 1 (user, 2026-09-14)
User report, verbatim: *"1. Confirmed / 2. Not quite, I get a "Kuribandit misses the timing", so no yes/no prompt.
But I have to add a spell/trap to my hand. / 3. Could not verify, as I couldnt say "No" to the missing the timing
prompt / 5. All confirmed"* — user then confirmed: the notice came after the 5 were revealed and before the picker,
the other 4 went to the GY, and "5" meant step 4 (negative controls).
- Step 1 (End-Phase prompt, Tribute, 5 revealed): **confirmed by user 2026-09-14**.
- Step 2: picker S/T-only + pick to hand + other 4 to GY **confirmed by user 2026-09-14**; the optional "add?" prompt is **BUG**.
- Step 3 (No / no-S/T case): not testable on Build 1.
- Step 4 negative controls (decline first prompt, Set/flip/SS copy, Deck of 4, next turn): **confirmed by user 2026-09-14**.
- ⇒ also in-game-confirmed: End-Phase registry row + cls1 +10 tag / +14 Tribute ordering (trigger machine slot4→slot5).

### Root cause (savestate rom_kuribandit.ml3, 2026-09-14)
- Both ov5 stubs resident byte-exact. Resolver phase `[0x0229AAFC+0x70]` = **0x7B** (only my 0x7D "ask" branch returns it).
- Prompt list `[0x0229DDD0]` = `0x10000107, 0x50000FD5` → prompt **0x107 = "<card> misses the timing"**.
- I copied the tag body's MISSED-TIMING branch (0x021E5108..28: 0x021EE0E0 nonzero → 0x107 + name + 0x0219A818(side,1)
  = OK-only notice, then abort). The real Yes/No is its other branch 0x021E512C..88: `0x0219AAAC(desc, 0xFA, desc[+0xC])`
  (0x149 if desc[+3]==0xE, 0x148 if ==0xB); answer `[0x0229DD94+0x34]`, 0 = No (→ 0x021D3828).
- Fix (user approved generic "activate?" wording 0xFA): phase 0x7D calls 0x0219AAAC(desc, 0xFA, desc[+0xC]).

## Build 2 (2026-09-14) — second prompt fixed
- Phase 0x7D now `ldrh r2,[r4,#0xC] ; adds r0,r4 ; movs r1,#0xFA ; bl 0x0219AAAC` (was 0x107 + name + 0x0219A818).
  0x0219AAAC = `movs r3,#1 ; bl 0x0219AA68`; Tuning's resolver uses its sibling 0x0219AAB8(desc, 0x35, desc[+0xC]) the
  same way and reads [0x0229DD94+0x34] next phase.
- `rom_kuribandit.nds` sha256 `84724d8018139e1216e7aa65806913d364fc7a7ed59ce0cb5a3e89239e12c865`; resolver 196 B;
  `--verify` 12/12 PASS; check_allocations OK. Every other byte of the patch unchanged from Build 1.
- **In-game confirmed by user 2026-09-14** ("Works perfectly, Ship it!") — steps 2 and 3 on this build.

## SHIPPED (2026-09-14)
- User: *"Works perfectly, Ship it!"* on Build 2 (steps 2 + 3 confirmed).
- Wired into `otn_enhanced.steps.STEPS` (step 61, above WiFi timers) and `_verify_all_patches.SHIPPED`.
  NOT `apply_all_patches.PATCHES` (retired per user 2026-09-14).
- EE fast build: **62/62 steps**, `rom_all_patches.nds` 129627272 B, sha256
  `ebad49ce090b50d6a3d009ac023788f6db45de7a853d572c5584f6d607549536` (previous copy kept as
  `rom_all_patches.pre_kuribandit.nds`). Verify sweep: **50 passed, 0 failed**.
- `equiv --all`: `[DIFFERS] patch_bulk_ydcs` (file 61 @+0x180C). bulk_ydcs + its migration were last modified
  2026-09-13 19:33, before this session, and neither references card_text / 0x0FD5; its prefix is earlier than any
  card step — so not caused by Kuribandit, but not investigated (out of scope). ⚠️ `equiv --all` uses
  `all(generator)` and STOPS at the first DIFFERS, so the other 13 migrated modules were run separately:
  12 IDENTICAL; `[DIFFERS] patch_vylon_element` — ov3 RAM 0x0228DCB0 (Vylon's own cls1 record slot)
  `0x0221DA95` (original) vs `0x02206CAD` (migrated). Migrated vylon_element.py last edited 2026-09-13 17:06, after
  the original (09-11), and its docstring records a user-approved 2026-09-13 rework. Prefix is far earlier than
  step 61 and neither module reads any constant Kuribandit changed → pre-existing, not investigated.

## Open Questions
- (answered above) `2 | param<<25` = top-N cap — PROVEN.
- Structural only, not measured: that End-Phase registry triggers actually run through the slot4→slot5 machine @0x021D45xx.
- Prompt 0x107 text for the second ("add a card?") dialog.

KB (2026-09-14): added timing.endphase_registry_poster_0x02253F89, dispatch.generic_gate_0x021F0820_counts_candidates,
resolver.mill_top_n_0x021D2148, dispatch.pot_of_duality_excavate_machine, dispatch.trigger_machine_runs_slot4_then_slot5
→ `author_facts --check`: 435 PASS / 0 FAIL / 38 UNVERIFIED.

## Next Experiment
In-game test of `rom_kuribandit.nds` (sha256 3ec241b1…3af4), normal duel (NOT a puzzle — ov5 is evicted there):
1. Normal Summon Kuribandit (Deck ≥ 5) → at the End Phase, expect prompt → Yes → Kuribandit to GY, 5 cards revealed.
2. With ≥1 Spell/Trap among them → "add?" prompt → Yes → picker lists ONLY Spells/Traps → pick to hand, the other 4 to GY.
3. Answer No at the second prompt → all 5 to GY. With no Spell/Trap excavated → no second prompt, all 5 to GY.
4. Negative controls: decline the first prompt (card stays); Set / flip-summoned / Special Summoned copy (no prompt);
   Deck of 4 (no prompt); next turn (no prompt).
If it fails, ask for a savestate at the failing step; likely suspects in order: slot5 Tribute on this machine,
the 0x7B phase round-trip after the dialog, the mill count after the add.

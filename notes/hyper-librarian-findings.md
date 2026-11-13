# T.G. Hyper Librarian (0x1225) -- DSL conversion findings

Byte-identity to the shipped build is the only claim here. Nothing run in-game this session.
NOTE: this file already existed (untracked) and was overwritten at the start of the DSL session; its earlier
contents are lost. Everything under "Inherited" below comes from the old module's docstring/comments (still in
git history), not from the lost file.

## Confirmed (this session)
- Reference ROM from the ORIGINAL module (`main(write_text=True, out=...)`, base `rom_ov3_compact.nds`,
  ov3=True, chain=True): `verify()` True. SHA-256 `0ddaaad3c88856bb74ddeac7859a141f7bbd3a46e8587f2a4215366b32d92a66`.
- DSL rebuild (`card(fusion_to_synchro_effect, synchro_summoned_draw, archetype_member(TG_TABLE))`): same
  SHA-256, full byte compare IDENTICAL, DSL `verify()` 15/15.
- Wiring the reference makes vs base (diff of ov3 / ARM9 / bin2): ov3 stubs (hook 0x021F1BFC, draw resolver
  0x021F2718), zero RAM words (latch 0x021DD854, scratch 0x021F95E0 x0x20), BL over 0x02265D00, cls2 insert
  (drops phantom 0x0E66; shifts the table tail), fusion row A[50] materials -> 0x3FFF/0x3FFF, ARM9 T.G. table
  (0x2552 -> 0x1225), bin2.pac card_prop + card_genre + text.
- 0x02265D00 is named in no other card module (grep: hyper_librarian, cave3, author_facts only).

## Inherited from the old module (UNVERIFIED, not re-proven this session)
- Trigger mechanism: cls1 is never polled for a bystander on a summon event; cls0 unreachable (zone gate byte
  is always nonzero -> class-3 path); cls2 needs runtime registration; cls3 tag 0x021E51E5 queues an OPTIONAL
  link; cls3 tag 0 does not auto-fire. Hence a code hook + register-prim 0x021D3168 -> chain link.
- Hook site: the SS-commit routines A/C (0x0226925C / 0x02269320) fire BEFORE the summoned card is in a zone
  (GDB check_placement_timing); the enumeration master 0x02265CF8 runs post-placement, so the hook is the BL at
  0x02265D00 (0x02266394 also works but is T.G. Warwolf's site).
- 0x021A25A0 searches the player+0x124 list, which does not receive fresh summons (-1); 0x021A2510 searches a
  sent-to-GY list at +0x55C. Neither may gate the hook.
- Zone word: low14 cid, bit14 side, bit15 properly-Extra-Deck-summoned, bit22 face-down/negated, bits23-30
  instance index; packed ref = (bits23-30)<<1 | bit14. Summon descriptor 0x02298A28: +0xC packed ref, +0xE cid,
  +0x10 bit0 proper summon.
- 0x020232AC ("IS_SYNCHRO") is really an is-Extra-Deck predicate (drew on Fusion Summons, cid 0x104E);
  0x0202ABF8 card-type code in {17,18,19} is the Synchro-only test.
- Face-up-at-resolve: entry+0 keeps the cid even face-down; the face-up marker is entry+8 (0x0229ACD0).
- Resolver phase protocol cloned from HANDSS_RES 0x02206ABD: act at phase 0x80, return 0x7F; both GDB-tunable
  assumptions. cls2 tag 0 = mandatory (Formula Synchron's wiring); +0C 0x0224A115 = always eligible.
- register-prim packed ref needs side<<31 (side<<14 left ctx+2 = 0, so side-1 copies fizzled).
- 3DS reference: registry row 0x6C443C {id 0x2552, router 0x442C2C, glue 0x49BFF8}; predicate 0x47FB40,
  gate 0x46DA9C, draw 0x459688 -> 0x387B74 (see CARDS_ZEXAL_3DS_ASM.md paragraph 5).
- Donor history: Gishilnodon 0x2004 -> Scarred Warrior 0x2338 -> (user-approved) Amphibious Bugroth 0x1225, an
  effectless Fusion (donor_scan: one binding, its own recipe A[50], materials 0x10B9 + 0x1163 with no card_prop;
  0 CPU decks); Synchro conversion recipe from orient_dragon (card_prop template 0x23FE + genre + recipe kill).
- The name is stored "T.G. Hyper Librarian" via CARD_TEXT (index-order re-emit); the old module's 15 B in-place
  name and `skip_name_if_too_long` were dead for this cid.

## Dropped in the conversion (still in git history)
- The non-chain variant (direct DRAW_PRIM per copy, `--no-chain`), the ov5 (`ov3=False`) variant and its
  `CAVE_LIB_*` slots, `OUT_CHAIN`, the TG_* constants.
- Old `verify()` checked card_prop fields (DARK/Spellcaster/5/2400/1800), card_genre and the recipe row directly;
  the DSL `verify()` checks the recipe row, T.G. table, cls2 row, stubs and text. Stats/genre are covered by
  byte-identity only.
- `dsl.fusion_to_synchro_effect` still calls `orient_dragon.apply_fusion_recipe_kill` /
  `apply_card_prop_and_genre` (a hand-written module): converting Orient Dragon will need to move them.

## Ruled Out
- (none this session)

## Open Questions
- Does the recorder telemetry at the scratch word still matter? It is emitted into the stub bytes, so it was
  kept for identity.

## Next Experiment
- None required for the conversion. In-game test of the unchanged ROM remains the user's call.

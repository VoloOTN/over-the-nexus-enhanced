# Aratama — findings (started 2026-10-12)

Printed text (scratch/ygoprodeck_cache.json, passcode 16889337, Spirit L4 DARK Fiend 800/1800):
"Cannot be Special Summoned. During the End Phase of the turn this card is Normal Summoned or
flipped face-up: Return it to the hand. When this card is Normal Summoned or flipped face-up:
You can add 1 Spirit monster from your Deck to your hand, except "Aratama"."

C1 cannot be SS / C2 EP return / C3 NS-or-flip Deck search (Spirit, except self).
Scope: whole card, C3 focus. Donor: **Souleater 0x13AC** (user pick 2026-10-12).
Status: WHOLE CARD IN-GAME CONFIRMED BY USER 2026-10-12 after build 2 (battle-flip fix, rom_aratama.nds e129165b...):
'Everything is all confirmed'. Full EE build 110/110 sha256 9717287635dda44372844b54edbf6992655b5eb050894607692b532389282b73, sweep 91/0.
Build 1 (7cee7db1...) had C1, C2, NS + Flip-SUMMON search confirmed.
**BUG (user 2026-10-12, later report): "the aratama search effect does not trigger when flipped face - up. The
return to hand effect in end-phase still triggers." -- clarified: "b) Flipped up by an attack. Is the one I observed".**
The earlier item-6 'search appeared' report is superseded by this one.
SHIPPED 2026-10-12 into the VANILLA+ block of steps.STEPS (after the Seal) + _verify_all_patches.SHIPPED;
card_genre row 0x1400020 (3DS); bulk_card_pack row renamed Souleater -> Aratama.

## Confirmed (this session, disassembly of stock data/over_the_nexus/working/rom.nds)
- Aratama absent from NDS; 3DS cid 0x2A0E, criteria row `{0x2A0E, aux 7, 0x004AD694, 0x22}` @0x68CCB0.
- C1 is native for card_type>>1 == 7 (Spirit, card_type 14/15): 0x02023398 =
  `bl 0x0202ABF8 ; cmp r0,#7 ; bne ; movs r0,#1 ; ... cmp r0,#0 ; beq ; movs r0,#0 ; pop` -> 0 = reject;
  SS gate 0x021BA6D0 calls it (KB summon.cannot_be_special_summoned_list).
- 0x02241EA4: `movs r0,#2 ; ... str r0,[sp,#4] ; ldr r2,=0x0223C7E5 ; bl 0x0223BC3C` = Deck enumerator,
  pick type 2 (add to hand), predicate 0x0223C7E5 (card_type>>1 == aux). Native user Woodland Archer
  crit[1013] {0x2112, 9, 0x02241EA5, 0x2}; 3DS handler 0x004AD694 is shared with Woodland Archer -> equivalence.
- 0x02241E58 is the SAME predicate but [sp+4]=0xA (Gemini Soldier crit[1001], SS from Deck) -> NOT for C3.

- C3 template = Senju of the Thousand Hands 0x1334 (native "Normal or Flip Summoned: you can add a
  Ritual monster from Deck"): cls1 {0x02207EF5, 0, 0x021F0821, 0x021E50DD, 0}, member of code-7-OR-8
  list 0x0228F598 (consumer 0x02265C1C `subs r0,r6,#7 ; cmp r0,#1 ; bhi` -> list literal @0x02265CE8,
  movs r2,#0x10). Siblings Berfomet/Sonic Bird/Manju use the same list + record shape.
- Native Spirit cls1 = [return {0x0220A901,0,0,0x021E88A9,0}, effect] (Maharaghi 0x14FD, Yata, Otohime).
- Phantoms (no card_prop, unclaimed, present stock + chained): c78 0x12B4, cls1 0x1506 (2 rows),
  criteria 0x0E9D (row 55; shift window below Dragon Shrine's anchored 0x14C1 row; not in lists A/B).
- BUILT 2026-10-12: rom_aratama.nds sha256 7cee7db1b29fab6a76685168680a91bbdd03f026890690dfd491b7b23b06905b,
  verify 5/5 PASS. Built card_prop 0x0006108F5A1413AC == 3DS Aratama prop 0x0006108F5A142A0E bar the cid.
- KB: summon.spirit_type_is_native_cannot_ss + dispatch.card_type_deck_search_handler (VERIFIED),
  card.aratama (UNVERIFIED, awaiting test). author_facts --check: 618 PASS / 0 FAIL.

- **"When this card is flipped face-up" (ANY flip) = ARM9 list 0x0209BB5C, 19 x u16** (literal 0x020231C4,
  `movs r2,#0x13` @0x020231AC), read by 0x02023188(cid): returns 0 if card_type>>1 in {0xD,0xE} or genre bit 22
  clear (0x0202A158(cid,0x16)); else 2 if in the list, 1 otherwise. Members: every NS-or-flipped Spirit (Maharaghi,
  Otohime, Dark Dust Spirit, Tsukuyomi, Izanami, Kinka-byo, Yaksha) + flipped-face-up non-Spirits (Nightmare Penguin,
  Batteryman AAA, Peggulsus...) + phantoms 0x1527 / 0x1534 / 0x1535. All members carry genre bit 22 ('(Flip)').
  Senju (Flip SUMMON only) is NOT a member; nor is Aratama -> the cause.
- Threshold tests `bl 0x02023188 ; cmp r7,r0 ; bgt` inside the face-up flip 0x021C4F44 (@0x021C5068) and the
  position primitive 0x021C5358 (@0x021C545C). 0x021C4F44 callers include Damage-Step region 0x0224F878/9CE/FB94.
- Summon evaluator 0x02265768: code 8 (Flip Summon) + 0x02023188 != 0 -> r5 = 2 @0x022658AA, but the later c78
  membership (0x02265C1C) resets r5 = 1, so Aratama's working Flip-Summon path is unchanged by adding bit 22.
- Native flipped-face-up "you can" records all use +10 0x021E51E5 (Batteryman AAA, Kinka-byo, Yaksha, Flip Flop
  Frog); Aratama has Senju's 0x021E50DD. 0x021E51E5 is the Gearframe/Hanzo record (Hanzo: NS + Flip Summon in-game
  confirmed).
- Single-card rom_aratama genre = Souleater's 0 (bit 22 clear). Chain build card_genre row 0x1400020 sets bit 22.

## Ruled Out
- Code-7-or-8 list alone covering a battle flip: falsified in-game (user 2026-10-12).
- Class-list / 0x0209BD6C insert for C1: unnecessary, Spirit type already rejects (above).
- Handler 0x02241E59 for C3 (pick type 0xA = Special Summon).

## Open Questions
- SUPERSEDED: battle flip does NOT trigger the search (user, later 2026-10-12). Return still happens. Native Spirits
  (Maharaghi/Otohime/Tsukuyomi) are only in code-7 list 0x0228F7AC; Aratama uses Senju's code-7-or-8
  list 0x0228F598 instead (covers Flip Summon; a battle flip is still unknown).
- End-Phase poster 0x02254B64 reading (zone bits 16/17/19) is agent disassembly, UNVERIFIED.

## Next Experiment
- BUILD 2 (battle-flip fix, user-approved 2026-10-12): genre 0x1400020 (bit 22) on 0x13AC + 0x13AC in
  0x0209BB5C over phantom 0x1527 (claimed flipped_faceup_list) + cls1 #1 tag 0x021E51E5. rom_aratama.nds sha256
  e129165b5b290cfd410458491e8fe80ccaca4cc3e1724a2da255775275de4809, verify 7/7 PASS. IN-GAME CONFIRMED BY USER 2026-10-12
  (item 6 + regressions 2, 3, 5). In the full EE build 97172876...
- Earlier: Full EE build blocked 2026-10-12 at step 107 patch_bulk_ydcs ('One For One' does not
  resolve to a konami ID) -- an UNRELATED in-progress edit to that file, not touched here. Vanilla+ build
  41/110 sha 4aa2e2a1...894a66 OK; patch_aratama + patch_card_genre verify PASS on it.

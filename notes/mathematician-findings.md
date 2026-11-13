# Mathematician — findings (donor Boneheimer 0x13B6)

STATUS: in-game confirmed by user 2026-09-14 -- all six oracle items, first test, on
rom_mathematician.nds sha256 02aa369c7f3233211f9a3e6fcf57182bf675e68ff77b5b902d8077d39684d21d.
SHIPPED 2026-09-14 into steps.STEPS only (step 60/61, before WiFi timers); EE build 61/61
sha256 fe5b8922dc72d9b5a96e56744091929f002042cf88be17fa425baf460efca588; sweep 48 passed / 0 failed.
Pre-ship chained ROM kept at rom_all_patches_pre_mathematician.nds.

Printed text (scratch/ygoprodeck_cache.json, id 41386308, EARTH / Spellcaster / Lv3 / 1500 / 500):
"When this card is Normal Summoned: You can send 1 Level 4 or lower monster from your Deck to the GY.
When this card is destroyed by battle and sent to the GY: You can draw 1 card."

Scope: BOTH clauses (user override of one-clause-per-session, 2026-09-14). Donor user-chosen.

## Confirmed (this session, 2026-09-14, static)
- Mathematician is absent from the NDS ROM (English name scan of card_prop/indx) and from the 3DS
  (`threeds_lookup "Mathematician"` -> no match). No Konami reference implementation.
- Boneheimer = cid 0x13B6, prop index 825, Normal / WATER / Aqua / Lv3 / 850/400.
  `donor_scan 0x13B6` -> CLEAN. Its 7 u16 hits (ov3 0x02148424/43C/440/46C, 0x02165E04/E20,
  0x021733FC) all disassemble as `asrs r6,r6,#0xe` followed by `b ...` = halfword noise.
- Donor English blobs: name 10 B, desc 74 B -> too short; text must go via card_text.CARD_TEXT.
- Armageddon Knight 0x1CFF: cls1[745] = {0x02208DD5, 0, 0x021F0B19, 0x021E51E5, 0};
  crit[632] = {aux 0xFFFF, 0x0223CAD9, 0x02000002}.
- Reinforcement of the Army 0x14D0 crit[161] = {0xFFFF, 0x0223CAD9, 0x78900002} -> level bits 0x0090
  (Lv<=4) are honoured on the DECK handler. Scarr 0x196A row carries word 0x00900002 exactly.
- Cyber Phoenix 0x1A07 cls2[205] = {0x022065B9 draw, 0, 0x021F069D, 0x021E51E5, 0}; draw count 1.
- Birdface 0x139D / Gokipon 0x19C5 are list106 members (battle && destroyed && to-GY, 0x021C80BC).
- Draw-count provider 0x02206304: table 0x022704A4 (189 x {u16 cid, s16 n}, sorted). Absent cid ->
  per-cid tree -> default 0x02206570 `adds r0,r5,#0 ; pop` with r5 = 0 => count 0 => no draw.
- 0x021F069C: `bl 0x02206304 ; beq ret0 ; side = desc[2]^desc[6] ; bl 0x021BAE30 ; pop`
  => offered only if the cid has a nonzero draw-count row AND 0x021BAE30(side).
- Stock phantoms: c7 list 0x0228F7AC {0xE74 0xE7E 0xE7F 0x14CC 0x15D0 0x19C0 0x19D3 0x1B1A 0x2346};
  list106 {0xE10 0xE3A 0xEB9 0x14DD 0x14E7 0x1B18 0x1B19 0x1B45..0x1B4A 0x1BBE 0x234E};
  draw table {0xE19 0xE7F 0xE86 0xE88 0xEAE 0xECE 0x1175 0x16C1 0x1748 0x1774 0x1790 0x1A1F 0x1AE9 0x1B1A}.

- Phantom picks (scratchpad probe_phantoms.py: stock phantom, no card_prop, absent from every
  PHANTOM_CLAIMS pool, still present in rom_all_patches.nds of 2026-09-14 07:53):
  summon_list_c7 0x15D0, cls1_table 0x0E1F, cls2_table 0x0E1C, populate_table 0x0E3C,
  list106 0x1B46, draw_count_table 0x16C1.
- list106 base 0x0226E990 has exactly ONE aligned u32 literal in stock ov3 (@0x021C831C), i.e. one
  consumer (the leave dispatcher) -- a count-neutral phantom swap cannot break another reader.
- 90 native cids own both a cls1 and a cls2 record (e.g. Slate Warrior 0x13AD), so cls1+cls2 on one
  cid is an ordinary shape, not a shadow risk.

- BUILT 2026-09-14: `_build_mathematician.py` -> BUILD_EXIT 0, allocation guard clean, verify 7/7 PASS,
  data/over_the_nexus/working/rom_mathematician.nds sha256
  02aa369c7f3233211f9a3e6fcf57182bf675e68ff77b5b902d8077d39684d21d.
  Negative control: verify() on the clean rom.nds -> 7/7 FAIL (checks are not vacuous).
  Insert positions: c7 @5, cls1 @151, crit @122, list106 @14, cls2 @78, draw @31; all counts unchanged.
- KB: dispatch.draw_condition_needs_the_count_row (VERIFIED); author_facts --check 429 PASS / 0 FAIL.
- card_text.CARD_TEXT[0x13B6] added. The chain's only CARD_TEXT loops (apply_all_patches ~L2229,
  otn_enhanced/text_guard.py) are read-only clobber guards, so the combined ROM is
  unaffected. The chain was deliberately NOT rebuilt (card still under test).

## Ruled Out
- A donor without a draw-count row: 0x021F069D returns 0 -> never offered (see above).
- list30 / mask table for clause 2: list30 = any field->GY (wrong timing, and full); list106 matches.

## In-game result (user, 2026-09-14): "1. Confirmed ... 6. Confirmed" -- all six items
- ANSWERED: list106 membership alone gates on battle (item 6: no prompt on Dark Hole / Tribute).
- ANSWERED: the code-7 list alone keeps clause 1 off Special and Flip Summons (item 4).
- KB: card.mathematician (VERIFIED recipe inputs, in-game confirmed by user 2026-09-14).

## Open Questions
- none for the card itself.

## Next Experiment
- none; done.

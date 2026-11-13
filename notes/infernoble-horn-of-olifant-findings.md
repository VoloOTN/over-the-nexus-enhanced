# Horn of Olifant — findings

Extra card for the Infernoble family (user 2026-10-22: "Build all the extra cards"). Searched by Angelica C1.
Donor Simultaneous Loss 0x1976 (Normal Trap) confirmed by user 2026-10-22 ("that donor is good").
donor_scan 2026-10-22: only binding ref = its own cls0 record[664]; non-key hits = instruction encodings.

## Printed text (scratch/ygoprodeck_cache.json id 55749927): Normal Trap
Activate 1 of these effects;
- A: Banish 1 Equip Spell you control or in your GY, then you can destroy 1 card on the field.
- B: Destroy 1 "Roland" monster you control, then Special Summon in Defense Position up to 3 FIRE Warrior monsters
  from your Deck, whose total Levels equal 9, but their effects are negated, also, until the end of your next turn
  after this effect resolves, you cannot Special Summon monsters, except Warrior monsters.
You can only activate 1 "Horn of Olifant" per turn.

## User decisions (2026-10-22)
- A: "It can banish monsters" -> a monster equipped as an Equip Spell counts as "1 Equip Spell you control".
- B: 1..3 FIRE Warriors, Levels sum exactly 9, picked one by one; "Mode B should not be available if no possible
  combination of 9 exists".

## Confirmed (2026-10-22, static)
- Modal: native "Activate 1 of these effects" = several same-class records + cost 0x021E6871 ("Use which effect?",
  desc[+0x18]) but ONLY for cids in find_event_handler's lists + 0x021E5794 arm + label rows (KB, see
  patch_uni_zombie). Family precedent instead: ONE record + own prompt 0x0219ABB5(desc, title, l0, l1, [sp] l2,
  [sp+4] l3, [sp+8] mask) -> answer [0x0229DD94+0x34] (Turpin / Oliver / Uni-Zombie). Labels (dlg_text_e): title
  0x103 "Use which effect?", A 0x16D "Remove from play a card from the field?", B 0x1AB "Destroy 1 monster you control."
- Warrior-only SS lock: Ricciardetto's front RC_LOCK @0x021BA368 (turn-log {0xB, key, kind 1} && race != Warrior ->
  deny). "Until the end of your next turn" = countdown nibble (activated on own turn 2, opponent's turn 1).
- Summon commit 0x0226925C(side, &word, r2, r3 = position (1 = face-up DEF per Snoww), [sp] = cid<<16).
- "Effects are negated" = KB summon.negate_is_kind2_node_plus_reader_list: source cid in 0x0228F708 (summon prologue
  posts kind-2 node {source cid}) + key in reader list 0x0226FAB4 (0x021EE402). Rescue Cat 0x1876 = SS 2 from the
  Deck, negated -- multi-SS-from-Deck precedent.
- Level-sum precedents: Variety Comes Out 0x21D1 cls0 {0x0221B4E1, 0x021DBB75, 0x02201B61, 0x021EAF99, 0x02238D61};
  Stardust Shimmer; Puppet Magic of Dark Ruler.
## BUILD 21 (2026-10-22) -- in-game confirmed by user 2026-10-22 ("Horn of Olifant works"; Angelica C1 search not reported)
- rom_infernoble.nds sha256 8a69df9f531245218c46b801a85ad6498a472ba9e6f7be45c1c2be2a40a93671; verify PASS; regression
  FAIL set identical to BUILD 20.
- cls0[664] re-pointed {HO_RES, 0, HO_COND, HO_COST, 0}; criteria row over 0x1748; prechecks (key 0x1976) at
  0x02268090 (-> NEXT's 0x0223F8E4) and 0x021EE418 (-> NEXT's 0x021FBC94); Warrior-lock front at 0x021BA368 ahead
  of Ricciardetto's RC_LOCK; text via card_text.apply_to_rom (0x9D bullet in latin-1 langs, U+25CF in j/k/r);
  Angelica AN_SEARCH = (0x1976,). ov5 CAVE_IK_HO_* 0x023AA510..0x023AAC70.
- EXECUTION-PROVEN: HO_LVCB exact-9 filter = brute-force oracle on 26,919 (deck, rem, k, Level) cases
  (scratch/infernoble/horn_lvcb_check.py), histogram restored every call.
- Verify-only tolerance: patch_dragon_rulers._chain_keys follows prechecks into ov5; chain @0x02268090 reads
  [0x1976, 0x1B22, babies..., 0x17F4, 0x0FE1] -> nothing behind Horn was cut off.
- ASSUMED (not executed): field banish 0x021CF450 on an S/T card; RECORD (0x02243B2D) + GY worker sharing one pick
  list; ldrh pick index; summon commit (side, &word, 1, 1) = face-up DEF from the Deck (NEXT's call from hand/GY).

## Ruled Out
## Next Experiment
- Precedents: modal Normal Traps ("Activate 1 of these effects"), banish an Equip Spell from field/GY, multi-SS
  from Deck with a Level-sum constraint, Warrior-only SS lock (Ricciardetto front @0x021BA368 / Obedience).

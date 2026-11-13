# Infernoble Knight Oliver — findings

Family card 3 (roadmap ~\.claude\plans\add-all-the-infernoble-merry-rainbow.md). Started 2026-10-20 while
the user tests Maugis BUILD 3. Donor Tune Warrior 0x1E04 (Normal Tuner L3 EARTH Warrior 1600/200) — user confirmed
2026-10-20 together with the clause split and "yes build the mixed cost". No ROM code yet.

## Printed text (scratch/ygoprodeck_cache.json): Tuner, Warrior, FIRE, L4, 1000/1500
- C1 While this card is an Equip Card, your opponent cannot target the equipped monster with card effects.
- C2 (OPT) You can send 1 FIRE Warrior monster or 1 Equip Spell from your hand or face-up field to the GY; Special
  Summon this card from your hand as a Level 1 monster.
- C3 (OPT) If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster.

## BUILD 4 (Ogier + Maugis + Oliver, 2026-10-20) — Oliver AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 8c444a873b53c618dda10ca4835155a35e8b84517f1fab94859e7c7fadb05b0c.
- ONE cls2 record over phantom 0x1B4A, slots switched on desc[+3] == 0x0B (hand, C2) vs else (GY, C3):
  +04 hand -> O_C2RES (OPT 0x5E04 check+stamp at 0x80, native hand self-SS 0x02206ABD, then our 0x7E: LOCATE +
  Level SET rider {0x1EC1, 3, 1}); +08 hand -> O_FIELD (0x021D6E40 mask 0x05 + MZ FIRE Warrior / S-T Equip Spell or
  FIRE Warrior); +0C hand -> OPT + free MZ (0x021AD870) + (hand row count || +08 sweep count 0x0224AA94) -> 2;
  +10 hand -> Hands/Field prompt (dlg 0x3A / 0x192 / 0x23C) then the native hand cost 0x021E7245 (criteria row
  {0xFFFF, O_HANDH, word 0} over 0x0ECA; O_HANDH = hand worker 0x0223BFD4 mode 0x11 + O_HANDCB) or field cost
  0x021E712D (+08); C3 -> post OPT 0x1E04; +14 hand -> 1 (no targets) / Vylon slot5.
  C3 = Ogier recipe (igncond over 0x0EA9, gy_vrow row, EQFILT +0x1E04). C1 = PROT arm: Oliver-equipped && targets
  flag && acting controller is the target's opponent. LIST B 0x0209BC8C: phantom 0x1A86 -> 0x1E04.
- EQFILT / PROT moved to bigger slots (0x023A7D60 / 0x023A7DE0); their old homes host O_SLOT5/O_RES/O_FILT/O_HANDH.
- Static: patch_infernoble.verify PASS; chain_walk_diff / miss_diff / gyv_equiv PASS; sweep 84/16, all 16 = the known
  local-arm / unregistered-walk categories (no new failure).
- ASSUMED (in-game will tell): mask bit 2 = face-up in 0x021D6E40; the hand/field cost machines leave desc[+0x18]
  alone; LOCATE(desc[+0xC]) finds the summoned Oliver one phase later (Psi-Reflector precedent); excluding by cid
  means a 2nd Oliver in hand can't be the cost; the free-MZ check ignores "a field cost frees the zone".

## IN-GAME RESULT — in-game confirmed by user 2026-10-20 (BUILD 5, rom_infernoble.nds 1c083248...1a48)
User's words: "Confirmed all of oliver, build Turpin"
- CONFIRMED: whole card -- C1 (opponent cannot target the equipped monster), C2 (hand OR field cost incl. the
  Hands/Field choice, SS from hand as Level 1, once per turn), C3 (GY equip). Rider key 0x1EC1 = SET -> Level 1 now
  in-game proven. NOT shipped (not in steps.STEPS).

## IN-GAME TEST 1 (BUILD 4, 8c444a87...) — user report 2026-10-20, reading confirmed by user ("yes")
User's words: "1. Confirmed / 2. Incorrect it does not let me activate from hand (see .ml2) / 3. Confirmed, it can
use cards on the field. However when summoned it is still level 4 instead of 1. (see .ml4) / 4. Only cards on the field
are offered (see .ml3) / 5-9. Confirmed"
- PASSED (user): O1 card face; O3 field-cost path (field card sent, Oliver Special Summoned); O5 filter; O6 C2 once
  per turn; O7 C3 GY equip; O8 C1 opponent-untargetable; Ogier regression.
- FAILED: O2 only a HAND cost available -> the hand effect is NOT OFFERED at all (savestate .ml2).
          O3 Level stays 4 after the summon (Level-1 rider not applied) (savestate .ml4).
          O4 hand + field both available -> no Hands/Field prompt, field-only picker (savestate .ml3).
- Reading: O2 + O4 = the hand candidate count is 0 (hand path never seen); O3 = rider step.
- O2/O4 ROOT CAUSE (savestate .ml2, ROM identity OK; scratch/infernoble/oliver_ss.py + handworker.py): side-0 hand
  @player+0x124 = Painful Choice, Maugis x2, Premature Burial, Card Destruction, RotA, Ogier, Oliver. Our +0C hand
  count 0x02243FE0(0, 0x1E04, param 0) = 0. Calling the hand worker 0x0223BFD4 directly: NO callback + word 0 ->
  count 1; FIRE Warrior word 0x7C000002 -> 0 although 3 FIRE Warriors are in hand; our callback is called ONLY for
  0x132F (hand slot 0). => for a HAND row, the param of 0x02243FE0 is a hand INDEX (the Jet Synchron docstring's
  upstart_golden_ninja warning) -- our availability checks only ever tested hand slot 0. The native hand cost
  machine is not implicated. FIX: loop i = 0 .. hand count-1 over 0x02243FE0(side, cid, i).

- O3 ROOT CAUSE (savestate .ml4, ROM identity OK): Oliver at side 0 zone 3 with NO rider (query 0x021A14E8 for keys
  0x1EC1 / 0x22EB kind 3 = 0). The native hand-SS resolver summons in ITS phase 0x80 (`bl 0x02269314 ; movs r0,#0x7f`
  @0x02206C1E) and ends in its 0x7F with 0; our wrapper passed that 0 through -> our 0x7E never ran.
  LOCATE(desc[+0xC]) over .ml4 on Oliver's hand descriptor (@0x0229A7FC, ref 0x44) = 0x300 = side 0 zone 3 -> the
  0x7E write lands on the right card once reached.
- BUILD 5 (2026-10-20) sha256 1c0832485f6b2348e475326eb2da7a73d7af2ae0b7e9a4f49eab8e957e011a48:
  (a) new ov5 O_HANDANY(desc) loops hand indices 0..count-1 (count = player+0x0C) over 0x02243FE0; used by +0C and by
  the cost's Hands/Field decision. (b) resolver: ANY native 0 -> our 0x7E.
  OFFLINE PROOF over the user's boards with the NEW stubs loaded into the savestate memory: .ml2 -> hand-any 1,
  field 0, +0C 2, mode "hand only"; .ml3 -> hand-any 1, field 2, +0C 2, mode "Hands/Field prompt".
  patch_infernoble.verify PASS; chain_walk_diff / miss_diff / gyv_equiv PASS. RE-TEST PASSED (user 2026-10-20).
- STILL ASSUMED: rider key 0x1EC1 = SET (KB dispatch.level_rider_key_is_a_selector, VERIFIED by A/B) gives Level 1.

## Plan (as built)
- C1: extend Ogier's PROT (0x021B059C) -- Oliver-equipped && targets flag && acting side != target side (Safe Zone's
  opponent test `1 - desc[+2] == r6`).
- C2: hand-SS ignition + mixed cost (hand OR face-up field; FIRE Warrior monster OR Equip Spell) + Level-1 rider
  {0x1EC1, kind 3, 1} (Psi-Reflector's in-game-confirmed recipe).
- C3: Ogier's GY equip: gy_vrow_hook row, EQFILT +cid, ignition row, cls2 record.

## Confirmed
- No NDS card has "send 1 card from hand OR face-up field as cost; SS this card from hand" (grep of the pool, this
  session). Nearest shipped shapes: Dragon Rulers C1 (hand/GY mixed-zone banish cost, hand+GY ignition; ov5 COST
  stub), Jet Synchron C2 (send 1 card from hand: Plaguespreader cost machine clone), Sakitama (hand effect + other
  clause in ONE cls2 record switched on desc[+3] == 0x0B, the hand probe 0x021EDD90 writes zone 0x0B).
- HAND EFFECTS ARE OFFERED ONLY FOR CIDS IN ARM9 LIST A 0x0209BC4E (x0x1E) OR LIST B 0x0209BC8C (x0x24)
  (KB @0x0202354C, hand-menu flag builder 0x0224BC40 @0x0224C050). Chain ROM: LIST A has NO phantom left; LIST B
  still holds phantom 0x1A86 (stock B phantoms 0x0E63 / 0x1774 / 0x1A86; the first two are gone in the chain).
  Maiden's ledger claim ("quickeffect_list", 0x1A86) is the DIFFERENT speed-2 list 0x0209C118
  (patch_maiden_eyes_of_blue.py:338-341) -> 0x1A86 in LIST B is unspent. Pool naming in check_allocations mixes the
  two lists -> file Oliver's claim under an explicit new pool name.
- C2 building blocks (record dumps + disasm, this session):
  * FIELD cost machine +10 0x021E712D, candidate filter = the record's +08 (Ultimate Baseball Kid 0x17E1 cls3[178]
    +08 0x021DBB75 "face-up FIRE monster you control"; Magic Planter 0x2008 +08 0x021E19CD (Continuous Trap in S/T);
    White Elephant's Gift 0x23B2 +08 0x021E0E45). Field filters start 0x021D6E40(desc, side, zone, mask): mask bits
    0-1 side (01 = source's side), bit 2 = face-up (in every "face-up" mask: 0x15, 0x8015, 0x20814), bits 4-6 zone
    class (0x10 = monster zone).
  * HAND cost machine +10 0x021E7245 with criteria row 0 = cost zone (Armed Changer 0x197C cls0[668], crit
    {0x0223CB65 send-from-hand, 0x00000204}; Ojama Country cls3 recipe in KB). Hand worker 0x0223BFD4(side, cid,
    r2 = param, r3 = CALLBACK, [sp] = cb arg, [sp+4] = word, [sp+8] = mode 0x11 send / 0x10 select); callback gets
    [sp] = &card word, [sp+4] = cb arg (same contract as the GY/Deck workers).
  * Criteria word low flags = OPTIONAL restrictions (0x0223BA24: bit 0x2 -> 0x02029E60 is-monster, 0x400 hand test,
    0x2000 ATK <= 1500 ...) -> word 0 = any card; the callback does the filtering.
  * card_prop getters (ARM9, word1 of the record), DECODED OVER THE REAL card_prop.bin: 0x0202ABB8 race (Warrior 15,
    every Spell 23, Trap 24); 0x0202ABC8 attribute bits 6..9 (FIRE 4, DARK 2, EARTH 5; Spells 8, Traps 9);
    0x0202ABD8 bits 10..13 level; **0x0202ABE8 bits 14..16 spell type: Equip = 3** (Mist Body, Premature Burial,
    Broken Bamboo Sword, Legendary Sword, Molting Escape), Normal 0, Field 4.
  * Hand self-SS resolver 0x02206ABD (Dragon Rulers RES_HAND_SS, in-game confirmed). Level rider {0x1EC1, kind 3, N}
    = Psi-Reflector's recipe. Hand-effect offer: LIST B 0x0209BC8C phantom 0x1A86 (unspent there).
  * "Use which?" prompt 0x0219ABB4(desc, title, l0, l1, [sp] l2, [sp+4] l3, [sp+8] mask): dlg_text_e ids (dlg_indx_e /
    dlg_text_e in bin2.pac): 0x3A "Select the card to send to the Graveyard.", 0x192 "Hands", 0x23C "Field",
    0x103 "Use which effect?", 0x3D "Send a card in your hand to the Graveyard.".

## Ruled Out
## Open Questions
- C2 cost picker over hand + field with a mixed filter: native precedent?
- C3 cls2 vs C2 record class: C2 is a HAND ignition (cls?) -- does it collide with C3's cls2 record (leftmost-only)?
## Next Experiment
- Grep KB/patches for hand-SS ignition records (Dark Grepher 0x1D89 "discard 1 L5+ DARK: SS from hand").

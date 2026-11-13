# Courageous Crimson Chevalier Bradamante — findings

Family card 9. User 2026-10-21: "While I test Astolfo, begin Bradamante". Clause split (C0 text only) + donor Sonic Duck 0x160B (L3 WIND Winged Beast Normal 1700/700) confirmed by user 2026-10-21 ("Confirmed, Sonic Duck — proceed"). donor_scan CLEAN.

## Printed text (scratch/ygoprodeck_cache.json): Tuner, Warrior, FIRE, L1, 500/200
- C0 (This card is always treated as an "Infernoble Knight" card.)
- C1 (hand ignition) cost: discard this card; target 1 Warrior you control; equip it with 1 Equip Spell from your
  Deck that can equip to it. (once per turn)
- C2 When this card, not equipped with an Equip Card, is destroyed by battle with an opponent's monster and sent to
  the GY: you can SS this card, and if you do, equip that opponent's monster to this card. (once per turn)

## Candidate donors (donor_scan CLEAN 2026-10-21; no free Lv1/2 or Lv4 <= 1500 Normal left)
- Sonic Duck 0x160B (L3 WIND Winged Beast 1700/700), Jerry Beans Man 0x190D (L3 EARTH Plant 1750/0),
  Hunter Dragon 0x1C19 (L3 DARK Dragon 1700/100).

## User decisions
- 2026-10-21: C0 text only (no "Infernoble Knight" set code exists; nothing built searches by it).
- 2026-10-21: C2's "not equipped with an Equip Card" -> "Build the hook" (faithful leave-time check).

## Confirmed (2026-10-21, static)
- C1 = Vylon Sigma 0x22D4 / Dragunity Primus Pilus 0x2170 shared resolver 0x0222DC49: cid 0x2170 takes the
  DECLARED-TARGET branch (0x02234904(desc, 0) -> (zone<<8|side)) at the literal compares @0x0222DC50 and
  @0x0222DCBE; every other cid equips to ITSELF (0x021A241C(desc[+0xC])). Sigma criteria handler 0x02242C18 =
  Deck worker 0x0223BC3C with callback 0x0223E395 and cb arg = &param; word 0x204. 0x0223E394 builds a probe desc
  (candidate cid, zone 0xB, ref) and returns 1 iff the equip-target switch 0x021D7348(probe, param & 0xFF,
  (param >> 8) & 0xFF) == 1 -- the native "Equip Spell that can equip to THAT monster" test, location = param.
  Pilus also has per-cid gates in its own +08 (0x021E0726) and +0C (0x021F9BAC) -- we use our own slots.
- C1 cost = Thunder Dragon's discard-self 0x021E6FD9 (KB dispatch.hand_discard_ignition_cls2_slots).
- C2 victim-side trigger list = list106 0x0226E990 (KB event.battle_destroy_flags_table: "this card destroyed by
  battle and sent to the GY"; Mathematician precedent). Yomi Ship 0x1591 / Exploder Dragon 0x1BB6: cls2
  {0x022048FD, +08 0x021E1479, +0C 0x0224A115, +10 0}. +08 0x021E1479 = Fist's filter: a cid-free copy is the
  prologue + jump to 0x021E1577 -> "the monster it battled" (KB, Amazoness Heirloom session).
- "Equip that opponent's monster to this card" = Allure Queen / Underground Arachnid resolver 0x0220BFFD with target
  step 0x02234D99.
- Leave dispatcher (memory otn-leave-descriptor-slots): per-cid switch @0x021C8216 runs BEFORE the leaving card's
  equips are processed; stack slots [sp+0x90] destroyed, [sp+0x44] by battle, [sp+0x98] side, [sp+0xa0] zone;
  currently BLs the shared T.G. arm trampoline CAVE3_TGSH_ARMTRAMP. Plan: ov5 front for 0x160B (EQUIP_TARGET_OF scan
  -> turn-log "was equipped" marker), tail-jump to the trampoline.

- Leave site 0x021C8216 BLs CAVE3_TGSH_ARMTRAMP 0x021FAC78 in rom_infernoble (stock bytes 77218901 = movs r1,#0x77;
  lsls r1,#6). list106 0x0226E990 x0x6A sorted, unclaimed phantoms incl. 0x1B18; 0x160B not a member.
- Allure resolver 0x0220BFFC: 0x80 target valid (0x022349B0 / 0x0224A924), 0x021D2C1C(desc) (this card OK) && free
  S/T 0x021AE644 -> reserve 0x0225BDD8 -> 0x7F move -> 0x7E attach; else 0x021CF6E0 on the target.
- Target steps 0x02234D81 / 0x02234D8D / 0x02234D99 = `r2 = msg (0x6F / 0x7C / 0x64) ; bx 0x02234CA5`.
- Fist filter 0x021E1478 prologue: zone predicate 0x021D6E40(desc, side, zone, 0x1010); arm 0x021E1576 = battle
  participant 0x021A3C78(side, zone) && (zone<<8|side) != 0x021A0DF8(desc side, desc zone).

## Build design (BUILD 12)
- ONE cls2 for 0x160B switched on desc[+3]: HAND = C1 {res: OPT 0x560B -> 0x0222DC49 (cid fronts @0x0222DC50 /
  @0x0222DCBE make 0x160B take Pilus's target branch), +08 Vylon filter -> EQFILT Warrior-you-control arm, +0C OPT +
  Equip Spell in Deck + free S/T + >= 1 legal target -> 1, +10 discard-self 0x021E6FD9, +14 0x02234D8D};
  GY = C2 {res: stage 0 OPT 0x360B + GY self-SS 0x0220731D -> 0x91 pop -> 0x92 desc[+3] = new zone, [0x70] = 0x80
  -> Allure 0x0220BFFD (0x7F / 0x7E pass through); +08 Fist copy + opponent-side check; +0C OPT, no "was equipped"
  marker, may SS, free MZ, free S/T -> 1; +10 "You can" + timing arm (prepended); +14 0x02234D99}.
- Criteria row: Deck worker + native legality callback 0x0223E395 with &loc, loc = 0x02234904(acting desc, 0).
- list106 member over phantom 0x1B18. Leave front (ov5) at 0x021C8216: 0x160B && by battle && destroyed -> scan
  S/T zones 5..9 both sides for EQUIP_TARGET_OF == (zone<<8|side) -> post marker {0x760B, kind 1} else remove it;
  tail-jump to CAVE3_TGSH_ARMTRAMP.
- DESIGN CHOICE TO FLAG: C2 needs "that monster" to still be on the field to activate (+0C returns 1 -> +08 must find
  it). If the user's ruling differs, change +0C to 2 and let the resolver skip the equip.

## IN-GAME RESULT BUILD 12 (user 2026-10-21)
User's words: "Bradamante does not get equipped by the opponents monster, instead the monster is sent to the GY. It
should behave like relinquished or thousand eyes restrict if you need a precedent" / follow-up: "Yes it was summoned,
the rest passed".
- PASSED (in-game confirmed by user 2026-10-21): BR1, BR2, BR3, BR4, BR6, BR7 (incl. the leave-time "was equipped"
  marker: C2 refused while equipped).
- FAILED: BR5 second half -- C2 activates, Bradamante IS Special Summoned from the GY, but the opponent's monster is
  sent to the GY instead of becoming an Equip Card on it. Precedent named by user: Relinquished / Thousand-Eyes Restrict.

## BR5 DIAGNOSIS (static, 2026-10-21)
- Relinquished 0x1281 / Thousand-Eyes Restrict 0x1284 (user's precedent): cls3 {0x0220BFFD, 0x021DB1E9, 0x021F2461,
  0x021E5061, 0x02234D99} = the SAME resolver as Allure -> the resolver choice is right.
- 0x0220BFFC phase 0x80: `bl 0x021D2C1C(desc)`; 0 -> `0x021CF6E0(target side, zone, 0, 0)` (target to the GY) instead
  of equipping. 0x021D2C1C on a monster zone (0..4): LOCATE(desc[+0xC]) >= 0, zone word [0x0229ACD8 + side*0xB3C +
  zone*0x14] bit 26 clear, desc[+0xE] == ([0x0229C33C + ref*8] << 11) >> 30 (2 instance bits), and the zone's
  halfword [0x0229ACD0 + ...] != 0. BR_C2RES re-pointed desc[+3] but NOT desc[+0xE]; the GY -> monster-zone move
  changes the instance bits -> stale -> 0 -> exactly the in-game symptom (summoned, monster sent to GY).
- FIX (BUILD 13): BR_C2RES phase 0x92 also writes desc[+0xE] = the card's current instance bits.

## IN-GAME RESULT BUILD 13 -- WHOLE CARD in-game confirmed by user 2026-10-21
User's words: "Okay Bradamante all confirmed". (The 21:36 .ml2 retest was STILL BUILD 12 code in RAM -- a savestate restores overlay 5; a fresh duel loads it from the ROM.) NOT shipped.

## BUILD 13 (2026-10-21)
- rom_infernoble.nds sha256 a03e78dc3376f23e6642cce35af7acd0976c97075013b0415141bd9035e65428; verify PASS; regression
  list = the known set. User's .ml2 retest (21:24, "hanzo went back to the GY") was on BUILD 12 -- the savestate's
  BR_C2RES bytes equal BUILD 12's, not BUILD 13's (checked 2026-10-21).

## BUILD 12 (2026-10-21)
- rom_infernoble.nds sha256 bec21c4a61dcd6621aeadc15b36fad6a9060cd630c290d6a9dc8372fcdaecc9b (all nine).
- patch_infernoble.verify PASS (BR rows, list106, three fronts, text). Regression list = BUILD 10/11's known set.
  NOT run: patch_tg_striker / tg_table verify -- they expect 0x021C8216 -> CAVE3_TGSH_ARMTRAMP directly; the site now
  BLs BR_LEAVE, which tail-jumps there for every other cid (local-front category).
- ASSUMED: (1) leave slots [sp+0x98]/[sp+0xA0] are the absolute side / zone 0x021A0DF8 compares against; (2) the
  marker post (queued) is applied before the list106 trigger's +0C runs; (3) desc[+3] re-pointing lets Allure's
  0x021D2C1C accept the newly summoned card.  Each maps to BR5/BR6.

## Ruled Out

## Open Questions
- Are the leaving card's equips really still attached at 0x021C8216? (static reading; confirm by disassembly of the
  equip clean-up order or in-game item).

## Next Experiment
- Disassemble Allure's 0x0220BFFC phases; list106 phantom; Fist-copy prologue; then build 12.

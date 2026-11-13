# Infernoble Knight Astolfo — findings

Family card 8. User 2026-10-21: "While I test Roland, begin Astolfo". Clause split + donor Griffore 0x0FD4 (L4 EARTH Beast Normal 1200/1500) confirmed by user 2026-10-21 ("Confirmed, Griffore — proceed"). donor_scan CLEAN.

## Printed text (scratch/ygoprodeck_cache.json): Effect, Warrior, FIRE, L1, 500/200
- C1 (hand ignition) cost: banish 1 FIRE Warrior from your hand or GY; SS this card from your hand, then you can make
  this card's Level become the banished monster's Level.
- C2 (GY ignition) cost: banish this card from your GY; during your 2nd Standby Phase after activation, SS this
  banished card, then you can SS 1 of your FIRE Warriors that is banished or in your GY.
- C3 each effect once per DUEL (not per turn).

## Candidate donors (donor_scan CLEAN, 2026-10-21)
- Griffore 0x0FD4 (L4 EARTH Beast 1200/1500), Sonic Duck 0x160B (L3 WIND Winged Beast 1700/700),
  Jerry Beans Man 0x190D (L3 EARTH Plant 1750/0), Hunter Dragon 0x1C19 (L3 DARK Dragon 1700/100).

## Confirmed (2026-10-21, static)
- ONCE PER DUEL = turn-log kind 5 (KB rider.turn_sweeper: kinds 0/4/5 never swept): Twin-Headed Behemoth 0x13A6 +0C
  0x021F44D8 = query 0x021A14E8(side, 0xB, cid, 5) clear -> 0x021F04FC; Glow-Up Bulb +10 0x021E81E4 = post
  0x021D2584(side, cid, 5, 0) -> 1. Astolfo: C1 key 0x0FD4? NO -- synthetic keys 0x4FD4 (C1) / 0x2FD4 (C2), kind 5,
  because 0x0FD4 kind 1 is C2's delayed-return node key.
- DELAYED RETURN = Drill Warrior 0x21CC ("banish this card. During your next Standby Phase: SS this card banished
  by this effect"): registry row 404 {0x02257739, 0x21CC} in section 293..428 (KB timing.registry_section_geometry);
  handler 0x02257738(side, cid): ONLY on that side's own turn, walks the turn log for {key cid, kind 1/2, countdown
  nibble [+2]bits4..7 == 0, ref} and posts 0x021D3168(0x04400000 | side<<31 | zone<<16 | cid, ref) = desc[+4] 2,
  cls2, zone = the ref's CURRENT zone; then removes the node. Drill's resolver posts the node at 0x0222E4F0 with kind
  byte 0x21 (countdown 2) when banished-card owner == desc side (else 0x11), param = ref.
  COUNTDOWN MODEL (KB rider.node_writer_and_kind_byte / rider.turn_sweeper): nibble N decremented at each turn end,
  node visible to the walker only at 0 => posted on my turn T: N=2 -> fires my Standby T+2 ("next"); N=4 -> my Standby
  T+4 = "2nd Standby Phase after activation" (at T+2 nibble = 2 -> skipped).
- Free registry row in section 293..428: row 294 {0x022573DD, phantom 0x1775} (unclaimed) -> {0x02257739, 0x0FD4}.
- Summon commit 0x02269315(side, &card word, 1, cid<<16) -> 0x0226925C derives ref + SOURCE zone from the word
  (0x021A220C) => zone-agnostic: summons Astolfo from banished and a picked FIRE Warrior from GY/banished.
- Self-SS resolver 0x0220731C is zone-agnostic too (current zone == desc[+3], instance bits desc[+0xE]).
- C1 cost = Dragon Rulers' hand+GY banish machine (MESSAGE -> PICKER(side,6,cid,0) -> READBACK -> HAND_INDEX /
  HAND_BANISH or REF_TO_WORD / GY_BANISH), list builders HAND_BUILDER 0x0223C16D / GY_BUILDER 0x0223C4E9 with
  [sp]=2, [sp+4]=0x10000 and a FILT callback excluding this card BY REF (acting desc[+0xC]).
- Optional Yes/No: Fire Formation - Tenki's YESNO 0x0219AAAD(desc, 0xFA, ref), answer [0x0229DD94+0x34].
- Level: LEVEL_OF_CID 0x0202ABD9 (printed Level); Level SET rider {0x1EC1, kind 3, N} (Oliver, in-game confirmed).

## Ruled Out

## Open Questions
- None blocking; design next.

## IN-GAME RESULT -- whole card in-game confirmed by user 2026-10-21 (BUILD 11)
User's words: "Astolfo is all confirmed" (AS1-AS6). This also confirms the countdown-4 node fires at the 2nd own Standby. NOT shipped.

## BUILD 11 (2026-10-21)
- rom_infernoble.nds sha256 80cab6c46790022bff7cbe6c3d102f53d32f8efc6e489cc5efd0236c3885ba7b (all eight Knights).
- patch_infernoble.verify PASS (AS cls2 / criteria / registry row 294 / GYV row / text). Regression list = BUILD 10's.
- Offline over .ml2 (AS stubs in memory): AS_COND hand -> 2 (3+ FIRE Warriors in hand+GY), banished event 2 -> 2,
  banished event 6 -> 0, GY event 7 -> 0.
- ASSUMED (not executed): the countdown-4 node reaches Drill Warrior's walker exactly at the 2nd own Standby (KB
  sweep model); the hand self-SS 0x02206ABD + Level rider path is Oliver's (confirmed).

## Next Experiment
- In-game AS1-AS6 (_build_infernoble.py). If AS5 fires at the wrong Standby, savestate each Standby and dump the
  turn log (scratch/infernoble/turnlog_dump.py: node 0x0FD4 flags = 0x?1, high nibble = remaining countdown).

# Eidos the Underworld Monarch (0x1230, donor Whiptail Crow) -- findings

Status 2026-11-11: E1 (DECK half) + E2 BUILT as a test ROM (`_build_eidos_monarch.py`, verify 38/38) and in the combined Monarch ROM (14 modules). NOT shipped, nothing user-confirmed.
NOT BUILT: E1's GY half, E3 (GY recursion on a Tribute Summon of a >=2400/1000 monster).  AWAITING IN-GAME TEST.

Text: "If this card is Normal or Special Summoned: You can add 1 "Monarch" Spell/Trap or 1 monster with 2800 ATK/1000 DEF from your Deck or GY to your hand. You can declare 1 Attribute; make 1 face-up
monster on the field become that Attribute. If you Tribute Summon a monster with 2400 or more ATK and 1000 DEF, while this card is in your GY: You can add this card to your hand or Special Summon it.
You can only use each effect of "Eidos the Underworld Monarch" once per turn."  DARK / Spellcaster / Lv6 / 2400 / 1000.

## Built
- E1: cls1 {native Deck->hand 0x02207EF5, 0, COND, "You can" 0x021E51E5, COST} over cls1 phantom 0x0EA7, N-or-SS shared hook (8th arm, BIG stub slot), virtual Deck row 0xFFD4 (Deck add enumerator
  + predicate: Monarch set code 0x6D OR ATK 2800 and DEF 1000; PRINTED values).
- E2: cls3 ignition {RES3, filter 0x021DB1D9, COND3, COST3, selector 0x02236ECD} over cls3 phantom 0x0E57 -- Genex Ally Changer's (0x2167) selector/filter reused UNPROVEN-as-generic; RES3 attaches the
  attribute rider keyed 0x2167 (cur_attribute 0x021B8E48 reads riders of key 0x2167: returns node+4 when node+6 >= r5, read this session) via 0x02207908(desc, kind 3, desc[+0x16] = the declared Attribute, 0),
  after swapping desc cid to 0x2167 and back.  Kind 3 = permanent (no duration printed).  KNOWN UNPROVEN: that the selector stores the declared Attribute at desc+0x16 and works for a non-Genex cid; node+6 meaning.

## CPU evidence (emulator CPU, NOT user-confirmed)
- cardtest mirror 0x1230 (March/Zaborg/Raiza kit), 8 duels: drawn 14 / summoned 7 / activated 7, no hang.
- scratch/emonarch_gdb.py seed 1: ED_COND -> ED_COST -> native Deck->hand phases 0x80/0x7E/0x7D/0x64; the hand gained 0x15EC (March of the Monarchs) at phase 0x64 -> E1's Deck half adds a Monarch S/T.
  E2 was not exercised (the CPU does not use it).

## Next
- GY half of E1: needs a native resolver that adds a GY card (cls2's 0x02208181 is target-based via the picker); or a two-row design with a mode switch.
- E3: bystander GY trigger on Tribute Summon (Assault Synchron's poster 0x021C93D0 -> 0x021D3648 recipe + the Mega TRIG front's Tribute test).
- User test: Normal/Tribute Summon it -> prompt, a Monarch S/T or 2800/1000 monster joins the hand; the ignition declares an Attribute and changes a face-up monster.

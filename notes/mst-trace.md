# Mystical Space Typhoon (cid 0x132D) - static ov3 call tree (2026-10-18)

Printed text (scratch/ygoprodeck_cache.json via cardrows.py): "Target 1 Spell/Trap on the field; destroy that target."
Static decode only. No in-game claim anywhere in this file.

## cls0[214] @0x0227FA5C (cardrows.py output)
| slot | value | note |
|---|---|---|
| +04 resolver | 0x02204899 (fn 0x02204898) | catalogue PARTIAL, callers=12 |
| +08 candidate predicate | 0x021DB3BD (fn 0x021DB3BC) | catalogue HANDLER (cls-table callback shared by 19 record slots) |
| +0C activation condition | NULL | |
| +10 cost/activation step | NULL | |
| +14 target step | 0x02234DA5 (fn 0x02234DA4) | KNOWN, card.target_step_board_vs_criteria |

## Call tree
(size / catalogue status / fact covering it / what it does on this card's path)

- 0x02234DA4 (0x10, KNOWN) [VERIFIED card.target_step_board_vs_criteria; dispatch.slot5_target_picker]: `ldr r2,=0x119 ; bx 0x02234CA5`. Prompt code 0x119 (r2) and the board step. Decoded now: 0x02234CA4(desc, r1, r2=prompt):
  - reads state counter [0x0229AB7C]; state 0 -> calls 0x0224AA94(desc).
  - 0x0224AA94 (0xA4) [VERIFIED engine.board_target_count_0x0224AA94]: find_event_handler 0x0224A118(desc,0) -> this card's cls0 record -> its +08 = 0x021DB3BD; sweeps side 0..1 x zone 0..10, skipping zones whose flag word has bit 21 set, calls the predicate per zone and counts hits.
  - count 0 -> 0x02234CA4 returns 1 with no picker (decoded: 0x02234CC4..0x02234CCE). count 1 -> only for cids 0x2179 / 0x2179+0x77 the auto-pick 0x02234E3C (not this card); otherwise (count >= 2, or count 1 for any other cid) goes to the picker call 0x0224BA34(side-from-desc, cid, 0, 0x0224A8C1) after 0x02234BDC / 0x0219A818 prompt setup (r4 = prompt 0x119 > 0 -> 0x0219A818(side, 0x119) shown). State counter [0x0229AB7C] is then incremented; the next call (state 1) tests 0x0224BBB0 (engine.pick_finished_predicate_0x0224BBB0) and, if finished, 0x022347B0 records the pick. (State machine decoded from 0x02234CA4..0x02234D58 only.)
- 0x021DB3BC (0x10, HANDLER) [VERIFIED engine.mst_candidate_pred_0x021DB3BC, new]: wrapper, passes (desc, side, zone) through with r3 = 0x21440 to
  - 0x021D6E40 (0x4EC, KNOWN) [VERIFIED card.safe_zone_either_side_controller_relative (partial), new VERIFIED engine.zone_predicate_mask_21440_path_0x021D6E40]. With mask 0x21440 (bits 6,10,12,17):
    1. (mask&3)==0: no side restriction (either field).
    2. (mask&0x70)==0x40: zone class arm 0x021D701A: zone > 10 rejected; zone 0..4 only if 0x021A1C54(side,zone) (flag bit 10 of [0x0229ACD8+side*0xB3C+zone*0x14]) non-zero; zones 5..10 accepted. This is the ONLY place "Spell/Trap" could be expressed in the predicate: it is a ZONE-INDEX test (zones 5..10), not a card-type test. Nothing in the decoded MST path reads the card's type.
    3. zone record word [0x0229AC94+side*0xB3C+zone*0x14+0x34] low 14 bits non-zero (occupied).
    4. bit 0x400 -> 0x021AFD3C(desc,side,zone) must be non-zero (targetability; PARTIAL, notes only, not decoded here; 0x4E0 bytes).
    5. bit 0x1000 -> 0x021B0828 (0x10 wrapper of 0x021B021C) must be non-zero.
    6. bit 0x20000 -> reject if desc[+0xC] (u16) equals the zone card's packed ref.
    7. zone <= 4 and [0x0229AB7C+0x14] <= 0: reject if 0x021AFCBC(desc,side,zone) non-zero.
    8. else return 1.
  - 0x021A1C54 (0x28, was UNKNOWN) [new VERIFIED engine.zone_flag_bit10_0x021A1C54]: reads zone flag bit 10.
  - 0x021AFD3C (0x4E0, PARTIAL), 0x021B0828 (0x10, PARTIAL) -> 0x021B021C (not examined), 0x021AFCBC (not examined): helpers, NOT decoded here.
- 0x02204898 (0xC, PARTIAL) [new VERIFIED engine.mst_resolver_0x02204898]: `bl 0x02204674 ; movs r0,#0`.
  - 0x02204674 (0x44, PARTIAL) [new VERIFIED engine.destroy_body_0x02204674; also covered by dispatch.destroy_then_protocol and card.souleating_oviraptor_c2 (UNVERIFIED mention)]:
    - zero [0x0229C314+0x14], [+0x18].
    - 0x022349B0(desc,0,&sp) (0x118, KNOWN) [VERIFIED engine.pick_validate_0x022349B0]: pick 0 -> side|key<<8, checks the zone record still holds the picked card ref.
    - 0x0224A924(desc,side,zone) (0x64, KNOWN) [VERIFIED dispatch.resolver_revalidates_pick_via_slot2]: find_event_handler -> record +08 (= 0x021DB3BD for this card) -> re-run the candidate predicate on the picked zone (skips it, returning 1, if the zone flag bit 21 clear test fails per that fact's description; bit 21 set -> returns 0). Increments/decrements [0x0229AB7C+0x10] around the call.
    - 0x021CF388(desc,side,zone) (0x18, PARTIAL) [new VERIFIED engine.destroy_at_field_0x021CF388]: mask = 1<<(side*16+zone) -> 0x021CDD4C(desc, mask, 0x0E, 0x10000002).
      - 0x021CDD4C (0x5C, PARTIAL) [new VERIFIED engine.relocation_request_core_0x021CDD4C]: queues the relocation request (copies desc to 0x0229DE34, ORs mask into [0x0229C294+0x7C], stores dest 0x0E / kind 0x10000002 at 0x0229DE14+0x44/+0x48, sets +0x18=1). The consumer that performs the move was NOT traced.

Resolver sharing: the catalogue lists 12 callers for 0x02204898; 12 was not enumerated here, and Trap Hole's wiring was not examined. By the decoded body, the resolver has no card-specific constant, so every card reaching it runs the same destroy of pick 0 and differs only in its +08 predicate (and +14 target step).

## What happens when you activate MST (static reading)
1. Activation reaches the cls0 record found by find_event_handler 0x0224A118 (VERIFIED dispatch.find_event_handler); +0C and +10 are NULL so no condition/cost step runs from this record.
2. Target step +14 = 0x02234DA5 -> 0x02234CA4 (card.target_step_board_vs_criteria; dispatch.slot5_target_picker). First sub-step calls the board counter 0x0224AA94 (engine.board_target_count_0x0224AA94).
3. The counter calls MST's +08 (0x021DB3BD -> 0x021D6E40 mask 0x21440; engine.mst_candidate_pred_0x021DB3BC, engine.zone_predicate_mask_21440_path_0x021D6E40) on all 22 (side,zone) pairs; accepted = occupied, zone 5..10 (or zone 0..4 with zone-flag bit 10), passes 0x021AFD3C and the 0x1000 check, desc[+0xC] mismatch, etc.
4. If the count is 0 the step returns 1 with no picker (no target selected; see NOT proven for what activation then does). Otherwise the picker (0x0224BA34, 0x0219A818 prompt 0x119) runs and 0x022347B0 records the pick as pick 0 of the descriptor (State machine of 0x02234CA4 decoded; the picker internals were not).
5. On resolution the cls0 +04 resolver 0x02204899 (engine.mst_resolver_0x02204898) calls 0x02204674 (engine.destroy_body_0x02204674).
6. 0x02204674 re-validates pick 0 with 0x022349B0 (engine.pick_validate_0x022349B0), then re-runs the +08 predicate through 0x0224A924 (dispatch.resolver_revalidates_pick_via_slot2). If either fails nothing is destroyed.
7. Otherwise 0x021CF388 -> 0x021CDD4C queues a relocation of that zone's card to destination code 0x0E (GY per engine.ref_to_locator_0x021A220C zone codes) with kind 0x10000002 (engine.destroy_at_field_0x021CF388, engine.relocation_request_core_0x021CDD4C).

## NOT proven
- That the predicate excludes face-up monsters / selects only Spell/Trap CARDS: the decoded path tests zone index (5..10) and zone-flag bit 10 for zones 0..4, never the card type. Meaning of flag bit 10 unknown. Whether zone 10 is the Field Spell zone and zones 5..9 the S/T row is only implied by the 0..4 monster / 5..10 split in the decoded arm.
- What 0x021AFD3C (targetability), 0x021B021C (via 0x021B0828), 0x021AFCBC compute; the meaning of the desc[+0xC] compare (bit 0x20000).
- Whether MST can target itself / Set cards / what the picker offers; picker internals 0x0224BA34, 0x0224BBB0 use.
- What happens at activation when the count is 0 (step returns 1 with no pick; whether the activation is then blocked is not shown here).
- The relocation consumer (who reads 0x0229DE14 and moves the card), what bit 28 of kind 0x10000002 does, and whether the "destroyed" flag [0x0229C314+0x14] is ever set on this path.
- The 12-caller sharing list and Trap Hole's wiring; chain-link / negation / response windows; any in-game behaviour.

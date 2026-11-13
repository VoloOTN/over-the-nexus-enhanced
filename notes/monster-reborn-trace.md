# Monster Reborn (cid 0x12EA) - static trace, 2026-10-18

Printed text (scratch/ygoprodeck_cache.json): "Target 1 monster in either GY; Special Summon it."
Static decode only. Nothing here is an in-game claim.
"New" facts are in block.py (all PASS in check_block.py): `engine.mr_cls0_resolver_front_0x0220D530`,
`engine.mr_cls0_activation_cond_front_0x021F2BAC`, `engine.thunk_0x02204724`,
`engine.mr_either_gy_criteria_thunk_0x0223D6E0`, `engine.ss_from_pick_0x02204730`.

## Records (cardrows.py 0x12EA)

cls0[166] @0x0227F5DC:

| slot | pointer | role | catalogue | fact |
|---|---|---|---|---|
| +04 | 0x0220D531 | resolver | HANDLER, 0x28 B | NEW engine.mr_cls0_resolver_front_0x0220D530 |
| +08 | NULL | candidate predicate | - | - |
| +0C | 0x021F2BAD | activation condition | HANDLER, 0x2C B | NEW engine.mr_cls0_activation_cond_front_0x021F2BAC |
| +10 | NULL | cost / activation step | - | - |
| +14 | 0x02235605 | target step | KNOWN, 0xFC B | dispatch.offfield_picker_sequence |

Criteria row 90 of 0x022713C4: {cid 0x12EA, aux 0xFFFF, handler 0x0223D6E1, word 0x00010002}
(card.either_gy_revive_trigger_template; also asserted by NEW engine.mr_either_gy_criteria_thunk_0x0223D6E0).

## Call tree

```
ACTIVATION CONDITION  0x021F2BAC(desc, r1)                      [NEW fact]
 |- 0x021AC204(0x12FB)  field count of cid 0x12FB (cardrows: Call of Darkness)   engine.field_cid_count_0x021AC204
 |     count > 0 -> return 0 (not offerable)
 `- else tail 0x021F03B4(desc, r1)   generic "is there a legal candidate"  (catalogue PARTIAL, 0x34 B)
      |   KB: card.either_gy_revive_trigger_template ("reads only r0 = desc") ; body decoded this session:
      |- x = desc[2]^desc[6]; 0x021F0384(desc)                  engine.desc_xor_bytes_two_helpers_0x021F0384
      |     |- 0x021F0114(desc, x) -> 0x021AD870(x)   SS gate #1  engine.thunk_0x021AD870 (body 0x021AD79C NOT pinned)
      |     `- 0x021B9EC0(x, cid) = 0x021B9708(x, 8, cid)  SS legality gate, cid-aware  summon.legality_gate_and_mode_bits
      |- 0x02234E78(desc)  row-param provider                    dispatch.row_param_provider_call_sites
      `- 0x02243FE0(x, cid, param) count of candidates, buffer restored   engine.criteria_count_0x02243FE0
            `- 0x02243B9C bsearch -> row 90 -> 0x02243F38 runner -> blx row.handler(row, side, param)   (criteria_collect_0x02243FA8 fact)
                  `- 0x0223D6E1 (thunk 0x0223D6E0)                 [NEW fact]
                        `- 0x0223C4E8(side, 0x12EA, 0, 0, word 0x00010002, flags 0xA)   engine.split_pair_sum_0x0223C4E8
                              `- 0x0223C1C4 x2 (flags bit 1 set: pass 1 with bit 1 cleared, pass 2 with bit 0 toggled)

TARGET STEP  0x02235605                                          dispatch.offfield_picker_sequence
   step 0: 0x02243FA8(side, cid, param) fills candidate buffer via the SAME row-90 path above; n==0 -> return 1;
           else prompt 0x0219A818(side, 0x5E), yield
   step 1: 0x0219C430(side, 6, cid) opens the list picker over the buffer, yield
   step 2: 0x0219C534() result -> record pick: 0x022347B0 (board slot) or 0x02234880(desc, side, key, ref)
           (recorded-pick halfword layout: dispatch.pick_halfword_layout)

RESOLVER  0x0220D530(desc)                                       [NEW fact]
 |- cid==0x12EA and 0x021AC204(0x12FB) > 0 -> return 0, nothing else
 `- else 0x02204724(desc) [thunk -> 0x02204730(desc, 1, 2)]       [NEW fact engine.thunk_0x02204730... = engine.thunk_0x02204724]
      `- 0x02204730(desc, r1=1, r2=2)  SS-from-recorded-pick machine [NEW fact engine.ss_from_pick_0x02204730]
          1. x = desc[2]^desc[6]; 0x021B9EC0(x, cid) == 0 -> return 0   (SS gate, cid-aware, mode 8)
          2. i = 0 (cid is not 0x213C / 0x23E2)
          3. 0x022349B0(desc, 0, 0) == 0 -> return 0                  engine.pick_validate_0x022349B0
          4. key = byte1(0x02234904(desc,0)); h = 0x02234964(desc,0); card = 0x021A25E8(h)
                                                                      engine.pick_accessor_side_key_0x02234904, dispatch.pick_halfword_layout
          5. 0x021F0114(desc, x) == 0 -> (r7==0xF: 0x021C7258) return 0   [0x021F0114 -> 0x021AD870(x)]
          6. cid 0x12EA is not in the special-cid list -> fall to 0x02204840
          7. r6 = 0x021B1BE8(x, 1, card, key, 1)   zone/legality step, 0x220 B, SHA-pinned only
          8. r6 != 0 -> 0x0226925C(x, 0x021A25E8(h), 1, 2, cid<<16); return 1   summon.commit_r0_places_bit4_only_attributes
```

## How "either GY" is expressed

Not by the row word. The row handler 0x0223D6E0 passes an IMMEDIATE flags value 0xA to the shared GY worker
0x0223C4E8. By dispatch.criteria_handler_flags_word, bit 1 (0x2) = scan both sides and bit 3 (0x8) = Special
Summon action. By engine.split_pair_sum_0x0223C4E8, bit 1 makes the worker run 0x0223C1C4 twice with bit 0 (opponent's
side) toggled between passes. The sibling thunk 0x0223D6FC/0x0223D740 style (flag word from a pool) is a different
handler family; Monster Reborn's thunk is unusual in that it takes the row word as argument `e` and hard-codes the flags.
The picked card carries its own side bit (pick halfword bit 0, engine.pick_validate_0x022349B0), while the summon is
placed on `x = desc[2]^desc[6]`, the effect controller's seat (the commit's r0 is the placing side).

## SS legality gates on this path

Used: 0x021B9EC0(x, cid) (cid-aware, mode 8; both in the condition via 0x021F0384 and at the top of 0x02204730),
0x021AD870(x) via 0x021F0114 (both places), and whatever 0x021B1BE8 checks. NOT used by this card:
0x021B9ECC (the cid-blind r2=0 thunk) and 0x021B9ED8 (that one is a 0x1DD1 field-count test): neither appears
in any function on the path. They belong to the deck-SS machine. The path-extra gate 0x021BA410 (-> 0x021BA258) is only
reached for the hard-coded special cids, not 0x12EA.

## Activation narrative (every step cites address + fact)

1. Offer check: front 0x021F2BAC returns 0 if a Call of Darkness (0x12FB) is on the field [NEW mr_cls0_activation_cond_front;
   engine.field_cid_count_0x021AC204], else forwards to 0x021F03B4.
2. 0x021F03B4 requires the SS gates 0x021AD870/0x021B9EC0 to pass for the controller (engine.desc_xor_bytes_two_helpers_0x021F0384),
   then needs 0x02243FE0 > 0 candidates (engine.criteria_count_0x02243FE0).
3. Candidates come from criteria row 90: 0x0223D6E1 -> 0x0223C4E8(side, 0x12EA, 0, 0, 0x00010002, 0xA) = both graveyards,
   Special-Summon action [NEW mr_either_gy_criteria_thunk; engine.split_pair_sum_0x0223C4E8].
4. Target step 0x02235605: collects the same list (0x02243FA8), prompts, opens the mode-6 list picker, records the pick
   (dispatch.offfield_picker_sequence, dispatch.pick_halfword_layout).
5. Resolution: 0x0220D531 re-checks the Call-of-Darkness count (returns 0 and stops if present) else calls 0x02204724 ->
   0x02204730(desc,1,2) [NEW thunk_0x02204724].
6. 0x02204730 re-runs the SS gate, validates recorded pick 0 against the live board (0x022349B0), re-checks 0x021AD870,
   runs 0x021B1BE8, and on success commits through 0x0226925C with face-up/position arguments 1 and 2
   [NEW ss_from_pick_0x02204730; summon.commit_r0_places_bit4_only_attributes]. The resolver front returns 0 regardless.

## NOT proven

- What 0x021B1BE8 (0x220 B) checks, and which of its sub-gates can reject a revive; only SHA-pinned.
- What exactly 0x0223C1C4 (0x324 B) filters with `e` = 0x00010002 (catalogue/other KB call it "any monster"; not re-derived here),
  and the candidate-buffer entry format.
- 0x021AD79C / 0x021B9708's concrete conditions for this cid (existing facts say mode 8 = Special, nothing about contents).
- That the resolver returning 0 means "resolved" to the caller, and what the 0x12FB early return does to a chain (only the code
  path is decoded; the text on Call of Darkness says Monster Reborn's targets are sent to the GY, which this front does NOT
  implement visibly, so any such effect lives elsewhere and is not traced).
- Whether r1=1 / r2=2 mean face-up / "player chooses position" at the commit 0x0226925C; r2=2 is read that way only from
  dispatch.ss_from_list_position_mode (in-game confirmed there for another card), r1 is not separately proven.
- 0x021A25E8's return value type (card/locator word), 0x021C7258's effect (the r7 == 0xF side branch), 0x0219CA28.
- Anything about duel behaviour: no emulator evidence was gathered.

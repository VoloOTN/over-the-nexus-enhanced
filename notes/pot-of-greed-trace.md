# Pot of Greed (cid 0x12EC) - static trace of the engine path (decode only)

Printed text (scratch/ygoprodeck_cache.json): "Draw 2 cards."
All facts below are bytes-only; NO in-game claim. New facts in block.py are marked [new].

## Records (cardrows.py 0x12EC)
cls0[168] @0x0227F60C: +04 0x022065B9, +08 NULL, +0C 0x021F069D, +10 NULL, +14 NULL. No criteria-registry row listed.
No cost step and no target step: the card has no cost/target phase of its own.

## Call tree
| addr | size | catalogue | fact | role on this card's path |
|---|---|---|---|---|
| 0x022065B8 (resolver +04) | 0x40 | KNOWN | resolver.draw_n_is_a_per_cid_table (partial); [new] engine.draw_resolver_body_0x022065B8 | side=desc[+2]^desc[+6]; n=0x02206304(desc); n>0 -> 0x021D12F4(side,n); returns 0 |
| 0x021F069C (condition +0C) | 0x1C | KNOWN | dispatch.draw_condition_needs_the_count_row; [new] engine.draw_condition_body_0x021F069C | n=0x02206304(desc); n==0 -> 0; else 0x021BAE30(side,n) |
| 0x02206304 count provider | 0x2B4 | PARTIAL | resolver.draw_n_is_a_per_cid_table; [new] engine.draw_count_provider_hit_path_0x02206304 (hit path only) | bsearch 0x02022E44 in table 0x022704A4; Pot of Greed hits and returns s16 +2 |
| 0x022704A4 count table | 189x4 B | - | [new] engine.draw_count_row_pot_of_greed_0x022704A4 | exactly one row for 0x12EC: count = +2 |
| 0x02022E44 | ARM9 | KNOWN | effect_dispatch_tables.yaml:2561 (generic sorted bsearch) | key = cid u16 desc[+0] |
| 0x021D2D40 | 0x38 | PARTIAL | [new] engine.owner_cid_of_desc_0x021D2D40 | called by resolver and provider; result compared with 0x12DA (side flip). Pot of Greed's value of this not decoded for a live desc |
| 0x021BAE30 can-draw check | 0xAC | PARTIAL | [new] engine.can_draw_check_0x021BAE30 | gates: field-count of cid 0x178B (opp side), probes 0xDBF / 0x1885, then Deck count D >= 2 |
| 0x021AC0C8 | 0x13C | KNOWN | engine.field_cid_count_side_0x021AC0C8 | called from can-draw check |
| 0x021A151C | 0x34 | PARTIAL | timing.skip_next_battle_phase_node (mentions) | called with (s,0xB,0xDBF) - semantics here not decoded |
| 0x021A1550 | 0x34 | UNKNOWN | none | called with (s,0xB,0x1885,0) in the [0x0229DD14+0x48]==0 case |
| 0x021D12F4 draw primitive | 0xC | KNOWN | equip.draw (ANCHORED); [new] engine.draw_primitive_thunk_0x021D12F4 | thunk = 0x021D0950(side,2,1,0) |
| 0x021D0950 draw mover | 0x9A4 | PARTIAL | [new] engine.draw_mover_head_0x021D0950 (SHA-pinned, head only) | the actual draw; body beyond the head NOT decoded |
| 0x02023660 / 0x02234964 | | KNOWN | pick_halfword_layout / accessor facts | leaf helpers of 0x021D2D40 |

## What happens on activation (static reading)
1. Activation offer: the engine calls cls0 +0C = 0x021F069D (dispatch.draw_condition_needs_the_count_row, engine.draw_condition_body_0x021F069C).
2. It asks 0x02206304 for the count (engine.draw_count_provider_hit_path_0x02206304); the table row (engine.draw_count_row_pot_of_greed_0x022704A4) gives 2, so the condition is non-zero-count.
3. It then calls 0x021BAE30(side, 2) (engine.can_draw_check_0x021BAE30): returns 0 if a field/timing probe (cids 0x178B, 0xDBF, 0x1885 nodes) hits, else 1 iff the side's Deck count >= 2.
4. No cost (+10) or target (+14) step exists; +08 NULL.
5. On resolution the engine calls +04 = 0x022065B9 (resolver.draw_n_is_a_per_cid_table, engine.draw_resolver_body_0x022065B8): count is re-read as 2 (same provider), side = desc[+2]^desc[+6] (flipped only if 0x021D2D40(desc) == 0x12DA).
6. n=2 > 0 so it calls 0x021D12F4(side, 2) (engine.draw_primitive_thunk_0x021D12F4) -> 0x021D0950(side, 2, 1, 0) (engine.draw_mover_head_0x021D0950). Resolver returns 0.

## NOT proven
- Anything in 0x021D0950 past its head: that two cards actually move Deck->Hand, hand-size/limit, draw-lock probes (cids 0xE9A, 0x123B, 0x188C, 0x1BF1, 0x18D5, 0x14F2 are read but unexplained), events/animations.
- Meaning of the cids 0x178B/0xDBF/0x1885/0x12DA, of [0x0229DD14+0x48], of 0x021A151C/0x021A1550 results.
- The desc layout: that desc[+2]/[+6] are bytes giving the activating side (named only by the arithmetic).
- Who calls +0C/+04 and when (cls0 dispatch order, chain/spell-speed handling, discarding the Spell after resolve) - not traced in this session.
- The miss path of 0x02206304 (not taken for this cid per the table row).
- The 2nd criteria registry: cardrows reports no row; "no row" is not proven to mean none is required.
- Any in-game behaviour: AWAITING IN-GAME TEST.

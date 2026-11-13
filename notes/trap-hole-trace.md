# Trap Hole 0x12E4 - static trace (EU ov3), 2026-10-18

Printed text (scratch/ygoprodeck_cache.json via cardrows.py): "When your opponent Normal or Flip Summons 1 monster with 1000 or more ATK: Target that monster; destroy that target."

Static decode only. Nothing here is in-game evidence.

## cls0 record (cardrows.py): cls0[160] @0x0227F54C = {cid 0x12E4, s1 0x02204899, s2 0x021DB0A9, s3 0x021F2B6D, s4 0, s5 0x02234E3D}
(asserted byte-exact in block.py fact engine.trap_hole_summon_condition_0x021F2B6C). Slot roles: dispatch.cls_slot_roles (VERIFIED).

## Call tree
| addr | size | catalogue | KB fact covering it | what it does ON THIS CARD'S PATH |
|---|---|---|---|---|
| 0x021F2B6C (s3 cond) | 0x14 | HANDLER | NEW engine.trap_hole_summon_condition_0x021F2B6C | returns 1 iff desc[+4] in {7,8}; returns 1 (not >=2) so 0x0224AD94 also needs s2 to find a target |
| 0x021DB0A8 (s2 pred) | 0x120 | HANDLER | NEW engine.trap_hole_candidate_predicate_0x021DB0A8 | the whole targeting rule, see below; contains the 1000 constant |
| 0x02234E3C (s5 step) | 0x3C | HANDLER (52 records) | NEW engine.trap_hole_target_step_0x02234E3C | loops side 0..1 x zone 0..10, first s2-accepted (side,zone) -> 0x022347B0; returns 1 |
| 0x02204898 (s1 resolver) | 0xC | PARTIAL | counter.cls_tail_is_a_target_template_zone_must_match (mentions); shared with MST | `push {r3,lr}; bl 0x02204674; movs r0,#0; pop` : calls the targeted-destroy body |
| 0x02204674 | 0x44 | PARTIAL | donor_card_technique (Ring of Destruction), "destroy it, then" two-phase protocol (effect_dispatch_tables ~2989) | targeted destroy body (not re-decoded here) |
| 0x021D6E40 (zone predicate) | 0x4EC | KNOWN | card.safe_zone_either_side_controller_relative; continuous_stat_engine.yaml:497 (bit meanings) | called by s2 with flags 0x416 |
| 0x021B8014 | 0x14 | KNOWN | engine.stat_recompute_readback_0x021B8014 | returns recompute out+0x10 (a stat accumulator); the 0x12E4 arm compares it with 1000 |
| 0x021B803C | 0x14 | PARTIAL | stat.recompute (mentions) | out+0x14; used by sibling cid 0x124F's arm, not by 0x12E4 |
| 0x021BA404 | 0xC | UNKNOWN | none | used by sibling cid 0x15C6's arm only |
| 0x021AFD3C | 0x4E0 | PARTIAL | notes only ("0x400 = targetability check") | reached from 0x021D6E40 because flag 0x400 is set |
| 0x0224A8C0 | 0x64 | KNOWN | dispatch.cls2_slot8_is_candidate_filter | s2 invoker used by s5 |
| 0x022347B0 | 0xD0 | PARTIAL | dispatch.slot5_target_picker | per-candidate target recording/picker called by s5 |
| 0x0224AD94 | 0xBC | KNOWN | dispatch.cls2_invoker (ANCHORED), dispatch.slot3_runs_at_admission | runs s3; consults s2 only when s3 == 1 |

## 0x021DB0A8(desc, side, zone) in order (r4=desc, r5=side, r7=zone)
1. `bl 0x021D6E40` with r3 = 0x416 (pool 0x021DB1B4); 0 -> return 0. Flags decoded: &3 == 2 (side must differ from desc[6]^desc[2]); &4 (zone u16 at 0x0229ACD0 != 0, a card is there); &0x70 == 0x10 (zone < 5, monster zone); &0x400 -> 0x021AFD3C must be non-zero. Other bits not decoded.
2. desc[4] must be 7 or 8 (`ldrb; adds #0xF9; cmp #1; bhi`).
3. w = desc[+0x20]. s = bit 9, f = bit 16. Reject if desc[2] == (s ^ f). Require side == s. Require zone == bits 10..13 of w. This is the "opponent summons" test (trap owner desc[2] vs summoner) and the "that monster" identity (zone from the event word).
4. Board zone word at 0x0229AC94 + (side&1)*0xB3C + 0x34 + zone*0x14: ((bits 23..30)<<1 | bit 14) must equal w & 0x1FF (instance id still in that slot).
5. cid switch on u16[desc]: 0x12E4 (bge arm @0x021DB15C) calls 0x021B8014(side, zone) and returns 1 iff result >= [sp] - 0x2E = 0x416 - 0x2E = 0x3E8 = 1000. Sibling arms: 0x124F: 0x021B803C <= 1000; 0x1250: 0x021B8014 <= 1000; 0x15C6: 0x021BA404 verdict; unlisted cid -> 1.

## How the event word reaches desc[+0x20] and why code 7/8
- 0x02267A38 (NORMAL, passes 7) and 0x02268B7C (FLIP, passes 8) both do `strh side->[0x02298A28+2]; strh zone->[+4]; bl 0x02265768` (disasm 0x02267A10..A38, 0x02268B5A..B7C). Fact summon.trigger_is_a_membership_list (VERIFIED) states these codes.
- 0x02265768 calls 0x02265470 (PARTIAL), which builds a word from the global summon record 0x02298A28: bit 9 = rec[2]&1, bits 10..13 = rec[4]&0xF, bit 14 = rec[8]&1, bit 15 = rec[6]&1, bit 16 = (rec[0] != rec[2]), bit 17 = rec[0x10]&1, low bits from rec[0xC] (read from disasm 0x02265470..0x022654EE; not KB-proven). The post at 0x02265CA8 passes that word as r1/r2 to the register-prim 0x021D3168 (dispatch.slot3_runs_at_admission) which stores it in desc[+0x20] (`str r7,[sp,#0x20]`@0x021D31B6) and runs COMMIT 0x021EDA08 -> 0x0224AD94 (VERIFIED chain). The selector there is hard-coded 1 (cls1) per summon.trigger_is_a_membership_list, so THIS post does not itself reach a cls0 trap.
- event.packed_word_layout (VERIFIED): desc[+4] = event code, desc[+2] = side bit 31.
- Miss-timing: 0x021EE0E0 (timing.miss_timing_test, VERIFIED) lists codes 7,8,9 among those whose desc[+0x20]&0x1FF is checked against the trigger-event log; a 'You can' body asks it. Whether a cls0 trap offer goes through that is not proven.

## Narrative: opponent summons into this Set trap
1. Opponent Normal Summons (0x02267A38 code 7) or Flips (0x02268B7C code 8): record 0x02298A28 filled, 0x02265768 called. [summon.trigger_is_a_membership_list]
2. 0x02265470 packs side, zone, instance id etc. into a word. [disasm only]
3. A descriptor with desc[+4] = 7 or 8 and desc[+0x20] = that word is presented to the trap's cls0 record found by find_event_handler 0x0224A118 (selector 0 table). [dispatch.find_event_handler; the selector-0 poster for this is NOT proven]
4. s3 0x021F2B6C returns 1 because desc[+4] is 7/8. [NEW fact]
5. 0x0224AD94 sees 1, so runs s2 as a candidate filter over side x zone (via 0x0224A8C0). [dispatch.cls_slot_roles]
6. s2 0x021DB0A8 accepts only the (side, zone) that is the opposing-side monster zone <5 from the event word, whose instance id matches, and whose stat out+0x10 >= 1000. [NEW fact]
7. If accepted the trap is offered; on activation s5 0x02234E3C records that candidate through 0x022347B0, returning 1. [NEW fact]
8. s1 0x02204899 -> 0x02204674 performs the targeted destroy. [counter.cls_tail_is_a_target_template_zone_must_match, PARTIAL]

## NOT proven
- Who builds the selector-0 descriptor for a Set trap on a summon (step 3), and how desc[+0x20] reaches it; 0x02265768 posts only cls1. Candidates not yet traced: other callers of 0x0224AD94 (0x021D333E/0x021D33A4 in the event-queue drain loop at 0x021D32A0.. that reads queue 0x0229A37C, 0x021E50FA, 0x021E561A, 0x021E9262, 0x021F0BB2).
- That out+0x10 is ATK (KB says only "two stat accumulators", out+0x14 the other).
- Bit 16/17 meaning of the word, what 0x021AFD3C tests, undecoded flag bits of 0x416.
- The destroy body 0x02204674 and picker 0x022347B0 internals; the "1 monster" count and the 'Target' timing vs chain.
- Whether 0x021EE0E0 miss-timing applies to this offer; AI/CPU behaviour; anything in-game.

## Addendum 2026-10-18: who posts the descriptor (RESOLVED statically)
The "selector-0 poster" question is closed by three VERIFIED facts (decode only, no in-game claim):
- `engine.trap_offer_call_chain_0x0224B644`: capability enumerator 0x0224BC40 zone 5..10 arm (0x0224BEB4) -> `0x0224B644(cid, side, zone)` -> (race 0x18 = Trap) -> `0x021EDD38`.
- `engine.field_trap_offer_builder_0x021EDD38`: builds the 0x24-byte descriptor (cid, side, zone, packed ref, desc[+4]=0, class 0) and calls `0x021EC93C`.
- `engine.offer_loop_over_pending_events_0x021EC93C`: its tail LOOPS over the pending-event queue (0x0229A37C, length [0x0229AB7C+0x30]); for each event sets desc[+4] = event code and desc[+0x20] = event word, then pre-check `0x021ECC6C` and commit `0x021EDA14` -> `0x0224AD94` -> the card's +0x0C. So Trap Hole's condition is tested once per queued event with desc[+4] = that event's code.
Still open: who ENQUEUES the summon event into 0x0229A37C (the summon evaluator 0x02265768 receives codes 7/8 but the enqueue site is not yet identified), what `0x021ECC6C` checks, and the body of `0x021EDA14`.

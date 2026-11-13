# Eclipse Wyvern — clause 1 LIGHT/DARK Attribute filter

User report 2026-10-19 (verbatim): "One last bug, Eclipse Wyvern still lets us target
all Attributes instead of just light and dark. Can we fix that"
Confirmed by user: clause 1 (Deck banish picker); seen on BOTH rom_redox_c3.nds and
rom_all_patches.nds; acceptance = no non-LIGHT/DARK Dragon appears in the list.

Clause 1 (ygoprodeck_cache): "If this card is sent to the Graveyard: Banish 1 Level 7
or higher LIGHT or DARK Dragon-Type monster from your Deck."
Clause 2 must not regress. Dragon Rulers share H6 0x021C71C8 (calls EW stub for non-rulers).

## Confirmed
- The old shipped deviation #2 (memory otn-eclipse-wyvern-shipped, module docstring
  lines 37-46): criteria row {0x1859, 0xFFFF, 0x0223CAD9, 0x0002, 0x085C} = Dragon,
  attr 0, Lv>=7. One attribute per row -> no LIGHT|DARK OR as data.
- Precedent: patch_shiens_dojo PART I — clone generic handler 0x0223CAB4 with the
  callback literal swapped for an ov5 OR-predicate (KB counter.criteria_handler_abi).

- NDS Deck handler 0x0223CAD8 (stock ov3, scratch/dis.py): push{r1-r3,lr}; [sp]=row+8
  (u32 flags|extra<<16), [sp+4]=2 (mode), r0=ctx, r1=row cid, **r2=0 (NO callback)**,
  r3=0; bl worker 0x0223BC3C.
- Worker 0x0223BC3C calls the callback at 0x0223BDFA (`blx r4`) only if r2!=0, with
  r0=side, r1=0xD, r2=index, r3=row cid, [sp]=&candidate word, [sp+4]=the r3 arg;
  result 0 = reject (0x0223BDFE beq skip).
- 3DS EW (cid 0x26E5) row 1572 = {0xFFFF, h 0x004B0518, 0x085C0002}. Handler 0x004B0518
  = same shape as NDS 0x0223CAD9 (flags word, mode 2) BUT r2 = callback 0x003F7F50 and
  r3 = &6. Callback = `(1 << get_attribute(cid)) & *[sp+4]` -> mask 6 = LIGHT(1)|DARK(2).
- NDS native twin callback: **0x0223C8DD** (body 0x0223C8DC): cid = [[sp+8 after push]]
  &0x3FFF, bl get_attribute 0x0202ABC8, return (*[sp+4] & (1<<attr)) != 0.
  Literal 0x0223C8DD appears once in ov3 (0x02242814), used by bespoke handler
  0x022427D0 (mask from a live field card, mode 0) — no row-driven handler uses it.
- => FIX = 30 B clone of 0x0223CAD9 with r2 = 0x0223C8DD, r3 = &6 on its own stack.
  No new filter logic.

## Ruled Out
- A pure-data fix (swap the row's handler to an existing one): no native row-driven
  handler passes 0x0223C8DD (literal scan, one hit, bespoke).

- EW is already ov5-dependent (cls2 +04 = CAVE_EW_RECORD), so the clone went to ov5:
  CAVE_EW_ATTRH 0x023A75D0 (0x30 reserve, 36 B used incl. pool), CAVE_FREE -> 0x023A7600.
  check_allocations: [OK], ledger in sync.
- Built clone disasm (capstone + assert_thumb1_only): push{r1-r3,lr}; [sp]=row+8; [sp+4]=2;
  [sp+8]=6; r3=sp+8; r0=ctx; r1=ldrh row; r2=lit 0x0223C8DD (pool @0x023A75F0); bl 0x0223BC3C.
- PART C2 in patch_eclipse_wyvern.py: POP_NEW handler = CAVE_EW_ATTRH|1, main installs it,
  verify() asserts the cave bytes + row.
- KB: dispatch.criteria_attribute_mask_callback (VERIFIED; author_facts --check 720/0/88).
- ⚠️ Base ROM: rom_redox_c3.nds now FAILS both EW and Rulers verify() — not from this change.
  patch_dragon_rulers.py was edited 18:52 by the sibling baby-banish session (H6/H7/H8
  `bmi` -> `lsrs r0,#2 ; bne`), so _h6_prev no longer recognises redox_c3's H6 stub.
  The delta is therefore built on rom_rulers_baby_ban.nds (= redox_c3 + that fix). The two
  changes share no bytes (theirs: H6/H7/H8, no new slots; mine: EW criteria row + new slot).
- BUILT: _build_ew_attr.py -> data/over_the_nexus/working/rom_ew_attr.nds
  sha256 30c9b0ef5679e8fb1349c6664200c3f8b71b788f570cbd9ea41ff95e23242c4e
  verify(): patch_eclipse_wyvern PASS, patch_dragon_rulers PASS (static only).
  NOT in steps.STEPS (module edit will reach the chain on the next EE build — the module is
  already a step; tell the user). AWAITING IN-GAME TEST.

- 2026-10-19 user: "Perfect! Ship it!" = SHIP APPROVAL. They did not explicitly say the in-game
  test passed, so it was not recorded as confirmed until the follow-up:
  IN-GAME CONFIRMED BY USER 2026-10-19: "Yes, I tested rom_ew_attr.nds in-game and only LIGHT/DARK
  Dragons were offered." EW is already in steps.STEPS + SHIPPED;
  the chain build was first BLOCKED by the permission check; user then said "You run it".
- CHAIN BUILT 2026-10-19: EE build 119/119 -> rom_all_patches.nds sha256
  f7a2b1605aef90a05a740e6a49a45f0d5e8b913c83d9eb321c00bfab455b8d4c (129720968 B); content
  checked: EW row handler 0x023A75D1 + cave bytes match; EW + Rulers verify PASS; sweep
  100 passed / 0 failed. Previous chain ROM kept as rom_all_patches.pre_ew_attr.nds.

## Open Questions
- none static. Live path: the row's handler is what the count probe 0x02243FA8 and the
  picker both dispatch through (that is how Dragon/Lv>=7 already filters in-game).

## Next Experiment
- In-game oracle in _build_ew_attr.py docstring (mixed-Attribute Lv7+ Dragon Deck).

# Raiden, Hand of the Lightsworn — findings

Scope (user, 2026-09-27): ALL clauses. Donor: Rogue Doll 0x0FD2 (user-chosen). Set code: ov5
16-entry Lightsworn list (user). Ignition requires Deck >= 2 (user). Plan:
`~\.claude\plans\raiden-hand-of-the-sorted-hoare.md`.
Status: ALL 10 ORACLE ITEMS IN-GAME CONFIRMED BY USER 2026-09-27 (build sha 51c044bf...ab695a).
SHIPPED 2026-09-27: build 2 (set code 0x33 in the ARM9 list in place, Raiden replacing Lightsworn Sabre 0x1E45; single-card sha e89ef782...72bf2f) in-game confirmed by user 2026-09-27 incl. the deck editor. steps.STEPS + _verify_all_patches.SHIPPED; EE build 79/79 sha b3219b36...86dff44; sweep 64 passed, 1 failed = pre-existing patch_ninishi. Was: BUILT, AWAITING IN-GAME TEST. `_build_raiden.py` -> rom_raiden.nds sha256
51c044bfddb785a76840cd6a84515ffd6839a2d9df354a6a1e99535276ab695a, verify 14/14. NOT in steps.STEPS.

Printed text (ygoprodeck 77558536), LIGHT Warrior Tuner Lv4 1700/1000:
> During your Main Phase: You can send the top 2 cards of your Deck to the GY, then if any
> "Lightsworn" monsters were sent to the GY by this effect, this card gains 200 ATK until the end of
> your opponent's turn. You can only use this effect of "Raiden, Hand of the Lightsworn" once per
> turn. Once per turn, during your End Phase: Send the top 2 cards of your Deck to the GY.

## Confirmed (this session)
- Raiden absent from NDS (konami_id_to_card_name.tsv) and 3DS (CARD_Indx_E/CARD_Prop scan: only
  the 15 NDS Lightsworn cids 0x1DA7..0x2194).
- Jain 0x1DA7 End-Phase mill (subagent, donor_scan + disasm of rom.nds): registry row 255 @0x0228E9D8
  = {0x02253EC9, 0x1DA7} (turn-player-only poster); cls1 rec 804 @0x0228AC34 = {0x1DA7, 0x022286AD, 0,
  0x0224A115, 0, 0}. Resolver 0x022286AC: default `movs r4,#3` @0x022286CA; cid switch -> N=2 for
  0x1DA7/0x1DDC/0x1E74/0x2193 (@0x02228738), N=4 for 0x1DAF; then 0x021D2148(desc, desc[2], r4) @0x02228744.
  Unlisted cid mills 3 -> Raiden needs an ov5 wrapper for N=2.
- Deck top = [0x0229AC94 + side*0xB3C + 0x304] & 0x3FFF (Magical Merchant 0x0221821C disasm
  @0x022182B6..C6); Deck[1] at +0x308; deck count [0x0229ACA4 + side*0xB3C].
- Lightsworn set code 0x33 -> thunk 0x02023BB8 -> list 0x0209C94A, 15 sorted u16, `movs r2,#0x0F`.
- Lightsworn-ish ATK table 2 0x0226E480 has +200/0 rows: 0x1DF2, 0x1E09, 0x216D, 0x2302 (ROM read, subagent).

- Rogue Doll 0x0FD2 donor gate: donor_scan VERDICT CLEAN; its 4 ARM9 data hits (0x0209D6F2,
  0x0209E3E0, 0x0209E6F0, 0x020A13E2) are monotonic numeric ramps 0x0FCD..0x0FD6 interleaved with
  +6-step values (e.g. 0246 0FD6 024D 0FD5 ...) and their mirrors — interpolation/trig tables, not cid keys.
- r4 IS the ATK accumulator: already VERIFIED in KB stat.neptune_pair_leaf_0x221D (closes the ASSUMED
  below). Kind 0x12 via 0x021C479C is in-game confirmed by user on Brilliant Fusion C3 (KB card.brilliant_fusion_c3).
- Built card_prop (decoded): Tuner Monster 33, LIGHT, Warrior, Lv4, 1700/1000.
- KB facts added (author_facts --check 506 PASS 0 FAIL): resolver.lightsworn_endphase_mill_0x022286AC,
  setcode.lightsworn_0x33_thunk, stat.table2_flat_delta_kind12 (VERIFIED), card.raiden (UNVERIFIED).
- Slots: ov5 CAVE_LIGHTSWORN_GROUP 0x023A1E18, CAVE_RAIDEN_ONFIELD/EP/COND/COST/RES 0x023A1E38..0x023A1FE8
  (CAVE_FREE -> 0x023A1FE8); PHANTOM_CLAIMS raiden: cls1 0x0ECB, registry_row 0x0ECB, cls3 0x0EBC.
- +200 ATK node, PROVEN statically (scratch.dis this session): rider walker reads node kind low nibble
  into r6 (@0x021B5FC8), key into r5 (@0x021B5FC0), param node+4 into [sp+0x80]. Kind jump table
  @0x021B6092: kinds 1,2,4 -> 0x021B60AC (skip if [sp+0x68]=[sp+0x14]&2 set), kind 3 -> 0x021B60B6.
  0x021B60B6 binary-searches table 2 0x0226E480 (0x71 x 6) by key; on hit: atk delta muls by param
  ONLY if delta == +-1 (sentinel), else `adds r4,r4,r2` flat; def into [sp+0x20]; then 0x021B6BCA ->
  bl 0x021B7692 (common next-node). Table-2 row 96 = {0x216D, +200, 0}; 0x216D not in table 1.
  => node {key 0x216D, kind 0x12} = flat +200 ATK, param ignored. Kind 2 low nibble matches Weapon
  Change 0x175D's kind 0x12 (note-level precedent). r4 = ATK accumulator: by that precedent (ASSUMED).
- Lightsworn thunk 0x02023BB8 PROVEN (scratch.dis): `ldr r1,[pc,#4]` -> LIST_LIT @0x02023BC0 =
  0x0209C94A; `ldr r3,[pc,#8]` = 0x02022E15 (sorted-u16 search); COUNT_IMM @0x02023BBC = 0x220F; bx r3.
  has_set_code ptr[0x33] = 0x02023BB9. Literal 0x0209C94A appears ONCE in arm9 (0x02023BC0), never in
  ov3 -> no sibling reader (unlike Psi-Reflector's 0x6E/0x6F). Next list starts 0x0209C968 (0x0D6B).
- Phantoms (scratch/raiden_pick_phantoms.py, stock AND rom_all_patches): 0x0ECB is a whole phantom
  End-Phase card: one cls1 row {0x0ECB, 0x022082A5, 0,0,0,0} (stock idx 54 / chain 48) + registry row 100
  {0x02253EC9, 0x0ECB}; no card_prop, unclaimed. cls3 phantom 0x0EBC (chain idx 34; donor sorts to 38).
- Jain resolver 0x022286AC guards (disasm): entry = [0x0229AC94+(side&1)*0xB3C+0x34+slot*0x14];
  ref = ((w<<1)>>24)*2 + ((w<<17)>>31) must == desc[+0xC]; zone word [..+0x44] bit 26 must be clear;
  then 0x021D2C1C(desc) != 0; all failures return 0.
- has_set_code 0x020240D8 is Thumb (push {r3,lr}; cmp r1,#0x70; blx table[r1]) -> (cid, code).
- Deck count = u32 `ldr` at player+0x10 (0x0229ACA4) (Magical Merchant @0x02218274).
- 0x021D2C1C(desc) is Thumb, reads desc[+0xC] locator (@0x021D2C20).

## Ruled Out
- Set code 0x33 list in ov5 (build 1): deck editor has no ov5 -> Charge / Solar Recharge / Judgment Dragon
  showed "Enchanted Javelin" (user 2026-09-27). Fixed in build 2 by the in-place ARM9 swap (Sabre out).
- A "what was milled" record: none exists (0x021D2148/0x021D2094 return nothing). Peek before milling.

## Open Questions
- DECK-EDITOR REGRESSION (user report 2026-09-27, verbatim): "charge of the light brigade and solar
  recharge and judgement dragon no longer "point" to the lightsworn table in the deck editor and show
  "enchanted javelin". It's not affecting the duels but it does affect the deck editor (where ov5 is not
  loaded!)". Interpretation pending user confirmation. User direction: keep the list in ARM9; possibly drop
  a Lightsworn spell/trap from the set to make room.

- Stats are the only engine path not proven by disassembly: whether type 33 (Tuner Monster) is offered a
  cls3 ignition. Native type-33 effect Tuners carry cls3 records, and Scrap Raptor 0x0FF6 (type 33 ignition)
  is AWAITING TEST too.
- Deck-editor has_set_code(0x33) outside a duel reads the ov5 address (same exposure as Psi-Reflector 0x6E).

## Next Experiment
- User in-game test, NORMAL duel, oracle items 1-10 in _build_raiden.py's docstring.

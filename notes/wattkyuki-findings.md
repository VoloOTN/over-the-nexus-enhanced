# Wattkyuki → St. Joan 0x1458 — findings (2026-10-05)

Scope (user, 2026-10-05): WHOLE CARD. Donor St. Joan 0x1458 (effectless Lv7 Fusion,
re-typed to Synchro per the Junk Speeder recipe). Watt set-code slot by displacing
Wattcannon 0x232A. Plan: `~/.claude/plans/wattkyuki-twinkling-hejlsberg.md`.

Printed text (scratch/ygoprodeck_cache.json, id 67752972, Synchro Lv8 LIGHT Thunder 1600/1700):

> 1 "Watt" Tuner + 1+ non-Tuner Thunder monsters
> This card can attack directly. When this card inflicts battle damage to your opponent
> by a direct attack: You can shuffle both 1 "Watt" Tuner from your GY and 1 face-up
> non-Tuner Thunder monster you control into the Deck, and if you do, Special Summon 1
> "Watt" Synchro Monster from your Extra Deck, except "Wattkyuki". You can only use this
> effect of "Wattkyuki" once per turn.

- C0 materials / C1 direct attack / C2 direct-damage trigger (shuffle 2 → SS Watt Synchro ≠ self), HOPT.

## Confirmed
- Wattkyuki exists in neither NDS nor 3DS (inherited from wattuna-findings; name scan there).
- donor_scan 0x1458 this session: ENTANGLED — binding = fusion recipe A[58] @ov3 0x02270D64
  + one unclassified u32 @ov3 0x021E2488 (also listed as a code-region encoding). Name slot
  'e' = 8 B (< 9 for "Wattkyuki") → needs card_text re-emit.
- Remaining Lv6+ effectless Fusions: all 6 "clean" ones spent; Twin-Headed Thunder Dragon
  0x120B went to Junk Speeder (pool note is stale on that).

- **St. Joan's unclassified hit ov3 0x021E2488 is NOT a per-cid gate** (disasm this session):
  `0x021E247C push{r3,lr}; ldr r3,=0x00001458; bl 0x021D6E40; pop{r3,pc}` — 0x1458 is the
  r3 MASK argument to the zone-mask wrapper 0x021D6E40 (siblings use 0x1414 @0x021E2402,
  0x1472 @0x021E246E). Coincidental value, no cid compare.
- **No per-cid arm can select 0x1458** (`scratch/cid_reach_probe.py` this session):
  Synchro material predicates 0x02248000-0x0224A000 → 0 literals within ±0xFF.
  Proper-summon tree 0x02265700-0x02266000 → 4 literals, all closed by disasm:
  0x13B5 @0x022657D4, 0x154B @0x022657DE, 0x1488 @0x02265926 are exact `cmp/beq`;
  0x14BA @0x02265D46/4E feeds stack slots [sp+0x84]/[sp+0x80] = 0x14BA+0x39 = 0x14F3; the other
  slots are 0x1D5E-0x8E=0x1CD0, 0x1D5E+0x2F=0x1D8D, 0x2040+0x76=0x20B6, 0x80000000. None = 0x1458.
- Wattcannon 0x232A: zero references in finished_patches/ and check_allocations.py (grep this session).

- **Native non-Tuner leaf for the Watt Synchros = 0x02248FD8, "non-Tuner race == the SYNCHRO's race".**
  Offline walk this session (scratchpad tree_walk.py = scratch/thumbemu.py over STOCK ov3+arm9 images,
  start 0x02248AB8, r5 = cid): 0x2477 Watthydra and 0x230F Wattchimera both reach 0x02248FD8 → 0x02249010,
  first BL = RACE_GETTER 0x0202ABB8. 0x1458 and 0x18FA (stock) fall to 0x022494C4 = `movs r0,#1` (accept).
  Disasm: hand (r7!=0): race(material cid from [0x0229AC94 + side*0xB3C + idx*4 + 0x124] & 0x3FFF) ==
  race(r5); field (r7==0): `0x021B8E30(r6, [sp+8], race(r5))` (live-race check); → b 0x02248F88 with r4.
  ⇒ With card_prop race = Thunder, routing 0x1458 here gives "non-Tuner Thunder" exactly — no new logic.

- **Native Tuner leaf for the Watt Synchros = 0x02248A40** `adds r0,r4,#0 ; bl 0x02023EF4 (is-Watt thunk) ;
  pop {r1-r7,pc}` (r4 = material cid set at 0x022485CE). Offline walk of OUTER's per-Synchro switch from
  0x02248660 (r5 = cid): 0x2477 and 0x230F both end `bl 0x02023EF4` from 0x02248A42. 0x1458 ends at the
  allow leaf 0x02248A70 `movs r0,#1 ; pop`.
- **C0 = ROUTING ONLY, two private 4-byte detours (LSD `mat_stub` shape), no shared-gate chain:**
  * OUTER site **0x02248660** `ldr r1,=0x221A ; cmp r5,r1` (7f49 8d42): r5 = Synchro cid; 0x1458 → `bx 0x02248A41`,
    else replay both instructions + `bx lr` (flags survive bx). 0x02248662 is not a branch target
    (capstone scan of all ov3 branch targets this session).
  * THIRD site **0x02248AFA** `ldr r0,=0x1E9A ; cmp r5,r0` (8948 8542), on 0x1458's THIRD path
    (0x02248AB8 → … → 0x02248AFA → … → default 0x022494C4): 0x1458 → `bx 0x02248FD9`, else replay.
    0x02248AFC is not a branch target. This is downstream of LSD's 0x02248AB8 detour, so LSD (donor 0x18FA,
    which leaves at 0x02248AB8) is untouched.
  * Leaf 0x02248FD8 ends `b 0x02248F88` = `adds r0,r4,#0 ; b 0x022494C6` (THIRD epilogue); it overwrites r4
    on both arms, so the r4=0x2003 left by the walk is harmless. Stub touches only r0/r1 + LR (THIRD/OUTER
    pushed LR in their prologues).
  * Why not the shared gates: 0x022485D8 chain JSP→DR_C1 is pinned byte-exact by both
    patch_junk_speeder.verify and patch_dragunity_remus.verify; 0x02248AAC is pinned by patch_azure_eyes.
  * Stock vs rom_all_patches.nds (this session): 0x02248660, 0x02248AFA, 0x02248FD8(+0x4C), 0x02248A40,
    0x02248A70, 0x02248F88 all IDENTICAL. No code/notes reference either site (grep).
  * Wattkyuki is not in the named-material table 0x02275B04 → must assert in verify (else OUTER never reaches 0x02248660).

### BUILD 1 (C0 + C1 + identity) — 2026-10-05, AWAITING IN-GAME TEST
- `patch_wattkyuki.py` on rom_all_patches.nds (not stale: chain 14:52 > newest module 14:47) →
  `rom_wattkyuki.nds`. verify 13/13. check_allocations --emit clean (384 ov5 slots, 413 claims).
- Caves: CAVE_WK_OUTER 0x023A4950, CAVE_WK_THIRD 0x023A4970 (0x1C B each, Thumb-1 asserted, disassembled:
  pools 0x1458/0x221A/0x02248A41 and 0x1458/0x1E9A/0x02248FD9 — odd targets, no POP).
- **Execution proof** `scratch/wattkyuki_route_equiv.py`: thumbemu over built vs chain ov3+ov5+arm9, every cid
  0x0E00..0x25FF through OUTER 0x02248660 and THIRD 0x02248AB8 → exactly ONE cid differs per tree, 0x1458,
  now exiting at Watthydra's exits (0x02248A40 / 0x02248FD8; stock 0x02248A70 accept / 0x022494C4 accept).
- Race field (card_prop [+4]<<0xA>>0x1B, what RACE_GETTER reads) = 19 = Watthydra's.

### C2 movers — PROVEN by disassembly this session (Phase 0 item 7 closed)
- **Field → Deck = `0x021CF590(desc, side, slot)`** = `0x021CDD4C(desc, 1<<(side*16+slot), 0x0D, 0)`
  (disasm 0x021CF590..0x021CF5A2). Native user: Gladiator Beast tag-out cost **0x021EAD71** (cls1 +10 of
  11 GBs + Gyzarus 0x1DC1 + Gaiodiaz 0x1C86): phase [0x0229AAFC+0x7C]==0xA → `0x021CF590(desc, desc[2], desc[3])`
  (self from field to Deck), state++ → return 0; ==0xB → `bl 0x021D26CC`, return 1. Sibling mask form
  0x021CF5BC(desc, mask) = 0x021CDD4C(desc, mask, 0xD, 0).
  * 0x021CDD4C is QUEUED, not immediate: copies the 0x24 desc to 0x0229DE34, ORs the mask into
    [0x0229C294+0x7C], dest → [0x0229DE14+0x44], flags → +0x48, [0x0229DE14+0x18]=1. The move happens after
    the phase returns → the shuffle must be in a LATER phase (exactly what the GB cost does).
  * Extra-Deck types with dest 0x0D: the same 0x021EAD71 (fixed 0x0D) is used by the EXTRA-DECK Fusions
    Gyzarus/Gaiodiaz ("return to the Extra Deck") → the queued processor routes Extra types to 0x0C.
    Structural inference from shared native use — NOT traced.
- **GY → Deck = `0x021C6A0C(desc, side, ref, 1)`** → 0x021C6A18(desc[2], side, ref, 1): requires ref in GY
  (0x021A2510 ≥ 0) else returns 0; dest = 0x0C if 0x0202307C(cid) (Extra type) else 0x0D; banish-replacement
  check 0x021BAB5C → 0x021C7118; else 0x021C69D0(side, 0xE, ref, side, [sp]=dest, ...) + event 0x26; returns 1.
  Immediate. ⇒ **KB `equip.atk_grant` ("ATK-grant applier @0x021C6A0C") is WRONG** — to be corrected_by.
- **Shuffle = `0x021D26CC()`**: for both players, if [0x0229AC94 + p*0xB3C + 0x120] bit 3 ("Deck received
  cards") → queue cmd 0x55 (the same shuffle command 0x021D269C builds). Native users: Pot of Avarice phase
  0x7E (after its GY→Deck moves), GB cost phase 0xB. The KB's "turn/phase bookkeeping" label for it
  (effect_dispatch_tables 0x021E9038 fact) is wrong.

### C2 picker plumbing — PROVEN by disassembly this session
- Picker = `0x0219C430(side, 6, cid, param)` (mode 6 = generic pick, 88 native callers); candidates come
  from the cid's criteria row via 0x02243FA8(side, cid, param) → the row's HANDLER picks the zone.
- Recorder 0x02243B2C(side, zone, index): card word → 0x02299458[n] (u32), u16 0x02299908[n] =
  `side | zone<<1` (disasm 0x02243B32..0x02243B70). **0x0219C534() returns the picked candidate's ZONE
  CODE** (`ldrh [0x02299908 + idx*2] ; lsl 0x1A ; lsr 0x1B`) — the KB fact dispatch.pick_readback_is_a_locator_pointer
  says it "returns a CID": WRONG. 0x0219C510() → &card word (KB correct).
- Field walker 0x0223C938 loops r6 = 0..9 and records (side, r6) → for a field pick zone code == SLOT
  → feeds 0x021CF590(desc, side, slot) directly.
- GY ref = key of the card word: `((w>>23)&0xFF)<<1 | (w>>14)&1` — exactly what 0x021A2510(side, ref)
  compares against each GY entry (disasm 0x021A2528..0x021A2538) → feeds 0x021C6A0C(desc, side, ref, 1).
- Criteria word: bit 15 = Tuner (KB), low 0x2 = Monster; NO non-Tuner bit — predicate callback
  (KB counter.no_nontuner_bit; 0x02243305 = set-code AND not Tuner).

### C2 design inputs — PROVEN by disassembly this session
- No native "face-up monster you control" criteria handler: the only field-loop handler 0x0223C939 (18 rows,
  all Fusion spells) gates slots on the Fusion predicate 0x022321D8. → own ov5 field loop.
- Field tests: occupied = 0x021A36EC(side, slot) != 0 (→ 0x021A36F8 with r2=1); face-up = word
  [0x0229ACD0 + side*0xB3C + slot*0x14] != 0 (Tyranno/Hyper Librarian); Tuner = 0x021A1C7C(side, slot)
  (card word 0x0229ACC8+.. → 0x02023110, rider fallback); live race = 0x021B8E30(side, slot, race) =
  bit `race` of 0x021B8D90(side, slot).
- GY→Deck selection = Pot of Avarice's handler 0x0223CBB0: GY builder 0x0223C4E8(side, cid, pred, list,
  [sp]=word, [sp+4]=flags 0). Set-code predicate 0x0223C824: cid = [[sp]]&0x3FFF, code = [[sp+4]] (u32).
- Extra Deck SS selection = Cyber-Stein's handler 0x0223D640: 0x0223BE40(side, cid, pred, list, [sp]=word,
  [sp+4]=0xA). Resolver 0x0220AF0C commit: 0x0226925C(side, 0x0219C510(), 1, 2) with [sp]=cid<<16.
- Avarice/Ojamassimilation move bracket: CHAIN_PUSH 0x021D28A4 → 0x021C6A0C → CHAIN_POP 0x021D2964 +
  0x021D26CC, flag in [0x0229AAFC+0x74]. Picker: msg 0x0219A818(side,0x30) then 0x0219C430(side,6,cid,
  0x02234E78(desc)) (NAST).
- Phantoms (chain ROM, unclaimed): **0x0E9B** owns exactly one cls1 row + one criteria row, no card_prop,
  no claim → both inserts drop it. LIST A: **0x1A1F** (only other claim: kuribandit registry_row).

### BUILD 2 (whole card) — 2026-10-05, AWAITING IN-GAME TEST
- verify 23/23; check_allocations --emit clean (389 ov5 slots, 417 claims). C0 route equivalence re-run: OK.
- C2 = LIST A (drop 0x1A1F) + cls1 {RES, 0x021E32D5, COND, 0x021E51E5, COST} + criteria {0xFFFF, HAND, 0x2}
  (both rows over 0x0E9B). Caves CAVE_WK_RES/HAND/EDPRED/COND/COST (0x023A4990..0x023A4E00).
- **Extra-Deck builder flags: 0xA (Cyber-Stein) DROPS every Synchro** — measured on rom_wattuna_cobra.ml3
  (Extra = Wattchimera + Watthydra): flags 0/8 → 2 candidates, 2/0xA/0x20/0x24 → 0. Native Synchro-from-Extra
  precedent Starlight Road's handler 0x022423C8 uses **flags 8** → shipped with 8.
- Pool probe `scratch/wattkyuki_pool_probe.py` (thumbemu over savestate RAM + built caves/Watt list):
  EXTRA → {Wattchimera, Watthydra}; GY (injected Wattuna 0x1050 + Watthydra + Upstart Goblin) → {Wattuna} only
  (non-Tuner Watt rejected). EDPRED direct: 0x1458→0, 0x230F→1, 0x2477→1, 0x1050→0, Splendid Rose 0x2272→0.
- NOT proven offline: the FIELD sub-handler (emu stops at an ARM-state helper 0x020895FC reached via
  0x020299AE) and the resolver phase machine end-to-end (needs the live picker UI) → in-game test.

### 🚢 SHIPPED 2026-10-05 (user: "It works now, ship both.")
- Wattuna E4 in-game confirmed by user 2026-10-05 on rom_wattuna_e4.nds ebf312c8...4316 (verbatim: "It works now").
- patch_wattkyuki added to steps.STEPS (step 92/96, right after patch_wattuna) and _verify_all_patches.SHIPPED;
  donor pool note updated (St. Joan + stale Twin-Headed Thunder Dragon -> Used).
- EE build: 96/96 steps, BUILD_EXIT 0, rom_all_patches.nds sha256 2cb7645d...ba9f4 (129669256 B); pre-ship copy
  rom_all_patches.pre_wattkyuki.nds. Sweep: 82 passed, 0 failed. Chain vs tested ROM: every Wattkyuki/E4 region
  identical except the unreachable 8 B tail of Wattuna's 64 B stub slot (chain keeps native dead-leaf bytes,
  the in-place test upgrade zero-filled them; the 56 B stub itself is byte-identical).

### ✅ IN-GAME CONFIRMED BY USER 2026-10-05 — BUILD 2, all 8 oracle items
User, verbatim: "Just for the record, all of Wattkyuki's test notes are confirmed. They all worked but I
encountered this edge during testing" (the edge = the Wattuna U4 report below, a patch_wattuna defect).
ROM rom_wattkyuki.nds sha256 5357b0f4...78466. NOT shipped yet (not in steps.STEPS) — awaiting user's ship order.

### USER REPORT 2026-10-05 (rom_wattkyuki.ml2) — Wattuna U4 offers nothing; ROOT CAUSE IS IN WATTUNA E2/E3
User: "if you have no cards in hand then, if you attack directly wattuna with a watt cobra on the field, it does
not offer anything as a synchro despite being able to make wattkyuki". Savestate: side 0 hand EMPTY, field
Wattcobra 0x0FD3 (slot 2) + Wattuna 0x1050 (slot 3) face-up, Extra 3x Wattkyuki + Wattchimera + others.
`scratch/wattkyuki_wattuna_offer_probe.py` (thumbemu over that RAM):
- Wattuna U4 candidate count 0x02243FE0(0, 0x1050, 0) = **0** (reproduces the report).
- can_synchro 0x02249540(0, cid, 0, 1): Wattkyuki **1 with CAVE_WU_PROBE = 0, 0 with PROBE = 1**; Scrap Dragon
  likewise 1 → 0. Wattkyuki's own material routing is fine.
- Mechanism (KB synchro.native_hand_material_mode, VERIFIED): with a Wattuna first pick, patch_wattuna's gate stub
  (0x021BB288, via 0x02249516) makes gate 0x022494EC TRUE while PROBE or the forced slot is set; then the validator
  accepts ONLY zone 0xB (hand) and level_sum walks ONLY the hand → field non-Tuners (Wattcobra) can never count;
  empty hand → nothing makeable. Same mode is on during the real summon (forced slot set) → printed "from your
  hand AND/OR face-up field" is currently hand-only. Affects every Watt Synchro, not just Wattkyuki.
- User chose "the proper fix" (2026-10-05). → patch_wattuna PART E4, built as rom_wattuna_e4.nds
  (_build_wattuna_e4.py: rom_wattkyuki.nds + patch_wattuna.apply_effect; Wattuna verify 39/39, Wattkyuki 23/23).
  * Second cause found by measurement: level_sum 0x0224966C's "another pick available?" block (entered only
    from 0x022496F6, with r6 = 0x0229ABFC and r7 = current cell) scans the HAND (gate true) OR the FIELD
    (0x0224999A) — never both. Variant table (scratch/wattuna_mixed_gate_probe.py): validator-only fix = no
    change; r6-only fix = field case fixed but hand-only case broken; both = all fixed.
  * E4 = gate stub `wmode: cmp r6,#0xB ; blt zero` (validator r6 = kind; level_sum r6 = pointer; Revolution's
    H1 stub tail-calls the gate with r6 intact) + in-place rewrite of the hand loop 0x0224992C..43 /
    0x02249980..99 (pool 0x02249944..7F untouched): keep r6, park r7 / hand count in dead frame slots
    [sp+0x14] / [sp+0x18] (epilogue reads only +0x20/+0x24), on a miss restore r7 and fall into the field scan.
  * Executed on BUILT bytes (scratch/wattuna_e4_built_probe.py): offer Wattkyuki/Scrap 0→1 on the user's board
    and with a junk hand card; hand-material boards unchanged; ordinary Synchro checks 0 regressions / 24.
  * AWAITING IN-GAME TEST (the real procedure with mixed hand+field picks is not emulated).

## Ruled Out
- Reusing Wattuna's Synchro resolver 0x02249EC0 for C2: it forces the activator into the
  forced-material slot 0x0229AC7C (wattuna-findings) — C2 is a plain SS, not a Synchro.

## Open Questions
- Is ov3 0x021E2488 a per-cid gate on 0x1458?
- Field monster → Main Deck mover: 0x021CDD4C dest 0x0D? 0x021C6DD8? (UNPROVEN)
- 0x021C6A0C: GY→Deck (Avarice) vs ATK grant (equip KB) conflict.
- Thunder race code value.
- Wattchimera/Watthydra cls1 +08 predicate.

- **Non-Tuner hook 0x02248AAC can't simply be chained.** `patch_azure_eyes` owns it, its stub calls
  INNER 0x0224829C itself, and `apply_normal_material_gate` asserts the site == its own BL.
  A Wattkyuki stub in front would break Azure-Eyes' verify. (Read this session, patch_azure_eyes.py:732-840.)
- **THIRD (0x02248A88) frame, by disasm this session:** r5 = Synchro cid, r6 = arg1 (side),
  [sp+8] = arg2+arg3, r7 = (arg2==0xB, i.e. hand). The per-cid tree starts at 0x02248AB8
  (`ldr r0,=0x219D; str r0,[sp,#0xC]`). Native leaf pattern (Life Stream @0x02249478):
  `bl 0x021A3320(r6,[sp+8])` → material cid; accept → `b 0x022494C4`; reject → 0x0224948C (r0=0).
  0x02248AB8 is DETOURED by patch_life_stream_dragon (CAVE_LSD_MAT): donor 0x18FA → leaf,
  else replay the entry + `bx lr`.

## Next Experiment
**IN-GAME TEST of rom_wattkyuki.nds sha256 5357b0f4...78466 (BUILD 2, whole card; single-card ROM on
rom_all_patches.nds — NOT in steps.STEPS).** Oracle items:
1. Synchro Summon Wattkyuki (Lv8) with a Watt Tuner + Thunder non-Tuners → allowed.
2. Negative: non-Watt Tuner, OR a non-Thunder non-Tuner → Wattkyuki not offered / material refused.
3. It attacks directly while the opponent controls a monster.
4. Direct hit, with a Watt Tuner in GY + a face-up non-Tuner Thunder you control + a Watt Synchro in the
   Extra Deck → "You can" prompt → pick GY Tuner → pick field monster → both go to the Deck, Deck shuffles
   → pick a Watt Synchro (Wattkyuki NOT listed) → it is Special Summoned.
5. Second direct hit same turn → not offered. 6. Declining the prompt → still usable later that turn.
7. Missing any one of the three pools → not offered. 8. Regression: Wattuna U4, Junk Speeder / Dragunity Remus /
   Azure-Eyes / Life Stream Dragon Synchro materials unchanged.
If item 4 fails, ask for a savestate at the failing step (picker open / after the move) before touching code.

### (superseded) earlier next-step note
- **Preferred C0 route (LSD precedent):** find the native THIRD-tree leaf that Wattchimera 0x230F /
  Watthydra 0x2477 reach ("non-Tuner Thunder"), plus the native Watt-Tuner check near 0x02248A42
  (wattuna-findings §684-719). If both exist, route 0x1458 to them (like LSD routes 0x18FA) instead
  of new race/set-code stubs.
  Method: wrap ov3+arm9 images as `ss.u8` for `scratch/thumbemu.py` `Emu.run(0x02248AB8)` with
  r5 = 0x2477, and log the first exit leaf. Then do the same for the OUTER/Tuner tree.
  Composing at 0x02248AB8 means extending LSD's `mat_stub` (a shipped module): ask the user first.
- Then Phase 0 item 6 (Wattchimera/Watthydra cls1 rows) and item 7 (field→Deck mover proof, hard gate).
- Thunder race code: still unread (read card_prop race of 0x230F via card_prop_codec).

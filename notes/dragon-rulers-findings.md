# Dragon Rulers (Redox/Tidal/Blaster/Tempest + Reactan/Stream/Burner/Lightning) — findings

Scope (user, 2026-10-15): whole cards, all 8 in one family module
(`patch_dragon_rulers.py`). Nebulus/Spectral excluded by user. Plan:
`~\.claude\plans\redox-dragon-ruler-of-swirling-steele.md`.

Donors APPROVED by user 2026-10-15: Redox←0x17CD Charcoal Inpachi, Tidal←0x115F Mech Bass, Blaster←0x1145 Mechanicalchaser, Tempest←0x1125 Parrot Dragon (swapped in, user-approved 2026-10-15, replacing Gadget Soldier / Sonic Duck), Reactan←0x0FF4 Axe Raider, Stream←0x115E 7 Colored Fish, Burner←0x0FEA Garoozis, Lightning←0x1CC6 Atlantean Pikeman.

Status: BUILD 2 (all 8 rulers) built 2026-10-15 -- rom_dragon_rulers.nds sha256 15834a89387df1f169a1a1d91b4166517daddc43bb5b80a0379426834b02075b, verify PASS (54 static checks), hook proof PASS (96 OK, rulers bad=0, non-ruler diffs=0). NOTHING in-game tested: AWAITING IN-GAME TEST for every card (user: "I'll test everything at the end"). Oracle = _build_dragon_rulers.py docstring.

## Confirmed

- **3DS cids** (CARD_Indx_E / CARD_Prop, 2026-10-15 script): Redox 0x2917,
  Tidal 0x2918, Blaster 0x2919, Tempest 0x291A, Reactan 0x2950, Stream 0x2951,
  Burner 0x2955, Lightning 0x2956. All > NDS max cid 0x24E8 → not in NDS,
  donor build required.
- **3DS criteria registry true base = 0x68689C** (pointer pair at 0x514AA0
  {0x68689C, 0x68CF2C}); the 0x686CBC base in CLAUDE.md is mid-table (my
  scan from 0x686CBC found Redox at "row 1901"; true index 1989).
  `threeds_lookup.py` / CARDS_ZEXAL_3DS_ASM.md also truncate the cls2-equiv
  table at 815 rows (true range [0x6C6780, 0x6CCC48)).
- **Redox criteria rows** (aux 0xFFFF): `0x4AD97C/0x05000002` (discard 1
  EARTH, C3), `0x4A5688/0x00000002` (banish 2, C1 — ruler-only handler),
  `0x4B1BE8/0x0D000002` (Deck pick EARTH Dragon, C4), `0x4B1B74/0x00010002`
  (GY target, C3). Siblings: 0x4AD97C word 0x03/0x04/0x06000002 (WATER/FIRE/
  WIND); search word 0x0B/0x0C/0x0E000002. Tidal +`0x4B1BE8/0x2`, Tempest
  +`0x4B1BE8/0x08000002`, Blaster no row 3. Babies `{0x4A5920,0x2}` +
  `{aux=big cid, 0x4A6834, 0x00000802}`.
- **3DS→NDS criteria handler equivalence** (row-by-row match over cids both
  builds ship, same word): 0x4B1BE8 ≡ 0x0223CAD9 (56 matches), 0x4B1B74 ≡
  0x0223C9D1 (40), 0x4AD97C ≡ 0x02242105 (2: Darkness Neosphere 0x2159 word
  0x18000002, Big One Warrior 0x2415 word 0x40002). 0x4A5688 / 0x4A5920 have
  no NDS equivalent.
- **3DS cls2-equiv Redox records** (rows 970-973): banished search
  `{0x4604B4,0,0x49C570,0x400258,0}`; hand SS self
  `{0x462030,0,0x49CD70,0x401E98,0}`; discard→revive
  `{0x45E8A0,0,0x49CD70,0x401E98,0x477CC0}`; GY SS self
  `{0x45E090,0,0x49DB90,0x400794,0}`. cls1-equiv EP return
  `{0x413030,0,0x49BFF8,0x400EF0,0}`. Slot equivalences (Explore agent,
  shared-cid matching): 0x4604B4≡0x02207EF5, 0x462030≡0x02206ABD,
  0x45E8A0≡0x02207191, 0x45E090≡0x0220731D, 0x413030≡0x0220A901,
  0x49CD70≡0x021F0935, 0x401E98≡0x021E6871 ("Use which effect?", 76/78),
  0x477CC0≡0x02235605, 0x400258≡0x021E5201. **Hand C1 + C3 share the
  0x401E98 which-effect prompt → NDS analogue 0x021E6871** (hardcodes cids).
  Agent-reported, not re-run by me: treat the slot table as ANCHORED-quality.

- **Donor scan 2026-10-15** (scratchpad donor_scan8.py + inline ranking over all 86
  `donor_scan --free` cids; stock rom.nds): u16 hits in ov3+ov5 + tight base±imm
  (ldr literal within 0xFF, adds/subs of the delta within ±12 halfwords).
  ZERO ov3/ov5 hits: 0x0FEA Garoozis, 0x0FF4 Axe Raider, 0x111E, 0x1123, 0x1125,
  0x1145, 0x115E 7 Colored Fish, 0x115F Mech Bass, 0x13E2, 0x13E4 Gadget Soldier,
  0x1573, 0x160B Sonic Duck, 0x16F0, 0x16F1, 0x17CD Charcoal Inpachi, 0x1CC6
  Atlantean Pikeman. ARM9 u16 hits for the picks are either Thumb shift
  encodings (asrs/lsrs) or inside all-cid ascending tables (0x020782C0..,
  0x0207B520.. run every cid 0x0FCA,0x0FCB,..) — not per-cid gates; no aligned
  u32 hits. Gadget Soldier + Atlantean Pikeman: 0 ARM9 u16 hits at all.
  REJECTED as noisy: Killer Needle 0x0FDB (154 ov3 hits, = `lsrs r3,r3,#31`),
  Jellyfish 0x0FED (10 ov3). Chamberlain 0x1C6C has 1 ov3 u16 + base±imm
  candidates (0x021EE73A 0x1C6B+1) — dropped rather than reviewed.

- find_event_handler per-cid record-offset machinery (stock ov3, 2026-10-15,
  scratchpad tdx.py + romss.py emulation of 0x0224A1F2 over every cid):
  lists 0x02275B60 x0x13 (offset 1 iff desc[+4]==2), 0x02275B86 x0x19 (iff
  desc[+4]==6), 0x02275BB8 x0x26 (offset desc[+0x18]-1), then a base±imm
  per-cid switch whose leaves set offset 0/1 from desc fields (e.g. leaf
  0x0224A644 for 0x14CC: offset 1 iff desc[+4]==0xE; leaf 0x0224A636: iff
  [0x0229DD14+0x34] != desc[+2]); default 0x0224A7E6 = Spirit-only arm.
  Apply site 0x0224A804..0x0224A836 (record = leftmost + offset, must still
  match the cid).

- **Criteria-registry interface is closed: resolver 0x02243B9C -> index ->
  invoker 0x02243F38** (chained rom_all_patches.nds, 2026-10-15, BL scan of
  arm9/ov3/ov5 + literal scan of every overlay). Resolver BL callers = exactly 3
  (0x02243FB6 in run-wrapper 0x02243FA8 [73 callers], 0x02243FEE in count-wrapper
  0x02243FE0 [201 callers], 0x02244080); invoker BL callers = the paired 3
  (0x02243FCA, 0x02244002, 0x022440B8). Table base 0x022713C4 literal appears in
  ov3 ONLY in the resolver/invoker pools (0x02243DFC, 0x02243F30, 0x02243FA0,
  +4 @0x02243FA4); other hits are ov5 patch stubs (0x023A15C0/0x023A1860/
  0x023A2DBC) for their own cids. No other overlay references it.
  Resolver miss tail @0x02243F24 = `subs r0,#0xd ; pop {r3-r7,pc}` (r0 = 0xC ->
  -1). Invoker row compute @0x02243F62..0x02243F6E: r0 = base + idx*12, r3 =
  [base+4 + idx*12], then `blx r3` with (row, side, param) @0x02243F74; both
  0x02243F50/0x02243F5A branch TO 0x02243F62; r6 dead after 0x02243F6E.
  -> VIRTUAL ROWS: hook miss tail (cid in ruler set -> idx 0x4000+k) + invoker
  compute (idx >= 0x4000 -> our row). No phantom rows needed.
- Capacity census (chained ROM, phantom = cid absent from scratch/cid_to_name.json,
  present in stock too, not in PHANTOM_CLAIMS; HEURISTIC, re-check vs card_prop):
  cls0 40, cls1 54, cls2 6 (0x1A8A 0x1B47 0x1B48 0x1B49 0x1B4A 0x1B8F), cls3 29,
  criteria 0 (only 0xFFFE sentinel).

- **cls tables are referenced ONLY by find_event_handler** (literal scan of
  arm9 + every overlay, chained ROM, 2026-10-15): cls2 base 0x02275C04 lit
  @0x0224A398, cls1 0x022860D4 lit @0x0224A3A8, nothing else. Miss path ends
  @0x0224A86A `movs r0,#0 ; pop {r1-r7,pc}` (4 B, native in chained ROM);
  r4 = desc, [sp] = key cid, desc[+5] = selector (0..3). cls0 misses first try
  generic records by card type (0x0202ABE8 == 2/3/6 -> base/+0x18/+0x30).
  -> VIRTUAL RECORDS: hook 0x0224A86A, return &vrec for ruler cids. Phantom
  census (card_prop-based, 4305 real cids 0xD48..0x24E8): cls2 6 free, cls1 54.

- **GY offer = virtual GY-action rows** (Revolution Synchron's 4 sites 0x0224C88E /
  0x0224C9A0 / 0x0224CD34 / 0x0224CD60, row {cid, 0x0E, 0x0224C591, 0x0224C6C1}).
  Revolution's shipped ov5 stubs are too small for 5 cids (GYPOST 0x30, GYHAS 0x20,
  VROW 0x10) and patch_revolution_synchron.verify asserts them byte-exact + the 4
  site BLs. DECISION: single-card build (step0 + patch on rom.nds, NEXT precedent)
  installs OUR table-driven H4-H7 in our own CAVE_DR_* slots; at SHIP time lift
  them into a shared module that Revolution (row 60) registers into, with an
  execution-equivalence proof (scratch/gyvrow_equiv.py precedent) + Rev verify edit.

- **"Was Special Summoned" = [slot+0x44] bit 4 (0x10), persistent** (MEASURED 2026-10-15,
  scratchpad slotscan.py over 99 occupied monster slots in every *.ml* savestate;
  slot = 0x0229AC94 + side*0xB3C + zone*0x14, card word @+0x34, face-up @+0x3C,
  flags @+0x44). Bit 4 set on 10/10 Fusion/Synchro slots and on tokens (0x110);
  clear on every known Normal Summon (0x410100 = bit 16 + bit 22 + bit 8). Survives
  turn change (life_stream ml4 Fusion 0x110 after bits 18/22 cleared). 3DS twin:
  Redox EP cond f2 0x482EC8 = bit 4 of [player + slot*0x18 + 0x4C].
  NOT yet seen on a disassembled NDS reader -- correlation only.
- 3DS EP-return condition for the rulers: ignition-cond table 0x6A6C30 rows
  {0x2917..0x291A, f1 0x49C570, f2 0x482EC8}; f1 0x49C570 = deny if turn-log
  (side, 0xB, cid=0xFB6?) posted ... (0xFB6 literal; not decoded).
- **C2 EP plan**: phantom EP-registry row 154 (0x19C0, already {0x02253F89,..})
  -> resolver = ov5 stub calling 0x02253F89 for each ruler cid until nonzero
  (== N adjacent native rows). cls1 virtual record {0x0220A901 Spirit return, 0,
  COND, ..} with COND = opponent's turn && bit4 && face-up.

- **EP walker** 0x022566F8.. walks registry 0x0228E3D8 (KB row 63 onward, 0xE1 rows,
  {fn, cid}): `blx r2` @0x02256716 (r0 = ctx r7, r1 = row cid); r0 == 0 -> STOP the
  walk (return 0); nonzero -> next row. Poster 0x02253F89(ctx, cid) = 0x02253EC8(ctx)
  then (1-ctx); 0x02253EC8(side, cid): returns 1 unless side == [0x0229DD14+0x34] ^
  [0x0229DD94]; scans zones for cid (0x021AC004), alive 0x021A32B4 (skipped when
  [0x0229AB7C+0x18] != 0), [slot+0x44] bits 26/27 clear -> 0x021D3230(side, zone, 6, 0)
  = event 6 (cls1), marks bit 0x1B via 0x021D2A40, returns 0. Row 154 @0x0228E6B0 =
  {0x02253F89, 0x19C0} in stock AND chained ROM; 0x19C0 unclaimed in registry_row
  (only summon_list_c7 by oviraptor, other pool). Multi-cid stub: for each cid r =
  0x02253F89(ctx, cid); if r == 0 return 0; end -> return 1  (== adjacent rows).
  ⚠️ stub MUST be ov3 (walker runs every End Phase in every mode).
- **Banish events, both routes** (stock ov3 disassembly 2026-10-15):
  (a) GY->banished 0x021C7118 gate @0x021C71C8 `ldr r1,=0x1CF6 ; cmp r0,r1` (r0 = cid,
      KB event.banish_from_gy_cid_gate; Eclipse Wyvern hooks it in the chain).
  (b) hand/field->banished: wrappers 0x021C6E4C/0x021C6E9x -> core 0x021C6B00 ->
      0x021D1300 (bl @0x021C6CB8) -> per-cid override switch @0x021D1B98 (r5 = cid;
      entry `ldr r1,=0x1D98 ; cmp r5,r1`, 4 B). Banish leaf 0x021D1D3E: [sp+0x30] == 0x0F
      && ([sp+0xC] & 0xC0) != 0xC0 -> [sp+0x14] = 1 -> post. Hook plan: ruler cid &&
      [sp+0x30] == 0x0F -> jump 0x021D1D3E; else replay + return (bx keeps flags).
- **Criteria word predicate 0x0223BA24 ANDs race and attribute** (disassembly): mask
  0xF8000000 -> race = word >> 27 vs 0x0202ABB8(cid) (GY zone 0xE: 0x021B1EE8); then
  mask 0x07000000 -> attribute. Dragon = race 1, EARTH = attr 5 -> 0x0D000002 =
  "EARTH Dragon". Deck handler 0x0223CAD9 -> builder 0x0223BC3C(side, cid, 0, 0,
  [sp] word, [sp+4] 2).

- ⚠️ CORRECTION 2026-10-15: my first donor ARM9 scan read ndspy `rom.arm9`, which is
  the COMPRESSED image (552 492 B vs 717 088 B reference_files/arm9.bin) -- its ARM9
  "hit" lists were garbage (ov3/ov5 scans were fine: overlays decompress). Re-run on
  the decompressed image + donor_scan: Gadget Soldier 0x13E4 is a member of the
  "Gadget" set-code list @0x0209C6AA (neighbours 0x1807/0x180B/0x180C Green/Red/Yellow
  Gadget, Gadget Hauler/Driver) -> REJECTED (per-cid gate). Sonic Duck 0x160B sits in
  an unsorted ARM9 list @0x020AA9AA (Sonic Chick, Gilasaurus, Mega Hamster...)
  -> unknown purpose, REJECTED to be safe. Others: Charcoal 0x17CD / Mech Bass 0x115F /
  7 Colored Fish 0x115E zero ARM9 hits; Axe Raider 0x0FF4 / Garoozis 0x0FEA hits are the
  known ramp tables 0x0209D6xx/0x0209E4xx/0x020A14xx + code encodings; Pikeman 0x1CC6 1
  code-region hit. Fully clean replacements (donor_scan, 0 ARM9 hits): Mechanicalchaser
  0x1145, Gil Garth 0x1573, Neo Bug 0x16F1, Mad Dog 0x16F0, Monster Tamer 0x111E,
  Shining Abyss 0x13E2, Parrot Dragon 0x1125.

- **Hand-offer lists are consulted by 7 callers of ARM9 0x0202354C** (decompressed arm9 +
  chained ov3/ov5 BL scan): ov3 0x021E4C78, 0x021EC982 (the offer gate 0x021EC93C, which
  then sets desc[+5] = 2 @0x021EC998), 0x02239656, 0x0224B082, 0x0224C052, 0x0224C0C4;
  ov5 0x02346706. No ARM9 caller, no literal. 0x0202354C = bsearch LIST A (0x1E) then
  `ldr r1,=LIST B ; adds r0,r4 ; movs r2,#0x24 ; bl 0x02022E14 @0x02023566 ; pop {r4,pc}`.
  -> ONE hook: replace that final BL with a BL to an ov3 stub (native bsearch, then the
  ruler test on a miss). (KB said "@0x0224C050 bl" -- the BL is at 0x0224C052.)
- Hand probe 0x021EDD90 desc: +0 cid, +2 side, +3 0xB, +0xC ref, +4 0; GY builder
  0x0224C590: +3 0xE, +5 2, +0xC ref (strh r7 @0x0224C5F8) -> desc[+0xC] = this card's
  ref in BOTH zones ("except this card" = ref compare).
- cls1/cls2 aux is 0 in every stock record (1333 / 697). Ouroboros banished record
  {0x022065B9, 0, 0, 0x021E5201, 0}; Spirit EP return {0x0220A901, 0, 0, 0x021E88A9, 0}.
- Criteria handlers: discard-1-filtered-from-hand-except-self = 0x02242105 (builder
  0x0223BFD4, predicate 0x0223C805, excludes acting desc[+0xC] ref, word = filter) --
  3DS ruler row 0 twin; own-GY target 0x0223C9D1 word 0x00010002; Deck 0x0223CAD9.
- 0x021F0384(desc) = 0x021F0114(desc, side) && 0x021B9EC0(side, cid) (can SS here + zone).
- Attribute accessor 0x0202ABC9 returns FLAG<<3|ATTR (mask 7; EARTH 5, WATER 3, FIRE 4,
  WIND 6); race getter 0x0202ABB9 raw (Dragon 1, Spell 23, Trap 24).
- dlg ids (dlg_text_e, scratchpad dlgdump.py): 0x103 "Use which effect?", 0x19F "Special
  Summon the designated monster(s).", 0x0EB "Discard from your hand.", 0x56 banish
  prompt, 0x29 "Select a monster to discard from your hand.", 0x1DE / 0x1F3 / 0x19C /
  0x1B4 = the 3DS per-ruler C3 labels (SS 1 designated / send Deck->GY / destroy 1 /
  add from Deck).

## Design (Redox build 1)
ov3 (cave3): find_k + RULER list; H1 find_event_handler miss 0x0224A86A; H2 resolver miss
0x02243F24 (idx = (0x40+k)<<8); H3 invoker 0x02243F62 (row = ROWS + k*0x30); H4 ARM9
0x02023566 bsearch-LIST-B BL; H5 EP row 154 resolver (multi-cid 0x02253F89); H6 0x021C71C8;
H7 0x021D1B98.  ov5: 4 virtual records per big ruler {HAND, GY, BAN, EP}, ROWS {VROW->CRIT,
SEARCH 0x0223CAD9 0x0D000002, DISCARD 0x02242105 0x05000002, GYT 0x0223C9D1 0x00010002},
CRIT mode handler, FILT, COUNT/MASK, COND_H/COND_G/COND_B/COND_EP, shared COST (prompt ->
banish two-pick | discard pick), RES_H, TGT_H, RES_B, GY vrows (Rod's generalized H4-H7).
Records: HAND {RES_H,0,COND_H,COST,TGT_H}; GY {0x0220731D,0,COND_G,COST,0};
BAN {RES_B,0,COND_B,0x021E51E5,0}; EP(cls1) {0x0220A901,0,COND_EP,0x021E88A9,0}.
OPT: ONCE_CHECK 0x021F6DD9 in conds; stamp at cost completion (C1/C3) / RES_B at 0x80 (C4).
C2 (mandatory return) NOT OPT-gated -- user ruling 2026-10-16: it does not count toward the 1-per-turn.

- **BUILD 1 hook proof PASSED** (2026-10-15, scratch/dragon_rulers_hooks_equiv.py on rom_dragon_rulers.nds
  d9a503d3...c670, ROM-backed thumbemu): Redox FEH -> HAND/GY/BAN/EP records exactly per descriptor (GY ev 0x1E
  and cls1 ev 9 -> 0), resolver -> 0x4000, count wrapper enters CRIT with ROWS+0, 0x0202354C -> 1; EVERY other cid
  0xD48..0x24E8: FEH (4 descriptor shapes), resolver, hand-offer lists identical to stock -> "rulers bad=0
  non-ruler diffs=0". (Emulation note: scripts in scratch/ must drop scratch/ from sys.path -- scratch/dis.py
  shadows stdlib dis; the cid-alias path 0x02023D48 enters ARM, so the harness compares that as a crash site.)
- Baby "cannot attack this turn": summon-event handler @0x02268080..0x022680A4: rider 0x021C479C(side [r4+2],
  zone [r4+4], key [r4+0x12] = SOURCE cid, 3, ..) then bsearch list 0x0228F708 (bl @0x02268090) -> kind-2 rider
  keyed [r4+0x12]. Attack check tests rider keys vs list 0x0226D6F8 (Summoner Monk 0x1900 a member). PLAN: hook
  the bl @0x02268090: native bsearch; on miss + baby source -> attach {key 0x1900, kind 2, 0} ourselves, return 0.
  ov5-hosted (the chain already sends this site to ov5 via Petiteranodon; SHIP-TIME compose with NEXT/Petit).

## Ruled Out

- Two independent hand cls2 records split by desc[+3]: both C1-hand and C3
  are hand ignitions; find_event_handler takes the leftmost same-cid record.
  Konami uses one which-effect prompt instead (above).
- Multiple cls2 records per ruler: needs an arm in the base±imm switch above
  per donor cid. DESIGN: ONE cls2 record per ruler whose slots branch on
  desc[+3]/desc[+4] (Sakitama / Jet Synchron precedent).
- 0x021E6871 native multi-effect cost: needs list 0x02275BB8 membership + arm in
  per-cid legality switch 0x021E5794 (default mask 0) -> use own prompt
  0x0219ABB5 in our cost stub (Uni-Zombie precedent, shipped/confirmed).
- Phantom criteria rows: exhausted -> virtual rows (above).

## Open Questions

- ARCHITECTURE APPROVED by user 2026-10-15 ("Yes, go with the 4 ov3 virtual-registry hooks; keep the card logic in ov5"): "virtual registry" — 4 ov3 hooks keyed on
  one ov3 ruler-cid list: H1 find_event_handler miss 0x0224A86A (virtual cls1/cls2
  records), H2 criteria resolver miss 0x02243F24, H3 invoker row compute
  0x02243F62 (virtual rows), H4 hand-offer BL 0x0224C050 (-> 0x0202354C).
  All 4 sites native in chained ROM. Stubs must be ov3 (every card's lookups pass
  them; an ov5 hop would break every card in the puzzle editor). cave3 has ~0x3F8 B
  left, largest runs 0x84 @0x021F1008, 0x5E @0x0220A5E0, 0x5C @0x021F19E8,
  0x4E @0x021FAE08. Card logic + virtual rows/records live in ov5.
- Still to RE: GY offer (virtual GY-action row: Revolution Synchron 4-hook
  machinery / Magician's Rod 2-row rewrite), C2 EP poster rows + "was SS'd"
  condition, C4 banish-trigger cid gates (0x021C71C8 GY->banished, 0x021D1300
  hand/field), 0x0223CAD9 decoding attr+race words, baby named-Deck SS +
  cannot-attack.

## In-game results (BUILD 2, rom_dragon_rulers.nds 15834a89...075b) -- user 2026-10-16
- BUG 1 (user, verbatim): "None of the level 3/4 dragon rulers have the option to activate their discard
  effect. See rom_dragon_rulers.ml2" + "only redox offers it hand effect." -> Tidal/Blaster/Tempest AND all 4
  babies: no hand activation offered; Redox: offered.
- BUG 2 (user, verbatim): "When I banish Blaster/Tempest/Tidal for Redox SS effect, the banished cards miss
  timing when they should not." -> C4 behaves as WHEN (misses timing); must be IF.

- BUG 1 ROOT CAUSES (offline, scratch/dragon_rulers_offer_probe.py + full offer gate 0x021EC93C emulated on
  rom_dragon_rulers.ml2, 2026-10-16):
  (a) CRIT's "C3 row" branch hard-coded GYT_H 0x0223C9D1 instead of the row's own handler -> Tidal / Tempest /
      every baby counted GY monsters (0 on that board) for their C3 row -> MASK bit 1 = 0. (Redox's C3 row IS the
      GY row, which is why only Redox worked.) Fix: `ldr r3,[row,#4]`.
  (b) A HAND record with a non-zero +08 (Blaster's FIELD_FILTER 0x021DE5A9) is offered ONLY if that filter accepts
      >= 1 board zone: the gate ran 0x021D6E40 over zones 0..0xA, found nothing on an empty field, returned 0 --
      although Blaster's COND_H returned 1 (C1 legal). Redox (slot2 0) -> gate 1, Blaster -> 0, call traces
      identical up to that sweep. Fix: mode-aware slot2 stub (C3 -> real filter, else accept).

- BUG 2 ROOT CAUSE: the "You can" tag body 0x021E50DC asks the miss-timing test 0x021EE0E0(desc) via
  `bl` @0x021E510A (its only other caller is 0x021E8914); 0x021EE0E0's head is a cid tree of hard-coded IF
  cards (Shadow Mist precedent, KB timing.miss_timing_test) -> the rulers counted as WHEN. Fix: front the BL
  @0x021E510A -> cave3 CAVE3_RUL_MISS 0x0221AC08 (0x18 B): ruler cid -> 0 (never miss), else the native test.
- BUILD 3 (2026-10-16): rom_dragon_rulers.nds sha256 f6e0a641e57bf643333361323b8ef2b8e9c5d37626608a04c2a75c3266c4f984,
  verify PASS (55). Offline on the user's .ml2 board with BUILD 3 code overlaid (scratch/dragon_rulers_offer_after.py):
  the real offer gate 0x021EC93C returns 1 for ALL 8 rulers (each put in hand slot 0). AWAITING IN-GAME RETEST.

- BUG 3 (user, verbatim): "Blaster's discard from Hand effect causes a freeze. See .ml2" -> "a)" (froze right
  after choosing "Discard from your hand") -> "while frozen" (.ml2 saved frozen).
  .ml2: cost phase [0x0229AAFC+0x7C] = 3 (our picker phase), acting desc 0x0229A7FC = Blaster 0x1145, zone 0xB,
  mode desc[+0x18] = 2, ref 0x16; hand Redox, 0x1D85, Burner(FIRE), Blaster, Axe Raider, Blaster, 0x15A1.
  ROOT CAUSE: 0x02242105's builder 0x0223BFD4 is INDEX-STYLE -- it tests the ONE hand card hand[param]
  (`ldr r1,[r2,param*4]` @0x0223BFFE), it does not build a list. The list picker 0x0219C431(side, 6, cid, 0)
  over that row -> empty list -> hang (Gates of Dark World's empty-picker freeze). ⚠️ CORRECTS my earlier
  "discard-1-filtered-from-hand-except-self = 0x02242105" design: it is for native discard machines that walk
  the hand index themselves. Fix: discard picks use the list builder 0x0223C16D + FILT (attr-only for big rulers,
  attr-or-Dragon for babies).

- BUILD 4 (2026-10-16): rom_dragon_rulers.nds sha256 c4b306a97361054861bda6aef53a8ff70fb3891ed26534e0db889bb53cdba1a5,
  verify PASS (55). On the user's FROZEN .ml2 with BUILD 4 code overlaid (scratch/dragon_rulers_discard_probe.py):
  Blaster's discard list = [Burner 0xFEA, the other Blaster 0x1145] (exactly the FIRE monsters besides itself;
  was EMPTY -> freeze); Redox [0x17CD, 0x0FF4]; each baby = every Dragon-or-attr monster but itself; Tidal /
  Tempest empty on that hand (no WATER / WIND monster -> MASK does not offer C3 there). User also reported
  (verbatim) "Tempest does not suffer from this bug, but Redox and Tidal do too." -- consistent: the index-style
  row tested only hand[0]. AWAITING IN-GAME RETEST.

- IN-GAME CONFIRMED BY USER 2026-10-16 on BUILD 4 (rom_dragon_rulers.nds c4b306a9...ba1a5), verbatim: "All good,
  ship it" (after testing BUILD 4 for the BUG 3 fix; BUG 1 / BUG 2 fixes were in BUILD 3 and carried). SHIP approved.

- SHIPPED 2026-10-16 (user: "All good, ship it"): steps.STEPS "Dragon Rulers" after NEXT; _verify_all_patches.SHIPPED;
  composed with Revolution Synchron (N-row GY stubs keep its row 60, its cid compared last; its verify accepts),
  Eclipse Wyvern (H6 calls its stub for non-rulers; its verify accepts), NEXT/Obedience Schooled/Petiteranodon (babies'
  single-cid prechecks spliced behind NEXT's at 0x02268090 and in front of NOATK at 0x021A4AC6, bl_reaches shape, in
  Rod's NOOP cave3 slots -- user OK). Bulk pack/deck tables renamed to the ruler names (same cids). EE build 115/115
  rom_all_patches.nds sha256 a060206cb1fda2258acbab873fbd98498fc6f8edc35e8be7aa50f083911cf4f9; sweep 96 passed / 0 failed.
  The composed chain ROM itself has not been played in-game.

## Known gaps / deviations (not yet user-ruled)

- Goblin of Greed 0x168A does NOT stop the rulers' discard-cost effects (0x021E4C60's discard-cost lists don't
  name them; adding them = a 4th hand-list-style hook). Not built.
- C2 (mandatory End Phase return) is NOT gated by "only 1 effect per turn" -- USER RULING 2026-10-16: "The end-phase return does not count towards the 1 effect per turn" (build already matches).
- C4's once-per-turn is stamped at RESOLUTION (RES_B phase 0x80), not at activation, so a negated C4 does not
  consume it. C1/C3 stamp when the cost is paid.
- Baby "cannot attack" rider is keyed 0x1900 (Summoner Monk's key), not the baby's own cid.
- Tempest's C1 text has no "except this card"; built with the exclusion like the others (banishing itself
  would leave nothing to summon).

## Ship-time work (NOT done; do not chain-wire until the user approves)

- Compose the GY-action sites with patch_revolution_synchron (and parked Rod) via a shared module + their verify.
- Compose H6 (0x021C71C8) with patch_eclipse_wyvern's stub (its donor cid must stay in the test).
- Compose SUMLIST (0x02268090) with NEXT's ov3 precheck -> Petiteranodon's ov5 stub chain.
- Then steps.STEPS + SHIPPED + EE build/sweep + donor-pool file moves, per CLAUDE.md.

## Next Experiment

- USER in-game test of rom_dragon_rulers.nds (15834a89...075b) with the oracle in _build_dragon_rulers.py.
- On any failure: quote the report back, then emulate the failing slot offline (scratch/thumbemu.py over a
  savestate of that board) before changing code.

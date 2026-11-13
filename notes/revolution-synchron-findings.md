# Revolution Synchron — findings (live)

Status: **C0 + C1 in-game confirmed by user 2026-09-15** (all 8 checks, first test, build sha256 f466960d…d44c2). C2 not implemented. Not in steps.STEPS (awaiting shipping approval).

User report, verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed 6. Confirmed 7. Confirmed 8. Confirmed". Numbering follows the 8-item list in the hand-off message:
1. identity
2. Tuning finds Revolution, not Bri, still Junk
3. field Tuner
4. Power Tool Dragon via hand Revolution + Lv4, both to GY
5. Stardust + Lv5
6. once per turn
7. Junk Warrior not offered
8. ordinary field-Tuner Synchro still works

## Printed text (scratch/ygoprodeck_cache.json, id 97682931)
Level 3 EARTH Machine Tuner, ATK 900 / DEF 1400.
> If you Synchro Summon a "Power Tool" monster or a Level 7 or 8 Dragon monster, this card in your hand can also be used as material. You can only use this effect of "Revolution Synchron" once per turn. If you control a Level 7 or higher Synchro Monster while this card is in your GY: You can send the top card of your Deck to the GY, and if you do, Special Summon this card, also its Level becomes 1. You can only use this effect of "Revolution Synchron" once per Duel.

- C0 identity: stats, Tuner, text, and the Synchron set-code list (0x4C). **IN SCOPE**
- C1 usable as Synchro Material from the hand (Power Tool / Lv7-8 Dragon target, once per turn). **IN SCOPE**
- C2 GY revive, once per Duel. **OUT OF SCOPE** (user, 2026-09-15)

## User decisions (2026-09-15)
- Synchron list: **drop Bri Synchron 0x2414**. No relocation to ov5, no ARM9 cave.
- Scope C0 + C1. Donor Acrobat Monkey 0x1649 approved via the plan.

## C2 session (2026-09-15, second session)
- Arrival: verify_knowledge = 511 facts, 471 PASS, 0 FAIL, 40 UNVERIFIED. Grep: "revolution" does not appear in otn_enhanced/ or _verify_all_patches.py (still not chained).
- **Scope: C2 (GY revive) IN SCOPE.** C0/C1 must not regress.
- **User rulings 2026-09-15 (verbatim):** "1. Yes it is a cost" / "2. The effects cannot be activated if there are no cards in deck"
  - The top-card send is a **COST**, paid at activation.
  - **Empty Deck → the effect cannot be activated** (the condition must check Deck count >= 1).
- Step 0 (ship C0+C1 into STEPS) asked again, **no answer** → do not wire.
- **User decision 2026-09-15 (verbatim): "Share a row".** No real card's GY-action row is spent. An ov5 hook in the GY-action scanner lets 0x1649 match an existing family-C row. Normal-duel-only is accepted as the default.
- **GY-action registry: EVERY consumer, a closed scan** (scratchpad gyreg_refs.py, blscan.py, tdis3.py; stock == chain over 0x0224C400-0x0224CE00, zero diffs):
  - Literal 0x0228DDF8 appears at exactly 4 pool words (stock and chain, arm9 + ov3 scanned):
    - 0x0224CB28 ← ldr @0x0224C88E (enumerator A, per-row fetch)
    - 0x0224CC78 ← ldr @0x0224CBD8 (D, inside A: reads row[+0xC] by the STORED ROW INDEX, compares to 0x0224C669)
    - 0x0224CD38 ← ldr @0x0224CD14 (B = 0x0224CD08, post-by-cid)
    - 0x0224CD68 ← ldr @0x0224CD42 (C = 0x0224CD3C, has-row-by-cid excluding post 0x0224C7C1)
  - Count imm8 `cmp #0x3C` sites: **0x0224C99A (A), 0x0224CD30 (B), 0x0224CD5C (C)**. ⚠️ patch_lightpulsar's GYREG_COUNT_SITES lists only the first two.
  - A = 0x0224C820, called by BL 0x0224B4F4 and thunk 0x02243A9C (literal 0x02243AA4). Per row: row cid → [sp+0x28]; prefilters `0x0202345C(row cid) >= 2` (if [sp+4]) and `0x022393CC(side, row cid)` (if [sp+8]); walks the zone cards (0x0219CE2C count, 0x0219CAE4 cid); on cid == row cid → `check(side, row cid, ref)` and appends ref → [sp+0x5C+4i], ROW INDEX → [sp+0x15C+4i].
  - B 0x0224CD08(r0, r1, r2 = cid, r3) ← BL 0x0224B53A, 0x0224CCF6: for rows with cid == r2 → `post(r0, cid, r3)` until nonzero.
  - C 0x0224CD3C(cid) ← BL 0x0224B074 (inside 0x0224B060: desc[+5] == 2 → has-row → 1), 0x0226BCB6.
  - ⇒ A cid with no row is invisible to all three. Making 0x1649 visible means either ~6 hooks for a virtual row 60, or RELOCATING the table: copy the 60 rows plus one {0x1649, 0x0E, 0x0224C591, 0x0224C6C1} row into ov5, repoint the 4 pool words, set the 3 imm8 to 0x3D. That is pure data with no Thumb (~0x3E0 B of cave; free tail ≈ 0x023AA120 − 0x0239FBD0).
- **RULED OUT: relocating the table.** `patch_lightpulsar.verify()` asserts `cmp rX,#0x3C` at 0x0224C99A and 0x0224CD30 (patch_lightpulsar.py:2523), so changing an imm8 fails a shipped patch. Relocation would also leave the ov3 copy stale for every future row-writing patch.
- **CHOSEN: virtual row 60, four 4-byte hooks that avoid every asserted byte** (scratchpad vrow_sites.py; stock == chain bytes):
  - H4 **0x0224C88E** `ldr r1,=base ; lsls r0,r6,#4` (49A6 0130). A's loop head, reached only by `b` @0x0224C99E and the initial `b 0x224c99a` → cmp → here. Stub: r1 = base, r0 = r6<<4; if r6 == 60, r0 = VROW − base. Resume 0x0224C892 `adds r0,r1,r0`.
  - H5 **0x0224C9A0** `ldr r0,=0x0229DD14 ; ldr r1,[r0,#0x34]` (4863 6B41). A's loop exit, reached ONLY from `bhs` @0x0224C99C. Stub: if r6 == 60, jump to 0x0224C88F (the virtual pass; r0/r1 are dead at the loop head). Else (r6 == 61) set r6 = 60, replay both instructions, and return to 0x0224C9A4.
  - H6 **0x0224CD34** `pop {r3-r7,pc} ; nop` (BDF8 46C0). B's exit, reached from fall-through (r4 == 60) and `bne` @0x0224CD2C (r4 < 60). Stub: if r4 >= 60 and r5 == 0x1649, r0 = post(r6, r5, r7). Then the same pop.
  - H7 **0x0224CD60** `movs r0,#0 ; pop {r3,r4,r5,pc}` (2000 BD38). C's not-found exit, fall-through only; r0 still holds the input cid (the loop never writes r0). Stub: r0 = (r0 == 0x1649), then the same pop.
  - D reads base+60·16+0xC = 0x0228E1C4 = 0x0224EB3D, not 0x0224C669, so it takes the generic path 0x0224CBC2 (ref only). The stored row index is consumed only at 0x0224CBAA..0x0224CBE6.
  - After A's exit, r6 is rewritten on every path (0x0224C9D2 `movs r6,#0`, 0x0224CB7A `ldr r6,=`), and H5 restores 60 anyway.
  - KB ov3 proofs run on the STOCK reference_files/nds_overlay_3.bin (knowledge/env.py), so `dispatch.gy_action_registry`'s pin on 0x0224C88E is unaffected.
  - VROW (16 B, ov5) = {0x1649, 0x0E, 0x0224C591, 0x0224C6C1}, Glow-Up Bulb's row with the cid changed.
  - ⚠️ Blast radius: A runs for every GY action scan, so in a PUZZLE (ov5 evicted) this crashes GY action menus. The user accepted normal-duel-only when choosing "Share a row".
- **COST (c), PROVEN by disassembly:** `0x021EBA34` is the native "send the top N cards of your Deck to the GY" COST (+10 of Naturia Rock 0x1F09 cls2[395], Lightsworn Barrier 0x1E54 cls3[421], Naturia Beast 0x1F21 cls3[466], Charge of the Light Brigade 0x1EBC cls0[986]).
  - It returns 1 at once if `0x021D2BC8(desc)` (cost already settled). Otherwise N comes from a cid switch (0x0D63→3, 0x0DBC(=0x1E54−0xA7... per arms)→4, 0x1E54/0x1EBC→2/3, 0x1F21→2), with **default N = 1**. Then `0x021D2168(desc[+2], N)` and return 1.
  - 0x021D2168 → 0x021D2094(side, N, 0, 0, [sp] = 0). Hidden Armory 0x1D45 cls0[923] +10 0x021EB190 also calls 0x021D2168(side, 1) as its "send the top card" cost.
  - ⇒ **+10 stub = if 0x021D2BC8(desc) return 1; post 0x021D2584(side, 0x1649, 5, 0); tail-call 0x021EBA35.**
  - The resolver-side mill 0x021D2148 has 27 callers, all resolvers (blscan.py). 0x021D2178 (r3 = 1) is the FLIP banish-top-3 cost (Lady Assailant of Flames).
- **TIMING CLASS, no arm needed (PROVEN by precedent + disassembly note):** timing_class_hook.py records that the GY-action offer 0x021EDC72 short-circuits +0C only for class 2. An unrecognised +10 (Grapha / Zephyros 0x021EB1B1, Jet Warrior C2 cave stub) leaves a GY cls2 record at class 0, and that is in-game confirmed correct (Grapha 2026-09-07). A cave pointer at our cls2 +10 gets the same class.
- **GY self-SS resolver 0x0220731C(desc, r1)** is SINGLE-SHOT: `0x021AD870(side)` gate, a per-cid switch, then `0x021B9EC0(side, r4)`, locates the card by desc[+0xC] ref (zone must equal desc[+3]), `0x0226925C(side, loc, faceup r6 = 1, pos r4 = 2, [sp] = cid<<16)`, `[0x0229AAFC+0x74] = 1`, return 0. An unlisted cid takes the defaults (face-up, player's choice).
- **CONDITION (a) building blocks, PROVEN by disassembly:** the on-field counter `0x021ACFE8(side, pred, exclude_zone, faceup_only)` (KB stat.gy_setcode_counter) does, per zone r4:
  - `cid = 0x021A3320(side, zone)` (0 = empty)
  - `rec = 0x0229AC94 + 0xB3C*side + 0x14*zone`
  - skip if `[rec+0x44]` bit 1 or bit 21
  - face-up iff `u16 [rec+0x3C] != 0`
  - then `blx pred(cid)`
  The stub mirrors these reads for zones 0..4, adds IS_SYNCHRO 0x02023050(cid) and the LIVE level `0x021B807D(side, zone, 0) >= 7` (reader per dispatch.level_rider_key_is_a_selector), then chains Bulb's f1 0x021F7B75(desc, arg). Controller side = (desc[+2] ^ desc[+6]) & 1, the same side Bulb's f1 uses for the Deck.
- **LEVEL SET rider MEASURED 2026-09-15** (scratch/revsyn_level_probe.py: thumbemu runs the getter 0x021B807C over rom_accel.ml4, Accel Synchron base Level 5, rewriting only node 11): {key **0x1EC1**, kind 3, value 1 / 2 / 7} → Level **1 / 2 / 7**. {key 0x18D9, kind 3, any value} → 5 (no effect at kind 3). ⇒ rider = `0x021C479D(side, slot, 0x1EC1, 3, [sp] = 1)`.
- **RESOLVER (d) design: mirror Psi-Reflector C2's in-game-confirmed phases.** In patch_psi_reflector.c2_res_stub, phase 0x80 = CHAIN_PUSH 0x021D28A5 + revive, returning 0x7F. Phase 0x7F = `LOCATE 0x021A241D(ref)`, which REQUIRES slot < 5 before its picker. The user saw the picker, so the monster was on the field in the very next phase.
  - Ours: 0x80 → CHAIN_PUSH, `0x0220731D(desc, r1)` (always returns 0), return 0x7F. 0x7F → `LOCATE(desc[+0xC])`; if slot < 5, write the rider. Then CHAIN_POP 0x021D2965, return 0.
  - **Ref space PROVEN:** LOCATE 0x021A241C walks both sides' zone words at player+0x34+0x14·z and compares r0 with `(w>>14 & 1) + ((w>>23 & 0xFF) << 1)`. 0x0220731C uses desc[+0xC] as `0x0229C33C[ref*8]` and `0x021A220C(ref)`, the same instance-ref space as Psi's GET_TARGET 0x02234964 (entry >> 5).
  - **ASSUMED (the one analogy):** 0x0220731C's commit 0x0226925C completes before phase 0x7F the way Psi's 0x02204730 revive did. Distinguishable failure if wrong: summoned at Level 3.
- **cls2 record slot:** phantom **0x164F** = chained cls2[123] (stock [124]), exactly at 0x1649's sorted index (0x1642 < 0x1649 < 0x1653), so the in-place cid rewrite shifts ZERO records. No card_prop, unclaimed, one record in stock and chain.
  - Its other mentions: revival list 0x0226DBBC[38] (left alone; self-GY revivers Bulb / Spore / Plaguespreader / Quillbolt / Jet Synchron are NOT members, so Revolution stays out), u32 literals 0x0219F4FC / 0x0219F9B0 (a phantom's own code arms, unreachable), and 2 ambiguous ARM9 data hits.
- **Enumerator row prefilter 0x022393CC(side, row cid), EXECUTED** (scratch/revsyn_gyprefilter_probe.py, thumbemu over rom_all_patches.ml2..ml7, both sides; ml1 is not a duel): returns 0 for 0x1649, Jet Synchron 0x224C (GY ignition in-game confirmed), Glow-Up Bulb, Spore, Quillbolt and Plaguespreader alike. In that mode ([sp+8] = 1) no GY ignition is listed; in the others the donor behaves identically. The other prefilter 0x0202345C (mode [sp+4]) is ARM code, a cid → card-kind read. The donor is "Tuner Monster", the same card_type as Jet Synchron → ASSUMED equivalent.
- **C2 IN-GAME CONFIRMED BY USER 2026-09-15** on sha256 2e4156e3...ed170, reply verbatim: "All confirmed Ship it" (oracle items 10-15 of _build_revolution_synchron.py, incl. the C0/C1 regression item 15). Shipping approved → steps.STEPS + SHIPPED.
- **SHIPPED 2026-09-15:** step "Acrobat Monkey -> Revolution Synchron (the whole card)" after Naturia Pineapple, plus `_verify_all_patches.SHIPPED`. EE build **69/69** in 191.3 s, exit 0, rom_all_patches.nds sha256 **39f75f5b1c3a82ce6bd53b416f4787ab3a65b2a767ba74374c904e136ae8d9b8**. Verify sweep **57 passed, 0 failed** (incl. lightpulsar / grapha / jet_synchron / jet_warrior / steam_synchron / revolution_synchron). The previous chain ROM was copied to the session scratchpad before the build.
- C2 build record (user approved the plan: "I approve go ahead").
  - `_build_revolution_synchron.py`: allocation guard OK; verify **36/36 PASS**; sha256 **2e4156e36fc9df45680bd74ee624a4d3acabf8c5793c081596a5fb13de2ed170**. NOT in steps.STEPS (Step 0 still unanswered).
  - Slots: VROW 0x0239FBD0 (16 B), GYFETCH 0x0239FBE0 (20 B), GYEXIT 0x0239FC00 (24 B), GYPOST 0x0239FC30 (28 B), GYHAS 0x0239FC60 (20 B), C2COND 0x0239FC80 (124 B / 0x80), C2COST 0x0239FD00 (40 B), C2RES 0x0239FD30 (92 B). CAVE_FREE = 0x0239FDA0. Phantoms cls2_table 0x164F and ignition_cond_registry 0x1748 claimed; `check_allocations --emit` gives 249 ov5 slots, 246 phantom claims.
  - All 7 stubs disassembled, with every literal-pool word and BL target checked by hand (see the session log).
  - **Offline (scratch/revsyn_c2_offline.py):**
    - The built ov3 differs from stock in 51 bytes, all inside {7 hook sites, the cls2 record, the ignition registry}.
    - thumbemu with the hooks and caves injected into rom_all_patches.ml2 RAM: has-row 0x0224CD3C (through H7) returns 1 for 0x1649 / 0x2387 / 0x1E5A and 0 for 0x1234.
    - The C2 condition over every duel savestate returns 1 exactly on boards with the side's face-up Synchro at live Lv ≥ 7: 0x1EDA Lv7, 0x126F / 0x1E36 / 0x1E12 Lv8, 0x24B1 Lv9, 0x239F Lv12. It returns 0 with only Lv4-6 Synchros (0x1F33, 0x11A3, 0x2338, 0x1D7C, 0x2474) and for a Lv7 non-Synchro (0x12B2).
    - rom.ml1 side 0 (three Stardust Lv8, **Deck 0**) returns 0 through Bulb's f1 Deck check, the user's empty-Deck ruling, measured.
  - NOT tested offline: the enumerator hooks H4/H5 and post H6 (they need a full menu frame), the cost, and the resolver phases. The in-game test covers them.
- **Once per Duel = turn-log kind 5**: KB `dispatch.turnlog_once_per_duel_is_kind_5` is VERIFIED (closed sweeper proof) and corroborated in-game by Unknown Synchron. It is distinct from C1's kind 1 (the node search matches key AND kind).
- **GY-action registry 0x0228DDF8 (60 rows, unsorted, linear, cannot grow): family {zone 0x0E, 0x0224C591, 0x0224C6C1} has NO phantom rows left** (scratchpad bulb_dump.py over the stock and chained ROMs). Chained rows 15 → 0x1961 grapha, 33 → 0x23EB jet_warrior (a REAL card's row, Sword of Sparkles, user decision 2026-09-04), 47 → 0x0FB1 lightpulsar, 48 → 0x224C jet_synchron. Every other row is a real cid. **A GY ignition for 0x1649 needs a user decision: spend another real card's row, or add an ov5 scanner hook.**
- **NATIVE TEMPLATE = Glow-Up Bulb 0x2387.** Printed: "If this card is in your GY: You can send the top card of your Deck to the GY, and if you do, Special Summon this card. You can only use this effect of "Glow-Up Bulb" once per Duel." Records (stock == chain except the cls2 index):
  - cls2[619] stock / [617] chain: +04 0x0222D1AD, +08 0, +0C 0x021F0BDD, +10 0x021E81E5, +14 0
  - ignition-condition registry row 120 @0x0227009C: {0x2387, 0, f1 0x021F7B75, f2 0x021F44D9 (once per Duel, kind 5)}
  - GY-action row 50 @0x0228E118: {0x2387, 0x0E, 0x0224C591, 0x0224C6C1}
  - Spore 0x225B shares +0C 0x021F0BDD and f2 0x021F44D9 (cls2[561], igncond[110], gyreg[41]).
- **Resolver 0x0222D1AC** (disassembled): phase [0x0229AAFC+0x70]. At 0x80, on desc cid: 0x20F8 → `bl 0x022078FC(desc,3,0)`; **0x2387 → `bl 0x021D2148(desc, side=desc[+2], 1)`**, and a zero result returns 0 (abort, the "and if you do"), else 0x7F. Any other cid returns 0x7F. At 0x7F → `bl 0x0220731C`, the shared GY self-SS resolver. Literals are at 0x0222D1F8 (0x0229AAFC), 0x0222D1FC (0x20F8) and 0x0222D200 (0x2387).
- **Bulb's other slots, disassembled (scratchpad dis.py, stock ov3):**
  - `+0C 0x021F0BDC`: binary search `0x02022E44(cid, 0x0226FAFC, 0x92, 0xC)`. A miss returns 0 (never offered). On a hit it returns `f1(desc, arg) && f2(desc, arg)`. **The donor needs a row in 0x0226FAFC** (sorted, count = imm `movs r2,#0x92` @0x021F0BE6).
  - `f1 0x021F7B74` (Bulb): `0x021BA9AC(desc[+2])` != 0 AND **Deck count** `[0x0229ACA4 + 0xB3C*((desc[+2]^desc[+6])&1)]` != 0 (0x0229ACA4 = PLAYER+0x10). **This natively implements the user's empty-Deck ruling.**
  - `f2 0x021F44D8`: `0x021A14E8(side, 0xB, cid, 5)` != 0 → 0, else `0x021F04FC(desc, arg)`.
  - `+10 0x021E81E4`: `0x021D2584(side, cid, 5, 0)` ; return 1. The kind-5 stamp at activation, costless. **Bulb sends the top card at RESOLUTION** (resolver phase 0x80), not as a cost.
- **Ignition-condition registry 0x0226FAFC, chained ROM** (scratchpad gyrow_survey.py): still sorted. Rows with no card_prop:
  - [6] 0x0E3E
  - [7] 0x0E7D
  - [8] 0x0E86
  - [9] 0x0EA9
  - [10] 0x0EAE
  - [22] 0x1748
  Only upstart_golden_ninja has claimed this pool (0x1446 / 0x1464). The donor 0x1649 sorts between [20] 0x1631 and [21] 0x165C, so **dropping 0x1748 shifts exactly one row** (0x165C, 21→22). Preferred phantom.
- **Level "becomes 1" precedent:** Psi-Reflector C2 (in-game confirmed 2026-09-15) writes the rider from its OWN resolver in a later phase (0x7E), using LOCATE on the summoned card and then `0x021C479C(side, slot, key, 3, N)`. So no summon_rider_hook arm is needed. Per `dispatch.level_rider_key_is_a_selector` (VERIFIED, measured by the A/B on a kind-3 node), key **0x1EC1 = SET** arm (key 0x22EB = DELTA). `rider.turn_sweeper` frees kind 3 only for keys 0x18D9 / 0x1F6A, so a {0x1EC1, 3, 1} node should persist. **UNVERIFIED for this card:** run scratch/accel_level_probe.py with key 0x1EC1 value 1.
  - ⚠️ So the native Bulb timing differs from the user's ruling (cost). A cost version moves the send into +10, and a cave pointer in +10 needs a timing_class_hook arm (`timing.class_is_the_slot4_literal`).

## Confirmed (this session)
- **Not in the 3DS build.** A CARD_Name_E walk for "Synchron" finds Junk, Nitro, Road, Turbo, Hyper, Quickdraw, Drill, Changer, Explorer, Formula, Fleur, Bri and Unknown, with no Revolution. There is no Konami implementation to copy.
- **Synchron list 0x0209C968 is full of real cards** (KB `archetype.synchron_list_is_full_and_has_a_stale_member`, re-read). Claimed slots per check_allocations.PHANTOM_CLAIMS:
  - 0x2501 unknown_synchron
  - 0x0D6B accel_synchron
  - 0x1E4E assault_synchron
  - 0x229E steam_synchron
- **Dropping 0x2414 breaks one shipped assertion:** `patch_steam_synchron.SYNCHRON_CORE` (lines 247-248) lists it, and the check runs at build @392 and in `verify()` @524. It must be removed from the tuple. `patch_jet_synchron.py:99` only mentions 0x2414 in a comment (leave-tree simulation list).
- **Donor Acrobat Monkey 0x1649** (Normal Lv3 EARTH Machine 1000/1800):
  - `donor_scan --free --level 3 --race Machine` on the stock image lists it as the ONLY clean Lv3 Machine Normal.
  - Grep of check_allocations, allocations.yaml and finished_patches: no claims. It is only named in grapha/darkflare notes as a test card.
- **Donor 0x1649 is clean in the CHAINED rom_all_patches.nds too** (scratchpad chained_donor_scan.py, 2026-09-15):
  - arm9: 1 aligned hit in both stock and chain (the same instruction-region hit donor_scan already classifies).
  - ov3: the one hit moved from 0x0227EC70 (stock) to 0x0227EC58 (chain). Its bytes `49 16 1f 02` are the pointer **0x021F1649** at cls0 record[64]+0xC, shifted one record by a count-neutral insert. It is a function pointer, not a cid.
  - 0x1649 is not in card_text.CARD_TEXT.
- **Chained Synchron list** (pool 0x0209C968, `movs r2,#0x0F`), with **0x2414 at index 14**:
  0x11A3, 0x12B6, 0x13AE, 0x181C, 0x1E07, 0x1E14, 0x1EA1, 0x1EBE, 0x1F46, 0x20F7, 0x21A7, 0x224C, 0x239E, 0x23EE, 0x2414.
- **There is no "Power Tool" set code** in archetype_setcode_tables.yaml. Power Tool Dragon = 0x1FC9 (notes/sea-lancer-findings.md:674).

## C0 build (2026-09-15) — superseded by the C0+C1 build, in-game confirmed by user 2026-09-15
- `_build_revolution_synchron.py`: check_allocations clean → `patch_revolution_synchron.main` → verify 6/6 PASS.
  sha256 `50a73b01042745fca93c1d353e945a1e36641864e133f1e887f755effb1d8d5c`, output rom_revolution_synchron.nds.
- Shared-list regression: `patch_revolution_synchron.main` applied on top of a copy of rom_all_patches.nds (scratchpad chain_plus_rev.nds). verify() PASS for:
  - unknown_synchron
  - steam_synchron (after removing 0x2414 from SYNCHRON_CORE)
  - accel_synchron
  - assault_synchron
  - jet_synchron
  - revolution_synchron
  This is a targeted check, not the full sweep; the card is not in the chain.
- Edits:
  - card_text.CARD_TEXT[0x1649]
  - patch_steam_synchron.SYNCHRON_CORE (−0x2414)
  - check_allocations PHANTOM_CLAIMS (+synchron_setcode_table 0x2414, +donor_cid 0x1649), ledger re-emitted

## C1 — Confirmed by static disassembly this session (scratchpad synchro_driver.asm, tdis.py over ygo_tools/reference_files/nds_overlay_3.bin)
- **Closed BL scan** (arm9 + ov3, two-halfword BL/BLX):
  - INNER 0x0224829C ← only 0x022485D8 (OUTER) and 0x02248AAC (THIRD).
  - THIRD 0x02248A88 ← only 0x02249C98 and 0x02249D96.
  - OUTER 0x022485B4 ← only 0x02249CC8 and 0x02249D12.
  - All six sites are inside validator 0x02249AFC.
  - Validator 0x02249AFC ← 0x02249614 (can_synchro loop), 0x02249986 and 0x022499CE (both in level_sum 0x0224966C).
  - level_sum 0x0224966C ← 0x02249A98, 0x02249E38, 0x022635B2, 0x022635CE.
  - can_synchro 0x02249540 ← 0x0223BF76, 0x0223D214, 0x0225E612.
  - "offer loop 0x022495B0" is NOT a function: it is mid-body of can_synchro 0x02249540 (the `movs r2,#1` at 0x022495B0 follows code at 0x022495AE).
- **THE ENGINE ALREADY HAS A HAND-MATERIAL MODE**, gated by `bl 0x022494EC` (result nonzero):
  - Validator 0x02249AFC(r0 side, r1 zone kind → r6, r2 idx):
    - @0x02249B12: `bl 0x022494EC` → [sp+0x14]. If nonzero, branch to 0x02249BE0.
    - Requires side == 0x0229ABFC+0x6C & 1, **r6 == 0xB** (hand), and **selected count 0x0229ABFC+0x7C == 1**.
    - Reads the hand ref at player(0x0229AC94 + 0xB3C*side) + 0x124 + 4*idx, turns it into an instance index, and gets the cid from table 0x0229C33C.
    - Rejects if `0x021AEA7C(cid, -1)` is nonzero.
    - If the FIRST pick's cid (u16 0x0229AA58[0x0229A9FC+0x58]) is **0x2353**, also requires `0x02023E7C(hand cid)`.
    - Falls through to the normal Tuner/non-Tuner tests and calls THIRD with r2 = 0xB.
  - Validator tail @0x02249DE0: for r6 == 0xB the level comes from `0x021B20AC(side, ref)` instead of `0x021B8064(side, idx)`. Then `0x02249A0C(side, 0xB, idx, lvl)` (which returns early for 0xB @0x02249A24), then level_sum `0x0224966C(side, 0xB, idx, lvl)`.
  - level_sum 0x0224966C @0x02249924: `bl 0x022494EC`. If nonzero, loops r4 over hand count player+0xC and calls `validator(side, 0xB, r4)`. Otherwise it loops the 10 field slots.
- **0x022494EC = "hand-material mode"** (leaf, `bx lr`): returns 1 iff count 0x0229ABFC+0x7C != 0 AND the FIRST pick's cid ∈ {0x0E66 (no card_prop), **0x2184 Eccentric Boy**, **0x2353 Malefic Parallel Gear**}.
  - Only two BL callers exist: 0x02249924 (level_sum) and 0x02249B12 (validator).
  - 0x02023E7C = has-set thunk for list 0x0209C7A2, count 10 (the Malefic cards). Parallel Gear's hand partner must be Malefic.
  → **NATIVE PRECEDENT for hand Synchro Material: Eccentric Boy / Malefic Parallel Gear.** In both, the SPECIAL card is the first (field) pick and the hand card is the 2nd pick (count == 1), a non-Tuner.
- **Synchro procedure 0x02263494** (state machine, step u16 at 0x02298A28+0x24; scratchpad synchro_proc.asm):
  - step 0 @0x022634C4: init. Synchro cid from [0x02298A28+0xE], side from +0xC, required count via 0x02248248, count/0x0229AC7C cleared, remaining level = Synchro level.
  - step 1 @0x02263500: `bl 0x0224B9F0(r0=[r4], r1=synchro, r2=0, r3=0x02249AFD validator)`, a generic picker with the validator as callback.
  - step 2 @0x0226350E: `bl 0x0224BBB0`. Pick location = side 0x0229DD94+0x78, kind +0x7C, idx [0x0229DE14]. **kind 0xB → level via 0x021B20AC(side, ref)** @0x0226353A, else 0x021B8064.
  - step @0x0226362C: `ref = 0x0219CBB8(side, kind, idx)`, remaining level -= lvl, count++, ref stored in 0x0229AA58 list. If remaining != 0, loop back to picking.
  - commit loop @0x022636E2: per pick, `0x021A241C(ref)`. If >= 0 (field) → bit (zone + side*16) set in [sp+0xC]. If < 0 → r5 = 0xB, `0x021A25A0(side, ref)`. Then `0x021CF768(desc sp+0x74, bitmask)` @0x02263956 for field picks.
  - hand-send step @0x0226395C: per pick, `0x021A25A0(side, ref)` (≥0 = still in hand) → anim cmd 0x4D via 0x021C3BC8 → **`0x021C6E74(side, hand idx)`**, re-entered each frame until no hand pick remains. Then anim 0x4E.
- **Picker UI cell predicate** 0x0224BC40(r0 side, r1 kind, r2 idx):
  - Gated on 0x0229DD94+0x54 != 0. Switch on picker mode 0x0229DD94+0x4C, cmp #9. Jump table i16 at 0x0224BC68, target = 0x0224BC6A + entry.
  - Modes: 0 → 0x0224C280 (reject), 1 → 0x0224BC7C, 2/3 → 0x0224BCBE, 4/5 → 0x0224C10E, 6 → 0x0224C114, **7/8 → 0x0224C1A2**, 9 → 0x0224C1CE.
  - `0x0224B9F0` (Synchro procedure step 1) sets **mode 8** and callback [0x0229DE14+0xC] = 0x02249AFD. Mode 9 comes from 0x0224BA34.
  - Mode 8 body 0x0224C1A2: callback NULL → reject. **kind == 0xB → require idx < hand count [player+0xC] (0x0229ACA0 + 0xB3C*side)**, then `blx callback(side, kind, idx)` @0x0224C1CA, result returned.
  - **So the Synchro picker offers a HAND card whenever validator(side, 0xB, idx) returns nonzero.** Static proof; the path is not yet GDB-traced.
- **Synchro procedure step table** (i16 at 0x022634AE, target 0x022634B0 + v):
  - 0 init 0x022634C4
  - 1 picker 0x02263500
  - 2 read pick 0x0226350E
  - 3 commit pick 0x0226362C
  - 4 commit loop + field bitmask send 0x022636C6
  - **5 hand-send 0x0226395C** (step := 6, then the first pick still in hand → `bl 0x021C6E74` @0x022639AA → return)
  - 6 anim 0x4E 0x022639BA
  - 7-9 done 0x022639F8
  - 10 0x02263606
  So **0x022639AA is reached once per Summon, exactly when a hand material is sent**. 0x021C6E74 is the "→ GY 0x0E" wrapper (KB event_queue).
- **OUTER's per-Synchro Tuner rules for the candidate targets** (scratchpad outer_leaves.py: scratch/thumbemu over stock arm9+ov3, entry 0x02248660 with r5 = Synchro cid; control Junk Synchron → generic):
  - Generic `return 1` @0x02248A72: Power Tool Dragon 0x1FC9, Dark End 0x1CCB, Light End 0x1CCC, Stardust 0x1E36, Red Dragon Archfiend 0x1E37, Black Rose 0x1EDA, Ancient Fairy 0x1F9A, Exploder Dragonwing 0x2000, Gungnir 0x2046, Black Brutdrago 0x211E, Black-Winged 0x226F, Scrap Dragon 0x230E.
  - Race must match (`0x021B8E30(side, zone, race(synchro))`, a FIELD read) @0x022489A8: Dragunity Knight - Trident 0x2180, Dragunity Knight - Barcha 0x221B.
  - Attribute must match (`0x021B938C(side, zone, attr(synchro))`, FIELD) @0x02248998: Hundred Eyes Dragon 0x219C, Infernity Doom Dragon 0x2271.
  - Named-material table 0x02275B04 (OUTER checks it first @0x02248608): only row {0x21CD Sun Dragon Inti, 0x21B7} hits a target, so Inti needs that named Tuner.
  - LIST 0x02275AD8 / LIST_A 0x02275AB8: no target.
  - **Consequence:** a hand path that skips OUTER must DENY {0x21CD, 0x2180, 0x221B, 0x219C, 0x2271}. EARTH Machine Revolution fails all five natively.
- "Power Tool" in OTN card_prop = only 0x1FC9 (Level 7 Machine). Lv7/8 Dragon Synchros in stock card_prop: the 16 listed above.
- Chained rom_all_patches vs stock ov3 diffs over 0x02248248-0x02249F00 / 0x0224B9F0-0x0224C440 / 0x02263494-0x02263A00:
  0x022482B2..B9, 0x02248564, 0x022485D8..DA, 0x02248778, 0x02248AAC..AF, 0x02248CAA, 0x0224938E..91, 0x02249D26 (Shooting Quasar, 0x211B only), 0x0224C026 (hand-SS trampoline).
  **Not touched: 0x02249B12, 0x02249626, 0x022639AA.** No hits in allocations.yaml / finished_patches either.
- Pick list: level_sum appends `0x0219CBB8(side, kind, idx)` as u16 to 0x0229AA58[(0x0229A9FC+0x58 + count) & 0x7F]. Count is 0x0229ABFC+0x7C; remaining level is 0x0229AAFC+0x74.

## Inherited, UNVERIFIED until re-checked (from the KB/memory survey)
- Offer loop 0x022495B0 walks 10 field zones. can_synchro_summon 0x02249540. Per-slot validator 0x02249AFC. Level-sum 0x0224966C.
- The Tuner test 0x021A1C7C reads a field slot.
- Commit: `bl 0x021CF768` @0x02263956, r1 = field-zone bitmask (bit = zone + side*16).
- INNER 0x0224829C computes a hand flag (zone_kind == 0xB). Sphreeze leaf 0x02249360 has a hand path. No known caller passes 0xB.
- Synchro cid during selection is at 0x0229ABFC+0x68.
- Once per turn: turn-log POST 0x021D2584 / QUERY 0x021A14E8, cid-keyed (KB VERIFIED `dispatch.turnlog_once_per_turn_pair`).

## Ruled Out
- **ARM9 cave for a relocated list.** The xsaber_table.py docstring records that ARM9 has no truly dead cave (a relocation broke Deep Diver). The ov5 relocation was viable (Psi-Reflector precedent) but declined by the user in favour of dropping Bri. Do not reopen.
- **"C1 needs a new hand pass through the offer loop, Tuner test and commit."** Killed by the native hand-material gate 0x022494EC and the procedure's hand support (see Confirmed).
- **"offer loop 0x022495B0" as a function.** It is mid-body of can_synchro 0x02249540 and has no BL callers. The inherited label was a loop, not an entry point.
- **Hand Tuner through the native count-0 validator path.** `is_tuner_slot` 0x021A1C7C and OUTER read field slots; with kind 0xB they index garbage (player+0x110+0x14·idx). Hence H1 bypasses to the accept tail 0x02249DA0.

## Open Questions
- ~~Does any caller pass zone code 0xB into INNER / THIRD?~~ ANSWERED: yes, THIRD with kind 0xB in native hand-material mode (Eccentric Boy / Parallel Gear).
- ~~Which "Power Tool" cids exist?~~ ANSWERED: only 0x1FC9.
- Does the AI (CPU) Synchro path reuse can_synchro/validator? Not checked; it only matters if a CPU deck runs Revolution.
- ~~Extra Deck command flag via 0x0225E612 not live-traced~~ ANSWERED live by the user's 2026-09-15 test (item 4).
- **Shipping C0+C1 into steps.STEPS:** asked, no answer yet.
- **C2 leads (all HYPOTHESIS):**
  - GY revive precedent: patch_jet_synchron clause 2 (cls2 + ov5 dispatchers), patch_jet_warrior clause 2.
  - Once per Duel: turn-log kind 5 (`dispatch.turnlog_once_per_duel_is_kind_5`; Unknown Synchron ss_commit_hook row). **Must NOT be kind 1**, which C1 uses on the same cid.
  - "Level becomes 1": `card.psi_reflector_clause2` Level rider 0x22EB kind 3 (that one adds), and Copy Plant 0x1EC1 "becomes" per patch_accel_synchron.py:430.
  - Mill top card: Tuning 0x23A2's resolver.
  - Condition "control Lv7+ Synchro": needs a board scan or a native condition.
  - Rulings (cost vs effect, empty Deck): ask the user.

## More confirmed (static)
- `0x0219CBB8(side, kind, idx)` → card ref. Switch on kind−0xB (i16 table 0x0219CBD0, target 0x0219CBD2 + v): kind 0xB → 0x0219CC5C, 0xC → +0x4E4, 0xD → +0x304, …; kind < 0xB → field path 0x0219CC7E. So it resolves HAND refs.
- `0x0225E612`: the Extra Deck command-flag builder. For cid r4 with 0x02023330 true and 0x0202303C false, it calls `can_synchro(r0 = player r6, r1 = cid, 0, 1)` and sets `r5 |= 4` on success; Fusion goes through 0x0223298C. **So can_synchro gates whether a Synchro in the Extra Deck is summonable**, and H2 is required for "Revolution in hand is the only Tuner".

## C1 BUILT (2026-09-15) — in-game confirmed by user 2026-09-15
- User approved: build the single-card ROM, and deny the 5 targets whose OUTER Tuner rule the hand card can't meet.
- Stubs:
  - CAVE_REVSYN_VALID 0x0239FA10: 232 B, reserve 0x100
  - CAVE_REVSYN_HANDPASS 0x0239FB10: 76 B, reserve 0x60
  - CAVE_REVSYN_STAMP 0x0239FB70: 92 B, reserve 0x60
  - CAVE_FREE moved to 0x0239FBD0; check_allocations `--emit` OK
- Offline (scratchpad c1_offline_check.py, thumbemu with faked callees):
  - No ov3 B/Bcc lands on 0x02249B14 / 0x02249628 / 0x022639AC.
  - H1 passes 15 cases: accept Stardust / Power Tool / Black Rose; reject field kind, count 1, side mismatch, other card, once-per-turn used, non-Dragon, Lv6, Lv9, Inti, Hundred Eyes, Barcha, INNER = 0. sp balanced.
  - H2: sets r6 only via the validator, replays `ldr r0,[sp,#4]` with flags.
  - H3: posts (side, 0x1649, 1) only for 0x1649, then tail-calls the send with r0/r1 restored.
- `_build_revolution_synchron.py`: verify 15/15 PASS, sha256 `f466960d8f9b15fd45c1761d1c0540b9692e84ae7f88479195d86acfb51d44c2`.
- Composition: rev.main on a copy of rom_all_patches.nds changes ov3 ONLY at the 12 hook bytes. verify() PASS for:
  - unknown_synchron, steam_synchron, accel_synchron, assault_synchron, jet_synchron
  - junk_speeder, shooting_quasar, boggart_knight, azure_eyes, tour_guide
  - accel_synchro_stardust_dragon, revolution_synchron
- Proven live by the user's test 2026-09-15 (items 4-5): the mode-8 picker offers hand cells, and the can_synchro hand pass enables the Extra Deck command.

## C1 architecture (as built)
Three ov5 stubs, all hooks unclaimed and stock in the chain:
- **H1 validator** `bl 0x022494EC` @0x02249B12 → stub.
  - If r6 == 0xB, count [0x0229ABFC+0x7C] == 0, r5 == [+0x6C]&1, hand[r5][[sp]] cid == 0x1649, turnlog QUERY(side, 0xB, 0x1649, 1) == 0, the Synchro target qualifies (cid 0x1FC9, or Level 7/8 with race 1, and not in the deny list), and `INNER(synchro, side, 0xB, idx)` != 0:
    return to **0x02249DA1** (the validator's accept tail: level via 0x021B20AC, then level_sum(side, 0xB, idx)).
  - Else tail-call 0x022494EC.
- **H2 can_synchro** `ldr r0,[sp,#4] ; cmp r0,#0` @0x02249626 → `bl` stub. If r6 == 0, try validator(player, 0xB, i) for i < hand count, set r6 = 1 on a hit, then redo the two instructions.
  Needed so the Synchro command is offered when Revolution in hand is the only Tuner.
- **H3 once-per-turn stamp** `bl 0x021C6E74` @0x022639AA → stub. If hand[r0][r1] cid == 0x1649, turnlog POST(side, 0x1649, 1, 0). Then tail-call 0x021C6E74.

## Next Experiment
- **C2 (2026-09-15): the user runs oracle items 10-15 of `_build_revolution_synchron.py` on rom_revolution_synchron.nds sha256 2e4156e3...ed170, in a NORMAL duel.** Report protocol: quote verbatim → MY INTERPRETATION → wait. If summoned at Level 3, check the phase-0x7F assumption (commit not finished → LOCATE misses). If not offered, check H4/H5 (enumerator) with a savestate. If offered twice, check the kind-5 stamp in C2COST (0x021D2BC8 settled path).
- Step 0 (ship into STEPS) is still unanswered: wire nothing.
- (older) DONE: in-game test passed 8/8 (user, 2026-09-15).
- Continuation prompt: `PROMPT_revolution_synchron_clause2.md`.
- Step 0: ask the user whether to ship C0+C1 into steps.STEPS (only on explicit approval).
- C2 first commands:
  - `.venv-1/Scripts/python.exe -m otn_enhanced.knowledge.verify_knowledge` (hand-off: 511 facts, 471 PASS, 0 FAIL, 40 UNVERIFIED)
  - `.venv-1/Scripts/python.exe -m otn_enhanced.tools.donor_scan 0x23A2` (Tuning's records → mill primitive)
- Then read patch_jet_synchron clause 2 and quote the C2 sub-clauses to the user before touching ROM code.

# Assault Synchron — findings

Continuation prompt: `PROMPT_assault_synchron_clause2.md`.
Plan (5 stages): `~\.claude\plans\assault-synchron-remove-synchro-glowing-quail.md`.

Printed text (`scratch/ygoprodeck_cache.json`, id 77202120) — DARK / Machine / Tuner / Lv2 / 700 / 0,
archetype Synchron:

- C1 "During your Main Phase: You can Special Summon this card from your hand, then take 700 damage,
  also you cannot Special Summon monsters from the Extra Deck, except Synchro Monsters, while this
  card is face-up in the Monster Zone."
- C2 "If a face-up Dragon Synchro Monster(s) you control is Tributed or banished (except during the
  Damage Step): You can banish this card from your GY, then target 1 of those monsters; Special
  Summon it."
- C3 "You can only use each effect of "Assault Synchron" once per turn."

## Status (2026-09-14)

| Piece | State |
|---|---|
| Chassis (Synchron membership, stats, text) | **in-game confirmed by user 2026-09-14** |
| C1 hand SS in your Main Phase + 700 damage | **in-game confirmed by user 2026-09-14** |
| C3 once-per-turn for effect 1 | **in-game confirmed by user 2026-09-14** |
| C1 Extra Deck lock ("except Synchro Monsters, while face-up") | **NOT BUILT, dropped by user 2026-09-14** |
| C2 GY revive of a Tributed/banished Dragon Synchro | **in-game confirmed by user 2026-09-14** (build 5 8096806e…cde4, *"Perfect! Ship it!"*) |
| C3 once-per-turn for effect 2 | **in-game confirmed by user 2026-09-14** (test 3 item 1 + build 5 sign-off) |
| C2 "except during the Damage Step" | NOT BUILT — user decision 2026-09-14 |
| Shipping | **SHIPPED 2026-09-14**: `steps.STEPS` step 63/64 + `_verify_all_patches.SHIPPED`; EE build 64/64 sha256 `8e249dacade01cc8fb991fbd32e401d85daecc5a743ed95865e8860d463b2da4`; verify sweep `52 passed, 0 failed` |

User decisions, verbatim:
- Donor: chose **"Shapesnatch 0x13AE"** over the recommended Mechanicalchaser.
- C1 shape question → *"Don't bother with the extra deck lock"*. Read as a hand-menu summon procedure
  (not a chain-link effect) with the lock dropped.
- Moving the hand-SS table → *"Yes, move it (Recommended)"*.
- Making the SS-commit hook shared → *"Yes, make it shared (Recommended)"*.
- Stage 2 test → *"All confirmed. Next phase"* (rom sha256 6ff8927c…c912e).
- **C2 rulings (2026-09-14, C2 session 1):** scope → *"Yes, scope confirmed"* (C2 + C3 effect-2 OPT,
  C1 must not regress); Tributed → *"Tribute summon and tribute as a cost"* (NOT Synchro/other
  material); timing → *"Never misses timing"*; revive → *"Must be properly summoned"*.
- **Ritual Tribute counts (2026-09-14):** *"tribute for ritual summon should count because it is a
  tribute"*. Probe hit→step mapping confirmed by the user: *"Yes"*.
- **Pre-build assumptions A/B/C approved by user 2026-09-14:** *"I approve. Build!"* (A event log
  alive at slot5, B properly-summoned enforced natively, C GY trigger offered / no missed timing).
- **Damage Step exclusion NOT built (user decision 2026-09-14):** *"Build C2 without the damage step -
  there are no instances of banish/tribute in damage step"*.
- Stage 3 test → *"1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed 6. Confirmed
  7. Confirmed 8. Confirmed 9. Confirmed 10. Confirmed"* (rom sha256 fbbf1701…fdf67bf).

## Confirmed

### Stage 1 — Synchron slot (2026-09-14)
- **Not in the NDS and not in the 3DS.** No name match in `scratch/cid_to_name.json`; a scan of the
  3DS `CARD_Indx_E`/`CARD_Name_E`/`CARD_Desc_E` found no "Assault Synchron". No Konami cid, no 3DS
  handler to copy.
- **Synchro Deflector is cid 0x1E4E (7758), a NORMAL TRAP** (ygoprodeck `"type":"Trap Card"`). The KB
  said Spell; corrected in `archetype.setcode_4c_is_monster_only` and
  `archetype.synchron_list_is_full_and_has_a_stale_member`. It's inert because every 0x4C consumer is
  MONSTER-only.
- Synchron list 0x0209C968 (15 x u16, `movs r2,#0x0F` @0x02023E20) slots: 0x2501 unknown_synchron,
  0x229E steam_synchron, 0x0D6B accel_synchron, **0x1E4E assault_synchron**. **No inert slot remains.**
- `patch_steam_synchron.SYNCHRON_CORE` (a survival assertion the ledger cannot see) no longer names
  0x1E4E; it's read only at patch_steam_synchron.py:392 (assert) and :524 (verify).
- Swap helper `patch_unknown_synchron.add_synchron_member(out, insert_cid, drop_cid)`.

### Stage 2 — donor + chassis (in-game confirmed by user 2026-09-14)
- `donor_scan --free --race Machine --attribute DARK` → 0x112A, 0x1145, 0x1279, 0x13AE, 0x1F18 (Striker's
  donor, excluded). No DARK or Machine Lv2 vanilla exists.
- **Shapesnatch 0x13AE:** donor_scan CLEAN apart from one u16 hit at ov3:0x0217EAA0, which is the low half
  of ARM instruction `0xFAFC13AE` = `blx #0x02083960` (capstone ARM disasm 0x0217EA60..0x0217EAD0). Not a
  cid. Not named in `ygo_tools/tools/**`, not a `CARD()` pivot in `data/over_the_nexus/decompiled`.
- Text via `card_text.CARD_TEXT[0x13AE]` (index re-emit). Adding a CARD_TEXT entry does not touch the
  chain: text is written only by a module's own `apply_stats_and_text`; `text_guard` only reports
  clobbers of text it has already seen.
- Ledger: `("donor_cid", 0x13AE, "assault_synchron")`, `("synchron_setcode_table", 0x1E4E, "assault_synchron")`.

### Stage 3 — C1 (in-game confirmed by user 2026-09-14, 10/10 oracles)
- **Hand-SS table was FULL** at 0x0239B1A8: rows (0x1F18, 0x0239B1C9) (0x17CE, 0x0239DEF1)
  (0x181C, 0x0239DF21) (0, 0), and 0x0239B1C8 is code (`0xB510`). Read from rom_all_patches.nds
  sha256 ad96eb4e…. **Moved** to `CAVE_TG_SSTABLE` 0x0239F240 (0x40 B, 7 rows); old slot RETIRED
  (`CAVE_TG_SSTABLE_OLD`). `tg_table.SS_TABLE_BYTES = 0x40`. The old bound also let a 4th row overwrite
  the terminator; fixed.
- **"your Main Phase"** = KB `duel.phase_and_turn_player`: u32 `[0x0229DD14+0x48]` in {2, 4}
  (`ldr r2,[r2,#0x48]` in Apophis 0x021F4EC4) and u32 `[0x0229DD14+0x34] == side` (`ldr r0,[r0,#0x34]`
  @0x02244D12).
- **Damage outside a resolver = `0x021CFB8C(target side, amount, flag, source cid)`** (KB
  `lp.damage_wrapper_outside_resolvers`, VERIFIED). It builds a stack desc and calls
  `0x021CFBC8(desc, side, amount)`. Flag 1 = opponent is the source (Magical Thorn 0x1306 @0x02244CDC),
  0 = self. All 90 direct callers of 0x021CFBC8 were scanned.
- **SS-commit displaced call `BL 0x02244D08` is Chain Energy 0x132C's pay-500-LP cost** (KB
  `summon.ss_commit_displaced_call_is_chain_energy`, VERIFIED). It reads only r0.
- **SS-commit stamp lifted** into `ss_commit_hook.py` (`CAVE_SSCOMMIT_HOOK` 0x0239F280, 76 B stub;
  `CAVE_SSCOMMIT_TABLE` 0x0239F2D0 rows `{u16 cid, u16 kind, u32 damage}`). Retired
  `CAVE_UNKSYN_STAMP`. Rows: (0x181C, 5, 0) Unknown Synchron, (0x13AE, 1, 700) Assault.
- **Equivalence proven by execution:** `python -m scratch.ss_commit_equiv`, 100 inputs x 3 configs.
  Unknown-only table == retired stub on every input; with Assault's row only 0x13AE-from-hand differs:
  `post(side,0x13AE,1,0) → damage(side,700,0,0x13AE) → replay(side)`.
- **Assault cond** `CAVE_ASSAULT_SSCOND` 0x0239F310, disassembled from the built ROM:
  `push{r4,lr}; bl 0x021A14E8(side,0xB,0x13AE,1); bne no; ldr r1,=0x0229DD14; [r1+0x34]==r4;
  [r1+0x48] in {2,4}; bl 0x021AD870 (canSS); pop{r4,pc}`. Table row (0x13AE, 0x0239F311).
- Test ROM (clean → striker → junk_servant → unknown → warwolf → assault): all 5 `verify()` PASS,
  sha256 `fbbf1701894f52a2742731ef6a525f7d52a8d66c2cb19b389c3ef1798fdf67bf`. **Dueled: 10/10 confirmed.**
- Chain after the shared changes (Assault NOT in STEPS): EE build 63/63 sha256
  `53df6240a01e515472a209a34ce0aec1028ebc79895a11b17bd8ff796669251a`; sweep `51 passed, 0 failed`.
  **That chain ROM itself was not dueled.**

### C2 session 1 — static (2026-09-14)
- KB at session start: `TOTAL 482 facts: 444 PASS 0 FAIL 38 UNVERIFIED` (matches handoff).
- `donor_scan 0x2176 0x2458 0x2430-0x2432` (needs `PYTHONIOENCODING=utf-8` for 0x2430):
  Jurrac Herra 0x2176 = cls2 record[511] + u32 literals ov3:0x021C9900, 0x021F0B00. Tanngnjostr
  0x2458 = cls2[666] + cls1[1291] + criteria row[1323] + literals 0x021C9F88, 0x021C5674, 0x02265A1C.
  Meklord Emperors = cls2 + 2x cls3 + alias pairs (poor template: many more structures).
- Pool loaders (`python -m scratch.pool_refs`): 0x021C9900←ldr r5 @0x021C97D6; 0x021F0B00←0x021F0A5A
  (a cid switch, not the trigger); 0x021C9F88←0x021C9D26; 0x021C9C60 (0x2430)←0x021C9B46.
- **Bystander leave triggers are HARD-CODED ARMS inside the leave dispatcher body**, posting the
  bystander's own cid. Disassembly `python -m scratch.dis 0x021C9780 0x90`:
  Jurrac Herra arm 0x021C979E: `[sp+0x44]!=0 && [sp+0x90]!=0 && [sp+0x144]!=0 &&
  u16[0x0229ACCE + (side&1)*0xB3C + [sp+0xA0]*0x14]!=0 && bl 0x02023D38(cid r4)!=0 (Jurrac set) &&
  r4!=0x2176 && bl 0x021A3320(r6,[sp+0xA0])==r4` → `bl 0x021D3648(r6, 0x2176, [sp+0x1C], [sp+0x200])`
  then `bl 0x021D36C0(same args)`.
  Tanngnjostr arm 0x021C9D10 (hand only): `[sp+0x44] && [sp+0x144] && bl 0x02029E60(r4)` →
  `bl 0x021D36C0(r6, 0x2458, [sp+0x1C], [sp+0x200])` only.
  ⇒ **PROVEN** (`python -m scratch.dis 0x021D3648 0x100` + KB `ram_layout` +0x124 hand / +0x55C GY):
  `0x021D3648(side, cid, code, cardword)` loops `i < u32[P+0x14]` over GY array `P+0x55C`
  (P = 0x0229AC94 + (side&1)*0xB3C); for each entry with `word & 0x3FFF == cid` it calls
  `0x021D3168(side<<31 | code<<25 | 0x4E<<16 | cid, (word>>14&1) + ((word>>23&0xFF)<<1), cardword)`.
  `0x021D36C0` is identical over the HAND `P+0x124`, count `P+0x0C`, zone byte **0x4B**.
  So a bystander trigger = one extra `bl 0x021D3648(r6, 0x13AE, [sp+0x1C], [sp+0x200])` in a leave arm;
  the GY copy then needs something that answers the 0x4E post (Herra: its cls2 record[511]).
  Register roles here: r4 = leaving cid, r6 = side word, [sp+0xA0] = zone index, [sp+0x1C] / [sp+0x200]
  = leave descriptor words passed through.
  KB fact **`event.leave_bystander_posters`** added VERIFIED (KB now 483 / 445 PASS / 0 FAIL / 38 UNV).
- **"Tributed" / field-banish templates actually in the NDS** (ygoprodeck text × `cid_to_name.json`):
  Legendary Six Samurai - Shinai 0x2462 ("on the field is Tributed": cls2[669] + criteria[1331]),
  Lich Lord 0x1BEB ("Tributed by a card effect": cls2[272] only), **Sword of Dark Rites 0x1BF0**
  ("When the equipped monster is Tributed" — a bystander on a Tribute: cls2[273] + literal
  ov3:0x021D790C loaded @0x021D779A), D.D. Survivor 0x18BC ("banished while face-up": cls2[172] +
  u16 in a list @ov3:0x0226D3A8). Shinai/Lich Lord have NO code literal → their cid is only reachable
  through a base±imm switch.
- 0x021D779A sits inside a large **base±imm cid switch** (~0x021D7700..0x021D7FA4, default leaf
  0x021D7FA4). Linear disasm there is misaligned (capstone shows `bl` halves) — per
  `thumb-stack-based-switch-footgun`, do NOT read it statically; execute it (thumbemu) for
  cid 0x1BF0 / 0x2462 / 0x1BEB to find their leaves. Function entry + caller not yet found.
- ~~0x021D7348 is the Tribute discriminator~~ RULED OUT: it is `(desc r0, side r1, zone r2)`, reads the
  field card at (side, zone) and switches on u16[desc]; an effect-applicability/target check with 11
  callers. Sword of Dark Rites is in it for "Equip only to a DARK monster".
- cls2 raw: Lich Lord 0x1BEB and Sword of Dark Rites 0x1BF0 = `{resolver 0x02208211, all other slots 0}`;
  Shinai 0x2462 = `{0x02208181, 0, 0x0224A115, 0, 0x02235605}`. No condition slot → the Tribute test is
  upstream of the cls2 record.
- **Leave-tree leaves by EXECUTION** (`python -m scratch.leave_tree_leaf`, image-backed thumbemu from
  TREE 1 root 0x021C8216 with r4 = cid; controls PASS: Minefieldriller 0x2085 → 0x021C8CC4 and
  records-free 0x0FB1 → generic tail `bl 0x021C93D0` @0x021C827A, both as in the KB):
  Lich Lord → `bl 0x021C9108`; Sword of Dark Rites → `bl 0x021C90F4`; Shinai → `bl 0x021C9324`;
  D.D. Survivor 0x18BC → generic tail @0x021C8368; Shapesnatch 0x13AE → generic tail @0x021C829C.
- **"TRIBUTED" = bit 0x1000 of [sp+0xC] at the leave dispatcher — PROVEN (disasm + printed text of two
  witnesses):**
  Lich Lord 0x021C9108: `[sp+0x144] && [sp+0x8] && ([sp+0xC] & 0x1000)` → 0x021C9334 (`movs r0,#1`;
  → str [sp+0x18]) — printed "Tributed by a CARD EFFECT and sent to the GY" = to-GY + by-effect + bit.
  Shinai 0x021C9324: `[sp+0x2C] && ([sp+0xC] & 0x1000)` → 0x021C9334 — printed "on the field is
  Tributed" = left-field + bit.
  Sword of Dark Rites 0x021C90F4: `[sp+0x144] && ([sp+0xC] & 0x200000)` (a different bit, for the equip
  card's own leave). Lich Lord's extra [sp+0x8] test implies bit 0x1000 is ALSO set by a
  non-effect Tribute (Tribute Summon); whether Synchro Material sets it is NOT proven.
  KB fact **`leave.tributed_reason_bit`** added VERIFIED (KB 484 / 446 PASS / 0 FAIL / 38 UNV).
- Dispatcher args (prologue `push {r0-r3}; push {r3-r7,lr}; sub sp,#0x1E8` @0x021C7FD0): [sp+0x200]=r0
  packed leave word; [sp+4]=r1 card record ptr (r4 = [r1]&0x3FFF cid, [sp+0x98] = controller bit,
  [sp+0x94] = u16[r1+8] face-up); [sp+8]=r2 by-card-effect; [sp+0xC]=r3 reason flags;
  r6 = (r0>>9)&1 side; [sp+0xA0] = (r0>>10)&0xF zone.
- **The bystander chain is shared by every TREE-1 leaf:** arms end at 0x021C9334 (`movs r0,#1`) /
  0x021C93CC, → `str r0,[sp,#0x18]` 0x021C93CE → falls into **0x021C93D0**, a LINEAR chain of bystander
  arms that each fall through (0x0E2F → 0x021D3438, 0x0EB7, 0x19AE, 0x0ECC → 0x021D34E0, 0x23EA,
  0x1C68, 0x169F → 0x021D35A0, 0x2318, 0x187F, 0x1971, …, 0x2257 → 0x021D3648 @0x021C972E, 0x227B →
  0x021D3438, 0x18AA, Jurrac Herra 0x021C979E, 0x197D, Tanngnjostr 0x021C9D10, 0x2486 …). Disasm
  `python -m scratch.dis 0x021C93C0 0x260` / `0x021C9700 0x80` + the branch-target scan (every branch
  into 0x021C9756/0x021C979E comes from the preceding arm). ⇒ ONE hook in this chain sees every
  leaving card that took TREE 1 (KB: TREE 1 is straight fall-through from the prologue).
  Other posters seen, roles unmapped: 0x021D3438 (r0=[sp+0x98]), 0x021D34E0 (r0=cid, no side),
  0x021D35A0 (r0=[sp+0x98]).
- Responder records: Herra cls2 `{0x0221E9DD, 0, 0x021F9551, 0x021E51E5, 0}`; Tanngnjostr cls2
  `{0x02206ABD, 0, 0x021F0A39, 0x021E51E5, 0}` — shared slot4 0x021E51E5; 0x021F0A38 is a per-cid
  slot3 switch naming 0x17C9/0x18EC/0x1D3C/0x2176/0x2352. The poster passes the leaving card's packed
  word as the card-word arg of 0x021D3168 → "those monsters" probably rides in the event descriptor
  (UNVERIFIED — check which descriptor field 0x021D3168 stores r2 in; KB `event.word_decoder`).
### C2 session 1 — response side (static, 2026-09-14, while the user runs the GDB probe)
- **Zone codes (KB `ram.container_for_zone_code`): 0x0B hand, 0x0C Extra, 0x0D DECK, 0x0E GY,
  0x0F BANISHED.** So `[sp+0x28]` (dest == 0xD) is most likely "returned to the Deck", NOT banish —
  the handoff's "field banish = dest 0xD" expectation is probably wrong; a field banish should show
  dest 0xF. The probe logs the raw nibble; `leave.descriptor_slots` stays UNVERIFIED until then.
- GY poster word `0x4E<<16` = zone bits 16..20 = 0x0E + class bits 21..23 = **2** (KB
  `event.word_decoder`), event code = [sp+0x1C] (0x1D for a non-battle leave). ⇒ Assault's GY copy
  answers through a **cls2** record. desc[+0x20] = the posted card word = the leaving card's leave word.
- **Precedent records** (raw dump, stride 24; slots {+04 resolver, +08, +0C cond, +10 cost, +14 target}):
  Mezuki 0x1CBF cls2[296] `02207191 0 021F0BDD 021E5709 02235605` ("banish this card from your GY,
  then target 1 Zombie in your GY; SS"), criteria row[609] handler 0x0223ED2D word 0x10010002;
  Dawn of the Herald 0x2282 cls2[568] `02208181 0 0 021E5201 02235605`, row[1171] 0x02242A81;
  Brain Crusher 0x1726 cls1[356] `02207191 0 021F03B5 021E50DD 02235605`, row[272] 0x0223E649 word 0;
  Fabled Dyf 0x20C9 cls1[1048] `02207191 0 0 021E5201 02235605`, row[980] 0x02241C79;
  Miraculous Descent 0x1A36 cls0[719] `02207529 0 021F03B5 0 02235605`, row[438] **0x0223E5D1**
  word 0x88010002 (Fairy) — banished-zone target; D.D.R. 0x1D5F row[664] 0x0223E5D1 word 0x00010002.
  Sun Dragon Inti 0x21CD cls2[534] `02207191 0 021F03B5 021E51E5 02235605`.
  KB `dispatch.cls2_gy_revive_resolver` (VERIFIED): cls2 revive = resolver 0x02207191 + picker
  0x02235605, unnamed cids fall to the common body 0x02204730.
- **"Those monsters" native memory = the trigger-event log** (Infernity Reflector 0x228B, "Select and
  SS THAT monster from your GY"): criteria row[1172] handler 0x02242B1D →
  `0x0223C4E8(side, cid, predicate 0x02242AA9, …)`. Predicate 0x02242AA8 (disasm
  `python -m scratch.dis 0x02242A80 0xA0`): `0x02023DA4(cid)` (Infernity set) → for i < u32[0x0229AB7C+0x30]:
  `u8[0x0229A37C+i+0x838] == 0x17` && `(w=u32[0x0229ABD4+i*4]) bit9 == side` && `w bit16` &&
  `w & 0x1FF == candidate ref` where ref = (card>>14 & 1) + ((card>>23 & 0xFF) << 1) → 1.
  ⇒ the leave word's low 9 bits are the leaving card's REF (consistent with bit 9 side / bit 16 battle
  in the leave unpack). For C2 the same walk with code 0x1D + dest 0xE/0xF would pick "those
  monsters". UNVERIFIED: that the log still holds the entry when a cls2 GY trigger's slot5 runs
  (native for Reflector, a trap chained to the event).
- Dawn of the Herald's predicate 0x02242A5C instead tail-calls `0x021A1640(inst, 0x2282, ref)` =
  per-INSTANCE node chain head `u16[0x0229C340 + inst*8]` walked by 0x021A129C — tags that follow the
  card between zones. Writer not found (not needed if the event log works).
- Criteria enumerators are zone twins with one signature `(side, cid, predicate, r3, [sp]=word,
  [sp+4]=flags; flag bit 1 = both players)`: **GY 0x0223C4E8 → per-side 0x0223C1C4**; **banished
  0x0223C6AC → per-side 0x0223C52C** (literals 0x7B4 / 0x0229ACB0 = player+0x1C). Handler
  0x0223E5D1 (Miraculous Descent) = `0x0223C6AC(side, cid, 0, 0, word, 0xC)`.
- Revive body 0x02204730 is called by BOTH 0x02207191 (@0x022072E0) and 0x02207529 (@0x022075D2)
  and branches on the target's zone `cmp r7,#0xF` @0x022047A6 → it has a BANISHED path.
- **Cost "banish this card from your GY" = Mezuki slot4 0x021E5709, cid-agnostic** (disasm):
  `idx = 0x021A2510(desc[+2], desc[+0xC]); if idx>=0: 0x021C7104(side, &P[+0x55C+idx*4], 0); return 1`.
  0x021C7104 → 0x021C7118; that mover's cid gate only guards the "this card is banished" POST.
  Mezuki's slot3 0x021F0BDC bsearches a per-cid table 0x0226FAFC (0x92 x 0xC) — not reusable as-is.
- Hard OPT = KB `dispatch.turnlog_once_per_turn_pair`: query 0x021A14E8(side, 0xB, cid, kind),
  post 0x021D2584(side, cid, kind, 0). C1 uses kind 1 → effect 2 uses kind 2.
- Offer path: KB `event.admission_accepts_recordless` + Herra having ONLY a cls2 record (no
  GY-action-registry row) ⇒ a 0x021D3648 post reaches the GY copy's cls2 slot3 via 0x021D3168 →
  COMMIT 0x021EDA08 → 0x0224AD94. (Herra's native GY trigger working is itself ASSUMED.)
- Predicates: race 0x0202ABB8(cid) == 1 Dragon (KB `card_data.race_accessor_decoded`), is_synchro
  0x02023050(cid) (KB fact @effect_dispatch_tables 0x0223BE40: card_category 0xA/0xB).

### C2 session 1 — GDB probe MEASURED (2026-09-14, user-run, mapping confirmed by user)
Log `scratch/gdb_assault_leave_probe.txt` (session 19:31:49), bp 0x021C93D0, normal duel, turn player 0:
| Hit | Leaving card | Step | [sp+0xC] reason | [sp+8] | dest | other |
|---|---|---|---|---|---|---|
| 1 | Stardust Dragon 0x1E36 z3 | (a) Tribute Summon | 0x11000 (**0x1000 set**) | 0 | 0xE | phase 2, code 0x1D |
| 2 | Stardust Dragon 0x1E36 z1 | (b) Ritual Tribute, Contract with the Abyss 0x1698 | 0x11000 (**set**) | 0x1698 | 0xE | |
| 3 | Contract with the Abyss z7 | spell to GY | 0x10000 | 0 | 0xE | |
| 4,5 | Shadow Ghoul 0x1116 z3, Junk Synchron 0x1E07 z4 | (c) Synchro Material | 0x10000 (**clear**) | 0 | 0xE | |
| 6 | Stardust Dragon 0x1E36 z3 | (d) banished by Dark Core 0x15E9 | 0x10000 | 0x15E9 | **0xF** | [sp+0x144]=0, [sp+0x28]=0 |
| 7 | Dark Core z7 | spell to GY | 0x10000 | 0 | 0xE | |
| 8 | Stardust Dragon 0x1E36 | (e) battle destruction | 0x7 | 0 | 0xE | **phase 3**, code 0x17, [sp+0x44]=1 [sp+0x90]=1 [sp+0x30]=1 |
| 9 | The Masked Beast 0x13E6 z1 | (f) effect destruction by Offerings to the Doomed 0x145E | 0x10010002 | 0x145E | 0xE | phase 4, [sp+0x90]=1 |
| 10 | Offerings to the Doomed z7 | spell to GY | 0x10000 | 0 | 0xE | |
- ⇒ **Tribute bit 0x1000 MEASURED**: set on Tribute Summon + Ritual Tribute, CLEAR on Synchro Material,
  battle and effect destruction. Material cannot false-trigger C2.
- ⇒ **Field banish reaches the leave dispatcher, dest nibble ((w>>19)&0xF) = 0xF.** [sp+0x28] (dest 0xD)
  stays 0 → the handoff's "banish = 0xD" was WRONG (0xD = Deck).
- ⇒ **[sp+8] is the CAUSING CARD's cid** (0 when not an effect), not a boolean.
- ⇒ The leaving card's zone = [sp+0xA0]; [sp+0x9C] = ref (low 9 bits of the leave word match: hit 1
  word 0x..0c18 & 0x1FF = 0x18 = [sp+0x9C]) — consistent with the Infernity Reflector log-walk reading.
- ⇒ **Damage Step NOT answered:** phase u32[0x0229DD14+0x48] = 3 for the whole battle (hit 8) — the
  Damage Step is a sub-state stored elsewhere. OPEN.
- Stub note: the stub dropped the connection at the end (resume failed) — user unpaused manually.

### C2 pre-build facts (2026-09-14)
- Chain head 0x021C93D0 bytes `11980028` (`ldr r0,[sp,#0x44]; cmp r0,#0`), followed by `beq`
  @0x021C93D4 — MEASURED on the live path by the probe. No shipped patch WRITES it (Lightpulsar
  retargets `bl 0x021C93D0` @0x021C827A, which still lands here).
- Shield Warrior 0x1E17 cls2[361] `022134A1 0 021FE559 021E5709 0` and Necro Gardna 0x1C0A cls2[276]
  `0221F9E1 0 021F0BDD 021E5709 0` — the GY-banish cost 0x021E5709 already ships in cls2 records.
  Shield Warrior's slot3 tests `desc[+4] == 0x0E` (damage-calc EVENT), not a step flag.
- Shared slot3 **0x021F03B4** (Inti/Brain Crusher/Miraculous Descent): `0x021F0384(desc,…)` then
  `0x02243FE0(side^desc[6], cid, 0x02234E78(desc))` != 0 → 1 = "at least one criteria target".
- Criteria handler shape (Mezuki 0x0223ED2C / Reflector 0x02242B1C): `(row r0, side r1, r2)`;
  `0x0223C4E8(side, u16 row[0], predicate, r3, [sp]=u32 row[8], [sp+4]=flags)`; GY revive flags = 8
  (Mezuki, Reflector), banished = 0xC (Miraculous Descent, D.D.R.).
- Predicate call inside 0x0223C1C4 @0x0223C4B4: `blx(r0 = owning side, r1 = 0xE zone, r2, r3 = effect
  cid, [sp] = card-word ptr, [sp+4])`.
- Event log: filled by the command handler @0x0219EC92 (copies u16[0x02298C58+2] entries of
  {u16 code, u32 word} into 0x0229ABB4[i] / 0x0229ABD4[i*4], count → [0x0229AB7C+0x30]); zeroed at
  0x021D49AA / 0x021D4A94. When it is snapshotted/cleared relative to a cls2 GY trigger's slot5 is
  NOT proven → ASSUMED.
- Phantoms (scratch/assault_pick_phantoms.py; no card_prop, exactly 1 row, no other table rows, in
  BOTH rom.nds and rom_all_patches.nds, unclaimed): **cls2 0x0E19**, **criteria 0x0EAD** (a known
  dead registry cid, notes/shiens-dojo-findings.md). Rejected 0x1A8A (Zeta Reticulant, cut card) and
  0xFFFE (sentinel-looking).
- Cave: CAVE_FREE = 0x0239F360, room to region end 0x023AA120 = 0xADC0.

### C2 BUILT (2026-09-14) — AWAITING IN-GAME TEST
- `patch_assault_synchron.py` PART D; `_build_assault_synchron.py` (striker → junk_servant →
  unknown_synchron → tg_warwolf → assault): BUILD_EXIT=0, all 5 verify() PASS,
  `rom_assault_synchron.nds` sha256 **f2c72ff424c7167851ce942eafa3c6a50fdbffb95f3bf39b9011b3c4d82c4f4d**.
- Slots: CAVE_ASSAULT_LEAVEHOOK 0x0239F360 (84/0x60), C2COND 0x0239F3C0 (64/0x50), C2COST 0x0239F410
  (28/0x20), C2CRIT 0x0239F430 (60/0x40), C2PRED 0x0239F470 (132/0x90); CAVE_FREE → 0x0239F500.
  Phantoms cls2_table 0x0E19, populate_table 0x0EAD registered; `check_allocations` [OK], ledger emitted.
- Read back from the ROM: cls2 `{000013AE 02207191 0 0239F3C1 0239F411 02235605}` (row 77);
  criteria `{13AE FFFF 0239F431 00010002}` (row 122); crit pool = 0x0239F471; site 0x021C93D0 =
  `d5f1c6ff` then native `08d0` beq. Stubs disassembled (all POPs to PC, no BLX, replay CMP last).
- Puzzle note: the hook runs for every departure in every mode; ov5 is evicted in puzzles. Same
  exposure the shipped T.G. trampoline at 0x021C8216 already has (accepted ov5 default).
- Test sheet: `_build_assault_synchron.py` docstring items 11–20.

### C2 test 1 FAILED (2026-09-14) — diagnosis
- User: *"see ml2 and ml3 before and after banish. Assault Synchron did noy activate"*; clarified:
  Dark Core banished their Iron Chain Dragon; Assault in the GY *"did not prompt nor flash"*; Tribute
  not attempted. Savestates `rom_assault_synchron.ml2` (before) / `.ml3` (after).
- `python -m scratch.assault_c2_ss_probe`: both states are the built ROM (5 stubs byte-exact in RAM,
  site 0x021C93D0 = BL). Iron Chain Dragon = cid 0x1EDB, race 1, is_synchro 1 (executed). Side 0 GY
  holds Assault ref 0x18; ml3 side 0 banished = ICD word 0x17809EDB ref 0x5E. Turn-log kind 2 clear.
  **Event log count u32[0x0229ABAC] = 0 in both.**
- `python -m scratch.assault_c2_exec_probe` (thumbemu over the real RAM, synthetic leave frame =
  measured Dark Core hit with ICD's cid/zone 2/ref 0x5E): on ml3 the path executes hook → why_ok →
  0x021D3648 → 0x021D3168 → COMMIT 0x021EDA14 → 0x0224AD94 → find_event_handler → blx +0C →
  **OUR COND** (passes code/zone/OPT/still-in-GY) → HAS_TARGETS 0x021F03B4 → 0x02243FE0 → OUR CRIT →
  GY + banished builders → OUR PRED ×8, **every call returns 0** → CRIT 0 → **COND 0** → dropped.
  (ml2 stopped at an unsupported ARM BLX in 0x02029BA2 before the banished builder.)
- **RULED OUT (strike 1 on the "those monsters" mechanism): reading the trigger-event log from a slot3
  that runs at ADMISSION.** slot3 is executed inside 0x021D3168 while the leave dispatcher is still
  running; the log is not populated then. Infernity Reflector only works because a Trap's criteria run
  later, in a response window.

- **Card word bit 15 = PROPERLY SUMMONED (1), not "not properly summoned"** — disasm
  `python -m scratch.dis 0x021A2618 0x40` (KB `summon.proper_synchro_check`): `if 0x020232AC(cid):
  return (word>>15)&1 else return 1`. patch_hyper_librarian.py's docstring has it inverted. ICD's
  word 0x17809EDB (field, ml2) and in banished (ml3) both carry bit 15 → properly summoned, revivable.
- **FIX (strike-1 response, execution-backed):** "those monsters" = an ov5 list written by the leave
  hook itself before it posts: CAVE_ASSAULT_C2REFS, 4 x u32 `(turn << 16) | 0x8000 | ref`
  (ref = [sp+0x9C], turn = u32[0x0229DD14+0x40]); newest first, shifted down. PRED = Dragon && Synchro
  && entry == (current turn, ref). COND no longer calls HAS_TARGETS at admission: returns 2 once
  code/zone/OPT/still-in-GY pass. Runtime ov5 cells have shipped precedent (CAVE_LIB_LATCH,
  CAVE_TGW_ARMLATCH, CAVE_AS_LATCH). Known ceiling: a Dragon Synchro that qualified EARLIER in the
  same turn (Assault absent / not activated) is still pickable.

- **Fix proven offline before rebuilding** (`python -m scratch.assault_c2_exec_probe`, current build
  overlaid on ml3's real RAM): hook writes REFS[0] = 0xF805E (turn 15, ICD ref 0x5E) and reaches OUR
  COND at admission, then continues into queue code (stops at an unsupported ARM BLX 0x021D30F2) —
  where the failed build returned 0 and stopped; COND on Assault's descriptor = **2**; CRIT handler
  (the picker's count) = **1** = ICD in banished, with Black Rose Dragon 0x1EDA (Dragon Synchro already
  in the GY, ref 0x5C) correctly excluded.
- **Build 2** (2026-09-14): slots re-laid — LEAVEHOOK 0x0239F360 (124/0x80), C2COND 0x0239F3E0
  (56/0x40), C2COST 0x0239F420 (28/0x20), C2CRIT 0x0239F440 (60/0x40), C2PRED 0x0239F480 (92/0x80),
  C2REFS 0x0239F500 (0x10, zero in image), CAVE_FREE 0x0239F510; check_allocations [OK].
  BUILD_EXIT=0, 5/5 verify PASS, sha256 **fab5caf1821df7664402a0ca65b263bca7898271a2fc832291daa918ff682c05**.
  Stubs disassembled from the ROM. AWAITING IN-GAME TEST.

- **User report on build 2 (verbatim, 2026-09-14):** *"Okay I have tested Assault Synchron and it
  special summons the banished target."* — scope of the test (which checks, which ROM hash) awaiting
  the user's clarification; not yet recorded as confirmation of any numbered check.
- **Check 13 in-game confirmed by user 2026-09-14** on build 2 fab5caf1…: user confirmed *"1. Yes"*
  to "fab5caf1 ROM, Dark Core on Iron Chain Dragon" → Assault offered, banished Dragon Synchro SS'd.
- **OPT BUG (build 2, user report 2026-09-14, verbatim):** *"the once-per-turn picker allowed me to
  activate the effect 3 times in a chain when the activation of the effect should gate the remaining
  cards from activating"*; clarified: *"They each had their own activation prompt, i clicked yes to
  one, and then then next popped up, and i click yes and so on."* / *"Yes all 3 were banish"* /
  *"only 1 monster was summoned, no freezes, the remaining links fizzled"* / fab5caf1 ROM.
  ⇒ one banish event admitted three GY copies; the kind-2 turn-log stamp in copy 1's COST did not
  stop copies 2 and 3 from being prompted and activating in the same chain.
- **RULED OUT (strike 2 → two-strike rule engaged): "a kind-2 turn-log post inside a bare cost at
  +0x10 gates other copies triggered by the same event".** Build 2's cls2 +0x10 = cave COST that calls
  Mezuki's banish directly — no slot3 re-check before each copy's prompt, and (KB
  `timing.class_is_the_slot4_literal`) a cave pointer at a cls2 +0x10 puts the trigger in NO timing class.
- **Precedent found (in-game confirmed shapes):**
  * KB `dispatch.once_per_turn_must_stamp_at_activation` (Maiden C1): slot4 wraps the "You can" BODY
    0x021E50DC — phase 0 runs slot3 via 0x0224AD94 (−1 = abort, no prompt), opens Yes/No; returns 1
    only on Yes; stamp only then. Same-chain double activation measured gone in-game.
  * patch_accel_synchro_stardust_dragon C1 (cls1 "If ... : You can" trigger, OPT, confirmed
    2026-09-14): `slot4_stub` = blx 0x021E50DD; if r0 == 1 → turn-log post; return r0. Plus a
    timing_class_hook ARMS entry (ARM_JW: desc[+5]==1 → tag 0x021E51E5, class 2).
  * Native cls2 bystander/GY triggers (Jurrac Herra, Tanngnjostr, Sun Dragon Inti) all carry +0x10 =
    0x021E51E5 — i.e. their prompt IS that body.
- Classifier 0x0224AF7C: `bl find_event_handler ; cmp r0,#0 ; beq 0x0224B028` @0x0224AF92 BEFORE the
  hook site 0x0224AF96 → a timing arm for 0x13AE is only reached when a 0x13AE record exists (no leak
  into ROMs without Assault).
- **User decision on the OPT fix (2026-09-14):** *"Go with: Cost stub becomes the Accel Synchro Stardust
  Dragon wrapper"* — item 1 ONLY: no timing_class_hook arm (trigger stays in no timing class), no ov5
  latch (relies on the turn log being visible to the next copy's slot3 re-check, as for Maiden).
- **Build 4 (OPT fix, 2026-09-14):** COST @0x0239F420 (36/0x30) = `bl 0x021E50DC ; cmp r0,#1 ; bne out ;
  post (side, 0x13AE, 2, 0) ; bl 0x021E5708 ; out: pop {r4,pc}` (disassembled from the ROM). Re-laid:
  C2CRIT 0x0239F450, C2PRED 0x0239F490, C2REFS 0x0239F510, CAVE_FREE 0x0239F520; ledger [OK].
  cls2 `{13AE 02207191 0 0239F3E1 0239F421 02235605}`, criteria `{13AE FFFF 0239F451 00010002}`.
  Same chain as build 3 (incl. ASSD). BUILD_EXIT=0, 6/6 verify PASS, sha256
  **a265b823c7a49775d43a361337146a3d7b6e5a1688c4c206efb7c19d5239add2**. Offline probe on ml3 unchanged
  (REFS 0xF805E, COND 2, target count 1). AWAITING IN-GAME TEST.
  UNPROVEN: that copy 1's queued turn-log post is visible to copy 2's slot3 re-check (Maiden's
  menu-activation precedent only); that no second prompt appears (trigger still has no timing class).
- **Build 4 in-game results, user report 2026-09-14 (verbatim):** *"1. Once per turn now lands
  2. Confirmed 3. No Double prompt 4. When tributing accel synchro dragon, assault synchron "misses the
  timing" which it should not do. it is an IF effect. 5. Confirmed 6. No regressions"*
  (items map to the build-4 test list: 1 same-chain OPT, 2 decline keeps it available, 3 no double
  prompt, 4 Tribute checks 11–12, 5 should-not-trigger checks 14–16, 6 regressions 1–10 + effect 1
  after effect 2). ⇒ **in-game confirmed by user 2026-09-14 on a265b823…: OPT across copies in one
  chain, decline does not burn it, single prompt, checks 14–16, no regressions.**
  **FAILED: Tribute of Accel Synchro Stardust Dragon → Assault "misses the timing"**. Clarified: the
  message WAS shown (*"1. Yes"*); between Tribute and message *"Accel Synchro attempts to do a synchro
  summon, per its effect"*; plain Tribute Summon not yet tried; savestates `rom_assault_synchron.ml3` /
  `.ml4`. ⇒ Tribute as ASSD C2's cost, chain resolves (Stardust Dragon SS + C3 Synchro Summon), the
  Tribute is no longer the last thing → engine applied the WHEN (miss-timing) rule to Assault's trigger.
- **The "misses the timing" message comes from the "You can" body 0x021E50DC phase 0** (disasm
  `python -m scratch.dis 0x021E50DC 0x100`): `bl 0x0224AD94` (slot3) == 0 → return −1 silently;
  else **`bl 0x021EE0E0(desc)` != 0 → prompt 0x107 (0x0219A6F4) + card name (0x0219A798) +
  0x0219A818(side, 1) = the OK-only MISSED-TIMING notice, return −1**; else Yes/No via 0x0219AAAC,
  phase++ (Kuribandit notes line 92 confirm 0x107 = "<card> misses the timing"). ⇒ our COND passed;
  **0x021EE0E0 is the miss-timing test** (memory said the rule was unlocated).
- **0x021EE0E0(desc) = the miss-timing test, fully decoded** (disasm 0x021EE0E0..0x021EE3CE):
  (1) register-based cid compare tree; listed cids → 0x021EE27E `movs r0,#0` = NEVER miss (engine's
  hard-coded IF cards; cid 0x2468−0x1B → 0x021EE282 extra code-9 test); 0x13AE is not listed.
  (2) default 0x021EE296: `desc[+4] − 7` (≤ 0x19) through the s16 table @0x021EE2AC (target =
  0x021EE2AE + v): codes 7,8,9,0xC,0xD,0x17,0x1B–0x20 → **0x021EE2E0: if desc[+0x20] & 0x1FF == 0 →
  return 0; else walk the event log (count [0x0229AB7C+0x30], codes 0x0229ABB4[i], words
  0x0229ABD4[i]) for code == desc[+4] && word & 0x1FF == desc[+0x20] & 0x1FF → 0, else 1 (MISSED)**;
  codes 0xA,0xB,0xE,0xF,0x12,0x14–0x16,0x18–0x1A (and out of range) → 0x021EE3CC return 0;
  0x10/0x11 → desc[+0x20]==0 → 0 else full-word log walk 0x021EE398; 0x13 → full-word log walk.
- **Measured on ml3/ml4** (`python -m scratch.assault_c2_timing_probe`): queue0 holds two Assault
  descriptors (refs 0x18, 0x1A) {zone 0xE, code 0x1D, sel 2, +0x20 = 0xE0720C56 (low 9 bits 0x56 =
  ASSD's ref)}; ml4 also in queue1. Executing 0x021EE0E0 on them = **1 (MISSES)** in both states —
  reproduces the report; with +0x20 & ~0x1FF = **0 (does not miss)**. Event log: ml3 empty, ml4 one
  entry {code 9, 0x00C28C58}.
- **ov5 RUNTIME STATE WAS WIPED between ml3 (22:08:58) and ml4 (22:09:09)**: the whole appended ov5
  region in ml4 is byte-identical to the ROM image; in ml2/ml3 it differed only at CAVE_TGW_ARMLATCH
  (=1 since ml2) and ml3's CAVE_ASSAULT_C2REFS (0x00048056 = turn 4, ref 0x56). Both reset together,
  stubs intact, native ov5 identical in all states ⇒ consistent with ov5 RELOADED from ROM during
  ASSD's C2/C3 resolution (Stardust Dragon SS + Synchro Summon). Not yet pinned which step reloads.
- **RULED OUT (strike 2 on "those monsters" memory): an ov5 runtime list.** It does not survive the
  resolution of an effect that Special/Synchro Summons. Dark Core (check 13) passed only because
  nothing reloaded ov5 between the banish and the picker.
- Turn-log query 0x021A14E8(side, slot, key, kind) (disasm): head = u16[0x0229ACD2 + side*0xB3C +
  slot*0x14] → walker 0x021A1268(head, key, kind): node u16[+0] == key (FULL 16 bits) && ([+2] & 0xF)
  == kind && kind < 6 → node ptr. Queued writer 0x021C479C: key bit 0x8000 selects a DIFFERENT chain
  writer (KB rider.node_writer_and_kind_byte) → a synthetic key must keep bit 15 clear.
  Kind-1 nodes are freed by the once-per-turn sweeper at the end of the turn (KB rider.turn_sweeper).
  KB: added `mem.ov5_runtime_state_wiped_mid_duel` (UNVERIFIED, with next experiment).
- **Two-strike rule engaged on "those monsters" memory → proposal to the user, no code written:**
  (T) timing: hook passes the leave word to the GY poster with low 9 bits cleared (measured: miss
  test 1 → 0 on the real queued descriptors). (M) memory: replace the ov5 list with a main-RAM
  turn-log node, POST 0x021D2584(r6, 0x4000 | ref, kind 1, 0) in the hook; PRED queries
  0x021A14E8(card side, 0x0B, 0x4000 | ref, 1). Engine-swept at end of turn.
  **User approved T and M 2026-09-14: *"Yes Approve"*.**
- **T + M proven offline on ml4 before building** (`python -m scratch.assault_c2_tm_probe`, current
  stubs overlaid on the real RAM): hook (frame = ASSD Tribute, ref 0x56) → `turnlog_post(0, 0x4056, 1,
  0)` and `gy_poster(0, 0x13AE, 0x1D, 0xE0720C00)`, replay Z = 1; synchronous writer 0x0219F190(0, 0xB,
  1, 0x4056) → node 0x12, query(0, 0xB, 0x4056, 1) = 1; PRED on the real GY words: ASSD 0x126F (ref
  0x56) = **1**, Assault ×2 = 0; control query for Iron Chain Dragon's key 0x405E = 0; miss test
  0x021EE0E0 on the real queued descriptor with +0x20 = 0xE0720C00 = **0**. Limits: the full builder
  walk (and PRED on ICD) reaches a card-data FILE load the emulator cannot run (ARM divmod 0x020989A4 /
  memset 0x020895FC were emulated in Python; opcode 0xFFFB @0x02089CB0 was not). The QUEUED post's
  delivery is not emulated (KB: event-queue ops don't settle statically).
- Cave: CAVE_ASSAULT_C2REFS dropped (never shipped), CAVE_FREE back to 0x0239F510; ledger [OK].
- **Build 5 (T + M, 2026-09-14):** same chain as build 3/4 (incl. ASSD). BUILD_EXIT=0, 6/6 verify PASS,
  stubs hook 104 B / cond 56 / cost 36 / crit 60 / pred 74, disassembled from the ROM (hook post +
  `lsrs r3,#9 ; lsls r3,#9` before 0x021D3648; pred query 0x021A14E8 → yes/no). sha256
  **8096806eec852f54e383123139b7127d945e7da673ce23210e547d7b0151cde4**. AWAITING IN-GAME TEST.
- **Build 3** (user request: *"Build the rom with accel synchro dragon so it is easier to test"*): chain
  striker → junk_servant → unknown_synchron → tg_warwolf → **accel_synchro_stardust_dragon** → assault.
  BUILD_EXIT=0, 6/6 verify PASS, criteria row now @124 (ASSD's rows precede it), sha256
  **c8bb4164a77dded268dade7577ce6599584ae1820fee2aa1a53c15d1ce28cfb4**. ASSD's C2 Tributes itself as a
  cost → a Dragon Synchro "Tribute as a cost" source for the test.

## C2 DESIGN PROPOSAL (not built; awaiting probe results + user approval)

| Part | What | Evidence |
|---|---|---|
| D1 hook | 4-B `bl` in the bystander chain (candidate 0x021C979E `ldr r0,[sp,#0x44]; cmp r0,#0`, replay with CMP last) → ov5 stub: if r4 race==1 && is_synchro(r4) && [sp+0x94] face-up && [sp+0x98]==r6 && [sp+0x2C] left field && (([sp+0xC]&0x1000) \|\| dest==0xF) && phase != DamageStep → `0x021D3648(r6, 0x13AE, [sp+0x1C], [sp+0x200])` | chain PROVEN; Tribute bit PROVEN; dest 0xF / DS phase / material bit = PROBE |
| D2 cls2 | record 0x13AE `{0x02207191, 0, COND(ov5), COST(ov5), 0x02235605}`, count-neutral (drop a phantom cls2 row) | template PROVEN (Mezuki/Inti); phantom TBD |
| D3 COND | desc code 0x1D/zone 0xE/class 2, still in GY, `0x021A14E8(side,0xB,0x13AE,2)==0` → 1 (slot2-less) or 2 | OPT pair PROVEN (KB) |
| D4 COST | `0x021D2584(side,0x13AE,2,0)` then tail 0x021E5709 | both PROVEN |
| D5 criteria | row 0x13AE → ov5 handler = 0x0223C4E8 + 0x0223C6AC with ov5 predicate: Dragon && Synchro && ref ∈ event log (code 0x1D, bit9 side, dest 0xE/0xF) | log walk PROVEN (Reflector); log alive at slot5 = ASSUMED |
| D6 revive | 0x02204730 handles GY + banished; "properly summoned" enforced natively = ASSUMED | banished branch PROVEN |

- GK Recruiter's own-leave mask row fires on Tribute AND Synchro Material alike (KB
  `event.leave_dispatcher_three_registers`) → the mask/list layer does not separate "Tributed".
- 3DS: Harrliard 0x2984 main_effect `009C2984 004B1DE8 00000002`, on_trigger `00463C48 … 0049DB90
  00403484`; Wingtortoise 0x25A7 event_trigger rows `0045E090/0049CF24/004001F4` and
  `00462030/0049BFF8`. Handler equivalence to NDS not mapped yet.

## Templates for C2 (text-level only — dispatch paths UNVERIFIED)

From the 3DS card DB (cid space shared with the NDS):
- **Jurrac Herra 0x2176 (NDS native)** — "When a Defense Position 'Jurrac' monster you control, except
  'Jurrac Herra', is destroyed by battle and sent to the Graveyard, you can Special Summon this card
  from your hand or Graveyard." A bystander leave trigger that fires from the GY. **Best template.**
- Tanngnjostr 0x2458, Meklord Emperor Wisel/Granel/Skiel 0x2430-0x2432 (NDS) — bystander leave
  trigger, from hand.
- Wingtortoise 0x25A7 (3DS only) — "When a face-up Fish, Sea Serpent, or Aqua-Type monster(s) you
  control is banished: You can Special Summon this card from your hand or Graveyard."
- Mecha Phantom Beast Harrliard 0x2984 (3DS only) — "when a monster(s) you control is Tributed ...".
- Leave dispatcher `0x021C7FCC` (KB `event.leave_dispatcher_three_registers`,
  `leave.mask_bit_semantics`); descriptor slots `[sp+0x90]` destroyed / `[sp+0x44]` battle /
  `[sp+0x144]` to GY / `[sp+0x28]` dest nibble 0xD (KB `leave.descriptor_slots` is **UNVERIFIED**).
  The mask table and lists register the LEAVING card's own triggers, not bystanders.
- GY→banished mover `0x021C7118` (KB `event.banish_from_gy_cid_gate`) — for the "banish this card from
  your GY" cost.

## Ruled Out

- **Static arm tuple in a shared hook when an existing owner is in the chain** — would ship
  Assault's 700 damage on vanilla Shapesnatch in every chain ROM. Use ov5 data rows. Do not retry.
- **Hand-SS table "slot 4 of 4"** — the 4th row is the required zero terminator; the table was full.
- **Summon-rider hook 0x02268666 for C1** — its arms are armed by a one-shot byte set inside a
  resolver; a hand-menu summon has no resolver.
- **Physically removing 0x1E4E before a donor existed** (count 15→14) — rejected by the user in favour
  of reserve-now, swap-in-patch.
- **Repointing steam_synchron at 0x1E4E** (the KB's old "clean fix") — slot now belongs to Assault.
- **`--compare rom_baseline.nds` as a no-change proof** — the baseline is the retired 55-step snapshot;
  a mismatch against a 63-step build means nothing.

## Open Questions (C2)

1. How does Jurrac Herra 0x2176 dispatch a trigger **from the GY** on **another** monster leaving?
   Which structures name 0x2176 (cls0-3, GY-action registry 0x0228DDF8, leave-mask 0x0226EC1C,
   list30/list106, a per-cid arm in the leave switch rooted at 0x021C8216)?
2. Does the leave descriptor distinguish **Tributed** (Tribute Summon fodder / Tribute cost) from other
   sends to the GY (Synchro Material, discard-cost, destruction)? Is there a bit, or only the caller?
3. Does a **field banish** reach the leave dispatcher with dest nibble 0xD (`[sp+0x28]`)? A
   banish-from-field that bypasses 0x021C7FCC would need a different hook.
4. "target 1 of those monsters" — where to remember the leaving cid(s) (an ov5 cell written at the
   leave event) and how to offer a picker over GY **and** banished zone.
5. Rulings the user must settle (do NOT assert from recall): does the revive ignore/obey summoning
   conditions; is it a trigger that can miss timing; what exactly counts as "Tributed".

## Next Experiment

**CARD SHIPPED 2026-09-14 — nothing pending for Assault Synchron.** Everything below this line is
historical. Follow-ups this card surfaced for OTHER work:
- KB `mem.ov5_runtime_state_wiped_mid_duel` (UNVERIFIED): pin which step reloads ov5, then audit the
  shipped ov5 latches (CAVE_TGW_ARMLATCH, CAVE_ASSD_STAGE, CAVE_LIB_LATCH, CAVE_AS_LATCH).
- patch_hyper_librarian.py's docstring calls card-word bit 15 "not properly summoned"; KB
  `summon.card_word_bit15_is_properly_summoned` shows it is inverted (docstring not edited — other card).
- Known ceiling: a Dragon Synchro that qualified earlier the same turn stays pickable (turn-log node).

00. **READY TO RUN (C2 session 1): `scratch/gdb_assault_leave_probe.py`** — one connection, bp at the
   bystander-chain head 0x021C93D0 (site bytes `11980028` checked in preflight), appends every hit to
   `scratch/gdb_assault_leave_probe.txt`: cid, r6, lr, phase/turn player, [sp+0xC] reason (+ tribute bit),
   [sp+8], packed word + dest nibble, and slots 0x08..0x200. Duel steps: (a) Tribute Summon, (b) Tribute
   as a cost, (c) Synchro Material, (d) banish from field, (e) battle destruction, (f) effect destruction.
   Expected: (a)(b) bit 0x1000 set; (c) CLEAR (else material needs another discriminator — the user
   ruled material does NOT count); (d) hits with dest 0xD (no hit = field banish bypasses this
   dispatcher → find its poster); (e) gives the Damage-Step phase value.
   Remaining static work (no emulator): what event/descriptor the 0x021D3648 post produces for a cls2
   responder; Herra's slot3 0x021F9551 / slot4 0x021E51E5 / resolver 0x0221E9DD; the "properly summoned"
   check; a cls2 insert for 0x13AE (count-neutral, phantom drop); the Dragon-Synchro predicate.
0. **(C2 session 1 status)** Step 1 below is DONE — see "C2 session 1 — static". Q1 is answered
   (bystander = hard-coded arm + `0x021D3648` GY poster). Remaining static lead for Q2: find the entry
   and caller of the cid switch around 0x021D779A (Sword of Dark Rites 0x1BF0) and execute it for
   0x1BF0 / 0x2462 / 0x1BEB. If its leaf reads a descriptor field, that field is the Tribute bit and
   the GDB run only confirms it.

1. **Static, no emulator:**
   `.venv-1/Scripts/python.exe -m otn_enhanced.tools.donor_scan 0x2176 0x2458 0x2430`
   → the complete data footprint of the native bystander-trigger templates. Then
   `.venv-1/Scripts/python.exe -m otn_enhanced.tools.threeds_lookup "Mecha Phantom Beast Harrliard"` and
   `... "Wingtortoise"` for Konami's Tributed / banished wiring.
2. **One-shot GDB session (only after 1):** extend `scratch/trace_leave_dispatch.py` to write to a file
   and dump `[sp+0x200]` (packed leave word), `[sp+0x28]`, `[sp+0x44]`, `[sp+0x90]`, `[sp+0x144]`,
   `[sp+0xB8]` (cid). Break at `0x021C8216`, then in ONE duel: (a) Tribute Summon a monster, (b) use a
   monster as Synchro Material, (c) banish a monster from the field, (d) destroy one by an effect.
   Expected: (a)/(b)/(d) dest nibble 0xE, (c) 0xD. A slot differing between (a) and (b) = the Tribute bit.
   No difference = "Tributed" is not visible here; report before designing.

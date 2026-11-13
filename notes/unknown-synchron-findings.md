# Unknown Synchron — findings

Live file. Everything below was verified **this session (2026-09-01)** unless marked
UNVERIFIED. Card: DARK / Machine / Tuner, Level 1, ATK 0 / DEF 0.

Text (`scratch/ygoprodeck_cache.json`, id 15310033):

> "If your opponent controls a monster and you control no monsters, you can Special
> Summon this card (from your hand). You can only Special Summon "Unknown Synchron"
> once per Duel this way."

Clause 1 = the conditional hand Special Summon.
Clause 2 = "once per Duel this way".
Both in scope (user decision). Plus Synchron archetype membership (user requirement:
`Tuning` must be able to search it).

---

## Confirmed

### Donor: Woodborg Inpachi `0x181C` (user-approved)

- `donor_scan 0x181C` → **VERDICT CLEAN**: named by no data structure. No cls0-cls3
  record, no criteria/populate row, no effect- or summon-procedure-registry row, no
  leave-mask row, no fusion-recipe membership.
- 5 occurrences, all **u16 in code regions** (`ov3:0x0219E5E4`, `0x021AD2E0`,
  `0x021E3C06`, `0x0223A2C4`, `arm9:0x02069B88`) = instruction encodings. **Zero
  u32-aligned hits anywhere**, which is what a per-cid compare's literal pool would leave.
- Native: Normal Monster, Lv5 FIRE Machine 500/2500, pack 6.
- Absent from the summon-procedure registry `0x0228F158` ⇒ generic summon path ⇒ the SS
  is **free**. That is the printed card, so the miss is the feature (contrast Lightpulsar
  / Darkflare, where the same miss cost two in-game tests each).
- Blob budgets measured against `len(old_string)` (the conservative test
  `apply_stats_and_text` applies, NOT the padding run):
  - English name 16 B; `"Unknown Synchron"` is 16 B → fits exactly.
  - English desc 177 B; the text below is 177 B → fits exactly.
  - Japanese desc 104 B / Korean 105 B are too small → those languages keep donor text.

Text to write (177 B — official text with the self-reference collapsed to "this card";
the full 186 B version does not fit and the blob must not grow):

```
If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand). You can only Special Summon this card once per Duel this way.
```

### Clause 1 mechanism (reuse, in-game confirmed elsewhere)

- Hook `0x0224C026` (`BL 0x0225E51C`) = the HAND-zone capability enumerator's hand-SS
  eligibility call. KB `handss.hook_site`, VERIFIED; in-game confirmed for T.G. Striker.
- The shared ov5 trampoline (`tg_table.register_tg_handss`) replays the dispatch, scans a
  `{u16 cid, u32 cond-ptr}` table at `CAVE_TG_SSTABLE`, and ORs flag `0x4` when the
  matching cond stub returns nonzero.
- **T.G. Striker's cond stub is cid-agnostic** — it takes only `r0 = side` and computes
  `canSS(0x021AD870) && monster_count(0x021ACF68, side)==0 && monster_count(1-side)!=0`,
  i.e. byte-for-byte the engine's Cyber-Dragon gate `0x0225F33A`. That is exactly Unknown
  Synchron's clause 1, so the stub is cloned, not invented.
- **Dispatch table has room, no relocation needed.** Only `patch_tg_striker` (`0x1F18`)
  and `patch_junk_servant` (`0x17CE`) call `register_tg_handss` (grep, whole repo), so
  rows 0-1 are used, row 2 is free and row 3 stays the zero terminator — all inside the
  `0x20` reserve. Verified against a built ROM: `rom_junk_servant.nds` has exactly one row
  `{0x17CE, 0x0239DEF1}`.

### Synchron archetype — set code `0x4C`

- Pointer table `0x0209D0D8` index **`0x4C`** → thunk **`0x02023E1D`**:
  `ldr r1,=0x0209C968 ; ldr r3,=0x02022E15 ; movs r2,#0xF ; bx r3`.
- Sorted u16 list at **`0x0209C968`, count 15** (count hardcoded `movs r2,#0xF` @
  `0x02023E20`). **Single consumer**: `0x0209C968` occurs as an aligned literal exactly
  once in all of ARM9 (`0x02023E24`), so there is no second hardcoded count.
- Contents (index: cid):
  `0 0x0D6B` Speed Spell - Deceased Synchron, `1 0x1E07` Junk Synchron,
  `2 0x1E14` Nitro Synchron, `3 0x1E4E` Synchro Deflector, `4 0x1EA1` Road Synchron,
  `5 0x1EBE` Turbo Synchron, `6 0x1F46` Hyper Synchron, `7 0x20F7` Quickdraw Synchron,
  `8 0x21A7` Drill Synchron, `9 0x224C` Changer Synchron, `10 0x229E` Synchron Explorer,
  `11 0x239E` Formula Synchron, `12 0x23EE` Fleur Synchron, `13 0x2414` Bri Synchron,
  **`14 0x2501` = PHANTOM** (no `card_prop`; Konami-reserved id for a Synchron absent
  from this game's DB).
- **`Tuning` really reads this set code**: Tuning `0x23A2` owns criteria row **1269** @
  `0x02274F40` = `{cid 0x23A2, aux 0x004C, handler 0x0223CAF5, word 0x00008002}`.
  `aux == 0x4C` is the Synchron set code, so list membership is exactly what makes Tuning
  offer the card.
- Phantom `0x2501` is **unclaimed** — absent from `otn_enhanced/docs/engine/allocations.yaml` and from
  `PHANTOM_CLAIMS` in `check_allocations.py`.
- Planned count-neutral edit: drop `0x2501`, insert `0x181C` at sorted index 1 (between
  `0x0D6B` and `0x1E07`), count stays 15.

### Clause 2 mechanism located (engine-native)

User named the native once-per-Duel cards: Glow-Up Bulb, Spore, Blackwing - Zephyrus the
Elite. Two of the three share one function:

- The **ignition-condition registry** is `0x0226FAFC`, 146 x `{u16 cid, u16 aux, u32 f1,
  u32 f2}` (geometry from KB `card.upstart_golden_ninja`; extent independently
  re-derived here as `0x0226FAFC .. 0x022701D4`).
- **Spore `0x225B` = row 110 @ `0x02270024`** `{f1 0x021F0949, f2 0x021F44D9}`
- **Glow-Up Bulb `0x2387` = row 120 @ `0x0227009C`** `{f1 0x021F7B75, f2 0x021F44D9}`
- The shared `f2 = 0x021F44D9` IS the once-per-Duel gate (disassembled):

```
0x021F44D8  push {r3,r4,r5,lr} ; r5 = desc ; r0 = desc[+2] (side) ; r2 = desc[+0] (cid)
            r1 = 0x0B ; r3 = 5 ; bl 0x021A14E8      ; turn-log query
            cmp r0,#0 ; bne -> return 0             ; already used this Duel -> deny
            r0 = desc ; r1 = r4 ; bl 0x021F04FC     ; else chain the real condition
```

  This is exactly KB `dispatch.turnlog_once_per_turn_pair` (Pot of Duality's
  `(side, 0x0B, cid, 1)` query) with the **kind argument 5 instead of 1**.
- Overlay-wide census: `0x021A14E8` has **89 call sites**, of which only **three** use
  `kind = 5`: `0x0219D0A0`, `0x021BF4BA`, `0x021F44E6`. The poster
  `0x021D2584(side, key, kind, r3)` -> `0x021C479C(side, 0x0B, key, kind)` has **206 call
  sites, 17 of them posting kind 5**.
- Query internals (`0x021A14E8`, disassembled): `r6 = side & 1`; indexes a per-side pool
  by `family * 0x14`; then `bl 0x021A1268(head, key, kind)` does the search. So **kind is
  a match field, not a duration** — see Open Questions.
- Both query and poster are **cid-generic** (the key is a caller argument read from the
  descriptor), the same property that made the once-per-turn pair usable by any donor.

### GATE A PASSED — `kind = 5` IS Duel-scoped (closed structural proof)

Chain of three reads, all static, no emulator needed:

1. **The node layout.** The list search `0x021A1268(head, key, kind)` walks 10-byte nodes
   (`r5 = 0xA`, link at `node[+8]`) and matches on
   `r7 = node[+2] & 0xF` — `cmp r7,#6 ; bhs skip` (kinds are 0..5, so **5 is the maximum
   legal kind**), then `node[+0] == key`, then `r7 == kind`. So **`node[+2] & 0xF` IS the
   kind field**.
2. **The end-of-turn sweeper switches on that same field.** `0x0219F9E0` does
   `ldrh r0,[r4,#2] ; r1 = r0 & 0xF ; cmp r1,#8 ; bhi 0x0219FAEE`, then a 9-entry
   halfword jump table (`add r1,pc ; ldrh r1,[r1,#6] ; add pc,r1`, table @ `0x0219FA2C`,
   PC base `0x0219FA2E`). Decoded targets:

   | kind | target | meaning |
   |------|--------|---------|
   | 0 | `0x0219FAEE` | skip |
   | **1** | `0x0219FA3E` | **countdown-or-remove** |
   | **2** | `0x0219FA3E` | **countdown-or-remove** |
   | 3 | `0x0219FA5C` | key-compare arm |
   | 4 | `0x0219FAEE` | skip |
   | **5** | **`0x0219FAEE`** | **skip — node untouched** |
   | 6,7,8 | `0x0219FA6C` | locator/expiry arm |

3. **`0x0219FAEE` really is "skip", not "remove".** The removal call is
   `0x0219FAEA bl 0x0219F03C`, and `0x0219FAEE` sits strictly *after* it, at the loop
   increment `movs r0,#1 ; adds r5,r5,#1 ; lsls r0,r0,#8 ; cmp r5,r0 ; blt 0x0219FA0C`.
   Two independent branches land there: the out-of-range `bhi`, and the tail of the
   kind-1/2 countdown after it writes the decremented value back.

**Conclusion:** kind 1 (Pot of Duality's once-per-turn) is decremented and removed at the
end of the turn; **kind 5 is never touched by the sweeper, so it persists for the Duel.**
That is the once-per-Duel latch, and it is the same cid-generic post/query pair the
once-per-turn cards already use — so it works for any donor.

---

### Gate B — the "this way" hook is the SUMMON-PROCEDURE REGISTRY (partial)

- `0x022651B8(r0 = cid, r1 = out_ptr)` is the **per-cid summon-procedure lookup**: a
  stack-based cid switch returning a procedure-table pointer, and `str r0,[r6]` with 0 when
  the cid has no row (`0x022653CA..0x022653D4`). Four ov3 callers: `0x0225D46E`,
  `0x0225F4EC`, `0x022625EA`, `0x02264BC8`.
- **`0x0225F4EC` is NOT an execution site** — its enclosing function is `0x0225E51C`, the
  hand-SS *eligibility* dispatch. That arm looks up the procedure and calls
  `0x0225CE0C(side, cid, 1, 1)` purely to test satisfiability, then branches to the shared
  SUCCESS trampoline `0x0225F216` (`movs r0,#4 ; orrs r5,r0`). Eligibility, not execution.
- **`0x022625DC` is a registry ROW HANDLER, not a chokepoint.** It has **zero** ov3
  callers; every reference to `0x022625DD` (13 of them) lies in `0x0228F29C..0x0228F57C`,
  i.e. **inside the summon-procedure registry `0x0228F158`**, whose rows are
  `{u32 handler, u32 cid}` pairs (e.g. `{0x022625DD, 0x1806}`). It reads the cid being
  summoned from a global summon context as `ldrh r0,[r4,#0xE]`. Other handlers in the same
  registry: `0x0226292D`, `0x02261F8D`, `0x02264921`, `0x0226448D`, `0x02263209`,
  `0x0226339D`, `0x02264BC1`, `0x022625B5`, `0x022625A5`.

**Consequence, and it is the good news:** a summon-procedure registry row means "when this
cid is summoned **by its own procedure**, run this handler" — which is exactly the printed
"Special Summoned **this way**", and would NOT fire for a later Monster Reborn / Call of
the Haunted revival. So the registry row is the architecturally correct stamp site, not a
generic SS-commit hook.

**REGISTRY ROW RULED OUT (2026-09-01).** The registry has 133 rows / 23 handlers, and
**none of the five costless "Cyber Dragon condition" cards is in it** — Cyber Dragon
0x0F07 and 0x18F6, Vice Dragon 0x1F37, Level Warrior 0x1FDB, Oracle of the Sun 0x21B6 all
summon by the generic free path with no row. Every row belongs to a card with a real
procedure (Ancient Gear 0x19AA / Sphinx Teleia 0x17C8 tribute, Cyber Eltanin 0x20EE,
Ananta 0x1D62, The Atmosphere 0x221E banish...). So there is no "free but tracked"
handler: adding a row necessarily attaches a cost. Per the user's 2026-09-01 decision
(strict or nothing), this route is closed.

### GATE B PASSED — the SS-commit descriptor carries the SOURCE ZONE

The stamp site is the SS-commit record builder, and it is fully determined statically:

- Routine A `0x0226925C..0x0226930A` (and its twin, routine C, ending `0x022693BA`) builds
  the global summon descriptor **`SUMMON_DESC = 0x02298A28`**:
  - `0x0226928E strh r5,[r4,#2]` → **`[+0x02]` = side**
  - `0x0226929E bl 0x021A220C` then bits [15:8] → `0x022692AC strh r0,[r4,#0xA]`
    → **`[+0x0A]` = the SOURCE ZONE**
  - `0x022692C2 strh r0,[r4,#0xE]` → **`[+0x0E]` = the summoned cid**
- **`[+0x0A]`'s entire vocabulary across ov3 is `{0x0B, 0x0D, 0x0E}`** (4 / 2 / 9 compare
  sites) = **HAND / DECK / GY**, the same numbering as the capability enumerator
  (`0x0B` → `0x0224BEFC`) and as Armory Arm's GY gate (`0x0E`).
- It is the engine's OWN "summoned from where" discriminator: at `0x022662F8`, after
  `cmp r6,#9` (event 9 = Special Summon), it branches on `[+0xA] == 0xE` (from GY) then
  `== 0xD` (from Deck); at `0x02265A7E` and `0x02265A9A` it tests `[+0xA] == 0xB`
  (**from the hand**).
- **These commit sites are reached ONLY for Special Summons** — GDB-confirmed 2026-07-12,
  recorded in `patch_tg_warwolf._build_arm_hook`; a Normal Summon never reaches them.

So `cid == 0x181C AND [SUMMON_DESC+0xA] == 0x0B` is exactly "Special Summoned from the
hand" = the printed "this way", and a later Monster Reborn (zone 0x0E) will not match.

**Hook sites chosen (unclaimed):** `bl 0x02244D08` at **`0x022692F2`** (routine A) and
**`0x022693A0`** (routine C) — on each routine's success path, with `r0 = side` at both,
and the return value dead (the caller immediately overwrites r0 with `ldrh r0,[r4,#0xE]`).
T.G. Warwolf owns the *other* call in the same routines (`bl 0x021A25A0` @0x022692E8 /
0x02269396), so there is no collision.

### Build status — CLAUSE 1 + SYNCHRON **IN-GAME CONFIRMED BY USER 2026-09-01**

All five oracle checks passed on `rom_unknown_synchron.nds` (sha256 `51120d79…4386d`).
User's words: *"1. Confirmed / 2. Confirmed / 3. Confirmed / 4. Confirmed (please
implement) / 5. Confirmed"*.

- **Clause 1 confirmed**: offered only when the opponent controls a monster and you control
  none (checks 1–3, including both negative controls); resolves **for free**; arrives as a
  Level 1 DARK Machine Tuner 0/0.
- **Synchron membership confirmed** (check 5): Tuning finds Unknown Synchron, **and** the
  other Synchrons still appear — so the re-sorted 15-entry list did not regress.
- **Check 4 confirmed the clause-2 gap is real**: the summon is repeatable within one Duel.
  User instruction: implement clause 2.
- User decision 2026-09-01 on scope: **strict "this way" or not at all** — the stamp must
  fire only on this card's own hand Special Summon, so a later Monster Reborn / Call of the
  Haunted must NOT consume it. If the only route imposes an unintended cost (the Darkflare
  failure mode), stop and report rather than ship it.

`patch_unknown_synchron.py` + `_build_unknown_synchron.py` →
`data/over_the_nexus/working/rom_unknown_synchron.nds`.

### Clause 2 **IN-GAME CONFIRMED BY USER 2026-09-02** — card SHIPPED to the chain

User's words: *"Confirmed all points, no regressions! Ship it"*. All eight oracle checks
passed:

- **check 4** — after one hand Special Summon, the offer does **not** return later in the
  same Duel. The once-per-Duel latch works.
- **check 6** — a **new Duel** offers it again, so the latch is genuinely per-Duel. This is
  what separates "the latch works" from "the card broke"; check 4 alone could not.
- **checks 7 and 8** — a Monster Reborn revival still works after the once-per-Duel is
  spent, and reviving from the GY first does **not** consume it. **The "this way" scoping
  is correct in both directions**, which confirms the zone gate `[SUMMON_DESC+0x0A] == 0x0B`
  really does mean "summoned from the hand".
- **checks 1, 2, 3, 5** — no regression in clause 1 or in Tuning.

Wired into `apply_all_patches` (47 steps, WiFi timers still last) and registered in
`_verify_all_patches.SHIPPED`, in the same edit.

**Chain build 2026-09-02 — artifact asserted, not trusted from the exit code:**

- `ALL 47 PATCHES APPLIED`; `rom_all_patches.nds` = 129,529,992 B, sha256
  `52c3a08df9df09dbfd35284382b23581673ec5824bb1d4f4722d41856e367a0e`.
  Previous ROM preserved as `rom_all_patches.BEFORE_UNKSYN.nds`.
- Content assertions on the built ROM all PASS: both new stubs populated, the shared
  trampoline / Junk Servant cond / Warwolf SS hook populated, the hand-SS table holding
  `0x1F18 / 0x17CE / 0x181C` + zero terminator, and all four SS-commit hooks pointing at the
  right stubs.
- Verify sweep: **36 PASS, 0 FAIL**, 2 skipped (`patch_boggart_knight`, `patch_darksoul` —
  neither has a `verify()`).

**This build also REPAIRED the broken chain ROM flagged on 2026-09-01.** The ov5 extension
now carries **8520** nonzero bytes versus **1430** in the failed build (and 2532 in
`.PREV`), and `CAVE_TG_SSTRAMP` / `CAVE_JS_SSCOND` are populated again — so T.G. Striker E1
and Junk Servant are live in the combined ROM once more.

### Clause 2 build detail

Two stubs, no new mechanism; both halves of the pair were proven above.

- **`CAVE_UNKSYN_SSCOND` (0x0239DF20, 64 B)** — the deny half. Prepends
  `0x021A14E8(side, 0x0B, 0x181C, 5)` to the clause-1 condition; nonzero ⇒ return 0, so
  the offer never appears once the node is posted.
- **`CAVE_UNKSYN_STAMP` (0x0239DF70, 48 B)** — the post half. Hooked over
  `BL 0x02244D08` at **0x022692F2** and **0x022693A0**; posts
  `0x021D2584(side, 0x181C, 5, 0)` iff `SUMMON_DESC[+0xE] == 0x181C` **and**
  `SUMMON_DESC[+0xA] == 0x0B` (from the hand), then replays the displaced call.
- Both disassembled from the built ROM: Thumb-1 only, every return via `pop {..,pc}`
  (never LR), literal pools resolve to `0x02298A28` and `0x0000181C`.
- **Composition with T.G. Warwolf verified** — Warwolf owns `BL 0x021A25A0` @0x022692E8 /
  0x02269396 in the *same two routines*; all four hooks coexist and `warwolf.verify()`
  passes unchanged on the composed ROM. This is now a permanent stage in
  `_build_unknown_synchron.py`, alongside Junk Servant and T.G. Striker.
- `verify()` all PASS, including that the condition stub BLs the query exactly once and the
  stamp BLs the poster once and replays the displaced call once (decoded from the emitted
  bytes, not trusted from the source).
- Card text updated to the full 177 B two-clause string — it fits the English slot exactly,
  `bin2.pac` unchanged at 10,974,720 B.
- ov5 cave after clause 2: `CAVE_FREE = 0x0239DFB0`, **368 bytes left**.

- `verify()` all PASS: stub byte-exact (42 B) + Thumb-1, hook installed and cid
  registered, Synchron list holds `0x181C` / dropped `0x2501` / still a sorted 15,
  count immediate and consumer pool intact, stats DARK / Machine / Lv1 / 0 / 0 /
  card_type 33.
- Name and description written **in place**: `bin2.pac` is 10,974,720 B before and after
  (+0 B), name 16 B → 16 B, desc 177 B → 115 B.
- Composition check (`rom_unknown_synchron_compose.nds`, static only): Junk Servant and
  T.G. Striker applied on top, all three `verify()` PASS, and the shared dispatch table
  reads `row0 0x181C / row1 0x17CE / row2 0x1F18 / row3 zero terminator`. **The table is
  now FULL** — a fourth registrant needs it relocated to a larger cave slot first.
- `check_allocations` clean; phantom `0x2501` claimed as pool `synchron_setcode_table`.
- KB: `setcode.synchron_table` and `dispatch.turnlog_once_per_duel_is_kind_5` both added
  as VERIFIED and passing (392 facts, 0 FAIL).
- ov5 cave after this patch: `CAVE_FREE = 0x0239DF50`, **464 bytes left**. The old
  "6032 bytes still free" comment was wrong and has been corrected.

---

## Ruled Out

- **Elder-of-the-Six-Samurai route for clause 1** (retarget a hand-SS dispatch-BST node to
  the shared gate `0x0225F33A`, a 2-byte edit). Not available: all four dead BST arms are
  spent — two reach only Speed Spells, `0x0225E6E6` is Lightpulsar's, `0x0225E88E` is
  Darkflare's — and a records-free Normal Monster has no node in the tree to retarget.
- **Donors whose native effect already IS the Cyber-Dragon condition.** Level Warrior
  `0x1FDB` (8 occurrences, carries a Synchro-level treatment), Oracle of the Sun `0x21B6`
  (21 occurrences, GY effect), Vice Dragon `0x1F37` (playable). All carry residual records
  that would ride into the card. Cyber Dragon is playable and off the table by policy.
- **Level-1 zero-occurrence Normal Monsters as donors for the FULL text.** Only three
  exist (`0x1783` Gigobyte, `0x17CD` Charcoal Inpachi, `0x1E05` Water Spirit); the largest
  English desc slot among them is 135 B, under the 177 B the two-clause text needs.
- **"No Synchron table exists"** — an early assumption of mine, wrong, corrected by the
  user. `donor_scan`'s `ARM9_STRUCTS` knows only seven set-code tables (Infernity, T.G.,
  X-Saber, AoJ, Watt, Karakuri, Gladiator Beast) and Synchron is not among them, so a
  clean donor_scan verdict does NOT mean "no set-code membership". Tool gap to fix.

---

## Open Questions

**Gate A - RESOLVED, see Confirmed. `kind = 5` IS Duel-scoped.**

**Gate B — where to stamp the node so it means "this way"?**
Clause 1 is a pure eligibility condition; nothing of ours runs when the summon actually
happens. The printed restriction is "once per Duel **this way**", so a later revive from
the GY must NOT consume it — the stamp must be gated on "Special Summoned **from the
hand**", not on any summon of the cid.

**Zephyros `0x241C`** is NOT in registry `0x0226FAFC`, so it reaches the same restriction
from a different record. Worth reading as a third witness.

---

## Next Experiment

**In-game test of clause 2** on `rom_unknown_synchron.nds` — checks 4, 6, 7, 8 in
`_build_unknown_synchron.py`'s oracle. The two that actually discriminate:

- **check 6** (new Duel → offered again) separates "the latch works" from "the card broke".
  Check 4 passing alone cannot tell those apart.
- **checks 7 and 8** (Monster Reborn before/after the hand summon) are the "this way"
  scoping. They are what the zone gate `[+0x0A] == 0x0B` buys; if a GY revival consumes or
  is blocked by the once-per-Duel, the zone test is wrong and the finding above is bad.

If check 4 fails (still offered), the first thing to measure is whether the stamp ran at
all: savestate after the summon and evaluate `0x021A14E8(side, 0x0B, 0x181C, 5)` with
`scratch/thumbemu.py`. Nonzero ⇒ the post worked and the deny half is at fault; zero ⇒ the
commit site was not reached on the hand-SS path, and the next candidate is the other pair
of calls in those routines.

⚠️ Known limitation of that offline check, inherited from
`counter.the_you_can_tag_is_the_per_copy_poster`: a node POST may not settle in a static
savestate run (the identical limitation was confirmed with Pot of Duality as a native
control), so a zero from thumbemu is weaker evidence than a nonzero.

### Older entries

**Gate A, static first (cheapest):** decode the end-of-turn sweeper `0x0219F9E0` — it
switches on `node[+2] & 0xF` across 9 arms, and arm 0 does the high-nibble
countdown-or-remove at `0x0219FA3E..0x0219FA54`. Read it together with the node writer
`0x021C479C` and the list search `0x021A1268` to see which kinds survive the sweep.
Expected result if the hypothesis holds: kind 1 nodes are removed at end of turn, kind 5
nodes are not.

**Gate A, empirical fallback (authoritative):** Glow-Up Bulb is in the ROM. Use its GY
effect, savestate, end the turn, savestate again, then evaluate
`0x021A14E8(side, 0x0B, 0x2387, 5)` on both states with `scratch/thumbemu.py`. Survives
the turn boundary ⇒ Duel-scoped.

**Gate B:** candidate stamp sites in order — the SS-commit hook T.G. Warwolf already uses
(`CAVE_TGW_SS_HOOK`, replays `0x021A25A0`) and the post-placement enumeration site
`0x02265D00` (Hyper Librarian's). Needed evidence: the site is reached on the hand-SS
path, and the **source zone** is readable there. One-shot GDB session (KB
`tool.gdb_one_shot_session`) or savestate.

If Gate A fails, clause 2 is not this pair — fall back to reading Zephyros's record, and
report before writing any code.

---

## Unrelated observation (flagged to user)

`data/over_the_nexus/working/rom_all_patches.nds` (built 2026-09-01 20:25) is missing the
shared hand-SS trampoline: `CAVE_TG_SSTRAMP` and `CAVE_TG_SSTABLE` are **all zeros** and
`CAVE_JS_SSCOND` is empty, while `rom_all_patches.PREV.nds` (19:34) still has the
trampoline. Extension-region nonzero bytes dropped 2532 -> 1430. Consistent with the known
silent-death chain-build failure (KB `otn-chain-build-verify-artifact`), which would mean
T.G. Striker E1 and Junk Servant are dead in the current combined ROM.

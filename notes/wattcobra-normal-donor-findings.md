# Wattcobra → Normal-Monster donor — findings (2026-09-10)

Task: re-home `patch_wattcobra` off **Blackwing - Fane the Steel Chain 0x2069**
(a real, playable Effect Monster) onto a records-free **Normal Monster**, the way
`patch_boggart_knight` (Molten Behemoth 0x13A5) and `patch_darksoul`
(Gigobyte 0x1783) were re-homed.

`notes/normal-donor-migration-findings.md` Open Question 2 was the blocker:

> **Battle-damage trigger dispatch.** Is a cls1 record with +08 = 0x021E32D5
> enough for a records-free donor, or is there a membership list like
> `summon.trigger_is_a_membership_list`? Decides Wattcobra.

## Confirmed (this session)

### ✅ ANSWER: it IS a membership list — same shape as the summon triggers

Disassembled `0x021D020A..0x021D0256` (ov3) this session:

```
0x021D020A: movs   r0, #2
0x021D020C: ldrsb  r0, [r5, r0]      ; r5 = 0x02298AD8, [+2] = "this was a DIRECT attack"
0x021D020E: cmp    r0, #0
0x021D0210: beq    0x021D0234        ; not a direct attack -> skip list A entirely
0x021D0212: ldr    r0, [sp, #0x18]
0x021D0214: movs   r1, #0xA
0x021D0216: ldrsh  r0, [r0, r1]      ; r0 = the ATTACKER's cid
0x021D0218: ldr    r1, [pc, #0x1e0]  ; = 0x0226EE7C   <-- LIST A
0x021D021A: movs   r2, #0x13         ; count = 19  (HARD-CODED)
0x021D021C: bl     0x02022E14        ; sorted binary-search membership
0x021D0220: cmp    r0, #0
0x021D0222: beq    0x021D0234        ; miss -> no event posted
0x021D0224: movs   r0, #4 ; movs r1, #5 ; ldrsb r0,[r4,r0] ; ldrsb r1,[r4,r1]
0x021D022C: movs   r2, #0x10         ; event code 16
0x021D022E: adds   r3, r6, #0
0x021D0230: bl     0x021D3230        ; POST the battle-damage event

0x021D0234: (same again, ungated) ldr r1, = 0x0226EEA4  <-- LIST B, count 0x33 = 51,
            same `movs r2,#0x10` + `bl 0x021D3230`
```

* **LIST A `0x0226EE7C`, 19 entries, count immediate `movs r2,#0x13` @0x021D021A**
  = *"When this card inflicts Battle Damage to your opponent **by a direct
  attack**"*. Members (named via `donor_scan.cards()`):
  0x0EC0 (phantom), Spirit Reaper 0x1596, Reaper on the Nightmare 0x1598,
  0x15D0 (phantom), Memory Crusher 0x19CF, 0x1A1F (phantom),
  AG Gadjiltron Chimera 0x1B15, X-Saber Airbellum 0x1D71, Unifrog 0x1DB2,
  0x1DB6 (phantom), E-HERO Ice Edge 0x1FBE, **Fane 0x2069**, Wattgiraffe 0x2261,
  Memory Crush King 0x2265, Wattbetta 0x22FB, Wattpheasant 0x22FD,
  Wattchimera 0x230F, Wattberyx 0x246A, Watthydra 0x2477.
  **FOUR PHANTOMS (0x0EC0 / 0x15D0 / 0x1A1F / 0x1DB6) → a count-neutral insert
  is free.**
* **LIST B `0x0226EEA4`, 51 entries, `movs r2,#0x33` @0x021D023C** = the plain
  *"inflicts Battle Damage"* trigger (White Magical Hat, Airknight Parshath,
  Don Zaloog, Vampire Lord…). **Not** used by this card.
* Both lists have exactly ONE literal reference each in the whole overlay
  (0x021D03FC / 0x021D0400, adjacent words of the same function's pool), so
  membership is the entire static gate — same property that made
  `battle.direct_attack_list` and the double-attack list safe to edit.

⇒ **Wattcobra moves from Tier B to Tier A.** The trigger is DATA.

### Fane's native halves, enumerated (`donor_scan 0x2069`)

`VERDICT: ENTANGLED`, 3 binding occurrences:
* `cls1 record[1021]` — `{+04 0x022076A5, +08 0x021E32D5, +0C 0x0224A115,
  +10 0, +14 0x02234E01}`. It is the ONLY cls1 record in the table with
  +08 = 0x021E32D5 (scanned all 0x535 rows this session).
* `ov3:0x0226D756/u16` = index 19 of the **direct-attack list 0x0226D730**
  (`battle.direct_attack_list`) — the "can attack directly" half.
* `arm9:0x0209CE42/u16` — ARM9 data hit, unclassified (Blackwing set-code table
  is the likely owner; **not our business — a re-homed Fane must KEEP it**).

So the donor needs exactly two data grants the vanilla lacks: **direct-attack
list membership** and **list-A membership**, plus a cloned cls1 row.

### The direct-attack GRANT list (the donor's other native half)

`battle.direct_attack_list` @**0x0226D730**, **25 entries**, count immediate
`movs r2,#0x19` @**0x021A6BDC**, single literal ref @0x021A6D98, consumer
`bl 0x02022E14` @0x021A6BDE (sorted binary search). Dumped this session:
0x0EB3*, 0x1129*, 0x1133*, 0x1134*, Jinzo #7 0x114C, 0x118E*, 0x1221*,
Mucus Yolk 0x13B2, Servant of Catabolism 0x13B3, Nightmare Horse 0x1597,
Reaper on the Nightmare 0x1598, Raging Flame Sprite 0x182D, Submarineroid
0x1A52, Cyberdark Edge 0x1AAF, CB Amethyst Cat 0x1B9F, Spell Striker 0x1BB5,
Goblin Black Ops 0x1C7F, Jinzo - Returner 0x1D9B, Unifrog 0x1DB2,
**Fane 0x2069**, Wattgiraffe 0x2261, Wattpheasant 0x22FD, Wattchimera 0x230F,
Scrap Worm 0x2468, Watthydra 0x2477.  (* = phantom, no card_prop row → **six**
free count-neutral drops.)

### Phantoms re-checked against the CHAINED image (rom_all_patches.nds, 2026-09-08)

* list A and the direct-attack list are **byte-identical to stock** there.
* cls1 phantoms 0x0E14 / 0x0E17 / 0x0E1B / 0x0E1F / 0x0E21 / 0x0E38 each still
  own exactly ONE cls1 row — unspent. (⚠️ `check_allocations` splits the cls1
  pool across two names, `cls1` and `cls1_table`; both were read.)
* Fane still owns exactly one cls1 row in the chained image.

### Composition BLOCKER found: patch_shooting_quasar's PART O tripwire

`patch_shooting_quasar.verify()` compares `ov[0x0226D730 : +0x60]` byte-for-byte
against the CLEAN overlay ("adjacent direct-attack/piercing lists untouched") —
a deliberate off-by-one tripwire for its own double-attack-list rewrite at
0x0226D712. Inserting our donor into the direct-attack list changes bytes inside
that window, so **Quasar's verify() would FAIL on the chained ROM**. Needs a
narrowed tripwire (compare the terminator + piercing region, and assert the
direct-attack list is still 25 strictly-sorted entries).

### Donor vetting — DONOR IS **WATTKID 0x0FD3** (user's pick, and it is the right one)

`donor_scan 0x0FD3`: Normal Monster, **Lv3 LIGHT Thunder 1000/500**, pack 2,
records-free in cls0-3 / populate / criteria. **VERDICT: ENTANGLED, by exactly
one thing — `set-code table: Watt[0]` @arm9:0x0209CBEA** — which is not an
obstacle but *the archetype membership the card needs*, already present and
already sorted.

Consequences, all of them good:
* **PART D (the ARM9 Watt-table edit) is deleted.** The old build swapped the
  donor in over 0x0FD3 ("Wattkid", a name-collision FALSE member). With Wattkid
  *as* the donor the entry becomes correct instead of being patched around. The
  module now only ASSERTS the table (`assert_donor_is_a_watt`).
* Attribute, race, ATK and DEF already match Wattcobra exactly; PART B changes
  only Level 3 -> 4 and Normal Monster -> Effect Monster.
* No fusion recipe or any other structure is disturbed.

Rejected alternatives:
* **Crawling Dragon #2 0x0FF7** (first suggestion): ENTANGLED —
  `fusion recipe A[38]+0x4` @ov3:0x02270CC8, the second material of
  **Bracchio-raidus 0x11A3**. Would rewrite a real, obtainable fusion recipe.
* **Crawling Dragon 0x1004**: ENTANGLED, 13 binding aligned-u32 occurrences.
* Clean LIGHT/Lv4 vanillas existed (Rogue Doll 0x0FD2, Spirit of the Harp
  0x1050, Shining Abyss 0x13E2) but all are strictly worse than Wattkid, which
  brings its own set-code row. (Dunames Dark Witch 0x12B2 is excluded twice
  over: a real 1800-ATK beater, and already White Dragon Ninja's donor.)

### Card text is not slot-limited

`apply_stats_and_text` takes the `card_text.CARD_TEXT` rebuild path whenever the
cid has an entry (`rebuild_blobs` re-emits every blob in index order), so the
donor's name/desc slot lengths are NOT a constraint — only the `CARD_TEXT` key
has to move from 0x2069 to the new donor. It also accepts `card_type=`, which is
what turns the vanilla into an Effect Monster.

## Ruled Out

* *"+08 = 0x021E32D5 is the direct-attack condition"* (the claim in
  `patch_wattcobra`'s docstring). It is `push {r3,lr}; ldr r3,=0x00040492;
  bl 0x021D6E40; pop {r3,pc}` — a call to the masked **zone predicate**
  (`0x021D6E40`), not a direct-attack test. The direct-attack half of the
  trigger is the `[0x02298AD8 + 2]` flag + **list A**, above. (The record's
  fields are still cloned verbatim, so this correction changes no bytes — but
  the docstring is wrong and the next session should not build on it.)

## Open Questions

1. **Donor pick — awaiting the user.** Crawling Dragon is not clean (above).
2. Does anything else key off the donor's ORIGINAL race/attribute once PART D
   makes it a "Watt"? (Nothing found; the Watt set-code table is cid-keyed.)

## Next Experiment

None outstanding — the mechanism is fully mapped. On donor approval, build:
A1 list-A insert, A2 cls1 clone of Fane's row (cid + resolver swapped),
A3 the existing populate row re-keyed, A4 direct-attack-list insert,
PART D re-keyed, `card_type="Effect Monster"`, `card_text` re-keyed, plus the
Quasar tripwire narrowing and an `_assert_fane_untouched` guard.

## ✅ DONE — IN-GAME CONFIRMED by user 2026-09-10, first test, all five oracles

User's words: *"Perfect. No Regressions and the 4) only shows monsters"*, and on
the follow-up question *"No regrssions cover all the points."* — i.e. all five
oracles: the card reads correctly; it declares a DIRECT attack; direct-attack
battle damage fires the search; **the prompt offers ONLY Watt monsters** (the new
is-monster test works); and **attacking into a monster triggers nothing**.

⚠️ THAT LAST ORACLE IS THE REUSABLE RESULT: joining list A and deliberately NOT
joining list B really is "by a direct attack" and not "inflicts Battle Damage".
The two-list split is measured, not inferred.

`rom_wattcobra.nds`, built by
`.venv-1/Scripts/python.exe -m otn_enhanced.cards.wattcobra --text`.

```
A Fane 0x2069 handed back: stock cls1 record + both list memberships intact
A direct-attack list @0x0226D730 (count 25): dropped phantom 0x0EB3, inserted 0x0FD3 @ idx 0
A direct-attack-damage trigger list @0x0226EE7C (count 19): dropped phantom 0x0EC0, inserted 0x0FD3 @ idx 0
A cls1: dropped phantom 0x0E14, inserted [0x0FD3 0x02207EF5 0x021E32D5 0x0224A115 0 0x02234E01] @ idx 57
A populate: dropped phantom 0x2347, inserted [a=0x0FD3 b=0x05DC h=0x0239A441 fl=0x00000002] @ idx 70
A ov5 filter 0x0239A480 (set-code 0x58 AND monster AND DEF<=1500) + wrapper 0x0239A440
Watt set-code: donor 0x0FD3 is entry 0 of the stock 22-entry table -- no edit needed
BEFORE: lvl=3 ... type=Normal Monster   AFTER: lvl=4 ... type=Effect Monster
verify(): 11/11 PASS
```

The 0x40 B filter disassembles clean (Thumb-1 only, both exits `pop {r3,pc}`,
three BLs -> 0x020240D8 / 0x02029E60 / 0x0202AC6C).

**The Spell/Trap deviation is fixed.** `0x02029E60(cid)` (card_intid bit 15 =
MONSTER, `carddata.card_intid_*`) was censused this session against the Watt
table: 1 for every Watt monster, 0 for Wattcube / Wattcine / Wattcannon /
Wattcastle / Wattjustment / Wattkey / Wattkeeper. All 15 Watt monsters have
DEF <= 1500, so the inherited DEF ceiling stays inert.

### Quasar composition, proven offline (no chain build needed to know)

`scratch`-run A/B on `rom_all_patches.nds`'s own overlay:

| state | narrowed tripwire |
|---|---|
| chained ROM as built | PASS |
| chained ROM + this patch's direct-attack insert | PASS |
| simulated 1-entry overrun from Quasar's 0x0226D712 rewrite | **FAIL** (as intended) |

So the tripwire still does its job and the two patches compose.

### KB contributed back

`battle.damage_trigger_is_a_membership_list` (VERIFIED, closed structural proof
over both lists, both count immediates, both posters, and the +08 correction).
`author_facts --check`: **413 PASS / 0 FAIL**.

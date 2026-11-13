# Maiden with Eyes of Blue — findings (RE-only session, 2026-08-19)

Session goal: **map the triggers, build no ROM.** Deliverable = KB entries in
`author_facts.py` + a build-ready design. No patch module, no ROM.

Card text (from `scratch/ygoprodeck_cache.json`, id 88241506 — not recall):

> LIGHT / Spellcaster / **Tuner** / Level 1 / ATK 0 / DEF 0
>
> When a card or effect is activated that targets this card (Quick Effect): You can
> Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. When this
> card is targeted for an attack: You can negate the attack, and if you do, change
> the battle position of this card, then you can Special Summon 1 "Blue-Eyes White
> Dragon" from your hand, Deck, or GY. You can only use 1 "Maiden with Eyes of Blue"
> effect per turn, and only once that turn.

1. (Quick Effect) activated card/effect targets this card → you can SS 1 BEWD.
2. (Battle) targeted for an attack → negate the attack, and if you do, change this
   card's battle position, then you can SS 1 BEWD.
3. (HOPT) 1 Maiden effect per turn, once that turn.

---

## Confirmed (this session, against the committed oracles)

`verify_knowledge` baseline at session start: **222 PASS / 0 FAIL / 32 UNVERIFIED**.

### Maiden is not in the ROM
No `0x295C` in `nds_card_prop.bin`; no such name in `nds_name.bin`. Full conversion.

### Payload: "SS 1 Blue-Eyes White Dragon from hand/Deck/GY" is ONE data row
- Handler **`0x0223E2C9`** (selector at `0x0223E2C8`) reads the row: target cid from
  `[row+2]` (falling back to `[row+0]` when `<= 0`), flags from `[row+8]`, match
  filter `0x0223C6F1` into r7, then calls **three zone builders**:
  `0x0223BC3C` (`[sp+4]=0`), `0x0223C4E8` (`[sp+4]=4`), `0x0223C16C` (`[sp+4]=0`),
  then `pop {r1-r7,pc}`.
- `0x0223C16C` is the **HAND** enumerator — proven: it loads
  `0x0229ACA0 + side*0xB3C` = `player+0x0C` = hand count (same literal the KB pins in
  `event.zone_pair_relocation_emitter`).
- Exactly **11** rows in the criteria/populate table `0x022713C4` use this handler,
  all with `fl = 0x0802`; every legible one is worded "hand, Deck, or Graveyard"
  (Yubel `0x1CF1→0x1CF2`, Yubel-TI `0x1CF2→0x1CF3`, Instant Neo Space, Skilled
  Dark/White Magician, Bonding-H2O, Photon Generator Unit, Limiter Overload,
  Summon Reactor SK).
- Resolver is `0x02206F41` (the generic "SS 1 card matching my row" machine).

### Blue-Eyes White Dragon = cid `0x0FA7`
Three card_prop records carry the name — `0x0ED9`, `0x0F09`, `0x0FA7` — but only
`0x0FA7` is obtainable (`card_pack.bin`: pack1=1/pack2=32; the other two are 0/0,
among the 99 pack-0 cards). All four native namers use `0x0FA7`:

| row | acting cid | card | aux | handler | fl |
|---|---|---|---|---|---|
| 209 | `0x15E0` | Paladin of White Dragon | `0x0FA7` | `0x0223CF45` | `0x0802` |
| 350 | `0x189A` | Kaibaman | `0x0FA7` | `0x0223DAA5` | `0x0802` |
| 767 | `0x1EAA` | The White Stone of Legend | `0x0FA7` | `0x0223D075` | `0x0002` |
| 1184 | `0x22A0` | Malefic Blue-Eyes White Dragon | `0x0FA7` | `0x0223D075` | `0x0002` |

**3DS cross-check:** the 3DS ships Maiden at record 5626, prop cid `0x295C`, main
registry row `{id 0x295C, flag 0x0FA7, handler 0x004A810C, param 0x00000802}` — same
`flag = summoned card id`, same `param 0x0802`, and its 12 handler-sharers are the
same card family as the NDS `0x0223E2C9` set. Two independent builds agree.

### Card-identity comparator (new)
`0x02022E98` (ARM9) = `same_card(cidA, cidB)`: equality, else walk an **alias table
at `0x0209BF8C`** (46 x 4 B `{u16,u16}`, sorted, searched via `0x02022E44`, partner
read at `+2`). Contents are phantom→real promo aliases and Token chains
(`0x0E10↔0x2400`, `0x0F3E↔0x0F3F`, …). **No Blue-Eyes art is in it** — which is
exactly why every native card names `0x0FA7` directly and alt arts are unreachable.

### Effect-registry section geometry (new)
`0x0228E1E0`, stride 8, `[resolver u32][cid u16][pad u16]`. Section bases appear as
literal-pool words; registry-proper bases are rows **1, 48, 63, 288, 293, 429**
(`0x0228E1E8`, `0x0228E360`, `0x0228E3D8`, `0x0228EAE0`, `0x0228EB08`, `0x0228EF48`).
Row 495 = `0x0228F158` = the summon-procedure registry already known from Darkflare —
independent cross-check that the indexing is right. Walker, read verbatim:

```
0225673E  ldr r5,=0x0228E360            ; section base (row 48)
02256744  lsls r2,r0,#3 ; adds r1,r5,r2 ; ldr r1,[r1,#4] ; ldr r2,[r5,r2]
0225674E  blx r2                         ; call the row's resolver
02256764  cmp r0,#0xf                    ; COUNT = 15 (rows 48..62)
```
Phase id stored to `[r4+0x78]`, per-section cursor at `[r4+0x7C]`. This is the
concrete mechanism behind the KB's "position == timing".

Section rows 1..47 are battle-flavoured (Magical Arm Shield `0x12E2`, every Gladiator
Beast, Red-Moon Baby `0x1415`, Helpoemer `0x1571`, Stealthroid `0x1A55`); Stardust
Dragon `0x1E36` is row 78 and Yubel `0x1CF1` row 164, in section 63..287.

### Clause 1 trigger — decoded (static)
A **cls3 record whose slot3 (`+0x0C`) walks the ACTIVATING descriptor's declared-target
array**: `slot3(r0 = my desc, r1 = the activation's desc)`, looping
`0x02234904(act, i)` for `i < [act+0x10]`, comparing the returned `side | (zone << 8)`
against my `desc[+2]` / `desc[+3]`.

| cid | card | record | slot3 | note |
|---|---|---|---|---|
| `0x17C2` | Blue-Eyes Shining Dragon | cls3[172] | `0x021F8135` | exact same trigger wording as Maiden cl.1 |
| `0x2213` | Naturia White Oak | cls3[655] | `0x02201FDD`, `+10=0x021E6FF5` | trigger **+ Special Summon**; opponent-only |
| `0x1F5A` | Inmato | cls3[481] | `0x021FFAD5` | opponent-only, Spell/Trap-only |

White Oak is the structural precedent and carries the "you can" `+10` tag.

Verified independently this session by disassembling `0x021F8134`: `adds r5,r1,#0 ;
bne` bails when `r1 == 0`; gate `0x021AB90C(act, 0)`; then
`for i in range(act[+0x10]): 0x02234904(act, i)` compared against
`(desc[+3] << 8) | desc[+2]`, returning 1 on a hit. The KB already had both
`0x02234904` and `desc[+0x10]` — but **only** as "how a resolver reads back its *own*
picks". Applied to *another* card's descriptor the same pair is the incoming-targeting
test.

### Clause 2 — three verbs, two already solved
| verb | status |
|---|---|
| change own battle position | **solved & shipped**: cls1 `{+04=0x0220C6B1, +0C=0x021F4D4D}`, 16 members; purest template Black Stego `0x1A78` cls1[574] `{0x1A78,0x0220C6B1,0,0x021F4D4D,0,0}`. `patch_ninishi.py` PART A2 already grafts it onto Dverg `0x245B` over phantom `0x1140`. |
| negate the attack | **resolver found**: `0x0221F9E0`, six members, all six cards' printed text says "negate the attack" — Krebons `0x1E24`, Fabled Rubyruda `0x2163`, Morphtronic Boomboxen `0x1EC5`, X-Saber Galahad `0x1E8E`, Necro Gardna `0x1C0A`, Hero Barrier `0x195F`. Template: Krebons cls1[849] `{0x1E24,0x0221F9E1,0,0,0x021E780D,0}` (cost in the swappable `+10`). |
| both verbs at once | Morphtransition `0x1EF6` cls0[1002], resolver `0x0221158C` — the only OTN card with Maiden's exact verb pair. |
| the "targeted for an attack" EVENT | **SOLVED — selector-1 event code 0x13.** See below. |

The whole family is **cls1** with `+0C = 0` (Krebons) or a generic `+0C` (Black
Stego's `0x021F4D4D` is the *face-up Attack Position* gate), so the discrimination is
carried by the **event descriptor**, not by a condition.

### ⭐ SOLVED: "targeted for an attack" = selector-1 event code **0x13**

Closed statically, producer and consumer, entirely on the committed oracles.

**Consumer.** Krebons `0x1E24` = cls1[849], `+04 = 0x0221F9E1`. That resolver's first
act is an event-code gate on `desc[+4]`:

```
0221F9E4  ldrb r0,[r5,#4]      ; desc[+4] = event code
0221F9E8  adds r0,#0xED
0221F9EA  lsls r0,#0x18 ; lsrs r0,#0x18
0221F9EE  cmp  r0,#1
0221F9F0  bhi  0x0221FA12      ; everything else
```
`(code + 0xED) & 0xFF <= 1` ⇒ **code ∈ {0x13, 0x14}**. Krebons is not the `0x195F`
(Hero Barrier) special case, so `bne` at `0x0221F9F8` sends it straight to
`bl 0x0221F944`. The other arm only turn-logs, for `0x195F` / `0x1C0A`.

**Producer.** The ONLY selector-1 posts of code `0x13` in the whole overlay are five
sites — `0x021C6390`, `0x021C641C`, `0x021C65AC`, `0x021C6798`, `0x021C6882` — all
inside the single function **`0x021C6304`**, and every one takes the poster's
`zone_index` from the battle context **`0x02298AD8`**:

```
021C6386  movs r1,#8 ; ldrsh r1,[r6,r1]     ; r6 = 0x02298AD8 (loaded 0x021C636E)
021C6788  ldr  r2,=0x02298AD8 ; ldrsh r1,[r2,#0xA]
```
Since `poster_cls1 0x021D3230(side, zone_index, code, arg)` resolves the cid FROM
(side, zone), the event lands on **the monster occupying the attack slot**. Two slot
fields (`+8` and `+0xA`) with two different side arguments ⇒ the event is announced to
both battle participants. `0x021C6304` is called from **`0x0224F3D4`**, inside the
battle-sequencer band.

⚠️ Code `0x14` is never posted with an immediate through `0x021D3230` (full histogram:
`{0x00:9, 0x01:1, 0x02:4, 0x06:6, 0x0C:2, 0x0D:1, 0x0E:2, 0x10:11, 0x13:5, 0x15:6,
0x16:1, 0x17:1, 0x18:4, 0x19:2, 0x1B:1, 0x1F:1}`); three sites build `r2` indirectly
and are unread. **Accept both codes the way Krebons does** rather than pinning one —
pinning a discriminator to a single code measured on another card's path is precisely
what cost Lightpulsar clause 3 a duel.

### ⭐ SOLVED: "negate the attack" = command opcode **0x1F**

`0x0221F944` reads the battle context `0x02298AD8` (`ldrsb r4,[r1,#0]` = side,
`ldrsh r5,[r1,#8]` = attack slot), runs five gates, then builds
`r0 = 0x1F | (side ? 0x8000 : 0)` and calls the command-queue append
`0x021C3BC8(op, slot, 0, 0)`. Opcode `0x1F` is arm `0x021C3DE4` → handler
`0x021BC274` in the dispatcher `0x021C3C3C`.

**The cost is the cls record's `+10`, not the resolver** — Krebons 800 LP
(`0x021E780D`), Rubyruda/Galahad discard-send (`0x021E5201`), Necro Gardna GY-banish
(`0x021E5709`), Hero Barrier free (`0`). A donor gets "negate the attack" at any cost
by cloning Krebons' five-word record and swapping `+10`.

### ⭐ SOLVED: battle position lives at `0x0229ACCE + side*0xB3C + slot*0x14`

`0x0220C6B0` sets `r4 = 1` (→ Defense) unless the cid is Reptilianne Naga `0x21B4`
(→ Attack, `r4 = 0`), gates on `0x021D2C1C(desc)`, reads the current position at that
address, and if it differs calls **`0x021C5324(desc, side, zone, 0, 1)`** — the
set-battle-position primitive. Black Stego's `+0C` `0x021F4D4C` reads the *same*
halfword and returns 0 when it is nonzero: the "face-up **Attack** Position" gate.

### Donor: Water Spirit `0x1E05`
L1 WATER Aqua **Normal Tuner** 400/1200, pack 54. Records-free across cls0–cls3, the
criteria registry, the effect / summon-procedure / GY-action registries, the
leave-mask table and both fusion tables, with **zero** LDR-reached u32 cid literals in
overlay 3. Already Level 1 and already a Tuner.

- Tier A (L1 LIGHT Spellcaster **Normal**) is **empty**.
- Only L1 LIGHT Normal Monster is Mokey Mokey `0x1782` — disqualified twice (fusion
  material for `0x183D`; live literal in the stat engine at `0x021B4BFA`).
- Backups: Charcoal Inpachi `0x17CD`, Unicycular `0x21A4`, Gigobyte `0x1783`,
  Cloudian - Smoke Ball `0x1C6D`.
- Retune needed: WATER→LIGHT, Aqua→Spellcaster, 400/1200→0/0, `card_type` 31→33.
- **Tuner is not a bit** — it is `card_prop` `card_type` bits `[32:38]`: `1` Normal,
  `31` Normal Tuner, `33` Tuner. Written via `apply_stats_and_text(card_type=…)`.

### `scratch/bin2/card_prop.bin` is a randomiser output, not a decoder bug
`card_intid.bin`, `card_pack.bin`, `card_indx_e.bin`, `card_name_e.bin` are
byte-identical to the in-ROM copies; `card_prop.bin` differs in **2521 of 4305**
records, and the differences are confined to **race + attribute** (level and ATK/DEF
preserved). ⇒ the ERA2 bitfield layout is CORRECT. This closes the standing
`next_experiment` on `tool.card_prop_race_attr_decode`.

Canonical read: `card_prop.bin` **from the ROM**, `8-byte header + 4305 x 8`. An
offset-0 read is shifted by one record.

---

## Ruled Out

- **The KB had nothing on any of this.** Grepping every `otn_enhanced/docs/engine/*.yaml` for
  `targeted by|is targeted|targets this card` → 0 matches; for attack
  declaration/negation → only capability lists (`battle.double_attack_list`,
  `direct_attack`, `pierce`, `indestructible`) and restriction chains
  (`rider.no_direct_attack_gate 0x021A6680`, `rider.attack_restriction_chain
  0x021A4770`). No attack-declaration/target/damage-step fact at any grade.
- **The criteria registry is OUTGOING targeting only** — "what may this card's effect
  pick, and from where". Being in someone else's pool is not recorded in your rows.
  So it is not where "this card is targeted" lives.
- **`leave.flip_primitives` are the wrong primitives** for clause 2's position change:
  `0x021C4F24` / `0x021C5894` are **face-up/face-down** flips (slot resolution via
  `0x021A36EC`, `slot*0x14` indexing), not Attack↔Defense. The real one is
  `0x0220C6B1`.
- **Not the alias table.** `0x0209BF8C` does not relate the three Blue-Eyes arts, so a
  by-name row cannot pick up `0x0ED9` / `0x0F09`. Irrelevant in practice — both are
  unobtainable.
- **Rejected sub-agent claim:** "nothing native does hand or Deck or GY in one row".
  That sweep looked only at handlers `0x0223CF45` / `0x0223DAA5` / `0x0223D075` and
  never at `0x0223E2C9`. Direct disassembly (three zone builders), the 11-row text
  census and the 3DS `param 0x0802` family all contradict it.
- **Krebons' arm is not the resolver prologue.** `0x0221F9E0` opens with
  `ldrb r0,[r5,#4] ; adds r0,#0xED ; lsl/lsr #0x18 ; cmp r0,#1 ; bhi 0x0221FA12`
  ⇒ event codes `{0x13, 0x14}` take one path and everything else the other, but
  **both paths then dispatch by cid**, so that split is a two-family branch inside a
  shared resolver, NOT the attack gate. (The same function also tests cid `0x195F`
  and the "Elemental HERO" set-code thunk `0x0202381D`.) Do not read it as
  Krebons-specific.

---

## Open Questions

1. **Which caller passes a non-zero `r1` (the activating descriptor) into cls3 slot3?**
   The condition itself is closed; the INVOKER is not. `0x0224AD94` has 39 callers;
   both callers of COMMIT `0x021EDA08` (`0x021D31CC`, `0x02263A76`) pass `r1 = 0`, so
   the admission path is out. Strongest candidate: the queue walker
   `0x021D3322..0x021D33A4`, which calls `0x0224AD94(desc, r6)` at `0x021D333E` and
   `0x021D33A4` (both confirmed present this session).
2. **What is event code `0x14`?** Krebons accepts `{0x13, 0x14}`. `0x14` is never
   posted with an immediate through `0x021D3230`; three sites build `r2` indirectly
   (`0x021C9EBC`, `0x021D3558`, `0x0224677E`) and are unread. Presumed a sibling of
   `0x13` (attack replay / second attack?).
3. **Ordering and optionality of clause 2's three steps.** Settle from the 3DS router
   `0x0040D528` (unique to Maiden; a four-state FSM on `[base+0xBB4]`, states
   `0x7D/0x7E/0x7F/0x80`, calling `0x004343A4`, `0x003CD1A4`, `0x00385898`,
   `0x0049D508`, `0x004632B0`). Semantic oracle only — never an NDS address.
4. **Donor `0x1E05` residual vetting**: not yet swept against the ritual-material
   tables, the Cocoon/evolution table, or the ARM9 archetype/set-code tables.
5. **How wide is the randomised-`card_prop` blast radius?** Both cached copies carry
   randomised race/attribute. Nothing in the KB depends on them for race/attribute
   today, but any past donor filter built on that path is suspect.

---

## Next Experiment

**E1 — close the clause-1 invoker (static first).** Walk the 39 callers of
`0x0224AD94` and find those whose `r1` is not an immediate zero; the queue walker
`0x021D3322..0x021D33A4` is the prime suspect. If static analysis cannot close it:
one GDB breakpoint at `0x021F813A` (Blue-Eyes Shining Dragon's `r1 != 0` test) in an
active **normal** duel; activate any targeting card on a face-up BESD and read `lr`
and `r1`.

**E2 — confirm code 0x13 on the live path (optional; the static chain is closed).**
Breakpoint `0x021C6304` and `0x0221F944` while a Krebons or Black Stego is attacked;
read `desc[+4]` and `desc[+5]`.

⚠️ Either way the melonDS stub is **ONE-SHOT**: connect exactly once, arm everything
in a single script, collect in one wait window, write results to a file, never probe.
Confirm an active normal duel (a puzzle loads ov41 over ov5) before connecting.

---

## Build-ready design (for the NEXT session — nothing below was built)

**Donor:** Water Spirit `0x1E05` (L1 WATER Aqua Normal Tuner 400/1200, pack 54).
Retune via `apply_stats_and_text`: attribute WATER→LIGHT, race Aqua→Spellcaster,
ATK/DEF→0/0, `card_type` 31→33 (Tuner). Name/desc/art per the usual PART C/E.

**Shared payload — one criteria row** (count-neutral over a phantom; criteria pool has
80 free):
```
{ a = 0x1E05, aux = 0x0FA7, handler = 0x0223E2C9, flags = 0x0802 }
```
= "Special Summon 1 Blue-Eyes White Dragon from your hand, Deck, or Graveyard."

**Clause 1 — cls3 record** (cls3 has 78 free phantoms), modelled on Naturia White Oak
`0x2213` cls3[655]:
```
{ cid = 0x1E05, +04 = 0x02206F41, +08 = 0, +0C = <targeting condition>,
  +10 = 0x021E6FF5 (optional "you can"), +14 = 0 }
```
`+0C` can be `0x021F8135` verbatim (Blue-Eyes Shining Dragon's — no opponent-only
filter, which matches Maiden's printed text: it responds to *any* card or effect,
including your own) or White Oak's `0x02201FDD` if an opponent-only gate is wanted.
⚠️ Maiden's real text says "**during either player's turn** … except during the Damage
Step" (per the 3DS description); the Damage-Step exclusion is not modelled here.

**Clause 2 — cls1 record** (cls1 has 141 free phantoms), Krebons' shape with the
position change folded in:
```
{ cid = 0x1E05, +04 = <negate ∘ flip ∘ summon>, +08 = 0, +0C = 0,
  +10 = 0 (costless — Maiden pays nothing), +14 = 0 }
```
The three verbs are all available: negate = `0x0221F944` (or the whole shared resolver
`0x0221F9E1`), flip = `0x021C5324(desc, side, zone, 0, 1)`, summon = the criteria row
above via `0x02206F41`. **Morphtransition `0x1EF6`'s resolver `0x0221158C` already
does negate-then-flip as one function** — read it first; if it is cid-generic it may be
usable directly, leaving only the summon to chain.

**Composition check:** clause 1 is cls3 and clause 2 is cls1 — different tables, so no
`find_event_handler` leftmost-record shadow (the bug that made Warwolf E1 shadow E2).
Both clauses share the single criteria row, which is correct: one row, one payload.
Confirm rather than assume at build time.

**Clause 3 (HOPT):** the turn-log pair is already mapped and cid-generic —
`POST 0x021D2584(side, cid, 1, 0)` / `QUERY 0x021A14E8(side, 0xB, cid, 1)` (Pot of
Duality's mechanism, reused by Dragon Shrine). Note the shared negate resolver ALREADY
turn-logs via `0x021D2584` on its non-0x13 arm, for `0x195F` / `0x1C0A`.

**Cost:** if both clauses land as cls records + one criteria row, this card costs
**zero ov5 cave** and works in puzzles too. Cave state if needed:
`CAVE_FREE = 0x0239C990`, 0x1790 = 6032 B free.

---
---

# BUILD SESSION — 2026-08-20

Baseline re-verified at session start: `verify_knowledge` = **269 facts, 238 PASS,
0 FAIL, 31 UNVERIFIED** (matches the handoff exactly — KB has not rotted).

Card text re-read from `scratch/ygoprodeck_cache.json` id 88241506 (not recall);
byte-identical to the text quoted in the RE session above.

## Confirmed (this session)

### `0x0221F944` is a fully cid-generic, self-driven "negate the attack" worker
Disassembled `0x0221F944..0x0221F9CC` this session. Signature
`negate_attack(desc, event) -> int`:
- side = `0x02298AD8[+0]` (ldrsb), attack slot = `0x02298AD8[+8]` (ldrsh) — read
  from the battle context, **not** from the descriptor and **not** from a pick
  array, so it is caller-independent.
- gate A: `0x0229C294[+0x78]` bit0 clear AND bit1 set (the "an attack is live and
  still negatable" pair).
- gate B: `0x021968BC(side, slot)` nonzero.
- gate C: `0x0229ACD8 + side*0xB3C + slot*0x14` (u32) bit **25** set.
- gate D: `0x0229ACD0 + side*0xB3C + slot*0x14` (u16) nonzero.
- gate E: `0x021AFCBC(desc, side, slot)` == 0.
- action: `r0 = 0x1F | (side ? 0x8000 : 0)`; `0x021C3BC8(op, slot, 0, 0)`.
- **returns 1 when the attack was negated, 0 on any gate failure.**

⇒ this single call is clause 2's verb 1 *and* its "and if you do" gate, for free.
No cid literal anywhere in it.

### `0x0221158C` is a SHARED negate resolver with a per-cid tail (not Morphtransition's)
Disassembled `0x0221158C..0x022116AE`. Structure:
1. same `0x0229C294[+0x78]` bit0/bit1 gate as `0x0221F944`;
2. `0x022349B0(desc,0,0)` then `0x02234904(desc,0)` — reads **pick #0** →
   side/zone, validated by `0x0224A924(desc,side,zone)`;
3. negate: `r0 = 0x1F | (side?0x8000:0)`; `0x021C3BC8`; then
   `0x0229AAFC[+0x74] = 1`;
4. **then** a switch on `desc[+0]` (the cid): `0x0E71`, `0x0E86`, `0x1404`,
   `0x176A`, `0x1EF6` → per-card tails; default → return.
5. Morphtransition's arm `0x0221166A` reads **pick #1** and calls
   `0x021C5324(desc, side, zone, 0, 1)` — the position change on the *second*
   picked card.

⇒ **not reusable for Maiden**: its front half is target/pick-driven (Morphtransition
is a Trap that picks the attacker and the monster to flip). Maiden is self-driven.
Correcting the handoff's hopeful reading: it is *not* a cid-generic
negate-then-flip that only needs the summon chained.

### `0x0220C6B0` is "change to **Defense** Position", not a true toggle
`r4 = 1` (Defense) for **every** cid except Reptilianne Naga `0x21B4` (`r4 = 0`,
Attack). It then compares `r4` against the live position halfword at
`0x0229ACCE + side*0xB3C + slot*0x14` and only calls
`0x021C5324(desc, side, zone, 0, 1)` when they differ.
Its 16 members pair it with condition `0x021F4D4D` = "face-up **Attack** Position",
so natively the family only ever does Attack→Defense.
⇒ For Maiden (which can be attacked in Defense too) a faithful "change the battle
position" needs `r4 = 1 - current`, i.e. ~10 bytes of our own code.

## Ruled Out (this session)

- **"Clause 2 costs zero cave."** It does not. Clause 2 needs one cls1 record whose
  `+04` sequences negate → flip → summon, and no native resolver does that
  self-driven (see `0x0221158C` above). `find_event_handler` returns the leftmost
  same-cid record, so we cannot split clause 2 across two cls1 records either.
  Budget a small ov5 cave stub.

### `0x02206F41` is the SS machine, and the donor rides its DEFAULT arm
Phase machine on `[0x0229AAFC+0x70]`, jump table @`0x02206FF6` (12 arms, phases
0x75..0x80), each arm **returning the next phase** (0 = done):

| phase | arm | what it does |
|---|---|---|
| 0x80 | `0x0220700E` | entry: per-cid turn-log; gate `0x021F0384(desc,event)`; count candidates `0x02243FA8(side, cid, 0x02234E78(desc))`; 0 → prompt 0x122, return **0x78**; else prompt 0x11D, return **0x7F** |
| 0x7F | `0x02207082` | open the picker `0x0219C430(side, 6, cid, param)`, return **0x7E** |
| 0x7E | `0x02207098` | read the pick and summon, return **0x7D** |
| 0x7D / 0x78 / 0x75 | `0x02207116` / `0x02207124` / `0x02207140` | teardown |

This independently CONFIRMS the previously-UNVERIFIED `resolver.phase_protocol`
(entry at phase 0x80, resolver returns the next phase).

Its prologue switch on `desc[+0]` only sets two flags (r6/r7) and has **no
stack-held base** (`str r1,[sp]` stores the *event*), so a concrete register trace
is sound here. Traced for every user: `0x1610`, `0x1611`, `0x167D`, `0x1713`,
`0x195C`, `0x19B1`, `0x1CF1`, `0x1D17`, `0x1F35`, `0x1F3E` **all take the DEFAULT
arm (r6 = r7 = 0)** — as does any records-free donor. The default is the beaten
path, not an exception.

### The rest of the clause-2 chain, all cid-generic
- `0x021C5324(desc, side, zone, 0, [sp]=1)` takes **no target-position argument** —
  it is a *toggle*. `0x0220C6B0`'s `cmp r4, r0 ; beq` is only a guard ("don't act if
  already in the position I want"), so calling the primitive unconditionally IS the
  faithful "change the battle position of this card". No position read needed.
- `0x021D2C1C(desc)` = still-on-field gate; `0x021D2D18(desc)` = re-sync
  `desc[+2]`/`desc[+3]` from the locator `desc[+0xC]` via `0x021A241C`.
- `0x0224AD94` runs slot3 as `slot3(desc, event)` (`ldr r2,[r4,#0xC] ; ldr r1,[sp] ;
  adds r0,r5 ; blx r2` @`0x0224AE06`) and returns 1 iff the code is > 0. Confirms
  `dispatch.cls_slot_roles`.
- `0x021D2584(r0=side, r1=cid, r2=kind, r3=0)` → `0x021C479C(side, 0xB, cid, kind,…)`.
  Confirms `dispatch.turnlog_once_per_turn_pair`'s signature byte-for-byte.
- The costless **"you can" tag** is `0x021E51E5` → thunk → `0x021E50DC`: phase 0
  runs `0x0224AD94`, then prompt id `0x107` + `0x0219A798(cid)` +
  `0x0219A818(side,1)`. 352 + 93 records use it. Cid-generic.

### ⭐ DONOR CHANGED: Comrade Swordsman of Landstar `0x1ED7`
Water Spirit `0x1E05` is **rejected at build time** for a reason the RE session did
not check: its **English name slot is 12 B** and "Maiden with Eyes of Blue" is 24 B.
The name blob must not be grown (`patch_gravekeepers_recruiter`,
`patch_hyper_librarian`, `patch_elder_six_samurai` all pass
`skip_name_if_too_long=True`; `patch_boggart_knight` records that growing it
correlated with in-game trouble), so the card would have shipped reading
"Water Spirit".

`0x1ED7` is better on every axis:

| | 0x1E05 Water Spirit | **0x1ED7 Comrade Swordsman of Landstar** |
|---|---|---|
| name slot (min over 8 langs) | 11 B | **24 B** — exactly fits, in every language |
| desc slot (min) | 96 B | 51 B (English; the floor) |
| `card_type` | 31 Normal Tuner → needs 33 | **already 33 Tuner Monster** |
| stats | L1 WATER Aqua 400/1200 | L3 EARTH Warrior 500/1200 |
| records (cls0-3 / criteria / effect reg / summon-proc reg / leave-mask) | none | **none** |
| aligned u16 + u32 refs in ov3 + arm9 | 0 | **0** |
| nameable by the Synchro-material switches | **YES (over-approx)** | **NO** |

That last row is the decisive one. `thumb-stack-based-switch-footgun` says per-cid
switch arms encode cids as `base ± imm` and are **ungreppable**, so a raw value
sweep cannot clear a donor. Over-approximating the nameable set of the OUTER
(`0x022485B4`) and INNER (`0x0224829C`) named-material predicates — every
cid-range literal-pool base, crossed with every imm8 in the function — gives 1810
and 603 cids. `0x1ED7` is in **neither** (a sound negative). `0x1E05` **is** in the
OUTER set. For a card that is a Tuner and will be used as Synchro material, that
gap matters.

Retune: EARTH→LIGHT, Warrior→Spellcaster, Level 3→1, 500/1200→0/0.

## Build-ready design — CLAUSE 2 (this session's scope)

**Donor** `0x1ED7`. **Zero ov3 code edits** — two count-neutral data inserts plus
two ov5 stubs.

**A1 — cls1 count-neutral insert** (drop phantom `0x1DB6` @cls1[815], insert at 907):
```
{ 0x1ED7, +04 = CAVE_MAIDEN_RES|1, +08 = 0, +0C = CAVE_MAIDEN_COND|1,
          +10 = 0x021E51E5, +14 = 0 }
```
**A2 — criteria count-neutral insert** (drop phantom `0x1BBE` @crit[517], insert at 777):
```
{ cid 0x1ED7, aux 0x0FA7, handler 0x0223E2C9, flags 0x0802, extra 0x0000 }
```
**B — `CAVE_MAIDEN_COND`** (slot3): Krebons' `{0x13,0x14}` event-code test, then Pot
of Duality's turn-log query `0x021A14E8(side, 0xB, cid, 1)`; 2 = activate, 0 = no.

**B — `CAVE_MAIDEN_RES`** (slot1): on phase 0x80 only — post the turn log, call
`0x0221F945` (negate; **returns 1 iff it negated** = the "and if you do" gate),
bail returning 0 if it did not, else `0x021D2C1D` gate → `0x021D2D19` re-sync →
`0x021C5325` toggle the battle position; then **every** phase tail-calls
`0x02206F41`.

Both phantoms verified UNIQUE, unclaimed, and absent from card_prop; both inserts
verified to keep each table sorted with **no duplicate-cid group split** (which
matters for cls1 because of `dispatch.find_event_handler_second_record`).

**Composition:** one cls1 record only, so the `+1` second-record rule falls back to
leftmost. No cls3 record this session, so clause 1 cannot shadow it later either
(different table). The criteria row is shared by both clauses by design.

---

## SHIPPED (built 2026-08-20, NOT yet in-game confirmed)

`otn_enhanced/cards/maiden_eyes_of_blue.py`, chained into
`apply_all_patches.py` as step **30 of 35**, above the card-art step and well above
the WiFi-timers step (which must stay last).

| part | what | where |
|---|---|---|
| A1 | cls1 record `{0x1ED7, CAVE_MAIDEN_RES\|1, 0, CAVE_MAIDEN_COND\|1, 0x021E51E5, 0}` | ov3, count-neutral over phantom `0x1DB6` (row 815 → insert at 907) |
| A2 | criteria row `{0x1ED7, 0x0FA7, 0x0223E2C9, 0x0802, 0x0000}` | ov3, count-neutral over phantom `0x1BBE` (row 517 → insert at 777) |
| B  | `CAVE_MAIDEN_COND` 44 B / 0x40 reserved | ov5 `0x0239C990` |
| B  | `CAVE_MAIDEN_RES` 112 B / 0x80 reserved | ov5 `0x0239C9D0` |
| C  | LIGHT / Spellcaster / Lv1 / 0 / 0, card_type 33 | bin2.pac `card_prop` |
| D  | name + desc, **in place in all eight languages** | bin2.pac |

`CAVE_FREE` `0x0239C990` → `0x0239CA50`; **5840 bytes still free.**

### Checks run
- Both stubs **disassembled out of the built ROM** and read back instruction by
  instruction (`assert_thumb1_only` rejects Thumb-2, it does not check meaning).
  Every literal resolves to the intended engine function, every branch target is
  right, and both stubs `POP {…, pc}` rather than tripping the POP-into-LR footgun.
- Name landed in **e/f/g/i/s/j/k/r** (24/29, 24/34, 24/36, 24/31, 24/31, 24/26,
  **24/24**, 24/50); description landed in all eight (48 B vs a 51 B floor).
  `bin2.pac` unchanged in size (+0 B) — nothing was grown.
- `check_allocations`: 106 ov5 slots, 62 phantom claims, **no overlaps, ledger in sync.**
- Combined build: **all 35 patches applied, exit 0.**
- `verify()` run against `rom_all_patches.nds` for **every** patch module in the
  tree: **26 PASS** (including this one), 13 no-`verify()`, and 2 FAIL —
  `wonder_wand` and `zeta_reticulant`, which are **not in `PATCHES`** and fail
  **identically on the stock ROM**, so they are pre-existing and unrelated.
- KB: **274 facts, 243 PASS, 0 FAIL, 31 UNVERIFIED.**

### One real bug this caught, worth keeping
The first `verify()` anchored Black Stego at `cls1[574]` **by row index**. That
passes on the single-card ROM and FAILS on the combined one, because
`patch_ninishi` also inserts into cls1 and shifts every row below its insert down
by one. Anchors into a table that other patches edit must be **looked up by cid**,
never by index. (`patch_maiden_eyes_of_blue.verify()` now does.)

### KB contributions
- `resolver.phase_protocol` **UNVERIFIED → VERIFIED** — closed structurally on
  `0x02206F40`'s jump table; the old "act at 0x80, return 0x7F" was one card's next
  step, not the protocol (the return value is a phase id).
- `battle.position_primitive_is_a_toggle` — NEW; corrects the natural misreading of
  `battle.change_own_position_resolver`'s `r4` as a target position.
- `dispatch.costless_you_can_tag` — NEW; closes the "which slot carries optionality"
  open question on `event.optionality_is_the_record`. It is **slot4**.
- `donor.name_slot_floor` — NEW; the donor sweep must include name-slot capacity.
- `tool.ungreppable_switch_overapprox` — NEW; a cheap **sound negative** for
  clearing a donor against a switch that cannot be grepped.
- `card.maiden_clause2` — NEW; the shipped card, deviations included.

---

## Next Experiment

**E0 — IN-GAME TEST of clause 2 (the arbiter; nothing here is confirmed until it runs).**
Normal duel (ov5 is not resident in a puzzle). Put Maiden face-up on the field with a
Blue-Eyes White Dragon somewhere in hand, Deck or GY, and have the opponent declare an
attack on her. Expected, in order:
1. a Yes/No prompt (prompt id `0x107`, naming the card);
2. the attack is negated;
3. Maiden's battle position changes (**both** directions — test her in Defense too,
   since that is the deliberate deviation from the 16 native cards);
4. a second prompt and Blue-Eyes is Special Summoned;
5. attacking her again the same turn offers **nothing** (clause 3).
Also confirm she still Synchro-Summons normally as a Level 1 Tuner.

**E1 — clause 1's invoker** (unchanged from the mapping session): which of the 39
callers of `0x0224AD94` passes a non-zero `r1`? Prime suspect the queue walker
`0x021D3322..0x021D33A4`. Static first; if that fails, ONE breakpoint at `0x021F813A`
in an active normal duel, activate any targeting card on a face-up Blue-Eyes Shining
Dragon, read `lr` and `r1`. ⚠️ The melonDS stub is ONE-SHOT.

---

# IN-GAME TEST 1 — FAILED, ROOT CAUSE FOUND (2026-08-20)

User report: clause 2 did not trigger when Maiden was targeted for an attack.
Savestates `rom_maiden.ml2..ml5`.

## Confirmed by savestate (the patch is NOT the problem)

Parsed all four states (`SaveState`, RAM0 auto-detected at file offset 0x24):

- **ov5 IS resident and both stubs match byte-for-byte** — `CAVE_MAIDEN_COND`
  @`0x0239C990` and `CAVE_MAIDEN_RES` @`0x0239C9D0` compare equal to the builders'
  output. The cave is live, not evicted.
- **The cls1 record is live in RAM at row 907**:
  `{0x1ED7, 0x0239C9D1, 0, 0x0239C991, 0x021E51E5, 0}` — exactly as built.
  Phantom `0x1DB6` is gone.
- **The criteria row is live at row 777**: `{0x1ED7, 0x0FA7, 0x0223E2C9, 0x0802, 0}`.
- **Maiden is on the field**: side 0, zone 2, cid `0x1ED7` at player+0x5C, position
  halfword 0 = face-up **Attack Position**.
- **The battle context `0x02298AD8` is correctly populated**: `[+0]` side 1,
  `[+8]` slot 2, `[+0xA]` slot 2; in ml5 `[+0x16..0x1A]` holds three copies of
  `0x1ED7`, so the engine did know Maiden was the target.
- `[0x0229C294+0x78]`: ml3 = 0, ml4 = **2**, ml5 = **3**. `0x0221F944` needs
  `bit0 == 0 && bit1 == 1`, so the negate was legal at ml4 and had closed by ml5
  (LP 8000 → 6200: the attack resolved for 1800).

⇒ Nothing in the patch is wrong. The record is simply **never dispatched**.

## ⭐ ROOT CAUSE: the code-0x13 post is GATED BY A 26-CID SWITCH

`battle.attack_target_event_code` says the five code-`0x13` post sites live in
`0x021C6304` and that the event "lands on the monster occupying the attack slot".
**That is materially incomplete: every one of the five sites is guarded, and the
guards are per-cid.** The five are not equivalent:

| site | slot arg | guard |
|---|---|---|
| `0x021C6390` | `[+8]` (the **attacker**) | membership in the 17-entry sorted cid list `0x0226E740`, searched by `0x02022E14` |
| `0x021C641C`, `0x021C65AC`, `0x021C6882` | loop counter `r6` = 0..4 / 0..0xA | zone-sweep broadcasts, not the target path |
| **`0x021C6798`** | **`[+0xA]` (the TARGET)** | **`cmp r6,#0 ; beq` @`0x021C678A`, where `r6` comes from a per-cid switch at `0x021C6620`** |

The 17-list is the ATTACKER family — Gravekeeper's Assailant, Turbo Warrior /
Turbo Synchron, Light End Dragon, Neo-Spacian Glow Moss, Chaos King Archfiend,
Vylon Soldier / Sigma, Dark Diviner, Exodius, Evil HERO Dark Gaia … i.e. "when
this card **declares** an attack". Not our path.

The TARGET gate is `0x021C6620`:
```
movs r6, #0                 ; DEFAULT: DO NOT POST
adds r0, r4, #0             ; r4 = the target's side
bl   0x021A37D8             ; -> r2 = the TARGET's cid
ldr  r0, =0x1E24  (Krebons) ; ...an ordered per-cid compare chain...
ldr  r1, =0x1A78  (Black Stego)
0x021C6754: movs r6,#1      /  0x021C6758: ldr r6,[sp,#0x10]
0x021C678A: cmp r6,#0 ; beq 0x021C679C     <-- skips the post entirely
```

**Measured, not inferred** (thumb-stack-based-switch-footgun: the arms encode cids
as `base ± imm`, so this had to be *executed*). A concrete Thumb interpreter run
over the whole cid space `0x0D48..0x24E8` gives **exactly 26 accepted cids**:

```
0x0E65 0x1A73* 0x1A78 0x1ACA* 0x1B8F 0x1C4F 0x1CB1 0x1CCC* 0x1CF5 0x1D05
0x1D11* 0x1E24 0x1E8E 0x1EBF 0x20E5 0x2163 0x21CE 0x22EC 0x22FF
0x2388 0x2389 0x238A 0x238B 0x238C 0x2466 0x2467          (* = r6 from [sp,#0x10])
```

The set self-validates: it is **precisely** the negate-attack family (Krebons
`0x1E24`, Galahad `0x1E8E`, Rubyruda `0x2163`) plus the position-change family
(Black Stego `0x1A78`, Mad Archfiend `0x1EBF`, all five Karakuri `0x2388..0x238C`)
plus Decoy Dragon `0x1C4F` — every card whose printed text is "when this card is
targeted for an attack".

- **`0x1ED7` (Maiden's donor): REJECTED.** No event is posted, so
  `find_event_handler` is never called, so the cls1 record — correct and live —
  is never reached. This is the whole failure.

## ⚠️ COLLATERAL: patch_ninishi's PART A2 clause is ALSO dead

**`0x245B` (Dverg of the Nordic Alfar, the Ninishi donor): REJECTED** by the same
gate. So Ninishi's grafted "when this face-up card is selected as an attack target,
change its battle position" clause **cannot ever have fired in-game**, and
`battle.change_own_position_resolver`'s "ALREADY PROVEN IN-GAME: patch_ninishi.py
PART A2" is WRONG — what was confirmed in-game must have been Ninishi's *other*
clause (the Karakuri extra Normal Summon). Trusting that claim is what let this
card be built with a dead trigger.

**Lesson for the KB: "a shipped patch does X" is not evidence that X fires.**

## Ruled Out

- ov5 eviction / puzzle mode — the cave is resident and byte-correct.
- A wrong or shifted cls1 / criteria insert — both live and exact in RAM.
- The donor not being on the field, or being face-down / wrong position.
- The negate worker's own gates — they were satisfiable at ml4.
- The condition stub rejecting — it is never even reached, because no event exists.

## THE FIX (built 2026-08-20, awaiting in-game test 2)

The gate switch cannot be extended by data. Every one of the 8 cid-range words in
its literal pool (`0x021C68B4..` = `0x1E24, 0x1C4F, 0x1A78, 0x0E65, 0x22EC, 0x20E5,
0x2466, 0x2467`) was rewritten to `0x1ED7` and the whole cid space re-simulated;
**none gave a clean swap** — each either admitted extra cids or dropped a real card
(e.g. `0x1E24 -> 0x1ED7` gains `{0x1F41, 0x1F72, 0x1ED7}` and loses Krebons,
Galahad and Mad Archfiend). An ordered compare tree does not take new leaves.

**PART A3 — retarget the one BL that feeds the switch its cid.**
`0x021C6624`'s `bl 0x021A37D8` → `CAVE_ATKTGT_GATE`:

```
push {r4, r5, lr}
ldr  r4, =0x021A37D9 ; blx r4      ; the ORIGINAL cid_at(side, slot)
ldr  r4, =CAVE_ATKTGT_LIST         ; zero-terminated u16 admit list
scan: ldrh r5,[r4] ; cmp r5,#0 ; beq out
      cmp r5,r0 ; beq hit ; adds r4,#2 ; b scan
hit:  ldr  r0, =0x00001CB1         ; a PHANTOM cid the native tree already accepts
out:  pop  {r4, r5, pc}
```

Why this is safe, and each part is checked rather than assumed:
- **The remap target `0x1CB1` is one of the 26 accepted cids AND has no
  `card_prop` record**, so no real card's identity is borrowed even transiently.
- **The cid register is dead after the switch** — the caller reloads `r2` with
  `=0x02298AD8` at `0x021C6788`, and the post itself uses only `r4` (side) and
  `[0x02298AD8 + 0xA]` (slot). Verified by disassembly.
- **The switch bytes are bit-identical.** Diffing the built overlay 3 against the
  stock oracle across `0x021C6620..0x021C6790` shows **exactly four bytes changed —
  `0x021C6624..27`, the hooked BL, and nothing else** — so every other cid's
  routing through the tree is unchanged by construction.
- Everything not in the admit list is returned untouched, so the hook is inert for
  all other cards.

`CAVE_ATKTGT_LIST` is a **shared, data-driven** admit list: adding a cid is a
one-line edit. Ninishi's Dverg `0x245B` belongs there if that clause is wanted.

Cave: `CAVE_ATKTGT_LIST` `0x0239CA50` (0x10), `CAVE_ATKTGT_GATE` `0x0239CA60`
(0x40); `CAVE_FREE` → `0x0239CAA0`, 5728 B free. `verify()` now also asserts the
hook, the `cmp r6,#0` guard, the `movs r2,#0x13`, and the post's call to
`0x021D3230` — so if any of them drifts the build fails instead of shipping dead.

## Next Experiment

**E0b — IN-GAME TEST 2.** Same setup as before: normal duel, Maiden face-up, a
Blue-Eyes reachable in hand/Deck/GY, opponent attacks her. This test now
discriminates cleanly:
- **A prompt appears** ⇒ the gate fix works and the whole chain is live; then check
  negate → position flip (test Defense too) → Blue-Eyes summon → and that a second
  attack the same turn offers nothing (clause 3).
- **Still nothing** ⇒ the gate was necessary but not sufficient; the next
  measurement is diagnostic counters in the two cave stubs (entered? event code
  seen? condition return? resolver phase?), read back out of a savestate — no GDB
  needed. Do NOT patch further before that.

### Why hooking exactly ONE call site is load-bearing

`0x021A37D8(side, zone) -> cid` is a shared helper. The fix retargets **only** the
call at `0x021C6624` (the one feeding the gate switch). The poster
`0x021D3230` **re-derives the cid through its own call** at `0x021D3250` —
`r0` = side is untouched from its entry, `r1` = zone — and that site is NOT hooked.

So the gate sees the remapped `0x1CB1` while **the descriptor carries the real
`0x1ED7`**, which is exactly what `find_event_handler` needs to reach our cls1
record. Hooking the helper globally, or at the wrong site, would have opened the
gate and then made the record unfindable — a fix that defeats itself.

---

# IN-GAME TEST 2 — FAILED. STOPPING TO INSTRUMENT (2026-08-20)

The gate fix did not make the effect activate. Per `otn-escalate-to-measurement`
("2 failed in-game tests on one subsystem ⇒ stop patching, instrument"), **no
further patching until the chain is measured.**

⚠️ There are NO savestates for test 2 — `rom_maiden.ml1..ml5` are all 11:22–11:24,
before the ROM was rebuilt at 11:45. So test 2 produced no evidence at all, and
the gate hook has never actually been observed running. It is UNVERIFIED whether
it fired, whether it matched, or whether the ROM under test even contained it.

## Ruled Out for test 2
Nothing. The static chain is unchanged and still self-consistent; what is missing
is any measurement of it on the live path.

## The instrument

`patch_maiden_eyes_of_blue --diag` → **`rom_maiden_diag.nds`**. It installs an
instrumented copy of all three stubs in their OWN cave slots (`CAVE_MD_COND`,
`CAVE_MD_RES`, `CAVE_MD_GATE`), so the shipped stubs stay byte-identical and the
diagnostic cannot perturb what it measures. Behaviour is unchanged; only counters
are added. Counter block `CAVE_MD_DIAG` = `0x0239CAA0`, verified all-zero at boot:

| off | meaning |
|---|---|
| +00 | gate hook entered (**any** cid attacked) |
| +04 | gate hook matched our donor and remapped |
| +08 | the last cid the gate actually saw |
| +0C | condition entered |
| +10 | condition accepted (returned 2) |
| +14 | `(desc[+5] << 8) \| desc[+4]` — selector and event code |
| +18 | turn-log query result **+ 1** (so 0 = never queried) |
| +1C | resolver entered |
| +20 | last resolution phase word seen |
| +24 | negate return **+ 1** (2 = negated, 1 = refused, 0 = never called) |

Every "+1" offset exists so that *never ran* and *ran and returned 0* are
different values — the trap that makes counter blocks lie.

Read with `.venv-1/Scripts/python.exe -m scratch.read_maiden_diag <state.mlN>`,
which first checks the DIAG stub is byte-resident (so a stale state from another
ROM is refused rather than misread — smoke-tested against `rom_maiden.ml4`, which
it correctly rejects) and then prints the counters **and the reading**.

All three instrumented stubs were disassembled out of the built ROM before use.

## What each outcome will mean (decided BEFORE the test, so the result cannot be rationalised)

- **+00 == 0** → `0x021C6620` is never reached on this attack path. The whole
  code-0x13 route is wrong for this card and the gate work was beside the point.
- **+00 > 0, +04 == 0** → the gate runs but the cid at `0x021C6624` is not
  `0x1ED7` (read +08). My reading of *whose* cid feeds the switch is wrong.
- **+04 > 0, +0C == 0** → event posted, record NOT dispatched ⇒ suspect
  `find_event_handler` (selector, or the `leftmost + 1` second-record rule).
- **+0C > 0, +10 == 0** → the condition rejected; +14 and +18 say which gate.
- **+10 > 0, +1C == 0** → the activation procedure (slot4 `0x021E51E5`) aborted.
- **+1C > 0, +24 == 0** → the resolver ran but not at phase 0x80 (read +20).
- **+24 == 1** → the negate was called and refused: a battle-state problem.

---

# ⭐ IN-GAME CONFIRMED (2026-08-20) — CLAUSE 2 WORKS

Test 3, on `rom_maiden_diag.nds`: **the effect negates the attack, changes battle
position, and Special Summons Blue-Eyes White Dragon — confirmed working from all
three zones (hand, Deck and Graveyard).**

Test 2's failure was a **ROM mix-up**: it was run on the pre-fix build. It produced
no savestate, which is exactly why the next move was an instrument whose reader
*refuses a state from the wrong ROM* rather than another blind patch. Had test 2
been read as real evidence, the correct fix would have been thrown away.

So the chain is now measured end to end:

| stage | status |
|---|---|
| the 26-cid gate on the code-0x13 post (`0x021C6620`) | **real** — without the remap nothing happens at all |
| `CAVE_ATKTGT_GATE` cid remap | **works** — the donor now receives the event |
| cls1 record dispatch → condition → slot4 "you can" | **works** — the effect is offered |
| negate `0x0221F944` | **works** |
| position change `0x021C5324` (toggle) | **works** |
| SS 1 Blue-Eyes via the one criteria row | **works from hand, Deck AND GY** |

The single criteria row `{aux 0x0FA7, handler 0x0223E2C9, flags 0x0802}` really is
the entire payload — all three zone builders fire, as
`dispatch.named_ss_multizone_handler` predicted.

Both `rom_maiden.nds` and the **combined 35-patch `rom_all_patches.nds`** carry the
identical hook (`BL 0x021C6624 -> 0x0239CA60`, gate stub byte-correct, admit list
`{0x1ED7}`); `verify()` passes for all 26 chained patches.

## Still unconfirmed (worth one more duel, no rebuild needed)
- **Clause 3 (HOPT)** — attacking Maiden a *second* time in the same turn should
  offer nothing.
- **The Defense→Attack half of the toggle** — the deliberate deviation from the 16
  native cards. Attack→Defense is confirmed; being attacked while in Defense
  should flip her to Attack.

## Next Experiment
**E1 — clause 1** (the Quick-Effect "targeted by a card or effect"), unchanged:
close the cls3 invoker (which of the 39 callers of `0x0224AD94` passes a non-zero
`r1`; prime suspect the queue walker `0x021D3322..0x021D33A4`). Note clause 1 will
need its own trigger route — the `0x021C6620` gate is battle-only.

## Ninishi admitted (2026-08-20)

`CAVE_ATKTGT_LIST` now reads `{0x245B, 0x1ED7}`. Dverg `0x245B` is the
patch_ninishi donor, whose grafted "when this face-up card is selected as an attack
target, change its battle position" record (`cls1[1293]` in the combined ROM,
`{0x245B, 0x0220C6B1, 0, 0x021F4D4D, 0, 0}` — confirmed present and correct) had
**never fired**, for exactly the reason Maiden's did not: rejected by the
`0x021C6620` gate.

- The record needed no change at all; only admission.
- `patch_maiden_eyes_of_blue.verify()` now asserts the admit list contents
  explicitly, so dropping `0x245B` fails the build rather than silently re-killing
  another card's clause.
- The dependency is documented at `patch_ninishi.py` PART A2: that clause is inert
  in any build that omits patch_maiden_eyes_of_blue.
- ⚠️ The *mechanism* is in-game confirmed (on Maiden). **Ninishi itself has not been
  re-tested** — worth one duel.

---
---

# CLAUSE 1 SESSION — 2026-08-20 (RE first, no ROM code touched yet)

Baseline re-verified at session start: `verify_knowledge` = **275 facts, 244 PASS,
0 FAIL, 31 UNVERIFIED** — matches the handoff exactly, KB has not rotted.

Card text re-read from `scratch/ygoprodeck_cache.json` id 88241506 (not recall);
byte-identical to the text quoted at the top of this file. Clause 1 is in scope;
clause 2 (cls1 + CAVE_MAIDEN_*) and clause 3 (turn log) must not regress.

## ⭐ Confirmed this session — THE CLAUSE-1 INVOKER IS CLOSED (static)

The handoff's open question was "which of the 39 callers of `0x0224AD94` passes a
non-zero `r1`". Answer: **three of them, all inside `0x021EDA14`**, and the
descriptor they pass comes from the **chain array**, not from any per-cid table.

Full chain, every link disassembled this session against `nds_overlay_3.bin`:

```
act_desc = &chain[depth-1]          chain 0x0229A7FC (stride 0x24)
                                    depth [0x0229A9FC + 0x44]
  0x0224B8B0(side, container, zone)     container 0..0xA => the FIELD arm @0x0224B92C
    -> 0x021EC654(viewpoint, side, zone, act_desc)          viewpoint = [0x0229DD94+0x74]
         builds MY desc: +0 = cid (0x021A36EC(side,zone)), +2 = side, +3 = zone,
                         +6 = (viewpoint != side)
      -> 0x021EC740(my_desc, act_desc)
           zone <= 0xA  =>  my_desc[+5] = 3   (SELECTOR 3 = cls3)   @0x021EC776
           zone >  0xA  =>  my_desc[+5] = 2   (cls2)                @0x021EC892
         -> per timing-table entry: 0x021EDA14(my_desc, act_desc, 0)
              (0x021EDA08 is only a `movs r2,#0 ; bx 0x021EDA15` THUNK — which is
               why "both callers of COMMIT pass r1 = 0" was true and yet misleading)
              `str r1,[sp]` @0x021EDA1A  => [sp] IS the activating descriptor
              selector != 0  =>  jumps straight to 0x021EDC70 @0x021EDB68
            -> 0x0224AD94(my_desc, act_desc)      @0x021EDC8C
                 -> find_event_handler -> the cls3 record for my cid
                 -> slot3(my_desc, act_desc)      @0x0224AE06
```

`0x0224AD94` puts its 2nd argument at `[sp]` (`push {r3,…}` + `str r1,[sp]`
@0x0224AD98) and hands it to slot3 as `r1` — so **`r1` = the activating
descriptor**, exactly what `0x021F8134` (Blue-Eyes Shining Dragon) requires.

### The selector -> table map, decoded from find_event_handler's jump table
`0x0224A122`: `ldrb r0,[r4,#5] ; cmp r0,#3 ; bhi <reject>`; table at `0x0224A134`
holds `[0x12, 0x30, 0x06, 0x36]`, targets = `0x0224A136 + off`:

| desc[+5] | arm | table |
|---|---|---|
| 0 | 0x0224A148 | cls0 `0x0227E64C` (0x51A) |
| 1 | 0x0224A166 | cls1 `0x022860D4` (0x535) |
| 2 | 0x0224A13C | cls2 `0x02275C04` (0x2B9) — **or cls0 when desc[+4] == 0x25** |
| 3 | 0x0224A16C | cls3 `0x02279D74` (0x308) |

### Second, independent producer of the same call
`0x02239A30(act_desc, viewpoint, out)` sweeps side 0..1 x zone 0..0xA with
`0x021EC654(viewpoint, side, zone, act_desc)` @0x02239B6A, taking `act_desc` from
its own `[sp]` (= arg0). Same terminal call. Its `0x1AF9`-family compares
(`0x02239AA6..0x02239AE6`) only set a permissive flag `[sp+0x24]`; they are not a
gate on reaching slot3.

## Ruled Out this session

- **The queue walker `0x021D3322..0x021D33A4` is NOT the clause-1 invoker.** It was
  the handoff's prime suspect. It does pass a non-zero `r1` (`r6` = the 3rd argument
  of `0x021D32A0`, which `0x0224C6EE` sets to `&chain[depth-1]`), but the descriptor
  it builds takes its selector from the packed word's bits 21..23, and **all four
  callers produce selector 0 or 2** (`0x0224B120`, `0x0224B1BE` and `0x0224C6EE` →
  `(0x4B or 0x4E) << 16` → selector 2; `0x0224B31C` → selector 0). It feeds
  cls0/cls2, never cls3.
- **`0x0224AF7C` (the timing classifier) cannot short-circuit us.** At `0x021EDC76`
  a class of 2 returns 1 *without* consulting slot3 — but `timing.class_is_the_slot4_literal`
  (VERIFIED) records that the classifier **returns 0 immediately for selectors 0 and 3**,
  so a cls3 descriptor always falls through to `0x0224AD94`.
- **The `0x02023584` 7-cid list is not on our path.** `0x021EC740` @0x021EC7A0 only
  applies it when `my_desc[+6] != 0`, and `0x021EC654` sets `+6 = (viewpoint != side)`.
  The list is `{0x0E47, 0x0E88, 0x1232, 0x149C, 0x1517, 0x1A67, 0x209B}` (7 entries at
  `0x0209BA5C`, binary-searched by `0x02022E14`) — it gates *the opponent's* cards
  being enumerated from your viewpoint, not your own.
  ⚠️ This corrects the reading in `dispatch.onfield_ignition_is_a_cls3_record_only`,
  which lists `0x02023584` as a gate "on the path": it is a gate on the
  `desc[+6] = 1` arm (`0x0224BD44`) only, and `0x0224BD32` (`viewpoint == side`)
  branches away before it.
- **`0x02029E60` is generic**: `0x02029E1C(cid)` bounds-checks `0x0D48 <= cid < 0x24E9`
  and indexes a u16 genre table; `0x02029E60` tests bit `0x8000`. No per-card arm.
- **`0x0224A874(cid)` is self-satisfying**: it builds a throwaway descriptor with
  `+5 = 3` and calls find_event_handler — i.e. "does this cid own a cls3 record".
  Inserting our record satisfies it.

## Open Questions

1. **`0x021D3788(desc)`** (`0x021EDC7C`) is a per-cid compare tree (base ± imm,
   ungreppable) whose non-zero result makes `0x021EDA14` return 1 **without**
   consulting slot3. A donor is almost certainly absent from it (absence = the
   normal path), but it has not been simulated. Cheap to close with the concrete
   Thumb interpreter already written for the `0x021C6620` gate.
2. **Is there an upstream gate that stops `0x0224B8B0` / `0x02239A30` being called
   at all for a records-free donor?** `patch_mystic_piper`'s v2 log says exactly
   this happened for an *ignition* effect. The static evidence says the field arm
   (`0x0224B92C`) has no cid table, but this is the failure mode clause 2 paid for
   and it is the one thing static analysis cannot fully close.
3. `0x021ECDA4(desc, 0, r2)` — the "is this effect currently negated / prohibited"
   pre-gate at `0x021EDA2E`. Reads zone-record bits; looks generic, not audited leaf
   by leaf.

## Next Experiment

**E1a (static, cheap): simulate `0x021D3788` over the whole cid space** and confirm
`0x1ED7` returns 0. Reuse the concrete interpreter from the `0x021C6620` work.

**E1b (the arbiter): build clause 1 AND clause-1 counters into `rom_maiden_diag.nds`**
in the same pass, so the first in-game test is self-diagnosing rather than a blind
build-test cycle. Counters to add to `CAVE_MD_DIAG`:

| off | meaning | reading if 0 |
|---|---|---|
| +28 | clause-1 condition entered | the cls3 record is never dispatched — open question 2 is real, stop and instrument upstream |
| +2C | `r1` (the activating descriptor) as seen | 0 => the invoker is a different one; the whole chain above is wrong |
| +30 | pick-array walk hit (target matched) | the condition runs but never matches — `0x02234904` / `desc[+2]/[+3]` reading is wrong |
| +34 | turn-log query result + 1 | 0 => never queried; 2 => clause 3 blocked it |
| +38 | clause-1 condition accepted (returned 2) | — |
| +3C | clause-1 resolver entered | — |

Decide the meanings **before** the test (done, above) so the result cannot be
rationalised afterwards.

---

# CLAUSE 1 BUILT — IN-GAME TEST 4 (2026-08-20): INCONCLUSIVE, BUT THE BIG RISK IS DEAD

Built and shipped in `patch_maiden_eyes_of_blue.py`:

| part | what | where |
|---|---|---|
| E | cls3 record `{0x1ED7, CAVE_MAIDEN_C1_RES\|1, 0, CAVE_MAIDEN_C1_COND\|1, 0x021E51E5, 0}` | ov3, count-neutral over phantom `0x1C80` (cls3[334] -> insert at 451) |
| E | `CAVE_MAIDEN_C1_COND` 96 B / 0x60 | ov5 `0x0239CCC0` |
| E | `CAVE_MAIDEN_C1_RES` 48 B / 0x40 | ov5 `0x0239CD20` |

No new criteria row (clause 1 reuses clause 2's), no ov3 **code** edit at all.

**E1a closed first (static, no emulator).** `0x021D3788` — the per-cid tree at
`0x021EDC7C` whose non-zero result returns 1 *without* consulting slot3 — was executed
over the whole cid space `0x0D48..0x24E8`. Only **10** cids leave its reject leaf
(`0x0E10 0x18D1 0x1ECE 0x20AB 0x20FD 0x2201 0x22C5 0x23B9 0x24DB 0x24E6`), and each of
its three accept leaves additionally requires `desc[+5]` to be **1 or 2** (or
`desc[+4] == 9` for `0x20FD`). On a **cls3** descriptor (`desc[+5] == 3`) *no cid at
all* can take that shortcut. Stronger than "the donor is absent": the gate is
structurally unreachable on this path.

## ⭐ Confirmed in-game: the cls3 record IS DISPATCHED for a records-free donor

`rom_maiden_diag.ml3`, read with `scratch.read_maiden_diag`:

```
+0x28  cl.1 condition entered              = 2
+0x2C  cl.1 the r1 it was handed           = 0
+0x30  cl.1 pick-array walk MATCHED        = 0
+0x34  cl.1 turn-log query + 1             = 0
+0x38  cl.1 condition ACCEPTED             = 0
+0x3C  cl.1 resolver entered               = 0
```

This kills the session's largest risk. `patch_mystic_piper`'s v2 log ("adding a cls3
entry to a card with no NATIVE ignition is not enough; an upstream gate decides whether
a monster's ignition is offered at all") and clause 2's own 26-cid gate both predicted
`+0x28 == 0`. It is **2**. A records-free donor's cls3 record is reached.

## What test 4 did NOT establish

Both invocations were handed `r1 = 0`, i.e. no activating descriptor, so the condition
correctly bailed at its first instruction.

`+0x2C` and `+0x34` are LAST-VALUE, not counters — but `+0x34` is written only *after*
the `r5 == 0` bail, so `+0x34 == 0` proves **no call ever arrived with a non-zero r1**.
The "last value" reading is safe here; that is why the counter was placed there.

The test was **the user destroying their own Maiden with their own Spell**, which is
the wrong experiment on two independent counts, and neither is a defect in the patch:

1. **Most OTN monster-destruction Spells do not TARGET** (Fissure, Smashing Ground,
   Hammer Shot, Dark Hole, Lightning Vortex). Clause 1 triggers on *targeting*, so a
   non-targeting destruction correctly does nothing.
2. **The response window is offered to the player who did not activate.** The only
   caller that reads the chain top is `0x0224B8B0`, whose viewpoint is
   `[0x0229DD94 + 0x74]` — the player being prompted. Activating your own Spell does
   not prompt you.

The two hits at `r1 = 0` are consistent with the *ignition-capability* sweeps, which
all pass `r1 = 0` by construction (`0x022398FC`, `0x0226A7D8`, `0x0224BEA4`,
`0x0224C76A`).

## The instrument was sharpened rather than the patch re-guessed

Per `otn-escalate-to-measurement`, no further patching. A second counter block
`CAVE_MD_DIAG2` (`0x0239CE80`, 0x20 B) now samples the CHAIN at clause-1 condition
entry, which separates the two things that both look like `+0x2C == 0`:

| off | meaning |
|---|---|
| +00 | chain depth `[0x0229A9FC + 0x44]` at entry (LAST) |
| +04 | entries seen with chain depth **> 0** (a RESPONSE window) |
| +08 | `&chain[depth-1]` when depth > 0 (LAST) |
| +0C | the cid on top of the chain then (LAST) |
| +10 | entries seen with chain depth **== 0** (an IGNITION sweep) |

Decided **before** the next test:

- **+04 == 0, +10 > 0** → we are only ever swept at chain depth 0. The response sweep
  never ran for this card's controller; the record and condition are not implicated.
  The experiment was wrong, not the patch.
- **+04 > 0 but +2C still 0** → the response sweep DOES reach us and withholds the
  chain top. The mapped invoker is wrong — and +08 shows the chain top is readable
  from `0x0229A7FC` directly, so the stub could fetch it itself.
- **+2C != 0, +30 == 0** → we get the descriptor but the pick-array walk never matches;
  `0x021F8134`'s reading of `0x02234904` / `desc[+2]/[+3]` needs re-deriving.

The reader's stale-state guard now checks the **clause-1** DIAG stub as well as the
clause-2 one: a state from an older diag build has byte-identical clause-2 stubs and
would otherwise have read as "clause 1 never ran" — inventing the exact false negative
the guard exists to prevent.

## Next Experiment

**E2 — the right test.** Normal duel, `rom_maiden_diag.nds`. Maiden face-up on your
field, a Blue-Eyes reachable in hand/Deck/GY, and have the **OPPONENT** activate a card
that genuinely **targets** her (an equip, a possession/control effect, or a targeting
removal — not Fissure/Dark Hole/Smashing Ground, which target nothing). Save a state and
read it. Expected on success: a Yes/No prompt, then Blue-Eyes is Special Summoned.

## CORRECTION to the test-4 reading (user supplied the card, 2026-08-20)

The Spell was **Offerings to the Doomed `0x145E`** — verified against
`scratch/ygoprodeck_cache.json` and present in the ROM: a Quick-Play Spell reading
"**Target 1 face-up monster on the field**; destroy that target, also skip your next
Draw Phase."

**So it DID target, and it could legally name the user's own Maiden.** Explanation 1
above ("most OTN destruction Spells do not target") is RULED OUT for this test — it was
a genuine targeting activation on a face-up Maiden, and the clause-1 condition still
never received an activating descriptor.

That leaves explanation 2 as the live one: the engine offers the response window to the
player who did **not** activate, so activating your own Quick-Play never prompts you and
the responder sweep `0x0224B8B0` (the only caller that reads the chain top) never ran.
The `CAVE_MD_DIAG2` chain probe decides this without another guess, and the test that
settles it is the **same setup repeated on the rebuilt diag ROM** — no new cards needed:

- `+04 == 0, +10 > 0` (only ever swept at chain depth 0) ⇒ confirmed; the activating
  player gets no response window. Clause 1 would then fire only when the OPPONENT
  targets her, which is the case that matters in play, and the self-target case is a
  stated deviation rather than a defect.
- `+04 > 0` with `+2C == 0` ⇒ the sweep DOES run during the activation and withholds the
  chain top; the invoker mapping is wrong, and `+08` proves the top is readable directly
  from `0x0229A7FC` so the stub can fetch it itself.

### Static support for explanation 2, found while the combined build ran

Twelve sites write `[0x0229DD94 + 0x74]` (the player whose prompt is open). **Two of
them compute the NON-TURN PLAYER and immediately open the capability enumerator**:

```
0219ECDE  ldr r0,=0x02299114 ; ldr r0,[r0,#4]   ; the turn-player word
0219ECE0  movs r5,#1 ; ands r0,r5                ; turn player side
0219ECEA  ldr r0,=0x0229DD94
0219ECEC  eors r1,r5                             ; r1 = turn_player ^ 1
0219ECEE  str r1,[r0,#0x74]                      ; <-- prompt the NON-TURN player
0219ECFC  bl 0x0224C28C                          ; <-- open the capability enumerator
```
(identically at `0x0219ED70` / `0x0219ED7E`). `0x0224C28C` is the enumerator whose
container-0..0xA arm is `0x0224B8B0` — the ONLY caller that reads the chain top.

So the response window that can reach a cls3 record is opened for the **non-turn
player**. That predicts test 4 exactly: the user activated on their OWN turn, so the
window went to the opponent and their Maiden was never swept with a live chain.

⚠️ Not all twelve sites are turn-keyed — `0x0224B99C` stores an arbitrary `r0`, so the
prompted player is caller-chosen in general. This is support, not proof; the chain
probe is still the arbiter.

**This yields a CONTROLLABLE test.** Offerings to the Doomed is a **Quick-Play** Spell:
SET it, pass, and activate it during the **OPPONENT's** turn targeting your own Maiden.
Then the non-turn player is you, your field is swept while the chain link is live, and
clause 1 should fire. Same card, same board — only the timing changes.

---

# IN-GAME TEST 5 (2026-08-20) + ⭐ THE SAVESTATE THAT CORRECTED THE MODEL

User targeted their own Maiden with **Offerings to the Doomed 0x145E**, AND the
opponent targeted with **Book of Moon 0x1538**. Still no activation. Counters:

```
+0x28 cl.1 condition entered = 2      +0x2C the r1 it was handed = 0
+0x04 entries with [+0x44] > 0 = 0    +0x10 entries with [+0x44] == 0 = 2
```

## ⭐ CORRECTION: `[0x0229A9FC+0x44]` IS NOT THE CHAIN DEPTH — it is COUNT MINUS ONE

Read straight out of `rom_maiden_diag.ml3` (live RAM, duel loaded):

| address | value | meaning |
|---|---|---|
| `[0x0229A9FC + 0x40]` | **2** | THE CHAIN-LINK COUNT |
| `[0x0229A9FC + 0x44]` | **1** | count − 1 |
| `[0x0229A9FC + 0x50]` | `0x0229A820` | `= 0x0229A7FC + 0x24` = &array[1] |
| `0x0229A7FC[0]` | cid **0x145E** side 0 zone 0x07 | Offerings to the Doomed |
| `0x0229A7FC[1]` | cid **0x1538** side 1 zone 0x06 | Book of Moon |
| Maiden `0x1ED7` | side 0, zone 2 | on the field, as expected |

`+0x44` has exactly ONE writer in overlay 3 — `ldr r0,[r7,#0x40] ; subs r0,#1 ;
str r0,[r7,#0x44]` at `0x021D4BF8` — confirming `+0x44 = +0x40 − 1`.

**So the previous session-note reading "entered only at chain depth 0" was WRONG.**
`+0x44 == 0` means **one** chain link, not none. The reader has been corrected; the
probe now records `[+0x40]` (the real count) as well.

## The likely bug, now evidence-backed rather than guessed

`0x0224B8B0` — the only caller that supplies the activating descriptor — does:

```
0224B8B8  ldr  r0,[r0,#0x44]     ; = chain count - 1
0224B8BE  cmp  r0,#0
0224B8C0  ble  0x0224B8CC        ; <-- with ONE chain link this is TAKEN, r7 stays 0
0224B8C2  subs r1,r0,#1
0224B8CA  adds r7,r3,r0          ; r7 = &array[[+0x44] - 1]
```

With exactly one activation on the chain, `[+0x44] == 0`, the `ble` fires and the
engine hands slot3 **r1 = 0**. That is precisely what both duels measured.

⚠️ If that is the whole story it also means **Blue-Eyes Shining Dragon's own clause
cannot fire in OTN** for a single-link chain — the native card is not evidence that
this path works. Do not lean on it.

## The fix that follows (NOT yet applied — one datum still missing)

The activating descriptor **is in RAM** when it is needed: `ml3` proves the array
holds the real card. So when `r1 == 0` the condition can read the chain top itself at
`0x0229A7FC + ([0x0229A9FC + 0x40] − 1) * 0x24`.

The one thing not yet measured is whether `[+0x40] > 0` **at the moment the condition
runs** (the earlier probe only recorded `+0x44`). The current `rom_maiden_diag.nds`
records it, along with the **invoker's return address read off the stack** — from the
stub's own 5-word frame, `[sp+0x28]` is `0x0224AD94`'s saved LR and `[sp+0x14]` is its
spilled r1, because `0x0224AD94` pushes `{r3..r7,lr}` and never moves sp. The reader
maps that address to the exact call site among the 39, so the caller is *named*, not
guessed — guessing it has now cost two duels.

## Next Experiment

**E3 — one duel, current `rom_maiden_diag.nds`.** Any targeting card on Maiden, either
side (Book of Moon / Offerings / Shrink all qualify). Save a state. The read then gives:

- **`[+0x40] > 0` at entry, r1 = 0** → the fix above is proven; implement the chain-top
  fallback in `CAVE_MAIDEN_C1_COND`.
- **`[+0x40] == 0` at entry** → the responder path genuinely never runs for us; the
  named invoker says which sweep did, and the next instrument goes inside `0x021EC740`.

---

# ⭐ ROOT CAUSE FOUND (2026-08-20): CLAUSE 1 IS A QUICK EFFECT AND THE ENGINE ENFORCES SPELL SPEED

Test 6 (`rom_maiden_diag.ml2/.ml4/.ml5`) is the one that closed it, because the probe
read the **invoker's return address off the stack** instead of guessing it:

```
+0x28 cl.1 condition entered              = 2
+0x14 INVOKER RETURN ADDRESS, first call  = 0x021EDC91  -> 0x021EDC8C, RESPONDER 0x021EDA14 arm C
+0x24 [0x0229A9FC+0x40] THE CHAIN COUNT   = 0
+0x28 desc word                            = zone 0x02, selector 3, +6 = 0
```

So **the mapped chain was right all along** — `0x0224B8B0 -> 0x021EC654 -> 0x021EC740
-> 0x021EDA14 -> 0x0224AD94 -> slot3` really is the path, and the cls3 record really is
dispatched. The two entries were the **chain-empty** ignition sweeps. Every *real*
response window died earlier, inside `0x021EDA14`:

```
021EDA38  ldr r0,[sp] ; cmp r0,#0 ; beq 0x021EDA76   <- chain EMPTY: skip the test
021EDA3E  bl 0x021A87BC(my desc)   -> r4 = MY spell speed
021EDA46  bl 0x021A87BC(the act)   -> r0 = the ACTIVATION's spell speed
021EDA4C  cmp r4,r0 ; bge 0x021EDA52 ; b 0x021EDC9E  <- my speed < theirs: RETURN
```

That is why the condition was only ever entered with `r1 == 0`: the only calls that got
past `0x021EDA14` were the ones where `[sp] == 0` skipped the comparison entirely.

## The spell-speed mechanism, fully decoded

`0x021A87BC(desc)` is a per-cid switch on `desc[+0]` (base ± imm, ungreppable) whose
leaves also test `desc[+5]` (the table selector) and `desc[+4]`. Its **DEFAULT leaf
`0x021A894C`** is `adds r0,r2,#0 ; bl 0x0202345C` — so a records-free donor's speed is
whatever `0x0202345C(cid)` says.

`0x0202345C(cid)` (ARM9):
- kind `0x17` (Spell): sub-type 5 (**Quick-Play**) -> **2**, else -> 1
- kind `0x18` (Trap): sub-type 1 (Counter) -> 3, else -> **2**
- otherwise (a MONSTER): membership in a **sorted 118-entry u16 cid list at
  `0x0209C118`**, binary-searched by `0x02022E14` with the hard-coded count
  `movs r2,#0x76` @`0x02023490` -> **2**; not a member -> **1**.

**The list self-identifies as "monsters with a Quick Effect"**: Kuriboh `0x0FE0`,
Injection Fairy Lily `0x13A7`, Gravekeeper's Watcher `0x158A`, Doomcaliber Knight
`0x1771`, Winged Kuriboh LV10 `0x1906`, Herald of Purple/Green Light `0x1A24`/`0x1A25`,
D.D. Crow `0x1B44` — and **Blue-Eyes Shining Dragon `0x17C2`**, the exact card whose
cls3 condition this patch transcribes.

⇒ **BESD's clause works because it is a member. Ours got speed 1 and every response to
a Quick-Play (speed 2) was refused.** Book of Moon `0x1538` and Offerings to the Doomed
`0x145E` are both Quick-Play Spells, so both test cards were speed 2.

This also retires the earlier worry that "BESD's own clause probably cannot fire in
OTN" — it can; it was our donor that was mis-classified.

## PART F — the fix, and it is DATA

Count-neutral insert of `0x1ED7` into `0x0209C118` over phantom `0x1A86` (no
`card_prop`, unclaimed, and the highest phantom below the donor so the fewest entries
move). Inserted at index 60; count 118 and sortedness preserved, both asserted.

It is an **ARM9** table, so unlike the ov5 stubs it is resident in **every duel mode,
puzzles included**.

`verify()` now asserts: count unchanged, still sorted, donor present, phantom gone, and
**Blue-Eyes Shining Dragon still in the list** (so a future edit cannot quietly evict
the card this design is modelled on). The list base literal `0x0202348C` and the count
immediate `0x02023490` are anchored too.

Claimed as `("quickeffect_list", 0x1A86, "maiden_eyes_of_blue")`.

## Next Experiment

**E4 — the arbiter.** Normal duel, rebuilt `rom_maiden_diag.nds`. Maiden face-up, a
Blue-Eyes in hand/Deck/GY, activate any targeting card on her (Book of Moon and
Offerings to the Doomed both proven to reach the responder). Expected: a Yes/No prompt,
then Blue-Eyes Special Summoned. If it still fails, `+0x28` vs `+0x2C` now discriminate
sharply — a non-zero `+0x2C` means the speed gate is passed and the walk is the suspect.

---

# ⭐ IN-GAME CONFIRMED (2026-08-20) — CLAUSE 1 FIRES

User report after PART F: **"It works during my opponent's turn, not during my turn."**

So the whole clause-1 chain is now measured end to end:

| stage | status |
|---|---|
| cls3 record dispatched for a records-free donor | **works** (counters, test 4) |
| invoker = responder `0x021EDA14` arm C | **measured** off the stack (test 6) |
| spell-speed gate `0x021EDA4C` | **was the blocker**; PART F fixes it |
| ARM9 Spell-Speed-2 list insert (PART F) | **works** — the effect now activates |
| condition -> slot4 "you can" -> resolver -> shared criteria row | **works** |

`dispatch.targeted_by_effect_condition`'s STILL-OPEN note ("which of the 39 callers
passes a non-zero r1") is now closed: **`0x021EDC8C`, inside `0x021EDA14`**, whose
`[sp]` is its own second argument. The mapping's prime suspect (the queue walker
`0x021D3322`) was wrong — it feeds cls0/cls2 only.

## Open: the OWN-TURN gap

Clause 1 does not offer on the controller's own turn. Real Maiden responds on either
turn, so this is a fidelity gap, not a design choice — but it may be an engine-level
property rather than anything about this record.

**Not yet measured, and not to be guessed at** (guessing the invoker already cost two
duels). What is known:

- `0x021ECC6C` — the chain-legality check between `0x021EC740` and `0x021EDA14` — has
  **no turn-player gate**. Its only turn-keyed arm (`0x021ECD3A`, message `0x15`) is
  behind `[0x0229C294 + 0x78] & 1`, i.e. the **Damage Step**, and it also requires
  `0x021A897C` (damage-step legality: sub-type 1, or membership in the 0x30-entry list
  at `0x0226D8B0`, or an event-code jump table) to refuse first.
- Two of the twelve writers of `[0x0229DD94 + 0x74]` compute `turn_player ^ 1` and
  immediately open the capability enumerator (`0x0219ECEE`/`0x0219ECFC` and
  `0x0219ED70`/`0x0219ED7E`) — the **non-turn player** gets that window. The other ten
  are caller-chosen, so this is suggestive, not conclusive.
- `0x0224B8B0` computes `r7 = &array[[+0x44] - 1]` and `[+0x44] = chain count - 1`, so
  a **single**-link chain yields `r7 = 0`. That the opponent's turn works implies the
  engine pre-pushes a link for the prospective response there (count 2 -> `[+0x44]` 1
  -> `&array[0]`). Whether it does the same on the turn player's side is exactly the
  unmeasured question.

**E5 — reproduce the own-turn failure on the diag ROM and save a state.** Then:

- `+0x28` rises but `+0x2C == 0` with `[+0x40] > 0` -> the sweep runs and withholds the
  chain top. Fix: fall back to reading it at
  `0x0229A7FC + ([0x0229A9FC + 0x40] - 1) * 0x24`, which `ml3` already proved holds the
  real activating card.
- `+0x28` does not rise -> the responder sweep is not run for the turn player at all.
  That is an engine-level window difference; record it as a stated deviation rather
  than forcing it.

## Also outstanding: CLAUSE 2 REGRESSION CHECK

PART F changes what `0x0202345C` returns for `0x1ED7` (1 -> 2), and that is the SAME
cid clause 2 uses. Clause 2's path reaches `0x021EDA14` with `act == 0` (via COMMIT
`0x021EDA08`), where the speed comparison is skipped and `0x0224AF7C` short-circuits on
its class-2 slot4 tag — so no regression is *expected*. But "not expected" is not
"measured", and this is the file that records what happens when that distinction is
skipped. **Re-test: have Maiden attacked, and confirm negate -> position change ->
Blue-Eyes still works.**

---

# CLAUSE 1 STATUS (2026-08-20) — ⚠️ CORRECTION OF AN EARLIER OVERCLAIM

**An earlier version of this section said "CLAUSE 1 — IN-GAME CONFIRMED". That was
written on the strength of one short user message and was NOT justified. It has been
deleted, and the same overclaim has been removed from
`dispatch.responder_spell_speed_gate` in the KB.** Recording the mistake here because
CLAUDE.md's rule — never write a fact you have not verified this session — is exactly
what was broken, and the correction is what has to survive.

## What is actually established

| claim | grade |
|---|---|
| the patch is live and correct in RAM | **MEASURED** — `rom_maiden.ml3`: cls3 row 451 = `{0x1ED7, 0x0239CD21, 0, 0x0239CCC1, 0x021E51E5}`, the shipped cond stub byte-correct in ov5, `0x1ED7` in the live Spell-Speed-2 list, Maiden at side 0 zone 2 |
| the condition receives a live activating descriptor, MATCHES, and RETURNS 2 | **MEASURED** (`rom_maiden_diag.ml3`: `+0x04 = 1`, `+0x30 = 1`, `+0x38 = 1`, chain top cid `0x1329` Rush Recklessly) |
| the activation procedure then begins | **NO** — `+0x3C = 0`, and slot4's phase-0 re-entry through `0x0224AD94` is never counted |
| clause 1 fires when the OPPONENT activates a targeting card | **USER-REPORTED, not reproduced on demand.** Do not upgrade this without a savestate showing `+0x3C > 0`. |
| clause 2 (attack trigger) | user-reported working, and user-reported no regression after PART F |

## The discriminator is WHO ACTIVATED, not whose turn it is

Corrected from the earlier "own turn" framing, which was wrong. Rush Recklessly `0x1329`
is a Quick-Play, so the user activated it on **both** turns and it failed both times;
Book of Moon `0x1538` and Offerings to the Doomed `0x145E` are Quick-Play too. All three
are the same card type, so type is not the variable. The only thing that separates the
working report from the failing ones is **who activated the card**.

⇒ Working hypothesis: **OTN never offers you a response to your own activation.** It
fits every data point, and the engine's own behaviour is visible in the counters — the
condition accepts (the capability display is computed) and the prompt is simply never
opened for the activating player.

⚠️ This is a hypothesis that fits the evidence, not a proven mechanism. What would
settle it: a savestate from a duel where the **opponent** activates a targeting card on
Maiden, showing `+0x3C > 0`.

## A reader bug fixed here too

`scratch/read_maiden_diag.py` keyed its clause-1 verdict on `+0x2C` (the LAST r1 seen)
and `+0x24` (the LAST chain count). Both are overwritten by every call, and the final
call in a duel is almost always a chain-empty ignition sweep — so it printed "the
responder path never ran while an activation was live" for a state whose `+0x30` and
`+0x38` both said the walk matched and the condition accepted. It now keys on the
cumulative counters `+0x04 / +0x30 / +0x38 / +0x3C`, which cannot be overwritten away.

## Next Experiment

**E6 -- DONE, see the section below.**


---

# ⭐⭐ CLAUSE 1 CONFIRMED WORKING (2026-08-20) — this time from RAM, not from a report

Test rig: `scratch/make_bom_test_rom.py` rewrites **every one of the 305 AI decks** in
`Data_arc_pac/deck.pac` to Book of Moon `0x1538` only, sized per deck so every record
keeps its byte length. With no monsters of its own, the only face-up monster the AI can
target is the player's Maiden. Built on top of `rom_maiden_diag.nds` ->
`rom_maiden_bom.nds`, so the counters stay live.

**Result (`rom_maiden_bom.ml3`), read out of the savestate's monster zones:**

```
side 0   z2: donor 0x1ED7 (Maiden), DEFENSE  <- flipped face-down by Book of Moon
         z3: Blue-Eyes White Dragon 0x0FA7, ATTACK   <- SUMMONED
side 1   (empty)
```

User account, matching: *"I was able to activate maiden in response to book of moon. I
was asked if I wanted to activate something and I selected maiden."*

So the full clause-1 chain works: opponent activates a targeting card -> the player is
offered a response -> Maiden is selectable -> her effect resolves -> **Blue-Eyes White
Dragon is Special Summoned**. Graded on the board state in RAM, not on a message.

## The ignition side-effect is NOT present — and the r1 == 0 bail is why

`dispatch.onfield_ignition_is_a_cls3_record_only` means a cls3 record alone also makes a
card look like a manually-activatable ON-FIELD IGNITION. That would have let Maiden
Special Summon a Blue-Eyes on demand every turn, which is not her card.

It does not happen, and `rom_maiden_bom.ml2` shows why: the condition was entered **7**
times, every one a chain-empty sweep (`DIAG2 +0x10 = 7`, `+0x04 = 0`), and `+0x38`
(accepted) is **0**. The condition's first instruction — `cmp r5,#0 ; beq reject`, taken
verbatim from Blue-Eyes Shining Dragon — refuses every call with no activating
descriptor, so the capability enumerator never lists her. **The bail that makes the
condition faithful doubles as the ignition guard.** Measured, not assumed.

## ⚠️ OPEN — the ov5 counters were zeroed mid-duel

In `ml3` the clause-1 **resolver** count is 2 while the **condition** count is 0 and all
of DIAG2 is zero — yet the response prompt necessarily ran the condition earlier in that
same chain. So the ov5 cave block was re-initialised from the ROM image between the
condition and the resolver (an overlay reload for the summon sequence is the obvious
suspect; ov5 shares its base with other overlays — cf. ov41 in puzzles).

**This matters beyond diagnostics:** several shipped patches keep LATCH STATE in ov5
scratch (`CAVE_DS_SCRATCH`, `CAVE_EW_SCRATCH`, `CAVE_DF_STAGE`). If the cave can be
reset mid-resolution, those latches are not reliable across a chain. NOT investigated
here, and deliberately NOT asserted either way — two claims in this session were made
on less evidence than this and both were wrong. It needs its own measurement.

## Status

| clause | grade |
|---|---|
| 1 — targeted by a card or effect -> SS 1 BEWD | **CONFIRMED** (board state in RAM) |
| 2 — targeted for an attack -> negate, flip, SS | user-reported working; user-reported no regression after PART F |
| 3 — 1 Maiden effect per turn | shared cid-keyed turn log; both clauses query and post |

**Stated deviation:** clause 1 does not fire on *your own* activation (either turn) —
the engine computes "can respond" and never opens the prompt for the activating player.
Documented in the module docstring.

⚠️ `rom_maiden.nds` / `rom_maiden_diag.nds` / `rom_maiden_bom.nds` were built WITHOUT
`--text`, so the card still shows the donor's name in-game. The shipping build needs
`--text` (or the `apply_all_patches` chain, which passes it).

---

# THE OWN-ACTIVATION GAP — differential measurement (2026-08-20)

⚠️ NOT a stated deviation any more. **The user can chain their own cards to their own
activation in OTN**, so the chain model is not the limitation and the gap is specific to
this record. The earlier "stated deviation" framing was me narrowing the scope; that was
the user's call and they made it: fix it.

`rom_maiden_bom.ml2` (FAIL: player activates) vs `.ml3` (WORK: opponent activates,
captured at the prompt before selecting):

| counter | FAIL (you activate) | WORK (opponent activates) |
|---|---|---|
| cl.1 condition entered | 7 | 15 |
| **sweeps with a LIVE chain** (`DIAG2 +0x04`) | **0** | **4** |
| chain-empty sweeps (`+0x10`) | 7 | 11 |
| chain count `[0x0229A9FC+0x40]` | **0** | 2 |
| chain top (`+0x0C`) | — | `0x1538` Book of Moon |
| walk MATCHED / ACCEPTED | 0 / 0 | 4 / 4 |
| `desc[+5]<<24|+6<<16|+4<<8|+3` | `0x03000202` | `0x03000602` |
| invoker | `0x021EDC91` | `0x021EDC91` |

Two things fall out:

1. **`[0x0229A9FC+0x44]` is NOT count-1.** In the working case `+0x44 = 2` AND
   `+0x40 = 2`, and `0x0224B8B0` computed `&array[[+0x44]-1] = &array[1]` = the chain
   TOP (Book of Moon), which is right. The single-writer inference at `0x021D4BF8` was
   over-generalised from one site; treat `+0x44` as "the index+1 of the link to respond
   to". *This correction matters: a fix built on the old reading would have been wrong.*
2. **In the failing case the responder sweep never runs with anything on the chain.**
   All 7 entries are ordinary chain-count-0 capability refreshes.

⇒ The fix previously lined up — "read the chain top ourselves when `r1 == 0`" — is DEAD.
There is nothing to read: the chain is empty at that moment, not withheld.

⚠️ Also correcting an earlier claim in this file: the Rush Recklessly run that showed
`+0x04 = 1` with MATCHED and ACCEPTED had **its own Rush Recklessly** as chain top and
still produced no prompt. So both variants end the same way — the capability is computed
and the prompt is never opened for the activating player.

## The remaining discriminator, and the next measurement

The one engine-state difference captured so far is the **event code**: `desc[+4] = 2`
in the failing case, `6` in the working case. `desc[+4]` is written by `0x021EC740`'s
loop from the pending-timing table at `0x0229A37C + 0x838`, bounded by
`[0x0229AB7C + 0x30]` (which was 1 in both cases).

**E7 — the decisive test, now that self-chaining is known to work.** Maiden face-up,
a Blue-Eyes reachable, AND a Set Trap the player can legally chain. Player activates a
targeting card on their own Maiden. A prompt WILL appear (the Trap is chainable), so:

- **Is Maiden listed alongside the Trap?**
- Save AT THE PROMPT and read the counters.

Discriminates cleanly:
- `+0x04 > 0` and ACCEPTED > 0 but Maiden absent from the list ⇒ the filter is
  downstream of the capability bit; hook there.
- `+0x04 == 0` while the Trap is offered ⇒ the self-chain window enumerates Spell/Trap
  zones but not monster zones, and the fix has to reach the enumerator.

⚠️ The emulator must RELOAD the ROM first: the last three savestates were captured with
the previous build resident (stub literal-pool offset `324e` vs the rebuilt `3d4e`), so
the four new differential words at `DIAG2 +0x30..+0x3C` were not present.

---

# ⭐⭐⭐ RESOLVED (2026-08-20) — CLAUSE 1 WORKS ON EITHER PLAYER'S ACTIVATION

User: *"I can activate maiden in response to my own card, but I wasn't forcing the
window."*

`rom_maiden_bom.ml2`, captured AT THE PROMPT during the player's own activation:

```
+0x28 condition entered = 5      +0x04 live-chain sweeps = 3
+0x30 walk MATCHED      = 3      +0x38 ACCEPTED          = 3
+0x0C chain top         = 0x1329 Rush Recklessly (the PLAYER's own card)
DIAG2 +0x30 prompted player = 0  (the player)   +0x38 UI state word = 5
```

**So the "does not offer on your own activation" deviation recorded earlier in this
file was WRONG, and has been removed from the module docstring.** The trigger fires for
either player's activation.

## What the three failed rounds actually were

The engine only evaluates responders **while a response window is open**, and the player
has to open one. With nothing else chainable it is easy to activate a card and never see
the window at all — which is exactly what the early tests did. Every counter reading was
correct; the interpretation ("the engine computes the capability and never opens the
prompt") was not, because an absent prompt was read as an absent trigger.

**Lesson, and the reason this is written down rather than quietly deleted: a UI prompt
that was never opened is indistinguishable, in these counters, from a trigger that was
never offered.** The diagnostic could not tell them apart, so it was the wrong tool for
that question and no amount of re-reading it would have helped. The thing that settled
it was the user forcing the window.

`scratch/read_maiden_diag.py` now says so: with `ACCEPTED > 0` and the resolver not yet
entered, it reports the effect as BEING OFFERED and asks whether the state was captured
at the prompt, instead of declaring failure.

## Final grades

| clause | grade |
|---|---|
| 1 — targeted by a card or effect -> SS 1 BEWD | **CONFIRMED**, either player's activation. Opponent case verified on the BOARD STATE (`ml3`/`ml4`: Blue-Eyes White Dragon 0x0FA7 summoned into side 0 zone 3); own-activation case verified by the counters at the prompt (`prompted player = 0`, chain top = the player's own card, ACCEPTED 3x) plus the user selecting it |
| 2 — targeted for an attack -> negate, flip, SS | user-reported working; user-reported no regression after PART F |
| 3 — 1 Maiden effect per turn | shared cid-keyed turn log; both clauses query and post it |

No deviations remain except the ones inherent to the printed text mapping (no Damage
Step qualifier; one "you can" tag covering the whole effect).

## Remaining, in one pass

- Build with `--text` (all three test ROMs were built WITHOUT it, so the card still
  shows the donor name "Comrade Swordsman of Landstar" in-game).
- `apply_all_patches`, `check_allocations --emit`, and `verify()` across every shipped
  patch on the combined ROM.
- Still-open, unrelated: the ov5 cave block was observed zeroed mid-duel between the
  condition and the resolver. Shipped patches keep latch state in ov5
  (`CAVE_DS_SCRATCH`, `CAVE_EW_SCRATCH`, `CAVE_DF_STAGE`) and this has NOT been
  investigated.

---

# CLAUSE 3 — instrumented, ONE REAL BUG FOUND AND FIXED (2026-08-20)

User's four states on `rom_maiden_bom`:

| counter | `.ml3` BUG twice/chain | `.ml4` used | `.ml5` refused | `.ml6` next turn |
|---|---|---|---|---|
| cl1 cond entered / MATCHED / ACCEPTED | 12 / 8 / 8 | 0 | 1 / 0 / 0 | 9 / 5 / 5 |
| cl1 turn-log query + 1 | 1 | 0 | **2** | 1 |
| cl1 resolver entered | 0 | 2 | 2 | 2 |
| **cl1 turn-log POSTs** | **0** | **0** | **0** | **0** |
| cl1 resolver phase word | 0 | **1** | **1** | **1** |
| cl1 REFUSED by the log | 0 | 0 | **1** | 0 |

Cases 1-3 (use / refused same turn / available next turn) all behaved correctly
**in-game**. But two things are wrong underneath, and the counters are what exposed them.

## BUG A — the resolvers' turn-log POST was DEAD CODE

`cl1 POSTs = 0` in every state, and the resolver phase word is **1**, never `0x80`.
Both resolvers gated their POST on `[0x0229AAFC + 0x70] == 0x80`, and on this path that
field is not the phase.

⚠️ **This narrows `resolver.phase_protocol`.** "The phase lives at `[0x0229AAFC + 0x70]`
and the entry phase is 0x80" was closed on `0x02206F40`'s OWN code, which does read
`+0x70` — but a clause-1 (cls3) activation drives the resolver with a different counter,
and the summon still worked. So the fact holds for that function and does NOT generalise
to "the phase word for any resolver invocation". The KB claim is not wrong; the reading
of it was.

So clause 3 has been working **entirely on the engine's own activation logging**, not on
anything this patch does.

FIX: the POST no longer gates on a phase word at all. The turn-log node is KEYED, not
counted, so posting on every resolver entry is free and cannot be skipped by a phase
assumption.

## BUG B — the once-per-turn was stamped at RESOLUTION, so it lost to the CHAIN

`.ml3`: **Maiden activated twice in the same chain.** Both activations query the turn log
before either resolves, so both see it clear — `cl1 turn-log query + 1 = 1` (clear) with
**8** acceptances in that window. The engine's own log is written late for the same
reason, which is why every cross-turn case looked right while the same-chain case did not.

FIX — **PART G, `CAVE_MAIDEN_C1_COST`**: the stamp moves into the ACTIVATION procedure,
clause 1's slot4 (`+0x10`). The wrapper calls the shared body `0x021E50DC` (not the thunk)
and posts only when it returns **1**.

Reading `0x021E50DC`, which the fix depends on: it runs on its **own** phase counter
`[0x0229AAFC + 0x7C]` — ⚠️ NOT the resolver's `+0x70` — phase 0 = run slot3 then open the
Yes/No dialog, phase 1 = read the answer, phase 2 = finish. Phase 1 is
`ldr r1,[0x0229DD94 + 0x34] ; cmp r1,#0 ; bne 0x021E51AE`, and **only** the non-zero arm
(player said YES) returns 1; the zero arm advances the phase and returns 0 to abort.
⇒ **declining the prompt does NOT burn the once-per-turn**, which is the correct reading
of "you can".

### Why this is safe for clause 1 and would NOT be for clause 2

`timing.class_is_the_slot4_literal`: the WHEN-vs-IF classifier `0x0224AF7C` reads the
`+0x10` literal RAW and never calls it, so an unrecognised value puts a card in NO timing
class — the failure that cost Lightpulsar a withdraw-and-restore cycle. But it **returns
0 at once for descriptor selectors 0 and 3**, so a cls3 record's `+0x10` is never read.
Clause 1 is cls3: safe. **Clause 2 is cls1 and MUST keep the bare `0x021E51E5` literal**,
and `verify()` now asserts exactly that, alongside asserting clause 1 carries the wrapper.

Clause 2 keeps the resolution-time stamp. It is not exposed to bug B: a card cannot be
attacked twice within one chain.

## Next Experiment

**E8 — re-test clause 3 on the rebuilt `rom_maiden_bom.nds`** (reload the ROM in the
emulator first). Repeat all four cases. The new counter `DIAG3 +0x18` counts
activation-time stamps, so:

- `.ml3` case must now **refuse the second activation in the same chain**, with
  `+0x18 >= 1` and `cl1 REFUSED` rising.
- Cases 1-3 must still behave as before, with `cl1 POSTs > 0` now instead of 0.
- Also worth one check that was never possible before: **decline the Yes/No prompt**,
  then try again the same turn — the effect must still be available, because the stamp
  only happens on the accepting arm.

---

# SHIPPED (2026-08-20)

`patch_maiden_eyes_of_blue.py` implements all three clauses. Composition run with
`WRITE_TEXT = True`, so the name and description land this time (every earlier test ROM
was built without `--text` and showed the donor name).

| part | what | where |
|---|---|---|
| A1 | cls1 record (clause 2) | ov3, count-neutral over phantom `0x1DB6` |
| A2 | criteria row `{0x1ED7, 0x0FA7, 0x0223E2C9, 0x0802}` — **shared by both clauses** | ov3, count-neutral over phantom `0x1BBE` |
| A3 | attack-target gate remap (`bl` @`0x021C6624`) + shared admit list | ov3 + ov5 |
| B | `CAVE_MAIDEN_COND` / `CAVE_MAIDEN_RES` (clause 2) | ov5 |
| C/D | LIGHT / Spellcaster / Lv1 / 0 / 0, card_type 33; name + desc in 8 languages | bin2.pac |
| E | cls3 record (clause 1) | ov3, count-neutral over phantom `0x1C80` |
| E | `CAVE_MAIDEN_C1_COND` / `CAVE_MAIDEN_C1_RES` | ov5 |
| F | Spell-Speed-2 list insert — **makes clause 1 a Quick Effect** | ARM9 `0x0209C118`, count-neutral over phantom `0x1A86` |
| G | `CAVE_MAIDEN_C1_COST` — once-per-turn stamped at ACTIVATION | ov5, clause 1's slot4 |

Phantoms consumed: `0x1DB6` (cls1), `0x1BBE` (criteria), `0x1C80` (cls3), `0x1A86`
(Spell-Speed-2 list). All claimed in `PHANTOM_CLAIMS`; `check_allocations` clean.

## Grades — stated precisely, because this session got this wrong twice

| claim | grade |
|---|---|
| clause 1 fires and Special Summons Blue-Eyes | **IN-GAME CONFIRMED** on the board state (`rom_maiden_bom.ml3`/`.ml4`) |
| clause 1 works on either player's activation | **IN-GAME CONFIRMED** (`.ml2` at the prompt, prompted player = the controller) |
| clause 2 (negate / flip / summon) | user-reported working, and user-reported no regression after PART F |
| clause 3 across turns | in-game correct — but see below, it was the ENGINE's log doing it |
| **the PART G once-per-turn fix** | **RE-TESTED IN-GAME (E8) and reported passing** — the same-chain double activation is gone, AND declining the Yes/No prompt leaves the effect available later the same turn. User report, not a savestate reading. |

The decline case is the strongest evidence PART G is doing the work, because it
exercises the exact branch the fix turns on. `0x021E50DC` phase 1 returns **1** only on
the accepting arm (`[0x0229DD94 + 0x34] != 0` -> `bl 0x021CF834`); the declining arm
advances the phase and returns 0. The wrapper stamps only on a return of 1, so declining
cannot burn the once-per-turn. Before PART G that behaviour did not exist at all: the
resolver-side stamp never ran (its `cmp phase,#0x80` gate was dead code), so the
restriction was entirely the engine's own activation log, which has no notion of a
declined prompt.

If the same-chain double activation is ever seen again, start at
`dispatch.once_per_turn_must_stamp_at_activation` and read the activation-time stamp
counter (`DIAG3 +0x18`) in the `--diag` build.

## KB contributions this session

- `dispatch.responder_spell_speed_gate` — NEW. The whole spell-speed mechanism and the
  ARM9 Quick-Effect list. This was the blocker that cost three in-game tests.
- `dispatch.once_per_turn_must_stamp_at_activation` — NEW. Resolver-time stamping loses
  to the chain; stamp in slot4, and only when the player accepts.
- `dispatch.targeted_by_effect_condition` — STILL-OPEN note CLOSED (the invoker is
  `0x021EDC8C` inside `0x021EDA14`), and the prime suspect recorded as ruled out.
- `resolver.phase_protocol` — NARROWED. `[0x0229AAFC + 0x70]` is not the phase for every
  resolver invocation; a cls3 activation uses a different counter, and a `cmp #0x80` gate
  written on that assumption was dead code.

`author_facts --check`: **277 facts, 246 PASS, 0 FAIL, 31 UNVERIFIED.**

## Still open, unrelated to this card

The ov5 cave block was observed **zeroed mid-duel** between the condition and the
resolver. `CAVE_DS_SCRATCH`, `CAVE_EW_SCRATCH` and `CAVE_DF_STAGE` keep latch state in
ov5. Not investigated, and no cause assumed.

## Card text — the 51-byte budget, and why it is not an engine limit

The shipped description was `"1/turn, if attacked: negate, flip, SS Blue-Eyes."`, written
when only clause 2 existed — **it never mentioned clause 1**. Replaced with
`"1/turn: if targeted or attacked, SS Blue-Eyes."` (46 B), which covers both triggers;
"negate, flip" is what had to go.

**The 51 bytes is the DONOR'S OWN English string**, because `patch_boggart_knight` writes
text strictly in place (`len(new) <= len(old_desc)`). It is NOT an engine ceiling: the
English desc blob already carries a **657-byte** description (Manga Ryu-Ran), and
f/g/i/s/j/k/r all exceed 680 (r reaches 1196).

### Donor swap: surveyed and REJECTED
`scratch/survey_donors.py` ranks every card by description slot subject to name slot >= 24,
records-free across cls0-3 / criteria / effect / summon-proc / GY-action / leave-mask, no
word-aligned cid literal in ov3 or ARM9, and obtainable. **Only 5 candidates exist**, and
four are Elemental HEROes (`0x1C1B` Neos Alius 279 B, `0x1A00` 242 B, `0x19FF` 153 B,
`0x1981` 105 B) — an archetype entangled with set-code and fusion tables the sweep does
not even check, so they are *less* clean than `0x1ED7`. Swapping would mean redoing every
phantom choice, every sorted insert position and the ARM9 insert, then re-testing the whole
card, to land on a worse donor.

⚠️ The reusable-dead-slot idea also fails: the 72 unobtainable cards with long
descriptions (120-244 B) are all **Tokens**, whose text IS displayed in play.

### The proper fix, deliberately deferred to its own task
APPEND the new string to `card_desc_<L>.bin` and repoint this card's `desc_off` in
`card_indx_<L>.bin`. Both are u32 offsets; `pac.build_modified_pac` already repacks a v1
archive when an inner file changes size. Untested here — bin2.pac has only ever been
edited at +0 B, and `patch_boggart_knight` records that growing the NAME blob correlated
with in-game trouble — so it needs its own build-and-test rather than being bolted onto
this card. **It would benefit every card in the repo: all of them ship truncated text.**

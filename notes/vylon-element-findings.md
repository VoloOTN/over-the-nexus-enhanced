# Vylon Element (0x24B5) — the +10-only build is broken; the fix is the full Spy transplant

Session 2026-09-13. Settles issue 1 of
`ygo_tools/tools/enhanced_edition_definitive/notes/vylon-element-discrepancies.md`
as reading **(b) a regression**.

## Confirmed

- **IN-GAME CONFIRMED BY USER 2026-09-13** on `rom_vylon_element.nds` sha256
  `6108dfc470a44f82b43bd842cef241c21c8f9ba67165a44a328b7a598c0b6d62` (the Spy
  transplant + "If ... Special Summon 1" text). User: *"it behaves exactly as the
  card text described"*, then, asked about each item separately, *"All 3."*:
  1. destroying a face-up "Vylon" Equip Card Special Summons exactly **1** "Vylon"
     Tuner from the Deck, with **no Yes/No prompt**;
  2. the **Synchro-material restriction still holds** on that Tuner;
  3. on the **Rod of Silence - Kay'est board** (something resolving after the
     destruction) the effect **still goes off — it does NOT miss timing.**
- **⚠️ WHICH FIELD DEFEATS THE MISS IS NOT ATTRIBUTED.** Item 3 is a measured
  outcome of the FULL four-field record, not of any one field. It is NOT the +10
  tag by that tag's own mechanism (the classifier consumers are proven boolean,
  below), so the candidates are +0C `0x0224A115` (offer unconditionally), the
  driver `0x02206CAD`, the dropped +14 tail, or the class-0 enqueue path through
  `0x021D3E78`'s `0x65` state. Nobody should cite this as "class 0 never misses".

- **The shipped `+10`-only build fails in-game.** User report, verbatim:
  *"The card "activates" but the resolver isn't working properly and doesnt
  special summon a tuner from deck anymore."* That is the failure mode the
  oracle's own docstring predicted at
  `otn_enhanced/cards/vylon_element.py:39-45` — `+10 = 0`
  alone makes the effect "summon nothing or data-abort", because the native
  resolver `0x0221DA95` is a multi-pass state machine reading offer-phase
  context (destroyed-Equip count, loop bounds) that the mandatory enqueue path
  never sets up.
- **`+0C = SPY_COND` alone does not rescue it.** The user's working-tree
  experiment moved only `+0C` to `0x0224A115` (`movs r0,#2 ; bx lr`, always
  eligible). That explains the "activates" half of the report: the card becomes
  unconditionally activatable while `+04` is still the native offer-phase
  resolver and `+14` still its count tail, so there is nothing to resolve.
  User, this session: *"The spy cond was me trying something that didnt work in
  the end."*
- **All four cls1 fields move together or not at all.** Vylon cls1[1321]
  `@0x0228DCAC` now carries Gravekeeper's Spy (0x1585)'s record verbatim:
  `{+04 0x02206CAD, +08 0, +0C 0x0224A115, +10 0, +14 0}`, cid kept at 0x24B5.
  `verify()` asserts both Vylon's record AND that Spy's own record still equals
  what we cloned, so a drift in the template cannot pass silently.
- Built `data/over_the_nexus/working/rom_vylon_element.nds`,
  `verify()` **4/4 passed**. AWAITING IN-GAME TEST.

## Ruled Out

- **⚠️⚠️ THE `+10` TAG CANNOT MAKE ANYTHING NEVER-MISS. THE WHOLE PATCH PREMISE
  IS THE DEBUNKED READING.** `timing.class_is_the_slot4_literal` (VERIFIED, KB
  proofs re-run this session: timing_classifier 6/6 PASS) settled this in-game
  on **2026-08-17**, i.e. *after* patch_vylon_element was written (2026-06-10):

  > "class 0 does NOT mean 'cannot miss the timing'; it means PROPERLY
  > CLASSIFIED TRIGGER, after which the engine applies the miss-timing rule to
  > it correctly. ⚠️ The opposite reading was inferred from
  > patch_gravekeepers_recruiter's prose and cost patch_lightpulsar a
  > withdraw-and-restore cycle."

  So `+10 = 0` was never going to stop the miss, and neither is
  `0x021E50DD`. patch_vylon_element's docstring table (`+10 == 0 -> never
  misses`) is the exact claim that was measured false. Everything this card has
  cost since was spent on a mechanism that does not exist.
- **WHEN→IF VIA THE TAG IS A PROVABLE NO-OP FOR THIS CARD — class 1 and class 2
  are behaviourally IDENTICAL everywhere except the GY-action offer.** Closed
  structural proof, offline, this session. `0x0224AF7C` has exactly five ov3 BL
  call sites (`scratch/vylon_classifier_consumers.py`), and how each one consumes
  the returned class is:

      0x021D3A0A  CMP R0,#0  BEQ    boolean
      0x021D3FF6  CMP R0,#0  BNE    boolean
      0x021D40A0  CMP R0,#0  BNE    boolean
      0x021F053E  CMP R0,#0  BEQ    boolean
      0x021EDC76  CMP R0,#2  BEQ    *** the ONLY site that distinguishes 2 ***

  `0x021EDC76` is inside the **GY-action** offer arm of `0x021EDA14`
  (`dispatch.gy_offer_consults_slot3_and_the_timing_class_can_bypass_it`,
  VERIFIED) — reached only for a descriptor with `desc[+5] == 2`, i.e. a GY
  ignition. Vylon Element is a Continuous Spell triggering on Equip destruction,
  so it never reaches that site. Every site it DOES reach treats the class as a
  boolean, so swapping `0x021E51E5` for `0x021E50DD` changes nothing it can
  observe. `+10 = 0` is not a no-op (it flips all four booleans) but it flips
  them the wrong way: it makes the trigger LESS classified, not never-missing.
- **The 3DS offers no never-miss template for this card.** `on_trigger[138]`
  0x24B5 = `{+04 0x00431394, +08 0, +0C 0x0049D1F0, +10 0x004001F4,
  +14 0x004773D4}`, and `0x004001F4` is the known equivalent of the NDS WHEN tag
  `0x021E51E5`. Konami ships it as can-miss in both builds, with its "up to N"
  resolver — because the printed card *is* "When … : You can", which genuinely
  misses timing under real rules. Never-missing is a house rule, so it cannot be
  copied from anywhere; it has to be built.

- **"Convert the WHEN tag into the IF tag" as a standalone fix** (the user's
  question this session). `+10 = 0x021E50DD` (category 1, scheduled, never
  misses) was tried in an earlier round and was "NOT enough" per the oracle
  docstring; per `HOWTO.md:348-350` the WHEN thunk `0x021E51E5` unconditionally
  tail-calls `0x021E50DC`, the IF tag's own body, so the two run identical
  timing logic and flipping the tag changes only the category the classifier
  `0x0224AF96` reports. It does not give the native resolver the offer-phase
  context it needs.

- **SHIPPED STATE (user decision 2026-09-13): the MANDATORY Spy transplant, with
  ONE summon accepted and the text reworded to match.** The user was offered the
  native "up to N" card and chose the mandatory record instead: *"keep it in its
  mandatory state as an IF effect but only special summons 1 monster."* So
  cls1[1321] = `{+04 0x02206CAD, +08 0, +0C 0x0224A115, +10 0, +14 0}` and
  `CARD_TEXT[0x24B5]` now reads "If ... Special Summon **1** 'Vylon' Tuner
  monster from your Deck. **It** cannot be used as a Synchro Material
  Monster ...". Built `rom_vylon_element.nds`, `verify()` **4/4 PASS** (record,
  the four fields, Spy's own template undrifted, and the text present via
  `card_text.check_rom_text`). In-game confirmed by user 2026-09-13 (top entry).
- **What the mandatory record actually buys, stated precisely.** Not a
  miss-timing bypass (proven impossible via the tag, below). It buys: class 0 =
  properly-classified trigger with **no Yes/No prompt**, and +0C = `0x0224A115`
  (`movs r0,#2`) = **offered unconditionally**, skipping the candidate re-check
  that a +0C return of exactly 1 would force (per
  `dispatch.gy_offer_consults_slot3_and_the_timing_class_can_bypass_it`). That
  is a real behavioural difference and is why it fires where the native optional
  record did nothing. The "If" in the card's text means "no prompt", not "cannot
  miss timing".
- **Where the trigger/response state machine lives (offline, this session).**
  Two of the four boolean consumers (`0x021D3FF6`, `0x021D40A0`) are in ONE
  function, `0x021D3E78`, which `notes/dueling-ai-findings.md:18` already
  identifies as the **secondary dispatcher: a switch on `[ctx+0x60]`, range
  0..0xE** (confirmed at the head: `ldr r0,[r5,#0x60] ; cmp r0,#0xE ; bgt ;
  add pc,r1`). `[ctx+0x60]` is the state, written back with `str r0,[r6,#0x60]`.
  At the `0x021D3FF6` site the arms are:
      class 0        -> `0x0225BD84` (KB: the kind-2 UI-REQUEST POST wrapper of
                        `0x0225BD40(side, kind, a, b)`) then state := 0x65
      class 1 or 2   -> branch away to 0x021D400C
  So class 0 is the arm that PROMPTS, which is consistent with the Lightpulsar
  measurement (class 0 = properly classified, and the player is told).

## Open Questions

- ~~Does the shipped record still miss timing?~~ **RESOLVED 2026-09-13: no**,
  in-game confirmed by user on the Kay'est board (see Confirmed).
- **Where the miss-timing rule is actually applied — still unlocated, and NO
  LONGER NEEDED FOR THIS CARD.** Only worth chasing if another card needs a
  never-miss trigger that keeps its native resolver (e.g. an "up to N" count). It is
  NOT the `+10` tag (proven above) and not the classifier. The live candidate is
  the `[ctx+0x60]` state machine `0x021D3E78`: something decides the pending
  trigger's window has closed before its arm is reached. Next step is to find
  which state value means "response window open" and who clears it.
- Whether the native "up to N" resolver's count comes from a destroyed-Equip
  tally that survives an intervening resolution, or is recomputed when the
  trigger finally runs. If it is recomputed, a never-miss fix has to preserve
  the count as well as the trigger.

- ~~Printed text overstates the count~~ **RESOLVED 2026-09-13**: text reworded
  to "If ... Special Summon 1", so the printed text matches the ROM. The card is
  a deliberate deviation from the real card's "equal or lower number", by user
  decision.

## Next Experiment

**NONE FOR THIS CARD — it is in-game confirmed (2026-09-13, all three items).**
The only remaining step is the chain re-baseline under *Not yet done*, which
waits for the user's go-ahead.

*PARKED, for a future card that needs a never-miss trigger while KEEPING its
native resolver (the thing this card gave up):* the recipe below locates the
real miss-timing rule. It was never run.

Ask the user for TWO savestates on `rom_vylon_element.nds`, both with Vylon
Element face-up and a "Vylon" Equip Card on a monster:

1. **MISS case** — the Rod of Silence - Kay'est board from the oracle docstring,
   saved immediately after the Equip is destroyed and the trigger has been lost.
2. **HIT case** — the same board with nothing else to resolve, saved immediately
   after the Equip is destroyed, with the prompt up.

Then, offline with `scratch/thumbemu.py` (savestate Thumb emulator) plus a
savestate diff of the two:

- Read `[ctx+0x60]` in both. The differing value names the state that means
  "response window still open".
- Walk `0x021D3E78`'s jump table (`add pc,r1` @0x021D3EBA, bound `cmp r0,#0xE`)
  and identify the arm each state selects.
- Find who WRITES `[ctx+0x60]` between the two states — that writer is the
  miss-timing rule, and a cid-scoped detour on it is the candidate fix.

Do NOT open a GDB session for this: savestate parsing is the authoritative bulk
read here, the melonDS stub is one-shot per emulator session, and we do not yet
know which breakpoint to arm — which is exactly the situation the preflight rule
says to stay out of.

## Not yet done

Behaviour changed, so the chain is now stale on purpose:

- `finished_patches/patch_vylon_element.py` (the oracle) still writes the
  `+10`-only record and has **no `verify()`**.
- `.equiv vylon_element` will report a difference, and the chain sha256 /
  `rom_baseline.nds` need a deliberate re-baseline.

The in-game test PASSED 2026-09-13, so the card is no longer being debugged; the
re-baseline is now blocked only on the user saying go. Order when they do: bring
the oracle's record in line with `patches/vylon_element.py` (+ give it a
`verify()`), copy `rom_all_patches.nds` aside, run `apply_all_patches` as a
script and assert the step count + `ALL ... PATCHES APPLIED` + sha256, copy over
`rom_baseline.nds`, record the hash in `CURRENT-BASELINE.md`, then
`.equiv vylon_element` → `[IDENTICAL]` and `.build --compare` → `IDENTICAL`.
Also rename `steps.py:52` — "WHEN -> IF trigger fix" no longer describes it.

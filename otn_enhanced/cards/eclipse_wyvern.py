"""Eclipse Wyvern (LIGHT / Dragon / Level 4 / 1600 / 1000) on Divine Dragon Ragnarok 0x1859.

    If this card is sent to the Graveyard: You can banish 1 LIGHT or DARK Dragon-Type monster with 7 or more Levels from
    your Deck. When this card is banished from the Graveyard: you can add that banished monster to your hand.
    (See notes/eclipse-wyvern-findings.md for the exact printed text and the accepted deviations.)
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class sent_to_graveyard_from_anywhere_banish_light_or_dark_dragon_level_7_or_higher_from_deck_and_add_it_later:
    """Eclipse Wyvern (Divine Dragon Ragnarok 0x1859): 'If this card is sent to the GY: banish 1 Level 7+ LIGHT or DARK Dragon from your
    Deck ... (and the banished card is later added to the hand).' Trigger from ANY location: a leave-mask row (sent-to-GY) with list30
    left untouched (being in list30 arms the field-only path), cls2 record behind an ov5 pick-recorder wrapper, a criteria row whose ov5
    handler restricts the Deck pool to LIGHT|DARK Dragons Level >= 7, the hardcoded sent-to-GY event gate admitted through an ov3 stub in
    a dead block, and the banish-from-GY event gate inside the mover 0x021C7118 admitted through a second ov3 stub (PART G was retired:
    it gated a chain a GY->banished move never enters). Original code embedded verbatim (BYPASS_G fixed True)."""

    def __post_init__(self):
        from otn_enhanced.cards import snoww as sn
        sn.register_switch_stub(0x021B5920, 24, {0x1859: 0x021D19BE})

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import ov3_off as _off
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid

        # --- PART A: the SENT-TO-GY (any location) trigger registration ---------------
        # The leave dispatcher has TWO registration paths and they are mutually exclusive:
        #   * list30 @0x0226E904 (+ list106 @0x0226E990) set the arming flag [sp+0x18];
        #   * ONLY IF that flag is still 0 (`ldr r0,[sp,#0x18]; cmp r0,#0; bne skip` at
        #     0x021C80FE) does it consult the MASK TABLE below.
        # list30's arm is gated on [sp+0x2C], which is "left the FIELD" -- in-game
        # confirmed: with the donor forced into list30 the effect fired only on a
        # field->GY leave, never on a discard or a mill. The mask table is the any-location
        # path, so registering here (and NOT in list30) is the correct fix.
        MASK_BASE, MASK_COUNT, MASK_STRIDE = 0x0226EC1C, 0x98, 4   # {u16 cid, s16 mask}, sorted
        MASK_FMT = "<Hh"
        # Mask 0x0800 = "this card is SENT TO THE GRAVEYARD", any source zone. All 15 real
        # cards carrying exactly this mask are worded that way -- Dandylion 0x19FE ("If this
        # card is sent to the Graveyard"), Peten the Dark Clown, Jinzo - Returner, The White
        # Stone of Legend, Skull-Mark Ladybug, Archfiend of Gilfer, Limiter Overload,
        # Cockroach Knight, Outstanding Dog Marron, Sword of Deep-Seated, Cross Porter.
        # (Contrast the KB's 0x0C04 = destroyed + to-GY, a strictly narrower mask.)
        MASK_SENT_TO_GY = 0x0800
        MASK_DROP_PHANTOM = 0x16F5          # a phantom that ALREADY carries mask 0x0800 -- inert either way
        MASK_NEW = (DONOR_CID, MASK_SENT_TO_GY)
        LIST30_BASE, LIST30_COUNT = 0x0226E904, 0x1E   # asserted untouched, never written

        # --- PART B: cls2 ------------------------------------------------------------
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 24
        SARCO_RESOLVER = 0x0221CD29
        SARCO_CONDITION = 0x021F0BDD   # the matched per-cid condition dispatcher (PART F)
        CLS2_DROP_PHANTOM = 0x194A          # phantom (no card_prop) sacrificed to keep the count
        # +0C is Gold Sarcophagus's OWN condition -- see PART F. Pairing the borrowed
        # resolver with the condition the native card uses is what removes the empty-deck
        # freeze: the effect simply does not trigger when it has no legal target.
        # DIAGNOSTIC A/B SWITCH. The card worked from hand+deck with cls2 +04 = the NATIVE
        # resolver and no PART H. It stopped after PART G + PART H were added, while the
        # PART E gate still verifies as ACCEPT -- so the event IS posted and the failure is
        # downstream. Setting BYPASS_H isolates which of the two is responsible in ONE test.
        # ===================== REVERT TO THE LAST KNOWN-GOOD STATE =====================
        # Clause 1 was CONFIRMED WORKING in-game from field, hand (discard) and deck (mill)
        # with PARTS A/B/C/D/E only: cls2 +04 = the NATIVE resolver 0x0221CD29, +0C = 0.
        # Everything added after that (F condition row, G banish gate, H ov5 wrapper) was a
        # regression. They are disabled here; clause 2 will be rebuilt from the 3DS
        # reference rather than by repairing borrowed Spell-activation code.
        # PART G is RETIRED. It admitted the donor to the
        # banish leaf of 0x021D1300 -- a chain a GY -> banished move PROVABLY never enters,
        # because that transition has its own mover (0x021C7118) that posts by calling the
        # register-prim 0x021D3168 directly. Its two ov3 dead blocks are released and one is
        # re-used by PART I, which hooks the gate that IS on the live path.
        BYPASS_G = True
        BYPASS_H = False
        CLS2_NEW = (DONOR_CID,
                    SARCO_RESOLVER if BYPASS_H else (ov5_cave.CAVE_EW_RECORD | 1),
                    0, 0, 0, 0)

        # --- PART F: the EMPTY-DECK FREEZE fix (pure data) ---------------------------
        # The bug: Gold Sarcophagus's resolver reaches the completion routine 0x021D269C
        # ONLY on its phase-0x7E success path. Its phase-0x80 arm returns 0 without it when
        # 0x02243FA8(side, cid, 0) finds no candidates, so the effect never finishes and the
        # console hangs. PART E made this MUCH easier to hit -- the trigger now fires from
        # the hand and the deck as well as the field.
        #
        # The fix is not a wrapper resolver but the condition slot the native card already
        # uses. Gold Sarcophagus's cls0 record pairs resolver 0x0221CD29 with
        # **+0C = 0x021F0BDD**, a per-cid condition DISPATCHER: it looks the acting cid up
        # in the table below via 0x02022E44 and, if a row exists, calls `blx [row+4]` and
        # then `blx [row+8]`; with NO row it returns 0 (0x021F0C0C).
        #   row+4 = 0x021F0619: side = desc[+2] ^ desc[+6], then
        #           0x02243FE0(side, cid, 0x02234E78(desc)) != 0  -> "a legal target exists"
        #   row+8 = 0x021F6565: 0x021BABE8(side) != 0             -> the SAME gate the
        #           resolver tests first at phase 0x80
        # i.e. the condition tests exactly the two things that make the resolver bail. If
        # either fails the condition returns 0, 0x0224AD94 hands back 0, the event is never
        # admitted, and the effect simply DOES NOT TRIGGER -- which is also the correct
        # Yu-Gi-Oh! behaviour for a target-less trigger.
        #
        # ⚠️ The docstring's warning that "a non-zero +0C froze earlier builds" came from
        # gravekeepers_recruiter pairing a MISMATCHED condition with its resolver.
        # Here the pair is the native one, taken from the card the resolver belongs to.
        # ⛔ WITHDRAWN -- IN-GAME REGRESSION. Setting cls2 +0C to the native
        # condition 0x021F0BDD stopped the trigger firing from the HAND and the DECK while it
        # still fired from the field. 0x021F0BDD returns `pred() && act()`, and its act
        # 0x021F6565 is `0x021BABE8(side)` -- a gate that evidently holds on the field path
        # but NOT while a discard/mill is resolving, so the event was refused at admission
        # (0x0224AD94 -> r6 = 0) before it could ever dispatch. The empty-deck guard now
        # lives inside the PART H wrapper, which is reached only after the event is admitted.
        COND_BASE, COND_COUNT, COND_STRIDE = 0x0226FAFC, 0x92, 12   # {u16 cid, u16 pad, u32 pred, u32 act}
        COND_FMT = "<HHII"
        COND_PRED = 0x021F0619              # "a legal target exists"
        COND_ACT = 0x021F6565               # the 0x021BABE8 gate
        COND_DROP_PHANTOM = 0x1748          # nearest phantom (row 22); 7 exist in this table
        COND_NEW = (DONOR_CID, 0, COND_PRED, COND_ACT)

        # --- PART C: criteria / populate registry ------------------------------------
        POP_BASE, POP_COUNT, POP_STRIDE = 0x022713C4, 1388, 12
        POP_FMT = "<HHIHH"
        POP_DROP_PHANTOM = 0x18F8
        # ⚠️ MUST be 0x0223CAD9, NOT 0x0223CAB5. Both are Deck-family handlers, but
        # 0x0223CAB5 is the SPECIAL-SUMMON-from-Deck family (28 of its 32 rows are Special
        # Summons) and it requires every candidate to be SS-legal. That silently rejected
        # EVERY Level 7+ Dragon -- Dark Armed Dragon and Red-Eyes Darkness Metal Dragon
        # cannot be Special Summoned from the Deck -- so the search returned 0 candidates
        # and the effect froze the game (savestate rom_all_patches.ml2: phase 0x80,
        # acting cid 0x1859, candidate count 0, with 4 legal targets sitting in the deck).
        # 0x0223CAD9 is the general-purpose Deck handler. THE TEMPLATE IS SOUL OF FIRE
        # 0x1BAF = {filt 0xFFFF, h 0x0223CAD9, flags 0x0002, extra 0x2000} -- "Select 1
        # Pyro-Type monster from your Deck and remove it from play", i.e. the SAME action
        # (race-filtered deck pick + banish), and one of the 8 native callers of the
        # deck-banish primitive 0x021D21DC. Fossil Dig 0x20A0 {h 0x0223CAD9, fl 0x0002,
        # extra 0x4898 = Dinosaur + Lv<=6} additionally proves handler + flags + race +
        # level bound compose correctly.
        DECK_HANDLER = 0x0223CAD9           # general-purpose Deck handler (Soul of Fire / Fossil Dig family)
        # --- PART C2: "LIGHT or DARK" -------------
        # 0x0223CAD9 hands the worker 0x0223BC3C NO per-candidate callback (r2 = 0, r3 = 0).
        # The 3DS ships Eclipse Wyvern (cid 0x26E5, word 0x085C0002) on a handler of the SAME
        # shape whose only difference is r2 = an attribute-mask callback and r3 = &6. The NDS
        # has that callback natively: 0x0223C8DD returns (*[sp+4] & (1 << get_attribute(cid)))
        # != 0, but no row-driven handler passes it. So PART C2 is a clone of 0x0223CAD9 in ov5
        # with r2/r3 set as the 3DS does -- no filter logic is reimplemented.
        # mask 6 = 1<<1 LIGHT | 1<<2 DARK (fusion.attribute_leaf numbering).
        CRIT_WORKER = 0x0223BC3C
        ATTR_CALLBACK = 0x0223C8DD
        ATTR_MASK = (1 << 1) | (1 << 2)
        ATTR_HANDLER_LEN = 0x30
        POP_NEW = (DONOR_CID, 0xFFFF, ov5_cave.CAVE_EW_ATTRH | 1, 0x0002, 0x085C)   # Dragon, Lv>=7, Deck, LIGHT|DARK
        POP_OLD = (DONOR_CID, 0xFFFF, DECK_HANDLER, 0x0002, 0x085C)   # pre-C2 row (any attribute)


        def _attr_handler(base: int) -> bytes:
            """0x0223CAD9 + the 3DS's attribute callback. Same stack shape: [sp] = row+8,
            [sp+4] = mode 2, [sp+8] = the mask that r3 points at (the callback's [sp+4])."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, LR}")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", f"R0, #0x{ATTR_MASK:X}")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R3, SP, #0x8")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.call_addr(CRIT_WORKER, R0, R1, ATTR_CALLBACK)
            b.insn("POP", "{R1, R2, R3, PC}")
            blob = b.assemble(base, pad="nop")
            assert_thumb1_only(blob, base)
            assert len(blob) <= ATTR_HANDLER_LEN, f"C2 handler {len(blob)} B > {ATTR_HANDLER_LEN}"
            return blob

        # --- PART D: card face -------------------------------------------------------
        NEW_ATTRIBUTE = "LIGHT"             # donor is ALREADY LIGHT
        NEW_RACE = "Dragon"                 # ... and already Dragon
        NEW_LEVEL = 4                       # ... and already Level 4
        NEW_ATK = 1600                      # donor was 1500
        NEW_DEF = 1000                      # ... and already 1000
        # The donor is a vanilla, so its card_type must be promoted or the card would still
        # read as a Normal Monster (and be seen by "Normal Monster" support) despite having
        # an effect. Same step the T.G. Normal-Monster conversions take.
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Effect Monster"]
        NEW_NAME = b"Eclipse Wyvern"
        # ⚠️ CLAUSE 2 IS DELIBERATELY WORDED MANDATORY. The printed card says "You can add",
        # and the engine's optional-trigger machinery is the cls record's activation procedure
        # (+0x0C / +0x10, run by 0x02217F80 -- see KB event.optional_trigger_is_record_shape),
        # NOT anything the resolver can raise. Our donor carries BOTH clauses on ONE cls2
        # record and clause 1 is mandatory, so optionality cannot be switched on there without
        # regressing clause 1. User's decision: change the text instead of building
        # a per-clause activation-procedure split. The effect is otherwise faithful.
        # ⚠️ THE DESCRIPTION IS WRITTEN IN PLACE, so it must fit the donor's existing slot:
        # 129 B for English, and the tool SILENTLY SKIPS the language (keeping Divine Dragon
        # Ragnarok's original text) when it does not. The full wording of both clauses is
        # 222 B and was skipped everywhere on the first attempt. Abbreviated to 121 B, which
        # fits e/g/i/s/r; [f] 99 B, [j] 88 B and [k] 86 B still skip, exactly as they did with
        # the clause-1-only text.
        NEW_DESC = (b"Sent to the GY: Banish 1 Lv7+ LIGHT or DARK Dragon from your Deck. "
                    b"If banished from your GY: add that card to your hand.")

        GATE_ARM = 0x021D14D2               # the terminal node cid 0x1859 actually reaches
        GATE_ARM_NATIVE = bytes.fromhex("95329542")       # ADD R2,#0x95 ; CMP R5,R2
        GATE_ACCEPT = 0x021D1526            # -> 0x021D1938 -> 0x021D199E  MOV R0,#1 = accept
        # ov3 dead-code block 0x021B591E (28 B, phantom 0x19BE), based 2 B in for a
        # 4-aligned literal pool.
        GATE_STUB = 0x021B5920
        GATE_STUB_LEN = 24

        # Declare this stub to snoww's whole-table switch tracer.  Registered at IMPORT
        # time, not on first use: snoww runs LATER in apply_all_patches (step 30 vs this
        # card's 25), and its regression walk stops at any BL it cannot see through -- so
        # without this every cid that merely passes through this stub reads as "changed leaf".
        # ⚠️ This emits NO BYTES; it only populates the tracer's tables.
        from otn_enhanced.cards import snoww as _snoww  # noqa: E402
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R3, R4, R7
        from otn_enhanced.effects.common import ov3_off as _off

        # The donor's terminus is the ACCEPT path's flag store.  snoww's tracer follows
        # this stub's INDIRECT tail (`LDR R0,[PC,#4] ; BX R0`) through GATE_ACCEPT and on to
        # 0x021D19BE `STR R0,[SP,#0x14]`, the first instruction it does not model.  That is a
        # MEANINGFUL terminus: reject cids stop two bytes later at 0x021D19C0 `MOVS R0,#0`
        # (snoww.SWITCH_END), so the guard genuinely distinguishes accept from reject
        # rather than merely checking that the walk stopped inside this stub.
        GATE_ACCEPT_LEAF = 0x021D19BE



        def _gate_stub(base: int) -> bytes:
            """Admit the donor, then hand the native 0x1828 test back to the caller's BEQ.

                +0   ADD R2,#0x95     ; replicate the displaced op -- downstream code on the
                                      ;   reject path expects r2 == 0x1828
                +2   LDR R0,[PC,#12]  ; = DONOR_CID                       (pool at +16)
                +4   CMP R5,R0
                +6   BEQ +12          ; our cid -> the unconditional accept
                +8   CMP R5,R2        ; the displaced 0x1828 test: sets Z for the caller
                +10  BX  LR           ; -> 0x021D14D6 BEQ (flags intact; BX never writes them)
                +12  LDR R0,[PC,#4]   ; = GATE_ACCEPT | 1                 (pool at +20)
                +14  BX  R0
                +16  .word DONOR_CID
                +20  .word GATE_ACCEPT | 1

            Register safety, checked on all THREE exits: reject reaches 0x021D19C0
            `LDR R0,[SP,#0x2C]`, accept reaches 0x021D199E `MOV R0,#1`, and the 0x1828 arm
            reaches 0x021D14E8 -> 0x021D18C4 `LDR R0,[SP,#0x34]` -- r0 is dead on every one.
            LR is dead because 0x021D1300 pushed it at entry and returns via POP {...,PC}.
            """
            assert base % 4 == 0, "literal pool needs a 4-aligned base"
            lit0 = ((base + 2 + 4) & ~3)
            lit1 = ((base + 12 + 4) & ~3)
            blob = struct.pack(
                "<8H2I",
                0x3295,                                    # ADD R2,#0x95
                0x4800 | (((base + 16) - lit0) // 4),      # LDR R0,[PC,#..] -> DONOR_CID
                0x4285,                                    # CMP R5,R0
                0xD001,                                    # BEQ +12 (-> base+12)
                0x4295,                                    # CMP R5,R2
                0x4770,                                    # BX  LR
                0x4800 | (((base + 20) - lit1) // 4),      # LDR R0,[PC,#..] -> accept
                0x4700,                                    # BX  R0
                DONOR_CID,
                GATE_ACCEPT | 1,                           # Thumb bit
            )
            assert len(blob) == GATE_STUB_LEN, len(blob)
            return blob


        # --- PART G: admit the donor to the BANISH event gate (clause 2's prerequisite) --
        # Clause 2 ("If this card is banished from your Graveyard: you can add the monster
        # banished by this card's effect to your hand") needs the engine to POST an event
        # when the card is banished -- and that is gated exactly like the sent-to-GY event
        # was, on the other branch of 0x021D1300.
        #
        # 0x021D138A routes NON-GY destinations to the switch at 0x021D1B98 (reached via the
        # compiler's BL-as-long-jump at 0x021D138E -- it is the tail of the same function,
        # not a callee). Its leaf 0x021D1D3E is the BANISH gate:
        #     LDR R0,[SP,#0x30] ; CMP R0,#0xF        -> destination == BANISHED
        #     LDR R0,[SP,#0xC]  ; AND #0xC0 ; CMP #0xC0 ; BEQ reject
        #     MOV R0,#1                               -> eligible
        # Only TWO cids reach it: 0x17BB and Cyber Ouroboros 0x1CF6 ("when this card is
        # removed from play"), which is the native template for this trigger.
        #
        # Simulating the chain for 0x1859 ends at the node that routes 0x17BB -- so, per the
        # session-13 lesson, THAT is the node to hook (never a phantom's arm: the chain is a
        # sorted binary search and an out-of-interval cid is simply never routed there):
        #     0x021D1C3E  BGT 0x021D1C44                  <- the only inbound branch
        #     0x021D1C44  LDR R0,=0x17BB                  <- DISPLACED
        #     0x021D1C46  CMP R5,R0                       <- DISPLACED
        #     0x021D1C48  BEQ 0x021D1D3E  (banish leaf)   <- KEPT IN PLACE
        #     0x021D1C4A  B   0x021D1D56  (no store -> 0) <- KEPT IN PLACE
        # Verified: nothing in ov3 branches to 0x021D1C46/48/4A.
        # ⚠️ 0x17BB IS a real card, so its test must survive -- the stub hands the flags
        # back to the caller's own BEQ, exactly as PART E does.
        BANISH_ARM = 0x021D1C44
        BANISH_ARM_NATIVE = bytes.fromhex("55488542")     # LDR R0,[PC,#0x154] ; CMP R5,R0
        BANISH_OTHER_CID = 0x17BB           # the real card whose test we displace
        # ov3 dead block 0x021B57EE (22 B, phantom 0x1789), based 2 B in for a 4-aligned pool
        # ⚠️ MUST gate on the DESTINATION ZONE. A GY-bound card runs the GY chain AND THEN
        # FALLS THROUGH into this one, so matching our cid unconditionally sent it to the
        # banish leaf 0x021D1D3E, whose `dest == 0x0F` test fails on a discard and then
        # STORES 0 to [sp+0x14] at 0x021D1D54 -- wiping the accept PART E had just set.
        # IN-GAME: discard/mill stopped triggering the moment PART G was added, and the
        # black-box recorder showed the resolver was never reached (entries == 0).
        # Base is 2 mod 4 on purpose: 18 B of code then a 4-aligned 1-word pool lands
        # exactly on the block end, fitting all 22 B.
        BANISH_STUB = 0x021B57EE
        BANISH_STUB_LEN = 22
        # The gate no longer fits one dead block once instrumented, so it spans two and
        # jumps between them (they are ~0x140 apart, well inside Thumb B's +-2KB).
        # ⚠️ PURE ov3 on purpose: 0x021D1300 runs in PUZZLES too, where ov41 evicts ov5, so
        # a BLX into the cave here would freeze the console on every puzzle.
        BANISH_DIAG = 0x021B56B8            # second dead block (16 B free)
        BANISH_DIAG_LEN = 16
        DIAG_DEST = 0x2A                    # scratch: last dest zone seen for OUR cid


        def _banish_stub(base: int) -> bytes:
            """Block A: route our cid to the diagnostic/gate in block B, else the native test.

            Returns with Z set for either our cid (when block B allows it) or 0x17BB, so the
            caller's own BEQ at 0x021D1C48 still routes both.
            """
            b = EffectBuilder()
            b.insn("LDR", "R0, [SP, #0x30]")
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R5, R1")
            b.insn("BEQ", "to_b")
            b.insn("SUB", f"R1, #0x{DONOR_CID - BANISH_OTHER_CID:X}")
            b.insn("CMP", "R5, R1")
            b.insn("BX", "LR")
            b.label("to_b")
            b.insn("NOP")
            body = b.assemble(base, pad="nop")
            # patch the placeholder NOP into an unconditional branch to block B
            idx = 7                                       # halfword index of the `nop`
            pc = base + idx * 2
            off = (BANISH_DIAG - (pc + 4)) >> 1
            assert -1024 <= off <= 1023, f"block A -> B out of B range: {off}"
            out = bytearray(body)
            struct.pack_into("<H", out, idx * 2, 0xE000 | (off & 0x7FF))
            assert len(out) <= BANISH_STUB_LEN, len(out)
            return bytes(out)


        def _banish_diag(base: int) -> bytes:
            """Block B: record the destination zone our cid was seen with, then gate on it.

            The recorded value is the whole point of this build. After banishing an Eclipse
            Wyvern from the GY, scratch[+0x2A] answers the question the savestates could not:
                0x0F  -> the relocation applier IS entered for a GY -> banished move and the
                         gate passed, so the failure is DOWNSTREAM (admission or dispatch)
                other -> our cid reaches this node only for other destinations
                0     -> our cid never reaches this node at all on a banish, i.e. the applier
                         is not the mover for GY -> banished and clause 2 needs another hook
            """
            b = EffectBuilder()
            b.ldr_const(2, ov5_cave.CAVE_EW_SCRATCH)
            b.insn("STRH", f"R0, [R2, #0x{DIAG_DEST:X}]")
            b.insn("CMP", "R0, #0xF")
            b.insn("BNE", "out")
            b.insn("CMP", "R5, R5")
            b.label("out")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        # --- PART I: admit the donor to the REAL banish-from-GY event gate ------------
        # Session 25. PART G was hooked on the wrong applier. A GY -> banished move does not
        # go through 0x021D1300 at all: it has its own mover
        #
        #     0x021C7118(r0 = side, r1 = &cardword, r2 = flags, r3 = facedown)
        #
        # which hardcodes BOTH zones into the word it builds (@0x021C7156 source = 0x0E,
        # @0x021C7178 dest = 0x0F) and posts by calling the register-prim 0x021D3168
        # DIRECTLY, with r0 = 0x404F0000 | (side << 31) | cid -- which decodes (against the
        # identical word built at 0x021D1D5C: bits 0..15 cid, 16..20 zone, bit 22, bits
        # 25..30 event code, bit 31 side) to zone 0x0F, event code 0x20.
        #
        # Traced by identifying the card that actually did the banishing from the savestates
        # instead of assuming a routine: rom_eclipse_wyvern.ml2 -> .ml3 shows Soul Release
        # 0x12F9 leaving the hand as 0x1859 moves GY -> banished. Soul Release is cls0[179],
        # resolver 0x02208D18, whose resolve loop is
        #     0x02234964 (pick) -> 0x021A25E8 (ref -> &word) -> 0x021C7098 -> 0x021C7118.
        #
        # THE GATE is a plain two-way compare -- not a sorted binary chain, so unlike PART E
        # there is no "terminal node of the interval" subtlety here:
        #     0x021C71BC  LDR  R0,[R4]              ; the card word
        #     0x021C71BE  LDR  R1,=0x17BB           ; Necroface           <- kept
        #     0x021C71C0  LSLS R0,#0x12 ; LSRS R0,#0x12   ; cid = w & 0x3FFF
        #     0x021C71C4  CMP  R0,R1
        #     0x021C71C6  BEQ  0x021C71CE           ; -> POST             <- kept
        #     0x021C71C8  LDR  R1,=0x1CF6           ; Cyber Ouroboros     <- DISPLACED
        #     0x021C71CA  CMP  R0,R1                                      <- DISPLACED
        #     0x021C71CC  BNE  0x021C71F8           ; else: move, no event <- KEPT IN PLACE
        # {0x17BB, 0x1CF6} is the same pair admitted by the 0x021D1D3E leaf on the other
        # applier -- the engine registers this trigger twice, once per mover.
        #
        # Register safety, checked on both exits:
        #   * r0 holds the cid and is LIVE afterwards (0x021C71DC) -- the stub never writes it;
        #   * r1 is dead on both exits (reloaded @0x021C71CE, re-set @0x021C71FC);
        #   * LR is free: 0x021C7118 pushed it and returns POP {...,PC}, and the code past the
        #     hook calls `bl` anyway.
        # Verified statically: NOTHING anywhere in ov3 branches to 0x021C71C8/CA/CC, so the
        # displaced pair is reachable only by fall-through.
        # ⚠️ ov3 DEAD CODE, never the ov5 cave: 0x021C7118 is shared engine code that also
        # runs in puzzles, where overlay 41 evicts ov5 and a BL into it freezes the console.
        BANISH_GATE = 0x021C71C8
        BANISH_GATE_NATIVE = bytes.fromhex("21498842")    # LDR R1,[PC,#0x84] ; CMP R0,R1
        OURO_CID = 0x1CF6                   # the real card whose test we displace
        # Released by PART G's retirement; based 2 B in so the assembler's literal pool is
        # 4-aligned. 20 B of the 22 B block.
        BANISH_GATE_STUB = 0x021B57F0
        BANISH_GATE_STUB_LEN = 20


        def _banish_gate_stub(base: int) -> bytes:
            """Return with Z set for Cyber Ouroboros OR the donor; the caller's BNE routes both.

            BX does not touch the flags, so the CMP that set them is handed straight back to
            `BNE 0x021C71F8` at 0x021C71CC.
            """
            assert base % 4 == 0, "literal pool needs a 4-aligned base"
            b = EffectBuilder()
            b.ldr_const(1, OURO_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "out")
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R0, R1")
            b.label("out")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        # --- PART H: remember the card clause 1 banished (clause 2's input) -----------
        # The 3DS reads it from desc[+0x16] -- recorded pick #1 of the descriptor pick array.
        # That works there because the 3DS runs clause 2 as a PHASE of the same resolver, so
        # it is the same descriptor. On the NDS the banish event builds a NEW descriptor, so
        # the value is kept in an ov5 slot keyed by side instead.
        PHASE_WORD = 0x0229AAFC             # +0x70 = the resolver phase (0x80 / 0x7F / 0x7E)
        # ⚠️⚠️ EVERY address called with `BLX Rm` MUST carry the THUMB BIT.
        # BLX takes the target instruction set from bit 0 of the register: an EVEN address
        # switches the core to ARM and executes garbage -- an instant freeze. Native code
        # reaches these with a Thumb `BL`, so the raw addresses are even. The only reason
        # 0x0221CD29 ever worked here is that a cls-record slot already carries the bit.
        # This single mistake caused the act-phase freezes previously blamed on gates and
        # candidate counters (0x021BABE8, 0x02243FA8, 0x021D269C, 0x0219A818 were all
        # BLX'd even). Use THUMB(...) for anything loaded into a register and BLX'd.
        def THUMB(addr: int) -> int:
            """Tag a function address for `BLX Rm` (bit 0 = stay in Thumb)."""
            assert addr % 2 == 0, f"{addr:#x} already carries the Thumb bit"
            return addr | 1


        PICK_GET = 0x0219C510               # -> &0x02299458[selected index]; takes NO args
        RECORDER_LEN = 0x160

        # --- clause 2's primitives (all verified against the NATIVE add-to-hand resolver
        #     0x02207EF5, whose phase chain is the NDS twin of the 3DS machine) ----------
        # ⚠️⚠️ 0x021C72CC IS THE **DECK** -> HAND MOVER, NOT A GENERAL ONE. Session 25 shipped
        # it and measured the result in-game: clause 2 triggered, the wrapper ran all four
        # phases, released the slot -- and the game opened a DECK SEARCH and shuffled, adding
        # nothing, because our card was in the banished zone. Disassembly confirms it: its one
        # search loop (0x021C732A..0x021C744C) walks `player + 0x304` with count `player+0x10`,
        # i.e. the Deck and only the Deck, and its own emit at 0x021C739C passes source zone
        # 0x0D. It is the primitive behind White Stone of Legend / Cross Porter, both of which
        # search the DECK. The session-22 note "it locates the card wherever it is" was wrong.
        # This is the THIRD time a mover turned out to be specific to one (source, destination)
        # pair -- see the KB fact event.gy_to_banished_mover.
        MOVE_TO_HAND_FROM_DECK = 0x021C72CC   # (side, &cardword) -- DECK only; kept as a warning
        # ⭐ The general zone-to-zone relocation emitter, and the ONLY one with both zones as
        # parameters. Native callers give the complete map (r1 = SOURCE, [sp+0] = DEST):
        #   0x021C69C0 hand->deck   0x021C6CA8 hand->GY     0x021C6AE4 banished->deck/extra
        #   0x021C726C banished->GY 0x021C72B2 banished->deck  0x021C739C deck->HAND
        # There is NO native banished->hand caller, so clause 2 builds one -- as a one-immediate
        # change from the native deck->hand call at 0x021C7384..0x021C739C, whose shape is:
        #   [sp+0] = 0x0B (dest zone), [sp+4] = player[side].hand_count (append index),
        #   [sp+8] = 0,  r0 = r3 = side, r1 = SOURCE zone, r2 = the packed ref.
        # ⚠️ It takes a REF -- (inst << 1) | side -- which is exactly what CAVE_EW_SCRATCH
        # already stores, so no card word has to be synthesised at all.
        RELOCATE = 0x021C69D0
        RELOCATE_LOG = 0x022391CC       # (0x26, 0) -- the tail 0x021C6A9C and 0x021C7258 both emit
        ZONE_HAND = 0x0B
        ZONE_BANISHED = 0x0F
        # player+0x0C is the hand count (KB ram.hand_is_zone_0x0B); the native deck->hand site
        # loads it from 0x0229ACA0 indexed by side * 0xB3C. Two literals beat a MULS here.
        HAND_COUNT_P0 = 0x0229ACA0
        HAND_COUNT_P1 = 0x0229ACA0 + 0xB3C
        DECLINE = 0x0225BF30            # (1 - side) then return 0x78
        # ⚠️⚠️ 0x021D269C IS **SHUFFLE THE DECK**, NOT A COMPLETION ROUTINE. Disassembled:
        # it loads the RNG state from [0x0229DD14+0x28], builds `r0 = 0x55 | (side ? 0x8000 : 0)`
        # and enqueues it through 0x021C3BC8 with the seed halves as arguments -- and command
        # 0x55 is the arm of the animation-command dispatcher (0x021C3C3C, `op = [0x02299B60]
        # & 0xFFF`, jump table at 0x021C3C5E) that calls the Fisher-Yates deck shuffle
        # 0x021A7B7C(side) over player+0x304. Passing the seed is exactly what a shuffle needs
        # so a replay/the other client reproduces the permutation.
        # It appears at the end of the native add-to-hand resolver 0x02207EF5 and of Gold
        # Sarcophagus 0x0221CD29 because BOTH OF THOSE SEARCH THE DECK, where shuffling is
        # correct. Clause 2 touches only the banished zone and the hand, so calling it made the
        # deck shuffle for no reason -- MEASURED in-game (same 28 cards, new order, our side
        # only) across three separate builds, and it survived removing the prompt, which is
        # what finally isolated it.
        # ⚠️ The same address is labelled "completion"/"EFFECT_DONE" in thunder_sea_horse,
        # w_nebula_meteorite and wonder_wand. Those are deck searches, so the call
        # is CORRECT there -- but the NAME is wrong everywhere and should not be copied again.
        SHUFFLE_DECK = 0x021D269C       # (side) -- enqueues command 0x55
        COMPLETE = SHUFFLE_DECK         # legacy alias; do NOT use for a non-deck effect
        PROMPT = 0x0219A818             # (side, id); id 0x33 is what the native add-to-hand
                                        #   resolver raises before returning 0x7E (0x022080BC)
        # ⚠️⚠️ 0x33 IS THE **DECK-SEARCH** MESSAGE, NOT A YES/NO. Enumerating every
        # 0x0219A818 call site by its r1 immediate gives id 0x33 exactly THREE users --
        # 0x022080BC (the shared add-from-Deck-to-hand resolver, i.e. White Stone of Legend /
        # Cross Porter), 0x02221018 and 0x0222BCB2 -- all of them Deck searches. Raising it
        # for clause 2 put the game into the Deck-search UI, and the deck was genuinely
        # SHUFFLED afterwards (measured: same multiset, different order, our side only,
        # rom_eclipse_wyvern.ml2 vs .ml3). It is also not a choice, which is why
        # clause 2 resolved as mandatory. Left here as the record of a dead end.
        PROMPT_ADD_TO_HAND = 0x33
        # ⭐ WHERE THE REAL YES/NO LIVES: NOT in the resolver at all -- it is the cls record's
        # ACTIVATION PROCEDURE. Per dispatch.cls_slot_roles, +0x0C slot3 is the activation
        # CONDITION (a code: 0 = cannot, 1 = needs slot2 to find a target, >=2 = unconditional;
        # DEFAULT 1 when the slot is 0) and +0x10 slot4 is the COST / ACTIVATION-PROCEDURE
        # step, run by the activation state machine at 0x02217F80. The repo already ships the
        # A/B pair proving it: gravekeepers_recruiter's
        #     Botanical Girl (OPTIONAL "you can") = (+04 0x02207EF5, +08 0, +0C 0x021F0821,
        #                                            +10 0x021E51E5, +14 0)
        #     Sangan          (MANDATORY)         = (+04 0x02207EF5, +08 0, +0C 0, +10 0, +14 0)
        # Our donor's record is the Sangan shape -- all four trailing slots 0 -- which is
        # exactly why clause 2 fired without asking.
        # ⚠️ COMPOSITION PROBLEM, unsolved: ONE cls2 record serves BOTH clauses, and clause 1
        # is MANDATORY while clause 2 is optional. Optionality cannot simply be switched on at
        # the record level without making clause 1 optional too. The way out is the same trick
        # the resolver already uses: point +0C/+10 at ov5 stubs that branch on desc[+3]
        # (0x0E -> the mandatory shape, 0x0F -> the optional shape). UNPROVEN -- verify that
        # slot3/slot4 receive a descriptor carrying the zone before building anything.
        WORD_SLOT = 0x2C                # scratch offset of the 4-byte card word we hand over

        # CAVE_EW_SCRATCH layout (48 B):
        #   +0x00..0x1F  8 slots x {u16 acting_instance, u16 banished_instance}
        #   +0x20 entries  +0x22 last phase  +0x24 progress  +0x26 acting  +0x28 event
        # Keyed by the ACTING copy's instance index (desc[+0xC]) rather than by side, so two
        # Eclipse Wyverns discarded in one action do not overwrite each other -- MEASURED:
        # a double discard banished two Dragons but the side-keyed slot kept only the last.
        # Both desc[+0xC] and the captured pick are RAW indices into the instance table
        # 0x0229C33C (stride 8, cid = word & 0x3FFF) -- verified against a live savestate.
        SLOTS = 8


        def _recorder(base: int) -> bytes:
            """Clause 1, UNCHANGED, plus one thing: remember which card it banished.

            ⚠️ MINIMAL BY DESIGN. Earlier versions replaced the resolver's act phase and
            re-implemented its gates; every one of those broke a working card. Clause 1 is
            confirmed working with the NATIVE resolver, so this touches nothing about it --
            it intercepts only phase 0x7E, copies the pick, then hands control to the native
            code with r0/r1 exactly as the invoker passed them.

            SHIPPING BUILD: the diagnostics are stripped. They lived at CAVE_EW_SCRATCH
            +0x20 entries / +0x22 phase / +0x24 progress / +0x26 acting / +0x28 event and are
            what solved the BLX-thumb-bit freeze, the wrong-mover bug and the deck shuffle --
            restore them (and scratch/read_ew_scratch.py reads them) before diagnosing anything
            here again. The per-instance table at +0x00..+0x1F is NOT diagnostic; it is
            clause 2's input and stays.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R7, R1, #0x0")
            b.insn("LDRB", "R6, [R4, #0x2]")
            b.ldr_const(5, PHASE_WORD)
            b.insn("LDR", "R5, [R5, #0x70]")
            b.insn("LDRB", "R3, [R4, #0x3]")
            b.insn("CMP", "R3, #0xF")
            b.insn("BEQ", "clause2")
            b.insn("CMP", "R5, #0x7E")
            b.insn("BNE", "native")
            b.call_addr(THUMB(PICK_GET), via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R0, R1")
            b.insn("LDRH", "R6, [R4, #0xC]")
            b.ldr_const(2, ov5_cave.CAVE_EW_SCRATCH)
            b.insn("MOV", "R3, #0x0")
            b.label("find")
            b.insn("LSL", "R5, R3, #0x2")
            b.insn("LDRH", "R1, [R2, R5]")
            b.insn("CMP", "R1, R6")
            b.insn("BEQ", "found")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "found")
            b.insn("ADD", "R3, #0x1")
            b.insn("CMP", f"R3, #0x{SLOTS:X}")
            b.insn("BLT", "find")
            b.insn("B", "native")
            b.label("found")
            b.insn("STRH", "R6, [R2, R5]")
            b.insn("ADD", "R5, #0x2")
            b.insn("STRH", "R0, [R2, R5]")
            b.label("native")
            b.call_addr(SARCO_RESOLVER, R4, R7, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("clause2")
            b.insn("CMP", "R5, #0x80")
            b.insn("BEQ", "c2_act")
            b.insn("CMP", "R5, #0x7F")
            b.insn("BEQ", "c2_ask")
            b.insn("CMP", "R5, #0x7E")
            b.insn("BEQ", "c2_do")
            b.insn("CMP", "R5, #0x64")
            b.insn("BEQ", "c2_fin")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("c2_act")
            b.insn("MOV", "R0, #0x7F")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("c2_ask")
            b.insn("LDRH", "R1, [R4, #0xC]")
            b.ldr_const(2, ov5_cave.CAVE_EW_SCRATCH)
            b.insn("MOV", "R3, #0x0")
            b.label("ask_find")
            b.insn("LSL", "R5, R3, #0x2")
            b.insn("LDRH", "R0, [R2, R5]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "ask_found")
            b.insn("ADD", "R3, #0x1")
            b.insn("CMP", f"R3, #0x{SLOTS:X}")
            b.insn("BLT", "ask_find")
            b.insn("MOV", "R0, #0x1")
            b.insn("SUB", "R0, R0, R6")
            b.call_addr(THUMB(DECLINE), via=R3)
            b.insn("MOV", "R0, #0x78")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("ask_found")
            b.insn("MOV", "R0, #0x7E")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("c2_do")
            b.insn("LDRH", "R1, [R4, #0xC]")
            b.ldr_const(2, ov5_cave.CAVE_EW_SCRATCH)
            b.insn("MOV", "R3, #0x0")
            b.label("do_find")
            b.insn("LSL", "R5, R3, #0x2")
            b.insn("LDRH", "R0, [R2, R5]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "do_found")
            b.insn("ADD", "R3, #0x1")
            b.insn("CMP", f"R3, #0x{SLOTS:X}")
            b.insn("BLT", "do_find")
            b.insn("MOV", "R0, #0x64")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("do_found")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R2, R5]")
            b.insn("ADD", "R5, #0x2")
            b.insn("LDRH", "R4, [R2, R5]")
            b.insn("STRH", "R0, [R2, R5]")
            b.insn("MOV", "R6, #0x1")
            b.insn("AND", "R6, R4")
            b.ldr_const(1, HAND_COUNT_P0)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "hc")
            b.ldr_const(1, HAND_COUNT_P1)
            b.label("hc")
            b.insn("LDR", "R5, [R1, #0x0]")
            b.ldr_const(7, THUMB(RELOCATE))
            b.insn("PUSH", "{R0, R1, R2}")
            b.insn("MOV", f"R0, #0x{ZONE_HAND:X}")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R5, [SP, #0x4]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", f"R1, #0x{ZONE_BANISHED:X}")
            b.insn("ADD", "R2, R4, #0x0")
            b.insn("ADD", "R3, R6, #0x0")
            b.insn("BLX", "R7")
            b.insn("POP", "{R0, R1, R2}")
            b.call_addr(THUMB(RELOCATE_LOG), 0x26, 0, via=R7)
            b.insn("MOV", "R0, #0x64")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("c2_fin")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")




        def _bl(src: int, dst: int) -> bytes:
            """ARMv4T two-halfword BL (Thumb-1 long branch-with-link)."""
            off = dst - (src + 4)
            assert -(1 << 22) <= off < (1 << 22), f"BL out of range: {off:#x}"
            hi = 0xF000 | ((off >> 12) & 0x7FF)
            lo = 0xF800 | ((off >> 1) & 0x7FF)
            return struct.pack("<HH", hi, lo)


        def _rows(ov: bytearray, base: int, count: int, stride: int) -> list[int]:
            return [struct.unpack_from("<H", ov, _off(base + i * stride))[0] for i in range(count)]


        def _insert_sorted(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                           record: tuple, drop_cid: int, label: str) -> None:
            """Count-neutral sorted insert: delete the phantom row, shift, write `record`."""
            keys = ([struct.unpack_from("<I", ov, _off(base + i * stride))[0] for i in range(count)]
                    if stride == 24 else _rows(ov, base, count, stride))
            new_cid = record[0]
            if new_cid in keys:
                print(f"{label}: 0x{new_cid:04X} already present (idempotent) -- skipped")
                return
            assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
            dst = keys.index(drop_cid)
            pos = sum(1 for k in keys if k < new_cid)
            if pos > dst:
                # the phantom sits BELOW the insert point: slide (dst, pos) DOWN one slot
                # and land at pos-1 (removing the phantom shifts everything after it left).
                blk = bytes(ov[_off(base + (dst + 1) * stride):_off(base + pos * stride)])
                ov[_off(base + dst * stride):_off(base + (pos - 1) * stride)] = blk
                pos -= 1
            else:
                # the phantom sits ABOVE: slide [pos, dst) UP one slot
                blk = bytes(ov[_off(base + pos * stride):_off(base + dst * stride)])
                ov[_off(base + (pos + 1) * stride):_off(base + (dst + 1) * stride)] = blk
            struct.pack_into(fmt, ov, _off(base + pos * stride), *record)
            print(f"{label}: dropped phantom 0x{drop_cid:04X} @{dst}, inserted 0x{new_cid:04X} @{pos} "
                  f"(count {count} unchanged)")


        def apply_effect(ov: bytearray) -> None:
            # -- PART A: register the ANY-LOCATION sent-to-GY trigger in the mask table.
            #    list30 must stay untouched: being in it would set [sp+0x18] and make the
            #    dispatcher SKIP the mask table entirely (0x021C80FE), which is exactly the
            #    field-only behaviour we are fixing.
            l30 = _rows(ov, LIST30_BASE, LIST30_COUNT, 2)
            assert DONOR_CID not in l30, \
                "donor is in list30 -- that arms the FIELD-only path and suppresses the mask table"
            assert all(l30[i] <= l30[i + 1] for i in range(LIST30_COUNT - 1)), "list30 disturbed"
            print(f"A  list30 @0x{LIST30_BASE:08X} UNTOUCHED ({LIST30_COUNT} entries, still sorted) "
                  f"-- donor absent, so the mask table IS consulted")
            _insert_sorted(ov, MASK_BASE, MASK_COUNT, MASK_STRIDE, MASK_FMT,
                           MASK_NEW, MASK_DROP_PHANTOM,
                           f"A  leave-mask (0x{MASK_SENT_TO_GY:04X} = sent-to-GY, any zone)")

            # -- PART B: cls2 record (the picker + banish action)
            _insert_sorted(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, "<6I",
                           CLS2_NEW, CLS2_DROP_PHANTOM, "B  cls2")

            # -- PART C: criteria row (the candidate pool)
            _insert_sorted(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT,
                           POP_NEW, POP_DROP_PHANTOM, "C  criteria")

            # -- PART F WITHDRAWN: see the constants. The empty-deck guard now lives in the
            #    PART H wrapper instead; the native condition refused the event off-field.

            # -- PART E: admit the donor to the hardcoded sent-to-GY event gate.
            #    Without this the event is never posted at all and A-C are inert off-field.
            native = bytes(ov[_off(GATE_ARM):_off(GATE_ARM) + len(GATE_ARM_NATIVE)])
            if native == _bl(GATE_ARM, GATE_STUB):
                print("E  GY-event gate already repointed (idempotent) -- skipped")
                return
            assert native == GATE_ARM_NATIVE, \
                f"E: the 0x16F5 arm is not native at 0x{GATE_ARM:08X} (got {native.hex()})"

            stub = _gate_stub(GATE_STUB)
            assert_thumb1_only(stub, GATE_STUB)
            ov[_off(GATE_STUB):_off(GATE_STUB) + GATE_STUB_LEN] = stub

            patch = _bl(GATE_ARM, GATE_STUB)
            assert_thumb1_only(patch, GATE_ARM)
            ov[_off(GATE_ARM):_off(GATE_ARM) + len(patch)] = patch
            # -- PART G: admit the donor to the BANISH event gate (clause 2's prerequisite).
            #    ⚠️ The first version routed our cid to the banish leaf UNCONDITIONALLY, and
            #    a GY-bound card falls through into this same chain, so the leaf's
            #    `dest == 0x0F` test failed and STORED 0 over PART E's accept -- silently
            #    killing the discard/mill trigger. The stub now gates on the dest zone.
            if not BYPASS_G:
                bnative = bytes(ov[_off(BANISH_ARM):_off(BANISH_ARM) + 4])
                if bnative == _bl(BANISH_ARM, BANISH_STUB):
                    print("G  banish gate already repointed (idempotent) -- skipped")
                else:
                    assert bnative == BANISH_ARM_NATIVE, \
                        f"G: banish node not native at 0x{BANISH_ARM:08X} (got {bnative.hex()})"
                    bstub = _banish_stub(BANISH_STUB)
                    assert len(bstub) <= BANISH_STUB_LEN, \
                        f"G: stub is {len(bstub)} B, block holds {BANISH_STUB_LEN}"
                    assert_thumb1_only(bstub, BANISH_STUB)
                    ov[_off(BANISH_STUB):_off(BANISH_STUB) + len(bstub)] = bstub
                    bdiag = _banish_diag(BANISH_DIAG)
                    assert len(bdiag) <= BANISH_DIAG_LEN, f"G: diag {len(bdiag)} B > {BANISH_DIAG_LEN}"
                    assert_thumb1_only(bdiag, BANISH_DIAG)
                    ov[_off(BANISH_DIAG):_off(BANISH_DIAG) + len(bdiag)] = bdiag
                    bpatch = _bl(BANISH_ARM, BANISH_STUB)
                    assert_thumb1_only(bpatch, BANISH_ARM)
                    ov[_off(BANISH_ARM):_off(BANISH_ARM) + 4] = bpatch
                    print(f"G  banish gate: 0x{BANISH_ARM:08X} BL -> stub 0x{BANISH_STUB:08X} "
                          f"({len(bstub)} B, dest-zone gated); 0x{DONOR_CID:04X} reaches "
                          f"the banish leaf 0x021D1D3E ONLY on a real banish")

            # -- PART I: admit the donor to the banish-from-GY event gate inside the mover
            #    0x021C7118. This is the gate that is actually ON the GY -> banished path;
            #    PART G's was on 0x021D1300, which that transition never enters.
            inative = bytes(ov[_off(BANISH_GATE):_off(BANISH_GATE) + 4])
            if inative == _bl(BANISH_GATE, BANISH_GATE_STUB):
                print("I  banish-from-GY gate already repointed (idempotent) -- skipped")
            else:
                assert inative == BANISH_GATE_NATIVE, \
                    f"I: banish gate not native at 0x{BANISH_GATE:08X} (got {inative.hex()})"
                istub = _banish_gate_stub(BANISH_GATE_STUB)
                assert len(istub) <= BANISH_GATE_STUB_LEN, \
                    f"I: stub is {len(istub)} B, block holds {BANISH_GATE_STUB_LEN}"
                assert_thumb1_only(istub, BANISH_GATE_STUB)
                ov[_off(BANISH_GATE_STUB):_off(BANISH_GATE_STUB) + len(istub)] = istub
                ipatch = _bl(BANISH_GATE, BANISH_GATE_STUB)
                assert_thumb1_only(ipatch, BANISH_GATE)
                ov[_off(BANISH_GATE):_off(BANISH_GATE) + 4] = ipatch
                print(f"I  banish-from-GY gate: 0x{BANISH_GATE:08X} BL -> stub "
                      f"0x{BANISH_GATE_STUB:08X} ({len(istub)} B); 0x021C7118 now posts the "
                      f"zone-0x0F / event-0x20 register-prim for 0x{DONOR_CID:04X} as well as "
                      f"0x{OURO_CID:04X} / 0x{BANISH_OTHER_CID:04X}")

            print(f"E  GY-event gate: 0x{GATE_ARM:08X} BL -> stub 0x{GATE_STUB:08X} "
                  f"({GATE_STUB_LEN} B in ov3 dead block 0x021B591E); the terminal node "
                  f"for this interval now admits 0x{DONOR_CID:04X}")

        stubs = ((ov5_cave.CAVE_EW_RECORD, _recorder(ov5_cave.CAVE_EW_RECORD), "pick recorder"),
                 (ov5_cave.CAVE_EW_ATTRH, _attr_handler(ov5_cave.CAVE_EW_ATTRH), "LIGHT|DARK criteria handler"))
        assert_thumb1_only(stubs[0][1], stubs[0][0])

        def install(rom, view):
            apply_effect(view.buf)

        def check_ov(rom, ov):
          h = _attr_handler(ov5_cave.CAVE_EW_ATTRH)
          assert ov5_cave.read_cave(rom, ov5_cave.CAVE_EW_ATTRH, len(h)) == h, "C2 attribute handler missing/wrong"
          ov = bytearray(ov)

          # A: the leave-mask registration, and list30 left alone
          l30 = _rows(ov, LIST30_BASE, LIST30_COUNT, 2)
          assert all(l30[i] <= l30[i + 1] for i in range(LIST30_COUNT - 1)), "list30 no longer sorted"
          assert DONOR_CID not in l30, \
              "donor is in list30 -- it would arm the FIELD-only path and suppress the mask table"
          mk = _rows(ov, MASK_BASE, MASK_COUNT, MASK_STRIDE)
          assert mk.count(DONOR_CID) == 1, f"expected exactly 1 mask row, got {mk.count(DONOR_CID)}"
          assert MASK_DROP_PHANTOM not in mk, "mask-table phantom still present -- count is wrong"
          assert all(mk[i] <= mk[i + 1] for i in range(MASK_COUNT - 1)), "mask table lost its sort"
          row = struct.unpack_from(MASK_FMT, ov, _off(MASK_BASE + mk.index(DONOR_CID) * MASK_STRIDE))
          assert row == MASK_NEW, f"mask row wrong: {[hex(x) for x in row]}"

          # B: cls2 -- present, correct, sorted, count unchanged
          cids = [struct.unpack_from("<I", ov, _off(CLS2_BASE + i * CLS2_STRIDE))[0]
                  for i in range(CLS2_COUNT)]
          assert cids.count(DONOR_CID) == 1, f"expected exactly 1 cls2 record, got {cids.count(DONOR_CID)}"
          assert CLS2_DROP_PHANTOM not in cids, "phantom still present -- count is wrong"
          assert all(cids[i] <= cids[i + 1] for i in range(CLS2_COUNT - 1)), "cls2 lost its sort"
          rec = struct.unpack_from("<6I", ov, _off(CLS2_BASE + cids.index(DONOR_CID) * CLS2_STRIDE))
          assert rec == CLS2_NEW, f"cls2 record wrong: {[hex(x) for x in rec]}"

          # C: criteria row -- present, correct, sorted, count unchanged
          pc = _rows(ov, POP_BASE, POP_COUNT, POP_STRIDE)
          assert pc.count(DONOR_CID) == 1, f"expected exactly 1 criteria row, got {pc.count(DONOR_CID)}"
          assert POP_DROP_PHANTOM not in pc, "phantom still present -- count is wrong"
          assert all(pc[i] <= pc[i + 1] for i in range(POP_COUNT - 1)), "criteria registry lost its sort"
          row = struct.unpack_from(POP_FMT, ov, _off(POP_BASE + pc.index(DONOR_CID) * POP_STRIDE))
          assert row == POP_NEW, f"criteria row wrong: {[hex(x) for x in row]}"
          assert (row[4] >> 8) >> 3 == 1 and (row[4] >> 8) & 7 == 0, "race/attribute nibbles wrong"
          assert (row[4] & 0xFF) & 0xC0 == 0x40 and ((row[4] & 0xFF) & 0x3F) >> 2 == 7, \
              "level bound is not the 'Level >= 7' form"

          # E: the sent-to-GY event gate -- the whole card is inert off-field without it
          arm = bytes(ov[_off(GATE_ARM):_off(GATE_ARM) + 4])
          assert arm == _bl(GATE_ARM, GATE_STUB), \
              f"the gate node is not repointed at the stub: {arm.hex()}"
          stub = bytes(ov[_off(GATE_STUB):_off(GATE_STUB) + GATE_STUB_LEN])
          assert stub == _gate_stub(GATE_STUB), f"gate stub bytes wrong: {stub.hex()}"
          assert_thumb1_only(stub, GATE_STUB)
          # the caller's own BEQ/B pair is REUSED by the stub (it returns with Z set from
          # the displaced 0x1828 compare), so it must still be stock
          assert bytes(ov[_off(0x021D14D6):_off(0x021D14D6) + 4]) == bytes.fromhex("07d072e2"), \
              "the kept BEQ 0x021D14E8 / B 0x021D19C0 pair was disturbed"
          # (PART G is RETIRED -- it gated a chain a GY -> banished move never enters.)

          # I: the banish-from-GY event gate, inside the mover 0x021C7118 itself
          igate = bytes(ov[_off(BANISH_GATE):_off(BANISH_GATE) + 4])
          # dragon_rulers fronts this site: its ov3 stub answers for the ruler cids and calls OUR stub
          # for every other cid (flags returned untouched), so the gate still reaches BANISH_GATE_STUB.
          from otn_enhanced.cards import dragon_rulers as _dr
          fronted = code_reaches(rom, BANISH_GATE, BANISH_GATE_STUB)   # through dragon_rulers' H6 or any later front
          assert igate == _bl(BANISH_GATE, BANISH_GATE_STUB) or fronted, \
              f"the banish-from-GY gate is not repointed at the stub: {igate.hex()}"
          istub = bytes(ov[_off(BANISH_GATE_STUB):_off(BANISH_GATE_STUB) + BANISH_GATE_STUB_LEN])
          assert istub == _banish_gate_stub(BANISH_GATE_STUB), \
              f"banish-gate stub bytes wrong: {istub.hex()}"
          assert_thumb1_only(istub, BANISH_GATE_STUB)
          # the kept halves of the native gate: Necroface's test before it and the BNE after
          assert bytes(ov[_off(0x021C71BC):_off(0x021C71BC) + 4]) == bytes.fromhex("20682349"), \
              "the kept LDR R0,[R4] / LDR R1,=0x17BB pair was disturbed"
          assert bytes(ov[_off(0x021C71CC):_off(0x021C71CC) + 2]) == bytes.fromhex("14d1"), \
              "the kept BNE 0x021C71F8 was disturbed"
          # and the mover's hardcoded zones must still be GY -> banished
          assert bytes(ov[_off(0x021C7156):_off(0x021C7156) + 6]) == bytes.fromhex("0e2080020143"), \
              "0x021C7118 source-zone (0x0E) encoding drifted"
          assert bytes(ov[_off(0x021C7178):_off(0x021C7178) + 6]) == bytes.fromhex("1e2080040843"), \
              "0x021C7118 dest-zone (0x0F) encoding drifted"

          # and the 0x16F5 arm must be back to STOCK: an earlier build wrongly repointed
          # it, which did nothing because a sorted binary search never routes 0x1859 there
          assert bytes(ov[_off(0x021D147A):_off(0x021D147A) + 6]) == \
              bytes.fromhex("b630854252d0"), "the 0x16F5 arm is not stock"

          print(f"PASS eclipse_wyvern: leave-mask 0x{MASK_SENT_TO_GY:04X} (sent-to-GY any zone), list30 untouched, "
                f"cls2 +04 = 0x{rec[1]:08X}, criteria row = Deck/Dragon/Level>=7/LIGHT|DARK (ov5 C2), both tables sorted")
          return True

        def check_fn(c, rom, view):
            try:
                check_ov(rom, bytearray(view.buf))
                c.ok(True, "Eclipse Wyvern: mask row, cls2, criteria row, gate stubs and their kept neighbours")
            except AssertionError as e:
                c.ok(False, f"Eclipse Wyvern: {e}")

        return Compiled(stubs, installs=(install,), checks=(check_fn,))


wyvern_effects = sent_to_graveyard_from_anywhere_banish_light_or_dark_dragon_level_7_or_higher_from_deck_and_add_it_later

SPEC = card(0x1859, wyvern_effects())

PROPS = card_props("LIGHT", "Dragon", level=4, atk=1600, defense=1000)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_eclipse_wyvern.nds")

# Names the KB proof dispatch.ov3_switch_stubs_must_register reads off this module.
DONOR_CID = 0x1859
GATE_STUB, GATE_STUB_LEN = 0x021B5920, 24
GATE_ACCEPT, GATE_ACCEPT_LEAF = 0x021D1526, 0x021D19BE


def _gate_stub(base: int = GATE_STUB) -> bytes:
    from otn_enhanced.effects.common import Ov
    from otn_enhanced.rom.overlay_io import load_overlay3
    _, ovb = load_overlay3(dsl.SRC)
    view = Ov(bytearray(ovb))
    SPEC.compile(view).installs[0](None, view)
    return view.blob(GATE_STUB, GATE_STUB_LEN)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

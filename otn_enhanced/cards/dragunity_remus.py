"""Dragunity Remus (WIND / Dragon / Tuner / Level 2 / 800 / 800) on Petit Dragon 0x106E.

See notes/dragunity-remus-findings.md for the printed text; clauses C1 (Synchro Material restriction), C3 (GY
self-Summon, banished if it leaves, Extra-Deck lock) and C4 (discard: add "Dragon Ravine"; once per turn) are built.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class named_spell_search_hand_discard_gy_self_summon_banish_on_leave_dragunity_synchro_material_lock:
    """Dragunity Remus (Petit Dragon 0x106E, a Tuner): 'Discard this card; add 1 "Dragon Ravine" from your Deck (once per turn);
    from the GY Special Summon this card by ...; banished if it leaves; cannot be used as Synchro Material except for a "Dragunity"
    Synchro.' ONE cls2 record serves every clause (C3's splitters switch on desc[+3] and chain into the C4 once-per-turn stubs):
    named-Deck-search criteria row (aux = the target cid), hand-effect list (OFFER gate) over phantom 0x0EB2, "Dragunity" set code
    by DISPLACING Trident 0x2180, GY-action registry phantom row converted, the shared summon-rider hook arm, and a Tuner-side
    material gate chained through Junk Speeder's. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        import ndspy.rom
        from otn_enhanced.effects.common import ARM9_BASE, insert_row
        from otn_enhanced.effects.common import bl as _thumb_bl
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        ENABLE_C4 = True    # "You can only use each effect ... once per turn" (on C2)
        ENABLE_C1 = True    # "Cannot be used as Synchro Material, except ... Dragunity"
        ENABLE_C3 = True    # GY self-SS + banish-on-leave + Extra-Deck lock

        from otn_enhanced.effects.common import ARM9_BASE
        RAVINE_CID = 0x2359         # "Dragon Ravine" -- the search target

        # --- templates, pinned stock ------------------------------------------------
        FUSION_SAGE = 0x1308        # criteria row shape: a NAMED SPELL Deck search
        BIRDFACE = 0x139D           # cls2 shape: main 0x02207EF5 + cond 0x021F0821
        WHITE_STONE = 0x1EAA        # second witness for main 0x02207EF5

        # ===========================================================================
        # PART B -- cls2 record
        # ===========================================================================
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 24
        CLS_FMT = "<HHIIIII"        # {cid u16, pad u16, +04 main, +08, +0C cond, +10 res, +14}
        CLS2_PHANTOM = 0x0E1D       # phantom (no card_prop), claimed nowhere -- dropped for the donor

        MAIN_ADD_ONE_FROM_DECK = 0x02207EF5   # "add 1 card matching my criteria row, Deck -> hand"
        COND_FLOODGATE_CANDS = 0x021F0821     # floodgate + "candidates >= 1" via the criteria row
        RES_DISCARD_SELF = 0x021E6FD9         # discard self by desc[+0xC]; cid-blind

        CLS2_SLOTS = (MAIN_ADD_ONE_FROM_DECK, 0x00000000, COND_FLOODGATE_CANDS,
                      RES_DISCARD_SELF, 0x00000000)
        CLS2_RECORD = (DONOR_CID, 0x0000) + CLS2_SLOTS

        # Birdface's stock record -- the same main + cond, with a battle-destroy cost.
        BIRDFACE_CLS2 = (BIRDFACE, 0x0000, MAIN_ADD_ONE_FROM_DECK, 0x00000000,
                         COND_FLOODGATE_CANDS, 0x021E51E5, 0x00000000)

        # The six cids main 0x02207EF5 special-cases; the donor must not be one of them.
        MAIN_SPECIAL_CASES = (0x200B, 0x2049, 0x220C, 0x23CA, 0x23E4, 0x24E1)
        # The three cids cond 0x021F0820 special-cases (they need > 1 candidate).
        COND_SPECIAL_CASES = (0x1FC9, 0x2049, 0x2410)

        # ===========================================================================
        # PART C -- criteria (populate) row
        # ===========================================================================
        POP_BASE, POP_COUNT, POP_STRIDE = 0x022713C4, 0x56C, 12
        POP_FMT = "<HHII"           # {cid u16, aux u16, handler u32, word u32}
        POP_PHANTOM = 0x0E3D        # phantom (no card_prop), claimed nowhere -- dropped for the donor's row

        NAMED_DECK_SELECTOR = 0x0223D075   # aux = TARGET CID; single-zone Deck builder 0x0223BC3C
        CRIT_SPELL = 0x00000004            # low bits = card-type mask; bit 2 = SPELL

        POP_RECORD = (DONOR_CID, RAVINE_CID, NAMED_DECK_SELECTOR, CRIT_SPELL)
        # Fusion Sage's stock row: the same handler + the same SPELL word, naming Polymerization.
        FUSION_SAGE_POP = (FUSION_SAGE, 0x12E5, NAMED_DECK_SELECTOR, CRIT_SPELL)

        # ===========================================================================
        # PART A -- ARM9 hand-effect cid list (the OFFER gate)
        # ===========================================================================
        HANDFX_LIST = 0x0209BC4E    # sorted u16 cids (Kuriboh, D.D. Crow, Thunder Dragon, Captain Gold, ...)
        HANDFX_COUNT = 0x1E         # `movs r2,#0x1E` @0x02023550 and @0x02023540 (dead thunk 0x0202353C)
        HANDFX_POOLS = (0x0202356C, 0x02023544)   # the only two u32 literals holding the list address
        HANDFX_COUNT_IMM = 0x02023550
        HANDFX_PHANTOM = 0x0EB2     # the LAST free phantom in this list (0x1B42 is spent by thunder_sea_horse)

        # ===========================================================================
        # PART D -- "Dragunity" set-code membership (a DISPLACEMENT, not an insert)
        # ===========================================================================
        # Set code 0x4A: has_set_code ptr table 0x0209D0D8[0x4A] -> thunk 0x02023DFD, whose
        # body is the standard `ldr r1,=list ; ldr r3,=bsearch ; movs r2,#N ; bx r3`.
        #
        # *** THIS LIST CANNOT GROW, SO A NEW MEMBER COSTS AN OLD ONE. ***  All 21 entries
        # are REAL cards (no phantom), and there is no slack anywhere in the set-code region:
        # the lists are packed end-to-end, every apparent gap is another cid list belonging to
        # a differently-shaped consumer thunk, and the 128 B at 0x0209D058 (between the last
        # list and the pointer table) is a live {u16 cid, u16 group} table read via thunk
        # 0x02023804.  Growing by shifting a neighbour is out because ELEVEN shipped modules
        # hardcode the neighbouring bases (Watt 0x0209CBEA, Karakuri 0x0209CC16 forward; AoJ
        # 0x0209CB96, X-Saber 0x0209CB6E, T.G. 0x0209CB48 backward).  Relocating the list to
        # the ov5 cave is WRONG -- all 12 BL callers of the thunk are in ov3, which is resident
        # in every duel mode, while ov5 is evicted by ov41 in a puzzle, so the bsearch would
        # read overlay-41 data and return silent wrong answers.  And the appended ARM9 cave is
        # FALSIFIED: its canary was run and freezes on entering a duel.
        #
        # So: the white_dragon_ninja / Sazank precedent -- swap one real card out, keep
        # the base AND the count immediate untouched, keep the array strictly sorted.
        #
        # DISPLACED: Dragunity Knight - Trident 0x2180 (USER'S CHOICE).  A Level 10
        # Extra-Deck Synchro that no "Dragunity" test can reach -- it cannot be added from the
        # Deck, cannot be equipped, and every GY-targeting Dragunity effect filters "Level 3 or
        # lower Dragon".  It loses only its contribution to Dux's "gains 200 ATK for each
        # 'Dragunity' card you control" count.  It keeps its own effect, its Synchro materials
        # and its Extra-Deck presence -- ONLY set-code membership is given up.
        DRAGUNITY_THUNK = 0x02023DFC        # `01 49 02 4b 15 22 18 47`
        DRAGUNITY_COUNT_IMM = 0x02023E00    # `movs r2,#0x15` -- read live, never assumed
        DRAGUNITY_POOL = 0x02023E04         # the u32 literal holding the list base
        DRAGUNITY_LIST = 0x0209CBC0
        DRAGUNITY_THUNK_SIG = bytes.fromhex("0149024b15221847")
        DISPLACED_CID = 0x2180              # Dragunity Knight - Trident -- gives up membership
        # The stock 21, so the displacement can be proven to cost exactly one card.
        DRAGUNITY_STOCK = (0x20C4, 0x20C5, 0x20C6, 0x20C7, 0x20C8, 0x20DE, 0x20EB, 0x2164,
                           0x216F, 0x2170, 0x2171, 0x2172, 0x2180, 0x220C, 0x220D, 0x220E,
                           0x220F, 0x221B, 0x2356, 0x2357, 0x2358)

        # ===========================================================================
        # PART F -- C4: "You can only use each effect ... once per turn"
        # ===========================================================================
        # The engine models a per-NAME once-per-turn as an ATTACHED-EFFECT NODE on the
        # per-turn log (pseudo-zone 0x0B), which auto-expires at turn end.  The matched
        # pair is dispatch.turnlog_once_per_turn_pair, and BOTH halves are cid-generic --
        # they read the cid out of the descriptor, so a donor does not fall into a
        # do-nothing default arm:
        #
        #   POST   0x021D2584(player, kid, kind, 0)   -> node {key=kid, kind} on (p, 0x0B)
        #   QUERY  0x021A14E8(player, 0x0B, kid, kind) -> nonzero iff already posted
        #
        # Pot of Duality 0x2321 is the native model: its act-cond 0x02203259 opens with
        # exactly `ldrb r0,[r5,#2] ; mov r1,#0xB ; ldrh r2,[r5] ; mov r3,#1 ; bl 0x021A14E8`.
        #
        # ⚠️ A per-SLOT latch (key 0x0FB6) is NOT usable here: Remus discards himself as
        # the cost, so there is no surviving slot to carry the flag.  It must be per-name.
        #
        # WHY TWO SHIMS AND NOT A DATA ROW.  The QUERY has to run BEFORE the native cond,
        # and the POST has to run ALONGSIDE the native discard-self cost.  Scanned every
        # non-null callback slot across all four cls tables and disassembled
        # each for BL targets: ZERO functions call both {0x021D2584, 0x021E8E74} and
        # {0x021C6DB4, 0x021E6FD8}.  So the cost needs a shim.  (The ignition-cond
        # registry 0x0226FAFC would supply the cond half as pure data via the pair
        # {0x021F0821, 0x021F6DD9} -- Gather Your Mind's wiring -- but its reachability on
        # the HAND-IGNITION path is unproven, and since the cave is already open for the
        # cost, a second shim is cheaper than an unproven data route plus a phantom.)
        #
        # Both shims gate on IS_RESOLVE_CTX first: the resolve/replay pass must not deny
        # or re-post its own activation.  This is Pot of Duality's own structure, and the
        # same guard 0x021F6DD8 and 0x021E8E74 use internally.
        IS_RESOLVE_CTX = 0x021D2B88   # nonzero in resolve/replay context
        TURNLOG_QUERY = 0x021A14E8    # (p, 0x0B, kid, kind) -> nonzero iff on this turn's log
        NODE_ATTACH = 0x021D2584      # (p, kid, kind, 0) -> attach {key=kid, kind} to (p, 0x0B)
        TURNLOG_KIND = 1              # kind 1 = card/effect activation

        C4_COND_ADDR = ov5_cave.CAVE_DR_COND
        C4_COND_RESERVE = 0x40
        C4_RES_ADDR = ov5_cave.CAVE_DR_RES
        C4_RES_RESERVE = 0x40

        # With C4 on, the cls2 record's cond and res point into the ov5 cave, which is
        # NOT resident in a puzzle (ov41 shares its base).  C2's data path is untouched.
        CLS2_RECORD_C4 = (DONOR_CID, 0x0000, MAIN_ADD_ONE_FROM_DECK, 0x00000000,
                          C4_COND_ADDR | 1, C4_RES_ADDR | 1, 0x00000000)


        def _build_c4_cond() -> bytes:
            """Act-cond shim: deny a second activation this turn, else chain the native cond.

            shim(ctx, arg1):
              if IS_RESOLVE_CTX(ctx):                       goto native
              if TURNLOG_QUERY([ctx+2], 0xB, [ctx+0], 1):   return 0
              native: return 0x021F0820(ctx, arg1)
            """
            b = EffectBuilder()
            b.prologue([R4, R5])
            b.insn("ADD", "R5, R0, #0x0")        # r5 = ctx
            b.insn("ADD", "R4, R1, #0x0")        # r4 = arg1, passed through
            b.call_addr(IS_RESOLVE_CTX)
            b.if_ne(R0, 0, "native")
            b.insn("LDRB", "R0, [R5, #0x2]")     # player
            b.insn("MOV", "R1, #0xB")            # pseudo-zone 0x0B = the per-turn log
            b.insn("LDRH", "R2, [R5, #0x0]")     # kid -- read from the descriptor, not a literal
            b.insn("MOV", "R3, #0x1")            # TURNLOG_KIND
            b.call_addr(TURNLOG_QUERY)
            b.if_ne(R0, 0, "deny")
            b.label("native")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R4, #0x0")
            b.call_addr(COND_FLOODGATE_CANDS & ~1)
            b.insn("POP", "{R4, R5, PC}")
            b.label("deny")
            b.epilogue(0)
            code = b.assemble(C4_COND_ADDR)
            assert len(code) <= C4_COND_RESERVE,         f"C4 cond shim {len(code)}B exceeds reserve 0x{C4_COND_RESERVE:X}"
            assert_thumb1_only(code, C4_COND_ADDR)
            return code


        def _build_c4_res() -> bytes:
            """Cost shim: stamp the once-per-turn node, then chain the native discard-self.

            shim(ctx):
              if not IS_RESOLVE_CTX(ctx):
                  NODE_ATTACH([ctx+2], [ctx+0], 1, 0)
              return 0x021E6FD8(ctx)

            ⚠️ The stamp MUST happen at ACTIVATION, not at resolution
            (dispatch.once_per_turn_must_stamp_at_activation) -- this is the cost slot,
            which is the activation-time hook.
            """
            b = EffectBuilder()
            b.prologue([R4])
            b.insn("ADD", "R4, R0, #0x0")        # r4 = ctx
            b.call_addr(IS_RESOLVE_CTX)
            b.if_ne(R0, 0, "chain")
            b.insn("LDRB", "R0, [R4, #0x2]")     # player
            b.insn("LDRH", "R1, [R4, #0x0]")     # kid
            b.insn("MOV", "R2, #0x1")            # TURNLOG_KIND
            b.insn("MOV", "R3, #0x0")
            b.call_addr(NODE_ATTACH)
            b.label("chain")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(RES_DISCARD_SELF & ~1)
            b.insn("POP", "{R4, PC}")
            code = b.assemble(C4_RES_ADDR)
            assert len(code) <= C4_RES_RESERVE,         f"C4 res shim {len(code)}B exceeds reserve 0x{C4_RES_RESERVE:X}"
            assert_thumb1_only(code, C4_RES_ADDR)
            return code


        # ===========================================================================
        # PART G -- C1: "Cannot be used as Synchro Material, except for the Synchro
        #               Summon of a \"Dragunity\" monster"
        # ===========================================================================
        # Remus is a TUNER, and the Synchro driver 0x02249C60 sends the Tuner material to
        # OUTER 0x022485B4 and every non-Tuner to THIRD 0x02248A88
        # (synchro.third_pred_is_the_nontuner_caller).  So the gate is OUTER's own call
        # into the INNER material predicate -- `bl 0x0224829C` @0x022485D8, which is
        # TUNER-ONLY BY CONSTRUCTION and therefore needs no is-a-Tuner test of its own
        # (synchro.tuner_gate_hook by Junk Speeder).
        #
        # At that site r0 = the SYNCHRO's cid, r1/r2/r3 = INNER's other arguments, and the
        # MATERIAL's cid comes from 0x021A3320(r1, r2) -- the same accessor OUTER itself
        # uses at 0x022485CA, so this introduces no new way of resolving a material.
        #
        # ⚠️ THE SITE IS SHARED, AND IT IS THE ONLY ONE.  INNER has exactly two callers and
        # the other is the non-Tuner half (owned by azure_eyes); 0x022482B2 /
        # 0x022482B6 are boggart_knight's and shooting_quasar's and run for
        # every material of every Synchro; the four driver call sites are azure_eyes'.
        # junk_speeder was at 0x022485D8 first.  So the two gates CHAIN, the way
        # Boggart and Quasar chain at 0x022482B2/0x022482B6:
        #
        #     0x022485D8  ->  CAVE_JSP_TUNER  ->  CAVE_DR_C1  ->  INNER 0x0224829C
        #
        # built by whichever patch applies second (junk_speeder.chain_tuner_gate, and
        # its apply_tuner_gate adopts a foreign hook as its next link).  Junk Speeder's own
        # rule is byte-identical either way -- only the address it delegates the base
        # verdict to moves.  In the single-card ROM, where junk_speeder is not applied,
        # this stub takes the site directly and calls INNER itself.
        #
        # ⚠️ The deny-key route was NOT available: synchro.material_embargo_deny_keys' five
        # keys are the "summoned by X cannot be material" riders, key 5 (the only
        # donor-independent one) belongs to tour_guide, and keys 1-4 are chained in
        # imm8 pairs -- donor 0x106E is 0x1205 from key 2 and 0x12B1 from key 4.
        MATERIAL_CID_OF = 0x021A3320    # (arg1, arg2) -> the material's cid; PURE (no stores)
        INNER_PRED = 0x0224829C         # the INNER material predicate this gate replays
        TUNER_HOOK_SITE = 0x022485D8    # OUTER's `bl 0x0224829C` -- the Tuner caller
        DRAGUNITY_THUNK_T = 0x02023DFD  # has_set_code[0x4A](cid) -> bool, Thumb

        C1_ADDR = ov5_cave.CAVE_DR_C1
        C1_RESERVE = 0x60


        def _build_c1_gate() -> bytes:
            """(r0 = Synchro cid, r1, r2, r3) -> INNER's verdict, denied when the material
            is Remus and the Synchro is not a "Dragunity".

            Every other material, and every other Synchro, gets INNER's verdict returned
            completely unchanged.  Mirrors junk_speeder.build_tuner_gate's ABI
            exactly, including restoring r1/r2/r3 on the way out -- INNER preserves r1-r7
            via `push {r1-r7,lr}`, so a drop-in replacement must too.
            """
            b = EffectBuilder()
            b.prologue([R4, R5, R6, R7])
            b.insn("ADD", "R4, R0, #0x0")        # r4 = the SYNCHRO's cid
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.call_addr(INNER_PRED)
            b.insn("ADD", "R7, R0, #0x0")        # r7 = INNER's verdict
            b.if_eq(R7, 0, "out")                # already rejected -> unchanged
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.call_addr(MATERIAL_CID_OF)         # r0 = the MATERIAL's cid
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "out")                 # not Remus -> unchanged
            b.insn("ADD", "R0, R4, #0x0")        # the SYNCHRO's cid
            b.call_addr(DRAGUNITY_THUNK_T & ~1)  # has_set_code[0x4A] -> 1 Dragunity, 0 not
            b.insn("ADD", "R7, R0, #0x0")
            b.label("out")
            b.insn("ADD", "R0, R7, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("ADD", "R2, R6, #0x0")
            b.insn("MOV", "R3, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            code = b.assemble(C1_ADDR)
            assert len(code) <= C1_RESERVE, f"C1 gate {len(code)}B exceeds reserve 0x{C1_RESERVE:X}"
            assert_thumb1_only(code, C1_ADDR)
            return code




        def apply_c1(ov: bytearray, rom) -> None:
            """Install the C1 gate and put it on the 0x022485D8 chain, in either order."""
            from otn_enhanced.cards import junk_speeder as jsp

            ov5_cave.install_cave(rom, C1_ADDR, _build_c1_gate(), reserve=C1_RESERVE)

            o = TUNER_HOOK_SITE - RAM_BASE
            cur = jsp._bl_target_at(ov, TUNER_HOOK_SITE)
            if cur == jsp.CAVE_TUNER:
                # Junk Speeder is already at the site -- chain behind it rather than clobber.
                jsp.chain_tuner_gate(ov, rom, C1_ADDR)
            elif cur == INNER_PRED:
                ov[o:o + 4] = _thumb_bl(TUNER_HOOK_SITE, C1_ADDR)
                print(f"G C1 Tuner gate -> ov5 0x{C1_ADDR:08X}; hooked `bl 0x{INNER_PRED:08X}` "
                      f"@0x{TUNER_HOOK_SITE:08X} (OUTER = the Tuner caller)")
            elif cur == C1_ADDR:
                print(f"G C1 Tuner gate: already installed @0x{TUNER_HOOK_SITE:08X}")
            else:
                raise SystemExit(
                    f"G C1: 0x{TUNER_HOOK_SITE:08X} calls 0x{cur:08X}, which is neither the "
                    f"native INNER, Junk Speeder's gate, nor ours -- a third patch claimed "
                    f"the only Tuner-side material gate. Report as a blocker.")


        # ===========================================================================
        # PART H -- C3a: "If you control a Dragunity monster: You can Special Summon
        #                this card from your GY"
        # ===========================================================================
        # WHAT IS AND IS NOT BUILT HERE.  C3a is the SUMMON only.  The clause's two
        # downsides -- "but banish it when it leaves the field" and "you cannot Special
        # Summon monsters from the Extra Deck for the rest of this turn, except Dragon
        # monsters" -- are NOT implemented, so the card is currently STRONGER than printed.
        # See notes/dragunity-remus-findings.md; neither is a cosmetic omission.
        #
        # THE ONE-RECORD CONSTRAINT.  The donor already owns a cls2 record (C2), and
        # find_event_handler returns the LEFTMOST same-cid record -- a second row would
        # SHADOW C2 (the Warwolf E1/E2 bug), and boggart_knight._insert_sorted
        # refuses it outright.  So both clauses run off ONE record, split on the path, as
        # lightpulsar and card.jet_synchron do: the GY-action descriptor builder
        # 0x0224C590 HARDCODES desc[+3] = 0x0E (`movs r1,#0xe ; strb r1,[r0,#3]`
        # @0x0224C5E8 -- dispatch.gy_action_offer_caps_the_event_code), so `desc[+3] ==
        # 0x0E` is a reliable POSITIVE test for the GY path.  Three thin splitters sit in
        # front of the three slots; the HAND path falls through to the already
        # in-game-confirmed C4 stubs, whose bytes are not touched.
        #
        # THE OFFER GATE is the GY-action registry 0x0228DDF8
        # (dispatch.gy_action_registry): a cid with no row there has its Graveyard effect
        # silently never offered, with every other structure correct and RAM-resident.
        # The Grapha family {chk 0x0224C591, post 0x0224C6C1} is FULL -- its three
        # phantoms went to grapha (row 15, 0x0EB2), lightpulsar (row 47, 0x0E3E) and
        # jet_synchron (row 48, 0x0E64).
        #
        # *** BUT THE REGISTRY IS NOT EXHAUSTED, AND THIS IS THE FINDING WORTH KEEPING. ***
        # All FOUR fields of a row are DATA.  The sibling family {chk 0x0224C55D, post
        # 0x0224C669} still has three unclaimed phantom rows -- 11 (0x1449), 12 (0x144C),
        # 13 (0x1452).  dispatch.gy_action_family_0224C55D_is_a_hand_gate proves that
        # family cannot host a Graveyard effect, but that is a property of its two
        # FUNCTIONS, not of the row slot: it builds no class descriptor and it gates on the
        # HAND (0x021A1584(side, 0x0B, cid)).  Rewriting a phantom row's chk/post to the
        # Grapha pair CONVERTS it into a Grapha-family row, and every reader agrees:
        # the enumerator scans [row+4] (zone, unchanged 0x0E); reader D tests
        # [row+0xC] == 0x0224C669 and now takes the generic ref path like all 45 Grapha
        # rows; reader B calls post(); reader C tests post != 0x0224C7C1.  So this needs
        # NO hooks -- contrast card.revolution_synchron C2, which had to synthesise a
        # VIRTUAL row 60 in ov5 behind FOUR hooks because this conversion was not known.
        GYREG_BASE = 0x0228DDF8         # 60 rows x 0x10 {u32 cid, u32 zone, u32 chk, u32 post}
        GYREG_COUNT = 60
        GYREG_CHK = 0x0224C591          # the Grapha (real GY-effect) family
        GYREG_POST = 0x0224C6C1
        GYREG_DONOR_ROW = (DONOR_CID, 0x0E, GYREG_CHK, GYREG_POST)
        GYREG_PHANTOM = 0x1449          # row 11, sibling family, unclaimed -- CONVERTED, not inserted
        GYREG_PHANTOM_ROW = (GYREG_PHANTOM, 0x0E, 0x0224C55D, 0x0224C669)

        ZONE_CID = 0x021A3320           # (side, zone) -> cid, 0 = empty (the same accessor C1 uses)
        PLAYER = 0x0229AC94             # per-side struct
        PLAYER_STRIDE = 0xB3C
        CHAIN_PUSH = 0x021D28A4
        CHAIN_POP = 0x021D2964
        GY_SELF_SS = 0x0220731C         # the GY self-Summon primitive (single-shot; returns 0)
        PHASE_STATE = 0x0229AAFC        # [+0x70] = the resolver phase
        C3_TURNLOG_KIND = 2             # SEPARATE from C4's kind 1 -- "each effect once per turn"

        C3COND_ADDR, C3COND_RESERVE = ov5_cave.CAVE_DR_C3_COND, 0x80
        C3MAIN_ADDR, C3MAIN_RESERVE = ov5_cave.CAVE_DR_C3_MAIN, 0x30
        C3RES_ADDR, C3RES_RESERVE = ov5_cave.CAVE_DR_C3_RES, 0x40
        C3SS_ADDR, C3SS_RESERVE = ov5_cave.CAVE_DR_C3_SS, 0x50

        CLS2_RECORD_C3 = (DONOR_CID, 0x0000, C3MAIN_ADDR | 1, 0x00000000,
                          C3COND_ADDR | 1, C3RES_ADDR | 1, 0x00000000)


        def _build_c3_cond() -> bytes:
            """cls2 +0C splitter. GY path: control a face-up Dragunity AND not used this turn."""
            b = EffectBuilder()
            b.prologue([R4, R5, R6, R7])
            b.insn("ADD", "R4, R0, #0x0")        # r4 = desc
            b.insn("ADD", "R7, R1, #0x0")        # r7 = arg1
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.if_ne(R0, 0xE, "hand")             # not the GY-action path -> C4 cond
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.insn("MOV", "R3, #0x2")            # kind 2 -- C3's own latch
            b.call_addr(TURNLOG_QUERY)
            b.if_ne(R0, 0, "deny")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R5, R0")              # r5 = controller
            b.insn("MOV", "R6, #0x0")            # r6 = zone
            b.label("loop")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.call_addr(ZONE_CID)
            b.if_eq(R0, 0, "next")
            b.insn("ADD", "R7, R0, #0x0")        # r7 = the zone's cid
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("MUL", "R0, R5")
            b.ldr_const(1, PLAYER)
            b.insn("ADD", "R0, R0, R1")
            b.insn("MOV", "R1, #0x14")
            b.insn("MUL", "R1, R6")
            b.insn("ADD", "R2, R0, R1")          # the zone record
            b.insn("LDRH", "R1, [R2, #0x3C]")
            b.if_eq(R1, 0, "next")               # face-down: its name is not known
            b.insn("ADD", "R0, R7, #0x0")
            b.call_addr(DRAGUNITY_THUNK_T & ~1)  # has_set_code[0x4A]
            b.if_ne(R0, 0, "allow")
            b.label("next")
            b.insn("ADD", "R6, R6, #0x1")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "loop")
            b.label("deny")
            b.epilogue(0)
            b.label("allow")
            b.epilogue(1)
            b.label("hand")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R7, #0x0")
            b.call_addr(C4_COND_ADDR)            # the in-game-confirmed C4 cond, untouched
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            code = b.assemble(C3COND_ADDR)
            assert len(code) <= C3COND_RESERVE, "C3 cond %dB > 0x%X" % (len(code), C3COND_RESERVE)
            assert_thumb1_only(code, C3COND_ADDR)
            return code


        def _build_c3_main() -> bytes:
            """cls2 +04 splitter: GY path -> the self-SS resolver, hand path -> add-1-from-Deck."""
            b = EffectBuilder()
            b.prologue([R4, R5])
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.if_ne(R0, 0xE, "hand")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.call_addr(C3SS_ADDR)
            b.insn("POP", "{R4, R5, PC}")
            b.label("hand")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.call_addr(MAIN_ADD_ONE_FROM_DECK & ~1)
            b.insn("POP", "{R4, R5, PC}")
            code = b.assemble(C3MAIN_ADDR)
            assert len(code) <= C3MAIN_RESERVE, "C3 main %dB > 0x%X" % (len(code), C3MAIN_RESERVE)
            assert_thumb1_only(code, C3MAIN_ADDR)
            return code


        def _build_c3_res() -> bytes:
            """cls2 +10 splitter: GY path stamps the kind-2 latch (no discard -- it is IN the GY)."""
            b = EffectBuilder()
            b.prologue([R4])
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.if_ne(R0, 0xE, "hand")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(IS_RESOLVE_CTX)
            b.if_ne(R0, 0, "ok")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.insn("MOV", "R2, #0x2")            # kind 2 -- C3's own latch
            b.insn("MOV", "R3, #0x0")
            b.call_addr(NODE_ATTACH)
            b.label("ok")
            b.epilogue(1)
            b.label("hand")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(C4_RES_ADDR)             # the in-game-confirmed C4 res, untouched
            b.insn("POP", "{R4, PC}")
            code = b.assemble(C3RES_ADDR)
            assert len(code) <= C3RES_RESERVE, "C3 res %dB > 0x%X" % (len(code), C3RES_RESERVE)
            assert_thumb1_only(code, C3RES_ADDR)
            return code


        def _build_c3_ss() -> bytes:
            """The GY self-Summon resolver: phase 0x80 -> 0x7F -> 0x64."""
            b = EffectBuilder()
            b.prologue([R4, R5])
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(0, PHASE_STATE)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.if_eq(R0, 0x80, "p80")
            b.if_eq(R0, 0x7F, "p7f")
            b.epilogue(0)
            b.label("p80")
            b.call_addr(CHAIN_PUSH)
            # C3b: arm the banish-on-leave rider BEFORE the summon commits. The shared
            # summon_rider_hook consumes (and clears) this byte when event 0x14 fires for
            # 0x106E, and attaches {key 0x1E15, kind 3} -- the cid-blind marker node that
            # rewrites the leave destination 0x0E (GY) -> 0x0F (banished).
            b.ldr_const(0, ov5_cave.CAVE_DR_ARM)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.call_addr(GY_SELF_SS)
            b.epilogue(0x7F)
            b.label("p7f")
            b.call_addr(CHAIN_POP)
            b.epilogue(0x64)
            code = b.assemble(C3SS_ADDR)
            assert len(code) <= C3SS_RESERVE, "C3 SS %dB > 0x%X" % (len(code), C3SS_RESERVE)
            assert_thumb1_only(code, C3SS_ADDR)
            return code


        def apply_c3(ov: bytearray, rom) -> None:
            """Install the C3a stubs, the C3b rider arm, and convert a phantom GY-action row."""
            from otn_enhanced.effects import summon_rider_hook as riderhook
            for addr, reserve, blob in ((C3SS_ADDR, C3SS_RESERVE, _build_c3_ss()),
                                        (C3COND_ADDR, C3COND_RESERVE, _build_c3_cond()),
                                        (C3MAIN_ADDR, C3MAIN_RESERVE, _build_c3_main()),
                                        (C3RES_ADDR, C3RES_RESERVE, _build_c3_res())):
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)

            # C3b: the SHARED summon-rider hook (one 4-byte BL at 0x02268666, a cid register).
            # 0x106E was MEASURED to reach that default leaf -- see the ARMS entry.
            riderhook.install(rom)
            riderhook.apply(ov)

            rows = [struct.unpack_from("<4I", ov, GYREG_BASE - RAM_BASE + i * 16)
                    for i in range(GYREG_COUNT)]
            if GYREG_DONOR_ROW in rows:
                print("H GY-action registry: 0x%04X already has a row -> no change" % DONOR_CID)
                return
            hit = [i for i, r in enumerate(rows) if r == GYREG_PHANTOM_ROW]
            assert len(hit) == 1, (
                "the sibling-family phantom row is not present exactly once (%d) -- "
                "another patch took it" % len(hit))
            struct.pack_into("<4I", ov, GYREG_BASE - RAM_BASE + hit[0] * 16, *GYREG_DONOR_ROW)
            print("H GY-action registry row %d: phantom 0x%04X {0x0224C55D, 0x0224C669} "
                  "CONVERTED to 0x%04X zone 0x0E {0x%08X, 0x%08X} (count %d unchanged)"
                  % (hit[0], GYREG_PHANTOM, DONOR_CID, GYREG_CHK, GYREG_POST, GYREG_COUNT))


        def _rows(ov, base, count, stride, fmt):
            return [struct.unpack_from(fmt, ov, base - RAM_BASE + i * stride) for i in range(count)]


        def _only(ov, base, count, stride, fmt, cid):
            hits = [r for r in _rows(ov, base, count, stride, fmt) if r[0] == cid]
            assert len(hits) == 1, f"{cid:#06x} owns {len(hits)} rows @{base:#010x}, expected 1"
            return hits[0]


        def _assert_templates(ov) -> None:
            """Pin every stock row this module copies, so a drift fails loudly here."""
            assert DONOR_CID not in MAIN_SPECIAL_CASES, (
                f"donor {DONOR_CID:#06x} is special-cased by main {MAIN_ADD_ONE_FROM_DECK:#010x}")
            assert DONOR_CID not in COND_SPECIAL_CASES, (
                f"donor {DONOR_CID:#06x} is special-cased by cond {COND_FLOODGATE_CANDS:#010x}")
            got = _only(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS_FMT, BIRDFACE)
            assert got == BIRDFACE_CLS2, f"Birdface cls2 template drifted: {[hex(v) for v in got]}"
            got = _only(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT, FUSION_SAGE)
            assert got == FUSION_SAGE_POP, f"Fusion Sage criteria template drifted: {[hex(v) for v in got]}"
            got = _only(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS_FMT, WHITE_STONE)
            assert got[2] == MAIN_ADD_ONE_FROM_DECK, "The White Stone of Legend lost the shared main"
            # the target must exist and must not already own the row we are about to add
            assert not [r for r in _rows(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT)
                        if r[0] == DONOR_CID], f"donor {DONOR_CID:#06x} already owns a criteria row"


        def _cls2_record() -> tuple:
            """The donor's cls2 record. ONE record serves every clause -- see PART H."""
            if ENABLE_C3:
                return CLS2_RECORD_C3
            return CLS2_RECORD_C4 if ENABLE_C4 else CLS2_RECORD


        def _arm9_data(rom):
            import ndspy.code
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            return mc, next(s for s in mc.sections if s.ramAddress == ARM9_BASE)


        def _handfx_list(data: bytes) -> list[int]:
            for p in HANDFX_POOLS:
                assert struct.unpack_from("<I", data, p - ARM9_BASE)[0] == HANDFX_LIST, \
                    f"hand-effect pool @0x{p:08X} moved"
            assert struct.unpack_from("<H", data, HANDFX_COUNT_IMM - ARM9_BASE)[0] == (0x2200 | HANDFX_COUNT), \
                "hand-effect list count immediate changed"
            return list(struct.unpack_from(f"<{HANDFX_COUNT}H", data, HANDFX_LIST - ARM9_BASE))


        def _dragunity_list(data: bytes) -> list[int]:
            """The live "Dragunity" cid list, with base and count read from the thunk itself."""
            sig = bytes(data[DRAGUNITY_THUNK - ARM9_BASE:DRAGUNITY_THUNK - ARM9_BASE + 8])
            assert sig == DRAGUNITY_THUNK_SIG, f"the 0x4A set-code thunk drifted: {sig.hex()}"
            base = struct.unpack_from("<I", data, DRAGUNITY_POOL - ARM9_BASE)[0]
            assert base == DRAGUNITY_LIST, f"the Dragunity list literal moved to 0x{base:08X}"
            imm = struct.unpack_from("<H", data, DRAGUNITY_COUNT_IMM - ARM9_BASE)[0]
            assert imm & 0xFF00 == 0x2200, "the Dragunity count is not `movs r2,#N`"
            n = imm & 0xFF
            return list(struct.unpack_from(f"<{n}H", data, base - ARM9_BASE))


        def apply_arm9(out_path: str) -> None:
            """PARTS A and D -- both ARM9 lists, edited in place in one open/save."""
            import ndspy.rom
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            mc, sec = _arm9_data(rom)
            d = bytearray(sec.data)
            dirty = False

            # --- PART A: the hand-effect offer list (count-neutral over a phantom) -----
            cur = _handfx_list(d)
            if DONOR_CID in cur:                                                   # idempotent
                print(f"A hand-effect list: 0x{DONOR_CID:04X} already present -> no change")
            else:
                assert cur.count(HANDFX_PHANTOM) == 1, \
                    f"phantom 0x{HANDFX_PHANTOM:04X} not in the hand-effect list (already spent?)"
                new = sorted([c for c in cur if c != HANDFX_PHANTOM] + [DONOR_CID])
                assert len(new) == HANDFX_COUNT and all(new[i] < new[i + 1] for i in range(HANDFX_COUNT - 1)), \
                    "hand-effect list lost its count or its strict sort"
                struct.pack_into(f"<{HANDFX_COUNT}H", d, HANDFX_LIST - ARM9_BASE, *new)
                dirty = True
                print(f"A hand-effect list @0x{HANDFX_LIST:08X}: dropped phantom 0x{HANDFX_PHANTOM:04X}, "
                      f"inserted 0x{DONOR_CID:04X} (count {HANDFX_COUNT}, sorted)")

            # --- PART D: "Dragunity" membership (DISPLACEMENT -- count stays put) ------
            cur = _dragunity_list(d)
            n = len(cur)
            if DONOR_CID in cur:                                                   # idempotent
                print(f"D Dragunity set code: 0x{DONOR_CID:04X} already a member -> no change")
            else:
                assert cur.count(DISPLACED_CID) == 1, \
                    f"0x{DISPLACED_CID:04X} is not a Dragunity member (list already edited?)"
                new = sorted([c for c in cur if c != DISPLACED_CID] + [DONOR_CID])
                assert len(new) == n and all(new[i] < new[i + 1] for i in range(n - 1)), \
                    "the Dragunity list lost its count or its strict sort"
                struct.pack_into(f"<{n}H", d, DRAGUNITY_LIST - ARM9_BASE, *new)
                dirty = True
                print(f"D Dragunity set code @0x{DRAGUNITY_LIST:08X}: displaced 0x{DISPLACED_CID:04X} "
                      f"(Dragunity Knight - Trident), inserted 0x{DONOR_CID:04X} "
                      f"(count {n} UNCHANGED, sorted)")

            if dirty:
                sec.data = bytes(d)
                rom.arm9 = mc.save()
                rom.saveToFile(out_path)

        def _assert_templates_stock(ov) -> None:
            """The three template cards must be handed back exactly as the stock ROM has them."""
            got = _only(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS_FMT, BIRDFACE)
            assert got == BIRDFACE_CLS2, f"Birdface cls2 altered: {[hex(v) for v in got]}"
            got = _only(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT, FUSION_SAGE)
            assert got == FUSION_SAGE_POP, f"Fusion Sage criteria altered: {[hex(v) for v in got]}"
            got = _only(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS_FMT, WHITE_STONE)
            assert got[2] == MAIN_ADD_ONE_FROM_DECK, "The White Stone of Legend lost the shared main"

        stubs = ((C4_COND_ADDR, _build_c4_cond(), "C4 cond"), (C4_RES_ADDR, _build_c4_res(), "C4 res"))

        def install(rom, view):
            ov = view.buf
            _assert_templates(ov)
            apply_c3(ov, rom)
            apply_c1(ov, rom)
            insert_row(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS_FMT, _cls2_record(), CLS2_PHANTOM, "B cls2")
            insert_row(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT, POP_RECORD, POP_PHANTOM, "C criteria")

        def check_fn(c, rom, view):
            ov = bytes(view.buf)
            checks = []
            def table(base, count, stride, fmt, ph, want):
                rows = _rows(ov, base, count, stride, fmt)
                keys = [r[0] for r in rows]
                return ([r for r in rows if r[0] == DONOR_CID] == [want]
                        and ph not in keys
                        and keys == sorted(keys))

            want = _cls2_record()
            checks.append((f"B cls2 record {{0x{DONOR_CID:04X}, main 0x{want[2]:08X}, "
                           f"cond 0x{want[4]:08X}, res 0x{want[5]:08X}}}",
                           table(CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS_FMT, CLS2_PHANTOM, want)))
            checks.append((f"C criteria row {{0x{DONOR_CID:04X}, aux 0x{RAVINE_CID:04X} = Dragon Ravine, "
                           f"fn 0x{NAMED_DECK_SELECTOR:08X}, word 0x{CRIT_SPELL:08X}}}",
                           table(POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT, POP_PHANTOM, POP_RECORD)))

            # templates handed back stock
            try:
                _assert_templates_stock(ov)
                checks.append(("templates stock (Fusion Sage / Birdface / White Stone)", True))
            except AssertionError as exc:
                checks.append((f"templates stock -- {exc}", False))

            # PART A: ARM9 list
            rom = rom
            _, sec = _arm9_data(rom)
            lst = _handfx_list(bytes(sec.data))
            checks.append((f"A hand-effect list @0x{HANDFX_LIST:08X} (x{HANDFX_COUNT}, sorted, "
                           f"0x{DONOR_CID:04X} in, phantom 0x{HANDFX_PHANTOM:04X} out)",
                           DONOR_CID in lst and HANDFX_PHANTOM not in lst
                           and lst == sorted(lst) and len(set(lst)) == HANDFX_COUNT))

            # PART D: the set-code list must have the SAME length, still be strictly sorted,
            # carry the donor, and have given up exactly the displaced card.
            dl = _dragunity_list(bytes(sec.data))
            checks.append((f"D Dragunity set code @0x{DRAGUNITY_LIST:08X} (x{len(dl)} unchanged, sorted, "
                           f"0x{DONOR_CID:04X} in, 0x{DISPLACED_CID:04X} Trident out)",
                           len(dl) == 21 and DONOR_CID in dl and DISPLACED_CID not in dl
                           and dl == sorted(dl) and len(set(dl)) == len(dl)))
            # ...and the OTHER twenty members must be untouched: the displacement must cost
            # exactly Trident and nothing else.
            checks.append((f"D the other 20 Dragunity members intact",
                           set(dl) == (set(DRAGUNITY_STOCK) - {DISPLACED_CID}) | {DONOR_CID}))

            if ENABLE_C4:
                # the installed stubs must match what the builders emit, byte for byte
                rom_c = rom
                ov5 = bytes(rom_c.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
                for label, addr, blob in (("cond", C4_COND_ADDR, _build_c4_cond()),
                                          ("res", C4_RES_ADDR, _build_c4_res())):
                    off = addr - ov5_cave.OV5_RAM_BASE
                    checks.append((f"F C4 {label} stub @0x{addr:08X} ({len(blob)} B, Thumb-1)",
                                   ov5[off:off + len(blob)] == blob))

            if ENABLE_C3:
                rom_h = rom
                ov5h = bytes(rom_h.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
                for label, addr, blob in (("SS resolver", C3SS_ADDR, _build_c3_ss()),
                                          ("cond splitter", C3COND_ADDR, _build_c3_cond()),
                                          ("main splitter", C3MAIN_ADDR, _build_c3_main()),
                                          ("res splitter", C3RES_ADDR, _build_c3_res())):
                    o5 = addr - ov5_cave.OV5_RAM_BASE
                    checks.append((f"H C3 {label} @0x{addr:08X} ({len(blob)} B, Thumb-1)",
                                   ov5h[o5:o5 + len(blob)] == blob))
                rows = [struct.unpack_from("<4I", ov, GYREG_BASE - RAM_BASE + i * 16)
                        for i in range(GYREG_COUNT)]
                checks.append((f"H GY-action registry: 0x{DONOR_CID:04X} row present, "
                               f"phantom 0x{GYREG_PHANTOM:04X} converted, {GYREG_COUNT} rows",
                               rows.count(GYREG_DONOR_ROW) == 1
                               and GYREG_PHANTOM_ROW not in rows
                               and len(rows) == GYREG_COUNT))
                # the three families must still be well-formed: only ONE row changed hands here.
                # Grapha/sibling counts drift as OTHER patches convert phantoms in this same
                # registry (miscellaneousaurus took a second sibling-family phantom
                # Grapha 46->47, sibling 5->4; ojamassimilation C3 the last one:
                # Grapha 47->48, sibling 4->3) -- this check floors rather than
                # pins them, so it stays true as long as nothing UNDOES a conversion.
                fams = {}
                for r in rows:
                    fams[(r[2], r[3])] = fams.get((r[2], r[3]), 0) + 1
                checks.append((f"H GY-action families intact (Grapha >=46, 0x0224C63D 9, sibling >=3)",
                               fams.get((GYREG_CHK, GYREG_POST), 0) >= 46
                               and fams.get((0x0224C63D, 0x0224C7C1)) == 9
                               and fams.get((0x0224C55D, 0x0224C669), 0) >= 3))

                # C3b: the shared summon-rider hook and every registered arm's one-shot byte.
                # riderhook.verify rebuilds the stub from ARMS, so it also pins that Jet
                # Synchron's and Jet Warrior's arms are still present and still first.
                from otn_enhanced.effects import summon_rider_hook as riderhook
                riderhook.verify(rom_h, bytes(ov), lambda ok, label: checks.append((label, ok)))
                checks.append((f"R 0x{DONOR_CID:04X} is registered on the shared rider hook",
                               DONOR_CID in [c for c, *_ in riderhook.ARMS]))

            if ENABLE_C1:
                from otn_enhanced.cards import junk_speeder as jsp
                rom_g = rom
                ov5g = bytes(rom_g.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
                blob = _build_c1_gate()
                off = C1_ADDR - ov5_cave.OV5_RAM_BASE
                checks.append((f"G C1 gate @0x{C1_ADDR:08X} ({len(blob)} B, Thumb-1)",
                               ov5g[off:off + len(blob)] == blob))
                # the site must reach our gate -- directly, or via Junk Speeder's chain
                tgt = jsp._bl_target_at(ov, TUNER_HOOK_SITE)
                direct = tgt == C1_ADDR
                chained = tgt == jsp.CAVE_TUNER and ov5_cave.read_cave(
                    rom_g, jsp.CAVE_TUNER,
                    len(jsp.build_tuner_gate(jsp.CAVE_TUNER, C1_ADDR))
                ) == jsp.build_tuner_gate(jsp.CAVE_TUNER, C1_ADDR)
                checks.append((f"G C1 site 0x{TUNER_HOOK_SITE:08X} reaches the gate "
                               f"({'direct' if direct else 'chained via Junk Speeder' if chained else 'NO'})",
                               direct or chained))
            for label, good in checks:
                c.ok(good, label)

        return Compiled(stubs, installs=(install,), posts=(apply_arm9,), checks=(check_fn,))


remus_effects = named_spell_search_hand_discard_gy_self_summon_banish_on_leave_dragunity_synchro_material_lock

SPEC = card(0x106E, remus_effects())

PROPS = card_props("WIND", "Dragon", level=2, atk=800, defense=800, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_dragunity_remus.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

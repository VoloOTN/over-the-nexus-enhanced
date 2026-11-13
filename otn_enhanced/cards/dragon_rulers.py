"""The Dragon Rulers on vanilla Normal donors -- all 8 whole cards, as a "virtual registry" (no table rows).

    Big: Redox (EARTH) / Tidal (WATER) / Blaster (FIRE) / Tempest (WIND), Dragon Lv7. Baby: Reactan / Stream / Burner / Lightning.
    The spec carries the last ruler (Lightning, WIND Dragon Lv3 500/1800); the other seven cards' stats and text are written by the verb's post.
    (See card_text.CARD_TEXT for the full printed texts.)
"""
from __future__ import annotations

import sys

from otn_enhanced.effects.common import code_reaches, reached_nodes
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, SRC
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.data.card_stats import apply_stats_and_text
from otn_enhanced.data import card_text
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class virtual_registry_eight_dragon_rulers_banish_special_summon_from_hand_or_graveyard_return_in_end_phase_discard_effect_banish_search:
    """The Dragon Rulers on vanilla Normal donors, all eight (Redox / Tidal / Blaster / Tempest and the babies Reactan / Stream / Burner / Lightning):
    a 'virtual registry' -- NO table rows. Seven small ov3 (cave3) hooks answer for the ruler cids (find_event_handler miss tail, the two criteria
    resolver tails, the ARM9 LIST B hand-offer gate, the End-Phase row, the GY->banish cid gate, the hand/field banish switch and the leave-mask
    bsearch) and the card logic plus virtual records / criteria rows live in ov5, with Revolution Synchron's GY-action sites rewritten to the N-row
    stubs. Original code embedded verbatim. The module state the original kept in globals (REV_PRESENT, EXTRA_GY_ROWS) is read from the input ROM in
    `install`; the other cards' modules still set it on the CARD module (dragon_rulers.py keeps those names). The card_prop + text rewrite of the
    first seven rulers is a post (it always writes text), the last ruler (spec.cid) goes through dsl.make, which keeps the original order."""

    def compile(self, view, cid) -> Compiled:
        import struct
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.effects import cave3
        from otn_enhanced.data import card_text
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import gy_vrow_hook as gyv
        from otn_enhanced.cards import revolution_synchron as rev
        from otn_enhanced.data.card_stats import apply_stats_and_text
        from otn_enhanced.effects.timing_class_hook import _bl
        from otn_enhanced.asm.effect_verify import bl_reaches
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7

        SRC = "data/over_the_nexus/working/rom.nds"
        OUT = "data/over_the_nexus/working/rom_dragon_rulers.nds"

        # ---------------------------------------------------------------------------------------------------
        # The family.  k = index in RULERS (the ov3 cid list order).  Big rulers carry an EP record.
        # ---------------------------------------------------------------------------------------------------
        REDOX, TIDAL, BLASTER, TEMPEST = 0x17CD, 0x115F, 0x1145, 0x1125   # Charcoal Inpachi / Mech Bass /
        REACTAN, STREAM, BURNER, LIGHTNING = 0x0FF4, 0x115E, 0x0FEA, 0x1CC6  # Mechanicalchaser / Parrot Dragon /
        #                                     Axe Raider / 7 Colored Fish / Garoozis / Atlantean Pikeman -- cids KEPT
        ATTR_EARTH, ATTR_WATER, ATTR_FIRE, ATTR_WIND = 5, 3, 4, 6
        CHK_SS, CHK_ROW, CHK_FIELD = 1, 2, 4      # C3 legality: may SS here / a C3-row candidate / any card on field


        def _search(attr: int) -> int:
            return (1 << 27) | (attr << 24) | 2     # "<attr> Dragon monster" (predicate 0x0223BA24 ANDs race and attribute)


        def _big(cid, attr, atk, defense, c3row, res_c3, tgt_c3, chk, slot2=0):
            return dict(cid=cid, attr=attr, level=7, atk=atk, defense=defense, big=True, search=_search(attr),
                        c3row=c3row, res_c3=res_c3, tgt_c3=tgt_c3, chk=chk, slot2=slot2)


        def _baby(cid, attr, level, atk, defense, big_cid):
            # "discard this card and 1 Dragon or <attr> monster; Special Summon 1 <big> from your Deck. It cannot attack
            # this turn."  Deck row = 3DS {aux = big cid, 0x4A6834 == 0x0223D075 named Deck pick, 0x00000802}.
            return dict(cid=cid, attr=attr, level=level, atk=atk, defense=defense, big=False, search=_search(attr),
                        c3row=(big_cid, NAMED_DECK_H, 0x00000802), res_c3=RES_DECK_SS, tgt_c3=0,
                        chk=CHK_SS | CHK_ROW, slot2=0)


        def _rulers():
            return (   # k order = CAVE3_RUL_LIST order; bigs first (only they own GY / BAN / EP records)
                _big(REDOX, ATTR_EARTH, 1600, 3000, (0xFFFF, GYT_H, 0x00010002), RES_REVIVE, TGT_STEP, CHK_SS),
                _big(TIDAL, ATTR_WATER, 2600, 2000, (0xFFFF, SEARCH_H, 0x00000002), RES_DECK_SEND, 0, CHK_ROW),
                _big(BLASTER, ATTR_FIRE, 2800, 1800, (0xFFFF, SEARCH_H, _search(ATTR_FIRE)), RES_DESTROY, BOARD_STEP,
                     CHK_FIELD, slot2=FIELD_FILTER),
                _big(TEMPEST, ATTR_WIND, 2400, 2200, (0xFFFF, SEARCH_H, 0x08000002), RES_SEARCH, 0, CHK_ROW),
                _baby(REACTAN, ATTR_EARTH, 4, 1800, 1200, REDOX),
                _baby(STREAM, ATTR_WATER, 4, 1600, 2000, TIDAL),
                _baby(BURNER, ATTR_FIRE, 3, 1000, 200, BLASTER),
                _baby(LIGHTNING, ATTR_WIND, 3, 500, 1800, TEMPEST),
            )


        _ATTR_NAME = {ATTR_EARTH: "EARTH", ATTR_WATER: "WATER", ATTR_FIRE: "FIRE", ATTR_WIND: "WIND"}

        # ---------------------------------------------------------------------------------------------------
        # Engine (every one proven in notes/dragon-rulers-findings.md or the KB fact quoted there)
        # ---------------------------------------------------------------------------------------------------
        STATE = 0x0229AAFC          # +0x70 resolver phase, +0x7C cost phase
        ACTING = 0x0229A9FC         # +0x50 the running activation's descriptor
        CHOICE = 0x0229DD94         # +0x34 menu answer (0-based)
        TURN = 0x0229DD14           # +0x34 turn player
        PLAYER, STRIDE = 0x0229AC94, 0xB3C
        HAND_ARR, HAND_CNT, GY_ARR, GY_CNT = 0x124, 0x0C, 0x55C, 0x14
        ONCE_CHECK = 0x021F6DD9     # (desc) -> 0 iff this cid's turn node exists
        COPY_EXEMPT = 0x021D2B89    # (desc) -> nonzero: replay context, skip the node
        TURN_NODE = 0x021D2585      # (side, cid, 1, 0)
        SHORTCIRCUIT = 0x021D2BC9   # (desc) -> nonzero: cost already settled
        CAN_SS = 0x021F0385         # (desc) -> may activate + SS this cid into a free zone
        GY_REVIVE_GATE = 0x021FF06D # (desc, arg) Plaguespreader's GY self-SS gate (Jet Synchron C2)
        DECK_COND = 0x021F0821      # (desc, arg) a Deck candidate exists (criteria count)
        TAG_YOU_CAN = 0x021E51E5
        PROMPT = 0x0219ABB5         # (desc, title, l0, l1, [sp] l2, [sp+4] l3, [sp+8] mask)
        MESSAGE = 0x0219A819        # (side, code)
        PICKER = 0x0219C431         # (side, 6, cid, param)
        READBACK = 0x0219C511       # () -> &picked card word
        CHAIN_PUSH, CHAIN_POP = 0x021D28A5, 0x021D2965
        HAND_INDEX = 0x021A25A1     # (side, ref) -> hand index or -1
        HAND_BANISH = 0x021C6E99    # (side, hand index)
        REF_TO_WORD = 0x021A25E9    # (ref) -> &card word or 0
        GY_BANISH = 0x021C7105      # (side, &word, 0)
        COST_DISCARD = 0x021C6DB5   # (side, hand index) kind-1 (cost) discard
        HAND_BUILDER, GY_BUILDER = 0x0223C16D, 0x0223C4E9
        BANISH_FLAGS = 0x10000
        SEARCH_H, DISCARD_H, GYT_H = 0x0223CAD9, 0x02242105, 0x0223C9D1
        RES_HAND_SS, RES_GY_SS, RES_REVIVE = 0x02206ABD, 0x0220731D, 0x02207191
        TGT_STEP = 0x02235605       # off-field list-zone target step (Lightpulsar C3)
        RES_SEARCH = 0x02207EF5
        RES_RETURN, TAG_MANDATORY = 0x0220A901, 0x021E88A9
        ATTR, RACE = 0x0202ABC9, 0x0202ABB9
        RACE_DRAGON = 1
        EP_POSTER = 0x02253F89
        BSEARCH = 0x02022E15
        RES_DECK_SEND = 0x02208DD5  # Deck -> GY by the C3 row (Tidal; Uni-Zombie C2)
        RES_DESTROY = 0x02204899    # destroy the declared target (Blaster; Kahkki/Gren)
        BOARD_STEP = 0x02234DA5     # +14 board target step (counts with the record's +08)
        FIELD_FILTER = 0x021DE5A9   # +08 "1 card on the field" (3DS Blaster 0x3E39D4, 19/19)
        RES_DECK_SS = 0x02206CAD    # Special Summon 1 from the Deck by the row (Summoner Monk / Gravekeeper's Spy)
        NAMED_DECK_H = 0x0223D075   # named Deck pick, aux = the cid (Dragunity Remus)
        CNT = 0x02243FE1            # (side, cid, param) -> candidates
        COUNT_CARDS = 0x021ACF29    # (side) -> occupied zones 0..0xA
        RIDER = 0x021C479D          # (side, zone, key, kind, [sp] value)
        MONK = 0x1900               # Summoner Monk: a member of the can't-attack rider list 0x0226D6F8
        SUMLIST_SITE = 0x02268090   # bl 0x02022E14 (list 0x0228F708 by SOURCE cid) in the summon-event handler
        TITLE, LABEL_C1, LABEL_C3 = 0x103, 0x19F, 0x0EB
        MSG_BANISH, MSG_DISCARD = 0x56, 0x29

        for _v in (ONCE_CHECK, COPY_EXEMPT, TURN_NODE, SHORTCIRCUIT, CAN_SS, GY_REVIVE_GATE, DECK_COND, TAG_YOU_CAN,
                   PROMPT, MESSAGE, PICKER, READBACK, CHAIN_PUSH, CHAIN_POP, HAND_INDEX, HAND_BANISH, REF_TO_WORD,
                   GY_BANISH, COST_DISCARD, HAND_BUILDER, GY_BUILDER, SEARCH_H, DISCARD_H, GYT_H, RES_HAND_SS,
                   RES_GY_SS, RES_REVIVE, TGT_STEP, RES_SEARCH, RES_RETURN, TAG_MANDATORY, ATTR, RACE, EP_POSTER,
                   BSEARCH, RES_DECK_SEND, RES_DESTROY, BOARD_STEP, FIELD_FILTER, RES_DECK_SS, NAMED_DECK_H, CNT,
                   COUNT_CARDS, RIDER):
            assert _v & 1, f"{_v:#x}: blx/bx to an even literal switches to ARM state -> freeze"

        RULERS = _rulers()
        STATS = {r["cid"]: dict(attribute=_ATTR_NAME[r["attr"]], race="Dragon", level=r["level"], atk=r["atk"],
                                defense=r["defense"], card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]) for r in RULERS}
        CIDS = [r["cid"] for r in RULERS]
        BIGS = [r["cid"] for r in RULERS if r["big"]]
        assert CIDS[:len(BIGS)] == BIGS, "big rulers must come first"
        assert len(BIGS) == 4, "H6/H7/H8 gate big rulers as `lsrs r0, k, #2 ; bne` (k in 0..3, miss = -1)"

        # ---------------------------------------------------------------------------------------------------
        # Hook sites (stock bytes; notes/dragon-rulers-findings.md)
        # ---------------------------------------------------------------------------------------------------
        H1_SITE, H1_STOCK = 0x0224A86A, bytes.fromhex("0020febd")   # movs r0,#0 ; pop {r1-r7,pc}
        H2_SITE, H2_STOCK = 0x02243F24, bytes.fromhex("0d38f8bd")   # subs r0,#0xd ; pop {r3-r7,pc}
        H3_SITE, H3_STOCK = 0x02243F62, bytes.fromhex("331c0c20")   # adds r3,r6,#0 ; movs r0,#0xc
        H3_RESUME = 0x02243F70                                      # adds r1,r5 ; adds r2,r7 ; blx r3
        H6_SITE, H6_STOCK = 0x021C71C8, bytes.fromhex("21498842")   # ldr r1,=0x1CF6 ; cmp r0,r1
        H7_SITE = 0x021D1B98                                        # ldr r1,=0x1D98 ; cmp r5,r1
        H7_LEAF = 0x021D1D3E                                        # the dest == 0x0F banish leaf
        H8_SITE = 0x021C810C                                        # bl 0x02022E44 (leave-mask bsearch, r4 = cid) in 0x021C7FD0
        H8_BSEARCH = 0x02022E44
        LEAVE_MASK_TABLE, LEAVE_MASK_ROWS = 0x0226EC1C, 0x98
        LEAVE_LEFT_FIELD = 0x0004                                   # leave.mask_bit_semantics: [sp+0x2C] left the field
        MISS_SITE, MISS_TEST = 0x021E510A, 0x021EE0E0                # bl 0x021EE0E0 in the "You can" body
        H4_ARM9_SITE = 0x02023566                                   # bl 0x02022E14 (LIST B) ; pop {r4,pc}
        EP_ROW = 0x0228E1E0 + 154 * 8                               # {0x02253F89, 0x19C0} stock
        EP_ROW_STOCK = (EP_POSTER, 0x19C0)

        # ---------------------------------------------------------------------------------------------------
        # Hosting.  ov3 = cave3 runs (Rod's NOOP slots avoided); ov5 = CAVE_RUL_*.
        # ---------------------------------------------------------------------------------------------------
        C3 = cave3
        O5 = ov5_cave
        NREC = 4                    # HAND, GY, BAN, EP
        REC_SIZE = 0x18
        ROW_STRIDE = 0x40           # VROW, SEARCH, DISCARD, C3 row (0x30) + PARAMS (0x10)
        P_RES, P_TGT, P_CHK, P_BABY, P_SLOT2 = 0x30, 0x34, 0x38, 0x39, 0x3C


        def _ruler_list() -> bytes:
            return b"".join(struct.pack("<H", c) for c in CIDS) + b"\0\0"


        def _ep_list() -> bytes:
            return b"".join(struct.pack("<H", c) for c in BIGS) + b"\0\0"


        # =================================================================================================
        # ov3 stubs
        # =================================================================================================
        def findk_stub(base: int) -> bytes:
            """(r0 = cid) -> r0 = k, or -1 (flags from the final compare: bmi on a miss).  Clobbers r1-r3."""
            b = EffectBuilder()
            b.ldr_const(1, C3.CAVE3_RUL_LIST)
            b.insn("MOV", "R2, #0x0")
            b.label("fk_lp")
            b.insn("LDRH", "R3, [R1, #0x0]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "fk_miss")
            b.insn("CMP", "R3, R0")
            b.insn("BEQ", "fk_hit")
            b.insn("ADD", "R1, #0x2")
            b.insn("ADD", "R2, #0x1")
            b.insn("B", "fk_lp")
            b.label("fk_hit")
            b.insn("ADD", "R0, R2, #0x0")
            b.insn("CMP", "R0, #0x0")
            b.insn("BX", "LR")
            b.label("fk_miss")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def h1_stub(base: int) -> bytes:
            """find_event_handler miss tail.  r4 = desc, [sp] = key cid, frame = push {r1-r7,lr}."""
            b = EffectBuilder()
            b.insn("LDR", "R0, [SP, #0x0]")
            b.call_addr(C3.CAVE3_RUL_FINDK)
            b.insn("BMI", "miss")
            b.insn("MOV", f"R1, #0x{NREC * REC_SIZE:X}")
            b.insn("MUL", "R0, R1")
            b.ldr_const(1, O5.CAVE_RUL_VREC)
            b.insn("ADD", "R0, R0, R1")
            b.insn("LDRB", "R1, [R4, #0x5]")
            b.insn("CMP", "R1, #0x1")
            b.insn("BEQ", "ep")
            b.insn("CMP", "R1, #0x2")
            b.insn("BNE", "miss")
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.insn("LDRB", "R2, [R4, #0x4]")
            b.insn("CMP", "R1, #0xB")
            b.insn("BEQ", "hand")
            b.insn("CMP", "R1, #0xF")
            b.insn("BEQ", "ban")
            b.insn("CMP", "R1, #0xE")
            b.insn("BNE", "miss")
            b.insn("CMP", "R2, #0x6")
            b.insn("BGT", "miss")
            b.insn("ADD", f"R0, #0x{REC_SIZE:X}")
            b.insn("B", "got")
            b.label("hand")
            b.insn("CMP", "R2, #0x0")
            b.insn("BNE", "miss")
            b.insn("B", "got")
            b.label("ban")
            b.insn("ADD", f"R0, #0x{2 * REC_SIZE:X}")
            b.insn("B", "got")
            b.label("ep")
            b.insn("LDRB", "R2, [R4, #0x4]")
            b.insn("CMP", "R2, #0x6")
            b.insn("BNE", "miss")
            b.insn("ADD", f"R0, #0x{3 * REC_SIZE:X}")
            b.label("got")
            b.insn("LDRH", "R1, [R0, #0x0]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "out")
            b.label("miss")
            b.insn("MOV", "R0, #0x0")
            b.label("out")
            b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def h2_stub(base: int) -> bytes:
            """criteria resolver miss tail: r5 = cid; native returns -1."""
            b = EffectBuilder()
            b.call_addr(C3.CAVE3_RUL_FINDK, R5)
            b.insn("BMI", "miss")
            b.insn("ADD", "R0, #0x40")
            b.insn("LSL", "R0, R0, #0x8")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("miss")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def h3_stub(base: int) -> bytes:
            """invoker row compute: r6 = row index.  Native: r3 = r6 ; r0 = 0xC (return to 0x02243F66)."""
            b = EffectBuilder()
            b.ldr_const(3, 0x3fff)
            b.insn("CMP", "R6, R3")
            b.insn("BGT", "virt")
            b.insn("ADD", "R3, R6, #0x0")
            b.insn("MOV", "R0, #0xC")
            b.insn("BX", "LR")
            b.label("virt")
            b.insn("LSR", "R0, R6, #0x8")
            b.insn("SUB", "R0, #0x40")
            b.insn("LSL", "R0, R0, #0x6")
            b.ldr_const(3, O5.CAVE_RUL_ROWS)
            b.insn("ADD", "R0, R0, R3")
            b.insn("LDR", "R3, [R0, #0x4]")
            b.ldr_const(6, H3_RESUME | 1)
            b.insn("BX", "R6")
            return b.assemble(base, pad="nop")


        def h4_stub(base: int) -> bytes:
            """BL'd from ARM9 0x02023566 with r0 = cid, r1 = LIST B, r2 = 0x24 (then `pop {r4,pc}`)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(BSEARCH, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.call_addr(C3.CAVE3_RUL_FINDK, R4)
            b.insn("ADD", "R0, #0x1")
            b.insn("BEQ", "out")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def h5_stub(base: int) -> bytes:
            """End-Phase registry row resolver (r0 = ctx, r1 = row cid): every big ruler, like adjacent rows."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.ldr_const(4, C3.CAVE3_RUL_EPLIST)
            b.label("lp")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "none")
            b.call_addr(EP_POSTER, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "out")
            b.insn("ADD", "R4, #0x2")
            b.insn("B", "lp")
            b.label("none")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def h6_stub(base: int, prev: int | None = None) -> bytes:
            """GY->banished gate 0x021C71C8: r0 = cid (live after), r1 dead; exit Z=1 to post.
            A BIG ruler -> Z=1 (babies have no C4: posting for them builds an empty chain link).  Anything else -> `prev` (the stub the site called before us -- eclipse_wyvern's in the
            chain, whose flags we return untouched: POP keeps them), or on a stock ROM the native 0x1CF6 compare."""
            b = EffectBuilder()
            b.ldr_const(1, 0x1CF6)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "ret")
            b.insn("PUSH", "{R0, R2, R3, LR}")
            b.call_addr(C3.CAVE3_RUL_FINDK)
            b.insn("LSR", "R0, R0, #0x2")
            b.insn("BNE", "other")
            b.insn("MOV", "R1, #0x0")
            b.insn("CMP", "R1, R1")
            b.insn("POP", "{R0, R2, R3, PC}")
            b.label("other")
            if prev:
                b.insn("LDR", "R0, [SP, #0x0]")
                b.call_addr(prev)
            else:
                b.insn("MOV", "R1, #0x0")
                b.insn("CMP", "R0, R1")
            b.insn("POP", "{R0, R2, R3, PC}")
            b.label("ret")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def h7_stub(base: int) -> bytes:
            """0x021D1300's per-cid override switch entry: r5 = cid, [sp+0x30] = destination zone.
            A BIG ruler going to 0x0F -> the banish leaf 0x021D1D3E (babies have no C4); POP / LDR-literal keep the flags, so
            one `beq` after the shared pop picks leaf (Z from `cmp dest, #0xf`) vs native (Z=0 from the k gate); everything else replays the native compare."""
            b = EffectBuilder()
            b.insn("PUSH", "{R0, R2, R3, LR}")
            b.call_addr(C3.CAVE3_RUL_FINDK, R5)
            b.insn("LSR", "R0, R0, #0x2")
            b.insn("BNE", "native")
            b.insn("LDR", "R0, [SP, #0x40]")
            b.insn("CMP", "R0, #0xF")
            b.label("native")
            b.insn("POP", "{R0, R2, R3}")
            b.ldr_const(1, 0x1d98)
            b.insn("BEQ", "leaf")
            b.insn("CMP", "R5, R1")
            b.insn("POP", "{PC}")
            b.label("leaf")
            b.insn("POP", "{R1}")
            b.ldr_const(1, H7_LEAF | 1)
            b.insn("BX", "R1")
            return b.assemble(base, pad="nop")


        def h8a_stub(base: int) -> bytes:
            """Leave-mask bsearch BL @0x021C810C (r0 = r4 = cid, r1-r3 = bsearch args; r1-r3 dead after).  A ruler skips
            the bsearch (no ruler owns a mask row) and asks ov5 CAVE_RUL_LEAVE for a virtual row; anything else runs the
            native bsearch with its arguments restored.  Split over two cave3 runs (no run left that holds 0x1C B):
            this one tail-enters h8b_stub's run at CAVE3_RUL_H8B."""
            b = EffectBuilder()
            b.insn("PUSH", "{R0, R1, R2, R3, LR}")
            b.call_addr(C3.CAVE3_RUL_FINDK)
            b.insn("BMI", "h8a_nat")
            b.call_addr(O5.CAVE_RUL_LEAVE)
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{PC}")
            b.label("h8a_nat")
            b.call_addr(C3.CAVE3_RUL_H8B)
            return b.assemble(base, pad="nop")


        def h8b_stub(base: int) -> bytes:
            b = EffectBuilder()
            b.insn("POP", "{R0, R1, R2, R3}")
            b.call_addr(H8_BSEARCH)
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        H8_FRAGS = ((C3.CAVE3_RUL_H8A, 0x14, h8a_stub), (C3.CAVE3_RUL_H8B, 0x08, h8b_stub))


        def leave_stub(base: int) -> bytes:
            """H8 body (ruler cids only).  Entered with 5 words pushed by H8A, so the dispatcher's packed leave word
            [sp+0x200] is at [sp+0x214].  dest = (w >> 19) & 0xF (0x021CA996's own unpack); 0xF -> the virtual row.
            r0 = FINDK's k: a baby (k >= len(BIGS)) has no C4 -> 0 (no row), else it posts a handler-less chain link."""
            b = EffectBuilder()
            b.insn("LSR", "R0, R0, #0x2")
            b.insn("BNE", "no")
            b.insn("LDR", "R0, [SP, #0x214]")
            b.insn("LSL", "R0, R0, #0x9")
            b.insn("LSR", "R0, R0, #0x1C")
            b.insn("CMP", "R0, #0xF")
            b.insn("BNE", "no")
            b.ldr_const(0, O5.CAVE_RUL_LVROW)
            b.insn("BX", "LR")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def miss_stub(base: int) -> bytes:
            """BL'd from 0x021E510A (the "You can" body 0x021E50DC's call of the miss-timing test 0x021EE0E0(desc)).
            A ruler is an "IF" card (C4 "If this card is banished: You can") -> 0 = never miss; everything else ->
            the native cid tree unchanged.  ov3: every optional trigger in every mode passes here."""
            b = EffectBuilder()
            b.insn("PUSH", "{R0, LR}")
            b.insn("LDRH", "R0, [R0, #0x0]")
            b.call_addr(C3.CAVE3_RUL_FINDK)
            b.insn("BMI", "nat")
            b.insn("POP", "{R0}")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{PC}")
            b.label("nat")
            b.insn("POP", "{R0}")
            b.call_addr(MISS_TEST)
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def precheck_stub(base: int, key: int, tail: int) -> bytes:
            """next_card.precheck's exact shape (effect_verify.bl_reaches follows it): key -> 1, else tail-call."""
            b = EffectBuilder()
            b.ldr_const(3, key)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "miss")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("miss")
            b.ldr_const(3, tail | 1)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")


        BABIES = [r["cid"] for r in RULERS if not r["big"]]
        SUM_SITE, ATK_SITE = 0x02268090, 0x021A4AC6    # bl 0x02022E14: list 0x0228F708 (source cid) / 0x0226D6F8 (node key)
        PRECHECK_SIZE = 0x18
        NEXT_KEY = 0x1B22                               # next_card's precheck key (its host may front SUM_SITE)


        def _sum_chain() -> list:
            return [C3.CAVE3_RUL_PC0 + i * PRECHECK_SIZE for i in range(4)]


        def _atk_chain() -> list:
            return [C3.CAVE3_RUL_PC4 + i * PRECHECK_SIZE for i in range(2)] + \
                   [C3.CAVE3_RUL_PC6 + i * PRECHECK_SIZE for i in range(2)]


        OV3_STUBS = (               # (name, cave3 constant name, source builder)
            ("findk", "CAVE3_RUL_FINDK", findk_stub),
            ("h1", "CAVE3_RUL_H1", h1_stub),
            ("h2", "CAVE3_RUL_H2", h2_stub),
            ("h3", "CAVE3_RUL_H3", h3_stub),
            ("h4", "CAVE3_RUL_H4", h4_stub),
            ("h5", "CAVE3_RUL_H5", h5_stub),
            ("h7", "CAVE3_RUL_H7", h7_stub),
            ("miss", "CAVE3_RUL_MISS", miss_stub),
        )


        # =================================================================================================
        # ov5 card logic
        # =================================================================================================
        def crit_stub(base: int) -> bytes:
            """Virtual criteria row handler (row r0, side r1, param r2).  Mode from the ACTING descriptor:
               zone 0xE (GY ignition)                       -> banish builders (hand + GY, FILT)
               zone 0xB, cost phase, pass < 2, mode 1       -> banish builders
               zone 0xB, cost phase, pass < 2, mode 2       -> hand LIST builder 0x0223C16D + FILT (big: <attr> only,
                                                               baby: <attr> or Dragon).  NOT 0x02242105: that row is
                                                               INDEX-style (tests hand[param] only) -> an empty list
                                                               under the picker = the BUILD 3 freeze.
               zone 0xB otherwise (target step / C3 cond)   -> the card's C3 row
               anything else (C4 trigger, no/foreign desc)  -> SEARCH row (Deck, EARTH Dragon)"""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("ADD", "R7, R2, #0x0")
            b.ldr_const(0, ACTING)
            b.insn("LDR", "R6, [R0, #0x50]")
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "search")
            b.insn("LDRH", "R0, [R6, #0x0]")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "search")
            b.insn("LDRB", "R0, [R6, #0x3]")
            b.insn("CMP", "R0, #0xE")
            b.insn("BEQ", "banish")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "search")
            b.ldr_const(0, STATE)
            b.insn("LDR", "R0, [R0, #0x7C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "gyt")
            b.insn("LDRH", "R0, [R6, #0x12]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BGE", "gyt")
            b.insn("LDRH", "R0, [R6, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "discard")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "banish")
            b.label("gyt")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R0, #0x24")
            b.insn("LDR", "R3, [R0, #0x4]")
            b.insn("B", "call")
            b.label("discard")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, O5.CAVE_RUL_FILT | 1)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(HAND_BUILDER, via=R6)
            b.insn("B", "out")
            b.label("search")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R0, #0xC")
            b.ldr_const(3, SEARCH_H)
            b.label("call")
            b.insn("ADD", "R1, R4, #0x0")
            b.insn("ADD", "R2, R7, #0x0")
            b.insn("BLX", "R3")
            b.insn("B", "out")
            b.label("banish")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, BANISH_FLAGS)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, O5.CAVE_RUL_FILT | 1)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(HAND_BUILDER, via=R6)
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, BANISH_FLAGS)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, O5.CAVE_RUL_FILT | 1)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(GY_BUILDER, via=R6)
            b.label("out")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def kbase_stub(base: int) -> bytes:
            """(r0 = cid) -> r0 = ROWS + k*0x40 (that ruler's rows + params), or 0.  Clobbers r1-r3."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.call_addr(C3.CAVE3_RUL_FINDK)
            b.insn("BMI", "none")
            b.insn("LSL", "R0, R0, #0x6")
            b.ldr_const(1, O5.CAVE_RUL_ROWS)
            b.insn("ADD", "R0, R0, R1")
            b.insn("POP", "{PC}")
            b.label("none")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def attr_stub(base: int) -> bytes:
            """(r0 = cid) -> r0 = that ruler's attribute (its DISCARD row word byte 3 & 7).  Clobbers r1-r3."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.call_addr(O5.CAVE_RUL_KBASE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "none")
            b.insn("ADD", "R0, #0x23")
            b.insn("LDRB", "R0, [R0, #0x0]")
            b.insn("MOV", "R1, #0x7")
            b.insn("AND", "R0, R1")
            b.label("none")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def filt_stub(base: int) -> bytes:
            """Builder filter (hand / GY list builders); at entry [sp] = &card word.  1 = keep.
            Keep = neither this card (desc[+0xC]) nor the first pick, AND: the ruler's attribute, or a Dragon -- except a
            BIG ruler's C3 discard (mode 2), which is "1 <attr> monster" only."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("LDR", "R0, [SP, #0x10]")
            b.insn("LDR", "R4, [R0, #0x0]")
            b.insn("LSL", "R0, R4, #0x11")
            b.insn("LSR", "R0, R0, #0x1F")
            b.insn("LSL", "R1, R4, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("ADD", "R6, R1, R0")
            b.ldr_const(0, ACTING)
            b.insn("LDR", "R5, [R0, #0x50]")
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRH", "R0, [R5, #0xC]")
            b.insn("CMP", "R0, R6")
            b.insn("BEQ", "no")
            b.insn("LDRH", "R0, [R5, #0x12]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "kind")
            b.insn("LDRH", "R0, [R5, #0x14]")
            b.insn("CMP", "R0, R6")
            b.insn("BEQ", "no")
            b.label("kind")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.call_addr(O5.CAVE_RUL_KBASE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("ADD", f"R1, #0x{P_BABY:X}")
            b.insn("LDRB", "R1, [R1, #0x0]")
            b.insn("LDRH", "R2, [R5, #0x18]")
            b.insn("CMP", "R2, #0x2")
            b.insn("BNE", "dok")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "dok")
            b.insn("MOV", "R1, #0x0")
            b.insn("B", "keep")
            b.label("dok")
            b.insn("MOV", "R1, #0x1")
            b.label("keep")
            b.insn("LSL", "R1, R1, #0x8")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "R0, #0x23")
            b.insn("LDRB", "R0, [R0, #0x0]")
            b.insn("MOV", "R2, #0x7")
            b.insn("AND", "R0, R2")
            b.insn("ORR", "R0, R1")
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("LSL", "R0, R4, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(ATTR, via=R3)
            b.insn("MOV", "R1, #0x7")
            b.insn("AND", "R0, R1")
            b.insn("LSL", "R1, R6, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "yes")
            b.insn("LSR", "R0, R6, #0x8")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LSL", "R0, R4, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("get_race", via=R3)
            b.insn("CMP", f"R0, #0x{RACE_DRAGON:X}")
            b.insn("BEQ", "yes")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def count_stub(base: int) -> bytes:
            """(desc) -> r0 = (hand attr-or-Dragon << 16) | (hand attr << 8) | (hand+GY attr-or-Dragon); monsters only,
            self included.  Frame: [0] attr, [4] elig, [8] hand attr, [0xC] hand flag, [0x10] scratch, [0x14] hand elig."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x18")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(O5.CAVE_RUL_ATTR, via=R3)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("STR", "R0, [SP, #0x14]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, STRIDE)
            b.insn("MUL", "R0, R1")
            b.ldr_const(7, PLAYER)
            b.insn("ADD", "R7, R7, R0")
            b.insn("LDR", f"R0, [R7, #0x{HAND_CNT:X}]")
            b.ldr_const(1, HAND_ARR)
            b.insn("ADD", "R1, R7, R1")
            b.insn("MOV", "R2, #0x1")
            b.bl_label("scan")
            b.insn("LDR", f"R0, [R7, #0x{GY_CNT:X}]")
            b.ldr_const(1, GY_ARR)
            b.insn("ADD", "R1, R7, R1")
            b.insn("MOV", "R2, #0x0")
            b.bl_label("scan")
            b.insn("LDR", "R0, [SP, #0x14]")
            b.insn("LSL", "R0, R0, #0x8")
            b.insn("LDR", "R1, [SP, #0x8]")
            b.insn("ORR", "R0, R1")
            b.insn("LSL", "R0, R0, #0x8")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("ORR", "R0, R1")
            b.insn("ADD", "SP, #0x18")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("scan")
            b.insn("PUSH", "{LR}")
            b.insn("STR", "R2, [SP, #0x10]")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.label("slp")
            b.insn("CMP", "R5, #0x0")
            b.insn("BLE", "sdone")
            b.insn("LDR", "R4, [R6, #0x0]")
            b.insn("LSL", "R4, R4, #0x12")
            b.insn("LSR", "R4, R4, #0x12")
            b.call_addr(ATTR, R4, via=R3)
            b.insn("MOV", "R1, #0x7")
            b.insn("AND", "R0, R1")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("SUB", "R0, R0, R1")
            b.insn("STR", "R0, [SP, #0x14]")
            b.call("get_race", R4, via=R3)
            b.insn("CMP", "R0, #0x17")
            b.insn("BGE", "snext")
            b.insn("LDR", "R1, [SP, #0x14]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "sdrag")
            b.insn("LDR", "R1, [SP, #0x10]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "selig")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("ADD", "R1, #0x1")
            b.insn("STR", "R1, [SP, #0xC]")
            b.insn("B", "selig")
            b.label("sdrag")
            b.insn("CMP", f"R0, #0x{RACE_DRAGON:X}")
            b.insn("BNE", "snext")
            b.label("selig")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [SP, #0x10]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "snext")
            b.insn("LDR", "R0, [SP, #0x18]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x18]")
            b.label("snext")
            b.insn("ADD", "R6, #0x4")
            b.insn("SUB", "R5, #0x1")
            b.insn("B", "slp")
            b.label("sdone")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def mask_stub(base: int) -> bytes:
            """(desc) -> bit 0 = C1 legal (big only: SS gate + >= 2 others to banish), bit 1 = C3 legal (HAND desc only:
            a discard candidate besides this card + the card's C3 checks: CHK_SS may SS / CHK_ROW a C3-row candidate /
            CHK_FIELD any card on the field)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("MOV", "R6, #0x0")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(O5.CAVE_RUL_KBASE, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("BEQ", "out")
            b.insn("ADD", f"R7, #0x{P_RES:X}")
            b.call_addr(O5.CAVE_RUL_COUNT, R4, via=R3)
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", f"R0, [R7, #0x{P_BABY - P_RES:X}]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "c3")
            b.call_addr(CAN_SS, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "c3")
            b.insn("LSL", "R0, R5, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("CMP", "R0, #0x3")
            b.insn("BLT", "c3")
            b.insn("MOV", "R6, #0x1")
            b.label("c3")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "out")
            b.insn("LDRB", f"R0, [R7, #0x{P_BABY - P_RES:X}]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "big")
            b.insn("LSR", "R0, R5, #0x10")
            b.insn("B", "have")
            b.label("big")
            b.insn("LSL", "R0, R5, #0x10")
            b.insn("LSR", "R0, R0, #0x18")
            b.label("have")
            b.insn("CMP", "R0, #0x2")
            b.insn("BLT", "out")
            b.insn("LDRB", f"R5, [R7, #0x{P_CHK - P_RES:X}]")
            b.insn("MOV", f"R0, #0x{CHK_SS:X}")
            b.insn("AND", "R0, R5")
            b.insn("BEQ", "nss")
            b.call_addr(CAN_SS, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "out")
            b.label("nss")
            b.insn("MOV", f"R0, #0x{CHK_ROW:X}")
            b.insn("AND", "R0, R5")
            b.insn("BEQ", "nrow")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(CNT, R0, R1, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "out")
            b.label("nrow")
            b.insn("MOV", f"R0, #0x{CHK_FIELD:X}")
            b.insn("AND", "R0, R5")
            b.insn("BEQ", "ok3")
            b.call_addr(COUNT_CARDS, 0, via=R3)
            b.insn("ADD", "R5, R0, #0x0")
            b.call_addr(COUNT_CARDS, 1, via=R3)
            b.insn("ADD", "R0, R0, R5")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "out")
            b.label("ok3")
            b.insn("MOV", "R0, #0x2")
            b.insn("ORR", "R6, R0")
            b.label("out")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def cond_h_stub(base: int) -> bytes:
            """HAND +0C (desc, arg)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.call_addr(ONCE_CHECK, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(O5.CAVE_RUL_MASK, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def cond_g_stub(base: int) -> bytes:
            """GY +0C (desc, arg): OPT, >= 2 others to banish, then the native GY self-SS gate."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "gate")
            b.call_addr(ONCE_CHECK, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(O5.CAVE_RUL_COUNT, R4, via=R3)
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("CMP", "R0, #0x3")
            b.insn("BLT", "no")
            b.label("gate")
            b.call_addr(GY_REVIVE_GATE, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def cond_b_stub(base: int) -> bytes:
            """BAN +0C (desc, arg): OPT, then a Deck candidate exists (criteria count -> SEARCH row)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "gate")
            b.call_addr(ONCE_CHECK, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.label("gate")
            b.call_addr(DECK_COND, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def cond_ep_stub(base: int) -> bytes:
            """EP cls1 +0C (desc, arg): the opponent's turn, and this monster's zone word bit 4 (was SS'd)."""
            b = EffectBuilder()
            b.ldr_const(1, TURN)
            b.insn("LDR", "R1, [R1, #0x34]")
            b.insn("LDRB", "R2, [R0, #0x2]")
            b.insn("CMP", "R1, R2")
            b.insn("BEQ", "no")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R2, R1")
            b.ldr_const(1, STRIDE)
            b.insn("MUL", "R2, R1")
            b.insn("LDRB", "R1, [R0, #0x3]")
            b.insn("MOV", "R3, #0x14")
            b.insn("MUL", "R1, R3")
            b.insn("ADD", "R2, R2, R1")
            b.ldr_const(1, PLAYER + 0x44)
            b.insn("ADD", "R1, R1, R2")
            b.insn("LDR", "R1, [R1, #0x0]")
            b.insn("MOV", "R2, #0x10")
            b.insn("AND", "R1, R2")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def cost_stub(base: int) -> bytes:
            """HAND/GY +10 (desc, arg), phase machine on [STATE+0x7C]:
               0  mode: GY -> 1; hand -> MASK: both legal -> "Use which effect?" (phase 1), else the one
               1  mode = answer + 1
               2  desc[+0x18] = mode, desc[+0x12] = 0 already; message (banish / discard prompt)
               3  picker (acting desc = ours, so CRIT serves the right list)
               4  store the pick's ref at desc[+0x14 + 2*pass]; banish: pass < 2 -> 2; else -> 5
               5  commit: banish both (hand / GY) | discard this card + the pick; OPT stamp; return 1
               Discard resets desc[+0x12] to 0: the target step that follows appends its pick at desc[+0x14 + 2*desc[+0x12]]
               (0x022345F4) and the revive core reads entry 0 -- leaving it at 2 put the target on the mode halfword +0x18
               (notes/redox-c3-revive-findings.md).  The driver zeroes [STATE+0x7C] before +0x14, so CRIT still serves gyt."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("ph")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, STATE)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "ph1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "ph2")
            b.insn("CMP", "R0, #0x3")
            b.insn("BEQ", "ph3")
            b.insn("CMP", "R0, #0x4")
            b.insn("BEQ", "ph4")
            b.insn("B", "ph5")
            b.label("ph0")
            b.insn("MOV", "R7, #0x1")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xE")
            b.insn("BEQ", "setmode")
            b.call_addr(O5.CAVE_RUL_MASK, R4, via=R3)
            b.insn("CMP", "R0, #0x3")
            b.insn("BEQ", "ask")
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("CMP", "R7, #0x0")
            b.insn("BNE", "setmode")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.insn("B", "ret")
            b.label("ask")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.ldr_const(1, TITLE)
            b.ldr_const(2, LABEL_C1)
            b.ldr_const(3, LABEL_C3)
            b.call_addr(PROMPT, via=R7)
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("B", "yield")
            b.label("ph1")
            b.ldr_const(0, CHOICE)
            b.insn("LDR", "R7, [R0, #0x34]")
            b.insn("ADD", "R7, #0x1")
            b.label("setmode")
            b.insn("STRH", "R7, [R4, #0x18]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("B", "yield")
            b.label("ph2")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{MSG_BANISH:X}")
            b.insn("LDRH", "R2, [R4, #0x18]")
            b.insn("CMP", "R2, #0x2")
            b.insn("BNE", "msg")
            b.insn("MOV", f"R1, #0x{MSG_DISCARD:X}")
            b.label("msg")
            b.call_addr(MESSAGE, via=R3)
            b.insn("B", "next")
            b.label("ph3")
            b.ldr_const(0, ACTING)
            b.insn("STR", "R4, [R0, #0x50]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x6")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, 0, via=R7)
            b.insn("B", "next")
            b.label("ph4")
            b.call_addr(READBACK, via=R3)
            b.insn("LDR", "R1, [R0, #0x0]")
            b.insn("LSL", "R0, R1, #0x11")
            b.insn("LSR", "R0, R0, #0x1F")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("LSL", "R2, R0, #0x1")
            b.insn("ADD", "R2, R4, R2")
            b.insn("STRH", "R1, [R2, #0x14]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.insn("MOV", "R1, #0x5")
            b.insn("LDRH", "R2, [R4, #0x18]")
            b.insn("CMP", "R2, #0x2")
            b.insn("BEQ", "setp")
            b.insn("CMP", "R0, #0x2")
            b.insn("BGE", "setp")
            b.insn("MOV", "R1, #0x2")
            b.label("setp")
            b.insn("STR", "R1, [R6, #0x7C]")
            b.insn("B", "yield")
            b.label("ph5")
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "discard")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R7, #0x0")
            b.label("blp")
            b.insn("LSL", "R0, R7, #0x1")
            b.insn("ADD", "R0, R4, R0")
            b.insn("LDRH", "R6, [R0, #0x14]")
            b.call_addr(HAND_INDEX, R5, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "bgy")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(HAND_BANISH, R5, via=R3)
            b.insn("B", "bnx")
            b.label("bgy")
            b.call_addr(REF_TO_WORD, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "bnx")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(GY_BANISH, R5, R1, 0, via=R3)
            b.label("bnx")
            b.insn("ADD", "R7, #0x1")
            b.insn("CMP", "R7, #0x2")
            b.insn("BLT", "blp")
            b.call_addr(CHAIN_POP, via=R3)
            b.insn("B", "stamp")
            b.label("discard")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0xC]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "d2")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(COST_DISCARD, R5, via=R3)
            b.label("d2")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x14]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "stamp")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(COST_DISCARD, R5, via=R3)
            b.label("stamp")
            b.call_addr(COPY_EXEMPT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R7)
            b.label("done")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("next")
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.label("yield")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def res_h_stub(base: int) -> bytes:
            """HAND +04: mode 2 (C3) -> the card's C3 resolver (PARAMS); else (C1) -> SS this card from the hand."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.ldr_const(3, RES_HAND_SS)
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "call")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(O5.CAVE_RUL_KBASE, via=R3)
            b.insn("LDR", f"R3, [R0, #0x{P_RES:X}]")
            b.label("call")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("ADD", "R2, R6, #0x0")
            b.insn("BLX", "R3")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def tgt_h_stub(base: int) -> bytes:
            """HAND +14: only C3, and only for a card whose C3 targets (PARAMS +4 != 0)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "one")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(O5.CAVE_RUL_KBASE, via=R3)
            b.insn("LDR", f"R3, [R0, #0x{P_TGT:X}]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "one")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("ADD", "R2, R6, #0x0")
            b.insn("BLX", "R3")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def res_b_stub(base: int) -> bytes:
            """BAN +04: stamp the OPT at the resolver's first phase, then the native Deck->hand resolver."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.ldr_const(0, STATE)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "go")
            b.call_addr(COPY_EXEMPT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "go")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R7)
            b.label("go")
            b.call_addr(RES_SEARCH, R4, R5, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def slot2_stub(base: int) -> bytes:
            """HAND +08 for a card whose C3 targets on the board (Blaster).  (desc, side, zone) -> accept.
            MEASURED (BUILD 2, rom_dragon_rulers.ml2): the hand-offer gate sweeps a NON-ZERO +08 over zones 0..0xA and
            refuses the whole record when nothing passes -- so a raw board filter hid Blaster's C1 on an empty field.
            Only C3 (desc[+0x18] == 2) asks the real filter (PARAMS +0xC); every other moment accepts."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "yes")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(O5.CAVE_RUL_KBASE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "yes")
            b.insn("LDR", f"R3, [R0, #0x{P_SLOT2:X}]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("ADD", "R2, R6, #0x0")
            b.insn("BLX", "R3")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        OV5_CODE = (                # (CAVE_* name, builder, reserve)
            ("CAVE_RUL_CRIT", crit_stub, 0xE0),
            ("CAVE_RUL_KBASE", kbase_stub, 0x20),
            ("CAVE_RUL_ATTR", attr_stub, 0x20),
            ("CAVE_RUL_FILT", filt_stub, 0xC0),
            ("CAVE_RUL_COUNT", count_stub, 0x100),
            ("CAVE_RUL_MASK", mask_stub, 0xD0),
            ("CAVE_RUL_CONDH", cond_h_stub, 0x40),
            ("CAVE_RUL_CONDG", cond_g_stub, 0x50),
            ("CAVE_RUL_CONDB", cond_b_stub, 0x40),
            ("CAVE_RUL_CONDEP", cond_ep_stub, 0x40),
            ("CAVE_RUL_COST", cost_stub, 0x200),
            ("CAVE_RUL_RESH", res_h_stub, 0x40),
            ("CAVE_RUL_TGTH", tgt_h_stub, 0x40),
            ("CAVE_RUL_RESB", res_b_stub, 0x50),
            ("CAVE_RUL_SLOT2", slot2_stub, 0x40),
            ("CAVE_RUL_LEAVE", leave_stub, 0x20),
        )


        def _a(name: str) -> int:
            return getattr(O5, name)


        def vrec_blob() -> bytes:
            out = b""
            for r in RULERS:
                recs = [
                    (_a("CAVE_RUL_RESH") | 1, _a("CAVE_RUL_SLOT2") | 1 if r["slot2"] else 0, _a("CAVE_RUL_CONDH") | 1,
                     _a("CAVE_RUL_COST") | 1,
                     _a("CAVE_RUL_TGTH") | 1),
                    (RES_GY_SS, 0, _a("CAVE_RUL_CONDG") | 1, _a("CAVE_RUL_COST") | 1, 0) if r["big"] else None,
                    (_a("CAVE_RUL_RESB") | 1, 0, _a("CAVE_RUL_CONDB") | 1, TAG_YOU_CAN, 0) if r["big"] else None,
                    (RES_RETURN, 0, _a("CAVE_RUL_CONDEP") | 1, TAG_MANDATORY, 0) if r["big"] else None,
                ]
                for rec in recs:
                    out += struct.pack("<HH5I", r["cid"], 0, *rec) if rec else bytes(REC_SIZE)
            return out


        def rows_blob() -> bytes:
            out = b""
            for r in RULERS:
                cid = r["cid"]
                aux, handler, word = r["c3row"]
                out += struct.pack("<HHII", cid, 0xFFFF, _a("CAVE_RUL_CRIT") | 1, 0 if r["big"] else 1)  # word bit0 = baby
                out += struct.pack("<HHII", cid, 0xFFFF, SEARCH_H, r["search"])
                out += struct.pack("<HHII", cid, 0xFFFF, DISCARD_H, (r["attr"] << 24) | 2)
                out += struct.pack("<HHII", cid, aux, handler, word)
                out += struct.pack("<IIBBHI", r["res_c3"], r["tgt_c3"], r["chk"], 0 if r["big"] else 1, 0, r["slot2"])
            return out


        REV_PRESENT = False         # set by main() from the input ROM: Revolution Synchron's virtual GY row is installed
        GY_SITE_SET = {s for s, _ in gyv.GY_SITES}
        REV_GY_STUBS = {rev.H4_ADDR, rev.H5_ADDR, rev.H6_ADDR, rev.H7_ADDR}


        EXTRA_GY_ROWS: list = []    # rows a LATER step appended (sekkas_light); verify() reads them from the ROM


        def _gy_rows() -> list:
            """Virtual GY rows 60.. in order: Revolution Synchron's row FIRST when it is in the build (its row 60 is
            unchanged), then the big rulers, then any rows a later step appended (EXTRA_GY_ROWS)."""
            rows = [tuple(rev.GYREG_ROW)] if REV_PRESENT else []
            return rows + [(cid,) + tuple(gyv.GY_FAMILY) for cid in BIGS] + list(EXTRA_GY_ROWS)


        def _extra_gy_rows(rom) -> list:
            """Grapha-family rows sitting after our own rows in CAVE_RUL_GYROWS (0x60 = 6 rows max)."""
            base = len(_gy_rows()) - len(EXTRA_GY_ROWS)
            out = []
            for i in range(base, 6):
                r = struct.unpack("<4I", ov5_cave.read_cave(rom, O5.CAVE_RUL_GYROWS + i * 16, 16))
                if r[1:] != tuple(gyv.GY_FAMILY):
                    break
                out.append(r)
            return out


        def gyrows_blob() -> bytes:
            return b"".join(struct.pack("<4I", *r) for r in _gy_rows())


        def _gy_cids() -> list:
            """Compare order for the post / has exits: Revolution's cid LAST, so a miss leaves r0 / r1 == it -- exactly
            what its shipped single-row stubs leave (the shared GY stub generators)."""
            cids = [r[0] for r in _gy_rows()]
            return cids[1:] + cids[:1] if REV_PRESENT else cids


        def gy_stubs() -> list:
            """(name, addr, reserve, blob): Rod's N-row generalisation of Revolution Synchron's H4-H7."""
            cids = _gy_cids()
            return [("gyfetch", O5.CAVE_RUL_GYFETCH, 0x20, gyv.gyfetch_stub(O5.CAVE_RUL_GYFETCH, O5.CAVE_RUL_GYROWS)),
                    ("gyexit", O5.CAVE_RUL_GYEXIT, 0x20, gyv.gyexit_stub(O5.CAVE_RUL_GYEXIT, len(cids))),
                    ("gypost", O5.CAVE_RUL_GYPOST, 0x60, gyv.gypost_stub(O5.CAVE_RUL_GYPOST, cids)),
                    ("gyhas", O5.CAVE_RUL_GYHAS, 0x50, gyv.gyhas_stub(O5.CAVE_RUL_GYHAS, cids))]


        def ov5_blobs() -> list:
            """(addr, reserve, blob, is_code)."""
            out = [(_a(n), r, f(_a(n)), True) for n, f, r in OV5_CODE]
            out += [(O5.CAVE_RUL_VREC, 0x60 * 8, vrec_blob(), False),
                    (O5.CAVE_RUL_ROWS, ROW_STRIDE * 8, rows_blob(), False),
                    (O5.CAVE_RUL_GYROWS, 0x60, gyrows_blob(), False),
                    (O5.CAVE_RUL_LVROW, 0x10, struct.pack("<HH", 0, LEAVE_LEFT_FIELD), False)]
            out += [(a, r, b, True) for _n, a, r, b in gy_stubs()]
            return out


        def ov3_blobs() -> list:
            """(addr, blob)."""
            out = []
            for _n, const, f in OV3_STUBS:
                a = getattr(C3, const)
                out.append((a, f(a)))
            out += [(C3.CAVE3_RUL_LIST, _ruler_list()), (C3.CAVE3_RUL_EPLIST, _ep_list())]
            out += [(a, cave3._checked(a, size, f(a), "")) for a, size, f in H8_FRAGS]
            return out


        # =================================================================================================
        # apply
        # =================================================================================================
        def _sites() -> list:
            """(site, stock bytes, new bytes) in ov3."""
            out = [(H1_SITE, H1_STOCK, _bl(H1_SITE, C3.CAVE3_RUL_H1)),
                   (H2_SITE, H2_STOCK, _bl(H2_SITE, C3.CAVE3_RUL_H2)),
                   (H3_SITE, H3_STOCK, _bl(H3_SITE, C3.CAVE3_RUL_H3)),
        ]
            out.append((H7_SITE, None, _bl(H7_SITE, C3.CAVE3_RUL_H7)))
            out.append((H8_SITE, _bl(H8_SITE, H8_BSEARCH), _bl(H8_SITE, C3.CAVE3_RUL_H8A)))
            out.append((MISS_SITE, _bl(MISS_SITE, MISS_TEST), _bl(MISS_SITE, C3.CAVE3_RUL_MISS)))
            for (site, stock), a in zip(gyv.GY_SITES, (O5.CAVE_RUL_GYFETCH, O5.CAVE_RUL_GYEXIT,
                                                      O5.CAVE_RUL_GYPOST, O5.CAVE_RUL_GYHAS)):
                out.append((site, stock, _bl(site, a)))
            return out


        H7_STOCK_LIT = 0x1D98


        def _bl_target(ov, site: int) -> int:
            h1, h2 = struct.unpack_from("<HH", ov, site - RAM_BASE)
            off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
            return site + 4 + (off - (1 << 23) if off & (1 << 22) else off)


        def _precheck_at(ov, t: int, ov5=None):
            """(key, tail, tail-literal address) if a bl_reaches-shape precheck sits at t, else None.  With *ov5* (the
            decompressed overlay-5 image) a precheck in the ov5 cave is read too (verify only: infernoble's Horn of
            Olifant fronts this chain from ov5)."""
            base = RAM_BASE
            if ov5 is not None and ov5_cave.OV5_RAM_BASE <= t < ov5_cave.OV5_RAM_BASE + len(ov5) - 0x18:
                ov, base = ov5, ov5_cave.OV5_RAM_BASE
            elif not RAM_BASE <= t < RAM_BASE + len(ov) - 0x18:
                return None
            hw = struct.unpack_from("<7H", ov, t - base)
            if not (hw[0] >> 8 == 0x4B and hw[1] == 0x4298 and hw[2] >> 8 == 0xD1 and hw[3] == 0x2001
                    and hw[4] == 0x4770 and hw[5] >> 8 == 0x4B and hw[6] == 0x4718):
                return None
            key = struct.unpack_from("<I", ov, ((t + 4) & ~3) + (hw[0] & 0xFF) * 4 - base)[0]
            lit = ((t + 10 + 4) & ~3) + (hw[5] & 0xFF) * 4
            return key, struct.unpack_from("<I", ov, lit - base)[0] & ~1, lit


        def _install_chain(ov, site: int, chain: list, allow_front_key: int | None) -> None:
            """Splice the babies' prechecks into the list-search chain at `site`.  If the site's first hop is a precheck
            keyed `allow_front_key` (next_card's host), we go right behind it by re-pointing ITS tail (next_card.verify
            accepts any tail); otherwise the site BL itself points at our chain head.  Our last precheck tail-calls
            whatever came after the splice point, so every earlier owner's chain (Obedience Schooled, Petiteranodon,
            the native bsearch) is still reached -- bl_reaches-shape all the way."""
            first = _bl_target(ov, site)
            pc = _precheck_at(ov, first)
            front = pc is not None and pc[0] == allow_front_key
            prev = pc[1] if front else first
            if prev == chain[0]:                                   # idempotent re-run: our chain is already spliced in
                prev = _precheck_at(ov, chain[-1])[1]
            for i, (a, key) in enumerate(zip(chain, BABIES)):
                tail = chain[i + 1] if i + 1 < len(chain) else prev
                blob = precheck_stub(a, key, tail)
                assert len(blob) <= PRECHECK_SIZE
                o = a - RAM_BASE
                assert bytes(ov[o:o + len(blob)]) in (bytes(len(blob)), blob) or _precheck_at(ov, a), f"slot {a:#x} busy"
                ov[o:o + len(blob)] = blob
            if front:
                struct.pack_into("<I", ov, pc[2] - RAM_BASE, chain[0] | 1)
                print(f"   {site:#010x}: behind next_card's precheck {first:#x} -> {[hex(a) for a in chain]} -> {prev:#x}")
            else:
                ov[site - RAM_BASE:site - RAM_BASE + 4] = _bl(site, chain[0])
                print(f"   {site:#010x}: bl -> {[hex(a) for a in chain]} -> {prev:#x}")


        def _chain_keys(ov, site: int, ov5=None) -> list:
            """Every precheck key on the path from `site` (bl_reaches shape), in order."""
            t, keys = _bl_target(ov, site), []
            for _ in range(16):
                pc = _precheck_at(ov, t, ov5)
                if pc is None:
                    break
                keys.append(pc[0])
                t = pc[1]
            return keys


        def _h7_stock(ov) -> bool:
            o = H7_SITE - RAM_BASE
            hw = struct.unpack_from("<H", ov, o)[0]
            if hw & 0xF800 != 0x4800 or (hw >> 8) & 7 != 1 or struct.unpack_from("<H", ov, o + 2)[0] != 0x428D:
                return False
            lit = ((H7_SITE + 4) & ~3) + (hw & 0xFF) * 4
            return struct.unpack_from("<I", ov, lit - RAM_BASE)[0] == H7_STOCK_LIT


        def _h6_prev(ov) -> int | None:
            """What the H6 site called before us: None on a stock ROM, else the previous stub (Eclipse Wyvern's)."""
            cur = bytes(ov[H6_SITE - RAM_BASE:H6_SITE - RAM_BASE + 4])
            if cur == H6_STOCK:
                return None
            t = _bl_target(ov, H6_SITE)
            if t != C3.CAVE3_RUL_H6:
                return t
            blob = bytes(ov[t - RAM_BASE:t - RAM_BASE + 0x30])        # re-run: recover prev from our own stub's bl
            for prev in (None,) + tuple(sorted({_bl_target(ov, t + i) for i in range(0, 0x2C, 2)})):
                if blob.startswith(h6_stub(t, prev)):
                    return prev
            raise AssertionError("H6 stub present but its previous target is unrecognisable")


        def apply_overlay(ov: bytearray) -> None:
            prev6 = _h6_prev(ov)
            h6 = h6_stub(C3.CAVE3_RUL_H6, prev6)
            o = C3.CAVE3_RUL_H6 - RAM_BASE
            assert bytes(ov[o:o + len(h6)]) in (bytes(len(h6)), h6), "H6 slot busy"
            cave3.put(ov, C3.CAVE3_RUL_H6, h6)
            ov[H6_SITE - RAM_BASE:H6_SITE - RAM_BASE + 4] = _bl(H6_SITE, C3.CAVE3_RUL_H6)
            print(f"   bl @{H6_SITE:#010x} -> H6 (prev {prev6:#x})" if prev6 else f"   bl @{H6_SITE:#010x} -> H6 (stock)")
            _install_chain(ov, SUM_SITE, _sum_chain(), NEXT_KEY)
            _install_chain(ov, ATK_SITE, _atk_chain(), None)
            for a, blob in ov3_blobs():
                cave3.put(ov, a, blob)
                print(f"   ov3 {a:#010x}  {len(blob)} B")
            for site, stock, new in _sites():
                o = site - RAM_BASE
                cur = bytes(ov[o:o + 4])
                if stock is None:
                    assert cur == new or _h7_stock(ov), f"H7 site {site:#x} not stock: {cur.hex()}"
                else:
                    ok = cur in (stock, new) or (site in GY_SITE_SET and _bl_target(ov, site) in REV_GY_STUBS)
                    assert ok, f"site {site:#x} = {cur.hex()}, expected {stock.hex()}"
                ov[o:o + 4] = new
                print(f"   bl @{site:#010x}")
            o = EP_ROW - RAM_BASE
            cur = struct.unpack_from("<II", ov, o)
            assert cur in (EP_ROW_STOCK, (C3.CAVE3_RUL_H5 | 1, 0x19C0)), f"EP row 154 = {[hex(x) for x in cur]}"
            struct.pack_into("<II", ov, o, C3.CAVE3_RUL_H5 | 1, 0x19C0)
            print(f"   EP row 154 @{EP_ROW:#010x} -> {C3.CAVE3_RUL_H5:#x}")


        def apply_arm9(rom) -> None:
            import ndspy.code
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == 0x02000000)
            d = bytearray(sec.data)
            o = H4_ARM9_SITE - 0x02000000
            new = _bl(H4_ARM9_SITE, C3.CAVE3_RUL_H4)
            stock = _bl(H4_ARM9_SITE, BSEARCH & ~1)
            assert bytes(d[o:o + 4]) in (stock, new), f"ARM9 {H4_ARM9_SITE:#x} = {bytes(d[o:o + 4]).hex()}"
            d[o:o + 4] = new
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"   ARM9 bl @{H4_ARM9_SITE:#010x} -> {C3.CAVE3_RUL_H4:#x}")


        def install_ov5(rom) -> None:
            for a, reserve, blob, code in ov5_blobs():
                if code:
                    effect_verify.assert_thumb1_only(blob, a)
                assert len(blob) <= reserve, f"{a:#x}: {len(blob)} B > reserve {reserve:#x}"
                if ov5_cave.read_cave(rom, a, len(blob)) != blob:
                    ov5_cave.install_cave(rom, a, blob, reserve=reserve)
                print(f"   ov5 {a:#010x}  {len(blob)} B / {reserve:#x}")


        def _rev_present(rom) -> bool:
            try:
                return any(ov5_cave.read_cave(rom, rev.VROW_ADDR, 4))
            except (AssertionError, IndexError, ValueError):       # ov5 not expanded yet: no shipped cave card at all
                return False



        def install(rom, view):
            nonlocal REV_PRESENT, EXTRA_GY_ROWS
            REV_PRESENT = _rev_present(rom)
            EXTRA_GY_ROWS = []
            ov = view.buf
            n = len(ov)
            apply_overlay(ov)
            assert len(ov) == n
            install_ov5(rom)
            apply_arm9(rom)

        def post(out):
            for cid_ in CIDS[:-1]:                  # the last ruler (spec.cid) is written by dsl.make, same order as the original loop
                name, desc = card_text.CARD_TEXT[cid_]["e"]
                apply_stats_and_text(out, cid=cid_, name=name.encode(), desc=desc.encode(),
                                     langs="".join(card_text.LANGS), write_text=True, **STATS[cid_])

        def check_fn(c, rom, view):
            nonlocal REV_PRESENT, EXTRA_GY_ROWS

            def check(cond, msg):
                c.ok(bool(cond), msg)

            ov = view.buf
            REV_PRESENT = _rev_present(rom)
            EXTRA_GY_ROWS = []
            EXTRA_GY_ROWS = _extra_gy_rows(rom)
            for a, blob in ov3_blobs():
                check(bytes(ov[a - RAM_BASE:a - RAM_BASE + len(blob)]) == blob, f"ov3 blob @{a:#x}")
            for site, _st, new in _sites():
                # fire_formation_tenki (a LATER step) fronts H2: 0x1777 -> its own virtual row, else tail CAVE3_RUL_H2
                # sacred_sword_seven_stars (later still) fronts Tenki's front the same way: 0x130A -> its row, else Tenki
                # disguise_copycat (latest) fronts H2 AND H3: step over its fronts (ov5_cave.dc_skip)
                fronted = (site == H2_SITE and ov5_cave.dc_skip(_bl_target(ov, site)) in (C3.CAVE3_TENKI_H2, C3.CAVE3_SSS_H2)
                           or site == H3_SITE and ov5_cave.dc_skip(_bl_target(ov, site)) == C3.CAVE3_RUL_H3
                           or site == H1_SITE and ov5_cave.dc_skip(_bl_target(ov, site)) == C3.CAVE3_RUL_H1)
                # gy_vrow_hook (a LATER step) moves the four GY sites to its 16-row table, which is built FROM
                # our CAVE_RUL_GYROWS rows (same order, same indices) -- accept that while all four sites point at it.
                from otn_enhanced.effects import gy_vrow_hook as _gyv
                lifted = site in GY_SITE_SET and _gyv.installed(rom, ov)
                check(bytes(ov[site - RAM_BASE:site - RAM_BASE + 4]) == new or fronted or lifted
                      or code_reaches(rom, site, ov5_cave.bl_dst(new, 0, site)), f"bl @{site:#x}")
            check(struct.unpack_from("<II", ov, EP_ROW - RAM_BASE) == (C3.CAVE3_RUL_H5 | 1, 0x19C0), "EP row 154")
            check(code_reaches(rom, H6_SITE, C3.CAVE3_RUL_H6), "H6 bl @0x021C71C8 reaches the H6 stub")
            t6 = C3.CAVE3_RUL_H6                          # read prev from OUR stub: a later front may own the site
            blob6 = bytes(ov[t6 - RAM_BASE:t6 - RAM_BASE + 0x30])
            prev6 = next((p for p in (None,) + tuple(sorted({_bl_target(ov, t6 + i) for i in range(0, 0x2C, 2)}))
                          if blob6.startswith(h6_stub(t6, p))), None)
            h6 = h6_stub(C3.CAVE3_RUL_H6, prev6)
            check(bytes(ov[C3.CAVE3_RUL_H6 - RAM_BASE:C3.CAVE3_RUL_H6 - RAM_BASE + len(h6)]) == h6,
                  f"H6 stub (prev {prev6 and hex(prev6)})")
            ov5img = bytes(ov5_cave._load_ov5_decompressed(rom).data)
            for site in (SUM_SITE, ATK_SITE):
                keys = [pc[0] for n in sorted(reached_nodes(rom, site))      # every precheck on ANY path, later fronts included
                        if (pc := _precheck_at(ov, n, ov5img)) is not None]
                check(all(b in keys for b in BABIES), f"babies' can't-attack prechecks on the chain @{site:#x}: "
                                                     f"{[hex(k) for k in keys]}")
            for a, _r, blob, _c in ov5_blobs():
                check(ov5_cave.read_cave(rom, a, len(blob)) == blob, f"ov5 blob @{a:#x}")
            import ndspy.code
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == 0x02000000)
            o = H4_ARM9_SITE - 0x02000000
            _h4_fronted = bytes(sec.data[o:o + 4]) in (_bl(H4_ARM9_SITE, O5.CAVE_IK_T_H4), _bl(H4_ARM9_SITE, O5.CAVE_IK_RO_H4),
                                                       _bl(H4_ARM9_SITE, O5.CAVE_DC_H4), _bl(H4_ARM9_SITE, O5.CAVE_GF_H4), _bl(H4_ARM9_SITE, O5.CAVE_BD_H4))
            check(bytes(sec.data[o:o + 4]) == _bl(H4_ARM9_SITE, C3.CAVE3_RUL_H4) or _h4_fronted
                  or code_reaches(rom, H4_ARM9_SITE, C3.CAVE3_RUL_H4),
                  "ARM9 hand-offer bl" + (" (via infernoble's Turpin front)" if _h4_fronted else ""))
            mask_cids = {struct.unpack_from("<H", ov, LEAVE_MASK_TABLE + 4 * i - RAM_BASE)[0] for i in range(LEAVE_MASK_ROWS)}
            check(not mask_cids & set(CIDS), "no ruler owns a native leave-mask row (H8 skips the bsearch for rulers)")
            out = getattr(c, "out", None)
            for cid_ in CIDS:
                if out:
                    ok_text, msg = card_text.check_rom_text(out, cid_)
                    check(ok_text, f"text {cid_:#x}: {msg}")

        return Compiled(installs=(install,), posts=(post,), checks=(check_fn,))


dragon_rulers_effects = virtual_registry_eight_dragon_rulers_banish_special_summon_from_hand_or_graveyard_return_in_end_phase_discard_effect_banish_search

SPEC = card(0x1CC6, dragon_rulers_effects())

PROPS = card_props("WIND", "Dragon", level=3, atk=500, defense=1800)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_dragon_rulers.nds")

# Names other modules read from this one (infernoble `_rul.*`, dsl.py `rul.*` / `_dr.*`): the closure of those names, verbatim from the original.
import struct

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE

from otn_enhanced.effects import cave3

from otn_enhanced.effects import ov5_cave

from otn_enhanced.effects import gy_vrow_hook as gyv

from otn_enhanced.cards import revolution_synchron as rev

from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7

REDOX, TIDAL, BLASTER, TEMPEST = 0x17CD, 0x115F, 0x1145, 0x1125   # Charcoal Inpachi / Mech Bass /

REACTAN, STREAM, BURNER, LIGHTNING = 0x0FF4, 0x115E, 0x0FEA, 0x1CC6  # Mechanicalchaser / Parrot Dragon /

ATTR_EARTH, ATTR_WATER, ATTR_FIRE, ATTR_WIND = 5, 3, 4, 6

CHK_SS, CHK_ROW, CHK_FIELD = 1, 2, 4      # C3 legality: may SS here / a C3-row candidate / any card on field

def _search(attr: int) -> int:
    return (1 << 27) | (attr << 24) | 2     # "<attr> Dragon monster" (predicate 0x0223BA24 ANDs race and attribute)

def _big(cid, attr, atk, defense, c3row, res_c3, tgt_c3, chk, slot2=0):
    return dict(cid=cid, attr=attr, level=7, atk=atk, defense=defense, big=True, search=_search(attr),
                c3row=c3row, res_c3=res_c3, tgt_c3=tgt_c3, chk=chk, slot2=slot2)

def _baby(cid, attr, level, atk, defense, big_cid):
    # "discard this card and 1 Dragon or <attr> monster; Special Summon 1 <big> from your Deck. It cannot attack
    # this turn."  Deck row = 3DS {aux = big cid, 0x4A6834 == 0x0223D075 named Deck pick, 0x00000802}.
    return dict(cid=cid, attr=attr, level=level, atk=atk, defense=defense, big=False, search=_search(attr),
                c3row=(big_cid, NAMED_DECK_H, 0x00000802), res_c3=RES_DECK_SS, tgt_c3=0,
                chk=CHK_SS | CHK_ROW, slot2=0)

def _rulers():
    return (   # k order = CAVE3_RUL_LIST order; bigs first (only they own GY / BAN / EP records)
        _big(REDOX, ATTR_EARTH, 1600, 3000, (0xFFFF, GYT_H, 0x00010002), RES_REVIVE, TGT_STEP, CHK_SS),
        _big(TIDAL, ATTR_WATER, 2600, 2000, (0xFFFF, SEARCH_H, 0x00000002), RES_DECK_SEND, 0, CHK_ROW),
        _big(BLASTER, ATTR_FIRE, 2800, 1800, (0xFFFF, SEARCH_H, _search(ATTR_FIRE)), RES_DESTROY, BOARD_STEP,
             CHK_FIELD, slot2=FIELD_FILTER),
        _big(TEMPEST, ATTR_WIND, 2400, 2200, (0xFFFF, SEARCH_H, 0x08000002), RES_SEARCH, 0, CHK_ROW),
        _baby(REACTAN, ATTR_EARTH, 4, 1800, 1200, REDOX),
        _baby(STREAM, ATTR_WATER, 4, 1600, 2000, TIDAL),
        _baby(BURNER, ATTR_FIRE, 3, 1000, 200, BLASTER),
        _baby(LIGHTNING, ATTR_WIND, 3, 500, 1800, TEMPEST),
    )

PLAYER, STRIDE = 0x0229AC94, 0xB3C

MESSAGE = 0x0219A819        # (side, code)

PICKER = 0x0219C431         # (side, 6, cid, param)

READBACK = 0x0219C511       # () -> &picked card word

REF_TO_WORD = 0x021A25E9    # (ref) -> &card word or 0

GY_BANISH = 0x021C7105      # (side, &word, 0)

HAND_BUILDER, GY_BUILDER = 0x0223C16D, 0x0223C4E9

BANISH_FLAGS = 0x10000

SEARCH_H, DISCARD_H, GYT_H = 0x0223CAD9, 0x02242105, 0x0223C9D1

RES_HAND_SS, RES_GY_SS, RES_REVIVE = 0x02206ABD, 0x0220731D, 0x02207191

TGT_STEP = 0x02235605       # off-field list-zone target step (Lightpulsar C3)

RES_SEARCH = 0x02207EF5

RES_DECK_SEND = 0x02208DD5  # Deck -> GY by the C3 row (Tidal; Uni-Zombie C2)

RES_DESTROY = 0x02204899    # destroy the declared target (Blaster; Kahkki/Gren)

BOARD_STEP = 0x02234DA5     # +14 board target step (counts with the record's +08)

FIELD_FILTER = 0x021DE5A9   # +08 "1 card on the field" (3DS Blaster 0x3E39D4, 19/19)

RES_DECK_SS = 0x02206CAD    # Special Summon 1 from the Deck by the row (Summoner Monk / Gravekeeper's Spy)

NAMED_DECK_H = 0x0223D075   # named Deck pick, aux = the cid (Dragunity Remus)

MSG_BANISH, MSG_DISCARD = 0x56, 0x29

RULERS = _rulers()

BIGS = [r["cid"] for r in RULERS if r["big"]]

H6_SITE, H6_STOCK = 0x021C71C8, bytes.fromhex("21498842")   # ldr r1,=0x1CF6 ; cmp r0,r1

C3 = cave3

def h6_stub(base: int, prev: int | None = None) -> bytes:
    """GY->banished gate 0x021C71C8: r0 = cid (live after), r1 dead; exit Z=1 to post.
    A BIG ruler -> Z=1 (babies have no C4: posting for them builds an empty chain link).  Anything else -> `prev` (the stub the site called before us -- eclipse_wyvern's in the
    chain, whose flags we return untouched: POP keeps them), or on a stock ROM the native 0x1CF6 compare."""
    b = EffectBuilder()
    b.ldr_const(1, 0x1CF6)
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "ret")
    b.insn("PUSH", "{R0, R2, R3, LR}")
    b.call_addr(C3.CAVE3_RUL_FINDK)
    b.insn("LSR", "R0, R0, #0x2")
    b.insn("BNE", "other")
    b.insn("MOV", "R1, #0x0")
    b.insn("CMP", "R1, R1")
    b.insn("POP", "{R0, R2, R3, PC}")
    b.label("other")
    if prev:
        b.insn("LDR", "R0, [SP, #0x0]")
        b.call_addr(prev)
    else:
        b.insn("MOV", "R1, #0x0")
        b.insn("CMP", "R0, R1")
    b.insn("POP", "{R0, R2, R3, PC}")
    b.label("ret")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")

REV_PRESENT = False         # set by main() from the input ROM: Revolution Synchron's virtual GY row is installed

EXTRA_GY_ROWS: list = []    # rows a LATER step appended (sekkas_light); verify() reads them from the ROM

def _gy_rows() -> list:
    """Virtual GY rows 60.. in order: Revolution Synchron's row FIRST when it is in the build (its row 60 is
    unchanged), then the big rulers, then any rows a later step appended (EXTRA_GY_ROWS)."""
    rows = [tuple(rev.GYREG_ROW)] if REV_PRESENT else []
    return rows + [(cid,) + tuple(gyv.GY_FAMILY) for cid in BIGS] + list(EXTRA_GY_ROWS)

def _bl_target(ov, site: int) -> int:
    h1, h2 = struct.unpack_from("<HH", ov, site - RAM_BASE)
    off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
    return site + 4 + (off - (1 << 23) if off & (1 << 22) else off)

def _h6_prev(ov) -> int | None:
    """What the H6 site called before us: None on a stock ROM, else the previous stub (Eclipse Wyvern's)."""
    cur = bytes(ov[H6_SITE - RAM_BASE:H6_SITE - RAM_BASE + 4])
    if cur == H6_STOCK:
        return None
    t = _bl_target(ov, H6_SITE)
    if t != C3.CAVE3_RUL_H6:
        return t
    blob = bytes(ov[t - RAM_BASE:t - RAM_BASE + 0x30])        # re-run: recover prev from our own stub's bl
    for prev in (None,) + tuple(sorted({_bl_target(ov, t + i) for i in range(0, 0x2C, 2)})):
        if blob.startswith(h6_stub(t, prev)):
            return prev
    raise AssertionError("H6 stub present but its previous target is unrecognisable")

def _rev_present(rom) -> bool:
    try:
        return any(ov5_cave.read_cave(rom, rev.VROW_ADDR, 4))
    except (AssertionError, IndexError, ValueError):       # ov5 not expanded yet: no shipped cave card at all
        return False

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

"""W - Nebula Meteorite (Normal Trap) on Last Will 0x1315.

See card_text.CARD_TEXT[0x1315] for the printed text (a custom Trap: flip a face-up LIGHT Reptile face-down, draw, and at the
End Phase Special Summon a Level 7 or higher LIGHT Reptile from the Deck). Last Will's Normal Spell record is replaced by
Trap Hole's whole card_prop record (cid swapped) so the frame renders as a Trap and Setting it does not freeze.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class normal_trap_flip_down_face_up_light_reptile_special_summon_level_7_or_higher_light_reptile_from_deck_at_end_phase:
    """W - Nebula Meteorite (Last Will 0x1315: a Normal Spell converted to a Normal Trap by copying Trap Hole's whole card_prop record with
    the cid swapped; copying only the card_type froze the game when the card was selected to Set). cls0 activation row, BOTH duplicate cls2
    rider rows, the End-Phase registry record kept, Last Will's second registry record (the "monster left the field" watcher) handed to a
    dead phantom, and the populate row repointed to a cloned Botanical Girl deck-search wrapper + custom filter (Lv >= 7 LIGHT Reptile).
    ov3-pool stubs only (every mode). Original code embedded verbatim (ov3 path)."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards.thunder_sea_horse import BUILDER, WRAPPER_BL_OFF, WRAPPER_POOL_OFF, WRAPPER_TEMPLATE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        PHANTOM_CID = 0x1449        # dead phantom (no card_prop); absorbs the donor's second registry record

        # ===========================================================================
        # Engine addresses (EU overlay 3 / ARM9; see HOWTO.md section 18 + this file's header)
        # ===========================================================================
        CLS0_BASE, CLS0_COUNT = 0x0227E64C, 0x51A
        CLS2_BASE, CLS2_COUNT = 0x02275C04, 0x2B9
        CLS_STRIDE = 0x18

        # donor's native cls rows (asserted before overwrite).  Last Will has ONE cls0
        # row and TWO cls2 rows for the same cid (the second carries the IF timing tag
        # 0x021E50DD); both cls2 rows are repointed to the rider config.
        NATIVE_CLS0 = (0x0220DFBD, 0x00000000, 0x00000000, 0x00000000, 0x00000000)   # res/sub/cond/tag/tail
        NATIVE_CLS2_ROWS = (
            (0x0220DFBD, 0x00000000, 0x021F3B95, 0x00000000, 0x00000000),
            (0x0220DFBD, 0x00000000, 0x021F3B95, 0x021E50DD, 0x00000000),
        )

        # donor's registry records.  Located by CONTENT, not address -- chain patches
        # may insert rows into earlier tables and shift this region (the same lesson
        # as TSH's _find_master_row).
        END_THUNK = 0x0225432D      # `movs r2,#0x10; bx 0x02254121` -- shared End-Phase node walker entry (KEPT)
        WATCH_THUNK = 0x0224C669    # Last Will's "monster left your field" watcher (NEUTRALIZED -> PHANTOM_CID)


        def _find_registry_recs(ov: bytearray, thunk: int, cid: int) -> list[int]:
            """Byte offsets of every {thunk, cid} effect-registry record."""
            want = struct.pack("<IHH", thunk, cid, 0)
            return [off for off in range(0, len(ov) - 8, 4) if bytes(ov[off:off + 8]) == want]


        def _find_registry_rec(ov: bytearray, thunk: int, cid: int) -> int:
            """Byte offset of the unique {thunk, cid} effect-registry record."""
            hits = _find_registry_recs(ov, thunk, cid)
            assert len(hits) == 1, (
                f"expected 1 registry record {{0x{thunk:08X}, 0x{cid:04X}}}, found {len(hits)}")
            return hits[0]

        # populate record (repointed to the custom deck filter)
        POP_BASE, POP_STRIDE, POP_COUNT = 0x022713C4, 12, 1391
        NATIVE_POP = (0xFFFF, 0x0223CA99, 0x00002002)     # donor's native b/h/fl (ATK<=1500-from-Deck wiring)
        POP_FL_NEW = 0x00000002                            # deck zone, filter applies all criteria

        # engine primitives (Thumb entry unless noted)
        ELIG_DISPATCH = 0x0224A924   # (ctx, side, zone) -> BLX cls-row +8 sub for the current event class
        ZONE_PRED = 0x021D6E40       # (ctx, side, zone, mask) -> generic per-zone predicate
        FLIP_FACEUP = 0x021C4F24     # (ctx, side, zone, 1) -> flip face-down monster face-up Defense (Eclipse rider)
        FLIP_FACEDOWN = 0x021C5894   # (ctx, side, zone) -> flip face-up monster face-down (Eclipse activation)
        SEL_OPEN = 0x021D28A4        # open an effect-resolution/selection session
        SEL_CLOSE = 0x021D2964       # close it
        NODE_ATTACH = 0x021D2584     # (p, kid, kind, instance) -> per-turn node on pseudo-zone 0xB
        IS_RESOLVE_CTX = 0x021D2B88  # nonzero in resolve/replay context
        DRAW = 0x021D12F4            # (side, count)
        # NOTE: effect_builder.PRIMITIVES' "special_summon_from_deck" 0x021D1AFC is NOT a
        # function entry (mid-function code reading an enclosing stack frame) -- calling
        # it data-aborts (diagnosed from rom_w_nebula_meteorite.ml2: CPU in the abort
        # vector, execution thrown into the duel heap).  The real path is SS_ENGINE below.
        UI_EVENT = 0x0219A818        # (player, 0x3A) -- deck-candidate selection pre-step
        UI_EV_DECKSEL = 0x3A
        SEL_REQUEST = 0x0219C430     # (player, mode, kid, crit) -- open the pick list (mode 6 = the SS driver's)
        SEL_GET = 0x0219C510         # () -> POINTER to the selected entry (0x02299458 + cursor*4)
        SEL_CURSOR = 0x0229944C      # +4 = s16 selection cursor (negative = nothing selected / cancelled)
        SS_ENGINE = 0x0226925C       # (side, &sel_entry, 1, 2, stack:[(kid<<16)|flag]) -- the Special Summon engine,
                                     # called EXACTLY like Gravekeeper's Spy's native driver 0x02206CAD does @0x02206EE0
        EFFECT_DONE = 0x021D269C     # (side) -- driver's post-summon cleanup (its state 0x78)
        CRIT_FROM_CTX = 0x02234E78   # (ctx) -> criteria word for the candidate builder
        GET_RACE = 0x0202ABB8        # ARM9 (cid) -> race        (20 = Reptile)
        GET_ATTRIBUTE = 0x0202ABC8   # ARM9 (cid) -> attribute   (1 = LIGHT)
        CID_LEVEL = 0x0202ABD8       # ARM9 (cid) -> level
        IS_MONSTER = 0x02029E60      # ARM9 (cid) -> bool

        FSM_STATE = 0x0229AAFC       # duel-FSM block: +0x70 state, +0x74 count scratch (Eclipse uses it too)
        PLAYER_BASE = 0x0229AC94     # per-player duel struct, stride 0xB3C
        PLAYER_STRIDE = 0xB3C
        DECK_COUNT_OFF = 0x10
        ZONE_CID_BASE = 0x0229ACC8   # + p*0xB3C + z*0x14 : u32 card word (cid = low 14)
        ZONE_FDOWN_BASE = 0x0229ACCE  # + p*0xB3C + z*0x14 : u16 face-down marker

        RACE_REPTILE = 20
        ATTR_LIGHT = 1
        MIN_LEVEL = 7

        # eligibility masks for ZONE_PRED (bit meanings in the header)
        MASK_ACT = 0x118             # face-down present + face-up slot empty + monster zone, any side
        MASK_RIDER = 0x015           # activator's side + face-up present + monster zone

        # cave slots
        CHECK_ADDR = ov5_cave.CAVE_WNM_CHECK          # shared LIGHT+Reptile monster core
        FILTER_ADDR = ov5_cave.CAVE_WNM_FILTER        # populate deck filter (CHECK + Lv>=7)
        WRAPPER_ADDR = ov5_cave.CAVE_WNM_WRAPPER      # cloned deck-search wrapper
        COND_ADDR = ov5_cave.CAVE_WNM_COND            # activation condition
        SUB_ACT_ADDR = ov5_cave.CAVE_WNM_SUB_ACT      # activation per-zone eligibility
        SUB_RIDER_ADDR = ov5_cave.CAVE_WNM_SUB_RIDER  # rider per-zone eligibility
        RES_ACT_ADDR = ov5_cave.CAVE_WNM_RES_ACT      # activation resolver
        RES_RIDER_ADDR = ov5_cave.CAVE_WNM_RES_RIDER  # End-Phase rider FSM resolver
        CHECK_RESERVE = 0x40
        FILTER_RESERVE = 0x40
        WRAPPER_RESERVE = 0x30
        COND_RESERVE = 0x60
        SUB_ACT_RESERVE = 0x20
        SUB_RIDER_RESERVE = 0x70
        RES_ACT_RESERVE = 0xA0
        RES_RIDER_RESERVE = 0x180
        # slot map: A5 = the shipped ov5 cave; main(ov3=True) uses A3 (cave3 pool, see _a3)
        A5 = dict(check=CHECK_ADDR, filter=FILTER_ADDR, wrapper=WRAPPER_ADDR, cond=COND_ADDR,
                  sub_act=SUB_ACT_ADDR, sub_rider=SUB_RIDER_ADDR, res_act=RES_ACT_ADDR, res_rider=RES_RIDER_ADDR)


        def _a3() -> dict:
            from otn_enhanced.effects import cave3 as c
            return dict(check=c.CAVE3_WNM_CHECK, filter=c.CAVE3_WNM_FILTER, wrapper=c.CAVE3_WNM_WRAPPER,
                        cond=c.CAVE3_WNM_COND, sub_act=c.CAVE3_WNM_SUB_ACT, sub_rider=c.CAVE3_WNM_SUB_RIDER,
                        res_act=c.CAVE3_WNM_RES_ACT, res_rider=c.CAVE3_WNM_RIDER_A, rider_b=c.CAVE3_WNM_RIDER_B)


        def _stubs3(A: dict) -> list[tuple[int, bytes]]:
            """(addr, blob) for every ov3-pool stub; sizes are the cave3 slot sizes."""
            ra, rb = _build_res_rider3(A, 0x68, 0xC0)
            return [(A[k], f(A)) for k, f in (
                ("check", _build_check), ("filter", _build_filter), ("wrapper", _build_wrapper),
                ("cond", _build_cond), ("sub_act", _build_sub_act), ("sub_rider", _build_sub_rider),
                ("res_act", _build_res_act))] + [(A["res_rider"], ra), (A["rider_b"], rb)]

        # ===========================================================================
        # PART C constants -- card name + description (written strictly IN-PLACE)
        # ===========================================================================
        # NAME: strictly IN-PLACE.  The append-and-repoint path is CONFIRMED to freeze
        # the game when the card is selected (grown name blob; boggart hit the same
        # wall, and the rom_w_nebula_meteorite.ml1/.ml2 pair proves it here: the
        # 'before' state has no name string in RAM, the frozen state has it half-loaded
        # in two buffers).  Last Will's EN name slot is 9B, so the name is shortened;
        # JP/KR (6B slots) keep the donor's original name.
        NEW_NAME = b"W Nebula"               # 8B; fits every western slot in place
        NEW_DESC = (                          # must fit the EN slot (206B); JP 136B / KR 195B slots keep their original text
            b"Flip all face-down monsters into face-up Defense. During the End Phase "
            b"this turn, flip your face-up LIGHT Reptiles face-down, draw 1 card for "
            b"each, then you can Special Summon 1 Lv7+ LIGHT Reptile from Deck"
        )
        assert len(NEW_DESC) <= 206, f"description {len(NEW_DESC)}B exceeds the 206B JP slot"
        from otn_enhanced.data.card_stats import TEXT_LANGS


        # ===========================================================================
        # Row / record locators
        # ===========================================================================
        def _find_cls_rows(ov: bytearray, base: int, count: int, cid: int) -> list[int]:
            """Byte offsets of ALL of the cid's rows in a cls table (duplicates exist:
            Last Will has two cls2 rows)."""
            boff = base - RAM_BASE
            rows = [boff + i * CLS_STRIDE for i in range(count)
                    if struct.unpack_from("<H", ov, boff + i * CLS_STRIDE)[0] == cid]
            if not rows:
                raise SystemExit(f"cls row for cid 0x{cid:04X} not found @0x{base:08X}")
            return rows


        def _find_pop(ov: bytearray, cid: int) -> int:
            boff = POP_BASE - RAM_BASE
            for i in range(POP_COUNT):
                off = boff + i * POP_STRIDE
                if struct.unpack_from("<H", ov, off)[0] == cid:
                    return off
            raise SystemExit(f"populate entry a=0x{cid:04X} not found")


        # ===========================================================================
        # Cave stubs
        # ===========================================================================
        def _build_check(A: dict | None = None) -> bytes:
            """CHECK(cid) -> 1 iff cid is a LIGHT Reptile monster (any level).

            Shared core: called by the rider eligibility (per-zone) and by the deck
            filter / deck scan (which add the Level >= 7 test on top).  Mirrors the
            3DS leaf 0x3E0E7C's attribute/race tests (same enum values: LIGHT = 1,
            Reptile = 20 -- the two games share the encoding).
            """
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, LR}")
             .insn("ADD", "R4, R0, #0x0")        # r4 = cid
             .bl(IS_MONSTER)
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "no")
             .insn("ADD", "R0, R4, #0x0")
             .bl(GET_ATTRIBUTE)
             .insn("CMP", "R0, #0x1")            # LIGHT
             .insn("BNE", "no")
             .insn("ADD", "R0, R4, #0x0")
             .bl(GET_RACE)
             .insn("CMP", "R0, #0x14")           # 20 = Reptile
             .insn("BNE", "no")
             .insn("MOV", "R0, #0x1")
             .insn("POP", "{R4, PC}")
             .label("no")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, PC}"))
            code = a.assemble(A["check"])
            assert len(code) <= CHECK_RESERVE
            assert_thumb1_only(code, A["check"])
            return code


        def _build_filter(A: dict | None = None) -> bytes:
            """Populate deck filter: candidate is a Level>=7 LIGHT Reptile monster.

            Builder ABI (proven by GK/Watt/TSH): entered via `blx` with r0 = searching
            player; the candidate-entry pointer (into the deck array) is the caller's
            [SP+0] -> [SP+8] after our 2-register push.  This is the DS port of the
            3DS type-0xA param 0xA15C0002 (byte3 0xA1 = Reptile<<3|LIGHT, byte2 0x5C =
            Level 7 or-higher, byte0 0x02 = SS-from-Deck).
            """
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, LR}")
             .insn("LDR", "R4, [SP, #0x8]")      # caller's [SP+0] = &deck entry
             .insn("LDR", "R4, [R4, #0x0]")
             .insn("LSL", "R4, R4, #0x12")
             .insn("LSR", "R4, R4, #0x12")       # r4 = candidate cid
             .insn("ADD", "R0, R4, #0x0")
             .bl(A["check"])                     # LIGHT Reptile monster?
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "reject")
             .insn("ADD", "R0, R4, #0x0")
             .bl(CID_LEVEL)
             .insn("CMP", "R0, #0x7")            # Level >= 7 ("or higher": 3DS bit6 of param byte2)
             .insn("BLT", "reject")
             .insn("MOV", "R0, #0x1")
             .insn("POP", "{R4, PC}")
             .label("reject")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, PC}"))
            code = a.assemble(A["filter"])
            assert len(code) <= FILTER_RESERVE
            assert_thumb1_only(code, A["filter"])
            return code


        def _build_wrapper(A: dict | None = None) -> bytes:
            """Clone the byte-proven Botanical deck-search wrapper; BL -> builder,
            filter-pool literal -> our custom filter | Thumb."""
            A = A or A5
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, LR}")
            b.insn("ADD", "R3, R0, #0x0")        # r3 = ctx
            b.insn("MOV", "R0, #0x2")
            b.raw(0x5E1A)                        # LDRSH R2, [R3, R0] (register form not encodable)
            b.insn("STR", "R2, [SP, #0x8]")
            b.insn("LDR", "R2, [R3, #0x8]")
            b.insn("STR", "R2, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R3, #0x0]")
            b.ldr_const(2, A["filter"] | 1)      # filter literal -> our custom filter | Thumb
            b.insn("ADD", "R3, SP, #0x8")
            b.bl(BUILDER)                        # shared deck-search builder
            b.insn("POP", "{R1, R2, R3, PC}")
            code = b.assemble(A["wrapper"], pad="nop")
            assert len(code) == len(WRAPPER_TEMPLATE)
            assert_thumb1_only(code, A["wrapper"])
            return code


        def _build_cond(A: dict | None = None) -> bytes:
            """Activation condition: at least one face-down monster on the field.

            3DS 0x3EF890: generic legality + face-down present (0x3980D8(s,z,1,1)).
            DS: scan both players' 5 monster zones for a nonzero face-down marker
            (u16 at [0x0229ACCE + p*0xB3C + z*0x14]).  In resolve/replay context the
            gate must not re-deny (TSH/PoD parity).
            """
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, R6, LR}")
             .bl(IS_RESOLVE_CTX)                 # r0 = ctx at entry
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "allow")
             .insn("MOV", "R5, #0x0")            # r5 = side
             .label("side_loop")
             .ldr_const(0, PLAYER_STRIDE)
             .insn("MUL", "R0, R5")              # r0 = side * 0xB3C
             .ldr_const(1, ZONE_FDOWN_BASE)
             .insn("ADD", "R1, R1, R0")          # r1 = face-down marker base for side
             .insn("MOV", "R6, #0x0")            # r6 = zone
             .label("zone_loop")
             .insn("LSL", "R0, R6, #0x2")
             .insn("ADD", "R0, R0, R6")          # 5*z
             .insn("LSL", "R0, R0, #0x2")        # 20*z
             .insn("LDRH", "R0, [R1, R0]")
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "allow")               # a face-down card exists
             .insn("ADD", "R6, R6, #0x1")
             .insn("CMP", "R6, #0x5")            # 5 monster zones
             .insn("BLT", "zone_loop")
             .insn("ADD", "R5, R5, #0x1")
             .insn("CMP", "R5, #0x2")
             .insn("BLT", "side_loop")
             .insn("MOV", "R0, #0x0")            # no face-down monster anywhere -> can't activate
             .insn("POP", "{R4, R5, R6, PC}")
             .label("allow")
             .insn("MOV", "R0, #0x1")
             .insn("POP", "{R4, R5, R6, PC}"))
            code = a.assemble(A["cond"])
            assert len(code) <= COND_RESERVE
            assert_thumb1_only(code, A["cond"])
            return code


        def _build_sub_act(A: dict | None = None) -> bytes:
            """Activation per-zone eligibility (cls0 +8): face-down card in a monster
            zone, either side -- generic predicate mask 0x118 (Eclipse-rider shape
            minus the opponent-side bit)."""
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, LR}")
             .insn("MOV", "R3, #0x8C")
             .insn("LSL", "R3, R3, #0x1")        # r3 = 0x118
             .bl(ZONE_PRED)
             .insn("POP", "{R4, PC}"))
            code = a.assemble(A["sub_act"])
            assert len(code) <= SUB_ACT_RESERVE
            assert_thumb1_only(code, A["sub_act"])
            return code


        def _build_sub_rider(A: dict | None = None) -> bytes:
            """Rider per-zone eligibility (cls2 +8): face-up LIGHT Reptile monster the
            ACTIVATOR controls -- mask 0x15 (side==activator + face-up present +
            monster zone) then the LIGHT+Reptile core on the zone's cid.  This is the
            3DS leaf 0x3E0E7C ported 1:1 (cat 0x15's side gate == mask bits0-1 = 1)."""
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, R6, LR}")
             .insn("ADD", "R5, R1, #0x0")        # r5 = side
             .insn("ADD", "R6, R2, #0x0")        # r6 = zone
             .insn("MOV", "R3, #0x15")
             .bl(ZONE_PRED)
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "no")
             .insn("MOV", "R0, #0x1")
             .insn("AND", "R5, R0")              # side &= 1
             .ldr_const(0, PLAYER_STRIDE)
             .insn("MUL", "R0, R5")
             .ldr_const(1, ZONE_CID_BASE)
             .insn("ADD", "R1, R1, R0")          # zone-cid base for side
             .insn("LSL", "R0, R6, #0x2")
             .insn("ADD", "R0, R0, R6")
             .insn("LSL", "R0, R0, #0x2")        # 20*z
             .insn("LDR", "R0, [R1, R0]")        # zone card word
             .insn("LSL", "R0, R0, #0x12")
             .insn("LSR", "R0, R0, #0x12")       # cid
             .bl(A["check"])                     # LIGHT Reptile monster? (returns 0/1)
             .insn("POP", "{R4, R5, R6, PC}")
             .label("no")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, R6, PC}"))
            code = a.assemble(A["sub_rider"])
            assert len(code) <= SUB_RIDER_RESERVE
            assert_thumb1_only(code, A["sub_rider"])
            return code


        def _build_res_act(A: dict | None = None) -> bytes:
            """Activation resolver (cls0 +4): flip ALL face-down monsters face-up
            Defense, then arm the End-Phase rider iff at least one was flipped.

            Mirrors Book of Eclipse's resolver 0x0222958C rider-branch loop (the
            flip-up direction) run synchronously, plus the 3DS arming rule from
            0x42E664 state 0x7E: NODE_ATTACH only when the flip count is nonzero.
            Node: (controller, cid, kind 1, instance [ctx+0xC]) -- exactly Eclipse's
            arming call; the native registry thunk 0x0225432D finds it at End Phase.
            """
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, R6, R7, LR}")
             .insn("ADD", "R4, R0, #0x0")        # r4 = ctx
             .bl(SEL_OPEN)
             .insn("MOV", "R7, #0x0")            # r7 = flip count
             .insn("MOV", "R5, #0x0")            # r5 = side
             .label("side_loop")
             .insn("MOV", "R6, #0x0")            # r6 = zone
             .label("zone_loop")
             .insn("ADD", "R0, R4, #0x0")
             .insn("ADD", "R1, R5, #0x0")
             .insn("ADD", "R2, R6, #0x0")
             .bl(ELIG_DISPATCH)                  # -> our cls0 sub (mask 0x118)
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "next")
             .insn("ADD", "R0, R4, #0x0")
             .insn("ADD", "R1, R5, #0x0")
             .insn("ADD", "R2, R6, #0x0")
             .insn("MOV", "R3, #0x1")
             .bl(FLIP_FACEUP)                    # flip face-up Defense (Eclipse's call)
             .insn("ADD", "R7, R7, #0x1")
             .label("next")
             .insn("ADD", "R6, R6, #0x1")
             .insn("CMP", "R6, #0xA")
             .insn("BLE", "zone_loop")           # zones 0..10 (mask restricts to monster zones)
             .insn("ADD", "R5, R5, #0x1")
             .insn("CMP", "R5, #0x2")
             .insn("BLT", "side_loop")
             .bl(SEL_CLOSE)
             .insn("CMP", "R7, #0x0")            # 3DS rule: arm the rider only if >=1 flipped
             .insn("BEQ", "done")
             .insn("LDRB", "R0, [R4, #0x2]")     # controller
             .insn("LDRH", "R1, [R4, #0x0]")     # cid (0x1C9B from this row)
             .insn("MOV", "R2, #0x1")            # kind 1 (walker accepts kind 1 or 2)
             .insn("LDRH", "R3, [R4, #0xC]")     # card instance (walker requires != 0)
             .bl(NODE_ATTACH)
             .label("done")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, R6, R7, PC}"))
            code = a.assemble(A["res_act"])
            assert len(code) <= RES_ACT_RESERVE
            assert_thumb1_only(code, A["res_act"])
            return code


        def _build_res_rider(A: dict | None = None) -> bytes:
            """End-Phase rider resolver (cls2 +4) -- FSM in [0x0229AAFC+0x70].

            3DS router 0x4543B8 ported stage-for-stage:
              0x80: open session; count=0; flip every face-up LIGHT Reptile the
                    activator controls face-down (eligibility -> our cls2 sub),
                    count in [FSM+0x74]                                     -> 0x7F
              0x7F: count==0 -> close, done (NO draw, NO summon -- 3DS rule).
                    Else DRAW(controller, count); inline deck scan for a Lv>=7
                    LIGHT Reptile monster; none -> close, done.
                    Else UI_EVENT(p, 0x3A)                                  -> 0x7E
              0x7E: SEL_REQUEST(p, 6, kid, CRIT_FROM_CTX(ctx))              -> 0x7D
                    (mode 6 = exactly what the native SS-from-Deck driver
                    0x02206CAD passes at 0x02206E58)
              0x7D: selection cursor < 0 (cancel -- the "you can") -> close, done.
                    Else SS_ENGINE(side, SEL_GET(), 1, 2, [(kid<<16)])      -> 0x7C
                    (byte-for-byte the driver's summon call @0x02206EE0)
              0x7C: SEL_CLOSE; EFFECT_DONE(side)  (driver's state 0x78)     -> done
            """
            A = A or A5
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, R6, R7, LR}")
             .insn("ADD", "R4, R0, #0x0")        # r4 = ctx
             .ldr_const(5, FSM_STATE)            # r5 = duel-FSM block
             .insn("LDR", "R0, [R5, #0x70]")
             .insn("CMP", "R0, #0x80")
             .insn("BEQ", "st80")
             .insn("CMP", "R0, #0x7F")
             .insn("BNE", "not7F")
             .insn("B", "st7F")
             .label("not7F")
             .insn("CMP", "R0, #0x7E")
             .insn("BNE", "not7E")
             .insn("B", "st7E")
             .label("not7E")
             .insn("CMP", "R0, #0x7D")
             .insn("BNE", "not7D")
             .insn("B", "st7D")
             .label("not7D")
             .insn("CMP", "R0, #0x7C")
             .insn("BNE", "unknown")
             .insn("B", "st7C")
             .label("unknown")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, R6, R7, PC}")
             # --- 0x80: flip own face-up LIGHT Reptiles face-down, count ------------
             .label("st80")
             .bl(SEL_OPEN)
             .insn("MOV", "R0, #0x0")
             .insn("STR", "R0, [R5, #0x74]")     # count = 0
             .insn("MOV", "R6, #0x0")            # r6 = side
             .label("r_side")
             .insn("MOV", "R7, #0x0")            # r7 = zone
             .label("r_zone")
             .insn("ADD", "R0, R4, #0x0")
             .insn("ADD", "R1, R6, #0x0")
             .insn("ADD", "R2, R7, #0x0")
             .bl(ELIG_DISPATCH)                  # -> our cls2 sub (my side + face-up LIGHT Reptile)
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "r_next")
             .insn("ADD", "R0, R4, #0x0")
             .insn("ADD", "R1, R6, #0x0")
             .insn("ADD", "R2, R7, #0x0")
             .bl(FLIP_FACEDOWN)                  # Eclipse's own flip-down call
             .insn("LDR", "R0, [R5, #0x74]")
             .insn("ADD", "R0, R0, #0x1")
             .insn("STR", "R0, [R5, #0x74]")
             .label("r_next")
             .insn("ADD", "R7, R7, #0x1")
             .insn("CMP", "R7, #0xA")
             .insn("BLE", "r_zone")
             .insn("ADD", "R6, R6, #0x1")
             .insn("CMP", "R6, #0x2")
             .insn("BLT", "r_side")
             .insn("MOV", "R0, #0x7F")
             .insn("POP", "{R4, R5, R6, R7, PC}")
             # --- 0x7F: draw per flipped card; check the Deck for a summon target ---
             .label("st7F")
             .insn("LDR", "R1, [R5, #0x74]")
             .insn("CMP", "R1, #0x0")
             .insn("BEQ", "finish")              # flipped nothing -> no draw, no summon (3DS rule)
             .insn("LDRB", "R0, [R4, #0x2]")     # controller
             .bl(DRAW)                           # draw <count>
             # inline deck scan: any Lv>=7 LIGHT Reptile monster left in the Deck?
             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("MOV", "R1, #0x1")
             .insn("AND", "R0, R1")              # p &= 1
             .ldr_const(1, PLAYER_STRIDE)
             .insn("MUL", "R1, R0")
             .ldr_const(0, PLAYER_BASE)
             .insn("ADD", "R6, R0, R1")          # r6 = player struct
             .insn("LDR", "R7, [R6, #0x10]")     # r7 = deck count
             .insn("MOV", "R0, #0xC1")
             .insn("LSL", "R0, R0, #0x2")        # 0x304
             .insn("ADD", "R6, R6, R0")          # r6 = deck array cursor
             .label("scan")
             .insn("CMP", "R7, #0x0")
             .insn("BLE", "finish")              # no qualifying card -> effect ends
             .insn("LDR", "R0, [R6, #0x0]")
             .insn("LSL", "R0, R0, #0x12")
             .insn("LSR", "R0, R0, #0x12")       # entry cid
             .bl(A["check"])                     # LIGHT Reptile monster?
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "scan_next")
             .insn("LDR", "R0, [R6, #0x0]")
             .insn("LSL", "R0, R0, #0x12")
             .insn("LSR", "R0, R0, #0x12")
             .bl(CID_LEVEL)
             .insn("CMP", "R0, #0x7")
             .insn("BGE", "found")
             .label("scan_next")
             .insn("ADD", "R6, R6, #0x4")
             .insn("SUB", "R7, R7, #0x1")
             .insn("B", "scan")
             .label("found")
             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("MOV", "R1, #0x3A")           # UI_EV_DECKSEL
             .bl(UI_EVENT)
             .insn("MOV", "R0, #0x7E")
             .insn("POP", "{R4, R5, R6, R7, PC}")
             # --- 0x7E: open the pick-1 list ----------------------------------------
             .label("st7E")
             .insn("ADD", "R0, R4, #0x0")
             .bl(CRIT_FROM_CTX)
             .insn("ADD", "R3, R0, #0x0")
             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("LDRB", "R1, [R4, #0x6]")
             .insn("EOR", "R0, R1")              # side (driver uses ctx2^ctx6)
             .insn("MOV", "R1, #0x6")            # the SS driver's list mode (0x02206E58)
             .insn("LDRH", "R2, [R4, #0x0]")     # kid
             .bl(SEL_REQUEST)
             .insn("MOV", "R0, #0x7D")
             .insn("POP", "{R4, R5, R6, R7, PC}")
             # --- 0x7D: consume the pick; Special Summon (driver-exact) -------------
             .label("st7D")
             .ldr_const(0, SEL_CURSOR)
             .insn("LDRH", "R0, [R0, #0x4]")     # s16 selection cursor
             .insn("LSL", "R0, R0, #0x10")
             .insn("BMI", "finish")              # negative = cancelled -> "you can" declined
             .insn(".HWORD", "0xB082")           # sub sp, #8  (room for the 5th argument)
             .bl(SEL_GET)                        # r0 = &selected entry
             .insn("ADD", "R1, R0, #0x0")
             .insn("LDRH", "R2, [R4, #0x0]")     # kid
             .insn("LSL", "R2, R2, #0x10")       # (kid << 16) | 0
             .insn("STR", "R2, [SP, #0x0]")      # 5th arg on the stack (driver @0x02206ED8)
             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("LDRB", "R3, [R4, #0x6]")
             .insn("EOR", "R0, R3")              # side
             .insn("MOV", "R2, #0x1")            # driver's [sp+4] default (0x02206E62)
             .insn("MOV", "R3, #0x2")            # driver's r7 default (0x02206E6C)
             .bl(SS_ENGINE)
             .insn(".HWORD", "0xB002")           # add sp, #8
             .insn("MOV", "R0, #0x7C")           # wait a state, like the driver's 0x78
             .insn("POP", "{R4, R5, R6, R7, PC}")
             # --- 0x7C: post-summon cleanup (driver's state 0x78) --------------------
             .label("st7C")
             .bl(SEL_CLOSE)
             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("LDRB", "R1, [R4, #0x6]")
             .insn("EOR", "R0, R1")              # side
             .bl(EFFECT_DONE)
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, R6, R7, PC}")
             .label("finish")
             .bl(SEL_CLOSE)
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, R6, R7, PC}"))
            code = a.assemble(A["res_rider"])
            assert len(code) <= RES_RIDER_RESERVE, f"rider {len(code)}B exceeds 0x{RES_RIDER_RESERVE:X}"
            assert_thumb1_only(code, A["res_rider"])
            return code


        def _far(prog: EffectBuilder, far: str, label: str) -> None:
            """Jump to a label in the other fragment: `b` (+-2 KB) or `bl` (far; clobbers LR)."""
            if far == "bl":
                prog.bl_label(label)
            else:
                prog.insn("B", label)


        def _res_rider3(A: dict) -> tuple[EffectBuilder, EffectBuilder]:
            """_build_res_rider ported to the builder and split for the ov3 pool (no run holds 292 B).
            Fragment A = dispatcher + state 0x80; fragment B = states 0x7F..0x7C + finish. Same
            instructions in the same order; the only additions are A's state jumps reaching B (`b`
            within +-2 KB, else `bl`, legal because LR was pushed at entry and never read again)."""
            far = "b" if abs(A["rider_b"] - A["res_rider"]) < 0x7F0 else "bl"
            a = EffectBuilder()
            b = EffectBuilder()
            a.insn("PUSH", "{R4, R5, R6, R7, LR}")
            a.insn("ADD", "R4, R0, #0")
            a.ldr_const(5, FSM_STATE)
            a.insn("LDR", "R0, [R5, #0x70]")
            a.insn("CMP", "R0, #0x80")
            a.insn("BEQ", "st80")
            a.insn("CMP", "R0, #0x7F")
            a.insn("BNE", "not7F")
            _far(a, far, "st7F")
            a.label("not7F")
            a.insn("CMP", "R0, #0x7E")
            a.insn("BNE", "not7E")
            _far(a, far, "st7E")
            a.label("not7E")
            a.insn("CMP", "R0, #0x7D")
            a.insn("BNE", "not7D")
            _far(a, far, "st7D")
            a.label("not7D")
            a.insn("CMP", "R0, #0x7C")
            a.insn("BNE", "unknown")
            _far(a, far, "st7C")
            a.label("unknown")
            a.insn("MOV", "R0, #0")
            a.insn("POP", "{R4, R5, R6, R7, PC}")
            a.label("st80")
            a.bl(SEL_OPEN)
            a.insn("MOV", "R0, #0")
            a.insn("STR", "R0, [R5, #0x74]")
            a.insn("MOV", "R6, #0")
            a.label("r_side")
            a.insn("MOV", "R7, #0")
            a.label("r_zone")
            a.insn("ADD", "R0, R4, #0")
            a.insn("ADD", "R1, R6, #0")
            a.insn("ADD", "R2, R7, #0")
            a.bl(ELIG_DISPATCH)
            a.insn("CMP", "R0, #0")
            a.insn("BEQ", "r_next")
            a.insn("ADD", "R0, R4, #0")
            a.insn("ADD", "R1, R6, #0")
            a.insn("ADD", "R2, R7, #0")
            a.bl(FLIP_FACEDOWN)
            a.insn("LDR", "R0, [R5, #0x74]")
            a.insn("ADD", "R0, R0, #1")
            a.insn("STR", "R0, [R5, #0x74]")
            a.label("r_next")
            a.insn("ADD", "R7, R7, #1")
            a.insn("CMP", "R7, #0xA")
            a.insn("BLE", "r_zone")
            a.insn("ADD", "R6, R6, #1")
            a.insn("CMP", "R6, #2")
            a.insn("BLT", "r_side")
            a.insn("MOV", "R0, #0x7F")
            a.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("st7F")
            b.insn("LDR", "R1, [R5, #0x74]")
            b.insn("CMP", "R1, #0")
            b.insn("BEQ", "finish")
            b.insn("LDRB", "R0, [R4, #2]")
            b.bl(DRAW)
            b.insn("LDRB", "R0, [R4, #2]")
            b.insn("MOV", "R1, #1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, PLAYER_STRIDE)
            b.insn("MUL", "R1, R0")
            b.ldr_const(0, PLAYER_BASE)
            b.insn("ADD", "R6, R0, R1")
            b.insn("LDR", "R7, [R6, #0x10]")
            b.insn("MOV", "R0, #0xC1")
            b.insn("LSL", "R0, R0, #2")
            b.insn("ADD", "R6, R6, R0")
            b.label("scan")
            b.insn("CMP", "R7, #0")
            b.insn("BLE", "finish")
            b.insn("LDR", "R0, [R6, #0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.bl(A["check"])
            b.insn("CMP", "R0, #0")
            b.insn("BEQ", "scan_next")
            b.insn("LDR", "R0, [R6, #0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.bl(CID_LEVEL)
            b.insn("CMP", "R0, #7")
            b.insn("BGE", "found")
            b.label("scan_next")
            b.insn("ADD", "R6, R6, #4")
            b.insn("SUB", "R7, R7, #1")
            b.insn("B", "scan")
            b.label("found")
            b.insn("LDRB", "R0, [R4, #2]")
            b.insn("MOV", "R1, #0x3A")
            b.bl(UI_EVENT)
            b.insn("MOV", "R0, #0x7E")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("st7E")
            b.insn("ADD", "R0, R4, #0")
            b.bl(CRIT_FROM_CTX)
            b.insn("ADD", "R3, R0, #0")
            b.insn("LDRB", "R0, [R4, #2]")
            b.insn("LDRB", "R1, [R4, #6]")
            b.insn("EOR", "R0, R1")
            b.insn("MOV", "R1, #6")
            b.insn("LDRH", "R2, [R4, #0]")
            b.bl(SEL_REQUEST)
            b.insn("MOV", "R0, #0x7D")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("st7D")
            b.ldr_const(0, SEL_CURSOR)
            b.insn("LDRH", "R0, [R0, #4]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("BMI", "finish")
            b.insn("SUB", "SP, #8")
            b.bl(SEL_GET)
            b.insn("ADD", "R1, R0, #0")
            b.insn("LDRH", "R2, [R4, #0]")
            b.insn("LSL", "R2, R2, #0x10")
            b.insn("STR", "R2, [SP, #0]")
            b.insn("LDRB", "R0, [R4, #2]")
            b.insn("LDRB", "R3, [R4, #6]")
            b.insn("EOR", "R0, R3")
            b.insn("MOV", "R2, #1")
            b.insn("MOV", "R3, #2")
            b.bl(SS_ENGINE)
            b.insn("ADD", "SP, #8")
            b.insn("MOV", "R0, #0x7C")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("st7C")
            b.bl(SEL_CLOSE)
            b.insn("LDRB", "R0, [R4, #2]")
            b.insn("LDRB", "R1, [R4, #6]")
            b.insn("EOR", "R0, R1")
            b.bl(EFFECT_DONE)
            b.insn("MOV", "R0, #0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("finish")
            b.bl(SEL_CLOSE)
            b.insn("MOV", "R0, #0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return a, b

        def _build_res_rider3(A: dict, size_a: int = 0x400, size_b: int = 0x400) -> list[bytes]:
            from otn_enhanced.effects import cave3
            fa, fb = _res_rider3(A)
            return cave3.asm_split([(A["res_rider"], size_a, fa), (A["rider_b"], size_b, fb)])

        def apply_effect(ov: bytearray, rom, ov3: bool = False) -> None:
            A = _a3() if ov3 else A5
            if ov3:   # ov3 compaction pool (step 0 must have run on *src*: cave3.put asserts the slot is zero)
                from otn_enhanced.effects import cave3
                assert all(A[k] % 4 == 0 for k in A5 if k != "res_rider"), "ThumbAssembler stubs need 4-aligned bases"
                for addr, blob in _stubs3(A):
                    cave3.put(ov, addr, blob)
                    print(f"A  ov3 stub @0x{addr:08X} ({len(blob)}B)")
            # --- cave stubs (grows ov5 + raises the arena-lo once; idempotent) ---
            for addr, blob, reserve, label in () if ov3 else (
                (CHECK_ADDR, _build_check(), CHECK_RESERVE, "check core"),
                (FILTER_ADDR, _build_filter(), FILTER_RESERVE, "deck filter"),
                (WRAPPER_ADDR, _build_wrapper(), WRAPPER_RESERVE, "wrapper"),
                (COND_ADDR, _build_cond(), COND_RESERVE, "act-cond"),
                (SUB_ACT_ADDR, _build_sub_act(), SUB_ACT_RESERVE, "act eligibility"),
                (SUB_RIDER_ADDR, _build_sub_rider(), SUB_RIDER_RESERVE, "rider eligibility"),
                (RES_ACT_ADDR, _build_res_act(), RES_ACT_RESERVE, "act resolver"),
                (RES_RIDER_ADDR, _build_res_rider(), RES_RIDER_RESERVE, "rider resolver"),
            ):
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"A  ov5 {label}: 0x{addr:08X} ({len(blob)}B)")

            # --- A1: cls0 activation row ---
            rows = _find_cls_rows(ov, CLS0_BASE, CLS0_COUNT, DONOR_CID)
            assert len(rows) == 1, f"expected 1 cls0 row, found {len(rows)}"
            off = rows[0]
            cur = struct.unpack_from("<5I", ov, off + 4)
            want = (A["res_act"] | 1, A["sub_act"] | 1, A["cond"] | 1, 0, 0)
            if cur == want:
                print("A1 cls0 row already repointed -> no change")
            else:
                assert cur == NATIVE_CLS0, f"cls0 row unexpected: {tuple(hex(x) for x in cur)}"
                struct.pack_into("<5I", ov, off + 4, *want)
                print(f"A1 cls0[0x{DONOR_CID:04X}] @0x{RAM_BASE + off:08X}: res/sub/cond -> cave stubs")

            # --- A2: BOTH cls2 rider rows (duplicate cid; the binary search may land
            # on either, so both get the identical rider config) ---
            rows = _find_cls_rows(ov, CLS2_BASE, CLS2_COUNT, DONOR_CID)
            assert len(rows) == len(NATIVE_CLS2_ROWS), f"expected {len(NATIVE_CLS2_ROWS)} cls2 rows, found {len(rows)}"
            want = (A["res_rider"] | 1, A["sub_rider"] | 1, 0, 0, 0)
            for off, native in zip(rows, NATIVE_CLS2_ROWS):
                cur = struct.unpack_from("<5I", ov, off + 4)
                if cur == want:
                    print(f"A2 cls2 row @0x{RAM_BASE + off:08X} already repointed -> no change")
                else:
                    assert cur == native, f"cls2 row unexpected: {tuple(hex(x) for x in cur)}"
                    struct.pack_into("<5I", ov, off + 4, *want)
                    print(f"A2 cls2[0x{DONOR_CID:04X}] @0x{RAM_BASE + off:08X}: res/sub -> cave stubs, cond/tag cleared")

            # --- A3a: End-Phase registry record (kept verbatim -- assert only) ---
            roff = _find_registry_rec(ov, END_THUNK, DONOR_CID)
            print(f"A3 registry record @0x{RAM_BASE + roff:08X} "
                  f"{{thunk 0x{END_THUNK:08X}, cid 0x{DONOR_CID:04X}}} kept as-is")

            # --- A3b: neutralize Last Will's second registry record (the "monster
            # left your field this turn" watcher) by handing it to a dead phantom.
            # (Phantom 0x1449 already owns an identical watcher record natively --
            # a duplicate is harmless, both can never fire.) ---
            hits = _find_registry_recs(ov, WATCH_THUNK, DONOR_CID)
            if hits:
                assert len(hits) == 1, f"expected 1 watcher record, found {len(hits)}"
                struct.pack_into("<H", ov, hits[0] + 4, PHANTOM_CID)
                print(f"A3 watcher record @0x{RAM_BASE + hits[0]:08X}: cid 0x{DONOR_CID:04X} -> phantom 0x{PHANTOM_CID:04X}")
            else:
                assert _find_registry_recs(ov, WATCH_THUNK, PHANTOM_CID), "watcher record vanished"
                print("A3 watcher record already neutralized -> no change")

            # --- A4: populate repoint (Special-Summon-from-Deck candidates) ---
            poff = _find_pop(ov, DONOR_CID)
            b, h, fl = struct.unpack_from("<HII", ov, poff + 2)
            want_pop = (0, A["wrapper"] | 1, POP_FL_NEW)
            if (b, h, fl) == want_pop:
                print("A4 populate already repointed -> no change")
            else:
                assert (b, h, fl) == NATIVE_POP, (
                    f"populate unexpected: b=0x{b:04X} h=0x{h:08X} fl=0x{fl:08X}")
                struct.pack_into("<HII", ov, poff + 2, *want_pop)
                print(f"A4 populate[0x{DONOR_CID:04X}] @0x{RAM_BASE + poff:08X}: "
                      f"h -> wrapper 0x{WRAPPER_ADDR | 1:08X}, fl 0x{POP_FL_NEW:08X}")

        CT_TRAP = 29                # ERA2 card_type code (bits [32:38]) -- for the verifier
        REFERENCE_NORMAL_TRAP_CID = 0x12E4   # Trap Hole (bulk_card_props' reference)


        def apply_card_prop(out_path: str) -> None:
            """Overwrite Last Will's card_prop record with Trap Hole's (cid swapped).

            Same-size 8-byte record edit, patched in place inside bin2.pac (no
            rebuild).  card_genre is deck-editor category metadata and is untouched
            (bulk_card_props' conversions don't write it either).
            """
            import ndspy.rom
            from otn_enhanced.rom.pac import parse_pac
            from otn_enhanced.data.card_stats import iter_paths as _iter_paths

            rom2 = ndspy.rom.NintendoDSRom.fromFile(out_path)
            pac_path = next(p for p in _iter_paths(rom2.filenames) if p.lower().endswith("bin2.pac"))
            fid = rom2.filenames.idOf(pac_path)
            pac = bytearray(rom2.files[fid])
            archive = parse_pac(bytes(pac), pac_path)
            cpf = next(f for f in archive.files if f.get_clean_name().lower() == "card_prop.bin")

            def _find(cid):
                for i in range((cpf.size - 8) // 8):
                    off = cpf.address + 8 + i * 8
                    if (int.from_bytes(pac[off:off + 8], "little") & 0x3FFF) == cid:
                        return off
                raise SystemExit(f"cid 0x{cid:04X} not found in card_prop.bin")

            ref = int.from_bytes(pac[_find(REFERENCE_NORMAL_TRAP_CID):][:8], "little")
            want = (ref & ~0x3FFF) | DONOR_CID          # Trap Hole's record, our cid
            off = _find(DONOR_CID)
            cur = int.from_bytes(pac[off:off + 8], "little")
            if cur == want:
                print("B  card_prop already the Trap Hole template -> no change")
                return
            pac[off:off + 8] = want.to_bytes(8, "little")
            rom2.files[fid] = bytes(pac)
            rom2.saveToFile(out_path)
            print(f"B  card_prop[0x{DONOR_CID:04X}]: 0x{cur:016X} -> 0x{want:016X} "
                  f"(Trap Hole 0x{REFERENCE_NORMAL_TRAP_CID:04X} template)")

        def install(rom, view):
            apply_effect(view.buf, rom, True)

        def check_fn(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            from otn_enhanced.asm.effect_verify import find_thumb2
            ov = bytearray(view.buf)
            out_path = None
            ok = True
            off = _find_cls_rows(ov, CLS0_BASE, CLS0_COUNT, DONOR_CID)[0]
            cur = struct.unpack_from("<5I", ov, off + 4)
            on3 = (cur[0] & ~1) == _a3()["res_act"]          # live pointer decides which cave to check
            A = _a3() if on3 else A5
            print(f"INFO stubs in {'the ov3 pool' if on3 else 'the ov5 cave'}")
            if cur != (A["res_act"] | 1, A["sub_act"] | 1, A["cond"] | 1, 0, 0):
                print(f"FAIL cls0 row: {tuple(hex(x) for x in cur)}"); ok = False
            else:
                print(f"PASS cls0 row @0x{RAM_BASE + off:08X}")

            for off in _find_cls_rows(ov, CLS2_BASE, CLS2_COUNT, DONOR_CID):
                cur = struct.unpack_from("<5I", ov, off + 4)
                if cur != (A["res_rider"] | 1, A["sub_rider"] | 1, 0, 0, 0):
                    print(f"FAIL cls2 row @0x{RAM_BASE + off:08X}: {tuple(hex(x) for x in cur)}"); ok = False
                else:
                    print(f"PASS cls2 row @0x{RAM_BASE + off:08X}")

            try:
                roff = _find_registry_rec(ov, END_THUNK, DONOR_CID)
                print(f"PASS End-Phase registry record @0x{RAM_BASE + roff:08X} intact")
            except AssertionError as e:
                print(f"FAIL End-Phase registry record: {e}"); ok = False
            if _find_registry_recs(ov, WATCH_THUNK, DONOR_CID):
                print("FAIL watcher record still carries the donor cid"); ok = False
            elif not _find_registry_recs(ov, WATCH_THUNK, PHANTOM_CID):
                print("FAIL watcher record missing entirely"); ok = False
            else:
                print("PASS watcher record neutralized (phantom cid)")

            poff = _find_pop(ov, DONOR_CID)
            b, h, fl = struct.unpack_from("<HII", ov, poff + 2)
            if (b, h, fl) != (0, A["wrapper"] | 1, POP_FL_NEW):
                print(f"FAIL populate: b=0x{b:04X} h=0x{h:08X} fl=0x{fl:08X}"); ok = False
            else:
                print("PASS populate -> custom wrapper/filter")

            ov5 = bytes(rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
            ov5_base = ov5_cave.OV5_RAM_BASE

            def cave(addr, n):
                from otn_enhanced.effects import cave3
                return cave3.read_code(rom, ov, addr, n)

            def check_stub(name, addr, want, bl_targets):
                nonlocal ok
                parts = want if isinstance(want, list) else [(addr, want)]
                tgts = []
                for pa, pw in parts:
                    got = cave(pa, len(pw))
                    if got != pw:
                        print(f"FAIL {name} bytes mismatch @0x{pa:08X}"); ok = False
                        return
                    if find_thumb2(pw, pa):
                        print(f"FAIL {name} contains Thumb-2"); ok = False
                        return
                    img, ib = (ov5, ov5_base) if pa >= ov5_base else (bytes(ov), RAM_BASE)
                    ins = decode_thumb(pw, pa, overlay_data=img, ram_base=ib)
                    tgts += [i.branch_target for i in ins if i.mnemonic == "BL"]
                want = b"".join(pw for _, pw in parts)
                if tgts != bl_targets:
                    print(f"FAIL {name} BL targets {[hex(t) for t in tgts]}"); ok = False
                else:
                    print(f"PASS {name} @0x{addr:08X} ({len(want)}B)")

            C = A["check"]
            check_stub("check core", C, _build_check(A),
                       [IS_MONSTER, GET_ATTRIBUTE, GET_RACE])
            check_stub("deck filter", A["filter"], _build_filter(A),
                       [C, CID_LEVEL])
            check_stub("act-cond", A["cond"], _build_cond(A), [IS_RESOLVE_CTX])
            check_stub("act eligibility", A["sub_act"], _build_sub_act(A), [ZONE_PRED])
            check_stub("rider eligibility", A["sub_rider"], _build_sub_rider(A),
                       [ZONE_PRED, C])
            check_stub("act resolver", A["res_act"], _build_res_act(A),
                       [SEL_OPEN, ELIG_DISPATCH, FLIP_FACEUP, SEL_CLOSE, NODE_ATTACH])
            rider = (list(zip((A["res_rider"], A["rider_b"]), _build_res_rider3(A, 0x68, 0xC0))) if on3
                     else _build_res_rider(A))
            check_stub("rider resolver", A["res_rider"], rider,
                       [SEL_OPEN, ELIG_DISPATCH, FLIP_FACEDOWN, DRAW, C,
                        CID_LEVEL, UI_EVENT, CRIT_FROM_CTX, SEL_REQUEST, SEL_GET,
                        SS_ENGINE, SEL_CLOSE, EFFECT_DONE, SEL_CLOSE])

            want_wrapper = _build_wrapper(A)
            wb = cave(A["wrapper"], len(want_wrapper))
            wpool = struct.unpack_from("<I", wb, WRAPPER_POOL_OFF)[0]
            if wb != want_wrapper or wpool != (A["filter"] | 1):
                print(f"FAIL wrapper (pool=0x{wpool:08X})"); ok = False
            else:
                print(f"PASS wrapper, filter pool 0x{wpool:08X}")

            # --- PART B: card_prop Spell -> Trap ---
            import ndspy.rom
            from otn_enhanced.rom.pac import parse_pac
            from otn_enhanced.data.card_stats import iter_paths as _iter_paths
            rom2 = rom
            pac_path = next(p for p in _iter_paths(rom2.filenames) if p.lower().endswith("bin2.pac"))
            pac = bytes(rom2.files[rom2.filenames.idOf(pac_path)])
            archive = parse_pac(pac, pac_path)
            cpf = next(f for f in archive.files if f.get_clean_name().lower() == "card_prop.bin")
            recs = {}
            for i in range((cpf.size - 8) // 8):
                val = int.from_bytes(pac[cpf.address + 8 + i * 8:cpf.address + 16 + i * 8], "little")
                cid = val & 0x3FFF
                if cid in (DONOR_CID, REFERENCE_NORMAL_TRAP_CID):
                    recs[cid] = val
            want = (recs[REFERENCE_NORMAL_TRAP_CID] & ~0x3FFF) | DONOR_CID
            if recs.get(DONOR_CID) != want:
                print(f"FAIL card_prop = 0x{recs.get(DONOR_CID, 0):016X} (want Trap Hole template 0x{want:016X})")
                ok = False
            else:
                print(f"PASS card_prop: full Trap Hole template (0x{want:016X})")
            c.ok(ok, "W - Nebula Meteorite: cls0/cls2 rows, registry, populate, every ov3 stub and its BL targets, Trap Hole card_prop template")

        return Compiled(installs=(install,), posts=(apply_card_prop,), checks=(check_fn,))


nebula_effects = normal_trap_flip_down_face_up_light_reptile_special_summon_level_7_or_higher_light_reptile_from_deck_at_end_phase

SPEC = card(0x1315, nebula_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_w_nebula_meteorite.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

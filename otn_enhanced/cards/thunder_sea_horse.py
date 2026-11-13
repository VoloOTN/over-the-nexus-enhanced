"""Thunder Sea Horse (LIGHT / Thunder / Level 4 / 1600 / 1200) on Fiend Kraken 0x0FEC.

    You can discard this card; add 2 cards with the same name, each a Level 4 LIGHT Thunder-Type monster with 1600 or
    less ATK, from your Deck to your hand. You cannot Special Summon the turn you activate this effect. You can only
    use this effect of "Thunder Sea Horse" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, NATIVE_COND, RES_RESERVE
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class discard_from_hand_add_two_same_name_level_4_light_thunder_from_deck_no_special_summon_this_turn:
    """Thunder Sea Horse (Fiend Kraken 0x0FEC): 'Discard this card; add 2 cards with the same name, Level 4 LIGHT Thunder
    with 1600 or less ATK, from your Deck to your hand. You cannot Special Summon the turn you activate this. Once per turn.'
    A re-home from Thunder Dragon 0x114F, which stays stock. Criteria row {custom wrapper, deck zone} over phantom 0x0EB0 (the
    wrapper is Botanical Girl's native deck-search wrapper cloned and pointed at a custom filter: Thunder + LIGHT + Lv4 + ATK
    ceiling + at least 2 copies left), cls2 hand-ignition record over 0x0E9E, ARM9 hand-effect list (the OFFER gate) over 0x1B42,
    a once-per-turn + embargo cond/res pair, a main executor with a pick loop, and the can-Special-Summon mega-gate deny-key
    trampoline at 0x021B999A. Six ov5 stubs."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import ARM9_BASE, insert_row_by_stride
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        TD_CID = 0x114F             # "Thunder Dragon" — the OLD donor, a real Effect Monster; handed back whole, pinned

        # ===========================================================================
        # PART A1 constants — criteria (populate) row insert (search criteria)
        # ===========================================================================
        POP_BASE = 0x022713C4       # RAM base of the populate table
        POP_STRIDE = 12             # bytes per populate record: [a u16][b u16][h u32][fl u32]
        POP_COUNT = 1389            # rows 0..1388 inclusive: real rows + the 0xFFFE/0xFFFF sentinel pair
        POP_FMT = "<HHII"
        POP_PHANTOM = 0x0EB0        # phantom (no card_prop), unclaimed -- dropped for the donor's row

        # Thunder Dragon's NATIVE populate record: the "search my own cid by same-name
        # mode" wiring.  Pinned untouched.
        NATIVE_POP_B = 0xFFFF
        NATIVE_POP_H = 0x0223D075
        NATIVE_POP_FL = 0x0000000E

        CLS2_BASE = 0x02275C04      # cls2 master effect table (24-byte records, +00 = cid, BINARY-searched)
        CLS2_STRIDE = 24
        CLS2_COUNT = 0x2B9
        CLS2_FMT = "<HHIIIII"       # {cid u16, pad u16, +04 main, +08, +0C cond, +10 res, +14}
        CLS2_PHANTOM = 0x0E9E       # phantom (no card_prop), unclaimed -- dropped for the donor's record

        # ===========================================================================
        # PART A0 constants — ARM9 "effect activatable from HAND" cid list (the OFFER gate)
        # ===========================================================================
        # The hand-menu flag builder 0x0224BC40 only sets flag 0x8 ("activate") after
        # `bl 0x0202354C(cid)` @0x0224C050 is nonzero, and 0x0202354C =
        # bsearch(HANDFX_LIST, 0x1E) || bsearch(quick-effect list 0x0209BC8C, 0x24).
        # Thunder Dragon is HANDFX_LIST[2]; a Normal donor is in neither, so without this
        # the cls2 record is never consulted (in-game test 1; A/B-emulated on
        # that savestate in scratch/tsh_hand_offer_ab.py: flags 0x50 -> 0x58).
        HANDFX_LIST = 0x0209BC4E    # sorted u16 cids (Kuriboh, D.D. Crow, Thunder Dragon, Captain Gold, ...)
        HANDFX_COUNT = 0x1E         # `movs r2,#0x1E` @0x02023550 (0x0202354C) and @0x02023540 (dead thunk 0x0202353C)
        HANDFX_POOLS = (0x0202356C, 0x02023544)   # the only two u32 literals holding the list address
        HANDFX_COUNT_IMM = 0x02023550
        HANDFX_PHANTOM = 0x1B42     # phantom (no card_prop), claimed nowhere -- dropped for the donor
        from otn_enhanced.effects.common import ARM9_BASE

        # --- Custom filter + cloned wrapper, hosted in the appended OVERLAY-5 cave ---
        # The shared deck-search builder (0x0223BC3C) invokes ONE per-candidate filter
        # via `blx` with r0 = searching player, candidate-entry ptr at [SP+0] (a pointer
        # INTO the deck array at player_struct+0x304; cid = low14 of the u32 entry) and
        # criteria (the populate record ptr) at [SP+4].  Disassembled this session.
        BUILDER = 0x0223BC3C         # shared deck/zone candidate builder (invokes the filter via blx)
        GET_RACE = 0x0202ABB8        # ARM9 get_race(r0=cid)      -> r0 = race (19 = Thunder)
        GET_ATTRIBUTE = 0x0202ABC8   # ARM9 get_attribute(r0=cid) -> r0 = attribute (1 = LIGHT)
        CID_LEVEL = 0x0202ABD8       # ARM9 cid_level(r0=cid)     -> r0 = Level
        GET_ATK = 0x0202AC48         # ARM9 get_atk(r0=cid)       -> r0 = ATK
        RACE_THUNDER = 19            # Era-2 race encoding (card_data_encoding.md)
        ATTR_LIGHT = 1                # Era-2 attribute encoding
        REQ_LEVEL = 4
        ATK_CEILING = 1600
        MIN_DECK_COPIES = 2          # 3DS 0x3F31F4: reject names with < 2 copies left in Deck

        PLAYER_BASE = 0x0229AC94     # per-player duel struct (stride 0xB3C)
        PLAYER_STRIDE = 0xB3C
        DECK_COUNT_OFF = 0x10        # u32 deck count   (builder: literal 0x0229ACA4)
        DECK_ARRAY_OFF = 0x304       # u32 entries, cid = low 14 bits (builder: 0xC1<<2)

        FILTER_ADDR = ov5_cave.CAVE_TSH_FILTER          # custom filter (appended ov5 cave)
        WRAPPER_ADDR = ov5_cave.CAVE_TSH_WRAPPER        # cloned wrapper (appended ov5 cave)
        FILTER_RESERVE = 0xC0
        WRAPPER_RESERVE = 0x40
        RETIRED_ADDR = ov5_cave.CAVE_TSH_RETIRED        # round-1 filter slot, must stay zero
        RETIRED_RESERVE = 0x60
        POP_H_NEW = WRAPPER_ADDR | 1   # populate 'h' = the cloned wrapper (Thumb entry)
        POP_B_NEW = 0x0000            # unused by the custom filter
        POP_FL_NEW = 0x00000002        # deck-zone, no type restriction (the filter applies every criterion)

        # Botanical Girl's 36-byte native deck-search populate wrapper, copied verbatim
        # (byte-proven template; BL @+0x18 re-encoded to the builder, filter literal
        # @+0x20 repointed at our custom filter | Thumb).
        WRAPPER_TEMPLATE = bytes.fromhex(
            "0eb5031c02201a5e02929a6800920190081c1988024a02abfef7d6fa0ebdc0469dc82302"
        )
        assert len(WRAPPER_TEMPLATE) == 0x24
        WRAPPER_BL_OFF = 0x18
        WRAPPER_POOL_OFF = 0x20

        # ===========================================================================
        # PART A2/A3 constants — master handler row (once-per-turn + embargo shims)
        # ===========================================================================
        # Thunder Dragon's cls2 record (stride 24: cid | main|1 | 0 | cond|1 | res|1 | 0),
        # pinned untouched.  The donor gets a CLONE of it with main/cond/res pointed at the
        # cave shims; cond and res shims chain the SHARED native handlers (85 / 29 rows).
        NATIVE_COND = 0x021F0821     # shared act-cond: Rai-Oh/Deck-Lockdown floodgate + candidates >= 1
        NATIVE_RES = 0x021E6FD9      # shared cost: discard self (desc[+0xC]) -- cid-blind
        NATIVE_MAIN = 0x0220B029     # Thunder Dragon's own discard+search executor (stays his)
        TD_CLS2 = (TD_CID, 0x0000, NATIVE_MAIN, 0x00000000, NATIVE_COND, NATIVE_RES, 0x00000000)

        # --- the generic deck-selection protocol (decoded from Dark Grepher's main
        # 0x02208DD4, the native "discard cost -> pick 1 card from a deck LIST" flow;
        # state codes proven by his jump table: entry 0x80, then 0x7F/0x7E/0x7D, 0x64 =
        # cleanup, 0x6F = fail; the framework stores the returned state in
        # [0x0229AAFC+0x70] and re-invokes main) ---
        FSM_STATE = 0x0229AAFC       # duel-FSM block: +0x70 state, +0x74/+0x78 per-effect scratch
        SEL_OPEN = 0x021D28A4        # open a selection session   (Grepher @0x02208E84)
        SEL_CLOSE = 0x021D2964       # close the selection session (Grepher @0x02208F30)
        UI_EVENT = 0x0219A818        # (player, event) -- 0x3A = deck-candidate selection pre-step
        UI_EV_DECKSEL = 0x3A
        SEL_REQUEST = 0x0219C430     # (player, npicks+6, kid, crit) -- open the pick list (populate filter applies)
        SEL_RESULT = 0x0219C94C      # (i 1-based) -> ptr to i-th selected entry word (low14 = cid)
        SEL_COUNT_PTR = 0x0229DD94   # +0x34 = number of entries the player selected
        CRIT_FROM_CTX = 0x02234E78   # (ctx) -> criteria word passed to the candidate builder
        FIND_IN_DECK = 0x021A7BC4    # (player, cid) -> deck index of first entry with that cid, or <0
        MOVE_TO_HAND = 0x021C72CC    # (player, &deck_entry) -> move that deck card to hand (TD's native move)
        EFFECT_DONE = 0x021D269C     # (player) -- state-0x64 cleanup (TD/Grepher shared)
        EFFECT_FAIL = 0x0225BF30     # (1-player) -- state-0x6F fail path (TD's)

        IS_RESOLVE_CTX = 0x021D2B88  # nonzero in resolve/replay context (PoD act-cond & resolver both gate on it)
        TURNLOG_QUERY = 0x021A14E8   # (p, 0xB, kid, kind) -> nonzero iff node on the per-turn log
        TURNLOG_SLOT = 0xB           # pseudo-zone 0xB = the per-turn log (auto-expires)
        TURNLOG_KIND = 1             # kind 1 = card/effect activation (PoD's HOPT uses (kid, 1))
        NODE_ATTACH = 0x021D2584     # (p, kid, kind, 0) -> attach {key=kid, kind} node to (p, slot 0xB)
        TURNFLAGS_BASE = 0x0229ADB4  # per-player turn-flags word (+p*0xB3C); bit18 = Special Summoned this turn
        SS_BIT = 18

        COND_ADDR = ov5_cave.CAVE_TSH_COND
        COND_RESERVE = 0x60
        RES_ADDR = ov5_cave.CAVE_TSH_RES
        RES_RESERVE = 0x40
        MAIN_ADDR = ov5_cave.CAVE_TSH_MAIN
        MAIN_RESERVE = 0x140

        CLS2_RECORD = (DONOR_CID, 0x0000, MAIN_ADDR | 1, 0x00000000, COND_ADDR | 1, RES_ADDR | 1, 0x00000000)
        POP_RECORD = (DONOR_CID, POP_B_NEW, POP_H_NEW, POP_FL_NEW)

        # ===========================================================================
        # PART A4 constants — can-SS mega-gate deny-key hook
        # ===========================================================================
        # The mega-gate 0x021B9708(player, mode, kid) is the single choke point every
        # Special-Summon path consults.  Its SS section walks per-card deny keys as
        # key-only node queries `0x021A1430(p, 0xB, key)`.  The LAST one (Steelswarm
        # Scout, key 0x23D3 in r2) at 0x021B999A is trampolined: the stub replays the
        # displaced query and, when it misses, queries deny key 0x0FEC instead.  Either
        # nonzero -> the caller's `BNE deny` fires -> Special Summon refused.
        NODE_QUERY = 0x021A1430          # key-only node query (p, slot, key)
        SS_GATE_SITE = 0x021B999A        # native `BL 0x021A1430` inside the mega-gate
        SS_GATE_NATIVE = (0xF7E7, 0xFD49)  # the displaced BL's native halfwords
        SSGATE_ADDR = ov5_cave.CAVE_TSH_SSGATE
        SSGATE_RESERVE = 0x30

        # ===========================================================================
        # PART B constants — visible stats written into card_prop.bin
        # ===========================================================================
        NEW_ATTRIBUTE = "LIGHT"        # donor was WATER
        NEW_RACE = "Thunder"           # donor was Aqua
        NEW_LEVEL = 4                   # donor already Level 4
        NEW_ATK = 1600                  # donor was 1200
        NEW_DEF = 1200                  # donor was 1400
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Effect Monster"]   # the donor ships as a Normal Monster

        # ===========================================================================
        # PART C constants — card name + description (written strictly IN-PLACE)
        # ===========================================================================

        def _rows(ov: bytearray, base: int, stride: int, count: int, fmt: str) -> list[tuple]:
            return [struct.unpack_from(fmt, ov, base - RAM_BASE + i * stride) for i in range(count)]


        def _table_state(ov: bytearray) -> list[str]:
            """Problems with the donor/Thunder Dragon records (empty list = all good)."""
            bad = []
            for name, rows, want, phantom, td in (
                ("cls2", _rows(ov, CLS2_BASE, CLS2_STRIDE, CLS2_COUNT, CLS2_FMT), CLS2_RECORD, CLS2_PHANTOM, TD_CLS2),
                ("criteria", _rows(ov, POP_BASE, POP_STRIDE, POP_COUNT, POP_FMT), POP_RECORD, POP_PHANTOM,
                 (TD_CID, NATIVE_POP_B, NATIVE_POP_H, NATIVE_POP_FL)),
            ):
                cids = [r[0] for r in rows]
                if [r for r in rows if r[0] == DONOR_CID] != [want]:
                    bad.append(f"{name}: donor 0x{DONOR_CID:04X} rows {[r for r in rows if r[0] == DONOR_CID]}")
                if phantom in cids:
                    bad.append(f"{name}: phantom 0x{phantom:04X} still present")
                if any(cids[i] > cids[i + 1] for i in range(len(cids) - 1)):
                    bad.append(f"{name}: table not sorted")
                if [r for r in rows if r[0] == TD_CID] != [td]:
                    bad.append(f"{name}: Thunder Dragon 0x{TD_CID:04X} altered {[r for r in rows if r[0] == TD_CID]}")
            return bad


        def _build_filter() -> bytes:
            """Custom Thumb-1 deck-search filter -- the 3DS 0x3F31F4 port.

            Accept a candidate iff Race==Thunder AND Attribute==LIGHT AND Level==4 AND
            ATK<=1600 AND the searching player's Deck holds >= 2 copies of that cid
            (the "same name" rule: only names that can still be added as a PAIR are
            offered; the untouched native pick stage takes up to 2).

            ABI (from the builder disassembly): entered via `blx` with r0 = searching
            player; the candidate-entry pointer (into the real deck array) is the
            caller's [SP+0] -> [SP+0x10] after our 4-register push.  Getters take the
            RAW cid (their shared record-fetcher masks internally).
            """
            b = EffectBuilder()
            b.prologue(save=[R4, R5, R6])
            b.insn("ADD", "R5, R0, #0x0")        # r5 = searching player
            b.insn("LDR", "R4, [SP, #0x10]")     # caller's [SP+0] = &deck entry
            b.insn("LDR", "R4, [R4, #0x0]")      # entry word
            b.insn("LSL", "R4, R4, #0x12")
            b.insn("LSR", "R4, R4, #0x12")       # r4 = candidate cid (low 14)
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(GET_RACE)
            b.if_ne(R0, RACE_THUNDER, "reject")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(GET_ATTRIBUTE)
            b.if_ne(R0, ATTR_LIGHT, "reject")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(CID_LEVEL)
            b.if_ne(R0, REQ_LEVEL, "reject")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(GET_ATK)
            b.ldr_const(1, ATK_CEILING)          # r1 = 1600
            b.insn("CMP", "R0, R1")
            b.insn("BGT", "reject")
            # --- deck-copies >= 2 (the 3DS 0x3B4EA0 walk) ---
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R5, R0")              # p &= 1
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("MUL", "R0, R5")
            b.ldr_const(1, PLAYER_BASE)
            b.insn("ADD", "R1, R1, R0")          # r1 = player struct
            b.insn("LDR", "R2, [R1, #0x10]")     # r2 = deck count
            b.insn("MOV", "R0, #0xC1")
            b.insn("LSL", "R0, R0, #0x2")        # 0x304
            b.insn("ADD", "R1, R1, R0")          # r1 = deck entry array
            b.insn("MOV", "R5, #0x0")            # r5 = copies found
            b.insn("MOV", "R6, #0x0")            # r6 = index
            b.label("count_loop")
            b.insn("CMP", "R6, R2")
            b.insn("BGE", "count_done")
            b.insn("LSL", "R0, R6, #0x2")
            b.insn("LDR", "R0, [R1, R0]")        # deck entry word
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")       # its cid
            b.insn("CMP", "R0, R4")
            b.insn("BNE", "count_next")
            b.insn("ADD", "R5, R5, #0x1")
            b.label("count_next")
            b.insn("ADD", "R6, R6, #0x1")
            b.insn("B", "count_loop")
            b.label("count_done")
            b.insn("CMP", "R5, #0x2")            # MIN_DECK_COPIES
            b.insn("BLT", "reject")
            b.epilogue(ret=1)                    # accept
            b.label("reject")
            b.epilogue(ret=0)
            code = b.assemble(FILTER_ADDR)
            assert len(code) <= FILTER_RESERVE, f"filter {len(code)}B exceeds reserve 0x{FILTER_RESERVE:X}"
            assert_thumb1_only(code, FILTER_ADDR)   # ARMv5TE / Thumb-1 only (HOWTO §11)
            return code


        def _build_wrapper() -> bytes:
            """Clone of Botanical's native deck-search wrapper (the old WRAPPER_TEMPLATE, decoded):
            marshals (player, ctx fields) into a stack block and calls the shared deck-search builder
            with our custom filter | Thumb as the pool literal. Byte-proven by the GK/Wattcobra patches.
            """
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
            b.ldr_const(2, FILTER_ADDR | 1)      # filter literal -> our custom filter | Thumb
            b.insn("ADD", "R3, SP, #0x8")
            b.bl(BUILDER)                        # shared deck-search builder
            b.insn("POP", "{R1, R2, R3, PC}")
            code = b.assemble(WRAPPER_ADDR, pad="nop")
            assert len(code) == len(WRAPPER_TEMPLATE), (
                f"wrapper is {len(code)} bytes (expected {len(WRAPPER_TEMPLATE)})")
            assert_thumb1_only(code, WRAPPER_ADDR)    # ARMv5TE / Thumb-1 only (HOWTO §11)
            return code


        def _build_cond() -> bytes:
            """Act-cond shim -- Pot of Duality's own two extra tests grafted onto the donor.

            shim(ctx, arg1):
              if IS_RESOLVE_CTX(ctx): goto native          ; resolve/replay context must not
                                                            ; re-deny its own activation (PoD parity)
              if TURNLOG_QUERY([ctx+2], 0xB, [ctx+0], 1):  return 0   ; once per turn
              if turnflags([ctx+2]) bit18:                 return 0   ; already Special Summoned
              native: return NATIVE_COND(ctx, arg1)        ; floodgates + candidate count
            """
            b = EffectBuilder()
            b.prologue(save=[R4, R5])
            b.insn("ADD", "R5, R0, #0x0")        # r5 = ctx (r0 still ctx for the call)
            b.insn("ADD", "R4, R1, #0x0")        # r4 = 2nd arg, passed through to the native cond
            b.call_addr(IS_RESOLVE_CTX)
            b.if_ne(R0, 0, "native")
            b.ctx_field("controller", dest=R0, ctx=R5)     # LDRB R0, [R5, #2] = player
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R5, #0x0]")     # kid (== 0x0FEC from this row)
            b.insn("MOV", "R3, #0x1")            # TURNLOG_KIND
            b.call_addr(TURNLOG_QUERY)
            b.if_ne(R0, 0, "deny")               # already activated this turn (HOPT)
            b.ctx_field("controller", dest=R0, ctx=R5)
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")              # p &= 1
            b.ldr_const(1, PLAYER_STRIDE)
            b.insn("MUL", "R1, R0")
            b.ldr_const(0, TURNFLAGS_BASE)
            b.insn("LDR", "R0, [R0, R1]")
            b.insn("LSR", "R0, R0, #0x12")       # >> SS_BIT
            b.insn("MOV", "R1, #0x1")
            b.insn("TST", "R0, R1")
            b.insn("BNE", "deny")                # already Special Summoned this turn
            b.label("native")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R4, #0x0")
            b.call_addr(NATIVE_COND & ~1)
            b.insn("POP", "{R4, R5, PC}")
            b.label("deny")
            b.epilogue(ret=0)
            code = b.assemble(COND_ADDR)
            assert len(code) <= COND_RESERVE, f"cond shim {len(code)}B exceeds reserve 0x{COND_RESERVE:X}"
            assert_thumb1_only(code, COND_ADDR)
            return code


        def _build_res() -> bytes:
            """Resolver shim -- Pot of Duality's resolver body, then the donor's native tail.

            shim(ctx):
              if not IS_RESOLVE_CTX(ctx):
                  NODE_ATTACH([ctx+2], [ctx+0], 1, 0)   ; attach the (slot 0xB, key 0x0FEC,
                                                        ; kind 1) rider: HOPT latch + the
                                                        ; mega-gate's forward SS embargo,
                                                        ; auto-expires at turn end
              return NATIVE_RES(ctx)
            """
            b = EffectBuilder()
            b.prologue(save=[R4])
            b.insn("ADD", "R4, R0, #0x0")        # r4 = ctx (r0 still ctx for the call)
            b.call_addr(IS_RESOLVE_CTX)
            b.if_ne(R0, 0, "chain")
            b.ctx_field("controller", dest=R0, ctx=R4)     # player
            b.insn("LDRH", "R1, [R4, #0x0]")     # kid (== 0x0FEC from this row)
            b.insn("MOV", "R2, #0x1")            # TURNLOG_KIND
            b.insn("MOV", "R3, #0x0")
            b.call_addr(NODE_ATTACH)
            b.label("chain")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(NATIVE_RES & ~1)
            b.insn("POP", "{R4, PC}")
            code = b.assemble(RES_ADDR)
            assert len(code) <= RES_RESERVE, f"res shim {len(code)}B exceeds reserve 0x{RES_RESERVE:X}"
            assert_thumb1_only(code, RES_ADDR)
            return code


        def _build_main() -> bytes:
            """Main state machine -- pick ONE qualifying card from the deck LIST, then
            add BOTH deck copies of the selected name to hand.

            Thunder Dragon's native main (0x0220B028) never shows a list: it finds deck
            entries by its OWN cid (0x021A7BC4(p, kid)) and moves up to 2 to hand, which
            is why the round-2 build only ever offered Thunder Sea Horse copies.  This
            replacement drives the engine's GENERIC deck-selection protocol instead --
            the exact shape of Dark Grepher's native main 0x02208DD4 (ignition, discard
            cost, pick 1 from a filtered deck list), whose jump table proves the state
            codes: the framework stores the returned state in [FSM_STATE+0x70] and
            re-invokes main; the selection list is built from the populate record, so
            the PART-A1 filter (incl. deck-copies>=2) decides what is offered.

              0x80 (entry): scratch=0; SEL_OPEN(); UI_EVENT(p, 0x3A)          -> 0x7F
              0x7F: SEL_REQUEST(p, 1 pick + 6, kid, CRIT_FROM_CTX(ctx))       -> 0x7E
              0x7E: read the pick (SEL_RESULT(1), low14 = cid) into +0x78,
                    copies-to-add = 2 into +0x74                              -> 0x7D
              0x7D: one copy per iteration (Grepher/TD convention -- each move
                    animates): FIND_IN_DECK(p, sel_cid) -> MOVE_TO_HAND       -> 0x7D
                    until +0x74 hits 0 or the deck runs out, then SEL_CLOSE   -> 0x64
              0x64: EFFECT_DONE(p) -> 0 (TD's own cleanup state, kept verbatim)
              0x6F: EFFECT_FAIL(1-p) -> 0x64 (TD's own fail state, kept verbatim)
            """
            b = EffectBuilder()
            b.prologue(save=[R4, R5, R6, R7])
            b.insn("ADD", "R4, R0, #0x0")        # r4 = ctx
            b.ldr_const(5, FSM_STATE)            # r5 = duel-FSM block
            b.insn("LDR", "R0, [R5, #0x70]")     # current state
            for state, target in ((0x64, "st64"), (0x6F, "st6F"), (0x80, "st80"),
                                  (0x7F, "st7F"), (0x7E, "st7E"), (0x7D, "st7D")):
                b.if_eq(R0, state, target)
            b.epilogue(ret=0)                    # unknown state -> done
            # --- 0x80: entry -----------------------------------------------------
            b.label("st80")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R5, #0x74]")     # copies-to-add = 0 (nothing picked yet)
            b.insn("STR", "R0, [R5, #0x78]")     # selected cid = 0
            b.call_addr(SEL_OPEN)
            b.ctx_field("controller", dest=R0, ctx=R4)     # player
            b.insn("MOV", f"R1, #0x{UI_EV_DECKSEL:X}")
            b.call_addr(UI_EVENT)
            b.epilogue(ret=0x7F)
            # --- 0x7F: open the pick-1 list ---------------------------------------
            b.label("st7F")
            b.insn("ADD", "R0, R4, #0x0")
            b.call_addr(CRIT_FROM_CTX)
            b.insn("ADD", "R3, R0, #0x0")        # crit
            b.ctx_field("controller", dest=R0, ctx=R4)     # player
            b.insn("MOV", "R1, #0x7")            # 1 pick + 6 (Grepher's npicks+6 encoding)
            b.insn("LDRH", "R2, [R4, #0x0]")     # kid
            b.call_addr(SEL_REQUEST)
            b.epilogue(ret=0x7E)
            # --- 0x7E: consume the selection --------------------------------------
            b.label("st7E")
            b.ldr_const(0, SEL_COUNT_PTR)
            b.insn("LDR", "R0, [R0, #0x34]")     # entries selected
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "finish")              # nothing picked (safety) -> close out
            b.insn("MOV", "R0, #0x1")
            b.call_addr(SEL_RESULT)              # -> ptr to 1st selected entry word
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")       # selected cid (low 14)
            b.insn("STR", "R0, [R5, #0x78]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [R5, #0x74]")     # add 2 copies of that name
            b.epilogue(ret=0x7D)
            # --- 0x7D: move one copy per iteration --------------------------------
            b.label("st7D")
            b.insn("LDR", "R0, [R5, #0x74]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "finish")
            b.ctx_field("controller", dest=R0, ctx=R4)     # player
            b.insn("LDR", "R1, [R5, #0x78]")     # selected cid
            b.call_addr(FIND_IN_DECK)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "finish")              # deck ran out of copies
            b.insn("ADD", "R7, R0, #0x0")        # r7 = deck index
            b.ctx_field("controller", dest=R0, ctx=R4)     # r0 = player (MOVE_TO_HAND's r0)
            b.insn("MOV", "R6, #0x1")
            b.insn("AND", "R6, R0")              # r6 = p & 1
            b.ldr_const(1, PLAYER_STRIDE)
            b.insn("MUL", "R1, R6")
            b.ldr_const(2, PLAYER_BASE)
            b.insn("ADD", "R1, R1, R2")          # player struct
            b.insn("MOV", "R2, #0xC1")
            b.insn("LSL", "R2, R2, #0x2")        # 0x304
            b.insn("ADD", "R1, R1, R2")          # deck array
            b.insn("LSL", "R2, R7, #0x2")
            b.insn("ADD", "R1, R1, R2")          # r1 = &deck[idx]
            b.call_addr(MOVE_TO_HAND)
            b.insn("LDR", "R0, [R5, #0x74]")
            b.insn("SUB", "R0, R0, #0x1")
            b.insn("STR", "R0, [R5, #0x74]")
            b.epilogue(ret=0x7D)
            # --- shared tail -------------------------------------------------------
            b.label("finish")
            b.call_addr(SEL_CLOSE)
            b.epilogue(ret=0x64)
            # --- 0x64 / 0x6F: TD's own cleanup / fail states -----------------------
            b.label("st64")
            b.ctx_field("controller", dest=R0, ctx=R4)     # player
            b.call_addr(EFFECT_DONE)
            b.epilogue(ret=0)
            b.label("st6F")
            b.ctx_field("controller", dest=R1, ctx=R4)
            b.insn("MOV", "R0, #0x1")
            b.insn("SUB", "R0, R0, R1")          # 1 - player
            b.call_addr(EFFECT_FAIL)
            b.epilogue(ret=0x64)
            code = b.assemble(MAIN_ADDR)
            assert len(code) <= MAIN_RESERVE, f"main {len(code)}B exceeds reserve 0x{MAIN_RESERVE:X}"
            assert_thumb1_only(code, MAIN_ADDR)
            return code


        def _build_ssgate() -> bytes:
            """Mega-gate hook stub -- replay the displaced deny-key query, add key 0x0FEC.

            Drop-in for the native `BL 0x021A1430` at SS_GATE_SITE (r0 = player,
            r1 = 0xB, r2 = 0x23D3 Steelswarm Scout).  Returns nonzero (deny) iff the
            native query hits OR a key-0x0FEC node is on the player's turn log.
            """
            b = EffectBuilder()
            b.prologue(save=[R4])
            b.insn("ADD", "R4, R0, #0x0")        # r4 = player
            b.call_addr(NODE_QUERY)              # replay the displaced query (0x23D3)
            b.if_ne(R0, 0, "done")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xB")            # TURNLOG_SLOT
            b.ldr_const(2, DONOR_CID)
            b.call_addr(NODE_QUERY)              # deny key 0x0FEC (Thunder Sea Horse)
            b.label("done")
            b.insn("POP", "{R4, PC}")
            code = b.assemble(SSGATE_ADDR)
            assert len(code) <= SSGATE_RESERVE, f"ss-gate stub {len(code)}B exceeds reserve 0x{SSGATE_RESERVE:X}"
            assert_thumb1_only(code, SSGATE_ADDR)
            return code

        def _arm9_data(rom):
            import ndspy.code
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            return mc, next(s for s in mc.sections if s.ramAddress == ARM9_BASE)


        def _handfx_list(data: bytes) -> list[int]:
            for p in HANDFX_POOLS:
                assert struct.unpack_from("<I", data, p - ARM9_BASE)[0] == HANDFX_LIST, f"pool @0x{p:08X} moved"
            assert struct.unpack_from("<H", data, HANDFX_COUNT_IMM - ARM9_BASE)[0] == (0x2200 | HANDFX_COUNT), \
                "hand-effect list count immediate changed"
            return list(struct.unpack_from(f"<{HANDFX_COUNT}H", data, HANDFX_LIST - ARM9_BASE))


        def apply_handfx_list(out_path: str) -> None:
            """PART A0 -- put the donor in the hand-effect list IN PLACE, dropping phantom 0x1B42."""
            import ndspy.rom
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            mc, sec = _arm9_data(rom)
            d = bytearray(sec.data)
            cur = _handfx_list(d)
            if DONOR_CID in cur:                                                  # idempotent
                print(f"A0 hand-effect list: 0x{DONOR_CID:04X} already present -> no change")
                return
            assert TD_CID in cur, "Thunder Dragon lost its hand-effect list entry"
            assert cur.count(HANDFX_PHANTOM) == 1, f"phantom 0x{HANDFX_PHANTOM:04X} not in the hand-effect list"
            new = sorted([c for c in cur if c != HANDFX_PHANTOM] + [DONOR_CID])
            assert len(new) == HANDFX_COUNT and all(new[i] < new[i + 1] for i in range(HANDFX_COUNT - 1))
            struct.pack_into(f"<{HANDFX_COUNT}H", d, HANDFX_LIST - ARM9_BASE, *new)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            rom.saveToFile(out_path)
            print(f"A0 hand-effect list @0x{HANDFX_LIST:08X}: dropped phantom 0x{HANDFX_PHANTOM:04X}, "
                  f"inserted 0x{DONOR_CID:04X} (count {HANDFX_COUNT}, sorted)")

        stubs = ((FILTER_ADDR, _build_filter(), "filter"), (WRAPPER_ADDR, _build_wrapper(), "wrapper"),
                 (COND_ADDR, _build_cond(), "cond shim"), (RES_ADDR, _build_res(), "res shim"),
                 (SSGATE_ADDR, _build_ssgate(), "mega-gate stub"), (MAIN_ADDR, _build_main(), "main"))

        def install(rom, view):
            from otn_enhanced.effects.common import thumb_bl as _thumb_bl
            ov = view.buf
            td_bad = [p for p in _table_state(ov) if "Thunder Dragon" in p]
            assert not td_bad, td_bad
            insert_row_by_stride(ov, POP_BASE, POP_STRIDE, POP_COUNT, POP_FMT, POP_RECORD, POP_PHANTOM, "criteria")
            insert_row_by_stride(ov, CLS2_BASE, CLS2_STRIDE, CLS2_COUNT, CLS2_FMT, CLS2_RECORD, CLS2_PHANTOM, "cls2")
            bad = _table_state(ov)
            assert not bad, bad
            soff = SS_GATE_SITE - RAM_BASE
            cur = struct.unpack_from("<2H", ov, soff)
            want = struct.unpack("<2H", _thumb_bl(SS_GATE_SITE, SSGATE_ADDR))
            if cur != want:
                assert cur == SS_GATE_NATIVE, (
                    f"mega-gate site @0x{SS_GATE_SITE:08X} = {cur[0]:04X} {cur[1]:04X} "
                    f"(expected native BL {SS_GATE_NATIVE[0]:04X} {SS_GATE_NATIVE[1]:04X})")
                struct.pack_into("<2H", ov, soff, *want)

        def check_fn(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            from otn_enhanced.asm.effect_verify import find_thumb2
            from otn_enhanced.effects.common import thumb_bl as _thumb_bl
            ov = view.buf
            ok = True
            # --- A1/A2: criteria row + cls2 record on the donor; Thunder Dragon stock ---
            bad = _table_state(ov)
            for p in bad:
                print(f"FAIL {p}")
            if bad:
                ok = False
            else:
                print(f"PASS cls2 + criteria rows on 0x{DONOR_CID:04X} (phantoms 0x{CLS2_PHANTOM:04X}/"
                      f"0x{POP_PHANTOM:04X} spent, sorted); Thunder Dragon 0x{TD_CID:04X} stock")

            # --- A0: hand-effect list membership (the offer gate) ---
            lst = _handfx_list(bytes(_arm9_data(rom)[1].data))
            if DONOR_CID in lst and TD_CID in lst and HANDFX_PHANTOM not in lst and lst == sorted(lst):
                print(f"PASS hand-effect list @0x{HANDFX_LIST:08X}: 0x{DONOR_CID:04X} + Thunder Dragon present, sorted")
            else:
                print(f"FAIL hand-effect list: {[hex(c) for c in lst]}"); ok = False

            # --- A4: mega-gate trampoline ---
            want_bl = struct.unpack("<2H", _thumb_bl(SS_GATE_SITE, SSGATE_ADDR))
            cur = struct.unpack_from("<2H", ov, SS_GATE_SITE - RAM_BASE)
            if cur != want_bl:
                print(f"FAIL mega-gate hook @0x{SS_GATE_SITE:08X}: {cur[0]:04X} {cur[1]:04X}"); ok = False
            else:
                print(f"PASS mega-gate hook @0x{SS_GATE_SITE:08X} -> BL 0x{SSGATE_ADDR:08X}")

            # --- cave stub bytes + BL targets ---
            ov5 = bytes(rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
            ov5_base = ov5_cave.OV5_RAM_BASE

            def cave(addr, n):
                return bytes(ov5[addr - ov5_base: addr - ov5_base + n])

            def check_stub(name, addr, want, bl_targets):
                nonlocal ok
                got = cave(addr, len(want))
                if got != want:
                    print(f"FAIL ov5 {name} bytes mismatch"); ok = False
                    return
                if find_thumb2(want, addr):
                    print(f"FAIL ov5 {name} contains Thumb-2"); ok = False
                    return
                ins = decode_thumb(want, addr, overlay_data=ov5, ram_base=ov5_base)
                tgts = [i.branch_target for i in ins if i.mnemonic == "BL"]
                if tgts != bl_targets:
                    print(f"FAIL {name} BL targets {[hex(t) for t in tgts]}"); ok = False
                else:
                    print(f"PASS {name} @0x{addr:08X} ({len(want)}B), BLs {[hex(t) for t in tgts]}")

            check_stub("filter", FILTER_ADDR, _build_filter(),
                       [GET_RACE, GET_ATTRIBUTE, CID_LEVEL, GET_ATK])
            check_stub("cond shim", COND_ADDR, _build_cond(),
                       [IS_RESOLVE_CTX, TURNLOG_QUERY, NATIVE_COND & ~1])
            check_stub("res shim", RES_ADDR, _build_res(),
                       [IS_RESOLVE_CTX, NODE_ATTACH, NATIVE_RES & ~1])
            check_stub("ss-gate stub", SSGATE_ADDR, _build_ssgate(),
                       [NODE_QUERY, NODE_QUERY])
            check_stub("main", MAIN_ADDR, _build_main(),
                       [SEL_OPEN, UI_EVENT, CRIT_FROM_CTX, SEL_REQUEST, SEL_RESULT,
                        FIND_IN_DECK, MOVE_TO_HAND, SEL_CLOSE, EFFECT_DONE, EFFECT_FAIL])

            want_wrapper = _build_wrapper()
            wb = cave(WRAPPER_ADDR, len(want_wrapper))
            wins = decode_thumb(wb, WRAPPER_ADDR, overlay_data=ov5, ram_base=ov5_base)
            wbl = next((i for i in wins if i.mnemonic == "BL"), None)
            wpool = struct.unpack_from("<I", wb, WRAPPER_POOL_OFF)[0]
            if wb != want_wrapper or not wbl or wbl.branch_target != BUILDER or wpool != (FILTER_ADDR | 1):
                print(f"FAIL wrapper (bl={wbl and hex(wbl.branch_target)} pool=0x{wpool:08X})"); ok = False
            else:
                print(f"PASS wrapper BL -> builder 0x{BUILDER:08X}, filter pool 0x{wpool:08X}")

            if cave(RETIRED_ADDR, RETIRED_RESERVE) != bytes(RETIRED_RESERVE):
                print("FAIL retired round-1 filter slot not zero"); ok = False
            c.ok(ok, "Thunder Sea Horse: tables, hand-effect list, mega-gate hook and every cave stub")

        return Compiled(stubs, installs=(install,), posts=(apply_handfx_list,), checks=(check_fn,))


tsh_effect = discard_from_hand_add_two_same_name_level_4_light_thunder_from_deck_no_special_summon_this_turn

SPEC = card(0x0FEC, tsh_effect())

PROPS = card_props("LIGHT", "Thunder", level=4, atk=1600, defense=1200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_thunder_sea_horse.nds")

# w_nebula_meteorite reads the byte-proven Botanical wrapper template and the builder ABI off this module.
BUILDER = 0x0223BC3C         # shared deck/zone candidate builder (invokes the filter via blx)
WRAPPER_TEMPLATE = bytes.fromhex(
    "0eb5031c02201a5e02929a6800920190081c1988024a02abfef7d6fa0ebdc0469dc82302"
)
WRAPPER_BL_OFF = 0x18
WRAPPER_POOL_OFF = 0x20

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

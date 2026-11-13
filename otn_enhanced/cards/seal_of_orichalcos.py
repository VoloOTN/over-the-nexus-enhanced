"""The Seal of Orichalcos (Field Spell, Spell donor Yami 0x10F5; card_prop unchanged, text only).

    All monsters you control gain 500 ATK. Once per turn, this card cannot be destroyed by card effects. While you control 2 or more face-up Attack
    Position monsters, your opponent cannot target your monster(s) with the lowest ATK for an attack. If this card is activated: Destroy all Special
    Summoned monsters you control. You cannot Special Summon monsters from the Extra Deck. You can only activate "The Seal of Orichalcos" once per
    Duel. (See card_text.CARD_TEXT[0x10F5] for the full printed text.)
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled, SRC
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.data import card_text
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class field_spell_monsters_gain_500_atk_not_destroyed_by_card_effects_protect_lowest_atk_destroy_own_special_summons_once_per_duel_no_extra_deck_summons:
    """The Seal of Orichalcos (Yami 0x10F5, a Field Spell kept a Spell): 'All monsters you control gain 500 ATK. Once per turn, this card cannot be
    destroyed by card effects. While you control 2 or more face-up Attack Position monsters, your opponent cannot target your monster(s) with the
    lowest ATK for an attack. If this card is activated: Destroy all Special Summoned monsters you control. You cannot Special Summon monsters from
    the Extra Deck. You can only activate "The Seal of Orichalcos" once per Duel.' All in overlay 3 (ov3 pool): the stat-engine arm rewrite (C1),
    the Kingshark-template hook and its stub in a phantom's dead arm (C2), the Pixie Ring presence redirect (C3), the cls0 record over phantom 0x234C
    with the filter / condition / resolver stubs (C4 + C6), and the two Extra-Deck summon gates in a phantom's dead leaf (C5). NOTE: six of the stubs
    (the arm, C2, C3, filter, condition, resolver-in-ov5 form and C5) are hand-encoded Thumb halfwords via struct.pack, NOT EffectBuilder -- embedded
    verbatim, so this verb keeps raw halfwords (only build_res3, the shipped resolver, uses EffectBuilder). Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        import struct
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        from otn_enhanced.data import card_text
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R4
        from otn_enhanced.effects.common import ov3_off as _off

        SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"   # stock + step 0 (ov3 is the default)
        OUT = "data/over_the_nexus/working/rom_seal_of_orichalcos.nds"

        DONOR_CID = 0x10F5                        # Yami
        ARM = 0x021B28A0                          # Yami's switch arm (jump table 0x021B2764 entry 5)
        NO_CHANGE = 0x021B2928                    # `b 0x021B2B48` with r4/r5 untouched
        EPILOGUE = 0x021B2B48                     # writes r4 -> out ATK, r5 -> out DEF

        # Stock arm, 22 B: Fiend|Spellcaster +200/+200, then Fairy -200/-200 via 0x021B289A.
        STOCK = bytes.fromhex("b1684e48084201d0c834c83502200004084239d0f1e7")


        def _b(site: int, target: int) -> int:
            off = (target - site - 4) >> 1
            assert -1024 <= off < 1024
            return 0xE000 | (off & 0x7FF)


        def _bne(site: int, target: int) -> int:
            off = (target - site - 4) >> 1
            assert -128 <= off < 128
            return 0xD100 | (off & 0xFF)


        def build_arm(base: int = ARM) -> bytes:
            hw = [
                0x9800,                            # ldr  r0,[sp,#0]   field-spell side
                0x4287,                            # cmp  r7,r0        monster side
                _bne(base + 4, NO_CHANGE),         # bne  NO_CHANGE    opponent's monster
                0x207D,                            # movs r0,#0x7D
                0x0080,                            # lsls r0,r0,#2     500
                0x1824,                            # adds r4,r4,r0     ATK only
                _b(base + 12, EPILOGUE),           # b    EPILOGUE
            ]
            blob = struct.pack(f"<{len(hw)}H", *hw)
            assert_thumb1_only(blob, base)
            return blob


        # ---------------------------------------------------------------------------
        # PART C -- C2 "Once per turn, this card cannot be destroyed by card effects".
        # 0x021CC028(side, zone, commit, targeted) is the "would be destroyed -> survives?" check
        # (r4 zone, r5 side, r6 commit, [sp+4] targeted, [sp+8] cid). Abyssal Kingshark 0x1CA8's arm
        # is the native once-per-turn template: from 0x021CC1CA it queries a key-0x1CA8 marker on the
        # card's own zone chain, and on commit flashes the card, attaches a kind-2 (this-turn) marker
        # and returns 1. The stub sends the Seal there with targeted := 0 (the Seal ignores targeting)
        # and cid := 0 (marker already present -> Kingshark falls to 0x021CC264 -> stub sees cid 0 ->
        # return 0, instead of looping). [sp+4]/[sp+8] are push{r1-r7} slots, popped into scratch r2/r3.
        # Hosted in phantom 0x2348's dead field arm (field.arm_map): ov3, so puzzle-safe.
        # ---------------------------------------------------------------------------
        HOOK = 0x021CC264                         # default exit `movs r0,#0 ; pop {r1-r7,pc}`
        HOOK_STOCK = bytes.fromhex("0020febd")
        STUB = 0x021B2B10                         # phantom 0x2348 field arm, 36 B dead
        STUB_SIZE = 36
        STUB_STOCK = bytes.fromhex("0a99381cf0f704fc71f660f9002813d00a99381c002205f0a9fa6421414364186d1a09e0")
        KINGSHARK_TAIL = 0x021CC1CA               # `ldr r2,=0x1CA8 ; ... bl 0x021A1430 ...`


        def _bl(site: int, target: int) -> bytes:
            off = (target - site - 4) >> 1
            assert -(1 << 21) <= off < (1 << 21)
            return struct.pack("<HH", 0xF000 | ((off >> 11) & 0x7FF), 0xF800 | (off & 0x7FF))


        def build_stub(base: int = STUB) -> bytes:
            blob = (struct.pack("<4H", 0x9802,     # ldr  r0,[sp,#8]    cid
                                0x4905,            # ldr  r1,=0x10F5    (base+0x18)
                                0x4288,            # cmp  r0,r1
                                0xD104)            # bne  no            (base+0x12)
                    + struct.pack("<3H", 0x2000,   # movs r0,#0
                                  0x9001,          # str  r0,[sp,#4]    targeted := 0
                                  0x9002)          # str  r0,[sp,#8]    cid := 0
                    + _bl(base + 0x0E, KINGSHARK_TAIL)
                    + struct.pack("<3H", 0x2000,   # no: movs r0,#0
                                  0xBDFE,          # pop  {r1-r7,pc}
                                  0x0000)          # pad
                    + struct.pack("<I", DONOR_CID))
            assert len(blob) == 0x1C <= STUB_SIZE
            assert_thumb1_only(blob[:0x16], base)
            return blob


        # ---------------------------------------------------------------------------
        # PART D -- C3 "While you control 2 or more face-up Attack Position monsters, your opponent
        # cannot target your monster(s) with the lowest ATK for an attack." == Pixie Ring 0x20A3's
        # printed clause, verbatim. Its native block (0x021A65C2..0x021A662C, attack-target restriction
        # function) asks `0x021AC0C8(target side, 0x20A3, -1)` @0x021A65E2; for a Field Spell cid that
        # helper checks zone 0x0A (face-up, not negated). The BL is retargeted to a stub that answers
        # "Pixie Ring OR the Seal". ov3 because attack selection also runs in puzzles.
        # HOST: the tail of Abyssal Designator's dead selector block 0x02237D8C..0x02237E53, which
        # obedience_schooled zero-fills and uses up to 0x02237E1B -- so this part REQUIRES that
        # patch to have run first (asserted: the slot must read all-zero).
        # ---------------------------------------------------------------------------
        PRESENCE = 0x021AC0C8                     # (side, cid, -1) -> count of face-up active copies
        C3_SITE = 0x021A65E2                      # `bl 0x021AC0C8` in Pixie Ring's block
        C3_STUB = 0x02237E1C
        C3_SIZE = 0x1C


        def build_c3_stub(base: int = C3_STUB) -> bytes:
            blob = (struct.pack("<H", 0xB507)                     # push {r0,r1,r2,lr}
                    + _bl(base + 0x02, PRESENCE)                  # Pixie Ring (r1 = 0x20A3 from caller)
                    + struct.pack("<5H", 0x2800,                  # cmp  r0,#0
                                  0xD104,                         # bne  out          (base+0x14)
                                  0x9800,                         # ldr  r0,[sp,#0]   side
                                  0x4902,                         # ldr  r1,=0x10F5   (base+0x18)
                                  0x9A02)                         # ldr  r2,[sp,#8]   -1
                    + _bl(base + 0x10, PRESENCE)                  # the Seal
                    + struct.pack("<2H", 0xB003,                  # out: add sp,#12
                                  0xBD00)                         # pop  {pc}
                    + struct.pack("<I", DONOR_CID))
            assert len(blob) == C3_SIZE
            assert_thumb1_only(blob[:0x18], base)
            return blob


        # ---------------------------------------------------------------------------
        # PART E -- C4 "If this card is activated: Destroy all Special Summoned monsters you control."
        #        + C6 "You can only activate "The Seal of Orichalcos" once per Duel."
        # A Field Spell's on-activation effect is a cls0 record (Array of Revealing Light 0x14D1,
        # Ancient Forest 0x2092). Template: Special Hurricane 0x179E cls0 {0x022048FD, 0x021DD6CD, ...}
        # -- the shared destroy resolver sweeps slot2 into a mask and destroys it. Slot2 0x021DD6CC is
        # "monster zone, Special Summoned" with zone-predicate mask 0x1010 (both sides); FILT replays
        # its prologue with 0x1011 (side mode 1 = the activator's side) and joins it at 0x021DD6D4.
        # C6 = the kind-5 turn-log pair (dispatch.turnlog_once_per_duel_is_kind_5): COND (slot3)
        # returns 0 once posted, else 2 (= activatable with no target requirement); RES posts it
        # and then runs the destroy, so a negated activation is not counted (user ruling).
        # Count-neutral: drops cls0 phantom 0x234C (no card_prop; its only other mention is one ov5 AI
        # list entry). ov5 stubs: run only when the Seal itself is activated (normal duels).
        # main(ov3=True) (opt-in) puts the same three stubs in the ov3 pool instead
        # (cave3.CAVE3_SEAL_*), so C4/C6 also run in puzzles, and moves PART D's C3 stub to its own pool
        # slot (cave3.CAVE3_SEAL_C3) so the Seal no longer needs obedience_schooled, and its RES calls the stock
        # Field resolver 0x02204C7C first (Ancient Forest's shape) so the opponent's Field Spell is destroyed.
        # In-game confirmed by user (normal duel + puzzle, 'Works now: Ship it'), ov3 is the default.
        # ---------------------------------------------------------------------------
        CLS0_BASE, CLS0_COUNT, CLS0_STRIDE = 0x0227E64C, 0x51A, 24
        CLS0_DROP = 0x234C
        SS_FILTER_JOIN = 0x021DD6D4               # Special Hurricane's slot2 after `ldr r3,=0x1010`
        TURNLOG_QUERY = 0x021A14E8                # (side, 0x0B, cid, kind) -> nonzero if posted
        TURNLOG_POST = 0x021D2584                 # (side, cid, kind, 0)
        DESTROY_RES = 0x022048FC                  # shared "destroy the slot2 matches" resolver


        def c3_home(ov3: bool = False) -> int:
            """C3 stub home: Obedience Schooled's zero-filled host tail, or (ov3=True) its own pool slot,
            which drops the dependency on obedience_schooled."""
            if ov3:
                from otn_enhanced.effects import cave3
                return cave3.CAVE3_SEAL_C3
            return C3_STUB


        def homes(ov3: bool = False) -> tuple[int, int, int]:
            """(filt, cond, res) stub homes: the ov5 cave, or the ov3 pool (cave3) with ov3=True."""
            if ov3:
                from otn_enhanced.effects import cave3
                return cave3.CAVE3_SEAL_FILT, cave3.CAVE3_SEAL_COND, cave3.CAVE3_SEAL_RES
            return ov5_cave.CAVE_SEAL_FILT, ov5_cave.CAVE_SEAL_COND, ov5_cave.CAVE_SEAL_RES


        def cls0_record(filt: int, cond: int, res: int) -> tuple:
            return (DONOR_CID, res | 1, filt | 1, cond | 1, 0, 0)


        CLS0_RECORD = cls0_record(*homes())


        def build_filt(base: int = ov5_cave.CAVE_SEAL_FILT) -> bytes:
            blob = (struct.pack("<4H", 0xB538,    # push {r3,r4,r5,lr}   (= 0x021DD6CC's frame)
                                0x4B02,           # ldr  r3,=0x1011      (base+0xC)
                                0x1C0D,           # adds r5,r1,#0
                                0x1C14)           # adds r4,r2,#0
                    + _bl(base + 8, SS_FILTER_JOIN)   # its tail pops OUR frame back to the caller
                    + struct.pack("<I", 0x1011))
            assert_thumb1_only(blob[:0xC], base)
            return blob


        def build_cond(base: int = ov5_cave.CAVE_SEAL_COND) -> bytes:
            blob = (struct.pack("<5H", 0xB508,    # push {r3,lr}
                                0x8802,           # ldrh r2,[r0]     cid
                                0x7880,           # ldrb r0,[r0,#2]  side
                                0x210B,           # movs r1,#0xB
                                0x2305)           # movs r3,#5       per-Duel kind
                    + _bl(base + 0x0A, TURNLOG_QUERY)
                    + struct.pack("<6H", 0x2800,  # cmp  r0,#0
                                  0xD001,         # beq  ok
                                  0x2000,         # movs r0,#0      already activated this Duel
                                  0xBD08,         # pop  {r3,pc}
                                  0x2002,         # ok: movs r0,#2  activatable, no target needed
                                  0xBD08))        # pop  {r3,pc}
            assert_thumb1_only(blob, base)
            return blob


        def build_res(base: int = ov5_cave.CAVE_SEAL_RES) -> bytes:
            blob = (struct.pack("<6H", 0xB510,    # push {r4,lr}
                                0x1C04,           # adds r4,r0,#0
                                0x78A0,           # ldrb r0,[r4,#2]  side
                                0x8821,           # ldrh r1,[r4]     cid
                                0x2205,           # movs r2,#5
                                0x2300)           # movs r3,#0
                    + _bl(base + 0x0C, TURNLOG_POST)
                    + struct.pack("<H", 0x1C20)   # adds r0,r4,#0
                    + _bl(base + 0x12, DESTROY_RES)
                    + struct.pack("<H", 0xBD10))  # pop  {r4,pc}    r0 = 0 (done) from the resolver
            assert_thumb1_only(blob, base)
            return blob


        FIELD_RESOLVER = 0x02204C7C               # stock Field/Continuous activation: destroys the OPPONENT's Field zone
        PHASE_STATE = 0x0229AAFC                  # [+0x70] = resolver phase (Ancient Forest's literal)


        def build_res3(base: int) -> bytes:
            """ov3 RES = Ancient Forest 0x2092's cls0 +04 shape (0x0222C9B0): every phase but 0x78 runs the stock
            Field Spell resolver 0x02204C7C (phase 0x80: destroy the opponent's face-up Field Spell -> 0x7F;
            Field Barrier 0x1BD7 face-up -> desc[+0xB] = 1), and when it returns 0 go to phase 0x78. Phase 0x78:
            unless desc[+0xB], post C6's kind-5 log and run the shared destroy (C4). The ov5 RES skipped
            0x02204C7C, so the opponent's Field Spell stayed (user report 2026-10-08)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(2, PHASE_STATE)
            b.insn("LDR", "R2, [R2, #0x70]")
            b.insn("CMP", "R2, #0x78")
            b.insn("BEQ", "eff")
            b.call_addr(FIELD_RESOLVER)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("MOV", "R0, #0x78")
            b.label("out")
            b.insn("POP", "{R4, PC}")
            b.label("eff")
            b.insn("LDRB", "R0, [R4, #0xB]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call("turnlog_post", R0, R1, 5, 0)
            b.call_addr(DESTROY_RES, R4)
            b.label("done")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        BUILDERS = (build_filt, build_cond, build_res)          # same order as homes()
        BUILDERS3 = (build_filt, build_cond, build_res3)        # main(ov3=True)


        def builders(ov3: bool = False) -> tuple:
            return BUILDERS3 if ov3 else BUILDERS


        OV5_STUBS = tuple(zip(homes(), BUILDERS))


        # ---------------------------------------------------------------------------
        # PART F -- C5 "You cannot Special Summon monsters from the Extra Deck."
        # User rulings: only WHILE the Seal is face-up, and only summons FROM THE EXTRA DECK
        # (a Synchro/Fusion revived from the GY/banished is allowed).
        #  A  Synchro Summons: the mega-gate 0x021B9708's SYNCHRO wrapper 0x021B9EF0
        #     (`ldr r3,=0x021B9709 ; movs r1,#0x18 ; movs r2,#0 ; bx r3`, callers 0x0224956C / 0x02249F14)
        #     -- its LITERAL is retargeted to stub A: deny if the summoner's Seal is active, else the gate.
        #  B  every other Extra-Deck Special Summon: the cid-aware gate 0x021BA258 keeps the location
        #     code in r6 (0x0C = Extra Deck) and the side in r7 for its whole body; its unconditional
        #     `bl 0x021BA20C` @0x021BA35A is retargeted to stub B: deny if r6 == 0x0C and the Seal is
        #     active for r7, else the native call. (0x021BA368 is NOT used: obedience_schooled owns
        #     it and its verify() pins that exact BL.)
        # Both gates also run in puzzles, so the host must be ov3: the 92 B leaf 0x022212E4 of phantom
        # 0x0E82's arm in resolver 0x02221298 (no card_prop in stock or chain; entered only through
        # `ldrh r3,[r5] ; cmp r3,=0x0E82 ; bne 0x02221340`, no other inbound edge/pointer/pool word).
        # The arm itself is sealed (bne -> b) so the leaf is unreachable by construction.
        # ---------------------------------------------------------------------------
        C5_HOST = 0x022212E4
        C5_HOST_SIZE = 92
        C5_HOST_STOCK = bytes.fromhex("a87898f7d3f900283fd0a1780120e2780b1c03401e1c1e48142346431d488019161c5e4334308659"
                                      "a38970047600360ec00f76008019834227d1281c0023a3f7fffda078e17814220123b1f787fba078"
                                      "e178a2890123a4f711fb16e0")
        C5_ARM = 0x022212E2                       # `bne 0x02221340` -> `b 0x02221340`
        C5_ARM_STOCK, C5_ARM_SEALED = 0xD12D, 0xE02D
        SYNC_LIT = 0x021B9EF8                     # literal of the SYNCHRO wrapper 0x021B9EF0
        MEGA_GATE = 0x021B9708
        SSGATE_SITE = 0x021BA35A                  # `bl 0x021BA20C` inside 0x021BA258
        SSGATE_NATIVE = 0x021BA20C
        STUB_A, STUB_B = C5_HOST, C5_HOST + 0x1C


        def build_c5(base: int = C5_HOST) -> bytes:
            blob = (struct.pack("<2H", 0xB501,    # A: push {r0,lr}
                                0x490E)           #    ldr  r1,=0x10F5      (base+0x3C)
                    + _bl(base + 0x04, PRESENCE)  #    0x021AC0C8(side, 0x10F5, r2) -- r2 unused for a Field Spell
                    + struct.pack("<5H", 0x2800,  #    cmp  r0,#0
                                  0xBC01,         #    pop  {r0}
                                  0xD104,         #    bne  denyA           (base+0x18)
                                  0x2118,         #    movs r1,#0x18
                                  0x2200)         #    movs r2,#0
                    + _bl(base + 0x12, MEGA_GATE)
                    + struct.pack("<3H", 0xBD00,  #    pop  {pc}
                                  0x2000,         # denyA: movs r0,#0
                                  0xBD00)         #    pop  {pc}
                    + struct.pack("<5H", 0x2E0C,  # B: cmp  r6,#0x0C        Extra Deck?
                                  0xD108,         #    bne  chainB          (base+0x32)
                                  0xB503,         #    push {r0,r1,lr}
                                  0x1C38,         #    adds r0,r7,#0        summoner
                                  0x4905)         #    ldr  r1,=0x10F5      (base+0x3C)
                    + _bl(base + 0x26, PRESENCE)
                    + struct.pack("<9H", 0x2800,  #    cmp  r0,#0
                                  0xBC07,         #    pop  {r0,r1,r2}      r2 = lr
                                  0x4696,         #    mov  lr,r2           (flags kept)
                                  0xD101,         #    bne  denyB           (base+0x36)
                                  0x4B03,         # chainB: ldr r3,=0x021BA20D (base+0x40)
                                  0x4718,         #    bx   r3
                                  0x2000,         # denyB: movs r0,#0
                                  0x4770,         #    bx   lr
                                  0x0000)         #    pad
                    + struct.pack("<2I", DONOR_CID, SSGATE_NATIVE | 1))
            assert len(blob) == 0x44 <= C5_HOST_SIZE
            assert_thumb1_only(blob[:0x3A], base)
            return blob


        def _cls0_cids(ov) -> list[int]:
            return [struct.unpack_from("<H", ov, _off(CLS0_BASE + i * CLS0_STRIDE))[0] for i in range(CLS0_COUNT)]


        def apply_cls0(ov: bytearray, record: tuple = CLS0_RECORD) -> None:
            """Count-neutral sorted insert of *record* over the phantom CLS0_DROP."""
            keys = _cls0_cids(ov)
            if DONOR_CID in keys:
                i = keys.index(DONOR_CID)
                assert struct.unpack_from("<6I", ov, _off(CLS0_BASE + i * CLS0_STRIDE)) == record, \
                    "cls0 already holds a different 0x10F5 record"
                return
            assert keys.count(CLS0_DROP) == 1, f"phantom 0x{CLS0_DROP:04X} not found exactly once"
            dst = keys.index(CLS0_DROP)
            pos = sum(1 for k in keys if k < DONOR_CID)
            row = lambda i: _off(CLS0_BASE + i * CLS0_STRIDE)
            if pos > dst:
                ov[row(dst):row(pos - 1)] = bytes(ov[row(dst + 1):row(pos)])
                pos -= 1
            elif pos < dst:
                ov[row(pos + 1):row(dst + 1)] = bytes(ov[row(pos):row(dst)])
            struct.pack_into("<6I", ov, row(pos), *record)
            after = _cls0_cids(ov)
            assert all(after[i] <= after[i + 1] for i in range(CLS0_COUNT - 1)), "cls0 lost its sort order"
            print(f"E  cls0: dropped 0x{CLS0_DROP:04X} @{dst}, inserted 0x{DONOR_CID:04X} @{pos}")


        def _patch(ov: bytearray, addr: int, new: bytes, stock: bytes, what: str) -> None:
            cur = bytes(ov[_off(addr):_off(addr) + len(stock)])
            if cur[:len(new)] != new:
                assert cur == stock, f"{what} @0x{addr:08X} = {cur.hex()}, not stock"
                ov[_off(addr):_off(addr) + len(new)] = new
            print(f"{what} @0x{addr:08X} -> {new.hex()}")



        def install(rom, view):
            ov = view.buf
            ov3 = True
            _patch(ov, ARM, build_arm(), STOCK, "A  C1 arm")
            _patch(ov, STUB, build_stub(), STUB_STOCK, "C  C2 stub")
            _patch(ov, HOOK, _bl(HOOK, STUB), HOOK_STOCK, "C  C2 hook")
            c3 = c3_home(ov3)
            _patch(ov, c3, build_c3_stub(c3), b"\0" * C3_SIZE,
                   "D  C3 stub (ov3 pool: needs step 0)" if ov3 else "D  C3 stub (needs obedience_schooled first)")
            _patch(ov, C3_SITE, _bl(C3_SITE, c3), _bl(C3_SITE, PRESENCE), "D  C3 hook")
            addrs = homes(ov3)
            apply_cls0(ov, cls0_record(*addrs))
            _patch(ov, C5_HOST, build_c5(), C5_HOST_STOCK[:0x44], "F  C5 stubs A/B (phantom 0x0E82 leaf)")
            _patch(ov, C5_ARM, struct.pack("<H", C5_ARM_SEALED), struct.pack("<H", C5_ARM_STOCK),
                   "F  0x0E82 arm sealed")
            _patch(ov, SYNC_LIT, struct.pack("<I", STUB_A | 1), struct.pack("<I", MEGA_GATE | 1),
                   "F  SYNCHRO wrapper literal")
            _patch(ov, SSGATE_SITE, _bl(SSGATE_SITE, STUB_B), _bl(SSGATE_SITE, SSGATE_NATIVE), "F  SS gate hook")
            for addr, build in zip(addrs, builders(ov3)):
                blob = build(addr)
                if ov3:   # ov3 pool: cave3.put asserts the slot is zero (step 0 ran on *src*)
                    from otn_enhanced.effects import cave3
                    cave3.put(ov, addr, blob)
                elif ov5_cave.read_cave(rom, addr, len(blob)) != blob:
                    ov5_cave.install_cave(rom, addr, blob, reserve=0x20)
                print(f"E  {'ov3' if ov3 else 'ov5'} stub @0x{addr:08X} ({len(blob)} B)")

        def check_fn(c, rom, view):
            ov = view.buf
            out = c.out
            from otn_enhanced.effects import cave3
            keys = _cls0_cids(ov)
            # the live record decides which home (ov5 cave or ov3 pool) to check
            live = (struct.unpack_from("<6I", ov, _off(CLS0_BASE + keys.index(DONOR_CID) * CLS0_STRIDE))
                    if DONOR_CID in keys else None)
            addrs = next((h for h in (homes(False), homes(True)) if live == cls0_record(*h)), None)
            h1, h2 = struct.unpack_from("<HH", ov, _off(C3_SITE))   # live C3 BL target decides its home
            c3 = C3_SITE + 4 + ((((h1 & 0x7FF) << 12 | (h2 & 0x7FF) << 1) ^ 1 << 22) - (1 << 22))
            blob = build_arm()
            jt5 = 0x021B2766 + struct.unpack_from("<H", ov, _off(0x021B2764 + 10))[0]
            ok_text, msg = card_text.check_rom_text(out, DONOR_CID)
            checks = [
                ("A arm bytes", bytes(ov[_off(ARM):_off(ARM) + len(blob)]) == blob),
                ("A jump table entry 5 -> arm", jt5 == ARM),
                ("A switch pivot literal 0x10F5 intact",
                 struct.unpack_from("<I", ov, _off(0x021B29AC))[0] == DONOR_CID),
                (f"B text: {msg}", ok_text),
                ("C stub bytes", bytes(ov[_off(STUB):_off(STUB) + 0x1C]) == build_stub()),
                ("C hook BL (or Block Dragon's C2 front ahead of the stub)", bytes(ov[_off(HOOK):_off(HOOK) + 4]) in {_bl(HOOK, f) for f in ov5_cave.dc_ahead_of(STUB)}),
                ("C Kingshark tail intact (ldr r2,=0x1CA8 / bl 0x021A1430)",
                 bytes(ov[_off(KINGSHARK_TAIL):_off(KINGSHARK_TAIL) + 10]).hex() == "2f4a281c211cd5f72ef9"
                 and struct.unpack_from("<I", ov, _off(0x021CC288))[0] == 0x1CA8),
                (f"D C3 hook BL -> {c3:#010x}", c3 in (c3_home(False), c3_home(True))),
                ("D C3 stub bytes", bytes(ov[_off(c3):_off(c3) + C3_SIZE]) == build_c3_stub(c3)),
                ("D Pixie Ring literal still feeds the stub",
                 struct.unpack_from("<I", ov, _off(0x021A664C))[0] == 0x20A3),
                ("E cls0: exactly one 0x10F5 record, phantom gone, sorted",
                 keys.count(DONOR_CID) == 1 and CLS0_DROP not in keys
                 and all(keys[i] <= keys[i + 1] for i in range(CLS0_COUNT - 1))),
                (f"E cls0 record ({'ov3' if addrs == homes(True) else 'ov5'} stubs)", addrs is not None),
                ("E stubs", addrs is not None
                 and all(cave3.read_code(rom, ov, a, len(b(a))) == b(a) for a, b in zip(addrs, builders(addrs == homes(True))))),
                ("F C5 stubs", bytes(ov[_off(C5_HOST):_off(C5_HOST) + 0x44]) == build_c5()),
                ("F 0x0E82 arm sealed", struct.unpack_from("<H", ov, _off(C5_ARM))[0] == C5_ARM_SEALED),
                ("F SYNCHRO wrapper -> stub A", struct.unpack_from("<I", ov, _off(SYNC_LIT))[0] == STUB_A | 1),
                ("F SS gate @0x021BA35A -> stub B", bytes(ov[_off(SSGATE_SITE):_off(SSGATE_SITE) + 4]) == _bl(SSGATE_SITE, STUB_B)),
                ("E Special Hurricane slot2 join point intact",
                 bytes(ov[_off(0x021DD6CC):_off(0x021DD6D8)]).hex() == "38b50c4b0d1c141cf9f7b4fb"),
            ]
            for label, good in checks:
                c.ok(good, label)

        return Compiled(installs=(install,), checks=(check_fn,))


seal_effects = field_spell_monsters_gain_500_atk_not_destroyed_by_card_effects_protect_lowest_atk_destroy_own_special_summons_once_per_duel_no_extra_deck_summons

SPEC = card(0x10F5, seal_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_seal_of_orichalcos.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

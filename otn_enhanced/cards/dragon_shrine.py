"""Dragon Shrine (Normal Spell) on The Puppet Magic of Dark Ruler 0x14C1.

    Send 1 Dragon monster from your Deck to the GY, then, if that monster in your GY is a Dragon Normal Monster, you
    can send 1 more Dragon monster from your Deck to the GY. You can only activate 1 "Dragon Shrine" per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS0, CRITERIA, Compiled, Edit, NATIVE_COND
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave


@dataclass(frozen=True)
class activate_once_per_turn_send_dragon_from_deck_then_another_if_dragon_normal:
    """'Send 1 Dragon monster from your Deck to the GY, then, if that monster in your GY is a Dragon Normal Monster, you can
    send 1 more Dragon monster from your Deck to the GY. You can only activate 1 "Dragon Shrine" per turn.' The Normal
    Spell donor's criteria row (-> select from the DECK, Dragon word) and cls0 record (-> Foolish Burial's deck-send
    resolver) are rewritten IN PLACE. Clause 3: condition denies a second activation (turn-log kind 1, raw desc[+2]) then
    runs the native condition; the cost resets the clause-2 latch and stamps the log (the cost runs once per
    activation). Clause 2 (always sends the second card, never optional: mode forced to 0, the known-good prompt) is an
    arm of the SHARED phase-0x7C dispatcher in `deck_send_follow_hook` (also serves Accel Synchron): this verb only
    installs that module's gate and dispatcher, idempotently, and never re-points the gate itself."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import deck_send_follow_hook
        CAVE_DS_COND, CAVE_DS_COST = ov5_cave.CAVE_DS_COND, ov5_cave.CAVE_DS_COST
        CAVE_DS_FOLLOW, CAVE_DS_SCRATCH = ov5_cave.CAVE_DS_FOLLOW, ov5_cave.CAVE_DS_SCRATCH
        DONOR_CID = cid
        DECK_HANDLER = 0x0223CAD9   # "select from the DECK" (== 3DS 0x004B1BE8)
        DRAGON_WORD = 0x08000002    # race << 3 = Dragon; Konami's own value (3DS + Dragon Ravine)

        CRIT_BEFORE = (DONOR_CID, 0xFFFF, 0x0223DCB1, 0x00000000)
        CRIT_AFTER = (DONOR_CID, 0xFFFF, DECK_HANDLER, DRAGON_WORD)

        # ---- the cls0 effect table (dispatch.cls_tables) -----------------------------
        CLS0_BASE, CLS0_COUNT, CLS0_STRIDE = 0x0227E64C, 0x51A, 24

        # slots +04 .. +14; Foolish Burial 0x1474's cls0[305] verbatim
        CLS0_BEFORE = (0x02213DC5, 0x021DE22D, 0x021F533D, 0x00000000, 0x02235605)
        CLS0_AFTER = (0x02208DD5, 0x00000000, 0x021F0B19, 0x00000000, 0x00000000)

        # ---- clause 2 / clause 3 engine addresses (all established by disassembly) ----
        TURNLOG_QUERY = 0x021A14E8   # (side, 0xB, cid, kind) -> nonzero iff already logged this turn
        TURNLOG_POST = 0x021D2584    # (side, cid, kind, 0) -> log it (wraps 0x021C479C, event 0x35)
        TURNLOG_SLOT = 0x0B
        TURNLOG_KIND = 1             # kind 1 = card/effect activation (Pot of Duality's HOPT)
        NATIVE_COND = 0x021F0B18     # Foolish Burial's activation condition (ARM addr, bit0 clear)
        CARD_TYPE_OF = 0x0202ABF8    # (cid) -> card_prop card_type >> 1  (ARM9, always resident)
        CT_NORMAL = 0                # card_type 1  = Normal Monster       (1 >> 1 == 0)
        CT_NORMAL_TUNER = 15         # card_type 31 = Normal Tuner Monster (31 >> 1 == 15)

        PLAYER_BASE, PLAYER_STRIDE = 0x0229AC94, 0xB3C   # ram.gy_and_banished (VERIFIED)
        GY_ARRAY, GY_COUNT = 0x55C, 0x14

        # ⚠️ The phase-0x7C gate constants (GATE_ADDR / GATE_STOCK / the native cid list)
        # used to live here.  They moved to `deck_send_follow_hook` when the gate was lifted
        # into a shared module  -- DO NOT re-declare them here, or the two
        # copies will drift and one of them will silently be the wrong one.

        PHASE_SELECT = 0x7F          # re-entering here re-runs the selection step
        PHASE_DONE = 0x64
        ST_COUNT, ST_MODE = 0x74, 0x78   # [r5+0x74] = send count, [r5+0x78] = mode

        def _build_cond() -> bytes:
            """CLAUSE 3 -- activation condition: deny a second activation this turn.

            cond(desc, arg1):
                if TURNLOG_QUERY(desc[+2], 0xB, desc[+0], 1): return 0
                return NATIVE_COND(desc, arg1)

            The probe uses the RAW desc[+2], not the desc[+2]^desc[+6] XOR: this mirrors Pot
            of Duality's native condition 0x02203259 instruction for instruction (`ldrb r0,
            [r5,#2] ; mov r1,#0xB ; ldrh r2,[r5] ; mov r3,#1 ; bl 0x021A14E8`). arg1 is
            carried in r4 and restored, because the native condition is a 2-argument function.
            """
            a = EffectBuilder()
            a.prologue([R4, R5])
            a.insn("ADD", "R5, R0, #0x0")        # r5 = descriptor
            a.insn("ADD", "R4, R1, #0x0")        # r4 = arg1 (the native cond reads it)
            a.insn("LDRB", "R0, [R5, #0x2]")     # side
            a.insn("MOV", "R1, #0x%X" % TURNLOG_SLOT)
            a.insn("LDRH", "R2, [R5, #0x0]")     # cid
            a.insn("MOV", "R3, #0x%X" % TURNLOG_KIND)
            a.call_addr(TURNLOG_QUERY & ~1)
            a.insn("CMP", "R0, #0x0")
            a.insn("BNE", "deny")                # already activated a Dragon Shrine this turn
            a.insn("ADD", "R0, R5, #0x0")
            a.insn("ADD", "R1, R4, #0x0")
            a.call_addr(NATIVE_COND)
            a.insn("POP", "{R4, R5, PC}")
            a.label("deny")
            a.epilogue(0)
            code = a.assemble(CAVE_DS_COND)
            assert_thumb1_only(code, CAVE_DS_COND)
            return code


        def _build_cost() -> bytes:
            """CLAUSE 3 -- cost slot: stamp the turn log, and reset the clause-2 latch.

            cost(desc, ...):
                [CAVE_DS_SCRATCH] = 0          ; a fresh activation never inherits a stale latch
                TURNLOG_POST(desc[+2], desc[+0], 1, 0)
                return 1

            The cost slot runs exactly ONCE per activation -- the activation state machine
            0x02217F80 tests desc[+7], runs slot4 only while it is clear, then sets desc[+7]=1
            (dispatch.step_table_target_select) -- which is what makes it the right place for
            both the stamp and the reset. Returning 1 is mandatory: 0 aborts the activation.
            """
            a = EffectBuilder()
            a.prologue([R4])
            a.insn("ADD", "R4, R0, #0x0")        # r4 = descriptor
            a.ldr_const(0, CAVE_DS_SCRATCH)
            a.insn("MOV", "R1, #0x0")
            a.insn("STR", "R1, [R0, #0x0]")      # clear the clause-2 re-entry latch
            a.insn("LDRB", "R0, [R4, #0x2]")     # side
            a.insn("LDRH", "R1, [R4, #0x0]")     # cid
            a.insn("MOV", "R2, #0x%X" % TURNLOG_KIND)
            a.insn("MOV", "R3, #0x0")
            a.call_addr(TURNLOG_POST & ~1)
            a.epilogue(1)
            code = a.assemble(CAVE_DS_COST)
            assert_thumb1_only(code, CAVE_DS_COST)
            return code


        def _build_follow() -> bytes:
            """CLAUSE 2 -- Dragon Shrine's BODY for the shared phase-0x7C hook.

            ⚠️ 2026-09-03: this stub used to own the gate at 0x02208F42 and do its own cid
            dispatch (three native cids -> 0x02208F56, 0x14C1 -> here, else -> 0x02209046).
            That gate is now owned by ``deck_send_follow_hook``, which dispatches to this
            body as a registered arm, because Accel Synchron clause 2 needs the same phase
            and a second module re-pointing the gate would have broken this clause.
            **The body below is byte-for-byte what it always did; only the dispatch moved.**
            Proved by execution: ``scratch/followhook_equiv.py``.

            Entered by a `bx` from the shared dispatcher, NOT a call: the resolver's own
            frame (`push {r1-r7,lr}` at 0x02208DD4) is still live, r4 = descriptor and
            r5 = the phase-state block. So LR is free to clobber -- the return address is on
            the stack -- and every exit is a replica of the resolver's own epilogue
            `pop {r1,r2,r3,r4,r5,r6,r7,pc}`.

                if [SCRATCH] == desc: [SCRATCH] = 0 ; return 0x64        ; second pass -- finish
                n = player[side].gy_count ; if n == 0: return 0x64
                t = CARD_TYPE_OF(player[side].gy[n-1] & 0x3FFF)
                if t not in (0, 15): return 0x64                        ; not a Normal Monster
                [SCRATCH] = desc ; count = 1 ; mode = 0 ; return 0x7F    ; run one more send

            Setting mode = 0 makes phase 0x7F pick the SAME prompt family as the first send
            (`count+6`), which is the known-good path. The mode!=0 family (`mode+0x27`) is what
            a bare re-entry would have used and is still undecoded -- see the findings note.

            ✅ 2026-09-03: "returning 0x7F from phase 0x7C re-enters selection" is NO LONGER
            an assumption. The activation state machine stores the resolver's return value AS
            the next phase (`0x02218042 strh r0,[r4,#0x18]`, reloaded to [0x0229AAFC+0x70] at
            0x02218038) -- see ``dispatch.resolver_return_is_next_phase``.
            """
            a = EffectBuilder()
            a.ldr_const(2, CAVE_DS_SCRATCH)
            a.insn("LDR", "R3, [R2, #0x0]")
            a.insn("CMP", "R3, R4")
            a.insn("BNE", "first")
            a.insn("MOV", "R3, #0x0")            # second pass: clear the latch and finish
            a.insn("STR", "R3, [R2, #0x0]")
            a.insn("B", "done")

            a.label("first")
            a.insn("LDRB", "R0, [R4, #0x2]")
            a.insn("LDRB", "R1, [R4, #0x6]")
            a.insn("EOR", "R0, R1")              # side = desc[+2] ^ desc[+6]
            a.ldr_const(1, PLAYER_STRIDE)
            a.insn("MUL", "R1, R0")              # r1 = side * 0xB3C
            a.ldr_const(3, PLAYER_BASE)
            a.insn("ADD", "R1, R1, R3")          # r1 = this side's player struct
            a.insn("LDR", "R3, [R1, #0x%X]" % GY_COUNT)
            a.insn("CMP", "R3, #0x0")
            a.insn("BEQ", "done")
            a.insn("SUB", "R3, #0x1")            # index of the card just sent
            a.insn("LSL", "R3, R3, #0x2")
            a.ldr_const(2, GY_ARRAY)
            a.insn("ADD", "R1, R1, R2")
            a.insn("LDR", "R0, [R1, R3]")        # the GY top word
            a.ldr_const(2, 0x3FFF)
            a.insn("AND", "R0, R2")              # -> its cid
            a.call_addr(CARD_TYPE_OF)
            a.insn("CMP", "R0, #0x%X" % CT_NORMAL)
            a.insn("BEQ", "normal")
            a.insn("CMP", "R0, #0x%X" % CT_NORMAL_TUNER)
            a.insn("BNE", "done")

            a.label("normal")
            a.ldr_const(2, CAVE_DS_SCRATCH)
            a.insn("STR", "R4, [R2, #0x0]")      # latch THIS activation
            a.insn("MOV", "R3, #0x1")
            a.insn("STR", "R3, [R5, #0x%X]" % ST_COUNT)   # send exactly one more
            a.insn("MOV", "R3, #0x0")
            a.insn("STR", "R3, [R5, #0x%X]" % ST_MODE)    # known-good prompt family
            a.insn("MOV", "R0, #0x%X" % PHASE_SELECT)
            a.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")

            a.label("done")
            a.insn("MOV", "R0, #0x%X" % PHASE_DONE)
            a.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
            code = a.assemble(CAVE_DS_FOLLOW)
            assert_thumb1_only(code, CAVE_DS_FOLLOW)
            return code

        stubs = ((CAVE_DS_COND, _build_cond(), "condition"), (CAVE_DS_COST, _build_cost(), "cost"),
                 (CAVE_DS_FOLLOW, _build_follow(), "phase-0x7C body"))

        def install(rom, view):
            deck_send_follow_hook.apply_gate(view.buf)
            blob = deck_send_follow_hook.build_dispatcher()
            try:
                ov5_cave.install_cave(rom, ov5_cave.CAVE_FOLLOWHOOK, blob, reserve=0x80)
            except AssertionError as exc:
                if "not free" not in str(exc) or ov5_cave.read_cave(rom, ov5_cave.CAVE_FOLLOWHOOK, len(blob)) != blob:
                    raise

        def check(c, rom, view):
            c.ok(deck_send_follow_hook.verify_gate(bytes(view.buf)), "phase-0x7C gate -> shared CAVE_FOLLOWHOOK")
            disp = deck_send_follow_hook.build_dispatcher()
            c.ok(ov5_cave.read_cave(rom, ov5_cave.CAVE_FOLLOWHOOK, len(disp)) == disp,
                 "the shared dispatcher is installed with every registered arm")

        return Compiled(
            stubs,
            edits=(Edit(CRITERIA, cid, (cid, 0xFFFF, 0x0223DCB1, 0), (cid, 0xFFFF, DECK_HANDLER, DRAGON_WORD)),
                   Edit(CLS0, cid, (cid,) + CLS0_BEFORE, (cid, CLS0_AFTER[0], 0, CAVE_DS_COND | 1, CAVE_DS_COST | 1, 0))),
            installs=(install,), checks=(check,))



SPEC = card(0x14C1, activate_once_per_turn_send_dragon_from_deck_then_another_if_dragon_normal())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_dragon_shrine.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

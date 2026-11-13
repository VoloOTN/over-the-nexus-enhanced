"""White Dragon Ninja (LIGHT / Dragon / Level 7 / 2700 / 1200) on Dunames Dark Witch 0x12B2.

    Spells/Traps you control cannot be destroyed by card effects.

("Cannot be Special Summoned, except with a "Ninjitsu Art" card's effect" is not built: no summon-restriction route
exists for it; see notes/white-dragon-ninja-findings.md.)
"""
import struct
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, Compiled
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class spells_traps_you_control_cannot_be_destroyed_by_card_effects_while_this_monster_is_face_up:
    """'Spells/Traps you control cannot be destroyed by card effects.' The "may this card effect affect this card" predicate
    0x021B021C splits by slot: slots 0..4 are monster zones (Safe Zone / Dreadmaster links), 5..0xA the Spell/Trap tail, so the
    clause is hooked at the tail's FIRST link (covers all card effects, not just the opponent's) with an ov5 leaf that
    inlines 0x021AC204's own per-slot acceptance test over the target's controller's monster zones (cid match, slot live,
    bit 26 of [slot+0x44] clear, per-slot mask clear). NOT 0x021AC5A8: its extra bit-18 gate was clear on 48 of 73 face-up
    monsters, so the protection expired at the turn boundary in-game. Miss -> replays the displaced native call."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.rom.overlay_io import RAM_BASE
        _off = lambda a: a - RAM_BASE
        DONOR_CID = cid
        PROT_HOOK = 0x021B07F4             # the displaced `bl 0x021A1430`
        PROT_NATIVE = 0x021A1430           # family-1 rider lookup (kind nibble < 6)
        PROT_PROTECTED_EXIT = 0x021B0296   # where the caller branches on a nonzero return
        PROT_AFFECTABLE_EXIT = 0x021B081E  # `movs r0,#1` -- the fall-through
        PROT_TAIL_KEY_POOL = 0x021B0824    # holds 0x0D6C, the first link's rider key
        PROT_TAIL_KEY = 0x00000D6C
        PROT_ZONE_SPLIT = 0x021B059C       # `cmp r5,#4`
        PROT_ZONE_SPLIT_ENC = 0x2D04

        # --- ROUND 2: why this stub scans the zones itself -------------------------
        # Round 1 delegated to 0x021AC5A8(side, cid), the primitive the ROM's own
        # Dreadmaster leaf at 0x021B05FE uses.  IN-GAME the protection worked and then
        # EXPIRED at the turn boundary.  Diagnosed offline from two savestates of the
        # same board (rom_wdn.ml2 protected / rom_wdn.ml3 destroyed):
        #
        #   0x021AC5A8's loop carries a flag test that 0x021AC204's does NOT --
        #       0x021AC5F2  lsrs r1,r0,#0x12
        #       0x021AC5F4  movs r0,#1
        #       0x021AC5F6  tst  r0,r1
        #       0x021AC5F8  beq  next          <-- BIT 18 of [slot+0x44] must be SET
        #   and bit 18 is clear on 48 of the 73 face-up field monsters across the whole
        #   savestate corpus.  On the donor it went 0x00448110 -> 0x00008110 across the
        #   turn change while cid, slot, 0x021A32B4 presence, bit 26 and the 0x0229C314
        #   mask were all IDENTICAL.  0x021AC5A8 has only 3 callers, two of them in the
        #   battle chains -- it is not the "do you control X" primitive.
        #
        # So the stub now inlines 0x021AC204's OWN per-slot acceptance test (the one
        # with 201 callers) over slots 0..4 of a single side.
        CID_AT = 0x021A36EC              # (side, slot) -> the cid in that field slot
        SLOT_PRESENT = 0x021A32B4        # (side, slot) -> nonzero if the slot holds a live card
        PLAYER_ARRAY = 0x0229AC94        # ram.player_array base
        SIDE_STRIDE = 0x00000B3C         # per-side stride
        SLOT_STRIDE = 0x14               # per-slot stride; the flag word is at +0x44
        GLOBAL_SLOT_MASK = 0x0229C314    # u32; bit (slot + side*16) set => skip that slot

        PROT_RESERVE = 0x80                # cave reserve for the stub

        def _u16(ov: bytes, addr: int) -> int:
            return struct.unpack_from("<H", ov, _off(addr))[0]


        def _u32(ov: bytes, addr: int) -> int:
            return struct.unpack_from("<I", ov, _off(addr))[0]


        def _thumb_bl(at: int, target: int) -> bytes:
            """Encode the ARMv4T two-halfword BL at *at* to *target*."""
            off = target - (at + 4)
            assert -0x400000 <= off < 0x400000, "BL out of range"
            hi = 0xF000 | ((off >> 12) & 0x7FF)
            lo = 0xF800 | ((off >> 1) & 0x7FF)
            return struct.pack("<HH", hi, lo)


        def _bl_target(ov: bytes, addr: int) -> int:
            """Resolve the ARMv4T two-halfword BL at *addr* to its target address."""
            hi, lo = struct.unpack_from("<HH", ov, _off(addr))
            assert (hi & 0xF800) == 0xF000 and (lo & 0xF800) == 0xF800, \
                f"0x{addr:08X} is not a two-halfword BL (reads 0x{hi:04X} 0x{lo:04X})"
            off = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
            if off & 0x400000:
                off -= 0x800000
            return addr + 4 + off

        def build_prot_stub(base: int) -> bytes:
            """The S/T destruction-protection leaf, hosted in the ov5 cave.

            Entered by the `bl` that replaced 0x021B07F4, so on entry the register state
            is whatever 0x021B021C's S/T tail set up:

                r4 = 0x0B                                   -- MUST be preserved
                r5 = 0x0D6C  (the first link's rider key)   -- MUST be preserved
                r6 = the TARGET Spell/Trap's controller
                r7 = the acting card's 0x24-byte descriptor -- MUST be preserved

            Returns nonzero to make the caller take `b 0x021B0296` (PROTECTED), zero to
            let it fall through to the `targets` half of the tail.

            The body is 0x021AC204's per-slot acceptance test -- cid match, then
            0x021A32B4, then bit 26 of [slot+0x44] clear, then the 0x0229C314 per-slot
            mask bit clear -- run over slots 0..4 of ONE side.  See the ROUND 2 note
            above for why it is not a call to 0x021AC5A8.

                push {r4,lr}               ; r4 is the only callee register we borrow
                movs r4,#0                 ; slot = 0
            loop:
                adds r0,r6,#0              ; side = the target S/T's controller
                adds r1,r4,#0
                ldr  r3,=CID_AT|1
                blx  r3                    ; -> the cid in that monster zone
                ldr  r3,=DONOR_CID
                cmp  r0,r3
                bne  next
                adds r0,r6,#0
                adds r1,r4,#0
                ldr  r3,=SLOT_PRESENT|1
                blx  r3
                cmp  r0,#0
                beq  next
                movs r0,#1                 ; flags = [PLAYER_ARRAY + (side&1)*0xB3C + slot*0x14 + 0x44]
                ands r0,r6
                ldr  r1,=SIDE_STRIDE
                muls r0,r1
                ldr  r1,=PLAYER_ARRAY
                adds r0,r0,r1
                movs r1,#0x14
                muls r1,r4
                adds r0,r0,r1
                ldr  r0,[r0,#0x44]
                lsrs r0,r0,#0x1A
                movs r1,#1
                tst  r0,r1
                bne  next                  ; bit 26 set -> this copy does not count
                ldr  r0,=GLOBAL_SLOT_MASK
                ldr  r0,[r0]
                lsls r1,r6,#4
                adds r1,r1,r4
                lsrs r0,r1
                movs r1,#1
                tst  r0,r1
                bne  next                  ; the per-slot mask bit is set -> skip
                movs r0,#1
                pop  {r4,pc}               ; FOUND -> PROTECTED
            next:
                adds r4,r4,#1
                cmp  r4,#5
                blt  loop                  ; monster zones only, exactly like 0x021AC204
                adds r0,r6,#0              ; miss -> replay the displaced native call
                movs r1,#0x0B
                adds r2,r5,#0
                ldr  r3,=PROT_NATIVE|1
                blx  r3
                pop  {r4,pc}
            """
            assert base % 4 == 0, f"stub base 0x{base:08X} must be 4-aligned"
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("MOV", "R4, #0x0")
            b.label("loop")
            b.call_addr(CID_AT, R6, R4, via=R3)               # -> the cid in that monster zone
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "next")
            b.call_addr(SLOT_PRESENT, R6, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "next")
            b.insn("MOV", "R0, #0x1")                         # flags = [PLAYER_ARRAY + (side&1)*0xB3C + slot*0x14 + 0x44]
            b.insn("AND", "R0, R6")
            b.ldr_const(1, SIDE_STRIDE)
            b.insn("MUL", "R0, R1")
            b.ldr_const(1, PLAYER_ARRAY)
            b.insn("ADD", "R0, R0, R1")
            b.insn("MOV", "R1, #0x14")
            b.insn("MUL", "R1, R4")
            b.insn("ADD", "R0, R0, R1")
            b.insn("LDR", "R0, [R0, #0x44]")
            b.insn("LSR", "R0, R0, #0x1A")
            b.insn("MOV", "R1, #0x1")
            b.insn("TST", "R0, R1")
            b.insn("BNE", "next")                             # bit 26 set -> this copy does not count
            b.ldr_const(0, GLOBAL_SLOT_MASK)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R6, #0x4")
            b.insn("ADD", "R1, R1, R4")
            b.insn("LSR", "R0, R1")
            b.insn("MOV", "R1, #0x1")
            b.insn("TST", "R0, R1")
            b.insn("BNE", "next")                             # the per-slot mask bit is set -> skip
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")                         # FOUND -> PROTECTED
            b.label("next")
            b.insn("ADD", "R4, R4, #0x1")
            b.insn("CMP", "R4, #0x5")
            b.insn("BLT", "loop")                             # monster zones only, exactly like 0x021AC204
            b.insn("ADD", "R0, R6, #0x0")                     # miss -> replay the displaced native call
            b.insn("MOV", "R1, #0x0B")
            b.insn("ADD", "R2, R5, #0x0")
            b.call_addr(PROT_NATIVE, via=R3)
            b.insn("POP", "{R4, PC}")
            blob = b.assemble(base, pad="nop")
            assert_thumb1_only(blob[:0x60], base)             # never a bare capstone disasm
            assert len(blob) <= PROT_RESERVE, f"prot stub {len(blob):#x} > reserve 0x{PROT_RESERVE:X}"
            return blob

        def _assert_preconditions(ov: bytes) -> None:
            """Pin every overlay-3 fact PART C depends on, before writing anything."""
            # The zone split -- the whole reason this hook is S/T-only.
            assert _u16(ov, PROT_ZONE_SPLIT) == PROT_ZONE_SPLIT_ENC, (
                f"0x{PROT_ZONE_SPLIT:08X} is not `cmp r5,#4` "
                f"(reads 0x{_u16(ov, PROT_ZONE_SPLIT):04X}) -- 0x021B021C's monster/S-T "
                f"split has moved")
            # The tail's first rider key, which our stub replays through r5.
            assert _u32(ov, PROT_TAIL_KEY_POOL) == PROT_TAIL_KEY, (
                f"the S/T tail's key literal @0x{PROT_TAIL_KEY_POOL:08X} is "
                f"0x{_u32(ov, PROT_TAIL_KEY_POOL):08X}, expected 0x{PROT_TAIL_KEY:08X}")
            # The tail's shape around the hook: r5 -> r2, pseudo-slot 0x0B, r6 -> r0.
            assert _u16(ov, 0x021B07EC) == 0x1C30, "0x021B07EC is not `adds r0,r6,#0`"
            assert _u16(ov, 0x021B07EE) == 0x210B, "0x021B07EE is not `movs r1,#0x0B`"
            assert _u16(ov, 0x021B07F0) == 0x1C2A, "0x021B07F0 is not `adds r2,r5,#0`"
            # The exits.
            assert _u16(ov, PROT_AFFECTABLE_EXIT) == 0x2001, (
                f"0x{PROT_AFFECTABLE_EXIT:08X} is not the `movs r0,#1` affectable exit")
            assert _u16(ov, 0x021B07F8) == 0x2800 and _u16(ov, 0x021B07FA) == 0xD000, (
                "the caller no longer tests our return with `cmp r0,#0 ; beq`")
            # --- the acceptance test the stub clones, pinned in its ORIGINAL ----------
            # 0x021AC204 (201 callers) is the template: cid match -> 0x021A32B4 ->
            # bit 26 of [slot+0x44] clear -> the 0x0229C314 per-slot mask clear, over
            # slots 0..4.  If any of it drifts, the clone is no longer faithful.
            assert _bl_target(ov, 0x021AC232) == CID_AT, \
                "0x021AC204 no longer reads the slot cid via 0x021A36EC"
            assert _bl_target(ov, 0x021AC23E) == SLOT_PRESENT, \
                "0x021AC204 no longer tests the slot via 0x021A32B4"
            assert _u16(ov, 0x021AC250) == 0x6C40, "0x021AC204 no longer loads [slot+0x44]"
            assert _u16(ov, 0x021AC252) == 0x0E81, "0x021AC204's bit-26 shift drifted"
            assert _u32(ov, 0x021AC614) == SIDE_STRIDE, "the per-side stride literal moved"
            assert _u32(ov, 0x021AC618) == PLAYER_ARRAY, "the player-array literal moved"
            assert _u32(ov, 0x021AC61C) == GLOBAL_SLOT_MASK, "the per-slot mask literal moved"
            # ...and the bit-18 test that makes 0x021AC5A8 the WRONG primitive, so that a
            # future edit cannot quietly go back to it believing the two are equivalent.
            assert _u16(ov, 0x021AC5F2) == 0x0C81 and _u16(ov, 0x021AC5F8) & 0xFF00 == 0xD000, (
                "0x021AC5A8's extra `lsrs r1,r0,#0x12 ; ... ; beq` bit-18 gate is gone -- "
                "re-check whether it is now a safe 'do you control X' primitive")

            # Nobody else has taken this site (azure_eyes claims 0x021B0592, not this).
            tgt = _bl_target(ov, PROT_HOOK)
            assert tgt in (PROT_NATIVE, ov5_cave.CAVE_WDN_PROT), (
                f"the BL at 0x{PROT_HOOK:08X} targets 0x{tgt:08X}, expected the native "
                f"0x{PROT_NATIVE:08X} -- another patch has claimed this hook site")
            # Azure-Eyes' neighbouring link must be untouched by us.
            assert _bl_target(ov, 0x021B0814) == PROT_NATIVE, (
                "the SECOND S/T link 0x021B0814 no longer calls 0x021A1430")

        def apply_effect(ov: bytearray) -> None:
            """PART C's overlay-3 half: redirect the S/T tail's first link into the cave."""
            _assert_preconditions(ov)

            if _bl_target(bytes(ov), PROT_HOOK) == ov5_cave.CAVE_WDN_PROT:
                print(f"C  hook 0x{PROT_HOOK:08X} already points at the cave (idempotent) -- skipped")
                return

            bl = _thumb_bl(PROT_HOOK, ov5_cave.CAVE_WDN_PROT)
            ov[_off(PROT_HOOK):_off(PROT_HOOK) + 4] = bl
            print(f"C  clause 2: S/T-tail link 0x{PROT_HOOK:08X} -> "
                  f"CAVE_WDN_PROT 0x{ov5_cave.CAVE_WDN_PROT:08X} "
                  f"(protected exit 0x{PROT_PROTECTED_EXIT:08X}; "
                  f"native 0x{PROT_NATIVE:08X} replayed on a miss)")

        def install(rom, view):
            apply_effect(view.buf)

        def check_fn(c, rom, view):
            ov = bytes(view.buf)

            def check(cond, msg):
                c.ok(bool(cond), msg)

            from otn_enhanced.effects import ov5_cave as _o5
            from otn_enhanced.effects.timing_class_hook import _bl as _tbl
            _fronted = code_reaches(rom, PROT_ZONE_SPLIT, _o5.CAVE_IK_PROT)
            check(_u16(ov, PROT_ZONE_SPLIT) == PROT_ZONE_SPLIT_ENC or _fronted,
                  f"C  0x{PROT_ZONE_SPLIT:08X} is still `cmp r5,#4` (the monster / S-T zone split)"
                  + (" -- via infernoble's front (S/T slots return to the native tail)" if _fronted else ""))
            check(_u32(ov, PROT_TAIL_KEY_POOL) == PROT_TAIL_KEY,
                  f"C  the S/T tail's rider key @0x{PROT_TAIL_KEY_POOL:08X} is still "
                  f"0x{PROT_TAIL_KEY:08X}")
            check(_bl_target(ov, PROT_HOOK) == ov5_cave.CAVE_WDN_PROT,
                  f"C  hook 0x{PROT_HOOK:08X} -> CAVE_WDN_PROT 0x{ov5_cave.CAVE_WDN_PROT:08X}")
            check(_u16(ov, 0x021B07F8) == 0x2800 and _u16(ov, 0x021B07FA) == 0xD000,
                  "C  the caller still tests the return with `cmp r0,#0 ; beq` "
                  "(nonzero => PROTECTED)")
            check(_u16(ov, PROT_AFFECTABLE_EXIT) == 0x2001,
                  f"C  the affectable exit 0x{PROT_AFFECTABLE_EXIT:08X} is still `movs r0,#1`")
            check(_bl_target(ov, 0x021B0814) == PROT_NATIVE,
                  "C  the SECOND S/T link 0x021B0814 is untouched (still native 0x021A1430)")
            check(_bl_target(ov, 0x021B0592) != ov5_cave.CAVE_WDN_PROT,
                  "C  azure_eyes' link 0x021B0592 is not pointed at our stub")
            check(_bl_target(ov, 0x021AC232) == CID_AT
                  and _bl_target(ov, 0x021AC23E) == SLOT_PRESENT
                  and _u16(ov, 0x021AC250) == 0x6C40 and _u16(ov, 0x021AC252) == 0x0E81,
                  "C  0x021AC204's acceptance test (the template the stub clones) is unchanged")
            check(_u32(ov, 0x021AC614) == SIDE_STRIDE and _u32(ov, 0x021AC618) == PLAYER_ARRAY
                  and _u32(ov, 0x021AC61C) == GLOBAL_SLOT_MASK,
                  "C  the player-array / stride / per-slot-mask literals are unchanged")
            check(_u16(ov, 0x021AC5F2) == 0x0C81,
                  "C  0x021AC5A8 still carries the bit-18 gate that made it the WRONG primitive")

            # -- PART C: overlay 5 ----------------------------------------------------
            want = build_prot_stub(ov5_cave.CAVE_WDN_PROT)
            live = ov5_cave.read_cave(rom, ov5_cave.CAVE_WDN_PROT, len(want))
            check(live == want,
                  f"C  the protection stub @0x{ov5_cave.CAVE_WDN_PROT:08X} matches "
                  f"({len(want)} B)")

        return Compiled(((ov5_cave.CAVE_WDN_PROT, build_prot_stub(ov5_cave.CAVE_WDN_PROT), "S/T protection leaf"),),
                        installs=(install,), checks=(check_fn,))



NINJA_TABLE = SetCodeTable("Ninja", 0x0209C722, 9, (0x020237E0,), (0x020237DC,))

SPEC = card(
    0x12B2,
    spells_traps_you_control_cannot_be_destroyed_by_card_effects_while_this_monster_is_face_up(),
    archetype_member(NINJA_TABLE, phantom=0x238B))     # Karakuri Ninja "Sazank": stays a Karakuri, loses "Ninja"

PROPS = card_props("LIGHT", "Dragon", level=7, atk=2700, defense=1200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_white_dragon_ninja.nds")

# Names other modules and tests read off this one.
PROT_RESERVE = 0x80


def build_prot_stub(base: int = None) -> bytes:
    from otn_enhanced.effects.common import Ov
    from otn_enhanced.rom.overlay_io import load_overlay3
    _, ovb = load_overlay3(dsl.SRC)
    return SPEC.compile(Ov(bytearray(ovb))).stubs[0][1]


def _ldr_pc(at: int, reg: int, target: int) -> int:
    imm = target - ((at + 4) & ~3)
    assert 0 <= imm <= 0x3FC and imm % 4 == 0, f"ldr [pc,#{imm}] out of range at 0x{at:08X}"
    return 0x4800 | (reg << 8) | (imm // 4)


def _bcond(at: int, target: int, cond: int) -> int:
    off = (target - (at + 4)) // 2
    assert -0x80 <= off < 0x80, "conditional branch out of imm8 range"
    return 0xD000 | (cond << 8) | (off & 0xFF)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

"""Safe Zone (Continuous Trap) on Battle-Scarred 0x16A2.

    Activate this card by targeting 1 face-up Attack Position monster on the field; that face-up monster cannot be
    destroyed by battle or your opponent's card effects, your opponent cannot target it with card effects, also it
    cannot attack your opponent directly. When this card leaves the field, destroy that monster. When that monster
    leaves the field, destroy this card.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class continuous_trap_protect_target_from_battle_destruction_and_opponents_targeting:
    """Safe Zone (Battle-Scarred 0x16A2, a Continuous Trap already): 'Activate by targeting 1 face-up Attack Position monster
    on the field; it cannot be destroyed by battle, your opponent cannot target it with card effects (or attack directly), when
    this leaves the field destroy that monster and vice versa.' ov3 path only (every stub in the ov3 pool): the donor's
    Standby LP drain literal replaced by a phantom, the cls0 filter slot moved to a thin zone-predicate wrapper (mask 0xC94, either
    side, Attack Position) and the three rider-chain links (battle protection, targeting, cannot-attack-directly) detoured to stubs
    that read the Safe Zone controller off the rider node's source locator ("your opponent" = the opponent of Safe Zone's controller).
    Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import thumb_bl
        from otn_enhanced.rom.overlay_io import RAM_BASE
        SAFE_ZONE_CID = cid
        prot, tgt, dirs = cave3.CAVE3_SZ_PROTECT, cave3.CAVE3_SZ_TARGET, cave3.CAVE3_SZ_DIRECT
        assert prot % 4 == tgt % 4 == dirs % 4 == 0, "EffectBuilder stubs need 4-aligned bases"
        FILTER_LEAF = 0x021E08C2        # Battle-Scarred's Archfiend-test leaf (1 inbound branch)
        FILTER_ACCEPT = 0x021E0A80      # the switch's generic accept leaf (`movs r0,#1`)
        FILTER_LEAF_ORIG = bytes.fromhex("281c")        # adds r0, r5, #0

        # --- PART B: the Standby-Phase LP drain ------------------------------------
        LP_POOL = 0x02258A50            # shared literal for both drain sites
        LP_PHANTOM = 0x2617             # absent from the card list; 0 occurrences in ov3

        # --- PART C: clause 2 -------------------------------------------------------
        PROT_LINK = 0x021984EC          # the GB Battle Manica `bl 0x021A0950` in the chain
        NODE_QUERY = 0x021A0950         # family-2 rider query (side, slot, cid) -> count
        STUB_ADDR = ov5_cave.CAVE_SZ_PROTECT
        STUB_RESERVE = 0x30

        # --- PART D: clauses 3 + 4 --------------------------------------------------
        TARGET_LINK = 0x021B05CC        # Heart of Clear Water's own query inside the "targets" block
        TARGET_REJECT = 0x021B0296      # the predicate's "NOT affectable" exit
        HOCW_CID = 0x150A               # Heart of Clear Water (its query is replayed untouched)
        TGT_STUB_ADDR = ov5_cave.CAVE_SZ_TARGET
        TGT_STUB_RESERVE = 0x50

        # --- PART E: clause 5 -------------------------------------------------------
        DIRECT_LINK = 0x021A69CC        # the Genex Ally Axel query in the "cannot attack directly" chain
        DIRECT_DENY = 0x021A6A0E        # `movs r0,#0` = cannot attack directly (the chain's hit target)
        AXEL_CID = 0x223B               # Genex Ally Axel -- its query is replayed untouched
        FAMILY1_QUERY = 0x021A1430      # the chain is family 1 (kind < 6, key@+0 IS a cid)
        DIR_STUB_ADDR = ov5_cave.CAVE_SZ_DIRECT
        DIR_STUB_RESERVE = 0x40

        def _build_stub(addr: int = STUB_ADDR) -> bytes:
            """Query the original granting cid, then OR in the donor's rider."""
            a = EffectBuilder()
            (a
             .insn("PUSH", "{LR}")
             .bl(NODE_QUERY)                    # original: r0/r1/r2 already set by the caller
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "done")               # original matched -> return its count
             .insn("ADD", "R0, R5, #0x0")       # side  (live across the chain)
             .insn("ADD", "R1, R4, #0x0")       # slot
             .ldr_const(2, SAFE_ZONE_CID)
             .bl(NODE_QUERY)
             .label("done")
             .insn("POP", "{PC}"))              # never POP {..,LR} -- Thumb-1 restores PC only
            code = a.assemble(addr)
            assert len(code) <= STUB_RESERVE, f"stub {len(code)}B exceeds reserve 0x{STUB_RESERVE:X}"
            assert_thumb1_only(code, addr)
            return code


        CLS0_BASE, CLS0_COUNT = 0x0227E64C, 0x51A
        FILTER_NATIVE = 0x021E0681          # cls0 +08: Battle-Scarred's own-side selector (shared)
        FILTER_MASK = 0x00000C94            # target-check | monster zone | face-up | ATTACK POSITION | either side
        ZONE_PRED = 0x021D6E40
        ZONE_HEAD, NODE_POOL = 0x0229ACD2, 0x0229D33C   # rider chain head (+ side*0xB3C + slot*0x14), node stride 0xA
        CID_AT = 0x021A36EC                 # (side, slot) -> cid on the field there


        def _filter3(base: int) -> bytes:
            b = EffectBuilder()
            b.insn("PUSH", "{R3, LR}")                    # the native 168-wrapper shape
            b.ldr_const(3, FILTER_MASK)
            b.bl(ZONE_PRED)
            b.insn("POP", "{R3, PC}")
            return b.assemble(base, pad="nop")


        def _szside(base: int) -> bytes:
            """(r0 side, r1 slot) -> the side controlling the first Safe Zone rider on that monster, or -1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("MOV", "R2, #0x1")
            b.insn("AND", "R0, R2")
            b.ldr_const(2, 0xB3C)
            b.insn("MUL", "R2, R0")
            b.insn("MOV", "R3, #0x14")
            b.insn("MUL", "R3, R1")
            b.insn("ADD", "R2, R2, R3")
            b.ldr_const(3, ZONE_HEAD)
            b.insn("ADD", "R2, R2, R3")
            b.insn("LDRH", "R4, [R2, #0x0]")              # node index (0 = end)
            b.label("next")
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "none")
            b.insn("MOV", "R0, #0xA")
            b.insn("MUL", "R0, R4")
            b.ldr_const(5, NODE_POOL)
            b.insn("ADD", "R5, R5, R0")                   # node
            b.insn("LDRH", "R4, [R5, #0x8]")              # next index
            b.insn("LDRH", "R0, [R5, #0x2]")
            b.insn("LSL", "R0, R0, #0x1C")
            b.insn("LSR", "R0, R0, #0x1C")                # kind nibble: family 2 = 6..0xB
            b.insn("CMP", "R0, #0x6")
            b.insn("BLT", "next")
            b.insn("CMP", "R0, #0xB")
            b.insn("BGT", "next")
            b.insn("LDRH", "R6, [R5, #0x0]")              # source locator: side | slot << 8
            b.insn("LSL", "R0, R6, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSR", "R1, R6, #0x8")
            b.bl(CID_AT)
            b.ldr_const(1, SAFE_ZONE_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "next")
            b.insn("LSL", "R0, R6, #0x18")
            b.insn("LSR", "R0, R0, #0x18")                # Safe Zone's controller
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("none")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def _target3(base: int, szside: int) -> bytes:
            """PART D, C3/C4: same contract as _build_target_stub, but 'opponent' = Safe Zone's controller's."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.bl(NODE_QUERY)                              # Heart of Clear Water (r2 already 0x150A)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("ADD", "R0, R6, #0x0")                 # protected monster: side
            b.insn("ADD", "R1, R5, #0x0")                 #                    slot
            b.ldr_const(2, SAFE_ZONE_CID)
            b.bl(NODE_QUERY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "allow")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.bl(szside)                                  # r0 = Safe Zone's controller
            b.insn("LDRB", "R1, [R7, #0x2]")              # acting card's controller
            b.insn("MOV", "R2, #0x1")
            b.insn("AND", "R1, R2")
            b.insn("AND", "R0, R2")
            b.insn("CMP", "R1, R0")
            b.insn("BEQ", "allow")                        # Safe Zone's controller's own effect
            b.insn("POP", "{R1}")                         # drop LR: SP back to the caller's frame
            b.ldr_const(0, TARGET_REJECT | 1)
            b.insn("BX", "R0")                            # -> "NOT affectable"
            b.label("allow")
            b.insn("MOV", "R0, #0x0")
            b.label("done")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def _direct3(base: int, szside: int) -> bytes:
            """PART E, C5: deny the direct attack only for a monster on Safe Zone's controller's side."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.bl(FAMILY1_QUERY)                           # Genex Ally Axel (r2 already 0x223B)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R4, #0x0")
            b.ldr_const(2, SAFE_ZONE_CID)
            b.bl(NODE_QUERY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")                         # no Safe Zone rider -> 0
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R4, #0x0")
            b.bl(szside)
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.insn("ADD", "R2, R5, #0x0")
            b.insn("AND", "R2, R1")
            b.insn("CMP", "R0, R2")
            b.insn("BEQ", "deny")
            b.insn("MOV", "R0, #0x0")                     # the opponent's Safe Zone: may attack directly
            b.insn("B", "done")
            b.label("deny")
            b.insn("MOV", "R0, #0x1")
            b.label("done")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")

        def _cls0_row(ov: bytearray) -> int:
            rows = [CLS0_BASE + i * 24 for i in range(CLS0_COUNT)
                    if struct.unpack_from("<H", ov, CLS0_BASE + i * 24 - RAM_BASE)[0] == SAFE_ZONE_CID]
            assert len(rows) == 1, f"expected 1 cls0 row for 0x{SAFE_ZONE_CID:04X}, found {len(rows)}"
            return rows[0]


        def _filter_patch() -> bytes:
            """`b FILTER_ACCEPT` encoded for FILTER_LEAF (2 bytes)."""
            off = (FILTER_ACCEPT - (FILTER_LEAF + 4)) // 2
            assert -0x400 <= off < 0x400, "accept leaf out of Thumb B range"
            return struct.pack("<H", 0xE000 | (off & 0x7FF))

        x = dict(filter=cave3.CAVE3_SZ_FILTER, side=cave3.CAVE3_SZ_SIDE)
        stubs = (("protect", prot, _build_stub(prot)), ("target", tgt, _target3(tgt, x["side"])),
                 ("direct", dirs, _direct3(dirs, x["side"])), ("filter", x["filter"], _filter3(x["filter"])),
                 ("side", x["side"], _szside(x["side"])))
        stubs = tuple((addr, blob, name) for name, addr, blob in stubs)

        def detour(ov, link, want_target, native_target, label):
            off = link - RAM_BASE
            want = thumb_bl(link, want_target)
            orig = thumb_bl(link, native_target)
            cur = bytes(ov[off:off + 4])
            if cur != want:
                assert cur == orig, f"{label} @0x{link:08X} = {cur.hex()} (expected {orig.hex()}) -- wrong or already-modified ROM?"
                ov[off:off + 4] = want

        def install(rom, view):
            ov = view.buf
            off = FILTER_LEAF - RAM_BASE
            want = _filter_patch()
            cur = bytes(ov[off:off + 2])
            if cur != want:
                assert cur == FILTER_LEAF_ORIG, f"filter leaf @0x{FILTER_LEAF:08X} = {cur.hex()} (expected {FILTER_LEAF_ORIG.hex()})"
                ov[off:off + 2] = want
            off = LP_POOL - RAM_BASE
            cur = struct.unpack_from("<I", ov, off)[0]
            if cur != LP_PHANTOM:
                assert cur == SAFE_ZONE_CID, f"LP literal @0x{LP_POOL:08X} = 0x{cur:08X} (expected 0x{SAFE_ZONE_CID:04X})"
                struct.pack_into("<I", ov, off, LP_PHANTOM)
            detour(ov, PROT_LINK, prot, NODE_QUERY, "protection link")
            detour(ov, TARGET_LINK, tgt, NODE_QUERY, "targeting link")
            detour(ov, DIRECT_LINK, dirs, FAMILY1_QUERY, "direct-attack link")
            row = _cls0_row(ov)
            cur = struct.unpack_from("<I", ov, row + 8 - RAM_BASE)[0]
            if cur != x["filter"] | 1:
                assert cur == FILTER_NATIVE, f"cls0 +08 = 0x{cur:08X}, expected 0x{FILTER_NATIVE:08X}"
                struct.pack_into("<I", ov, row + 8 - RAM_BASE, x["filter"] | 1)

        def check_fn(c, rom, view):
            ov = bytearray(view.buf)
            STUB_ADDR, TGT_STUB_ADDR, DIR_STUB_ADDR = prot, tgt, dirs
            ok = True
            # 1) PART A -- the filter leaf jumps to the generic accept leaf.
            off = FILTER_LEAF - RAM_BASE
            want = _filter_patch()
            if bytes(ov[off:off + 2]) == want:
                print(f"PASS PART A filter leaf @0x{FILTER_LEAF:08X} -> b 0x{FILTER_ACCEPT:08X}")
            else:
                print(f"FAIL PART A filter leaf @0x{FILTER_LEAF:08X} = "
                      f"{bytes(ov[off:off+2]).hex()} (expected {want.hex()})"); ok = False

            # 2) PART B -- the LP literal is the phantom, so the drain can never match.
            cur = struct.unpack_from("<I", ov, LP_POOL - RAM_BASE)[0]
            if cur == LP_PHANTOM:
                print(f"PASS PART B LP literal @0x{LP_POOL:08X} = phantom 0x{LP_PHANTOM:04X}")
            else:
                print(f"FAIL PART B LP literal @0x{LP_POOL:08X} = 0x{cur:08X}"); ok = False

            # 3) PART C -- the chain link is detoured to the stub.
            off = PROT_LINK - RAM_BASE
            want = thumb_bl(PROT_LINK, STUB_ADDR)
            if bytes(ov[off:off + 4]) == want:
                print(f"PASS PART C protection link @0x{PROT_LINK:08X} -> bl 0x{STUB_ADDR:08X}")
            else:
                print(f"FAIL PART C protection link @0x{PROT_LINK:08X} = "
                      f"{bytes(ov[off:off+4]).hex()} (expected {want.hex()})"); ok = False

            # 4) The rest of the protection chain is untouched (no collateral damage).
            for site, cid in ((0x02198490, None), (0x021984A2, 0x17FF), (0x021984B6, None),
                              (0x021984C8, 0x1992), (0x021984DC, None), (0x02198502, 0x21D6)):
                off = site - RAM_BASE
                # infernoble (Maugis C1) fronts Mist Body's link with ov5 CAVE_IK_M_BATTLE, which calls
                # the native query FIRST and only adds an "equipped with 0x139A" OR (byte-checked by infernoble.verify).
                from otn_enhanced.effects import ov5_cave as _o5
                if bytes(ov[off:off + 4]) == thumb_bl(site, NODE_QUERY):
                    print(f"PASS chain link @0x{site:08X} still -> bl 0x{NODE_QUERY:08X}")
                elif site == 0x021984C8 and bytes(ov[off:off + 4]) == thumb_bl(site, _o5.CAVE_IK_M_BATTLE):
                    print(f"PASS chain link @0x{site:08X} -> infernoble's Maugis front (native query first)")
                else:
                    print(f"FAIL chain link @0x{site:08X} was disturbed"); ok = False

            # 5) PART D -- the targeting link reaches its stub (march's front sits AHEAD of it and tails here).
            from otn_enhanced.effects.common import code_reaches
            off = TARGET_LINK - RAM_BASE
            if code_reaches(rom, TARGET_LINK, TGT_STUB_ADDR):
                print(f"PASS PART D targeting link @0x{TARGET_LINK:08X} reaches 0x{TGT_STUB_ADDR:08X}")
            else:
                print(f"FAIL PART D targeting link @0x{TARGET_LINK:08X} = "
                      f"{bytes(ov[off:off+4]).hex()} does not reach 0x{TGT_STUB_ADDR:08X}"); ok = False

            # 6) The reject exit PART D jumps into is still the instruction we think it is.
            if bytes(ov[TARGET_REJECT - RAM_BASE:TARGET_REJECT - RAM_BASE + 2]) == bytes.fromhex("1698"):
                print(f"PASS PART D reject exit @0x{TARGET_REJECT:08X} intact (ldr r0,[sp,#0x58])")
            else:
                print(f"FAIL PART D reject exit @0x{TARGET_REJECT:08X} drifted"); ok = False

            # 7) PART E -- the direct-attack link is detoured, and its deny exit is intact.
            off = DIRECT_LINK - RAM_BASE
            want = thumb_bl(DIRECT_LINK, DIR_STUB_ADDR)
            if bytes(ov[off:off + 4]) == want:
                print(f"PASS PART E direct-attack link @0x{DIRECT_LINK:08X} -> bl 0x{DIR_STUB_ADDR:08X}")
            else:
                print(f"FAIL PART E direct-attack link @0x{DIRECT_LINK:08X} = "
                      f"{bytes(ov[off:off+4]).hex()} (expected {want.hex()})"); ok = False
            if bytes(ov[DIRECT_DENY - RAM_BASE:DIRECT_DENY - RAM_BASE + 2]) == bytes.fromhex("0020"):
                print(f"PASS PART E deny exit @0x{DIRECT_DENY:08X} intact (movs r0,#0)")
            else:
                print(f"FAIL PART E deny exit @0x{DIRECT_DENY:08X} drifted"); ok = False
            p8 = struct.unpack_from("<I", ov, _cls0_row(ov) + 8 - RAM_BASE)[0]
            ok &= p8 == x["filter"] | 1
            c.ok(ok, "Safe Zone: filter leaf, LP drain, the three detoured links, deny/reject exits and the cls0 filter slot")

        return Compiled(stubs, installs=(install,), checks=(check_fn,))



SPEC = card(0x16A2, continuous_trap_protect_target_from_battle_destruction_and_opponents_targeting())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_safe_zone.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

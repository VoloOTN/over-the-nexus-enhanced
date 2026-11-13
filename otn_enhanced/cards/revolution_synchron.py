"""Revolution Synchron (EARTH / Machine / Tuner / Level 3 / 900 / 1400) on Acrobat Monkey 0x1649.

    If you Synchro Summon a "Power Tool" monster or a Level 7 or 8 Dragon monster, this card in your hand can also be
    used as material. You can only use this effect of "Revolution Synchron" once per turn.
    If you control a Level 7 or higher Synchro Monster while this card is in your GY: You can send the top card of your
    Deck to the GY, and if you do, Special Summon this card, also its Level becomes 1. You can only use this effect of
    "Revolution Synchron" once per Duel.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.cards.unknown_synchron import SYNCHRON_TABLE
from otn_enhanced.dsl import archetype_member, card, card_props, CLS2, Compiled, Row
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import thumb_bl
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.effects.common import Table
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


IGNITION_REGISTRY = Table(0x0226FAFC, 0x92, 12, "<HHII", label="ignition registry row")


def revolution_synchron_stubs(cid: int, slots: dict) -> list:
    """-> [(name, addr, blob)] for every Revolution Synchron stub. Pure function of the cid and the ov5 slot addresses, so the card
    module can re-export them (`_stubs()`) for the KB proof that pins the hook sites."""
    PLAYER, STRIDE, INSTANCES, SYN_STATE = 0x0229AC94, 0xB3C, 0x0229C33C, 0x0229ABFC
    HANDMODE, VALIDATOR, ACCEPT_TAIL, INNER, LEVEL, RACE = 0x022494EC, 0x02249AFC, 0x02249DA0, 0x0224829C, 0x0202ABD8, 0x0202ABB8
    TLQ, TLP, KIND_C1, KIND_C2 = 0x021A14E8, 0x021D2584, 1, 5
    POWER_TOOL, DENY = 0x1FC9, (0x21CD, 0x2180, 0x221B, 0x219C, 0x2271)
    SEND_HAND_TO_GY = 0x021C6E74
    GYREG_BASE, ENUM_LOOP_HEAD, ENUM_POST_EXIT, GY_POST = 0x0228DDF8, 0x0224C88E, 0x0229DD14, 0x0224C6C1
    ZONE_CID, IS_SYNCHRO, LIVE_LEVEL, COST_SETTLED, DECK_TOP_COST, BULB_F1 = 0x021A3320, 0x02023050, 0x021B807C, 0x021D2BC8, 0x021EBA34, 0x021F7B74
    PHASE_STATE, CHAIN_PUSH, CHAIN_POP, GY_SELF_SS, LOCATE, RIDER_WRITE, LEVEL_SET_KEY = 0x0229AAFC, 0x021D28A4, 0x021D2964, 0x0220731C, 0x021A241C, 0x021C479C, 0x1EC1

    def hand_cid(a, side, idx):
        return (a.insn("LSL", f"R0, {idx}, #2").ldr_const(1, STRIDE).insn("MUL", f"R1, {side}").ldr_const(2, PLAYER + 0x124)
                .insn("ADD", "R1, R1, R2").insn("LDR", "R0, [R1, R0]").insn("LSL", "R1, R0, #17").insn("LSR", "R1, R1, #31")
                .insn("LSL", "R0, R0, #1").insn("LSR", "R0, R0, #24").insn("LSL", "R0, R0, #1").insn("ADD", "R0, R0, R1")
                .insn("LSL", "R0, R0, #3").ldr_const(1, INSTANCES).insn("LDR", "R0, [R1, R0]").insn("LSL", "R0, R0, #18")
                .insn("LSR", "R0, R0, #18"))

    out = []
    a = EffectBuilder()          # H1: BL'd from the validator: r5 = side, r6 = kind, [sp] = idx
    (a.insn("CMP", "R6, #0xB").insn("BNE", "orig").ldr_const(0, SYN_STATE).insn("LDR", "R1, [R0, #0x7C]").insn("CMP", "R1, #0x0")
     .insn("BNE", "orig").insn("LDR", "R1, [R0, #0x6C]").insn("MOV", "R2, #0x1").insn("AND", "R1, R2").insn("CMP", "R1, R5")
     .insn("BNE", "orig").insn("PUSH", "{R4, LR}").insn("LDR", "R3, [SP, #0x8]").insn("ADD", "R4, R5, #0x0"))
    hand_cid(a, "R4", "R3")
    (a.ldr_const(1, cid).insn("CMP", "R0, R1").insn("BNE", "no").insn("ADD", "R0, R5, #0x0").insn("MOV", "R1, #0xB")
     .ldr_const(2, cid).insn("MOV", f"R3, #0x{KIND_C1:X}").bl(TLQ).insn("CMP", "R0, #0x0").insn("BNE", "no")
     .ldr_const(0, SYN_STATE).insn("LDR", "R4, [R0, #0x68]").ldr_const(0, POWER_TOOL).insn("CMP", "R4, R0").insn("BEQ", "inner"))
    for c_ in DENY:
        a.ldr_const(0, c_).insn("CMP", "R4, R0").insn("BEQ", "no")
    (a.insn("ADD", "R0, R4, #0x0").bl(RACE).insn("CMP", "R0, #0x1").insn("BNE", "no").insn("ADD", "R0, R4, #0x0").bl(LEVEL)
     .insn("SUB", "R0, #0x7").insn("CMP", "R0, #0x1").insn("BHI", "no").label("inner").insn("ADD", "R0, R4, #0x0")
     .insn("ADD", "R1, R5, #0x0").insn("MOV", "R2, #0xB").insn("LDR", "R3, [SP, #0x8]").bl(INNER).insn("CMP", "R0, #0x0")
     .insn("BEQ", "no").insn("POP", "{R4}").insn("POP", "{R3}").ldr_const(3, ACCEPT_TAIL | 1).insn("BX", "R3")
     .label("no").insn("POP", "{R4}").insn("POP", "{R3}").insn("MOV", "LR, R3").label("orig").ldr_const(3, HANDMODE | 1)
     .insn("BX", "R3"))
    out.append(("valid", slots["valid"], a.assemble(slots["valid"])))

    a = EffectBuilder()          # H2: BL'd from can_synchro over `ldr r0,[sp,#4] ; cmp r0,#0`: r6 = any field material found
    (a.insn("PUSH", "{R4, R5, R7, LR}").insn("CMP", "R6, #0x0").insn("BNE", "done").ldr_const(0, SYN_STATE).insn("LDR", "R5, [R0, #0x6C]")
     .insn("MOV", "R0, #0x1").insn("AND", "R5, R0").ldr_const(0, STRIDE).insn("MUL", "R0, R5").ldr_const(1, PLAYER)
     .insn("ADD", "R0, R0, R1").insn("LDR", "R7, [R0, #0xC]").insn("MOV", "R4, #0x0").insn("B", "test").label("loop")
     .insn("ADD", "R0, R5, #0x0").insn("MOV", "R1, #0xB").insn("ADD", "R2, R4, #0x0").bl(VALIDATOR).insn("CMP", "R0, #0x0")
     .insn("BEQ", "next").insn("MOV", "R6, #0x1").insn("B", "done").label("next").insn("ADD", "R4, #0x1").label("test")
     .insn("CMP", "R4, R7").insn("BLT", "loop").label("done").insn("LDR", "R0, [SP, #0x14]").insn("POP", "{R4, R5, R7}")
     .insn("POP", "{R3}").insn("CMP", "R0, #0x0").insn("BX", "R3"))
    out.append(("handpass", slots["handpass"], a.assemble(slots["handpass"])))

    a = EffectBuilder()          # H3: replaces `bl 0x021C6E74` (r0 = side, r1 = hand idx)
    (a.insn("PUSH", "{R0, R1, R4, LR}").insn("ADD", "R4, R0, #0x0").insn("ADD", "R0, R1, #0x0").insn("MOV", "R1, #0x1").insn("AND", "R4, R1"))
    hand_cid(a, "R4", "R0")
    (a.ldr_const(1, cid).insn("CMP", "R0, R1").insn("BNE", "go").insn("LDR", "R0, [SP, #0x0]").ldr_const(1, cid)
     .insn("MOV", f"R2, #0x{KIND_C1:X}").insn("MOV", "R3, #0x0").bl(TLP).label("go").insn("POP", "{R0, R1, R4}").insn("POP", "{R3}")
     .insn("MOV", "LR, R3").ldr_const(3, SEND_HAND_TO_GY | 1).insn("BX", "R3"))
    out.append(("stamp", slots["stamp"], a.assemble(slots["stamp"])))

    a = EffectBuilder()          # H4: replaces `ldr r1,=base ; lsls r0,r6,#4`; row 60 is the virtual row
    (a.ldr_const(1, GYREG_BASE).insn("LSL", "R0, R6, #4").insn("CMP", "R6, #0x3C").insn("BNE", "out")
     .ldr_const(0, slots["vrow"] - GYREG_BASE).label("out").insn("BX", "LR"))
    out.append(("gyfetch", slots["gyfetch"], a.assemble(slots["gyfetch"])))
    a = EffectBuilder()          # H5: the enumerator's loop exit: one extra pass for row 60
    (a.insn("CMP", "R6, #0x3C").insn("BNE", "rest").ldr_const(0, ENUM_LOOP_HEAD | 1).insn("BX", "R0").label("rest")
     .insn("MOV", "R6, #0x3C").ldr_const(0, ENUM_POST_EXIT).insn("LDR", "R1, [R0, #0x34]").insn("BX", "LR"))
    out.append(("gyexit", slots["gyexit"], a.assemble(slots["gyexit"])))
    a = EffectBuilder()          # H6: post-by-cid exit: r4 = rows walked, r5 = cid, r6/r7 = the post's r0/r2
    (a.insn("CMP", "R4, #0x3C").insn("BCC", "out").ldr_const(0, cid).insn("CMP", "R5, R0").insn("BNE", "out")
     .insn("ADD", "R0, R6, #0x0").insn("ADD", "R1, R5, #0x0").insn("ADD", "R2, R7, #0x0").bl(GY_POST & ~1)
     .label("out").insn("POP", "{R3, R4, R5, R6, R7, PC}"))
    out.append(("gypost", slots["gypost"], a.assemble(slots["gypost"])))
    a = EffectBuilder()          # H7: has-row not-found exit: r0 still holds the queried cid
    (a.ldr_const(1, cid).insn("CMP", "R0, R1").insn("BEQ", "yes").insn("MOV", "R0, #0x0").insn("POP", "{R3, R4, R5, PC}")
     .label("yes").insn("MOV", "R0, #0x1").insn("POP", "{R3, R4, R5, PC}"))
    out.append(("gyhas", slots["gyhas"], a.assemble(slots["gyhas"])))

    a = EffectBuilder()          # ignition-registry f1(desc, arg): a face-up Lv7+ Synchro in your monster zones, then Bulb's f1
    (a.insn("PUSH", "{R4, R5, R6, R7, LR}").insn("SUB", "SP, #0x4").insn("STR", "R1, [SP, #0x0]").insn("ADD", "R4, R0, #0x0")
     .insn("LDRB", "R5, [R4, #0x2]").insn("LDRB", "R0, [R4, #0x6]").insn("EOR", "R5, R0").insn("MOV", "R0, #0x1").insn("AND", "R5, R0")
     .insn("MOV", "R6, #0x0").label("loop").insn("ADD", "R0, R5, #0x0").insn("ADD", "R1, R6, #0x0").bl(ZONE_CID)
     .insn("CMP", "R0, #0x0").insn("BEQ", "next").insn("ADD", "R7, R0, #0x0").ldr_const(0, STRIDE).insn("MUL", "R0, R5")
     .ldr_const(1, PLAYER).insn("ADD", "R0, R0, R1").insn("MOV", "R1, #0x14").insn("MUL", "R1, R6").insn("ADD", "R2, R0, R1")
     .insn("LDR", "R1, [R2, #0x44]").insn("MOV", "R3, #0x2").insn("TST", "R1, R3").insn("BNE", "next").insn("LSR", "R1, R1, #21")
     .insn("MOV", "R3, #0x1").insn("TST", "R1, R3").insn("BNE", "next").insn("LDRH", "R1, [R2, #0x3C]").insn("CMP", "R1, #0x0")
     .insn("BEQ", "next").insn("ADD", "R0, R7, #0x0").bl(IS_SYNCHRO).insn("CMP", "R0, #0x0").insn("BEQ", "next")
     .insn("ADD", "R0, R5, #0x0").insn("ADD", "R1, R6, #0x0").insn("MOV", "R2, #0x0").bl(LIVE_LEVEL).insn("CMP", "R0, #0x7")
     .insn("BLT", "next").insn("ADD", "R0, R4, #0x0").insn("LDR", "R1, [SP, #0x0]").bl(BULB_F1).insn("B", "out")
     .label("next").insn("ADD", "R6, #0x1").insn("CMP", "R6, #0x5").insn("BLT", "loop").insn("MOV", "R0, #0x0")
     .label("out").insn("ADD", "SP, #0x4").insn("POP", "{R4, R5, R6, R7, PC}"))
    out.append(("c2cond", slots["c2cond"], a.assemble(slots["c2cond"])))
    a = EffectBuilder()          # cls2 +10(desc): stamp once per Duel only when the Deck-top cost is actually paid
    (a.insn("PUSH", "{R4, LR}").insn("ADD", "R4, R0, #0x0").bl(COST_SETTLED).insn("CMP", "R0, #0x0").insn("BNE", "settled")
     .insn("LDRB", "R0, [R4, #0x2]").ldr_const(1, cid).insn("MOV", f"R2, #0x{KIND_C2:X}").insn("MOV", "R3, #0x0").bl(TLP)
     .insn("ADD", "R0, R4, #0x0").bl(DECK_TOP_COST).insn("POP", "{R4, PC}").label("settled").insn("MOV", "R0, #0x1").insn("POP", "{R4, PC}"))
    out.append(("c2cost", slots["c2cost"], a.assemble(slots["c2cost"])))
    a = EffectBuilder()          # cls2 +04(desc, arg): psi_reflector's phases around the GY self-SS
    (a.insn("PUSH", "{R2, R3, R4, R5, R6, R7, LR}").insn("ADD", "R4, R0, #0x0").insn("ADD", "R5, R1, #0x0").ldr_const(0, PHASE_STATE)
     .insn("LDR", "R0, [R0, #0x70]").insn("CMP", "R0, #0x80").insn("BEQ", "p80").insn("CMP", "R0, #0x7F").insn("BEQ", "p7f")
     .insn("CMP", "R0, #0x64").insn("BEQ", "p64").insn("B", "zero").label("p80").bl(CHAIN_PUSH).insn("ADD", "R0, R4, #0x0")
     .insn("ADD", "R1, R5, #0x0").bl(GY_SELF_SS).insn("MOV", "R0, #0x7F").insn("B", "out").label("p7f")
     .insn("LDRH", "R0, [R4, #0xC]").bl(LOCATE).insn("LSL", "R1, R0, #16").insn("LSR", "R1, R1, #24").insn("CMP", "R1, #0x5")
     .insn("BGE", "done").insn("LSL", "R0, R0, #24").insn("LSR", "R0, R0, #24").insn("MOV", "R2, #0x1").insn("STR", "R2, [SP, #0x0]")
     .ldr_const(2, LEVEL_SET_KEY).insn("MOV", "R3, #0x3").bl(RIDER_WRITE).label("done").insn("MOV", "R0, #0x64").insn("B", "out")
     .label("p64").bl(CHAIN_POP).label("zero").insn("MOV", "R0, #0x0").label("out").insn("POP", "{R2, R3, R4, R5, R6, R7, PC}"))
    out.append(("c2res", slots["c2res"], a.assemble(slots["c2res"])))
    for _n, addr, blob in out:
        assert_thumb1_only(blob, addr)
    return out


@dataclass(frozen=True)
class hand_synchro_material_and_graveyard_self_summon_through_virtual_row:
    """Revolution Synchron.
      C1 'If you Synchro Summon a "Power Tool" monster or a Level 7 or 8 Dragon monster, this card in your hand can also be used as
         material. Once per turn.' rides the engine's NATIVE hand-material path (Eccentric Boy / Malefic Parallel Gear, gate
         0x022494EC): three ov5 hooks add the donor as the FIRST pick (the Tuner): H1 0x02249B12 the validator's hand-mode test; H2
         0x02249626 the can_synchro field-loop exit (Extra Deck command when the donor in hand is the only Tuner); H3 0x022639AA the
         hand-material send (once-per-turn stamp, turn-log kind 1). The hand Tuner skips OUTER 0x022485B4 (field-only), so five targets
         whose OUTER Tuner rule an EARTH Machine fails natively are denied (user decision); INNER 0x0224829C (hand-aware) still runs.
      C2 'If you control a Level 7 or higher Synchro Monster while this card is in your GY: You can send the top card of your Deck to
         the GY, and if you do, Special Summon this card, also its Level becomes 1. Once per Duel.' (the send is a COST, empty Deck ->
         cannot activate): Glow-Up Bulb's chassis on cls2 + an ignition-registry row, and a VIRTUAL GY-action row (row 60 lives in the
         ov5 table, made visible by H4/H5 on the enumerator, H6 post-by-cid, H7 has-row) -- no real row is spent.
         NORMAL-DUEL-ONLY: H4-H7 run on every GY action scan, so a puzzle (ov5 evicted) crashes there."""
    slots: dict                 # valid, handpass, stamp, gyfetch, gyexit, gypost, gyhas, vrow, c2cond, c2cost, c2res
    cls2_phantom: int
    ign_phantom: int

    def compile(self, view, cid) -> Compiled:
        s = self.slots
        stubs = revolution_synchron_stubs(cid, s)
        by = {n: (a, b) for n, a, b in stubs}
        hooks = (("valid", 0x02249B12, common_bl(0x02249B12, 0x022494EC)), ("handpass", 0x02249626, bytes.fromhex("01980028")),
                 ("stamp", 0x022639AA, common_bl(0x022639AA, 0x021C6E74)), ("gyfetch", 0x0224C88E, bytes.fromhex("a6493001")),
                 ("gyexit", 0x0224C9A0, bytes.fromhex("6348416b")), ("gypost", 0x0224CD34, bytes.fromhex("f8bdc046")),
                 ("gyhas", 0x0224CD60, bytes.fromhex("002038bd")))
        GYREG_ROW = (cid, 0x0E, 0x0224C591, 0x0224C6C1)
        ZONE = IGN_DISPATCH = 0x021F0BDD
        ign_row = (cid, 0, s["c2cond"] | 1, 0x021F44D9)
        cls2_slots = (s["c2res"] | 1, 0, IGN_DISPATCH, s["c2cost"] | 1, 0)
        stub_list = [(a, b, n) for n, a, b in stubs] + [(s["vrow"], struct.pack("<4I", *GYREG_ROW), "virtual GY-action row")]

        def install(rom, view):
            for name, site, stock in hooks:
                hook = common_bl(site, s[name])
                cur = view.blob(site, 4)
                assert cur in (stock, hook), f"{site:#010x} = {cur.hex()} -- someone else hooked it"
                view.write(site, hook)

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            # dragon_rulers takes over the four GY-action sites with N-row stubs whose table keeps OUR row as row 60 (first) and
            # compares our cid LAST (gy_vrow_hook): accept that, but only while the composed table still starts with our row.
            dr_gy = {0x0224C88E: ov5_cave.CAVE_RUL_GYFETCH, 0x0224C9A0: ov5_cave.CAVE_RUL_GYEXIT,
                     0x0224CD34: ov5_cave.CAVE_RUL_GYPOST, 0x0224CD60: ov5_cave.CAVE_RUL_GYHAS}
            try:
                dr_row60 = struct.unpack("<4I", ov5_cave.read_cave(rom, ov5_cave.CAVE_RUL_GYROWS, 16)) == GYREG_ROW
            except (AssertionError, IndexError, ValueError):
                dr_row60 = False
            from otn_enhanced.effects import gy_vrow_hook as _gyv
            for name, site, _stock in hooks:
                composed = site in dr_gy and dr_row60 and (view.blob(site, 4) == common_bl(site, dr_gy[site])
                                                           or (_gyv.installed(rom, view.buf) and _gyv.rows(rom)[0] == GYREG_ROW))
                c.ok(view.blob(site, 4) == common_bl(site, s[name]) or composed,
                     f"{site:#010x} = BL {s[name]:#010x}" + (" (via dragon_rulers' N-row stub)" if composed else ""))
            bl_targets = lambda n: [i.branch_target for i in decode_thumb(by[n][1], by[n][0], overlay_data=bytes(view.buf), ram_base=view.base)
                                    if i.mnemonic == "BL"]
            c.eq(bl_targets("valid"), [0x021A14E8, 0x0202ABB8, 0x0202ABD8, 0x0224829C], "H1 BLs: turn-log query, race, level, INNER")
            c.eq(bl_targets("handpass"), [0x02249AFC], "H2 BL: validator")
            c.eq(bl_targets("stamp"), [0x021D2585 & ~1], "H3 BL: turn-log post")
            c.eq(bl_targets("gypost"), [0x0224C6C0], "H6 BL: GY post")
            c.eq(bl_targets("c2cond"), [0x021A3320, 0x02023050, 0x021B807C, 0x021F7B74], "condition BLs: zone cid, is_synchro, live level, Bulb f1")
            c.eq(bl_targets("c2cost"), [0x021D2BC8, 0x021D2584, 0x021EBA34], "cost BLs: settled, turn-log post, Deck-top cost")
            c.eq(bl_targets("c2res"), [0x021D28A4, 0x0220731C, 0x021A241C, 0x021C479C, 0x021D2964], "resolver BLs: chain push, GY self-SS, locate, rider, chain pop")
            c.ok(all(view.u8(x) == 0x3C for x in (0x0224C99A, 0x0224CD30, 0x0224CD5C)), "GY-action count sites still cmp #0x3C (lightpulsar asserts them)")
            c.ok(GYREG_ROW not in [tuple(view.unpack(0x0228DDF8 + i * 16, "<4I")) for i in range(60)], "no real GY-action row spent (the row is virtual)")

        return Compiled(tuple(stub_list),
                        (Row(CLS2, (cid, 0) + cls2_slots, self.cls2_phantom), Row(IGNITION_REGISTRY, ign_row, self.ign_phantom)),
                        installs=(install,), checks=(check,))



DONOR_CID = 0x1649
SYNCHRON_DROP_CID = 0x2414      # Bri Synchron -- user decision: dropped to make room in the full "Synchron" list
DENY = (0x21CD, 0x2180, 0x221B, 0x219C, 0x2271)

SLOTS = dict(valid=ov5_cave.CAVE_REVSYN_VALID, handpass=ov5_cave.CAVE_REVSYN_HANDPASS, stamp=ov5_cave.CAVE_REVSYN_STAMP,
             gyfetch=ov5_cave.CAVE_REVSYN_GYFETCH, gyexit=ov5_cave.CAVE_REVSYN_GYEXIT, gypost=ov5_cave.CAVE_REVSYN_GYPOST,
             gyhas=ov5_cave.CAVE_REVSYN_GYHAS, vrow=ov5_cave.CAVE_REVSYN_VROW, c2cond=ov5_cave.CAVE_REVSYN_C2COND,
             c2cost=ov5_cave.CAVE_REVSYN_C2COST, c2res=ov5_cave.CAVE_REVSYN_C2RES)

SPEC = card(
    DONOR_CID,
    hand_synchro_material_and_graveyard_self_summon_through_virtual_row(slots=SLOTS, cls2_phantom=0x164F, ign_phantom=0x1748),
    archetype_member(SYNCHRON_TABLE, phantom=SYNCHRON_DROP_CID))

PROPS = card_props("EARTH", "Machine", level=3, atk=900, defense=1400, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_revolution_synchron.nds")

# -- names dragon_rulers, gy_vrow_hook and a KB proof read from this module ---------------------------------------
GYREG_BASE = 0x0228DDF8
GYREG_ROW = (DONOR_CID, 0x0E, 0x0224C591, 0x0224C6C1)
ENUM_LOOP_HEAD, ENUM_POST_EXIT, GY_POST = 0x0224C88E, 0x0229DD14, 0x0224C6C1
H1_SITE, H2_SITE, H3_SITE = 0x02249B12, 0x02249626, 0x022639AA
H4_SITE, H5_SITE, H6_SITE, H7_SITE = 0x0224C88E, 0x0224C9A0, 0x0224CD34, 0x0224CD60
H1_ADDR, H2_ADDR, H3_ADDR = SLOTS["valid"], SLOTS["handpass"], SLOTS["stamp"]
H4_ADDR, H5_ADDR, H6_ADDR, H7_ADDR = SLOTS["gyfetch"], SLOTS["gyexit"], SLOTS["gypost"], SLOTS["gyhas"]
H4_STOCK, H5_STOCK = bytes.fromhex("a6493001"), bytes.fromhex("6348416b")
H6_STOCK, H7_STOCK = bytes.fromhex("f8bdc046"), bytes.fromhex("002038bd")
VROW_ADDR = SLOTS["vrow"]
_RESERVES = dict(valid=0x100, handpass=0x60, stamp=0x60, gyfetch=0x20, gyexit=0x30, gypost=0x30, gyhas=0x20)
_SITES = dict(valid=(H1_SITE, thumb_bl(H1_SITE, 0x022494EC)), handpass=(H2_SITE, bytes.fromhex("01980028")),
              stamp=(H3_SITE, thumb_bl(H3_SITE, 0x021C6E74)), gyfetch=(H4_SITE, H4_STOCK), gyexit=(H5_SITE, H5_STOCK),
              gypost=(H6_SITE, H6_STOCK), gyhas=(H7_SITE, H7_STOCK))


def _stubs() -> list:
    """(site, addr, reserve, stock site bytes, blob) -- the hooked stubs (the KB proof pins them)."""
    by = {n: (a, b) for n, a, b in revolution_synchron_stubs(DONOR_CID, SLOTS)}
    return [(_SITES[n][0], by[n][0], _RESERVES[n], _SITES[n][1], by[n][1]) for n in _SITES]


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

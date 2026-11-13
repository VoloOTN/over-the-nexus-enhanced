"""Unknown Synchron (DARK / Machine / Tuner / Level 1 / 0 / 0) on Woodborg Inpachi 0x181C.

    If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand).
    You can only Special Summon this card once per Duel this way.
"""
import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, Compiled
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


@dataclass(frozen=True)
class special_summon_self_from_hand_once_per_duel_if_only_opponent_controls_monster:
    """'If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand). You
    can only Special Summon this card once per Duel this way.' The OFFER is the shared hand-SS trampoline; the condition stub
    (ov3 pool) = turn-log (side, 0x0B, cid, kind 5 = per Duel, never swept) clear && canSS(side) && monster_count(side) == 0 &&
    monster_count(1 - side) != 0. The stamp is the shared SS-commit hook row (cid, kind 5, no damage), which posts the per-Duel
    node only when THIS card is summoned FROM THE HAND (descriptor +0x0E == cid and +0x0A == 0x0B), so a later revival from the
    GY (zone 0x0E) does not consume it."""
    slot: int

    def compile(self, view, cid) -> Compiled:
        CANSS, MONSTER_COUNT, TLQ, KIND, FAMILY = 0x021AD870, 0x021ACF68, 0x021A14E8, 5, 0x0B
        a = EffectBuilder()
        a.prologue(save=[R4])
        a.insn("ADD", "R4, R0, #0x0")
        a.insn("MOV", f"R1, #0x{FAMILY:X}")
        a.ldr_const(2, cid)
        a.insn("MOV", f"R3, #0x{KIND:X}")
        a.call_addr(TLQ)
        a.if_ne(R0, 0, "no")
        a.insn("ADD", "R0, R4, #0x0")
        a.call_addr(CANSS)
        a.if_eq(R0, 0, "no")
        a.insn("ADD", "R0, R4, #0x0")
        a.call_addr(MONSTER_COUNT)
        a.if_ne(R0, 0, "no")
        a.insn("MOV", "R0, #0x1")
        a.insn("SUB", "R0, R0, R4")
        a.call_addr(MONSTER_COUNT)
        a.if_eq(R0, 0, "no")
        a.epilogue(1)
        a.label("no")
        a.epilogue(0)
        code = a.assemble(self.slot)
        assert len(code) <= 0x50
        assert_thumb1_only(code, self.slot)

        def install(rom, view):
            from otn_enhanced.effects import ss_commit_hook, tg_table
            tg_table.register_tg_handss(rom, view.buf, cid, self.slot)
            ss_commit_hook.register(rom, view.buf, cid, KIND, 0, ov3=True)

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            from otn_enhanced.effects import ss_commit_hook, tg_table
            c.ok(tg_table.tg_handss_ok(rom, view.buf, cid), "shared hand-SS hook installed, cid registered")
            c.eq(tg_table.handss_cond_ptr(rom, view.buf, cid), self.slot, "hand-SS table cond ptr = the stub")
            c.ok(ss_commit_hook.ok(rom, view.buf, cid, KIND, 0), f"shared SS-commit hook over both sites, row ({cid:#06x}, kind {KIND}, no damage)")
            fins = decode_thumb(code, self.slot, overlay_data=bytes(view.buf), ram_base=view.base)
            c.eq([i.branch_target for i in fins if i.mnemonic == "BL"].count(TLQ), 1, "condition stub BLs the turn-log query exactly once")

        return Compiled(((self.slot, code, "hand-SS condition"),), installs=(install,), checks=(check,))



DONOR_CID = 0x181C
SYNCHRON_PHANTOM = 0x2501    # a Konami-reserved "Synchron" id, phantom here -- dropped for the donor

# "Synchron" set code 0x4C list: other Synchron cards (accel_synchron) read these.
SYNCHRON_TBL = 0x0209C968
SYNCHRON_COUNT = 15
SYNCHRON_COUNT_IMM = 0x02023E20
SYNCHRON_POOL_PTR = 0x02023E24
SYNCHRON_TABLE = SetCodeTable("Synchron", SYNCHRON_TBL, SYNCHRON_COUNT, (SYNCHRON_POOL_PTR,), (SYNCHRON_COUNT_IMM,))

SPEC = card(
    DONOR_CID,
    special_summon_self_from_hand_once_per_duel_if_only_opponent_controls_monster(cave3.CAVE3_UNKSYN_SSCOND),
    archetype_member(SYNCHRON_TABLE, phantom=SYNCHRON_PHANTOM))

PROPS = card_props("DARK", "Machine", level=1, atk=0, defense=0, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_unknown_synchron.nds")


def add_synchron_member(out_path: str, insert_cid: int, phantom_cid: int) -> None:
    """Register *insert_cid* as a "Synchron" member IN PLACE over *phantom_cid* (accel_synchron / revolution_synchron call this)."""
    archetype_member(SYNCHRON_TABLE, phantom=phantom_cid).compile(None, insert_cid).posts[0](out_path)


def _bl_targets(blob: bytes, base: int) -> list[int]:   # revolution_synchron.verify reads this
    """Every ARMv4T two-halfword BL target inside *blob* (assembled at *base*)."""
    out = []
    for off in range(0, len(blob) - 3, 2):
        h1, h2 = struct.unpack_from("<2H", blob, off)
        if (h1 & 0xF800) == 0xF000 and (h2 & 0xF800) == 0xF800:
            imm = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
            if imm & 0x400000:
                imm -= 0x800000
            out.append(base + off + 4 + imm)
    return out


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

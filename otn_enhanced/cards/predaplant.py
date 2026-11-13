"""Predaplant Darlingtonia Cobra (0x0FED, donor Jellyfish) + Predaplant Ophrys Scorpio (0x17CF, donor Skull Dog Marron).

Both whole cards, one module (user 2026-11-06). SHIPPED 2026-11-06 on user approval (steps.STEPS + _verify_all_patches.SHIPPED), WITHOUT custom art; in-game test NOT
reported. Single-card test: layered on the chain ROM. Design, proofs and rulings: notes/predaplant-darlingtonia-ophrys-findings.md.  Nothing here is in-game confirmed.

Archetype   a NEW "Predaplant" set code = index 0x28 (list @0x0209C582, two phantoms) -> [0x0FED, 0x17CF].
Ophrys      "If Normal or Special Summoned: You can send 1 monster from your hand to the GY; Special Summon 1 'Predaplant' monster
            from your Deck, except Ophrys. Once per turn."
            cls1 {O_RES, 0, O_COND, 'You can' 0x021E51E5, O_COST}; VIRTUAL criteria rows 0xFF30 = {aux 0x28, 0x0223CAB5, 0x22}
            (Deck summon, except self) and 0xFF31 = {0xFFFF, 0x0223CB65, 0x02} (monster from hand), chosen by the H2 front from
            Upstart Golden Ninja's discriminator (hand-scan probe byte OR cost running -> 0xFF31); c79 arm (5th arm -> stub
            re-homed to 0x50 B).
Darlingtonia "If Special Summoned by the effect of a 'Predaplant' monster: You can add 1 'Polymerization' / 'Fusion' Spell. Once per
            Duel."  cls1 {add-to-hand 0x02207EF5, 0, D_COND, 'You can', D_COST}; virtual row 0xFF32 = {aux 0x59 (the native
            Polymerization / 'Fusion' list), 0x0223CAF5, 0x04 (Spell)}; c9 arm.  The Ophrys-only gate = Ophrys's resolver stamps
            KEY_ARM (this turn) and D_COND also requires the summon to have come FROM THE DECK ([0x02298A28+0xA] == 0x0D).
Why virtual rows: the criteria table has no free phantom (its 4 spare ones are the second stock copies that tg_striker,
tg_warwolf, sea_lancer and ninjitsu_art still count on), so the rows live in ov5 data and are reached through H2/H3 fronts
AHEAD of Gearfried's, exactly as Disguise / Medraut / Gearfried do.

    uv run python -m otn_enhanced.cards.predaplant
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS1, Compiled, Row, SetCodeTable, archetype_member, card, card_props
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

DARL, OPHRYS = 0x0FED, 0x17CF
C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_predaplant.nds"

# --- natives (all Thumb, odd where called through a register) ---------------------------------------------------
DECK_TO_HAND, TAG_YOU_CAN = 0x02207EF5, 0x021E51E5
HAND_SEND, DECK_SS, DECK_SEARCH = 0x0223CB65, 0x0223CAB5, 0x0223CAF5      # criteria handlers: hand send / Deck SS / Deck add
H3_RESUME = 0x02243F71
for _v in (DECK_TO_HAND, TAG_YOU_CAN, DECK_SS, DECK_SEARCH, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

PREDAPLANT_SETCODE, FUSION_SETCODE = 0x28, 0x59
PRED_TABLE = SetCodeTable("Predaplant", 0x0209C582, 2, (0x02023AF8,), (0x02023AF4,))
WORD_MONSTER, WORD_SPELL, WORD_MONSTER_EXCEPT_SELF = 0x00000002, 0x00000004, 0x00000022

# virtual criteria rows (index 0xFF00|j is the Disguise namespace, 0xFF10 Medraut, 0xFF20 Gearfried; ours 0xFF30..0xFF32)
IDX_O_EFFECT, IDX_O_COST, IDX_D = 0xFF30, 0xFF31, 0xFF32
ROW_O_EFFECT = (OPHRYS, PREDAPLANT_SETCODE, DECK_SS, WORD_MONSTER_EXCEPT_SELF)
ROW_O_COST = (OPHRYS, 0xFFFF, HAND_SEND, WORD_MONSTER)
ROW_D = (DARL, FUSION_SETCODE, DECK_SEARCH, WORD_SPELL)
ROWS_BLOB = b"".join(struct.pack("<HHII", *r) + bytes(4) for r in (ROW_O_EFFECT, ROW_O_COST, ROW_D))

CLS1_DROP_D, CLS1_DROP_O = 0x0E17, 0x0E20
SETCODE_DROP_D, SETCODE_DROP_O = 0x1434, 0x1433

S = {n: getattr(O5, f"CAVE_PD_{n}") for n in ("D_COND", "D_COST", "O_COND", "O_COST", "O_RES", "MISS", "PROBE", "ROWS", "H2", "H3")}
RESERVE = {"D_COND": 0x60, "D_COST": 0x20, "O_COND": 0x80, "O_COST": 0x40, "O_RES": 0x40, "MISS": 0x20, "PROBE": 0x10,
           "ROWS": 0x30, "H2": 0x50, "H3": 0x30}

CLS1_D = (DARL, 0, DECK_TO_HAND, 0, S["D_COND"] | 1, TAG_YOU_CAN, S["D_COST"] | 1)
CLS1_O = (OPHRYS, 0, S["O_RES"] | 1, 0, S["O_COND"] | 1, TAG_YOU_CAN, S["O_COST"] | 1)

H2_SITE, H3_SITE, MISS_SITE = 0x02243F24, 0x02243F62, 0x021EE10C
_DN = O5.dc_next()
H2_PREV, H3_PREV, MISS_PREV = _DN[O5.CAVE_PD_H2], _DN[O5.CAVE_PD_H3], _DN[O5.CAVE_PD_MISS]
COST_STATE = 0x0229AAFC         # + 0x7C = the cost machine's step (Upstart's discriminator)

# the arms live in c9_trigger_hook.ARMS / c79_trigger_hook.ARMS (registered by cid there); a ROM built before this card shipped holds
# the stubs without them, which the installs below rewrite (rewrite_shared refuses anything that is not exactly the old stub)


def _c(stub: str) -> bytes:
    blob = compile_c(C_DIR / "predaplant.c", S[stub], {"STUB": stub, "PROBE": f"0x{S['PROBE']:08X}"})
    assert len(blob) <= RESERVE[stub], f"{stub}: {len(blob):#x} B > {RESERVE[stub]:#x}"
    assert_thumb1_only(blob, S[stub])
    return blob


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


def h2_front() -> bytes:
    """criteria resolver miss tail (r5 = cid; Medraut's shape): Darlingtonia -> 0xFF32; Ophrys -> 0xFF31 while the hand scan
    probes or the cost machine runs, else 0xFF30; then pop the caller's frame. Everyone else: BL onward to Gearfried's front
    (the chain ends in a front that pops, so control never comes back here)."""
    b = EffectBuilder()
    b.ldr_const(0, DARL)
    b.insn("CMP", "R5, R0")
    b.insn("BEQ", "d")
    b.ldr_const(0, OPHRYS)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, S["PROBE"])
    b.insn("LDRB", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "cost")
    b.ldr_const(0, COST_STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "cost")
    b.ldr_const(0, IDX_O_EFFECT)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("cost")
    b.ldr_const(0, IDX_O_COST)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("d")
    b.ldr_const(0, IDX_D)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _asm(b, "H2")


def h3_front() -> bytes:
    """invoker row compute (r6 = index): 0xFF30..0xFF32 -> r0 = ROWS + 0x10 * (index - 0xFF30), r3 = [r0+4], resume 0x02243F70
    (Medraut's contract); else tail-jump to Gearfried's H3 with lr intact."""
    b = EffectBuilder()
    b.ldr_const(0, IDX_O_EFFECT)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x3")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _asm(b, "H3")


def miss_front() -> bytes:
    """miss-timing node (r3 = cid; Disguise's shape): Darlingtonia / Ophrys -> return with Z set (never miss), else previous."""
    b = EffectBuilder()
    for cid in (DARL, OPHRYS):
        b.ldr_const(1, cid)
        b.insn("CMP", "R3, R1")
        b.insn("BEQ", "ret")
    b.ldr_const(1, MISS_PREV | 1)
    b.insn("BX", "R1")
    b.label("ret")
    b.insn("BX", "LR")
    return _asm(b, "MISS")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _exits(base: int, blob: bytes) -> set[int]:
    """Every BL target and every odd (Thumb) pool literal in an assembled front, even-ised."""
    from otn_enhanced.asm.thumb_disasm import decode_thumb
    out = {i.branch_target for i in decode_thumb(blob, base) if i.mnemonic == "BL"}
    out |= {w & ~1 for (w,) in struct.iter_unpack("<I", blob[:len(blob) & ~3]) if w & 1}
    return out


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()          # later owners' fronts may sit ahead of ours
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


@dataclass(frozen=True)
class darlingtonia_whole_card:
    def compile(self, view, cid) -> Compiled:
        assert cid == DARL
        stubs = ((S["D_COND"], _c("D_COND"), "Darlingtonia +0C"),
                 (S["D_COST"], _c("D_COST"), "Darlingtonia +14 (per-Duel stamp)"),
                 (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFF30..0xFF32"),
                 (S["H2"], h2_front(), "H2 front (criteria miss tail)"),
                 (S["H3"], h3_front(), "H3 front (invoker row compute)"),
                 (S["MISS"], miss_front(), "never-miss front (Darlingtonia + Ophrys)"))

        def install(rom, view):
            from otn_enhanced.effects import c9_trigger_hook as c9
            from otn_enhanced.effects.common import rewrite_shared
            _front_at(view, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(view, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            _front_at(view, MISS_SITE, MISS_PREV, S["MISS"], "miss-timing node")
            c9.apply(view.buf)
            base = O5.CAVE_C9TRIG
            assert any(a[0] == DARL for a in c9.ARMS), "Darlingtonia is not registered in c9_trigger_hook.ARMS"
            old = tuple(a for a in c9.ARMS if a[0] != DARL)          # a ROM built before this card shipped holds the stub without our arm
            rewrite_shared(rom, base, c9.RESERVE, c9.stub(base, old), c9.stub(base, c9.ARMS), "c9 stub")

        def check(c, rom, view):
            from otn_enhanced.effects import c9_trigger_hook as c9
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3"), (MISS_SITE, "MISS")):
                c.ok(_reaches(view, site, slot), f"bl @{site:#x} reaches the Predaplant {slot} front")
            nxt = O5.dc_next()
            for slot, prev, blob in (("H2", H2_PREV, h2_front()), ("H3", H3_PREV, h3_front()), ("MISS", MISS_PREV, miss_front())):
                c.eq(nxt[S[slot]], prev, f"dc_next {slot} falls through to Gearfried's/Gearblade's front")
                c.ok(prev in {e & ~1 for e in _exits(S[slot], blob)}, f"{slot} front really exits to {prev:#x}")
            c.eq(O5.read_cave(rom, S["ROWS"], len(ROWS_BLOB)), ROWS_BLOB, "virtual rows resident")
            blob = c9.stub(O5.CAVE_C9TRIG)
            c.ok(O5.read_cave(rom, O5.CAVE_C9TRIG, len(blob)) == blob and len(blob) <= c9.RESERVE,
                 f"c9 stub carries the Darlingtonia arm ({len(blob)} B of {c9.RESERVE})")
            c.eq(ov3_bl_target(view.buf, c9.SITE), O5.CAVE_C9TRIG, "c9 verdict site -> shared stub")

        return Compiled(stubs, (Row(CLS1, CLS1_D, CLS1_DROP_D),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class ophrys_whole_card:
    def compile(self, view, cid) -> Compiled:
        assert cid == OPHRYS
        stubs = ((S["O_COND"], _c("O_COND"), "Ophrys +0C"),
                 (S["O_COST"], _c("O_COST"), "Ophrys +14 (OPT + hand send)"),
                 (S["O_RES"], _c("O_RES"), "Ophrys +04 (stamp + Deck summon)"),
                 (S["PROBE"], bytes(0x10), "DATA: hand-scan probe byte (ships clear)"))

        def install(rom, view):
            from otn_enhanced.effects import c79_trigger_hook as c79
            # c79: the 5th arm overflows the old 0x40 slot -> a 0x50 slot at the new CAVE_C79TRIG; repoint the 4-byte site
            arms = c79.ARMS
            assert any(a[0] == OPHRYS for a in arms), "Ophrys is not registered in c79_trigger_hook.ARMS"
            blob = c79.stub(O5.CAVE_C79TRIG, arms)
            assert_thumb1_only(blob, O5.CAVE_C79TRIG)
            assert len(blob) <= c79.RESERVE, f"c79 stub {len(blob)} B > {c79.RESERVE:#x}"
            if O5.read_cave(rom, O5.CAVE_C79TRIG, len(blob)) != blob:
                O5.install_cave(rom, O5.CAVE_C79TRIG, blob, reserve=c79.RESERVE)
            want_new = common_bl(c79.SITE, O5.CAVE_C79TRIG)
            want_old = common_bl(c79.SITE, O5.CAVE_C79TRIG_OLD2)
            cur = view.blob(c79.SITE, 4)
            assert cur in (want_old, want_new), f"c79 site {c79.SITE:#x} = {cur.hex()}, not the old or new stub BL"
            view.write(c79.SITE, want_new)

        def check(c, rom, view):
            from otn_enhanced.effects import c79_trigger_hook as c79
            slot, reserve = c79.where()           # the stub moves to a bigger slot as later cards add arms
            arms = c79.all_arms()
            blob = c79.stub(slot)
            c.ok(0x17CF in [a[0] for a in arms] and O5.read_cave(rom, slot, len(blob)) == blob,
                 f"c79 stub @{slot:#x} carries all {len(arms)} arms incl. 0x17CF ({len(blob)} B of {reserve:#x})")
            c.ok(code_reaches(rom, c79.SITE, slot), "c79 verdict site reaches the shared stub")
            c.eq(O5.read_cave(rom, S["PROBE"], 4), bytes(4), "probe byte ships clear")
            c.eq(O5.read_cave(rom, S["ROWS"], len(ROWS_BLOB)), ROWS_BLOB, "virtual rows resident (Ophrys 0xFF30/0xFF31)")

        return Compiled(stubs, (Row(CLS1, CLS1_O, CLS1_DROP_O),), installs=(install,), checks=(check,))


DARL_SPEC = card(DARL, darlingtonia_whole_card(), archetype_member(PRED_TABLE, phantom=SETCODE_DROP_D))
OPHRYS_SPEC = card(OPHRYS, ophrys_whole_card(), archetype_member(PRED_TABLE, phantom=SETCODE_DROP_O))
DARL_PROPS = card_props("DARK", "Plant", level=3, atk=1000, defense=1500)
OPHRYS_PROPS = card_props("DARK", "Plant", level=3, atk=1200, defense=800)

_main_d, _verify_d = dsl.make(DARL_SPEC, DARL_PROPS, out=OUT)
_main_o, _verify_o = dsl.make(OPHRYS_SPEC, OPHRYS_PROPS, out=OUT)


def main(write_text: bool = True, src: str = CHAIN, out: str = OUT) -> None:
    _main_d(write_text=write_text, src=src, out=out)
    _main_o(write_text=write_text, src=out, out=out)


def verify(out: str = OUT) -> bool:
    a = _verify_d(out)
    b = _verify_o(out)
    return a is not False and b is not False


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)

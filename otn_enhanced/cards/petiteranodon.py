"""Petiteranodon (EARTH / Dinosaur / Level 2 / 500 / 500) on Mammoth Graveyard 0x0FE1.

    "If this card is destroyed by a card effect and sent to the Graveyard: Special Summon 1 Level 4 or higher
     Dinosaur-Type monster from your Deck, but it cannot attack this turn."
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS2, CRITERIA, Compiled, LEAVE_MASK, Row, _template
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


_CRIT_SELECT_FROM_DECK = 0x0223CA99      # criteria handler: select from the Deck (this entry is the thumb-bit-set form)


@dataclass(frozen=True)
class destroyed_by_effect_special_summon_from_deck:
    """'If this card is destroyed by a card effect and sent to the GY: Special Summon 1 <filter> monster from your
    Deck' -- the native `template`'s three records (cls2, criteria, field leave-mask) re-keyed to the donor, with the
    criteria word swapped to `word` (the template's `template_word` asserted). All three drop rows of ONE phantom.
    The leave-mask row is FIELD-ONLY; off the field the hardcoded cid chain needs `hand_destroy_rekey`."""
    template: int
    cls2_slots: tuple
    template_word: int
    word: int
    mask: int
    phantom: int

    def compile(self, view, cid) -> Compiled:
        cls2 = _template(view, CLS2, self.template, self.cls2_slots)
        pop = _template(view, CRITERIA, self.template)
        assert pop[1:] == (0xFFFF, _CRIT_SELECT_FROM_DECK, self.template_word), f"template criteria drifted: {pop}"
        mask = _template(view, LEAVE_MASK, self.template)
        assert mask[1] == self.mask, f"template leave mask drifted: {mask[1]:#06x}"
        return Compiled(rows=(Row(CLS2, (cid, cls2[1]) + self.cls2_slots, self.phantom),
                              Row(CRITERIA, (cid, 0xFFFF, _CRIT_SELECT_FROM_DECK, self.word), self.phantom),
                              Row(LEAVE_MASK, (cid, self.mask), self.phantom)))


_BSEARCH = 0x02022E14        # Thumb binary search (reached by plain BL from Thumb)


@dataclass(frozen=True)
class summoned_monster_cannot_attack:
    """'... Special Summon 1 ..., but it cannot attack this turn' via Summoner Monk's wiring: the source cid is
    in the summon-event list (attaches a kind-2 rider keyed by the SOURCE cid) AND the attack-check list (a listed
    key = cannot attack). Both lists are full of real cards, so both `bl 0x02022E14` searches go to ONE stub:
    key == cid -> 1, else tail-call the native search. Both sites load r0 = key and only zero-test the result.
    A site may be fronted by another card that tail-calls the stub (verify accepts that).
    SHARED PATHS in ov5: every summon event / attack check in a puzzle jumps into overlay 41 (user accepted)."""
    slot: int                 # ov5 cave
    sites: tuple              # ((bl site, pool literal, list address, label), ...)

    def _stub(self, cid):
        b = EffectBuilder()
        b.ldr_const(3, cid)
        b.insn("CMP", "R0, R3")
        b.insn("BNE", "miss")
        b.insn("MOV", "R0, #0x1")
        b.insn("BX", "LR")
        b.label("miss")
        b.ldr_const(3, _BSEARCH | 1)
        b.insn("BX", "R3")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        return blob

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.summon_trigger_hook import _bl
        want = {s: _bl(s, self.slot) for s, *_ in self.sites}

        def install(rom, view):
            for site, pool, lst, label in self.sites:
                assert view.u32(pool) == lst, f"{label}: pool drifted"
                cur = view.blob(site, 4)
                if cur != want[site]:
                    assert cur == _bl(site, _BSEARCH), f"{label} @{site:#010x} is {cur.hex()} -- another patch owns it"
                    view.write(site, want[site])

        def check(c, rom, view):
            from otn_enhanced.asm import effect_verify
            for site, pool, lst, label in self.sites:
                # Obedience Schooled / Horn of Olifant front these sites and tail-call the stub.
                reach = code_reaches(rom, site, self.slot)
                c.ok(reach and view.u32(pool) == lst, f"{label} bl @{site:#010x} reaches the stub")

        return Compiled(((self.slot, self._stub(cid), "no-attack stub"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class hand_destroy_rekey:
    """'destroyed ... and sent to the GY' from the HAND (any non-field zone): off the field this is the hardcoded
    sorted cid chain in relocator 0x021D1300. The donor's search ends at node `node`, which tests the PHANTOM
    cid (no card_prop; its literal has that one reader); re-key literal -> donor and branch -> `arm`
    (the template's accept arm), IN PLACE. A whole-table walk proves only the donor and the phantom change leaf.
    Registers the node with snoww's switch-stub patcher at construction (what the module did at import)."""
    donor: int
    node: int
    literal: int
    branch: int
    phantom: int
    stock_arm: int              # the arm the phantom's branch stock-targets
    arm: int                    # template's accept arm
    template: int

    def __post_init__(self):
        from otn_enhanced.cards import snoww as sn
        sn.register_switch_stub(self.node, 0, {self.donor: self.arm, self.phantom: sn.SWITCH_END})

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import snoww as sn
        assert cid == self.donor

        def b(src, dst):
            off = (dst - (src + 4)) >> 1
            assert -1024 <= off <= 1023, f"B out of range {src:#x}->{dst:#x}"
            return struct.pack("<H", 0xE000 | (off & 0x7FF))

        def install(rom, view):
            ov = view.buf
            lit = view.u32(self.literal)
            br = view.blob(self.branch, 2)
            if lit == cid and br == b(self.branch, self.arm):
                return
            assert lit == self.phantom and br == b(self.branch, self.stock_arm), \
                f"node drifted: lit {lit:#x}, br {br.hex()}"
            assert view.blob(self.node, 6) == bytes.fromhex("784885420" "0d1"), "node shape"
            assert sn._switch_leaf(bytes(ov), self.template) == self.arm, "template left its arm"
            before = {c: sn._switch_leaf(bytes(ov), c) for c in range(0x2700)}
            assert before[cid] == sn.SWITCH_END and before[self.phantom] == self.stock_arm
            view.write(self.literal, struct.pack("<I", cid))
            view.write(self.branch, b(self.branch, self.arm))
            moved = {c: (before[c], now) for c in range(0x2700)
                     if (now := sn._switch_leaf(bytes(ov), c)) != before[c]}
            assert moved == {cid: (sn.SWITCH_END, self.arm), self.phantom: (self.stock_arm, sn.SWITCH_END)}, moved

        def check(c, rom, view):
            for k, want in ((cid, self.arm), (self.template, self.arm), (self.phantom, sn.SWITCH_END)):
                c.eq(sn._switch_leaf(bytes(view.buf), k), want, f"sent-to-GY chain: 0x{k:04X} -> {want:#010x}")

        return Compiled(installs=(install,), checks=(check,))



SPEC = card(
    0x0FE1,
    destroyed_by_effect_special_summon_from_deck(
        template=0x1A8F,                                    # Babycerasaurus
        cls2_slots=(0x02206CAD, 0, 0x0224A115, 0, 0),
        template_word=0x48900002,                           # Lv<=4
        word=0x48500002,                                    # Lv>=4
        mask=0x0E00,                                        # to-GY + destroyed + by effect
        phantom=0x0E6A),
    summoned_monster_cannot_attack(
        ov5_cave.CAVE_PTER_NOATK,
        sites=((0x02268090, 0x02268118, 0x0228F708, "summon-rider list"),
               (0x021A4AC6, 0x021A4CE0, 0x0226D6F8, "attack-check list"))),
    hand_destroy_rekey(donor=0x0FE1, node=0x021D13C2, literal=0x021D15A4, branch=0x021D13C8, phantom=0x0EC9,
                       stock_arm=0x021D185C, arm=0x021D18D2, template=0x1A8F))

PROPS = card_props("EARTH", "Dinosaur", level=2, atk=500, defense=500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_petiteranodon.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

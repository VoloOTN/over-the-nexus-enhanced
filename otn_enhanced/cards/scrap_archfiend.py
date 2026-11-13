"""Scrap Archfiend (EARTH / Fiend / Synchro / Level 7 / 2700 / 1800) on Humanoid Worm Drake 0x13C6.

    1 Tuner + 1 or more non-Tuner monsters
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, Compiled, _FUSION_DEAD_MATERIAL, _FUSION_TABLE_A, _SYNCHRO_DONOR_GENRE, _SYNCHRO_NEW_GENRE, _fusion_recipe_kill
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from dataclasses import dataclass
import ndspy.rom


@dataclass(frozen=True)
class effectless_fusion_becomes_synchro_monster:
    """'1 Tuner + 1 or more non-Tuner monsters' with NO effect (a vanilla Synchro): the donor's fusion recipe materials are
    blanked (the CPU planner reads them without an is-Fusion gate), its card_prop record is copied from an effectless Synchro
    reference (cid swapped; type 35 Synchro Monster, genre bits {21 nomi, 36 SYNCHRO} and NO Tuner bit 35: not a Tuner, but a
    non-Tuner material), and the stat fields follow from `card_props`. Set-code membership is `archetype_member` per list.
    The Synchro summon procedure is ABSENCE from the three exception lists (LIST_A, min-3, two-leading-Tuners)."""
    row: int
    stock: tuple
    reference: int            # an effectless Synchro Monster (card_type 35) whose whole card_prop record is the template

    def compile(self, view, cid) -> Compiled:
        def install(rom, view):
            _fusion_recipe_kill(view.buf, cid, self.row, self.stock)

        def post(out):
            from otn_enhanced.data.card_stats import find_pac
            new_type, donor_type = ERA2_CARD_TYPE_REVERSE["Synchro Monster"], ERA2_CARD_TYPE_REVERSE["Fusion Monster"]
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            fid, orig, archive = find_pac(rom)
            pac = bytearray(orig)
            cpf = next(f for f in archive.files if f.get_clean_name().lower() == "card_prop.bin")
            gnf = next(f for f in archive.files if f.get_clean_name().lower() == "card_genre.bin")
            n = (cpf.size - 8) // 8
            assert n == (gnf.size - 8) // 8 == 4305, "card_prop / card_genre not parallel"
            prop_off = genre_off = ref_off = None
            for i in range(n):
                o = cpf.address + 8 + i * 8
                k = int.from_bytes(pac[o:o + 8], "little") & 0x3FFF
                if k == cid and prop_off is None:
                    prop_off, genre_off = o, gnf.address + 8 + i * 8
                if k == self.reference and ref_off is None:
                    ref_off = o
            assert prop_off is not None and ref_off is not None, "donor or reference cid not in card_prop.bin"
            ref = int.from_bytes(pac[ref_off:ref_off + 8], "little")
            assert (ref >> 32) & 0x3F == new_type, f"reference {self.reference:#06x} is not a Synchro Monster (type {new_type})"
            cur = int.from_bytes(pac[prop_off:prop_off + 8], "little")
            if (cur >> 32) & 0x3F != new_type:
                assert (cur >> 32) & 0x3F == donor_type, f"card_prop[{cid:#06x}] is not the stock effectless Fusion"
                pac[prop_off:prop_off + 8] = ((ref & ~0x3FFF) | cid).to_bytes(8, "little")
            g = int.from_bytes(pac[genre_off:genre_off + 8], "little")
            if g != _SYNCHRO_NEW_GENRE:
                assert g in (_SYNCHRO_DONOR_GENRE, _SYNCHRO_NEW_GENRE), f"card_genre is {g:#018x}, not the stock effectless-Fusion value"
                pac[genre_off:genre_off + 8] = _SYNCHRO_NEW_GENRE.to_bytes(8, "little")
            assert len(pac) == len(orig), "bin2.pac changed size -- these edits are in place"
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out)

        def check(c, rom, view):
            c.eq(view.unpack(_FUSION_TABLE_A + self.row * 8, "<4H"),
                 (cid, _FUSION_DEAD_MATERIAL, _FUSION_DEAD_MATERIAL, 0), f"fusion recipe A[{self.row}] neutralised")
            for lst, n in ((0x02275AB8, 16), (0x02275AD8, 21), (0x02248280, 2)):
                c.ok(cid not in view.unpack(lst, f"<{n}H"), f"donor absent from Synchro exception list {lst:#x}")

        return Compiled(installs=(install,), posts=(post,), checks=(check,))



PHANTOM = 0x23F2        # Scrap Archfiend's OWN reserved cid (3DS 4339): both lists drop exactly this slot
SCRAP = SetCodeTable("Scrap", 0x0209CC70, 25, (0x02023EEC,), (0x02023EE8,))              # thunk 0x02023EE4
ARCHFIEND = SetCodeTable("Archfiend", 0x0209CF90, 42, (0x02023768,), (0x02023764,))      # thunk 0x02023760

SPEC = card(
    0x13C6,
    effectless_fusion_becomes_synchro_monster(row=57, stock=(0x13C5, 0x13C4), reference=0x1E11),    # Gaia Knight
    archetype_member(SCRAP, phantom=PHANTOM),
    archetype_member(ARCHFIEND, phantom=PHANTOM))

PROPS = card_props("EARTH", "Fiend", level=7, atk=2700, defense=1800, card_type="Synchro Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_scrap_archfiend.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

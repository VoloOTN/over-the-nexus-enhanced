"""code_reaches follows hook chains through later fronts, and does not leak into neighbouring stubs.

    uv run python -m unittest otn_enhanced.tests.test_code_reaches
"""
import unittest
from pathlib import Path

ROM = Path("data/over_the_nexus/working/rom_all_patches.nds")


@unittest.skipUnless(ROM.exists(), f"needs a built {ROM}")
class CodeReaches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ndspy.rom
        cls.rom = ndspy.rom.NintendoDSRom.fromFile(str(ROM))

    def test_chains(self):
        from otn_enhanced.effects.common import code_reaches
        cases = [
            (0x021B05CC, 0x021F5778, True),    # Safe Zone targeting link, March's front ahead of it
            (0x02269266, 0x023AFE70, True),    # March free-zone check, First Monarch's front ahead
            (0x02243F24, 0x023AE000, True),    # criteria miss-tail: Erebus -> Masterplan -> Tessera -> ... -> Block Dragon H2
            (0x02243F62, 0x023AE020, True),
            (0x021B05CC, 0x023AE3B0, False),   # a stub on a different chain
            (0x02243F24, 0x023AE020, False),   # H2 must not fall through into the adjacent H3 cave
            (0x02243F62, 0x023AE000, False),
        ]
        for site, want, expect in cases:
            with self.subTest(site=hex(site), want=hex(want)):
                self.assertEqual(code_reaches(self.rom, site, want), expect)


if __name__ == "__main__":
    unittest.main()

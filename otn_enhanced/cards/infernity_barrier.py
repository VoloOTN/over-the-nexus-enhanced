"""Infernity Barrier (Counter Trap) on Destruction Jammer 0x1DDD.

    "If you control a face-up ATK Position "Infernity" monster with no cards in hand: Negate an
     opponent's Spell/Trap/effect and destroy it."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import archetype_member, card, SetCodeTable, Compiled
from otn_enhanced.effects.common import Table
from dataclasses import dataclass
from otn_enhanced.effects.common import rows


COND_DISPATCHER = 0x021F5F94    # shared counter-trap condition dispatcher: binary-searches the cid to a per-card leaf


_CLS0_NEGATE = Table(base=0x0227E64C, count=0x51A, stride=0x18, fmt="<HHIIIII", label="cls0")


_GENERIC_NEGATE = 0x022062F9    # cls0 +04 generic "negate the activation + destroy"


@dataclass(frozen=True)
class negate_with_native_condition:
    """'Negate the activation and destroy it' under a condition Konami already ships under an unused phantom cid:
    the ONE dispatcher branch `site` the search takes for this cid is retargeted from the donor's own leaf
    (`stock_leaf`) to the phantom's `leaf`. No stubs: the donor keeps its real cid, its cls0 row and the generic
    negate+destroy resolver, so nothing downstream sees a spoofed cid."""
    site: int
    stock_leaf: int
    leaf: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import common
        old, new = common.b(self.site, self.stock_leaf), common.b(self.site, self.leaf)

        def install(rom, v):
            cur = v.blob(self.site, 2)
            assert cur in (old, new), f"dispatcher branch @0x{self.site:08X} = {cur.hex()}, expected {old.hex()}"
            i = next((i for i, r in enumerate(rows(v, _CLS0_NEGATE)) if r[0] == cid), None)
            assert i is not None, f"cls0 row for 0x{cid:04X} not found"
            _, _, res, _, cond, _, _ = rows(v, _CLS0_NEGATE)[i]
            assert (res, cond) == (_GENERIC_NEGATE, COND_DISPATCHER | 1), (
                f"donor 0x{cid:04X} cls0 +04/+0C = 0x{res:08X}/0x{cond:08X}, not the generic negate + dispatcher")
            v.write(self.site, new)

        def check(c, rom, v):
            c.eq(v.blob(self.site, 2), new, f"dispatcher branch @0x{self.site:08X} -> leaf 0x{self.leaf:08X}")

        return Compiled(installs=(install,), checks=(check,))



INFERNITY_TABLE = SetCodeTable("Infernity", 0x0209CB22, 0x13, (0x02023DAC, 0x02023DD8), (0x02023DA8, 0x02023DC6))

SPEC = card(
    0x1DDD,
    negate_with_native_condition(site=0x021F6042, stock_leaf=0x021F6298, leaf=0x021F63B6),
    archetype_member(INFERNITY_TABLE, phantom=0x234C))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_infernity_barrier.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

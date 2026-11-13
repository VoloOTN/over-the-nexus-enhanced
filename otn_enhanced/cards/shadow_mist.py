"""Elemental HERO Shadow Mist (DARK / Warrior / Level 4 / 1000 / 1500) on Ryu-Kishin Powered 0x111F.

    "If this card is Special Summoned: You can add 1 "Change" Quick-Play Spell Card from your Deck to your hand.
     If this card is sent to the GY: You can add 1 "HERO" monster from your Deck to your hand, except "Elemental HERO
     Shadow Mist". You can only use 1 ... effect per turn, and only once that turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, CLS1, CLS2, CRITERIA, Compiled, LEAVE_MASK, LIST_CODE9, Row, _HOPT_KIND, _SM_STOCK_SRC, _TAG_YOU_CAN, _TURNLOG_POST, _TURNLOG_QUERY, _hopt_you_can_stub, bl_target
from otn_enhanced.effects import ov5_cave
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import insert_sorted
from otn_enhanced.effects.common import keys
from otn_enhanced.rom.overlay_io import load_overlay3
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class special_summoned_or_sent_to_gy_search_shared_lock:
    """'If this card is Special Summoned: You can add 1 <named Spell> from your Deck to your hand.' + 'If this card is
    sent to the GY: You can add 1 <HERO> monster from your Deck to your hand, except this card.' + 'only once that
    turn' for BOTH: one turn-log kind, one cond stub (+0C: lock clear -> native 0x021F0821 offer gate) and one slot4
    stub (+10: 'You can' 0x021E51E5, a Yes stamps the lock) shared by the cls1 and the cls2 record.
      code-9 list + cls1 {add-to-hand, +0C, +10}; leave-mask row {cid, sent-to-GY} + cls2 (same slots); criteria rel 0
      = the named card from the Deck, rel 1 = the HERO row (bit 0x20 'except this card') placed IMMEDIATELY after
      rel 0 (the resolver adds r4 to the LEFTMOST row). The class-2 'You can' arm (timing_class_hook) and the
      rel-0/rel-1 picker (criteria_row_hook) are the SHARED hooks; both ARMS are registered in their own modules."""
    add_to_hand: int
    named: tuple[int, int, int]       # criteria rel 0: (aux = named cid, handler, word)
    hero: tuple[int, int, int]        # criteria rel 1: (aux, handler, word)
    mask: int
    have_target: int
    slots: tuple[int, int]            # (+0C cond, +10 slot4), ov5
    phantoms: tuple[int, int, int, int, int, int]   # (code-9 list, cls1, crit rel0, leave mask, cls2, crit rel1)

    def compile(self, view, cid) -> Compiled:
        cond, slot4 = self.slots
        ph9, ph1, phc0, phm, ph2, phc1 = self.phantoms
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_query(R0, cid, _HOPT_KIND, via=R6)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.call_addr(self.have_target, R4, R5, via=R6)
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        cb = b.assemble(cond, pad="nop")
        sb = _hopt_you_can_stub(slot4, cid)
        assert_thumb1_only(cb, cond)
        for a in (self.add_to_hand, _TURNLOG_QUERY, _TURNLOG_POST, self.have_target, _TAG_YOU_CAN):
            assert a & 1, f"{a:#x}: blx to an even literal switches to ARM state -> freeze"
        slots = (self.add_to_hand, 0, cond | 1, slot4 | 1, 0)
        row0 = (cid,) + self.named
        row1 = (cid,) + self.hero

        def install(rom, view):
            from otn_enhanced.effects import criteria_row_hook as crh
            from otn_enhanced.effects import timing_class_hook as tch
            insert_sorted(view, CRITERIA, row0, drop=phc0, quiet=True)
            recs = list(rows(view, CRITERIA))
            mine = [r for r in recs if r[0] == cid]
            if mine != [row0, row1]:
                assert mine == [row0], f"criteria expected donor rows [rel 0], got {mine}"
                ks = [r[0] for r in recs]
                assert ks.count(phc1) == 1, f"criteria phantom {phc1:#06x} must own exactly one row"
                src = ks.index(phc1)
                dst = ks.index(cid) + 1
                recs.pop(src)
                recs.insert(dst - 1 if src < dst else dst, row1)
                for i, r in enumerate(recs):
                    view.pack(CRITERIA.addr(i), CRITERIA.fmt, *r)
                assert keys(view, CRITERIA) == sorted(keys(view, CRITERIA)), "criteria unsorted"
            tch.apply(view.buf, quiet=True)
            crh.apply(view.buf, quiet=True)
            tch.install(rom, quiet=True)
            crh.install(rom, quiet=True)

        def check(c, rom, view):
            from otn_enhanced.effects import criteria_row_hook as crh
            from otn_enhanced.effects import timing_class_hook as tch
            recs = rows(view, CRITERIA)
            ks = [r[0] for r in recs]
            c.ok(ks == sorted(ks) and [r for r in recs if r[0] == cid] == [row0, row1]
                 and phc0 not in ks and phc1 not in ks,
                 "criteria rel 0 + rel 1 under the donor, adjacent and in order; both phantoms dropped; sorted")
            tch.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            c.ok(any(x == cid for x, *_ in tch.ARMS), f"{cid:#06x} registered in timing_class_hook.ARMS")
            crh.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            c.ok(any(x == cid for x, *_ in crh.ARMS), f"{cid:#06x} registered in criteria_row_hook.ARMS")

        return Compiled(((cond, cb, "+0C cond"), (slot4, sb, "+10 slot4")),
                        (Row(LIST_CODE9, (cid,), ph9),
                         Row(CLS1, (cid, 0) + slots, ph1),
                         Row(LEAVE_MASK, (cid, self.mask), phm),
                         Row(CLS2, (cid, 0) + slots, ph2)),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class sent_to_gy_chain_node_rekeyed:
    """Off-field 'sent to the GY' triggers walk a hardcoded sorted cid chain (0x021D1392). The donor's search ends at
    a node testing a PHANTOM cid (`subs r1,#k ; cmp r5,r1 ; beq accept ; b reject`, r1 loaded from the shared pool
    literal `literal` = `literal_value`); the immediate is re-keyed so the node tests the donor and the beq goes to
    the accept arm, IN PLACE (8 bytes). Pure ov3, no stub: the chain also runs in puzzles. The whole-chain walk
    proves only the donor and the phantom change leaf. Registers with snoww's switch-stub patcher at construction.
    Overtex Qoatlus may later LIFT the node's first 4 B into a BL to a chain stub that replays this test."""
    node: int
    native: bytes
    patched: bytes
    literal: int
    literal_value: int
    phantom: int
    accept_leaf: int

    def __post_init__(self):
        from otn_enhanced.cards import snoww as sn
        sn.register_switch_stub(self.node, 0, {self._donor(): self.accept_leaf, self.phantom: sn.SWITCH_END})

    def _donor(self) -> int:
        return self.literal_value - self.patched[0]

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import snoww as sn
        assert cid == self._donor() and self.literal_value - self.native[0] == self.phantom

        def install(rom, view):
            cur = view.blob(self.node, 8)
            if cur == self.patched:
                return
            assert cur == self.native, f"node {self.node:#x} is {cur.hex()}, not stock -- another patch owns it"
            assert view.u32(self.literal) == self.literal_value, "chain subtree literal moved"
            view.write(self.node, self.patched)

        def check(c, rom, view):
            node = view.blob(self.node, 8)
            lifted = node[4:] == self.patched[4:] and sn._in_stub(bl_target(node[:4], self.node))
            c.ok(node == self.patched or lifted,
                 f"sent-to-GY node {self.node:#x} re-keyed to the donor -> accept" + (" (lifted into a stub)" if lifted else ""))
            c.eq(sn._switch_leaf(bytes(view.buf), cid), self.accept_leaf,
                 f"simulated chain: {cid:#06x} reaches the ACCEPT store {self.accept_leaf:#x}")
            _, stock = load_overlay3(_SM_STOCK_SRC)
            stock = bytes(stock)
            moved = [k for k in range(0x2700) if sn._switch_leaf(stock, k) != sn._switch_leaf(bytes(view.buf), k)]
            allowed = set(sn.EXTRA_SWITCH_DONORS) | {sn.DONOR_CID}     # other chain patches registered with snoww
            c.ok({self.phantom, cid} <= set(moved) and set(moved) <= allowed,
                 f"whole-chain walk vs stock: nothing but registered donors moved (got {[hex(k) for k in moved]})")

        return Compiled(installs=(install,), checks=(check,))


def miss_node_reaches(buf, base: int, node: int, goal: int, ov5=None) -> bool:
    """The node BLs `goal` -- directly, or through later cards' front stubs (eva, infernoble) whose literal pools
    tail-jump onward. With *ov5* (the decompressed overlay-5 image) a front in the ov5 cave is followed too."""
    t = bl_target(bytes(buf[node - base:node - base + 4]), node)
    for _ in range(12):
        if t == goal:
            return True
        if ov5 is not None and ov5_cave.OV5_RAM_BASE <= t < ov5_cave.OV5_RAM_BASE + len(ov5):
            win = bytes(ov5[t - ov5_cave.OV5_RAM_BASE:t - ov5_cave.OV5_RAM_BASE + 0x40])
        elif t < base:
            return False
        else:
            win = bytes(buf[t - base:t - base + 0x20])
        lits = [struct.unpack_from("<I", win, i)[0] for i in range(0, len(win) - 3, 2)]
        if goal | 1 in lits:
            return True
        hi = ov5_cave.OV5_RAM_BASE + (len(ov5) if ov5 is not None else 0)
        nxt = [v & ~1 for v in lits if v & 1 and v & ~1 != t
               and (base <= v < 0x022C5900 or (ov5 is not None and ov5_cave.OV5_RAM_BASE <= v < hi))]
        if not nxt:
            return False
        t = nxt[0]
    return False


def miss_blocks(a: int, b: int, donor: int) -> tuple[bytes, bytes]:
    """The two ov3 dead blocks the miss-timing node BLs into. A replays the node's two displaced ops (`subs r2,#0x13 ;
    cmp r3,r2`) and returns on the caller's own beq when r3 is the real cid it tests; otherwise B tests r3 == donor
    (built as 0x89 << 5 - 1, no pool). Z goes back to the caller's beq; r1 is dead on both exits."""
    def br(src, dst):
        off = (dst - (src + 4)) >> 1
        assert -1024 <= off <= 1023, f"B out of range {src:#x}->{dst:#x}"
        return 0xE000 | (off & 0x7FF)

    assert (0x89 << 5) - 1 == donor
    return (struct.pack("<5H", 0x3A13, 0x4293, 0xD000, br(a + 6, b), 0x4770),
            struct.pack("<5H", 0x2189, 0x0149, 0x3901, 0x428B, 0x4770))


@dataclass(frozen=True)
class never_miss_timing:
    """'You can' triggers ask 0x021EE0E0 (timing.miss_timing_test) whether the timing was missed; its head is a cid tree
    of hard-coded IF cards ending in `never miss`. The donor's search ends at `node` (`subs r2,#0x13 ; cmp r3,r2 ;
    beq never ; b walk` -- Sinister Sprocket 0x1E1B, a REAL card, kept). The two displaced ops become a BL into the
    ov3 dead blocks (puzzle-safe): the donor never misses its timing (Fusion / Synchro material, Tribute Summon)."""
    node: int
    native: bytes
    block_a: int
    block_b: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        a, b = miss_blocks(self.block_a, self.block_b, cid)
        blocks = ((self.block_a, a), (self.block_b, b))

        def install(rom, view):
            if (miss_node_reaches(view.buf, view.base, self.node, self.block_a)
                    and all(view.blob(addr, len(blob)) == blob for addr, blob in blocks)):
                return
            assert view.blob(self.node, 8) == self.native, f"node {self.node:#x} not stock -- another patch owns it"
            for addr, blob in blocks:
                assert_thumb1_only(blob, addr)
                view.write(addr, blob)
            view.write(self.node, tch._bl(self.node, self.block_a))

        def check(c, rom, view):
            ov5 = bytes(ov5_cave._load_ov5_decompressed(rom).data)
            c.ok(miss_node_reaches(view.buf, view.base, self.node, self.block_a, ov5)
                 and view.blob(self.node + 4, 4) == self.native[4:],
                 f"miss-timing node {self.node:#x} -> BL {self.block_a:#x} (direct or via a front stub), caller's beq/b kept")
            c.ok(view.blob(self.block_a, 10) == a, f"ov3 block @{self.block_a:#x} installed")
            # Overtex Qoatlus may end block B `b C` instead of `bx lr`; its donor test (first four halfwords) stays intact.
            blk = view.blob(self.block_b, 10)
            c.ok(blk[:8] == b[:8] and (blk[8:] == b[8:] or blk[9] >> 3 == 0x1C),
                 f"ov3 block @{self.block_b:#x} installed (donor test intact)")

        return Compiled(installs=(install,), checks=(check,))



DONOR_CID = 0x111F
MISS_NODE, MISS_NODE_NATIVE = 0x021EE10C, bytes.fromhex("133a934231d0c0e0")
MISS_BLOCK_A, MISS_BLOCK_B = 0x021B58D0, 0x021B5AAA
GATE_NODE = 0x021D13CC
GATE_NATIVE, GATE_PATCHED = bytes.fromhex("10398d4207d0f5e2"), bytes.fromhex("66398d4214d0f5e2")
GATE_ACCEPT_LEAF = 0x021D19BE

SPEC = card(
    DONOR_CID,
    special_summoned_or_sent_to_gy_search_shared_lock(
        add_to_hand=0x02207EF5,
        named=(0x236A, 0x0223D075, 0x4),                    # Mask Change, from the Deck
        hero=(0x001B, 0x0223CAF5, 0x22),                    # "HERO" monster, Deck, except self
        mask=0x0800,                                        # sent to the GY, from any location
        have_target=0x021F0821,
        slots=(ov5_cave.CAVE_SM_COND, ov5_cave.CAVE_SM_SLOT4),
        phantoms=(0x176C, 0x1190, 0x0EB7, 0x0EBA, 0x0EBA, 0x0EB5)),
    sent_to_gy_chain_node_rekeyed(
        node=GATE_NODE, native=GATE_NATIVE, patched=GATE_PATCHED, literal=0x021D159C, literal_value=0x1185,
        phantom=0x1175, accept_leaf=GATE_ACCEPT_LEAF),
    never_miss_timing(MISS_NODE, MISS_NODE_NATIVE, MISS_BLOCK_A, MISS_BLOCK_B),
    archetype_member(SetCodeTable("Elemental HERO", 0x0209CFE4, 58, (0x02023824, 0x020239E0), ()), phantom=0x1A6F))

PROPS = card_props("DARK", "Warrior", level=4, atk=1000, defense=1500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_shadow_mist.nds")

# eva and overtex_qoatlus ride this card's miss-timing node and chain node.
_bl_target = dsl.bl_target


def _miss_node_reaches_a(ov, ov5=None, target=None):
    return miss_node_reaches(ov, RAM_BASE, MISS_NODE, MISS_BLOCK_A if target is None else target, ov5)


def miss_block_b():
    return miss_blocks(MISS_BLOCK_A, MISS_BLOCK_B, DONOR_CID)[1]


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)

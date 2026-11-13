"""CPU play for hand Special Summons the CPU's own planner never offered, split out of Block Dragon (2026-11-09).

    THE PROBLEM (measured by GDB in CPU-vs-CPU duels, notes/block-dragon-findings.md):  the CPU's hand-card loop (ov5 0x02340EEC) asks `bl 0x0225E51C` for every hand
    card at 0x02340F16 -- the engine's own hand-SS legality BST -- and NEVER goes through the shared hand-SS trampoline (ov3 0x021F1398) that is hooked only at the
    HUMAN menu site 0x0224C026.  So the CPU never saw any trampoline-registered card (the Elemental Lords: Grandsoil / Moulinglacia / Pyrorex / Windrose, Junk
    Servant, Unknown Synchron, T.G. Striker ...), nor any card whose offer is a virtual record (the Dragon Rulers, Block Dragon).

    ONE front at that call site:  CPUL(side, cid) answers for the cids it knows (-1 = not mine); everyone else tails to the shared trampoline, which replays the
    native test and adds the registered cards -> the Elemental Lords (and the other trampoline cards) become CPU-playable with NO per-card code.
    CPUL itself covers Block Dragon (3 EARTH from hand+GY) and the four big Dragon Rulers Redox / Tidal / Blaster / Tempest (2 monsters of their attribute and/or Dragons).

    COST: a Special Summon that the CPU performs through the generic path pays NOTHING (a summon-procedure registry MISS = free).  Each customer therefore gets a
    summon-procedure registry row (0x0228F158, one phantom 0x02261F8D row dropped each) pointing at PAY, a private ov5 handler: a human seat returns done at once
    (it already paid through its own cls2 cost), a CPU seat banishes the cards itself, one per call.

    NOT covered: the Rulers' CPU summon does not stamp their once-per-turn flag; the Rulers' GY-origin summons are not offered through this hand loop.
    Evidence is CPU-vs-CPU only (not user-confirmed); the human paths are unchanged by construction (PAY returns 1 for a human).  SINGLE-CARD TEST: uv run python _build_cpu_hand_ss.py
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import Compiled
from otn_enhanced.effects import cave3
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import Checker, Ov, RAM_BASE as _RB, cave_holds
from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3

C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_cpu_hand_ss.nds"
BD = 0x0FDD

S = {n: getattr(O5, f"CAVE_CPUHS_{n}") for n in ("FRONT", "PAY", "LEGAL")}
RESERVE = {"FRONT": 0x40, "PAY": 0x1A0, "LEGAL": 0x140}


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


CPU_SITE, CPU_NATIVE = 0x02340F16, 0x0225E51C
CPU_TAIL = cave3.CAVE3_TGSH_SSTRAMP         # ov5 CPU hand-card loop: `bl 0x0225E51C(side, slot)`, r6 = the card's cid (live across the call)


def cpu_front() -> bytes:
    """The CPU's hand-SS legality call (r0 side, r6 cid live): CPUL(side, cid) -> -1 = not ours -> the shared hand-SS trampoline (native + tg table), else 0/1."""
    b = EffectBuilder()
    b.insn("LSL", "R2, R6, #0x12")
    b.insn("LSR", "R2, R2, #0x12")                  # r2 = cid (r6 is live across the call: the human hook's contract)
    b.insn("PUSH", "{R0, R1, LR}")
    b.insn("ADD", "R1, R2, #0x0")
    b.ldr_const(3, S["LEGAL"] | 1)
    b.insn("BLX", "R3")                             # CPUL(side, cid): -1 = not ours, else 0/1
    b.insn("ADD", "R2, R0, #0x0")
    b.insn("POP", "{R0, R1, R3}")
    b.insn("MOV", "LR, R3")
    b.insn("CMP", "R2, #0x0")
    b.insn("BLT", "tail")
    b.insn("ADD", "R0, R2, #0x0")
    b.insn("BX", "LR")
    b.label("tail")
    b.ldr_const(3, CPU_TAIL | 1)                    # everyone else: the shared hand-SS trampoline (native + tg table)
    b.insn("BX", "R3")
    return _asm(b, "FRONT")


REG_BASE, REG_COUNT = 0x0228F158, 133                               # summon-procedure registry {u32 cid, u32 handler}, sorted; one phantom row (handler 0x02261F8D) dropped per insert
REG_ROWS = ((BD, 0x0FDE), (0x17CD, 0x0E5C), (0x115F, 0x0E60), (0x1145, 0x112E), (0x1125, 0x128C))   # (cid, phantom dropped); Block Dragon + the four big Dragon Rulers
REC = 0x02298A28                                                    # summon record: +2 side, +0xE cid, +0x24 state


def pay_stub() -> bytes:
    """Registry handler (no args; 0 = call again, nonzero = done): a human returns done at once, the CPU pays the banish cost."""
    blob = compile_c(C_DIR / "cpu_hand_ss.c", S["PAY"], {"STUB": "PAY"})
    assert len(blob) <= RESERVE["PAY"], f"PAY: {len(blob):#x} B > {RESERVE['PAY']:#x}"
    return blob


@dataclass(frozen=True)
class cpu_pays_banish_cost_through_the_registry:
    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import insert_row_by_stride

        def _keys(buf):
            return [struct.unpack_from("<I", buf, REG_BASE - _RB + 8 * j)[0] for j in range(REG_COUNT)]

        def install(rom, view):
            for rcid, ph in REG_ROWS:
                insert_row_by_stride(view.buf, REG_BASE, 8, REG_COUNT, "<II", (rcid, S["PAY"] | 1), ph, f"registry {rcid:#06x}")

        def check(c, rom, view):
            keys = _keys(view.buf)
            c.ok(all(keys[j] < keys[j + 1] for j in range(REG_COUNT - 1)), "registry strictly sorted")
            for rcid, ph in REG_ROWS:
                i = keys.index(rcid)
                c.eq(struct.unpack_from("<II", view.buf, REG_BASE - _RB + 8 * i), (rcid, S["PAY"] | 1), f"registry row {rcid:#06x} -> CAVE_CPUHS_PAY")
                c.ok(ph not in keys, f"registry phantom {ph:#06x} dropped")

        return Compiled(((S["PAY"], pay_stub(), "CPU cost payment handler"),), (), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class cpu_hand_loop_asks_for_hand_special_summons:
    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.summon_trigger_hook import _bl
        blob = cpu_front()
        want = _bl(CPU_SITE, S["FRONT"])
        was = _bl(CPU_SITE, CPU_NATIVE)

        def install(rom, view):
            ov5 = O5._load_ov5_decompressed(rom)
            data = bytearray(ov5.data)
            o = CPU_SITE - O5.OV5_RAM_BASE
            assert bytes(data[o:o + 4]) in (was, want), f"ov5 {CPU_SITE:#x} is not the native `bl 0x0225E51C`"
            data[o:o + 4] = want
            O5._save_ov5(rom, ov5, bytes(data))

        def check(c, rom, view):
            o5 = O5._load_ov5_decompressed(rom).data
            o = CPU_SITE - O5.OV5_RAM_BASE
            c.eq(bytes(o5[o:o + 4]), want, f"CPU hand loop {CPU_SITE:#x} -> Block Dragon front")

        cpul = compile_c(C_DIR / "cpu_hand_ss.c", S["LEGAL"], {"STUB": "CPUL"})
        assert len(cpul) <= RESERVE["LEGAL"], f"CPUL: {len(cpul):#x} B > {RESERVE['CPUL']:#x}"
        return Compiled(((S["FRONT"], blob, "CPU hand-loop legality front"), (S["LEGAL"], cpul, "CPU legality (Block Dragon + big Rulers)")),
                        installs=(install,), checks=(check,))



# --- build / verify (a card-less module: no stats or text to write) ----------------------------------------------------------------
def _compiled(view) -> Compiled:
    parts = [cpu_hand_loop_asks_for_hand_special_summons().compile(view, BD), cpu_pays_banish_cost_through_the_registry().compile(view, BD)]
    return Compiled(tuple(s for p in parts for s in p.stubs), (), installs=tuple(f for p in parts for f in p.installs),
                    checks=tuple(f for p in parts for f in p.checks))


def main(write_text: bool = False, src: str = CHAIN, out: str = OUT) -> None:
    rom, ovb = load_overlay3(src)
    view = Ov(bytearray(ovb))
    compiled = _compiled(view)
    for addr, blob, _ in compiled.stubs:
        O5.install_cave(rom, addr, blob, reserve=len(blob))
    for fn in compiled.installs:
        fn(rom, view)
    save_overlay3(rom, bytes(view.buf), out)


def verify(out: str = OUT) -> bool:
    import ndspy.rom
    c = Checker(f"cpu_hand_ss ({out})")
    c.out = out
    rom, ovb = load_overlay3(out)
    view = Ov(bytearray(ovb))
    compiled = _compiled(view)
    ov5_view = Ov(bytes(ndspy.rom.NintendoDSRom.fromFile(out).loadArm9Overlays([O5.OV5_ID])[O5.OV5_ID].data), base=O5.OV5_RAM_BASE)
    for addr, blob, what in compiled.stubs:
        cave_holds(c, ov5_view, addr, blob, what)
    for fn in compiled.checks:
        fn(c, rom, view)
    return c.result()

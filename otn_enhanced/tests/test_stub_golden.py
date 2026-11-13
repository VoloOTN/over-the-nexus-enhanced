"""Does ThumbAssembler reproduce the text assembler's bytes, and are existing builder cards unaffected?

    uv run python -m otn_enhanced.tests.test_stub_golden

`golden_asm.json.gz` holds every `thumb_asm.asm()` call made during a full build: its caller, real slot address,
resolved text and emitted bytes (captured with `tools/asm_capture.py`). The contract for the EffectBuilder port is
that `assemble(base, pad="nop")` of the translated program equals those bytes.

Plain asserts, no framework.
"""
from __future__ import annotations

import os

from otn_enhanced.asm.effect_shim import ThumbAssembler
from otn_enhanced.asm.thumb_asm import asm
from otn_enhanced.tools.asm_probe import classify, load_calls

GOLDEN = os.path.join(os.path.dirname(__file__), "golden_asm.json.gz")


def test_builder_reproduces_every_captured_block() -> None:
    """All captured blocks, at their real slot addresses, byte for byte."""
    calls = load_calls(GOLDEN)
    bad = []
    for r in calls:
        kind, detail = classify(r)
        if kind != "identical":
            bad.append(f"{r['module'].split('.')[-1]}.{r['func']} @0x{r['base']:08X}: {kind} {detail}")
    assert not bad, f"{len(bad)} of {len(calls)} blocks differ:\n  " + "\n  ".join(bad[:10])
    assert len(calls) >= 500, f"golden file shrank to {len(calls)} blocks"


def _pool_program() -> ThumbAssembler:
    a = ThumbAssembler()
    a.ldr_const(0, 0x12345678)
    a.insn("MOV", "R0, #0x1")
    a.insn("MOV", "R1, #0x2")
    return a


def test_default_layout_is_unchanged() -> None:
    """The opt-in must stay opt-in: cards already on the builder pad with zeros and need a 4-aligned base."""
    got = _pool_program().assemble(0x0239A000)
    want = bytes.fromhex("0148" "0120" "0221" "0000" "78563412")      # ldr; movs; movs; 0000 pad; pool
    assert got == want, (got.hex(), want.hex())

    no_pool = ThumbAssembler().insn("MOV", "R0, #0x1").insn("MOV", "R1, #0x2").insn("MOV", "R2, #0x3")
    assert len(no_pool.assemble(0x0239A000)) == 6, "default mode must not add trailing padding"

    try:
        no_pool.assemble(0x0239A002)
    except ValueError:
        pass
    else:
        raise AssertionError("default mode accepted a halfword-aligned base")


def test_nop_mode_matches_the_text_assembler() -> None:
    """Padding is nop, always to a 4-byte boundary of the real address, including with no pool."""
    text = "movs r0,#1\nmovs r1,#2\nmovs r2,#3"
    prog = ThumbAssembler().insn("MOV", "R0, #0x1").insn("MOV", "R1, #0x2").insn("MOV", "R2, #0x3")
    # 6 bytes of code: a 4-aligned base needs a pad to reach the next boundary, a 2-mod-4 base already ends on one.
    for base, padded in ((0x0239A000, True), (0x0239A002, False)):
        got, want = prog.assemble(base, pad="nop"), asm(base, text)
        assert got == want, (hex(base), got.hex(), want.hex())
        assert got.endswith(b"\xc0\x46") == padded and len(got) == (8 if padded else 6), (hex(base), got.hex())


def test_bl_label_matches_the_text_assembler() -> None:
    text = "push {r4,lr}\nbl helper\npop {r4,pc}\nhelper:\nmovs r0,#0\nbx lr"
    prog = ThumbAssembler()
    prog.insn("PUSH", "{R4, LR}").bl_label("helper").insn("POP", "{R4, PC}")
    prog.label("helper").insn("MOV", "R0, #0x0").insn("BX", "LR")
    for base in (0x0221B4A0, 0x021B594A):
        got, want = prog.assemble(base, pad="nop"), asm(base, text)
        assert got == want, (hex(base), got.hex(), want.hex())


def test_bl_label_rejects_unknown_label() -> None:
    try:
        ThumbAssembler().bl_label("nowhere").assemble(0x0239A000)
    except ValueError as e:
        assert "nowhere" in str(e)
    else:
        raise AssertionError("an undefined label was accepted")


QUERY_LIT, POST_LIT = 0x021A14E9, 0x021D2585          # turnlog_query / turnlog_post | 1, as stubs write them


def _same_as_text(prog, text, bases=(0x0221B4A0, 0x021B594A)) -> None:
    for base in bases:
        got, want = prog.assemble(base, pad="nop"), asm(base, text)
        assert got == want, (hex(base), got.hex(), want.hex())


def test_turnlog_idioms_match_real_windows() -> None:
    """The shapes mined from the golden blocks (57, 35, ... sites each), rebuilt with the idioms."""
    from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R4, R5, R6, R7

    def build(desc, fn):
        b = EffectBuilder()
        b.ctx_field("controller", dest=R0, ctx=desc)
        fn(b)
        return b

    # query, side from the descriptor in R4, scratch R5 (57 sites)
    _same_as_text(build(R4, lambda b: b.turnlog_query(R0, 0x1234, 1, via=R5)),
                  f"ldrb r0,[r4,#2]\nmovs r1,#0xb\nldr r2,=0x1234\nmovs r3,#1\nldr r5,={QUERY_LIT:#x}\nblx r5")
    # the same with the descriptor in R5, scratch R4
    _same_as_text(build(R5, lambda b: b.turnlog_query(R0, 0x1234, 1, via=R4)),
                  f"ldrb r0,[r5,#2]\nmovs r1,#0xb\nldr r2,=0x1234\nmovs r3,#1\nldr r4,={QUERY_LIT:#x}\nblx r4")
    # kind 5, and a side that is a register move rather than a field load
    _same_as_text(build(R4, lambda b: b.turnlog_query(R0, 0x1234, 5, via=R5)),
                  f"ldrb r0,[r4,#2]\nmovs r1,#0xb\nldr r2,=0x1234\nmovs r3,#5\nldr r5,={QUERY_LIT:#x}\nblx r5")
    b = EffectBuilder()
    b.turnlog_query(R7, 0x1234, 1, via=R5)
    _same_as_text(b, f"adds r0,r7,#0\nmovs r1,#0xb\nldr r2,=0x1234\nmovs r3,#1\nldr r5,={QUERY_LIT:#x}\nblx r5")

    # post, cid a literal (35 sites)
    _same_as_text(build(R4, lambda b: b.turnlog_post(R0, 0x1234, 1, via=R5)),
                  f"ldrb r0,[r4,#2]\nldr r1,=0x1234\nmovs r2,#1\nmovs r3,#0\nldr r5,={POST_LIT:#x}\nblx r5")
    # post, cid read from the descriptor
    def from_desc(b):
        b.ctx_field("cid", dest=R1, ctx=R4)
        b.turnlog_post(R0, R1, 1, via=R6)
    _same_as_text(build(R4, from_desc),
                  f"ldrb r0,[r4,#2]\nldrh r1,[r4]\nmovs r2,#1\nmovs r3,#0\nldr r6,={POST_LIT:#x}\nblx r6")


def test_call_via_rejects_a_clobbering_register() -> None:
    """The literal call register must sit above the argument registers."""
    from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R2
    try:
        EffectBuilder().call_addr(0x021D12F4, R0, 1, via=R2)       # 2 args use R0,R1; R2 is fine
        EffectBuilder().call_addr(0x021D12F4, R0, 1, 2, via=R2)    # 3 args use R0..R2; R2 would clobber arg 2
    except ValueError as e:
        assert "clobber" in str(e)
    else:
        raise AssertionError("via overlapping an argument register was accepted")


def test_large_immediate_goes_through_the_pool() -> None:
    """cids do not fit a MOV immediate; the real stubs load them with `ldr rN,=cid`."""
    from otn_enhanced.asm.effect_builder import EffectBuilder
    b = EffectBuilder()
    b.call_addr(0x021D12F4, 0x1234, 7)
    _same_as_text(b, "ldr r0,=0x1234\nmovs r1,#7\nbl 0x21d12f4")


def test_ported_stubs_match_their_golden_bytes() -> None:
    """A card ported onto the builder must emit the bytes it emitted before, at every slot home.

    `golden_ported.json` is captured BEFORE a stub is ported (module, builder function, slot address, bytes).
    """
    import importlib
    import json
    rows = json.load(open(os.path.join(os.path.dirname(__file__), "golden_ported.json"), encoding="utf-8"))
    bad = []
    for r in rows:
        got = getattr(importlib.import_module(r["module"]), r["func"])(r["base"]).hex()
        if got != r["hex"]:
            bad.append(f"{r['module'].split('.')[-1]}.{r['func']} @0x{r['base']:08X}")
    assert not bad, f"{len(bad)} ported stub(s) changed bytes: {bad}"
    assert len(rows) >= 6


def _registry_disagreements(records: dict[int, str]) -> list[str]:
    """Names in `records` (addr -> name) that differ from the builder's table or the curated proven table."""
    from otn_enhanced.asm.effect_builder import PRIMITIVES
    from otn_enhanced.tools.effect_registry.primitive_names import _PROVEN
    want = {p.addr: name for name, p in PRIMITIVES.items()}
    want.update({addr: name for addr, (name, _sig) in _PROVEN.items()})
    return [f"0x{a:08X}: registry says {records[a]!r}, expected {n!r}"
            for a, n in sorted(want.items()) if a in records and records[a] != n]


def test_registry_names_agree_with_the_builder_and_proven_table() -> None:
    """The effect registry is a navigator; a wrong name there sends a session after the wrong routine."""
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "tools", "effect_registry", "data", "primitives.json")
    records = {r["addr"]: r["name"] for r in json.load(open(path, encoding="utf-8"))}
    bad = _registry_disagreements(records)
    assert not bad, "registry names disagree:\n  " + "\n  ".join(bad)

    # negative control: a wrong name in the data must be reported, or this test proves nothing
    assert _registry_disagreements({0x021D2584: "special_summon_from_deck"}), "the check cannot fail"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

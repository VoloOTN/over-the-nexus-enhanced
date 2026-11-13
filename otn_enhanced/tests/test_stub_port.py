"""Does tools/stub_port convert text-assembler blocks without moving a byte?

    uv run python -m otn_enhanced.tests.test_stub_port

Converts a small synthetic module, runs the original and the converted source at several bases (including a
halfword-aligned one), and compares the bytes. Plain asserts, no framework.
"""
from __future__ import annotations

from otn_enhanced.tools.stub_port import convert_source

SRC = '''
from otn_enhanced.asm.thumb_asm import asm

K = 0x1234
G = 0x021F06E8
N = 5
SPLICE = "movs r0,#0"


def query(base):
    return asm(base, f"""
        push {{r4,lr}}
        adds r4,r0,#0
        ldrb r0,[r4,#2]
        movs r1,#0xb
        ldr  r2,=0x{K:X}
        movs r3,#1
        ldr  r5,=0x21a14e9
        blx  r5
        cmp  r0,#0
        beq  no
        adds r0,r4,#0
        bl   0x{G:08X}
        pop  {{r4,pc}}
      no:
        movs r0,#0
        pop  {{r4,pc}}
    """)


def post(base):
    blob = asm(base, f"""
        push {{r4,lr}}
        adds r4,r0,#0
        ldrb r0,[r4,#2]
        ldrh r1,[r4]
        movs r2,#{N}
        movs r3,#0
        ldr  r6,=0x21d2585
        blx  r6
        pop  {{r4,pc}}
    """)
    return blob


def local_call(base):
    return asm(base, """
        push {lr}
        bl   helper
        pop  {pc}
      helper:
        movs r0,#7
        bx   lr
    """)


LOCK = """
    push {lr}
    movs r0,#9
    pop  {pc}
"""


def lit_call(base):
    return asm(base, f"""
        push {{r4,lr}}
        adds r4,r0,#0
        ldrb r0,[r4,#2]
        movs r1,#2
        ldr  r5,=0x21d12f5
        blx  r5
        adds r0,r4,#0
        movs r1,#5
        ldr  r2,=0x{K:X}
        ldr  r3,=0x{G:08X}
        blx  r3
        bl   0x{G:08X}
        pop  {{r4,pc}}
    """)


def hex_immediate(base):
    return asm(base, f"""
        push {{lr}}
        movs r2,#0x{N:X}
        movs r1,#{N}
        pop  {{pc}}
    """)


def local_text(base):
    text = f"""
        push {{lr}}
        movs r0,#{N}
        pop  {{pc}}
    """
    return asm(base, text)


def module_text(base):
    return asm(base, LOCK)


def spliced(base):
    return asm(base, f"""
        push {{lr}}
        {SPLICE}
        pop {{pc}}
    """)
'''

BASES = (0x0239A000, 0x0221B4A0, 0x021B594A)


def _run(src: str) -> dict:
    ns: dict = {}
    exec(compile(src, "<synthetic>", "exec"), ns)
    return ns


def test_converted_functions_emit_identical_bytes() -> None:
    old = _run(SRC)
    new_src, results = convert_source(SRC, old)
    new = _run(new_src)
    for fn in ("query", "post", "local_call", "local_text", "module_text", "hex_immediate", "lit_call"):
        for base in BASES:
            assert new[fn](base) == old[fn](base), (fn, hex(base))


def test_turn_log_shapes_become_idiom_calls() -> None:
    old = _run(SRC)
    new_src, results = convert_source(SRC, old)
    assert "b.turnlog_query(R0, K, 1, via=R5)" in new_src, new_src
    assert "b.turnlog_post(R0, R1, N, via=R6)" in new_src, new_src
    assert new_src.count("b.turnlog_") == 2


def test_unconvertible_blocks_are_skipped_with_a_reason() -> None:
    old = _run(SRC)
    new_src, results = convert_source(SRC, old)
    by = {r.func: r for r in results}
    assert by["spliced"].ok is False and "splices" in by["spliced"].reason, by["spliced"]
    assert all(by[f].ok for f in ("query", "post", "local_call", "local_text", "module_text", "hex_immediate", "lit_call"))
    assert "asm(base" in new_src                                  # the skipped block is left as it was
    assert new_src.count("pad=\"nop\"") == 7


def test_text_variables_resolve_through_their_assignment() -> None:
    old = _run(SRC)
    new_src, results = convert_source(SRC, old)
    body = new_src[new_src.index("def local_text"):new_src.index("def module_text")]
    assert "text = f" not in body, "the local text variable's assignment should be removed"
    assert 'LOCK = """' in new_src, "a module-level constant must be kept (others may import it)"
    by = {r.func: r for r in results}
    assert "LOCK" in by["module_text"].note and not by["local_text"].note


def test_literal_calls_become_call_and_call_addr() -> None:
    """`[arg setup] ldr rN,=ADDR ; blx rN` and a bare `bl ADDR`, with a primitive name when one matches."""
    old = _run(SRC)
    new_src, _ = convert_source(SRC, old)
    body = new_src[new_src.index("def lit_call"):new_src.index("def hex_immediate")]
    assert 'b.call("draw", R0, 2, via=R5)' in body, body          # R0 was set by the ldrb before it: passed as itself
    assert "b.call_addr(G, R4, 5, K, via=R3, arm=True)" in body, body   # 0x021F06E8 is even: an ARM target
    assert "b.call_addr(G)" in body, body                           # direct bl, no arguments
    assert "ldr_const" not in body and '"BLX"' not in body, body


def test_unused_registers_are_not_imported() -> None:
    old = _run(SRC)
    new_src, _ = convert_source(SRC, old)
    imp = next(l for l in new_src.splitlines() if l.startswith("from otn_enhanced.asm.effect_builder import"))
    assert imp.endswith("EffectBuilder, R0, R1, R3, R4, R5, R6"), imp      # R2 and R7 are never named, so not imported


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

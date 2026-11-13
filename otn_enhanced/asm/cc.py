"""Compile a C effect stub to a flat Thumb-1 blob linked at its slot address.

    blob = compile_c(Path("otn_enhanced/cards/c/mystic_piper.c"), cave3.CAVE3_PIPER_RES)

The blob goes wherever an EffectBuilder blob goes; table rows and hooks are unchanged. Engine routines come
from ``c/engine_syms.txt`` (one per line: ``addr name kind kb_fact_id``), each declared with ``.thumb_set``
so the compiler emits a direct Thumb ``BL`` (a plain absolute symbol would make the linker pick an ARM-state
BLX, which freezes). A symbol is refused unless its KB fact exists and is graded VERIFIED or ANCHORED.

The ``.thumb_set`` symbol file is the approach of CardWorkshop's tools/inject.py (write_engine_ld),
Copyright (c) 2026 BlueKitkallos, MIT License.

    uv run python -m otn_enhanced.asm.cc      # self-check (needs the toolchain)
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from otn_enhanced.asm.effect_verify import assert_thumb1_only

HERE = Path(__file__).resolve().parent
C_DIR = HERE / "c"
SYMS = C_DIR / "engine_syms.txt"
KB = HERE.parent / "docs" / "engine"
TOOLCHAIN = Path(os.environ.get("ARM_TOOLCHAIN", Path.home() / "tools" / "arm-gnu-toolchain" / "bin"))
GCC_VERSION = "14.2.Rel1"   # pinned: a different compiler changes the bytes, and with them every baseline sha256
CFLAGS = ["-mcpu=arm946e-s", "-mthumb", "-mthumb-interwork", "-Os", "-ffreestanding", "-nostdlib", "-fno-builtin",
          "-fno-pic", "-ffunction-sections", "-fdata-sections", "-Wall", "-Werror", "-std=gnu11"]
_LD = """\
ENTRY(entry)
SECTIONS
{{
  . = 0x{start:08X};
  .text : {{ {pad}KEEP(*(.text.entry)) *(.text*) *(.rodata*) }}
  .data : {{ *(.data*) *(.bss*) *(COMMON) }}
  ASSERT(SIZEOF(.data) == 0, "C stubs cannot have mutable globals or statics: nothing initialises them")
  /DISCARD/ : {{ *(.ARM.*) *(.comment) *(.note*) }}
}}
"""


class CcError(Exception):
    pass


def _tool(name: str) -> str:
    exe = TOOLCHAIN / (f"arm-none-eabi-{name}.exe" if os.name == "nt" else f"arm-none-eabi-{name}")
    if not exe.exists():
        raise CcError(f"{exe} not found: install Arm GNU Toolchain {GCC_VERSION} or set ARM_TOOLCHAIN to its bin")
    return str(exe)


def _run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise CcError(f"{' '.join(cmd)}\n{r.stdout}{r.stderr}")
    return r.stdout


def _proven_ids() -> set[str]:
    ids, cur = set(), None
    for p in KB.glob("*.yaml"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if m := re.match(r'- id: "(.+)"', line):
                cur = m.group(1)
            elif cur and (m := re.match(r'  confidence: "(\w+)"', line)) and m.group(1) in ("VERIFIED", "ANCHORED"):
                ids.add(cur)
    return ids


def _engine_syms_asm() -> str:
    proven = _proven_ids()
    out = ["    .syntax unified\n"]
    for line in SYMS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        addr, name, kind, fact = line.split()[:4]
        if ".c_midfn_" in fact:
            raise CcError(f"engine_syms.txt: {name} cites {fact}, a mid-function point: not callable from C")
        if fact not in proven:
            raise CcError(f"engine_syms.txt: {name} cites {fact}, which is not a VERIFIED/ANCHORED KB fact")
        if kind != "t":
            raise CcError(f"engine_syms.txt: {name} kind {kind!r}; only Thumb functions ('t') are supported")
        out.append(f"    .global {name}\n    .thumb_set {name}, 0x{int(addr, 16) | 1:08X}\n")
    # Our own stubs: every ledger slot is callable as slot_<NAME> (declare the prototype in engine.h's slot section).
    from otn_enhanced.tools.c_corpus import slot_symbols
    for name, addr in slot_symbols().items():
        out.append(f"    .global slot_{name}\n    .thumb_set slot_{name}, 0x{addr | 1:08X}\n")
    return "".join(out)


def compile_c(src: Path | list[Path], base: int, defines: dict | None = None) -> bytes:
    """-> the stub's bytes, linked so that its ``entry`` function starts at *base* (4-aligned).

    *src* is one file or several; ``.c`` and ``.S`` mix freely. A ``.S`` entry goes in section ``.text.entry``
    as a global ``.thumb_func`` named ``entry``; place its pools with explicit ``.ltorg``.
    """
    srcs = [src] if isinstance(src, Path) else list(src)
    assert base % 2 == 0, "Thumb stubs start 2-aligned"
    # A 2-aligned slot is linked at base-2 behind a 2-byte pad (stripped below), so literal pools keep their
    # absolute 4-alignment (ldr rX,[pc,#imm] uses pc & ~3) and the entry still lands exactly at base.
    pad = base % 4
    if GCC_VERSION not in _run([_tool("gcc"), "--version"]):
        raise CcError(f"arm-none-eabi-gcc is not {GCC_VERSION}; the pin keeps ROM hashes reproducible")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "engine_syms.S").write_text(_engine_syms_asm(), encoding="utf-8")
        (t / "link.ld").write_text(_LD.format(start=base - pad, pad="SHORT(0) " if pad else ""), encoding="utf-8")
        gcc = [_tool("gcc"), *CFLAGS, "-I", str(C_DIR), *(f"-D{k}={v}" for k, v in (defines or {}).items())]
        objs = [t / f"src{i}.o" for i in range(len(srcs))] + [t / "syms.o"]
        for s, o in zip([*srcs, t / "engine_syms.S"], objs):
            _run([*gcc, "-c", str(s), "-o", str(o)])
        _run([*gcc, "-T", str(t / "link.ld"), "-Wl,--gc-sections", *map(str, objs), "-lgcc", "-o", str(t / "stub.elf")])
        syms = {f[2]: int(f[0], 16) for f in (l.split() for l in _run([_tool("nm"), str(t / "stub.elf")]).splitlines())
                if len(f) == 3}
        if syms.get("entry", 0) & ~1 != base:
            raise CcError(f"entry is not at 0x{base:08X}: mark it ENTRY (section .text.entry)")
        _run([_tool("objcopy"), "-O", "binary", "-j", ".text", str(t / "stub.elf"), str(t / "stub.bin")])
        blob = (t / "stub.bin").read_bytes()[pad:]
    assert_thumb1_only(blob, base)
    return blob


if __name__ == "__main__":
    from otn_enhanced.asm.thumb_disasm import decode_thumb
    with tempfile.TemporaryDirectory() as tmp:
        ok = Path(tmp) / "ok.c"
        ok.write_text('#include "engine.h"\nENTRY int entry(EffectCtx *e) { draw(e->controller, 1); return 0; }\n')
        base = 0x02220BE4
        blob = compile_c(ok, base)
        bls = [i.branch_target for i in decode_thumb(blob, base) if i.mnemonic == "BL"]
        assert bls == [0x021D12F4], f"expected one BL to draw, got {[hex(b) for b in bls]}"
        bad = Path(tmp) / "bad.c"
        bad.write_text('#include "engine.h"\nint n;\nENTRY int entry(EffectCtx *e) { return n++; }\n')
        try:
            compile_c(bad, base)
            raise AssertionError("a mutable global was accepted")
        except CcError:
            pass
        # .S path: exact bytes, explicit pool, engine symbol resolves to a Thumb BL
        asm = Path(tmp) / "ok.S"
        asm.write_text("    .syntax unified\n    .thumb\n    .section .text.entry\n    .global entry\n"
                       "    .thumb_func\nentry:\n    push {r4, lr}\n    ldr r0, =0x12345678\n    bl draw\n"
                       "    pop {r4, pc}\n    .ltorg\n")
        sb = compile_c(asm, base)
        assert sb[:4] == bytes.fromhex("10b50248"), sb.hex()          # push {r4,lr}; ldr r0,[pc,#8]
        assert sb[8:10] == bytes.fromhex("10bd") and sb[12:16] == (0x12345678).to_bytes(4, "little"), sb.hex()
        assert [i.branch_target for i in decode_thumb(sb, base) if i.mnemonic == "BL"] == [0x021D12F4]
        # mixed: .S entry calling a C helper
        (Path(tmp) / "h.c").write_text('#include "engine.h"\nvoid helper(int x) { draw(x, 1); }\n')
        asm.write_text(asm.read_text().replace("bl draw", "bl helper"))
        compile_c([asm, Path(tmp) / "h.c"], base)
    print(f"cc self-check OK ({len(blob)} B stub, BL -> 0x021D12F4)")

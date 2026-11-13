"""Re-emit a decompiled Thumb-1 card-effect handler as relocatable bytes.

This is the bridge between the *reading* pipeline (``effect_extract`` /
``effect_decompile``) and the *writing* idiom used by the finished patches
(``mystic_piper._build_stub`` + ``boggart_knight._thumb_bl``).

A :class:`StubBuilder` records a handler as a sequence of operations:

* ``hw(u16)``   — a raw little-endian halfword (verbatim ISA bits).
* ``bl(target)``/``blx(target)`` — a 32-bit Thumb call, re-encoded for the
  build address so the stub is **relocatable**.
* ``pool(u32)`` — a 32-bit literal-pool word.

``build(base)`` lays the bytes out at *base* and re-encodes every call:

* ``build(orig_addr)`` reproduces the original overlay bytes exactly.
* ``build(other)`` is a relocated copy whose calls still reach the same
  engine primitives — ready to drop into the overlay-5 cave.

Only ``BL``/``BLX`` need re-encoding; every other instruction is
PC-relative-rigid (intra-function ``Bcc``/``B`` and ``[pc, #imm]`` pool
loads move as a block) and is emitted verbatim, which is byte-exact by
construction.

For *authoring* new effects, :class:`ThumbAssembler` provides a label-aware
layer on top of ``StubBuilder``: text instructions, named branch targets, an
auto-managed literal pool (``ldr_const``), and relocatable ``bl``/``blx`` — so
a custom resolver reads as code rather than a halfword list.
"""

from __future__ import annotations

import bisect
import struct

from otn_enhanced.asm.thumb_disasm import decode_thumb, encode_thumb_line, pool_start_index, ThumbInsn
from otn_enhanced.tools.effect_extract import (
    RAM_BASE,
    HANDLER_TABLE_OFFSET,
    HANDLER_ENTRY_SIZE,
    HANDLER_ENTRY_COUNT,
    detect_function_size,
)

# Thumb BL/BLX reach: ±4 MB, encoded as a signed 22-bit halfword displacement.
_BL_RANGE = 1 << 22


def _bl(runtime: int, target: int) -> bytes:
    """Encode a 32-bit Thumb-1 ``BL`` from *runtime* to *target*.

    *runtime* is the address of the first halfword of the instruction; the
    program counter when the offset is applied is ``runtime + 4``.
    """
    off = target - (runtime + 4)
    if off & 1:
        raise ValueError(f"BL target not halfword-aligned: 0x{target:08X}")
    if not -_BL_RANGE <= off < _BL_RANGE:
        raise ValueError(f"BL out of range: 0x{runtime:08X} -> 0x{target:08X}")
    hi = 0xF000 | ((off >> 12) & 0x7FF)
    lo = 0xF800 | ((off >> 1) & 0x7FF)
    return struct.pack("<HH", hi, lo)


def _blx(runtime: int, target: int) -> bytes:
    """Encode a 32-bit Thumb-1 ``BLX`` (Thumb→ARM) from *runtime* to *target*.

    The ARM target is word-aligned and the offset is relative to
    ``Align(runtime + 4, 4)`` — unlike ``BL``, which uses ``runtime + 4``.
    Relocating by a multiple of 4 preserves the target; all handler bases are
    4-aligned, so a relocated copy reaches the same primitive.
    """
    if target & 3:
        raise ValueError(f"BLX ARM target not word-aligned: 0x{target:08X}")
    off = target - ((runtime + 4) & ~3)
    if not -_BL_RANGE <= off < _BL_RANGE:
        raise ValueError(f"BLX out of range: 0x{runtime:08X} -> 0x{target:08X}")
    hi = 0xF000 | ((off >> 12) & 0x7FF)
    lo = 0xE800 | ((off >> 1) & 0x7FF)
    return struct.pack("<HH", hi, lo)


class StubBuilder:
    """Accumulates a relocatable Thumb-1 routine, mirroring ``_build_stub``."""

    def __init__(self) -> None:
        # Each op is (kind, value): kind in {"hw", "bl", "blx", "pool"}.
        self._ops: list[tuple[str, int]] = []
        self._comments: list[str] = []

    # -- recording --------------------------------------------------------
    def hw(self, value: int, comment: str = "") -> "StubBuilder":
        """Append a raw little-endian halfword (verbatim instruction bits)."""
        self._ops.append(("hw", value & 0xFFFF))
        self._comments.append(comment)
        return self

    def bl(self, target: int, comment: str = "") -> "StubBuilder":
        """Append a 32-bit ``BL`` to the absolute *target* (re-encoded on build)."""
        self._ops.append(("bl", target))
        self._comments.append(comment)
        return self

    def blx(self, target: int, comment: str = "") -> "StubBuilder":
        """Append a 32-bit ``BLX`` to the absolute ARM *target*."""
        self._ops.append(("blx", target))
        self._comments.append(comment)
        return self

    def pool(self, value: int, comment: str = "") -> "StubBuilder":
        """Append a 32-bit literal-pool word (must land 4-aligned)."""
        self._ops.append(("pool", value & 0xFFFFFFFF))
        self._comments.append(comment)
        return self

    # -- source rendering -------------------------------------------------
    def render_python(self, var: str = "s",
                      resolve_call=None) -> list[str]:
        """Render the recorded ops as ``var.hw(...)`` / ``.bl(...)`` source lines.

        *resolve_call*, if given, is ``callable(target_addr) -> str | None``; a
        non-empty return is appended to a ``bl``/``blx`` op's comment so the
        line shows the called routine's name (e.g. ``-> draw``) rather than only
        its address.
        """
        lines: list[str] = []
        for (kind, value), comment in zip(self._ops, self._comments):
            note = comment
            if kind == "hw":
                call = f"{var}.hw(0x{value:04X})"
            elif kind == "pool":
                call = f"{var}.pool(0x{value:08X})"
            else:  # bl / blx
                call = f"{var}.{kind}(0x{value:08X})"
                if resolve_call is not None:
                    name = resolve_call(value)
                    if name:
                        note = f"{comment} -> {name}" if comment else f"-> {name}"
            lines.append(f"    {call}{f'  # {note}' if note else ''}")
        return lines

    # -- layout -----------------------------------------------------------
    @staticmethod
    def _op_size(kind: str) -> int:
        return 2 if kind == "hw" else 4

    @property
    def size(self) -> int:
        """Total encoded length in bytes."""
        return sum(self._op_size(kind) for kind, _ in self._ops)

    def build(self, base: int, *, halfword_base: bool = False) -> bytes:
        """Encode the routine for a runtime start address of *base*.

        *base* must be 4-aligned so ``BLX`` alignment and ``pool`` word
        alignment are preserved relative to the original function.
        *halfword_base* relaxes that to 2-aligned; pool words must still land 4-aligned.
        """
        if base & (1 if halfword_base else 3):
            raise ValueError(f"stub base must be {'2' if halfword_base else '4'}-aligned: 0x{base:08X}")
        out = bytearray()
        for kind, value in self._ops:
            runtime = base + len(out)
            if kind == "hw":
                out += struct.pack("<H", value)
            elif kind == "bl":
                out += _bl(runtime, value)
            elif kind == "blx":
                out += _blx(runtime, value)
            else:  # pool
                if runtime & 3:
                    raise ValueError(
                        f"pool word not 4-aligned at 0x{runtime:08X}")
                out += struct.pack("<I", value)
        return bytes(out)


class ThumbAssembler:
    """Label-aware Thumb-1 assembler that lowers onto :class:`StubBuilder`.

    This is the writable counterpart to the byte-level ``StubBuilder``: instead
    of hand-picking opcodes and computing branch offsets, you write text
    instructions, name branch targets with :meth:`label`, load 32-bit constants
    with :meth:`ldr_const` (the literal pool is laid out automatically), and
    emit calls with :meth:`bl` / :meth:`blx`.

    ``assemble(base)`` runs two passes — assign every item a byte offset, then
    encode — and produces the same relocatable bytes as the equivalent
    ``StubBuilder``: ``assemble(orig) == original`` and ``assemble(other)``
    differs only in ``BL``/``BLX`` bytes.

    Everything except ``BL``/``BLX`` is PC-relative-rigid (branches and
    ``LDR [PC, #imm]`` move as a block), so those are encoded once at their
    final offset; only the calls are re-encoded per build address.
    """

    def __init__(self) -> None:
        # Items: ("insn", mnemonic, ops) | ("label", name) | ("bl"/"blx", target)
        #        | ("ldrc", rd, const) | ("raw", u16) | ("word", u32)
        self._items: list[tuple] = []
        self._consts: list[int] = []   # ordered, de-duplicated pool constants

    # -- recording --------------------------------------------------------
    def insn(self, mnemonic: str, operands: str = "") -> "ThumbAssembler":
        """Append a 16-bit Thumb instruction.

        Branch operands may reference a :meth:`label` name; it is resolved to
        an absolute address at assemble time (e.g. ``insn("BEQ", "done")``).
        """
        self._items.append(("insn", mnemonic, operands))
        return self

    def label(self, name: str) -> "ThumbAssembler":
        """Mark the current position with a named branch target."""
        self._items.append(("label", name))
        return self

    def bl(self, target: int) -> "ThumbAssembler":
        """Append a relocatable 32-bit ``BL`` to absolute *target*."""
        self._items.append(("bl", target))
        return self

    def blx(self, target: int) -> "ThumbAssembler":
        """Append a relocatable 32-bit ``BLX`` to absolute ARM *target*."""
        self._items.append(("blx", target))
        return self

    def bl_label(self, name: str) -> "ThumbAssembler":
        """Append a ``BL`` to a local :meth:`label` (resolved at assemble time).

        Like the text assembler's ``bl name``: it clobbers LR, so use it only once LR is saved.
        """
        self._items.append(("bllabel", name))
        return self

    def ldr_const(self, rd: int, value: int) -> "ThumbAssembler":
        """Load a 32-bit *value* into ``Rd`` via the auto-managed literal pool."""
        if value not in self._consts:
            self._consts.append(value)
        self._items.append(("ldrc", rd, value))
        return self

    def raw(self, value: int) -> "ThumbAssembler":
        """Append a verbatim 16-bit halfword (escape hatch for exotic encodings)."""
        self._items.append(("raw", value & 0xFFFF))
        return self

    # -- layout helpers ---------------------------------------------------
    @staticmethod
    def _item_size(item: tuple) -> int:
        kind = item[0]
        if kind == "label":
            return 0
        if kind in ("bl", "blx", "bllabel"):
            return 4
        return 2   # insn, ldrc, raw

    def _layout(self) -> tuple[list[tuple[int, tuple]], dict[str, int], int]:
        """Pass 1: assign a byte offset to every item and locate labels.

        Returns ``(positioned_items, label_offsets, code_end)`` where
        *code_end* is the byte offset just past the last item.
        """
        positioned: list[tuple[int, tuple]] = []
        labels: dict[str, int] = {}
        off = 0
        for item in self._items:
            if item[0] == "label":
                if item[1] in labels:
                    raise ValueError(f"duplicate label: {item[1]!r}")
                labels[item[1]] = off
            positioned.append((off, item))
            off += self._item_size(item)
        return positioned, labels, off

    def to_builder(self, base: int, pad: str = "zero") -> StubBuilder:
        """Lower the program to a :class:`StubBuilder` for runtime start *base*.

        Branch and pool-load instructions are encoded against *base* (they are
        base-independent in byte terms once laid out); ``bl``/``blx`` become
        relocatable builder ops.  ``assemble`` is the usual entry point.

        *pad* selects the layout rules:

        * ``"zero"`` (default): *base* must be 4-aligned; the pool is aligned by a ``0x0000``
          halfword, and only when there are constants. This is what existing builder cards ship.
        * ``"nop"``: byte-for-byte what :func:`thumb_asm.asm` emits. *base* may be 2-aligned; the
          code is always padded to a 4-byte boundary of the REAL address with ``nop`` (``0x46C0``),
          even with no pool, then the pool follows.
        """
        if pad not in ("zero", "nop"):
            raise ValueError(f"pad must be 'zero' or 'nop', not {pad!r}")
        if base & (1 if pad == "nop" else 3):
            raise ValueError(f"assembler base must be {'2' if pad == 'nop' else '4'}-aligned: 0x{base:08X}")
        positioned, labels, code_end = self._layout()
        if pad == "nop":
            pool_offset = code_end + (-(base + code_end) % 4)   # align the REAL address
        else:
            pool_offset = code_end + (-code_end % 4)            # 4-align the pool start
        const_addr = {c: base + pool_offset + 4 * i
                      for i, c in enumerate(self._consts)}

        builder = StubBuilder()
        for off, item in positioned:
            kind = item[0]
            addr = base + off
            if kind == "label":
                continue
            if kind == "bl":
                builder.bl(item[1], f"BL 0x{item[1]:08X}")
            elif kind == "bllabel":
                if item[1] not in labels:
                    raise ValueError(f"bl_label: undefined label {item[1]!r}")
                builder.bl(base + labels[item[1]], f"BL {item[1]}")
            elif kind == "blx":
                builder.blx(item[1], f"BLX 0x{item[1]:08X}")
            elif kind == "raw":
                builder.hw(item[1], ".hword")
            elif kind == "ldrc":
                _, rd, value = item
                pc = (addr + 4) & ~3
                imm = const_addr[value] - pc
                enc = encode_thumb_line("LDR", f"R{rd}, [PC, #0x{imm:X}]", addr=addr)
                builder.hw(struct.unpack("<H", enc)[0],
                           f"LDR R{rd}, =0x{value:08X}")
            else:  # insn
                _, mnemonic, operands = item
                resolved = self._resolve_labels(operands, labels, base)
                enc = encode_thumb_line(mnemonic, resolved, addr=addr)
                for k in range(0, len(enc), 2):
                    builder.hw(struct.unpack_from("<H", enc, k)[0],
                               f"{mnemonic} {resolved}".strip() if k == 0 else "")

        if pad == "nop":
            # asm() always pads to a 4-byte boundary, pool or not.
            for _ in range((pool_offset - code_end) // 2):
                builder.hw(0x46C0, "nop (pool align)")
            for value in self._consts:
                builder.pool(value)
            return builder

        # 4-align padding (0 or 2 bytes) then the literal pool — only when
        # there are constants to place (no pool ⇒ no trailing padding).
        if self._consts:
            if pool_offset > code_end:
                builder.hw(0x0000, "pool align")
            for value in self._consts:
                builder.pool(value)
        return builder

    @staticmethod
    def _resolve_labels(operands: str, labels: dict[str, int], base: int) -> str:
        """Resolve a branch target operand that names a label.

        A label is only ever a branch's sole target operand, so this matches
        the whole (stripped) operand against the label table — never a
        substring, which would corrupt hex literals like ``#0x0``.
        """
        key = operands.strip()
        if key in labels:
            return f"0x{base + labels[key]:08X}"
        return operands

    def assemble(self, base: int, pad: str = "zero") -> bytes:
        """Assemble the program to bytes for a runtime start address of *base*.

        ``pad="nop"`` reproduces :func:`thumb_asm.asm` exactly (see :meth:`to_builder`).
        """
        return self.to_builder(base, pad).build(base, halfword_base=(pad == "nop"))


# ---------------------------------------------------------------------------
# Handler extent helpers
# ---------------------------------------------------------------------------

def collect_handler_addrs(overlay: bytes) -> list[int]:
    """Return the sorted, de-duplicated list of every handler function address.

    Pointers carry the Thumb bit (``| 1``); it is cleared here.  Used to clamp
    a function's detected extent by the start of the next function.
    """
    addrs: set[int] = set()
    for idx in range(HANDLER_ENTRY_COUNT):
        off = HANDLER_TABLE_OFFSET + idx * HANDLER_ENTRY_SIZE
        for ptr in struct.unpack_from("<5I", overlay, off):
            if ptr:
                addrs.add(ptr & ~1)
    return sorted(addrs)


def handler_extent(overlay: bytes, func_addr: int,
                   sorted_addrs: list[int] | None = None) -> int:
    """Return the byte length of the handler at *func_addr*.

    Uses the heuristic :func:`detect_function_size`, clamped by the next
    distinct handler address so an over-read can never bleed into a
    neighbouring function (which would split a ``BL`` across the boundary).
    """
    file_off = func_addr - RAM_BASE
    size = detect_function_size(overlay, file_off)
    if sorted_addrs:
        j = bisect.bisect_right(sorted_addrs, func_addr)
        if j < len(sorted_addrs):
            size = min(size, sorted_addrs[j] - func_addr)
    return size


# ---------------------------------------------------------------------------
# Lift a handler into a StubBuilder
# ---------------------------------------------------------------------------

def lift_handler_to_builder(
    overlay: bytes,
    func_addr: int,
    *,
    sorted_addrs: list[int] | None = None,
    size: int | None = None,
) -> StubBuilder:
    """Decompile the handler at *func_addr* into a relocatable :class:`StubBuilder`.

    Every non-call instruction is emitted as raw halfwords; ``BL``/``BLX`` that
    do not overlap an in-function literal-pool word become relocatable calls;
    the trailing literal pool becomes :meth:`StubBuilder.pool` words.

    The guarantee is ``build(func_addr) == overlay[file_off:file_off+extent]``.

    *size* overrides the detected extent.  ``detect_function_size`` is a heuristic
    and **under-reports functions with several ``POP {..,PC}`` returns or an inline
    literal pool** — it stops at the first return it likes.  A truncated lift still
    round-trips byte-for-byte (the prefix is genuine), so the identity check cannot
    catch it; what gives it away is a ``LDR Rx,[PC,#imm]`` whose literal lies past
    the end of the copy.  Relocating such a clone makes that load read whatever
    follows it in the cave — see the Sea Lancer multi-select template, whose real
    extent is 0x34C against a detected 0x232.
    """
    file_off = func_addr - RAM_BASE
    size = handler_extent(overlay, func_addr, sorted_addrs) if size is None else size
    insns = decode_thumb(overlay[file_off:file_off + size], func_addr,
                         overlay_data=overlay, ram_base=RAM_BASE)
    ps = pool_start_index(insns)
    code = insns[:ps]

    # Literal-pool words referenced from within the code must never be treated
    # as relocatable branches even if their bytes look like a BL/BLX prefix.
    pool_word_ranges = [
        (ins.pool_addr, ins.pool_addr + 4) for ins in code if ins.is_pool_ref
    ]

    def overlaps_pool(ins: ThumbInsn) -> bool:
        lo, hi = ins.addr, ins.addr + ins.size
        return any(lo < pe and ps_ < hi for ps_, pe in pool_word_ranges)

    builder = StubBuilder()
    for ins in code:
        asm = f"{ins.mnemonic} {ins.operands}".strip()
        if ins.size == 4 and ins.mnemonic in ("BL", "BLX") and not overlaps_pool(ins):
            if ins.mnemonic == "BL":
                builder.bl(ins.branch_target, asm)
            else:
                # Decoder stores addr+4+offset; the true ARM target subtracts
                # the PC's word-alignment slack.
                builder.blx(ins.branch_target - (ins.addr & 2), asm)
        else:
            for k in range(0, ins.size, 2):
                builder.hw(struct.unpack_from("<H", ins.raw, k)[0],
                           asm if k == 0 else "")

    # Trailing literal pool: emit alignment padding as halfwords, then words.
    if ps < len(insns):
        tail_start = insns[ps].addr - RAM_BASE
        tail_end = file_off + size
        addr = func_addr + (tail_start - file_off)
        off = tail_start
        while off < tail_end:
            if addr % 4 != 0 or tail_end - off < 4:
                builder.hw(struct.unpack_from("<H", overlay, off)[0], "pool (half)")
                off += 2
                addr += 2
            else:
                builder.pool(struct.unpack_from("<I", overlay, off)[0])
                off += 4
                addr += 4

    return builder

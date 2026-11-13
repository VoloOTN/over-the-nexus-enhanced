"""Shared building blocks for card patches: overlay views, table edits, Thumb encoders, checks.

Sections, in order: Ov / Table / Thumb / ARM9 / Checker, then the raw-offset helpers that used to be
private to individual cards.
"""
from __future__ import annotations

import struct
from otn_enhanced.rom.overlay_io import RAM_BASE as OV3_BASE
from dataclasses import dataclass
from contextlib import contextmanager
import ndspy.code
from otn_enhanced.rom.overlay_io import RAM_BASE


# ----------------------------------------------------------------------
# ov: Read and write an overlay by RAM address, once instead of ~70 times.
# ----------------------------------------------------------------------

ARM9_BASE = 0x02000000     # MainCodeFile section base; `a9(addr)` in ~4 modules

OV5_BASE = 0x022C5900      # ov5_cave.OV5_RAM_BASE

class Ov:
    """A RAM-addressed view over one decompressed overlay buffer.

    Wraps, does not copy: writes go straight to the underlying bytearray, so an `Ov` can be
    handed to code that still wants the raw buffer (`ov.buf`).
    """

    __slots__ = ("buf", "base")

    def __init__(self, buf: bytearray | bytes, base: int = OV3_BASE):
        self.buf = buf if isinstance(buf, bytearray) else bytearray(buf)
        self.base = base

    def __len__(self) -> int:
        return len(self.buf)

    @property
    def end(self) -> int:
        """One past the last valid RAM address."""
        return self.base + len(self.buf)

    def off(self, addr: int) -> int:
        """Buffer offset for RAM address *addr*, bounds-checked.

        The check is the point. Every hand-rolled `_off` returns a negative number for an
        address below the overlay, and `unpack_from` happily reads from the END of the buffer
        instead of raising -- so a wrong base silently returns plausible garbage.
        """
        o = addr - self.base
        if not 0 <= o < len(self.buf):
            raise IndexError(f"0x{addr:08X} is outside this overlay "
                             f"(0x{self.base:08X}..0x{self.end:08X})")
        return o

    # -- reads -------------------------------------------------------------------------
    def u8(self, addr: int) -> int:
        return self.buf[self.off(addr)]

    def u16(self, addr: int) -> int:
        return struct.unpack_from("<H", self.buf, self.off(addr))[0]

    def u32(self, addr: int) -> int:
        return struct.unpack_from("<I", self.buf, self.off(addr))[0]

    def blob(self, addr: int, n: int) -> bytes:
        o = self.off(addr)
        return bytes(self.buf[o:o + n])

    def unpack(self, addr: int, fmt: str) -> tuple:
        return struct.unpack_from(fmt, self.buf, self.off(addr))

    # -- writes ------------------------------------------------------------------------
    def set_u8(self, addr: int, value: int) -> None:
        self.buf[self.off(addr)] = value & 0xFF

    def set_u16(self, addr: int, value: int) -> None:
        struct.pack_into("<H", self.buf, self.off(addr), value & 0xFFFF)

    def set_u32(self, addr: int, value: int) -> None:
        struct.pack_into("<I", self.buf, self.off(addr), value & 0xFFFFFFFF)

    def write(self, addr: int, data: bytes) -> None:
        """Overwrite in place. Refuses to change the overlay's length -- overlay 3 cannot grow."""
        o = self.off(addr)
        if o + len(data) > len(self.buf):
            raise IndexError(f"write of {len(data)}B at 0x{addr:08X} runs past the overlay end")
        self.buf[o:o + len(data)] = data

    def pack(self, addr: int, fmt: str, *values) -> None:
        struct.pack_into(fmt, self.buf, self.off(addr), *values)

    # -- tables ------------------------------------------------------------------------
    def rows(self, base: int, *, count: int, stride: int, fmt: str) -> list[tuple]:
        """Unpack *count* records of *stride* bytes starting at RAM address *base*."""
        return [self.unpack(base + i * stride, fmt) for i in range(count)]

    def keys(self, base: int, *, count: int, stride: int, wide: bool = False) -> list[int]:
        """The leading key of each record -- u16 unless *wide*, then u32.

        The `_keys` helper duplicated in 7 modules (grapha.py:451,
        ninja_grandmaster_hanzo.py:399, ninjitsu_art_super_transformation.py:490,
        snoww.py:343, boggart_knight.py, reborn_tengu.py, eclipse_wyvern.py).
        """
        fmt = "<I" if wide else "<H"
        return [struct.unpack_from(fmt, self.buf, self.off(base + i * stride))[0]
                for i in range(count)]


# ----------------------------------------------------------------------
# thumb: The Thumb-1 hand-encoders, once instead of ~32 times.
# ----------------------------------------------------------------------

EQ, NE, CS, CC, MI, PL, VS, VC, HI, LS, GE, LT, GT, LE = range(14)

def bl(src: int, dst: int) -> bytes:
    """ARMv4T two-halfword BL (Thumb-1 long branch-with-link). 4 bytes.

    The majority form, byte-identical in criteria_row_hook.py:347, timing_class_hook.py:202,
    summon_rider_hook.py:112, handss_banish_cost.py:122, jet_synchron.py:986,
    lightpulsar.py:1814, darkflare.py:434, junk_speeder.py:928 (as
    `_thumb_bl`) and ninjitsu_art_super_transformation.py:416.
    """
    off = dst - (src + 4)
    assert -(1 << 22) <= off < (1 << 22), f"BL out of range: {off:#x}"
    return struct.pack("<HH", 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))

def b(src: int, dst: int) -> bytes:
    """Thumb-1 unconditional B (11-bit signed halfword offset, +-2 KB). 2 bytes.

    Verbatim from darkflare.py:_b.
    """
    off = dst - (src + 4)
    assert -(1 << 11) <= off < (1 << 11), f"B out of range: {off:#x}"
    return struct.pack("<H", 0xE000 | ((off >> 1) & 0x7FF))

def bcond(at: int, target: int, cond: int) -> int:
    """Conditional branch at *at* to *target*. Returns the halfword.

    Verbatim from white_dragon_ninja.py:_bcond. Range is imm8 -- +-256 bytes only.
    """
    off = (target - (at + 4)) // 2
    assert -0x80 <= off < 0x80, "conditional branch out of imm8 range"
    return 0xD000 | (cond << 8) | (off & 0xFF)

def ldr_pc(at: int, reg: int, target: int) -> int:
    """`ldr rREG,[pc,#imm]` at *at*, loading the word at *target*. Returns the halfword.

    Verbatim from white_dragon_ninja.py:_ldr_pc. Note the `(at + 4) & ~3` alignment:
    PC-relative loads round the base DOWN to a word boundary, so the encodable offset depends
    on whether *at* is 2- or 4-aligned.
    """
    imm = target - ((at + 4) & ~3)
    assert 0 <= imm <= 0x3FC and imm % 4 == 0, f"ldr [pc,#{imm}] out of range at 0x{at:08X}"
    return 0x4800 | (reg << 8) | (imm // 4)

def bl_target(buf, site: int, base: int) -> int:
    """Decode the BL at RAM address *site* in *buf* and return where it goes.

    Verbatim from snoww.py:_bl_target, with the overlay base passed in rather than
    closed over. Used by verify() to assert a hook still points where it was installed.
    """
    off = site - base
    w0, w1 = struct.unpack_from("<HH", buf, off)
    assert (w0 & 0xF800) == 0xF000 and (w1 & 0xF800) == 0xF800, f"0x{site:08X} is not a BL"
    hi = w0 & 0x7FF
    if hi & 0x400:
        hi -= 0x800
    return (site + 4) + (hi << 12) + ((w1 & 0x7FF) << 1)

def assert_blx_target(value: int, what: str = "BLX target") -> int:
    """Assert a literal destined for `blx rX` has the Thumb bit set. Returns it unchanged.

    `blx rX` takes its instruction set from bit 0 of rX. A raw (even) address from a
    disassembly listing switches the core to ARM and executes garbage -- an instant freeze.
    This recurred on jet_warrior in 2026-09-04 *with the fact already in the KB*, and
    cost an in-game test. Prose did not prevent it; a mechanical check does. The literal's
    value never appears in a disassembly (only `ldr rX,[pc,#imm]` does), so neither a passing
    verify() nor a capstone listing can show you this.
    """
    assert value & 1, (f"{what} 0x{value:08X} has bit 0 CLEAR -- blx would switch to ARM state "
                       f"and freeze. Use 0x{value | 1:08X}.")
    return value


# ----------------------------------------------------------------------
# tables: Count-neutral sorted inserts -- the donor-card core, once instead of ~42 times.
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Table:
    """Geometry of one sorted, fixed-length overlay table.

    *count* is load-bearing: it mirrors a literal the engine reads (e.g. the criteria
    registry's 0x56C at CRIT_COUNT_LIT) and must never change. That is the whole reason
    inserts are count-neutral.
    """
    base: int
    count: int
    stride: int
    fmt: str
    wide: bool = False        # the leading key is a u32, not a u16
    label: str = "table"

    @property
    def key_fmt(self) -> str:
        return "<I" if self.wide else "<H"

    def addr(self, i: int) -> int:
        return self.base + i * self.stride

def keys(view: Ov, t: Table) -> list[int]:
    """The leading key of every record."""
    return [struct.unpack_from(t.key_fmt, view.buf, view.off(t.addr(i)))[0]
            for i in range(t.count)]

def rows(view: Ov, t: Table) -> list[tuple]:
    """Every record, unpacked with *t.fmt*."""
    return [view.unpack(t.addr(i), t.fmt) for i in range(t.count)]

def find(view: Ov, t: Table, cid: int) -> int | None:
    """Index of the FIRST record whose key is *cid*, or None.

    Leftmost on purpose: `find_event_handler` (0x0224A118) returns the leftmost same-cid
    record, which is why two cls2 records for one cid make the first shadow the second --
    the bug that had Warwolf's E1 silently disabling its E2.
    """
    ks = keys(view, t)
    return ks.index(cid) if cid in ks else None

def assert_sorted(view: Ov, t: Table, when: str = "") -> list[int]:
    ks = keys(view, t)
    bad = next((i for i in range(len(ks) - 1) if ks[i] > ks[i + 1]), None)
    assert bad is None, (f"{t.label}: not sorted{' ' + when if when else ''} at index {bad} "
                         f"(0x{ks[bad]:04X} > 0x{ks[bad + 1]:04X})")
    return ks

def insert_sorted(view: Ov, t: Table, record: tuple, *, drop: int, quiet: bool = False) -> int:
    """Insert *record* at its sorted position, dropping phantom cid *drop*. Count-neutral.

    Idempotent: if `record[0]` is already present, nothing happens and its index is returned.
    Returns the index the record ended up at.
    """
    recs = [list(r) for r in rows(view, t)]
    cid = record[0]

    present = next((i for i, r in enumerate(recs) if r[0] == cid), None)
    if present is not None:
        if not quiet:
            print(f"{t.label}: 0x{cid:04X} already present @{present} -- skipped (idempotent)")
        return present

    assert_sorted(view, t, "before insert")
    dst = next((i for i, r in enumerate(recs) if r[0] == drop), None)
    assert dst is not None, (f"{t.label}: phantom 0x{drop:04X} not present to drop -- "
                             f"already spent by another patch, or wrong table")
    recs.pop(dst)

    # bisect-right over the remaining keys. B's `next(r[0] > cid)` raises StopIteration when
    # the new key is the largest in the table; this does not.
    pos = sum(1 for r in recs if r[0] <= cid)
    recs.insert(pos, list(record))

    assert len(recs) == t.count, f"{t.label}: count changed {t.count} -> {len(recs)}"
    for i, r in enumerate(recs):
        view.pack(t.addr(i), t.fmt, *r)
    assert_sorted(view, t, "after insert")

    if not quiet:
        print(f"{t.label}: dropped phantom 0x{drop:04X} @{dst}, inserted 0x{cid:04X} @{pos} "
              f"(RAM 0x{t.addr(pos):08X}); {t.count} records, sorted, count-neutral")
    return pos

def swap_key(view: Ov, t: Table, old_cid: int, new_cid: int, *, quiet: bool = False) -> int:
    """Repoint an existing row from *old_cid* to *new_cid*, keeping the table sorted.

    The "slot steal" -- keep a native resolver, change whose cid invokes it. Only legal when
    the move does not disturb the sort; asserts rather than silently corrupting the binary
    search. (`_count_neutral_swap` x3: azure_eyes, maiden_eyes_of_blue, ninishi.)
    """
    i = find(view, t, old_cid)
    assert i is not None, f"{t.label}: 0x{old_cid:04X} not present to swap"
    row = list(view.unpack(t.addr(i), t.fmt))
    row[0] = new_cid
    view.pack(t.addr(i), t.fmt, *row)
    try:
        assert_sorted(view, t, "after swap")
    except AssertionError:
        row[0] = old_cid                                   # put it back before raising
        view.pack(t.addr(i), t.fmt, *row)
        raise AssertionError(f"{t.label}: swapping 0x{old_cid:04X} -> 0x{new_cid:04X} @{i} "
                             f"would break the sort; use insert_sorted with a phantom instead")
    if not quiet:
        print(f"{t.label}: row @{i} repointed 0x{old_cid:04X} -> 0x{new_cid:04X}")
    return i


# ----------------------------------------------------------------------
# arm9: Edit the ARM9 main module, once instead of 42 times.
# ----------------------------------------------------------------------

def sections(rom) -> dict[int, int]:
    """{ramAddress: length} for every arm9 section -- for asserting you have the right ROM."""
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    return {s.ramAddress: len(s.data) for s in mc.sections}

def view(rom, base: int = ARM9_BASE) -> Ov:
    """A READ-ONLY RAM-addressed view of an arm9 section. Writes to it are discarded.

    Use this in `verify()`, where reopening the module to write would be wrong anyway.
    """
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == base)
    return Ov(bytearray(sec.data), base)

@contextmanager
def arm9_edit(rom, base: int = ARM9_BASE):
    """Yield a writable :class:`Ov` over an arm9 section; write it back on clean exit.

        with arm9_edit(rom) as a9:
            a9.set_u32(0x0209CB48, new_value)

    On an exception nothing is written back, so a failed assertion mid-edit leaves the ROM
    untouched rather than half-patched -- which the 35 inline copies do NOT guarantee, since
    they mutate a bytearray and write it back unconditionally.
    """
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next((s for s in mc.sections if s.ramAddress == base), None)
    assert sec is not None, (f"no arm9 section at 0x{base:08X}; sections are "
                             + ", ".join(f"0x{s.ramAddress:08X}" for s in mc.sections))
    before = len(sec.data)
    v = Ov(bytearray(sec.data), base)

    yield v

    assert len(v.buf) == before, (f"arm9 section 0x{base:08X} changed length "
                                  f"{before} -> {len(v.buf)}; arm9 edits must be in place")
    sec.data = bytes(v.buf)
    rom.arm9 = mc.save()          # rebuilds the module params -- never write rom.arm9 directly

def read_setcode_table(a9: Ov, pool: int, expect_base: int, count: int, label: str) -> list[int]:
    """Read an archetype set-code list through its thunk's pointer literal.

    `_read_setcode_table` x3 (ninja_grandmaster_hanzo:491, upstart_golden_ninja:474,
    white_dragon_ninja:319). The literal at *pool* is the ADDRESS of the list, not the list --
    asserting it still equals *expect_base* is what catches a thunk table that moved.
    """
    base = a9.u32(pool)
    assert base == expect_base, (f"{label}: the thunk's list literal @0x{pool:08X} is "
                                 f"0x{base:08X}, expected 0x{expect_base:08X}")
    return [a9.u16(base + i * 2) for i in range(count)]


# ----------------------------------------------------------------------
# checks: One `verify()` contract instead of three, plus the checks every module re-writes.
# ----------------------------------------------------------------------

class Checker:
    """Collect PASS/FAIL lines, then report once.

        c = Checker("Dark Soul")
        c.ok(row is not None, "cls2 record present")
        c.eq(ov.u16(addr), 0x1783, "donor cid at the hook site")
        return c.result()
    """

    def __init__(self, label: str = "", *, quiet: bool = False):
        self.label = label
        self.quiet = quiet
        self.failures: list[str] = []
        self.passes = 0

    def ok(self, cond, msg: str) -> bool:
        good = bool(cond)
        if good:
            self.passes += 1
        else:
            self.failures.append(msg)
        if not self.quiet:
            print(f"  [{'PASS' if good else 'FAIL'}] {msg}")
        return good

    def eq(self, got, want, msg: str) -> bool:
        """Like :meth:`ok`, but shows both values when it fails -- which is when you need them."""
        good = got == want
        detail = msg if good else f"{msg}  (got {_show(got)}, want {_show(want)})"
        return self.ok(good, detail)

    def result(self) -> bool:
        """True iff every check passed. THE return contract -- always a bool, never None."""
        n = self.passes + len(self.failures)
        if self.failures:
            print(f"{self.label}: {len(self.failures)}/{n} FAILED")
            for f in self.failures:
                print(f"    - {f}")
            return False
        if not self.quiet:
            print(f"{self.label}: {n}/{n} passed")
        return True

def _show(v) -> str:
    if isinstance(v, int):
        return f"0x{v:X}" if v > 9 else str(v)
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    return repr(v)

def table_intact(c: Checker, view: Ov, t: Table, *, expect: int, phantom: int) -> bool:
    """The check every donor patch re-writes: sorted, right length, phantom spent, cid present.

    All four matter and each has broken a card on its own:
      * not sorted        -> the engine's binary search silently misses the row;
      * wrong count       -> the hardcoded row-count literal now lies;
      * phantom still in  -> the insert did not happen (or ran on the wrong table);
      * cid absent        -> the row was inserted somewhere else.
    """
    ks = keys(view, t)
    good = c.ok(len(ks) == t.count, f"{t.label}: {t.count} records (count-neutral)")
    good &= c.ok(ks == sorted(ks), f"{t.label}: still sorted")
    good &= c.ok(phantom not in ks, f"{t.label}: phantom 0x{phantom:04X} spent")
    good &= c.ok(expect in ks, f"{t.label}: cid 0x{expect:04X} present")
    return bool(good)

def hook_points_at(c: Checker, view: Ov, site: int, target: int, what: str = "hook") -> bool:
    """Assert the BL at *site* still branches to *target*.

    A shared 4-byte hook site is claimed by whichever patch runs first, so this is how a later
    patch confirms it did not silently lose the site to another one.
    """
    try:
        got = bl_target(view.buf, site, view.base)
    except AssertionError as exc:
        return c.ok(False, f"{what} @0x{site:08X}: {exc}")
    return c.eq(got, target, f"{what} @0x{site:08X} -> 0x{target:08X}")

def cave_holds(c: Checker, ov5: Ov, addr: int, blob: bytes, what: str = "stub") -> bool:
    """Assert an ov5 cave slot still holds exactly *blob* -- i.e. nothing overwrote it."""
    try:
        got = ov5.blob(addr, len(blob))
    except IndexError:
        return c.ok(False, f"{what} @0x{addr:08X}: past the end of ov5 (cave not grown?)")
    if got == blob:
        return c.ok(True, f"{what} @0x{addr:08X} intact ({len(blob)} B)")
    off = next((i for i in range(len(blob)) if got[i] != blob[i]), 0)
    return c.ok(False, f"{what} @0x{addr:08X} differs at +0x{off:X}: "
                       f"{got[off:off + 4].hex()} != {blob[off:off + 4].hex()}")


# ----------------------------------------------------------------------
# Raw-offset helpers. Formerly private to the cards that first needed them.
# ----------------------------------------------------------------------


POP_BASE = 0x022713C4         # criteria table
CRIT_STRIDE = 12
CLS1_BASE = 0x022860D4
CLS1_STRIDE = 24
CLS1_COUNT = 0x535
CLS1_FMT = "<IIIIII"


def ov3_off(ram: int) -> int:
    """RAM address -> overlay-3 buffer offset."""
    return ram - RAM_BASE


# ---------------------------------------------------------------------------
# Count-neutral sorted inserts.  Ported from snoww / reborn_tengu /
# ninja_grandmaster_hanzo -- the house pattern for adding a row to a table
# the engine binary-searches.
# ---------------------------------------------------------------------------
def u16_keys(ov: bytearray, base: int, count: int, stride: int) -> list:
    """The u16 key (cid) of every row in the table."""
    return [struct.unpack_from("<H", ov, ov3_off(base + i * stride))[0] for i in range(count)]


def insert_row(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                   record: tuple, drop_cid: int, label: str) -> None:
    """Count-neutral sorted insert: delete the phantom row, shift, write *record*."""
    keys = u16_keys(ov, base, count, stride)
    new_cid = record[0]
    if any(struct.unpack_from(fmt, ov, ov3_off(base + i * stride)) == record for i in range(count)):
        print(f"{label}: this exact record is already present (idempotent) -- skipped")
        return
    if new_cid in keys:                                   # a DIFFERENT record for this cid would be shadowed
        raise SystemExit(f"{label}: 0x{new_cid:04X} already has a row -- a second one is "
                         f"unreachable (find_event_handler returns the LEFTMOST record)")
    assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
    dst = keys.index(drop_cid)                            # the row being deleted
    pos = sum(1 for k in keys if k < new_cid)             # where the new row must land to stay sorted
    if pos > dst:                                         # deleting BEFORE the target: shift the block left
        blk = bytes(ov[ov3_off(base + (dst + 1) * stride):ov3_off(base + pos * stride)])
        ov[ov3_off(base + dst * stride):ov3_off(base + (pos - 1) * stride)] = blk
        pos -= 1                                          # the deletion moved the insertion point down one
    elif pos < dst:                                       # deleting AFTER the target: shift the block right
        blk = bytes(ov[ov3_off(base + pos * stride):ov3_off(base + dst * stride)])
        ov[ov3_off(base + (pos + 1) * stride):ov3_off(base + (dst + 1) * stride)] = blk
    struct.pack_into(fmt, ov, ov3_off(base + pos * stride), *record)
    moved = abs(pos - dst)
    print(f"{label}: dropped phantom 0x{drop_cid:04X} @{dst}, inserted 0x{new_cid:04X} @{pos} "
          f"({moved} row{'' if moved == 1 else 's'} shifted, count {count} unchanged)")
    after = u16_keys(ov, base, count, stride)
    assert all(after[i] <= after[i + 1] for i in range(count - 1)), f"{label}: table lost its sort order"


def list_insert(ov: bytearray, base: int, count: int, new_cid: int, drop_cid: int,
                 label: str) -> None:
    """Count-neutral STRICTLY-sorted insert into a u16 membership list."""
    cur = u16_keys(ov, base, count, 2)
    if new_cid in cur:
        print(f"{label}: 0x{new_cid:04X} already a member (idempotent) -- skipped")
        return
    assert drop_cid in cur, f"{label}: 0x{drop_cid:04X} not in the list -- already spent?"
    assert all(cur[i] < cur[i + 1] for i in range(len(cur) - 1)), \
        f"{label}: the list is not strictly sorted in the base ROM"
    new = sorted([c for c in cur if c != drop_cid] + [new_cid])
    assert len(new) == count and all(new[i] < new[i + 1] for i in range(len(new) - 1)), \
        f"{label}: result is not a strictly sorted {count}-entry set"
    struct.pack_into(f"<{count}H", ov, ov3_off(base), *new)
    print(f"{label}: dropped 0x{drop_cid:04X}, inserted 0x{new_cid:04X} @{new.index(new_cid)}, "
          f"count {count} unchanged")


# ===========================================================================
# Low-level helpers
# ===========================================================================
def thumb_bl(src: int, dst: int) -> bytes:
    """Encode a 32-bit Thumb-1 BL from *src* to *dst* (both even addresses)."""
    off = dst - (src + 4)                 # BL offset is relative to the address AFTER the BL (pc = src+4)
    if off & 1:                           # Thumb targets must be halfword-aligned
        raise ValueError("odd BL offset")
    hi = 0xF000 | ((off >> 12) & 0x7FF)   # first halfword: high 11 bits of the signed offset
    lo = 0xF800 | ((off >> 1) & 0x7FF)    # second halfword: low 11 bits (>>1 because Thumb offsets are in halfwords)
    return struct.pack("<HH", hi, lo)     # little-endian pair of halfwords


def find_pop(ov: bytearray, cid: int) -> int:
    """Return the byte offset of the criteria record whose 'a' (source cid) == *cid*."""
    base = ov3_off(POP_BASE)                                 # convert the table's RAM address to an overlay-buffer offset
    for i in range(2200):                                 # scan a generous upper bound of 12-byte records
        off = base + i * CRIT_STRIDE                      # byte offset of record i
        if off + CRIT_STRIDE > len(ov):                   # don't read past the overlay buffer
            break                                         # ran off the end -> stop
        if struct.unpack_from("<H", ov, off)[0] == cid:   # read 'a' (u16 source cid) and compare
            return off                                    # matched -> return this record's offset
    raise SystemExit(f"criteria entry with a=0x{cid:04X} not found")  # abort clearly if absent


def crit_count(ov: bytearray) -> int:
    """Rows in the criteria table, INCLUDING the trailing a=0xFFFF sentinel.

    Counted rather than hardcoded so a chained build (where an earlier patch has
    already inserted rows) still gets the exact bound the engine searches.
    """
    n = 0                                                 # rows counted so far
    while True:                                           # walk until the sentinel is consumed
        a = struct.unpack_from("<H", ov, ov3_off(POP_BASE) + n * CRIT_STRIDE)[0]
        n += 1                                            # this row counts either way
        if a == 0xFFFF:                                   # the sentinel terminates the table
            return n                                      # include it, so inserts can never step past it


# elbow: insert_row / insert_row_wide / insert_row_by_stride are three near-copies. They differ in
# duplicate handling and argument order; collapse once every caller is on tables.insert_sorted.


def insert_row_by_stride(ov: bytearray, base: int, stride: int, count: int, fmt: str,
                   record: tuple, phantom_cid: int, label: str) -> None:
    """Count-neutral INSERT of *record* into a cid-sorted overlay-3 table.

    Drops the single phantom record whose cid (field 0) == *phantom_cid*, inserts *record*
    at its sorted position (by cid), and rewrites the whole region in place -- so the table
    stays the same size, sorted, and (for populate) keeps its trailing a=0xFFFF sentinel.
    The proven technique for giving a records-free donor a cls2 / populate record
    (see wattcobra.py and repo memory otn-donorfree-endphase-search.md). Idempotent.
    """
    b = base - RAM_BASE
    recs = [list(struct.unpack_from(fmt, ov, b + i * stride)) for i in range(count)]
    cid = record[0]
    if any(r[0] == cid for r in recs):                       # idempotent
        print(f"E2 {label} insert: 0x{cid:04X} already present -> no change")
        return
    assert all(recs[i][0] <= recs[i + 1][0] for i in range(count - 1)), (
        f"{label} table not sorted before insert")
    ph = [i for i, r in enumerate(recs) if r[0] == phantom_cid]
    assert len(ph) >= 1, f"{label}: phantom 0x{phantom_cid:04X} not present to drop"
    recs.pop(ph[0])
    ins = next(i for i, r in enumerate(recs) if r[0] > cid)   # sorted insert position
    recs.insert(ins, list(record))
    assert len(recs) == count and all(
        recs[i][0] <= recs[i + 1][0] for i in range(count - 1)), (
        f"{label} table not sorted / wrong count after insert")
    for i, r in enumerate(recs):
        struct.pack_into(fmt, ov, b + i * stride, *r)
    print(f"E2 {label} insert: dropped phantom 0x{phantom_cid:04X}, inserted 0x{cid:04X} "
          f"@ idx {ins} (RAM 0x{base + ins * stride:08X}); {count} records, sorted, count-neutral")


def insert_row_by_res(ov: bytearray, base: int, stride: int, count: int,
                       record: tuple, phantom_cid: int, label: str) -> None:
    """Count-neutral INSERT of a stride-24 cls2 *record*, keyed on (cid, res) for idempotency (not
    cid alone) so a SECOND record for a cid that already owns one still inserts -- here: Warwolf's E1
    summon-response record alongside its E2 End-Phase record (two cls2 records per cid is
    native-proven, e.g. Doppelwarrior 0x244D). Drops the phantom, inserts at the sorted-by-cid
    position (after any same-cid rows, keeping the pair adjacent)."""
    b = base - RAM_BASE
    recs = [list(struct.unpack_from("<6I", ov, b + i * stride)) for i in range(count)]
    cid, res = record[0], record[1]
    if any(r[0] == cid and r[1] == res for r in recs):
        print(f"{label} insert: (0x{cid:04X}, res 0x{res:08X}) already present -> no change")
        return
    ph = [i for i, r in enumerate(recs) if r[0] == phantom_cid]
    assert len(ph) >= 1, f"{label}: phantom 0x{phantom_cid:04X} not present to drop"
    recs.pop(ph[0])
    ins = len(recs)
    for i, r in enumerate(recs):
        if r[0] > cid:
            ins = i
            break
    recs.insert(ins, list(record))
    assert len(recs) == count and all(recs[i][0] <= recs[i + 1][0] for i in range(count - 1)), (
        f"{label} table not sorted / wrong count after insert")
    for i, r in enumerate(recs):
        struct.pack_into("<6I", ov, b + i * stride, *r)
    print(f"{label} insert: dropped phantom 0x{phantom_cid:04X}, inserted 0x{cid:04X} "
          f"(res 0x{res:08X}) @ idx {ins} (RAM 0x{base + ins * stride:08X}); count-neutral")


def row_keys(ov: bytearray, base: int, count: int, stride: int, wide: bool) -> list[int]:
    fmt = "<I" if wide else "<H"
    return [struct.unpack_from(fmt, ov, ov3_off(base + i * stride))[0] for i in range(count)]


def record_present(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                    record: tuple) -> bool:
    return any(struct.unpack_from(fmt, ov, ov3_off(base + i * stride)) == record
               for i in range(count))


def insert_row_wide(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                   record: tuple, drop_cid: int, label: str, wide: bool,
                   after_same_cid: bool = False, expect_dupe: bool = False) -> None:
    """Count-neutral sorted insert: delete the phantom row, shift, write *record*.

    *after_same_cid* places the new record AFTER any existing row with the same
    cid.  The table is sorted by cid alone so either side is legal, but
    0x02243B9C returns `leftmost_row_for_cid + r4` -- WHICH SIDE decides which
    clause is rel 0, so the cost row must go in first and the effect row after.
    """
    keys = row_keys(ov, base, count, stride, wide)
    new_cid = record[0]
    if record_present(ov, base, count, stride, fmt, record):
        print(f"{label}: this exact record is already present (idempotent) -- skipped")
        return
    if new_cid in keys and not expect_dupe:
        print(f"{label}: 0x{new_cid:04X} already present (idempotent) -- skipped")
        return
    assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
    dst = keys.index(drop_cid)
    pos = sum(1 for k in keys if (k <= new_cid if after_same_cid else k < new_cid))
    if pos > dst:
        blk = bytes(ov[ov3_off(base + (dst + 1) * stride):ov3_off(base + pos * stride)])
        ov[ov3_off(base + dst * stride):ov3_off(base + (pos - 1) * stride)] = blk
        pos -= 1
    elif pos < dst:
        blk = bytes(ov[ov3_off(base + pos * stride):ov3_off(base + dst * stride)])
        ov[ov3_off(base + (pos + 1) * stride):ov3_off(base + (dst + 1) * stride)] = blk
    struct.pack_into(fmt, ov, ov3_off(base + pos * stride), *record)
    moved = abs(pos - dst)
    print(f"{label}: dropped phantom 0x{drop_cid:04X} @{dst}, inserted 0x{new_cid:04X} @{pos} "
          f"({moved} row{'' if moved == 1 else 's'} shifted, count {count} unchanged)")
    after = row_keys(ov, base, count, stride, wide)
    assert all(after[i] <= after[i + 1] for i in range(count - 1)), \
        f"{label}: table lost its sort order"


def u16(ov, ram: int) -> int:
    """Little-endian u16 at RAM address *ram* in an overlay-3 buffer."""
    return struct.unpack_from("<H", ov, ram - RAM_BASE)[0]


def u32(ov, ram: int) -> int:
    """Little-endian u32 at RAM address *ram* in an overlay-3 buffer."""
    return struct.unpack_from("<I", ov, ram - RAM_BASE)[0]


def read_thunk_list(d: bytes, pool: int, count_imm: int, expect_base: int,
                     label: str) -> tuple[int, int, list[int]]:
    """Read a binary-searched u16 cid list, taking BASE and COUNT from the code.

    setcode.slot_addresses_are_not_stable: never assume either.  An earlier patch
    in the chain may have rewritten this very table, and a hardcoded count that
    disagrees with the immediate is how a binary search starts reading garbage.
    """
    base = struct.unpack_from("<I", d, pool - ARM9_BASE)[0]
    assert base == expect_base, (
        f"{label}: pool word @0x{pool:08X} is 0x{base:08X}, expected 0x{expect_base:08X} "
        f"-- refusing to patch a moved table")
    imm = struct.unpack_from("<H", d, count_imm - ARM9_BASE)[0]
    assert (imm & 0xFF00) == 0x2200, (
        f"{label}: 0x{count_imm:08X} is not `movs r2,#N` (reads 0x{imm:04X})")
    n = imm & 0xFF
    lst = list(struct.unpack_from(f"<{n}H", d, base - ARM9_BASE))
    return base, n, lst


def swap_in_list(lst: list[int], drop: int, insert: int, label: str) -> list[int]:
    """Count-neutral sorted swap inside a flat u16 list."""
    assert all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)), \
        f"{label}: not strictly sorted before the edit"
    assert lst.count(drop) == 1, \
        f"{label}: expected exactly one 0x{drop:04X}, found {lst.count(drop)}"
    out = [c for c in lst if c != drop]
    pos = next((i for i, c in enumerate(out) if c > insert), len(out))
    out.insert(pos, insert)
    assert len(out) == len(lst), f"{label}: count changed"
    assert all(out[i] < out[i + 1] for i in range(len(out) - 1)), \
        f"{label}: lost its strict sort"
    return out


def ov3_bl_target(ov, src: int) -> int:
    h1, h2 = struct.unpack_from("<HH", ov, src - RAM_BASE)
    assert h1 >> 11 == 0b11110 and h2 >> 11 == 0b11111, f"no BL @0x{src:08X}"
    off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
    return src + 4 + (off - (1 << 23) if off & (1 << 22) else off)


def put(ov: bytearray, addr: int, blob: bytes, stock: bytes, label: str) -> None:
    from otn_enhanced.asm import effect_verify
    o = addr - RAM_BASE
    cur = bytes(ov[o:o + len(blob)])
    if cur == blob:
        return
    assert cur == stock, f"{label} @{addr:#x} is {cur.hex()}, expected {stock.hex()} -- another patch owns it"
    effect_verify.assert_thumb1_only(blob, addr)
    ov[o:o + len(blob)] = blob
    print(f"{label} @{addr:#x} ({len(blob)} B)")


def rewrite_shared(rom, base: int, reserve: int, old: bytes, new: bytes, label: str) -> None:
    """Rewrite a SHARED ov5 stub with this card's arm, only over exactly the registered stub (Dark Law)."""
    from otn_enhanced.asm import effect_verify as _ev
    from otn_enhanced.effects import ov5_cave as _o5
    _ev.assert_thumb1_only(new, base)
    assert len(new) <= reserve, f"{label} {len(new)} B > {reserve:#x}"
    if _o5.read_cave(rom, base, len(new)) == new:
        return
    ov5 = _o5._load_ov5_decompressed(rom)
    data = bytearray(ov5.data)
    o = base - _o5.OV5_RAM_BASE
    cur = bytes(data[o:o + reserve])
    if cur == bytes(reserve):                  # fresh ROM: nobody installed it yet
        _o5.install_cave(rom, base, new, reserve=reserve)
    else:
        assert cur == old + bytes(reserve - len(old)), f"{label} is not the registered stub -- refusing"
        data[o:o + reserve] = new + bytes(reserve - len(new))
        _o5._save_ov5(rom, ov5, bytes(data))
    print(f"{label} rewritten with the 0x10A5 arm ({len(old)} -> {len(new)} B)")


# ----------------------------------------------------------------------
# reach: does a hook site still end up in our stub once later cards put fronts AHEAD of it?
# ----------------------------------------------------------------------

def _duel_code(rom) -> list[tuple[int, bytes]]:
    """(ram base, bytes) for arm9 + ov3 + ov5: everything a duel-time hook chain can run through."""
    import ndspy.rom
    if not hasattr(rom, "arm9"):
        rom = ndspy.rom.NintendoDSRom.fromFile(str(rom))
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    ovs = rom.loadArm9Overlays([3, 5])
    return ([(s.ramAddress, bytes(s.data)) for s in mc.sections]
            + [(ovs[i].ramAddress, bytes(ovs[i].data)) for i in (3, 5)])


def code_reaches(rom, site: int, want: int, *, is_site: bool = True, max_nodes: int = 256) -> bool:
    """True iff the BL at *site* (or, with is_site=False, the code AT *site*) reaches *want*. See reached_nodes."""
    return (want & ~1) in reached_nodes(rom, site, is_site=is_site, max_nodes=max_nodes)


def reached_nodes(rom, site: int, *, is_site: bool = True, max_nodes: int = 256) -> set[int]:
    """Every code address the BL at *site* (or the code AT *site*) can call or jump to, through our caves.

    Follows, from the ROM's own bytes: BL/BLX targets, B / Bcc, and the `ldr rN,=addr|1 ; bx/blx rN`
    tail every front in this repo uses to pass on to the previous chain head. So a check written
    as "site -> my stub" keeps passing when a later card legitimately puts its front ahead of ours,
    and still fails if the chain is broken (nothing on any path calls or jumps to *want*).
    *rom*: an ndspy ROM or a path.
    """
    import capstone
    regions = _duel_code(rom)

    def read(addr: int, n: int) -> bytes | None:
        for base, data in regions:
            if base <= addr and addr + n <= base + len(data):
                return data[addr - base:addr - base + n]
        return None

    # Walk only OUR code: the appended ov5 region and every declared cave. Native game functions are
    # leaves -- they never lead into a stub except through a hooked site, and walking them blows the budget.
    from otn_enhanced.effects import cave3, ov5_cave
    caves = {v & ~1 for m in (cave3, ov5_cave) for k, v in vars(m).items()
             if k.startswith("CAVE") and isinstance(v, int)}

    def precheck(a: int) -> bool:
        """`ldr r3,=key ; cmp r0,r3 ; bne ; movs r0,#1 ; bx lr ; ldr r3,=next|1 ; bx r3`: the list-search
        pre-check shape cards drop into dead ov3 code (effect_verify.bl_reaches), often outside any CAVE name."""
        raw = read(a, 14)
        if raw is None:
            return False
        hw = struct.unpack("<7H", raw)
        return (hw[0] >> 8 == 0x4B and hw[1] == 0x4298 and hw[2] >> 8 == 0xD1 and hw[3] == 0x2001
                and hw[4] == 0x4770 and hw[5] >> 8 == 0x4B and hw[6] == 0x4718)

    def ours(a: int) -> bool:
        return ov5_cave.OV5_NATIVE_END <= a < 0x02400000 or a in caves or precheck(a)

    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    if is_site:
        raw = read(site, 4)
        if raw is None:
            return set()
        h1, h2 = struct.unpack("<HH", raw)
        if h1 >> 11 != 0b11110 or h2 >> 11 not in (0b11111, 0b11101):
            return set()
        off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
        start = site + 4 + (off - (1 << 23) if off & (1 << 22) else off)
    else:
        start = site
    seen_nodes, found, nodes = set(), set(), [start & ~1]
    while nodes and len(seen_nodes) < max_nodes:
        node = nodes.pop()
        found.add(node)
        if node in seen_nodes or not ours(node):
            continue
        seen_nodes.add(node)
        pcs, seen_pc = [node], set()
        while pcs and len(seen_pc) < 256:            # one node = one stub/function body, walked by control flow
            pc = pcs.pop()
            if pc in seen_pc or (pc != node and pc in caves) or (code := read(pc, 4) or read(pc, 2)) is None:
                continue                                 # never fall through into the NEXT cave's stub
            seen_pc.add(pc)
            ins = next(md.disasm(code, pc, 1), None)
            if ins is None:
                continue
            m, ops, nxt = ins.mnemonic, ins.op_str, pc + ins.size
            if m in ("bl", "blx") and ops.startswith("#"):
                nodes.append(int(ops[1:], 16) & ~1)
                if read(nxt, 2) != b"\xc0\x46":          # `bl x ; mov r8,r8` = a tail jump: nothing after it runs
                    pcs.append(nxt)
            elif m == "ldr" and "[pc, #" in ops:
                lit = ((pc + 4) & ~3) + int(ops.rsplit("#", 1)[1].rstrip("]"), 16)
                v = read(lit, 4)
                if v is not None and (t := struct.unpack("<I", v)[0]) & 1 and read(t & ~1, 2) is not None:
                    nodes.append(t & ~1)                 # a Thumb address that a later bx/blx will jump to
                pcs.append(nxt)
            elif m == "b":
                pcs.append(int(ops[1:], 16))
            elif m.startswith("b") and len(m) == 3 and ops.startswith("#"):   # beq/bne/... : both ways
                pcs += [int(ops[1:], 16), nxt]
            elif m in ("bx", "blx") or (m == "pop" and "pc" in ops) or (m == "mov" and ops.startswith("pc")):
                if m == "blx":
                    pcs.append(nxt)
            else:
                pcs.append(nxt)
    return found

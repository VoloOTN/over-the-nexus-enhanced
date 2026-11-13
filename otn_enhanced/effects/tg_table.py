"""Shared T.G. set-code (archetype) membership-table helper for OTN (EU rom.nds).

OTN ships a DORMANT T.G. archetype: the ARM9 already contains a SORTED 19-entry u16
cid table @0x0209CB48 (set-code index 0x5C in the has_set_code ptr table 0x0209D0D8),
binary-searched by a single consumer thunk that hardcodes the count. NONE of the 19
listed cids has a card_prop record -- Konami pre-listed the whole archetype (Konami IDs
0x0E66-0x0E6C, 0x250F-0x2514, 0x2526-0x252A, 0x2552) even though the cards are absent
from this game's DB. Several of those reserved cids are the REAL Konami IDs of the T.G.
cards we are adding (0x2510 = T.G. Striker, 0x2513 = T.G. Warwolf, 0x2552 = T.G. Hyper
Librarian).

Like the X-Saber / Six Samurai tables, this table CANNOT be relocated (ARM9 has no safe
44-byte cave), so it is edited STRICTLY IN PLACE at 19 entries: to register a donor cid
as a T.G. member we DROP one reserved phantom (ideally the card's own reserved Konami ID)
and INSERT the donor cid, keeping the run sorted so the binary-search thunk (which
hardcodes count 0x13) keeps reading it correctly. This is the identical count-neutral
"phantom swap" the Watt / Karakuri / Six Samurai patches use.

`add_tg_member(out_path, insert_cid, phantom_cid)` performs one such swap. Stacking the
Striker patch (adds Fear Monger 0x1A64, drops phantom 0x2510) and the Warwolf patch (adds
Emissary 0x1796, drops phantom 0x2513) yields both donors registered as real T.G.
members with the table still a sorted 19 entries and every native T.G. card intact --
the two swaps are independent (distinct phantoms) so they compose cleanly.
"""
from __future__ import annotations

import struct

import ndspy.code
import ndspy.rom

from otn_enhanced.effects.common import ARM9_BASE


def force_name_in_place(out_path: str, donor_cid: int, name: bytes,
                        langs: str = "efgisjkr") -> None:
    """Overwrite a donor's card name IN-PLACE using the name blob's trailing NUL-PADDING run.

    apply_stats_and_text measures the available space as the CURRENT string's length, so it skips
    any new name longer than the donor's original (e.g. "Ally Mind" 9B -> "TG Striker" 10B) even
    when the blob has NUL padding to spare. The real writable space is the run from this card's
    name offset to the NEXT name's offset -- everything between is the current string plus its NUL
    padding and is safe to overwrite.

    Writes only when the new name + its NUL terminator fits that run, so the blob NEVER GROWS.
    (Growing/repointing a name blob is a twice-confirmed freeze: the game locks up the moment the
    card is highlighted. Shorten the name to the run instead.) Per-language: skipped when the run
    is genuinely too small -- Korean runs are ~4-12B and usually cannot hold a Latin name.
    """
    import struct as _struct
    from otn_enhanced.data.card_stats import iter_paths, rebuild_v1_pac
    from otn_enhanced.data.card_text import CARD_TEXT
    from otn_enhanced.rom.pac import parse_pac

    # OBSOLETE for any card in card_text.CARD_TEXT. This helper exists only to
    # squeeze a name into the donor's NUL-padding run, because growing the blob
    # used to be believed fatal. It is not: the real rule is that a blob must be
    # RE-EMITTED IN INDEX ORDER, never appended to (card_text.py). Those cards
    # already have their full printed name from apply_stats_and_text, and running
    # this afterwards would overwrite it with the abbreviated one -- which is
    # exactly what left T.G. Striker and T.G. Rush Rhino short in the
    # chain build.
    if donor_cid in CARD_TEXT:
        print(f"  force_name_in_place: 0x{donor_cid:04X} is in card_text -- skipped "
              f"(full printed name already written)")
        return

    rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
    pac_path = next(p for p in iter_paths(rom.filenames) if p.lower().endswith("bin2.pac"))
    fid = rom.filenames.idOf(pac_path)
    orig = bytes(rom.files[fid])
    arch = parse_pac(orig, pac_path)

    def _of(f):
        return orig[f.address:f.address + f.size]

    cpf = next(f for f in arch.files if f.get_clean_name().lower() == "card_prop.bin")
    cp = _of(cpf)
    n = (cpf.size - 8) // 8
    idx = next((i for i in range(n)
                if (int.from_bytes(cp[8 + i * 8:8 + i * 8 + 8], "little") & 0x3FFF) == donor_cid), None)
    assert idx is not None, f"card_prop record for 0x{donor_cid:04X} not found"

    modified: dict = {}
    for L in langs:
        idxf = next((f for f in arch.files if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
        namef = next((f for f in arch.files if f.get_clean_name().lower() == f"card_name_{L}.bin"), None)
        if not (idxf and namef):
            continue
        ib = modified.get(idxf.address, _of(idxf))
        nb = bytearray(modified.get(namef.address, _of(namef)))
        noff = _struct.unpack_from("<I", ib, 8 + idx * 8)[0]
        # available in-place run = distance to the next name's start.
        offs = [_struct.unpack_from("<I", ib, 8 + j * 8)[0] for j in range(n)]
        nxt = min((o for o in offs if o > noff), default=len(nb))
        run = nxt - noff
        if len(name) + 1 <= run:
            nb[noff:noff + len(name)] = name
            nb[noff + len(name)] = 0
            for k in range(noff + len(name) + 1, nxt):   # NUL-pad the rest: byte-length unchanged
                nb[k] = 0
            modified[namef.address] = bytes(nb)
            print(f"  [{L}] name -> {name!r} in-place (run {run}B)")
        else:
            print(f"  [{L}] name kept (run {run}B < {len(name) + 1}B needed)")

    if modified:
        rom.files[fid] = rebuild_v1_pac(orig, arch, modified)
        rom.saveToFile(out_path)

# ---------------------------------------------------------------------------
# Shared on-DESTRUCTION End-Phase-trigger arming (used by all three T.G. cards)
# ---------------------------------------------------------------------------
# Each card's End-Phase deck-search needs its cid "armed" when it is DESTROYED on the field and
# sent to the GY, via the per-cid leave-switch entry 0x021C8216. One hook can host only ONE
# trampoline, so a SINGLE shared trampoline scans a zero-terminated cid list in the cave and, if
# r4 (the departing cid) matches ANY entry AND the leave was a destruction ([sp+0x90]), branches
# to the GY gate 0x021CA640; otherwise it replays the two displaced ops (MOV R1,#0x77 ;
# LSL R1,R1,#6) and returns. Each patch calls arm_tg_leave_trigger(rom, ov, cid) to install the
# hook (idempotent) and append its cid to the list.
#
# NOTE: this trampoline was originally cloned from darksoul.py, where firing on ANY leave is
# correct for that card. The T.G. cards need "destroyed on the field and sent to the GY", so the
# [sp+0x90] DESTROYED test below is REQUIRED -- without it Tribute Summon fodder and Synchro
# Material also armed the search (both send to the GY, so the gate's own [sp+0x144] test passes).
LEAVE_HOOK_SITE = 0x021C8216
LEAVE_HOOK_NATIVE = (0x2177, 0x0189)   # MOV R1,#0x77 ; LSL R1,R1,#6
LEAVE_GATE = 0x021CA640

# Shooting Quasar Dragon takes an IMMEDIATE leave action rather than the T.G. End-Phase
# arm, so the shared trampoline routes its cid to its own stub. Declared here (not imported
# from shooting_quasar) to keep this module free of a circular import; the two must
# agree, which the Quasar patch asserts at build time.
IMMEDIATE_CID = 0x211B                       # Shooting Quasar Dragon (Majestic Star donor)
IMMEDIATE_ACTION = 0x0239B688                # == ov5_cave.CAVE_QSR_LEAVE
IMMEDIATE_ACTION3 = 0x022379EC               # == cave3.CAVE3_QSR_LEAVE -- the DEFAULT  
OV3_RAM_BASE = 0x02141700       # overlay-3 RAM base (offset = addr - this)

# ov3 compaction Phase D: with ov3=True the three shared trampolines and their
# tables live in the ov3 pool (cave3.CAVE3_TGSH_*; needs step 0), so the hooks stay resident in a
# puzzle, where ov41 evicts ov5. ov3=None means OV3_HOME, which every registrant in the chain
# shares. True (default), so EVERY
# registrant's row / list entry lands in the ov3 table. Needs step 0 (ov3_compact) first.
OV3_HOME = True


def _ov3(ov3):
    return OV3_HOME if ov3 is None else ov3


def _put3(ov: bytearray, addr: int, blob: bytes, code: bool = True) -> None:
    """Write *blob* into an ov3 pool slot that must be zero (step 0 ran) or already hold it."""
    from otn_enhanced.effects import cave3
    if code:
        cave3._checked(addr, len(blob), blob, "")
    o = addr - OV3_RAM_BASE
    assert bytes(ov[o:o + len(blob)]) in (bytes(len(blob)), blob), (
        f"ov3 slot @{addr:#x} is not zero -- step 0 (ov3_compact) must run first")
    ov[o:o + len(blob)] = blob


def _u16_list(buf, off: int) -> list[int]:
    """The zero-terminated u16 cid list (max 7 + terminator) at *off* in *buf*."""
    out = []
    for i in range(7):
        v = struct.unpack_from("<H", buf, off + 2 * i)[0]
        if v == 0:
            break
        out.append(v)
    return out


def _append3(ov: bytearray, addr: int, cid: int, what: str) -> None:
    o = addr - OV3_RAM_BASE
    cids = _u16_list(ov, o)
    if cid not in cids:
        assert len(cids) < 7, f"T.G. {what} cid list is full (0x10 bytes / 7 cids)"
        struct.pack_into("<H", ov, o + 2 * len(cids), cid)


def _hook_target(ov, site: int):
    """BL target at an ov3 hook *site* (None if it is not a BL)."""
    hi, lo = struct.unpack_from("<2H", ov, site - OV3_RAM_BASE)
    if hi >> 11 != 0x1E or lo >> 11 != 0x1F:
        return None
    off = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
    return (site + 4 + (off - 0x800000 if off & 0x400000 else off)) & 0xFFFFFFFF


def _shared_arm_trampoline(tramp_addr: int, list_addr: int,
                           immediate: int = IMMEDIATE_ACTION3) -> bytes:
    """Assemble the shared multi-cid on-destruction arming trampoline (Thumb-1).

    Installed over the leave-switch entry 0x021C8216 (called via BL, so LR = 0x021C821A).
    r4 = the departing card's cid. Scans the zero-terminated u16 cid list at *list_addr*;
    if r4 matches an entry AND the leave was a destruction ([sp+0x90]), BX into the GY gate
    0x021CA640 (which flags the card "left the field this turn"); else replays the two
    displaced ops and BX LR.
    """
    from otn_enhanced.asm.effect_builder import EffectBuilder
    from otn_enhanced.asm.effect_verify import assert_thumb1_only
    a = EffectBuilder()
    a.ldr_const(2, list_addr)             # r2 = &cid_list
    a.label("scan")
    a.insn("LDRH", "R1, [R2, #0x0]")      # r1 = list entry
    a.insn("CMP", "R1, #0x0")
    a.insn("BEQ", "other")                # end of list (0 terminator) -> not a T.G. cid
    a.insn("CMP", "R4, R1")
    a.insn("BEQ", "match")                # departing cid is one of ours
    a.insn("ADD", "R2, R2, #0x2")
    a.insn("B", "scan")
    a.label("match")
    # E2 fires only on DESTRUCTION (battle or effect), never on tribute / Synchro Material /
    # cost. The leave dispatcher (0x021C7FCC) unpacked its packed descriptor [sp+0x200] into
    # named stack slots at 0x021C7FD6-0x021C80BA -- well before this hook -- so [sp+0x90]
    # (= descriptor bit 15, DESTROYED) is live here. SP is intact: we are entered by BL and
    # this stub pushes nothing. The gate 0x021CA640 already enforces destination == GY
    # ([sp+0x144]) and the controller check, so DESTROYED is the only predicate missing;
    # together they are the native requirement mask 0x0C04 that the engine ships on the real
    # T.G. cids 0x0E66..0x0E6C in the leave-requirement table at 0x0226EC1C.
    a.insn("LDR", "R1, [SP, #0x90]")      # r1 = DESTROYED flag
    a.insn("CMP", "R1, #0x0")
    a.insn("BEQ", "other")                # left the field but not destroyed -> no trigger
    # --- Shooting Quasar takes an IMMEDIATE action instead of the End-Phase gate. ---
    # The T.G. cards arm a Darksoul-timed End-Phase trigger; Quasar must Special Summon
    # "Shooting Star Dragon" right away, so its cid is routed to its own stub. This branch
    # is UNREACHABLE unless shooting_quasar has also added 0x211B to the cid list
    # above, so the bytes are safe to emit unconditionally -- which keeps this trampoline
    # byte-identical no matter which patch in the chain installs it first (install_cave
    # relies on that idempotence).
    a.ldr_const(1, IMMEDIATE_CID)
    a.insn("CMP", "R4, R1")
    a.insn("BNE", "gate")
    a.ldr_const(1, immediate | 1)
    a.insn("BX", "R1")                    # -> Quasar's immediate leave action
    a.label("gate")
    a.ldr_const(1, LEAVE_GATE | 1)
    a.insn("BX", "R1")                    # -> gate arms the End-Phase trigger for r4=cid
    a.label("other")
    a.insn("MOV", "R1, #0x77")            # replay 0x021C8216
    a.insn("LSL", "R1, R1, #6")           # replay 0x021C8218
    a.insn("BX", "LR")                    # return to 0x021C821A
    code = a.assemble(tramp_addr)
    assert_thumb1_only(code, tramp_addr)
    return code


def arm_tg_leave_trigger(rom, ov: bytearray, cid: int, ov3=None,
                         immediate: int = IMMEDIATE_ACTION3) -> None:
    """Install the shared any-leave arming trampoline + register *cid* (idempotent).

    Grows/writes the shared trampoline cave, installs the hook at 0x021C8216 (if not already),
    and appends *cid* to the zero-terminated cid list. Safe to call from both T.G. patches; the
    order they run in does not matter. ov3=True: trampoline + list in the ov3 pool.
    """
    from otn_enhanced.effects import ov5_cave

    if _ov3(ov3):
        from otn_enhanced.effects import cave3
        TRAMP, LIST = cave3.CAVE3_TGSH_ARMTRAMP, cave3.CAVE3_TGSH_ARMLIST
        _put3(ov, TRAMP, _shared_arm_trampoline(TRAMP, LIST, immediate))
        _append3(ov, LIST, cid, "arming")
    else:
        TRAMP = ov5_cave.CAVE_TG_ARMTRAMP
        LIST = ov5_cave.CAVE_TG_ARMLIST
        _arm_ov5(rom, TRAMP, LIST, cid)
    _arm_hook(ov, TRAMP, cid)


def _arm_ov5(rom, TRAMP: int, LIST: int, cid: int) -> None:
    from otn_enhanced.effects import ov5_cave
    # 1. install the shared trampoline stub (idempotent -- same bytes each time).
    tramp = _shared_arm_trampoline(TRAMP, LIST)
    # install_cave asserts the slot is zero before writing; guard idempotency by reading first.
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    already = bytes(ov5.data[TRAMP - ov5_cave.OV5_RAM_BASE: TRAMP - ov5_cave.OV5_RAM_BASE + len(tramp)]) == tramp \
        if len(ov5.data) >= (TRAMP - ov5_cave.OV5_RAM_BASE + len(tramp)) else False
    if not already:
        ov5_cave.install_cave(rom, TRAMP, tramp, reserve=0x40)

    # 2. append cid to the zero-terminated list in the cave (idempotent).
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    data = bytearray(ov5.data)
    lo = LIST - ov5_cave.OV5_RAM_BASE
    entries = []
    i = lo
    while i + 2 <= lo + 0x10:
        v = struct.unpack_from("<H", data, i)[0]
        if v == 0:
            break
        entries.append(v)
        i += 2
    if cid not in entries:
        assert len(entries) < 7, "T.G. arming cid list is full (0x10 bytes / 7 cids)"
        struct.pack_into("<H", data, lo + len(entries) * 2, cid)   # append (list stays zero-terminated)
        ov5.data = bytes(data)
        # persist the ov5 change (install_cave already grew/registered ov5; just re-save its data)
        compressed = ov5.save(compress=ov5.compressed)
        rom.files[ov5.fileID] = compressed
        tbl = rom.arm9OverlayTable
        entry = ov5_cave.OV5_ID * 32
        struct.pack_into("<I", tbl, entry + 0x08, len(data))
        flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
        struct.pack_into("<I", tbl, entry + 0x1C,
                         ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


def _arm_hook(ov: bytearray, TRAMP: int, cid: int) -> None:
    from otn_enhanced.effects.common import thumb_bl as _thumb_bl
    # 3. install the hook at the leave-switch entry (idempotent).
    want = struct.unpack("<2H", _thumb_bl(LEAVE_HOOK_SITE, TRAMP))
    cur = struct.unpack_from("<2H", ov, LEAVE_HOOK_SITE - OV3_RAM_BASE)
    if cur == want:
        print(f"T.G. leave-arm hook @0x{LEAVE_HOOK_SITE:08X}: already installed; cid 0x{cid:04X} registered")
    else:
        assert cur == LEAVE_HOOK_NATIVE, (
            f"leave hook @0x{LEAVE_HOOK_SITE:08X} = {cur[0]:04X} {cur[1]:04X} "
            f"(expected native {LEAVE_HOOK_NATIVE[0]:04X} {LEAVE_HOOK_NATIVE[1]:04X})")
        struct.pack_into("<2H", ov, LEAVE_HOOK_SITE - OV3_RAM_BASE, *want)
        print(f"T.G. shared leave-arm trampoline @0x{TRAMP:08X}; hook @0x{LEAVE_HOOK_SITE:08X}; "
              f"cid 0x{cid:04X} registered")


# ---------------------------------------------------------------------------
# Shared multi-cid End-Phase registry-INVOKE trampoline (Rush Rhino onward)
# ---------------------------------------------------------------------------
# The End-Phase deck-search needs the registrar 0x02254221 (End-Phase-trigger scheduler) INVOKED for
# the donor cid at End Phase. Striker/Warwolf did this by STEALING one of the two spare phantom
# 0x02254221 registry rows (0x1A9F / 0x2347); both are now consumed and every other 0x02254221 row is
# a real card. So instead of sacrificing a card, a SINGLE shared trampoline invokes 0x02254221 for each
# cid in a zero-terminated list -- the same multi-cid pattern as the leave-arm / hand-SS trampolines.
#
# 0x02254221 is a thunk `MOV R2,#0xE; BX 0x02254121` (=0x02254120 body): it schedules the End-Phase
# trigger for the (ctx, cid) it is called with. GDB bring-up pinned the walker's per-row
# dispatch at 0x02256716 (`BLX R2` with R1=row.cid, R2=row.resolver, R0=ctx, R6=row index). The shared
# trampoline replaces the 4 bytes `BLX R2; CMP R0,#0` there: it calls the row's real resolver, and ONCE
# per walk (first row) invokes 0x02254221(0, cid) for each listed T.G. cid -- so records-free donors get
# their End-Phase trigger scheduled with NO registry row stolen and every real row still dispatched.
ENDPHASE_REGISTRAR = 0x02254221        # End-Phase-trigger scheduler (invoked per listed cid)
REG_WALK_HOOK_SITE = 0x02256716        # walker `BLX R2` dispatch site (GDB-pinned)
REG_WALK_HOOK_NATIVE = (0x4790, 0x2800)  # displaced `BLX R2` + `CMP R0,#0` (the trampoline replays both)


def _shared_reg_invoke_trampoline(tramp_addr: int, list_addr: int) -> bytes:
    """Assemble the shared multi-cid End-Phase registry-invoke trampoline (Thumb-1).

    GDB-PINNED SITE & CONVENTION (2026-07-13): the End-Phase registry walker
    (overlay 3) dispatches each row's resolver at 0x02256716 with:
        0x02256710: LDR R1,[row+4]   ; R1 = row.cid
        0x02256712: LDR R2,[row+0]   ; R2 = row.resolver (0x02254221 for End-Phase rows)
        0x02256714: ADD R0,R7,#0     ; R0 = ctx (R7, observed 0)
        0x02256716: BLX R2           ; resolver(R0=ctx, R1=cid) -> R0 (nonzero => stop the walk)
        0x02256718: CMP R0,#0
        0x0225671A: BNE ...          ; matched -> stop
        (R6 = row index, counts 0..0xE0)
    We hook the 4 bytes at 0x02256716 (`BLX R2` + `CMP R0,#0`) with a `BL` here. The trampoline:
      1. calls the row's real resolver `BLX R2` (R0=ctx, R1=cid) exactly as before, saving its result;
      2. ONCE per walk (on the first row, R6==0) invokes the End-Phase registrar 0x02254221(ctx=0,
         cid) for each cid in the zero-terminated list -- scheduling our records-free T.G. donors'
         End-Phase triggers (they have no registry row of their own);
      3. returns the real resolver's result in R0 with the Z flag set as `CMP R0,#0` would, so the
         walker's following `BNE` behaves identically.
    Non-destructive: no registry row stolen, every real row still dispatches normally.

    Thumb-1 note: `POP` restores PC only, never LR (see repo memory thumb-pop-into-lr-footgun); we keep
    live values in callee-saved regs and return via the stacked LR.
    """
    from otn_enhanced.asm.effect_builder import EffectBuilder
    from otn_enhanced.asm.effect_verify import assert_thumb1_only
    a = EffectBuilder()
    a.insn("PUSH", "{R4, R5, R6, R7, LR}")
    a.insn("ADD", "R7, R6, #0x0")          # r7 = row index (was R6; preserved)
    a.insn("ADD", "R6, R0, #0x0")          # r6 = ctx (preserved)
    # 1. call the row's real resolver (R0=ctx, R1=cid, R2=resolver) -> result in r4
    a.insn("BLX", "R2")
    a.insn("ADD", "R4, R0, #0x0")          # r4 = real resolver result (walk-stop signal)
    # 2. schedule our T.G. cids EXACTLY ONCE per End Phase. The walk runs 4 outer passes (R5=0..3);
    #    the walker writes the pass phase to two globals: [0x0229DD94] = R5&1 and [0x0229AB7C+0x18] =
    #    (R5>=2). Gating on row index 0 alone recurs every pass (=> double search); also require BOTH
    #    phase globals == 0, i.e. the R5==0 pass only -> fires once.
    a.insn("CMP", "R7, #0x0")              # first row of the pass?
    a.insn("BNE", "done")
    a.ldr_const(0, 0x0229DD94)             # phase-lo global = R5&1
    a.insn("LDR", "R0, [R0, #0x0]")
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "done")                  # not the R5&1==0 half
    a.ldr_const(0, 0x0229AB7C)             # phase-hi global @+0x18 = (R5>=2)
    a.insn("LDR", "R0, [R0, #0x18]")
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "done")                  # R5>=2 -> not the first pass
    a.ldr_const(5, list_addr)              # r5 = &cid_list
    a.label("scan")
    a.insn("LDRH", "R1, [R5, #0x0]")       # r1 = list cid
    a.insn("CMP", "R1, #0x0")
    a.insn("BEQ", "done")                  # end of list
    a.insn("MOV", "R0, #0x0")              # r0 = ctx (0, as the walker passes)
    a.ldr_const(2, ENDPHASE_REGISTRAR | 1)
    a.insn("BLX", "R2")                    # 0x02254221(ctx=0, cid) -> schedule End-Phase trigger
    a.insn("ADD", "R5, #0x2")              # next cid (2-op ADD -> no imm3 footgun)
    a.insn("B", "scan")
    a.label("done")
    a.insn("ADD", "R0, R4, #0x0")          # restore the real resolver's result
    a.insn("CMP", "R0, #0x0")              # set Z flag exactly like the displaced `CMP R0,#0`
    a.insn("POP", "{R4, R5, R6, R7, PC}")
    code = a.assemble(tramp_addr)
    assert_thumb1_only(code, tramp_addr)
    return code


def invoke_tg_endphase(rom, ov: bytearray, cid: int, ov3=None) -> None:
    """Install the shared End-Phase registry-invoke trampoline + register *cid* (idempotent).

    Writes/refreshes the shared trampoline stub and appends *cid* to its zero-terminated cid list, so
    the End-Phase registrar 0x02254221 is invoked for *cid* at End Phase WITHOUT stealing a registry
    row. The 4-byte hook at the registry walker's per-row dispatch is installed by the caller once its
    site is GDB-pinned (this function is the stub/list half so the two compose like the other shared
    T.G. trampolines).
    """
    from otn_enhanced.effects import ov5_cave

    if _ov3(ov3):
        from otn_enhanced.effects import cave3
        TRAMP, LIST = cave3.CAVE3_TGSH_REGTRAMP, cave3.CAVE3_TGSH_REGLIST
        _put3(ov, TRAMP, _shared_reg_invoke_trampoline(TRAMP, LIST))
        _append3(ov, LIST, cid, "End-Phase-invoke")
    else:
        TRAMP = ov5_cave.CAVE_TG_REGTRAMP
        LIST = ov5_cave.CAVE_TG_REGLIST
        _reg_ov5(rom, TRAMP, LIST, cid)
    _reg_hook(ov, TRAMP)


def _reg_ov5(rom, TRAMP: int, LIST: int, cid: int) -> None:
    from otn_enhanced.effects import ov5_cave
    # 1. install the shared trampoline stub (idempotent -- same bytes each time).
    tramp = _shared_reg_invoke_trampoline(TRAMP, LIST)
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    lo_tr = TRAMP - ov5_cave.OV5_RAM_BASE
    already = (len(ov5.data) >= lo_tr + len(tramp)
               and bytes(ov5.data[lo_tr:lo_tr + len(tramp)]) == tramp)
    if not already:
        ov5_cave.install_cave(rom, TRAMP, tramp, reserve=0x50)

    # 2. append cid to the zero-terminated list in the cave (idempotent).
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    data = bytearray(ov5.data)
    lo = LIST - ov5_cave.OV5_RAM_BASE
    entries = []
    i = lo
    while i + 2 <= lo + 0x10:
        v = struct.unpack_from("<H", data, i)[0]
        if v == 0:
            break
        entries.append(v)
        i += 2
    if cid not in entries:
        assert len(entries) < 7, "T.G. End-Phase-invoke cid list is full (0x10 bytes / 7 cids)"
        struct.pack_into("<H", data, lo + len(entries) * 2, cid)   # append (list stays zero-terminated)
        _persist_ov5(rom, data)
        print(f"T.G. shared End-Phase-invoke trampoline @0x{TRAMP:08X}; cid 0x{cid:04X} registered")
    else:
        print(f"T.G. End-Phase-invoke: cid 0x{cid:04X} already registered -> no change")


def _reg_hook(ov: bytearray, TRAMP: int) -> None:
    # 3. install the 4-byte hook at the GDB-pinned walker dispatch site (idempotent). Replaces the
    #    displaced `BLX R2; CMP R0,#0` with a `BL` into the trampoline (which replays both).
    from otn_enhanced.effects.common import thumb_bl as _thumb_bl
    want = struct.unpack("<2H", _thumb_bl(REG_WALK_HOOK_SITE, TRAMP))
    cur = struct.unpack_from("<2H", ov, REG_WALK_HOOK_SITE - OV3_RAM_BASE)
    if cur == want:
        print(f"T.G. End-Phase reg-walk hook @0x{REG_WALK_HOOK_SITE:08X}: already installed")
    else:
        assert cur == REG_WALK_HOOK_NATIVE, (
            f"reg-walk hook @0x{REG_WALK_HOOK_SITE:08X} = {cur[0]:04X} {cur[1]:04X} "
            f"(expected native BLX R2/CMP {REG_WALK_HOOK_NATIVE[0]:04X} {REG_WALK_HOOK_NATIVE[1]:04X})")
        struct.pack_into("<2H", ov, REG_WALK_HOOK_SITE - OV3_RAM_BASE, *want)
        print(f"T.G. End-Phase reg-walk hook @0x{REG_WALK_HOOK_SITE:08X}: "
              f"BLX R2/CMP -> BL 0x{TRAMP:08X} (shared registry-invoke)")


TG_TBL = 0x0209CB48             # RAM address of the sorted 19-entry T.G. cid table (EU rom.nds)
TG_COUNT = 0x13                 # 19 entries (the consumer thunk hardcodes this count)
TG_SETCODE = 0x5C               # T.G. set-code index in the has_set_code ptr table 0x0209D0D8

# The single consumer thunk (used only to sanity-check the table addr + count before edit).
TG_POOL_PTR = 0x02023F3C        # 4-aligned word holding the table address
TG_COUNT_IMM = 0x02023F38       # `movs r2,#0x13` halfword feeding the bsearch count

# The 19 native (phantom) entries the game ships. Asserted before the first swap so a
# wrong base ROM fails loudly; after a swap the table diverges from this by exactly the
# swapped pair(s).
TG_NATIVE = (0x0E66, 0x0E67, 0x0E68, 0x0E69, 0x0E6A, 0x0E6B, 0x0E6C,
             0x250F, 0x2510, 0x2511, 0x2512, 0x2513, 0x2514,
             0x2526, 0x2527, 0x2528, 0x2529, 0x252A, 0x2552)


def _open(out_path: str):
    """Open the ROM and return (rom, mc, sec, bytearray(sec.data)) for ARM9 main."""
    rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
    return rom, mc, sec, bytearray(sec.data)


# ---------------------------------------------------------------------------
# Shared hand-SS "can Special Summon from hand" flag-forcing (Striker & Warwolf)
# ---------------------------------------------------------------------------
# The hand-SS OFFER is gated by dispatch fn 0x0225E51C (returns flags in r0; bit 0x4 = "can SS from
# hand"), consulted by the hand menu at 0x0224C026 (BL 0x0225E51C; ORR R5,R0). One hook site can host
# ONE trampoline, but both T.G. cards need to force bit 0x4 under their own condition. So a SINGLE
# shared trampoline replays the dispatch and walks a {cid u16, cond-stub-ptr u32}[] table (zero-
# terminated): for r6==cid it calls that card's condition stub (r0 = side, from the caller) and, if
# the stub returns nonzero, ORs bit 0x4 into the flags. Each patch registers its (cid, cond-stub).
SS_HOOK_SITE = 0x0224C026
SS_HOOK_NATIVE = (0xF012, 0xFA79)      # native BL 0x0225E51C at the hand-menu call site
SS_DISPATCH = 0x0225E51C               # the eligibility dispatch the trampoline replays
SS_FLAG = 0x4                          # bit set = "can Special Summon this card from hand"
SS_TABLE_BYTES = 0x80                  # ov5_cave.CAVE_TG_SSTABLE reserve: 15 rows + zero terminator (was 0x40 / 7, 0x20 / 3)


def _legacy_ss_tables():
    """Retired (addr, bytes) homes of the hand-SS table, newest first -- migrated on a layered build."""
    from otn_enhanced.effects import ov5_cave
    return ((ov5_cave.CAVE_TG_SSTABLE_OLD2, 0x40), (ov5_cave.CAVE_TG_SSTABLE_OLD, 0x20))


def _shared_ss_trampoline(tramp_addr: int, table_addr: int) -> bytes:
    """Assemble the shared hand-SS flag-forcing trampoline (Thumb-1).

    Installed over `BL 0x0225E51C` at 0x0224C026. At the hook r0 = side, r6 = the card's cid.
    Replays the dispatch (r0 -> flags), then scans the {cid u16, cond-ptr u32}[] table at
    *table_addr* (zero cid terminates): for the entry whose cid == r6, calls the cond stub with
    r0 = side; if it returns nonzero, ORs SS_FLAG into the flags. Returns the (possibly augmented)
    flags. Each per-card cond stub takes r0 = side and returns nonzero iff the offer should appear.
    """
    from otn_enhanced.asm.effect_builder import EffectBuilder
    from otn_enhanced.asm.effect_verify import assert_thumb1_only
    a = EffectBuilder()
    a.insn("PUSH", "{R4, R5, R6, R7, LR}")
    a.insn("ADD", "R5, R0, #0x0")          # r5 = side
    a.insn("ADD", "R4, R6, #0x0")          # r4 = this card's cid
    a.bl(SS_DISPATCH)                       # replay dispatch -> r0 = native flags
    a.insn("ADD", "R7, R0, #0x0")          # r7 = native flags (preserved)
    a.ldr_const(6, table_addr)             # r6 = &dispatch table
    a.label("scan")
    a.insn("LDRH", "R0, [R6, #0x0]")       # entry cid
    a.insn("CMP", "R0, #0x0")
    a.insn("BEQ", "done")                  # zero cid = end of table
    a.insn("CMP", "R0, R4")
    a.insn("BEQ", "hit")
    a.insn("ADD", "R6, #0x8")              # next entry (stride 8: cid@+0, cond-ptr@+4, word-aligned)
    #  NB: 2-operand `ADD Rd,#imm8` — the 3-operand `ADD Rd,Rn,#imm3` form caps imm at 7 and the
    #  assembler silently miscoded `ADD R6,R6,#0x8` as `SUB R6,R6,#0x0` (infinite scan -> freeze).
    a.insn("B", "scan")
    a.label("hit")
    a.insn("LDR", "R1, [R6, #0x4]")        # r1 = cond-stub ptr (Thumb, LSB set; word-aligned @+4)
    a.insn("ADD", "R0, R5, #0x0")          # r0 = side (cond-stub arg)
    a.insn("BLX", "R1")                    # r0 = cond result
    a.insn("CMP", "R0, #0x0")
    a.insn("BEQ", "done")                  # condition false -> leave flags as-is
    a.insn("MOV", "R0, #0x4")              # SS_FLAG
    a.insn("ORR", "R7, R0")
    a.label("done")
    a.insn("ADD", "R0, R7, #0x0")
    a.insn("POP", "{R4, R5, R6, R7, PC}")
    code = a.assemble(tramp_addr)
    assert_thumb1_only(code, tramp_addr)
    return code


def _persist_ov5(rom, data: bytes) -> None:
    """Recompress ov5 *data*, store it, and update the overlay table (mirrors ov5_cave._save_ov5)."""
    from otn_enhanced.effects import ov5_cave
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    ov5.data = bytes(data)
    compressed = ov5.save(compress=ov5.compressed)
    rom.files[ov5.fileID] = compressed
    tbl = rom.arm9OverlayTable
    entry = ov5_cave.OV5_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(data))
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    struct.pack_into("<I", tbl, entry + 0x1C,
                     ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


def _ss_append(data: bytearray, lo: int, rows) -> None:
    """Append {cid u16 @+0, cond_ptr u32 @+4} rows (stride 8, zero-terminated) at *lo*, idempotent."""
    for row_cid, row_ptr in rows:
        n = 0
        while lo + n * 8 + 8 <= lo + SS_TABLE_BYTES and struct.unpack_from("<H", data, lo + n * 8)[0] != 0:
            if struct.unpack_from("<H", data, lo + n * 8)[0] == row_cid:
                n = -1
                break
            n += 1
        if n >= 0:
            assert (n + 2) * 8 <= SS_TABLE_BYTES, "T.G. hand-SS dispatch table is full (the last row must stay the zero terminator)"
            struct.pack_into("<HH", data, lo + n * 8, row_cid, 0)    # cid @+0, pad @+2
            struct.pack_into("<I", data, lo + n * 8 + 4, row_ptr)    # cond-ptr @+4 (word-aligned)


def register_tg_handss(rom, ov: bytearray, cid: int, cond_stub_addr: int, ov3=None) -> None:
    """Install the shared hand-SS trampoline + register (cid -> cond_stub_addr) (idempotent).

    *cond_stub_addr* is a Thumb-1 stub taking r0 = side and returning nonzero iff
    the hand-SS offer should appear for *cid*. Installs the shared trampoline + the hook at
    0x0224C026 (once), and appends {cid, cond_stub_addr|1} to the dispatch table. Safe to call from
    both T.G. patches in any order. ov3=True: trampoline + table in the ov3 pool.
    """
    from otn_enhanced.effects import ov5_cave
    from otn_enhanced.effects.common import thumb_bl as _thumb_bl

    if _ov3(ov3):
        from otn_enhanced.effects import cave3
        TRAMP, TABLE = cave3.CAVE3_TGSH_SSTRAMP, cave3.CAVE3_TGSH_SSTABLE
        _put3(ov, TRAMP, _shared_ss_trampoline(TRAMP, TABLE))
        _ss_append(ov, TABLE - OV3_RAM_BASE, [(cid, cond_stub_addr | 1)])
        _ss_hook(ov, TRAMP, cid, cond_stub_addr)
        return

    TRAMP = ov5_cave.CAVE_TG_SSTRAMP
    TABLE = ov5_cave.CAVE_TG_SSTABLE

    # 1. install the shared trampoline stub (idempotent).
    tramp = _shared_ss_trampoline(TRAMP, TABLE)
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    lo_tr = TRAMP - ov5_cave.OV5_RAM_BASE
    already = (len(ov5.data) >= lo_tr + len(tramp)
               and bytes(ov5.data[lo_tr:lo_tr + len(tramp)]) == tramp)
    rows = []                               # (cid, cond-ptr|1) to (re)register, in order
    if not already:
        # A trampoline still pointing at a retired table home (a layered build over an older
        # chain ROM): carry its rows across, or every earlier registrant silently loses its offer.
        for old, size in _legacy_ss_tables():
            if bytes(ov5.data[lo_tr:lo_tr + len(tramp)]) == _shared_ss_trampoline(TRAMP, old):
                o = old - ov5_cave.OV5_RAM_BASE
                for i in range(size // 8):
                    c, p = struct.unpack_from("<H2xI", ov5.data, o + i * 8)
                    if c == 0:
                        break
                    rows.append((c, p))
                print(f"hand-SS table: migrating {len(rows)} row(s) 0x{old:08X} -> 0x{TABLE:08X}")
                data = bytearray(ov5.data)
                data[lo_tr:lo_tr + len(tramp)] = tramp   # same length; only the table literal moved
                _persist_ov5(rom, data)
                break
        else:
            ov5_cave.install_cave(rom, TRAMP, tramp, reserve=0x40)
    rows.append((cid, cond_stub_addr | 1))

    # 2. append {cid u16 @+0, cond_ptr u32 @+4} to the dispatch table (stride 8, word-aligned,
    #    zero-terminated), idempotent.
    ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
    data = bytearray(ov5.data)
    _ss_append(data, TABLE - ov5_cave.OV5_RAM_BASE, rows)
    if bytes(data) != bytes(ov5.data):
        ov5.data = bytes(data)
        _persist_ov5(rom, data)
    _ss_hook(ov, TRAMP, cid, cond_stub_addr)


def _ss_hook(ov: bytearray, TRAMP: int, cid: int, cond_stub_addr: int) -> None:
    from otn_enhanced.effects.common import thumb_bl as _thumb_bl
    # 3. install the hook at the hand-menu call site (idempotent).
    want = struct.unpack("<2H", _thumb_bl(SS_HOOK_SITE, TRAMP))
    cur = struct.unpack_from("<2H", ov, SS_HOOK_SITE - OV3_RAM_BASE)
    if cur == want:
        print(f"T.G. hand-SS hook @0x{SS_HOOK_SITE:08X}: already installed; cid 0x{cid:04X} registered")
    else:
        assert cur == SS_HOOK_NATIVE, (
            f"hand-SS hook @0x{SS_HOOK_SITE:08X} = {cur[0]:04X} {cur[1]:04X} "
            f"(expected native {SS_HOOK_NATIVE[0]:04X} {SS_HOOK_NATIVE[1]:04X})")
        struct.pack_into("<2H", ov, SS_HOOK_SITE - OV3_RAM_BASE, *want)
        print(f"T.G. shared hand-SS trampoline @0x{TRAMP:08X}; hook @0x{SS_HOOK_SITE:08X}; "
              f"cid 0x{cid:04X} -> cond 0x{cond_stub_addr:08X}")


def _intact(ov, t, tramp3, tramp5, src3, src5, rom, tramp_blob) -> bool:
    from otn_enhanced.effects import ov5_cave
    if t == tramp3:
        buf, base, src = bytes(ov), OV3_RAM_BASE, src3
    else:
        buf = bytes(rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
        base, src = ov5_cave.OV5_RAM_BASE, src5
    blobs = tramp_blob(t, src)
    return any(buf[t - base:t - base + len(b)] == b for b in (blobs if isinstance(blobs, list) else [blobs]))


def _home(ov, site: int, tramp5: int, tramp3: int, src5: int, src3: int, rom, tramp_blob):
    """(buf, off) of the table/list whose trampoline the live hook at *site* reaches, or None.

    The trampoline bytes must also be intact at that home (catches a slot overwritten later)."""
    from otn_enhanced.effects import ov5_cave
    t = _hook_target(ov, site)
    if t is not None:
        t = ov5_cave.ik_walk(t)          # Infernoble's leave-switch front chain: follow it to its tail
    if t == tramp3:
        buf, base, src = bytes(ov), OV3_RAM_BASE, src3
    elif t == tramp5:
        buf = bytes(rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
        base, src = ov5_cave.OV5_RAM_BASE, src5
    else:
        return None
    blobs = tramp_blob(t, src)
    if not any(buf[t - base:t - base + len(b)] == b
               for b in (blobs if isinstance(blobs, list) else [blobs])):
        return None
    return buf, src - base


def tg_handss_ok(rom, ov: bytearray, cid: int) -> bool:
    """Verify the shared hand-SS hook is installed and *cid* is in the dispatch table. Read-only.
    Follows the live hook to the ov5 or ov3 home."""
    from otn_enhanced.effects import ov5_cave
    from otn_enhanced.effects import cave3
    h = _home(ov, SS_HOOK_SITE, ov5_cave.CAVE_TG_SSTRAMP, cave3.CAVE3_TGSH_SSTRAMP,
              ov5_cave.CAVE_TG_SSTABLE, cave3.CAVE3_TGSH_SSTABLE, rom, _shared_ss_trampoline)
    if h is None:
        return False
    buf, lo = h
    for n in range(SS_TABLE_BYTES // 8):
        c = struct.unpack_from("<H", buf, lo + n * 8)[0]
        if c == 0:
            return False
        if c == cid:
            return True
    return False


def handss_cond_ptr(rom, ov: bytearray, cid: int) -> int | None:
    """The cond-stub pointer (Thumb bit cleared) the live hand-SS table holds for *cid*, or None.
    Lets a card's verify() find its stub in either the ov5 cave or the ov3 pool."""
    from otn_enhanced.effects import ov5_cave
    from otn_enhanced.effects import cave3
    h = _home(ov, SS_HOOK_SITE, ov5_cave.CAVE_TG_SSTRAMP, cave3.CAVE3_TGSH_SSTRAMP,
              ov5_cave.CAVE_TG_SSTABLE, cave3.CAVE3_TGSH_SSTABLE, rom, _shared_ss_trampoline)
    if h is None:
        return None
    buf, lo = h
    for n in range(SS_TABLE_BYTES // 8):
        c = struct.unpack_from("<H", buf, lo + n * 8)[0]
        if c == 0:
            return None
        if c == cid:
            return struct.unpack_from("<I", buf, lo + n * 8 + 4)[0] & ~1
    return None


def CAVE_TG_ARM_OK(rom, ov: bytearray, cid: int) -> bool:
    """Verify the shared any-leave arming: hook installed at 0x021C8216 -> the shared trampoline,
    and *cid* present in the trampoline's cid list. Read-only. Follows the live hook to ov5 or ov3."""
    from otn_enhanced.effects import ov5_cave
    from otn_enhanced.effects import cave3
    h = _home(ov, LEAVE_HOOK_SITE, ov5_cave.CAVE_TG_ARMTRAMP, cave3.CAVE3_TGSH_ARMTRAMP,
              ov5_cave.CAVE_TG_ARMLIST, cave3.CAVE3_TGSH_ARMLIST, rom,
              lambda t, l: [_shared_arm_trampoline(t, l, i) for i in (IMMEDIATE_ACTION, IMMEDIATE_ACTION3)])
    return h is not None and cid in _u16_list(*h)


def tg_reg_ok(rom, ov: bytearray, cid: int) -> bool:
    """Verify the shared End-Phase invoke hook + *cid* in its list. Read-only; ov5 or ov3 home."""
    from otn_enhanced.effects import ov5_cave
    from otn_enhanced.effects import cave3
    h = _home(ov, REG_WALK_HOOK_SITE, ov5_cave.CAVE_TG_REGTRAMP, cave3.CAVE3_TGSH_REGTRAMP,
              ov5_cave.CAVE_TG_REGLIST, cave3.CAVE3_TGSH_REGLIST, rom, _shared_reg_invoke_trampoline)
    return h is not None and cid in _u16_list(*h)


def add_tg_member(out_path: str, insert_cid: int, phantom_cid: int) -> None:
    """Register *insert_cid* as a T.G. member IN PLACE, dropping *phantom_cid*.

    Keeps the table a sorted 19 entries so the binary-search consumer thunk (which
    hardcodes count 0x13) keeps reading it correctly. Idempotent: if *insert_cid* is
    already present, nothing changes. *phantom_cid* MUST be one of the reserved (no
    card_prop) entries currently in the table -- pass the donor card's own reserved
    Konami ID so the slot literally reserved for that card now points at our donor.
    """
    rom, mc, sec, d = _open(out_path)

    def off(addr: int) -> int:                                  # RAM address -> section-buffer offset
        return addr - ARM9_BASE

    # Sanity: the consumer still points at the table with the hardcoded count 19.
    ptr = struct.unpack_from("<I", d, off(TG_POOL_PTR))[0]
    assert ptr == TG_TBL, (
        f"T.G. consumer pool @0x{TG_POOL_PTR:08X} = 0x{ptr:08X} (expected 0x{TG_TBL:08X}); "
        f"refusing to patch a moved table"
    )
    imm = struct.unpack_from("<H", d, off(TG_COUNT_IMM))[0]
    assert imm == (0x2200 | TG_COUNT), (
        f"T.G. count immediate @0x{TG_COUNT_IMM:08X} = 0x{imm:04X} (expected movs r2,#0x13)"
    )

    cur = list(struct.unpack_from(f"<{TG_COUNT}H", d, off(TG_TBL)))   # current 19-entry table

    if insert_cid in cur:                                        # idempotent
        print(f"T.G. set-code: 0x{insert_cid:04X} already present -> no change")
        return

    assert phantom_cid in cur, (
        f"T.G. set-code: phantom 0x{phantom_cid:04X} not present to drop "
        f"(table = {[hex(x) for x in cur]})"
    )

    new_tbl = tuple(sorted((set(cur) - {phantom_cid}) | {insert_cid}))   # drop one, add one, re-sort
    assert len(new_tbl) == TG_COUNT and all(                    # still exactly 19, strictly ascending
        new_tbl[i] < new_tbl[i + 1] for i in range(len(new_tbl) - 1)
    ), f"resulting T.G. table is not a sorted {TG_COUNT}-entry set: {[hex(x) for x in new_tbl]}"

    struct.pack_into(f"<{TG_COUNT}H", d, off(TG_TBL), *new_tbl)  # write back in place (same addr/size)
    sec.data = bytes(d)
    rom.arm9 = mc.save()
    rom.saveToFile(out_path)

    print(f"T.G. set-code: in-place table @0x{TG_TBL:08X} (count {TG_COUNT}); "
          f"dropped phantom 0x{phantom_cid:04X}, inserted 0x{insert_cid:04X}")
    print(f"  entries: {', '.join(f'0x{v:04X}' for v in new_tbl)}")

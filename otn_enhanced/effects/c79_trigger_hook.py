"""The SHARED N-or-SS ("If this card is Normal or Special Summoned") trigger hook: one stub, a REGISTER of cids.

The twin of summon_trigger_hook.py, one list over.  The summon-trigger evaluator 0x02265768 searches the
code-7-or-9 list 0x0228F60A (0x18 entries) for the summoned cid:

    0x02265C40  bl 0x02022E14(cid, 0x0228F60A, 0x18)   only reached for code 7 / 9 (0x02265C32..38)
    0x02265C44  cmp r0,#0 ; beq 0x02265C4A               <-- HOOK SITE (4 B)
    0x02265C48  movs r5,#1                               member: the event is posted
    0x02265C4A  ldrh r0,[r4,#0xe] ; ldr r1, ...          the next search reloads r0 / r1

The list has NO droppable phantom left (Pyrorex spent 0x164A, 2026-10-06) and it ends flush against the c9
list 0x0228F63A, so a donor can only join through this site.  Same register contract as summon_trigger_hook
(r0 = verdict, r4 = summon record, +0xE = cid), so its stub is reused with skip = 0x02265C4A - 0x02265C48.
Adding a card is one entry in ARMS.

DUEL-ONLY: the stub lives in the ov5 cave, which overlay 41 evicts in a puzzle.

REGISTERED CARDS
    0x190B  Soitsu -> Windrose the Elemental Lord   (in-game confirmed by user 2026-10-06)
    0x111E  Monster Tamer -> Disguise, the Copycat Hero C2 (2026-11-04; the 4th arm moved the stub to a 0x40 slot)
    0x17CF  Skull Dog Marron -> Predaplant Ophrys Scorpio (2026-11-06; the 5th arm moved the stub to a 0x50 slot)
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.summon_trigger_hook import _bl, _off, stub as _stub

SITE = 0x02265C44                 # `cmp r0,#0 ; beq 0x02265C4A`
NATIVE = bytes.fromhex("002800d0")
MEMBER, NONMEMBER = 0x02265C48, 0x02265C4A
LIST_LITERAL, C79_LIST = 0x02265CEC, 0x0228F60A
RESERVE = 0x50                    # was 0x40 at 0x023AC970 (full at 4 arms); re-homed 2026-11-06 for a 5th

ARMS: tuple[tuple[int, str], ...] = (
    (0x190B, "Soitsu -> Windrose the Elemental Lord (in-game confirmed by user 2026-10-06)"),
    (0x13A3, "Robotic Knight -> Infernoble Knight Ogier C2 (in-game confirmed by user 2026-10-20)"),
    (0x0FE6, "Tiger Axe -> Infernoble Knight Ricciardetto C2 (in-game confirmed by user 2026-10-20)"),
    (0x111E, "Monster Tamer -> Disguise, the Copycat Hero C2 (shipped on user approval 2026-11-04)"),
    (0x17CF, "Skull Dog Marron -> Predaplant Ophrys Scorpio (shipped on user approval 2026-11-06, in-game test not reported; 5th arm re-homed the stub to 0x50 B)"),
)


EXTRA: list[tuple[int, str]] = []   # UNSHIPPED test cards register here at compile time (cards/edea.py); the shipped chain never sees them


def register_extra(cid: int, note: str) -> None:
    if all(c != cid for c, _ in EXTRA):
        EXTRA.append((cid, note))


def all_arms() -> tuple:
    return ARMS + tuple(EXTRA)


def stub(base: int, arms: tuple | None = None) -> bytes:
    return _stub(base, all_arms() if arms is None else arms, skip=NONMEMBER - MEMBER)


BIG_RESERVE = 0x80                # the 0x50 slot is full at 6 arms (12 B each): 7..9 arms go to CAVE_ES_C79BIG (unshipped test cards only)


def where() -> tuple[int, int]:
    """(slot, reserve) the CURRENT arm set lives in: the shipped 0x50 slot while it fits, else the 0x80 one."""
    if len(stub(ov5_cave.CAVE_C79TRIG)) <= RESERVE:
        return ov5_cave.CAVE_C79TRIG, RESERVE
    assert len(stub(ov5_cave.CAVE_ES_C79BIG)) <= BIG_RESERVE, "more than 9 C79 arms"
    return ov5_cave.CAVE_ES_C79BIG, BIG_RESERVE


def apply(ov: bytearray) -> None:
    """Install the 4-byte overlay-3 hook. Idempotent."""
    slot, _ = where()
    want = _bl(SITE, slot)
    cur = bytes(ov[_off(SITE):_off(SITE) + 4])
    if cur == want:
        return
    assert cur == NATIVE or cur in (_bl(SITE, ov5_cave.CAVE_C79TRIG), _bl(SITE, ov5_cave.CAVE_ES_C79BIG)),         f"C79 0x{SITE:08X} is {cur.hex()}, expected native {NATIVE.hex()} or one of our stubs -- another patch owns it"
    assert struct.unpack_from("<I", ov, _off(LIST_LITERAL))[0] == C79_LIST, \
        f"C79 0x{SITE:08X} no longer follows the N-or-SS list search"
    ov[_off(SITE):_off(SITE) + 4] = want
    print(f"C79 trigger hooked @0x{SITE:08X} -> ov5 0x{slot:08X} ({len(all_arms())} cids)")


def install(rom) -> None:
    """Write the stub into ov5; an older stub (fewer ARMS) in this slot is ours and is replaced."""
    slot, reserve = where()
    blob = stub(slot)
    effect_verify.assert_thumb1_only(blob, slot)
    assert len(blob) <= reserve, f"C79 stub is {len(blob)} B > {reserve:#x}"
    if ov5_cave.read_cave(rom, slot, len(blob)) == blob:
        return
    if any(ov5_cave.read_cave(rom, slot, reserve)):
        ov5 = ov5_cave._load_ov5_decompressed(rom)
        data = bytearray(ov5.data)
        off = slot - ov5_cave.OV5_RAM_BASE
        data[off:off + reserve] = bytes(reserve)
        ov5_cave._save_ov5(rom, ov5, bytes(data))
    ov5_cave.install_cave(rom, slot, blob, reserve=reserve)
    print(f"C79 stub -> ov5 0x{slot:08X} ({len(blob)} B)")


def verify(ov: bytearray, check, *, rom=None) -> None:
    slot, _ = where()
    check(bytes(ov[_off(SITE):_off(SITE) + 4]) == _bl(SITE, slot),
          f"C79 verdict @0x{SITE:08X} -> shared stub 0x{slot:08X}")
    check(struct.unpack_from("<I", ov, _off(LIST_LITERAL))[0] == C79_LIST,
          f"C79 site still follows the N-or-SS list 0x{C79_LIST:08X} search")
    if rom is not None:
        blob = stub(slot)
        check(ov5_cave.read_cave(rom, slot, len(blob)) == blob,
              f"C79 stub in ov5 @0x{slot:08X} (arms {', '.join(f'0x{c:04X}' for c, _ in all_arms())})")

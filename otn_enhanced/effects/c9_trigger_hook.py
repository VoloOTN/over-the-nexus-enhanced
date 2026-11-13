"""The SHARED plain-Special-Summon trigger hook ("If this card is Special Summoned"): one stub, a REGISTER of cids.

The twin of c79_trigger_hook.py / summon_trigger_hook.py, one list over.  The summon-trigger evaluator 0x02265768
searches the code-9 (plain Special Summon) list 0x0228F63A (0x1F entries) for the summoned cid:

    0x022658B8  bl 0x02022E14(cid, 0x0228F63A, 0x1F)   ⚠️ OWNED by azure_eyes PART G in the chain (bl 0x0239D030)
    0x022658BC  cmp r0,#0 ; beq 0x022658C2              <-- HOOK SITE (4 B), free in stock AND chain (2026-10-20)
    0x022658C0  movs r5,#1                              member: the event is posted
    0x022658C2  ldr r0,[pc,#0x160] ; ldr r0,[r0,#0x78] ; lsrs r1,r0,#3   (r1 redefined on both paths)

The list has NO phantom left in the chain ROM (scratch scan 2026-10-20), so a donor can only join through this
site.  Same register contract as the c79 site (r0 = verdict, r4 = summon record, +0xE = cid; member/non-member 2 B
apart), so summon_trigger_hook.stub is reused with skip = 2.  Adding a card is one entry in ARMS.

DUEL-ONLY: the stub lives in the ov5 cave.

REGISTERED CARDS
    0x1E05  Water Spirit -> Infernoble Knight - Renaud C3   in-game confirmed by user 2026-10-20 (infernoble)
    0x1002  Rabid Horseman -> Angelica, Princess of Noble Arms C1 (infernoble)
    0x0FED  Jellyfish -> Predaplant Darlingtonia Cobra (2026-11-06)
"""
from __future__ import annotations

import struct

from otn_enhanced.asm import effect_verify
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.summon_trigger_hook import _bl, _off, stub as _stub

SITE = 0x022658BC                 # `cmp r0,#0 ; beq 0x022658C2`
NATIVE = bytes.fromhex("002800d0")
MEMBER, NONMEMBER = 0x022658C0, 0x022658C2
LIST_LITERAL, C9_LIST = 0x02265A20, 0x0228F63A
RESERVE = 0x30

ARMS: tuple[tuple[int, str], ...] = (
    (0x1E05, "Water Spirit -> Infernoble Knight - Renaud C3 (in-game confirmed by user 2026-10-20)"),
    (0x1002, "Rabid Horseman -> Angelica, Princess of Noble Arms C1 (infernoble)"),
    (0x0FED, "Jellyfish -> Predaplant Darlingtonia Cobra (shipped on user approval 2026-11-06, in-game test not reported; the 3rd arm fills the 0x30 reserve exactly)"),
)


def stub(base: int, arms: tuple = ARMS) -> bytes:
    return _stub(base, arms, skip=NONMEMBER - MEMBER)


def apply(ov: bytearray) -> None:
    want = _bl(SITE, ov5_cave.CAVE_C9TRIG)
    cur = bytes(ov[_off(SITE):_off(SITE) + 4])
    if cur == want:
        return
    assert cur == NATIVE, f"C9 0x{SITE:08X} is {cur.hex()}, expected native {NATIVE.hex()} -- another patch owns it"
    assert struct.unpack_from("<I", ov, _off(LIST_LITERAL))[0] == C9_LIST, \
        f"C9 0x{SITE:08X} no longer follows the plain-SS list search"
    ov[_off(SITE):_off(SITE) + 4] = want
    print(f"C9 trigger hooked @0x{SITE:08X} -> ov5 0x{ov5_cave.CAVE_C9TRIG:08X} ({len(ARMS)} cids)")


def install(rom) -> None:
    blob = stub(ov5_cave.CAVE_C9TRIG)
    effect_verify.assert_thumb1_only(blob, ov5_cave.CAVE_C9TRIG)
    assert len(blob) <= RESERVE, f"C9 stub is {len(blob)} B > {RESERVE:#x}"
    if ov5_cave.read_cave(rom, ov5_cave.CAVE_C9TRIG, len(blob)) == blob:
        return
    ov5_cave.install_cave(rom, ov5_cave.CAVE_C9TRIG, blob, reserve=RESERVE)
    print(f"C9 stub -> ov5 0x{ov5_cave.CAVE_C9TRIG:08X} ({len(blob)} B)")


def verify(ov: bytearray, check, *, rom=None) -> None:
    check(bytes(ov[_off(SITE):_off(SITE) + 4]) == _bl(SITE, ov5_cave.CAVE_C9TRIG),
          f"C9 verdict @0x{SITE:08X} -> shared stub 0x{ov5_cave.CAVE_C9TRIG:08X}")
    check(struct.unpack_from("<I", ov, _off(LIST_LITERAL))[0] == C9_LIST,
          f"C9 site still follows the plain-SS list 0x{C9_LIST:08X} search")
    if rom is not None:
        blob = stub(ov5_cave.CAVE_C9TRIG)
        check(ov5_cave.read_cave(rom, ov5_cave.CAVE_C9TRIG, len(blob)) == blob,
              f"C9 stub in ov5 @0x{ov5_cave.CAVE_C9TRIG:08X} (arms {', '.join(f'0x{c:04X}' for c, _ in ARMS)})")

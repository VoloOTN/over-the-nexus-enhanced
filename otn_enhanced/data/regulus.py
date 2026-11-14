import struct

import ndspy.rom

DONOR_CID = 0x20FA                 # Regulus
from otn_enhanced.effects.common import ARM9_BASE
PB_TBL = 0x0209C6D4                   # RAM address of the sorted Phantom Beast cid table
PB_COUNT = 0x07                       # 7 entries (the consumer thunk hardcodes this)
PB_FALSE_MEMBER = 0x232E              # Horn of the Phantom Beast

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_regulus.nds"

def apply_phantom_beast_setcode(src_path: str, out_path: str) -> None:
    """Replace 0x232E (Horn of the Phantom Beast, a false member) with 0xFA20 (Regulus) in ARM9's Phantom Beast cid table.

    Keeps the table a sorted 7 entries so the single binary-search consumer thunk
    (which hardcodes count 0x07) keeps reading it correctly. Idempotent.
    """
    rom = ndspy.rom.NintendoDSRom.fromFile(src_path)
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
    d = bytearray(sec.data)

    def off(addr: int) -> int:
        return addr - ARM9_BASE

    cur = list(struct.unpack_from(f"<{PB_COUNT}H", d, off(PB_TBL)))   # current 7-entry table

    if DONOR_CID in cur:                                     # idempotent
        print(f"Phantom Beast set-code: 0x{DONOR_CID:04X} already present -> no change")
        return

    assert PB_FALSE_MEMBER in cur, (
        f"Phantom Beast set-code: false member 0x{PB_FALSE_MEMBER:04X} not present to drop "
        f"(table = {[hex(x) for x in cur]})")
    new_tbl = tuple(sorted((set(cur) - {PB_FALSE_MEMBER}) | {DONOR_CID}))   # drop one, add one, re-sort
    assert len(new_tbl) == PB_COUNT and all(               # still exactly 7, strictly ascending
        new_tbl[i] < new_tbl[i + 1] for i in range(len(new_tbl) - 1)
    ), f"resulting Phantom Beast table is not a sorted {PB_COUNT}-entry set: {[hex(x) for x in new_tbl]}"

    struct.pack_into(f"<{PB_COUNT}H", d, off(PB_TBL), *new_tbl)        # write back in place (same addr/size)
    sec.data = bytes(d)
    rom.arm9 = mc.save()
    rom.saveToFile(out_path)

    print(f"Phantom Beast set-code: in-place table @0x{PB_TBL:08X} (count {PB_COUNT}); "
          f"dropped 0x{PB_FALSE_MEMBER:04X} (false member), inserted 0x{DONOR_CID:04X}")
    print(f"  entries: {', '.join(f'0x{v:04X}' for v in new_tbl)}")

def main(src: str, out: str) -> None:
    apply_phantom_beast_setcode(src, out)

if __name__ == "__main__":
    main(src=SRC, out=OUT)
"""Donor vetting: is this cid safe to repurpose, and which Normal Monsters are?

The donor-card technique converts card X into card Y by KEEPING X's cid and
overwriting the effect-engine tables for that cid.  That is only safe when the
engine has no OTHER use for the cid, and "records-free" (no cls0-cls3 record) is
necessary but not sufficient -- see ``donor.vetting_beyond_cls_records`` in
docs/engine/donor_card_technique.yaml, plus the leave tables that the Reborn
Tengu re-homing added on top of it.

The decisive test is the one reborn_tengu used to pick The Portrait's
Secret: **scan overlay 3 and ARM9 for the cid as an aligned u16 / u32**.  Every
per-cid structure in this engine is a table of cids, so a cid with zero aligned
occurrences anywhere in the binary is entangled in nothing.  The structured
table checks below do not add coverage -- they EXPLAIN a hit, telling you which
subsystem you would break.

WHAT THIS CANNOT SEE: a per-cid switch that encodes its cids as ``base +/- imm``
off a pool literal (the thumb.stack_based_switch footgun) never stores the cid,
so it leaves no occurrence.  Those are per-card refinements on shared
dispatchers.  A clean report means "no DATA structure names this cid", which is
the property the donor technique actually needs.

Usage
-----
    python -m otn_enhanced.tools.donor_scan 0x1463            # audit one cid
    python -m otn_enhanced.tools.donor_scan --free            # every clean Normal Monster
    python -m otn_enhanced.tools.donor_scan --free --level 4 --race Dragon
"""
from __future__ import annotations

import argparse
import functools
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARM9_BASE, OV3_BASE = 0x02000000, 0x02141700

# ---------------------------------------------------------------------------
# Known per-cid structures: (base, count, stride, [(key offset, size)], label).
# Every geometry here is a KB fact or a constant a shipped patch asserts.
# ---------------------------------------------------------------------------
OV3_STRUCTS = [
    (0x02275C04, 0x2B9, 0x18, [(0, 2)], "cls2 record"),
    (0x02279D74, 0x308, 0x18, [(0, 2)], "cls3 record"),
    (0x0227E64C, 0x51A, 0x18, [(0, 2)], "cls0 record"),
    (0x022860D4, 0x535, 0x18, [(0, 2)], "cls1 record"),
    (0x022713C4, 0x56C, 12,   [(0, 2), (2, 2)], "criteria row"),
    (0x0226EC1C, 0x98,  4,    [(0, 2)], "leave-mask row"),
    (0x0226E904, 0x1E,  2,    [(0, 2)], "list30 (sent-to-GY leave list)"),
    (0x0226E990, 0x6A,  2,    [(0, 2)], "list106 (leave list)"),
    (0x0226D484, 0x4C,  8,    [(0, 2), (2, 2)], "token-summon row"),
    (0x0226DFB0, 94,    6,    [(0, 2)], "equip ATK/DEF row"),
    (0x02270B94, 161,   8,    [(0, 2), (2, 2), (4, 2), (6, 2)], "fusion recipe A"),
    (0x02270B58, 5,     12,   [(i * 2, 2) for i in range(6)], "fusion recipe B"),
    # the nine "when this card is Summoned" membership lists
    # (summon.trigger_is_a_membership_list)
    (0x0228F7AC, 0x67, 2, [(0, 2)], "summon list: Normal (code 7)"),
    (0x0228F5B8, 0x12, 2, [(0, 2)], "summon list: Normal + Tribute (Monarchs)"),
    (0x0228F580, 0x0C, 2, [(0, 2)], "summon list: Flip (code 8)"),
    (0x0228F63A, 0x1F, 2, [(0, 2)], "summon list: Special, plain (code 9)"),
    (0x0228F5DC, 0x17, 2, [(0, 2)], "summon list: Special + self-cid"),
    (0x0228F6C0, 0x24, 2, [(0, 2)], "summon list: proper SS (Synchro/Fusion/Ritual)"),
    (0x0228F598, 0x10, 2, [(0, 2)], "summon list: Normal or Flip"),
    (0x0228F60A, 0x18, 2, [(0, 2)], "summon list: Normal or Special"),
    (0x0228F678, 0x23, 2, [(0, 2)], "summon list: any summon"),
]
ARM9_STRUCTS = [
    (0x0209BF8C, 0x2E, 4, [(0, 2), (2, 2)], "card-identity alias pair"),
    (0x0209CB22, 0x0E, 2, [(0, 2)], "set-code table: Infernity"),
    (0x0209CB48, 0x13, 2, [(0, 2)], "set-code table: T.G."),
    (0x0209CB6E, 0x14, 2, [(0, 2)], "set-code table: X-Saber"),
    (0x0209CB96, 0x15, 2, [(0, 2)], "set-code table: Ally of Justice"),
    (0x0209CBEA, 0x16, 2, [(0, 2)], "set-code table: Watt"),
    (0x0209CC16, 0x1A, 2, [(0, 2)], "set-code table: Karakuri"),
    (0x0209CDF2, 0x1A, 2, [(0, 2)], "set-code table: Gladiator Beast"),
]

# Where each oracle's per-cid DATA block begins.  Below these, the image is
# Thumb code, and a bare aligned u16 that happens to equal a cid is almost always
# an instruction encoding, not a table entry -- 0x0FA9 (the shipped Warwolf
# donor) matches `lsrs r1,r5,#0x1e` at 0x02187168, for instance.  A u32-aligned
# hit in code IS meaningful: that is a PC-relative literal-pool constant, which
# is how a per-cid compare gets its key.
DATA_START = {"ov3": 0x0226D000, "arm9": 0x02098000}

# Address ranges worth naming when a hit lands outside a mapped table.
CODE_REGIONS = [
    (0x0225E51C, 0x02260400, "hand-SS / summon-restriction cid tree"),
    (0x02248000, 0x0224A000, "Synchro material predicates"),
    (0x021B4000, 0x021B6000, "continuous stat-recompute tree"),
    (0x0228E1E0, 0x0228F158, "effect / timing registry"),
    (0x0228F158, 0x0228F580, "summon-procedure registry"),
]


# ---------------------------------------------------------------------------
# Oracles
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def images() -> dict:
    from otn_enhanced.rom import stock
    return {"arm9": stock.arm9(), "ov3": stock.ov3()}


def _base(oracle: str) -> int:
    return ARM9_BASE if oracle == "arm9" else OV3_BASE


@functools.lru_cache(maxsize=1)
def cards() -> dict:
    """cid -> card_prop fields + English name + pack availability + name-slot budget."""
    import ndspy.rom
    from otn_enhanced.rom.pac import parse_pac
    from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
    from otn_enhanced.data.card_stats import iter_paths

    rom = ndspy.rom.NintendoDSRom.fromFile(
        str(ROOT / "data" / "over_the_nexus" / "working" / "rom.nds"))
    path = next(q for q in iter_paths(rom.filenames) if q.lower().endswith("bin2.pac"))
    pac = bytes(rom.files[rom.filenames.idOf(path)])
    arch = parse_pac(pac, path)

    def blob(n):
        f = next(x for x in arch.files if x.get_clean_name().lower() == n)
        return pac[f.address:f.address + f.size]

    cp, pk = blob("card_prop.bin"), blob("card_pack.bin")
    langs = "efgijkrs"
    idx = {L: blob("card_indx_%s.bin" % L) for L in langs}
    nm = {L: blob("card_name_%s.bin" % L) for L in langs}
    ds = {L: blob("card_desc_%s.bin" % L) for L in langs}

    out = {}
    for i in range((len(cp) - 8) // 8):
        d = GC.decode_entry(cp[8 + i * 8:16 + i * 8])
        d["idx"] = i
        d["rarity1"] = pk[8 + i * 8]
        d["pack1"], d["pack2"] = pk[8 + i * 8 + 3], pk[8 + i * 8 + 4]
        # name / description slot budgets.  The engine copies these blobs into
        # FIXED-SIZE buffers, so a patch must write strictly in place -- growing
        # one freezes the game the moment the card is loaded.  The in-place slot
        # is the length of the card's CURRENT string, which is what the shared
        # writer (`_place_string`) tests: `len(new) <= len(old_str)` or skip.
        # (It is NOT the gap to the next index entry -- that over-reports by the
        # inter-string padding, which is where a 15-vs-12 byte disagreement on
        # Atlantean Pikeman's Japanese name came from.)
        nb, db = {}, {}
        for L in langs:
            no, do = struct.unpack_from("<II", idx[L], (i + 1) * 8)
            nb[L] = nm[L].index(b"\x00", no) - no
            db[L] = ds[L].index(b"\x00", do) - do
        o_e = struct.unpack_from("<I", idx["e"], (i + 1) * 8)[0]
        d["name"] = nm["e"][o_e:nm["e"].index(b"\x00", o_e)].decode("latin1")
        d["name_budget"], d["name_floor"] = nb, min(nb.values())
        d["desc_budget"], d["desc_floor"] = db, min(db.values())
        d["desc_en"] = db["e"]
        out[d["card_id"]] = d
    return out


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------
def _struct_hits(cid: int, oracle: str, table) -> list:
    img, base = images()[oracle], _base(oracle)
    hits = []
    for tb, count, stride, keys, label in table:
        off = tb - base
        if off < 0 or off + count * stride > len(img):
            continue
        for i in range(count):
            for ko, ksz in keys:
                fmt = "<H" if ksz == 2 else "<I"
                v = struct.unpack_from(fmt, img, off + i * stride + ko)[0]
                if v == cid:
                    hits.append("%s[%d] (+0x%X)" % (label, i, ko))
                    break
    return hits


def occurrences(cid: int) -> list:
    """Every ALIGNED u16/u32 occurrence of *cid* in overlay 3 and ARM9."""
    out = []
    pat16, pat32 = struct.pack("<H", cid), struct.pack("<I", cid)
    for oracle in ("ov3", "arm9"):
        img, base = images()[oracle], _base(oracle)
        start = 0
        while True:
            off = img.find(pat16, start)
            if off < 0:
                break
            start = off + 1
            if off % 2 == 0:
                out.append((oracle, base + off, 2))
        start = 0
        while True:
            off = img.find(pat32, start)
            if off < 0:
                break
            start = off + 1
            if off % 4 == 0:
                out.append((oracle, base + off, 4))
    return out


def describe_addr(oracle: str, addr: int) -> str:
    table = OV3_STRUCTS if oracle == "ov3" else ARM9_STRUCTS
    for tb, count, stride, keys, label in table:
        if tb <= addr < tb + count * stride:
            i, rem = divmod(addr - tb, stride)
            return "%s[%d]+0x%X" % (label, i, rem)
    for lo, hi, label in CODE_REGIONS:
        if lo <= addr < hi:
            return "in " + label
    return "unclassified"


def _in_known_struct(oracle: str, addr: int, width: int):
    """(is_key_field, label) if *addr* falls inside a mapped table, else None.

    A hit on a NON-key field is not a cid reference at all: criteria row 811's
    handler is 0x02240FD9, whose low halfword equals Armored Lizard's cid.
    """
    for tb, count, stride, keys, label in (OV3_STRUCTS if oracle == "ov3" else ARM9_STRUCTS):
        if tb <= addr < tb + count * stride:
            rem = (addr - tb) % stride
            is_key = any(rem == ko and width == ksz for ko, ksz in keys)
            return is_key, "%s[%d]+0x%X" % (label, (addr - tb) // stride, rem)
    return None


def classify(oracle: str, addr: int, width: int) -> str:
    """'binding' | 'advisory' | 'noise' for one occurrence."""
    known = _in_known_struct(oracle, addr, width)
    if known is not None:
        return "binding" if known[0] else "noise"
    if width == 4:
        # a PC-relative literal-pool constant, or a u32 field of an unmapped table
        return "binding"
    if oracle == "ov3" and addr >= DATA_START["ov3"]:
        # overlay 3's data block is per-cid tables end to end
        return "binding"
    if oracle == "arm9" and addr >= DATA_START["arm9"]:
        # ARM9's data block also holds numeric/geometry tables, so a bare u16 there
        # is ambiguous -- surface it, do not disqualify on it
        return "advisory"
    return "noise"


def scan(cid: int) -> dict:
    occ = occurrences(cid)
    buckets = {"binding": [], "advisory": [], "noise": []}
    for o in occ:
        buckets[classify(*o)].append(o)
    return {
        "cid": cid,
        "card": cards().get(cid),
        "occurrences": occ,
        "structs": (_struct_hits(cid, "ov3", OV3_STRUCTS)
                    + _struct_hits(cid, "arm9", ARM9_STRUCTS)),
        "clean": not buckets["binding"],
        **buckets,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
NORMAL_TYPES = ("Normal Monster", "Normal Tuner Monster")


def fmt_card(c) -> str:
    if not c:
        return "<no card_prop row>"
    if c["card_type"] in ("Spell Card", "Trap Card"):
        tail = c["spell_trap_subtype"]
    else:
        tail = "Lv%-2d %-5s %-13s %4d/%-4d" % (
            c["level"], c["attribute"], c["race"], c["real_atk"], c["real_def"])
    return "%-36s %-22s %s" % (c["name"], c["card_type"], tail)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cids", nargs="*", help="cids to audit (hex ok)")
    ap.add_argument("--free", action="store_true",
                    help="list every clean Normal-Monster donor")
    ap.add_argument("--level", type=int, help="filter --free by level")
    ap.add_argument("--race", help="filter --free by race")
    ap.add_argument("--attribute", help="filter --free by attribute")
    ap.add_argument("--min-name", type=int, default=0,
                    help="filter --free by name-slot floor (bytes)")
    ap.add_argument("--min-desc", type=int, default=0,
                    help="filter --free by description-slot floor (bytes)")
    ap.add_argument("--sort", choices=("cid", "name", "desc"), default="cid",
                    help="order --free output (default cid)")
    ap.add_argument("--obtainable", action="store_true",
                    help="filter --free to cards that are actually in a pack")
    a = ap.parse_args(argv)

    if a.free:
        # A shipped donor keeps its cid, so the stock-image scan still calls it
        # CLEAN (Basic Insect 0x0FD8 was re-offered after Metal Armored Bug spent
        # it).  Skip every cid a patch already rewrites or claims.
        from otn_enhanced.data.card_text import CARD_TEXT
        from otn_enhanced.knowledge.check_allocations import PHANTOM_CLAIMS
        spent = set(CARD_TEXT) | {c for k, c, _ in PHANTOM_CLAIMS if k == "donor_cid"}
        rows = []
        for cid, c in sorted(cards().items()):
            if c["card_type"] not in NORMAL_TYPES:
                continue
            if a.level and c["level"] != a.level:
                continue
            if a.race and c["race"] != a.race:
                continue
            if a.attribute and c["attribute"] != a.attribute:
                continue
            if c["name_floor"] < a.min_name:
                continue
            if c["desc_floor"] < a.min_desc:
                continue
            if a.obtainable and not c["pack1"]:
                continue
            if cid in spent:
                continue
            if not scan(cid)["clean"]:
                continue
            rows.append((cid, c))
        key = {"cid": lambda r: r[0],
               "name": lambda r: -r[1]["name_floor"],
               "desc": lambda r: -r[1]["desc_floor"]}[a.sort]
        rows.sort(key=key)
        print("%d clean Normal-Monster donors "
              "(zero aligned u16/u32 occurrences in ov3 + arm9)\n" % len(rows))
        print("%-8s%-32s%-14s%-4s%-6s%-14s%-11s%-5s%-6s%s" % (
            "cid", "name", "type", "lv", "attr", "race", "atk/def", "pk1",
            "name", "desc"))
        for cid, c in rows:
            print("0x%04X  %-32s%-14s%-4d%-6s%-14s%-11s%-5d%-6d%d" % (
                cid, c["name"][:31], c["card_type"].replace(" Monster", ""),
                c["level"], c["attribute"], c["race"],
                "%d/%d" % (c["real_atk"], c["real_def"]), c["pack1"],
                c["name_floor"], c["desc_floor"]))
        print("\n'name' / 'desc' are the SMALLEST in-place slot across the eight "
              "languages (bytes).")
        return 0

    for s in a.cids:
        cid = int(s, 0)
        r = scan(cid)
        c = r["card"]
        print("\n0x%04X  %s" % (cid, fmt_card(c)))
        if c:
            print("        pack1=%d pack2=%d" % (c["pack1"], c["pack2"]))
            print("        name slots (floor %d): %s" % (c["name_floor"], c["name_budget"]))
            print("        desc slots (floor %d): %s" % (c["desc_floor"], c["desc_budget"]))
        print("        VERDICT: %s" % ("CLEAN - no data structure names this cid"
                                       if r["clean"] else "ENTANGLED"))
        if r["structs"]:
            print("        named by:")
            for h in r["structs"]:
                print("          - " + h)
        if r["binding"]:
            byreg = {}
            for oracle, addr, w in r["binding"]:
                byreg.setdefault(describe_addr(oracle, addr), []).append((oracle, addr, w))
            print("        %d binding occurrence(s):" % len(r["binding"]))
            for k, v in sorted(byreg.items(), key=lambda kv: -len(kv[1])):
                addrs = ", ".join("%s:0x%08X/u%d" % (o, ad, w * 8) for o, ad, w in v[:6])
                more = " (+%d more)" % (len(v) - 6) if len(v) > 6 else ""
                print("          %-40s %s%s" % (k + ":", addrs, more))
        if r["advisory"]:
            addrs = ", ".join("%s:0x%08X" % (o, ad) for o, ad, w in r["advisory"][:8])
            print("        %d ARM9 data-region u16 hit(s) -- ambiguous (ARM9 data holds "
                  "numeric tables too): %s" % (len(r["advisory"]), addrs))
        if r["noise"]:
            addrs = ", ".join("%s:0x%08X" % (o, ad) for o, ad, w in r["noise"][:6])
            print("        %d non-key / code-region u16 hit(s), instruction encodings or "
                  "pointer halves: %s" % (len(r["noise"]), addrs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

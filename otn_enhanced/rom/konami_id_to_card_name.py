import pandas as pd

def load_konami_id_to_card_name_map(tsv_path: str) -> dict[int, str]:
    """
    Load a mapping from Konami ID (uint16) to card name from a TSV file.

    Args:
        tsv_path (str): Path to the TSV file containing 'konami_id' and 'card_name' columns.
    Returns:
        dict[int, str]: A dictionary mapping Konami ID (as int) to card name (str).
    """
    df = pd.read_csv(tsv_path, sep=r"\s{4,}", engine="python")
    df["uint16"] = df["konami_id"].apply(lambda x: int(x, 16))
    konami_id_to_name = dict(zip(df["uint16"], df["card_name"]))
    return konami_id_to_name

import functools
import os
KONAMI_ID_TO_CARD_NAME = load_konami_id_to_card_name_map(os.path.join(os.path.dirname(__file__), "konami_id_to_card_name.tsv"))

def load_card_name_to_konami_id_map(rom_path: str) -> list[tuple[str, int]]:
    """[(name, cid)] from the ROM's bin2.pac, in card_prop order: card_prop[i] &
    0x3FFF is the cid, and card_indx_e[i] holds the offset of its name in
    card_name_e.bin. Duplicate names (alt arts, tokens) are all kept; the first
    is the original printing ("Cyber Dragon" 0x0F07 before the 0x18F6 copy)."""
    import struct
    import ndspy.rom
    from otn_enhanced.rom.pac import parse_format_v1

    bin2 = bytes(ndspy.rom.NintendoDSRom.fromFile(rom_path).getFileByName("Data_arc_pac/bin2.pac"))
    files = {f.name: f for f in parse_format_v1(bin2, "bin2.pac").files}
    blob = lambda n: bin2[files[n].address:files[n].address + files[n].size]
    prop, indx, names = blob(b"card_prop.bin"), blob(b"card_indx_e.bin"), blob(b"card_name_e.bin")
    out = []
    for i in range(1, len(prop) // 8):  # record 0 is a blank dummy
        off = struct.unpack_from("<I", indx, i * 8)[0]
        out.append((names[off:names.index(b"\0", off)].decode("latin-1"), struct.unpack_from("<I", prop, i * 8)[0] & 0x3FFF))
    return out

def _patched_names(pairs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """The base ROM holds stock names; the build renames donor cids from
    card_text.CARD_TEXT, so a donor's stock name gives way to its new one."""
    from otn_enhanced.data.card_text import CARD_TEXT
    renamed = {cid: t["e"][0] for cid, t in CARD_TEXT.items() if isinstance(t.get("e"), tuple)}
    return [(renamed.get(cid, name), cid) for name, cid in pairs]

@functools.cache
def _name_table(rom_path: str) -> list[tuple[str, int]]:
    return _patched_names(load_card_name_to_konami_id_map(rom_path))


def card_names() -> list[tuple[str, int]]:
    """[(name, cid)] for the ROM deckgen is pointed at (resources.rom_path(): the repo's working/rom.nds in a
    checkout, the ROM being randomised inside the randomiser).  Read on FIRST USE, never at import: the frozen
    randomiser .exe has no repo data folder, and reading it at import crashed the .exe on start-up."""
    from otn_enhanced.deckgen import resources
    return _name_table(str(resources.rom_path()))


def __getattr__(name: str):
    # `from ... import CARD_NAME_TO_KONAMI_ID` keeps working, loaded when first imported by name.
    if name == "CARD_NAME_TO_KONAMI_ID":
        return card_names()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def card_name_to_konami_id(name: str) -> int | None:
    """cid of the FIRST record named `name` (the original printing), else None."""
    # ponytail: linear scan of ~4300 tuples, build a dict cache if a hot loop ever needs it
    return next((cid for n, cid in card_names() if n == name), None)

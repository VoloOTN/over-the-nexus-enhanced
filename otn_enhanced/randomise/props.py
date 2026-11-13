"""Stage: randomise card properties in bin2.pac / card_prop.bin."""
from __future__ import annotations

from otn_enhanced.randomise.cardprop import (
    ATTRIBUTE_POOL, ATTRIBUTES, CARD_TYPES, MAX_LEVEL, MAX_STAT, MIN_LEVEL,
    MIN_SYNCHRO_LEVEL, RACE_POOL, RACES, SPELL_TRAP_TYPES, STAT_DIVISOR, STAT_STEP,
    SYNCHRO_TYPES, TOKEN_TYPE, UNKNOWN_STAT, cap_for_level, decode_entry,
    encode_entry,
)
from otn_enhanced.randomise.config import Config, Progress, _stream
from otn_enhanced.rom.pac_inplace import PacArchive, parse_pac_v1, write_same_size

BIN2_PATH = "Data_arc_pac/bin2.pac"


def _stat_from_unit(unit: float, cap: int) -> int:
    """Map a uniform [0,1) draw onto a multiple of 50 no greater than *cap*.

    The draw is taken before the cap is known so that turning balanced mode on
    or off, or editing a band, changes the resulting value without shifting the
    RNG stream for any other card.
    """
    steps = cap // STAT_STEP + 1
    return STAT_STEP * min(steps - 1, int(unit * steps))


def _card_names(pac: bytes, archive: PacArchive, count: int) -> list[str]:
    """Names from card_name_e.bin, index-aligned with card_prop.bin.

    Cosmetic -- used only for the change log, so a mismatch degrades to indices
    rather than failing the run.
    """
    entry = archive.by_name("card_name_e.bin")
    if entry is None:
        return []
    raw = archive.payload(pac, entry)
    names = [s.decode("latin-1", "replace") for s in raw.split(b"\x00")]
    names = [n for n in names if n]
    return names if len(names) == count else []


def stage_properties(rom, cfg: Config, log, progress=None) -> int:
    """Randomise card_prop.bin inside bin2.pac.  Returns the number of rows changed."""
    pac = bytearray(rom.getFileByName(BIN2_PATH))
    archive = parse_pac_v1(bytes(pac))
    entry = archive.by_name("card_prop.bin")
    if entry is None:
        raise ValueError("card_prop.bin not found in bin2.pac")

    body = bytearray(archive.payload(bytes(pac), entry))
    count = (len(body) - 8) // 8
    names = _card_names(bytes(pac), archive, count)
    log(f"  card_prop.bin: {count} entries")
    progress = progress or Progress()
    progress.stage("randomising card properties", count)

    attr_rng = _stream(cfg.seed, "attribute")
    race_rng = _stream(cfg.seed, "race")
    level_rng = _stream(cfg.seed, "level")
    atk_rng = _stream(cfg.seed, "atk")
    def_rng = _stream(cfg.seed, "def")

    changed = 0
    skipped_unknown = 0
    for i in range(count):
        # Batched: 4305 individual UI updates would cost more than the work.
        if i % 128 == 0:
            progress.step(min(128, count - i))
        off = 8 + i * 8
        fields = decode_entry(bytes(body[off:off + 8]))
        ctype = fields["card_type"]

        # Spells, Traps, Tokens and the handful of level-0 rows are out of scope.
        if ctype in SPELL_TRAP_TYPES or ctype == TOKEN_TYPE or fields["level"] == 0:
            continue

        is_synchro = ctype in SYNCHRO_TYPES

        # Draw for every eligible card unconditionally -- see _stream().
        new_attr = attr_rng.choice(ATTRIBUTE_POOL)
        new_race = race_rng.choice(RACE_POOL)
        new_level = level_rng.randint(
            MIN_SYNCHRO_LEVEL if is_synchro else MIN_LEVEL, MAX_LEVEL)
        atk_unit = atk_rng.random()
        def_unit = def_rng.random()

        before = dict(fields)

        # DIVINE is outside the pool, so those cards keep their attribute.
        if cfg.randomise_attribute and fields["attribute"] in ATTRIBUTE_POOL:
            fields["attribute"] = new_attr
        if cfg.randomise_race and fields["race"] in RACE_POOL:
            fields["race"] = new_race
        if is_synchro:
            if cfg.randomise_synchro_level:
                fields["level"] = new_level
        elif cfg.randomise_level:
            fields["level"] = new_level

        cap = cap_for_level(fields["level"], cfg.caps) if cfg.balanced else MAX_STAT

        # A "?" stat stays "?" -- overwriting the 511 marker would invent a number
        # the card is not supposed to have.
        if cfg.randomise_atk:
            if fields["atk_encoded"] == UNKNOWN_STAT:
                skipped_unknown += 1
            else:
                fields["atk_encoded"] = _stat_from_unit(atk_unit, cap) // STAT_DIVISOR
        if cfg.randomise_def:
            if fields["def_encoded"] == UNKNOWN_STAT:
                skipped_unknown += 1
            else:
                fields["def_encoded"] = _stat_from_unit(def_unit, cap) // STAT_DIVISOR

        new_bytes = encode_entry(fields)
        if new_bytes == bytes(body[off:off + 8]):
            continue
        body[off:off + 8] = new_bytes
        changed += 1

        label = names[i] if i < len(names) else f"#{i}"
        kind = CARD_TYPES.get(ctype, f"type {ctype}")
        deltas = []
        if before["attribute"] != fields["attribute"]:
            deltas.append(f"Attribute {ATTRIBUTES.get(before['attribute'])} -> "
                          f"{ATTRIBUTES.get(fields['attribute'])}")
        if before["race"] != fields["race"]:
            deltas.append(f"Race {RACES.get(before['race'])} -> {RACES.get(fields['race'])}")
        if before["level"] != fields["level"]:
            deltas.append(f"Level {before['level']} -> {fields['level']}")
        if before["atk_encoded"] != fields["atk_encoded"]:
            deltas.append(f"ATK {before['atk_encoded'] * STAT_DIVISOR} -> "
                          f"{fields['atk_encoded'] * STAT_DIVISOR}")
        if before["def_encoded"] != fields["def_encoded"]:
            deltas.append(f"DEF {before['def_encoded'] * STAT_DIVISOR} -> "
                          f"{fields['def_encoded'] * STAT_DIVISOR}")
        log(f"{i} - {label} [{kind}]: " + "; ".join(deltas), detail=True)

    if skipped_unknown:
        log(f"  preserved {skipped_unknown} '?' ATK/DEF value(s)")

    if not cfg.dry_run:
        write_same_size(pac, entry, bytes(body))
        rom.setFileByName(BIN2_PATH, bytes(pac))
    return changed

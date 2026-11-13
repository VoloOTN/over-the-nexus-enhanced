"""Curated names for overlay0003 / ARM9 engine routines.

This is the hand-editable source of truth that :mod:`gen_registry` merges into
``primitives.json``.  Each entry records a *confidence tier* so consumers never
mistake an inference for a fact:

* ``"known"``  — from :data:`effect_extract.KNOWN_SUBROUTINES` and
  :data:`effect_builder.PRIMITIVES`; the pre-existing curated set.
* ``"proven"`` — addresses used in *shipped, in-game-tested* finished patches
  (their signatures are documented in ``finished_patches/HOWTO.md §18``).
* ``"inferred"`` — never written here; heuristic role labels come from
  :mod:`infer_names` and are kept as separate metadata.

The NDS ARM9 is ARM946E-S; routine addresses are absolute RAM addresses.  The
``known`` tier is generated from ``KNOWN_SUBROUTINES`` (overlay file offsets) by
adding ``RAM_BASE``; ``proven`` entries are ARM9 / overlay RAM addresses copied
verbatim from the patches.
"""

from __future__ import annotations

from dataclasses import dataclass

from otn_enhanced.tools.effect_extract import KNOWN_SUBROUTINES, RAM_BASE
from otn_enhanced.asm.effect_builder import PRIMITIVES as _BUILDER_PRIMITIVES

CONFIDENCE_LEVELS = ("known", "proven", "inferred")


@dataclass(frozen=True)
class PrimitiveName:
    """A curated name for an engine routine."""
    name: str
    signature: str | None
    confidence: str          # one of CONFIDENCE_LEVELS
    source: str              # where the name came from


# ---------------------------------------------------------------------------
# Tier "proven" — addresses proven by use in shipped finished patches.
# Signatures from finished_patches/*.py comments + HOWTO.md §18.
# ---------------------------------------------------------------------------
_PROVEN: dict[int, tuple[str, str | None]] = {
    0x021D12F4: ("draw", "(side, count)"),
    0x021D2624: ("reveal_top", "(side)  -- reveal top of Deck; queues display cmd 0x59"),
    0x02029E60: ("is_monster", "(cid) -> bool  -- summonable monster?"),
    0x0202ABD8: ("cid_level", "(cid) -> level  -- card_prop bits [42:46]"),
    0x0202ABB8: ("get_race", "(cid) -> race  (KB carddata.race_getter_is_criteria_race)"),
    0x020240D8: ("has_set_code", "(cid_low14, set_code) -> bool  -- set_code < 0x70"),
    0x0202AC6C: ("get_def", "(cid_low14) -> DEF"),
    0x0202AC48: ("get_atk", "(cid_low14) -> ATK"),
    0x0223BC3C: ("deck_candidate_builder",
                 "builds Deck/zone candidates; BLXes the per-candidate filter"),
    0x02243F38: ("deck_count_builder", "BLXes the populate 'h' to count candidates"),
    0x0223C824: ("native_setcode_filter", "(cand@[SP+0], crit@[SP+4]) -- set-code match"),
    0x0223C89C: ("native_def_filter", "(cand@[SP+8], crit@[SP+0xC]) -- DEF ceiling"),
    0x0223C84D: ("native_atk_filter", "(cand@stack, crit@stack) -- ATK match"),
    # Turn log, KB-verified (dispatch.turnlog_once_per_turn_pair, rider.kind_exact_node_query). The 'known' tier
    # once called 0x021D2584 "special_summon_from_deck", a heuristic label from effect_extract.
    0x021D2584: ("turnlog_post", "(side, cid, kind, 0)  -- slot-0xB wrapper around the attached-node writer"),
    0x021A14E8: ("turnlog_query", "(side, slot, key, kind) -> nonzero iff a kind-exact node exists"),
    # Each has a VERIFIED knowledge-base fact at its address; the 'known' tier had heuristic labels for all of them.
    0x0219A818: ("ui_event_post", "(side, code); posts only for a human seat (engine.ui_event_post_0x0219A818)"),
    0x021D28A4: ("depth_push", "() push half of the [0x0229AB7C+0x28] counter (engine.depth_counter_push_pop_*)"),
    0x021D2964: ("depth_pop", "() pop half of that counter; does not undo the push's first-push init"),
    0x0219C510: ("picker_readback", "() -> pointer to the picked locator (dispatch.pick_readback_is_a_locator_pointer)"),
    0x0219C430: ("list_picker", "(side, mode, cid, param); needs a criteria row for cid (dispatch.list_picker_needs_a_criteria_row)"),
    0x021AD870: ("ss_gate_a", "(side) = 0x021AD79C(side, 0); what the gate checks is NOT proven (engine.thunk_0x021AD870)"),
    0x021B9ECC: ("ss_gate_b", "(side) = 0x021B9708(side, 8, 0); what the gate checks is NOT proven (engine.thunk_0x021B9ECC)"),
}


def _build() -> dict[int, PrimitiveName]:
    """Assemble the curated table: known tier first, then proven (proven wins)."""
    table: dict[int, PrimitiveName] = {}

    # Tier "known": KNOWN_SUBROUTINES (overlay file offsets -> RAM addresses).
    for off, name in KNOWN_SUBROUTINES.items():
        table[RAM_BASE + off] = PrimitiveName(
            name=name, signature=None, confidence="known",
            source="effect_extract.KNOWN_SUBROUTINES")

    # Tier "known": effect_builder.PRIMITIVES (ARM9 addresses, with signatures).
    for name, prim in _BUILDER_PRIMITIVES.items():
        table[prim.addr] = PrimitiveName(
            name=name, signature=prim.signature, confidence="known",
            source="effect_builder.PRIMITIVES")

    # Tier "proven": shipped-patch addresses (override on collision — they carry
    # the verified signature).
    for addr, (name, sig) in _PROVEN.items():
        table[addr] = PrimitiveName(
            name=name, signature=sig, confidence="proven",
            source="finished_patches (in-game proven)")

    return table


PRIMITIVE_NAMES: dict[int, PrimitiveName] = _build()


def lookup(addr: int) -> PrimitiveName | None:
    """Return the curated name for *addr*, or None."""
    return PRIMITIVE_NAMES.get(addr)

# Infernity Barrier -- inherited claims (UNVERIFIED, from the pre-DSL module docstring)

## Open Questions
- UNVERIFIED: the dispatcher walk / per-cid simulation proving 0x021F6042 is reached for 0x1DDD alone lives in `finished_patches/infernity_barrier.py` (the oracle); not re-proven this session.
- UNVERIFIED: counter-trap conditions all route through 0x021F5F94, a binary search of cid -> per-card leaf.
- UNVERIFIED: phantom 0x234C carries Konami's complete Infernity Barrier condition (leaf 0x021F63B6); no card_prop for it.
- UNVERIFIED: PART D (set-code table) is NOT needed for the effect -- the condition detects Infernity *monsters*, which the table already lists; it only makes the card itself an archetype member.
- UNVERIFIED: ctx+0 stays the donor's real cid throughout (no spoof), so nothing downstream is poisoned.
- UNVERIFIED: name/desc loaded into fixed-size buffers -- a grown blob freezes on load (now moot: CARD_TEXT re-emit path).

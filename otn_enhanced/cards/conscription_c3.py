"""Conscription 0x192F -> a NORMAL SPELL test harness for Grapha's CLAUSE 3 payload.

    uv run python -m otn_enhanced.cards.conscription_c3

WHY THIS CARD EXISTS
--------------------
Grapha clause 3 is *"...then, if this card was discarded from your hand to your
Graveyard by an OPPONENT's card effect, look at 1 random card in your opponent's
hand, then, if it was a monster, you can Special Summon it to your side of the
field."*

The **condition** (C3a) and the **payload** (C3b + C3c) fail independently, and
the condition is expensive to reach in-game: it needs the AI to play a
hand-discard effect on the player, which no test so far has done -- every
clause-2 test discarded Grapha with the player's OWN Gates of Dark World, a
SAME-side discard that correctly leaves clause 3 inert.

So the payload gets its own front door.  This patch turns Conscription into a
Normal Spell whose entire effect IS the payload, with **no C3a gate at all**, so
one activation from the hand exercises the exact bytes Grapha will run.  The
resolver is installed ONCE, at :data:`ov5_cave.CAVE_C3_RES`, and Grapha's clause
3 will point at the SAME address -- the harness cannot drift from the thing it
is testing.

⚠️ THIS IS A TEST CARD, NOT A SHIPPED CARD.  It is not in ``apply_all_patches``
and must not be until the user says so.  Conscription's printed effect is
DESTROYED by this patch, deliberately.

THE PAYLOAD, AND WHY EVERY PIECE IS NATIVE
------------------------------------------
Nothing here is invented; it is two native primitives spliced at the seam the
engine already put there.

``dispatch.random_hand_peek_primitive`` -- the NDS ships "look at 1 random card
in your opponent's hand" as a **card-agnostic** two-phase resolver 0x0220F754,
shared by Omega Goggles 0x1EED (cls3[460]) and Inspection 0x1367 (cls1[132]).
Two cards, two different cls tables, and the random hand-peek is the ONLY
printed text they have in common -- which is what makes it card-agnostic rather
than merely reused (contrast the Zephyros 400-damage trap that cost
card.grapha_clause1 an in-game test).  Its shape:

    phase 0x80  (1 - side) = the opponent; if that player's HAND COUNT
                (player+0x0C) is 0, return 0 and do nothing; else post
                0x022599F8(opponent, 0) -- kind 5 into the UI dispatcher
                0x0225985C -- and return phase 0x7F.
    phase 0x7F  read the chosen index back as the u16 at 0x0229DE94+6, index
                the opponent's HAND array (player+0x124,
                ram.zone_code_0x0B_is_the_hand), unpack a "ref" from the card
                word and call the reveal 0x021D2598.

⚠️ The pick is NEVER computed inline -- 0x022599F8 only posts a request, so the
selection lands on the UI round-trip.  That is why the card must be multi-phase,
and it is confirmed by Delinquent Duo 0x1325 (cls0[207], 0x0220E108), a
three-phase machine posting the sibling wrapper 0x022599C8(opponent, 1, 1) =
"discard 1 random card" (dispatch.random_pick_from_hand_family).

``dispatch.summon_from_zone_primitive`` -- 0x021BA684 Special Summons a card to
your field and takes the **SOURCE ZONE in r3**.  Twenty callers in overlay 3
split **14 passing 0x0B (the hand)** against 6 passing 0x0D (the Deck), so
summoning out of the opponent's HAND -- which no NDS card prints -- is a
parameter change, not new machinery.  The template for the surrounding logic is
Conscription's OWN resolver 0x0221F1F4, which already computes (1 - side),
guards on an empty zone, masks the cid, tests 0x02029E60 (is-a-monster) and
calls the summon as ``(r0 = my side, r1 = cid, r2 = ref, r3 = zone)``.

THE SPLICE: phase 0x7F's tail.  After the native reveal, mask the cid out of the
SAME hand word already in hand, test 0x02029E60, and only then summon with
r3 = 0x0B.  Because phase 0x7F already holds the randomly-chosen card, there is
no second selection to synchronise -- an index-coupling problem that looked real
until Delinquent Duo showed the pick is a UI round-trip.

⚠️ 0x020232EC IS DELIBERATELY NOT CALLED.  That is Conscription's *"that can be
Normal Summoned/Set"* gate -- its own printed clause, not Grapha's.  Grapha says
only "if it was a monster".  Keeping it would be the exact failure
grep-the-template-cards-text-too describes.

⚠️ A NON-MONSTER DOES NOTHING -- no discard, no bounce, no side effect (user,
2026-08-28).  The stub simply returns 0.

WHAT THIS PATCH TOUCHES
-----------------------
    1  ov5   CAVE_C3_RES: the shared payload resolver.
    2  ov3   cls0[644] +04 -> the stub, and +0C -> 0x021F2BD9.
    3  pac   card_prop: card type Trap (29) -> Spell (27); subtype stays Normal.
    4  pac   the description, so the test card says what it does.

(2)'s +0C swap matters: Conscription's own condition 0x021F98F4 gates on the
opponent's **DECK** count plus a free monster zone, which is wrong for a card
that looks at a **HAND**.  0x021F2BD9 is the native condition shared by
Confiscation 0x1324, Delinquent Duo 0x1325 and The Forceful Sentry 0x132B, and
is exactly "the opponent's hand is not empty".

IN-GAME ORACLE -- NORMAL DUEL ONLY (the payload lives in the ov5 cave, which a
puzzle's overlay 41 evicts).

  H1. Activate Conscription from your hand as a Normal Spell while your
      opponent holds at least one card.                                  [ ]
  H2. -> expect to be shown 1 RANDOM card from your opponent's hand.      [ ]
  H3. If that card is a MONSTER -> expect it Special Summoned to YOUR
      side of the field, and to LEAVE the opponent's hand.               [ ]
  H4. If it is a Spell/Trap -> expect NOTHING to happen after the look.   [ ]
  H5. NEGATIVE CONTROL: with the opponent's hand EMPTY, the card must not
      be activatable at all (that is the 0x021F2BD9 condition).          [ ]
  H6. FULL FIELD: with five monsters on your side and a monster revealed,
      expect the LOOK-AT to still happen, NO summon, and no hang.  The
      payload guards this itself with 0x021B9ECD, because the summon
      primitive forces past its own legality test -- see SUMMON.         [ ]
  H7. REGRESSION: Omega Goggles 0x1EED, Inspection 0x1367 and Delinquent
      Duo 0x1325 still work -- this patch calls their primitives but
      rewrites no row of theirs.                                         [ ]
"""
from __future__ import annotations

import struct

import ndspy.rom
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

from otn_enhanced.asm import effect_verify
from otn_enhanced.effects import ov5_cave
from otn_enhanced.cards import grapha as _g   # pac + ov3 helpers
from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3
from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
from otn_enhanced.asm.effect_builder import EffectBuilder, R3, R5

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_conscription.nds"

# --- the donor -------------------------------------------------------------
DONOR_CID = 0x192F                 # Conscription -- a Trap the user does not play, whose
                                   # own resolver is the C3c template.  donor_scan: name
                                   # floor 6 / desc floor 167 (ample), and NO per-cid
                                   # gates -- its single ARM9 hit at 0x020202CC is
                                   # `ADDS R7,R5,R4`, an instruction encoding that reads
                                   # as 0x192F.
CLS0_BASE, CLS0_COUNT, CLS0_STRIDE = 0x0227E64C, 0x51A, 0x18
CLS0_ROW = 644                     # asserted, not assumed -- verify() re-finds it by cid
STOCK_RES = 0x0221F1F5             # Conscription's own resolver (the C3c template)
STOCK_COND = 0x021F98F5            # its own condition: opponent's DECK + a free zone
HAND_COND = 0x021F2BD9             # the native "opponent's hand is not empty" condition,
                                   # shared by Confiscation / Delinquent Duo / Sentry

# --- engine entry points the payload calls (Thumb bit set: all are BLX targets)
STATE_PHASE = 0x0229AAFC           # [+0x70] = the resolver phase (resolver.phase_protocol)
STATE_A     = 0x0229AC94           # the per-player struct array
SIDE_STRIDE = 0x00000B3C           # per-side stride
HAND_COUNT  = 0x0229ACA0           # == STATE_A + 0x0C, the HAND COUNT
HAND_ARRAY  = 0x124                # == 0x49 << 2, the HAND card-word array
EFFECT_CTX  = 0x0229DE94           # shared effect-context block; +6 u16 = the chosen index
PEEK_POST   = 0x022599F9           # (opponent, 0) -> post "look at 1 random card", kind 5
REVEAL      = 0x021D2599           # (side, ref) -> the actual look-at
IS_MONSTER  = 0x02029E61           # (cid) -> is this cid a monster
MAY_SUMMON  = 0x021BA685           # ⚠️ A PREDICATE: (side, cid, ref, ZONE) -> 0/1, "may this
                                   # card be Special Summoned from zone Z".  IT SUMMONS
                                   # NOTHING -- every path ends `MOVS R0,#1` (0x021BA80A) or
                                   # `MOVS R0,#0` (0x021BA6CA).  Round 2 of this harness
                                   # called it and DISCARDED the boolean, which is why the
                                   # payload ran end to end and put no monster on the field.
                                   # It still has to be called: it is the per-cid summon
                                   # restriction gate, and its zone argument is what makes a
                                   # HAND source legal at all.
SS_ALLOWED  = 0x021AD871           # (side) -> may this player Special Summon right now.  The
                                   # second gate the template applies, between the predicate
                                   # and the action.
SUMMON      = 0x02269315           # THE ACTUAL SUMMON: (side, SLOT POINTER, 1, 0).  ⚠️ r1 is a
                                   # POINTER TO THE CARD-WORD SLOT in the source array, not a
                                   # cid/ref pair -- that is how it removes the card from the
                                   # source.  72 callers, all r0 = desc[+2], r1 = a pointer,
                                   # r2 = 1.  Conscription builds player[opp] + 0x304 (the
                                   # Deck); this builds player[opp] + 0x124 + index*4.
FREE_ZONE   = 0x021B9ECD           # (side) -> has a free monster zone; == 0x021B9708(side,8,0).
                                   # Conscription's OWN condition 0x021F98F4 called this, and
                                   # this patch swapped that condition out -- so the payload
                                   # re-applies it itself, right before the summon.
NOT_NORMAL_SUMMONABLE = 0x020232EC  # asserted intact, NEVER called -- see the docstring

C3_STUB, C3_RESERVE = ov5_cave.CAVE_C3_RES, 0x60        # the phase shell
# ⚠️ THE SHARED HALVES LIVE IN grapha, THE MODULE THAT SHIPS.  They were
# authored here, but this harness is never wired into apply_all_patches, so
# clause 3 would have called into an unwritten cave.  Re-exported for the tests
# below; grapha.main() is what actually installs them.
c3_post_stub = _g.c3_post_stub
c3_finish_stub = _g.c3_finish_stub
C3_POST, C3_POST_RESERVE = _g.C3_POST_STUB, _g.C3_POST_RESERVE
C3_FIN, C3_FIN_RESERVE = _g.C3_FIN_STUB, _g.C3_FIN_RESERVE
DIAG, DIAG_RESERVE = ov5_cave.CAVE_C3_DIAG, 0x40

NEW_CARD_TYPE = 27                 # Spell Card (was 29 = Trap Card); subtype stays Normal
STOCK_CARD_TYPE = 29
NEW_DESC = (b"Look at 1 random card in your opponent's hand, then, if it was a "
            b"monster, you can Special Summon it to your side of the field.")
TEXT_LANGS = _g.TEXT_LANGS


# ---------------------------------------------------------------------------
# the payload
# ---------------------------------------------------------------------------
def c3_stub(base: int = None) -> bytes:
    """Conscription's cls0 +04 SHELL: phase dispatch only, no logic of its own."""
    base = C3_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R5, R0, #0x0")
    b.ldr_const(4, DIAG)
    b.insn("LDR", "R0, [R4, #0x0]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R4, #0x0]")
    b.ldr_const(0, STATE_PHASE)
    b.insn("LDR", "R0, [R0, #0x70]")
    b.insn("LDR", "R1, [R4, #0x4]")
    b.insn("ORR", "R1, R0")
    b.insn("STR", "R1, [R4, #0x4]")
    b.insn("CMP", "R0, #0x7F")
    b.insn("BEQ", "fin")
    b.insn("CMP", "R0, #0x80")
    b.insn("BEQ", "post")
    b.insn("LDR", "R0, [R4, #0x8]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R4, #0x8]")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    b.label("post")
    b.call_addr(C3_POST, R5, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "stop")
    b.insn("MOV", "R0, #0x7F")
    b.insn("POP", "{R4, R5, PC}")
    b.label("fin")
    b.call_addr(C3_FIN, R5, via=R3)
    b.label("stop")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")






# ---------------------------------------------------------------------------
def _row_of(ov: bytes, cid: int) -> int:
    for i in range(CLS0_COUNT):
        if struct.unpack_from("<I", ov, _g._off(CLS0_BASE + i * CLS0_STRIDE))[0] == cid:
            return i
    raise AssertionError(f"cid {cid:#06x} has no cls0 record")


def _assert_preconditions(ov: bytes) -> None:
    row = _row_of(ov, DONOR_CID)
    assert row == CLS0_ROW, f"Conscription moved to cls0[{row}], not [{CLS0_ROW}]"
    o = _g._off(CLS0_BASE + row * CLS0_STRIDE)
    slots = struct.unpack_from("<6I", ov, o)
    assert slots[1] == STOCK_RES, f"+04 is {slots[1]:#010x}, not the stock resolver"
    assert slots[3] == STOCK_COND, f"+0C is {slots[3]:#010x}, not the stock condition"
    assert slots[2] == slots[4] == slots[5] == 0, "the donor gained a slot we would clobber"
    # the native condition we borrow, and the primitives we call, are all stock
    for name, addr in (("hand condition", HAND_COND), ("peek post", PEEK_POST),
                       ("reveal", REVEAL), ("summon", SUMMON)):
        assert addr & 1, f"{name} is not a Thumb pointer"
    # the gate we deliberately do NOT call is still where the TEMPLATE has it, so
    # "we chose not to call it" stays a meaningful statement rather than a stale one
    tmpl = struct.unpack_from("<H", ov, _g._off(0x0221F264))[0]
    assert tmpl == 0xF604, f"Conscription's Normal-Summonable gate moved ({tmpl:#06x})"
    print(f"0  cls0[{row}] = {{+04 0x{slots[1]:08X}, +0C 0x{slots[3]:08X}}} (stock)")


def apply_effect(ov: bytearray) -> None:
    o = _g._off(CLS0_BASE + CLS0_ROW * CLS0_STRIDE)
    struct.pack_into("<I", ov, o + 0x04, C3_STUB | 1)
    struct.pack_into("<I", ov, o + 0x0C, HAND_COND)
    print(f"2  cls0[{CLS0_ROW}] +04 -> 0x{C3_STUB | 1:08X} (the shared C3 payload), "
          f"+0C -> 0x{HAND_COND:08X} (opponent's hand not empty)")


def main(write_text: bool = True, src: str = SRC, out: str = OUT) -> None:
    rom, ovb = load_overlay3(src)
    ov = bytearray(ovb)
    _assert_preconditions(bytes(ov))
    apply_effect(ov)

    # only the shell -- grapha owns and installs the two shared halves
    for blob, addr, res, label in (
            (c3_stub(), C3_STUB, C3_RESERVE, "1c Conscription phase shell"),):
        effect_verify.assert_thumb1_only(blob, addr)
        assert len(blob) <= res, f"{label}: {len(blob)} B exceeds 0x{res:X}"
        ov5_cave.install_cave(rom, addr, blob, reserve=res)
        print(f"{label} @0x{addr:08X} ({len(blob)} B of 0x{res:X})")
    ov5_cave.install_cave(rom, DIAG, bytes(DIAG_RESERVE), reserve=DIAG_RESERVE)
    print(f"1d diagnostic block @0x{DIAG:08X} (0x{DIAG_RESERVE:X} B, zeroed)")

    save_overlay3(rom, bytes(ov), out)
    print(f"\nwrote overlay-3 + overlay-5 edits -> {out}")

    rom2 = ndspy.rom.NintendoDSRom.fromFile(out)
    fid, pac_data, archive = _g._open_pac(rom2)
    target_off, card_index = _g._find_prop(bytes(pac_data), archive, DONOR_CID)
    fields = GC.decode_entry(pac_data[target_off:target_off + 8])
    print(f"\n3  card_prop[{card_index}] BEFORE type={fields['card_type']}")
    assert fields["card_type_encoded"] == STOCK_CARD_TYPE, \
        f"donor is not a Trap Card (got {fields['card_type']})"
    fields["card_type_encoded"] = NEW_CARD_TYPE
    new_bytes = GC.encode_entry(fields)
    pac_data[target_off:target_off + 8] = new_bytes
    print(f"   card_prop[{card_index}] AFTER  "
          f"type={GC.decode_entry(new_bytes)['card_type']}")

    if write_text:
        pad_cursor: dict = {}
        for L in TEXT_LANGS:
            idxf = next((f for f in archive.files
                         if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
            descf = next((f for f in archive.files
                          if f.get_clean_name().lower() == f"card_desc_{L}.bin"), None)
            if not (idxf and descf):
                continue
            rec = idxf.address + 8 + card_index * 8
            old_desc_off = struct.unpack_from("<I", pac_data, rec + 4)[0]
            d = _g._place_string(pac_data, descf.address, descf.size,
                                 old_desc_off, NEW_DESC, pad_cursor)
            if d is not None:
                struct.pack_into("<I", pac_data, rec + 4, d)
            print(f"4  [{L}] desc -> "
                  f"{'in-place' if d == old_desc_off else f'relocated->0x{d:X}' if d else 'KEPT: no room'}")

    rom2.files[fid] = bytes(pac_data)
    rom2.saveToFile(out)
    print(f"\nwrote card_prop + text -> {out}")


def verify(out: str = OUT) -> bool:
    print(f"\n=== verify: Conscription C3 harness, against {out} ===")
    _, ovb = load_overlay3(out)
    ov = bytes(ovb)
    ok = True

    def chk(cond, msg):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
        ok = ok and bool(cond)

    row = _row_of(ov, DONOR_CID)
    chk(row == CLS0_ROW, f"the donor is still cls0[{CLS0_ROW}] (found {row})")
    o = _g._off(CLS0_BASE + row * CLS0_STRIDE)
    slots = struct.unpack_from("<6I", ov, o)
    chk(slots[1] == (C3_STUB | 1), f"+04 = 0x{slots[1]:08X} is the C3 payload")
    chk(slots[3] == HAND_COND, f"+0C = 0x{slots[3]:08X} is the hand-not-empty condition")
    keys = [struct.unpack_from("<I", ov, _g._off(CLS0_BASE + i * CLS0_STRIDE))[0]
            for i in range(CLS0_COUNT)]
    chk(all(keys[i] <= keys[i + 1] for i in range(CLS0_COUNT - 1)), "cls0 is still sorted")
    chk(keys.count(DONOR_CID) == 1, "exactly one cls0 record for the donor")

    # the three donors whose primitives we borrow must be byte-identical
    for cid, tbl, base, cnt, want04 in (
            (0x1EED, "cls3", 0x02279D74, 0x308, 0x0220F755),
            (0x1367, "cls1", 0x022860D4, 0x535, 0x0220F755),
            (0x1325, "cls0", 0x0227E64C, 0x51A, 0x0220E109)):
        hit = [i for i in range(cnt)
               if struct.unpack_from("<I", ov, _g._off(base + i * 24))[0] == cid]
        got = struct.unpack_from("<I", ov, _g._off(base + hit[0] * 24 + 4))[0] if hit else 0
        chk(len(hit) == 1 and got == want04,
            f"{tbl} donor 0x{cid:04X} keeps its own +04 0x{want04:08X}")

    for blob, addr, res, label in (
            (c3_post_stub(), C3_POST, C3_POST_RESERVE, "post half"),
            (c3_finish_stub(), C3_FIN, C3_FIN_RESERVE, "finish half"),
            (c3_stub(), C3_STUB, C3_RESERVE, "phase shell")):
        chk(len(blob) <= res, f"{label} is {len(blob)} B of 0x{res:X}")
        try:
            effect_verify.assert_thumb1_only(blob, addr)
            chk(True, f"{label} is Thumb-1 only")
        except Exception as e:                               # pragma: no cover
            chk(False, f"{label} is NOT Thumb-1 only: {e}")
    blob = c3_finish_stub()
    dis = "\n".join(f"{i.mnemonic} {i.op_str}"
                    for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(blob, C3_FIN))
    chk("#0xb" in dis, "the summon is given zone 0x0B (the HAND), not 0x0D")
    chk(f"0x{NOT_NORMAL_SUMMONABLE:x}" not in dis.lower(),
        "the 'can be Normal Summoned/Set' gate is NOT called (it is Conscription's clause)")

    rom2 = ndspy.rom.NintendoDSRom.fromFile(out)
    _, pac_data, archive = _g._open_pac(rom2)
    off, idx = _g._find_prop(bytes(pac_data), archive, DONOR_CID)
    f = GC.decode_entry(pac_data[off:off + 8])
    chk(f["card_type_encoded"] == NEW_CARD_TYPE,
        f"card_prop[{idx}] type = {f['card_type']} (was Trap Card)")

    print("PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys
    main(write_text="--text" in sys.argv)
    verify()

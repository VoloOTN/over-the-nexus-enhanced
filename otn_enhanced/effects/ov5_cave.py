"""Shared "appended overlay-5" cave allocator for the finished card patches.

WHY: overlay 3 (the card-effect engine) has only ~270 bytes of fragmented zero-run
"caves" for injected code, and the finished patches were competing for them.  This
module relocates those caves into a SPACIOUS new region appended to OVERLAY 5.

HOW IT WORKS (proven in-game 2026-06-09 -- see repo memory otn_overlay3_effect_engine.md):
  * Overlay 5 is CO-RESIDENT with overlay 3 during every duel and ends exactly at
    the duel heap base 0x0239A120.  Appending bytes to ov5 puts them at 0x0239A120+,
    resident and executable, callable from ov3 via an ordinary Thumb-1 BL (within
    +-4MB).  To make room we shrink the duel heap by raising ONE arm9 literal
    (the duel arena-lo at main-section offset 0x51ED8).
  * The ARM9 is a multi-section module: arm9 edits MUST go through
    ``ndspy.code.MainCodeFile`` (a raw codeCompression round-trip white-screens).
    This matches the path xsaber_table.py / wifi_timers.py already use, so the
    arena-lo edit chains cleanly with them.

*** ISA: the NDS ARM9 is ARMv5TE = Thumb-1 ONLY.  Injected stubs must never use
    Thumb-2 (movw/movt/b.w/cbz...).  All relocated stubs here are pre-existing,
    proven Thumb-1 code -- only their ADDRESS changes. ***

USAGE (inside a patch's ``main``, on the live ``rom`` object, BEFORE save):
    from otn_enhanced.effects import ov5_cave
    ov5_cave.install_cave(rom, ov5_cave.CAVE_MYSTIC, stub_bytes, reserve=0x60)
    # ... point your overlay-3 reference at CAVE_MYSTIC | 1 ...
``install_cave`` is IDEMPOTENT for the expansion: the first patch in a chain grows
ov5 + raises arena-lo; later patches see it already expanded and just write their
own (distinct, non-overlapping) slot.
"""
from __future__ import annotations

import struct

import ndspy.code
import ndspy.codeCompression
import ndspy.rom

# ---------------------------------------------------------------------------
# Overlay 5 geometry (EU rom.nds / eu_apfix.nds -- identical ov5 layout)
# ---------------------------------------------------------------------------
OV5_ID = 5
OV5_RAM_BASE = 0x022C5900                       # ov5 load address
OV5_NATIVE_END = 0x0239A120                     # ov5 native end == appended-region start == duel arena-lo
OV5_NATIVE_LEN = OV5_NATIVE_END - OV5_RAM_BASE  # 0xD4820

# How much to append to ov5 (== how much the duel heap is shrunk).
#
# 0x10000 (64 KB). The cave was full at 0x4000 (16 KB): Junk Speeder clause 2 took the last 0x150
# bytes and then had to delete dead code to fit a revision.
#
# MEASURED BEFORE CHANGING, not guessed.  The duel arena is
# [0x0239A120, 0x023E0000) = 0x45EE0 = 279.7 KB and is an NNS_FndExpHeap whose
# header exposes its free list (+0x18 heapStart, +0x1C heapEnd, +0x24/+0x28
# free-list head/tail).  Across ALL 153 live-duel savestates in
# data/over_the_nexus/working the free list is a SINGLE block every time and the
# peak allocation is 37.3 KB (minimum 33.1 KB).  64 KB therefore leaves the heap
# 215.7 KB against a 37.3 KB observed peak -- about 5.8x headroom.
#
# The raise is also COMPLETE at any size: 0x0239A120 occurs exactly ONCE as an
# aligned u32 in the whole ROM (arm9 main section 0x02051ED8, the literal
# _raise_arena_lo edits) -- scanned across the ARM9 main section and all 50
# overlays -- and the only other overlay sharing ov5's load address is ov41
# (0x161E0, the puzzle overlay), an order of magnitude smaller.
#
# ⚠️ 37.3 KB is a measured LOWER BOUND on the true peak: the sample is mid-turn
# normal duels, not duel load or tag/turbo modes.  The MARGIN carries the risk,
# not the sample -- so bump further only with fresh numbers, and note that the
# rollback is this one constant (plus the ledger refresh; no CAVE_* slot moves,
# because growing RESERVE moves only the ceiling).
# See notes/ov5-cave-capacity-findings.md and the KB fact mem.ov5_cave_can_grow.
# 0x10000 -> 0x14000 (+16 KB). Scan of the 62 duel-arena savestates in data/over_the_nexus/working: 61 use
# 33.1..35.6 KB, the outlier rom_ov5_canary.ml1 109.2 KB; 0x14000 leaves a 199.7 KB heap = 1.8x even that outlier.
RESERVE = 0x1B400   # +0xC00 (2026-11-12 session 2) for Eidos E1 GY half + E3, the Monarch never-miss-timing front, the prefind stub growth and Masterplan C2 (0x50 B were free); was 0x1A800; +0xC00 (2026-11-12) for the remaining Monarch cards (Perfection / First Monarch / Prime GY / Erebus halves; only 0x30 B were free); was 0x19C00; +0x1000 (2026-11-11) for Strike + Domain of the Monarchs (~0x310 B were free); was 0x18C00; +0x1000 (2026-11-11) for Edea + the remaining Monarch monsters (only 0x250 B were free); was 0x17C00; +0x800 (2026-11-11) for The Monarchs Revolt (the GY table relocated AGAIN for 19+ virtual rows: GYV2 ROWS 0x180 / HAS 0x100 / POST 0x120); was 0x17400; +0x400 (2026-11-11) for Frost Blast of the Monarchs (a 18th virtual GY row needs the POST stub relocated too); was 0x17000; +0x400 (2026-11-11) for Pantheism's Graveyard effect (a 17th virtual GY row needs a bigger table + HAS stub); was 0x16C00; +0x400 (2026-11-11) for Thestalos the Mega Monarch (+ Restoration / Awaken / the Mega set growing); was 0x16800; +0x400 (2026-11-10) for Return of the Monarchs; was 0x16400 (+0x400 for Tenacity-era slack) ; +0x400 (2026-11-10) for The Monarchs Stormforth; was 0x16000 (+0x400 for March of the Monarchs (protection fronts); was 0x15C00 (Caius), 0x15800 (Raiza), 0x15400 (Zaborg), 0x15000 (mega_monarch E1/E2); +0x800 (2026-11-09) Block Dragon C3, was 0x14400
OV5_NEW_LEN = OV5_NATIVE_LEN + RESERVE

# ---------------------------------------------------------------------------
# ARM9 duel arena-lo literal (the single source of the heap base)
# ---------------------------------------------------------------------------
from otn_enhanced.effects.common import ARM9_BASE
ARENA_LO_OFF = 0x51ED8                          # main-section offset of the arena-lo word
ARENA_LO_NATIVE = OV5_NATIVE_END                # 0x0239A120
ARENA_LO_NEW = ARENA_LO_NATIVE + RESERVE        # heap base raised above the grown ov5

# ---------------------------------------------------------------------------
# Fixed, non-overlapping cave map (RAM addresses inside the appended region).
# Placed at the START so each stub's BL reach is independent of RESERVE.
# Each address is 4-aligned (required: the stubs use `ldr rX,[pc,#imm]` pools).
# ---------------------------------------------------------------------------
CAVE_MINEFIELD = 0x0239A120     # RETIRED: moved to the NATIVE ov3 handler 0x0223D075 (no cave3 slot;
                                #   ov3 compaction Phase D). Was Reborn Tengu's deck self-SS selector (<= 0x40 bytes);
                                #   only main(ov3=False) writes it now.
                                # (historical name: the card used to sit on the REAL
                                #  card Minefieldriller 0x2085; reborn_tengu
                                #  moved it to the Normal Monster 0x1463 and gave
                                #  Minefieldriller back. The blob itself is unchanged
                                #  and cid-agnostic; the constant keeps its name so
                                #  shooting_quasar's chained-build probe and the
                                #  allocation ledger do not have to be re-keyed.)
CAVE_BOGGART   = 0x0239A160     # moved to ov3 cave3.CAVE3_BOGGART: boggart synchro stub (== 0x18 bytes)
CAVE_MYSTIC    = 0x0239A180     # moved to ov3 cave3.CAVE3_PIPER_RES: mystic-piper resolver stub (== 0x48 bytes)
CAVE_GK_WRAPPER = 0x0239A1E0    # moved to ov3 cave3.CAVE3_GK_WRAPPER
CAVE_GK_FILTER  = 0x0239A220    # moved to ov3 cave3.CAVE3_GK_FILTER
CAVE_TG_FILTER    = 0x0239A260  # moved to ov3 cave3.CAVE3_TG_FILTER
CAVE_TG_WRAPPER   = 0x0239A2A0  # moved to ov3 cave3.CAVE3_TG_SELECTOR
CAVE_TG_NEGATE    = 0x0239A2E0  # moved to ov3 cave3.CAVE3_TG_NEGATE: negate-first + embargo stub  (0x60 bytes)
CAVE_TG_TAGDATA   = 0x0239A340  # 12-byte side-table: [0]=ARMED flag,[1]=pad,[2..11]=EMBARGO[player][slot_rel]
CAVE_TG_SS_HOOK   = 0x0239A350  # SS-engine (0x0226925C) entry-hook stub (0x60 bytes)
CAVE_TG_PRED_HOOK = 0x0239A3B0  # synchro-material predicate entry-hook stub (0x90 bytes)
CAVE_WATT_WRAPPER = 0x0239A440  # moved to ov3 cave3.CAVE3_WATT_WRAPPER: wattcobra cloned deck-search wrapper (== 0x24 bytes)
CAVE_WATT_FILTER  = 0x0239A480  # moved to ov3 cave3.CAVE3_WATT_FILTER: wattcobra custom set-code+DEF filter (== 0x30 bytes)
CAVE_LIB_RETIRED  = 0x0239A4C0  # hyper-librarian round-15 hook slot, RETIRED (0xC0 bytes, zero; too small for round 16)
CAVE_LIB_LATCH    = 0x0239A580  # moved to ov3 cave3.CAVE3_LIB_LATCH: hyper-librarian once-per-summon latch word (stays 0 in the ROM image)
CAVE_LIB_RET0     = 0x0239A584  # hyper-librarian inert "return 0" resolver (4 bytes)
CAVE_LIB_SCRATCH  = 0x0239A588  # moved to ov3 cave3.CAVE3_LIB_SCRATCH: hyper-librarian black-box recorder telemetry (0x20 bytes, zero in image)
CAVE_TSH_RETIRED  = 0x0239A5A8  # thunder sea horse round-1 filter slot, RETIRED (0x60 bytes, zero; too small for the count>=2 filter)
CAVE_TSH_WRAPPER  = 0x0239A608  # thunder sea horse: cloned deck-search wrapper (0x24 bytes)
CAVE_LIB_HOOK     = 0x0239A648  # moved to ov3 cave3.CAVE3_LIB_HOOK: hyper-librarian SS-commit hook (round 16, 3DS-faithful; shared by both hook sites) (<= 0x100 bytes)
CAVE_TSH_FILTER   = 0x0239A748  # thunder sea horse: Lv4+LIGHT+Thunder+ATK<=1600 + deck-copies>=2 filter (0xC0 bytes)
CAVE_TSH_COND     = 0x0239A808  # thunder sea horse: act-cond shim -- HOPT + "already SS'd" embargo, chains native cond (0x60 bytes)
CAVE_TSH_RES      = 0x0239A868  # thunder sea horse: resolver shim -- attaches the (0xB, kid) embargo/HOPT node, chains native res (0x40 bytes)
CAVE_TSH_SSGATE   = 0x0239A8A8  # thunder sea horse: can-SS mega-gate deny-key hook (replayed node query + key 0x0FEC) (0x30 bytes)
CAVE_TSH_MAIN     = 0x0239A8D8  # thunder sea horse: main state machine -- pick-1-from-deck UI, add 2 copies of the selected name (0x140 bytes)
CAVE_WNM_CHECK     = 0x0239AA18  # moved to ov3 cave3.CAVE3_WNM_CHECK: w nebula meteorite: shared LIGHT+Reptile monster check core (0x40 bytes)
CAVE_WNM_FILTER    = 0x0239AA58  # moved to ov3 cave3.CAVE3_WNM_FILTER: w nebula meteorite: populate deck filter -- CHECK + Level>=7 (0x40 bytes)
CAVE_WNM_WRAPPER   = 0x0239AA98  # moved to ov3 cave3.CAVE3_WNM_WRAPPER: w nebula meteorite: cloned deck-search wrapper (0x24 bytes)
CAVE_WNM_COND      = 0x0239AAC8  # moved to ov3 cave3.CAVE3_WNM_COND: w nebula meteorite: act-cond -- any face-down monster on the field (0x60 bytes)
CAVE_WNM_SUB_ACT   = 0x0239AB28  # moved to ov3 cave3.CAVE3_WNM_SUB_ACT: w nebula meteorite: activation per-zone eligibility (mask 0x118) (0x20 bytes)
CAVE_WNM_SUB_RIDER = 0x0239AB48  # moved to ov3 cave3.CAVE3_WNM_SUB_RIDER: w nebula meteorite: rider per-zone eligibility (mask 0x15 + LIGHT Reptile) (0x70 bytes)
CAVE_WNM_RES_ACT   = 0x0239ABB8  # moved to ov3 cave3.CAVE3_WNM_RES_ACT: w nebula meteorite: activation resolver -- flip-all-face-down face-up + arm rider (0xA0 bytes)
CAVE_WNM_RES_RIDER = 0x0239AC58  # moved to ov3 cave3.CAVE3_WNM_RIDER_A + CAVE3_WNM_RIDER_B (split): w nebula meteorite: End-Phase rider FSM -- flip own LIGHT Reptiles down, draw, optional SS (0x180 bytes)
CAVE_WW_MAIN   = 0x0239ADD8   # wonder wand: +500 ATK grant shim (Black-Pendant-clean) (0x40 bytes)
CAVE_WW_TARGET = 0x0239AE18   # wonder wand: Spellcaster-only equip-target predicate (0x60 bytes)
CAVE_WW_RES    = 0x0239AE78   # wonder wand: ignition resolver -- send both to GY + draw 2 (0x60 bytes)
# --- T.G. Striker (Destiny HERO - Fear Monger 0x1A64 donor) ---
CAVE_TGS_TRAMP   = 0x0239AED8  # striker E1: hand-SS eligibility trampoline (IN-GAME CONFIRMED -- do not move) (0x40 bytes)
# (0x0239AF18..0x0239AF40 == 0x28 bytes free between the Striker E1 trampoline and Warwolf's SS hook)
# --- T.G. Warwolf (Emissary of the Afterlife 0x1796 donor): Lv<=4-SS trigger + End-Phase search ---
CAVE_TGW_SS_HOOK = 0x0239AF40  # moved to ov3 cave3.CAVE3_TGW_ARMHOOK: warwolf: SS-commit hook -- replay 0x021A25A0, gate summoned Level<=4, offer SS-from-hand (0x100 bytes)
CAVE_TGW_FILTER  = 0x0239B040  # moved to ov3 cave3.CAVE3_TGW_FILTER: warwolf: except-self T.G. deck filter (has_set_code(cid,0x5C) AND cid!=0x1796) (0x40 bytes)
CAVE_TGW_WRAPPER = 0x0239B080  # moved to ov3 cave3.CAVE3_TGW_WRAPPER: warwolf: cloned deck-search wrapper -> the filter above (0x24 bytes)
# --- T.G. Striker E2 (End-Phase "add 1 T.G., except self" deck-search) -- placed after Warwolf to avoid
#     the collision the old 0x0239AF18/0x0239AF48 layout had with CAVE_TGW_SS_HOOK. ---
CAVE_TGS_FILTER  = 0x0239B0A8  # moved to ov3 cave3.CAVE3_TGS_FILTER: striker E2: except-self T.G. deck filter (has_set_code(cid,0x5C) AND cid!=0x1A64) (0x30 bytes)
CAVE_TGS_WRAPPER = 0x0239B0D8  # moved to ov3 cave3.CAVE3_TGS_WRAPPER: striker E2: cloned deck-search wrapper -> the filter above (0x28 bytes)
CAVE_TGS_E2TRAMP = 0x0239B100  # striker E2: (LEGACY single-cid arming; superseded by the SHARED one below) (0x28 bytes)
# --- SHARED T.G. any-leave arming trampoline (multi-cid; both Striker & Warwolf register here) ---
# One hook at 0x021C8216 can host only ONE trampoline, but BOTH T.G. cards need their cid routed to
# the any-leave gate. So a SINGLE shared trampoline scans a zero-terminated cid list and branches to
# the gate if r4 matches ANY entry; each patch idempotently installs the hook + appends its cid.
CAVE_TG_ARMTRAMP = 0x0239B128  # moved to ov3 cave3.CAVE3_TGSH_ARMTRAMP: shared any-leave arming trampoline (0x40 bytes; grew when Quasar's
                               # immediate-action branch was added -- ARMLIST moved out to make room)
CAVE_TG_ARMLIST  = 0x0239B708  # moved to ov3 cave3.CAVE3_TGSH_ARMLIST: zero-terminated u16 cid list the trampoline scans (0x10 bytes = up to 7 cids)
# --- SHARED T.G. hand-SS trampoline (multi-cid; both Striker & Warwolf register here) ---
# The single hook 0x0224C026 (BL 0x0225E51C) can host only ONE trampoline, but both T.G. cards need
# to force the "can SS from hand" flag (bit 0x4). One shared trampoline replays the dispatch, then
# walks a {cid u16, cond-stub-ptr u32}[] table (zero-terminated): for a matching cid it calls that
# card's condition stub (r0 = side) and, if it returns nonzero, ORs bit 0x4 into the flags.
CAVE_TG_SSTRAMP  = 0x0239B168  # moved to ov3 cave3.CAVE3_TGSH_SSTRAMP: shared hand-SS trampoline (0x40 bytes)
CAVE_TG_SSTABLE_OLD = 0x0239B1A8  # RETIRED -- the 4-row hand-SS dispatch table (0x20 bytes) was FULL
                                  #   (Striker, Junk Servant, Unknown Synchron + terminator) and could not grow:
                                  #   CAVE_TG_SSCOND_STRIKER sits at exactly +0x20. Moved to CAVE_TG_SSTABLE below.
CAVE_TG_SSCOND_STRIKER = 0x0239B1C8  # moved to ov3 cave3.CAVE3_TGS_COND: Striker's condition stub: only opp controls a monster (0x30 bytes)
CAVE_TG_SSCOND_WARWOLF = 0x0239B1F8  # moved to ov3 cave3.CAVE3_TGW_E1COND: Warwolf's condition stub: canSS && latch && response-window (0x50 bytes)
CAVE_TGW_ARMLATCH = 0x0239B248  # moved to ov3 cave3.CAVE3_TGW_ARMLATCH: Warwolf E1: "a Lv<=4 monster was just SS'd" armed latch word (0x4 bytes)
# --- T.G. Rush Rhino (Dash Warrior 0x22E6 donor, records-free Normal Monster): E1 battle ATK boost + E2 search ---
CAVE_TGR_FILTER  = 0x0239B250  # moved to ov3 cave3.CAVE3_TGR_FILTER: rush rhino E2: except-self T.G. deck filter (has_set_code(cid,0x5C) AND cid!=0x22E6) (0x30 bytes)
CAVE_TGR_WRAPPER = 0x0239B280  # moved to ov3 cave3.CAVE3_TGR_WRAPPER: rush rhino E2: cloned deck-search wrapper -> the filter above (0x28 bytes)
CAVE_TGR_ATK_HOOK = 0x0239B2A8  # rush rhino E1: damage-step battle ATK-boost trampoline (+400 when this card is the attacker) (0x60 bytes)
# --- SHARED T.G. End-Phase registry-invoke trampoline (multi-cid; avoids consuming a scarce phantom registry
# row per card). The registrar 0x02254221 (End-Phase-trigger scheduler) is invoked per registry row with the
# row's cid set up as the effect ctx; both spare phantom rows are already taken (Striker 0x1A9F, Warwolf 0x2347).
# So instead a single shared trampoline (hooked on the registry walker's per-row dispatch -- site pinned during
# GDB bring-up) scans a zero-terminated cid list and invokes 0x02254221 for each listed T.G. cid at End Phase. ---
CAVE_TG_REGTRAMP = 0x0239B308  # moved to ov3 cave3.CAVE3_TGSH_REGTRAMP: shared End-Phase registry-invoke trampoline (0x50 bytes: resolver call + once-per-EP phase gate + invoke loop)
CAVE_TG_REGLIST  = 0x0239B358  # moved to ov3 cave3.CAVE3_TGSH_REGLIST: zero-terminated u16 cid list the reg trampoline invokes (0x10 bytes = up to 7 cids)
# --- T.G. Warwolf E1 (summon-response hand-SS): the missing "enumerate the donor as a responder" piece ---
# The SS-responder enumeration 0x02265CF8 is a hardcoded per-summon-kind cid dispatch that never lists the
# records-free donor 0x0FA9. This trampoline (hooked over BL 0x02244418 @0x02266390, inside 0x02265CF8)
# replays that call and then registers the donor via 0x021D36C0, exactly as Doppelwarrior's own block does.
CAVE_TGW_E1_ENUMREG = 0x0239B368  # moved to ov3 cave3.CAVE3_TGW_ENUMREG: warwolf E1: summon-responder enumeration-registration trampoline (0x40 bytes)
# --- T.G. Warwolf E2 End-Phase WALKER-HOOK search (the self-contained fix) ---
# E2 ("End-Phase: add 1 T.G. except self, with a pick menu") is shadowed at cls2 resolution (E1's
# summon-response record is the leftmost same-cid record; find_event_handler returns leftmost for the
# records-free donor 0x0FA9, and telemetry proved the End-Phase path never BLXes the record's +04). So
# E2's ACTION is supplied self-contained by an ov5 stub hooked over the End-Phase walker's event-post
# `BL 0x021C3BC8` @0x022500CC (R1 = the resolving trigger's cid, live, End-Phase-only). For R1==0x0FA9
# the stub logs the cid to a small telemetry ring (diagnostic), drives the deck-selection pick menu
# (SEL_*/MOVE_TO_HAND over Warwolf's populate criteria), then replays `BL 0x021C3BC8`. This slot spans
# the two retired coexistence slots (old RESSHIM 0x40 + TELEM 0x10) extended into the former free run.
CAVE_TGW_E2_SEARCH = 0x0239B3A8  # moved to ov3 cave3.CAVE3_TGW_E2SEARCH: warwolf E2: End-Phase COMMIT cid-swap stub (0x0FA9->phantom 0x2511) (0x40 bytes)
# --- T.G. Hyper Librarian CHAIN-DRAW (ENABLE_CHAIN_DRAW): make the draw a response-able chain link ---
# The base card's draw is a silent direct DRAW_PRIM; the chain version registers a cls2 WHEN responder
# per on-field Librarian at the enumeration hook (via register-prim 0x021D3168), and this ov5 resolver
# performs the draw when the chain link RESOLVES. It clones the known-good HANDSS_RES 0x02206ABD phase
# skeleton (act at phase word [0x0229AB6C]==0x80, DRAW_PRIM(ctx+0x2,1), return 0x7F; else return 0).
CAVE_LIB_DRAW_RES = 0x0239B3E8  # moved to ov3 cave3.CAVE3_LIB_DRAW_RES: hyper librarian chain: draw-1 cls2 resolver (HANDSS-clone + face-up gate) (0x60 bytes)
# Shooting Quasar: "materials must be Synchro monsters" gate. Hooked over the 4 bytes at
# 0x022482B6 (`cmp r0,#0xb ; beq`) INSIDE the inner Synchro-material predicate 0x0224829C --
# GDB-confirmed to run for EVERY material (the Tuner via the outer predicate 0x022485B4, each
# non-Tuner via the third predicate 0x02248A88), with r4 = the material's cid and r7 = the
# Synchro's cid. Boggart owns the adjacent site 0x022482B2, so the two hooks chain.
CAVE_QSR_PRED  = 0x0239B448   # moved to ov3 cave3.CAVE3_QSR_PRED: quasar: Synchro-only material gate (<= 0x40 bytes)
# Quasar once-per-turn latch (Pot-of-Duality idiom, cloned from thunder_sea_horse):
# cond shim denies if the (0xB, 0x211B, 1) turn-log node exists, then chains the native
# condition; res shim attaches that node, then chains the native negate resolver.
CAVE_QSR_COND  = 0x0239B488   # moved to ov3 cave3.CAVE3_QSR_COND: quasar: HOPT act-cond shim (<= 0x60 bytes)
CAVE_QSR_RES   = 0x0239B4E8   # moved to ov3 cave3.CAVE3_QSR_RES: quasar: HOPT resolver shim (<= 0x40 bytes)
CAVE_QSR_EXSEL = 0x0239B528   # moved to ov3 cave3.CAVE3_QSR_EXSEL: quasar PART M: Extra-Deck named-target selector (clone of the donor's
                              # GY selector 0x0223E904 with flags #8->#2 and the builder swapped
                              # 0x0223C4E8 (GY) -> 0x0223BE40 (Extra Deck)) (<= 0x40 bytes)
CAVE_QSR_RECSTUB = 0x0239B568 # quasar DIAGNOSTIC: cls2 +0C recorder shim (counts calls / cids /
                              # verdicts, then tail-calls the real condition) (<= 0x60 bytes)
CAVE_QSR_RESREC  = 0x0239B5C8 # quasar DIAGNOSTIC: per-cid resolver-entry counter (<= 0x50 bytes)
CAVE_QSR_RESREC1 = 0x0239B638 # quasar DIAGNOSTIC: same recorder installed on the CLS1 row, so we
                              # can tell WHICH class the leave event dispatches to (<= 0x50 bytes)
CAVE_QSR_SCRATCH = 0x0239B618 # quasar DIAGNOSTIC: recorder counters (0x30 bytes)
                              #   +00 cond called (instrumented rows) +04 last cid seen by cond
                              #   +08 cond called for 0x211B          +0C last verdict for 0x211B
                              #   +10 verdict!=0 for 0x211B           +14 resolver entered 0x211B
                              #   +18 resolver entered 0x2085 (ctrl)  +1C last cid at resolver
CAVE_QSR_LEAVE = 0x0239B688   # moved to ov3 cave3.CAVE3_QSR_LEAVE: quasar PART N: immediate leave-action stub reached from the SHARED
                              # leave trampoline (0x021C8216) when the departing cid is 0x211B --
                              # scans the Extra Deck for 0x239D and drives SS_FROM_EXTRA (0x80 bytes)
# --- Armory Arm (cid 0x1F33): battle-destruction burn "still in the GY at resolution" bug fix ---
# The code=0x0C LP-change resolver (function 0x02204D08) gates the burn on the destroyed monster
# being CURRENTLY in the GY (zone-scan 0x021A220C -> zone byte == 0xE), so it fizzles once the
# monster leaves the GY. This detour (installed over the code=0x0C branch entry at 0x02204E42)
# replays the ref computation + zone-scan, and ONLY for source cid 0x1F33 forces the located zone
# byte to 0xE so the caller's gate always passes; the subsequent ATK-by-cid read is GY-independent.
# All other code=0x0C cards (Flame Wingman, Nitro Unit, ...) are byte-identical.
CAVE_ARMORY_BURN = 0x0239B720  # RETIRED: moved to cave3.CAVE3_ARMORY_BURN. armory arm: GY-presence-gate bypass for the battle burn (<= 0x60 bytes)
CAVE_ARMORY_SCRATCH = 0x0239B780  # RETIRED (telemetry off; stub now in cave3.CAVE3_ARMORY_BURN). armory arm DIAGNOSTIC: black-box recorder counters (0x20 bytes, zero in image)
                               #   +00 code=0x0C branch entries (any cid)  +04 last source cid seen
                               #   +08 entries with cid==0x1F33            +0C last ref (0x1F33)
                               #   +10 last located word from 0x021A220C (0x1F33)
# --- Safe Zone (Battle-Scarred 0x16A2 donor): clause 2 "cannot be destroyed by battle" ---
# 0x02197E90 is the rules "can this monster be destroyed by battle" predicate; it returns 0 when
# protected, via the shared tail 0x02197F16. Protection comes from either the innate cid list
# 0x0226D26C or a flat chain of 0x021A0950(side, slot, granting cid) rider queries at
# 0x0219848C..0x02198512 (Heart of Clear Water, Ninjitsu Art of Decoy, Mist Body, GB Battle Manica,
# Rocket Pilder). The chain is dense with no free slot, so this stub detours ONE link -- the GB
# Battle Manica query at 0x021984EC -- and ORs in a second query for the donor cid, leaving Battle
# Manica's own protection intact. Relies on r5=side / r4=slot being live across the chain, which
# every native link relies on too (`adds r0,r5,#0 ; adds r1,r4,#0`).
CAVE_SZ_PROTECT = 0x0239B7A0  # moved to ov3 cave3.CAVE3_SZ_PROTECT: safe zone: battle-destruction protection rider query (<= 0x30 bytes)
# --- Safe Zone clauses 3+4: "cannot be destroyed by / cannot be targeted by the OPPONENT's effects" ---
# 0x021B021C(r0=r7 acting card, r1=r6 side, r2=r5 slot, r3=[sp] "targets" flag) is the target-
# eligibility predicate: it returns 1 (@0x021B081E) when the monster IS affectable and exits via
# 0x021B0296 (returning the caller's [sp+0x58] default) when it is NOT. Inside the `targets` block,
# Heart of Clear Water 0x150A takes exactly that protected exit. This stub detours HoCW's own query
# at 0x021B05CC: it runs the HoCW query untouched, and only on a miss checks the donor's rider AND
# that the acting card belongs to the OPPONENT, in which case it drops the saved LR and jumps
# straight to 0x021B0296 (SP restored, so the caller's [sp+0x58] read stays valid).
CAVE_SZ_TARGET = 0x0239B7D0   # moved to ov3 cave3.CAVE3_SZ_TARGET: safe zone: opponent-only targeting/effect-destruction protection (<= 0x50 bytes)
# --- Safe Zone clause 5: "it cannot attack your opponent directly" ---
# 0x021A6ABC(r0=r5 side, r1=r6 slot) answers "can this monster attack DIRECTLY?": 1 = yes,
# 2 = the Toon Defense special case, and 0 (@0x021A72A4) = no. Its node chain (Opti-Camouflage
# Armor 0x1759, Gear Golem 0x1295, ...) is the set of riders that GRANT a direct attack, so
# clause 5 is the inverse: force the 0 exit. This stub detours the Toon Defense query at the top
# of the function (0x021A6AE0); on a miss it checks the donor's rider and, if present, drops the
# saved LR and jumps to 0x021A72A4 (whose `add sp,#0x40` needs the caller's frame).
CAVE_SZ_DIRECT = 0x0239B820   # moved to ov3 cave3.CAVE3_SZ_DIRECT: safe zone: forbid the direct attack (<= 0x40 bytes)
# --- Sea Lancer (Mermaid Archer 0x1FFC donor) E1: equip from YOUR banished Fish/Sea Serpent/Aqua ---
# The donor's E1 is a records-driven cls3[527] effect. Retargeting its slot5 (+0x14) from the BOARD
# picker thunk 0x02234D8C to the OFF-FIELD template 0x02235604 makes the engine enumerate a list
# zone via the criteria registry 0x022713C4 -- which needs a row for 0x1FFC whose handler supplies
# a multi-race filter. CAVE_SL_CRIT is that handler: a clone of Unicorn Beacon's 0x02242E60 calling
# the registrar 0x0223C6AC(side, cid, predicate, &list, criteria, type) with the race-list predicate
# 0x0223C791, the list below, criteria 0x00010002 and type 0x8 ("read the banished zone, own side
# only" -- the add-to-hand family's type; UB's 0xE would add bit 2 = BOTH players and bit 4 = the
# Special-Summon-legality gate, neither of which Sea Lancer wants since she EQUIPS).
CAVE_SL_CRIT     = 0x0239B860  # moved to ov3 cave3.CAVE3_SL_CRIT: sea lancer E1: criteria-registry handler (<= 0x40 bytes)
CAVE_SL_RACELIST = 0x0239B8A0  # moved to ov3 cave3.CAVE3_SL_RACELIST: sea lancer E1: zero-terminated race list {8, 5, 14, 0} (0x10 bytes)
# Unused: a cid-scoped detour over the donor resolver 0x0220BFFC's board-array pick dereference at
# 0x0220C05C..0x0220C07E. 0x0220BFFC never moves the card AT ALL -- 0x0225BDD8, which it ends on, only
# posts a UI request (kind 4 via 0x0225BD40) -- so the whole resolver is replaced instead
# (CAVE_SL_EQUIP below), which reads its pick with 0x02234964 natively.
CAVE_SL_PICK     = 0x0239B8B0  # sea lancer E1: unused pick detour (0x60 bytes, zero in image)
# --- Sea Lancer E1: the equip ACTION, cloned from the Cyberdarks ---
# Cyberdark Horn/Edge/Keel (cls1[588..590]) equip a monster FROM THE GRAVEYARD -- an off-field LIST
# zone, structurally identical to Sea Lancer's banished zone. Their record already uses the same
# off-field slot5 template 0x02235604 with slots 2/3/4 NULL, and their resolver 0x022186E4 reads its
# pick with 0x02234964, LOOPS over every recorded pick, and actually relocates each card via
# 0x021C7484(side, SOURCE_ZONE, ref, side, ...). It is Graveyard-bound in exactly FOUR places, all
# ⚠️ "relocates each card via 0x021C7484" is WRONG. Disassembled,
# 0x021C7484 packs its six args into four u16s and tail-calls 0x021C3BC8 with opcode 0x40 --
# it is a thin wrapper of the ANIMATION/REPLAY COMMAND QUEUE append (0x02299B68), not a mover.
# See KB event.animation_command_queue. The zone-code edits listed below still describe real
# immediates in the lifted clones, but whoever revisits Sea Lancer E1 must find where the
# equip actually lands the card -- do not assume this call does it.
# verified by an exhaustive scan of both functions for zone-code immediates and container offsets:
#   locator 0x021A2510  +0x10 `ldr r4,[r2,#0x14]` GY count   -> `[r2,#0x1C]` banished count
#   locator 0x021A2510  +0x44 pool 0x55C GY array            -> 0x7B4 banished array
#   resolver 0x022186E4 +0x172 `mov r1,#0xE` GY zone code    -> `mov r1,#0xF` banished
#   resolver 0x022186E4 +0x1E4 pool 0x55C GY array           -> 0x7B4 banished array
# Both functions are lifted whole (lift_handler_to_builder round-trips them byte-exactly at their
# original address) so the natives stay untouched and no cid-scoping is needed -- the clones are
# reachable only from cls3[527].
CAVE_SL_LOCATE   = 0x0239B910  # moved to ov3 cave3.CAVE3_SL_LOCATE: sea lancer E1: ref -> banished-array index (0x021A2510 clone) (0x60 bytes)
CAVE_SL_EQUIP    = 0x0239B970  # moved to ov3 cave3.the NATIVE resolver 0x022186E4 + cid-gated detours CAVE3_SL_LOCSEL/ARR1/ARR2/ZONE: sea lancer E1: equip-from-banished resolver (0x022186E4 clone) (0x200 bytes)
# --- Sea Lancer E1: "any number", i.e. MULTI-select ---
# The off-field target template 0x02235604 records exactly ONE pick, so E1 could only ever equip one
# card. 0x02235700 is its MULTI-select sibling (Burial from a Different Dimension, Pot of Avarice,
# Miracle Dig, Psychic Path...): it hands the picker a count, then LOOPS in its third sub-step,
# recording every chosen card through the same 0x022347B0 / 0x02234880 recorders. The cloned equip
# resolver already iterates every recorded pick, so this is the only remaining piece.
# Its per-card count comes from a cid switch in its prologue that sets r4 (count code) and r6
# (prompt id); the tail derives max picks = r4 - 6 and min required = (r4 - 6 if 6 <= r4 <= 0x26
# else 1). cid 0x1FFC has no case there and would fall to the default r4 = 8 => "exactly 2", which
# would FIZZLE with a single banished target. So the clone's 3-halfword prologue is replaced with
# `mov r4,#0x2A ; mov r6,#0x4C ; b <tail>`, skipping the switch: min 1, max 36 -- the same mode
# Burial from a Different Dimension uses, which is the closest shipped analogue (banished zone,
# multi-target, no minimum).
# !! 0x360, not 0x240: the template's TRUE extent is 0x34C. detect_function_size reported 0x232
# because it stops at the `pop {..,pc}` at 0x02235946, before the inline literal pool -- and a
# truncated lift still round-trips byte-for-byte, so only a pool-containment check catches it.
# Shipping the short copy made the tail's `ldr r7,[pc,#0x78]` read past the blob and take a data
# abort (freeze savestate: PC = 0xFFFF0108, LR = 0x0239BD8C inside this clone).
CAVE_SL_SELECT   = 0x0239BB70  # moved to ov3 cave3.CAVE3_SL_SELECT (prologue + jump into the native tail 0x02235912): sea lancer E1: multi-select target template (0x02235700 clone) (0x360 bytes)
# --- Sea Lancer E1: don't let the effect be ACTIVATED with nothing to equip ---
# The donor's activation condition (cls3 +0x0C = 0x021F2460) knows nothing about the banished zone,
# and slot2 is NULL, so 0x0224AD94 said "activatable" even with an empty banished pile. The target
# template then found 0 candidates and returned 1 ("step complete") WITHOUT recording a pick, and
# the equip resolver's first phase reads pick 0 unconditionally (0x02234964 -> 0x021C4A68) -- so it
# consumed an uninitialised pick and froze. This shim chains the donor's condition and then
# additionally requires at least one legal candidate, using the same probe the template itself
# uses: param = 0x02234E78(desc), then 0x02243FE0(side, cid, param).
CAVE_SL_COND     = 0x0239BED0  # moved to ov3 cave3.CAVE3_SL_COND: sea lancer E1: activation condition -- donor cond AND >=1 candidate (0x40 bytes)
# --- Sea Lancer E3: make the ATK grant FLAT (+1000) instead of +1000 PER equipped card ---
# The donor's grant leaf 0x021B75F8 is reached from the ATK-compute function 0x021B44C0 by TWO
# kinds of pass, and both add r1 to the accumulator [sp+0xB0]:
#   * the HOLDER's own pass  -- stat block [r7+0x3C] = the holder's card-instance pointer
#                               (0x02296470 for Sea Lancer); happens ONCE per computation;
#   * an EQUIP-CONTRIBUTION pass, one PER equipped card -- [r7+0x3C] == 0, and [r7+0x24] carries
#                               the equipped card's packed word (e.g. 0x191A191A).
# Mermaid Archer can only ever equip one monster, so its native +800 never stacked; Sea Lancer
# equips any number, and 2 equips read 3300 = 1300 + 2x1000 (savestate ml4). GDB-measured: the two
# passes differ ONLY in SP-relative values and [r7+0x3C] / [sp+0xCC], with the accumulator at a
# DIFFERENT address each time (separate frames, summed upstream).
# So the leaf's 4 bytes become `bl CAVE_SL_ATK`, and the stub sets r1 = 1000 only on the holder
# pass, 0 on the equip passes; the leaf's own `b 0x021B7226` then applies r1 as before. Exact for
# every equip count -- no divide, no rounding. Only reachable while equipped, i.e. in a duel, so
# the ov5 dependency is safe (a deck-editor ATK read has no equips and never reaches the leaf).
CAVE_SL_ATK      = 0x0239BF10  # moved to ov3 cave3.CAVE3_SL_ATK: sea lancer E3: flat-vs-per-equip ATK grant gate (0x20 bytes)
# The N contributing passes are INDISTINGUISHABLE (measured: gating on [r7+0x3C]!=0 grants N
# times, gating on ==0 grants 0 times -- the ==0 pass's accumulator never reaches the stored
# ATK). So instead of telling passes apart, grant ONCE PER COMPUTATION with a flag that is
# cleared exactly where 0x021B44C0 zeroes its own accumulator [sp+0xB0] (0x021B44EC:
# `mov r4,#0 ; str r4,[sp,#0xB0]`) -- one reset per invocation, by construction.
CAVE_SL_ATKFLAG  = 0x0239BF30  # moved to ov3 cave3.CAVE3_SL_ATKFLAG: sea lancer E3: "already granted this computation" (4 bytes)
CAVE_SL_ATKRESET = 0x0239BF34  # moved to ov3 cave3.CAVE3_SL_ATKRESET: sea lancer E3: accumulator-zero hook that clears it (0x20 bytes)
# Shien's Dojo clause 2: the card's Level bound is "<= the number of Bushido Counters", but the
# criteria-registry row's bound field (row +0x0A) is STATIC data. This stub is installed as the
# donor's OWN cls3 +0C slot (the activation condition, ours alone -- no shared-function surgery),
# so it runs once per activation check, just before the deck search reads the row. It recomputes
# N = 0x021A3054(side, zone, 6), clamps to 12, writes 0x80 | (N << 2) into the row's bound byte,
# then tail-calls the native condition 0x021FD489 and returns its verdict unchanged.
# ov5 is fine here: the slot is CID-KEYED (only dereferenced for this card), not a shared path.
CAVE_DOJO_LVL    = 0x0239BF54  # moved to ov3 cave3.CAVE3_DOJO_LVL: shien's dojo: counter-derived Level bound writer (0x40 bytes)
# Shien's Dojo clause 2, the "Six Samurai OR Shien" filter. A criteria row holds ONE set code, but
# the card needs two (0x1E Six Samurai, 0x4F Shien -- there is no combined code; all 112 were
# enumerated). The engine's search calls a per-candidate CALLBACK that extracts the candidate's cid
# and tail-calls has_set_code(cid, setcode) = 0x020240D9; so ORing two codes only means replacing
# that callback. CAVE_DOJO_CB is the OR predicate; CAVE_DOJO_CRIT is a faithful clone of the
# generic criteria handler 0x0223CAB4 with its baked-in callback literal swapped for CAVE_DOJO_CB.
CAVE_DOJO_CB     = 0x0239BF94  # moved to ov3 cave3.CAVE3_DOJO_CB: shien's dojo: set-code OR predicate (0x40 bytes)
CAVE_DOJO_CRIT   = 0x0239BFD4  # moved to ov3 cave3.CAVE3_DOJO_CRIT: shien's dojo: criteria handler using that predicate (0x40 bytes)
CAVE_EW_RECORD   = 0x0239C014  # eclipse wyvern PART H: wrapper around Gold Sarcophagus's
                              #   resolver 0x0221CD29 that RECORDS which card clause 1
                              #   banished, and carries clause 2's whole phase machine
                              #   (reached when desc[+3] == 0x0F). 0x160 bytes reserved
                              #   (the add-to-hand action uses the general relocation emitter
                              #   0x021C69D0 -- 0x021C72CC is DECK-only, see the patch).
CAVE_EW_SCRATCH  = 0x0239C178  # eclipse wyvern PART H: the remembered banished card --
                              #   8 slots of {u16 acting_ref, u16 banished_ref}, keyed by
                              #   the ACTING copy's ref so simultaneous copies do not
                              #   collide, plus diagnostics at +0x20..+0x2A. The NDS builds
                              #   a NEW descriptor for the banish event, so desc[+0x16]
                              #   alone cannot carry the pick from clause 1 to clause 2
                              #   (unlike the 3DS, where clause 2 is an arm of the SAME
                              #   phase machine). 0x30 bytes.
CAVE_LP_C2COND   = 0x0239C1A8  # Lightpulsar CLAUSE 2 condition: Dark Simorgh's
                              #   0x021FEBA9 with the two ATTRIBUTE immediates changed
                              #   from DARK(2)/WIND(6) to LIGHT(1)/DARK(2). The attribute
                              #   is param's TOP NIBBLE (`movs r2,#N ; lsls r2,#0x1c`),
                              #   which is why the verbatim clone asked for a WIND monster
                              #   and the card was un-activatable in-game.
                              #   ⚠️ ov5, so CLAUSE 2 IS NORMAL-DUEL-ONLY; clauses 1 and 3 are ov3 and work in puzzles.
                              #   The ov3 dead run had only 46 B contiguous left. 0x40 bytes.
CAVE_LP_C2COST   = 0x0239C1E8  # Lightpulsar CLAUSE 2 COST -- the card's OWN selection
                              #   state machine, replacing Dark Simorgh's 0x021EC57D.
                              #   *** THE 3DS SAYS THIS CARD NEEDS ITS OWN HANDLER. ***
                              #   Native Lightpulsar (3DS cid 0x26E3) does NOT reuse the
                              #   shared banish-cost handler that Chaos Sorcerer and
                              #   Darkflare share (0x004B509C): it owns 0x004B5AE4, which
                              #   is literally `if (source is the GY) { GY path } else
                              #   { tail-call 0x004B509C }`. Borrowing Simorgh's cost on
                              #   the NDS could never work, because that cost hardcodes
                              #   `movs r2,#0` for BOTH selection passes and our donor's
                              #   cid can only ever address criteria rows 0/1.
                              #   This clone arms the selection with the PROXY cid 0x1303
                              #   (whose rows 0/1 are the hand-select LIGHT/DARK pair) and
                              #   the real pass index desc[+0x12], and its state 3 calls
                              #   0x021C6E74 (hand 0x0B -> GY 0x0E) instead of Simorgh's
                              #   0x021C6E98 (hand -> BANISHED), so the cost SENDS rather
                              #   than banishes.
                              #   ⚠️ ov5 is safe HERE, unlike the earlier hooks on Simorgh's
                              #   shared cost: this stub is reached only through our own
                              #   cls2 record's +10, so no native card can ever jump into
                              #   it (in a puzzle ov41 evicts ov5). Clause 2 stays
                              #   normal-duel-only. 0x180 bytes.
CAVE_LP_DIAG     = 0x0239C368  # Lightpulsar CLAUSE 2 INSTRUMENTATION scratch (0x40 B).
                              #   Written only when lightpulsar's
                              #   DIAG_C2_INSTRUMENT is set; the shipped build never
                              #   touches it. Read it back out of a savestate:
                              #     +0x00 magic 0x4C504431 ('1DPL') = the probe ran
                              #     +0x04 0x02243B9C(proxy 0x1303, param 0)
                              #     +0x08 0x02243B9C(proxy 0x1303, param 1)
                              #     +0x0C 0x02243B9C(donor 0x0FB1, param 0)
                              #     +0x10 0x02243B9C(donor 0x0FB1, param 1)
                              #     +0x14 desc[+0x12], the live pass index
                              #     +0x18 handler of the row +0x04 resolved to
                              #     +0x1C word    of the row +0x04 resolved to
CAVE_LP_C2COND2  = 0x0239C3A8  # Lightpulsar CLAUSE 2 CONDITION, self-contained.
                              #   Walks the HAND (player+0x124, count player+0x0C)
                              #   and asks the engine's own attribute accessor
                              #   0x0202ABC8 for each card, requiring at least one
                              #   LIGHT and one DARK before deferring to the native
                              #   condition 0x021FEBA9. The earlier 0x40-byte version
                              #   probed the criteria rows via 0x02243FA8 and always
                              #   returned 0 -- those rows do not filter by attribute
                              #   on this path, which is the same reason the COST now
                              #   checks each pick itself. 0x120 bytes: it also carries clause 3's
                              #   zone+event branch and the PART Q latch.
CAVE_LP_ROWHOOK  = 0x0239C4C8  # RETIRED -- lifted into criteria_row_hook.py
                              #   and re-homed to CAVE_ROWHOOK below, because a second
                              #   card (Darkflare) needed an arm and only 20 B of the
                              #   0x60 reserve were left (CAVE_LP_RESDISP sits at
                              #   exactly this address + 0x60). Nothing writes here now.
                              #   Was: Lightpulsar CLAUSE 2, "Simorgh-style" variant only.
                              #   A per-cid arm for the criteria-row disambiguation
                              #   0x02243B9C, hooked at 0x02243BEC, that reproduces
                              #   Dark Simorgh's own switch arm (0x02243DEA):
                              #   for our donor's GY-zone lookups it returns
                              #   r4 = 2 + (desc[+0x12] != 0), i.e. rows 2/3, and for
                              #   everything else it replays the displaced list-A
                              #   lookup and resumes. Lets clause 2's rows live on the
                              #   DONOR at rel 2/3 like Simorgh's, so the proxy cid,
                              #   the proxy cls2 record and the desc[+0] swap all go
                              #   away.
                              #   ⚠️⚠️ 0x02243B9C is the SHARED row resolver -- every
                              #   card that selects anything passes through it. An ov5
                              #   target here freezes ALL of them in a puzzle (ov41
                              #   evicts ov5). Duel-only; this variant ships to its own ROM,
                              #   rom_lightpulsar_simorgh.nds, never the main build.
                              #   ⚠️ CLAUSE 3 added a third arm: the
                              #   clause-2 and clause-3 descriptors share BOTH the
                              #   cid and the zone (0x0E), so the arm is selected by
                              #   desc[+4], the EVENT CODE -- 0x1E (sent-to-GY) gives
                              #   r4 = 4 (clause 3's revive row at rel 4), anything
                              #   else keeps r4 = 2 + (desc[+0x12] != 0).
                              #   0x60 bytes.
CAVE_LP_RESDISP  = 0x0239C528  # Lightpulsar: the cls2 record's +04 RESOLVER SLOT is
                              #   shared by clauses 2 and 3, because a second cls2
                              #   record on one cid is unreachable -- find_event_handler
                              #   only applies its +1 offset when desc[+5] == 1 (cls1),
                              #   and every relocation event is class 2
                              #   (dispatch.find_event_handler_second_record). So the
                              #   slot points here and we branch on desc[+4]:
                              #     0x1E (sent to GY) -> 0x02207191, the cls2 GY-revive
                              #                          resolver (Colossal Fighter
                              #                          0x1E12, Lord Poison 0x156D)
                              #     else             -> 0x0220731D, the self-SS-from-GY
                              #                          resolver clause 2 already used
                              #   Both are FUNCTION ENTRIES, so a register-preserving
                              #   `bx` is legal here (contrast
                              #   dispatch.midfunction_tail_needs_prologue_frame, which
                              #   forbids jumping into a mid-function arm -- that froze the game).
                              #   ov5 is safe: reached ONLY through our own record.
                              #   0x20 bytes.
CAVE_LP_TGTDISP  = 0x0239C548  # Lightpulsar: the same split for the record's +14 TARGET
                              #   DECLARATION slot.
                              #     0x1E -> 0x02235605, the off-field (list-zone) picker
                              #             that opens the Graveyard for clause 3
                              #     else -> `movs r0,#1 ; bx lr`
                              #   Returning 1 reproduces clause 2's previous +14 == 0
                              #   behaviour EXACTLY: the slot5 wrapper 0x0224AE84 falls
                              #   to `movs r0,#1 ; pop` when the slot is null (and the
                              #   slot4 wrapper 0x0224AE5E does the same for +10).
                              #   0x20 bytes.
CAVE_LP_TIMING   = 0x0239C568  # RETIRED -- lifted into timing_class_hook.py
                              #   and re-homed to CAVE_TIMINGHOOK below, because a
                              #   second card (Jet Synchron) needed an arm and the
                              #   0x40 reserve holds only one (CAVE_ROWHOOK sits at
                              #   exactly this address + 0x40). Nothing writes here
                              #   now. Was: Lightpulsar CLAUSE 3, the WHEN-vs-IF
                              #   TIMING CLASS.
                              #   The classifier 0x0224AF7C reads the cls record's +0x10
                              #   LITERAL (it never calls the slot): +0x10 == 0 -> class 0,
                              #   0x021E51E5 -> class 2, a dozen other tags -> class 1.
                              #   Ours is CAVE_LP_C2COST, because clause 2 needs a real
                              #   cost function there, so the card lands in NO class at
                              #   all. This stub displaces the classifier's own
                              #   `ldr r0,[r0,#0x10] ; cmp r0,#0` and substitutes 0 for
                              #   OUR cid on a leave event, replaying both instructions
                              #   verbatim for every other card.
                              #   ⚠️ WHAT THIS ACTUALLY DOES IS MEASURED, NOT INFERRED:
                              #   WITHOUT it the game says nothing when the card is used
                              #   as Synchro Material; WITH it the game correctly reports
                              #   "missed the timing" (in-game). So class 0
                              #   makes the engine treat the effect as a real WHEN
                              #   trigger -- an unrecognised tag leaves it unclassified
                              #   and silent. It is REQUIRED for correct behaviour, not a
                              #   generosity hack. 0x40 bytes.
CAVE_ROWHOOK_OLD = 0x0239C5A8  # RETIRED -- the shared criteria-row hook outgrew
                              #   its 0x100 reserve when Psi-Reflector added the 7th arm
                              #   (244 B -> 284 B; CAVE_DF_STAGE sits at exactly this
                              #   address + 0x100), so it was re-homed to CAVE_ROWHOOK
                              #   below. Nothing writes here now. Lift proven by execution:
                              #   scratch/rowhook_equiv.py (old stub @ this address vs new).
                              #   Was: SHARED criteria-row-offset hook, 0x100 bytes.
                              #   One stub, a REGISTER of cids, on the single 4-byte BL at
                              #   0x02243BEC inside the shared row resolver 0x02243B9C.
                              #   ⚠️⚠️ DUEL-ONLY: every card that selects anything passes
                              #   through this resolver, and ov41 evicts ov5 in a puzzle.
CAVE_DF_STAGE    = 0x0239C6A8  # Darkflare clause-2 STAGE byte, 0x4 bytes.
                              #   Which criteria row the NEXT lookup wants,
                              #   as 0/1/2 -> relative row 2/3/4. WRITABLE DATA, deliberately
                              #   OUTSIDE the row-hook blob so verify() can pin that blob
                              #   byte-for-byte. Ships as 2 (the either-GY target row), which
                              #   is what the target step needs and what ov5 reloads to at the
                              #   start of every duel. 0x4 bytes.
CAVE_DF_COST     = 0x0239C6AC  # Darkflare clause-2 two-zone COST, 0x100 bytes.
                              #   +10 of the cls3 record: sends 1 Dragon from the
                              #   HAND (delegating to the native 0x021E7245, which
                              #   owns slot4 steps 0..3) and then 1 from the DECK
                              #   (steps 4..6, the list-zone path Foolish Burial
                              #   uses). It also posts the once-per-turn latch
                              #   0x021E5060 itself, because 0x021E7245 only does
                              #   that from a per-cid switch arm our donor misses.
CAVE_DF_COND     = 0x0239C7AC  # Darkflare clause-2 activation gate, 0x80 bytes.
                              #   +0C of the cls3 record: probes rel 2 (a Dragon in
                              #   hand) and rel 3 (a Dragon in the Deck) before tail-
                              #   calling Card Ejector's native gate 0x021F05E9.
                              #   Without it the cost is half-payable: the hand Dragon
                              #   goes and the Deck half silently finds nothing.
CAVE_DF_DIAG     = 0x0239C82C  # Darkflare row-hook DIAGNOSTIC latch, 0x20 bytes.
                              #   [+0] times the hook saw our cid at all
                              #   [+4] times the cls3 arm was TAKEN
                              #   [+8] zone [+9] event [+0xA] STAGE [+0xB] r4 returned
                              #   Counters, not a poll: [+0] vs [+4] separates "the
                              #   hook never ran" from "it ran and the arm rejected".
CAVE_DS_COND     = 0x0239C84C  # Dragon Shrine CLAUSE 3 activation condition, 0x40 bytes.
                              #   +0C of cls0[329]: refuses if the turn-log already
                              #   holds (side, 0xB, cid, 1) -- Pot of Duality's exact
                              #   once-per-turn test 0x021A14E8 -- else chains Foolish
                              #   Burial's native condition 0x021F0B18.
CAVE_DS_COST     = 0x0239C88C  # Dragon Shrine CLAUSE 3 cost + clause-2 reset, 0x40 bytes.
                              #   +10 of cls0[329]: stamps the turn log via
                              #   0x021D2584(side, cid, 1, 0) and clears CAVE_DS_SCRATCH
                              #   so a fresh activation can never inherit a stale latch.
CAVE_DS_FOLLOW   = 0x0239C8CC  # Dragon Shrine CLAUSE 2 post-send follow-up, 0xC0 bytes.
                              #   Reached from the resolver's phase-0x7C gate @0x02208F42,
                              #   which is rewritten to jump here. Re-dispatches the three
                              #   native cids (0x0DBF/0x1C15/0x1DC2) back to 0x02208F56 and
                              #   handles 0x14C1: if the card just sent (GY top) is a
                              #   Normal Monster it re-enters selection for a second send.
CAVE_DS_SCRATCH  = 0x0239C98C  # Dragon Shrine CLAUSE 2 re-entry latch, 0x4 bytes.
                              #   Holds the descriptor pointer of the activation whose
                              #   second send has already been armed, so phase 0x7C runs
                              #   its body exactly once. Cleared by CAVE_DS_COST.
CAVE_MAIDEN_COND = 0x0239C990  # Maiden with Eyes of Blue CLAUSE 2 activation
                              #   condition, 0x40 bytes.  +0C of the donor's cls1
                              #   record.  Two gates: Krebons' event-code test
                              #   ((desc[+4] + 0xED) & 0xFF <= 1, i.e. code in
                              #   {0x13, 0x14} -- "targeted for an attack"), then
                              #   Pot of Duality's turn-log query
                              #   0x021A14E8(side, 0xB, cid, 1) for the card's
                              #   once-per-turn.  Returns 2 (activatable
                              #   unconditionally) or 0 (cannot activate).
CAVE_MAIDEN_RES  = 0x0239C9D0  # Maiden with Eyes of Blue CLAUSE 2 resolver, 0x80 bytes.
                              #   +04 of the donor's cls1 record.  On resolution
                              #   phase 0x80 only: stamps the turn log
                              #   (0x021D2584), then 0x0221F944 "negate the attack"
                              #   -- whose RETURN VALUE is the card's "and if you
                              #   do" gate -- and on success toggles this card's
                              #   battle position (0x021D2C1C gate, 0x021D2D18
                              #   re-sync, 0x021C5324 the position primitive, which
                              #   takes NO target position: it is a toggle).
                              #   Every phase then tail-calls the shared
                              #   "SS 1 card matching my criteria row" machine
                              #   0x02206F41, which reads the donor's criteria row
                              #   {aux 0x0FA7, handler 0x0223E2C9, flags 0x0802}.
CAVE_ATKTGT_LIST = 0x0239CA50  # moved to ov3 cave3.CAVE3_ATKTGT_LIST: SHARED "admit this cid to the attack-target event"
                              #   list, 0x10 bytes: zero-terminated u16 cids.
                              #   Read by CAVE_ATKTGT_GATE below.  Add a cid here to
                              #   give a donor the code-0x13 "targeted for an attack"
                              #   event -- see battle.attack_target_post_is_cid_gated.
                              #   Currently: {0x1ED7 Maiden}.  ⚠️ Dverg 0x245B
                              #   (ninishi PART A2) is ALSO rejected by the
                              #   native gate and would need adding here to work.
CAVE_ATKTGT_GATE = 0x0239CA60  # moved to ov3 cave3.CAVE3_ATKTGT_GATE: SHARED attack-target gate hook, 0x40 bytes.
                              #   Installed over the `bl 0x021A37D8` at 0x021C6624 --
                              #   the call inside 0x021C6620 that fetches the ATTACK
                              #   TARGET's cid for the per-cid switch guarding the
                              #   code-0x13 post at 0x021C6798.  It calls the original,
                              #   then, if the cid is in CAVE_ATKTGT_LIST, returns the
                              #   PHANTOM cid 0x1CB1 instead -- a cid the native switch
                              #   already accepts (r6 = 1) and which has no card_prop,
                              #   so no real card is impersonated.  The cid register is
                              #   dead after the switch (r2 is reloaded with
                              #   =0x02298AD8 at 0x021C6788), so the remap cannot leak.
# --- Maiden DIAGNOSTIC build only (maiden_eyes_of_blue --diag). These are a
# --- parallel, instrumented copy of the three stubs above plus a counter block; the
# --- shipped stubs are left untouched so the diagnostic cannot perturb what it measures.
CAVE_MD_DIAG     = 0x0239CAA0  # counter block, 0x40 bytes, zero in the image:
                              #   CLAUSE 2 (the attack-target trigger)
                              #   +00 gate hook entered (any cid)   +04 gate matched our cid
                              #   +08 last cid the gate saw         +0C condition entered
                              #   +10 condition returned 2          +14 (desc[+5]<<8)|desc[+4]
                              #   +18 turn-log query result + 1     +1C resolver entered
                              #   +20 last phase word seen          +24 negate return + 1
                              #   CLAUSE 1 (the targeted-by-a-card-or-effect trigger)
                              #   +28 cl.1 condition entered        +2C the r1 it was given
                              #   +30 pick-array walk MATCHED       +34 turn-log query + 1
                              #   +38 cl.1 condition returned 2     +3C cl.1 resolver entered
                              #   Counters, not a poll: +00 vs +04 separates "the hook never
                              #   ran" from "it ran and did not match", exactly as
                              #   CAVE_DF_DIAG does for Darkflare.
CAVE_MD_COND     = 0x0239CAE0  # instrumented clause-2 condition, 0x80 bytes
CAVE_MD_RES      = 0x0239CB60  # instrumented clause-2 resolver, 0xE0 bytes
CAVE_MD_GATE     = 0x0239CC40  # instrumented attack-target gate hook, 0x80 bytes
# --- Maiden with Eyes of Blue CLAUSE 1 ("when a card or effect is activated that
# --- targets this card"). A cls3 record, so it is a DIFFERENT table from clause 2's
# --- cls1 record and the two cannot shadow each other (the leftmost-record rule is
# --- per-table). Both clauses share the ONE criteria row and the ONE cid-keyed turn
# --- log, which is what makes "1 Maiden effect per turn" span them for free.
CAVE_MAIDEN_C1_COND = 0x0239CCC0  # clause-1 slot3 activation condition, 0x60 bytes.
                              #   Transcribes Blue-Eyes Shining Dragon's 0x021F8134 --
                              #   walk the ACTIVATING descriptor's declared-target array
                              #   (0x02234904(act, i) for i < act[+0x10]) and compare each
                              #   returned `side | (zone << 8)` against my own
                              #   (desc[+3] << 8) | desc[+2] -- with the clause-3 turn-log
                              #   query 0x021A14E8(side, 0xB, cid, 1) folded in front.
                              #   Returns 2 (activatable, no board target needed) or 0.
CAVE_MAIDEN_C1_RES  = 0x0239CD20  # clause-1 slot1 resolver, 0x40 bytes.
                              #   Phase 0x80 only: post the turn log 0x021D2584(side, cid,
                              #   1, 0); then EVERY phase tail-calls the shared named-SS
                              #   machine 0x02206F41, which reads the criteria row that
                              #   clause 2 already ships. No verbs of its own.
# --- clause-1 DIAGNOSTIC copies (maiden_eyes_of_blue --diag only)
CAVE_MD_C1COND   = 0x0239CD60  # instrumented clause-1 condition, 0x140 bytes
CAVE_MD_C1RES    = 0x0239CEA0  # instrumented clause-1 resolver, 0x60 bytes
CAVE_MD_DIAG2    = 0x0239CF00  # SECOND counter block, 0x40 bytes, zero in the image.
                              #   Grown after in-game test 5: the clause-1 condition is
                              #   entered but ONLY at [0x0229A9FC+0x44] == 0, even when
                              #   the OPPONENT targets with Book of Moon. So that field
                              #   is not the live-chain depth this reading assumed, and
                              #   guessing which caller reaches us has now cost two
                              #   duels. STOP GUESSING: read the caller off the STACK.
                              #   0x0224AD94 pushes {r3..r7,lr} and does not move sp, so
                              #   from the stub's own frame (5 words) [sp+0x14] is the
                              #   invoker's spilled r1 and [sp+0x28] is its RETURN
                              #   ADDRESS -- which names the call site exactly.
                              #   +00 [0x0229A9FC+0x44] at entry (LAST)
                              #   +04 entries with that field > 0
                              #   +08 &array[n-1] when > 0 (LAST)
                              #   +0C the cid there (LAST)
                              #   +10 entries with that field == 0
                              #   +14 invoker's return address, FIRST call (write-once)
                              #   +18 invoker's return address, LAST call
                              #   +1C invoker's spilled r1 (must equal our r1) (LAST)
                              #   +20 [0x0229AB7C+0x30] pending-event count (LAST)
                              #   +24 [0x0229A9FC+0x40] (LAST)
                              #   +28 desc[+5]<<24|desc[+6]<<16|desc[+4]<<8|desc[+3]
                              #   +2C [0x0229A9FC+0x50] the engine's current descriptor
CAVE_MD_DIAG3    = 0x0239CF40  # THIRD counter block, 0x20 bytes, zero in the image.
                              #   Clause 3 (the once-per-turn) instrumentation. The
                              #   turn log is ENGINE state, not ov5, so it survives the
                              #   mid-duel cave zeroing that bit the other blocks.
                              #   +00 clause-1 turn-log POSTs executed
                              #   +04 clause-1 resolver phase word (LAST)
                              #   +08 clause-2 turn-log POSTs executed
                              #   +0C clause-2 resolver phase word (LAST)
                              #   +10 clause-1 condition REFUSED by the turn log
                              #   +14 clause-2 condition REFUSED by the turn log
CAVE_MAIDEN_C1_COST = 0x0239CF60  # Maiden CLAUSE 1 slot4 (+0x10), 0x40 bytes.
                              #   THE ONCE-PER-TURN MUST BE STAMPED AT ACTIVATION, NOT AT
                              #   RESOLUTION. With the stamp in the
                              #   resolver, Maiden could be activated TWICE IN ONE CHAIN,
                              #   because both activations pass the turn-log query before
                              #   either resolves. This wrapper calls the shared costless
                              #   "you can" body 0x021E50DC and stamps the log only when it
                              #   returns 1 -- its phase-1 arm 0x021E51AE, reached when the
                              #   Yes/No answer [0x0229DD94+0x34] is non-zero, i.e. the
                              #   player ACCEPTED. Declining therefore does not burn the
                              #   once-per-turn.
                              #   SAFE ONLY BECAUSE CLAUSE 1 IS cls3: the WHEN-vs-IF
                              #   classifier 0x0224AF7C reads the +0x10 literal RAW, but it
                              #   returns 0 at once for selectors 0 and 3, so it never looks
                              #   at ours. Clause 2 is cls1 and MUST keep the literal
                              #   0x021E51E5 or it loses its timing class entirely
                              #   (timing.class_is_the_slot4_literal).
CAVE_MD_C1COST   = 0x0239CFA0  # instrumented copy of the above (--diag), 0x40 bytes
# --- Azure-Eyes Silver Dragon CLAUSE 1: "1 Tuner + 1+ non-Tuner NORMAL Monsters" ---
# Hooked over the `bl 0x0224829C` at 0x02248AAC -- the call the THIRD Synchro-material
# predicate 0x02248A88 makes into the inner predicate. Deliberately NOT the crowded
# 0x022482B6 (Quasar) / 0x022482B2 (Boggart) pair: the third predicate is the NON-TUNER
# caller, so a gate here never sees the Tuner. Proof (see the findings file): the inner
# predicate has exactly two callers, and the driver reaches 0x02248A88 only after
# 0x021A1C7C (is-Tuner) has returned 0 -- in BOTH of its branches -- except via four
# hardcoded per-Synchro shortcuts (cids 0x208E / 0x21CB / 0x239D / 0x239F / 0x211B),
# none of which is this donor. The stub tail-chains the inner predicate and returns its
# verdict unchanged for every Synchro except 0x1E9C, so Quasar and Boggart are untouched.
CAVE_AZURE_NORMALMAT = 0x0239CFE0  # azure-eyes clause 1: non-Tuner-must-be-Normal gate (<= 0x50 bytes)
# --- Azure-Eyes Silver Dragon CLAUSE 2: the on-Special-Summon Dragon protection ---
# TWO stubs, one per half of the clause.
#  * SSPROT is hooked over the `bl 0x02022E14` at 0x022658B8 -- the membership search of
#    the "plain when-this-card-is-Special-Summoned" cid list 0x0228F63A, inside the
#    `cmp r6,#9` (= Special Summon) block of the summon-trigger evaluator 0x02265768.
#    It replays the search and returns its verdict UNCHANGED (the donor is not in the
#    list, so the answer stays 0 and no cls1 event is posted -- clause 3's record is
#    never consulted), and on the way attaches one rider node to every Dragon in the
#    summoner's monster zones.  Reachability is structural: the four native "when this
#    card is Synchro Summoned" cards are found by the sibling search at 0x022658FC,
#    which is in the same straight-line block 0x44 bytes later.
#  * PROT is hooked over the `bl 0x021A1430` at 0x021B0592 -- Vehicroid Connection
#    Zone's family-1 rider link inside the "may this card effect affect this monster"
#    predicate 0x021B021C.  It replays VCZ's query and, only on a miss, asks the same
#    question about our own key.  Deliberately NOT Heart of Clear Water's link at
#    0x021B05CC: that one is claimed by safe_zone AND sits inside the `targets`
#    block, which is the origin of Safe Zone's "non-targeting destruction still
#    resolves" divergence.  0x021B0592 is before that gate.
CAVE_AZURE_SSPROT = 0x0239D030  # azure-eyes clause 2: on-SS "protect my Dragons" (<= 0x60 bytes)
CAVE_AZURE_PROT   = 0x0239D090  # azure-eyes clause 2: the protection query link (<= 0x30 bytes)
# --- Karakuri Muso mdl 818 "Haipa" (karakuri_haipa, donor Saggi 0x0FC8) ---
# Both are cid REMAPS on `bl 0x021A36EC` (cid_at) call sites: same ABI in, a
# different cid out for the donor only, so every other card routes through the
# native chains byte-for-byte.
CAVE_HAIPA_MUSTATK = 0x0239D0C0  # moved to ov3 cave3.CAVE3_HAIPA_MUSTATK: clause 1 "must attack if able": remap donor -> Nisamu
                                 # 0x2388, which BOTH must-attack chains' five-entry
                                 # jump table already accepts.  Hooked at the two
                                 # `bl 0x021A36EC` sites 0x0224D254 / 0x0224D534.
                                 # 24 B used, 0x30 reserved.
CAVE_HAIPA_BPFLIP  = 0x0239D0F0  # moved to ov3 cave3.CAVE3_HAIPA_BPFLIP: clause 3 "changed to Defense Position at the end of
                                 # the Battle Phase": latches r5 = cid for the
                                 # end-of-Battle-Phase sweep 0x02252EC0 and, for the
                                 # donor only, jumps to ARM B (0x02253078 -- the arm
                                 # that flips WITHOUT attaching the position lock).
                                 # Hooked at 0x02252F9A.  28 B used, 0x30 reserved.
# --- The Gates of Dark World clause 2 (gates_of_dark_world, donor 0x1C8B) ---
CAVE_GDW_MOVER   = 0x0239D120  # PART P: make the donor's discard an EFFECT discard.
                               # 0x021C6D90 and 0x021C6DB4 are the SAME function twice,
                               # byte-identical except that the former inserts
                               # `movs r0,#2` so [sp+4] = 2 where the latter leaves 1;
                               # 0x021C6B00 hands that word to 0x021D1300 as the
                               # relocation KIND, and kind 2 is what "if this card is
                               # discarded to the Graveyard by a card effect" listens
                               # for.  So the criteria-FILTERED cost picker
                               # (slot5 0x021E4EED, proven in-game to offer only Fiends)
                               # keeps its selection and only its mover changes.
                               # 0x021E4EED is shared by 19 records, so the swap is
                               # cid-scoped: at its `bl 0x021C6DB4` @0x021E4F66 r5 still
                               # holds the descriptor, so the trampoline reads the acting
                               # cid from [r5].  36 B used, 0x40 held.
                               # (Unused: CAVE_GDW_RES's two-phase
                               #  request-based resolver and CAVE_GDW_FILT's discard-
                               #  window callback wrapper both lived in this range.  The
                               #  wrapper FROZE the game -- hooking three pickers whose
                               #  role was not established -- and neither is needed once
                               #  the discard is a one-argument change at the mover.)
CAVE_GDW_COND    = 0x0239D170  # slot3: the once-per-turn gate PLUS a candidate-existence
                               # test.  0x021F01C1's body (no 0x0FB6 rider) AND
                               # 0x02243FE0(side, cid, 1<<28) > 0 -- a Fiend in the GY,
                               # criteria ROW 1.  Without it the card is activatable with
                               # nothing to banish and the engine FREEZES on the empty
                               # candidate list.  ⚠️ it must NOT test the hand with a bare
                               # param -- see
                               # dispatch.candidate_count_param_is_family_dependent.
                               # 52 B used, 0x50 held.
CAVE_SNOWW_RES   = 0x0239D1C0  # Snoww CLAUSE 2, cls2 +04: the resolver.  Goldd 0x0221FB50's
                               # 2-phase skeleton with clause 1 grafted in -- phase 0x7F is
                               # UNUSED by the add-to-hand resolver (its jump table sends
                               # 0x7F to a bare `movs r0,#0 ; pop`), so clause 2 hangs off
                               # the end of clause 1's chain without disturbing it.  Reads
                               # [0x0229AAFC+0x74] (the declared-target counter) exactly as
                               # Goldd does -- 0x02207EF4 never touches that word, scanned.
                               # ⚠️ the
                               # declared-pick count is desc[+0x10] (both shared
                               # recorders 0x022347B0 / 0x02234880 bump that byte),
                               # NOT [0x0229AAFC+0x74] -- that word is Goldd's own
                               # bespoke slot5 machinery and is never written on the
                               # shared-picker path, so the first build let the player
                               # select a target and then summoned nothing.
                               # 48 B used, 0x40 held.
CAVE_SNOWW_SLOT5 = 0x0239D200  # Snoww CLAUSE 2, cls2 +14: the target-declaration wrapper.
                               # Goldd's slot5 step-0 gate (desc[+0x20] bit 18 and bit 9 vs
                               # desc[+2] = "an OPPONENT's card effect did this"), returning
                               # 1 = SKIP so no prompt appears on your own discard, else a
                               # tail-call to the native off-field picker 0x02235604.
                               # STATELESS -- it must not consume a step of [0x0229AB7C].
                               # 36 B used, 0x30 held.
CAVE_SNOWW_ROW   = 0x0239D230  # Snoww CLAUSE 2: the criteria-ROW selector.  Cid-scoped
                               # trampoline on the param provider `bl 0x02234E78` @0x02235610
                               # (59 callers, so it MUST be cid-scoped): returns 1 for the
                               # donor so LIST A's `row = (param != 0)` picks ROW 1 (the
                               # opponent's-GY row) for slot5, while the add-to-hand
                               # resolver's own provider call @0x02208028 keeps returning 0
                               # = ROW 0 (the Deck row).  Deliberately avoids L2, which
                               # gates_of_dark_world has already hijacked (CAVE_GDW_L2).
                               # r3 is dead at the call site (0x02235616 overwrites it);
                               # r2 is push/popped because its liveness is not established.
                               # 28 B used, 0x20 held.
CAVE_GRAPHA_FILT = 0x0239D250  # Grapha CLAUSE 1, cls2 +08: the CANDIDATE FILTER for the
                               # "return 1 'Dark World' monster you control to the hand"
                               # cost.  The NDS's own template (Blackwing - Zephyrus the
                               # Elite 0x241C) has NO archetype test -- its +08 is a bare
                               # tail-call to the generic bitmask predicate 0x021D6E40 with
                               # mask 0x00208075 -- so this stub adds the two tests the 3DS
                               # implementation has and the NDS lacks (cid != self, then
                               # has_set_code 0x0F via the ARM9 thunk 0x020238B5) before
                               # tail-calling 0x021D6E40 with Zephyrus's own mask.
                               # (r0 = source desc, r1 = cand side, r2 = cand zone.)
                               # 68 B used, 0x50 held.
CAVE_GRAPHA_GATE = 0x0239D2A0  # Grapha CLAUSE 1, cls2 +0C: the "may this GY effect be
                               # offered" gate.  A transcription of 0x021F44D8 +
                               # 0x021F04FC with ONE deviation: 0x021F04FC sends only the
                               # hard-coded triple {0x1B20 Infernal Dragon, 0x20B9 King of
                               # the Beasts, 0x241C Zephyrus} to the cid-less free-zone
                               # check 0x021B9ECC and everything else to 0x021F0384, which
                               # first demands a FREE MONSTER ZONE.  A cost that returns a
                               # monster you control to the hand frees its own zone, which
                               # is why those three bypass it -- and why Grapha must too.
                               # A new cid cannot join the triple by data alone.
                               # 152 B used, 0xB0 held.
CAVE_GRAPHA_RES  = 0x0239D350  # Grapha CLAUSE 1, cls2 +04: the RESOLVER.  Was originally
                               # Zephyros's own 0x02230EBC, reused verbatim -- which cost one
                               # in-game test, because THAT RESOLVER HARD-CODES ZEPHYROS'S
                               # 400 LP SELF-DAMAGE: its phase 0x7F is
                               # `ldrb r1,[r5,#2] ; movs r2,#0x19 ; lsls r2,r2,#4 ;
                               #  bl 0x021CFBC8` and 0x19 << 4 == 0x190 == 400.  Zephyros's
                               # printed text really does say "Special Summon this card, and
                               # if you do, take 400 damage"; Grapha's does not.  This stub
                               # is that phase machine with phase 0x7F DELETED -- phase 0x80
                               # returns 0x7E unconditionally instead of branching to 0x7F on
                               # [0x0229AAFC+0x74], which is exactly equivalent because 0x7F
                               # does nothing but the damage and then returns 0x7E itself.
                               # 64 B used, 0x50 held.
CAVE_GRAPHA_DIAG = 0x0239D3A0  # Grapha CLAUSE 2 DIAGNOSTIC BLOCK, 0x40 bytes, zero in the
                               # image.  16 u32 slots recording what the engine actually
                               # hands each cls2 slot on each of the TWO paths that reach
                               # them (the GY-action activation of clause 1 and the
                               # discard trigger of clause 2), because no static read this
                               # session could show which argument distinguishes them:
                               #   [0]/[1]/[2]/[3]  +04 entries, last event r1,
                               #                    last [0x0229AAFC+0x70], last [+0x74]
                               #   [4]/[5]          +08 entries, last [+0x74]
                               #   [6]/[7]          +14 entries, last event r1
                               # Read it out of a savestate; it is what turns one duel into
                               # the measurement.
CAVE_GRAPHA_DECL = 0x0239D3E0  # Grapha CLAUSE 2, cls2 +14: the target declaration.
                               # Kahkki/Gren declare with 0x02234DA5 (the shared picker,
                               # param 0x119).  Clause 1 must NOT declare a target, so this
                               # stub tail-calls the picker only when the event word says
                               # this is not the GY-action path, and otherwise returns
                               # 1 = SKIP.  0x40 bytes.
CAVE_GRAPHA_RES2 = 0x0239D420  # Grapha CLAUSE 2, cls2 +04: the DISPATCHER.  Leaves
                               # CAVE_GRAPHA_RES (clause 1) byte-identical and simply
                               # chooses: event code 0x4E -> clause 1, else clause 2's
                               # destroy (Kahkki/Gren's 0x02204899).  0x60 bytes.
CAVE_GRAPHA_FILT2 = 0x0239D480 # Grapha CLAUSE 2, cls2 +08: the DISPATCHER.  ⚠️ The filter
                               # is called as (src_desc, cand_side, cand_zone) -- it does
                               # NOT receive the event -- so it cannot use the same test.
                               # It keys on [0x0229AAFC+0x74], the declared-target counter,
                               # which is nonzero only once a target has been declared:
                               # nonzero -> Goldd's "cards your opponent controls" filter
                               # 0x021DE7C9, zero -> clause 1's own CAVE_GRAPHA_FILT.
                               # THE ZERO CASE IS THE SAFE ONE: if the counter is not yet
                               # set while the picker enumerates, clause 2's target list is
                               # wrong but CLAUSE 1 IS UNHARMED, and the diagnostic block
                               # records the counter so the next build knows.  68 B used, 0x50 held.
CAVE_GRAPHA_DIAG2 = 0x0239D4D0 # Grapha CLAUSE 2, SECOND diagnostic block, 0x40 bytes.
                               # The first one could only see the resolver, and the
                               # measurement showed the resolver is never reached on
                               # the discard path -- so this one instruments slot3
                               # (+0C) and slot4 (+10), which are what refuse it.
CAVE_GRAPHA_GATE2 = 0x0239D510 # Grapha CLAUSE 2, cls2 +0C DISPATCHER, 0x60 bytes.
                               # dispatch.cls_slot_roles: +0C is the ACTIVATION
                               # CONDITION and returns a CODE, where 0 = cannot
                               # activate. Clause 1 gate returns 0 on the discard
                               # path, which is why clause 2 never even reached the
                               # resolver. Kahkki/Gren use 0x0224A115 (movs r0,#2 =
                               # activatable unconditionally); this stub returns that
                               # for the discard path and delegates to clause 1 s own
                               # CAVE_GRAPHA_GATE otherwise.
CAVE_GRAPHA_COST2 = 0x0239D570 # Grapha CLAUSE 2, cls2 +10 DISPATCHER, 0x40 bytes.
                               # +10 is the COST / activation-procedure step. Clause 1
                               # needs the bounce machine 0x021EB1B1; clause 2 is a
                               # mandatory trigger with NO cost (Kahkki/Gren have +10
                               # == 0), so bouncing a monster on a discard would be
                               # badly wrong. Returns 0 for the discard path.
CAVE_GRAPHA_LATCH = 0x0239D5B0 # Grapha: WHICH CLAUSE IS RESOLVING, 4 B (0x10 held).
                               # Written by CAVE_GRAPHA_GATE2 (cls2 +0C) and read by
                               # every other slot. +0C is the ONLY slot that can tell
                               # the two clauses apart -- it sees LR, and the trigger
                               # path calls slot3 from 0x0224AE10 so LR == 0x0224AE13
                               # there -- because the descriptor and the event word are
                               # IDENTICAL on both paths. 1 = the
                               # Graveyard summon, 2 = the discard trigger.
CAVE_C3_RES      = 0x0239D5C0  # Conscription harness SHELL, 0x60 B: the cls0 +04 entry
                               # point.  Dispatches [0x0229AAFC+0x70] 0x80 -> CAVE_C3_POST,
                               # 0x7F -> CAVE_C3_FINISH, and holds no logic of its own, so
                               # Grapha clause 3 can drive the SAME two halves from its own
                               # phase machine instead of duplicating them.
CAVE_C3_POST     = 0x0239D620  # SHARED C3 half 1, 0x60 B: (r0 = desc) -> 1 if the random
                               # pick was posted, 0 if the opponent's hand is empty.  Guards
                               # on the hand count then calls 0x022599F8(opponent, 0).
CAVE_C3_FINISH   = 0x0239D680  # SHARED C3 half 2, 0xE0 B: (r0 = desc).  Reads the chosen
                               # card back out of the opponent's hand, performs the printed
                               # "look at", and -- if it is a monster and all three summon
                               # gates pass -- Special Summons it to the caller's field via
                               # 0x02269314 (dispatch.summon_from_opponent_hand_recipe).
CAVE_C3_DIAG     = 0x0239D760  # C3 DIAGNOSTIC block, 0x40 bytes, zero in the image.
                               # ⚠️ Savestates taken before the move from 0x0239D700 read garbage here.
CAVE_GRAPHA_C3   = 0x0239D7A0  # Grapha CLAUSE 2 + CLAUSE 3 arm, 0xA0 bytes.  The
                               # cls2 +04 dispatcher CAVE_GRAPHA_RES2 tail-calls this for
                               # the discard path; it does NOT fit inside RES2's own 0x60.
                               # A two-phase machine on the SAME phase values the shared
                               # C3 halves use: phase 0x80 runs clause 2's destroy then
                               # tests dispatch.opponent_effect_discard_test and, if it
                               # passes, calls CAVE_C3_POST and returns 0x7F; phase 0x7F
                               # calls CAVE_C3_FINISH.  The payload itself is NOT
                               # duplicated -- it is the same two addresses the
                               # Conscription harness uses.
CAVE_CERULI_RES  = 0x0239D840  # Ceruli, Guru of Dark World CLAUSE 1, cls2 +04 (donor
                               # Kahkki 0x1B3E): the RESOLVER.  A port of the NDS's own
                               # self-SS-from-GY tail 0x022073F8..0x022074EE with the three
                               # deltas the 3DS's Ceruli handler 0x00443184 applies --
                               # face-up (r2=1), DEFENSE (r3=1), and bit 4 of the commit's
                               # 5th argument set, which makes 0x0226925C place the card on
                               # the OPPONENT's side (summon.commit_bit4_flips_destination_side).
                               # Gate 3 inlines 0x021BA440 with the side flipped to
                               # 1 - desc[+2], so the free-zone test reads the OPPONENT's
                               # field.  CLAUSE 2 is inlined as a follow-on to the same
                               # resolver (see ceruli), so this one slot is the
                               # whole card.  0xC0 bytes.
CAVE_HANZO_PARAM = 0x0239D900  # Ninja Grandmaster Hanzo CLAUSE 2: the criteria-ROW
                               # selector, 0x24 B of 0x40.  Reached from the retargeted
                               # `bl 0x02022E14` @0x02234E84 -- the L1 lookup INSIDE the
                               # param provider 0x02234E78 (the gates_of_dark_world PART I
                               # technique; GDW owns the L2 site 0x02234E96).  Returns
                               # param != 0 for the donor 0x13E7 iff the descriptor's event
                               # code [r5,#4] is 8 (Flip) or 9 (Special), which makes
                               # 0x02243B9C read criteria row 1 (Ninja) instead of row 0
                               # (Ninjitsu Art); every other cid tail-calls the native
                               # search byte for byte.
                               # ⚠️ THIS IS A SHARED PATH -- every deck-search card runs it.
                               # Hosting it in ov5 therefore makes a PUZZLE crash on the
                               # first search by ANY card (ov41 loads over ov5), not merely
                               # break Hanzo.  There was no ov3 dead-code run big enough
                               # (largest free = 22 B at 0x0225F2A8, stub needs 26 B).
                               # To restore puzzle safety, relocate THIS STUB ALONE into ov3.
CAVE_NAST_PRED   = 0x0239D940  # Ninjitsu Art of Super-Transformation, cls0 +08: the
                               # TWO-SIDE candidate predicate.  0x48 B of 0x50.  A clone of
                               # Bubble Shuffle's 0x021E00D8 -- one predicate serves both
                               # declared targets and branches on whether the candidate is
                               # on the acting side: my side gets zone mask 0x0C15 plus a
                               # "Ninja" set-code test (0x020237D8), the opponent's side
                               # gets mask 0x0C16 and nothing else.
CAVE_NAST_DIAG   = 0x0239D990  # Ninjitsu Art of Super-Transformation DIAGNOSTIC block,
                               # 0x20 B of 0x50.  ⚠️ DEBUG ONLY -- STRIP BEFORE SHIPPING
                               # (card.eclipse_wyvern did the same).  Counters written by
                               # the criteria handler and the resolver so a savestate can
                               # answer "was the Deck search even called, and what did it
                               # return" without a GDB session:
                               #   +0x00 times CAVE_NAST_CRIT was entered
                               #   +0x04 the Deck walker's last return value
                               #   +0x08 times the resolver's default arm called 0x0220667C
                               #   +0x0C that call's last return value
                               # (This slot previously held CAVE_NAST_CRIT, which outgrew
                               #  0x50 once instrumented and moved to 0x0239DAC0.)
CAVE_NAST_CRIT   = 0x0239DB20  # ... and its criteria-row handler.  0x5C B of 0x60.  A clone
                               # of Ninjitsu Art of Transformation's 0x0223E768 carrying the
                               # race whitelist {1, 9, 5, 0} = Dragon / Dinosaur / Sea
                               # Serpent (no such 4-word list exists anywhere in ov3) and
                               # searching ONLY container 0x0A, the Deck -- Transformation
                               # searches hand THEN Deck, this card's text says Deck.
CAVE_NAST_RES    = 0x0239D9E0  # Ninjitsu Art of Super-Transformation, cls0 +10: THE
                               # COST (slot4).  0x80 B of 0x140.  ⚠️ THE NAME IS MISLEADING:
                               # an earlier design used this slot for a cloned
                               # RESOLVER, which worked for the cost but stole resolver
                               # phase 0x80 from the Deck engine 0x02206F40, and 0x80 is
                               # where that engine runs the criteria search and the card
                               # picker (jump table @0x02206FF6).  The card then summoned
                               # a RANDOM monster with no prompt.
                               # The work moved to slot4, where Transformation puts its own
                               # Tribute, and +04 is now Transformation's UNMODIFIED
                               # 0x0221B2FD.  Old comment follows.
                               # (was) cls0 +04: THE
                               # RESOLVER.  0x12C B of 0x140 (heavily instrumented; shrinks
                               # back to ~0xD8 once the DEBUG probes are stripped).  A clone of Bubble Shuffle's
                               # 0x0221EBBC with the two changes its printed text forces:
                               # phase 0x80 keeps the declared-target VALIDATION loop but
                               # drops the battle-position change (Bubble Shuffle prints it,
                               # this card does not), and phase 0x7F sends EVERY declared
                               # target to the GY instead of hunting for the hard-coded cid
                               # 0x18F9 "Elemental Hero Bubbleman" and tributing just that
                               # one.  *** THAT HARD-CODED CID IS WHY BORROWING THE NATIVE
                               # RESOLVER FROZE THE GAME: no other card can satisfy it, the
                               # cost never pays, phase 0x7E's default arm sets the phase
                               # back to 0x80 and the machine spins 0x80 -> 0x7F -> 0x7E ->
                               # 0x80 forever. ***
CAVE_NAST_RES2   = 0x0239DB80  # Ninjitsu Art of Super-Transformation, cls0 +04: THE
                               # PURPOSE-WRITTEN RESOLVER.  0x180 B reserved.  Round 12.
                               # It SUPERSEDES CAVE_NAST_RES, which is only 0x140 and is
                               # boxed in by CAVE_NAST_CRIT at 0x0239DB20, so the stub
                               # could not grow in place.  The resolver owns every phase
                               # itself -- three rounds of delegating to a native
                               # resolver (0x0221EBBD Bubble Shuffle, 0x0221B2FD
                               # Transformation, 0x02206CAD deck-SS) each froze the game,
                               # and the user has ruled that approach out.  It
                               # reimplements the DEFAULT-ARM path of the shared deck-SS
                               # resolver 0x02206CAC (phases 0x80 count -> 0x7F prompt ->
                               # 0x7E picker -> 0x7C read-back + summon -> 0x78 teardown)
                               # with the "send both declared targets to the GY" step
                               # prepended to phase 0x80.
                               # ⚠️ CAVE_NAST_RES (0x0239D9E0, 0x140 B) is now UNUSED but
                               # deliberately STILL RESERVED to this card: freeing it
                               # while the card is mid-debug is how a slot gets double
                               # booked.  Reclaim it explicitly once the card ships.
                               # 0x200 includes the phase-1
                               # arm that attaches C4's card->monster link.
# --- White Dragon Ninja (white_dragon_ninja, donor Dunames Dark Witch 0x12B2) ---
# CLAUSE 2, "Spells/Traps you control cannot be destroyed by card effects".
# Hooked at 0x021B07F4 -- the FIRST family-1 rider link in the SPELL/TRAP + FIELD
# tail of the affect/destruction predicate 0x021B021C.  That function splits by
# slot at 0x021B059C (`cmp r5,#4 / ble / b 0x021B07EA`), so slots 0..4 (monster
# zones) take the long body and slots 5..0x0A (S/T + Field) take this tail --
# which is why Safe Zone's link 0x021B05CC and Dreadmaster's 0x021B05FA are
# UNREACHABLE for a Spell/Trap, and why this slot is the S/T analogue of
# CAVE_AZURE_PROT rather than a duplicate of it.
# The stub scans the TARGET's own monster zones for the donor cid and returns
# non-zero to make the caller take `b 0x021B0296` (PROTECTED), else replays the
# displaced `bl 0x021A1430(r6, 0x0B, r5)` verbatim.
# r6 = the TARGET's controller (proven by 0x021B0804-0x021B080A comparing it
# against `1 - actingSide`), so the side test is free -- no controller compare
# of our own.  Deliberately NOT the second link at 0x021B0814: that one sits
# behind the opponent-side gate, i.e. "your opponent's card effects only", and
# the printed text says ALL card effects.
# ⚠️ r4, r5, r6 and r7 are ALL LIVE in the caller after this call (0x021B0804 -
# 0x021B0814), so the stub saves r4 and writes only r0..r3.
# ⚠️⚠️ The first attempt called 0x021AC5A8(side, cid) -- the
# primitive the ROM's own Dreadmaster leaf at 0x021B05FE uses -- and the
# protection EXPIRED at the turn boundary in-game.  Measured from two
# savestates of the same board: 0x021AC5A8 has an EXTRA flag test that
# 0x021AC204 (201 callers) does not, `lsrs r1,r0,#0x12 ; tst ; beq skip`, i.e.
# BIT 18 of the field slot's [+0x44] must be SET -- and bit 18 is clear on 48 of
# the 73 face-up field monsters in the savestate corpus.  It cleared on the
# summoned monster between rom_wdn.ml2 (protected) and rom_wdn.ml3 (destroyed)
# while cid, slot, presence, bit 26 and the global mask all stayed identical.
# 0x021AC5A8 is therefore NOT "does this side control X face-up"; it has only 3
# callers, two of them in the battle chains.  The stub now inlines 0x021AC204's
# per-slot acceptance test (cid match + 0x021A32B4 + bit 26 clear + the
# 0x0229C314 per-slot mask clear) over slots 0..4 of ONE side instead.
CAVE_WDN_PROT    = 0x0239DD80  # White Dragon Ninja clause 2: the S/T protection
                               # query link.  0x7C B of 0x80.
CAVE_UGN_COST    = 0x0239DE00  # Upstart Golden Ninja, cls3 +10: the COST.  On cost state 0
                               # ONLY it calls the shared "you can" tag 0x021E5060, which posts
                               # the PER-COPY 0x0FB6 rider (keyed side + SLOT) that the native
                               # condition already queries -- NOT the cid-keyed turn log, which
                               # locked every copy for the turn (in-game test 2).  Then it
                               # tail-calls the native "send N from hand" cost 0x021E7245,
                               # whose donor default arm sends exactly 1
                               # (`movs r7,#1` @0x021E724C).  ⚠️ 0x021E7245 posts NO latch
                               # of its own from a donor's default arm -- measured for
                               # card.darkflare_clause2 -- which is why this wrapper exists.
                               # 0x60 B reserved.  This is the card's ONLY injected code:
                               # the condition stub and the STAGE byte both went away
                               # after in-game test 2 (the native 0x021F0BDD + the
                               # per-copy 0x0FB6 rider replaced them).
CAVE_UGN_COND    = 0x0239DE60  # Upstart Golden Ninja, cls3 +0C: the ACTIVATION CONDITION.
                               # 0x80 B reserved.  Added after in-game test 3: the stock
                               # 0x021F0BDD probes rel 0 (the DECK row) only, so the effect
                               # was OFFERED with no Trap in hand and the discard picker
                               # then opened EMPTY AND UNESCAPABLE -- a soft-lock, not a
                               # fizzle.  This stub scans the hand for a legal cost first
                               # and returns 0 if there is none, then chains 0x021F0BDD.
                               # ⚠️ The scan MUST loop: 0x02243FE0 (and 0x02243FA8) test
                               # only hand slot `param`, measured -- [filler, Trap] returns
                               # 0 at param 0 and 1 at param 1.
CAVE_UGN_PROBE   = 0x0239DEE0  # Upstart Golden Ninja: "a hand probe is in progress", 4 B.
                               # The row-hook arm ORs this with the cost-machine state so
                               # the scan reads rel 1 (the Hand/Trap row).
                               # ⚠️ THIS IS A LATCH AND THAT IS FINE HERE -- unlike the
                               # STAGE byte that in-game test 2 killed.  That one wrapped
                               # 0x021E7245, which only ARMS an asynchronous picker and
                               # returns; this one wraps 0x02243FE0, a SYNCHRONOUS count
                               # that has already returned by the time the byte is cleared.
# --- Junk Servant (Neo Aqua Madoor 0x17CE donor, records-free Normal Monster) ---
CAVE_JS_SSCOND   = 0x0239DEF0  # moved to ov3 cave3.CAVE3_JS_SSCOND: Junk Servant: hand-SS CONDITION stub for the shared
                               # trampoline (CAVE_TG_SSTRAMP).  r0 = side in, nonzero out.
                               # A direct clone of the engine's own Six Samurai gate
                               # 0x0225F7A0: canSS(side) && 0x021ACFE8(side, junk_thunk,
                               # exclude=-1, faceup_only=1) != 0, i.e. "you control a
                               # face-up 'Junk' monster".  The Junk thunk is
                               # has_set_code[0x50] = 0x02023E5D (list 0x0209C842).
                               # 0x30 B reserved.
# --- Unknown Synchron (Woodborg Inpachi 0x181C donor, records-free Normal Monster) ---
CAVE_UNKSYN_SSCOND = 0x0239DF20  # moved to ov3 cave3.CAVE3_UNKSYN_SSCOND: Unknown Synchron: hand-SS CONDITION stub for the shared
                                 # trampoline (CAVE_TG_SSTRAMP).  r0 = side in, nonzero out.
                                 # Clause 1 = the engine's own Cyber-Dragon gate
                                 # 0x0225F33A, cloned: canSS(0x021AD870) &&
                                 # monster_count(0x021ACF68, side) == 0 &&
                                 # monster_count(1 - side) != 0.  Identical logic to
                                 # T.G. Striker's stub, kept as
                                 # its own copy so a single-card build does not depend on
                                 # tg_striker having run.  Clause 2 prepends the
                                 # once-per-Duel turn-log query 0x021A14E8(side, 0x0B, cid,
                                 # kind 5).  0x50 B reserved.
CAVE_UNKSYN_STAMP  = 0x0239DF70  # RETIRED -- lifted into ss_commit_hook.py / CAVE_SSCOMMIT_HOOK (Assault Synchron needed a 2nd arm). Was: Unknown Synchron clause 2: the once-per-Duel STAMP.
                                 # Installed over `BL 0x02244D08` at BOTH SS-commit sites
                                 # 0x022692F2 (routine A) and 0x022693A0 (routine C) -- the
                                 # calls T.G. Warwolf does NOT own (it holds the adjacent
                                 # `BL 0x021A25A0` @0x022692E8 / 0x02269396).  r0 = side at
                                 # both.  Reads the global summon descriptor 0x02298A28 and,
                                 # iff [+0xE] == the donor cid AND [+0xA] == 0x0B (= summoned
                                 # FROM THE HAND, the engine's own zone vocabulary for this
                                 # field is {0x0B hand, 0x0D deck, 0x0E GY}), posts the
                                 # duel-scoped node 0x021D2584(side, cid, 5, 0), then replays
                                 # the displaced call.  0x40 B reserved.
# --- Junk Speeder (Daigusto Sphreeze 0x24B3 donor, Extra-Deck Synchro) ---
CAVE_JSP_DATA    = 0x0239DFB0  # Junk Speeder clause 2: TWO runtime words, 0x10 B reserved.
                               # +0x00 = the CRITERIA WORD the ov5 criteria handler feeds to
                               # the Deck walker.  The resolver rewrites it once per Level:
                               # ((k << 2) << 16) | 0x8002 = "Level EXACTLY k, is a Tuner,
                               # is a real card" (dispatch.criteria_word_level_field op 0 +
                               # criteria word bit 15).  This is why the ov3 criteria table
                               # is never mutated at runtime.
                               # +0x04 = the AUX (set code) cell, refreshed from the row on
                               # every call; the walker takes the aux BY REFERENCE in r3.
CAVE_JSP_CRIT    = 0x0239DFC0  # Junk Speeder clause 2: the criteria-row handler, 0x38 B of
                               # 0x40.  A clone of the stock DECK handler 0x0223CAB4 with
                               # ONE change: the word comes from CAVE_JSP_DATA+0 instead of
                               # row[+8], so the Level filter can vary per iteration.  Mode
                               # 0x0A and callback 0x0223C825 are copied verbatim from the
                               # stock handler rather than reasoned about.
CAVE_JSP_RES     = 0x0239E000  # Junk Speeder clause 2, cls1[1320] +04: THE RESOLVER,
                               # 0x11C B of 0x200.  Own phase machine (no delegation --
                               # see the NAST note: three delegating wrappers all froze).
                               # 0x80 = the three SS legality gates + a candidate probe;
                               # 0x7E = the loop over Levels 1..12, each iteration setting
                               # CAVE_JSP_DATA+0, re-running 0x02243FA8 and, on a hit,
                               # calling 0x0226925C(side, 0x02299458, face_up=1,
                               # position=1) -- face-up DEFENCE, Phantom Magician's leaf;
                               # 0x7B = no-candidate cleanup; 0x78 = teardown, returns 0x64
                               # (stop) because this card attaches no phase-1 rider.
                               # No picker is opened: "as many as possible" has no choice.
CAVE_JSP_TUNER   = 0x0239E200  # Junk Speeder CLAUSE 1: the TUNER-side material gate,
                               # 0x60 B reserved.  Installed over `bl 0x0224829C` at
                               # 0x022485D8 -- OUTER's call into the INNER material
                               # predicate.  INNER has EXACTLY TWO callers
                               # (synchro.third_pred_is_the_nontuner_caller): 0x022485D8
                               # inside OUTER, which the driver reaches only for the
                               # TUNER, and 0x02248AAC inside THIRD, the non-Tuner
                               # caller that azure_eyes owns.  So a gate here is
                               # TUNER-ONLY BY CONSTRUCTION -- the exact mirror of Azure
                               # Eyes' argument, needing no GDB and no LR sniffing.
                               # Deliberately NOT 0x022482B2/0x022482B6: Boggart and
                               # Quasar own those and already chain into 0x022482BC.
                               # Behaviour: replay INNER; if it rejected, or the Synchro
                               # is not the donor, return its verdict UNCHANGED; else AND
                               # it with has_set_code[0x4C] (the "Synchron" thunk
                               # 0x02023E1C) applied to the material's cid, which OUTER
                               # itself resolves with 0x021A3320(arg1, arg2).
CAVE_JSP_USED    = 0x0239E280  # Junk Speeder CLAUSE 2 (pooled-picker revision):
                               # 16 BYTES, one per Level 0..15.  0 = that Level is
                               # still available this resolution, 1 = already summoned.
                               # A byte array rather than a bitmask because Thumb-1's
                               # register-operand shift is not in thumb_asm, while
                               # `ldrb rt,[rn,rm]` is.  0x20 B reserved.
                               # CLEARED at phase 0x80 AND at teardown 0x78 -- the
                               # activation gate runs the same criteria handler BEFORE
                               # 0x80, so leftovers would under-count and silently stop
                               # the effect being offered (the stale-criteria-word trap).
CAVE_JSP_CB      = 0x0239E2A0  # Junk Speeder CLAUSE 2: the Deck-walker CALLBACK clone,
                               # 0x40 B reserved.  A clone of 0x0223C824 with a veto
                               # added.  MEASURED (thumbemu, twice): the stock callback
                               # runs exactly once per ACCEPTED candidate, and its return
                               # value is a hard veto -- forcing 0 takes the candidate
                               # count 10 -> 0, forcing 1 leaves it at 10.
                               # ⚠️ It has NO stack frame: the original reads its args
                               # from [sp] and [sp+4], so the clone must load them BEFORE
                               # it pushes anything.
                               # ⚠️ Its tail target 0x020240D8 takes (cid, SELECTOR<0x70)
                               # and dispatches through a pointer table -- that second
                               # argument is NOT the criteria word.
CAVE_JSP_COND    = 0x0239E2F0  # Junk Speeder CLAUSE 5, cls1 +0C: the HARD ONCE-PER-TURN
                               # gate, 0x50 B reserved.  Replaces the shared optional-
                               # trigger condition 0x021F0419 with:
                               #   if 0x021D2B88(desc)            -> chain the native cond
                               #      (a RESOLVING effect must not re-deny itself)
                               #   if 0x021A14E8(desc[+2], 0x0B, desc[+0], 1) -> return 0
                               #   else                            -> chain the native cond
                               # This is Pot of Duality's own shape
                               # (dispatch.turnlog_once_per_turn_pair), and the same shim
                               # shooting_quasar PART K already ships in-game.
                               # kind 1 is the END-OF-TURN-SWEPT kind (kinds 1/2 go to the
                               # countdown-and-remove arm of 0x0219F9E0), which is what
                               # makes it per-TURN and not per-Duel like kind 5.
CAVE_TIMINGHOOK_OLD = 0x0239E340  # RETIRED (0x100 bytes) -- FULL at 248 B / 10 arms; re-homed to
                              #   CAVE_TIMINGHOOK (0x200) for Grandsoil's arm. Never reuse. History below.
                              ## SHARED timing-class hook, 0x100 bytes.
                              #   One stub, a REGISTER of cids, on the single 4-byte
                              #   site 0x0224AF96 inside the WHEN-vs-IF classifier
                              #   0x0224AF7C, which reads the cls record's +0x10
                              #   LITERAL and never calls it: +0x10 == 0 -> class 0,
                              #   0x021E51E5 -> class 2, a dozen other tags -> class 1,
                              #   anything else -> NO CLASS AT ALL and the trigger is
                              #   silently dropped. A card whose +0x10 must hold a real
                              #   cost function (because two clauses share one cls2
                              #   record) therefore needs an arm here or its OTHER
                              #   clause loses its timing class.
                              #   One stub (a REGISTER of cids) so a second card can gain an arm without re-pointing
                              #   the hook -- the criteria_row_hook precedent exactly.
                              #   ⚠️⚠️ DUEL-ONLY: the classifier runs for every
                              #   triggered effect, and ov41 evicts ov5 in a puzzle.
# --- Jet Synchron CLAUSE 2 -------------------------------------
# One cls2 record (555, cid 0x224C) carries BOTH clauses, split by
# `desc[+3] == 0x0E && desc[+4] > 6` -- clause 1 (the Synchro-Material trigger)
# above, clause 2 (the GY ignition) below.  dispatch.gy_action_offer_caps_the_
# event_code proves a GY-action descriptor can never carry a code above 6, so the
# split cannot misroute.  ⚠️⚠️ DUEL-ONLY: the criteria_row_hook arm this card needs
# sits on every selecting card's path.
CAVE_JS_RESDISP  = 0x0239E440  # +04 RESOLVER dispatcher, 0x40 bytes.
                              #   clause 1 -> 0x02207EF5 (add-to-hand)
                              #   clause 2 -> 0x0220731D (the GY self-SS resolver,
                              #   68 cls2 records share it; the donor takes its
                              #   position switch's DEFAULT arm, r4=2 / r6=1 =
                              #   "player chooses, face-up").
CAVE_JS_COND     = 0x0239E480  # +0C CONDITION dispatcher, 0x80 bytes.
                              #   BOTH clauses first query the cid-keyed turn log
                              #   0x021A14E8(side, 0x0B, cid, 1) -- that is CLAUSE 3,
                              #   "you can only use 1 'Jet Synchron' effect per turn",
                              #   and one cid-keyed stamp locks both clauses.
                              #   clause 1 -> 0x021F0821 (a Deck candidate exists)
                              #   clause 2 -> hand count [player+0x0C] != 0, then
                              #   Plaguespreader's own gate 0x021FF06D.
CAVE_JS_SLOT4    = 0x0239E500  # +10 ACTIVATION-PROCEDURE dispatcher, 0x40 bytes.
                              #   clause 1 -> the costless "You can" BODY 0x021E50DC
                              #   (NOT the thunk 0x021E51E5), and posts the turn-log
                              #   stamp 0x021D2584(side, cid, 1, 0) only when it
                              #   returns 1, so DECLINING does not burn the once-per-
                              #   turn (dispatch.once_per_turn_must_stamp_at_activation).
                              #   clause 2 -> CAVE_JS_COST below.
                              #   ⚠️ This slot is ALSO the timing-class literal, read
                              #   RAW by 0x0224AF7C -- which is why this card needs an
                              #   arm on the SHARED timing_class_hook.  Without it
                              #   clause 1 lands in NO timing class and its trigger
                              #   evaporates silently.
CAVE_JS_COST     = 0x0239E540  # clause 2's HAND-SEND COST machine, 0x140 bytes.
                              #   A re-implementation of Plaguespreader Zombie's
                              #   0x021E9038 (dispatch.hand_cost_machine_0x021E9038)
                              #   with ONE semantic change: the mover is 0x021C6DB4
                              #   (hand -> GY, kind 1 = COST) instead of 0x021C6988
                              #   (hand -> DECK, which is Plaguespreader's printed
                              #   "place 1 card on top of the Deck").  The per-cid
                              #   switch collapses because the donor takes the DEFAULT
                              #   arm; we use PLAGUESPREADER's values (r4 = 0, so the
                              #   phase-2 0x021D26CC broadcast is skipped) rather than
                              #   the default's, to match the exemplar that is known
                              #   to work.  The Graverobber 0x1379 sub-clause is
                              #   reproduced verbatim -- it is a hard-coded per-card
                              #   clause riding inside the shared machine
                              #   (grep-the-template-cards-text-too), and omitting it
                              #   would change what happens when Graverobber is the
                              #   card discarded.
CAVE_JS_RIDER    = 0x0239E680  # RETIRED -- lifted into
                              #   summon_rider_hook.py and re-homed to
                              #   CAVE_RIDERHOOK below, because a second card (Jet
                              #   Warrior) needed an arm and this 0x60 reserve holds
                              #   only one: CAVE_JS_ARM sits at exactly this address
                              #   + 0x60, so it could not grow in place. Nothing
                              #   writes here now. The CAVE_LP_TIMING ->
                              #   CAVE_TIMINGHOOK precedent exactly.
                              #   Was: "but banish it when it leaves the field".
                              #   Hooks 0x02268666 -- the DEFAULT leaf of the
                              #   summon-event per-cid switch (root 0x022680A8, cid
                              #   from the global event record [0x02298A28+0x12]) --
                              #   and attaches the family-1 marker node ourselves:
                              #   0x021C479C(side, slot, 0x1E15, 3, 0), exactly what
                              #   arm 0x02268542 does for Plaguespreader and Quillbolt.
                              #   rider.banish_marker_is_cid_blind_to_the_destination
                              #   proves the node alone is sufficient: the predicate
                              #   0x021B0950 tests the key with no cid in scope and its
                              #   caller 0x021CCBDA rewrites destination 0x0E -> 0x0F.
                              #   ⚠️ It REPLAYS the two displaced instructions
                              #   (`ldrh r0,[r4,#0xe]` + `ldr r6,=0x14FC`) and returns
                              #   to 0x0226866A, whose `cmp r0,r6` consumes them; r6
                              #   must NOT be in the POP list or the pop would undo it.
CAVE_JS_ARM      = 0x0239E6E0  # the rider's ONE-SHOT arm byte, 0x4 bytes.
                              #   Opcode 0x14 is a general "a card arrived on the
                              #   field" event, so an ungated hook would banish a Jet
                              #   Synchron that was Normal Summoned or Special
                              #   Summoned by something else.  Clause 2's resolver
                              #   dispatcher SETS this byte; the rider stub CONSUMES
                              #   it (attach, then clear).  It is cleared by the STUB,
                              #   never by the resolver, because the summon commit
                              #   0x0226925C can finish after the resolver returns --
                              #   the timing window that killed
                              #   card.upstart_golden_ninja's first STAGE latch.
CAVE_FOLLOWHOOK  = 0x0239E700  # SHARED deck-send phase-0x7C dispatcher, 0x80 bytes.
                              #   Owned by deck_send_follow_hook.py, NOT by a card.
                              #   The gate @0x02208F42 jumps here; this re-dispatches
                              #   the three native cids (0x0DBF/0x1C15/0x1DC2) back to
                              #   0x02208F56, each registered arm to its own body, and
                              #   everything else to 0x02209046 ("nothing to do").
                              #   ⚠️ Adding an arm moves every other arm's offsets --
                              #   run scratch/followhook_equiv.py after any change.
CAVE_AS_FOLLOW   = 0x0239E780  # Accel Synchron CLAUSE 2 post-send follow-up, 0x100 B.
                              #   Registered arm of CAVE_FOLLOWHOOK for cid 0x11A3.
                              #   TWO PASSES over phase 0x7C (legal because the deck-send
                              #   resolver's RETURN VALUE IS THE NEXT PHASE -- proven at
                              #   0x02218042, `strh r0,[r4,#0x18]`):
                              #     pass 1  read the sent monster's Level off the GY top,
                              #             raise the two-option prompt 0x0219ABB4, latch,
                              #             return 0x7C to re-enter this same phase;
                              #     pass 2  read the choice from [0x0229DD94+0x34], negate
                              #             the amount for option 2, write the Level rider
                              #             0x021C479C(side, zone, 0x11A3, kind 3, delta),
                              #             clear the latch, return 0x64.
CAVE_AS_LATCH    = 0x0239E880  # Accel Synchron CLAUSE 2 pass latch + amount, 0x8 bytes.
                              #   [+0] the descriptor whose prompt is already raised (so
                              #        phase 0x7C runs pass 1 exactly once), [+4] the sent
                              #        monster's Level, carried from pass 1 to pass 2.
CAVE_AS_RES      = 0x0239E890  # Accel Synchron cls3 slot-1 SPLITTER, 0x40 bytes.
                              #   The donor owns ONE cls3 record and two clauses want
                              #   it: clause 1 (deck-send, your Main Phase) and
                              #   clause 3 (Synchro Summon, your OPPONENT's Main
                              #   Phase).  A second cls3 record is impossible --
                              #   find_event_handler does a leftmost-equal walk-back
                              #   and returns exactly one (dispatch.cls_table_selector;
                              #   the Warwolf bug).  So all three contended slots are
                              #   split here on WHOSE TURN IT IS, which is the printed
                              #   text: [0x0229DD14+0x34] != desc[+2] -> clause 3.
                              #   Tail-jumps to 0x02249EC0 (clause 3) or 0x02208DD4.
CAVE_AS_COND     = 0x0239E8D0  # Accel Synchron cls3 slot-3 SPLITTER, 0x40 bytes.
                              #   Same test: opponent's turn -> Formula's 0x021F1490
                              #   (which IS the printed timing, incl. clause 3's own
                              #   once-per-turn turn-log scan), else clause 1's
                              #   ignition condition 0x021F0B70.
CAVE_AS_COST     = 0x0239E910  # Accel Synchron cls3 slot-4 SPLITTER, 0x40 bytes.
                              #   ⚠️ WITHOUT THIS, ACTIVATING CLAUSE 3 WOULD CONSUME
                              #   CLAUSE 1's ONCE-PER-TURN: slot 4 is 0x021E5061, which
                              #   stamps key 0x0FB6 on (side, zone) -- the very key
                              #   clause 1's condition queries.  Formula's own record
                              #   has slot 4 = 0.  So: our turn -> stamp as before;
                              #   opponent's turn -> return 1 and stamp nothing.
# --- Jet Warrior, clauses 2 + 3 -------------------------------
# Clause 1 lives in cls1[1279] and clause 2 in a new cls2 row, so unlike Jet
# Synchron the two clauses need NO resolver/condition dispatcher -- each record
# carries its own stub.  Both records are cls1/cls2, whose +0x10 IS read raw by
# the WHEN-vs-IF classifier, so BOTH slot-4 stubs additionally require the cid
# 0x23EB to be registered on the shared timing-class hook.
CAVE_JW_C1_COND  = 0x0239E950  # cls1 +0C, 0x30 B.  Clause 3 for clause 1: the
                              #   turn-log query (key 0x23EB, kind 1).  Returns 0
                              #   ("cannot activate") if already used this turn,
                              #   else 2 ("activatable unconditionally"), which is
                              #   what the stock 0x0224A115 returned.
CAVE_JW_C1_SLOT4 = 0x0239E980  # cls1 +10, 0x40 B.  Wraps the costless "you can"
                              #   BODY 0x021E50DC and posts the kind-1 turn-log
                              #   node ONLY when it returns 1 = "the player said
                              #   yes".  dispatch.once_per_turn_must_stamp_at_
                              #   activation: stamping in the RESOLVER instead
                              #   loses to the chain (the card activates twice in
                              #   one chain), measured in-game on Maiden.
CAVE_JW_C2_COND  = 0x0239E9C0  # cls2 +0C, 0x60 B.  Turn-log query (kind 2), then
                              #   Plaguespreader's own GY-revive gate 0x021FF06D,
                              #   then -- and this is what it grew for -- ITS OWN
                              #   CANDIDATE COUNT.  Returning slot3's code 1
                              #   ("activatable iff slot2 finds a target") is NOT
                              #   honoured on the GY-action offer path, so the
                              #   effect was offered on an empty board and, by the
                              #   engine's zero-candidate convention, summoned FOR
                              #   FREE.  It now calls 0x0224AB38(desc, 0x0224A8C1)
                              #   -- the SAME sweeper the Tribute machine uses, so
                              #   the gate and the cost can never disagree -- and
                              #   denies on a count of 0.
CAVE_JW_C2_SLOT4 = 0x0239EA20  # cls2 +10, 0x40 B.  Chains the shared Tribute
                              #   machine 0x021E7C89 and posts the kind-2 node
                              #   only on a return of 1 = "the Tribute was paid"
                              #   (its phase 1 returns 0 and rewinds the phase on
                              #   a cancel), so declining does not burn the latch.
CAVE_JW_TRIBFILT = 0x0239EA60  # cls2 +08, 0x40 B.  "1 Level 2 or lower monster":
                              #   the zone predicate 0x021D6E40 with the engine's
                              #   own TRIBUTE mask 0x00020013 (4/4 of that mask's
                              #   owners print "Tribute"), then the LIVE Level
                              #   getter 0x021B807C(side, zone, 0) <= 2.  There is
                              #   no Level field in the mask, so the test must be
                              #   written -- no stock slot2 pointer means this.
CAVE_JW_C2_POS   = 0x0239EAA0  # 0x20 B.  Forces DEFENSE POSITION.  Displaces the
                              #   4 bytes `ldrb r0,[r5,#2] ; adds r3,r4,#0` at
                              #   0x022074E6, which load two of the four arguments
                              #   of the SS commit 0x0226925C(side, locator,
                              #   face_up, POSITION).  Writes only r0 and r3 -- the
                              #   same two registers the displaced pair writes --
                              #   so for every cid but ours it is the identical
                              #   pair in the opposite order, which is
                              #   unobservable.  68 cls2 records share this
                              #   resolver; that is why the equivalence is closed
                              #   by construction rather than by a harness.
# --- O15, the banish rider (SHARED module) ----------
CAVE_RIDERHOOK   = 0x0239EAC0  # SHARED summon-rider hook, 0x80 bytes.  Owns the
                              #   single 4-byte site 0x02268666 -- the DEFAULT leaf
                              #   of the summon-event per-cid switch (root
                              #   0x022680A8, cid from the global event record
                              #   [0x02298A28+0x12]) -- and attaches the family-1
                              #   marker node 0x021C479C(side, slot, 0x1E15, 3, 0),
                              #   exactly what arm 0x02268542 does for Plaguespreader
                              #   and Quillbolt.  Re-homed here from CAVE_JS_RIDER so
                              #   a second card could gain an arm without re-pointing
                              #   the hook -- the timing_class_hook precedent.
                              #   Each arm consumes its OWN one-shot byte, because
                              #   opcode 0x14 fires on every summon; the byte is
                              #   cleared HERE, never by the setter (the commit
                              #   0x0226925C can finish after the resolver returns).
                              #   ⚠️ It REPLAYS the two displaced instructions
                              #   (`ldrh r0,[r4,#0xe]` + `ldr r6,=0x14FC`) and returns
                              #   to 0x0226866A, whose `cmp r0,r6` consumes them; r6
                              #   must NOT be in the POP list or the pop would undo it.
                              #   ⚠️⚠️ DUEL-ONLY: it runs for every summon in the
                              #   game, and ov41 evicts ov5 in a puzzle.
CAVE_JW_ARM      = 0x0239EB40  # Jet Warrior's rider ONE-SHOT arm byte, 0x4 bytes.
                              #   Set by CAVE_JW_C2_POS -- cid-scoped AND inside the
                              #   GY self-SS resolver 0x0220731D -- so ONLY clause 2's
                              #   revive arms it and a Synchro Summon of Jet Warrior
                              #   never does.  Tighter than Jet Synchron's, which arms
                              #   from its resolver.  Consumed and cleared by
                              #   CAVE_RIDERHOOK.  SHIPS CLEAR.
CAVE_OD_TRIG     = 0x0239EB50  # moved to ov3 cave3.CAVE3_OD_TRIG: Orient Dragon's "Synchro Summoned" TRIGGER
                              #   trampoline, 0x20 bytes.  Hooks the `bl` at
                              #   0x022658FC -- the ONLY reader of the 36-entry
                              #   Synchro/Fusion/Ritual summon-trigger list
                              #   0x0228F6C0 (exactly one reference exists in the
                              #   whole ROM, the pool word at 0x02265A30), so this
                              #   one site is total coverage.  Returns 1 for the
                              #   donor 0x0FCB and otherwise delegates to the
                              #   native binary search 0x02022E14 -- via `blx` on
                              #   an ODD literal, and preserving r3 exactly as the
                              #   native `PUSH {R3,R4,R5,LR}` does.
                              #   ⚠️⚠️ DUEL-ONLY: it runs for every summon in the
                              #   game, and ov41 evicts ov5 in a puzzle.
CAVE_DS_ARMTRAMP = 0x0239EB70  # moved to ov3 cave3.CAVE3_DS_ARMTRAMP: XX-Saber Darksoul's ANY-LEAVE arming trampoline, 0x30 bytes.
                              #   Hooks TREE 2's root 0x021C9F1C (native `LDR R0,[PC,#0x9C]
                              #   ; CMP R4,R0`, 4827 4284) in the single leave-dispatch
                              #   function 0x021C7FD0, and for r4 == the donor cid BX's into
                              #   the any-leave gate 0x021CA640; otherwise it replays
                              #   r0 = 0x1A64 and `CMP R4,R0` -- IN THAT ORDER, because
                              #   0x021C9F20 is a `BLE` that consumes those flags -- and
                              #   BX LR back to 0x021C9F20.
                              #   ⚠️ WHY NOT the shared T.G. trampoline at 0x021C8216
                              #   (CAVE_TG_ARMTRAMP): that stub gates on [sp+0x90] DESTROYED,
                              #   which its own comment says is REQUIRED for the T.G. cards
                              #   ("without it Tribute Summon fodder and Synchro Material also
                              #   armed the search").  Darksoul is printed "sent from your side
                              #   of the field to your Graveyard ... by ANY means", so that
                              #   filter is exactly wrong for it :
                              #   battle destruction armed, Synchro Material did not.  A
                              #   SEPARATE hook keeps the four shipped cards on that trampoline
                              #   byte-untouched.  This is also the position the old Deep Diver
                              #   build armed from (a tree-2 leaf), which the user confirms
                              #   worked on Synchro Material.
CAVE_PIPER_COND  = 0x0239EBA0  # moved to ov3 cave3.CAVE3_PIPER_COND: Mystic Piper, cls3 +0C: the ONCE-PER-TURN condition.
                              #   0x30 B (38 used).  Queries the turn log
                              #   0x021A14E8(desc[+2], 0x0B, desc[+0], 1) and returns 0 if the
                              #   node is already posted, else chains the donor's native
                              #   generic condition 0x021F06E8 (which is CID-BLIND: side/slot
                              #   zone-state only, pool words 0xB3C and 0x0229ACD8).
                              #   ⚠️ THE desc[+7] GUARD IS NOT DECORATION.  slot3 is
                              #   re-evaluated mid-activation AFTER the cost has run
                              #   (dispatch.slot3_recheck_and_cost_flag), and the cost is what
                              #   posts the node -- so an unguarded query would return 0 on the
                              #   re-check and the effect would activate from the menu and then
                              #   FIZZLE SILENTLY.  desc[+7] == 0 is the menu call, 1 is the
                              #   re-check.  (Piper has +14 == 0 = NO target template, and the
                              #   KB says only the MULTI-select template 0x02235700 re-checks,
                              #   so this is belt-and-braces -- but a silent fizzle costs a duel.)
CAVE_PIPER_COST  = 0x0239EBD0  # moved to ov3 cave3.CAVE3_PIPER_COST: Mystic Piper, cls3 +10: the COST.  0x20 B (24 used).
                              #   POSTs the once-per-turn node
                              #   0x021D2584(desc[+2], desc[+0], 1, 0) and then tail-chains the
                              #   donor's native Tribute slot 0x021E50CC (7 instructions:
                              #   send-self 0x021CF658(side, slot), return 1).  The latch is
                              #   stamped HERE and not in the resolver --
                              #   dispatch.once_per_turn_must_stamp_at_activation.
CAVE_NS_ARM      = 0x0239EBF0  # moved to ov3 cave3.CAVE3_NS_ARM: ninishi SITE 1, 0x70 B.  The extra-Normal-Summon
                              #   granter arm of 0x021B95C4, run for BOTH Dverg 0x245B /
                              #   is_nordic AND the donor 0x0FFD / is_karakuri:
                              #   archetype-predicate -> on-field 0x021ABE4C -> spent-rider
                              #   0x021A1430(side, 0xB, cid) -> return the granter cid.
                              #   Entered by the `bl` that replaced 0x021B9634 and exits
                              #   through the HOST's epilogue (pop {r3-r7,pc}), so it must
                              #   push nothing.
CAVE_NS_SPENT    = 0x0239EC60  # moved to ov3 cave3.CAVE3_NS_SPENT: ninishi SITE 2, 0x20 B.  Tail of the "is the extra
                              #   Normal Summon spent" chain 0x021B9EFC: keeps the Dverg
                              #   answer, else asks the same rider question for the donor,
                              #   then runs the host's own `movs r4,#0` / return tail.
CAVE_NS_PRED     = 0x0239EC80  # moved to ov3 cave3.CAVE3_NS_PRED: ninishi SITE 3, 0x30 B.  Replaces the action state
                              #   machine's `bl is_nordic` @0x02261E3E: answers
                              #   "Nordic OR Karakuri" and writes the matching granter cid
                              #   into the arm's literal-pool word 0x02261F84 (its only
                              #   three readers are downstream of this call).
CAVE_NS_MATCH    = 0x0239ECB0  # moved to ov3 cave3.CAVE3_NS_MATCH: ninishi SITE 4, 0x20 B.  Replaces
                              #   `ldr r1,=0x245B ; cmp r0,r1` @0x0226515C: returns with Z
                              #   set for EITHER granter and leaves the MATCHED cid in r1
                              #   (the host's next `bl 0x021ABE4C` consumes r1).
CAVE_NS_FIELD    = 0x0239ECD0  # moved to ov3 cave3.CAVE3_NS_FIELD: ninishi, ALL SITES, 0x90 B.  "Where is the granter
                              #   on the field?", replacing every `bl 0x021ABE4C` in the
                              #   granter machinery.  Native 0x021ABE4C also demands a
                              #   kind<6 node keyed by the card's own cid on its own slot --
                              #   Dverg's printed "AFTER YOU NORMAL SUMMON THIS CARD ... this
                              #   turn" window.  MEASURED over 8 duel savestates
                              #   (scratch/ninishi_onfield_probe.py): it returns -1 for EVERY
                              #   ordinary face-up monster, which is why the first build never
                              #   offered Ninishi's summon.  This stub runs the same loop
                              #   WITHOUT the node query for the donor cid, and TAIL-CALLS the
                              #   native function for every other cid, so Dverg keeps its window.
CAVE_NIN_POSCOND = 0x0239ED60  # moved to ov3 cave3.CAVE3_NIN_POSCOND: ninishi clause 2, cls1 +0C, 0x10 B.  `movs r0,#1 ; bx lr`.
                              #   NOT invented: it is the DISJUNCTION of the engine's own two
                              #   position gates.  0x021F4D4D returns 1 iff the card is in ATTACK
                              #   position (Black Stego / the five STBL Karakuri) and 0x021F4D99
                              #   returns 1 iff it is in DEFENSE (Reptilianne Naga 0x21B4's record,
                              #   cls1[1130]) -- so a card whose printed clause is the SYMMETRICAL
                              #   "change its battle position" is activatable in either, i.e.
                              #   always.  (0x0224A115, `movs r0,#2 ; bx lr`, would also serve, but
                              #   2 is what the native gate returns for exactly two cids and its
                              #   meaning is unpinned; 1 is what all 20 users of this resolver get.)
CAVE_NIN_POSRES  = 0x0239ED70  # moved to ov3 cave3.CAVE3_NIN_POSRES: ninishi clause 2, cls1 +04, 0x40 B.  The shared resolver
                              #   0x0220C6B1 with the DIRECTION removed: it picks a target
                              #   position in r4 (1 = Defense, or 0 for Naga alone) and calls the
                              #   flip primitive 0x021C5324 only when r4 differs from the current
                              #   position -- which is how one shared resolver serves both
                              #   directions, since the primitive takes NO target argument and is
                              #   therefore a TOGGLE (proven by the pairing: Naga reaches it from
                              #   the DEFENSE gate with identical constants and ends in Attack).
                              #   A symmetrical card needs no direction at all, so this clone drops
                              #   the r4 compare and always toggles.  Same gates
                              #   (0x021D2C1C / 0x021D2D18), same primitive, same return 0.
CAVE_CARDCAR_RES  = 0x0239EDB0  # cardcar_d clause 2, cls3 +04, 0x50 B.  DRAW(side, 2), then
                              #   Neko Mane King's End-Phase body (0x02217352..0x02217396) minus
                              #   its [0x0229C294+0x78]&1 branch -- the same cut the 3DS makes
                              #   (Cardcar 0x404DB0 calls 0x426AC4, Neko's body without it).
CAVE_CARDCAR_COND = 0x0239EE00  # cardcar_d clauses 2+3, cls3 +0C, 0x70 B.  MP1 + your turn +
                              #   not Special Summoned this turn (turn flags bit 18, as Pot of
                              #   Duality's cond 0x02203258) + zone-word bit 16 ("Normal Summoned
                              #   this turn"), then the generic gate 0x021F06E8; desc[+7] guard.
CAVE_CARDCAR_COST = 0x0239EE70  # cardcar_d clause 3, cls3 +10, 0x20 B.  Post Pot of Duality's
                              #   SS-lock node 0x021D2584(side, 0x2321, 1, 0) -- denied natively by
                              #   the can-SS mega-gate @0x021B993C -- then the native Tribute.
CAVE_SC_SELECT   = 0x0239EE90  # soul_charge clause 1, cls0 +14, 0x20 B.  The multi-select
                              #   template 0x02235700's own prologue (push / r5 = desc / [sp] = r1),
                              #   then r4 = 0x47 (Barcha's "any number"; 0x29 capped at 3 in-game),
                              #   r6 = 0x11D (Infernity Launcher's GY-summon prompt) and a BL into
                              #   the native tail 0x02235912.
                              #   LR is already pushed, so the BL is a plain jump -- no 0x360 B clone.
CAVE_SC_RES      = 0x0239EEB0  # soul_charge clauses 1+2, cls0 +04, 0x50 B.  In phase 0x78
                              #   counts picks that 0x021A241C finds on the field, pays 1000 x n via
                              #   Premature Burial's LP primitive 0x021CF924(side, amount), then runs
                              #   the native GY multi-summon resolver 0x0221B4E0 unchanged.
CAVE_SC_COND     = 0x0239EF00  # soul_charge clauses 3+4, cls0 +0C, 0x40 B.  Unless desc[+7]
                              #   (the template's mid-activation re-check, Pot of Benevolence's guard):
                              #   phase == MP1 (Soul Exchange / Makiu) and 0x021F6DD8 (no own node this
                              #   turn); then the native 0x021F03B4.
CAVE_SC_COST     = 0x0239EF40  # soul_charge clauses 3+4, cls0 +10, 0x30 B.  Unless 0x021D2B88:
                              #   node(side, 0x123D, 1, 0) = 1/turn (tag 0x021E8E74 shape) and
                              #   node(side, 0x0EBD, 1, desc[+0xC]) = no Battle Phase (borrowed from the
                              #   BP gate 0x0224CD84's list; 0x0EBD is a non-collectible BP-lock card).
CAVE_KURIBANDIT_COND = 0x0239EF70  # kuribandit C1, cls1 +0C, 0x50 B.  desc[+7] guard, Deck >= 5,
                              #   zone-word bit 16 (Genex Neutron 0x021FEDDC without its candidate-count tail).
CAVE_KURIBANDIT_RES  = 0x0239EFC0  # kuribandit C3, cls1 +04, 0xE0 B.  Wrapper over Pot of Duality's
                              #   resolver 0x0222FD90: build 5, Yes/No, picker, mill 5 / mill 4.
CAVE_ASSD_TRIG   = 0x0239F0A0  # RETIRED -- lifted into summon_trigger_hook.py /
                              #   CAVE_SUMMONTRIG when Junk Speeder's re-donor needed a SECOND
                              #   arm on the same 4-byte site and the 0x20 B slot could not hold
                              #   two cid compares plus their literal pool.  Was:
                              #   accel_synchro_stardust_dragon C1, BL'd from the
                              #   membership verdict `cmp r0,#0 ; beq` @0x02265900 (AFTER Orient
                              #   Dragon's own hook at 0x022658FC, which stays untouched): member,
                              #   or cid [r4+0xE] == 0x126F -> return to 0x02265904 (proper-summon
                              #   test); else r0 = 0 and return to 0x02265910.
CAVE_ASSD_C1_COND = 0x0239F0C0  # accel_synchro_stardust_dragon C1 OPT, cls1 +0C, 0x30 B.
                              #   Turn-log query (side, 0xB, 0x126F, kind 1) -> 0, else the native
                              #   GY-candidate condition 0x021F03B4.  Jet Warrior C1's shape.
CAVE_ASSD_C1_SLOT4 = 0x0239F0F0  # accel_synchro_stardust_dragon C1 OPT, cls1 +10, 0x30 B.
                              #   "You can" body 0x021E50DC; on a yes post (side, 0x126F, 1, 0).
                              #   Verbatim jet_warrior._stub_c1_slot4 with the cid swapped.
CAVE_ASSD_C2_RES = 0x0239F120  # accel_synchro_stardust_dragon C2, cls3 +04, 0x40 B.  Phase
                              #   0x7E: Cyber-Stein 0x0220AF0C's summon body replayed with
                              #   [sp] = (cid<<16)|1 ("treated as a Synchro Summon"); every other
                              #   phase tail-jumps to 0x0220AF0D unchanged.
CAVE_ASSD_C2_COND = 0x0239F160  # accel_synchro_stardust_dragon C2, cls3 +0C, 0x50 B.  Main
                              #   Phase 1/2 (Apophis 0x021F4EC0's test, either turn); desc[+7]-guarded
                              #   turn-log query (side, 0xB, 0x126F, kind 2); then Kaibaman 0x021F90E0.
CAVE_ASSD_C2_COST = 0x0239F1B0  # accel_synchro_stardust_dragon C2, cls3 +10, 0x30 B.  Post
                              #   (side, 0x126F, 2, 0), then the native Tribute tag 0x021E50CC.
CAVE_ASSD_STAGE  = 0x0239F1E0  # accel_synchro_stardust_dragon C3, 4 B DATA (ships 0).  1 while
                              #   the shared Synchro resolver 0x02249EC0 runs as C2's follow-up; read
                              #   by the criteria_row_hook arm (row 1 + STAGE).
CAVE_ASSD_C3_DISP = 0x0239F1F0  # accel_synchro_stardust_dragon C3, cls3 +04, 0x50 B.  STAGE set
                              #   -> blx 0x02249EC1, zero the forced-material global 0x0229AC7C
                              #   (else the Tributed source is required), clear STAGE when it
                              #   returns 0; else phase 0x7D ->
                              #   STAGE = 1, return 0x80 (the resolver's own native 0x7D->0x80 re-entry);
                              #   else tail to the in-game-confirmed CAVE_ASSD_C2_RES unchanged.
CAVE_TG_SSTABLE_OLD2 = 0x0239F240  # RETIRED -- the 7-row hand-SS dispatch table (0x40 bytes) was FULL
                              #   (CAVE_SSCOMMIT_HOOK sits at exactly +0x40). Moved to CAVE_TG_SSTABLE for
                              #   Grandsoil (8th registrant); tg_table.register_tg_handss migrates its rows.
CAVE_SSCOMMIT_HOOK = 0x0239F280  # moved to ov3 cave3.CAVE3_SSCOMMIT_HOOK: SHARED SS-commit stamp, ss_commit_hook.py (0x50 bytes). Over `BL 0x02244D08`
                              #   @0x022692F2 / 0x022693A0. For a
                              #   summon FROM THE HAND (desc 0x02298A28 +0xA == 0x0B) of a cid in
                              #   CAVE_SSCOMMIT_TABLE: post turn-log (side, cid, kind, 0), then optional damage
                              #   0x021CFB8C(side, amount, 0, cid); then replay the displaced BL.
CAVE_SSCOMMIT_TABLE = 0x0239F2D0  # moved to ov3 cave3.CAVE3_SSCOMMIT_TABLE: SHARED SS-commit arm table {cid u16, kind u16, damage u32}, zero-terminated (0x40 bytes)
CAVE_ASSAULT_SSCOND = 0x0239F310  # assault_synchron C1: hand-SS condition (0x50 bytes). turn-log
                              #   (side, 0xB, 0x13AE, 1) clear && turn player == side && phase in {2,4} && canSS(side).
CAVE_ASSAULT_LEAVEHOOK = 0x0239F360  # assault_synchron C2: over `ldr r0,[sp,#0x44]; cmp r0,#0`
                              #   @0x021C93D0 (bystander-chain head, 0x80 bytes). Face-up Dragon Synchro you
                              #   control left the field Tributed ([sp+0xC]&0x1000) or banished (dest 0xF) ->
                              #   turn-log node 0x021D2584(r6, 0x4000|ref, 1, 0), then
                              #   0x021D3648(r6, 0x13AE, [sp+0x1C], [sp+0x200] & ~0x1FF); replay (CMP last).
CAVE_ASSAULT_C2COND = 0x0239F3E0  # assault_synchron C2: cls2 slot3 (0x40 bytes). code 0x1D / zone 0xE,
                              #   turn-log (side, 0xB, 0x13AE, 2) clear, still in GY -> 2. (Runs at ADMISSION.)
CAVE_ASSAULT_C2COST = 0x0239F420  # assault_synchron C2: cls2 slot4 (0x30 bytes). "You can" body
                              #   0x021E50DC (slot3 re-check + Yes/No); on 1: post turn-log kind 2, then
                              #   Mezuki's GY-banish cost 0x021E5708.
CAVE_ASSAULT_C2CRIT = 0x0239F450  # assault_synchron C2: criteria handler (0x40 bytes). GY builder
                              #   0x0223C4E8 (flags 8) + banished builder 0x0223C6AC (flags 0xC), predicate below.
CAVE_ASSAULT_C2PRED = 0x0239F490  # assault_synchron C2: target predicate (0x80 bytes). Dragon && Synchro
                              #   && turn-log node (card side, 0x0B, 0x4000|ref, kind 1) exists.
                              #   (A runtime ov5 ref list at 0x0239F510 was dropped before shipping: ov5 runtime
                              #   state is wiped mid-duel, KB mem.ov5_runtime_state_wiped_mid_duel.)
CAVE_PSI_GROUP   = 0x0239F510  # psi_reflector C1: 12 x u16 sorted cid list (0x18 bytes, DATA) = the
                              #   "lists Assault Mode Activate" group. Set code 0x6E's thunk literal @0x02024090
                              #   is repointed here and its count immediate set to 12.
CAVE_PSI_COND    = 0x0239F528  # psi_reflector C1: cls1 +0C (0x30 bytes). turn-log (desc[+2], 0xB, 0x1008, 1)
                              #   clear -> Gearframe's slot3 0x021F0821, else 0.
CAVE_PSI_SLOT4   = 0x0239F558  # psi_reflector C1: cls1 +10 (0x30 bytes). "You can" 0x021E51E5; on 1 post
                              #   turn-log (desc[+2], 0x1008, 1, 0).
CAVE_PSI_C2COND  = 0x0239F588  # psi_reflector C2: cls3 +0C (0x70 bytes). turn-log kind 2 clear, AMA 0x1F7A
                              #   in hand (direct scan), then Rite of Spirit's GY-candidate cond 0x021F03B5.
CAVE_PSI_C2COST  = 0x0239F5F8  # psi_reflector C2: cls3 +10 (0x30 bytes). Koa'ki reveal cost 0x021EAAA1; on 1
                              #   post turn-log (desc[+2], 0x1008, 2, 0).
CAVE_PSI_C2RES   = 0x0239F628  # psi_reflector C2: cls3 +04 (0xD0 bytes). Call of the Haunted phases: 0x80 SS,
                              #   0x7F number picker 1..4, 0x7E Level rider 0x22EB kind 3 on the summoned monster, 0x64 pop.
CAVE_ROWHOOK     = 0x0239F6F8  # SHARED criteria-row-offset hook, 0x180 bytes (criteria_row_hook.RESERVE).
                              #   One stub, a REGISTER of cids, on the single 4-byte BL at 0x02243BEC.
                              #   ⚠️⚠️ DUEL-ONLY: every card that selects anything passes through this
                              #   resolver, and ov41 evicts ov5 in a puzzle.
CAVE_KMW_COND    = 0x0239F878  # moved to ov3 cave3.CAVE3_KMW_COND (Phase C pilot). Was
                              #   koaki_meiru_wall C2: cls3 +0C (0x60 bytes). Not written by any build now.
CAVE_HEIRLOOM_POST   = 0x0239F8D8  # moved to ov3 cave3.CAVE3_HEIRLOOM_POST: amazoness_heirloom C3 (0x18 bytes). BL'd from 0x022517C6 (after-dmg-calc
                              #   attacker-equip walk): flags = cid==Thorn of Malice 0x2007 || cid==donor 0x2124.
CAVE_HEIRLOOM_FILTER = 0x0239F8F0  # moved to ov3 cave3.CAVE3_HEIRLOOM_FILTER: amazoness_heirloom C3 (0x30 bytes). cls1 +08: Ancient Gear Fist 0x021E1478's
                              #   prologue, then its "monster it battled, not the equipped one" arm 0x021E1576.
CAVE_PINE_COND   = 0x0239F920  # moved to ov3 cave3.CAVE3_PINE_COND: naturia_pineapple C2: cls2 +0C (0x60 bytes). Treeborn's S/T + face-up-self
                              #   checks, then GY monsters == GY Plant + GY Beast, tail 0x021F04FD.
CAVE_PINE_RES    = 0x0239F980  # moved to ov3 cave3.CAVE3_PINE_RES: naturia_pineapple C2: cls2 +04 (0x30 bytes). S/T recheck (Treeborn 0x022073C8),
                              #   then the shared GY self-SS resolver 0x0220731D.
CAVE_PINE_RACE   = 0x0239F9B0  # moved to ov3 cave3.CAVE3_PINE_RACE: naturia_pineapple C1 (0x60 bytes). BL'd from 0x021B8ACC (race resolver
                              #   0x021B88F0 board scan): donor face-up in your monster zone -> race Plant.
CAVE_REVSYN_VALID    = 0x0239FA10  # revolution_synchron C1 (0x100 bytes). BL'd from 0x02249B12 (Synchro
                              #   material validator's `bl 0x022494EC` hand-mode test): kind 0xB && count 0 &&
                              #   summoner's hand card is 0x1649 && turn-log kind 1 clear && target Power Tool
                              #   0x1FC9 or Lv7/8 Dragon (minus 5 deny cids) && INNER(syn, side, 0xB, idx) ->
                              #   return into the validator's accept tail 0x02249DA0; else tail-call 0x022494EC.
CAVE_REVSYN_HANDPASS = 0x0239FB10  # revolution_synchron C1 (0x60 bytes). BL'd over `ldr r0,[sp,#4]; cmp r0,#0`
                              #   @0x02249626 (can_synchro field loop exit): no field hit -> validator(side, 0xB, i)
                              #   over the summoner's hand; replay the pair (CMP last).
CAVE_REVSYN_STAMP    = 0x0239FB70  # revolution_synchron C1 (0x60 bytes). BL'd from 0x022639AA (Synchro procedure
                              #   hand-material send `bl 0x021C6E74`): hand card 0x1649 -> turn-log (side, 0x1649, 1, 0);
                              #   tail-call 0x021C6E74.
CAVE_REVSYN_VROW     = 0x0239FBD0  # revolution_synchron C2 (0x10 bytes). DATA: the virtual GY-action registry
                              #   row 60 {0x1649, 0x0E, 0x0224C591, 0x0224C6C1} (Glow-Up Bulb's row, cid changed).
CAVE_REVSYN_GYFETCH  = 0x0239FBE0  # revolution_synchron C2 (0x20 bytes). BL'd over `ldr r1,=0x0228DDF8 ;
                              #   lsls r0,r6,#4` @0x0224C88E (GY-action enumerator row fetch): r6 == 60 -> r0 = VROW-base.
CAVE_REVSYN_GYEXIT   = 0x0239FC00  # revolution_synchron C2 (0x30 bytes). BL'd over the enumerator's loop exit
                              #   @0x0224C9A0: r6 == 60 -> run the virtual pass (0x0224C88E); else r6 = 60 + replay.
CAVE_REVSYN_GYPOST   = 0x0239FC30  # revolution_synchron C2 (0x30 bytes). BL'd over `pop {r3-r7,pc} ; nop`
                              #   @0x0224CD34 (post-by-cid 0x0224CD08 exit): r4 >= 60 && cid 0x1649 -> post 0x0224C6C1.
CAVE_REVSYN_GYHAS    = 0x0239FC60  # revolution_synchron C2 (0x20 bytes). BL'd over `movs r0,#0 ; pop {r3-r5,pc}`
                              #   @0x0224CD60 (has-row 0x0224CD3C not-found exit): return cid == 0x1649.
CAVE_REVSYN_C2COND   = 0x0239FC80  # revolution_synchron C2 (0x80 bytes). Ignition-registry f1: you control a
                              #   face-up Lv7+ (live) Synchro in zones 0..4 -> Glow-Up Bulb's f1 0x021F7B75.
CAVE_REVSYN_C2COST   = 0x0239FD00  # revolution_synchron C2 (0x30 bytes). cls2 +10: settled -> 1; else turn-log
                              #   (side, 0x1649, 5, 0) then the Deck-top cost 0x021EBA35 (N = 1).
CAVE_REVSYN_C2RES    = 0x0239FD30  # revolution_synchron C2 (0x70 bytes). cls2 +04: Psi-Reflector phases -- 0x80
                              #   chain push + GY self-SS 0x0220731D; 0x7F LOCATE -> Level rider {0x1EC1, 3, 1}; 0x64 pop.
CAVE_ELDER_SSCOND = 0x0239FDA0  # moved to ov3 cave3.CAVE3_ELDER_SSCOND: elder_six_samurai (re-donored to Flame Cerebrus): hand-SS condition
                              #   stub (0x30 bytes). canSS(side) && monster_count(side)==0 &&
                              #   monster_count(1-side)!=0 -- registered with tg_table.register_tg_handss.
CAVE_AI_L_OPPTURN = 0x0239FDD0  # ai_tables.py: relocated CPU-AI list "opponent's-turn usable"
                              #   (native 0x0227113C x0x13). 0x200 reserve = 256 u16 slots; the
                              #   read site 0x022395BA's count immediate caps it at 255.
CAVE_AI_L_SUMMON  = 0x0239FFD0  # ai_tables.py: relocated CPU-AI list "summon response"
                              #   (native 0x022711B8 x0x30, read 0x0223961E). 0x200 reserve.
CAVE_AI_L_DESTROY = 0x023A01D0  # ai_tables.py: relocated CPU-AI list "destruction response"
                              #   (native 0x02271162 x0x15, read 0x02239738). 0x200 reserve.
CAVE_AI_L_CHAIN   = 0x023A03D0  # ai_tables.py: relocated CPU-AI list "chain related"
                              #   (native 0x0227118C x0x16, read 0x0223989E). 0x200 reserve.
CAVE_AI_L_DEDUP   = 0x023A05D0  # ai_tables.py: relocated move-validator dedup list
                              #   (native 0x0226EF2E x0x1D, read 0x021D308E). 0x200 reserve.
CAVE_AI_RULETABLE = 0x023A07D0  # ai_tables.py: relocated REACTIVE RULE TABLE (native 0x02275510
                              #   x0xB5 of {u32 fn, u32 arg}). 0x800 reserve = 256 rows, capped at
                              #   255 by the two `cmp rN,#0xB5` sites 0x02248196 / 0x0224821C.
                              #   ⚠️ FUNCTION POINTERS IN A NORMAL-DUEL-ONLY CAVE: in a puzzle ov41
                              #   evicts ov5 and the rule scan's `blx r1` would branch into garbage,
                              #   so ai_tables relocates this one only on an explicit opt-in.
CAVE_CB_LOCK     = 0x023A0FD0  # crimson_blader Stage A (0x30 bytes). cls1 +04 resolver for
                              #   Crimson Sunbird 0x1179: posts the summon-lock node on the OPPONENT,
                              #   0x021D2585(1 - desc[+2], desc[+0], kind, 0) -> zone 0x0B.  Kind byte
                              #   = 1 | countdown << 4, countdown 1 when the trigger fires on the
                              #   controller's own turn and 2 when it fires on the opponent's, so
                              #   the node dies at the end of the OPPONENT'S NEXT turn either way
                              #   (rider.turn_sweeper).  Non Aggression Area 0x15AD's handler
                              #   0x02216A38 hardcodes 0x11 because it can only ever be activated on
                              #   its controller's Standby Phase; Crimson Blader cannot.
CAVE_CB_GATE     = 0x023A1000  # crimson_blader Stage B (0x80 bytes).  The SHARED summon
                              #   restriction predicate, cloned from Konami's own
                              #   0x021BA1E8(r0 = side, r1 = Level) -> 1 allow / 0 deny and
                              #   widened to (r0 = side, r1 = Level, r2 = cid, r3 = flag).
                              #   It answers BOTH locks: Worm Bait 0x2146 (Level 3-4, with its
                              #   cid exemption r2 == 0x1FDB && r3 != 0) and Crimson Blader
                              #   0x1179 (Level >= 5).  Four overlay-3 arms call it --
                              #   0x021AF176 Normal, 0x021BA1E8 Special, 0x0225D87A and
                              #   0x0225E0DA the two AI planners -- because those are the only
                              #   four sites in ov3 that read a zone-0x0B lock node and then
                              #   test a Level.  Keeping Worm Bait's rule here is NOT optional:
                              #   these arms ARE Worm Bait's implementation.
CAVE_DR_COND     = 0x023A1080  # dragunity_remus C4 (0x40 bytes): act-cond shim for the
                              #   hand discard/search -- denies when the (slot 0xB, key 0x106E,
                              #   kind 1) turn-log node is already posted, then chains the native
                              #   cond 0x021F0820.  Gated on IS_RESOLVE_CTX 0x021D2B88 so the
                              #   resolve/replay pass does not deny its own activation.
                              #   Pot of Duality's HOPT test, minus PoD's bit18 "already Special
                              #   Summoned" clause, which is Thunder Sea Horse-specific.
CAVE_DR_RES      = 0x023A10C0  # dragunity_remus C4 (0x40 bytes): resolver shim -- posts
                              #   the (0xB, 0x106E, kind 1) turn-log node via 0x021D2584, then
                              #   chains the native discard-self cost 0x021E6FD8.  NO native res
                              #   does both: every non-null callback slot in all four cls tables
                              #   was scanned and none calls both the poster and the
                              #   discard.  ⚠️ These two slots make C4 NORMAL-DUEL ONLY (the cls2
                              #   record now points into the cave); C2's data path is unaffected.
CAVE_DR_C1       = 0x023A1100  # dragunity_remus C1 (0x60 bytes): the TUNER-side material
                              #   gate -- "Remus cannot be used as Synchro Material, except for
                              #   the Synchro Summon of a 'Dragunity' monster".  Same ABI as
                              #   junk_speeder's gate (r0 = the SYNCHRO's cid, r1/r2/r3 =
                              #   INNER's other args): replay INNER 0x0224829C, return its verdict
                              #   unchanged unless the material is 0x106E, and then AND in
                              #   has_set_code[0x4A] on the SYNCHRO's cid.
                              #   ⚠️ 0x022485D8 is the ONLY Tuner-side gate (synchro.tuner_gate_hook)
                              #   and junk_speeder was there first, so the two CHAIN:
                              #   site -> CAVE_JSP_TUNER -> CAVE_DR_C1 -> INNER, built by whichever
                              #   patch applies second (junk_speeder.chain_tuner_gate /
                              #   apply_tuner_gate's site adoption).  Order-independent.
CAVE_DR_C3_COND  = 0x023A1160  # dragunity_remus C3a (0x80 bytes): cls2 +0C SPLITTER.
                              #   desc[+3] == 0x0E is the GY-ACTION path (the descriptor builder
                              #   0x0224C590 hardcodes it -- dispatch.gy_action_offer_caps_the_event_code),
                              #   so the record serves BOTH clauses off one cls2 row, which it
                              #   must: find_event_handler returns the LEFTMOST same-cid record,
                              #   so a second row for 0x106E would shadow C2.  GY path = "you
                              #   control a Dragunity" (zone walk, face-up, has_set_code 0x4A)
                              #   AND the kind-2 turn log; hand path = the confirmed C4 cond.
CAVE_DR_C3_MAIN  = 0x023A11E0  # dragunity_remus C3a (0x30 bytes): cls2 +04 splitter --
                              #   GY path -> the self-SS resolver, hand path -> 0x02207EF5.
CAVE_DR_C3_RES   = 0x023A1210  # dragunity_remus C3a (0x40 bytes): cls2 +10 splitter --
                              #   GY path posts the kind-2 turn-log node (a SEPARATE latch from
                              #   C4's kind 1, because the printed text is "each effect once per
                              #   turn"); hand path -> the confirmed C4 res.
CAVE_DR_C3_SS    = 0x023A1250  # dragunity_remus C3a (0x50 bytes): the GY self-Summon
                              #   resolver -- phase 0x80 CHAIN_PUSH + GY_SELF_SS 0x0220731C ->
                              #   0x7F -> 0x64.  Zephyrus's own resolver 0x02230EBC is NOT
                              #   reusable (it hardcodes his printed 400 LP self-damage --
                              #   dispatch.resolver_hardcodes_printed_damage).
CAVE_DR_ARM      = 0x023A12A0  # dragunity_remus C3b: the rider's ONE-SHOT arm byte, 4 B.
                              #   Set by the C3a GY self-Summon resolver at phase 0x80 and
                              #   CLEARED BY THE CONSUMER (summon_rider_hook), never by the
                              #   setter -- the commit 0x0226925C can finish after the setting
                              #   resolver returns, the window that killed upstart_golden_ninja's
                              #   first STAGE latch.  Without the gate, event opcode 0x14 ("a card
                              #   arrived on the field", five posters) would rider a Normal
                              #   Summoned Remus too.
# NEVER SHIPPED: wattuna's CAVE_WU_ED (0x023A12B0,
# 0x30 B) held a clone of Blackwing Aurora's criteria handler with the mode byte
# changed from `movs r0,#4` to `movs r0,#0x24`.  That extra 0x20 bit adds
# can_synchro 0x02249540, which walks only the 10 FIELD slots, so for a card whose
# Synchro materials may come from the HAND it answered "cannot summon" and emptied
# the Extra-Deck offer -- in-game failure 1, root-caused offline by
# scratch/wattuna_u4_probe.py.  The module now POINTS AT Aurora's stock handler
# 0x022430A1 instead and injects no code at all, so the slot is FREE AGAIN and
# CAVE_FREE is back where it was.  No ROM was ever shipped holding this stub.
CAVE_SR_DECKFIND = 0x023A12B0  # scrap_raptor C2 (0x24 bytes). A criteria-row HANDLER:
                              #   builds the Deck candidate list for "add 1 non-Tuner 'Scrap'
                              #   monster from your Deck to your hand".
                              #   It is Gusto Egul's handler 0x02243338 RELOCATED byte for byte,
                              #   with exactly ONE halfword changed: +0x10 `movs r0,#0xa` ->
                              #   `movs r0,#2`, i.e. the [sp+4] mode loses bit 8.  The 4-byte
                              #   literal pool at +0x20 keeps Gusto Egul's CALLBACK POINTER
                              #   0x02243305 (ov3, resident in every duel mode), which is
                              #   `has_set_code(cid, row->aux) && !is_tuner(cid)` -- the only
                              #   non-Tuner predicate in the ROM.  The two-halfword BL at +0x1A
                              #   is re-encoded for this address; everything else is copied.
                              #   ⚠️ The mode is taken from SCRAPYARD (whose ACTION matches: a
                              #   Deck->hand search, mode 2) and the callback from GUSTO EGUL
                              #   (whose PREDICATE matches).  Do not take both from one card:
                              #   mode bit 8 makes the shared builder 0x0223BC3C run the
                              #   Special-Summon legality check `bl 0x021B9ED8` on every
                              #   candidate, which is right for Gusto Egul (it SS's from the
                              #   Deck) and wrong here.  This is the retired CAVE_WU_ED failure
                              #   below, in reverse -- that stub ADDED a mode bit and emptied
                              #   its offer in-game.
                              #   ⚠️ thumb.cloned_pool_pointer: +0x20 is a FUNCTION POINTER
                              #   (odd = Thumb).  Copy it as a pointer; never inline its target.
CAVE_SR_C1COND   = 0x023A12D4  # scrap_raptor C1a, cls3 +0C: the ONCE-PER-TURN condition.
                              #   0x30 B.  Queries the turn log
                              #   0x021A14E8(desc[+2], 0x0B, desc[+0], 1) and returns 0 if the
                              #   node is already posted, else chains the card's NATIVE generic
                              #   ignition condition 0x021F01C0.
                              #   ⚠️ WHY THE TURN LOG AND NOT THE NATIVE PAIR ALONE.  The stock
                              #   pair (+0C 0x021F01C1 / +10 0x021E5061) IS a complete
                              #   once-per-turn latch on its own -- but it is the PER-COPY
                              #   rider, node kind 0x0FB6, keyed (side, slot).  Two reasons that
                              #   is the wrong mechanism here: the printed text is per-NAME
                              #   ("each effect of 'Scrap Raptor' once per turn"), and C1a can
                              #   legally target and destroy ITSELF, which destroys a slot-keyed
                              #   node that Stage 4's grant window still has to read.  The
                              #   cid-keyed turn log survives both.  The native pair is still
                              #   CHAINED, so the per-copy latch also holds -- per-name is
                              #   strictly stricter, so the turn log is what binds.
                              #   ⚠️ THE desc[+7] GUARD IS NOT DECORATION: slot3 is re-evaluated
                              #   AFTER the cost runs, and the cost is what posts the node, so an
                              #   unguarded query makes the effect activate and then FIZZLE
                              #   SILENTLY.  desc[+7] == 0 is the menu call, 1 is the re-check.
                              #   This card has +14 == 0x02234DA5 (a real target template), so
                              #   the re-check is live -- this is NOT belt-and-braces here the
                              #   way it was for Mystic Piper.
CAVE_SR_C1COST   = 0x023A1304  # scrap_raptor C1a, cls3 +10: the COST.  0x20 B.
                              #   POSTs the turn-log node 0x021D2584(desc[+2], desc[+0], 1, 0)
                              #   and then tail-chains the card's native cost slot 0x021E5060
                              #   (which posts the per-copy 0x0FB6 rider and returns 1).
                              #   Stamped HERE, not in the resolver --
                              #   dispatch.once_per_turn_must_stamp_at_activation: a resolver
                              #   stamp lets a cancelled or negated activation escape the limit.
CAVE_SUMMONTRIG  = 0x023A1324  # summon_trigger_hook.py: the SHARED proper-Summon trigger hook,
                              #   0x60 B.  BL'd over the 4-byte membership verdict
                              #   `cmp r0,#0 ; beq 0x02265910` @0x02265900, which follows the
                              #   binary search of the proper-SS list 0x0228F6C0
                              #   (summon.trigger_is_a_membership_list).  The list is 36 REAL
                              #   cids with no phantom and its neighbours are packed flush at
                              #   both ends, so a donor can only join it from here.
                              #   A member, or a cid [r4+0xE] in ARMS -> return to lr
                              #   (0x02265904, the proper-summon test); otherwise r0 = 0 and
                              #   return to lr + 0xC (0x02265910).
                              #   Orient Dragon's own hook one instruction earlier
                              #   (0x022658FC) is NOT touched, so the two compose either way.
                              #   Replaces CAVE_ASSD_TRIG, which held the same stub with one arm.
CAVE_SR_C2COND   = 0x023A1384  # scrap_raptor C2, cls2 +0C: "was I destroyed by the
                              #   effect of a *SCRAP* card?"  0x30 B.
                              #   KONAMI'S OWN TEST, lifted from the per-cid leave arm that the
                              #   stock Scrap trigger family uses at 0x021C92E6:
                              #       ldr r0,=0x0229A9FC ; ldr r0,[r0,#0x50]  ; acting descriptor
                              #       bl  0x021D2D78                          ; -> DESTROYER's cid
                              #       bl  0x02023EE4                          ; has_set_code(Scrap)
                              #   then chains the native availability gate 0x021F05A8, which
                              #   counts the criteria row's candidates.
                              #   ⚠️ WHY IT EXISTS: the leave-MASK table can ARM the trigger, but
                              #   its 12 bits (leave.mask_bit_semantics) cannot express the
                              #   DESTROYER'S ARCHETYPE -- the destroyer is not among the mask's
                              #   inputs.  So the mask row carries only 0x0C00 (0x0400 destroyed |
                              #   0x0800 to-GY), exactly the arm's two non-archetype tests, and
                              #   THIS STUB supplies the third.  Together they reproduce the
                              #   printed text EXACTLY -- no deviation.
                              #   ⚠️ 0x0229A9FC+0x50 is the ACTING descriptor: during a destroy
                              #   resolution that is the DESTROYING effect's, not ours.  Measured
                              #   in the stock savestate rom.ml3, where a WORKING Scrap Beast
                              #   trigger reads {cid 0x22F8, zone 0x0E, event 0x1D, class 2}.
# --- scrap_raptor C1b: the extra Normal Summon of 1 "Scrap" monster ----
#  SEVEN stubs, and FIVE of them CHAIN INTO ninishi's CAVE_NS_* stubs
#  rather than replacing them
#  and not one of its bytes is rewritten.  ⚠️ THAT MAKES ninishi A HARD
#  DEPENDENCY, APPLIED FIRST: five of these hooks assert a `bl CAVE_NS_*`
#  before-image, so a missing or mis-ordered ninishi aborts the build instead of
#  freezing a duel.  See notes/scrap-raptor-findings.md, "FINAL HOOK TABLE".
#  The grant itself needs NO code here: C1a's shipped cost stub already posts
#  0x021D2584(side, 0x0FF6, kind 1, 0), and that node IS the grant (the two
#  conditions -- "C1a activated this turn" and "the extra summon is available" --
#  are the same thing).  Kind 1 = granted, kind 2 = spent, on ONE key, read back
#  with the KIND-EXACT query 0x021A14E8 (see rider.family1_has_a_kind_exact_lens).
#  ⚠️ NEVER query these with the kind-AGNOSTIC 0x021A1430: it would see C1a's own
#  kind-1 latch and report the grant spent the instant C1a is activated.
CAVE_SR_NSARM    = 0x023A13B4  # moved to ov3 cave3.CAVE3_SR_NSARM: SITE 1 @0x021B9634: "which granter permits this hand
                               #   card?"  Scrap + grant(kind 1) + !spent(kind 2)
                               #   -> return 0x0FF6; else tail-jump CAVE_NS_ARM.
                               #   Exits through the HOST's POP {R3-R7,PC}.  0x40 B.
CAVE_SR_NSSPENT  = 0x023A13F4  # moved to ov3 cave3.CAVE3_SR_NSSPENT: SITE 2 @0x021B9F9C: "is the extra summon spent?"
                               #   Raptor's kind-2 query, else chain CAVE_NS_SPENT.  0x30 B.
CAVE_SR_NSPRED   = 0x023A1424  # moved to ov3 cave3.CAVE3_SR_NSPRED: SITE 3 @0x02261E3E: the arm's archetype predicate.
                               #   is_scrap -> write 0x0FF6 into the arm's literal-pool
                               #   word 0x02261F84 and return 1; else chain
                               #   CAVE_NS_PRED (which writes Dverg/Ninishi).  0x30 B.
CAVE_SR_NSFIELD  = 0x023A1454  # moved to ov3 cave3.CAVE3_SR_NSFIELD: SITE 3 @0x02261E68: "where is the granter?"  For
                               #   0x0FF6 answers from the GRANT NODE instead of the
                               #   field -- this is what makes the grant outlive the
                               #   granter -- returning 0 (present) / -1 (absent); the
                               #   value is read ONLY by the following `blt`, r0 being
                               #   reloaded at 0x02261E70.  Else chain CAVE_NS_FIELD.  0x30 B.
CAVE_SR_NSCOUNT  = 0x023A1484  # moved to ov3 cave3.CAVE3_SR_NSCOUNT: SITE 3 @0x02261E92 -- A FRESH HOOK, stock before-image
                               #   `bl 0x021B9514`.  For 0x0FF6 returns 0, forcing the
                               #   `beq 0x02261ED6` announce-SKIP.  That is deliberate:
                               #   the announce at 0x02261E9A DEREFERENCES the granter's
                               #   field slot (0x02261EC0 `ldr r5,[r6,r3]`), which for a
                               #   granter that has left the field would decode a garbage
                               #   card ref.  Cost: the 0xE2 announce event is not posted
                               #   for Raptor.   0x30 B --
                               #   0x20 fits with ZERO free, the exact trap that
                               #   forced ninishi's five stubs to be relocatable.
CAVE_SR_NSMATCH  = 0x023A14B4  # moved to ov3 cave3.CAVE3_SR_NSMATCH: SITE 4 @0x0226515C: "is this descriptor's granter ours?"
                               #   ⚠️ the host reads BOTH Z and r1, so the tail MUST be
                               #   `ldr r1,=CAVE_NS_MATCH|1 ; bx r1` -- a `bl` would eat
                               #   the LR that CAVE_NS_MATCH returns through.  0x20 B.
CAVE_SR_NSPOST   = 0x023A14D4  # moved to ov3 cave3.CAVE3_SR_NSPOST: SITE 4 @0x0226517C -- A FRESH HOOK, stock before-image
                               #   `bl 0x021D2584`.  The host hardcodes the kind with
                               #   `movs r2,#1` at 0x02265176, a lone 2 B instruction that
                               #   cannot branch; kind 1 on key 0x0FF6 is C1a's OPT latch,
                               #   so posting it would mark NOTHING spent and C1b would be
                               #   repeatable while verify() passed.  This forces r2 = 2
                               #   for 0x0FF6, then tails into the native poster.  0x20 B.
CAVE_MISC_COND   = 0x023A14F4  # Miscellaneousaurus C2, cls2 +0C: OPT, SS gates, and "some
                               #   Level L in 1..GY Dinosaurs has a Deck candidate" (writes the
                               #   criteria row-0 Level byte, restores 0); C1 hand Main-Phase gate.  0xD0 B.
CAVE_MISC_COST   = 0x023A15C4  # Miscellaneousaurus C2, cls2 +10: 0x47 "any number" picker over ALL GY
                               #   Dinosaurs incl. this card, banish picks, then this card if unpicked; N -> desc[+0x14]; OPT
                               #   stamp; C1 tail-calls 0x021E8FB9.  0x110 B.
CAVE_MISC_RES    = 0x023A16D4  # Miscellaneousaurus C2, cls2 +04: NAST's Deck-SS phase machine,
                               #   Level byte = N<<2; C1 Dinosaur protection tags.  0x1B0 B.
CAVE_MISC_SPEED  = 0x023A1884  # Miscellaneousaurus C1: speed-lookup default-leaf hook 0x021A894C --
                               #   speed 1 for 0x0FF2's GY path (keeps C2 an ignition).  0x20 B.
CAVE_OVI_COND    = 0x023A18A4  # Souleating Oviraptor C1, cls1 +0C: turn-log kind 1 clear, then 0x021F0821.  0x30 B.
CAVE_OVI_SLOT4   = 0x023A18D4  # Souleating Oviraptor C1, cls1 +10: "You can" 0x021E51E5; post turn log on 1.  0x30 B.
CAVE_OVI_RES     = 0x023A1904  # Souleating Oviraptor C1, cls1 +04: phase 0x80 hand/GY prompt -> private 0x90
                               #   stores the answer in desc[+0x18], then 0x02207EF5 (hand) / 0x02208DD5 (GY).  0x60 B.
CAVE_OVI_C2FILT  = 0x023A1964  # Souleating Oviraptor C2, cls3 +08 (desc, side, zone): Snowman Eater's 0x1414
                               #   wrapper, not this card's zone, live Level <= 4, live race Dinosaur.  0x80 B.
CAVE_OVI_C2COND  = 0x023A19E4  # Souleating Oviraptor C2, cls3 +0C: turn log kind 2 clear (desc[+7] guard),
                               #   a Dinosaur in own GY, then native 0x021F01C1.  0x70 B.
CAVE_OVI_C2COST  = 0x023A1A54  # Souleating Oviraptor C2, cls3 +10: post turn log kind 2, then native 0x021E5061.  0x28 B.
CAVE_OVI_C2RES   = 0x023A1A7C  # Souleating Oviraptor C2, cls3 +04: 0x80 destroy -> 0x90 [0x0229C314+0x14] test,
                               #   SS gates, candidates -> Misc's picker/commit (DEF) phases.  0x120 B.
CAVE_PTER_NOATK  = 0x023A1B9C  # Petiteranodon C3: BOTH `bl 0x02022E14` list searches (0x021A4AC6 attack-check
                               #   list 0x0226D6F8, 0x02268090 summon-rider list 0x0228F708) -> "key 0x0FE1 ? 1 :
                               #   tail 0x02022E14".  SHARED paths: a puzzle freezes on them.
                              #   0x20 B.
# --- Brilliant Fusion C1 + C4 (donor Temple of the Sun 0x21D5) ---
#  notes/brilliant-fusion-findings.md.
CAVE_RIDERLATCH  = 0x023A1BBC  # summon_rider_hook LATCH PREFIX (0x50 bytes): cid-blind riders; hook
                               #   0x02268666 points here ONLY when LATCH_ARMS is non-empty, and the
                               #   prefix tail-jumps to CAVE_RIDERHOOK.  Owned by summon_rider_hook.
CAVE_BF_MODE     = 0x023A1C0C  # (0x20 bytes) the 10 `bl 0x022325B4` fusion-mode sites -> 0x21D5 ? 2 (Deck
                               #   materials) : tail `bx` 0x022325B5 with lr intact.
CAVE_BF_DECKGY   = 0x023A1C2C  # (0x50 bytes) hook 0x02233564 in the material-move loop: Deck material +
                               #   dest GY + effect 0x21D5 -> 0x021D1DAC(side, 0, ref, 0x10, [sp]=cid), set
                               #   CAVE_BF_ARM, return Z=0; else replay `ldr r0,[sp,#4] ; cmp r0,#0xf`.
CAVE_BF_COND     = 0x023A1C7C  # (0x30 bytes) cls0 +0C: 1/turn query 0x021F6DD8, then native 0x02232CB1.
CAVE_BF_COST     = 0x023A1CAC  # (0x30 bytes) cls0 +10: post the 1/turn node, clear a stale CAVE_BF_ARM.
CAVE_BF_ARM      = 0x023A1CDC  # (0x4 bytes) the ATK/DEF-0 rider's one-shot latch byte.  SHIPS CLEAR.
# (Build 2's CAVE_BF_RES -- Future Fusion's pre-picker ED UI step -- was removed in build 3: the picker had
#  been filled from the wrong criteria ROW, not shown the wrong view.  Build 4 reuses the slot for C2.)
CAVE_BF_RES      = 0x023A1CE0  # (0x60 bytes) cls0 +04, C2: on resolver phase 1 (after the commit returns 1), if the
                               #   summon event says source 0x21D5 summoned the Fusion target, attach the leave link
                               #   0x021C479C(side, [0x02298A28+4], desc[3]<<8|desc[2], 0x17, 0) -- Future Fusion /
                               #   Ninjitsu Art recipe -- then the native Fusion resolver 0x02232CFD.
CAVE_BF_C3FIND   = 0x023A1D40  # (0x48 bytes) C3 helper: (desc) -> (side<<8)|slot of the monster linked to this card
                               #   (0x021A0C94 over both sides x slots 0..4, != 0 && != 0xC like the leave loop), else -1.
CAVE_BF_C3COND   = 0x023A1D88  # (0x30 bytes) cls3 +0C, C3: linked monster present -> Chiron's cid-blind 0x021F7375.
CAVE_BF_C3RES    = 0x023A1DB8  # (0x60 bytes) cls3 +04, C3: 0x021B44B4 original ATK/DEF, then two riders
                               #   {0x221D (Tyrant Neptune pair leaf 0x021B6CA0), kind 0x12} = +ATK, +DEF to end of next turn.
# 0x023A1E18..0x023A1E38 (0x20 B) was CAVE_LIGHTSWORN_GROUP, raiden build 1 only (never shipped): the deck
# editor has no ov5, so the set-code list went back to ARM9 in place. Free for reuse.
CAVE_RAIDEN_ONFIELD = 0x023A1E38  # (0x50 bytes) raiden helper (desc) -> 1 iff desc[+0xC] is still the card in
                                  #   zone desc[3] and zone-word bit 26 is clear (Jain resolver 0x022286AC's guard).
CAVE_RAIDEN_EP   = 0x023A1E88  # (0x34 bytes) raiden C2, cls1 +04: guard, 0x021D2C1C, mill 2 via 0x021D2148.
CAVE_RAIDEN_COND = 0x023A1EBC  # (0x50 bytes) raiden C1, cls3 +0C: desc[+7] guard, Deck >= 2, turn-log clear,
                               #   then native 0x021F06E8.
CAVE_RAIDEN_COST = 0x023A1F0C  # (0x1C bytes) raiden C1, cls3 +10: post turn-log kind 1, return 1.
CAVE_RAIDEN_RES  = 0x023A1F28  # (0xC0 bytes) raiden C1, cls3 +04: peek top 2, mill 2, Lightsworn monster
                               #   -> rider {0x216D, kind 0x12} = flat +200 ATK to end of next turn.
CAVE_SM_COND     = 0x023A1FE8  # (0x30 bytes) shadow_mist, cls1 AND cls2 +0C: turn log (side, 0xB, 0x111F, 1)
                               #   clear -> 0x021F0821 (r1 preserved), else 0.  Shared lock = printed C3.
CAVE_SM_SLOT4    = 0x023A2018  # (0x30 bytes) shadow_mist, cls1 AND cls2 +10: "You can" 0x021E51E5; on 1 post
                               #   turn log (side, 0x111F, 1, 0) -- stamp at ACTIVATION.
CAVE_DL_COND     = 0x023A2048  # (0x50 bytes) masked_hero_dark_law C3, cls1 +0C: code 0x1B/0x1C, not Draw
                               #   Phase, opponent hand non-empty, then per-copy 0x0FB6 gate 0x021F01C1.
CAVE_DL_SLOT4    = 0x023A2098  # (0x30 bytes) masked_hero_dark_law C3, cls1 +10: "You can" 0x021E51E5; on 1
                               #   stamp the per-copy 0x0FB6 rider via 0x021E5061 -- at ACTIVATION.
CAVE_DL_RES      = 0x023A20C8  # (0x78 bytes) masked_hero_dark_law C3, cls1 +04: 0x80 random pick of the
                               #   opponent's hand 0x022599F9, 0x7F face-up banish 0x021C6E4D(opp, &hand[i], 1).
CAVE_DEP_COND    = 0x023A2140  # (0xE0 bytes) double_evolution_pill, cls0 +0C: desc[+7] -> native; once per
                               #   turn 0x021F6DD8; own hand+GY scan for a Dinosaur AND a non-Dinosaur monster;
                               #   then Emergency Teleport's native cond 0x021F0419.
CAVE_DEP_COST    = 0x023A2220  # (0x140 bytes) double_evolution_pill, cls0 +10: two picks from row 0 (cost
                               #   mode), refs in desc[+0x14/+0x16]; commit per ref: hand 0x021C6E98 else GY
                               #   0x021C7104; stamp once per turn 0x021D2584.
CAVE_DEP_HAND_OLD = 0x023A2360  # RETIRED (0xC0 bytes) -- DEP's first criteria handler; superseded by
                               #   CAVE_DEP_HAND (the second, gate-free Deck pass for restricted-class Dinosaurs).
CAVE_DEP_FILT    = 0x023A2420  # (0x60 bytes) double_evolution_pill builder filters: +0 Dinosaur, +0x30
                               #   non-Dinosaur monster (race != 9 and < 23).
CAVE_UCT_SSCOND  = 0x023A2480  # (0x40 bytes) ultimate_conductor_tyranno C1, hand-SS trampoline cond:
                               #   0x0225D0D0 with the count fixed at 2 (canSS, free zone, >= 2 GY Dinosaurs).
CAVE_UCT_RES     = 0x023A24C0  # (0xB0 bytes) ultimate_conductor_tyranno C4, cls1 +04: 0x80 burn 1000 to the
                               #   defender side, 0x7F send the defender to GY (0x021CDD4C kind 0x1000), 0x7E close.
CAVE_UCT_C2COND  = 0x023A2570  # (0x30 bytes) ultimate_conductor_tyranno C2, cls3 +0C: Main Phase (2/4) of
                               #   either player unless desc[+7], then the per-copy OPT latch 0x021F01C1.
CAVE_UCT_C2HELP  = 0x023A25A0  # (0xA0 bytes) ultimate_conductor_tyranno C2 helper: count / record own
                               #   monsters in hand (is-monster 0x02029E60) or field zones 0..4 via recorder 0x02243B2C.
CAVE_UCT_C2RES   = 0x023A2640  # (0x220 bytes) ultimate_conductor_tyranno C2, cls3 +04: Hands/Field prompt,
                               #   own picker list + UI 0x0219C99C, destroy 0x021CF374 / 0x021D2478, then Book of
                               #   Eclipse's flip 0x021C4F24 on the opponent's face-up monsters.
CAVE_DEP_HAND    = 0x023A2860  # (0xE0 bytes) double_evolution_pill criteria handler, row 0 of 0x1319: cost
                               #   mode (hand+GY banish, filter by desc[+0x12]) else Emergency Teleport's hand+Deck
                               #   PLUS a second Deck pass (type 2, no 0x021BA69C gate) keeping only restricted-class
                               #   cids -- "ignoring its Summoning conditions" for nomi Dinosaurs (Tyranno 0x1265).
CAVE_DEP_NOMI    = 0x023A2940  # (0x20 bytes) double_evolution_pill Deck-pass predicate: 0x020231C8(cid) != 0.
CAVE_UCT_C4COND  = 0x023A2960  # (0x20 bytes) ultimate_conductor_tyranno C4, cls1 +0C: face-up Defense
                               #   0x021F842D OR face-down Defense 0x021F5A1D (either face, not a direct attack).
CAVE_ARCH_COND   = 0x023A2980  # (0x60 bytes) animadorned_archosaur cls1 +0C: turn log (side, 0xB, 0x1297, 1)
                               #   clear AND a destroyable Dinosaur in hand / face-up field (CAVE_ARCH_HELP).
CAVE_ARCH_SLOT4  = 0x023A29E0  # (0x30 bytes) animadorned_archosaur cls1 +10: "You can" 0x021E51E5, post turn log on Yes.
CAVE_ARCH_HELP   = 0x023A2A10  # (0xE0 bytes) animadorned_archosaur: count / record own Dinosaurs (not 0x1297) in
                               #   hand (printed race) or face-up field zones 0..4 (live race 0x021B88F0).
CAVE_ARCH_PRED   = 0x023A2AF0  # (0x60 bytes) animadorned_archosaur Deck-walker predicate: monster -> race in
                               #   {Reptile 20, Sea Serpent 5, Winged Beast 16}; Spell -> cid in the Evolution Pill list.
CAVE_ARCH_CRIT   = 0x023A2B50  # (0x30 bytes) animadorned_archosaur criteria handler: Deck walker 0x0223BC3C, type 2.
CAVE_ARCH_RES    = 0x023A2B80  # (0x280 bytes) animadorned_archosaur cls1 +04: Tyranno's Hand/Field pick + destroy,
                               #   Level -> criteria row +0xA, then the native add-to-hand resolver 0x02207EF5.
CAVE_OQ_SSCOND   = 0x023A2E00  # (0x40 bytes) overtex_qoatlus C1, hand-SS trampoline cond: 0x0225D0D0
                               #   with the count fixed at 5 (banished Dinosaurs via criteria row 0).
CAVE_OQ_PAY      = 0x023A2E40  # (0xC0 bytes) overtex_qoatlus C1, summon-procedure registry handler for
                               #   0x10A5: wraps 0x0226292D; own state 0 (count 5) + state 2 (banished->Deck
                               #   0x021C727C per pick, then SHUFFLE_DECK 0x021D269C).
CAVE_OQ_CRIT     = 0x023A2F00  # (0xA0 bytes) overtex_qoatlus C1 criteria handler (row 0 of 0x10A5): 0x0223DB24's
                               #   banished walk (type 8) + a predicate rejecting Extra-Deck cards 0x0202307C ("Main Deck");
                               #   C3 mode (own cls2 descriptor): Deck walk word 0x4 + CAVE_ARCH_PRED (Pills).
CAVE_OQ_C3COND   = 0x023A2FA0  # (0x30 bytes) overtex_qoatlus C3, cls2 +0C: turn log (side, 0xB, 0x10A5, 2)
                               #   clear -> native have-target 0x021F0821.
CAVE_OQ_C3SLOT4  = 0x023A2FD0  # (0x30 bytes) overtex_qoatlus C3, cls2 +10: "You can" 0x021E51E5, stamp kind 2 on Yes.
CAVE_OQ_C2COND   = 0x023A3000  # (0xA0 bytes) overtex_qoatlus C2, cls3 +0C: Wall's pre-checks (Spell OR Trap,
                               #   opponent), per-copy latch 0x021F01C0, destroyable Dinosaur, offer gate 0x021F06E8.
CAVE_OQ_C2HELP   = 0x023A30A0  # (0xE0 bytes) overtex_qoatlus C2: count / record own Dinosaurs in hand / face-up field.
CAVE_OQ_C2RES    = 0x023A3180  # (0x240 bytes) overtex_qoatlus C2, cls3 +04: stash act, Archosaur's pick + destroy
                               #   on phases 0x90..0x94, then negate 0x022062F9(desc, act).
CAVE_OQ_C2ACT    = 0x023A33C0  # (0x10 bytes) overtex_qoatlus C2: RUNTIME cell, the activation descriptor pointer.
CAVE_OQ_SPEED    = 0x023A33D0  # (0x20 bytes) overtex_qoatlus C2: speed-leaf stub (0x10A5 cls3 -> 2, else Misc's).
CAVE_LSD_MAT     = 0x023A33F0  # moved to ov3 cave3.CAVE3_LSD_MAT: (0x20 bytes) life_stream_dragon C0: THIRD cid-tree entry 0x02248AB8 -> for
                               #   Synchro 0x18FA jump to the native Life Stream 0x2525 leaf 0x02249478 (material == 0x1FC9).
CAVE_LSD_RES     = 0x023A3410  # moved to ov3 cave3.CAVE3_LSD_RES: (0x30 bytes) life_stream_dragon C1, cls1 +04: phase 0x80 -> set LP 0x021CF8F4(side, 4000).
CAVE_LSD_DMG     = 0x023A3440  # moved to ov3 cave3.CAVE3_LSD_DMG: (0x30 bytes) life_stream_dragon C2: Des Wombat arm 0x021BACCC detour, + 0x18FA face-up.
CAVE_OJ_OJ       = 0x023A3470  # (0x40 bytes) ojamassimilation helper: (cid) -> "Ojama" monster, not a Token.
CAVE_OJ_OPRED    = 0x023A34B0  # (0x20 bytes) ojamassimilation hand / GY builder filter -> CAVE_OJ_OJ.
CAVE_OJ_HAS      = 0x023A34D0  # (0xB0 bytes) ojamassimilation helper: (side, cid) -> that name in hand/Deck/GY.
CAVE_OJ_ZCAP     = 0x023A3580  # (0x60 bytes) ojamassimilation helper: (side) -> empty MZ + face-up field Ojamas.
CAVE_OJ_RPRED    = 0x023A35E0  # (0x60 bytes) ojamassimilation Extra-Deck walker predicate: a literal recipe
                               #   slot (>= 0xBB8) names a card in own hand / Deck / GY (Prisma 0x0224050C, 3 zones).
CAVE_OJ_GYCOND   = 0x023A3640  # (0x40 bytes) ojamassimilation C3 cls2 +0C: >= 3 own banished Ojama (param 2).
                               #   This and GYSEL re-use the first 0x140 of the former 0x190 CAVE_OJ_HANDLER slot
                               #   (unshipped card; the handler outgrew it for C3's mode and moved to 0x023A3C80).
CAVE_OJ_GYSEL    = 0x023A3680  # (0x100 bytes) ojamassimilation C3 cls2 +14: multi-select tail 0x02235912
                               #   rewritten with count code 9 / prompt 0x116 / param 2 (0x02234E78 gives 0 = REVEAL).
CAVE_OJ_COND     = 0x023A37D0  # (0x60 bytes) ojamassimilation cls0 +0C.
CAVE_OJ_COST     = 0x023A3830  # (0x260 bytes) ojamassimilation cls0 +10: reveal pick, number picker, exact-N
                               #   Ojama pick, reveal cmd 0x58 + 3-zone banish (payment machine 0x02262B7E order).
CAVE_OJ_RES      = 0x023A3A90  # (0x170 bytes) ojamassimilation cls0 +04: one material SS per entry, names excluded.
CAVE_LSD_DEC     = 0x023A3C00  # moved to ov3 cave3.CAVE3_LSD_DEC: (0x20 bytes) life_stream_dragon C3: non-field substitute DECIDE switch
                               #   0x021CE89C -> 0x18FA joins Laval the Greater's criteria-row arm 0x021CE940.
CAVE_LSD_ACK     = 0x023A3C20  # moved to ov3 cave3.CAVE3_LSD_ACK: (0x20 bytes) life_stream_dragon C3: Yes-consumer switch 0x021CF00E -> 0x18FA
                               #   joins Laval's picker arm 0x021CF066 (step 9, then GY->banished 0x021C7104).
CAVE_LSD_STEP9   = 0x023A3C40  # moved to ov3 cave3.CAVE3_LSD_STEP9: (0x20 bytes) life_stream_dragon C3: UI step 9 0x0225CAC8 / 0x0225CAF2,
                               #   flags = (r4 == 0x22D3 || r4 == 0x18FA).
CAVE_LSD_SURV    = 0x023A3C60  # moved to ov3 cave3.CAVE3_LSD_SURV: (0x20 bytes) life_stream_dragon C3: executor survive leaf 0x021CC656, r4 := 0x18FA
                               #   when [sp+0x64] is the donor, else Laval's 0x22D3.
CAVE_OJ_HANDLER  = 0x023A3C80  # (0x1B0 bytes) ojamassimilation criteria handler, row 0 of 0x170F, mode = param:
                               #   0 Extra-Deck LIGHT Machine Fusions | 1 Ojama hand/GY/face-up field | 2 own banished
                               #   Ojama (C3) | 0x10000 listed materials minus excluded slots | 0x20000 one cid.
CAVE_OJ_GYRES    = 0x023A3E30  # (0x100 bytes) ojamassimilation C3 cls2 +04: Pot of Avarice 0x0221FB94 on the
                               #   banished zone (index 0x021A2558, mover 0x021C727C), then draw 1.
CAVE_TGLG_COND   = 0x023A3F30  # (0x40 bytes) that_grass_looks_greener cls0 +0C: DFW gate + own Deck > opp Deck.
CAVE_TGLG_RES    = 0x023A3F70  # (0x40 bytes) that_grass_looks_greener cls0 +04: mill (own - opp) if > 0.
CAVE_OS_PRED     = 0x023A3FB0  # (0x60 bytes) obedience_schooled Deck builder filter: Effect Monster, name not
                               #   in the param (pick1 | pick2 << 14).
CAVE_OS_HANDLER  = 0x023A4010  # (0x40 bytes) obedience_schooled criteria row 312: Deck builder, flags 0xA, PRED.
CAVE_OS_COND     = 0x023A4050  # (0x80 bytes) obedience_schooled cls0 +0C: canSS, 0 own monsters, 3 distinct names.
CAVE_OS_RES      = 0x023A40D0  # (0x120 bytes) obedience_schooled cls0 +04: pick 1 / exclude name / SS, x3.
CAVE_SEAL_FILT   = 0x023A41F0  # moved to ov3 cave3.CAVE3_SEAL_FILT: (0x20 bytes) seal_of_orichalcos C4 cls0 +08: Special Hurricane's 0x021DD6CC
                               #   with mask 0x1011 (own side) -- replays its prologue, joins at 0x021DD6D4.
CAVE_SEAL_COND   = 0x023A4210  # moved to ov3 cave3.CAVE3_SEAL_COND: (0x20 bytes) seal_of_orichalcos C6 cls0 +0C: kind-5 turn-log query -> 0 / 2.
CAVE_SEAL_RES   = 0x023A4230  # moved to ov3 cave3.CAVE3_SEAL_RES: (0x20 bytes) seal_of_orichalcos C4+C6 cls0 +04: post kind 5, then the shared
                               #   destroy resolver 0x022048FC (C6 counts only on resolution, user ruling).
CAVE_EVA_BPRED   = 0x023A4250  # (0x30 bytes) eva GY banish filter: card ref != the activating card's ref.
CAVE_EVA_DPRED   = 0x023A4280  # (0x30 bytes) eva Deck filter: name differs from the excluded (first pick) cid.
CAVE_EVA_HANDLER = 0x023A42B0  # (0xC0 bytes) eva criteria handler: mode 1 banish (GY + face-up field LIGHT
                               #   Fairy, not this card) | mode 2 Deck Lv<=2 LIGHT Fairy, not "Eva", name != excl.
CAVE_EVA_COND    = 0x023A4370  # (0x60 bytes) eva cls2 +0C: desc[+7] | turn-log kind 1 clear, a banish + a Deck target.
CAVE_EVA_COST    = 0x023A43D0  # (0x1C0 bytes) eva cls2 +14: OPT stamp, number picker 1..min(2,..), pick, banish.
CAVE_EVA_RES     = 0x023A4590  # (0x100 bytes) eva cls2 +04: add N different-name picks Deck -> hand.
CAVE_MARA_VALID  = 0x023A4690  # moved to ov3 cave3.CAVE3_MARA_VALID: (0xB0 bytes) mara validator hand branch @0x02249BEE: Mara mode = count 1-2,
                               #   hand card is a Nordic monster and not already pick 1; else native `cmp count,#1`.
CAVE_MARA_COUNT  = 0x023A4740  # moved to ov3 cave3.CAVE3_MARA_COUNT: (0x40 bytes) mara level_sum completion @0x02249714: Mara mode needs >= 3 picks.
CAVE_MARA_FIRST  = 0x023A4780  # moved to ov3 cave3.CAVE3_MARA_FIRST: (0x30 bytes) mara validator field `bl 0x02029E60` @0x02249B92: donor at count != 0
                               #   -> reject 0x02249B20 (Mara is only ever the first material).
CAVE_MARA_SEND   = 0x023A47B0  # moved to ov3 cave3.CAVE3_MARA_SEND: (0x90 bytes) mara Synchro step 5 @0x0226395C: Mara mode sends hand picks 2..
                               #   (native step 5 sends only the first hand pick).
CAVE_WU_U3COND   = 0x023A4840  # (0x30 bytes) wattuna U3 cls2 +0C: turn-log kind 1 clear -> native 0x021F0A39.
CAVE_WU_U3COST   = 0x023A4870  # (0x30 bytes) wattuna U3 cls2 +14 cost: short-circuit 0x021D2BC8, stamp turn-log kind 1 (Eva shape).
CAVE_WU_U4COND   = 0x023A48A0  # (0x30 bytes) wattuna U4 cls1 +0C: turn-log kind 2 clear -> native 0x0224A115.
CAVE_WU_U4COST   = 0x023A48D0  # (0x30 bytes) wattuna U4 cls1 +14 (slot5): short-circuit, stamp turn-log kind 2.
CAVE_WU_OFFER    = 0x023A4900  # (0x40 bytes) wattuna U4 criteria handler: Aurora 0x022430A0 with mode 0x24
                               #   (+ can_synchro), CAVE_WU_PROBE = 1 around the Extra-Deck enumerator call.
CAVE_WU_PROBE    = 0x023A4940  # (0x10 bytes) wattuna U4 probe flag word (read by the ov3 gate stub 0x021BB288).
CAVE_WK_OUTER    = 0x023A4950  # (0x20 bytes) wattkyuki C0 Tuner side: OUTER cid-switch entry 0x02248660 ->
                               #   Synchro 0x1458 jumps to the native Watt Tuner leaf 0x02248A40 (is-Watt), else replay.
CAVE_WK_THIRD    = 0x023A4970  # (0x20 bytes) wattkyuki C0 non-Tuner side: THIRD tree pair 0x02248AFA ->
                               #   Synchro 0x1458 jumps to the native Watt leaf 0x02248FD8 (race == Synchro's), else replay.
CAVE_WK_RES      = 0x023A4990  # (0x200 bytes) wattkyuki C2 cls1 +04: own phase machine -- pick GY Watt Tuner ->
                               #   0x021C6A0C (push/pop), pick face-up non-Tuner Thunder -> 0x021CF590, 0x021D26CC, pick + SS.
CAVE_WK_HAND     = 0x023A4B90  # (0x160 bytes) wattkyuki C2 criteria handler (row, side): phase-keyed GY / EXTRA / FIELD
                               #   sub-handlers (side) at +0x40 / +0x80 / +0xC0 (direct-callable by CAVE_WK_COND).
CAVE_WK_EDPRED   = 0x023A4CF0  # (0x40 bytes) wattkyuki C2 Extra-Deck predicate: Watt (0x58) Synchro, cid != 0x1458.
CAVE_WK_COND     = 0x023A4D30  # (0xA0 bytes) wattkyuki C2 cls1 +0C: turn-log kind 1 + all three candidate pools > 0.
CAVE_WK_COST     = 0x023A4DD0  # (0x30 bytes) wattkyuki C2 cls1 +14: stamp turn-log kind 1 (Wattuna's opt_cost_stub).
CAVE_TG_SSTABLE  = 0x023A4E00  # moved to ov3 cave3.CAVE3_TGSH_SSTABLE: SHARED hand-SS dispatch table {cid u16, pad u16, cond-ptr u32}, zero-terminated (0x80 bytes)
                               #   = 15 registrants + terminator. Read by the trampoline's pool literal.
CAVE_GS_SSCOND   = 0x023A4E80  # (0x40 bytes) grandsoil C2 hand-SS trampoline cond: free zone && canSS &&
                               #   0x021B1810(side, EARTH=5) == 5 (Dark Armed Dragon's gate 0x0225FB8C, 5 EARTH).
CAVE_TIMINGHOOK  = 0x023A4EC0  # (0x200 bytes) SHARED timing-class hook stub (timing_class_hook.py); 4-aligned base.
CAVE_GS_COND     = 0x023A50C0  # (0x30 bytes) grandsoil C3/C4 cls1 +0C: turn log (side,0xB,0x1110,1) clear -> 0x021F03B5.
CAVE_GS_SLOT4    = 0x023A50F0  # (0x30 bytes) grandsoil C3/C4 cls1 +10: "You can" 0x021E51E5; on Yes post the turn log.
CAVE_ML_SSCOND   = 0x023A5120  # (0x40 bytes) moulinglacia C2 hand-SS trampoline cond: CAVE_GS_SSCOND's shape
                               #   with 0x021B1810(side, WATER=3) == 5.
CAVE_ML_RES      = 0x023A5160  # (0x50 bytes) moulinglacia C3/C4 cls1 resolver: post turn log (side,0x1C1A,1),
                               #   n = min(2, opp hand) (Wiraqocha clamp); n -> 0x022599C8(1-side, 1, n). Returns 0.
CAVE_ML_COND     = 0x023A51B0  # (0x30 bytes) moulinglacia C3/C4 cls1 +0C: turn log (side,0xB,0x1C1A,1) clear -> 2.
CAVE_PX_SSCOND   = 0x023A51E0  # (0x40 bytes) pyrorex C2 hand-SS trampoline cond: CAVE_GS_SSCOND's shape
                               #   with 0x021B1810(side, FIRE=4) == 5.
CAVE_PX_RES      = 0x023A5220  # (0xD0 bytes) pyrorex C3 cls1 resolver: 0x02210311's destroy-then protocol,
                               #   amount = half original ATK (Edge Hammer read), damage both (Ring of Destruction).
CAVE_PX_COND     = 0x023A52F0  # (0x30 bytes) pyrorex C3/C4 cls1 +0C: turn log (side,0xB,0x181F,1) clear -> 1.
CAVE_PX_SLOT4    = 0x023A5320  # (0x30 bytes) pyrorex C3/C4 cls1 +10: "You can" 0x021E51E5; on Yes post the turn log.
CAVE_WR_SSCOND   = 0x023A5350  # (0x40 bytes) windrose C2 hand-SS trampoline cond: CAVE_GS_SSCOND's shape
                               #   with 0x021B1810(side, WIND=6) == 5.
CAVE_WR_RES      = 0x023A5390  # (0x30 bytes) windrose C3/C4 cls1 resolver: post turn log (side,0x190B,1),
                               #   then the native HFD resolver 0x022048FD(desc) (record-driven, +08 0x021DA081). Returns 0.
CAVE_WR_COND     = 0x023A53C0  # (0x30 bytes) windrose C3/C4 cls1 +0C: turn log (side,0xB,0x190B,1) clear -> 2.
CAVE_C79TRIG_OLD = 0x023A53F0  # RETIRED (0x30 bytes) -- FULL at 3 arms (a 4th = 60 B); c79 stub re-homed to CAVE_C79TRIG 2026-11-04 (Disguise).
CAVE_WR_AICLASS  = 0x023A5420  # (0x20 bytes) windrose: CPU hand-SS planner site ov5 0x0236A1BA ->
                               #   0x020231C8(cid), but 2 for 0x190B (rules keep class 4; AI sees class 2).
CAVE_UZ_MASK     = 0x023A5440  # (0x80 bytes) uni_zombie: (desc) -> C1|C2 legality bits (OPT + hand / Zombie in Deck).
CAVE_UZ_COND     = 0x023A54C0  # (0x30 bytes) uni_zombie cls3 +0C: post-cost pass-through, MASK != 0, offer gate 0x021F06E9.
CAVE_UZ_COST     = 0x023A54F0  # (0x90 bytes) uni_zombie cls3 +10: "Use which effect?" prompt, desc[+0x18], OPT post.
CAVE_UZ_RES      = 0x023A5580  # (0x100 bytes) uni_zombie cls3 +04: C1 discard -> Level+1 / C2 lock + native deck-send
                               #   0x02208DD5 + phase-0x7C Level+1. (Its attack-gate hook stays ov3: cave3.CAVE3_UZ_ATK.)
CAVE_SK_COND     = 0x023A5680  # (0xF0 bytes) sakitama cls2 +0C: desc[+3]==0xB -> C3 (turn/MP/OPT/floodgate/Spirit
                               #   in hand) else C4 (OPT kind 2, criteria count).
CAVE_SK_COST     = 0x023A5770  # (0x30 bytes) sakitama cls2 +10: C3 reveal + post (0x13E5,1) = OPT+grant; C4 post kind 2.
CAVE_SK_RES_OLD  = 0x023A57A0  # RETIRED (0x20 bytes): sakitama RES outgrew it -> CAVE_SK_RES.
CAVE_SK_TGT      = 0x023A57C0  # (0x20 bytes) sakitama cls2 +14: C3 -> 1 (absent), C4 -> 0x02235605.
CAVE_SK_LEAVE    = 0x023A57E0  # (0x30 bytes) sakitama: front over Assault's BL @0x021C93D0 -- 0x13E5 Tributed
                               #   off the field -> [sp+0x18] = 1 (Shinai's arm), then CAVE_ASSAULT_LEAVEHOOK.
CAVE_SK_RES      = 0x023A5810  # (0x30 bytes) sakitama cls2 +04: C3 -> 0x0220D80C then post (side, 0x3E50, 1)
                               #   when it returns 0; C4 -> 0x02208181.
CAVE_NK_GAINCOND = 0x023A5840  # (0x30 bytes) nikitama cls1 #1 +0C: grant (side, 0x3E52, 1) absent -> 2.
CAVE_NK_GAINRES  = 0x023A5870  # (0x20 bytes) nikitama cls1 #1 +04: post (side, 0x3E52, 1) = the extra-NS grant.
CAVE_NK_DRAWCOND = 0x023A5890  # (0x30 bytes) nikitama cls2 +0C: face-up Spirit (0x021ACFE8) && draw cond 0x021F069D.
CAVE_NK_DRAWRES  = 0x023A58C0  # (0x30 bytes) nikitama cls2 +04: face-up Spirit -> draw 0x022065B8.
CAVE_NSC_PRED    = 0x023A5A90  # (0x80 bytes) neo_space_connector: 9-cid predicate (8 Neo-Spacians + E-HERO Neos), caller [sp] = card word ptr.
CAVE_NSC_CRIT    = 0x023A5B10  # (0x90 bytes) neo_space_connector: ONE criteria row, mode switch on acting desc (own cls3 -> GY, else hand+Deck).
CAVE_NSC_COND    = 0x023A5BA0  # (0x90 bytes) neo_space_connector C1 cls1 +0C: OPT kind 1 clear + direct hand/Deck scan via the predicate.
CAVE_NSC_SLOT4   = 0x023A5C30  # (0x30 bytes) neo_space_connector C1 cls1 +10: "You can" 0x021E51E5; on 1 post kind 1.
CAVE_NSC_RES     = 0x023A5C60  # (0x100 bytes) neo_space_connector C1 cls1 +04: deck-SS machine phases, commit position 1 (DEF).
CAVE_NSC_C2COND  = 0x023A5D60  # (0x80 bytes) neo_space_connector C2 cls3 +0C: desc[+7] guard, OPT kind 2 + own-GY scan, then 0x021F06E9.
CAVE_NSC_C2COST  = 0x023A5DE0  # (0x30 bytes) neo_space_connector C2 cls3 +10: post kind 2, then Tribute-self 0x021E50CD.
CAVE_NSC_C2RES   = 0x023A5E10  # (0x20 bytes) neo_space_connector C2 cls3 +04: 0x02204731(desc, 1, 1 = DEF), return 0.
CAVE_NEXT_DATA   = 0x023A5E30  # (0x20 bytes) next_card: u32 USED-name mask (runtime) + the 9 listed cids (u16).
CAVE_NEXT_PRED   = 0x023A5E50  # (0x40 bytes) next_card: listed cid AND its USED bit clear; caller [sp] = card word ptr.
CAVE_NEXT_CRIT   = 0x023A5E90  # (0x50 bytes) next_card: criteria row 489 handler = hand builder + GY builder.
CAVE_NEXT_COND   = 0x023A5EE0  # (0xA0 bytes) next_card cls0 +0C: OPT (desc[+7]==0) + free zone + listed cid in hand/GY.
CAVE_NEXT_COST   = 0x023A5F80  # (0x30 bytes) next_card cls0 +10: post the 1-per-turn node at activation.
CAVE_NEXT_RES    = 0x023A5FB0  # (0x160 bytes) next_card cls0 +04: pick -> SS DEF -> Yes/No loop (Giant Germ shape).
# Dragon Rulers family (dragon_rulers).
# Prefix CAVE_RUL_ (NOT CAVE_DR_ -- that prefix is dragunity_remus').
CAVE_RUL_CRIT    = 0x023A6110  # (0xE0 bytes) dragon_rulers: virtual criteria row handler (mode switch on the acting desc)
CAVE_RUL_KBASE   = 0x023A61F0  # (0x20 bytes) dragon_rulers: (cid) -> ROWS + k*0x40 or 0
CAVE_RUL_ATTR    = 0x023A6210  # (0x20 bytes) dragon_rulers: (cid) -> ruler attribute
CAVE_RUL_FILT    = 0x023A6230  # (0xC0 bytes) dragon_rulers: C1 banish / baby discard builder filter
CAVE_RUL_COUNT   = 0x023A62F0  # (0x100 bytes) dragon_rulers: hand/GY attr-or-Dragon counts
CAVE_RUL_MASK    = 0x023A63F0  # (0xD0 bytes) dragon_rulers: C1/C3 legality mask
CAVE_RUL_CONDH   = 0x023A64C0  # (0x40 bytes) dragon_rulers: HAND record +0C
CAVE_RUL_CONDG   = 0x023A6500  # (0x50 bytes) dragon_rulers: GY record +0C
CAVE_RUL_CONDB   = 0x023A6550  # (0x40 bytes) dragon_rulers: BAN record +0C
CAVE_RUL_CONDEP  = 0x023A6590  # (0x40 bytes) dragon_rulers: EP cls1 record +0C (opp turn + zone bit 4)
CAVE_RUL_COST    = 0x023A65D0  # (0x200 bytes) dragon_rulers: HAND/GY +10 prompt / banish / discard machine
CAVE_RUL_RESH    = 0x023A67D0  # (0x40 bytes) dragon_rulers: HAND +04 dispatch (PARAMS res)
CAVE_RUL_TGTH    = 0x023A6810  # (0x40 bytes) dragon_rulers: HAND +14 (PARAMS tgt)
CAVE_RUL_RESB    = 0x023A6850  # (0x50 bytes) dragon_rulers: BAN +04 OPT stamp + Deck->hand
CAVE_RUL_SUMLIST = 0x023A68A0  # (0x50 bytes) RETIRED before shipping (dragon_rulers: the babies' can't-attack moved to cave3 CAVE3_RUL_PC* prechecks); never in a shipped ROM.
CAVE_RUL_VREC    = 0x023A68F0  # (0x300 bytes) dragon_rulers: DATA: 4 virtual records x 8 rulers (k-indexed; babies use HAND only)
CAVE_RUL_ROWS    = 0x023A6BF0  # (0x200 bytes) dragon_rulers: DATA: per ruler 4 virtual criteria rows + PARAMS (0x40 x 8)
CAVE_RUL_GYROWS  = 0x023A6DF0  # (0x60 bytes) dragon_rulers: DATA: virtual GY-action rows (big rulers)
CAVE_RUL_GYFETCH = 0x023A6E50  # (0x20 bytes) dragon_rulers: GY enumerator row fetch (site 0x0224C88E)
CAVE_RUL_GYEXIT  = 0x023A6E70  # (0x20 bytes) dragon_rulers: GY enumerator loop exit (site 0x0224C9A0)
CAVE_RUL_GYPOST  = 0x023A6E90  # (0x60 bytes) dragon_rulers: GY post-by-cid exit (site 0x0224CD34)
CAVE_RUL_GYHAS   = 0x023A6EF0  # (0x50 bytes) dragon_rulers: GY has-row exit (site 0x0224CD60)
CAVE_RUL_SLOT2   = 0x023A6F40  # (0x40 bytes) dragon_rulers: HAND +08 mode-aware board filter (C3 only; BUILD 3)
# Sekka's Light on Stop Defense 0x10E6 (sekkas_light; notes/sekkas-light-findings.md). Card-only stubs (reached via its own cls0/cls2 records); the C3 lock
# front lives in cave3 (CAVE3_SEKKA_LOCK). C4 also REWRITES the CAVE_RUL_GY* stubs above (+1 virtual row).
CAVE_SEKKA_COND   = 0x023A6F80  # (0xA0 bytes) sekkas_light cls0 +0C: OPT kind 1 + no S/T in own GY + can draw 2
CAVE_SEKKA_COST   = 0x023A7020  # (0x40 bytes) sekkas_light cls0 +10: post kind 1 (OPT) + kind 5 (duel-long lock)
CAVE_SEKKA_RES    = 0x023A7060  # (0x20 bytes) sekkas_light cls0 +04: draw 2
CAVE_SEKKA_HASMON = 0x023A7080  # (0x50 bytes) sekkas_light (side) -> own hand holds a monster
CAVE_SEKKA_GYCOND = 0x023A70D0  # (0x40 bytes) sekkas_light cls2 +0C: OPT kind 2 + monster in hand
CAVE_SEKKA_GYCOST = 0x023A7110  # (0x40 bytes) sekkas_light cls2 +10: banish self 0x021E5709 + post kind 2
CAVE_SEKKA_CB     = 0x023A7150  # (0x50 bytes) sekkas_light 0x0224B9F0 filter: own hand + monster -> 0x800
CAVE_SEKKA_GYRES  = 0x023A71A0  # (0x100 bytes) sekkas_light cls2 +04: pick, reveal, hand->Deck, shuffle, draw 1
# Fire Formation - Tenki on Marshmallon Glasses 0x1777 (fire_formation_tenki; notes/fire-formation-tenki-findings.md).
# TENKI_ROW must sit at CAVE_RUL_ROWS + k*0x40 (Rulers' H3 formula,
# k = 27 -> virtual criteria index 0x5B00), so 0x023A72A0..0x023A72AF is an alignment hole, left zero.
CAVE_TENKI_ROW    = 0x023A72B0  # (0x10 bytes) fire_formation_tenki DATA: virtual criteria row {0x1777, 0xFFFF, 0x0223CAD9, 0x60900002}
CAVE_TENKI_COND   = 0x023A72C0  # (0x40 bytes) fire_formation_tenki cls0 +0C: menu check = OPT kind 1 not posted
CAVE_TENKI_COST   = 0x023A7300  # (0x40 bytes) fire_formation_tenki cls0 +10: post OPT kind 1 at activation
CAVE_TENKI_RES    = 0x023A7340  # (0x60 bytes) fire_formation_tenki cls0 +04: candidate? Yes/No 0xFA -> 0x02207EF5
# Sacred Sword of Seven Stars on Block Attack 0x130A (sacred_sword_seven_stars; notes/sacred-sword-of-seven-stars-findings.md).
# SSS_ROW must sit at CAVE_RUL_ROWS + k*0x40 (Rulers' H3 formula,
# k = 31 -> virtual criteria index 0x5F00), so 0x023A73A0..0x023A73AF is an alignment hole, left zero.
CAVE_SSS_ROW      = 0x023A73B0  # (0x10 bytes) sacred_sword_seven_stars DATA: virtual criteria row {0x130A, 0xFFFF, HANDLER, 0x001C0002}
CAVE_SSS_HANDLER  = 0x023A73C0  # (0x80 bytes) sacred_sword_seven_stars criteria handler: hand Lv7 + face-up field current-Lv7
CAVE_SSS_COND     = 0x023A7440  # (0x60 bytes) sacred_sword_seven_stars cls0 +0C: OPT kind 1 + candidate + can draw 2
CAVE_SSS_COST     = 0x023A74A0  # (0xE0 bytes) sacred_sword_seven_stars cls0 +10: post OPT, pick 1, banish hand/field
CAVE_SSS_RES      = 0x023A7580  # (0x20 bytes) sacred_sword_seven_stars cls0 +04: draw 2
# Dragon Rulers C4 from the FIELD (dragon_rulers H8; notes/dragon-rulers-field-banish-findings.md). Reached only for ruler cids (cave3 CAVE3_RUL_H8A tests first).
CAVE_RUL_LEAVE   = 0x023A75A0  # (0x20 bytes) dragon_rulers: H8 body: leave dest 0xF -> CAVE_RUL_LVROW, else 0
CAVE_RUL_LVROW   = 0x023A75C0  # (0x10 bytes) dragon_rulers: DATA: virtual leave-mask row {0, 0x0004 left the field}
# Eclipse Wyvern C1 LIGHT/DARK filter (eclipse_wyvern PART C2; notes/eclipse-wyvern-attr-findings.md). Reached only through EW's own criteria row.
CAVE_EW_ATTRH    = 0x023A75D0  # (0x30 bytes) eclipse_wyvern: criteria handler = 0x0223CAD9 + attr-mask callback 0x0223C8DD, mask 6
# Shared virtual GY-action rows (gy_vrow_hook.py): Rulers' full 6-row table, lifted.
# The four GY sites (rod.GY_SITES) point at these; Rulers' table/stubs are unused.
CAVE_GYV_ROWS    = 0x023A7600  # (0x100 bytes) gy_vrow_hook: DATA: 16 virtual GY-action rows (row 60 = Revolution)
CAVE_GYV_FETCH   = 0x023A7700  # (0x20 bytes) gy_vrow_hook: enumerator row fetch (site 0x0224C88E)
CAVE_GYV_EXIT    = 0x023A7720  # (0x20 bytes) gy_vrow_hook: enumerator loop exit (site 0x0224C9A0)
CAVE_GYV_POST    = 0x023A7740  # (0xC0 bytes) gy_vrow_hook: GY post-by-cid exit (site 0x0224CD34)
CAVE_GYV_HAS     = 0x023A7800  # (0xB0 bytes) gy_vrow_hook: GY has-row exit (site 0x0224CD60)
# Infernoble Knights family (infernoble; notes/infernoble-ogier-findings.md). EQFILT / PROT live in the larger slots below.
CAVE_IK_O_SLOT5  = 0x023A78B0  # (0x20 bytes) infernoble: Oliver cls2 +14: hand -> 1 (no target) / Vylon 0x02234D81
CAVE_IK_O_RES    = 0x023A78D0  # (0x20 bytes) infernoble: Oliver cls2 +04: hand -> O_C2RES / Vylon 0x02210961
CAVE_IK_O_FILT   = 0x023A78F0  # (0x20 bytes) infernoble: Oliver cls2 +08: hand -> O_FIELD / Vylon 0x021D8465
CAVE_IK_O_HANDH  = 0x023A7910  # (0x30 bytes) infernoble: Oliver C2 hand criteria handler: worker 0x0223BFD4 mode 0x11 + HANDCB
CAVE_IK_C3F2     = 0x023A7950  # (0x30 bytes) infernoble: Ogier C3 ignition-row f2: OPT kind 1 then Vylon f2 0x022043F5
CAVE_IK_C3COST   = 0x023A7980  # (0x20 bytes) infernoble: Ogier C3 cls2 +10: post OPT (side, 0x13A3, 1), return 1
CAVE_IK_C2H      = 0x023A79A0  # (0x30 bytes) infernoble: Ogier C2 criteria handler = 0x0223CAD9 + exclude-cid callback
CAVE_IK_C2CB     = 0x023A79D0  # (0x20 bytes) infernoble: Ogier C2 per-candidate callback: cid != [sp+4]
CAVE_IK_C2COND   = 0x023A79F0  # (0x30 bytes) infernoble: Ogier C2 cls1 +0C: OPT key 0x53A3 then Armageddon's 0x021F0B19
CAVE_IK_C2SLOT4  = 0x023A7A20  # (0x30 bytes) infernoble: Ogier C2 cls1 +10: "You can" 0x021E51E5, on 1 post OPT key 0x53A3
# Infernoble Knight Maugis (infernoble; notes/infernoble-maugis-findings.md).
# ONE cls2 record, slots switched on desc[+3] == 0x0E && desc[+4] > 6 (C2 sent-to-GY trigger) vs GY ignition (C3).
CAVE_IK_M_RES    = 0x023A7A50  # (0x20 bytes) infernoble: Maugis cls2 +04 dispatch: C2RES / Vylon 0x02210961
CAVE_IK_M_FILT   = 0x023A7A70  # (0x20 bytes) infernoble: Maugis cls2 +08 dispatch: C2 -> 0 / Vylon 0x021D8465
CAVE_IK_M_COND   = 0x023A7A90  # (0x60 bytes) infernoble: Maugis cls2 +0C: C2 OPT 0x539A + >= 3 candidates -> 2 / 0x021F0BDD
CAVE_IK_M_SLOT4  = 0x023A7AF0  # (0x50 bytes) infernoble: Maugis cls2 +10: C2 "You can" + post 0x539A / C3 post 0x139A, 1
CAVE_IK_M_SLOT5  = 0x023A7B40  # (0x30 bytes) infernoble: Maugis cls2 +14: C2 slot5 0x02235700 replay r4 = 9 (3 targets) / Vylon 0x02234D81
CAVE_IK_M_C2RES  = 0x023A7B70  # (0x120 bytes) infernoble: Maugis C2 resolver = 0x0221FB94 phases with GY-OR-banished targets
CAVE_IK_M_C2H    = 0x023A7C90  # (0x40 bytes) infernoble: Maugis C2 criteria handler: GY worker + banished worker, exclude 0x139A
CAVE_IK_M_C3F2   = 0x023A7CD0  # (0x30 bytes) infernoble: Maugis C3 ignition-row f2: OPT 0x139A then Vylon f2 0x022043F5
CAVE_IK_M_BATTLE = 0x023A7D00  # (0x60 bytes) infernoble: Mist Body query front (site 0x021984C8): || Maugis-equipped
# Infernoble Knight Oliver (infernoble; notes/infernoble-oliver-findings.md)
CAVE_IK_EQFILT   = 0x023A7D60  # (0x80 bytes) infernoble: equip-target switch 0x021D7348 front (site 0x021D73A0): Warrior you control (Ogier/Maugis/Oliver)
CAVE_IK_PROT     = 0x023A7DE0  # (0xA0 bytes) infernoble: affect predicate 0x021B021C split (site 0x021B059C): Ogier-equipped / Oliver-equipped+opp target
CAVE_IK_O_FIELD  = 0x023A7E80  # (0x70 bytes) infernoble: Oliver C2 field-cost +08: yours, face-up; MZ FIRE Warrior / S-T Equip Spell or FIRE Warrior
CAVE_IK_O_COND   = 0x023A7EF0  # (0x80 bytes) infernoble: Oliver cls2 +0C: hand -> OPT 0x5E04 + free MZ + a hand or field cost / 0x021F0BDD
CAVE_IK_O_COST   = 0x023A7F70  # (0x100 bytes) infernoble: Oliver cls2 +10: hand -> Hands/Field prompt, delegate 0x021E7245 / 0x021E712D; C3 post OPT
CAVE_IK_O_C2RES  = 0x023A8070  # (0x90 bytes) infernoble: Oliver C2 resolver: OPT stamp + hand self-SS 0x02206ABD + Level SET 1 rider
CAVE_IK_O_C3F2   = 0x023A8100  # (0x30 bytes) infernoble: Oliver C3 ignition-row f2: OPT 0x1E04 then Vylon f2 0x022043F5
CAVE_IK_O_HANDCB = 0x023A8130  # (0x60 bytes) infernoble: Oliver C2 hand-cost callback: != 0x1E04 && (FIRE Warrior || Equip Spell)
CAVE_IK_O_HANDANY = 0x023A8190  # (0x40 bytes) infernoble: Oliver: any hand index i with 0x02243FE0(side, cid, i) (BUILD 5 fix)
# Infernoble Knight Turpin (infernoble; notes/infernoble-turpin-findings.md)
CAVE_IK_T_ARM    = 0x023A81D0  # (0x10 bytes) infernoble: Turpin one-shot "banish when it leaves" byte (summon_rider_hook arm)
CAVE_IK_T_RES    = 0x023A81E0  # (0x40 bytes) infernoble: Turpin cls2 +04: hand -> HANDRES; GY mode 1 -> GYSS, else EQRES
CAVE_IK_T_FILT   = 0x023A8220  # (0x30 bytes) infernoble: Turpin cls2 +08: hand / GY mode 1 -> 0; else Vylon 0x021D8465
CAVE_IK_T_EQX    = 0x023A8250  # (0x60 bytes) infernoble: Turpin: (desc) -> 1 iff a monster of desc[+2]'s is equipped with an Equip Card
CAVE_IK_T_LEGAL  = 0x023A82B0  # (0x80 bytes) infernoble: Turpin: (desc) -> bit0 C2 SS legal, bit1 C3 equip legal (GY) / bit0 (hand)
CAVE_IK_T_COND   = 0x023A8330  # (0x30 bytes) infernoble: Turpin cls2 +0C: GY resets mode; LEGAL != 0 -> 2
CAVE_IK_T_COST   = 0x023A8360  # (0x90 bytes) infernoble: Turpin cls2 +10: GY "Use which effect?" (0x103 / 0x19F / 0x1A1) -> mode
CAVE_IK_T_SLOT5  = 0x023A83F0  # (0x30 bytes) infernoble: Turpin cls2 +14: GY mode 2 -> Vylon slot5; else 1
CAVE_IK_T_HANDRES = 0x023A8420  # (0x50 bytes) infernoble: Turpin C2 hand: OPT 0x4FC1 check+stamp, native hand self-SS 0x02206ABD
CAVE_IK_T_GYSS   = 0x023A8470  # (0x70 bytes) infernoble: Turpin C2 GY: OPT 0x4FC1, chain push, arm byte, 0x0220731D, chain pop
CAVE_IK_T_EQRES  = 0x023A84E0  # (0x50 bytes) infernoble: Turpin C3: OPT 0x0FC1 check+stamp at 0x80, Vylon resolver 0x02210961
CAVE_IK_T_H4     = 0x023A8530  # (0x20 bytes) infernoble: front of Rulers' ARM9 H4 (0x02023566): 0x0FC1 -> 1 (hand offer), else CAVE3_RUL_H4
CAVE_IK_T_TUNER  = 0x023A8550  # (0x60 bytes) infernoble: front of Partisan's 0x021A09BC @0x021A1D06: || equipped with 0x0FC1
# Infernoble Knight - Renaud (infernoble; notes/infernoble-renaud-findings.md)
CAVE_C9TRIG      = 0x023A85B0  # (0x30 bytes) c9_trigger_hook.py: the SHARED plain-SS trigger stub (site 0x022658BC)
CAVE_IK_R_ARM    = 0x023A85E0  # (0x10 bytes) infernoble: Renaud one-shot "summoned by the procedure" byte (rider LATCH arm)
CAVE_IK_R_SSCOND = 0x023A85F0  # (0x90 bytes) infernoble: Renaud hand-SS procedure cond: can SS, free MZ, OPT, face-up FIRE Warrior; arms the byte
CAVE_IK_R_COND   = 0x023A8680  # (0x50 bytes) infernoble: Renaud C3 cls1 +0C: OPT 0x5E05 + >= 1 criteria candidate -> 2
CAVE_IK_R_RES    = 0x023A86D0  # (0x50 bytes) infernoble: Renaud C3 cls1 +04: OPT stamp at 0x80, add-target-to-hand 0x02208181
CAVE_IK_R_C3H    = 0x023A8720  # (0x40 bytes) infernoble: Renaud C3 criteria handler: GY + banished workers, Oliver's HANDCB
CAVE_IK_R_LATCH  = 0x023A8760  # (0x50 bytes) infernoble: Renaud rider front at the summon-event leaf: byte && source 0x1E05 -> attach 0x1E40; else CAVE_RIDERLATCH
CAVE_IK_RC_ARM   = 0x023A87B0  # (0x10 bytes) infernoble: Ricciardetto C1 one-shot "summoned by C1" byte (Tuner latch)
CAVE_IK_RC_COND  = 0x023A87C0  # (0x70 bytes) infernoble: Ricciardetto C1 cls2 +0C (hand / GY): OPT, f1, hand>=2 | f2
CAVE_IK_RC_COST  = 0x023A8830  # (0x50 bytes) infernoble: Ricciardetto C1 cls2 +10: banish self (GY native / hand)
CAVE_IK_RC_RES   = 0x023A8880  # (0x60 bytes) infernoble: Ricciardetto C1 cls2 +04: OPT stamp + arm byte, hand SS 0x0220667D
CAVE_IK_RC_C2CND = 0x023A88E0  # (0x30 bytes) infernoble: Ricciardetto C2 cls1 +0C: OPT -> Junk Synchron's 0x021F03B5
CAVE_IK_RC_C2RES = 0x023A8910  # (0x70 bytes) infernoble: Ricciardetto C2 cls1 +04: OPT + Warrior lock post, revive 0x02207191
CAVE_IK_RC_C2H   = 0x023A8980  # (0x30 bytes) infernoble: Ricciardetto C2 criteria handler: GY worker, excl 0x0FE6
CAVE_IK_RC_LOCK  = 0x023A89B0  # (0x40 bytes) infernoble: Ricciardetto front @0x021BA368 (-> Obedience LOCK): Warrior-only SS
CAVE_IK_RC_LATCH = 0x023A89F0  # (0x50 bytes) infernoble: Ricciardetto rider front: byte && source 0x0FE6 -> 0x1E40; else Renaud's
CAVE_IK_RC_ROW   = 0x023A8A40  # (0x40 bytes) infernoble: Ricciardetto front @0x02243BEC (criteria row hook): cls1 -> rel 1; else CAVE_ROWHOOK
CAVE_IK_RO_RES   = 0x023A8A80  # (0x90 bytes) infernoble: Roland cls2 +04: hand -> C1 OPT + Vylon equip 0x02210961; GY -> C2 OPT + add 0x02207EF5
CAVE_IK_RO_FILT  = 0x023A8B10  # (0x20 bytes) infernoble: Roland cls2 +08: hand -> Vylon filter 0x021D8465; else 0
CAVE_IK_RO_COND  = 0x023A8B30  # (0xB0 bytes) infernoble: Roland cls2 +0C: hand C1 (OPT, f1, f2); GY ev 6 = C2 (OPT, Deck count); GY ev > 6 = post sent-this-turn node
CAVE_IK_RO_COST  = 0x023A8BE0  # (0x20 bytes) infernoble: Roland cls2 +10: hand -> 1; GY -> "You can" 0x021E51E5
CAVE_IK_RO_SLOT5 = 0x023A8C00  # (0x20 bytes) infernoble: Roland cls2 +14: hand -> Vylon slot5 0x02234D81; else 1
CAVE_IK_RO_C2H   = 0x023A8C20  # (0x30 bytes) infernoble: Roland C2 criteria handler: Deck worker + Oliver's HANDCB excl 0x0FDB
CAVE_IK_RO_H4    = 0x023A8C50  # (0x40 bytes) infernoble: ARM9 H4 front (LIST B): Turpin / Ricciardetto / Roland / Astolfo -> 1, else Rulers' CAVE3_RUL_H4
CAVE_IK_AS_COND  = 0x023A8C90  # (0x100 bytes) infernoble: Astolfo cls2 +0C: hand C1 / GY C2 activation / banished C2 return (event 2)
CAVE_IK_AS_COST  = 0x023A8D90  # (0x20 bytes) infernoble: Astolfo cls2 +10: hand -> AS_COSTM; GY -> Stygian banish-self 0x021E5709; else 1
CAVE_IK_AS_RES   = 0x023A8DB0  # (0x30 bytes) infernoble: Astolfo cls2 +04: zone switch -> C1RES / C2ACT / C2RET
CAVE_IK_AS_COSTM = 0x023A8DE0  # (0xE0 bytes) infernoble: Astolfo C1 cost: message, picker (hand+GY FIRE Warrior), banish; ref/Level -> desc+0x1C/+0x1E
CAVE_IK_AS_C1RES = 0x023A8EC0  # (0xC0 bytes) infernoble: Astolfo C1 resolver: once-per-Duel 0x4FD4, hand self-SS 0x02206ABD, Yes/No -> Level SET rider
CAVE_IK_AS_C2ACT = 0x023A8F80  # (0x50 bytes) infernoble: Astolfo C2 activation resolver: once-per-Duel 0x2FD4 + return node {0x0FD4, 0x41, ref}
CAVE_IK_AS_C2RET = 0x023A8FD0  # (0x130 bytes) infernoble: Astolfo C2 return (2nd Standby): SS from banished, Yes/No, pick + SS a FIRE Warrior (GY/banished)
CAVE_IK_AS_CRIT  = 0x023A9100  # (0xA0 bytes) infernoble: Astolfo criteria handler: hand desc -> hand+GY builders; else GY+banished workers
CAVE_IK_AS_FILT  = 0x023A91A0  # (0x60 bytes) infernoble: Astolfo candidate callback: FIRE Warrior; hand mode excludes this card BY REF
CAVE_IK_BR_COND  = 0x023A9200  # (0x100 bytes) infernoble: Bradamante cls2 +0C: hand C1 (OPT, Equip Spell in Deck, free S/T, target) / GY C2 (OPT, not-equipped marker, room) -> 1
CAVE_IK_BR_COST  = 0x023A9300  # (0x20 bytes) infernoble: Bradamante cls2 +10: hand -> discard-self 0x021E6FD9; GY -> 'You can' 0x021E51E5
CAVE_IK_BR_FILT  = 0x023A9320  # (0x20 bytes) infernoble: Bradamante cls2 +08: hand -> Vylon filter (EQFILT Warrior arm); GY -> BR_FIST
CAVE_IK_BR_SLOT5 = 0x023A9340  # (0x20 bytes) infernoble: Bradamante cls2 +14: hand -> 0x02234D8D (Pilus msg); GY -> 0x02234D99 (Allure msg)
CAVE_IK_BR_RES   = 0x023A9360  # (0x20 bytes) infernoble: Bradamante cls2 +04: hand -> BR_C1RES; GY -> BR_C2RES
CAVE_IK_BR_C1RES = 0x023A9380  # (0x60 bytes) infernoble: Bradamante C1 resolver: OPT 0x560B at 0x80 -> Sigma/Pilus equip-from-Deck 0x0222DC49
CAVE_IK_BR_C2RES = 0x023A93E0  # (0xC0 bytes) infernoble: Bradamante C2 resolver: OPT 0x360B, GY self-SS 0x0220731D, re-point desc[+3], Allure equip 0x0220BFFD
CAVE_IK_BR_FIST  = 0x023A94A0  # (0x40 bytes) infernoble: Bradamante C2 +08: Fist's 'the monster it battled' (prologue + 0x021E1577) and opponent-side only
CAVE_IK_BR_CRIT  = 0x023A94E0  # (0x50 bytes) infernoble: Bradamante criteria handler: Deck worker + legality callback 0x0223E395 vs the declared target's location
CAVE_IK_BR_LEAVE = 0x023A9530  # (0xB0 bytes) infernoble: Bradamante front @0x021C8216 (leave switch): 0x160B destroyed by battle -> 'was equipped' marker; -> T.G. arm trampoline
CAVE_IK_BR_CIDA  = 0x023A95E0  # (0x20 bytes) infernoble: Bradamante front @0x0222DC50: Z iff r2 in {0x2170, 0x160B} (Pilus target branch)
CAVE_IK_BR_CIDB  = 0x023A9600  # (0x20 bytes) infernoble: Bradamante front @0x0222DCBE: Z iff r1 in {0x2170, 0x160B}
CAVE_IK_CR_FRONT = 0x023A9620  # (0x20 bytes) infernoble: Captain Roland front @0x02265900 (proper-Summon trigger): 0x0FEB -> member path, else the shared cave3 stub
CAVE_IK_CR_COND1 = 0x023A9640  # (0x40 bytes) infernoble: Captain Roland cls1 +0C (Synchro Summoned trigger): OPT 0x4FEB clear -> 2
CAVE_IK_CR_RES1  = 0x023A9680  # (0x60 bytes) infernoble: Captain Roland cls1 +04: OPT 0x4FEB stamp + End-Phase node {0x0FEB, kind 1, ref} (Into the Void's machinery)
CAVE_IK_CR_COND2 = 0x023A96E0  # (0x20 bytes) infernoble: Captain Roland cls2 +0C: zone 0x10 && event 6 (End-Phase rider walker) -> 2, else 0
CAVE_IK_CR_RES2  = 0x023A9700  # (0x80 bytes) infernoble: Captain Roland cls2 +04: stage 0 send Equip Spell Deck->GY (0x02208DD5), stage 1 add Warrior Deck->hand (0x02207EF5)
CAVE_IK_CR_CRIT  = 0x023A9780  # (0x40 bytes) infernoble: Captain Roland criteria handler: Deck worker + CR_CB (stage from the acting desc)
CAVE_IK_CR_CB    = 0x023A97C0  # (0x60 bytes) infernoble: Captain Roland Deck candidate callback: stage 0 Equip Spell / stage 1 Warrior monster
CAVE_IK_CR_RESW  = 0x023A9820  # (0x20 bytes) infernoble: Captain Roland cls2 +04: zone 0xE -> CR_C2RES; else CR_RES2 (End Phase)
CAVE_IK_CR_FILT  = 0x023A9840  # (0x20 bytes) infernoble: Captain Roland cls2 +08: zone 0xE -> Vylon filter (EQFILT Warrior arm); else 0
CAVE_IK_CR_CONDX = 0x023A9860  # (0x80 bytes) infernoble: Captain Roland cls2 +0C: zone 0x10 -> CR_COND2; zone 0xE event 0 -> C2 (Main Phase, OPT, Vylon f1 / f2) -> 1
CAVE_IK_CR_SLOT5 = 0x023A98E0  # (0x20 bytes) infernoble: Captain Roland cls2 +14: zone 0xE -> Vylon slot5 0x02234D81; else 1
CAVE_IK_CR_C2RES = 0x023A9900  # (0x50 bytes) infernoble: Captain Roland C2 resolver: OPT 0x2FEB at 0x80 -> equip-this-card-from-GY 0x02210961
CAVE_IK_CR_SPEED = 0x023A9950  # (0x20 bytes) infernoble: Captain Roland front @0x021A894C (speed default leaf): 0x0FEB GY desc -> 2 (Quick Effect); else CAVE_OQ_SPEED
CAVE_IK_CR_SPD9  = 0x023A9970  # (0x20 bytes) infernoble: Captain Roland front @0x0224C8AC / @0x0224C8E4 (GY enumerator's native-speed prefilter 0x0202345C): 0x0FEB -> 2, else the native
CAVE_IK_CO_ARM    = 0x023A9990  # (0x10 bytes) infernoble: Captain Oliver one-shot 'summoned by C2' byte (Tuner latch)
CAVE_IK_CO_C1COND = 0x023A99A0  # (0x60 bytes) infernoble: Captain Oliver cls1 +0C (attack declared): an Equip Card is equipped to this card -> 1
CAVE_IK_CO_C2COND = 0x023A9A00  # (0xA0 bytes) infernoble: Captain Oliver cls2 +0C (GY): own Main Phase, OPT 0x3118, not sent this turn, may SS, free MZ + S/T -> 1
CAVE_IK_CO_C2RES  = 0x023A9AA0  # (0xC0 bytes) infernoble: Captain Oliver cls2 +04: OPT, arm latch byte, GY self-SS, re-point desc, Allure equip 0x0220BFFD
CAVE_IK_CO_C2FILT = 0x023A9B60  # (0x50 bytes) infernoble: Captain Oliver cls2 +08: a face-up Warrior you control
CAVE_IK_CO_LATCH  = 0x023A9BB0  # (0x50 bytes) infernoble: Captain Oliver rider front: byte && source 0x1118 -> 0x1E40 Tuner; else Ricciardetto's front
CAVE_IK_CO_LEAVE  = 0x023A9C00  # (0x50 bytes) infernoble: Captain Oliver front @0x021C8216: 0x1118 leaving to the GY -> 'sent this turn' marker 0x7118; else Bradamante's
CAVE_IK_CO_STAT   = 0x023A9C50  # (0x60 bytes) infernoble: Captain Oliver front @0x021B7088 (equip bonus): holder 0x1118 + a MONSTER equip card -> +500 ATK
CAVE_IK_CH_EQ    = 0x023A9CB0  # (0x50 bytes) infernoble: Emperor Charles front @0x021C4B4E (equip routine cid compare): post cls1 event 0x19 to every face-up 0x17EF
CAVE_IK_CH_COND  = 0x023A9D00  # (0x80 bytes) infernoble: Emperor Charles cls1 +0C: event 0x19 C1 OPT / event 6 C2 OPT + free S/T + >= 1 Equip Spell -> 2
CAVE_IK_CH_FILT  = 0x023A9D80  # (0x20 bytes) infernoble: Emperor Charles cls1 +08: event 0x19 -> Dark Voltanis's card filter 0x021DE5A9, else 0
CAVE_IK_CH_SLOT5 = 0x023A9DA0  # (0x20 bytes) infernoble: Emperor Charles cls1 +14: event 0x19 -> target step 0x02234DA5, else 1 (skip)
CAVE_IK_CH_RESW  = 0x023A9DC0  # (0x60 bytes) infernoble: Emperor Charles cls1 +04: event 0x19 -> C1 OPT stamp + destroy 0x02204899; else the C2 machine
CAVE_IK_CH_C2RES = 0x023A9E20  # (0x1c0 bytes) infernoble: Emperor Charles C2: Sigma's pick/zone/move/link machine, hand-or-GY Equip Spell then Deck FIRE Warrior
CAVE_IK_CH_CRIT  = 0x023A9FE0  # (0x70 bytes) infernoble: Emperor Charles criteria handler: hand+GY appropriate Equip Spells / Deck FIRE Warriors (param bit 16)
CAVE_IK_AN_COND1 = 0x023AA050  # (0x80 bytes) infernoble: Angelica cls1 +0C: event 0x13 C2 OPT + FIRE Warrior in Deck / else C1 OPT + searchable card -> 2
CAVE_IK_AN_COND3 = 0x023AA0D0  # (0x60 bytes) infernoble: Angelica cls3 +0C: C2 OPT + FIRE Warrior in Deck + 0x021F8135 (activation targets this card)
CAVE_IK_AN_RES1  = 0x023AA130  # (0x60 bytes) infernoble: Angelica cls1 +04: event 0x13 -> C2 machine; else C1 OPT stamp + Deck add 0x02207EF5
CAVE_IK_AN_C2RES = 0x023AA190  # (0x280 bytes) infernoble: Angelica C2: send FIRE Warrior, banish self until EP (IMT encoding + node), Yes/No SS a Roland
CAVE_IK_AN_CRIT  = 0x023AA410  # (0x90 bytes) infernoble: Angelica criteria handler: mode 0 search set / 1 Deck FIRE Warriors / 2 Deck+Extra Rolands
CAVE_IK_AN_SRCHCB= 0x023AA4A0  # (0x40 bytes) infernoble: Angelica C1 candidate callback: cid in AN_SEARCH
CAVE_IK_AN_ROLCB = 0x023AA4E0  # (0x30 bytes) infernoble: Angelica 'Roland' callback: 0x0FDB / 0x0FEB
CAVE_IK_HO_LEGAL  = 0x023AA510  # (0x90 bytes) infernoble: Horn of Olifant LEGAL
CAVE_IK_HO_COND   = 0x023AA5A0  # (0x40 bytes) infernoble: Horn of Olifant COND
CAVE_IK_HO_COST   = 0x023AA5E0  # (0xa0 bytes) infernoble: Horn of Olifant COST
CAVE_IK_HO_RES    = 0x023AA680  # (0x340 bytes) infernoble: Horn of Olifant RES
CAVE_IK_HO_CRIT   = 0x023AA9C0  # (0x140 bytes) infernoble: Horn of Olifant CRIT
CAVE_IK_HO_EQSPCB = 0x023AAB00  # (0x40 bytes) infernoble: Horn of Olifant EQSPCB
CAVE_IK_HO_HISTCB = 0x023AAB40  # (0x30 bytes) infernoble: Horn of Olifant HISTCB
CAVE_IK_HO_LVCB   = 0x023AAB70  # (0x80 bytes) infernoble: Horn of Olifant LVCB
CAVE_IK_HO_LOCK   = 0x023AABF0  # (0x40 bytes) infernoble: Horn of Olifant LOCK
CAVE_IK_HO_PRENEG = 0x023AAC30  # (0x20 bytes) infernoble: Horn of Olifant PRENEG
CAVE_IK_HO_PREPOST= 0x023AAC50  # (0x20 bytes) infernoble: Horn of Olifant PREPOST
CAVE_IK_JO_E1COND = 0x023AAC70  # (0x70 bytes) infernoble: Infernoble Arms - Joyeuse E1COND
CAVE_IK_JO_E1RES  = 0x023AACE0  # (0x90 bytes) infernoble: Infernoble Arms - Joyeuse E1RES
CAVE_IK_JO_E2COND = 0x023AAD70  # (0x40 bytes) infernoble: Infernoble Arms - Joyeuse E2COND
CAVE_IK_JO_E2RES  = 0x023AADB0  # (0x50 bytes) infernoble: Infernoble Arms - Joyeuse E2RES
CAVE_IK_JO_LEAVE  = 0x023AAE00  # (0x30 bytes) infernoble: Infernoble Arms - Joyeuse LEAVE
CAVE_IK_JO_ROW    = 0x023AAE30  # (0x40 bytes) infernoble: Infernoble Arms - Joyeuse ROW
CAVE_IK_DU_E1COND = 0x023AAE70  # (0x70 bytes) infernoble: Infernoble Arms - Durendal E1COND
CAVE_IK_DU_E1RES  = 0x023AAEE0  # (0x90 bytes) infernoble: Infernoble Arms - Durendal E1RES
CAVE_IK_DU_E2COND = 0x023AAF70  # (0x40 bytes) infernoble: Infernoble Arms - Durendal E2COND
CAVE_IK_DU_E2RES  = 0x023AAFB0  # (0x60 bytes) infernoble: Infernoble Arms - Durendal E2RES
CAVE_IK_DU_LEAVE  = 0x023AB010  # (0x30 bytes) infernoble: Infernoble Arms - Durendal LEAVE
CAVE_IK_DU_ROW    = 0x023AB040  # (0x40 bytes) infernoble: Infernoble Arms - Durendal ROW
CAVE_IK_AL_E1COND = 0x023AB080  # (0x90 bytes) infernoble: Infernoble Arms - Almace E1COND
CAVE_IK_AL_E1RES  = 0x023AB110  # (0x1e0 bytes) infernoble: Infernoble Arms - Almace E1RES
CAVE_IK_AL_E2COND = 0x023AB2F0  # (0x50 bytes) infernoble: Infernoble Arms - Almace E2COND
CAVE_IK_AL_E2RES  = 0x023AB340  # (0x50 bytes) infernoble: Infernoble Arms - Almace E2RES
CAVE_IK_AL_LEAVE  = 0x023AB390  # (0x30 bytes) infernoble: Infernoble Arms - Almace LEAVE
CAVE_IK_AL_CRIT   = 0x023AB3C0  # (0xd0 bytes) infernoble: Infernoble Arms - Almace CRIT
CAVE_IK_AL_ARMCB  = 0x023AB490  # (0x40 bytes) infernoble: Infernoble Arms - Almace ARMCB
CAVE_IK_AR_MISS  = 0x023AB4D0  # (0x40 bytes) infernoble: Infernoble Arms never-miss front @0x021EE10C (-> Maugis's ov3 front)
CAVE_IK_HA_E1COND = 0x023AB510  # (0x60 bytes) infernoble: Infernoble Arms - Hauteclere E1COND
CAVE_IK_HA_E1FILT = 0x023AB570  # (0x40 bytes) infernoble: Infernoble Arms - Hauteclere E1FILT
CAVE_IK_HA_E1RES  = 0x023AB5B0  # (0xa0 bytes) infernoble: Infernoble Arms - Hauteclere E1RES
CAVE_IK_HA_E2COND = 0x023AB650  # (0x40 bytes) infernoble: Infernoble Arms - Hauteclere E2COND
CAVE_IK_HA_E2FILT = 0x023AB690  # (0x40 bytes) infernoble: Infernoble Arms - Hauteclere E2FILT
CAVE_IK_HA_E2RES  = 0x023AB6D0  # (0x50 bytes) infernoble: Infernoble Arms - Hauteclere E2RES
CAVE_IK_HA_LEAVE  = 0x023AB720  # (0x30 bytes) infernoble: Infernoble Arms - Hauteclere LEAVE
CAVE_IK_HA_MISS   = 0x023AB750  # (0x20 bytes) infernoble: Infernoble Arms - Hauteclere MISS
CAVE_IK_AR_NACB  = 0x023AB770  # (0x60 bytes) infernoble: Ogier / Maugis C2 worker callback: not the excluded cid AND (an Infernoble Arms OR a FIRE Warrior monster)
CAVE_IK_MU_STAT   = 0x023AB7D0  # (0x20 bytes) infernoble: Noble Arms Museum STAT
CAVE_IK_MU_COND   = 0x023AB7F0  # (0xc0 bytes) infernoble: Noble Arms Museum COND
CAVE_IK_MU_FILT   = 0x023AB8B0  # (0x60 bytes) infernoble: Noble Arms Museum FILT
CAVE_IK_MU_COST   = 0x023AB910  # (0xa0 bytes) infernoble: Noble Arms Museum COST
CAVE_IK_MU_SLOT5  = 0x023AB9B0  # (0x20 bytes) infernoble: Noble Arms Museum SLOT5
CAVE_IK_MU_RES    = 0x023AB9D0  # (0x150 bytes) infernoble: Noble Arms Museum RES
CAVE_IK_MU_SPARE  = 0x023ABB20  # (0x40 bytes) infernoble: DEAD -- Museum's first CRITF slot, outgrown
CAVE_IK_MU_ARMCB  = 0x023ABB60  # (0x40 bytes) infernoble: Noble Arms Museum ARMCB
CAVE_IK_MU_KNCB   = 0x023ABBA0  # (0xa0 bytes) infernoble: Noble Arms Museum KNCB
CAVE_IK_EP_COND   = 0x023ABC40  # (0x70 bytes) infernoble: The Continuing Epic of Charles COND
CAVE_IK_EP_COST   = 0x023ABCB0  # (0x40 bytes) infernoble: The Continuing Epic of Charles COST
CAVE_IK_EP_RES    = 0x023ABCF0  # (0x220 bytes) infernoble: The Continuing Epic of Charles RES
CAVE_IK_EP_E2COND = 0x023ABF10  # (0x70 bytes) infernoble: The Continuing Epic of Charles E2COND
CAVE_IK_EP_E2FILT = 0x023ABF80  # (0x40 bytes) infernoble: The Continuing Epic of Charles E2FILT
CAVE_IK_EP_E2RES  = 0x023ABFC0  # (0x170 bytes) infernoble: The Continuing Epic of Charles E2RES
CAVE_IK_MU_CRITF  = 0x023AC130  # (0x80 bytes) infernoble: Noble Arms Museum CRITF (Almace-row front, modes 3..5; moved)
CAVE_DC_ROWS     = 0x023AC1B0  # (0x40 bytes) disguise_copycat: DATA: virtual criteria rows (0xFF00|j) j0 C2 row, j1 N2 row (+0xC excluded cid), j2 N2 scratch
CAVE_DC_C3_FILT  = 0x023AC1F0  # (0x50 bytes) disguise_copycat: Disguise C3 cls3 +08
CAVE_DC_C3_COND  = 0x023AC240  # (0x70 bytes) disguise_copycat: Disguise C3 cls3 +0C
CAVE_DC_C3_COST  = 0x023AC2B0  # (0x30 bytes) disguise_copycat: Disguise C3 cls3 +10
CAVE_DC_C3_RES   = 0x023AC2E0  # (0x90 bytes) disguise_copycat: Disguise C3 cls3 +04
CAVE_DC_C1_COND  = 0x023AC370  # (0xe0 bytes) disguise_copycat: Disguise C1 cls2 +0C (hand)
CAVE_DC_C1_RES   = 0x023AC450  # (0x50 bytes) disguise_copycat: Disguise C1 cls2 +04 (hand SS)
CAVE_DC_C2_COND  = 0x023AC4A0  # (0x30 bytes) disguise_copycat: Disguise C2 cls1 +0C
CAVE_DC_C2_SLOT4 = 0x023AC4D0  # (0x30 bytes) disguise_copycat: Disguise C2 cls1 +10 (You can + OPT)
CAVE_DC_H2       = 0x023AC500  # (0x30 bytes) disguise_copycat: 0x02243F24 front: 0x111E/0x10E3 -> 0xFF00/0xFF01, else previous front
CAVE_DC_H3       = 0x023AC530  # (0x30 bytes) disguise_copycat: 0x02243F62 front: index>>8 == 0xFF -> CAVE_DC_ROWS row, else previous
CAVE_DC_MISS     = 0x023AC560  # (0x20 bytes) disguise_copycat: 0x021EE10C never-miss front: 0x111E, else previous
CAVE_DC_H4       = 0x023AC580  # (0x20 bytes) disguise_copycat: ARM9 0x02023566 hand-offer front: 0x111E -> 1, else previous
CAVE_DC_N1_FRONT = 0x023AC5A0  # (0x40 bytes) disguise_copycat: 0x021B7088 stat front: equip 0x10E3 -> +200 x Equip Spells ATK/DEF
CAVE_DC_N1_COUNT = 0x023AC5E0  # (0xa0 bytes) disguise_copycat: Noble Arms N1 count (C)
CAVE_DC_N2_COND  = 0x023AC680  # (0xc0 bytes) disguise_copycat: Noble Arms N2 cls3 +0C
CAVE_DC_N2_COST  = 0x023AC740  # (0x30 bytes) disguise_copycat: Noble Arms N2 cls3 +10
CAVE_DC_N2_RES   = 0x023AC770  # (0x1b0 bytes) disguise_copycat: Noble Arms N2 cls3 +04 (Deck-SS wrapper)
CAVE_DC_N2_H     = 0x023AC920  # (0x30 bytes) disguise_copycat: Noble Arms N2 criteria handler (Deck worker + CB)
CAVE_DC_N2_CB    = 0x023AC950  # (0x20 bytes) disguise_copycat: Noble Arms N2 worker callback (cid != excluded)
CAVE_C79TRIG_OLD2 = 0x023AC970  # RETIRED (0x40 bytes) -- FULL at 4 arms; c79 stub re-homed to CAVE_C79TRIG 2026-11-06 (Predaplant Ophrys Scorpio, 5th arm = 68 B).
CAVE_C79TRIG     = 0x023ADA40  # (0x50 bytes) c79_trigger_hook.py: the SHARED N-or-SS trigger stub (site 0x02265C44); re-homed from 0x023AC970 when Ophrys added a 5th arm.
CAVE_MK_ROWS     = 0x023AC9B0  # (0x20 bytes) noble_knight_medraut: DATA: virtual criteria row (index 0xFF10) + scratch (+0x10 u16 target loc, +0x12 u8 MZ mask)
CAVE_MK_FILT     = 0x023AC9D0  # (0x60 bytes) noble_knight_medraut: cls3 +08 (own face-up Equip Spell, S/T 5..9)
CAVE_MK_COND     = 0x023ACA30  # (0x110 bytes) noble_knight_medraut: cls3 +0C
CAVE_MK_COST     = 0x023ACB40  # (0x30 bytes) noble_knight_medraut: cls3 +10 (OPT)
CAVE_MK_RES      = 0x023ACB70  # (0x100 bytes) noble_knight_medraut: cls3 +04 (Deck-SS wrapper + destroy)
CAVE_MK_ACT      = 0x023ACC70  # (0xc0 bytes) noble_knight_medraut: mk_active(side, zone) for the Level / attribute fronts
CAVE_MK_H        = 0x023ACD30  # (0x30 bytes) noble_knight_medraut: criteria handler (Deck worker + KNIGHT callback)
CAVE_MK_CB       = 0x023ACD60  # (0xc0 bytes) noble_knight_medraut: worker callback (cid in the Knight list, not Medraut)
CAVE_MK_H2       = 0x023ACE20  # (0x30 bytes) noble_knight_medraut: 0x02243F24 front (AHEAD of CAVE_DC_H2): 0x0FD9 -> 0xFF10
CAVE_MK_H3       = 0x023ACE50  # (0x30 bytes) noble_knight_medraut: 0x02243F62 front (AHEAD of CAVE_DC_H3): index 0xFF10 -> CAVE_MK_ROWS
CAVE_MK_LVL      = 0x023ACE80  # (0x30 bytes) noble_knight_medraut: Level getter 0x021B88BA front (+1 while active)
CAVE_MK_ATTR     = 0x023ACEB0  # (0x40 bytes) noble_knight_medraut: attribute getter 0x021B927E front (DARK while active)
CAVE_MK_POS      = 0x023ACEF0  # (0x20 bytes) noble_knight_medraut: Deck-SS position 0x02206E70 front (Medraut -> Defense)
CAVE_GF_ROWS     = 0x023ACF10  # (0x20 bytes) immortal_phoenix_gearfried: DATA: virtual criteria row (index 0xFF20) for the C1 banish picker
CAVE_GF_C1_COND  = 0x023ACF30  # (0xd0 bytes) immortal_phoenix_gearfried: hand cls2 +0C (virtual record)
CAVE_GF_C1_RES   = 0x023AD000  # (0x40 bytes) immortal_phoenix_gearfried: hand cls2 +04 (OPT + native hand SS)
CAVE_GF_C1_COST  = 0x023AD040  # (0xc0 bytes) immortal_phoenix_gearfried: hand cls2 +10 banish cost machine (GY / field Equip Spell)
CAVE_GF_C1_H     = 0x023AD100  # (0x80 bytes) immortal_phoenix_gearfried: C1 criteria handler (GY builder + S/T recorder)
CAVE_GF_C1_PRED  = 0x023AD180  # (0x50 bytes) immortal_phoenix_gearfried: C1 GY builder predicate (Equip Spell)
CAVE_GF_C1_S5    = 0x023AD1D0  # (0x10 bytes) immortal_phoenix_gearfried: hand cls2 +14 (no target: return 1)
CAVE_GF_VREC     = 0x023AD1E0  # (0x30 bytes) immortal_phoenix_gearfried: DATA: virtual cls2 hand record (24 B)
CAVE_GF_H1       = 0x023AD210  # (0x30 bytes) immortal_phoenix_gearfried: find_event_handler miss-tail front 0x0224A86A (AHEAD of Dragon Rulers' H1)
CAVE_GF_H2       = 0x023AD240  # (0x20 bytes) immortal_phoenix_gearfried: 0x02243F24 front (AHEAD of Medraut's): 0x0FC7 -> 0xFF20
CAVE_GF_H3       = 0x023AD260  # (0x30 bytes) immortal_phoenix_gearfried: 0x02243F62 front (AHEAD of Medraut's): index 0xFF20 -> CAVE_GF_ROWS
CAVE_GF_H4       = 0x023AD290  # (0x20 bytes) immortal_phoenix_gearfried: ARM9 0x02023566 hand-offer front: 0x0FC7 -> 1
CAVE_GF_C2_FILT  = 0x023AD2B0  # (0x30 bytes) immortal_phoenix_gearfried: cls1 +08 any face-up monster except self
CAVE_GF_C2_COND  = 0x023AD2E0  # (0x90 bytes) immortal_phoenix_gearfried: cls1 +0C attacker, no monster equipped, OPT
CAVE_GF_C2_RES   = 0x023AD370  # (0x50 bytes) immortal_phoenix_gearfried: cls1 +04 OPT + Allure equip resolver
CAVE_GF_STAT     = 0x023AD3C0  # (0x40 bytes) immortal_phoenix_gearfried: 0x021B7088 stat front: holder 0x0FC7 + monster equip -> +500 ATK (AHEAD of Disguise's N1 front)
CAVE_GF_DMG      = 0x023AD400  # (0x20 bytes) immortal_phoenix_gearfried: start-of-Damage-Step poster front (AHEAD of Tyranno's M stub): 0x0FC7 -> hit leaf
CAVE_GF_C3_FILT  = 0x023AD420  # (0x50 bytes) immortal_phoenix_gearfried: cls3 +08 own face-up Equip Card in S/T 5..9 (Equip Spell or equipped monster)
CAVE_GF_C3_COND  = 0x023AD470  # (0x70 bytes) immortal_phoenix_gearfried: cls3 +0C monster-effect activation, OPT, Equip Card available
CAVE_GF_C3_COST  = 0x023AD4E0  # (0x40 bytes) immortal_phoenix_gearfried: cls3 +10 send Equip Card to GY (native field cost) + OPT
CAVE_PG_EQ       = 0x023AD520  # (0x40 bytes) phoenix_gearblade: equip-legality arm 0x021D7F66 stub: race Warrior (bit 15) OR attribute FIRE
CAVE_PG_C3_COND  = 0x023AD560  # (0x60 bytes) phoenix_gearblade: cls1 +0C C3 trigger condition (always offer)
CAVE_PG_C3_COST  = 0x023AD5C0  # (0x60 bytes) phoenix_gearblade: cls1 +10 'You can' prompt, then send this card to the GY (zeroed-cid mover)
CAVE_PG_C3_RES   = 0x023AD620  # (0xa0 bytes) phoenix_gearblade: cls1 +04 snapshot rider on each of your Warrior / FIRE monsters
CAVE_PG_EOD      = 0x023AD6C0  # (0x30 bytes) phoenix_gearblade: End-of-Damage-Step walker front @0x02252210: 0x10EA -> attacker-only post arm 0x0225225C
CAVE_PG_DA       = 0x023AD6F0  # (0x40 bytes) phoenix_gearblade: double-attack tail front @0x021A3F20: rider key 0x10EA -> may attack twice
CAVE_PG_VALID    = 0x023AD730  # (0x20 bytes) phoenix_gearblade: effect-still-valid check 0x021EDE48 default-arm front @0x021EE05A: cost slot == CAVE_PG_C3_COST is accepted
CAVE_PG_C4_COND  = 0x023AD750  # (0xb0 bytes) phoenix_gearblade: cls2 +0C C4 condition: OPT clear, this card in the GY or banished pile
CAVE_PG_C4_COST  = 0x023AD800  # (0x40 bytes) phoenix_gearblade: cls2 +10 'You can' prompt + hard OPT stamp (dsl._hopt_you_can_stub)
CAVE_PG_C4_RES   = 0x023AD840  # (0xc0 bytes) phoenix_gearblade: cls2 +04 add this card to the hand from the GY / banished pile (native add-target protocol)
CAVE_PG_LEAVE    = 0x023AD900  # (0xe0 bytes) phoenix_gearblade: BL @0x021C8216 leave-switch front (AHEAD of Hauteclere's): cost-sent / cost-banished Gearblade -> Sword of Dark Rites' accept arm
CAVE_PG_DBG      = 0x023AD9E0  # (0x40 bytes) phoenix_gearblade: DATA: C4 diagnostic breadcrumbs (leave front + cond + res write raw observations here; read from a savestate)
CAVE_PG_MISS     = 0x023ADA20  # (0x20 bytes) phoenix_gearblade: 0x021EE10C never-miss front (AHEAD of Disguise's): 0x10EA -> Z set (the 'If ... You can' trigger never misses timing), else previous
CAVE_PD_D_COND   = 0x023ADA90  # (0x60 bytes) predaplant: Darlingtonia Cobra cls1 +0C (per-Duel clear, Ophrys stamp, source zone Deck, target)
CAVE_PD_D_COST   = 0x023ADAF0  # (0x20 bytes) predaplant: Darlingtonia Cobra cls1 +14 (stamp per-Duel use, kind 5)
CAVE_PD_O_COND   = 0x023ADB10  # (0x80 bytes) predaplant: Ophrys Scorpio cls1 +0C (OPT, hand-monster scan via PROBE, Deck target)
CAVE_PD_O_COST   = 0x023ADB90  # (0x40 bytes) predaplant: Ophrys Scorpio cls1 +14 (OPT stamp + native hand send 0x021E7245)
CAVE_PD_O_RES    = 0x023ADBD0  # (0x40 bytes) predaplant: Ophrys Scorpio cls1 +04 (stamp KEY_ARM then native Deck SS 0x02206CAD)
CAVE_PD_MISS     = 0x023ADC10  # (0x20 bytes) predaplant: 0x021EE10C never-miss front (AHEAD of Gearblade's): 0x0FED / 0x17CF -> Z set, else previous
CAVE_PD_PROBE    = 0x023ADC30  # (0x10 bytes) predaplant: DATA: hand-scan probe byte read by the criteria_row_hook arm (ships clear)
CAVE_PD_ROWS     = 0x023ADC40  # (0x30 bytes) predaplant: DATA: virtual criteria rows 0xFF30 (Ophrys Deck summon, except self), 0xFF31 (Ophrys hand-monster cost), 0xFF32 (Darlingtonia Spell search)
CAVE_PD_H2       = 0x023ADC70  # (0x50 bytes) predaplant: criteria resolver miss-tail front @0x02243F24 (AHEAD of Gearfried's): 0x0FED -> 0xFF32, 0x17CF -> 0xFF30 / 0xFF31 (probe or cost running), else previous
CAVE_PD_H3       = 0x023ADCC0  # (0x30 bytes) predaplant: invoker row-compute front @0x02243F62 (AHEAD of Gearfried's): 0xFF30..0xFF32 -> CAVE_PD_ROWS + 0x10*i, else previous
CAVE_BD_ROWS     = 0x023ADCF0  # (0x20 bytes) block_dragon: DATA: virtual criteria row (index 0xFF40) for the C1 3-pick banish picker
CAVE_BD_VREC     = 0x023ADD10  # (0x30 bytes) block_dragon: DATA: virtual cls2 hand record (24 B)
CAVE_BD_C1_COND  = 0x023ADD40  # (0xb0 bytes) block_dragon: hand cls2 +0C (hand zone, free zone, >= 3 other EARTH monsters in hand+GY)
CAVE_BD_C1_COST  = 0x023ADDF0  # (0x100 bytes) block_dragon: hand cls2 +10 three-pick banish cost (Double Evolution Pill's protocol, 3 picks)
CAVE_BD_C1_H     = 0x023ADEF0  # (0x50 bytes) block_dragon: C1 criteria handler (hand + GY builders, EARTH filter)
CAVE_BD_C1_FILT  = 0x023ADF40  # (0x80 bytes) block_dragon: EARTH monster candidate filter, excluding this card's own ref
CAVE_BD_C1_S5    = 0x023ADFC0  # (0x10 bytes) block_dragon: hand cls2 +14 (no target: return 1)
CAVE_BD_H1       = 0x023AE9D0  # (0x70 bytes) block_dragon: find_event_handler miss-tail front 0x0224A86A (AHEAD of Gearfried's); MOVED from 0x023ADFD0 (0x30 B, now an unclaimed hole) to fit the C3 record
CAVE_BD_H2       = 0x023AE000  # (0x20 bytes) block_dragon: 0x02243F24 front (AHEAD of Predaplant's): 0x0FDD -> 0xFF40
CAVE_BD_H3       = 0x023AE020  # (0x30 bytes) block_dragon: 0x02243F62 front (AHEAD of Predaplant's): index 0xFF40 -> CAVE_BD_ROWS
CAVE_BD_H4       = 0x023AE050  # (0x20 bytes) block_dragon: ARM9 0x02023566 hand-offer front (AHEAD of Gearfried's): 0x0FDD -> 1
CAVE_BD_AI       = 0x023AE070  # (0x20 bytes) block_dragon: CPU hand-SS planner site ov5 0x0236A1BA front (AHEAD of Windrose's CAVE_WR_AICLASS): 0x0FDD -> class 2
CAVE_CPUHS_FRONT = 0x023AE090  # (0x40 bytes) cpu_hand_ss: CPU hand-card loop legality call ov5 0x02340F16 (`bl 0x0225E51C`) front: CPUL answers for its cids, else the shared hand-SS trampoline
CAVE_CPUHS_PAY   = 0x023AE0D0  # (0x1A0 bytes) cpu_hand_ss: summon-procedure registry handler for Block Dragon + the four big Dragon Rulers (CPU pays the banish cost; human returns done)
CAVE_CPUHS_LEGAL = 0x023AE270  # (0x140 bytes) cpu_hand_ss: CPUL -- CPU hand-loop legality for Block Dragon + the four big Dragon Rulers
CAVE_BD_C2W      = 0x023AE3B0  # (0x30 bytes) block_dragon C2: survive-check default-exit front (ov3 0x021CC264 bl), ahead of Seal of Orichalcos' stub
CAVE_BD_C2       = 0x023AE3E0  # (0x80 bytes) block_dragon C2: Rock-survives test
CAVE_BD_C3REC    = 0x023AE460  # (0x30 bytes) block_dragon C3: DATA: virtual cls2 leave-trigger record (24 B)
CAVE_BD_C3COND   = 0x023AE490  # (0x1A0 bytes) block_dragon C3 +0C: once per turn + a legal selection (1-3 Rocks, total Level 8) in the Deck
CAVE_BD_C3COST   = 0x023AE630  # (0x40 bytes) block_dragon C3 +14: stamp the once-per-turn lock, open the pick state
CAVE_BD_C3PRED   = 0x023AE670  # (0x1A0 bytes) block_dragon C3: Deck-builder candidate filter (Rock that can still finish at exactly 8)
CAVE_BD_C3RES    = 0x023AE810  # (0x120 bytes) block_dragon C3 +04: picker loop + native add-to-hand mover, one Rock per pass
CAVE_BD_C3H      = 0x023AE930  # (0x80 bytes) block_dragon C3: criteria row handler front (param>>16 == 2 -> Deck walker, else C1's handler)
CAVE_BD_C3MISS   = 0x023AE9B0  # (0x20 bytes) block_dragon C3: miss-timing node 0x021EE10C front (never miss), ahead of the current head
CAVE_BD_GYREC    = 0x023AEA40  # (0x30 bytes) block_dragon C1 GY half: DATA: virtual cls2 GY record (24 B), RES = the shared GY self-SS resolver 0x0220731D
CAVE_CORAL_C2COND = 0x023AEA70  # (0x70 bytes) coral_dragon C2: cls2 +0C -- GY card's word bit 15 (properly summoned) AND native draw cond 0x021F069D
CAVE_CORAL_DBG   = 0x023AEAE0  # (0x10 bytes) coral_dragon: DATA: debug scratch {cond calls, last GY word, GY idx, desc[+0xC]} -- read from a savestate
CAVE_CORAL_C1COND = 0x023AEAF0  # (0x60 bytes) coral_dragon C1: cls3 +0C -- OPT tag 0x0FB6 absent AND >= 1 card to discard (Chiron's cond with the discard mode = any card)
CAVE_CORAL_C1COST = 0x023AEB90  # (0x40 bytes) coral_dragon C1: cls3 +10 -- stamp the OPT tag (0x021E5060) then discard 1 card of ANY kind (0x0225991C mode 0)
CAVE_BD_GYRES    = 0x023AEB60  # (0x30 bytes) block_dragon C1 GY half: cls2 +04 wrapper: set the 'properly Special Summoned' flag (card word bit 15) on this card, then the shared GY self-SS resolver 0x0220731D
CAVE_CORAL_DBG1  = 0x023AEBD0  # (0x10 bytes) coral_dragon: DATA: C1 counters {cond calls, cond yes, cost calls, 0} -- read from a savestate / CPU-duel dump
CAVE_CORAL_SSF   = 0x023AEBE0  # (0x70 bytes) coral_dragon C2: SS-commit front (BL'd from 0x022692F2 / 0x022693A0): record 'Special Summoned FROM THE EXTRA DECK' per card ref, then run the previous head
CAVE_CORAL_MARK  = 0x023AEC50  # (0x40 bytes) coral_dragon C2: DATA: 512-bit bitmap by packed card ref (idx<<1|side): 1 = last Special Summon of that card was from the Extra Deck (= Synchro Summoned)
CAVE_CORAL_PREV  = 0x023AEC90  # (0x10 bytes) coral_dragon: DATA: {previous SS-commit BL head, previous miss-timing node head or 0 = stock}
CAVE_CORAL_MISS  = 0x023AECA0  # (0x30 bytes) coral_dragon C2: never-miss front for the miss-timing node 0x021EE10C (IF effect: Synchro material / Tribute must not miss)
CAVE_CORAL_DBG2  = 0x023AECD0  # (0x10 bytes) coral_dragon: DATA: last SS-commit of the donor {cid, src zone, ref, count}
CAVE_MM_SEL3      = 0x023AEEA0  # (0xa0 bytes) mega_monarch: Mobius cls1 +14: the Granmarg selector shape with r6 = 3, but RETURNS to a continuation that, on 'selection done' + a WATER Tribute, latches the targets' (side, zone) mask (E2 lock). Old 0x023AECE0 slot (0x20 B) is a dead hole
CAVE_MM_RESM      = 0x023AEF40  # (0x20 bytes) mega_monarch: Mobius cls1 +04: native up-to-N destroy 0x022048A4, then clear the E2 lock
CAVE_MM_LKF       = 0x023AEF60  # (0x70 bytes) mega_monarch: E2 lock front over the 3 BLs to the activation-prohibited predicate (0x021EDA2E / 0x021D6B5C / 0x021FC116): prior verdict || (lock live && opponent of the Mobius controller && S/T zone in the latched mask)
CAVE_MM_LOCK      = 0x023AEFD0  # (0x10 bytes) mega_monarch: DATA: E2 lock {mask (side*16+zone bits), phase, turn player, Mobius controller}
CAVE_MM_M0       = 0x023B3870  # (0xA0 bytes) mega_monarch: M0 alternate Tribute front; RELOCATED AGAIN 2026-11-12 (8 cids with Erebus + Ehther > 0x80); the old slots 0x023B0978 (0x80) and 0x023AF730 (0x70) are unused holes
CAVE_MM_TRIG     = 0x023B3910  # (0x80 bytes) mega_monarch: front over the Monarch-list search `bl 0x02022E14` @0x022657B8; RELOCATED AGAIN 2026-11-12 (9 cids with Erebus + Ehther > 0x60); the old slots 0x023B09F8 (0x60) and earlier are unused holes
CAVE_MM_SEL       = 0x023AED40  # (0x30 bytes) mega_monarch: cls1 +14 target selector = Mobius' arm (up to 2, msg 0x8D, kind 0x21) entered mid-function at 0x02237C3E with its prologue replicated
CAVE_MM_RES       = 0x023AED70  # (0x50 bytes) mega_monarch: cls1 +04 resolver = native up-to-2 destroy 0x022046B8, then E2: draw 1 if the Tribute-commit capture saw an EARTH Tribute
CAVE_MM_CAP      = 0x023AF7A0  # (0xa0 bytes) mega_monarch: front over the four Tribute-payment BLs of 0x021CF68C: latch 1 << attribute of each selected Tribute when the summoned card is a Mega. MOVED (2nd time) from 0x023AF070 (0x90 B dead hole) for the 5th arm
CAVE_MM_FLAG      = 0x023AEE40  # (0x10 bytes) mega_monarch: DATA: E2 latch word (1 = the last Mega Tribute Summon used an EARTH Tribute)
CAVE_MM_RESZ     = 0x023AF100  # (0x200 bytes) mega_monarch: Zaborg cls1 +04: phase machine (0x80 read target + destroy + plan, 0x7F next pick, 0x7E picker, 0x7D send to GY, 0x64 close) over the Extra Deck; replaces the first one-shot RESZ
CAVE_MM_ZROW     = 0x023AF300  # (0x20 bytes) mega_monarch: DATA: virtual criteria row 0xFF50 {cid, 0xFFFF, ZH|1, 2} for Zaborg's Extra Deck picker
CAVE_MM_ZH       = 0x023AF320  # (0x50 bytes) mega_monarch: Zaborg criteria handler: the Extra Deck enumerator 0x0223BE40, own or the OTHER player's (param bit 16)
CAVE_MM_ZH2      = 0x023AF370  # (0x20 bytes) mega_monarch: 0x02243F24 front (AHEAD of Block Dragon's): donor cid -> 0xFF50
CAVE_MM_ZH3      = 0x023AF390  # (0x30 bytes) mega_monarch: 0x02243F62 front (AHEAD of Block Dragon's): index 0xFF50 -> CAVE_MM_ZROW
CAVE_MM_ZST      = 0x023AF3C0  # (0x30 bytes) mega_monarch: DATA: Zaborg step state {step, picks done, nsteps, step0, step1}
CAVE_MM_RESR      = 0x023AF430  # (0x1d0 bytes) mega_monarch: Raiza cls1 +04 phase machine (plan, pick field / GY / extra field at resolution, apply the moves)
CAVE_MM_RRH       = 0x023AF600  # (0xa0 bytes) mega_monarch: Raiza criteria handler: mode 0 every field card (both players) except the first pick, mode 1 both Graveyards
CAVE_MM_RROW      = 0x023AF6A0  # (0x20 bytes) mega_monarch: DATA: virtual criteria row 0xFF51 {cid, 0xFFFF, RRH|1, 2}
CAVE_MM_RH2       = 0x023AF6C0  # (0x20 bytes) mega_monarch: 0x02243F24 front (AHEAD of Zaborg's): donor cid -> 0xFF51
CAVE_MM_RH3       = 0x023AF6E0  # (0x30 bytes) mega_monarch: 0x02243F62 front (AHEAD of Zaborg's): index 0xFF51 -> CAVE_MM_RROW
CAVE_MM_RRST      = 0x023AF710  # (0x20 bytes) mega_monarch: DATA: Raiza step state {step, field ref, GY ref, extra ref, nsteps}
CAVE_MM_RESC     = 0x023AF840  # (0x320 bytes) mega_monarch: Caius cls1 +04 phase machine (target 0, optional 2nd pick after a DARK Tribute, banish + 1000 + DARK copies)
CAVE_MM_CRH      = 0x023AFB60  # (0xa0 bytes) mega_monarch: Caius criteria handler (mega_raiza's rh_stub over Caius' own state)
CAVE_MM_CROW     = 0x023AFC00  # (0x20 bytes) mega_monarch: DATA: virtual criteria row 0xFF52 {cid, 0xFFFF, CRH|1, 2}
CAVE_MM_CH2      = 0x023AFC20  # (0x20 bytes) mega_monarch: 0x02243F24 front (AHEAD of Raiza's): donor cid -> 0xFF52
CAVE_MM_CH3      = 0x023AFC40  # (0x30 bytes) mega_monarch: 0x02243F62 front (AHEAD of Raiza's): index 0xFF52 -> CAVE_MM_CROW
CAVE_MM_CST      = 0x023AFC70  # (0x20 bytes) mega_monarch: DATA: Caius state {-, excluded ref, 2nd ref, -, 1st location, 2nd location}
CAVE_MA_TINY       = 0x023AFC90  # (0x10 bytes) march: cls0 cond (+0) / cost (+4) / res (+8) for the Continuous Spell activation
CAVE_MA_TEST      = 0x023AFCA0  # (0xa0 bytes) march: (side, zone) -> 1 if March protects that Tribute Summoned monster (compiled C, march.c)
CAVE_MA_C2W       = 0x023AFD40  # (0x30 bytes) march: survive-check default-exit front @0x021CC264 (AHEAD of Block Dragon's C2W): March-protected -> survives
CAVE_MA_TGT       = 0x023AFD70  # (0x50 bytes) march: targeting-link front @0x021B05CC (AHEAD of Safe Zone's CAVE3_SZ_TARGET): March-protected -> NOT affectable
CAVE_MA_LOCK      = 0x023B2C90  # (0x140 bytes; RELOCATED 2026-11-11 for Domain of the True Monarchs' D1 clause (0x120 B); 0x023B0020..0x023B00B0 is now an unused hole) (was 0x90 bytes; grew past 0x70 with Return, into the hole 0x023B0090..0x023B00F0) (relocated 2026-11-10: grew past 0x50 with the Stormforth latch; 0x023AFDC0..0x023AFE10 is now an unused hole) march: ED_LOCK(side) -> 1 if side has a face-up March (the Extra Deck Special Summon lock; compiled C, edlock.c)
CAVE_MA_HS        = 0x023AFE10  # (0x30 bytes) march: front over `bl is_synchro` @0x0224954E inside can_synchro_summon: lock -> not a legal Synchro Summon
CAVE_MA_HF        = 0x023AFE40  # (0x30 bytes) march: front over `bl is_fusion` @0x0223299A inside can_fusion_summon: lock -> not a legal Fusion Summon
CAVE_MA_HE        = 0x023AFE70  # (0x50 bytes) march: front over `bl 0x021AD8C4` (free-zone check) @0x02269266 in the SS engine: lock && source zone 0xC -> 'no free zone' (-1)
CAVE_SF_COND      = 0x023AFEC0  # (0x30 bytes) stormforth: cls0 cond (HOPT query)
CAVE_SF_COST      = 0x023AFEF0  # (0x30 bytes) stormforth: cls0 cost (post HOPT node = 'activated this turn')
CAVE_SF_RES       = 0x023AFF20  # (0x10 bytes) stormforth: cls0 res (no-op)
CAVE_SF_PERM      = 0x023AFF30  # (0x60 bytes) stormforth: front over `bl 0x021A14B4` @0x021AD94A in the Tribute-release core: opponent's monster may be Tributed for a Tribute Summon
CAVE_SF_WRAP      = 0x023AFF90  # (0x30 bytes) stormforth: front over `bl 0x021AD8F4` @0x021AE102 (summon release): sets the 'Tribute Summon in progress' flag around the core
CAVE_SF_PAY       = 0x023AFFC0  # (0x50 bytes) stormforth: front over the four `bl 0x021CF68C` Tribute payments: an opponent slot in the mask posts the 'used' node
CAVE_SF_FLAG      = 0x023B0010  # (0x10 bytes) stormforth: data word, 1 while the summon-release core runs
# (0x023B0090..0x023B00F0: unused hole, the first CAVE_TN_COND slot)
CAVE_TN_COST     = 0x023B00F0  # (0x50 bytes) tenacity: cls0 cost (native reveal 0x021EAAA1 under the hand-row probe, then post OPT)
CAVE_TN_RES      = 0x023B0140  # (0x20 bytes) tenacity: cls0 res (native Deck -> hand 0x02207EF5)
CAVE_TN_ROWS     = 0x023B0160  # (0x20 bytes) tenacity: DATA: virtual criteria rows 0xFF60 (Monarch S/T Deck search, except self), 0xFF61 (hand reveal by set code 0x6C)
CAVE_TN_PROBE    = 0x023B0180  # (0x10 bytes) tenacity: DATA: hand-row probe byte (ships clear)
CAVE_TN_H2       = 0x023B0190  # (0x50 bytes) tenacity: criteria miss-tail front @0x02243F24 (AHEAD of Block Dragon's): 0x12EB -> 0xFF61 (probe / cost running) else 0xFF60, else previous
CAVE_TN_H3       = 0x023B01E0  # (0x30 bytes) tenacity: invoker row-compute front @0x02243F62 (AHEAD of Block Dragon's): 0xFF60..0xFF61 -> CAVE_TN_ROWS + 0x10*i, else previous
CAVE_TN_MON      = 0x023B1AA0  # (0x30 bytes) [RELOCATED 2026-11-11 from 0x023B0210 (0x10): the list outgrew 8 entries with Revolt]  tenacity: DATA: "Monarch" set-code list (set code 0x6D repointed here), 5 x u16
CAVE_TN_REV      = 0x023B0220  # (0x30 bytes) tenacity: DATA: ATK/DEF 2400/1000 or 2800/1000 monster list (set code 0x6C repointed here), 22 x u16
CAVE_TN_COND     = 0x023B0250  # (0x90 bytes) tenacity: cls0 cond (OPT, a direct hand scan for a set-0x6C monster, a Monarch S/T in the Deck); relocated 2026-11-10 (grew past 0x60; 0x023B0090..0x023B00F0 is now an unused hole)
CAVE_RT_TINY     = 0x023B02E0  # (0x10 bytes) return_monarchs: cls0 cond / cost / res (March tiny stubs)
# (0x023B02F0..0x023B0350: unused hole, the first CAVE_RT_COND slot)
CAVE_RT_COST     = 0x023B0350  # (0x30 bytes) return_monarchs: cls1 +14 cost (post the once-per-turn node) (C)
# (CAVE_RT_RES first slot 2026-11-10: unused hole 0x023B0380..0x023B0450 covers RES + TEST)

CAVE_RT_TRIG     = 0x023B0450  # (0x40 bytes) return_monarchs: 4-byte BL hook over cmp r5,#0 ; beq @0x02265C70 (summon-event dispatcher verdict)
CAVE_RT_POST     = 0x023B0490  # (0x30 bytes) return_monarchs: front over bl 0x021D3168 @0x02265CA8: swaps the posted event cid for Return when the flag is up
CAVE_RT_PRED     = 0x023B04C0  # (0x60 bytes) return_monarchs: Deck-search predicate (ATK 2400/2800, DEF 1000, different name from the summoned monster)
CAVE_RT_HAND     = 0x023B0520  # (0x30 bytes) return_monarchs: virtual row handler (0x0223CAF4 with the custom predicate)
CAVE_RT_ROWS     = 0x023B0550  # (0x10 bytes) return_monarchs: DATA: virtual criteria row 0xFF70
CAVE_RT_DATA     = 0x023B0560  # (0x20 bytes) return_monarchs: DATA: swap flag, summoner side, zone, summoned cid
CAVE_RT_H2       = 0x023B0580  # (0x40 bytes) return_monarchs: criteria miss-tail front @0x02243F24 (AHEAD of Block Dragon's): 0x14A1 -> 0xFF70
CAVE_RT_H3       = 0x023B05C0  # (0x30 bytes) return_monarchs: invoker row-compute front @0x02243F62 (AHEAD of Block Dragon's): 0xFF70 -> CAVE_RT_ROWS
CAVE_RT_COND     = 0x023B05F0  # (0x80 bytes) return_monarchs: cls1 +0C cond (OPT, summoned monster face-up, Deck candidate) (C); relocated 2026-11-10 (grew past 0x60; 0x023B02F0..0x023B0350 is now an unused hole)
CAVE_RT_RES      = 0x023B0670  # (0x80 bytes) return_monarchs: cls1 +04 resolver (face-up check, native Deck -> hand) (C); relocated 2026-11-10 (grew past 0x50)
CAVE_RT_TEST     = 0x023B06F0  # (0x90 bytes) return_monarchs: trigger test leaf (face-up Return, OPT clear -> record + raise swap flag) (C); relocated 2026-11-10 (grew past 0x80)
CAVE_RS_COND     = 0x023B0780  # (0x40 bytes) restoration: cls0 +0C cond (OPT, then Premature Burial's native GY-Special-Summon condition) (C)
CAVE_RS_COST     = 0x023B07C0  # (0x20 bytes) restoration: cls0 +10 cost (post the once-per-turn node, no LP) (C)
CAVE_RS_POS      = 0x023B07E0  # (0x30 bytes) restoration: front over bl 0x02204730 @0x022075D2 (PB resolver): 0x12EE -> Defense Position (r2 = 1)
CAVE_RS_PREA     = 0x023B0810  # (0x18 bytes) restoration: precheck 0x12EE ? 1 : tail 0x02223490, for the leave-cleanup list bl @0x021CB3BC and the kind-3 summon poster bl @0x02268074
CAVE_RS_PREB     = 0x023B0828  # (0x18 bytes) restoration: precheck 0x12EE ? 1 : tail 0x023AAC30, for the negate-reader list bl @0x021EE418
CAVE_RS_ROWS     = 0x023B0840  # (0x10 bytes) restoration: DATA: virtual criteria row 0xFF80 (GY Special Summon, set code 0x6C = 2400/1000 or 2800/1000 monsters)
CAVE_RS_H2       = 0x023B0850  # (0x28 bytes) restoration: criteria miss-tail front @0x02243F24 (AHEAD of Block Dragon's): 0x12EE -> 0xFF80
CAVE_RS_H3       = 0x023B0878  # (0x30 bytes) restoration: invoker row-compute front @0x02243F62 (AHEAD of Block Dragon's): 0xFF80 -> CAVE_RS_ROWS
CAVE_RS_TRIBW    = 0x023B08A8  # (0x30 bytes) restoration: front over `adds r5,r3,#0 ; adds r6,r1,#0` @0x021AE14A (native double-Tribute predicate): TRUE for an equipped monster
CAVE_RS_TRIB     = 0x023B0380  # (0x60 bytes) restoration: leaf of that front (equipped by a face-up Restoration?) (C)  [unused hole 0x023B0380..0x023B0450, shared with CAVE_RT_RES]
CAVE_AW_FILT     = 0x023B02F0  # (0x40 bytes) monarchs_awaken: cls0 +08 target filter (own face-up Tribute Summoned monster) (C)  [unused hole 0x023B02F0..0x023B0350]
CAVE_AW_COND     = 0x023B0330  # (0x20 bytes) monarchs_awaken: cls0 +0C cond (no cards in your Extra Deck) (C)
CAVE_AW_RES      = 0x023B03E0  # (0x48 bytes) monarchs_awaken: cls0 +04 resolver (kind-3 rider keyed 0x1633 on the target) (C)  [unused hole 0x023B03E0..0x023B0450]
CAVE_AW_PREB     = 0x023B0428  # (0x18 bytes) monarchs_awaken: negate-reader precheck 0x1633 ? 1 : tail, for the list search bl @0x021EE418
CAVE_AW_PROT     = 0x023AFDC0  # (0x50 bytes) monarchs_awaken: affect-predicate front over `bl` @0x021B059C: a monster with the 0x1633 rider is protected from every card but Awaken  [unused hole 0x023AFDC0..0x023AFE10]
CAVE_MM_REST      = 0x023B08D8  # (0xA0 bytes) mega_monarch: Thestalos the Mega Monarch cls1 +04 (clone of 0x0221D150 with Level x 200, + FIRE-latch 1000 damage) (C)
CAVE_AG_COND      = 0x023B0A58  # (0x50 bytes) angmarl: cls1 +0C cond (a Spell Card in your Graveyard) (C)
CAVE_AG_COST      = 0x023B0AA8  # (0x10 bytes) angmarl: cls1 +14 cost (the native banish cost 0x021E5319 over the GY row) (C)
CAVE_AG_RES       = 0x023B0AB8  # (0x60 bytes) angmarl: cls1 +04 resolver (remember the banished cid, native Deck -> hand) (C)
CAVE_AG_PRED      = 0x023B0B18  # (0x30 bytes) angmarl: Deck-search predicate (same name as the banished card)
CAVE_AG_HAND      = 0x023B0B48  # (0x30 bytes) angmarl: virtual Deck row handler (0x0223CAF4 body with the custom predicate)
CAVE_AG_ROWS      = 0x023B0B78  # (0x20 bytes) angmarl: DATA: virtual criteria rows 0xFF90 (GY Spell, banish cost) and 0xFF91 (Deck, same name)
CAVE_AG_DATA      = 0x023B0B98  # (0x10 bytes) angmarl: DATA: +0 the banished card's cid (ships clear)
CAVE_AG_H2        = 0x023B0BA8  # (0x30 bytes) angmarl: criteria miss-tail front @0x02243F24: 0x14D8 -> 0xFF90 while the cost machine runs, else 0xFF91 (AHEAD of the Mega chain)
CAVE_AG_H3        = 0x023B0BD8  # (0x30 bytes) angmarl: invoker row-compute front @0x02243F62: 0xFF90..0xFF91 -> CAVE_AG_ROWS
CAVE_PT_COND      = 0x023B0C08  # (0x70 bytes) pantheism: cls0 +0C cond (another Monarch S/T in the hand, Deck >= 2) (C)
CAVE_PT_RES       = 0x023B0C78  # (0x10 bytes) pantheism: cls0 +04 resolver (draw 2) (C)
CAVE_PT_ROWS      = 0x023B0C88  # (0x20 bytes) pantheism: DATA: virtual criteria row 0xFFA0 (hand, "Monarch" Spell/Trap except self)
CAVE_PT_H2        = 0x023B0CA8  # (0x30 bytes) pantheism: criteria miss-tail front @0x02243F24 (AHEAD of the Monarch chain): 0x1923 -> 0xFFA0
CAVE_PT_H3        = 0x023B0CD8  # (0x30 bytes) pantheism: invoker row-compute front @0x02243F62: 0xFFA0 -> CAVE_PT_ROWS
CAVE_GYV2_ROWS    = 0x023B12B0  # (0x180 bytes) [relocated 2026-11-11, was 0x023B0D08 / 0x120: 24 rows] pantheism: the shared virtual GY-action table RELOCATED for a 17th row (gy_vrow_hook layout GYV2; the chain keeps the 16-row table at CAVE_GYV_ROWS)
CAVE_GYV2_HAS     = 0x023B1430  # (0x100 bytes) [relocated 2026-11-11, was 0x023B0E28 / 0xC0] pantheism: gy_vrow_hook GY has-row exit for 17 cids (layout GYV2; the old 0xB0 slot is too small)
CAVE_PT_COND3     = 0x023B0EE8  # (0x40 bytes) pantheism: cls2 +0C cond (OPT, >= 3 Monarch S/T in the Deck) (C)
CAVE_PT_COST3     = 0x023B0F28  # (0x28 bytes) pantheism: cls2 +10 cost (native self-banish 0x021E5709, then the once-per-turn node) (C)
CAVE_PT_RES3      = 0x023B0F50  # (0x120 bytes) pantheism: cls2 +04 resolver (Painful Choice phases, pick 3, opponent chooses, shuffle) (C)
CAVE_GYV2_POST    = 0x023B1530  # (0x120 bytes) [relocated 2026-11-11, was 0x023B1070 / 0xD0] frost blast: gy_vrow_hook GY post-by-cid exit for 18 cids (layout GYV2; the old 0xC0 slot is too small)
CAVE_FB_COND      = 0x023B1140  # (0x70 bytes) frost_blast: cls0 +0C cond (a face-up monster with ATK >= 2400 and DEF 1000) (C)
CAVE_FB_COND2     = 0x023B11B0  # (0x70 bytes) frost_blast: cls2 +0C cond (another Monarch S/T in the GY) (C)
CAVE_FB_COST2     = 0x023B1220  # (0x20 bytes) frost_blast: cls2 +10 cost (native banish cost over the GY row, then self-banish) (C)
CAVE_FB_ROWS      = 0x023B1240  # (0x10 bytes) frost_blast: DATA: virtual criteria row 0xFFB0 (GY, "Monarch" Spell/Trap except self)
CAVE_FB_H2        = 0x023B1250  # (0x30 bytes) frost_blast: criteria miss-tail front @0x02243F24 (AHEAD of the Monarch chain): 0x14C3 -> 0xFFB0
CAVE_FB_H3        = 0x023B1280  # (0x30 bytes) frost_blast: invoker row-compute front @0x02243F62: 0xFFB0 -> CAVE_FB_ROWS
CAVE_RV_COND      = 0x023B1650  # (0x68 bytes) revolt: cls0 +0C cond (OPT, another card in hand, >= 3 matching monsters in the Deck) (C)
CAVE_RV_COST      = 0x023B16B8  # (0x28 bytes) revolt: cls0 +10 cost (native hand-pick cost 0x021E4EED, then the once-per-turn node) (C)
CAVE_RV_RES       = 0x023B16E0  # (0x148 bytes) revolt: cls0 +04 resolver (Painful Choice phases, pick 3, opponent chooses, rest to the GY, Extra Deck lock) (C)
CAVE_RV_COND2     = 0x023B1828  # (0x88 bytes) revolt: cls2 +0C cond (OPT, an 800/1000 monster in the hand) (C)
CAVE_RV_COST2     = 0x023B18B0  # (0x28 bytes) revolt: cls2 +10 cost (native self-banish + the once-per-turn node) (C)
CAVE_RV_RES2      = 0x023B18D8  # (0x20 bytes) revolt: cls2 +04 resolver (mode 1, the native hand Special Summon 0x0220667D) (C)
CAVE_RV_PRED      = 0x023B18F8  # (0x48 bytes) revolt: Deck predicate (DEF 1000 and ATK >= 2400 or ATK 800)
CAVE_RV_PREDH     = 0x023B1940  # (0x40 bytes) revolt: hand predicate (ATK 800 and DEF 1000)
CAVE_RV_HANDD     = 0x023B1980  # (0x30 bytes) revolt: virtual Deck row handler (0x0223CAF4 body with PRED)
CAVE_RV_HANDH     = 0x023B19B0  # (0x40 bytes) revolt: virtual hand row handler (0x0223CB38 body with PREDH)
CAVE_RV_ROWS      = 0x023B19F0  # (0x30 bytes) revolt: DATA: virtual criteria rows 0xFFC0 (hand, any card: the cost), 0xFFC1 (Deck monsters), 0xFFC2 (hand 800/1000)
CAVE_RV_DATA      = 0x023B1A20  # (0x10 bytes) revolt: DATA: +0 criteria mode (0 Deck row, 1 hand 800/1000 row) (ships clear)
CAVE_RV_H2        = 0x023B1A30  # (0x40 bytes) revolt: criteria miss-tail front @0x02243F24: 0x1DCD -> hand row while the cost runs, else by mode
CAVE_RV_H3        = 0x023B1A70  # (0x30 bytes) revolt: invoker row-compute front @0x02243F62: 0xFFC0..0xFFC2 -> CAVE_RV_ROWS
CAVE_ED_COND      = 0x023B1AD0  # (0x80 bytes) edea: cls1 +0C cond (OPT clear, SS gates, a Deck 800/1000 monster) (C)
CAVE_ED_COST      = 0x023B1B50  # (0x20 bytes) edea: cls1 +14 cost (stamps the once-per-turn node) (C)
CAVE_ED_RES       = 0x023B1B70  # (0x120 bytes) edea: cls1 +04 resolver (the native Deck-SS default arm replayed in Defense Position, then the Extra Deck lock) (C)
CAVE_ED_COND2     = 0x023B1C90  # (0x40 bytes) edea: cls2 +0C cond (sent to the GY: OPT clear, a banished Monarch Spell/Trap; sets mode 1) (C)
CAVE_ED_RES2      = 0x023B1CD0  # (0x40 bytes) edea: cls2 +04 resolver (mode 1, OPT stamp, the native add-target resolver 0x02208181) (C)
CAVE_ED_SEL2      = 0x023B1D10  # (0x20 bytes) edea: cls2 +14 selector (mode 1, the native off-field picker 0x02235605) (C)
CAVE_ED_PRED      = 0x023B1D30  # (0x40 bytes) edea: Deck predicate (ATK 800, DEF 1000, not Edea)
CAVE_ED_DECKH     = 0x023B1D70  # (0x30 bytes) edea: virtual Deck row handler (Deck-SS enumerator 0x0223BC3C with PRED)
CAVE_ED_BANH      = 0x023B1DA0  # (0x30 bytes) edea: virtual banished row handler (0x0223FBA0's body with the add-to-hand type 8)
CAVE_ED_ROWS      = 0x023B1DD0  # (0x20 bytes) edea: DATA: virtual criteria rows 0xFFD0 (Deck 800/1000) / 0xFFD1 (banished Monarch Spell/Trap)
CAVE_ED_DATA      = 0x023B1DF0  # (0x10 bytes) edea: DATA: +0 criteria mode (0 Deck row, 1 banished row) (ships clear)
CAVE_ED_H2        = 0x023B1E00  # (0x30 bytes) edea: criteria miss-tail front @0x02243F24: 0x0FDC -> row by mode
CAVE_ED_H3        = 0x023B1E30  # (0x30 bytes) edea: invoker row-compute front @0x02243F62: 0xFFD0..0xFFD1 -> CAVE_ED_ROWS
CAVE_ES_COND     = 0x023B1E60  # (0x30 bytes) eidos_squire: cls1 +0C cond (E1 once per turn) (C)
CAVE_ES_RES      = 0x023B1E90  # (0x30 bytes) eidos_squire: cls1 +04 resolver (OPT node + Double Summon's grant node) (C)
CAVE_ES_COND2    = 0x023B1EC0  # (0x40 bytes) eidos_squire: cls2 +0C cond (E2 OPT + the native GY-SS cond) (C)
CAVE_ES_COST2    = 0x023B1F00  # (0x30 bytes) eidos_squire: cls2 +10 cost (native self-banish + OPT) (C)
CAVE_ES_RES2     = 0x023B1F30  # (0x30 bytes) eidos_squire: cls2 +04 resolver (Extra Deck lock + the PB-family resolver) (C)
CAVE_ES_PRED     = 0x023B1F60  # (0x40 bytes) eidos_squire: GY predicate (ATK 800, DEF 1000, not Eidos the Underworld Squire)
CAVE_ES_GYH      = 0x023B1FA0  # (0x30 bytes) eidos_squire: virtual GY row handler (0x0223C9D0's body with PRED)
CAVE_ES_ROWS     = 0x023B1FD0  # (0x10 bytes) eidos_squire: DATA: virtual criteria row 0xFFD2 (GY monsters 800/1000)
CAVE_ES_H2       = 0x023B1FE0  # (0x20 bytes) eidos_squire: criteria miss-tail front @0x02243F24: 0x0FE2 -> row 0xFFD2
CAVE_ES_H3       = 0x023B2000  # (0x30 bytes) eidos_squire: invoker row-compute front @0x02243F62: 0xFFD2 -> CAVE_ES_ROWS
CAVE_ES_POS      = 0x023B2030  # (0x20 bytes) eidos_squire: Defense Position front @0x022075D2 (PB resolver position call)
CAVE_ES_C79BIG   = 0x023B2050  # (0x80 bytes) eidos_squire: shared N-or-SS trigger stub in a 0x80 B slot for 7+ arms (c79_trigger_hook, the 0x50 slot is full at 6)
CAVE_TS_COND3    = 0x023B20D0  # (0x30 bytes) tessera: cls3 +0C cond (T2 OPT + the vanilla ignition check) (C)
CAVE_TS_COST3    = 0x023B2100  # (0x30 bytes) tessera: cls3 +10 cost (stamps the T2 node) (C)
CAVE_TS_RES3     = 0x023B2130  # (0x30 bytes) tessera: cls3 +04 resolver (posts Double Summon's grant node) (C)
CAVE_TS_COND     = 0x023B2160  # (0x70 bytes) tessera: cls2 +0C cond (sent to the GY: OPT, SS gates, an 800/1000 monster in the Deck) (C)
CAVE_TS_RES      = 0x023B21D0  # (0x40 bytes) tessera: cls2 +04 resolver (OPT + Extra Deck lock, then the native Deck-SS machine) (C)
CAVE_TS_PRED     = 0x023B2210  # (0x40 bytes) tessera: Deck predicate (ATK 800 and DEF 1000)
CAVE_TS_DECKH    = 0x023B2250  # (0x30 bytes) tessera: virtual Deck row handler (Deck-SS enumerator with PRED)
CAVE_TS_ROWS     = 0x023B2280  # (0x10 bytes) tessera: DATA: virtual criteria row 0xFFD3 (Deck 800/1000)
CAVE_TS_H2       = 0x023B2290  # (0x20 bytes) tessera: criteria miss-tail front @0x02243F24: 0x1123 -> row 0xFFD3
CAVE_TS_H3       = 0x023B22B0  # (0x30 bytes) tessera: invoker row-compute front @0x02243F62: 0xFFD3 -> CAVE_TS_ROWS
CAVE_EM_COND     = 0x023B22E0  # (0x60 bytes) eidos_monarch: cls1 +0C cond (C)
CAVE_EM_COST     = 0x023B2340  # (0x30 bytes) eidos_monarch: cls1 +14 cost (C)
CAVE_EM_COND3    = 0x023B2370  # (0x30 bytes) eidos_monarch: E2 cls3 cond (C)
CAVE_EM_COST3    = 0x023B23A0  # (0x30 bytes) eidos_monarch: E2 cls3 cost (C)
CAVE_EM_RES3     = 0x023B23D0  # (0x40 bytes) eidos_monarch: E2 cls3 resolver (Genex attribute rider) (C)
CAVE_EM_PRED     = 0x023B2410  # (0x60 bytes) eidos_monarch: Deck predicate
CAVE_EM_DECKH    = 0x023B2470  # (0x30 bytes) eidos_monarch: virtual Deck row handler
CAVE_EM_ROWS     = 0x023B24A0  # (0x10 bytes) eidos_monarch: DATA: virtual criteria row 0xFFD4
CAVE_EM_H2       = 0x023B24B0  # (0x20 bytes) eidos_monarch: criteria miss-tail front
CAVE_EM_H3       = 0x023B24D0  # (0x30 bytes) eidos_monarch: invoker row-compute front
CAVE_T1_COND     = 0x023B2500  # (0x80 bytes) tessera_hand: T1 virtual cls2 hand record +0C cond (C)
CAVE_T1_COST     = 0x023B2580  # (0x30 bytes) tessera_hand: T1 +10 cost (reveal) (C)
CAVE_T1_RES      = 0x023B25B0  # (0x40 bytes) tessera_hand: T1 +04 resolver (OPT stamp + native hand self-SS) (C)
CAVE_T1_VREC     = 0x023B25F0  # (0x20 bytes) tessera_hand: T1 virtual cls2 hand record (24 B)
CAVE_T1_ROWS     = 0x023B2610  # (0x10 bytes) tessera_hand: DATA: virtual criteria row 0xFFD5 (hand Monarch Spell/Trap)
CAVE_T1_H2       = 0x023B2620  # (0x30 bytes) tessera_hand: criteria miss-tail front: cost running -> row 0xFFD5 else tail
CAVE_T1_H3       = 0x023B2650  # (0x30 bytes) tessera_hand: invoker row-compute front 0xFFD5
CAVE_T1_H4       = 0x023B2680  # (0x20 bytes) tessera_hand: ARM9 hand-offer front (Tessera -> 1)
CAVE_PF_STUB     = 0x023B4CE0  # (0x100 bytes) [relocated AGAIN 2026-11-12 for 7 entries (Eidos E3, Masterplan C2); 0x023B4290 / 0xC0 is now a hole] [relocated 2026-11-12 for a 5th entry (The Prime Monarch GY half); the old 0x90 B at 0x023B26A0 are now a hole] prefind: find_event_handler PRE-DISPATCH front @0x0224A124 (virtual records for cids registered in effects/prefind_hook.py)
CAVE_MP_ROWS     = 0x023B5430  # (0x30 bytes) masterplan: DATA: virtual criteria rows 0xFFD6 (C1) / 0xFFD7 (C2 targets) / 0xFFD8 (C2 adds); RELOCATED 2026-11-12 session 2 (0x023B2730 / 0x10 is now a hole)
CAVE_MP_H2       = 0x023B53E0  # (0x50 bytes) masterplan: criteria miss-tail front (MODE-aware since C2); RELOCATED 2026-11-12 session 2 (0x023B2740 / 0x20 is now a hole)
CAVE_MP_H3       = 0x023B2760  # (0x30 bytes) masterplan: invoker row-compute front
CAVE_ER_TINY     = 0x023B2790  # (0x10 bytes) erupt: cls0 cost (+0) / res (+4) for the Continuous Trap activation
CAVE_ER_COND     = 0x023B27A0  # (0x80 bytes) erupt: cls0 +0C cond E1 (compiled C, erupt.c ER_COND)
CAVE_ER_TEST     = 0x023B2820  # (0xC0 bytes) erupt: (side, zone) -> 1 if a face-up Erupt negates that non-Tribute-Summoned monster (compiled C, erupt.c ER_TEST)
CAVE_ER_NEG      = 0x023B28E0  # (0x30 bytes) erupt: front over both bl 0x021EE3DC (@0x021D3AE6 resolution negate, @0x021EE4F6 continuous monster negate): native first, then TEST
CAVE_ER_EP       = 0x023B2910  # (0x100 bytes) erupt: E3 End-Phase walker front, fn of registry row 277 @0x0228EA88 (compiled C, erupt.c ER_EP)
CAVE_ST_FILT     = 0x023B2A10  # (0x90 bytes) strike: cls0 +08 Tribute-cost / target filter (compiled C, strike.c ST_FILT)
CAVE_ST_TGT      = 0x023B2AA0  # (0x20 bytes) strike: target-only filter for the candidate counter (compiled C, strike.c ST_TGT)
CAVE_ST_RES      = 0x023B2AC0  # (0x60 bytes) strike: cls0 +04 negate rider + draw 1 (compiled C, strike.c ST_RES)
CAVE_ST_PREB     = 0x023B2B20  # (0x20 bytes) strike: negate-reader list-search precheck: key 0x0DE4 -> negated
CAVE_ST_COND     = 0x023B2B40  # (0x20 bytes) strike: cls0 +0C can-draw-1 condition (compiled C, strike.c ST_COND; Gemini Spark's needs a draw-count row)
CAVE_ST_COND2    = 0x023B2B60  # (0x10 bytes) strike: S4 virtual cls2 +0C (code 2, compiled C, strike.c ST_COND2)
CAVE_ST_SEL2     = 0x023B2B70  # (0x80 bytes) strike: S4 virtual cls2 +14 declare-an-Attribute selector (DNA Transplant shape, compiled C, strike.c ST_SEL2)
CAVE_ST_RES2     = 0x023B2BF0  # (0x80 bytes) strike: S4 virtual cls2 +04 Attribute rider on every face-up monster (compiled C, strike.c ST_RES2)
CAVE_ST_VREC     = 0x023B2C70  # (0x20 bytes) strike: DATA: S4 virtual cls2 record (prefind_hook, class 2, zone 0x0E)
CAVE_DM_FRONT    = 0x023B2DD0  # (0x20 bytes) domain: D2 front over `ldr r7,=0x02298AD8 ; cmp r5,#0` @0x02197A14 in the battle calculator (Skyscraper's bonus site)
CAVE_DM_BONUS    = 0x023B2DF0  # (0xB0 bytes) domain: D2 +800 for a Tribute Summoned attacker of the Domain controller (compiled C, domain.c DM_BONUS)
CAVE_DM_COND3    = 0x023B2EA0  # (0xB0 bytes) domain: D3 cls3 +0C once per turn + 2800/1000 in hand (compiled C, domain.c DM_COND3)
CAVE_DM_COST3    = 0x023B2F50  # (0x20 bytes) domain: D3 cls3 +10 once-per-turn stamp (compiled C, domain.c DM_COST3)
CAVE_DM_RES3     = 0x023B2F70  # (0xE0 bytes) domain: D3 cls3 +04 Star Blast picker + 0x1F6A instance Level rider (compiled C, domain.c DM_RES3)
CAVE_DM_PRED     = 0x023B3050  # (0xA0 bytes) domain: D3 picker predicate: own hand 2800/1000 monster (compiled C, domain.c DM_PRED)
CAVE_EB_COND   = 0x023B30F0  # (0xC0 bytes) erebus: cls1 +0C cond: >= 2 distinct Monarch S/T in hand + Deck (C)
CAVE_EB_COST   = 0x023B31B0  # (0x150 bytes) erebus: cls1 +14 cost step machine: send 2 different Monarch S/T hand/Deck -> GY (C)
CAVE_EB_RES    = 0x023B3300  # (0xC0 bytes) erebus: cls1 +04 resolver: opponent GY card -> Deck + shuffle (C)
CAVE_EB_PRED   = 0x023B33C0  # (0x50 bytes) erebus: list predicate: Monarch S/T, not the first pick's cid (C)
CAVE_EB_ROWH   = 0x023B3410  # (0x80 bytes) erebus: cost row handler: hand test per index + Deck walker (C)
CAVE_EB_ROWS     = 0x023B3490  # (0xC0 bytes) erebus: DATA: virtual criteria rows 0xFFE0..0xFFEB; RELOCATED 2026-11-12 (session 2) into the zero hole after CAVE_EB_ROWH for Monarchic Perfection's 2 rows (0x023B3EB0 / 0xA0 is now a hole); RELOCATED AGAIN 2026-11-12 into the RESERVE-bump space (a 9th row for The First Monarch; the 0x80 B at 0x023B0978 are a hole)
CAVE_EB_H2       = 0x023B0020  # (0xD0 bytes) erebus: criteria miss-tail front (grown 2026-11-12 inside its 0xD0 hole for the Prime Monarch GY row); RELOCATED 2026-11-12 into the old March-lock hole (the old 0x90 B at 0x023B34F0 are now a hole)
CAVE_EB_H3     = 0x023B3580  # (0x30 bytes) erebus: invoker row-compute front
CAVE_EB_DATA   = 0x023B35B0  # (0x10 bytes) erebus: DATA: +0 first pick's cid, +4 MODE
CAVE_EB_COND2  = 0x023B35C0  # (0x100 bytes) erebus: E2 virtual cls2 +0C cond (C)
CAVE_EB_COST2  = 0x023B36C0  # (0x50 bytes) erebus: E2 virtual cls2 +10 cost: hand discard + OPT (C)
CAVE_EB_RES2   = 0x023B3710  # (0x20 bytes) erebus: E2 virtual cls2 +04: MODE reset + native GY->hand (C)
CAVE_EB_PRED2  = 0x023B3730  # (0x40 bytes) erebus: GY/Deck predicate ATK >= 2400 / DEF 1000 (C)
CAVE_EB_GYH    = 0x023B3770  # (0x30 bytes) erebus: GY monster row handler (C)
CAVE_EB_VREC   = 0x023B37A0  # (0x20 bytes) erebus: DATA: E2 virtual cls2 record
CAVE_EB_EHRES  = 0x023B37C0  # (0x30 bytes) erebus: ehther cls1 +04 resolver: native Deck SS (C)
CAVE_EB_EHDH   = 0x023B37F0  # (0x30 bytes) erebus: ehther Deck SS row handler (C)
CAVE_EB_EHTR   = 0x023B3820  # (0x50 bytes) erebus: ehther summon-rider list front @0x02268090 (source cid 0x1312 -> kind-2 node)
CAVE_EC_TINY   = 0x023B3990  # (0x10 bytes) escalation: cls0 cost (+0) / res (+4) for the Continuous Trap activation
CAVE_EC_COND   = 0x023B39A0  # (0x100 bytes) escalation: cls3 +0C cond: opponent's Main/Battle Phase, a Tribute-Summonable hand monster (compiled C)
CAVE_EC_COST   = 0x023B3AA0  # (0x30 bytes) escalation: cls3 +10 once-per-turn stamp (compiled C)
CAVE_EC_PRED   = 0x023B3AD0  # (0x50 bytes) escalation: hand predicate for Cry Havoc!'s resolver: Level 5+ (compiled C)
CAVE_EC_FRONT  = 0x023B54E0  # (0x40 bytes) [RELOCATED 2026-11-12 session 2: grew past 0x30 with the Masterplan arm; 0x023B3B20 / 0x30 is now a hole] escalation: front on the 3 BL callers of the per-cid predicate lookup 0x0220D7B4
CAVE_PM_COND     = 0x023B0D08  # (0x90 bytes) prime monarch: cls3 +0C cond: >= 2 Monarch S/T in the GY, once per turn (compiled C); in the old 0x023B0D08 hole (the former GYV table)
CAVE_PM_COST     = 0x023B0D98  # (0x20 bytes) prime monarch: cls3 +10 once-per-turn stamp (compiled C)
CAVE_PM_RES      = 0x023B0DB8  # (0xE8 bytes) prime monarch: cls3 +04 resolver: pick 2 Monarch S/T from the GY, return to the Deck, shuffle, draw 1 (compiled C)
CAVE_PM_TINY     = 0x023B0EA0  # (0x10 bytes) prime monarch: cls0 cost / res for the Continuous Trap activation
CAVE_EB_H4    = 0x023B3B50  # (0x20 bytes) erebus: ARM9 0x02023566 hand-offer (list B) front: Ehther -> 1
CAVE_EB_SPD     = 0x023B09F8  # (0x60 bytes) erebus: speed-lookup default-leaf front @0x021A894C: Ehther hand cls2 desc -> 2, Erebus GY desc -> 2 (Quick Effects); RELOCATED 2026-11-12 into the old Mega-Monarch TRIG hole (the 0x30 B at 0x023B3B70 are now a hole)
CAVE_EB_COND3 = 0x023B3BA0  # (0xC0 bytes) erebus: Ehther E2 virtual cls2 +0C cond (opponent's Main Phase, Ehther summonable from the hand, a Monarch S/T in the GY) (compiled C)
CAVE_EB_COST3 = 0x023B3C60  # (0x30 bytes) erebus: Ehther E2 virtual cls2 +10 cost: native GY banish (compiled C)
CAVE_EB_VREC2 = 0x023B3C90  # (0x20 bytes) erebus: DATA: Ehther E2 virtual cls2 record
CAVE_EC_PREH  = 0x023B3CB0  # (0x40 bytes) escalation: hand predicate for Ehther's E2 (hand card == Ehther) (compiled C)
CAVE_FM_COND  = 0x023B3CF0  # (0x80 bytes) first monarch E1 cls1 +0C cond (compiled C)
CAVE_FM_COST  = 0x023B3D70  # (0xD0 bytes) first monarch E1 cls1 +14 cost: discard 1 card (native hand cost over row 0xFFE8), then the DNA Transplant declare step (compiled C)
CAVE_FM_RES   = 0x023B3E40  # (0x70 bytes) first monarch E1 cls1 +04 resolver: permanent Attribute rider on itself (compiled C)
CAVE_FM_LOCK  = 0x023B3F50  # (0x70 bytes) first monarch: helper (side, card word) -> 1 when a face-up First Monarch forbids that Special Summon (compiled C)
CAVE_FM_TRIB  = 0x023B3FC0  # (0x70 bytes) first monarch: helper (player, summoned cid, cand side, cand slot) -> 1 when the First Monarch counts as 2 Tributes (compiled C)
CAVE_FM_LOCKF = 0x023B4030  # (0x30 bytes) first monarch: front over `bl 0x021AD8C4` @0x02269266 in the SS engine (tails to March's front)
CAVE_FM_M0F   = 0x023B4060  # (0x40 bytes) first monarch: front over the M0 hook BL @0x021AE14A (tails to mega_monarch's M0 stub)
CAVE_EB_FROWH = 0x023B40A0  # (0xA0 bytes) erebus E1 effect row handler: opponent's GY + field cards into the candidate list (compiled C)
CAVE_EB_RESX  = 0x023B4140  # (0x150 bytes) erebus cls1 +04 resolver v2: pick an opponent GY/field card (list picker) or, on cancel, a random opponent hand card; return it to the Deck (compiled C)
CAVE_PM_COND2 = 0x023B4350  # (0x100 bytes) prime monarch GY half: virtual cls2 +0C cond: OPT 0x54CF, SS room, another Monarch S/T in the GY (compiled C)
CAVE_PM_COST2 = 0x023B4450  # (0x90 bytes) prime monarch GY half: virtual cls2 +10 cost: native GY banish over row 0xFFE9 + OPT stamp (compiled C)
CAVE_PM_VREC  = 0x023B44E0  # (0x20 bytes) prime monarch GY half: DATA: virtual cls2 GY record {+04 0x0220731D GY self-SS}
CAVE_PM_POS   = 0x023B45A0  # (0x30 bytes) [relocated 2026-11-12: grew past 0x20 with the trap-monster flag; 0x023B4500..0x023B4520 is now a hole] prime monarch GY half: front over the GY self-SS resolver's BL @0x022074E6 (0x14CF -> Defense, else Jet Warrior's CAVE_JW_C2_POS)
CAVE_PM_PRED  = 0x023B4520  # (0x50 bytes) prime monarch GY half: row 0xFFE9 predicate: Monarch S/T, not the source card by GY index (compiled C)
CAVE_PM_GYH   = 0x023B4570  # (0x30 bytes) prime monarch GY half: row 0xFFE9 handler: plain GY walker + CAVE_PM_PRED (compiled C)
CAVE_PF_COND  = 0x023A58F0  # (0x140 bytes) monarchic perfection: cls1 +0C cond (compiled C, c/perfection.c); in a zero-byte hole (2026-11-12)
CAVE_PF_FROWH = 0x023AEFE0  # (0x80 bytes) monarchic perfection: row 0xFFEB handler: field candidates for the chosen effect (compiled C); in a zero-byte hole
CAVE_PF_COST  = 0x023AF060  # (0x20 bytes) monarchic perfection: cls1 +14 cost: native GY banish over row 0xFFEA (compiled C)
CAVE_PF_DATA  = 0x023AF080  # (0x10 bytes) monarchic perfection: DATA: +0 chosen effect, +4 menu page, +8 usable-effect mask
CAVE_PF_TINY  = 0x023AF090  # (0x10 bytes) monarchic perfection: cls0 cost / res for the Continuous Trap activation
CAVE_PF_TRIG  = 0x023AF0A0  # (0x30 bytes) monarchic perfection: front over `bl 0x02023C90` @0x02266524 in the summon-event Special-Summon block (posts event 5 to the opponent's 0x12F6)
CAVE_PF_RES   = 0x023B45D0  # (0x300 bytes) monarchic perfection: cls1 +04 resolver: two-page effect menu, list picker, destroy / Deck-top / banish / random discard (compiled C)
CAVE_EM_GYH     = 0x023B48D0  # (0x50 bytes) eidos monarch E1: row 0xFFD4 handler: Deck + GY candidates (compiled C) [2026-11-12 session 2, RESERVE 0x1AC00]
CAVE_EM_RES1    = 0x023B4920  # (0x100 bytes) eidos monarch E1: cls1 +04 resolver: list picker, Deck -> hand (0x021C72CC) or GY -> hand (0x021C7038), shuffle (compiled C)
CAVE_EM_TRIGF   = 0x023B4A20  # (0x20 bytes) eidos monarch E3: front over the bl 0x022391CC @0x02265D2A at the head of the summon dispatch 0x02265CF8 (event 7 -> CAVE_EM_POST)
CAVE_EM_POST    = 0x023B4A40  # (0x80 bytes) eidos monarch E3: poster: own Tribute Summon of a 2400+/1000 monster -> 0x021D3648 GY post for 0x1230 (compiled C)
CAVE_EM_COND3G  = 0x023B4AC0  # (0xA0 bytes) eidos monarch E3: virtual cls2 GY +0C cond (compiled C)
CAVE_EM_RES3G   = 0x023B4B60  # (0x100 bytes) eidos monarch E3: virtual cls2 +04: menu add-to-hand / Special Summon, GY -> hand or native GY self-SS (compiled C)
CAVE_EM_VREC3   = 0x023B4C60  # (0x20 bytes) eidos monarch E3: DATA: virtual cls2 GY record
CAVE_MON_NOMISS = 0x023B4C80  # (0x60 bytes) monarch set: never-miss-timing front over the You-can body's bl 0x021EE0E0 @0x021E510A (Monarch cids -> 0, else the Dragon Rulers' CAVE3_RUL_MISS)
CAVE_MP_COND2   = 0x023B4DE0  # (0x140 bytes) masterplan C2: virtual cls2 (banished zone 0xF) +0C cond (compiled C, c/masterplan.c) [RESERVE 0x1B400]
CAVE_MP_RES2    = 0x023B4F20  # (0x280 bytes) masterplan C2: +04 resolver: opponent monster picker, Deck/GY add, optional named-Monarch Normal Summon via Cry Havoc!'s machine (compiled C)
CAVE_MP_TGTH    = 0x023B51A0  # (0x130 bytes) masterplan C2: row 0xFFD7 handler: the opponent's face-up monsters with a same-Attribute 2400/1000 add (compiled C)
CAVE_MP_ADDH    = 0x023B52D0  # (0x50 bytes) masterplan C2: row 0xFFD8 handler: Deck + GY (compiled C)
CAVE_MP_APRED   = 0x023B5320  # (0x50 bytes) masterplan C2: row 0xFFD8 predicate: 2400 / 1000 and the chosen Attribute (compiled C)
CAVE_MP_NSPRED  = 0x023B5370  # (0x70 bytes) masterplan C2: Cry Havoc!'s hand predicate for 0x0D6A: the six named Monarchs (compiled C; routed by escalation's front)
CAVE_MP_DATA    = 0x023B5460  # (0x10 bytes) masterplan C2: DATA: +0 MODE, +4 chosen Attribute, +8 delegate flag
CAVE_MP_VREC    = 0x023B5470  # (0x20 bytes) masterplan C2: DATA: virtual cls2 record for the banished zone
CAVE_MP_H6F     = 0x023B5490  # (0x20 bytes) masterplan C2: front on the GY->banished gate 0x021C71C8 (0x0D6A -> post), tails to the Dragon Rulers' H6
CAVE_MP_H7F     = 0x023B54B0  # (0x30 bytes) masterplan C2: front on the banish override switch 0x021D1B98 (0x0D6A to 0xF -> the banish leaf), tails to the Rulers' H7
CAVE_FREE        = 0x023B5520  # first free address for FUTURE patches (the ceiling: 0 B left at RESERVE 0x1B400)
# *** NEVER TRUST A BYTE COUNT WRITTEN IN THIS COMMENT. ***  The ceiling is
#  OV5_RAM_BASE + OV5_NEW_LEN, which MOVES with RESERVE, and the live answer is
#  always that minus CAVE_FREE.  With RESERVE = 0x10000 the ceiling is
#  0x023AA120, so the free tail is 0x023AA120 - 0x0239E120 =
#  0xC000 == 49152 bytes.
#  This warning is not decorative: the figure here has been wrong TWICE.  It
#  said "0x1790 == 6032 bytes still free" when the true answer was 0x200, and
#  then "0x1D0 == 464 bytes" when the sentinel had already moved to 0x0239DFB0
#  and the truth was 0x170.  Compute it; do not read it.
#  CAVE_FREE itself is the first free ADDRESS, not the ceiling, so it does NOT
#  move when RESERVE grows -- enlarging the cave is purely additive and no
#  existing CAVE_* slot changes address.
# NOTE (in-game proven): the populate-'h' / deck-search COUNT path DOES map
# overlay 5 in a NORMAL DUEL -- both Reborn Tengu's self-SS selector and Gravekeeper's
# Recruiter's deck-search wrapper+filter run correctly from these ov5 caves in a duel.
# (The earlier "deck-search needs overlay 3" belief was a PUZZLE-mode confound: in a
# puzzle, overlay 41 -- not overlay 5 -- loads at 0x022C5900, so NO ov5 cave is mapped.
# Every ov5 cave stub is normal-duel-only.)
# ⚠️ "puzzles need overlay-3 hosting instead" (the old ending of this note) is NOT a
# usable plan: ov3 IS resident in every mode, but the engine CLEARS ov3's BSS at duel
# init over its original extent, so growing ov3's data into its BSS cannot hold code --
# proven by in-game canary (see notes/ov3-cave-findings.md and the KB fact
# mem.ov3_bss_is_cleared). A mode-independent cave needs a different host; the current
# candidate is appending to the ARM9 main section + raising the MAIN heap base literal
# (0x020AF120, main-section offsets 0xB90/0xB94, 0xCE4/0xCE8, 0x81558/0x8155C), which is
# the same shape as this module's arena-lo raise but has NO bss clear over it.


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _arm9_main(rom: "ndspy.rom.NintendoDSRom"):
    """Return ``(MainCodeFile, main_section)`` for the arm9 of *rom*.

    Works whether the arm9 is still BLZ-compressed (clean ROM) or already
    decompressed (after an earlier MainCodeFile edit in the chain).
    """
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == rom.arm9RamAddress)
    return mc, sec


def _raise_arena_lo(rom: "ndspy.rom.NintendoDSRom") -> None:
    """Raise the duel arena-lo literal to ARENA_LO_NEW (idempotent, via MainCodeFile)."""
    mc, sec = _arm9_main(rom)
    d = bytearray(sec.data)
    cur = struct.unpack_from("<I", d, ARENA_LO_OFF)[0]
    if cur == ARENA_LO_NEW:
        return                                  # already raised by an earlier patch
    assert cur == ARENA_LO_NATIVE, (
        f"arm9 arena-lo @0x{ARENA_LO_OFF:X} = 0x{cur:08X}; expected native "
        f"0x{ARENA_LO_NATIVE:08X} or raised 0x{ARENA_LO_NEW:08X} -- wrong base ROM?"
    )
    struct.pack_into("<I", d, ARENA_LO_OFF, ARENA_LO_NEW)
    sec.data = bytes(d)
    rom.arm9 = mc.save()                        # write arm9 back (decompressed, valid module params)


def _load_ov5_decompressed(rom: "ndspy.rom.NintendoDSRom") -> "ndspy.overlay.Overlay":
    """Return ov5's Overlay object (ndspy auto-decompresses ov.data on load)."""
    return rom.loadArm9Overlays([OV5_ID])[OV5_ID]


def _save_ov5(rom: "ndspy.rom.NintendoDSRom", ov, data: bytes) -> None:
    """Recompress ov5 *data*, store it in the ROM, and update the overlay table."""
    ov.data = bytes(data)
    ov.ramSize = len(data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed
    tbl = rom.arm9OverlayTable
    entry = OV5_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(data))
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    struct.pack_into("<I", tbl, entry + 0x1C,
                     ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def read_cave(rom: "ndspy.rom.NintendoDSRom", ram_addr: int, n: int) -> bytes:
    """Read *n* bytes back out of the appended ov5 region at *ram_addr*.

    Exists so a SHARED stub (one installed by whichever of several card patches
    runs first) can be made idempotent: install_cave() asserts its destination is
    all-zero and therefore raises on a second call at the same address.
    Returns b"" if ov5 has not been expanded yet.
    """
    ov = _load_ov5_decompressed(rom)
    data = bytes(ov.data)
    off = ram_addr - OV5_RAM_BASE
    if off < 0 or off + n > len(data):
        return b""
    return data[off:off + n]


def install_cave(rom: "ndspy.rom.NintendoDSRom", ram_addr: int, blob: bytes,
                 *, reserve: int) -> int:
    """Write *blob* into the appended ov5 region at *ram_addr* and ensure expansion.

    Idempotent for the expansion: grows ov5 to OV5_NEW_LEN and raises the duel
    arena-lo only if not already done.  Asserts the target slot is free (zero) and
    that *blob* fits in *reserve*.  Operates ON the live *rom* object (no file save);
    the caller saves the ROM afterwards.  Returns *ram_addr* (the cave address).
    """
    assert ram_addr % 4 == 0, f"cave 0x{ram_addr:08X} must be 4-aligned"
    assert OV5_NATIVE_END <= ram_addr, f"cave 0x{ram_addr:08X} is below the appended region"
    assert ram_addr + reserve <= OV5_RAM_BASE + OV5_NEW_LEN, (
        f"cave 0x{ram_addr:08X}+0x{reserve:X} overruns the reserved region"
    )
    assert len(blob) <= reserve, f"blob {len(blob)}B exceeds reserve 0x{reserve:X}"

    ov = _load_ov5_decompressed(rom)
    data = bytearray(ov.data)

    # --- grow ov5 once (idempotent) ---
    if len(data) == OV5_NATIVE_LEN:
        data += bytes(RESERVE)                  # append RESERVE zero bytes
    elif len(data) != OV5_NEW_LEN:
        raise AssertionError(
            f"ov5 length 0x{len(data):X} is neither native 0x{OV5_NATIVE_LEN:X} "
            f"nor expanded 0x{OV5_NEW_LEN:X}"
        )

    # --- write the blob into its (zero) slot ---
    off = ram_addr - OV5_RAM_BASE
    if bytes(data[off:off + len(blob)]) == blob:
        return ram_addr                         # already installed byte-for-byte (shared leaves: several modules write the same blob)
    assert all(data[off + i] == 0 for i in range(len(blob))), (
        f"ov5 cave 0x{ram_addr:08X} is not free ({len(blob)} bytes)"
    )
    data[off:off + len(blob)] = blob

    _save_ov5(rom, ov, bytes(data))
    _raise_arena_lo(rom)
    return ram_addr


# ---- Infernoble fronts (infernoble) ---------------------------------------------------------------------------
# Infernoble chains its own ov5 fronts AHEAD of several shared hook sites.  Other owners' verify() follow the chain with
# ik_tail() and require it to END at their own stub (accepting ANY Infernoble front hid a break
# behind one).  IK_NEXT = each front's fall-through for a non-Infernoble cid; infernoble.verify() proves every entry
# against the front's assembled bytes, so the map cannot drift from the code.
def ik_next() -> dict[int, int]:
    from otn_enhanced.effects import cave3
    return {CAVE_IK_DU_ROW: CAVE_IK_JO_ROW, CAVE_IK_JO_ROW: CAVE_IK_RC_ROW, CAVE_IK_RC_ROW: CAVE_ROWHOOK,
            CAVE_IK_CO_LATCH: CAVE_IK_RC_LATCH, CAVE_IK_RC_LATCH: CAVE_IK_R_LATCH, CAVE_IK_R_LATCH: CAVE_RIDERLATCH,
            CAVE_IK_CR_FRONT: cave3.CAVE3_SUMMONTRIG,
            CAVE_IK_HA_LEAVE: CAVE_IK_AL_LEAVE, CAVE_IK_AL_LEAVE: CAVE_IK_DU_LEAVE, CAVE_IK_DU_LEAVE: CAVE_IK_JO_LEAVE,
            CAVE_IK_JO_LEAVE: CAVE_IK_CO_LEAVE, CAVE_IK_CO_LEAVE: CAVE_IK_BR_LEAVE,
            CAVE_IK_BR_LEAVE: cave3.CAVE3_TGSH_ARMTRAMP,
            CAVE_IK_HO_PRENEG: 0x021FBC94, CAVE_IK_HO_PREPOST: 0x0223F8E4,
            CAVE_IK_CR_SPEED: CAVE_OQ_SPEED,
            CAVE_IK_HO_LOCK: CAVE_IK_RC_LOCK, CAVE_IK_RC_LOCK: 0x02237DBC}


def combo() -> bool:
    """MONARCH_COMBO=1: every Monarch module is applied in ONE ROM (scratch/_combo.py / build_monarch_all.py).  Order: mega_monarch first, then the
    support cards; each shared front tails to the previous owner instead of the chain's head."""
    import os
    return os.environ.get("MONARCH_COMBO", "1") == "1"     # default ON since the Monarch set shipped (2026-11-12); MONARCH_COMBO=0 for a single-card test build


def dc_next() -> dict[int, int]:
    """Disguise / Cursed Copycat Noble Arms fronts (disguise_copycat), each placed AHEAD of an existing owner: front ->
    the address it tail-calls for every other cid. disguise_copycat.verify() proves each entry against the front's
    assembled bytes. Kept apart from ik_next() because infernoble.verify() proves every ik_next entry against its OWN
    stubs."""
    from otn_enhanced.effects import cave3
    d = {CAVE_RV_H2: CAVE_BD_H2, CAVE_RV_H3: CAVE_BD_H3, CAVE_ED_H2: CAVE_BD_H2, CAVE_ED_H3: CAVE_BD_H3, CAVE_ES_H2: CAVE_BD_H2, CAVE_ES_H3: CAVE_BD_H3, CAVE_TS_H2: CAVE_BD_H2, CAVE_TS_H3: CAVE_BD_H3, CAVE_EM_H2: CAVE_BD_H2, CAVE_EM_H3: CAVE_BD_H3, CAVE_T1_H2: CAVE_BD_H2, CAVE_T1_H3: CAVE_BD_H3, CAVE_MP_H2: CAVE_BD_H2, CAVE_MP_H3: CAVE_BD_H3, CAVE_EB_H2: CAVE_BD_H2, CAVE_EB_H3: CAVE_BD_H3, CAVE_EB_H4: CAVE_BD_H4, CAVE_T1_H4: CAVE_BD_H4, CAVE_FB_H2: CAVE_BD_H2, CAVE_FB_H3: CAVE_BD_H3, CAVE_PT_H2: CAVE_BD_H2, CAVE_PT_H3: CAVE_BD_H3, CAVE_AG_H2: CAVE_MM_CH2, CAVE_AG_H3: CAVE_MM_CH3, CAVE_DC_H2: cave3.CAVE3_SSS_H2, CAVE_DC_H3: cave3.CAVE3_RUL_H3, CAVE_DC_MISS: CAVE_IK_AR_MISS,
            CAVE_DC_N1_FRONT: CAVE_IK_CO_STAT, CAVE_DC_H4: CAVE_IK_RO_H4,
            CAVE_MK_H2: CAVE_DC_H2, CAVE_MK_H3: CAVE_DC_H3,      # noble_knight_medraut fronts sit AHEAD of Disguise's
            CAVE_GF_H2: CAVE_MK_H2, CAVE_GF_H3: CAVE_MK_H3, CAVE_GF_H4: CAVE_DC_H4,   # immortal_phoenix_gearfried fronts sit AHEAD of those
            CAVE_GF_STAT: CAVE_DC_N1_FRONT, CAVE_GF_H1: cave3.CAVE3_RUL_H1,
            CAVE_PG_LEAVE: CAVE_IK_HA_LEAVE, CAVE_PG_MISS: CAVE_DC_MISS,
            CAVE_PD_MISS: CAVE_PG_MISS,
            CAVE_PD_H2: CAVE_GF_H2, CAVE_PD_H3: CAVE_GF_H3,
            CAVE_BD_H1: CAVE_GF_H1, CAVE_BD_H2: CAVE_PD_H2, CAVE_BD_H3: CAVE_PD_H3, CAVE_BD_H4: CAVE_GF_H4,
            CAVE_BD_C3MISS: CAVE_PD_MISS, CAVE_BD_C2W: 0x021B2B10, CAVE_BD_AI: CAVE_WR_AICLASS,
            CAVE_CORAL_MISS: CAVE_BD_C3MISS,
            CAVE_MM_ZH2: CAVE_BD_H2, CAVE_MM_ZH3: CAVE_BD_H3,
            CAVE_MM_RH2: CAVE_MM_ZH2, CAVE_MM_RH3: CAVE_MM_ZH3,
            CAVE_MM_CH2: CAVE_MM_RH2, CAVE_MM_CH3: CAVE_MM_RH3,
            CAVE_TN_H2: CAVE_BD_H2, CAVE_TN_H3: CAVE_BD_H3,
            CAVE_RT_H2: CAVE_BD_H2, CAVE_RT_H3: CAVE_BD_H3,      CAVE_RS_H2: CAVE_BD_H2, CAVE_RS_H3: CAVE_BD_H3,      # restoration fronts also sit AHEAD of Block Dragon's      # return_monarchs fronts sit AHEAD of Block Dragon's too (as tenacity's and mega_monarch's: a combined ROM needs them chained)      # tenacity's criteria fronts sit AHEAD of Block Dragon's (mega_monarch's sit ahead of Block Dragon's too: combining the two needs one of them re-pointed)
            CAVE_MA_C2W: CAVE_BD_C2W, CAVE_MA_TGT: cave3.CAVE3_SZ_TARGET}   # march fronts sit AHEAD of Block Dragon's C2W and Safe Zone's targeting stub   # mega_monarch's Zaborg criteria fronts sit AHEAD of Block Dragon's (2026-11-10)
            #   # coral_dragon never-miss front sits AHEAD of Block Dragon's (2026-11-09)   # block_dragon fronts sit AHEAD of the current heads (C2W -> Seal of Orichalcos' ov3 stub, AI -> Windrose's class-view stub)      # phoenix_gearblade's leave front sits AHEAD of the Arms chain (kept OUT of ik_next: infernoble.verify proves every ik_next entry against its OWN stubs)
    if combo():                                 # MONARCH_COMBO: mega_monarch's Caius->Raiza->Zaborg chain is the head, then tenacity -> return -> restoration (apply order)
        d.update({CAVE_TN_H2: CAVE_AG_H2, CAVE_TN_H3: CAVE_AG_H3, CAVE_RT_H2: CAVE_TN_H2, CAVE_RT_H3: CAVE_TN_H3,
                  CAVE_RS_H2: CAVE_RT_H2, CAVE_RS_H3: CAVE_RT_H3, CAVE_PT_H2: CAVE_RS_H2, CAVE_PT_H3: CAVE_RS_H3, CAVE_FB_H2: CAVE_PT_H2, CAVE_FB_H3: CAVE_PT_H3, CAVE_RV_H2: CAVE_FB_H2, CAVE_RV_H3: CAVE_FB_H3, CAVE_ED_H2: CAVE_RV_H2, CAVE_ED_H3: CAVE_RV_H3, CAVE_ES_H2: CAVE_ED_H2, CAVE_ES_H3: CAVE_ED_H3, CAVE_TS_H2: CAVE_ES_H2, CAVE_TS_H3: CAVE_ES_H3, CAVE_EM_H2: CAVE_TS_H2, CAVE_EM_H3: CAVE_TS_H3, CAVE_T1_H2: CAVE_EM_H2, CAVE_T1_H3: CAVE_EM_H3, CAVE_MP_H2: CAVE_T1_H2, CAVE_MP_H3: CAVE_T1_H3, CAVE_EB_H2: CAVE_MP_H2, CAVE_EB_H3: CAVE_MP_H3, CAVE_EB_H4: CAVE_T1_H4, CAVE_T1_H4: CAVE_BD_H4})
    return d


def dc_ahead_of(owner: int) -> set[int]:
    """*owner* and every front that chains (dc_next) onward to it: the set of BL targets a site may legitimately hold while *owner* is the
    owner that module's verify() is proving (later cards' fronts sit AHEAD of it)."""
    nxt = dc_next()
    out = {owner}
    for front in nxt:
        t = front
        for _ in range(16):
            if t == owner:
                out.add(front)
                break
            if t not in nxt:
                break
            t = nxt[t]
    return out


def dc_skip(t: int) -> int:
    """*t* with a Disguise front stepped over (for owner checks that compare a site's BL target directly)."""
    nxt = dc_next()
    while t in nxt:         # fronts may chain (Medraut's H2/H3 sit ahead of Disguise's)
        t = nxt[t]
    return t


def ik_walk(t: int) -> int:
    """Follow the Infernoble (and Disguise) front chain from address *t* to the first address that is neither
    (t itself if none)."""
    nxt = {**ik_next(), **dc_next()}
    for _ in range(16):
        if t not in nxt:
            return t
        t = nxt[t]
    raise AssertionError(f"Infernoble front chain loops at {t:#x}")


def bl_dst(blob, off: int, site: int) -> int:
    import struct as _s
    h1, h2 = _s.unpack_from("<HH", blob, off)
    o = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
    return site + 4 + (o - (1 << 23) if o & (1 << 22) else o)


def ik_tail(blob, off: int, site: int) -> int | None:
    """Where the BL at blob[off] (executing at RAM *site*) ends up after the Infernoble front chain, or None when that
    BL does not enter an Infernoble front at all."""
    import struct as _s
    h1, h2 = _s.unpack_from("<HH", blob, off)
    if (h1 & 0xF800) != 0xF000 or (h2 & 0xF800) != 0xF800 or bl_dst(blob, off, site) not in {**ik_next(), **dc_next()}:
        return None
    return ik_walk(bl_dst(blob, off, site))

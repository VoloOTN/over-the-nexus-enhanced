"""Card-text DSL: a spec that reads like the printed text, compiled to Thumb stubs plus the table
record that wires them in.

    SPEC = ignition(
        0x13B8,
        cost=tribute_self(),
        limit=once_per_turn(),
        effect=[draw_and_reveal(1), if_(revealed.is_level(1), draw(1))],
        slots=(RES, COND, COST), phantom=0x1436)
    main, verify = make(SPEC, card_props("LIGHT", "Spellcaster", 1, 0, 0), out="...nds")

A card module is then just its spec and its card props; name and printed text come from
`card_text.CARD_TEXT[cid]`. Every phrase carries the engine trap it hides (the latch is stamped in
the COST; the condition skips its query once the cost has run; a deck peek happens BEFORE the
queued draw), so an author cannot forget them.

Timings: `ignition` (one cls3 record + 3 stubs) and pure-data table clones
(`normal_summon_send_from_deck`, `battle_destroyed_draw`, combined by `table_card`; no stubs, rows in
cls1/cls2/criteria/lists). A timing is any spec with `compile(view) -> Compiled(stubs, rows)`.
Each stub goes to the ov3 pool (needs step 0, `system.ov3_compact`) or the ov5 cave, chosen per slot
by its address.
`gy_summon_spell` (Normal Spell: cls0 record rewritten in place + criteria row + 4 ov5 stubs) is
built from the phrase verbs `main_phase_1_only`, `once_per_turn`, `no_battle_phase`,
`special_summon_from_gy`, `lose_lp_each`; its cond/cost/resolver/select stubs are composed from them.
`synchro_summoned_draw` (enumeration-site hook + cls2 chain draw) and `fusion_to_synchro_effect` (Fusion donor
-> Synchro Effect Monster) are composed with `card(...)` and `archetype_member`.
`negate_with_native_condition` (Counter Trap: one cond-dispatcher branch retargeted, no stubs).
New verbs: add a class with `lower(b, ctx)`. New timings: add a spec class with `compile`.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import ndspy.rom

from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7
from otn_enhanced.asm.effect_shim import _bl as _shim_bl
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.data import card_text
from otn_enhanced.data.card_stats import apply_stats_and_text, find_pac
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.effects.common import Checker, Ov, Table, cave_holds, insert_sorted, keys, rows, table_intact
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target as common_bl_target
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3

SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"   # stock + step 0
from otn_enhanced.data.card_stats import TEXT_LANGS

# cls3 = the ignition table. Its count is hardcoded in find_event_handler, so inserts are
# count-neutral: `phantom` is the cid dropped to make room.
CLS3 = Table(base=0x02279D74, count=0x308, stride=24, fmt="<IIIIII", wide=True,
             label="cls3 ignition record")

# Framework slots a cls3 ignition record borrows (cid-blind generic engine routines).
NATIVE_COND = 0x021F06E8    # generic offer gate
NATIVE_TRIB = 0x021E50CC    # "Tribute this card"
TURNLOG_KIND_ACTIVATION = 1


def _in_ov5(addr: int) -> bool:
    """A slot lives in the appended ov5 cave iff it is past ov5's native end; anything below is ov3."""
    return addr >= ov5_cave.OV5_NATIVE_END


# -- resolver lowering state ----------------------------------------------------------------
@dataclass
class _Ctx:
    side: object = R4                 # controller, loaded once
    revealed: object | None = None    # register holding the peeked cid, once something reveals
    n_labels: int = 0

    def label(self) -> str:
        self.n_labels += 1
        return f"L{self.n_labels}"


# -- actions (the effect text) ---------------------------------------------------------------
@dataclass(frozen=True)
class draw:
    count: int

    def lower(self, b, ctx):
        b.call("draw", ctx.side, self.count)






# -- conditions on the revealed card --------------------------------------------------------
@dataclass(frozen=True)
class _IsLevel:
    level: int

    def lower_skip(self, b, ctx, skip):
        assert ctx.revealed is not None, "nothing was revealed"
        b.call("is_monster", ctx.revealed)
        b.if_eq(R0, 0, skip)
        b.call("cid_level", ctx.revealed)
        b.if_ne(R0, self.level, skip)


class revealed:
    @staticmethod
    def is_level(n: int) -> _IsLevel:
        return _IsLevel(n)


# -- costs / limits --------------------------------------------------------------------------
@dataclass(frozen=True)
class tribute_self:
    """'Tribute this card' as the cost (the engine's own routine)."""


@dataclass(frozen=True)
class once_per_turn:
    """'can only be activated once per turn' -- latch stamped in the cost, checked in the condition."""


# -- timing + card data ---------------------------------------------------------------------
@dataclass(frozen=True)
class Row:
    """One count-neutral sorted insert: `record` into `table`, spending `phantom`."""
    table: Table
    record: tuple
    phantom: int
    stock_copies: int = field(default=1, repr=False)   # >1: stock holds the phantom this many times; one is spent


@dataclass(frozen=True)
class Edit:
    """Rewrite the donor's one record in `table` in place (no insert); `native` is its stock content."""
    table: Table
    cid: int
    native: tuple
    patched: tuple


@dataclass(frozen=True)
class Compiled:
    stubs: tuple = ()   # ((addr, blob, what), ...)
    rows: tuple = ()    # (Row, ...)
    edits: tuple = ()   # (Edit, ...) in-place rewrites of a record the donor already owns
    installs: tuple = ()   # (fn(rom, view), ...) shared-hook / registry wiring, run after rows + edits
    posts: tuple = ()      # (fn(out_path), ...) ARM9 edits on the saved ROM, run before the card text
    checks: tuple = ()     # (fn(c, rom, view), ...) extra verify() assertions


@dataclass(frozen=True)
class ignition:
    cid: int
    cost: tribute_self
    limit: once_per_turn
    effect: list
    slots: tuple[int, int, int]   # resolver, condition, cost; each is ov5 if >= OV5_NATIVE_END, else ov3 pool
    phantom: int                  # cls3 cid dropped to keep the table count-neutral

    def compile(self, view=None) -> Compiled:
        res, cond, cost = self.slots
        blobs = (_resolver(self, res), _condition(cond), _cost(cost))
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        stubs = tuple(zip(self.slots, blobs, ("resolver", "condition", "cost")))
        return Compiled(stubs, (Row(CLS3, (self.cid, res | 1, 0, cond | 1, cost | 1, 0), self.phantom),))


# -- pure-data timings: clone a native card's rows --------------------------------------------
# Tables the engine dispatches on. Counts mirror literals the engine reads, so inserts are count-neutral.
_CLS_FMT = "<HHIIIII"       # u16 cid, u16 hi, five u32 action slots
LIST_CODE7 = Table(0x0228F7AC, 0x67, 2, "<H", label="code-7 (Normal Summon only) trigger list")
LIST_106 = Table(0x0226E990, 0x6A, 2, "<H", label="list106 (battle && destroyed && to-GY)")
CLS1 = Table(0x022860D4, 0x535, 24, _CLS_FMT, label="cls1 record")
CLS2 = Table(0x02275C04, 0x2B9, 24, _CLS_FMT, label="cls2 record")
CRITERIA = Table(0x022713C4, 0x56C, 12, "<HHII", label="criteria row")
DRAW_COUNT = Table(0x022704A4, 189, 4, "<Hh", label="draw-count row")



def _template(view, table: Table, cid: int, slots: tuple | None = None) -> tuple:
    """The one row native card `cid` owns in `table`; its action slots must be exactly `slots`."""
    hits = [r for r in rows(view, table) if r[0] == cid]
    assert len(hits) == 1, f"{cid:#06x} owns {len(hits)} rows in {table.label}, expected 1"
    assert slots is None or hits[0][2:] == slots, (
        f"{cid:#06x} template drifted: {[hex(v) for v in hits[0][2:]]}")
    return hits[0]














LEAVE_MASK = Table(0x0226EC1C, 0x98, 4, "<Hh", label="leave-mask row")
LIST_30 = Table(0x0226E904, 0x1E, 2, "<H", label="list30")
_DECK_SEARCHER = 0x0223BC3C




# -- Normal Spell timing: "Special Summon from your GY, then lose LP" ---------------------------------
# Natives the spell stubs call (KB: dispatch.gy_multi_summon_resolver, dispatch.multiselect_target_template,
# dispatch.lp_pay_primitive; the rest are cited in notes/soul-charge-findings.md, UNVERIFIED here).
CLS0 = Table(0x0227E64C, 0x51A, 24, "<6I", wide=True, label="cls0 spell record")
_DUEL_STATE = 0x0229DD14       # +0x48 phase (2 = MP1)
_PHASE_STATE = 0x0229AAFC      # [+0x70] = resolver phase; 0x78 = final






# `once_per_turn` (above, the ignition limit) lowers differently in a Spell: a turn node on the card's
# own cid, posted in the cost and tested in the condition (skipped on the desc[+7] re-check).


















# -- T.G. monster timings: hand Special Summon + End-Phase search + archetype membership -----------------
# Both timings wire through the SHARED tg_table trampolines (hand-SS @0x0224C026, leave-arm @0x021C8216),
# which Warwolf / Rush Rhino also ride; this file never installs a second hook, it registers a cid.
# Native addresses below are inherited from tg_striker.py (KB: see notes/tg-striker-findings.md), UNVERIFIED here.
_CAN_SS = 0x021AD870            # canSS(side) -> bool
_MONSTER_COUNT = 0x021ACF68     # monster_count(side) -> count (masks side&1)
_HAS_SETCODE = 0x020240D8
TG_SETCODE = 0x5C
CLS2_SEARCH_RESOLVER = 0x02207EF5   # native add-to-hand / player-choice deck-search resolver
CLS2_ALWAYS_ELIGIBLE = 0x0224A115
CLS2_DELAYED_END_PHASE = 0x021E50DD  # delayed End-Phase "sent from field this turn" classifier
REG_ENDPHASE_RESOLVER = 0x02254221   # the delayed End-Phase registrar (Darksoul's; KEPT)
REG_ROW_ADDR = 0x0228E600            # the spare registry row whose CID is repointed
REG_ROW_PHANTOM = 0x1A9F
# The criteria table counted PAST its 0xFFFF sentinel (1391, not 0x56C): how the original patch reads it.
CRITERIA_PAST_SENTINEL = Table(0x022713C4, 1391, 12, "<HHII", label="E2 populate")
POP_DECK_ZONE, POP_FLAGS = 0x0000, 0x00000002   # deck zone; the filter stub does all the filtering


def _deck_search_wrapper(filt: int) -> EffectBuilder:
    """Botanical Girl's deck-search wrapper, BL re-encoded, filter literal repointed (pool word at +0x20)."""
    wb = EffectBuilder()
    wb.insn("PUSH", "{R1, R2, R3, LR}")
    wb.insn("ADD", "R3, R0, #0x0")
    wb.insn("MOV", "R0, #0x2")
    wb.raw(0x5E1A)                       # LDRSH R2, [R3, R0] (the encoder has no LDRSH)
    wb.insn("STR", "R2, [SP, #0x8]")
    wb.insn("LDR", "R2, [R3, #0x8]")
    wb.insn("STR", "R2, [SP, #0x0]")
    wb.insn("STR", "R0, [SP, #0x4]")
    wb.insn("ADD", "R0, R1, #0x0")
    wb.insn("LDRH", "R1, [R3, #0x0]")
    wb.ldr_const(2, filt | 1)
    wb.insn("ADD", "R3, SP, #0x8")
    wb.call_addr(_DECK_SEARCHER)
    wb.insn("POP", "{R1, R2, R3, PC}")
    wb.raw(0x46C0)                       # nop: the pool must sit at +0x20
    return wb


@dataclass(frozen=True)
class only_opponent_controls_monster:
    """'If only your opponent controls a monster' -- canSS(side) && you control none && opponent controls some."""
    calls = frozenset({_CAN_SS, _MONSTER_COUNT})

    def lower_cond(self, b):
        b.prologue(save=[R4])
        b.insn("ADD", "R4, R0, #0x0")        # r4 = side
        b.call_addr(_CAN_SS)
        b.if_eq(R0, 0, "no")
        b.call_addr(_MONSTER_COUNT, R4)
        b.if_ne(R0, 0, "no")                 # you control a monster
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R0, R0, R4")          # r0 = 1 - side = opponent
        b.call_addr(_MONSTER_COUNT)
        b.if_eq(R0, 0, "no")                 # opponent controls none
        b.epilogue(ret=1)
        b.label("no")
        b.epilogue(ret=0)






@dataclass(frozen=True)
class special_summon_self_from_hand:
    """'You can Special Summon this card (from your hand)' -- the OFFER is forced by the shared hand-SS
    trampoline (the eligibility dispatch alone decides it; retargeting the dispatch tree or editing the
    donor's records was proven NOT to work), so this registers the card's condition stub there."""
    when: object    # a condition with lower_cond(b)
    slot: int       # ov3 pool address of the condition stub

    def compile(self, view, cid) -> Compiled:
        assert not _in_ov5(self.slot), "hand-SS condition must live in the ov3 pool"
        b = EffectBuilder()
        self.when.lower_cond(b)
        blob = b.assemble(self.slot)
        assert_thumb1_only(blob, self.slot)

        def install(rom, view):
            from otn_enhanced.effects.tg_table import register_tg_handss
            register_tg_handss(rom, view.buf, cid, self.slot, ov3=True)

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            from otn_enhanced.effects.tg_table import SS_HOOK_SITE, tg_handss_ok
            c.ok(tg_handss_ok(rom, view.buf, cid),
                 f"E1 shared hand-SS hook installed @0x{SS_HOOK_SITE:08X}, cid 0x{cid:04X} registered")
            ins = decode_thumb(blob, self.slot, overlay_data=bytes(view.buf), ram_base=view.base)
            c.eq({i.branch_target for i in ins if i.mnemonic == "BL"}, set(self.when.calls),
                 "E1 condition BLs -> the condition's engine calls")

        return Compiled(((self.slot, blob, "hand-SS condition"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class add_from_deck_end_phase:
    """'Once per turn, during the End Phase, if this card is in the GY because it was destroyed on the field
    and sent there this turn: add 1 <archetype> monster from your Deck to your hand, except this card.'

    Four pieces, any one of which alone fires nothing: the shared on-destruction arming trampoline (gates on
    DESTROYED, so Tribute / Synchro Material deliberately do not arm); the registry row's CID repointed at the
    donor KEEPING resolver 0x02254221 (this INVOKES the effect at End Phase); a cls2 insert (native
    add-to-hand pick menu); a populate insert (the candidate pool: the filter stub + a deck-search wrapper)."""
    set_code: int
    except_self: bool
    slots: tuple[int, int]      # (filter, wrapper) ov3 pool addresses
    phantoms: tuple[int, int]   # (cls2, populate) cids dropped
    populate_stock_copies: int = 1
    shared_invoke: bool = False   # True: INVOKE through the shared multi-cid registry-invoke trampoline
                                  # (tg_table.invoke_tg_endphase) instead of repointing a spare registry row --
                                  # for when every spare row on resolver 0x02254221 is spent

    def compile(self, view, cid) -> Compiled:
        filt, wrap = self.slots
        assert self.except_self and not any(_in_ov5(a) for a in self.slots)
        fb = EffectBuilder()
        fb.prologue(save=[R3])
        fb.insn("LDR", "R0, [SP, #0x8]")
        fb.insn("LDR", "R0, [R0, #0x0]")
        fb.insn("LSL", "R0, R0, #0x12")
        fb.insn("LSR", "R0, R0, #0x12")
        fb.ldr_const(1, cid)
        fb.insn("CMP", "R0, R1")
        fb.insn("BEQ", "reject")             # 'except this card'
        fb.insn("MOV", f"R1, #0x{self.set_code:X}")
        fb.call_addr(_HAS_SETCODE)
        fb.if_eq(R0, 0, "reject")
        fb.epilogue(ret=1)
        fb.label("reject")
        fb.epilogue(ret=0)
        wb = _deck_search_wrapper(filt)
        blobs = (fb.assemble(filt), wb.assemble(wrap))
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        stubs = tuple(zip(self.slots, blobs, ("except-self set-code filter", "deck-search wrapper")))
        ph2, php = self.phantoms
        rows_ = (Row(CLS2, (cid, 0, CLS2_SEARCH_RESOLVER, 0, CLS2_ALWAYS_ELIGIBLE, CLS2_DELAYED_END_PHASE, 0), ph2),
                 Row(CRITERIA_PAST_SENTINEL, (cid, POP_DECK_ZONE, wrap | 1, POP_FLAGS), php,
                     self.populate_stock_copies))

        def install(rom, view):
            from otn_enhanced.effects.tg_table import arm_tg_leave_trigger, invoke_tg_endphase
            if self.shared_invoke:
                invoke_tg_endphase(rom, view.buf, cid, ov3=True)
            else:
                res, cur = view.unpack(REG_ROW_ADDR, "<IH")
                if not (res == REG_ENDPHASE_RESOLVER and cur == cid):
                    assert res == REG_ENDPHASE_RESOLVER and cur == REG_ROW_PHANTOM, (
                        f"registry row @0x{REG_ROW_ADDR:08X} = res 0x{res:08X} cid 0x{cur:04X} "
                        f"(expected phantom 0x{REG_ROW_PHANTOM:04X} w/ resolver 0x{REG_ENDPHASE_RESOLVER:08X})")
                    view.set_u16(REG_ROW_ADDR + 4, cid)      # the cid only; keep the resolver
            arm_tg_leave_trigger(rom, view.buf, cid, ov3=True)

        def check(c, rom, view):
            if self.shared_invoke:
                from otn_enhanced.effects.tg_table import tg_reg_ok
                c.ok(tg_reg_ok(rom, view.buf, cid), "E2 reg-walk hook -> the shared invoke trampoline, list carries the donor")
                return
            c.eq(view.unpack(REG_ROW_ADDR, "<IH"), (REG_ENDPHASE_RESOLVER, cid),
                 f"E2 registry row @0x{REG_ROW_ADDR:08X} keeps resolver 0x{REG_ENDPHASE_RESOLVER:08X}, "
                 f"cid repointed to the donor")

        return Compiled(stubs, rows_, installs=(install,), checks=(check,))






@dataclass(frozen=True)
class SetCodeTable:
    """An ARM9 archetype member table: sorted u16 cids, count hardcoded in its consumers (edited IN PLACE)."""
    name: str
    base: int
    count: int
    pool_ptrs: tuple   # words holding `base`
    count_imms: tuple  # `movs r2,#count` halfwords


TG_TABLE = SetCodeTable("T.G.", 0x0209CB48, 0x13, (0x02023F3C,), (0x02023F38,))
XSABER_TABLE = SetCodeTable("X-Saber", 0x0209CB6E, 0x14, (0x02023BA0, 0x02023DE4), (0x02023B84, 0x02023DE0))


@dataclass(frozen=True)
class archetype_member:
    """The card counts as a member of `table`'s archetype: its cid joins the ARM9 set-code table, dropping
    `phantom` -- the card's own reserved Konami ID (count-neutral, as the consumers hardcode the count)."""
    table: SetCodeTable
    phantom: int

    def compile(self, view, cid) -> Compiled:
        t = self.table

        def post(out):
            from otn_enhanced.effects import common
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            a9 = common.view(rom)
            for p in t.pool_ptrs:
                assert a9.u32(p) == t.base, f"{t.name} consumer pool @0x{p:08X} moved"
            for p in t.count_imms:
                assert a9.u16(p) == 0x2200 | t.count, f"{t.name} count immediate @0x{p:08X} moved"
            cur = list(a9.unpack(t.base, f"<{t.count}H"))
            assert cid not in cur and self.phantom in cur, f"{t.name} set-code table = {[hex(x) for x in cur]}"
            new = sorted((set(cur) - {self.phantom}) | {cid})
            with common.arm9_edit(rom) as w:
                w.pack(t.base, f"<{t.count}H", *new)
            rom.saveToFile(out)

        def check(c, rom, view):
            from otn_enhanced.effects import common
            tbl = list(common.view(rom).unpack(t.base, f"<{t.count}H"))
            c.ok(cid in tbl and self.phantom not in tbl and tbl == sorted(tbl) and len(tbl) == t.count,
                 f"{t.name} table: 0x{cid:04X} in, phantom 0x{self.phantom:04X} out, sorted")

        return Compiled(posts=(post,), checks=(check,))


_GET_DEF = 0x0202AC6C
CRITERIA_1389 = Table(0x022713C4, 1389, 12, "<HHII", label="A2 populate")   # how this timing's original counts it
_BOTANICAL = 0x1ED4                   # real Effect Monster whose wrapper is cloned; must stay untouched




# -- Normal Summon: Special Summon from hand or Deck, negated, no Synchro Material ----------------------
# Natives inherited from tour_guide.py (git history), UNVERIFIED here; see notes/tour-guide-findings.md.
RIDER_ATTACH = Table(0x0228F750, 0x2E, 2, "<H", label="rider attach list (kind 3)")      # the node is only WRITTEN for members
















@dataclass(frozen=True)
class card:
    """A card made of several timings: each effect supplies `compile(view, cid) -> Compiled`; merged in order."""
    cid: int
    effects: tuple

    def __init__(self, cid, *effects):
        object.__setattr__(self, "cid", cid)
        object.__setattr__(self, "effects", effects)

    def compile(self, view) -> Compiled:
        parts = [e.compile(view, self.cid) for e in self.effects]
        return Compiled(*(tuple(x for p in parts for x in getattr(p, f))
                          for f in ("stubs", "rows", "edits", "installs", "posts", "checks")))








@dataclass(frozen=True)
class normal_spell:
    """cls0 record of the donor Spell rewritten in place: +04 resolver, +0C condition; no criteria row.
    `effect` supplies lower_cond / lower_resolver. slots = (resolver, condition), ov5 cave."""
    cid: int
    native: tuple                    # the donor's stock cls0 record, asserted at build
    effect: object
    slots: tuple[int, int]

    def compile(self, view=None) -> Compiled:
        res, cond = self.slots
        blobs = []
        for addr, lower in ((res, self.effect.lower_resolver), (cond, self.effect.lower_cond)):
            b = EffectBuilder()
            lower(b)
            blob = b.assemble(addr, pad="nop")
            assert_thumb1_only(blob, addr)
            blobs.append(blob)
        stubs = tuple(zip(self.slots, blobs, ("resolver", "condition")))
        return Compiled(stubs, (), (Edit(CLS0, self.cid, self.native, (self.cid, res | 1, 0, cond | 1, 0, 0)),))


def _patch_bytes(view, addr: int, stock: bytes, new: bytes, what: str) -> None:
    cur = view.blob(addr, len(new))
    if cur != new:
        assert cur == stock, f"{what} @{addr:#x} = {cur.hex()}, not stock {stock.hex()}"
        view.write(addr, new)


# Equip target lock: the donor's Reptile arm becomes the "Ancient Gear" arm shape on another set-code thunk.




# After-damage-calculation attacker-equip walk (Thorn of Malice rides the same branch).




_ZONE_WORD = 0x0229ACD8        # zone word = base + (side&1)*0xB3C + slot*0x14; bit 16 = Normal Summoned this turn
_TURNLOG_POST_FN = 0x021D2584  # POST(side, key, kind, 0) onto the turn log
















NOMI_CLASS_2_TABLE = SetCodeTable("nomi class 2", 0x0209BE9C, 0x39, (0x0202321C,), (0x020231E0,))
_TURNLOG_QUERY, _TURNLOG_POST, _HOPT_KIND = 0x021A14E9, 0x021D2585, 1
_TAG_YOU_CAN, _NATIVE_OFFER_COND, _TARGET_STEP = 0x021E51E5, 0x021F03B5, 0x02235605
LIST_NS_OR_SS = Table(0x0228F60A, 0x18, 2, "<H", label="N-or-SS trigger list")


@dataclass(frozen=True)
class hand_special_summon_by_gy_attribute:
    """'Must be Special Summoned (from your hand) by having exactly N <ATTRIBUTE> monsters in your GY': no summon
    registry row (the Summon is costless), one ov5 condition stub = free zone 0x021B9ECC && canSS 0x021AD870 &&
    0x021B1810(side, attribute) == count, registered with the SHARED tg_table hand-SS trampoline (hook 0x0224C026,
    ridden by the T.G. cards too; this verb never installs a second hook)."""
    attribute: int
    count: int
    slot: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import tg_table
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(0x021B9ECC, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.call_addr(0x021AD870, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.call_addr(0x021B1810, R4, self.attribute, via=R3)
        b.insn("CMP", f"R0, #0x{self.count:X}")
        b.insn("BNE", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)

        def install(rom, view):
            tg_table.register_tg_handss(rom, view.buf, cid, self.slot)

        def check(c, rom, view):
            c.ok(tg_table.tg_handss_ok(rom, view.buf, cid), "hand-SS trampoline row")

        return Compiled(((self.slot, blob, "hand-SS condition"),), installs=(install,), checks=(check,))




def _hopt_you_can_stub(slot4: int, cid: int) -> bytes:
    """cls1 +10: 'You can' 0x021E51E5; on Yes post (side, cid, 1, 0) -- declining is free."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.call_addr(_TAG_YOU_CAN, via=R2)
    b.insn("CMP", "R0, #0x1")
    b.insn("BNE", "out")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.turnlog_post(R0, cid, _HOPT_KIND, via=R4)
    b.insn("ADD", "R0, R5, #0x0")
    b.label("out")
    b.insn("POP", "{R4, R5, PC}")
    blob = b.assemble(slot4, pad="nop")
    assert_thumb1_only(blob, slot4)
    return blob


def _timing_arms_install(rom, view):
    """Shared class-2 'You can' timing: the ov3 hook + the ov5 stub carrying every registered arm (idempotent)."""
    from otn_enhanced.effects import timing_class_hook as tch
    from otn_enhanced.effects.common import rewrite_shared
    tch.apply(view.buf, quiet=True)
    base = ov5_cave.CAVE_TIMINGHOOK
    rewrite_shared(rom, base, tch.RESERVE, tch.stub(base), tch.stub(base, tch.ARMS), "timing stub")


def _timing_arms_check(c, rom, view):
    from otn_enhanced.effects import timing_class_hook as tch
    base = ov5_cave.CAVE_TIMINGHOOK
    blob = tch.stub(base, tch.ARMS)
    c.ok(len(blob) <= tch.RESERVE and ov5_cave.read_cave(rom, base, len(blob)) == blob,
         f"shared timing stub @{base:#x} carries the arms ({len(blob)} B)")
    tch.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg))


_PHASE_STATE, _DESTROYED = 0x0229AAFC, 0x0229C314
_PLAYER_BASE = 0x0229AC94






















_RES_STATE, _UI_RESULT, _DECK_COUNT_WORD = 0x0229AAFC, 0x0229DD94, 0x0229ACA4




_FUSION_RECIPE_A = 0x02270B94




LIST_CODE9 = Table(0x0228F63A, 0x1F, 2, "<H", label="code-9 (when Special Summoned) trigger list")








_TURNLOG_QUERY_ODD, _TURNLOG_POST_ODD = 0x021A14E9, 0x021D2585
_COPY_EXEMPT_BX, _HAS_CANDIDATE, _YESNO, _DECK_TO_HAND = 0x021D2B89, 0x021F0821, 0x0219AAAD, 0x02207EF5
_H2_SITE, _H3_SITE = 0x02243F24, 0x02243F62




_CHAIN_PUSH, _CHAIN_POP = 0x021D28A5, 0x021D2965




_IS_MONSTER = 0x02029E60                       # bit 15 of card_intid; rejects Spells/Traps










@dataclass(frozen=True)
class fusion_recipe_blanked:
    """The donor's fusion recipe row A[row] materials -> 0x3FFF (the CPU planner reads it without an is-Fusion gate)."""
    row: int
    stock: tuple

    def compile(self, view, cid) -> Compiled:
        addr = _FUSION_RECIPE_A + self.row * 8

        def install(rom, view):
            cur = tuple(view.unpack(addr, "<4H"))
            if cur != (cid, 0x3FFF, 0x3FFF, 0):
                assert cur == self.stock, f"recipe A[{self.row}] is {[hex(v) for v in cur]}"
                view.pack(addr + 2, "<2H", 0x3FFF, 0x3FFF)

        def check(c, rom, view):
            c.eq(tuple(view.unpack(addr, "<4H")), (cid, 0x3FFF, 0x3FFF, 0), f"fusion recipe A[{self.row}] blanked")

        return Compiled(installs=(install,), checks=(check,))


@dataclass(frozen=True)
class card_prop_copied_from_template:
    """card_prop <- a native template's record with the donor cid (same card type), and the donor's card_genre
    word set (stock asserted). E.g. Formula Synchron 0x239E (the only type-39 Synchro Tuner Effect record)."""
    ref_cid: int
    card_type: str
    donor_genre: int
    new_genre: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.data import card_genre as pcg
        from otn_enhanced.data.card_stats import find_pac
        type_code = ERA2_CARD_TYPE_REVERSE[self.card_type]

        def post(out):
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            fid, orig, archive = find_pac(rom)
            pac = bytearray(orig)
            files = {f.get_clean_name().lower(): f for f in archive.files}
            cp, gn = files["card_prop.bin"], files["card_genre.bin"]
            n = (cp.size - 8) // 8
            assert n == (gn.size - 8) // 8, "card_prop / card_genre not parallel"

            def at(k):
                hits = [i for i in range(n)
                        if int.from_bytes(pac[cp.address + 8 + i * 8:cp.address + 16 + i * 8], "little") & 0x3FFF == k]
                assert len(hits) == 1, f"{k:#x}: {hits}"
                return hits[0]

            i, r = at(cid), at(self.ref_cid)
            ref = int.from_bytes(pac[cp.address + 8 + r * 8:cp.address + 16 + r * 8], "little")
            assert (ref >> 32) & 0x3F == type_code, f"reference {self.ref_cid:#x} is not type {type_code}"
            po, go = cp.address + 8 + i * 8, gn.address + 8 + i * 8
            if (int.from_bytes(pac[po:po + 8], "little") >> 32) & 0x3F != type_code:
                pac[po:po + 8] = ((ref & ~0x3FFF) | cid).to_bytes(8, "little")
            g = int.from_bytes(pac[go:go + 8], "little")
            if g != self.new_genre:
                assert g == self.donor_genre, f"genre drifted: {g:#x}"
                pac[go:go + 8] = self.new_genre.to_bytes(8, "little")
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out)

        def check(c, rom, view):
            _, pac, archive = find_pac(rom)
            files = {f.get_clean_name().lower(): f for f in archive.files}
            cp, gn = files["card_prop.bin"], files["card_genre.bin"]
            i = next(k for k in range((cp.size - 8) // 8)
                     if int.from_bytes(pac[cp.address + 8 + k * 8:][:8], "little") & 0x3FFF == cid)
            prop = int.from_bytes(pac[cp.address + 8 + i * 8:][:8], "little")
            c.eq((prop >> 32) & 0x3F, type_code, f"card_type = {self.card_type}")
            c.ok(int.from_bytes(pac[gn.address + 8 + i * 8:][:8], "little") in pcg.accepted(cid, self.new_genre),
                 "card_genre updated")

        return Compiled(posts=(post,), checks=(check,))
































_LEAVE_SITE, _LEAVE_NATIVE = 0x021C8078, bytes.fromhex("00200690")
_C5_STUB, _C5_RESERVE = 0x0220A158, 104        # dead resolver body of phantom 0x0EAB's cls0[86]
_C5_HOST_HEAD = bytes.fromhex("7cb5051c16480021")
ELEMENTAL_LORD_CIDS = (0x1110, 0x1C1A, 0x181F, 0x190B)   # Grandsoil, Moulinglacia, Pyrorex, Windrose
_SKIP_BP_KEY = 0x1502


def _skip_bp_stub(base: int, cids: tuple) -> bytes:
    b = EffectBuilder()
    for c in cids[:-1]:
        b.ldr_const(0, c)
        b.insn("CMP", "R4, R0")
        b.insn("BEQ", "go")
    b.ldr_const(0, cids[-1])
    b.insn("CMP", "R4, R0")
    b.insn("BNE", "out")
    b.label("go")
    b.insn("LDR", "R0, [SP, #0x2c]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "out")
    b.insn("LDR", "R0, [SP, #0x94]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "out")
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("LDR", f"R0, [SP, #{0x98 + 0x14:#x}]")
    b.ldr_const(1, _DUEL_STATE)
    b.insn("LDR", "R1, [R1, #0x34]")
    b.insn("MOV", "R2, #0x11")
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "post")
    b.insn("MOV", "R2, #0x21")
    b.label("post")
    b.ldr_const(1, _SKIP_BP_KEY)
    b.insn("MOV", "R3, #0x0")
    b.call_addr(_TURNLOG_POST, via=R4)
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [SP, #{:#x}]".format(0x18 + 0x14))
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    b.label("out")
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [SP, #0x18]")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


@dataclass(frozen=True)
class leave_field_skip_next_battle_phase:
    """'If this face-up card leaves the field, skip the Battle Phase of your next turn.' ONE ov3 stub shared by every
    card in `cids` (the family), reached by a BL over the leave dispatcher's straight-line
    `movs r0,#0 ; str r0,[sp,#0x18]` @0x021C8078 and living in phantom 0x0EAB's dead cls0 resolver body 0x0220A158:
    cid in cids, left the field, was face-up -> post (owner, key 0x1502, kind 0x21 on the owner's turn / 0x11
    otherwise, 0). The skip-BP predicate 0x0224CF90 matches key 0x1502 only at countdown 0. A ROM carrying a stub for a
    prefix of `cids` (an earlier family member's build) is upgraded in place. Stub is 104 B max (the family is full)."""
    cids: tuple

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        assert cid in self.cids
        blob = _skip_bp_stub(_C5_STUB, self.cids)
        assert_thumb1_only(blob, _C5_STUB)
        assert len(blob) <= _C5_RESERVE, f"skip-BP stub {len(blob)} B > {_C5_RESERVE}"
        priors = [_skip_bp_stub(_C5_STUB, self.cids[:k]) for k in range(1, len(self.cids))]
        want = tch._bl(_LEAVE_SITE, _C5_STUB)

        def install(rom, view):
            cur = view.blob(_C5_STUB, len(blob))
            if cur != blob:
                assert view.blob(_C5_STUB, 8) == _C5_HOST_HEAD or any(
                    view.blob(_C5_STUB, len(p)) == p for p in priors), "0x0220A158 is not the stock dead body or a family stub"
                view.write(_C5_STUB, blob)
            site = view.blob(_LEAVE_SITE, 4)
            if site != want:
                assert site == _LEAVE_NATIVE, f"leave site {_LEAVE_SITE:#x} is not stock"
                view.write(_LEAVE_SITE, want)

        def check(c, rom, view):
            c.ok(view.blob(_C5_STUB, len(blob)) == blob and view.blob(_LEAVE_SITE, 4) == want,
                 f"leave hook @{_LEAVE_SITE:#x} -> shared ov3 stub @{_C5_STUB:#x} with cids {[hex(x) for x in self.cids]}")
            c.eq(view.u32(0x0224CFD8), _SKIP_BP_KEY, "skip-BP predicate still reads key 0x1502")

        return Compiled(installs=(install,), checks=(check,))




CANNOT_SS_TABLE = SetCodeTable("cannot-be-Special-Summoned", 0x0209BD6C, 0x30, (0x0202340C,), (0x020233C8,))












LIST_CODE78 = Table(0x0228F598, 0x10, 2, "<H", label="code-7-or-8 (Normal / Flip Summon) trigger list")
FLIPPED_FACE_UP_TABLE = SetCodeTable("flipped-face-up", 0x0209BB5C, 0x13, (0x020231C4,), (0x020231AC,))




@dataclass(frozen=True)
class card_genre_word:
    """The donor's card_genre.bin word (stock must be 0): e.g. bit 22 '(Flip)' so a battle flip counts as
    'flipped face-up'. `word` is the 3DS value for the card."""
    word: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.data import card_genre as pcg
        from otn_enhanced.rom.pac import parse_pac

        def offset(pac, archive):
            files = {f.get_clean_name().lower(): f for f in archive.files}
            cpf, gnf = files["card_prop.bin"], files["card_genre.bin"]
            for i in range((cpf.size - 8) // 8):
                if int.from_bytes(pac[cpf.address + 8 + i * 8:][:8], "little") & 0x3FFF == cid:
                    return gnf.address + 8 + i * 8
            raise RuntimeError(f"cid {cid:#x} not in card_prop")

        def post(out):
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            fid, orig, archive = pcg._find_pac(rom)
            pac = bytearray(orig)
            g = offset(orig, archive)
            cur = int.from_bytes(pac[g:g + 8], "little")
            if cur != self.word:
                assert cur == 0, f"card_genre for {cid:#x} is {cur:#x}, not stock vanilla"
                pac[g:g + 8] = self.word.to_bytes(8, "little")
                rom.files[fid] = bytes(pac)
                rom.saveToFile(out)

        def check(c, rom, view):
            bin2 = bytes(rom.getFileByName("Data_arc_pac/bin2.pac"))
            g = offset(bin2, parse_pac(bin2, "bin2.pac"))
            c.ok(int.from_bytes(bin2[g:g + 8], "little") in pcg.accepted(cid, self.word),
                 f"card_genre = {self.word:#x}")

        return Compiled(posts=(post,), checks=(check,))


@dataclass(frozen=True)
class card_props:
    attribute: str
    race: str
    level: int
    atk: int
    defense: int
    card_type: str = "Effect Monster"


# -- Stat edits: card_prop.bin (+ card_intid.bin) only, no overlay, no text ---------------------------
# card_intid.bin is indexed by (cid - 0xD48); bounds literals of the lookup 0x02029E1C (arm9), which reads
# the table at [[lit+0x10]+0x3C].
INTID_BASE_CID = 0x0D48


class card_stat_edit:
    """`card_stat_edit(cid, copy_from=TEMPLATE_CID, level=8, atk_encoded=195, ...)`: the donor's card_prop
    record <- the template's (re-stamped with this cid), then the named decoded fields over it.
    card_intid.bin duplicates the monster / field-spell classification, so it is re-derived from the new
    record: low 14 bits = card_prop index, bit 15 = MONSTER (0x02029E60), bit 14 = FIELD SPELL (0x02029E80).
    The field-zone placement at 0x02217EDE branches on 0x02029E80, NOT on card_prop's subtype, so without
    this a converted Field Spell lands in an ordinary spell/trap zone. Edits apply in order."""

    def __init__(self, cid: int, copy_from: int | None = None, **fields):
        self.cid, self.copy_from, self.fields = cid, copy_from, fields


def _stat_files(rom):
    fid, pac, archive = find_pac(rom)
    files = {f.get_clean_name().lower(): f for f in archive.files}
    return fid, pac, files["card_prop.bin"], files.get("card_intid.bin")


def _prop_off(pac, cpf, cid: int) -> int:
    for i in range((cpf.size - 8) // 8):
        off = cpf.address + 8 + i * 8
        if int.from_bytes(pac[off:off + 8], "little") & 0x3FFF == cid:
            return off
    raise ValueError(f"Could not find target index for CID {cid} in card_prop.bin")


def _intid_want(iv: int, fields: dict) -> int:
    want = iv & 0x3FFF
    if fields["card_type"] not in ("Spell Card", "Trap Card"):
        want |= 0x8000
    if fields["card_type"] == "Spell Card" and fields["spell_trap_subtype"] == "Field":
        want |= 0x4000
    return want


def apply_card_stat_edits(edits, *, src: str, out: str) -> None:
    from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    fid, pac, cpf, cif = _stat_files(rom)
    pac = bytearray(pac)
    for e in edits:
        off = _prop_off(pac, cpf, e.cid)
        old = GC.decode_entry(bytes(pac[off:off + 8]))
        new = dict(old)
        if e.copy_from is not None:
            tmpl = GC.decode_entry(bytes(pac[_prop_off(pac, cpf, e.copy_from):][:8]))
            tmpl["card_id"] = e.cid
            new.update(tmpl)
        new.update(e.fields)
        print(f"New fields for CID {e.cid}: { {k: v for k, v in new.items() if old.get(k) != v} }")
        pac[off:off + 8] = GC.encode_entry(new)
        if cif is not None:
            ioff = cif.address + (e.cid - INTID_BASE_CID) * 2
            iv = int.from_bytes(pac[ioff:ioff + 2], "little")
            want = _intid_want(iv, new)
            if want != iv:
                print(f"  card_intid[0x{e.cid:04X}]: 0x{iv:04X} -> 0x{want:04X}")
                pac[ioff:ioff + 2] = want.to_bytes(2, "little")
    rom.files[fid][:] = pac       # in place: Session.normalise guarantees a bytearray
    rom.saveToFile(out)


def verify_card_stat_edits(edits, out: str) -> bool:
    from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    _, pac, cpf, cif = _stat_files(rom)
    c = Checker(f"card stat edits ({out})")
    for e in edits:
        got = GC.decode_entry(bytes(pac[_prop_off(pac, cpf, e.cid):][:8]))
        c.ok(all(got.get(k) == v for k, v in e.fields.items()), f"0x{e.cid:04X} card_prop fields")
        if e.copy_from is not None and not e.fields:       # record == template's, bar the cid
            u = lambda k: int.from_bytes(pac[_prop_off(pac, cpf, k):][:8], "little") & ~0x3FFF
            c.eq(u(e.cid), u(e.copy_from), f"0x{e.cid:04X} record copied from 0x{e.copy_from:04X}")
        if cif is not None:
            iv = int.from_bytes(pac[cif.address + (e.cid - INTID_BASE_CID) * 2:][:2], "little")
            c.eq(iv, _intid_want(iv, got), f"0x{e.cid:04X} card_intid classification bits")
    return c.result()


# -- Fusion donor -> Synchro Effect Monster, and "If a monster is Synchro Summoned: Draw 1" -------------
# Native addresses below are inherited from hyper_librarian.py (git history), UNVERIFIED here; see
# notes/hyper-librarian-findings.md.
HOOK_RESERVE, RES_RESERVE = 0x100, 0x60


@dataclass(frozen=True)
class fusion_to_synchro_effect:
    """Donor conversion: an effectless Fusion becomes a Synchro Effect Monster. Its fusion recipe row is
    blanked (the CPU planner reads it without an is-Fusion gate) and its card_prop record is copied from a
    Synchro template with a Synchro-only card_genre. Stats and text follow from `card_props` / CARD_TEXT."""
    row: int
    stock: tuple      # the recipe row's stock materials, asserted at build

    def compile(self, view, cid) -> Compiled:
        def install(rom, view):
            _fusion_recipe_kill(view.buf, cid, self.row, self.stock)

        def post(out):
            _synchro_card_prop_and_genre(out, cid)

        def check(c, rom, view):
            c.eq(view.unpack(_FUSION_TABLE_A + self.row * 8, "<4H"),
                 (cid, _FUSION_DEAD_MATERIAL, _FUSION_DEAD_MATERIAL, 0), f"fusion recipe A[{self.row}] neutralised")

        return Compiled(installs=(install,), posts=(post,), checks=(check,))


_FUSION_TABLE_A = 0x02270B94
_FUSION_DEAD_MATERIAL = 0x3FFF      # >= 0x33 so it reads as a literal cid, above the max real cid, never satisfiable
_SYNCHRO_REFERENCE_CID = 0x23FE     # Laval Twin Slayer, a Synchro Effect Monster: its whole card_prop record is the template
_SYNCHRO_DONOR_GENRE = 0x0000000020200000      # bits {21 nomi, 29 FUSION}: the plain effectless-Fusion value
_SYNCHRO_NEW_GENRE = (_SYNCHRO_DONOR_GENRE & ~(1 << 29)) | (1 << 36)       # clear FUSION, set SYNCHRO, NO bit 35 TUNER
assert _SYNCHRO_NEW_GENRE == 0x0000001000200000


def _fusion_recipe_kill(ov, cid: int, row: int, stock: tuple) -> None:
    """Blank the donor's fusion recipe materials. Count-neutral, idempotent. Not for the player (can_fusion_summon rejects on
    is_fusion before the table) but for the CPU AI planner 0x022112B2, which reads fusion_material_count with no is_fusion gate."""
    addr = _FUSION_TABLE_A + row * 8
    off = addr - 0x02141700
    result, m1, m2, m3 = struct.unpack_from("<4H", ov, off)
    assert result == cid, f"fusion table A row {row} @0x{addr:08X} holds result 0x{result:04X}, expected the donor 0x{cid:04X}"
    if (m1, m2) == (_FUSION_DEAD_MATERIAL, _FUSION_DEAD_MATERIAL):
        return
    assert (m1, m2, m3) == (*stock, 0), f"fusion row {row} materials are ({m1:#06x}, {m2:#06x}, {m3:#06x}), not the stock {stock}"
    struct.pack_into("<2H", ov, off + 2, _FUSION_DEAD_MATERIAL, _FUSION_DEAD_MATERIAL)


def _synchro_card_prop_and_genre(out_path: str, cid: int) -> None:
    """A: copy the reference Synchro's whole card_prop record (cid swapped). B: rewrite the card_genre record's category tags.
    Same-size in-place writes; the text pass rebuilds bin2.pac and re-reads it from the saved ROM."""
    from otn_enhanced.data.card_stats import find_pac
    new_type = ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]
    rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
    fid, orig, archive = find_pac(rom)
    pac = bytearray(orig)
    cpf = next(f for f in archive.files if f.get_clean_name().lower() == "card_prop.bin")
    gnf = next(f for f in archive.files if f.get_clean_name().lower() == "card_genre.bin")
    n = (cpf.size - 8) // 8
    assert n == (gnf.size - 8) // 8 == 4305, "card_prop / card_genre not parallel"
    prop_off = genre_off = ref_off = None
    for i in range(n):
        o = cpf.address + 8 + i * 8
        k = int.from_bytes(pac[o:o + 8], "little") & 0x3FFF
        if k == cid and prop_off is None:
            prop_off, genre_off = o, gnf.address + 8 + i * 8
        if k == _SYNCHRO_REFERENCE_CID and ref_off is None:
            ref_off = o
    assert prop_off is not None and ref_off is not None, "donor or reference cid not in card_prop.bin"
    ref = int.from_bytes(pac[ref_off:ref_off + 8], "little")
    assert (ref >> 32) & 0x3F == new_type, "reference is not a Synchro Effect Monster"
    cur = int.from_bytes(pac[prop_off:prop_off + 8], "little")
    if (cur >> 32) & 0x3F != new_type:
        pac[prop_off:prop_off + 8] = ((ref & ~0x3FFF) | cid).to_bytes(8, "little")
    g = int.from_bytes(pac[genre_off:genre_off + 8], "little")
    if g != _SYNCHRO_NEW_GENRE:
        assert g in (_SYNCHRO_DONOR_GENRE, _SYNCHRO_NEW_GENRE), f"card_genre is {g:#018x}, not the stock effectless-Fusion value"
        pac[genre_off:genre_off + 8] = _SYNCHRO_NEW_GENRE.to_bytes(8, "little")
    assert len(pac) == len(orig), "bin2.pac changed size -- these edits are in place"
    rom.files[fid] = bytes(pac)
    rom.saveToFile(out_path)








# -- compilation -----------------------------------------------------------------------------
@dataclass(frozen=True)
class c_source:
    """A resolver written in C (asm/cc.py) instead of DSL verbs: ``effect=c_source(path, size)``.
    *size* is the slot's reservation (the CAVE3_*/CAVE_* comment); the build fails if the compiled stub is larger."""
    path: str
    size: int


def _resolver(spec: ignition, addr: int) -> bytes:
    if isinstance(spec.effect, c_source):
        from otn_enhanced.asm.cc import compile_c
        blob = compile_c(Path(spec.effect.path), addr)
        assert len(blob) <= spec.effect.size, f"{spec.effect.path}: {len(blob)} B > slot {spec.effect.size} B"
        return blob
    b, ctx = EffectBuilder(), _Ctx()
    b.prologue(save=[R4, R5])
    b.ctx_field("controller", dest=R4)
    for a in spec.effect:
        a.lower(b, ctx)
    b.epilogue(ret=0)
    return b.assemble(addr)


def _condition(addr: int) -> bytes:
    b = EffectBuilder()
    b.prologue(save=[R4])
    b.insn("ADD", "R4, R0, #0x0")                  # R4 = descriptor
    b.ctx_field("cost_ran", dest=R0, ctx=R4)
    b.if_ne(R0, 0, "chain")                        # mid-activation re-check: never re-query
    b.ctx_field("controller", dest=R0, ctx=R4)
    b.ctx_field("cid", dest=R2, ctx=R4)
    b.turnlog_query(R0, R2, TURNLOG_KIND_ACTIVATION)
    b.if_eq(R0, 0, "chain")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    b.label("chain")
    b.insn("ADD", "R0, R4, #0x0")
    b.bl(NATIVE_COND)
    b.insn("POP", "{R4, PC}")
    return b.assemble(addr)


def _cost(addr: int) -> bytes:
    b = EffectBuilder()
    b.prologue(save=[R4])
    b.insn("ADD", "R4, R0, #0x0")
    b.ctx_field("controller", dest=R0, ctx=R4)
    b.ctx_field("cid", dest=R1, ctx=R4)
    b.turnlog_post(R0, R1, TURNLOG_KIND_ACTIVATION)
    b.insn("ADD", "R0, R4, #0x0")
    b.bl(NATIVE_TRIB)
    b.insn("POP", "{R4, PC}")
    return b.assemble(addr)


def compile_card(spec: ignition):
    """-> ((resolver, cond, cost) bytes, cls3 record tuple)."""
    c = spec.compile()
    return tuple(blob for _, blob, _ in c.stubs), c.rows[0].record


# -- Elemental HERO Shadow Mist: "If this card is Special Summoned / sent to the GY: You can add ...", once per turn
_SM_STOCK_SRC = "data/over_the_nexus/working/rom.nds"






def bl_target(pair: bytes, src: int) -> int:
    """Decode a two-halfword Thumb BL at *src* (-1 if it is not one)."""
    w1, w2 = struct.unpack("<HH", pair)
    if w1 >> 11 != 0x1E or w2 >> 11 != 0x1F:
        return -1
    off = ((w1 & 0x7FF) << 12) | ((w2 & 0x7FF) << 1)
    if off & (1 << 22):
        off -= 1 << 23
    return src + 4 + off








# -- Assault Synchron: hand Special Summon + burn, Dragon Synchro leaves -> revive from the GY ---------------
_AS_TURNLOG_QUERY, _AS_CANSS, _AS_DUEL_STATE = 0x021A14E8, 0x021AD870, 0x0229DD14
_AS_REVIVE_RESOLVER, _AS_OFFFIELD_PICKER = 0x02207191, 0x02235605






# -- Crimson Blader: "destroys an opponent's monster by battle and sends it to the GY: opponent cannot summon Lv5+" ----




# -- criteria rows past index 0: inserted IMMEDIATELY after the donor's existing rows ------------------------
def _append_criteria_row(view, cid: int, row: tuple, phantom: int, before: list) -> None:
    """The criteria resolver adds r4 to the LEFTMOST row, so row order = row number; spend `phantom` count-neutrally."""
    recs = list(rows(view, CRITERIA))
    mine = [r for r in recs if r[0] == cid]
    if mine[:len(before) + 1] == before + [row]:
        return
    assert mine == before, f"expected donor criteria rows {before}, got {mine}"
    ks = [r[0] for r in recs]
    assert ks.count(phantom) == 1, f"criteria phantom {phantom:#06x} must own exactly one row"
    src = ks.index(phantom)
    dst = max(i for i, k in enumerate(ks) if k == cid) + 1
    recs.pop(src)
    recs.insert(dst - 1 if src < dst else dst, row)
    for i, r in enumerate(recs):
        view.pack(CRITERIA.addr(i), CRITERIA.fmt, *r)
    assert keys(view, CRITERIA) == sorted(keys(view, CRITERIA)), "criteria unsorted"


# -- Accel Synchro Stardust Dragon: Synchro Summoned revive a Tuner; Quick Effect Tribute for Stardust Dragon ----






# -- Psi-Reflector: summoned -> search a named group; reveal a card -> revive from the GY with a Level rider -------






# -- T.G. Warwolf: E1 hand Special Summon in response to a Lv<=4 Special Summon; E2 End-Phase search under a swapped cid --








# -- Double Evolution Pill: banish a Dinosaur + a non-Dinosaur from hand and/or GY; Special Summon a Lv7+ Dinosaur ----


# -- Karakuri Muso mdl 818 "Haipa": must attack if able; to DEF when attacked / after attacking -----------------
KARAKURI_TABLE = SetCodeTable("Karakuri", 0x0209CC16, 0x16, (0x02023F4C,), (0x02023F48,))








# -- Souleating Oviraptor: take a Dinosaur from the Deck to hand or GY; destroy a low-level Dinosaur, revive one -----




# -- Masked HERO Dark Law: Masked HERO member + Fusion class 5; opponent's cards banished; hand banish on a Deck add --
_DL_ARM9 = 0x02000000








# -- Obedience Schooled: no monsters -> SS 3 low-level Beasts (different names) from the Deck, negated, destroyed ----


# -- Steam Synchron: opponent's Main Phase Quick Effect Synchro Summon -- a pure DATA transplant of Formula Synchron ----


# -- Neo Space Connector: Normal Summoned -> SS a Neo-Spacian / Neos from hand or Deck; Tribute -> revive one ------




# -- Brilliant Fusion: Continuous Spell, Fusion Summon a Gem-Knight using Deck materials at 0/0, destroy on leave, discard -> gain --




# -- Orient Dragon: "If this card is Synchro Summoned: target 1 Synchro Monster your opponent controls; banish it" -----


# -- Nikitama / Sakitama-style Spirit extra-Normal-Summon grant: six ov3 fronts on the shared Normal Summon path -----










# -- Sekka's Light: draw 2 with no S/T in the GY, lock own S/T activations for the Duel; GY: reveal a monster, shuffle, draw ---


# -- NEXT: Normal Trap, Special Summon any number of "Neo-Spacian" / Neos with different names from hand and/or GY, negated ---


# -- Scrap Archfiend: an effectless Fusion donor becomes an effectless Synchro Monster ------------------------------


# -- Unknown Synchron: hand Special Summon if only the opponent controls a monster, once per Duel this way --------------


# -- Animadorned Archosaur: Normal / Special Summoned -> destroy a Dinosaur from hand or field, add a same-Level monster or a Pill ----




# -- Karakuri Komachi mdl 224 "Ninishi": must attack, toggle position when attack-targeted, extra Normal Summon of a Karakuri ----


# -- Revolution Synchron: hand Synchro material (first pick) + GY self-Special Summon through a VIRTUAL GY-action row ----










































































@dataclass(frozen=True)
class synchro_materials_synchro_only_attack_twice_negate_activation_and_destroy_it_once_per_turn_revive_shooting_star_dragon_on_leave:
    """Shooting Quasar Dragon (Stardust Dragon 0x211B donor, LIGHT / Dragon / Synchro Effect Monster / Level 12 / 4000 / 4000): 'materials: 1 Synchro
    Tuner + 2 or more non-Tuner Synchro monsters; can attack twice each Battle Phase; once per turn when a card or effect is activated that targets...
    negate the activation and destroy it; if this card leaves the field, Special Summon 1 "Shooting Star Dragon" from the Extra Deck'. Parts A/B/D/E/F/H
    are small in-place table / branch edits, I the Synchro-only material gate, J/K the negate + once-per-turn cls3 shims, M the Extra-Deck revive, N the
    leave trampoline through the shared T.G. hook, O the double-attack list. Original code embedded verbatim and run in `install` in the old order; the
    five live stubs go to the ov3 pool (CAVE3_QSR_*). The check is the old verify body (it diffs overlay 3 against the clean `SRC` ROM)."""

    def compile(self, view, cid) -> Compiled:
        import os
        import struct
        import ndspy.rom
        from otn_enhanced.rom.overlay_io import load_overlay3, RAM_BASE
        from otn_enhanced.data.card_stats import apply_stats_and_text
        from otn_enhanced.effects.common import thumb_bl
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import cave3
        from otn_enhanced.knowledge.check_allocations import parse_cave3_slots
        from otn_enhanced.effects.common import ov3_off as _off

        SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"   # stock + step 0 (the stubs live in its freed ov3 runs)
        OUT = "data/over_the_nexus/working/rom_shooting_quasar.nds"     # standalone output (orchestrator overrides)

        DONOR_CID = 0x211B          # Majestic Star Dragon -> becomes Shooting Quasar Dragon (cid KEPT)

        # --- PART A: LIST_A (the "exact material count" list) ---
        LIST_A       = 0x02275AB8   # sorted u16 cid list; membership => extras forbidden
        LIST_A_COUNT = 0x10         # 16 — hard-coded as `movs r2,#0x10` at LIST_A_COUNT_IMM
        LIST_A_COUNT_IMM = 0x02248268   # the count immediate in material_rule_class
        LIST_B_COUNT_IMM = 0x0224824C   # the count immediate in min_material_count (guard only; untouched)

        # Phantom substituted for 0x211B in LIST_A. Requirements: no card_prop record (so it
        # can never be summoned and can never reach the classifier), zero references anywhere,
        # and 0x208B < p < 0x219B so LIST_A stays strictly ascending at index 3.
        # Verified: 0x20BD has no card_prop record and scores 0/0/0 halfword hits across
        # overlay 3 / ARM9 / overlay 5 — the only candidate in that window clean on all three.
        # (LIST_A already contains the phantoms 0x0E6C / 0x2525 / 0x2526, so unreachable cids
        # are an established, engine-tolerated pattern here.)
        LIST_A_PHANTOM = 0x20BD

        SYNCHRO_PIVOT_LIT = 0x02248544   # a literal inside the INNER material predicate that must be 0x2346 (sanity anchor)

        # --- PART O: the DOUBLE-ATTACK list ("this card can attack twice each Battle Phase") ---
        # Same primitive as LIST_A: a sorted u16 cid list binary-searched by the ARM9 helper
        # 0x02022E14(r0=cid, r1=list, r2=count), with the count as an inline immediate:
        #
        #   0x021A3CFA  bl   0x021A36EC   ; r0 = this monster's cid
        #   0x021A3CFE  ldr  r1,[pc,#..]  ; r1 = 0x0226D712        <- DBLATK_LIST
        #   0x021A3D00  movs r2,#0xF      ; r2 = 15                <- DBLATK_COUNT_IMM
        #   0x021A3D04  bl   0x02022E14   ; sorted binary search
        #   0x021A3D0A  beq  ...          ; miss -> per-cid switch (CONDITIONAL double-attackers)
        #   0x021A3D0C  movs r0,#1        ; HIT  -> "can attack twice"
        #
        # The list has exactly ONE literal reference in the whole overlay (0x021A3F84), so membership
        # is the entire static grant. The two lists immediately after it are the same shape and each
        # read true end-to-end, which is what makes the identification safe rather than a guess:
        #   0x0226D730 (ref 0x021A6D98) DIRECT ATTACK  - Nightmare Horse, Amethyst Cat, Unifrog, ...
        #   0x0226D764 (ref 0x021A7434) PIERCING       - Airknight Parshath, Spear Dragon, Bladedge, ...
        #
        # NOTE the grant is a BOOLEAN (`movs r0,#1`), not a count. "Attacks = number of non-Tuner
        # materials" is therefore NOT expressible here -- Shooting Star Dragon's "up to 5" runs through
        # a different path entirely (the summon-FSM scratch at 0x0229AAFC +0x74 count / +0x78 result).
        # Quasar deliberately ships the flat "twice", and the card text says exactly that.
        DBLATK_LIST      = 0x0226D712
        DBLATK_COUNT     = 0x0F          # 15 -- hard-coded as `movs r2,#0xF` at DBLATK_COUNT_IMM
        DBLATK_COUNT_IMM = 0x021A3D00
        DBLATK_LIST_LIT  = 0x021A3F84    # the one literal-pool word holding DBLATK_LIST (sanity anchor)
        DBLATK_NEXT_LIST = 0x0226D730    # the DIRECT-ATTACK list abuts ours -- overrun tripwire

        # Phantom dropped to make room for 0x211B, count-neutrally. Requirement here is the MIRROR of
        # LIST_A's: since we are REMOVING this cid, it must not be a real card (else that card silently
        # loses its double attack). 0x18B9 is absent from all 4306 card records in cards_text.json, i.e.
        # it has no card_prop record at all. Every other entry in the list is a real, canonical
        # double-attacker (Hayabusa Knight, Mataza the Zapper, Cyber Twin Dragon, ...), so 0x18B9 is the
        # only safe choice.
        DBLATK_PHANTOM = 0x18B9

        # --- PART D: the donor's named-material leaf ("Majestic Dragon" + "Stardust Dragon") ---
        NAMED_MAT_BRANCH = 0x02248778    # the ONE `b` reaching the donor's named-material leaf (guarded by cmp r5,#0x211B)
        NAMED_MAT_LEAF   = 0x02248A04    # that leaf: material must be Majestic Dragon 0x20F4 or Stardust 0x1E36, else reject
        GENERIC_ALLOW    = 0x02248A70    # the switch's own default leaf: `movs r0,#1; pop {r1-r7,pc}` (unconditional ALLOW)
        GENERIC_ALLOW_BYTES = bytes.fromhex("0120febd")   # movs r0,#1 ; pop {r1,r2,r3,r4,r5,r6,r7,pc}

        # --- PART E: the donor's SECOND named-material leaf, inside the third predicate 0x02248A88 ---
        PAIR_BRANCH   = 0x02248CAA   # the ONE `b` reaching it; guarded by `cmp r5, 0x211B` ([sp,#0xc] base 0x219D - 0x82)
        PAIR_LEAF     = 0x0224916A   # "materials #1+#2 must be {Majestic Dragon, Stardust Dragon}", else REJECT
        ACCEPT_TRAMP  = 0x0224922E   # itself `b 0x022494C4` (ACCEPT); used because a direct B to 0x022494C4 is out of range
        ACCEPT_EPI    = 0x022494C4   # `movs r0,#1; add sp,#0x10; pop {r3-r7,pc}` = ACCEPT (borrowed epilogue)

        # --- PART J: retune the donor's negate (drop the Tribute cost + "destroy ALL" -> "destroy IT") ---
        # The donor's mode-1 effect is *"You can Tribute this card to negate the activation of an opponent's
        # Spell Card, Trap Card, or Effect Monster's effect and destroy all cards your opponent controls."*
        # Its resolver 0x0222D4F0 dispatches on ctx[0x18]: mode 1 = that negate, mode 2 = "negate the effects
        # of 1 face-up monster your opponent controls" (which Quasar does not have).
        #
        #   0x0222D502: movs r2,#1 ; bl 0x022061A4   <- eligibility gate
        #   0x0222D510: bl 0x022048FC                <- the action: Tribute + destroy-ALL   (WRONG for Quasar)
        #
        # The shared "negate the activation and destroy it" resolver is frame-compatible by construction:
        #   0x022062F8: push {r3,lr}; movs r2,#1; bl 0x02206230; movs r0,#0; pop {r3,pc}
        #   0x02206230(ctx,event,1): FIRST does `bl 0x022061A4` -- the SAME gate, same three args, same position.
        # It is not cid-switched, so it will not silently no-op on the donor's cid. Swapping +04 therefore
        # replaces the action (dropping the Tribute, which lives inside 0x022048FC, and turning "destroy all
        # your opponent's cards" into "destroy the negated card") while keeping the donor's own condition.
        #
        # +08 is set to 0 to match the canonical shape: ALL cls3 rows that use 0x022062F9 have +08 == 0
        # (0x0E5B, 0x0E6C, 0x148C Maryokutai, 0x183A, 0x1B90 Carrierroid, 0x1D8F Prime Material Dragon,
        # 0x1DFA Herald of Perfection, 0x1E3A Thought Ruler Archfiend, ...). 352/776 cls3 rows have +08 == 0,
        # so a null there is thoroughly native. The donor's +08 (0x021DED69) is only a zone-predicate thunk
        # (`ldr r3,[pc,#8]; bl 0x021D6E40`), not the cost.
        #
        # ROUND 2 (after the first attempt still tributed in-game): GDB proved the OLD resolver
        # 0x0222D4F0 NEVER RUNS after the +04 swap (0 hits while activating the effect), so the Tribute
        # is an ACTIVATION-time cost, not part of resolution. Comparing a tributing negate against a
        # costless one shows where it actually lives:
        #
        #   Stardust 0x1E36  cls3[418] +04=0x02229541(own resolver: TRIBUTE+negate) +0C=0x021FE72D +10=0x021E50CD
        #   Majestic 0x211B  cls3[597] +04=<mode dispatch>                          +0C=0x021F0935 +10=0x021E6871
        #   Maryokutai 0x148C cls3[79] +04=0x022062F9 (shared, costless)            +0C=0x021F2D01 +10=0x021E50CD
        #
        # So the cost is bound to the donor's bespoke CONDITION path: +0C 0x021F0935 -> dispatcher
        # 0x021E5794 -> the donor's leaf 0x021E6412, which sets ctx[0x18] (mode 1/2), builds the
        # two-effect menu, and declares the Tribute cost for mode 1.
        #
        # The fix is to replace the CONDITION as well, with **0x021FE72D** -- the availability test that
        # Stardust already uses directly as its +0C, and which **already special-cases 0x211B** (it has an
        # explicit `cmp r1,0x211B` arm at 0x021FE75A that applies the "opponent activated it" restriction).
        # That bypasses the donor's menu/mode/cost machinery entirely while keeping a condition the engine
        # already knows how to run for this cid. +10 becomes 0x021E50CD, the tag both Stardust and the
        # costless Maryokutai use for this responder shape.
        NEGATE_ROW_CID   = DONOR_CID
        NEGATE_OLD_RES   = 0x0222D4F1   # the donor's mode-dispatching resolver
        NEGATE_NEW_RES   = 0x022062F9   # the shared "negate the activation, and if you do, destroy it"
        NEGATE_OLD_SUB   = 0x021DED69   # zone-predicate thunk; the shared negate's rows all carry +08 == 0
        NEGATE_OLD_COND  = 0x021F0935   # -> 0x021E5794 -> 0x021E6412: the two-effect menu + Tribute cost
        NEGATE_NEW_COND  = 0x021FE72D   # Stardust's condition; already has an explicit 0x211B arm
        NEGATE_OLD_TAG   = 0x021E6871
        #
        # ROUND 4 — **the +10 tag IS the cost.** Rounds 2/3 still tributed even with both rows correct in live
        # RAM, because 0x021E50CD is not a neutral "responder" tag at all:
        #     0x021E50CC: push {r3,lr}; ldrb r0,[r1,#2](side); ldrb r1,[r1,#3](slot);
        #                 bl 0x021CF658   <-- sends THIS card to the GY = the Tribute
        #                 movs r0,#1; pop {r3,pc}
        # Stardust AND Maryokutai both use it because BOTH cards read "Tribute this card to negate" -- I had
        # mistaken Maryokutai for a costless card. Exactly 3 of the 94 distinct cls3 +10 tags call 0x021CF658
        # (0x021E50CD, 0x021E7765, 0x021EA6FD); those three are the "tribute self" cost tags.
        # 0x021E7215 does NOT: it is what Prime Material Dragon 0x1D8F uses ("negate the effect ... and destroy
        # it", no cost), and the engine's own phantom 0x0E6C pairs that tag with the shared negate resolver
        # 0x022062F9 -- i.e. a ready-made COSTLESS negate-activation.
        NEGATE_NEW_TAG   = 0x021E7215   # costless responder tag (Prime Material Dragon / phantom 0x0E6C)
        NEGATE_TRIBUTE_TAG = 0x021E50CD # the tribute-self cost tag (round-3 mistake; kept for the assert)
        TRIBUTE_PRIM     = 0x021CF658   # "send the card at (side,slot) to the GY" -- the cost itself

        # ROUND 3: retuning cls3[597] alone was STILL not enough in-game -- Quasar kept tributing, and a RAM
        # dump of the live savestates proved why: row 597 held the new costless shape, but **cls3[598] was
        # untouched** and still carried +0C = 0x021F0935 -> 0x021E6412, i.e. the two-effect menu that declares
        # the Tribute. The offer the player accepts comes from THAT row. Majestic Star has two effects; the real
        # Quasar has one, so row 598 must simply never be activatable.
        #
        # +0C = 0 does NOT mean "never": the 40 native rows with a null condition are ordinary ignition effects
        # (Catapult Turtle, Cannon Soldier, Mass Driver, ...), so a null there reads as "no extra condition,
        # always activatable" -- the exact opposite of what we want. Instead point +0C at a trivial
        # `movs r0,#0 ; bx lr` (0x021D2AC8, immediately after a `bx lr`, so it is a clean standalone entry that
        # touches no stack). A condition returning 0 means "cannot activate", so the row is never offered.
        NEGATE_ROW2_COND = 0x021D2AC9   # `movs r0,#0 ; bx lr` -> always "cannot activate"

        # --- PART K: once-per-turn latch (the Tribute WAS the de-facto limiter; removing it left the
        #     negate unlimited). Straight clone of the Pot-of-Duality idiom that thunder_sea_horse
        #     already proves in-game: per-turn restrictions are attached-effect nodes on pseudo-zone 0xB
        #     (the per-turn log), which auto-expire at turn end. ---
        IS_RESOLVE_CTX = 0x021D2B88   # nonzero in resolve/replay ctx (PoD gates both shims on it)
        TURNLOG_QUERY  = 0x021A14E8   # (p, 0xB, kid, kind) -> nonzero iff the node is on the turn log
        NODE_ATTACH    = 0x021D2584   # (p, kid, kind, 0) -> attach {key=kid, kind} to (p, slot 0xB)
        TURNLOG_SLOT   = 0xB
        TURNLOG_KIND   = 1            # kind 1 = card/effect activation (PoD's HOPT uses (kid, 1))
        QSR_COND_ADDR    = ov5_cave.CAVE_QSR_COND
        QSR_COND_RESERVE = 0x60
        QSR_RES_ADDR     = ov5_cave.CAVE_QSR_RES
        QSR_RES_RESERVE  = 0x40
        CLS3_BASE  = 0x02279D74
        CLS3_COUNT = 0x308

        # --- PART I: "materials must be Synchro monsters" gate (the only NEW CODE in this patch) ---
        # Hook the 4 bytes at 0x022482B6 (`cmp r0,#0xb` + `beq 0x022482BC`) inside the INNER material
        # predicate 0x0224829C. GDB-confirmed at that site: r4 = the MATERIAL's cid, r7 = the SYNCHRO's
        # cid, and it runs for EVERY material (observed r4 = 0x239E Formula / 0x2338 Scarred Warrior /
        # 0x0F56 Fluff Token while r7 = 0x211B). Boggart owns 0x022482B2 and its stub `bx lr`s back to
        # 0x022482B6, so the two hooks chain in either patch order.
        QSR_PRED_HOOK  = 0x022482B6
        QSR_PRED_ORIG  = bytes.fromhex("0b2800d0")   # cmp r0,#0xb ; beq 0x022482BC
        QSR_PRED_CONT  = 0x022482BC                  # the switch head (resume point; it LOADs r0, so r0 is dead there)
        QSR_PRED_STUB  = ov5_cave.CAVE_QSR_PRED
        QSR_PRED_RESERVE = 0x40
        CARD_TYPE_GETTER = 0x0202ABF8                # -> 5-bit card-type code; Synchro = 17/18/19
        BOGGART_REMAP_CID = 0x2346                   # Boggart's remap target: a phantom with no card_prop record
        INNER_EPILOGUE = 0xBDFE                      # POP {r1,r2,r3,r4,r5,r6,r7,pc} == 0x0224829C's own epilogue

        # --- PART H: the donor's effect-registry row (the "SS Stardust from the GY" End-Phase half) ---
        REG_BASE   = 0x0228E1E0   # effect registry: stride 8 = [resolver u32][cid u16][pad u16]; linear walk, NOT sorted
        REG_STRIDE = 8
        REG_COUNT  = 600          # scan bound (generous; the donor's row is reg[264])
        REG_ENDPHASE_RES = 0x022544F5   # the donor's UNIQUE registry resolver (references Majestic Dragon 0x20F4)

        # --- PART F: route the donor to the engine's GENERIC non-Tuner rule ---
        NONTUNER_BHS      = 0x02249D26   # `bhs 0x02249D54`; fires ONLY for cid 0x211B (the bhi above took everything >)
        MAJESTIC_RULE     = 0x02249D54   # Majestic Star's bespoke rule (material #2 unrestricted; #3+ non-Tuner)
        GENERIC_NONTUNER  = 0x02249D66   # the engine's generic rule: every material after the Tuner must be a non-Tuner

        # ===========================================================================
        # PART L — "When this card leaves the field" trigger (cls2 INSERT)
        # ===========================================================================
        # Phase 3, step 1. NOT new RE: the leave-trigger is a shipped, in-game-proven pattern.
        # patch_minefield_driller.py ("Reborn Tengu", built on this same clean rom.nds and
        # distributed as tenguboggartdarksoul_*.xdelta) gives a card
        # "when this card leaves the field: Special Summon <named monster>" by reusing
        # **Yubel - Terror Incarnate 0x1CF2**'s evolution-leave resolver. Its cls2 row IS the model:
        #
        #     cls2[306]  cid=0x1CF2  +04=0x02206F41  +08=0  +0C=0x021F0419  +10=0x021E51E5  +14=0
        #
        #   +04  the evolution-leave Special-Summon state machine
        #   +0C  a GENERIC "this card left the field" precheck -- no hardcoded cid, so it is reusable
        #   +10  0x021E51E5 = OPTIONAL ("you can"); 0 would be MANDATORY (what Reborn Tengu uses)
        #
        # Quasar's text is "You can Special Summon", so we keep the OPTIONAL tag.
        #
        # ⚠️ WORDING TRAP (cost a wrong conclusion once -- do not repeat it): searching the ROM's
        # English text for "leaves the field" returns 0 hits across all 4305 cards, which looks like
        # "OTN has no leave triggers". The OTN-era wording is **"removed from the field"**, which
        # matches 31 monsters (Yubel-TI, Fortune Lady Light 0x206D, Doomkaiser 0x1EA8, Genex Ally
        # Birdman 0x2205, ...). Always search era-appropriate phrasing.
        #
        # The donor has NO cls2 row (its sorted insertion point is between row 494 = 0x2117 and
        # row 495 = 0x211E, both real cards), so the row must be INSERTED into a binary-searched
        # table. We use the repo's proven count-neutral idiom (tg_striker._insert_sorted, as
        # used by Rush Rhino / Wattcobra): drop one phantom row, insert ours in sorted position,
        # rewrite the region -- count and sort order preserved, so the binary search is undisturbed.
        #
        # Phantom choice: 0x1175 (cls2 row 50). It has NO card_prop record, so no such card can ever
        # exist or reach the table, and it scores just 2 halfword references across overlay 3 / ARM9 /
        # overlay 5 (the fewest of all 64 unclaimed cls2 phantoms) -- the same selection criterion
        # PART A's LIST_A phantom used. It is distinct from every phantom the rest of the chain
        # claims (Striker 0x2347, Warwolf 0x234D, Rush Rhino 0x234E, Darksoul 0x1CDE, ... ).
        CLS2_BASE      = 0x02275C04   # cls2 master effect table (cid-sorted, binary-searched)
        CLS2_COUNT     = 0x2B9        # 697 records, stride CLS_STRIDE (0x18)
        CLS2_PHANTOM   = 0x1175       # phantom row dropped to stay count-neutral (no card_prop record)
        LEAVE_RESOLVER = 0x02206F41   # +04 Yubel-TI evolution-leave Special-Summon state machine
        LEAVE_AUX      = 0x00000000   # +08 unused (matches Yubel-TI)
        # +0C condition. ROUND 3 (after the instrumented A/B proved the row is NEVER consulted):
        #
        #   The black-box recorder (donor row AND Reborn Tengu control on identical shims, both cards
        #   destroyed in the same turn) returned:
        #       +00 cond called = 1,  +04 last cid = 0x2085 (Tengu),  +08 cond called for 0x211B = 0
        #   i.e. the recorder demonstrably WORKS and Quasar's cls2 row is simply never reached.
        #
        #   Census of every native row using resolver 0x02206F41:
        #       cond 0x021F0419 users: Yubel 0x1CF1(t1), Yubel-TI 0x1CF2(t1), Instant Neo Space
        #           0x1D17(t13), Geartown 0x1E03(t13), Morphtronic Cameran 0x1EC6(t1)   <- ALL main-deck
        #       cond 0 users:          Dark Flare Knight 0x1642 (t3 = FUSION, EXTRA DECK), Peten 0x17C5,
        #                              Clock Tower Prison 0x1A0C, Limiter Overload, Fake Explosion
        #
        #   **No Extra-Deck monster anywhere pairs this resolver with 0x021F0419.** The ONE Extra-Deck
        #   card that uses this resolver -- Dark Flare Knight, "when this card is destroyed: Special
        #   Summon 1 'Mirage Knight'", structurally identical to what Quasar needs -- uses a NULL
        #   condition and a NULL tag. So clone THAT shape for an Extra-Deck donor.
        #
        #   (+0C = 0 means "no extra condition, always activatable", NOT "never" -- the same lesson
        #   PART J learned the hard way; see NEGATE_ROW2_COND.)
        LEAVE_COND_MAINDECK = 0x021F0419   # Yubel-TI's precheck -- main-deck cards only, in practice
        LEAVE_COND_NULL     = 0x00000000   # Dark Flare Knight's shape: the Extra-Deck precedent
        LEAVE_COND     = LEAVE_COND_NULL   # <-- A/B knob
        # +10 timing/prompt tag. ROUND 2 (after the first in-game test produced NO PROMPT AT ALL):
        #
        #   savestate evidence (rom_all_patches.ml5 before / .ml6 after / .ml7 way after) ruled out
        #   every cheap explanation -- the patched cls2 row AND the ov5 selector were both live in RAM,
        #   Quasar 0x211B really was on the field and really left it, and "Shooting Star Dragon" 0x239D
        #   really was in that player's Extra Deck (7 cards). So a legal target existed, the code was
        #   live, the card left -- and nothing was offered.
        #
        #   That leaves the ONE wiring difference against the in-game-proven control, Reborn Tengu
        #   (Minefield Driller 0x2085), which lives in the SAME chained ROM (step 1) and works:
        #
        #       Reborn Tengu  cls2  +04=0x02206F41 +08=0 +0C=0x021F0419 +10=0x00000000  <- MANDATORY
        #       Quasar        cls2  +04=0x02206F41 +08=0 +0C=0x021F0419 +10=0x021E51E5  <- optional
        #
        #   0x021E51E5 is a thin wrapper that always tail-calls 0x021E50DC, a multi-phase protocol
        #   handler driven by the duel FSM word 0x0229AAFC+0x7C (phase 0 -> cls2 invoker 0x0224AD94,
        #   phases 1/2 -> other paths). It is the most common non-zero cls2 tag (184 rows), so it is
        #   not exotic -- but it clearly imposes a phase protocol that a `0` tag does not, and Reborn
        #   Tengu deliberately uses `0`.
        #
        #   So: match the proven control exactly. With MANDATORY there is no Yes/No prompt -- the
        #   summon simply happens -- which ALSO removes the "an optional effect with no offer looks
        #   identical to a dead trigger" ambiguity that made the first test hard to read.
        #
        #   ⚠️ Quasar's real text is "You CAN Special Summon", so mandatory is a deliberate, temporary
        #   divergence to isolate the variable (exactly what Reborn Tengu shipped, for the same reason).
        #   If mandatory fires, we know the trigger path is sound and can revisit the optional tag.
        LEAVE_TAG_OPTIONAL  = 0x021E51E5   # Yubel-TI's tag: phase-protocol wrapper -> 0x021E50DC
        LEAVE_TAG_MANDATORY = 0x00000000   # Reborn Tengu's tag: fires immediately, no prompt
        LEAVE_TAG      = LEAVE_TAG_MANDATORY   # <-- A/B knob; match the proven control first
        LEAVE_TAIL     = 0x00000000   # +14 unused (matches Yubel-TI)
        YUBEL_TI_CID   = 0x1CF2       # the model row, asserted to still have the expected shape

        # The donor ALREADY owns a populate record -- populate[1019] a=0x211B b=0x1E36
        # h=0x0223E905 fl=0x00010002 -- i.e. the "Special Summon 1 <named monster>" half of its old
        # End-Phase clause, with b = "Stardust Dragon" and a selector that searches the GRAVEYARD.
        # PART L deliberately leaves that record ALONE, so this step is independently testable:
        # with PART L alone the card should read "when Quasar leaves the field: you can Special
        # Summon Stardust Dragon from your Graveyard". If that fires in-game, the whole trigger path
        # is proven and only the ZONE + TARGET swap remains (PART M).
        POP_BASE   = 0x022713C4       # evolution/populate table: [a u16][b u16][h u32][fl u32], sorted by a
        POP_STRIDE = 12
        POP_COUNT  = 1391             # real record count (entries past this are garbage, not records)
        DONOR_POP_TARGET = 0x1E36     # b: "Stardust Dragon" -- becomes 0x239D in PART M
        DONOR_POP_SELECTOR = 0x0223E905  # h: the donor's own GY selector (zone 8) -- swapped in PART M

        # --- PART M — retarget the summon to "1 'Shooting Star Dragon' from the Extra Deck" ---
        # The donor's populate record already carries the "Special Summon 1 <named monster>" shape; PART M
        # only changes WHICH card (b) and WHICH ZONE (the selector h).
        #
        # Selector anatomy, shared by all three known selectors:
        #     [sp+0] = ctx[8]      criteria word
        #     [sp+4] = flags/zone  (bit0 = opponent's side; the builder reads it as its 6th arg)
        #     [sp+8] = target cid  (from populate `b`, via ctx[+2] s16 else ctx[+0])
        #     r3     = &[sp+8] for a NAMED target   (r3 = 0 => the player picks from all matches)
        #     r2     = per-candidate match filter
        #     then `bl <zone builder>`
        #
        #     donor          0x0223E904:  flags #8, filter 0x0223C6F1, builder 0x0223C4E8  (GRAVEYARD)
        #     Yubel-TI       0x0223E2C8:  filter 0x0223C6F1,           builder 0x0223BC3C  (DECK)
        #     Instant Fusion 0x0223F760:  flags #2, filter 0x0223F739, builder 0x0223BE40  (EXTRA DECK)
        #
        # So the donor's selector is ALREADY the right shape (named target + the right filter) and differs
        # from what Quasar needs in exactly TWO places. We clone it into an ov5 cave and change:
        #     offset 0x16   `movs r0,#8` -> `movs r0,#2`   (flags word, Instant Fusion's proven pairing
        #                                                   with the Extra-Deck builder)
        #     offset 0x20   `bl 0x0223C4E8` -> `bl 0x0223BE40`   (GRAVEYARD builder -> EXTRA DECK builder)
        #
        # ⚠️ Filter choice is load-bearing. 0x0223C6F1 (which the donor already uses, and Yubel too) is a
        # zone-agnostic NAMED-TARGET match -- it compares the candidate's cid against *r3. Instant Fusion's
        # 0x0223F739 is instead a Level/Fusion CRITERIA filter (it calls 0x02023228 / 0x020235A4 and never
        # looks at a target), which is why Instant Fusion lets you pick any qualifying Fusion. Quasar needs
        # one specific card, so we keep 0x0223C6F1 -- i.e. we do NOT touch the literal.
        #
        # The clone is byte-verbatim including the trailing literal, so the `ldr r2,[pc,#8]` at offset 0x1E
        # still resolves to the copied literal at offset 0x28 -- no PC-relative fixup is needed.
        #
        # 0x0223BE40 is confirmed to be the EXTRA-DECK builder two independent ways: its literal pool holds
        # BOTH 0x0229ACAC (= player0 + 0x18, the extra-deck count) and the immediate 0x000004E4 (the array
        # offset), and GDB caught SS_ENGINE receiving r1 = player0+0x4E4 during an Instant Fusion resolve.
        EXSEL_SRC       = 0x0223E904   # the donor's GY selector -- the clone source
        EXSEL_LEN       = 0x2C         # header 0x24 + pop + align nop + the 4-byte filter literal
        EXSEL_OFF_FLAGS = 0x16         # `movs r0,#8` (the [sp+4] flags word)
        EXSEL_OFF_BL    = 0x20         # `bl 0x0223C4E8`
        EXSEL_ORIG_FLAGS = bytes.fromhex("0820")   # movs r0,#8
        EXSEL_NEW_FLAGS  = bytes.fromhex("0220")   # movs r0,#2
        GY_BUILDER      = 0x0223C4E8   # the donor's original builder (GRAVEYARD)
        EXTRA_BUILDER   = 0x0223BE40   # Instant Fusion's builder (EXTRA DECK) -- literal pool proves it
        NAMED_FILTER    = 0x0223C6F1   # zone-agnostic "candidate cid == *r3" match (kept, not rewritten)
        EXSEL_ADDR      = ov5_cave.CAVE_QSR_EXSEL
        EXSEL_RESERVE   = 0x40

        SHOOTING_STAR_CID = 0x239D     # "Shooting Star Dragon" -- the card Quasar revives
        # Populate flags: adopt Yubel-TI's exact value. PART L replaced the trigger with Yubel-TI's
        # resolver, and Reborn Tengu proved 0x00000802 drives that resolver; the donor's own 0x00010002
        # belonged to its End-Phase clause, which no longer runs.
        POP_FL_YUBEL    = 0x00000802
        YUBEL_POP_CID   = 0x1CF2       # asserted to still carry POP_FL_YUBEL (the model)

        # --- superseded notes (kept: these addresses were measured and are still true) ---
        # Remaining delta vs Reborn Tengu: zone must be EXTRA DECK, not Deck/GY, and the target is a
        # different named card. Groundwork already measured, recorded here so it is not re-derived:
        #   * Extra Deck array  = player + 0x4E4 (u32 packed card words), count = player + 0x18
        #     (savestate scan, 8 independent cases; adjacent literal pools; GDB-confirmed).
        #   * Selector anatomy (all three share it): [sp+0]=ctx[8] criteria, [sp+4]=ZONE CODE,
        #     [sp+8]=target cid, r3=&[sp+8] for a NAMED target (0 = player picks), r2=match filter,
        #     then `bl <zone builder>`.
        #         donor 0x0223E904: zone 8, builder searches the GRAVEYARD
        #         Yubel 0x0223E2C8: builder 0x0223BC3C = DECK       (what Reborn Tengu clones)
        #         Instant Fusion 0x0223F760: builder 0x0223BE40 = EXTRA DECK, zone code 2, r3=0
        #     => Quasar wants Instant Fusion's EXTRA-DECK builder 0x0223BE40 with the donor/Yubel
        #        style NAMED target (r3 = &[sp+8], b = 0x239D), assembled into an ov5 cave blob the
        #        way patch_minefield_driller.build_blob does.
        #   * Alternative already GDB-confirmed: SS_FROM_EXTRA 0x02269314(side, &extra[i], 1,
        #     (kid<<16)|flag) -- a 4-register wrapper over SS_ENGINE 0x0226925C. Measured live:
        #     r1 pointed straight at player0+0x4E4. ⚠️ but that bypasses the selector protocol the
        #     leave resolver drives, so prefer the blob unless the blob proves unworkable.
        # Do NOT claim the Shooting Star revive in the card text until PART M is in-game confirmed.

        # --- PART B: the donor's End-Phase "return to Extra Deck" clause ---
        CLS1_BASE   = 0x022860D4    # cls1 table RAM base
        CLS1_COUNT  = 0x535
        CLS_STRIDE  = 0x18
        ENDPHASE_RETURN_RES = 0x02222655   # cls1 +04 shared by the 9 Neos fusions + Majestic Star/Red
        ENDPHASE_RETURN_TAIL = 0x02235605  # cls1 +14 on the two Majestic rows

        # --- PART C: visible card ---
        QUASAR_NAME = b"Shooting Quasar"   # 15B; the donor's smallest name slot is 20B (k/e) -> fits in place everywhere.
                                           # "Shooting Quasar Dragon" (22B) does NOT fit and name blobs must never grow.

        # Honest text: describes ONLY what this patch actually enforces TODAY.
        #   * "Synchro Monsters" is NOT claimed yet -- P3 (the Synchro-only material gate over
        #     0x022482B6) is not built, so materials are currently any 1 Tuner + 2+ non-Tuners.
        #     Tighten this line to "1 Tuner Synchro Monster + 2 or more non-Tuner Synchro
        #     Monsters" (+14B, still fits) in the SAME change that lands P3.
        #   * The negate line follows PART J: the action is now the shared "negate the activation, and if you
        #     do, destroy it" (no Tribute, destroys the negated card rather than the whole board). The donor's
        #     own CONDITION is kept, which is "an opponent activates a Spell/Trap/Effect Monster effect" -- so
        #     the text says "your opponent activates", NOT the real card's "during either player's turn, when a
        #     card or effect is activated". Do not widen this line until that condition is actually widened.
        #   * "Once per turn" is claimed as of PART K (the turn-log latch). Before that it was deliberately
        #     omitted, because removing the Tribute also removed the de-facto limiter.
        #   * The multi-attack line is claimed as of PART O (IN-GAME CONFIRMED). It is worded
        #     "can attack twice during each Battle Phase", NOT the real card's "maximum number of attacks
        #     ... equals the number of non-Tuner monsters used as its Synchro Material", because the
        #     engine's grant is a BOOLEAN list membership, not a count (see PART O). A variable count is
        #     not expressible on this path at all -- it would need the separate summon-FSM scratch route
        #     that Shooting Star Dragon's "up to 5" uses (0x0229AAFC +0x74/+0x78).
        #   (PARTS A/E/F/I make the material line literally true: LIST_B forces min 3, required_tuner_count
        #    forces exactly 1 Tuner, LIST_A's absence allows the extras, PART F makes every material after the
        #    Tuner a non-Tuner, and PART I forces every material to be a Synchro monster.)
        #   * The revive line is claimed as of PART N (IN-GAME CONFIRMED: destroying Quasar
        #     Special Summoned Shooting Star Dragon from the Extra Deck). It is worded "When this card is
        #     DESTROYED", not the real card's "when this card LEAVES THE FIELD", because the shared
        #     trampoline gates on [sp+0x90] = DESTROYED -- tribute, bounce and Synchro-Material do NOT
        #     trigger it. It also omits "You can": the action is mandatory/automatic, with no Yes/No
        #     prompt. Widen the text only if/when those two are actually widened.
        QUASAR_DESC = (
            b'1 Tuner Synchro Monster + 2 or more non-Tuner Synchro Monsters\r\n'
            b'This card can attack twice during each Battle Phase. '
            b'Once per turn, when your opponent activates a Spell Card, Trap Card, or Effect '
            b'Monster\'s effect: You can negate the activation, and if you do, destroy it. '
            b'When this card is destroyed: Special Summon 1 "Shooting Star Dragon" from your Extra Deck.'
        )




        # ===========================================================================
        # PART A — remove the donor from LIST_A so "2 or more" materials are legal
        # ===========================================================================
        def apply_material_rule(ov: bytearray) -> None:
            """Substitute a phantom for 0x211B in LIST_A (count-neutral, order-preserving).

            LIST_A membership = "exact material count, extras forbidden". Dropping the donor
            makes material_rule_class() return 0 (generic), which is what permits Quasar's
            "2 OR MORE non-Tuner" materials. Idempotent.
            """
            # Guard: the classifiers must still look the way we decoded them.
            imm_a = struct.unpack_from("<H", ov, _off(LIST_A_COUNT_IMM))[0]
            assert imm_a == (0x2200 | LIST_A_COUNT), (
                f"LIST_A count immediate @0x{LIST_A_COUNT_IMM:08X} = 0x{imm_a:04X} (expected movs r2,#0x10)"
            )
            imm_b = struct.unpack_from("<H", ov, _off(LIST_B_COUNT_IMM))[0]
            assert imm_b == 0x2215, (
                f"LIST_B count immediate @0x{LIST_B_COUNT_IMM:08X} = 0x{imm_b:04X} (expected movs r2,#0x15)"
            )
            pivot = struct.unpack_from("<I", ov, _off(SYNCHRO_PIVOT_LIT))[0]
            assert pivot == 0x2346, (
                f"material-predicate pivot literal @0x{SYNCHRO_PIVOT_LIT:08X} = 0x{pivot:04X} (expected 0x2346)"
            )

            cur = list(struct.unpack_from(f"<{LIST_A_COUNT}H", ov, _off(LIST_A)))

            if DONOR_CID not in cur:                                    # idempotent
                print(f"PART A: LIST_A already free of 0x{DONOR_CID:04X} -> no change")
                return
            assert LIST_A_PHANTOM not in cur, f"phantom 0x{LIST_A_PHANTOM:04X} unexpectedly already in LIST_A"

            new = tuple(sorted((set(cur) - {DONOR_CID}) | {LIST_A_PHANTOM}))
            assert len(new) == LIST_A_COUNT and all(new[i] < new[i + 1] for i in range(len(new) - 1)), (
                f"resulting LIST_A is not a sorted {LIST_A_COUNT}-entry set: {[hex(x) for x in new]}"
            )

            struct.pack_into(f"<{LIST_A_COUNT}H", ov, _off(LIST_A), *new)
            print(f"PART A: LIST_A @0x{LIST_A:08X} (count {LIST_A_COUNT}) — dropped 0x{DONOR_CID:04X}, "
                  f"inserted phantom 0x{LIST_A_PHANTOM:04X}  => materials are now '1 Tuner + 2 or more non-Tuners'")


        # ===========================================================================
        # PART O — "This card can attack twice during each Battle Phase"
        # ===========================================================================
        def apply_double_attack(ov: bytearray) -> None:
            """Insert 0x211B into the engine's double-attack cid list (count-neutral, sorted).

            The exact mirror of PART A: drop a phantom, insert the donor, keep the count and the
            ascending order intact so the binary search is undisturbed. Idempotent.

            This is the WHOLE of the multi-attack feature -- there is no per-monster attack counter to
            write and no ov5 stub. See the DBLATK_* constants for the decoded search site.
            """
            # Guard: the searcher must still look the way we decoded it.
            imm = struct.unpack_from("<H", ov, _off(DBLATK_COUNT_IMM))[0]
            assert imm == (0x2200 | DBLATK_COUNT), (
                f"double-attack count immediate @0x{DBLATK_COUNT_IMM:08X} = 0x{imm:04X} (expected movs r2,#0xF)"
            )
            lit = struct.unpack_from("<I", ov, _off(DBLATK_LIST_LIT))[0]
            assert lit == DBLATK_LIST, (
                f"double-attack list literal @0x{DBLATK_LIST_LIT:08X} = 0x{lit:08X} (expected 0x{DBLATK_LIST:08X})"
            )

            cur = list(struct.unpack_from(f"<{DBLATK_COUNT}H", ov, _off(DBLATK_LIST)))

            if DONOR_CID in cur:                                        # idempotent
                print(f"PART O: donor 0x{DONOR_CID:04X} already in the double-attack list -> no change")
                return
            assert DBLATK_PHANTOM in cur, (
                f"phantom 0x{DBLATK_PHANTOM:04X} not present in the double-attack list "
                f"{[hex(x) for x in cur]} -- refusing to drop a real card's double attack"
            )

            new = tuple(sorted((set(cur) - {DBLATK_PHANTOM}) | {DONOR_CID}))
            assert len(new) == DBLATK_COUNT and all(new[i] < new[i + 1] for i in range(len(new) - 1)), (
                f"resulting double-attack list is not a sorted {DBLATK_COUNT}-entry set: {[hex(x) for x in new]}"
            )

            struct.pack_into(f"<{DBLATK_COUNT}H", ov, _off(DBLATK_LIST), *new)
            print(f"PART O: double-attack list @0x{DBLATK_LIST:08X} (count {DBLATK_COUNT}) — dropped phantom "
                  f"0x{DBLATK_PHANTOM:04X}, inserted 0x{DONOR_CID:04X}  => can attack twice each Battle Phase")


        # ===========================================================================
        # PART B — neutralise the donor's End-Phase "return to the Extra Deck" clause
        # ===========================================================================
        def _find_cls1(ov: bytes, cid: int) -> int:
            """Return the byte offset of *cid*'s cls1 row, asserting it is unique."""
            hits = [i for i in range(CLS1_COUNT)
                    if struct.unpack_from("<H", ov, _off(CLS1_BASE + i * CLS_STRIDE))[0] == cid]
            assert len(hits) == 1, f"expected exactly 1 cls1 row for 0x{cid:04X}, found {hits}"
            return _off(CLS1_BASE + hits[0] * CLS_STRIDE)


        def apply_endphase_neutralise(ov: bytearray) -> None:
            """Zero the donor's cls1 handler fields, keeping its cid (the engine's own inert-row shape).

            cls1[1084] IS the "During the End Phase, return this card to the Extra Deck" clause:
            its resolver 0x02222655 is shared by exactly the 11 cards whose text says that (the
            9 Neos fusions + Majestic Star + Majestic Red). Without this, Quasar bounces itself
            to the Extra Deck every End Phase. Idempotent.
            """
            off = _find_cls1(bytes(ov), DONOR_CID)
            cid, _pad, res, aux, cond, tag, tail = struct.unpack_from("<HHIIIII", ov, off)

            if res == 0 and tail == 0:                                  # idempotent
                print(f"PART B: cls1 row for 0x{DONOR_CID:04X} already inert -> no change")
                return
            assert res == ENDPHASE_RETURN_RES, (
                f"cls1 +04 for 0x{DONOR_CID:04X} = 0x{res:08X}, expected the End-Phase-return "
                f"resolver 0x{ENDPHASE_RETURN_RES:08X} — donor rows changed, re-verify before patching"
            )
            assert tail == ENDPHASE_RETURN_TAIL, (
                f"cls1 +14 for 0x{DONOR_CID:04X} = 0x{tail:08X}, expected 0x{ENDPHASE_RETURN_TAIL:08X}"
            )

            # Match the native inert-row shape exactly: everything but the cid goes to 0.
            struct.pack_into("<HHIIIII", ov, off, cid, 0, 0, 0, 0, 0, 0)
            print(f"PART B: cls1 row for 0x{DONOR_CID:04X} @0x{off + RAM_BASE:08X} made inert "
                  f"(+04 0x{res:08X}->0, +14 0x{tail:08X}->0)  => no more End-Phase self-bounce")


        # ===========================================================================
        # PART D — retarget the donor's named-material leaf to the generic ALLOW leaf
        # ===========================================================================
        def _thumb_b(at: int, target: int) -> int:
            """Encode an unconditional Thumb-1 `B target` placed at *at* (imm11, +/-2KB)."""
            off = (target - (at + 4)) // 2
            assert -0x400 <= off < 0x400, f"B 0x{at:08X} -> 0x{target:08X} out of Thumb-1 range ({off})"
            return 0xE000 | (off & 0x7FF)


        def apply_named_material_fix(ov: bytearray) -> None:
            """Point the donor's per-Synchro material leaf at the switch's generic ALLOW leaf.

            Without this the donor still demands "Majestic Dragon" + "Stardust Dragon" as its
            materials and rejects everything else -- PART A only fixes the material COUNT.
            The retargeted branch is guarded by `cmp r5, #0x211B`, so ONLY the donor is
            affected (Majestic Red's mirror leaf at 0x02248A2C is untouched). Idempotent.
            """
            want_old = _thumb_b(NAMED_MAT_BRANCH, NAMED_MAT_LEAF)     # 0xE144
            want_new = _thumb_b(NAMED_MAT_BRANCH, GENERIC_ALLOW)      # 0xE17A
            cur = struct.unpack_from("<H", ov, _off(NAMED_MAT_BRANCH))[0]

            if cur == want_new:                                       # idempotent
                print(f"PART D: named-material leaf already retargeted -> no change")
                return
            assert cur == want_old, (
                f"branch @0x{NAMED_MAT_BRANCH:08X} = 0x{cur:04X}, expected 0x{want_old:04X} "
                f"(b 0x{NAMED_MAT_LEAF:08X}) — the material switch moved, re-verify before patching"
            )
            # The destination must really be the generic "return 1" leaf.
            got = bytes(ov[_off(GENERIC_ALLOW):_off(GENERIC_ALLOW) + 4])
            assert got == GENERIC_ALLOW_BYTES, (
                f"generic ALLOW leaf @0x{GENERIC_ALLOW:08X} = {got.hex()}, expected {GENERIC_ALLOW_BYTES.hex()} "
                f"(movs r0,#1; pop {{r1-r7,pc}})"
            )

            struct.pack_into("<H", ov, _off(NAMED_MAT_BRANCH), want_new)
            print(f"PART D: @0x{NAMED_MAT_BRANCH:08X} b 0x{NAMED_MAT_LEAF:08X} -> b 0x{GENERIC_ALLOW:08X} "
                  f"(0x{cur:04X} -> 0x{want_new:04X})  => drops the \"Majestic Dragon + Stardust Dragon\" requirement")


        def _thumb_bcc(at: int, target: int, cond: int) -> int:
            """Encode a conditional Thumb-1 `B<cond> target` placed at *at* (imm8, +/-256B)."""
            off = (target - (at + 4)) // 2
            assert -0x80 <= off < 0x80, f"B<cond> 0x{at:08X} -> 0x{target:08X} out of range ({off})"
            return 0xD000 | (cond << 8) | (off & 0xFF)


        # ===========================================================================
        # PART E — kill the donor's SECOND named-material rule (the {Majestic Dragon, Stardust} PAIR)
        # ===========================================================================
        def apply_pair_material_fix(ov: bytearray) -> None:
            """Retarget the donor's leaf in the 3rd predicate (0x02248A88) to unconditional ACCEPT.

            That leaf (0x0224916A) fires while choosing material #2 and demands that material #1 was
            "Stardust Dragon" or "Majestic Dragon" -- so ANY ordinary Tuner is rejected and the search
            can never get past 2 materials. GDB-confirmed: 0x02248A88 returned 0 for every candidate
            while its own inner call returned 1.

            The retargeted branch is guarded by `cmp r5, 0x211B`, so it is DONOR-ONLY. Idempotent.
            """
            want_old = _thumb_b(PAIR_BRANCH, PAIR_LEAF)        # 0xE25E
            want_new = _thumb_b(PAIR_BRANCH, ACCEPT_TRAMP)     # 0xE2C0
            cur = struct.unpack_from("<H", ov, _off(PAIR_BRANCH))[0]

            if cur == want_new:
                print("PART E: pair-material leaf already retargeted -> no change")
                return
            assert cur == want_old, (
                f"branch @0x{PAIR_BRANCH:08X} = 0x{cur:04X}, expected 0x{want_old:04X} "
                f"(b 0x{PAIR_LEAF:08X}) — the 3rd predicate's switch moved, re-verify before patching"
            )
            # The trampoline must really be an unconditional branch to the ACCEPT epilogue.
            tramp = struct.unpack_from("<H", ov, _off(ACCEPT_TRAMP))[0]
            assert tramp == _thumb_b(ACCEPT_TRAMP, ACCEPT_EPI), (
                f"trampoline @0x{ACCEPT_TRAMP:08X} = 0x{tramp:04X}, expected b 0x{ACCEPT_EPI:08X}"
            )
            assert bytes(ov[_off(ACCEPT_EPI):_off(ACCEPT_EPI) + 2]) == bytes.fromhex("0120"), (
                f"ACCEPT epilogue @0x{ACCEPT_EPI:08X} does not start with `movs r0,#1`"
            )

            struct.pack_into("<H", ov, _off(PAIR_BRANCH), want_new)
            print(f"PART E: @0x{PAIR_BRANCH:08X} b 0x{PAIR_LEAF:08X} -> b 0x{ACCEPT_TRAMP:08X} "
                  f"(0x{cur:04X} -> 0x{want_new:04X})  => drops the \"Majestic Dragon + Stardust\" PAIR rule")


        # ===========================================================================
        # PART F — use the engine's GENERIC "non-Tuners only" rule for the donor
        # ===========================================================================
        def apply_generic_nontuner_rule(ov: bytearray) -> None:
            """Route the donor from Majestic Star's bespoke non-Tuner rule to the engine's generic one.

            0x02249D54 (Majestic Star's) leaves material #2 unrestricted (`cmp selected,#2; blo accept`),
            which would let Quasar take a second Tuner. 0x02249D66 (generic) requires EVERY material after
            the Tuner to be a non-Tuner -- exactly "1 Tuner + 2 or more non-Tuner monsters".

            The `bhs` fires only when the Synchro cid == 0x211B (the `bhi` above already took everything
            greater), so Majestic Red 0x21CB -- which reaches 0x02249D54 via its own branch at 0x02249D3C
            -- keeps its rule. Idempotent.
            """
            want_old = _thumb_bcc(NONTUNER_BHS, MAJESTIC_RULE, 2)      # bhs 0x02249D54 -> 0xD215
            want_new = _thumb_bcc(NONTUNER_BHS, GENERIC_NONTUNER, 2)   # bhs 0x02249D66 -> 0xD21E
            cur = struct.unpack_from("<H", ov, _off(NONTUNER_BHS))[0]

            if cur == want_new:
                print("PART F: donor already on the generic non-Tuner rule -> no change")
                return
            assert cur == want_old, (
                f"branch @0x{NONTUNER_BHS:08X} = 0x{cur:04X}, expected 0x{want_old:04X} "
                f"(bhs 0x{MAJESTIC_RULE:08X}) — the hardcoded switch moved, re-verify before patching"
            )
            struct.pack_into("<H", ov, _off(NONTUNER_BHS), want_new)
            print(f"PART F: @0x{NONTUNER_BHS:08X} bhs 0x{MAJESTIC_RULE:08X} -> bhs 0x{GENERIC_NONTUNER:08X} "
                  f"(0x{cur:04X} -> 0x{want_new:04X})  => materials after the Tuner must all be non-Tuners")


        # ===========================================================================
        # PART J — retune the donor's negate to "negate the activation, and if you do, destroy it"
        # ===========================================================================
        def apply_negate_retune(ov: bytearray) -> None:
            """Point the donor's FIRST cls3 row at the shared negate+destroy, and null its +08.

            Donor rows (both cid 0x211B, adjacent): cls3[597] and cls3[598]. Only the FIRST is retuned --
            it is the one whose resolver path is mode 1 (the negate). The second row (the "negate 1 face-up
            monster" effect) is deliberately left alone FOR NOW: whether the engine still offers it depends
            on whether cls3 lookups return the leftmost same-cid row (which would shadow it) or the menu
            enumerates both. That is an in-game question, not a static one -- test before touching it.

            Idempotent.
            """
            rows = [i for i in range(CLS3_COUNT)
                    if struct.unpack_from("<H", ov, _off(CLS3_BASE + i * CLS_STRIDE))[0] == NEGATE_ROW_CID]
            assert len(rows) == 2, f"expected exactly 2 cls3 rows for 0x{NEGATE_ROW_CID:04X}, found {rows}"
            off = _off(CLS3_BASE + rows[0] * CLS_STRIDE)
            res, sub, cond, tag = struct.unpack_from("<IIII", ov, off + 4)

            if (res, sub, cond, tag) == (NEGATE_NEW_RES, 0, NEGATE_NEW_COND, NEGATE_NEW_TAG):
                print("PART J: negate already retuned -> no change")          # idempotent
                return
            assert res in (NEGATE_OLD_RES, NEGATE_NEW_RES), (
                f"cls3[{rows[0]}] +04 = 0x{res:08X}, expected 0x{NEGATE_OLD_RES:08X} "
                f"— rows changed, re-verify before patching"
            )
            assert sub in (NEGATE_OLD_SUB, 0), f"cls3[{rows[0]}] +08 = 0x{sub:08X}"
            assert cond in (NEGATE_OLD_COND, NEGATE_NEW_COND), f"cls3[{rows[0]}] +0C = 0x{cond:08X}"
            assert tag in (NEGATE_OLD_TAG, NEGATE_NEW_TAG, NEGATE_TRIBUTE_TAG), f"cls3[{rows[0]}] +10 = 0x{tag:08X}"
            # Guard the round-4 lesson: the chosen tag must NOT be one of the tribute-self cost tags.
            assert NEGATE_NEW_TAG != NEGATE_TRIBUTE_TAG, "the +10 tag must be costless, not a tribute tag"

            struct.pack_into("<IIII", ov, off + 4, NEGATE_NEW_RES, 0, NEGATE_NEW_COND, NEGATE_NEW_TAG)
            print(f"PART J: cls3[{rows[0]}] +04 0x{res:08X}->0x{NEGATE_NEW_RES:08X}, +08 0x{sub:08X}->0, "
                  f"+0C 0x{cond:08X}->0x{NEGATE_NEW_COND:08X}, +10 0x{tag:08X}->0x{NEGATE_NEW_TAG:08X}\n"
                  f"        => costless negate+destroy; bypasses the donor's Tribute/two-effect menu")

            # --- row 2: the donor's SECOND effect must never be activatable. It still carries the
            #     Tribute-declaring two-effect condition, and a live RAM dump proved THAT is the offer
            #     the player was accepting (row 597 was already costless yet Quasar still tributed). ---
            off2 = _off(CLS3_BASE + rows[1] * CLS_STRIDE)
            cond2 = struct.unpack_from("<I", ov, off2 + 12)[0]
            if cond2 == NEGATE_ROW2_COND:
                print(f"PART J: cls3[{rows[1]}] already disabled -> no change")
                return
            assert cond2 == NEGATE_OLD_COND, f"cls3[{rows[1]}] +0C = 0x{cond2:08X}, expected 0x{NEGATE_OLD_COND:08X}"
            struct.pack_into("<I", ov, off2 + 12, NEGATE_ROW2_COND)
            print(f"PART J: cls3[{rows[1]}] +0C 0x{cond2:08X} -> 0x{NEGATE_ROW2_COND:08X} (movs r0,#0; bx lr)  "
                  f"=> the donor's 2nd effect (and its Tribute menu) is never offered")


        # ===========================================================================
        # PART K — once per turn (Pot-of-Duality turn-log latch)
        # ===========================================================================
        def _build_hopt_cond(base: int = QSR_COND_ADDR) -> bytes:
            """Act-cond shim: deny if this card already used its effect this turn, else chain the native cond.

            shim(ctx, arg1):
              if IS_RESOLVE_CTX(ctx): goto native            ; a resolving effect must not re-deny itself
              if TURNLOG_QUERY([ctx+2], 0xB, [ctx+0], 1): return 0    ; once per turn
              native: return NATIVE_COND(ctx, arg1)          ; the donor's own "opponent activated" test

            arg1 matters: the native condition 0x021FE72C tests it (`adds r4,r1,#0 ; bne`), so it is
            carried through in r4 and restored, exactly as the Thunder Sea Horse shim does.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, LR}")
             .insn("ADD", "R5, R0, #0x0")        # r5 = ctx
             .insn("ADD", "R4, R1, #0x0")        # r4 = arg1 (passed through to the native cond)
             .bl(IS_RESOLVE_CTX)
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "native")
             .insn("LDRB", "R0, [R5, #0x2]")     # player
             .insn("MOV", "R1, #0xB")            # TURNLOG_SLOT
             .insn("LDRH", "R2, [R5, #0x0]")     # kid (== 0x211B from this row)
             .insn("MOV", "R3, #0x1")            # TURNLOG_KIND
             .bl(TURNLOG_QUERY)
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "deny")                # already negated this turn
             .label("native")
             .insn("ADD", "R0, R5, #0x0")
             .insn("ADD", "R1, R4, #0x0")
             .bl(NEGATE_NEW_COND & ~1)
             .insn("POP", "{R4, R5, PC}")
             .label("deny")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, PC}"))
            code = a.assemble(base)
            assert len(code) <= QSR_COND_RESERVE, f"cond shim {len(code)}B > 0x{QSR_COND_RESERVE:X}"
            assert_thumb1_only(code, base)
            return code


        def _build_hopt_res(base: int = QSR_RES_ADDR) -> bytes:
            """Resolver shim: stamp the turn-log node, then chain the shared negate+destroy.

            shim(ctx, event):
              if not IS_RESOLVE_CTX(ctx): NODE_ATTACH([ctx+2], [ctx+0], 1, 0)
              return NATIVE_RES(ctx, event)

            ⚠️ **r1 (the EVENT) must be preserved.** The shared negate takes TWO arguments --
            `0x022062F8(ctx, event, 1)` -> `0x02206230`, which does `adds r4,r1,#0` and then reads
            `ldrh r0,[r4,#0xc]` off it. The first version of this shim loaded the cid into r1 for
            NODE_ATTACH and chained without restoring it, so the negate silently did nothing
            (in-game regression: Goblin Zombie resolved despite Quasar "activating"). Thunder Sea
            Horse's equivalent shim gets away with r0-only because ITS native resolver is 1-arg --
            do not copy that detail blindly.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, LR}")
             .insn("ADD", "R4, R0, #0x0")        # r4 = ctx
             .insn("ADD", "R5, R1, #0x0")        # r5 = event  (MUST survive; the native res needs it)
             .bl(IS_RESOLVE_CTX)
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "chain")
             .insn("LDRB", "R0, [R4, #0x2]")     # player
             .insn("LDRH", "R1, [R4, #0x0]")     # kid (== 0x211B)
             .insn("MOV", "R2, #0x1")            # TURNLOG_KIND
             .insn("MOV", "R3, #0x0")
             .bl(NODE_ATTACH)
             .label("chain")
             .insn("ADD", "R0, R4, #0x0")
             .insn("ADD", "R1, R5, #0x0")        # restore the event before chaining
             .bl(NEGATE_NEW_RES & ~1)
             .insn("POP", "{R4, R5, PC}"))
            code = a.assemble(base)
            assert len(code) <= QSR_RES_RESERVE, f"res shim {len(code)}B > 0x{QSR_RES_RESERVE:X}"
            assert_thumb1_only(code, base)
            return code


        def apply_hopt(ov: bytearray, rom, ov3: bool = False) -> None:
            """Route the donor's negate row through the HOPT shims (PART K). Idempotent."""
            rows = [i for i in range(CLS3_COUNT)
                    if struct.unpack_from("<H", ov, _off(CLS3_BASE + i * CLS_STRIDE))[0] == NEGATE_ROW_CID]
            off = _off(CLS3_BASE + rows[0] * CLS_STRIDE)
            res, _sub, cond = struct.unpack_from("<III", ov, off + 4)

            S = _slots(ov3)
            if res == (S["res"] | 1) and cond == (S["cond"] | 1):
                print("PART K: once-per-turn latch already installed -> no change")
                return
            assert res == NEGATE_NEW_RES and cond == NEGATE_NEW_COND, (
                f"PART K expects PART J's shape first (got +04=0x{res:08X} +0C=0x{cond:08X})"
            )

            _install(rom, ov, S["cond"], _build_hopt_cond(S["cond"]), QSR_COND_RESERVE, ov3)
            _install(rom, ov, S["res"], _build_hopt_res(S["res"]), QSR_RES_RESERVE, ov3)
            struct.pack_into("<I", ov, off + 4, S["res"] | 1)     # +04 -> res shim
            struct.pack_into("<I", ov, off + 12, S["cond"] | 1)   # +0C -> cond shim
            print(f"PART K: cls3[{rows[0]}] +04 -> 0x{S['res']:08X}, +0C -> 0x{S['cond']:08X}  "
                  f"=> ONCE PER TURN (turn-log node 0xB/0x{NEGATE_ROW_CID:04X}/1, auto-expires)")


        # ===========================================================================
        # PART I — "materials must be Synchro monsters"
        # ===========================================================================
        def _build_synchro_only_stub(base: int) -> bytes:
            """Assemble the Synchro-only material gate (Thumb-1, position-dependent literals).

            Entered by BL from 0x022482B6, where the two instructions BEFORE it have already run
            (natively, or replayed by Boggart's stub), so on entry:
                r0 = the predicate's arg2 (zone kind)   r5 = 1
                r4 = the MATERIAL's cid                 r7 = the SYNCHRO's cid
            We must reproduce `cmp r0,#0xb / beq / movs r5,#0` ourselves, because the hook consumes
            the `beq` and the following `movs r5,#0` (0x022482BA) would otherwise always execute.

            LR is deliberately NOT preserved: neither exit path returns through it (reject borrows the
            predicate's own POP epilogue; allow BXes to 0x022482BC), so the BL below may clobber it.
            r4/r5/r7 survive the call (AAPCS callee-saved, verified: 0x0202ABF8 pushes {r3,lr} only).
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only

            a = EffectBuilder()
            # --- reproduce the displaced r5 logic FIRST, while r0 still holds arg2 ---
            a.insn("CMP", "R0, #0xB")
            a.insn("BEQ", "keep")          # r0 == 0xB -> leave r5 == 1
            a.insn("MOV", "R5, #0x0")
            a.label("keep")
            # --- gate: only Shooting Quasar (donor 0x211B) is restricted ---
            a.ldr_const(3, DONOR_CID)
            a.insn("CMP", "R7, R3")
            a.insn("BNE", "cont")          # any other Synchro -> native behaviour, byte-identical
            # Boggart's remap target is a phantom with no card_prop record -> reject deterministically
            a.ldr_const(3, BOGGART_REMAP_CID)
            a.insn("CMP", "R4, R3")
            a.insn("BEQ", "reject")
            # --- card_type(material) must be a Synchro: code 17/18/19 ---
            a.insn("MOV", "R0, R4")        # 2-operand MOV (low regs) -- avoids the ADD/SUB imm3 footgun
            a.bl(CARD_TYPE_GETTER)         # r0 = (record[+4] >> 1) & 0x1F ; clobbers r0-r3 + lr only
            a.insn("SUB", "R0, #0x11")     # 2-operand SUB imm8 (17)
            a.insn("CMP", "R0, #0x2")      # 17..19 => Synchro / Synchro Effect / Synchro Tuner
            a.insn("BHI", "reject")
            a.label("cont")
            a.ldr_const(3, QSR_PRED_CONT | 1)
            a.insn("BX", "R3")             # resume the predicate's per-material switch
            a.label("reject")
            a.insn("MOV", "R0, #0x0")      # r0 = 0 => REJECT this material
            a.raw(INNER_EPILOGUE)          # POP {r1-r7,pc} -- borrow 0x0224829C's own epilogue
            code = a.assemble(base)
            assert_thumb1_only(code, base)
            assert len(code) <= QSR_PRED_RESERVE, f"stub is {len(code)}B > {QSR_PRED_RESERVE}B reserve"
            return code


        def apply_synchro_only_materials(ov: bytearray, rom, ov3: bool = False) -> None:
            """Install the Synchro-only material gate (PART I). Idempotent."""
            cur = bytes(ov[_off(QSR_PRED_HOOK):_off(QSR_PRED_HOOK) + 4])
            pred = _slots(ov3)["pred"]
            bl = thumb_bl(QSR_PRED_HOOK, pred)
            if cur == bl:
                print("PART I: Synchro-only material gate already installed -> no change")
                return
            assert cur == QSR_PRED_ORIG, (
                f"hook site 0x{QSR_PRED_HOOK:08X} = {cur.hex()}, expected {QSR_PRED_ORIG.hex()} "
                f"(cmp r0,#0xb ; beq) — the predicate moved, re-verify before patching"
            )
            # The pivot literal proves we are hooking the same, unmoved predicate Boggart anchors on.
            pivot = struct.unpack_from("<I", ov, _off(SYNCHRO_PIVOT_LIT))[0]
            assert pivot == 0x2346, f"material-predicate pivot @0x{SYNCHRO_PIVOT_LIT:08X} = 0x{pivot:04X}, expected 0x2346"

            stub = _build_synchro_only_stub(pred)
            _install(rom, ov, pred, stub, QSR_PRED_RESERVE, ov3)
            ov[_off(QSR_PRED_HOOK):_off(QSR_PRED_HOOK) + 4] = bl
            print(f"PART I: hook 0x{QSR_PRED_HOOK:08X} -> stub 0x{pred:08X} ({len(stub)}B)  "
                  f"=> Quasar's materials must be Synchro monsters (card-type 17/18/19)")


        # ===========================================================================
        # PART L — install the "when this card leaves the field" trigger
        # ===========================================================================
        def apply_leave_trigger(ov: bytearray) -> None:
            """INSERT a cls2 row for the donor carrying Yubel-TI's evolution-leave SS wiring.

            Count-neutral (drops phantom 0x1175) so the binary-searched cls2 table keeps its
            size and sort order. Idempotent -- ``_insert_sorted`` no-ops if the cid is present.

            PART L is the TRIGGER only. The donor's existing populate record (b = "Stardust
            Dragon", GY selector) is left untouched on purpose, so this step is independently
            testable in-game before PART M swaps the zone/target to the Extra Deck + 0x239D.
            """
            from otn_enhanced.effects.common import insert_row_by_stride

            # Guard 1: the model row must still look the way we decoded it. If Yubel-TI's wiring
            # moved, the resolver/condition constants below are stale and must be re-derived.
            yb = [i for i in range(CLS2_COUNT)
                  if struct.unpack_from("<H", ov, _off(CLS2_BASE + i * CLS_STRIDE))[0] == YUBEL_TI_CID]
            assert len(yb) == 1, f"expected exactly 1 cls2 row for Yubel-TI 0x{YUBEL_TI_CID:04X}, found {yb}"
            ycid, yres, yaux, ycond, ytag, ytail = struct.unpack_from(
                "<6I", ov, _off(CLS2_BASE + yb[0] * CLS_STRIDE))
            # NB: compare against the OPTIONAL tag -- that is what Yubel-TI natively carries. LEAVE_TAG
            # is the A/B knob for OUR row and may deliberately differ (see its comment).
            assert (yres, ycond, ytag) == (LEAVE_RESOLVER, LEAVE_COND_MAINDECK, LEAVE_TAG_OPTIONAL), (
                f"Yubel-TI cls2[{yb[0]}] = +04 0x{yres:08X} +0C 0x{ycond:08X} +10 0x{ytag:08X}, expected "
                f"0x{LEAVE_RESOLVER:08X}/0x{LEAVE_COND_MAINDECK:08X}/0x{LEAVE_TAG_OPTIONAL:08X} -- leave-trigger "
                f"wiring moved, re-verify against patch_minefield_driller before patching"
            )

            # Guard 2: the phantom we are about to drop must really be unreachable (no card_prop
            # record was checked when it was chosen; here we assert it is at least still present
            # and is not one of the cids the rest of the chain claims).
            assert CLS2_PHANTOM not in (0x2347, 0x234D, 0x234E, 0x1CDE, 0x1A9F, 0x2346), (
                f"phantom 0x{CLS2_PHANTOM:04X} is claimed by another patch in the chain"
            )

            insert_row_by_stride(ov, CLS2_BASE, CLS_STRIDE, CLS2_COUNT, "<6I",
                           (DONOR_CID, LEAVE_RESOLVER, LEAVE_AUX, LEAVE_COND, LEAVE_TAG, LEAVE_TAIL),
                           CLS2_PHANTOM, "cls2")
            print(f"PART L: leave-trigger installed (clone of Yubel-TI cls2[{yb[0]}])  "
                  f"=> \"when this card leaves the field: you can Special Summon ...\"")

            # Report -- but do NOT modify -- the populate record that supplies the ACTION half.
            poff = _find_populate(bytes(ov), DONOR_CID)
            if poff is not None:
                a, b, h, fl = struct.unpack_from("<HHII", ov, poff)
                print(f"        populate @0x{poff + RAM_BASE:08X}: a=0x{a:04X} b=0x{b:04X} "
                      f"h=0x{h:08X} fl=0x{fl:08X}  (untouched -- PART M retargets b -> 0x239D, "
                      f"h -> an Extra-Deck selector)")


        # ===========================================================================
        # PART N — leave trigger via the SHARED T.G. TRAMPOLINE (replaces the cls2 route)
        # ===========================================================================
        # WHY the cls2 route was abandoned. Instrumented A/B, three separate row shapes, with the
        # in-game-proven Reborn Tengu control destroyed in the SAME turn each time:
        #
        #   shape                                   control fired   Quasar resolver entered
        #   +10=0x021E51E5 (Yubel-TI optional)           yes                 NO
        #   +10=0            (Reborn Tengu mandatory)     yes                 NO
        #   +0C=0            (Dark Flare Knight, Extra)   yes (5x)            NO
        #
        # The row is correctly formed, findable (the engine's binary search was simulated and lands
        # on it), and its shim code is resident in RAM -- it is simply never consulted. cls2 dispatch
        # does not happen for this donor.
        #
        # THE FIX (user's suggestion, and the repo's own escape hatch): stop relying on a table
        # LOOKUP and use a CODE CHOKEPOINT where the departing cid is already live in a register --
        # exactly what the T.G. patches do for records-free Normal Monster donors
        # (see repo memory otn-normal-donor-trampoline-method).
        #
        #   hook 0x021C8216 (entered by BL, LR = 0x021C821A):
        #       0x021C8216: movs r1,#0x77      <- displaced
        #       0x021C8218: lsls r1,r1,#6      <- displaced
        #       0x021C821A: cmp  r4,r1         <- r4 = THE DEPARTING CARD'S CID
        #
        # tg_table._shared_arm_trampoline already owns that hook, scans a zero-terminated cid list
        # (CAVE_TG_ARMLIST), and checks [sp+0x90] = DESTROYED. We register 0x211B in that list and
        # add ONE donor-only branch: on a match for our cid, BX to the stub below instead of the
        # T.G. End-Phase gate. T.G. cids keep their exact previous path.
        #
        # ⚠️ cls1 was deliberately NOT used even though the probe was built: cls1 is the CONTINUOUS /
        # on-field class, which is where Phase 2's "maximum attacks per Battle Phase" must live. The
        # donor has exactly one cls1 row, so spending it on the leave trigger would block Phase 2.
        #
        # side comes from **[sp+0x98]** -- the leave gate 0x021CA640 does `ldr r0,[sp,#0x98]; cmp r6,r0`
        # as its controller check, so that slot holds the departing card's controller. It must be read
        # BEFORE the stub pushes anything (the trampoline is entered by BL and pushes nothing, so SP is
        # still the dispatcher's).
        #
        # ⚠️ RE-ENTRANCY is the real risk here and is not statically decidable: we drive the Special
        # Summon engine from INSIDE the card-removal path. If this freezes or corrupts, the fallback is
        # to latch a flag here and perform the summon at a later, safer point.
        LEAVE_HOOK      = 0x021C8216   # shared trampoline hook (T.G. owns it; we register our cid)
        LEAVE_SIDE_SLOT = 0x98         # [sp+0x98] = departing card's controller (from gate 0x021CA640)
        SS_FROM_EXTRA   = 0x02269314   # (side, &extra_entry, 1, (kid<<16)|flag) -> GDB-confirmed wrapper
        QSR_LEAVE_ADDR  = ov5_cave.CAVE_QSR_LEAVE
        QSR_LEAVE_RESERVE = 0x80


        def _build_leave_action(base: int = None) -> bytes:
            """Scan the controller's Extra Deck for 0x239D and Special Summon it, then resume.

            Entered by BX from the shared trampoline with SP INTACT and LR = 0x021C821A, so we
            finish by replaying the two displaced instructions and POPping into PC -- i.e. the
            dispatcher continues exactly as if the hook had not fired.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            a = EffectBuilder()
            # --- side FIRST, while SP is still the dispatcher's frame ---
            a.insn("LDR", f"R0, [SP, #0x{LEAVE_SIDE_SLOT:X}]")
            a.insn("PUSH", "{R4, R5, R6, R7, LR}")
            a.insn("MOV", "R4, R0")
            a.insn("MOV", "R7, #0x1")
            a.insn("AND", "R4, R7")                     # side &= 1
            a.ldr_const(5, PLAYER_BASE)
            a.insn("CMP", "R4, #0x0")
            a.insn("BEQ", "side0")
            a.ldr_const(6, PLAYER_STRIDE)
            a.insn("ADD", "R5, R5, R6")                 # player struct for side 1
            a.label("side0")
            a.insn("LDR", f"R6, [R5, #0x{EXTRA_CNT_OFF:X}]")   # extra deck count
            a.insn("CMP", "R6, #0x0")
            a.insn("BEQ", "done")
            a.ldr_const(7, EXTRA_ARR_OFF)
            a.insn("ADD", "R7, R7, R5")                 # r7 = &extra[0]
            a.label("loop")
            a.insn("LDR", "R0, [R7, #0x0]")
            a.ldr_const(1, 0x3FFF)
            a.insn("AND", "R0, R1")                     # cid = word & 0x3FFF
            a.ldr_const(1, SHOOTING_STAR_CID)
            a.insn("CMP", "R0, R1")
            a.insn("BEQ", "found")
            a.insn("ADD", "R7, #0x4")                   # 2-operand imm8 (avoids the imm3 footgun)
            a.insn("SUB", "R6, #0x1")
            a.insn("CMP", "R6, #0x0")
            a.insn("BNE", "loop")
            a.insn("B", "done")
            a.label("found")
            a.insn("MOV", "R0, R4")                     # side
            a.insn("MOV", "R1, R7")                     # &extra[i]  (a packed card word)
            a.insn("MOV", "R2, #0x1")
            a.ldr_const(3, (DONOR_CID << 16) | 1)       # (source kid << 16) | flag -- kid is the SOURCE
            a.bl(SS_FROM_EXTRA)
            a.label("done")
            a.insn("MOV", "R1, #0x77")                  # replay 0x021C8216
            a.insn("LSL", "R1, R1, #6")                 # replay 0x021C8218  -> r1 = 0x1DC0
            a.insn("POP", "{R4, R5, R6, R7, PC}")       # return to 0x021C821A with r4 (cid) intact
            base = QSR_LEAVE_ADDR if base is None else base
            code = a.assemble(base)
            assert_thumb1_only(code, base)
            assert len(code) <= QSR_LEAVE_RESERVE, f"leave stub {len(code)}B > 0x{QSR_LEAVE_RESERVE:X}"
            return code


        def apply_leave_trampoline(ov: bytearray, rom, ov3: bool = False) -> None:
            """Register the donor with the shared leave trampoline + install its action stub."""
            from otn_enhanced.effects.tg_table import arm_tg_leave_trigger
            from otn_enhanced.effects import tg_table
            leave = _slots(ov3)["leave"]
            assert (tg_table.IMMEDIATE_ACTION, tg_table.IMMEDIATE_ACTION3) == (QSR_LEAVE_ADDR, cave3.CAVE3_QSR_LEAVE), \
                "tg_table's Quasar literals disagree with the slots"
            _install(rom, ov, leave, _build_leave_action(leave), QSR_LEAVE_RESERVE, ov3)
            arm_tg_leave_trigger(rom, ov, DONOR_CID, immediate=leave)
            print(f"PART N: 0x{DONOR_CID:04X} registered on the shared leave trampoline "
                  f"(hook 0x{LEAVE_HOOK:08X}); action stub @0x{leave:08X}  "
                  f"=> on destruction, SS \"Shooting Star Dragon\" 0x{SHOOTING_STAR_CID:04X} from the Extra Deck")


        PLAYER_BASE   = 0x0229AC94
        PLAYER_STRIDE = 0xB3C
        EXTRA_ARR_OFF = 0x4E4
        EXTRA_CNT_OFF = 0x18


        # ===========================================================================
        # DIAGNOSTIC — black-box recorder for the leave trigger (set RECORDER = True)
        # ===========================================================================
        # WHY: three melonDS GDB sessions in a row died the same way (memory reads fine, `continue`
        # closes the connection, ZERO breakpoint hits), so control-flow data via the stub is not
        # obtainable here. This is the repo's proven alternative -- the Hyper Librarian
        # "black-box recorder" (see librarian_recorder.py): instrument the code to write counters
        # into an ov5 scratch word, then read them out of a SAVESTATE.
        #
        # Crucially this hooks NOTHING SHARED: it only repoints OUR OWN cls2 row's +0C / +04 at
        # shims that bump counters and then tail-call the real condition / resolver. Zero blast
        # radius, so it is safe to ship in a test build.
        #
        # Reading the counters afterwards answers the one open question outright:
        #   +00 == 0                -> the condition never runs AT ALL (wrong gate entirely)
        #   +00 > 0 but +08 == 0    -> cls2 IS consulted for other cards but NEVER for 0x211B
        #                              => the leave event does not dispatch class 2 for a SYNCHRO
        #   +08 > 0 and +10 == 0    -> the row IS consulted; the CONDITION denies it
        #   +10 > 0 but +14 == 0    -> condition passes but the resolver is never entered
        #   +14 > 0                 -> everything upstream works; the bug is in the resolver/selector
        RECORDER = os.environ.get("QSR_RECORDER") == "1"   # QSR_RECORDER=1 builds the diagnostic ROM
        REC_SCRATCH = ov5_cave.CAVE_QSR_SCRATCH
        REC_COND_ADDR = ov5_cave.CAVE_QSR_RECSTUB
        REC_RES_ADDR  = ov5_cave.CAVE_QSR_RESREC
        REC_RES1_ADDR = ov5_cave.CAVE_QSR_RESREC1   # same recorder, installed on the CLS1 row


        def _build_cond_recorder() -> bytes:
            """cond_shim(ctx, arg1): bump counters, then tail-call the real condition."""
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, R6, LR}")
             .insn("ADD", "R4, R0, #0x0")          # r4 = ctx
             .insn("ADD", "R5, R1, #0x0")          # r5 = arg1
             .ldr_const(6, REC_SCRATCH))           # r6 = scratch
            # +00 ++ (any cid)
            a.insn("LDR", "R0, [R6, #0x0]").insn("ADD", "R0, #0x1").insn("STR", "R0, [R6, #0x0]")
            # +04 = last cid seen
            a.insn("LDRH", "R0, [R4, #0x0]").insn("STR", "R0, [R6, #0x4]")
            # if cid != donor -> skip the per-donor counters
            a.ldr_const(1, DONOR_CID)
            a.insn("CMP", "R0, R1").insn("BNE", "chain")
            a.insn("LDR", "R0, [R6, #0x8]").insn("ADD", "R0, #0x1").insn("STR", "R0, [R6, #0x8]")
            a.label("chain")
            a.insn("ADD", "R0, R4, #0x0").insn("ADD", "R1, R5, #0x0")
            # Chain the MAIN-DECK condition explicitly: this shim is only ever installed on rows that
            # HAVE a condition (the Tengu control). Quasar's row now carries the null condition and is
            # deliberately left unwrapped, so LEAVE_COND itself may be 0 and is not a valid BL target.
            a.bl(LEAVE_COND_MAINDECK & ~1)
            # record the verdict, but only attribute it to the donor when the cid matched
            a.insn("LDRH", "R1, [R4, #0x0]")
            a.ldr_const(2, DONOR_CID)
            a.insn("CMP", "R1, R2").insn("BNE", "out")
            a.insn("STR", "R0, [R6, #0xC]")        # last verdict for the donor
            a.insn("CMP", "R0, #0x0").insn("BEQ", "out")
            a.insn("LDR", "R1, [R6, #0x10]").insn("ADD", "R1, #0x1").insn("STR", "R1, [R6, #0x10]")
            a.label("out")
            a.insn("POP", "{R4, R5, R6, PC}")      # never POP into LR (Thumb-1 footgun)
            code = a.assemble(REC_COND_ADDR)
            assert_thumb1_only(code, REC_COND_ADDR)
            assert len(code) <= 0x60, f"cond recorder {len(code)}B > 0x60"
            return code


        def _build_res_recorder(addr: int = None, donor_slot: int = 0x14,
                                ctrl_slot: int = 0x18, cid_slot: int = 0x1C) -> bytes:
            """res_shim(ctx, ev): count resolver entries PER CID, then tail-call the real resolver.

            ROUND 3: the previous version bumped a single counter shared by both instrumented
            rows, so a nonzero +14 could not be attributed to Quasar vs the Tengu control --
            useless for the very comparison it existed to make. Now:
                +14 resolver entered for 0x211B (Quasar)
                +18 resolver entered for 0x2085 (control)
                +1C last cid seen at the resolver
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            addr = REC_RES_ADDR if addr is None else addr
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, R6, LR}")
             .insn("ADD", "R4, R0, #0x0")
             .insn("ADD", "R5, R1, #0x0")
             .ldr_const(6, REC_SCRATCH))
            a.insn("LDRH", "R0, [R4, #0x0]").insn("STR", f"R0, [R6, #0x{cid_slot:X}]")
            a.ldr_const(1, DONOR_CID)
            a.insn("CMP", "R0, R1").insn("BNE", "ctrl")
            (a.insn("LDR", f"R0, [R6, #0x{donor_slot:X}]").insn("ADD", "R0, #0x1")
              .insn("STR", f"R0, [R6, #0x{donor_slot:X}]"))
            a.insn("B", "go")
            a.label("ctrl")
            a.ldr_const(1, CONTROL_CID)
            a.insn("CMP", "R0, R1").insn("BNE", "go")
            (a.insn("LDR", f"R0, [R6, #0x{ctrl_slot:X}]").insn("ADD", "R0, #0x1")
              .insn("STR", f"R0, [R6, #0x{ctrl_slot:X}]"))
            a.label("go")
            a.insn("ADD", "R0, R4, #0x0").insn("ADD", "R1, R5, #0x0")
            a.bl(LEAVE_RESOLVER & ~1)
            a.insn("POP", "{R4, R5, R6, PC}")
            code = a.assemble(addr)
            assert_thumb1_only(code, addr)
            assert len(code) <= 0x50, f"res recorder {len(code)}B > 0x50"
            return code


        CONTROL_CID = 0x2085          # Minefield Driller -> "Reborn Tengu": the WORKING leave trigger,
                                      # step 1 of the same chain. Instrumenting it with the SAME shims
                                      # gives a positive control: if destroying Tengu moves the counters
                                      # and destroying Quasar does not, the recorder is proven functional
                                      # and the difference is real (not a broken shim).


        def _build_cls1_probe() -> bytes:
            """cls1 class-probe: count the call, record the cid, return 0. NEVER chains.

            Deliberately does NOT tail-call the leave-SS resolver. cls1 is the CONTINUOUS /
            on-field class, so it may be invoked constantly; running a Special-Summon state
            machine from there could do real damage in a test build. We only need to know
            WHETHER the row is reached, so counting is enough. Returning 0 keeps the row inert,
            exactly as PART B left it.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder
            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R6, LR}")
             .insn("ADD", "R4, R0, #0x0")
             .ldr_const(6, REC_SCRATCH))
            a.insn("LDR", "R0, [R6, #0x20]").insn("ADD", "R0, #0x1").insn("STR", "R0, [R6, #0x20]")
            a.insn("LDRH", "R0, [R4, #0x0]").insn("STR", "R0, [R6, #0x28]")   # cid seen at cls1
            a.insn("MOV", "R0, #0x0")                                          # stay inert
            a.insn("POP", "{R4, R6, PC}")
            code = a.assemble(REC_RES1_ADDR)
            assert_thumb1_only(code, REC_RES1_ADDR)
            assert len(code) <= 0x30, f"cls1 probe {len(code)}B > 0x30"
            return code


        def apply_recorder(ov: bytearray, rom) -> None:
            """Repoint the donor's AND the control's cls2 rows at the recorder shims.

            ROUND 2: the first diagnostic came back all-zero for Quasar, but with NO positive
            control there was no way to tell "our row is never consulted" from "my shim is
            broken". Reborn Tengu (0x2085) shares this exact resolver+condition pair and is
            known to work in-game, so pointing its row at the same shims turns the next test
            into a controlled A/B. Still no shared code is hooked -- only two specific rows.
            """
            if not RECORDER:
                return
            ov5_cave.install_cave(rom, REC_COND_ADDR, _build_cond_recorder(), reserve=0x60)
            ov5_cave.install_cave(rom, REC_RES_ADDR, _build_res_recorder(), reserve=0x50)
            ov5_cave.install_cave(rom, REC_SCRATCH, b"\x00" * 0x20, reserve=0x20)

            for cid, label in ((DONOR_CID, "Quasar"), (CONTROL_CID, "Reborn Tengu CONTROL")):
                rows = [i for i in range(CLS2_COUNT)
                        if struct.unpack_from("<H", ov, _off(CLS2_BASE + i * CLS_STRIDE))[0] == cid]
                if len(rows) != 1:
                    print(f"DIAG: WARNING - expected 1 cls2 row for 0x{cid:04X}, found {rows}; skipped")
                    continue
                off = _off(CLS2_BASE + rows[0] * CLS_STRIDE)
                res, cond = struct.unpack_from("<I", ov, off + 4)[0], struct.unpack_from("<I", ov, off + 12)[0]
                # The control only carries the leave-SS shape in the CHAIN (Reborn Tengu is step 1).
                # In a standalone build it still has its native resolver -- skip it rather than abort.
                if res not in (LEAVE_RESOLVER, REC_RES_ADDR | 1):
                    print(f"DIAG: 0x{cid:04X} ({label}) +04 = 0x{res:08X}, not the leave resolver "
                          f"-- not instrumented (expected in a standalone build)")
                    continue
                struct.pack_into("<I", ov, off + 4, REC_RES_ADDR | 1)   # resolver: always instrument
                # ⚠️ Only wrap +0C when the row HAS a condition. Our row now deliberately carries the
                # NULL condition (Dark Flare Knight's Extra-Deck shape); pointing it at a shim would
                # make it non-null and silently destroy the very thing being tested.
                note = "+04 only (null cond preserved)"
                if cond not in (0, REC_COND_ADDR | 1):
                    struct.pack_into("<I", ov, off + 12, REC_COND_ADDR | 1)
                    note = f"+04 and +0C (was 0x{cond:08X})"
                print(f"DIAG: cls2[{rows[0]}] 0x{cid:04X} ({label}) instrumented: {note}")
            # --- ROUND 4: which CLASS does this card's leave actually dispatch to? ---
            # cls2 is proven never consulted for 0x211B across three row shapes, while the Reborn
            # Tengu control fires every time. Rather than guess again, instrument the donor's OTHER
            # class row. PART B left cls1[0x211B] fully zeroed (its End-Phase self-bounce), so that
            # row is free real estate: give it the same recorder and see whether the leave event
            # dispatches CLASS 1 for this card instead.
            #   +20 > 0  => the leave dispatches cls1 for 0x211B -> move the trigger there
            #   +20 == 0 => neither cls1 nor cls2 -> the class tables are not the route at all,
            #               fall back to the per-cid leave hook 0x021C8216
            rows1 = [i for i in range(CLS1_COUNT)
                     if struct.unpack_from("<H", ov, _off(CLS1_BASE + i * CLS_STRIDE))[0] == DONOR_CID]
            if len(rows1) == 1:
                off1 = _off(CLS1_BASE + rows1[0] * CLS_STRIDE)
                res1 = struct.unpack_from("<I", ov, off1 + 4)[0]
                if res1 in (0, REC_RES1_ADDR | 1):
                    ov5_cave.install_cave(rom, REC_RES1_ADDR, _build_cls1_probe(), reserve=0x30)
                    struct.pack_into("<I", ov, off1 + 4, REC_RES1_ADDR | 1)
                    print(f"DIAG: cls1[{rows1[0]}] 0x{DONOR_CID:04X} +04 0x{res1:08X} -> "
                          f"0x{REC_RES1_ADDR:08X} (class-probe, counter +0x20)")
                else:
                    print(f"DIAG: cls1[{rows1[0]}] +04 = 0x{res1:08X} (not free) -- class probe skipped")
            print(f"DIAG: counters @0x{REC_SCRATCH:08X}  "
                  f"(+14 cls2/0x{DONOR_CID:04X}, +18 cls2/ctrl, +20 cls1/0x{DONOR_CID:04X})")


        # ===========================================================================
        # PART M — summon "Shooting Star Dragon" from the EXTRA DECK (not Stardust from the GY)
        # ===========================================================================
        def _build_extra_selector(ov: bytes, base: int) -> bytes:
            """Clone the donor's GY selector, swapping the flags word and the zone builder.

            Byte-verbatim clone (including the trailing filter literal, so the `ldr r2,[pc,#8]`
            needs no fixup), with exactly two edits: `movs r0,#8` -> `movs r0,#2`, and the
            builder BL retargeted from the GRAVEYARD builder to the EXTRA DECK builder.
            """
            blob = bytearray(ov[_off(EXSEL_SRC):_off(EXSEL_SRC) + EXSEL_LEN])

            # Guard: the clone source must still be the selector we decoded.
            got = bytes(blob[EXSEL_OFF_FLAGS:EXSEL_OFF_FLAGS + 2])
            assert got == EXSEL_ORIG_FLAGS, (
                f"selector @0x{EXSEL_SRC:08X}+0x{EXSEL_OFF_FLAGS:X} = {got.hex()}, expected "
                f"{EXSEL_ORIG_FLAGS.hex()} (movs r0,#8) -- the donor's selector moved"
            )
            assert bytes(blob[EXSEL_OFF_BL:EXSEL_OFF_BL + 4]) == thumb_bl(
                EXSEL_SRC + EXSEL_OFF_BL, GY_BUILDER), (
                f"selector BL @0x{EXSEL_SRC + EXSEL_OFF_BL:08X} is not `bl 0x{GY_BUILDER:08X}`"
            )
            # The trailing literal must be the NAMED-target filter (we rely on it, unmodified).
            lit = struct.unpack_from("<I", blob, 0x28)[0]
            assert lit == NAMED_FILTER, (
                f"selector literal = 0x{lit:08X}, expected the named-match filter 0x{NAMED_FILTER:08X}"
            )

            blob[EXSEL_OFF_FLAGS:EXSEL_OFF_FLAGS + 2] = EXSEL_NEW_FLAGS
            blob[EXSEL_OFF_BL:EXSEL_OFF_BL + 4] = thumb_bl(base + EXSEL_OFF_BL, EXTRA_BUILDER)

            from otn_enhanced.asm.effect_verify import assert_thumb1_only
            assert_thumb1_only(bytes(blob[:0x26]), base)   # code only; 0x28.. is the literal
            return bytes(blob)


        def apply_extra_deck_revive(ov: bytearray, rom, ov3: bool = False) -> None:
            """Retarget the donor's populate record: SS "Shooting Star Dragon" from the EXTRA DECK.

            PART L supplies the trigger; this supplies the action. Idempotent.
            """
            poff = _find_populate(bytes(ov), DONOR_CID)
            assert poff is not None, f"donor 0x{DONOR_CID:04X} has no populate record to retarget"
            a, b, h, fl = struct.unpack_from("<HHII", ov, poff)
            exsel = _slots(ov3)["exsel"]

            if (b, h, fl) == (SHOOTING_STAR_CID, exsel | 1, POP_FL_YUBEL):
                print("PART M: Extra-Deck revive already installed -> no change")
                return
            assert b in (DONOR_POP_TARGET, SHOOTING_STAR_CID), (
                f"populate b = 0x{b:04X}, expected the donor's 0x{DONOR_POP_TARGET:04X} "
                f"-- record changed, re-verify before patching"
            )
            assert h in (DONOR_POP_SELECTOR, exsel | 1), f"populate h = 0x{h:08X}"

            # Sanity: the flags we adopt must really be Yubel-TI's (the resolver PART L installed).
            ypoff = _find_populate(bytes(ov), YUBEL_POP_CID)
            assert ypoff is not None, "Yubel-TI has no populate record -- cannot confirm the flags"
            _ya, _yb, _yh, yfl = struct.unpack_from("<HHII", ov, ypoff)
            assert yfl == POP_FL_YUBEL, (
                f"Yubel-TI populate flags = 0x{yfl:08X}, expected 0x{POP_FL_YUBEL:08X} "
                f"-- re-derive before adopting them"
            )

            blob = _build_extra_selector(bytes(ov), exsel)
            _install(rom, ov, exsel, blob, EXSEL_RESERVE, ov3)

            struct.pack_into("<H", ov, poff + 0x02, SHOOTING_STAR_CID)   # b  -> Shooting Star Dragon
            struct.pack_into("<I", ov, poff + 0x04, exsel | 1)           # h  -> Extra-Deck selector (Thumb)
            struct.pack_into("<I", ov, poff + 0x08, POP_FL_YUBEL)        # fl -> Yubel-TI's proven flags
            print(f"PART M: populate @0x{poff + RAM_BASE:08X}  b 0x{b:04X}->0x{SHOOTING_STAR_CID:04X}, "
                  f"h 0x{h:08X}->0x{exsel:08X}|1, fl 0x{fl:08X}->0x{POP_FL_YUBEL:08X}\n"
                  f"        => Special Summon 1 \"Shooting Star Dragon\" from your EXTRA DECK "
                  f"({len(blob)}B selector: builder 0x{GY_BUILDER:08X}->0x{EXTRA_BUILDER:08X}, flags #8->#2)")


        def _find_populate(ov: bytes, cid: int) -> int | None:
            """Return the byte offset of the populate record whose 'a' (source cid) == *cid*."""
            hits = [i for i in range(POP_COUNT)
                    if struct.unpack_from("<H", ov, _off(POP_BASE + i * POP_STRIDE))[0] == cid]
            assert len(hits) <= 1, f"expected at most 1 populate record for 0x{cid:04X}, found {hits}"
            return _off(POP_BASE + hits[0] * POP_STRIDE) if hits else None


        # ===========================================================================
        # PART H — make the donor's effect-registry row inert (the End-Phase "SS Stardust" half)
        # ===========================================================================
        def _find_registry_row(ov: bytes, cid: int) -> int | None:
            """Return the byte offset of *cid*'s registry row, asserting it is unique."""
            hits = [i for i in range(REG_COUNT)
                    if struct.unpack_from("<H", ov, _off(REG_BASE + i * REG_STRIDE) + 4)[0] == cid]
            assert len(hits) <= 1, f"expected at most 1 registry row for 0x{cid:04X}, found {hits}"
            return _off(REG_BASE + hits[0] * REG_STRIDE) if hits else None


        def apply_registry_neutralise(ov: bytearray) -> None:
            """Blank the cid of the donor's registry row, KEEPING its resolver (the engine's own idiom).

            This is the second half of the donor's End-Phase clause ("Special Summon 1 'Stardust
            Dragon' from your Graveyard"). PART B removes the bounce; without this the card still
            visibly ACTIVATES during the End Phase (confirmed in-game). Idempotent.
            """
            off = _find_registry_row(bytes(ov), DONOR_CID)
            if off is None:                                            # idempotent
                print(f"PART H: no registry row for 0x{DONOR_CID:04X} -> already inert, no change")
                return
            res = struct.unpack_from("<I", ov, off)[0]
            assert res == REG_ENDPHASE_RES, (
                f"registry row for 0x{DONOR_CID:04X} has resolver 0x{res:08X}, expected "
                f"0x{REG_ENDPHASE_RES:08X} — the registry moved, re-verify before patching"
            )
            # cid = 0 (never matches an on-field card); resolver KEPT non-zero (a null would be BLX 0).
            struct.pack_into("<H", ov, off + 4, 0)
            print(f"PART H: registry row @0x{off + RAM_BASE:08X} cid 0x{DONOR_CID:04X} -> 0x0000 "
                  f"(resolver 0x{res:08X} kept)  => no more End-Phase \"SS Stardust\" activation")


        # ===========================================================================
        # PART C — visible stats + name/description
        # ===========================================================================
        def apply_text(out_path: str, *, write_text: bool = False) -> None:
            """Set card_prop stats and (optionally) the name/description, all strictly in place.

            card_type is deliberately NOT passed: the donor already decodes to type code 18
            ("Synchro Effect Monster"), which is exactly what grants "Must be Synchro Summoned /
            cannot be Special Summoned by other ways". Changing it would break the card.
            """
            apply_stats_and_text(
                out_path,
                cid=DONOR_CID,
                attribute="LIGHT",
                race="Dragon",
                level=12,
                atk=4000,
                defense=4000,
                name=QUASAR_NAME,
                desc=QUASAR_DESC,
                langs="efgijkrs",
                write_text=write_text,
                skip_name_if_too_long=True,   # belt-and-braces: never grow a name blob (a grown blob is a confirmed freeze)
            )


        # ===========================================================================
        # ov3 compaction: the five live stubs can live in the ov3 pool (cave3.CAVE3_QSR_*),
        # which stays resident in a puzzle where ov41 evicts ov5. Opt-in until the user signs off.
        # ===========================================================================
        def _slots(ov3: bool) -> dict:
            if ov3:
                return dict(pred=cave3.CAVE3_QSR_PRED, cond=cave3.CAVE3_QSR_COND, res=cave3.CAVE3_QSR_RES,
                            exsel=cave3.CAVE3_QSR_EXSEL, leave=cave3.CAVE3_QSR_LEAVE)
            return dict(pred=QSR_PRED_STUB, cond=QSR_COND_ADDR, res=QSR_RES_ADDR,
                        exsel=EXSEL_ADDR, leave=QSR_LEAVE_ADDR)


        def _install(rom, ov: bytearray, addr: int, blob: bytes, reserve: int, ov3: bool) -> None:
            """ov5 cave, or the ov3 pool slot -- which must be zero (step 0 ran) or already hold *blob*."""
            if not ov3:
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                return
            size = next(s["size"] for s in parse_cave3_slots() if s["addr"] == addr)
            cave3._checked(addr, size, blob, "")
            o = _off(addr)
            assert bytes(ov[o:o + size]) in (bytes(size), blob.ljust(size, b"\0")), \
                f"ov3 slot @{addr:#x} is not zero -- step 0 (ov3_compact) must run first"
            ov[o:o + len(blob)] = blob


        def _cave_bytes(rom, ov: bytes, addr: int, n: int) -> bytes:
            """*n* bytes at *addr*, read from ov3 if it is a pool address, else from the ov5 cave."""
            if addr < ov5_cave.OV5_RAM_BASE:
                return bytes(ov[_off(addr):_off(addr) + n])
            return ov5_cave.read_cave(rom, addr, n)


        # ===========================================================================
        # Driver
        # ===========================================================================


        def install(rom, view):
            ov = view.buf
            ov3 = True
            apply_material_rule(ov)          # PART A: LIST_A removal -> "2 or more" materials
            apply_double_attack(ov)          # PART O: can attack twice each Battle Phase
            apply_endphase_neutralise(ov)    # PART B: kill the End-Phase self-bounce
            apply_named_material_fix(ov)     # PART D: drop the 1st named-material rule (gates the Tuner)
            apply_pair_material_fix(ov)      # PART E: drop the 2nd named-material rule (the pair check)
            apply_generic_nontuner_rule(ov)  # PART F: use the engine's generic "non-Tuners only" rule
            apply_registry_neutralise(ov)    # PART H: kill the End-Phase "SS Stardust from GY" half
            apply_synchro_only_materials(ov, rom, ov3)   # PART I: materials must be Synchro monsters
            apply_negate_retune(ov)          # PART J: negate the activation + destroy IT (no Tribute)
            apply_hopt(ov, rom, ov3)         # PART K: once per turn (turn-log latch)
            apply_extra_deck_revive(ov, rom, ov3)  # PART M: SS 1 "Shooting Star Dragon" from the Extra Deck
            apply_leave_trampoline(ov, rom, ov3)   # PART N: leave trigger via the shared T.G. trampoline
            apply_recorder(ov, rom)          # DIAGNOSTIC: only when QSR_RECORDER=1 in the environment

        def check_fn(c, rom, view):
            ok = True
            ov = bytes(view.buf)
            cov = bytes(load_overlay3(SRC)[1])

            # --- PART A ---
            tbl = list(struct.unpack_from(f"<{LIST_A_COUNT}H", ov, _off(LIST_A)))
            a_ok = (len(tbl) == LIST_A_COUNT
                    and DONOR_CID not in tbl
                    and LIST_A_PHANTOM in tbl
                    and all(tbl[i] < tbl[i + 1] for i in range(len(tbl) - 1)))
            ok &= a_ok
            print(f"[{'PASS' if a_ok else 'FAIL'}] PART A: LIST_A = {[hex(x) for x in tbl]}")

            # The classifiers' hard-coded counts must be untouched.
            imm_ok = (struct.unpack_from("<H", ov, _off(LIST_A_COUNT_IMM))[0] == (0x2200 | LIST_A_COUNT)
                      and struct.unpack_from("<H", ov, _off(LIST_B_COUNT_IMM))[0] == 0x2215)
            ok &= imm_ok
            print(f"[{'PASS' if imm_ok else 'FAIL'}] PART A: classifier count immediates unchanged")

            # --- PART O ---
            dbl = list(struct.unpack_from(f"<{DBLATK_COUNT}H", ov, _off(DBLATK_LIST)))
            cdbl = list(struct.unpack_from(f"<{DBLATK_COUNT}H", cov, _off(DBLATK_LIST)))
            o_ok = (len(dbl) == DBLATK_COUNT
                    and DONOR_CID in dbl
                    and DBLATK_PHANTOM not in dbl
                    and all(dbl[i] < dbl[i + 1] for i in range(len(dbl) - 1))
                    # exact delta: +donor / -phantom, every other cid survives
                    and set(dbl) - set(cdbl) == {DONOR_CID}
                    and set(cdbl) - set(dbl) == {DBLATK_PHANTOM})
            ok &= o_ok
            print(f"[{'PASS' if o_ok else 'FAIL'}] PART O: double-attack list = {[hex(x) for x in dbl]}")

            # The searcher's hard-coded count and list literal must be untouched.
            o_imm_ok = (struct.unpack_from("<H", ov, _off(DBLATK_COUNT_IMM))[0] == (0x2200 | DBLATK_COUNT)
                        and struct.unpack_from("<I", ov, _off(DBLATK_LIST_LIT))[0] == DBLATK_LIST)
            ok &= o_imm_ok
            print(f"[{'PASS' if o_imm_ok else 'FAIL'}] PART O: searcher count immediate + list literal unchanged")

            # The DIRECT-ATTACK and PIERCING lists abut ours -- an off-by-one here would silently
            # rewrite them, so check the whole neighbouring region.
            # ⚠️ This USED to be a flat byte-compare against clean, which is no longer legal:
            # wattcobra legitimately inserts its donor into the direct-attack list
            # 0x0226D730 (count-neutrally, over a phantom), so on the CHAINED ROM those 50
            # bytes differ from clean by design. The tripwire is therefore split:
            #   * the direct-attack list must still be exactly 25 STRICTLY SORTED entries --
            #     an overrun from our own 15-entry rewrite at 0x0226D712 lands on entry 0 and
            #     breaks that ordering, which is the failure this check exists to catch;
            #   * everything from its 0x0000 terminator onwards (the PIERCING list) must still
            #     be byte-identical to clean, since no patch of ours may reach past it.
            da = list(struct.unpack_from("<25H", ov, _off(DBLATK_NEXT_LIST)))
            da_ok = all(da[i] < da[i + 1] for i in range(len(da) - 1))
            term_off = _off(DBLATK_NEXT_LIST) + 25 * 2
            o_nb_ok = da_ok and ov[term_off:term_off + 0x2E] == cov[term_off:term_off + 0x2E]
            ok &= o_nb_ok
            print(f"[{'PASS' if o_nb_ok else 'FAIL'}] PART O: direct-attack list still 25 sorted entries, "
                  f"piercing list byte-identical to clean")

            # LIST_B must still contain the donor (min 3 materials).
            listb = list(struct.unpack_from("<21H", ov, _off(0x02275AD8)))
            b_ok = DONOR_CID in listb
            ok &= b_ok
            print(f"[{'PASS' if b_ok else 'FAIL'}] PART A: donor still in LIST_B (min 3 materials)")

            # --- PART B ---
            off = _find_cls1(ov, DONOR_CID)
            cid, _pad, res, aux, cond, tag, tail = struct.unpack_from("<HHIIIII", ov, off)
            b2_ok = (cid == DONOR_CID and (res, aux, cond, tag, tail) == (0, 0, 0, 0, 0))
            ok &= b2_ok
            print(f"[{'PASS' if b2_ok else 'FAIL'}] PART B: cls1 row inert "
                  f"(cid=0x{cid:04X} +04=0x{res:08X} +14=0x{tail:08X})")

            # --- PART D ---
            cur = struct.unpack_from("<H", ov, _off(NAMED_MAT_BRANCH))[0]
            d_ok = cur == _thumb_b(NAMED_MAT_BRANCH, GENERIC_ALLOW)
            ok &= d_ok
            print(f"[{'PASS' if d_ok else 'FAIL'}] PART D: named-material branch @0x{NAMED_MAT_BRANCH:08X} "
                  f"= 0x{cur:04X} (b 0x{GENERIC_ALLOW:08X} = generic ALLOW)")

            # Majestic Red's mirror leaf must be untouched (proves the edit is donor-only).
            red_ok = ov[_off(0x02248A2C):_off(0x02248A2C) + 0x14] == cov[_off(0x02248A2C):_off(0x02248A2C) + 0x14]
            ok &= red_ok
            print(f"[{'PASS' if red_ok else 'FAIL'}] PART D: Majestic Red's named-material leaf untouched")

            # --- PART E ---
            cur = struct.unpack_from("<H", ov, _off(PAIR_BRANCH))[0]
            e_ok = cur == _thumb_b(PAIR_BRANCH, ACCEPT_TRAMP)
            ok &= e_ok
            print(f"[{'PASS' if e_ok else 'FAIL'}] PART E: pair-material branch @0x{PAIR_BRANCH:08X} "
                  f"= 0x{cur:04X} (b 0x{ACCEPT_TRAMP:08X} -> ACCEPT)")

            # --- PART F ---
            cur = struct.unpack_from("<H", ov, _off(NONTUNER_BHS))[0]
            f_ok = cur == _thumb_bcc(NONTUNER_BHS, GENERIC_NONTUNER, 2)
            ok &= f_ok
            print(f"[{'PASS' if f_ok else 'FAIL'}] PART F: @0x{NONTUNER_BHS:08X} = 0x{cur:04X} "
                  f"(bhs 0x{GENERIC_NONTUNER:08X} = generic non-Tuner rule)")

            # Majestic Red must keep its own rule + leaf (proves E/F are donor-only).
            red_ok = (ov[_off(0x02249D3C):_off(0x02249D3C) + 2] == cov[_off(0x02249D3C):_off(0x02249D3C) + 2]
                      and ov[_off(PAIR_LEAF):_off(PAIR_LEAF) + 0x40] == cov[_off(PAIR_LEAF):_off(PAIR_LEAF) + 0x40])
            ok &= red_ok
            print(f"[{'PASS' if red_ok else 'FAIL'}] PARTS E/F: Majestic Red's branch + the shared leaf body untouched")

            # --- PART H ---
            h_off = _find_registry_row(ov, DONOR_CID)
            h_ok = h_off is None
            ok &= h_ok
            print(f"[{'PASS' if h_ok else 'FAIL'}] PART H: no registry row matches 0x{DONOR_CID:04X} "
                  f"(End-Phase 'SS Stardust' inert)")
            # the resolver must still be intact (a null would BLX 0), and Majestic Red's row untouched
            creg = _find_registry_row(cov, DONOR_CID)
            hres_ok = creg is not None and struct.unpack_from("<I", ov, creg)[0] == REG_ENDPHASE_RES
            ok &= hres_ok
            print(f"[{'PASS' if hres_ok else 'FAIL'}] PART H: resolver kept non-zero at the blanked row")
            red_reg = _find_registry_row(ov, 0x21CB)
            rr_ok = red_reg is not None
            ok &= rr_ok
            print(f"[{'PASS' if rr_ok else 'FAIL'}] PART H: Majestic Red's registry row still intact")

            # --- PART I ---
            cur = bytes(ov[_off(QSR_PRED_HOOK):_off(QSR_PRED_HOOK) + 4])
            # Home of the five stubs (ov5 cave or ov3 pool), decided by the live PART I hook.
            on3 = cur == thumb_bl(QSR_PRED_HOOK, cave3.CAVE3_QSR_PRED)
            S = _slots(on3)
            rom_v = rom
            i_ok = cur == thumb_bl(QSR_PRED_HOOK, S["pred"])
            ok &= i_ok
            print(f"[{'PASS' if i_ok else 'FAIL'}] PART I: hook @0x{QSR_PRED_HOOK:08X} = {cur.hex()} "
                  f"(BL -> stub 0x{S['pred']:08X}, {'ov3 pool' if on3 else 'ov5 cave'})")
            # Boggart's adjacent hook must not have been clobbered BY US. The two sites chain and
            # must not overlap, but Boggart legitimately owns 0x022482B2 and rewrites it in a
            # combined build -- so comparing against the CLEAN rom made this fail on every chained
            # build by design. The real invariant is: the site is either pristine (standalone) or
            # Boggart's own BL into CAVE_BOGGART; anything else -- in particular a BL into OUR
            # stub -- means the two detours have collided.
            bog_cur = bytes(ov[_off(0x022482B2):_off(0x022482B2) + 4])
            bog_native = bog_cur == cov[_off(0x022482B2):_off(0x022482B2) + 4]
            # Boggart's stub moved ov5 -> ov3 (cave3.CAVE3_BOGGART); accept either home.
            from otn_enhanced.effects import cave3 as _c3
            bog_owned = bog_cur in (thumb_bl(0x022482B2, ov5_cave.CAVE_BOGGART),
                                    thumb_bl(0x022482B2, _c3.CAVE3_BOGGART))
            bog_ok = bog_native or bog_owned
            ok &= bog_ok
            who = "pristine (standalone build)" if bog_native else (
                f"Boggart's BL (chained build)" if bog_owned
                else f"UNRECOGNISED {bog_cur.hex()} -- detour collision")
            print(f"[{'PASS' if bog_ok else 'FAIL'}] PART I: Boggart's site 0x022482B2 is {who}")
            # The stub must actually be present in the appended ov5 region.
            ov5 = rom_v.loadArm9Overlays()[ov5_cave.OV5_ID].data
            want = _build_synchro_only_stub(S["pred"])
            blob = _cave_bytes(rom_v, ov, S["pred"], len(want))
            s_ok = blob == want
            ok &= s_ok
            print(f"[{'PASS' if s_ok else 'FAIL'}] PART I: stub @0x{S['pred']:08X} matches the builder "
                  f"(first bytes {blob[:8].hex()})")
            # Always disassemble the built stub (Thumb-1 encoding footguns bite silently).
            try:
                from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
                md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
                print("        stub disassembly:")
                for ins in md.disasm(blob, S["pred"]):
                    print(f"          0x{ins.address:08X}: {ins.mnemonic:6} {ins.op_str}")
            except ImportError:
                pass

            # --- PART L RETIRED: assert the donor has NO cls2 row (that route is abandoned) ---
            l_rows = [i for i in range(CLS2_COUNT)
                      if struct.unpack_from("<H", ov, _off(CLS2_BASE + i * CLS_STRIDE))[0] == DONOR_CID]
            l_ok = not l_rows
            ok &= l_ok
            print(f"[{'PASS' if l_ok else 'FAIL'}] PART L retired: donor has no cls2 row "
                  f"(proven inert; PART N replaces it)")

            # --- PART N: the leave trampoline ---
            from otn_enhanced.effects import tg_table as _tg
            rom_n = rom_v
            stub = _build_leave_action(S["leave"])
            n_ok = _cave_bytes(rom_v, ov, S["leave"], len(stub)) == stub
            ok &= n_ok
            print(f"[{'PASS' if n_ok else 'FAIL'}] PART N: leave-action stub @0x{S['leave']:08X} "
                  f"({len(stub)}B) matches the builder")
            # the shared trampoline's immediate-action literal must point at THIS home of the stub
            t = _tg._hook_target(bytearray(ov), LEAVE_HOOK)

            def _tramp_ok(t):
                tb = _tg._shared_arm_trampoline(t or 0, cave3.CAVE3_TGSH_ARMLIST if t == cave3.CAVE3_TGSH_ARMTRAMP
                                                else ov5_cave.CAVE_TG_ARMLIST, S["leave"])
                return t is not None and _cave_bytes(rom_v, ov, t, len(tb)) == tb
            if t is not None:
                t = ov5_cave.ik_walk(t)          # Infernoble's leave-switch front chain: follow it to its tail
            n3_ok = _tramp_ok(t)
            ok &= n3_ok
            print(f"[{'PASS' if n3_ok else 'FAIL'}] PART N: shared trampoline BXes Quasar's cid to 0x{S['leave']:08X}")
            # The shared trampoline + cid list live in ov5 or (ov3 compaction) the ov3 pool;
            # CAVE_TG_ARM_OK follows the live hook @LEAVE_HOOK to whichever home, checks the trampoline
            # bytes there against the builder, and looks the cid up in that home's list.
            n2_ok = _tg.CAVE_TG_ARM_OK(rom_n, bytearray(ov), DONOR_CID)
            ok &= n2_ok
            print(f"[{'PASS' if n2_ok else 'FAIL'}] PART N: hook @0x{LEAVE_HOOK:08X} -> shared trampoline "
                  f"(0x{_tg._hook_target(bytearray(ov), LEAVE_HOOK) or 0:08X}, matches the builder), "
                  f"0x{DONOR_CID:04X} in its cid list")

            # --- PART M: the Extra-Deck revive ---
            poff = _find_populate(ov, DONOR_CID)
            m_ok = poff is not None
            if m_ok:
                pa, pb, ph, pfl = struct.unpack_from("<HHII", ov, poff)
                m_ok = (pb == SHOOTING_STAR_CID and ph == (S["exsel"] | 1) and pfl == POP_FL_YUBEL)
                print(f"[{'PASS' if m_ok else 'FAIL'}] PART M: populate b=0x{pb:04X} h=0x{ph:08X} "
                      f"fl=0x{pfl:08X} (SS \"Shooting Star Dragon\" 0x{SHOOTING_STAR_CID:04X} from Extra Deck)")
            else:
                print("[FAIL] PART M: donor has no populate record")
            ok &= m_ok

            # the selector blob must be present, and must differ from its GY source in exactly the
            # two intended places (flags word + builder BL)
            sel = _cave_bytes(rom_v, ov, S["exsel"], EXSEL_LEN)
            src = cov[_off(EXSEL_SRC):_off(EXSEL_SRC) + EXSEL_LEN]
            want = bytearray(src)
            want[EXSEL_OFF_FLAGS:EXSEL_OFF_FLAGS + 2] = EXSEL_NEW_FLAGS
            want[EXSEL_OFF_BL:EXSEL_OFF_BL + 4] = thumb_bl(S["exsel"] + EXSEL_OFF_BL, EXTRA_BUILDER)
            s_ok = sel == bytes(want)
            ok &= s_ok
            print(f"[{'PASS' if s_ok else 'FAIL'}] PART M: selector blob @0x{S['exsel']:08X} is the donor's "
                  f"selector with flags #8->#2 and builder -> 0x{EXTRA_BUILDER:08X}")
            # the named-target filter literal must be carried through UNCHANGED (load-bearing)
            f_ok = len(sel) >= 0x2C and struct.unpack_from("<I", sel, 0x28)[0] == NAMED_FILTER
            ok &= f_ok
            print(f"[{'PASS' if f_ok else 'FAIL'}] PART M: named-target filter literal 0x{NAMED_FILTER:08X} "
                  f"preserved (NOT Instant Fusion's criteria filter)")
            try:
                from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
                md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
                print("        selector disassembly:")
                for ins in md.disasm(sel[:0x26], S["exsel"]):
                    print(f"          0x{ins.address:08X}: {ins.mnemonic:6} {ins.op_str}")
            except ImportError:
                pass

            # --- Blast radius: overlay 3 must differ from clean ONLY at the intended sites ---
            c3j = [i for i in range(CLS3_COUNT)
                   if struct.unpack_from("<H", ov, _off(CLS3_BASE + i * CLS_STRIDE))[0] == DONOR_CID]
            allowed = (set(range(_off(LIST_A), _off(LIST_A) + LIST_A_COUNT * 2))
                       # PART O: the double-attack cid list (count and searcher untouched)
                       | set(range(_off(DBLATK_LIST), _off(DBLATK_LIST) + DBLATK_COUNT * 2))
                       | set(range(off, off + CLS_STRIDE))
                       | set(range(_off(NAMED_MAT_BRANCH), _off(NAMED_MAT_BRANCH) + 2))
                       | set(range(_off(PAIR_BRANCH), _off(PAIR_BRANCH) + 2))
                       | set(range(_off(NONTUNER_BHS), _off(NONTUNER_BHS) + 2))
                       | set(range(creg + 4, creg + 6) if creg is not None else set())
                       | set(range(_off(QSR_PRED_HOOK), _off(QSR_PRED_HOOK) + 4))
                       # PART J: the first donor cls3 row's +04/+08 (8 bytes)
                       | set(range(_off(CLS3_BASE + c3j[0] * CLS_STRIDE) + 4,
                                   _off(CLS3_BASE + c3j[0] * CLS_STRIDE) + 20) if c3j else set())
                       | set(range(_off(CLS3_BASE + c3j[1] * CLS_STRIDE) + 12,
                                   _off(CLS3_BASE + c3j[1] * CLS_STRIDE) + 16) if len(c3j) > 1 else set())
                       # PART N: the shared leave-trampoline hook (4 bytes). The trampoline body and
                       # the cid list live in the ov5 cave, not overlay 3, so this is the only ov3 site.
                       | set(range(_off(LEAVE_HOOK), _off(LEAVE_HOOK) + 4))
                       # PART M: the donor's populate record, fields b/h/fl (its cid `a` is untouched)
                       | set(range(poff + 2, poff + 12) if poff is not None else set()))
            for _s in parse_cave3_slots():
                if _s["addr"] in (*S.values(), cave3.CAVE3_TGSH_ARMTRAMP, cave3.CAVE3_TGSH_ARMLIST):
                    allowed |= set(range(_off(_s["addr"]), _off(_s["addr"]) + _s["size"]))
            diff = {i for i in range(len(ov)) if ov[i] != cov[i]}
            stray = diff - allowed
            # This check can only attribute bytes in a STANDALONE build: it diffs against the
            # clean ROM and whitelists Quasar's own sites, so in a chained build every other
            # patch's edits look like strays and it failed by construction. Detect a chained
            # build from the ov5 cave -- if a slot owned by another patch is populated, the
            # foreign bytes are not ours and the check is reported as SKIP rather than FAIL.
            foreign = [(n, a) for n, a in (("minefield", ov5_cave.CAVE_MINEFIELD),
                                           ("boggart", ov5_cave.CAVE_BOGGART),
                                           ("mystic_piper", ov5_cave.CAVE_MYSTIC))
                       if bytes(ov5[a - ov5_cave.OV5_RAM_BASE:a - ov5_cave.OV5_RAM_BASE + 4]) not in
                       (b"\x00\x00\x00\x00", b"\xff\xff\xff\xff")]
            # All three ov5 probes above are RETIRED (minefield, boggart, mystic_piper
            # their stubs left ov5), so also probe ov3 pool slots other shipped cards fill. They
            # are zero in a standalone Quasar build (step 0 frees them, nothing of Quasar's lives there).
            foreign +=[(n, a) for n, a in (("koaki_meiru_wall", cave3.CAVE3_KMW_COND),
                                            ("gravekeepers_recruiter", cave3.CAVE3_GK_WRAPPER),
                                            ("mystic_piper", cave3.CAVE3_PIPER_RES))
                        if any(ov[_off(a):_off(a) + 4])]
            chained = bool(foreign)
            r_ok = not stray
            if stray and chained:
                print(f"[SKIP] blast radius: {len(diff)} bytes differ from clean, {len(stray)} outside "
                      f"Quasar's own sites -- CHAINED build (ov5 cave also holds "
                      f"{', '.join(n for n, _ in foreign)}), so strays cannot be attributed. "
                      f"Re-run against a standalone rom_shooting_quasar.nds to exercise this check.")
                r_ok = True
            else:
                print(f"[{'PASS' if r_ok else 'FAIL'}] blast radius: {len(diff)} bytes differ from clean, "
                      f"{len(stray)} outside LIST_A + the cls1 row + the D/E/F branches"
                      + (f" -> {[hex(x + RAM_BASE) for x in sorted(stray)[:8]]}" if stray else ""))
            ok &= r_ok

            # --- PART J ---
            c3 = [i for i in range(CLS3_COUNT)
                  if struct.unpack_from("<H", ov, _off(CLS3_BASE + i * CLS_STRIDE))[0] == DONOR_CID]
            j_ok = len(c3) == 2
            if j_ok:
                r0off = _off(CLS3_BASE + c3[0] * CLS_STRIDE)
                res, sub = struct.unpack_from("<II", ov, r0off + 4)
                cond, tag = struct.unpack_from("<II", ov, r0off + 12)
                j_ok = (res == (S["res"] | 1) and sub == 0
                        and cond == (S["cond"] | 1) and tag == NEGATE_NEW_TAG)
                k_ok = all(_cave_bytes(rom_v, ov, a, len(b)) == b for a, b in (
                    (S["cond"], _build_hopt_cond(S["cond"])), (S["res"], _build_hopt_res(S["res"]))))
                ok &= k_ok
                print(f"[{'PASS' if k_ok else 'FAIL'}] PART K: HOPT shims @0x{S['cond']:08X}/0x{S['res']:08X} "
                      f"match the builders")
                print(f"[{'PASS' if j_ok else 'FAIL'}] PART J/K: cls3[{c3[0]}] +04=0x{res:08X} +08=0x{sub:08X} "
                      f"+0C=0x{cond:08X} +10=0x{tag:08X} (HOPT shims -> costless negate)")
                # the +10 tag must NOT be one of the three tribute-self cost tags
                t_ok = tag not in (0x021E50CD, 0x021E7765, 0x021EA6FD)
                ok &= t_ok
                print(f"[{'PASS' if t_ok else 'FAIL'}] PART J: +10 tag is costless (does not tribute)")
                # the SECOND row is intentionally untouched for now (in-game question, see apply_negate_retune)
                r1off = _off(CLS3_BASE + c3[1] * CLS_STRIDE)
                cond2 = struct.unpack_from("<I", ov, r1off + 12)[0]
                r2_ok = cond2 == NEGATE_ROW2_COND
                ok &= r2_ok
                print(f"[{'PASS' if r2_ok else 'FAIL'}] PART J: cls3[{c3[1]}] +0C=0x{cond2:08X} "
                      f"(never-activatable -> 2nd effect + Tribute menu gone)")
            ok &= j_ok


            c.ok(ok, "all shooting_quasar PART checks (see the printed PASS/FAIL lines above)")

        return Compiled(installs=(install,), checks=(check_fn,))








# -- build / verify --------------------------------------------------------------------------
def _apply_edit(view, e: Edit) -> None:
    hits = [i for i, r in enumerate(rows(view, e.table)) if r[0] == e.cid]
    assert len(hits) == 1, f"{e.cid:#06x} owns {len(hits)} {e.table.label}s, expected 1"
    cur = rows(view, e.table)[hits[0]]
    if cur == e.patched:
        return
    assert cur == e.native, f"{e.table.label} {e.cid:#06x} = {[hex(x) for x in cur]}, not stock"
    view.write(e.table.addr(hits[0]), struct.pack(e.table.fmt, *e.patched))


def make(spec, props: card_props | None, *, out: str):
    """-> (main, verify) with the signatures `steps` expects. `spec` supplies `compile(view)`."""
    name, desc = (s.encode("ascii", "replace") for s in card_text.CARD_TEXT[spec.cid]["e"])   # fallback bytes only; CARD_TEXT cids are re-emitted in full

    def main(write_text: bool = False, src: str = SRC, out: str = out) -> None:
        rom, ovb = load_overlay3(src)
        view = Ov(bytearray(ovb))
        compiled = spec.compile(view)
        for addr, blob, _ in compiled.stubs:
            if _in_ov5(addr):
                ov5_cave.install_cave(rom, addr, blob, reserve=len(blob))
                continue
            cave3._checked(addr, len(blob), blob, "")
            assert view.blob(addr, len(blob)) in (bytes(len(blob)), blob), (
                f"ov3 slot @{addr:#x} is not zero -- step 0 (ov3_compact) must run first")
            view.write(addr, blob)
        for r in compiled.rows:
            insert_sorted(view, r.table, r.record, drop=r.phantom)
        for e in compiled.edits:
            _apply_edit(view, e)
        for fn in compiled.installs:
            fn(rom, view)
        save_overlay3(rom, bytes(view.buf), out)
        for fn in compiled.posts:
            fn(out)
        if props is None:       # a Spell/Trap donor keeps its stats; only the text changes
            if write_text:
                card_text.apply_to_rom(out, spec.cid)
            return
        apply_stats_and_text(out, cid=spec.cid, attribute=props.attribute, race=props.race,
                             level=props.level, atk=props.atk, defense=props.defense,
                             card_type=ERA2_CARD_TYPE_REVERSE[props.card_type],
                             name=name, desc=desc, langs=TEXT_LANGS, write_text=write_text)

    def verify(out: str = out) -> bool:
        c = Checker(f"0x{spec.cid:04X} ({out})")
        c.out = out      # the ROM path, for checks that read text/pac (rom.filename is None for a file-loaded ROM)
        rom, ovb = load_overlay3(out)
        view = Ov(bytearray(ovb))
        compiled = spec.compile(view)
        for r in compiled.rows:
            if r.stock_copies > 1:      # stock holds the phantom more than once: one copy is spent, not all
                ks = keys(view, r.table)
                c.ok(len(ks) == r.table.count and ks == sorted(ks) and spec.cid in ks
                     and ks.count(r.phantom) == r.stock_copies - 1,
                     f"{r.table.label}: {r.table.count} records, sorted, cid 0x{spec.cid:04X} present, "
                     f"one of the {r.stock_copies} stock 0x{r.phantom:04X} rows spent")
            else:
                table_intact(c, view, r.table, expect=spec.cid, phantom=r.phantom)
            c.eq([x for x in rows(view, r.table) if x[0] == spec.cid], [r.record],
                 f"exactly one exact {r.table.label}")
        ov5_view = None
        for e in compiled.edits:
            c.eq([x for x in rows(view, e.table) if x[0] == spec.cid], [e.patched],
                 f"exactly one exact {e.table.label}")
        for addr, blob, what in compiled.stubs:
            if _in_ov5(addr) and ov5_view is None:
                ov5_view = Ov(bytes(ndspy.rom.NintendoDSRom.fromFile(out).loadArm9Overlays(
                    [ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data), base=ov5_cave.OV5_RAM_BASE)
            cave_holds(c, ov5_view if _in_ov5(addr) else view, addr, blob, what)
        for fn in compiled.checks:
            fn(c, rom, view)
        ok_text, msg = card_text.check_rom_text(out, spec.cid)
        c.ok(ok_text, f"text: {msg}")
        return c.result()

    return main, verify

"""High-level vocabulary for authoring Over the Nexus card effects.

:class:`EffectBuilder` sits on top of
:class:`otn_enhanced.asm.effect_shim.ThumbAssembler` and turns the recurring
shapes of a card-effect resolver — prologue/epilogue, reading a context field,
calling an engine primitive with marshalled arguments, branching on a
comparison — into named methods.  A resolver then reads as intent rather than
as Thumb opcodes::

    b = EffectBuilder()
    b.prologue(save=[R4, R5])
    side = b.ctx_field("controller", dest=R4)      # LDRB R4, [R0, #2]
    b.call("reveal_top", side)
    cid = b.peek_deck_top_cid(side, dest=R5, scratch=(R2, R3))
    b.call("draw", side, 1)
    b.call("is_monster", cid); b.if_eq(R0, 0, "done")
    b.call("cid_level", cid);  b.if_ne(R0, 1, "done")
    b.call("draw", side, 1)
    b.label("done")
    b.epilogue(ret=0)
    stub = b.assemble(cave_addr)

Because the builder lowers onto ``ThumbAssembler`` (and thence ``StubBuilder``),
the output is relocatable Thumb-1 with the usual guarantee: assembling at the
original address reproduces the original bytes.  Engine-primitive addresses are
the **in-game-proven** ones from the shipped patches; the long tail is reachable
with :meth:`call_addr`.
"""

from __future__ import annotations

from dataclasses import dataclass

from otn_enhanced.asm.effect_shim import ThumbAssembler


# ---------------------------------------------------------------------------
# Registers
# ---------------------------------------------------------------------------

class Reg(int):
    """A Thumb low register (R0–R7).

    Subclasses ``int`` so it formats and compares as its number, while
    ``isinstance(x, Reg)`` distinguishes a register operand from an immediate.
    """

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"R{int(self)}"


R0, R1, R2, R3, R4, R5, R6, R7 = (Reg(i) for i in range(8))


# ---------------------------------------------------------------------------
# Engine primitives (proven in shipped, in-game-tested patches)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Primitive:
    """A callable engine routine: its address, a human signature, and ABI."""
    addr: int
    signature: str
    arm: bool = False   # True → reached with BLX (Thumb→ARM); else BL


PRIMITIVES: dict[str, Primitive] = {
    # name                 addr          signature
    "draw":        Primitive(0x021D12F4, "(side, count)"),
    "reveal_top":  Primitive(0x021D2624, "(side)"),
    "is_monster":  Primitive(0x02029E60, "(cid) -> bool"),
    "cid_level":   Primitive(0x0202ABD8, "(cid) -> level"),
    "get_race": Primitive(0x0202ABB8, "(cid) -> race"),
    # The engine's turn log: a matched post/query pair (KB dispatch.turnlog_once_per_turn_pair).
    "turnlog_post": Primitive(0x021D2584, "(side, cid, kind, 0)"),
    "turnlog_query": Primitive(0x021A14E8, "(side, slot, cid, kind) -> nonzero iff logged"),
}
# Add a primitive here when a card first calls it, with the KB fact that proves it. Names for engine routines
# nothing calls yet live in tools/effect_registry/primitive_names.py (_PROVEN); a test keeps the two in step.
# There is no "special_summon_from_deck" here: 0x021D1AFC, which this table once named that, is the middle of a
# larger function (calling it data-aborts). The real Special Summon engine is 0x0226925C, with a stack protocol
# (see cards/w_nebula_meteorite.py SS_ENGINE) rather than a plain (side, cid) call.


# ---------------------------------------------------------------------------
# Effect context fields (R0 at entry points at the ctx struct)
# offset, size: B=byte (LDRB), H=halfword (LDRH), W=word (LDR)
# ---------------------------------------------------------------------------

CTX_FIELDS: dict[str, tuple[int, str]] = {
    "cid": (0x00, "H"),
    "controller": (0x02, "B"),
    "race": (0x03, "B"),
    "trigger_type": (0x04, "B"),
    "trigger_category": (0x05, "B"),
    "slot_phase": (0x06, "B"),
    "cost_ran": (0x07, "B"),        # 0 at the menu offer-check, 1 once the cost has run (descriptor, not effect ctx)
    "card_instance": (0x0C, "B"),
}

_LOAD_MNEMONIC = {"B": "LDRB", "H": "LDRH", "W": "LDR"}

# Per-player duel-struct geometry (folded so the deck-top read needs no add).
PLAYER_BASE = 0x0229AC94
PLAYER_STRIDE = 0xB3C
DECK_TOP_OFF = 0x304
DECK_TOP_PTR = PLAYER_BASE + DECK_TOP_OFF   # 0x0229AF98 (player 0 top-of-Deck)
CID_MASK_BITS = 14                          # card ids are 14 bits
TURNLOG_SLOT = 0x0B                         # the per-turn log's pseudo-zone (KB dispatch.turnlog_once_per_turn_pair)


# ---------------------------------------------------------------------------
# Branch-condition mnemonics for if_eq / if_ne
# ---------------------------------------------------------------------------

_TAKEN = {"eq": "BEQ", "ne": "BNE"}


class EffectBuilder(ThumbAssembler):
    """A :class:`ThumbAssembler` with card-effect idioms."""

    def __init__(self) -> None:
        super().__init__()
        self._saved: list[int] = []

    # -- prologue / epilogue ---------------------------------------------
    def prologue(self, save: list[Reg] | tuple[Reg, ...] = ()) -> "EffectBuilder":
        """Emit ``PUSH {<save>, LR}`` and remember the saved registers."""
        self._saved = sorted(int(r) for r in save)
        self.insn("PUSH", _reglist(self._saved, "LR"))
        return self

    def epilogue(self, ret: int = 0) -> "EffectBuilder":
        """Set the return value and emit ``POP {<saved>, PC}``."""
        self.insn("MOV", f"R0, #0x{ret:X}")
        self.insn("POP", _reglist(self._saved, "PC"))
        return self

    # -- context access ---------------------------------------------------
    def ctx_field(self, name: str, *, dest: Reg, ctx: Reg = R0) -> Reg:
        """Load a named effect-context field into *dest*; returns *dest*."""
        if name not in CTX_FIELDS:
            raise KeyError(f"unknown ctx field {name!r}; known: {sorted(CTX_FIELDS)}")
        offset, size = CTX_FIELDS[name]
        self.insn(_LOAD_MNEMONIC[size], f"R{int(dest)}, [R{int(ctx)}, #0x{offset:X}]")
        return dest

    # -- calls ------------------------------------------------------------
    def call(self, name: str, *args: Reg | int, via: Reg | None = None) -> Reg:
        """Marshal *args* into R0.. and call primitive *name*; result in R0.

        *via* selects the call form: omitted is a direct ``BL``; a register is the literal form
        ``ldr via,=addr|1 ; blx via``, which is how most stubs call the engine.
        """
        if name not in PRIMITIVES:
            raise KeyError(f"unknown primitive {name!r}; known: {sorted(PRIMITIVES)}")
        return self.call_addr(PRIMITIVES[name].addr, *args,
                              arm=PRIMITIVES[name].arm, via=via)

    def call_addr(self, addr: int, *args: Reg | int, arm: bool = False, via: Reg | None = None) -> Reg:
        """Like :meth:`call` but to a raw *addr* (for un-registered routines)."""
        self._marshal(args)
        if via is None:
            self.blx(addr) if arm else self.bl(addr)
        else:
            if int(via) < len(args):
                raise ValueError(f"via R{int(via)} would clobber argument register R{int(via)}; use R{len(args)} or higher")
            self.ldr_const(int(via), addr if arm else addr | 1)    # the Thumb bit selects Thumb state for blx
            self.insn("BLX", f"R{int(via)}")
        return R0

    def _marshal(self, args: tuple[Reg | int, ...]) -> None:
        """Move call arguments into R0, R1, … (registers or immediates)."""
        if len(args) > 4:
            raise ValueError("at most 4 register arguments (R0..R3)")
        written: set[int] = set()
        for i, arg in enumerate(args):
            if isinstance(arg, Reg):
                if int(arg) in written:
                    raise ValueError(
                        f"argument {i} reads R{int(arg)} after it was overwritten "
                        "by marshalling; reorder or stage through another register")
                if int(arg) != i:
                    self.insn("ADD", f"R{i}, R{int(arg)}, #0x0")
            elif arg > 0xFF:
                self.ldr_const(i, arg)         # a cid or address does not fit a MOV immediate
            else:
                self.insn("MOV", f"R{i}, #0x{arg:X}")
            written.add(i)

    # -- comparisons / branches ------------------------------------------
    def if_eq(self, reg: Reg, imm: int, goto: str) -> "EffectBuilder":
        """Branch to label *goto* when ``reg == imm``."""
        return self._cmp_branch("eq", reg, imm, goto)

    def if_ne(self, reg: Reg, imm: int, goto: str) -> "EffectBuilder":
        """Branch to label *goto* when ``reg != imm``."""
        return self._cmp_branch("ne", reg, imm, goto)

    def _cmp_branch(self, cond: str, reg: Reg, imm: int, goto: str) -> "EffectBuilder":
        self.insn("CMP", f"R{int(reg)}, #0x{imm:X}")
        self.insn(_TAKEN[cond], goto)
        return self

    # -- compound idioms --------------------------------------------------
    def turnlog_query(self, side: Reg, cid: Reg | int, kind: int, *, via: Reg | None = None) -> Reg:
        """Has *cid* logged a kind-*kind* node this turn? Nonzero in R0 if so.

        Emits ``(side, 0xB, cid, kind)`` for ``turnlog_query``. Load *side* into R0 first, and *cid* into R2
        first if it comes from the descriptor, so no argument move is needed.
        """
        return self.call("turnlog_query", side, TURNLOG_SLOT, cid, kind, via=via)

    def turnlog_post(self, side: Reg, cid: Reg | int, kind: int, *, via: Reg | None = None) -> Reg:
        """Log a kind-*kind* node for *cid* this turn: ``(side, cid, kind, 0)`` for ``turnlog_post``."""
        return self.call("turnlog_post", side, cid, kind, 0, via=via)

    def peek_deck_top_cid(self, side: Reg, *, dest: Reg,
                          scratch: tuple[Reg, Reg]) -> Reg:
        """Read the top-of-Deck card id for *side* into *dest* (masked to 14 bits).

        The engine's draw is asynchronous, so the card a draw will take is
        inspected by peeking the deck top *before* drawing.  Uses the two
        *scratch* registers; returns *dest*.
        """
        sa, sb = int(scratch[0]), int(scratch[1])
        shift = 32 - CID_MASK_BITS
        self.ldr_const(sa, PLAYER_STRIDE)
        self.insn("MUL", f"R{sa}, R{int(side)}")
        self.ldr_const(sb, DECK_TOP_PTR)
        self.insn("ADD", f"R{sb}, R{sb}, R{sa}")
        self.insn("LDR", f"R{int(dest)}, [R{sb}, #0x0]")
        self.insn("LSL", f"R{int(dest)}, R{int(dest)}, #0x{shift:X}")
        self.insn("LSR", f"R{int(dest)}, R{int(dest)}, #0x{shift:X}")
        return dest


def _reglist(regs: list[int], extra: str) -> str:
    """Format ``{R4, R5, LR}`` from a register-number list plus LR/PC."""
    parts = [f"R{r}" for r in regs]
    parts.append(extra)
    return "{" + ", ".join(parts) + "}"

"""Structure recovery for lifted Thumb functions.

Takes a flat list of ``ThumbInsn`` and produces structured Python source
with real ``if``/``elif``/``else``/``while`` control flow instead of
``goto`` labels.

Algorithm (classical structured-decompilation):

1. **Basic blocks** — split at branch targets and after each branch/return.
2. **CFG** — each block has 0, 1 or 2 successors.
3. **Post-dominators** — iterative Cooper-Harvey-Kennedy on the reverse CFG.
4. **Loops** — back-edges identified via DFS (target dominates source).
5. **Structuring** — recursive descent that emits:
   * ``return r0`` for return blocks,
   * ``while True: …`` for loop headers (with ``break``/``continue``),
   * ``if cond: <then> else: <else>`` using the post-dominator as the
     join point,
   * ``goto(...)`` only for irreducible flow we cannot otherwise structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from otn_enhanced.asm.thumb_disasm import ThumbInsn


# ---------------------------------------------------------------------------
# Branch condition table
# ---------------------------------------------------------------------------

COND_TO_PY = {
    "BEQ": "{a} == {b}",
    "BNE": "{a} != {b}",
    "BCS": "uge({a}, {b})",
    "BCC": "ult({a}, {b})",
    "BMI": "({a}) < 0",
    "BPL": "({a}) >= 0",
    "BVS": "overflow()",
    "BVC": "not overflow()",
    "BHI": "ugt({a}, {b})",
    "BLS": "ule({a}, {b})",
    "BGE": "{a} >= {b}",
    "BLT": "{a} < {b}",
    "BGT": "{a} > {b}",
    "BLE": "{a} <= {b}",
}

COND_NEGATE = {
    "BEQ": "BNE", "BNE": "BEQ",
    "BCS": "BCC", "BCC": "BCS",
    "BMI": "BPL", "BPL": "BMI",
    "BVS": "BVC", "BVC": "BVS",
    "BHI": "BLS", "BLS": "BHI",
    "BGE": "BLT", "BLT": "BGE",
    "BGT": "BLE", "BLE": "BGT",
}


# ---------------------------------------------------------------------------
# Basic block
# ---------------------------------------------------------------------------

@dataclass
class Block:
    bid: int                          # 0-based block id (== addr-sorted index)
    addr: int                         # start address
    insns: list[ThumbInsn] = field(default_factory=list)
    succ_taken: int | None = None     # successor when condition true (or unconditional target)
    succ_fall: int | None = None      # fall-through successor (None if branch is unconditional/return)
    cond_mn: str | None = None        # branch mnemonic of the terminator (e.g. "BEQ")
    is_return: bool = False
    cmp_lhs: str = ""                 # last CMP/TST left side as Python expr
    cmp_rhs: str = ""

    @property
    def succs(self) -> list[int]:
        out: list[int] = []
        if self.succ_taken is not None:
            out.append(self.succ_taken)
        if self.succ_fall is not None and self.succ_fall != self.succ_taken:
            out.append(self.succ_fall)
        return out


# ---------------------------------------------------------------------------
# Build basic blocks from a flat instruction list
# ---------------------------------------------------------------------------

def build_blocks(insns: list[ThumbInsn]) -> list[Block]:
    """Split *insns* into basic blocks. *insns* must be the code-only slice
    (literal pool already excluded)."""
    if not insns:
        return []

    # Step 1: find leader addresses
    addrs = [i.addr for i in insns]
    addr_set = set(addrs)
    leaders = {insns[0].addr}
    for idx, ins in enumerate(insns):
        if ins.is_branch and ins.branch_target in addr_set:
            leaders.add(ins.branch_target)
        if (ins.is_branch or ins.is_return) and idx + 1 < len(insns):
            leaders.add(insns[idx + 1].addr)

    # Step 2: group instructions between leaders
    blocks: list[Block] = []
    current: Block | None = None
    addr_to_bid: dict[int, int] = {}
    for ins in insns:
        if ins.addr in leaders:
            current = Block(bid=len(blocks), addr=ins.addr)
            addr_to_bid[ins.addr] = current.bid
            blocks.append(current)
        assert current is not None
        current.insns.append(ins)

    # Step 3: wire successors and detect terminator type
    for i, blk in enumerate(blocks):
        terminator = blk.insns[-1] if blk.insns else None
        if terminator is None:
            continue
        if terminator.is_return:
            blk.is_return = True
            continue
        mn = terminator.mnemonic
        if mn == "B" and terminator.is_branch:
            blk.succ_taken = addr_to_bid.get(terminator.branch_target)
            blk.cond_mn = "B"
        elif mn in COND_TO_PY:
            blk.cond_mn = mn
            blk.succ_taken = addr_to_bid.get(terminator.branch_target)
            if i + 1 < len(blocks):
                blk.succ_fall = blocks[i + 1].bid
        else:
            # Block ends without a branch (e.g. fall-through)
            if i + 1 < len(blocks):
                blk.succ_fall = blocks[i + 1].bid

    return blocks


# ---------------------------------------------------------------------------
# Post-dominator computation
# ---------------------------------------------------------------------------

def compute_postdominators(blocks: list[Block]) -> list[set[int]]:
    """Iterative algorithm (Aho et al). Returns set of post-dominators per
    block. Multiple exits are unified through a virtual exit node."""
    n = len(blocks)
    if n == 0:
        return []

    # Predecessors of each block (used for both forward dominance and PDOM)
    preds: list[list[int]] = [[] for _ in range(n)]
    for b in blocks:
        for s in b.succs:
            preds[s].append(b.bid)

    # Build reverse-CFG: PDOM[X] = post-dominators in forward CFG
    # = dominators of X in reverse CFG starting from EXIT
    # We treat any return block as a virtual exit predecessor.
    exits = [b.bid for b in blocks if b.is_return or not b.succs]

    pdom: list[set[int]] = [set(range(n)) for _ in range(n)]
    for e in exits:
        pdom[e] = {e}

    changed = True
    while changed:
        changed = False
        for b in reversed(range(n)):
            if b in exits:
                continue
            succs = blocks[b].succs
            if not succs:
                new = {b}
            else:
                new = set(range(n))
                for s in succs:
                    new &= pdom[s]
                new.add(b)
            if new != pdom[b]:
                pdom[b] = new
                changed = True
    return pdom


def immediate_postdominator(b: int, pdom: list[set[int]]) -> int | None:
    """Return the IPD of *b* — the unique post-dominator that is itself
    post-dominated by every other post-dominator of *b* (other than *b*)."""
    candidates = pdom[b] - {b}
    if not candidates:
        return None
    # IPD is the candidate dominated by all others
    for c in candidates:
        if all(c in pdom[d] or c == d for d in candidates):
            return c
    return None


# ---------------------------------------------------------------------------
# Loop detection
# ---------------------------------------------------------------------------

def find_back_edges(blocks: list[Block]) -> set[tuple[int, int]]:
    """Identify back-edges (src, dst) where dst dominates src in the forward
    CFG. We approximate "dominates" with a DFS finishing-time check."""
    n = len(blocks)
    if n == 0:
        return set()
    # Standard DFS: edge (u, v) is a back-edge iff v is on the current DFS stack
    state = [0] * n  # 0=unvisited, 1=on stack, 2=done
    back: set[tuple[int, int]] = set()

    def dfs(u: int) -> None:
        state[u] = 1
        for v in blocks[u].succs:
            if state[v] == 0:
                dfs(v)
            elif state[v] == 1:
                back.add((u, v))
        state[u] = 2

    # Iterative DFS to avoid recursion limits on large funcs
    stack: list[tuple[int, int]] = [(0, 0)]
    state[0] = 1
    succs_iter: list[list[int]] = [[] for _ in range(n)]
    succs_iter[0] = list(blocks[0].succs)
    while stack:
        u, _ = stack[-1]
        if succs_iter[u]:
            v = succs_iter[u].pop()
            if state[v] == 0:
                state[v] = 1
                succs_iter[v] = list(blocks[v].succs)
                stack.append((v, 0))
            elif state[v] == 1:
                back.add((u, v))
        else:
            state[u] = 2
            stack.pop()
    return back


# ---------------------------------------------------------------------------
# Structurer
# ---------------------------------------------------------------------------

class Structurer:
    """Recursive descent that emits structured Python from a CFG."""

    def __init__(
        self,
        blocks: list[Block],
        render_block: Callable[[Block], list[str]],
    ) -> None:
        self.blocks = blocks
        self.render_block = render_block
        self.pdom = compute_postdominators(blocks)
        self.back_edges = find_back_edges(blocks)
        # Map loop-header → set of blocks in its body (very loose)
        self.loop_headers: set[int] = {dst for _, dst in self.back_edges}
        self.emitted: set[int] = set()

    def emit(self) -> list[str]:
        if not self.blocks:
            return []
        return self._emit(0, follow=None, indent=1, in_loop=None)

    # ------------------------------------------------------------------
    def _cond_expr(self, blk: Block, *, negate: bool = False) -> str:
        mn = blk.cond_mn or "BEQ"
        if negate:
            mn = COND_NEGATE.get(mn, mn)
        tmpl = COND_TO_PY.get(mn, "{a} ?? {b}")
        a = blk.cmp_lhs or "?"
        b = blk.cmp_rhs or "0"
        return tmpl.format(a=a, b=b)

    # ------------------------------------------------------------------
    def _emit(
        self,
        bid: int,
        follow: int | None,
        indent: int,
        in_loop: int | None,
    ) -> list[str]:
        out: list[str] = []
        prefix = "    " * indent

        # Stop if we've reached the follow node (the join)
        if follow is not None and bid == follow:
            return out

        # Loop body via continue / break to a containing loop
        if in_loop is not None:
            if bid == in_loop:
                out.append(prefix + "continue")
                return out

        # Already emitted — irreducible flow, fall back to goto
        if bid in self.emitted:
            out.append(prefix + f"goto('L_{self.blocks[bid].addr & 0xFFFFFF:06X}')")
            return out

        blk = self.blocks[bid]

        # Loop header: wrap subsequent emission in `while True:`
        if bid in self.loop_headers and in_loop != bid:
            out.append(prefix + f"while True:  # loop @ L_{blk.addr & 0xFFFFFF:06X}")
            inner = self._emit_loop(bid, follow, indent + 1)
            out.extend(inner)
            return out

        self.emitted.add(bid)

        # Render the block's instructions (excluding the branch terminator)
        body = self.render_block(blk)
        for line in body:
            out.append(prefix + line)

        # Handle the terminator
        if blk.is_return:
            out.append(prefix + "return r0")
            return out

        succs = blk.succs
        cond = blk.cond_mn

        if not succs:
            return out

        if len(succs) == 1 or cond == "B":
            # Unconditional successor
            nxt = blk.succ_taken if cond == "B" else (blk.succ_fall or blk.succ_taken)
            if nxt is None:
                return out
            if in_loop is not None and nxt == in_loop:
                out.append(prefix + "continue")
                return out
            if follow is not None and nxt == follow:
                return out
            out.extend(self._emit(nxt, follow, indent, in_loop))
            return out

        # Two successors: structured if/else
        ipd = immediate_postdominator(bid, self.pdom)
        # If ipd is None or out of range, fall back to a flat if-goto
        then_bid = blk.succ_taken
        else_bid = blk.succ_fall

        # Choose simpler form: if `else` block IS the join, we only need an `if`
        if ipd is not None and else_bid == ipd and then_bid is not None:
            cond_expr = self._cond_expr(blk)
            out.append(prefix + f"if {cond_expr}:")
            self._extend_or_pass(
                out, self._emit(then_bid, ipd, indent + 1, in_loop), indent + 1)
            out.extend(self._emit(ipd, follow, indent, in_loop))
            return out
        if ipd is not None and then_bid == ipd and else_bid is not None:
            cond_expr = self._cond_expr(blk, negate=True)
            out.append(prefix + f"if {cond_expr}:")
            self._extend_or_pass(
                out, self._emit(else_bid, ipd, indent + 1, in_loop), indent + 1)
            out.extend(self._emit(ipd, follow, indent, in_loop))
            return out

        # Full if/else
        cond_expr = self._cond_expr(blk)
        out.append(prefix + f"if {cond_expr}:")
        if then_bid is not None:
            self._extend_or_pass(
                out, self._emit(then_bid, ipd, indent + 1, in_loop), indent + 1)
        else:
            out.append(prefix + "    pass")
        # Only emit `else:` if there's a non-trivial alternative path
        else_lines: list[str] = []
        if else_bid is not None and else_bid != ipd:
            else_lines = self._emit(else_bid, ipd, indent + 1, in_loop)
        if self._has_statement(else_lines):
            out.append(prefix + "else:")
            self._extend_or_pass(out, else_lines, indent + 1)
        if ipd is not None:
            out.extend(self._emit(ipd, follow, indent, in_loop))
        return out

    # ------------------------------------------------------------------
    @staticmethod
    def _has_statement(lines: list[str]) -> bool:
        """True if *lines* contains at least one non-comment, non-blank line."""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return True
        return False

    @classmethod
    def _extend_or_pass(cls, out: list[str], lines: list[str], indent: int) -> None:
        """Append *lines* to *out*; if the body has no executable statement,
        append a `pass` at *indent* so the resulting Python is valid."""
        if cls._has_statement(lines):
            out.extend(lines)
        else:
            out.extend(lines)  # keep any comments
            out.append("    " * indent + "pass")

    # ------------------------------------------------------------------
    def _emit_loop(self, header: int, follow: int | None, indent: int) -> list[str]:
        """Emit the body of a loop with header *header*."""
        # Mark header as already emitted so we can re-enter and emit body
        # Determine the loop's exit: typically the IPD of header (the block
        # outside the loop), but with multi-exit loops this isn't always right.
        loop_exit = immediate_postdominator(header, self.pdom)
        # Render header instructions then continue with structured emission,
        # treating loop_exit as the follow target. Inside the loop, jumps back
        # to *header* become `continue`; jumps to loop_exit become `break`.
        out: list[str] = []
        prefix = "    " * indent

        # If we've already emitted, fall back
        if header in self.emitted:
            out.append(prefix + f"goto('L_{self.blocks[header].addr & 0xFFFFFF:06X}')")
            return out
        self.emitted.add(header)

        blk = self.blocks[header]
        body = self.render_block(blk)
        for line in body:
            out.append(prefix + line)

        if blk.is_return:
            out.append(prefix + "return r0")
            return out

        succs = blk.succs
        if len(succs) == 1 or blk.cond_mn == "B":
            nxt = blk.succ_taken if blk.cond_mn == "B" else (blk.succ_fall or blk.succ_taken)
            if nxt == header:
                out.append(prefix + "continue")
                return out
            if nxt == loop_exit:
                out.append(prefix + "break")
                return out
            if nxt is not None:
                out.extend(self._emit_loop_body(nxt, header, loop_exit, indent))
            return out

        # Two-way branch in the header: emit as if/break
        cond_expr = self._cond_expr(blk)
        out.append(prefix + f"if {cond_expr}:")
        then_lines: list[str] = []
        if blk.succ_taken == header:
            then_lines.append(prefix + "    continue")
        elif blk.succ_taken == loop_exit:
            then_lines.append(prefix + "    break")
        elif blk.succ_taken is not None:
            then_lines.extend(
                self._emit_loop_body(blk.succ_taken, header, loop_exit, indent + 1))
        if self._has_statement(then_lines):
            out.extend(then_lines)
        else:
            out.append(prefix + "    pass")
        else_lines: list[str] = []
        if blk.succ_fall == header:
            else_lines.append(prefix + "    continue")
        elif blk.succ_fall == loop_exit:
            else_lines.append(prefix + "    break")
        elif blk.succ_fall is not None:
            else_lines.extend(
                self._emit_loop_body(blk.succ_fall, header, loop_exit, indent + 1))
        if self._has_statement(else_lines):
            out.append(prefix + "else:")
            out.extend(else_lines)

        # After the loop, render the exit
        if loop_exit is not None and follow != loop_exit:
            out.extend(self._emit(loop_exit, follow, indent - 1, None))
        return out

    def _emit_loop_body(
        self,
        bid: int,
        header: int,
        loop_exit: int | None,
        indent: int,
    ) -> list[str]:
        """Emit a non-header block inside a loop, where edges back to header
        become `continue` and edges to loop_exit become `break`."""
        prefix = "    " * indent
        if bid == header:
            return [prefix + "continue"]
        if loop_exit is not None and bid == loop_exit:
            return [prefix + "break"]
        if bid in self.emitted:
            return [prefix + f"goto('L_{self.blocks[bid].addr & 0xFFFFFF:06X}')"]
        self.emitted.add(bid)
        blk = self.blocks[bid]
        out: list[str] = []
        for line in self.render_block(blk):
            out.append(prefix + line)
        if blk.is_return:
            out.append(prefix + "return r0")
            return out
        succs = blk.succs
        if not succs:
            return out
        if len(succs) == 1 or blk.cond_mn == "B":
            nxt = blk.succ_taken if blk.cond_mn == "B" else (blk.succ_fall or blk.succ_taken)
            if nxt == header:
                out.append(prefix + "continue")
            elif nxt == loop_exit:
                out.append(prefix + "break")
            elif nxt is not None:
                out.extend(self._emit_loop_body(nxt, header, loop_exit, indent))
            return out
        # two-way
        cond_expr = self._cond_expr(blk)
        out.append(prefix + f"if {cond_expr}:")
        then_lines: list[str] = []
        for sub in (blk.succ_taken,):
            if sub == header:
                then_lines.append(prefix + "    continue")
            elif sub == loop_exit:
                then_lines.append(prefix + "    break")
            elif sub is not None:
                then_lines.extend(self._emit_loop_body(sub, header, loop_exit, indent + 1))
        if self._has_statement(then_lines):
            out.extend(then_lines)
        else:
            out.append(prefix + "    pass")
        else_lines: list[str] = []
        for sub in (blk.succ_fall,):
            if sub == header:
                else_lines.append(prefix + "    continue")
            elif sub == loop_exit:
                else_lines.append(prefix + "    break")
            elif sub is not None:
                else_lines.extend(self._emit_loop_body(sub, header, loop_exit, indent + 1))
        if self._has_statement(else_lines):
            out.append(prefix + "else:")
            out.extend(else_lines)
        return out

@ Glue between engine hook sites and C. `.include "shim.S"` from a card's .S, one line per hook.
@ Proven by otn_enhanced/tools/c_shim_proof.py (trace-equivalence against real shipped stubs).
@ Both shims assume BL entry (LR = the engine's return site, sp = the engine's sp).

@ SPLICE_SHIM entry_name, hook
@   C side: void hook(Regs *r, u32 *frame);
@   r->r[0..7] are the engine's live r0-r7: read them, and write them to change what the engine sees on return.
@   frame is the engine's sp at the hook: frame[0x90/4] is [sp+0x90] (leave descriptor etc.), readable and writable.
@   Covers both splice hooks and frame readers. Cost: 10 B + the hook.
    .macro SPLICE_SHIM entry_name, hook
    .thumb_func
\entry_name:
    push {r0-r7, lr}
    mov r0, sp
    add r1, sp, #36
    bl \hook
    pop {r0-r7}
    pop {pc}
    .endm

@ FRONT_SHIM entry_name, hook, native, scratch
@   C side: int hook(Regs *r, u32 *frame);  as SPLICE_SHIM, plus the return value picks the exit:
@   0 -> return to the engine with r->r[0..7]; nonzero -> tail-jump to native with r->r[0..7], lr and sp as the
@   engine passed them, except `scratch` (a low register native doesn't read), which holds the native address.
@   native is a Thumb address (bit 0 set). Cost: 24 B + the hook + a 4 B literal (place .ltorg after).
    .macro FRONT_SHIM entry_name, hook, native, scratch
    .thumb_func
\entry_name:
    push {r0-r7, lr}
    mov r0, sp
    add r1, sp, #36
    bl \hook
    ldr r1, [sp, #32]
    mov lr, r1
    cmp r0, #0
    pop {r0-r7}           @ pop and add sp keep the flags
    add sp, #4
    beq 1f
    ldr \scratch, =\native
    bx \scratch
1:  bx lr
    .endm

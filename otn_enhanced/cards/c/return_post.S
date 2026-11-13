/* Return of the Monarchs: front over `bl 0x021D3168` @0x02265CA8 (post the summon event).  r0 = event word (low 16 bits = the summoned cid),
 * r1/r2 = the callee's other arguments (untouched), r3 free.  While the swap flag (DATA+0) is up it is cleared and the event's cid
 * becomes Return's, so Return's cls1 record answers.  Build with -DDATA=<addr> -DRETURN=0x14A1. */
    .syntax unified
    .thumb
    .section .text.entry,"ax"
    .global entry
    .thumb_func
entry:
    ldr r3, =DATA
    ldr r3, [r3]
    cmp r3, #0
    bne swap
plain:
    ldr r3, =0x021D3169
    bx r3
swap:
    mov r12, r0
    movs r0, #0
    ldr r3, =DATA
    str r0, [r3]
    mov r0, r12
    lsrs r0, r0, #16
    lsls r0, r0, #16
    ldr r3, =RETURN
    orrs r0, r3
    ldr r3, =0x021D3169
    bx r3
    .ltorg

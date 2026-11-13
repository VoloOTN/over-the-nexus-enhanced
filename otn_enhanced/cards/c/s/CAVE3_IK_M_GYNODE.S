    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    subs r2, #0x83
    movs r0, #0x49
    subs r0, r2, r0
    cmp r5, r0
    beq .L021FAE50
    cmp r5, r2
.L021FAE50:
    bx lr
    nop

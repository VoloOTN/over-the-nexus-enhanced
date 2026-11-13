    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    beq .L021B5846
    subs r1, #0x7a
    cmp r3, r1
.L021B5846:
    bx lr

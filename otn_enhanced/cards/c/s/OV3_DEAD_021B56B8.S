    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    adds r0, #0x8d
    cmp r5, r0
    beq .L021B56C4
    subs r0, #0x2d
    cmp r5, r0
    bx lr
.L021B56C4:
    bl 0x021D185C

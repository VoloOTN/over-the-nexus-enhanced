    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r5, r1
    bx lr
    bl 0x021D185C

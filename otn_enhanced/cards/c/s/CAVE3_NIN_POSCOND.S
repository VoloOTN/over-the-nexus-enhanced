    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    movs r0, #0x1
    bx lr

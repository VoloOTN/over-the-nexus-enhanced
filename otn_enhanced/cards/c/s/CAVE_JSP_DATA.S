    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    strh r2, [r0, #0x0]
    movs r0, r0
    lsls r4, r1, #1
    movs r0, r0
    movs r0, r0
    movs r0, r0
    movs r0, r0
    movs r0, r0

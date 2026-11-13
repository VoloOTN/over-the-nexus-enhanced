    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, .L0220A5D4
    cmp r5, r0
    bne .L0220A5CE
    ldr r0, .L0220A5D8
    bx r0
.L0220A5CE:
    ldr r0, .L0220A5DC
    cmp r5, r0
    bx lr
.L0220A5D4:
    .word 0x00000FE3
.L0220A5D8:
    .word 0x021D1939
.L0220A5DC:
    .word 0x00000FE1

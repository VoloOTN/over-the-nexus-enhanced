    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021F3E14
    cmp r0, r1
    beq .L021F3E12
    ldr r1, .L021F3E18
    cmp r0, r1
.L021F3E12:
    bx lr
.L021F3E14:
    .word 0x00000FFD
.L021F3E18:
    .word 0x0000245B

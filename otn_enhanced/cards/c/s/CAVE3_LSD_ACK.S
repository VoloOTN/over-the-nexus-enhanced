    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021FC2A8
    cmp r5, r1
    beq .L021FC2A4
    ldr r1, .L021FC2AC
    cmp r5, r1
    bx lr
.L021FC2A4:
    ldr r1, .L021FC2B0
    bx r1
.L021FC2A8:
    .word 0x000018FA
.L021FC2AC:
    .word 0x00001C8B
.L021FC2B0:
    .word 0x021CF067

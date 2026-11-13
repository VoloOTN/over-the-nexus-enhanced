    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, .L023A960C
    cmp r1, r0
    beq .L023A960A
    ldr r0, .L023A9610
    cmp r1, r0
.L023A960A:
    bx lr
.L023A960C:
    .word 0x00002170
.L023A9610:
    .word 0x0000160B

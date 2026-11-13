    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023A95EC
    cmp r2, r1
    beq .L023A95EA
    ldr r1, .L023A95F0
    cmp r2, r1
.L023A95EA:
    bx lr
.L023A95EC:
    .word 0x00002170
.L023A95F0:
    .word 0x0000160B

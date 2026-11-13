    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r6, #0x3c
    bge .L023A770A
    ldr r1, .L023A7714
    lsls r0, r6, #4
    bx lr
.L023A770A:
    lsls r1, r6, #4
    ldr r0, .L023A7718
    adds r0, r0, r1
    ldr r1, .L023A7714
    bx lr
.L023A7714:
    .word 0x0228DDF8
.L023A7718:
    .word 0x00119448

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r6, #0x42
    bge .L023A6E78
    ldr r0, .L023A6E80
    bx r0
.L023A6E78:
    movs r6, #0x3c
    ldr r0, .L023A6E84
    ldr r1, [r0, #0x34]
    bx lr
.L023A6E80:
    .word 0x0224C88F
.L023A6E84:
    .word 0x0229DD14

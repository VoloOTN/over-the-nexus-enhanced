    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r6, #0x4b
    bge .L023A7728
    ldr r0, .L023A7730
    bx r0
.L023A7728:
    movs r6, #0x3c
    ldr r0, .L023A7734
    ldr r1, [r0, #0x34]
    bx lr
.L023A7730:
    .word 0x0224C88F
.L023A7734:
    .word 0x0229DD14

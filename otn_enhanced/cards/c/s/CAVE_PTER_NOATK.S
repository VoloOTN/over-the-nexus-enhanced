    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L023A1BAC
    cmp r0, r3
    bne .L023A1BA6
    movs r0, #0x1
    bx lr
.L023A1BA6:
    ldr r3, .L023A1BB0
    bx r3
    nop
.L023A1BAC:
    .word 0x00000FE1
.L023A1BB0:
    .word 0x02022E15

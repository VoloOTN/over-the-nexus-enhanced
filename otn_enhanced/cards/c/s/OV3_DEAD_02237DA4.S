    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L02237DB4
    cmp r0, r3
    bne .L02237DAE
    movs r0, #0x1
    bx lr
.L02237DAE:
    ldr r3, .L02237DB8
    bx r3
    nop
.L02237DB4:
    .word 0x000017F4
.L02237DB8:
    .word 0x023A1B9D

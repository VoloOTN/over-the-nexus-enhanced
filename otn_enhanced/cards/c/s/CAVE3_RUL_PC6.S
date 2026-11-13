    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L021FADC8
    cmp r0, r3
    bne .L021FADC2
    movs r0, #0x1
    bx lr
.L021FADC2:
    ldr r3, .L021FADCC
    bx r3
    nop
.L021FADC8:
    .word 0x00000FEA
.L021FADCC:
    .word 0x021FADD1
    .hword 0x4B03
    .hword 0x4298
    .hword 0xD101
    .hword 0x2001
    .hword 0x4770
    .hword 0x4B02
    .hword 0x4718
    .hword 0x46C0
.L021FADE0:
    .word 0x00001CC6
.L021FADE4:
    .word 0x023A1B9D

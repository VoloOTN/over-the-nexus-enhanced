    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L023AAC40
    cmp r0, r3
    bne .L023AAC3A
    movs r0, #0x1
    bx lr
.L023AAC3A:
    ldr r3, .L023AAC44
    bx r3
    nop
.L023AAC40:
    .word 0x00001976
.L023AAC44:
    .word 0x021FBC95

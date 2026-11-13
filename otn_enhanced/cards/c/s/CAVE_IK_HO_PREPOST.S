    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L023AAC60
    cmp r0, r3
    bne .L023AAC5A
    movs r0, #0x1
    bx lr
.L023AAC5A:
    ldr r3, .L023AAC64
    bx r3
    nop
.L023AAC60:
    .word 0x00001976
.L023AAC64:
    .word 0x0223F8E5

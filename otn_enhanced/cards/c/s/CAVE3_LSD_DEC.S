    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L02236EB8
    cmp r5, r1
    beq .L02236EB4
    ldr r1, .L02236EBC
    cmp r5, r1
    bx lr
.L02236EB4:
    ldr r1, .L02236EC0
    bx r1
.L02236EB8:
    .word 0x000018FA
.L02236EBC:
    .word 0x00001C8B
.L02236EC0:
    .word 0x021CE941

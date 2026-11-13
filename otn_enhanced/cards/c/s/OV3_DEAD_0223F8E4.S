    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L0223F8F4
    cmp r0, r3
    bne .L0223F8EE
    movs r0, #0x1
    bx lr
.L0223F8EE:
    ldr r3, .L0223F8F8
    bx r3
    nop
.L0223F8F4:
    .word 0x00001B22
.L0223F8F8:
    .word 0x02220B3D

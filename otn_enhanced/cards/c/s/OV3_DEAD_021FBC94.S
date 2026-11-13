    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L021FBCA4
    cmp r0, r3
    bne .L021FBC9E
    movs r0, #0x1
    bx lr
.L021FBC9E:
    ldr r3, .L021FBCA8
    bx r3
    nop
.L021FBCA4:
    .word 0x00001B22
.L021FBCA8:
    .word 0x02237D8D

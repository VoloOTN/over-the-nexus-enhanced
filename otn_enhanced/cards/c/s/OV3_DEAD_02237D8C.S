    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L02237D9C
    cmp r0, r3
    bne .L02237D96
    movs r0, #0x1
    bx lr
.L02237D96:
    ldr r3, .L02237DA0
    bx r3
    nop
.L02237D9C:
    .word 0x000017F4
.L02237DA0:
    .word 0x02223491

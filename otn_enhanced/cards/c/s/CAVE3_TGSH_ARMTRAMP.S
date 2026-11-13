    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r2, .L021FACA4
.L021FAC7A:
    ldrh r1, [r2, #0x0]
    cmp r1, #0x0
    beq .L021FAC9C
    cmp r4, r1
    beq .L021FAC88
    .hword 0x1C92    @ adds r2, r2, #0x2
    b .L021FAC7A
.L021FAC88:
    ldr r1, [sp, #0x90]
    cmp r1, #0x0
    beq .L021FAC9C
    ldr r1, .L021FACA8
    cmp r4, r1
    bne .L021FAC98
    ldr r1, .L021FACAC
    bx r1
.L021FAC98:
    ldr r1, .L021FACB0
    bx r1
.L021FAC9C:
    movs r1, #0x77
    lsls r1, r1, #6
    bx lr
    movs r0, r0
.L021FACA4:
    .word 0x021FC2BC
.L021FACA8:
    .word 0x0000211B
.L021FACAC:
    .word 0x022379ED
.L021FACB0:
    .word 0x021CA641

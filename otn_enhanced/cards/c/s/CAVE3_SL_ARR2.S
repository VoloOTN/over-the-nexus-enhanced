    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r3}
    ldrh r1, [r4, #0x0]
    ldr r3, .L0220A320
    cmp r1, r3
    ldr r1, .L0220A324
    bne .L0220A31A
    ldr r1, .L0220A328
.L0220A31A:
    ldr r1, [r2, r1]
    pop {r3}
    bx lr
.L0220A320:
    .word 0x00001FFC
.L0220A324:
    .word 0x0000055C
.L0220A328:
    .word 0x000007B4

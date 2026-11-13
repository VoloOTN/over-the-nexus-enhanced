    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r6, #0x3c
    bne .L0239FC08
    ldr r0, .L0239FC10
    bx r0
.L0239FC08:
    movs r6, #0x3c
    ldr r0, .L0239FC14
    ldr r1, [r0, #0x34]
    bx lr
.L0239FC10:
    .word 0x0224C88F
.L0239FC14:
    .word 0x0229DD14

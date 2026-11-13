    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r0}
    ldr r1, .L0220A348
    ldr r0, [r1, #0x0]
    cmp r0, #0x0
    bne .L0220A342
    movs r0, #0x1
    str r0, [r1, #0x0]
    movs r1, #0x7d
    lsls r1, r1, #3
    pop {r0}
    bx lr
.L0220A342:
    movs r1, #0x0
    pop {r0}
    bx lr
.L0220A348:
    .word 0x021BA0F4

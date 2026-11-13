    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r0, #0x0
    bne .L0221AE68
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L0221AE74
    movs r3, #0x2
    bl 0x021A14E8
    cmp r0, #0x0
    beq .L0221AE6C
.L0221AE68:
    adds r0, r4, #0x0
    pop {r3, r4, r5, r6, r7, pc}
.L0221AE6C:
    movs r0, #0x0
    bl 0x0221D7CC
    movs r0, r0
.L0221AE74:
    .word 0x00000FF6

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r4, #0x0
    beq .L021F1B3A
    adds r0, r4, #0x0
    bl 0x020230D4
    cmp r0, #0x0
    beq .L021F1B5C
.L021F1B3A:
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L021F1B60
    movs r3, #0x1
    bl 0x021A14E8
    cmp r0, #0x0
    beq .L021F1B5C
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L021F1B64
    bl 0x021A1430
    cmp r0, #0x0
    bne .L021F1B5C
    ldr r0, .L021F1B64
    pop {r3, r4, r5, r6, r7, pc}
.L021F1B5C:
    bl 0x02212330
.L021F1B60:
    .word 0x00003E52
.L021F1B64:
    .word 0x00003E51

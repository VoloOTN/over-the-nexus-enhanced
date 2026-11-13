    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r6, .L021D87B0
    cmp r4, #0x0
    beq .L021D8764
    adds r0, r4, #0x0
    bl 0x02023FC4
    cmp r0, #0x0
    beq .L021D877E
.L021D8764:
    adds r0, r5, #0x0
    adds r1, r6, #0x0
    bl 0x021F12B8
    cmp r0, #0x0
    blt .L021D877E
    adds r0, r5, #0x0
    movs r1, #0xb
    adds r2, r6, #0x0
    bl 0x021A1430
    cmp r0, #0x0
    beq .L021D87A8
.L021D877E:
    ldr r6, .L021D87B4
    cmp r4, #0x0
    beq .L021D878E
    adds r0, r4, #0x0
    bl 0x02023F44
    cmp r0, #0x0
    beq .L021D87AC
.L021D878E:
    adds r0, r5, #0x0
    adds r1, r6, #0x0
    bl 0x021F12B8
    cmp r0, #0x0
    blt .L021D87AC
    adds r0, r5, #0x0
    movs r1, #0xb
    adds r2, r6, #0x0
    bl 0x021A1430
    cmp r0, #0x0
    bne .L021D87AC
.L021D87A8:
    adds r0, r6, #0x0
    pop {r3, r4, r5, r6, r7, pc}
.L021D87AC:
    movs r0, #0x0
    pop {r3, r4, r5, r6, r7, pc}
.L021D87B0:
    .word 0x0000245B
.L021D87B4:
    .word 0x00000FFD

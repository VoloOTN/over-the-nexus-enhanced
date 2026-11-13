    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r2, .L0239C91C
    ldr r3, [r2, #0x0]
    cmp r3, r4
    bne .L0239C8DA
    movs r3, #0x0
    str r3, [r2, #0x0]
    b .L0239C918
.L0239C8DA:
    ldrb r0, [r4, #0x2]
    ldrb r1, [r4, #0x6]
    eors r0, r1
    ldr r1, .L0239C920
    muls r1, r0
    ldr r3, .L0239C924
    adds r1, r1, r3
    ldr r3, [r1, #0x14]
    cmp r3, #0x0
    beq .L0239C918
    subs r3, #0x1
    lsls r3, r3, #2
    ldr r2, .L0239C928
    adds r1, r1, r2
    ldr r0, [r1, r3]
    ldr r2, .L0239C92C
    ands r0, r2
    bl 0x0202ABF8
    cmp r0, #0x0
    beq .L0239C908
    cmp r0, #0xf
    bne .L0239C918
.L0239C908:
    ldr r2, .L0239C91C
    str r4, [r2, #0x0]
    movs r3, #0x1
    str r3, [r5, #0x74]
    movs r3, #0x0
    str r3, [r5, #0x78]
    movs r0, #0x7f
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
.L0239C918:
    movs r0, #0x64
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
.L0239C91C:
    .word 0x0239C98C
.L0239C920:
    .word 0x00000B3C
.L0239C924:
    .word 0x0229AC94
.L0239C928:
    .word 0x0000055C
.L0239C92C:
    .word 0x00003FFF

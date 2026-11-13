    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [sp, #0x98]
    push {r4, r5, r6, r7, lr}
    movs r4, r0
    movs r7, #0x1
    ands r4, r7
    ldr r5, .L02237A34
    cmp r4, #0x0
    beq .L02237A00
    ldr r6, .L02237A38
    adds r5, r5, r6
.L02237A00:
    ldr r6, [r5, #0x18]
    cmp r6, #0x0
    beq .L02237A2C
    ldr r7, .L02237A3C
    adds r7, r7, r5
.L02237A0A:
    ldr r0, [r7, #0x0]
    ldr r1, .L02237A40
    ands r0, r1
    ldr r1, .L02237A44
    cmp r0, r1
    beq .L02237A20
    adds r7, #0x4
    subs r6, #0x1
    cmp r6, #0x0
    bne .L02237A0A
    b .L02237A2C
.L02237A20:
    movs r0, r4
    movs r1, r7
    movs r2, #0x1
    ldr r3, .L02237A48
    bl 0x02269314
.L02237A2C:
    movs r1, #0x77
    lsls r1, r1, #6
    pop {r4, r5, r6, r7, pc}
    movs r0, r0
.L02237A34:
    .word 0x0229AC94
.L02237A38:
    .word 0x00000B3C
.L02237A3C:
    .word 0x000004E4
.L02237A40:
    .word 0x00003FFF
.L02237A44:
    .word 0x0000239D
.L02237A48:
    .word 0x211B0001

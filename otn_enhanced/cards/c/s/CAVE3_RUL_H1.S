    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [sp, #0x0]
    bl 0x021F19E8
    bmi .L021F1052
    movs r1, #0x60
    muls r0, r1
    ldr r1, .L021F1058
    adds r0, r0, r1
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    beq .L021F1044
    cmp r1, #0x2
    bne .L021F1052
    ldrb r1, [r4, #0x3]
    ldrb r2, [r4, #0x4]
    cmp r1, #0xb
    beq .L021F103A
    cmp r1, #0xf
    beq .L021F1040
    cmp r1, #0xe
    bne .L021F1052
    cmp r2, #0x6
    bgt .L021F1052
    adds r0, #0x18
    b .L021F104C
.L021F103A:
    cmp r2, #0x0
    bne .L021F1052
    b .L021F104C
.L021F1040:
    adds r0, #0x30
    b .L021F104C
.L021F1044:
    ldrb r2, [r4, #0x4]
    cmp r2, #0x6
    bne .L021F1052
    adds r0, #0x48
.L021F104C:
    ldrh r1, [r0, #0x0]
    cmp r1, #0x0
    bne .L021F1054
.L021F1052:
    movs r0, #0x0
.L021F1054:
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
    nop
.L021F1058:
    .word 0x023A68F0

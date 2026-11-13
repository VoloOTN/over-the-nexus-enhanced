    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, [r5, #0x74]
    cmp r1, #0x0
    beq .L02209A06
    ldrb r0, [r4, #0x2]
    bl 0x021D12F4
    ldrb r0, [r4, #0x2]
    movs r1, #0x1
    ands r0, r1
    ldr r1, .L02209A10
    muls r1, r0
    ldr r0, .L02209A14
    adds r6, r0, r1
    ldr r7, [r6, #0x10]
    movs r0, #0xc1
    lsls r0, r0, #2
    adds r6, r6, r0
.L0220997E:
    cmp r7, #0x0
    ble .L02209A06
    ldr r0, [r6, #0x0]
    lsls r0, r0, #18
    lsrs r0, r0, #18
    bl 0x022222A0
    cmp r0, #0x0
    beq .L0220999E
    ldr r0, [r6, #0x0]
    lsls r0, r0, #18
    lsrs r0, r0, #18
    bl 0x0202ABD8
    cmp r0, #0x7
    bge .L022099A4
.L0220999E:
    .hword 0x1D36    @ adds r6, r6, #0x4
    .hword 0x1E7F    @ subs r7, r7, #0x1
    b .L0220997E
.L022099A4:
    ldrb r0, [r4, #0x2]
    movs r1, #0x3a
    bl 0x0219A818
    movs r0, #0x7e
    pop {r4, r5, r6, r7, pc}
    adds r0, r4, #0x0
    bl 0x02234E78
    adds r3, r0, #0x0
    ldrb r0, [r4, #0x2]
    ldrb r1, [r4, #0x6]
    eors r0, r1
    movs r1, #0x6
    ldrh r2, [r4, #0x0]
    bl 0x0219C430
    movs r0, #0x7d
    pop {r4, r5, r6, r7, pc}
    ldr r0, .L02209A18
    ldrh r0, [r0, #0x4]
    lsls r0, r0, #16
    bmi .L02209A06
    sub sp, #0x8
    bl 0x0219C510
    adds r1, r0, #0x0
    ldrh r2, [r4, #0x0]
    lsls r2, r2, #16
    str r2, [sp, #0x0]
    ldrb r0, [r4, #0x2]
    ldrb r3, [r4, #0x6]
    eors r0, r3
    movs r2, #0x1
    movs r3, #0x2
    bl 0x0226925C
    add sp, #0x8
    movs r0, #0x7c
    pop {r4, r5, r6, r7, pc}
    bl 0x021D2964
    ldrb r0, [r4, #0x2]
    ldrb r1, [r4, #0x6]
    eors r0, r1
    bl 0x021D269C
    movs r0, #0x0
    pop {r4, r5, r6, r7, pc}
.L02209A06:
    bl 0x021D2964
    movs r0, #0x0
    pop {r4, r5, r6, r7, pc}
    nop
.L02209A10:
    .word 0x00000B3C
.L02209A14:
    .word 0x0229AC94
.L02209A18:
    .word 0x0229944C

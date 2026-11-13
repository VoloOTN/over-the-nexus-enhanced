    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, r7, lr}
    sub sp, #0xc
    adds r4, r0, #0x0
    ldrb r5, [r4, #0x2]
    ldr r6, .L023AB288
    ldr r0, [r6, #0x70]
    cmp r0, #0x80
    bne .L023AB122
    b .L023AB220
.L023AB122:
    cmp r0, #0x7f
    beq .L023AB144
    cmp r0, #0x7e
    beq .L023AB154
    cmp r0, #0x7d
    beq .L023AB188
    cmp r0, #0x7c
    beq .L023AB198
    cmp r0, #0x7b
    beq .L023AB1BA
    cmp r0, #0x7a
    bne .L023AB13C
    b .L023AB1D8
.L023AB13C:
    cmp r0, #0x79
    bne .L023AB142
    b .L023AB1F4
.L023AB142:
    b .L023AB27E
.L023AB144:
    adds r0, r5, #0x0
    movs r1, #0x6
    ldr r2, .L023AB28C
    ldr r3, .L023AB290
    ldr r7, .L023AB294
    blx r7
    movs r0, #0x7e
    b .L023AB284
.L023AB154:
    ldr r1, .L023AB298
    ldrh r0, [r1, #0x4]
    lsls r0, r0, #1
    ldr r1, .L023AB29C
    ldrh r0, [r1, r0]
    movs r1, #0x1
    ands r1, r0
    lsls r2, r0, #26
    lsrs r2, r2, #27
    strh r2, [r4, #0x18]
    ldr r3, .L023AB2A0
    blx r3
    ldr r0, [r0, #0x0]
    lsls r1, r0, #17
    lsrs r1, r1, #31
    lsls r0, r0, #1
    lsrs r0, r0, #24
    lsls r0, r0, #1
    adds r0, r0, r1
    strh r0, [r4, #0x1c]
    adds r0, r5, #0x0
    movs r1, #0x79
    ldr r3, .L023AB2A4
    blx r3
    movs r0, #0x7d
    b .L023AB284
.L023AB188:
    adds r0, r5, #0x0
    movs r1, #0x6
    ldr r2, .L023AB28C
    ldr r3, .L023AB2A8
    ldr r7, .L023AB294
    blx r7
    movs r0, #0x7c
    b .L023AB284
.L023AB198:
    ldr r1, .L023AB298
    ldrh r0, [r1, #0x4]
    lsls r0, r0, #1
    ldr r1, .L023AB29C
    ldrh r0, [r1, r0]
    movs r1, #0x1
    ands r1, r0
    lsls r2, r0, #26
    lsrs r2, r2, #27
    strh r2, [r4, #0x1e]
    adds r0, r5, #0x0
    adds r1, r5, #0x0
    ldrh r2, [r4, #0x1c]
    ldr r3, .L023AB2AC
    blx r3
    movs r0, #0x7b
    b .L023AB284
.L023AB1BA:
    ldr r0, .L023AB2B0
    ldrh r0, [r0, #0x24]
    str r0, [sp, #0x0]
    movs r0, #0x1
    str r0, [sp, #0x4]
    movs r0, #0x0
    str r0, [sp, #0x8]
    ldrh r1, [r4, #0x18]
    adds r0, r5, #0x0
    ldrh r2, [r4, #0x1c]
    adds r3, r5, #0x0
    ldr r7, .L023AB2B4
    blx r7
    movs r0, #0x7a
    b .L023AB284
.L023AB1D8:
    ldr r0, .L023AB2B0
    ldrh r1, [r0, #0x24]
    lsls r1, r1, #24
    lsrs r1, r1, #16
    orrs r1, r5
    ldrh r2, [r4, #0x1e]
    lsls r2, r2, #8
    orrs r2, r5
    movs r3, #0xa
    adds r0, r5, #0x0
    ldr r7, .L023AB2B8
    blx r7
    movs r0, #0x79
    b .L023AB284
.L023AB1F4:
    ldrh r0, [r4, #0xc]
    ldr r3, .L023AB2BC
    blx r3
    lsls r1, r0, #24
    lsrs r1, r1, #24
    lsls r2, r0, #16
    lsrs r2, r2, #24
    cmp r2, #0x9
    bgt .L023AB27E
    str r1, [sp, #0x0]
    str r2, [sp, #0x4]
    adds r0, r4, #0x0
    ldr r3, .L023AB2C0
    blx r3
    cmp r0, #0x0
    beq .L023AB27E
    adds r0, r4, #0x0
    ldr r1, [sp, #0x0]
    ldr r2, [sp, #0x4]
    ldr r3, .L023AB2C4
    blx r3
    b .L023AB27E
.L023AB220:
    ldr r3, .L023AB2C8
    blx r3
    ldrb r0, [r4, #0x2]
    movs r1, #0xb
    ldr r2, .L023AB2CC
    movs r3, #0x1
    ldr r5, .L023AB2D0
    blx r5
    cmp r0, #0x0
    bne .L023AB27E
    ldrb r0, [r4, #0x2]
    ldr r1, .L023AB2CC
    movs r2, #0x1
    movs r3, #0x0
    ldr r5, .L023AB2D4
    blx r5
    ldrb r5, [r4, #0x2]
    adds r0, r4, #0x0
    ldr r3, .L023AB2D8
    blx r3
    cmp r0, #0x0
    beq .L023AB27E
    adds r0, r5, #0x0
    ldr r3, .L023AB2DC
    blx r3
    cmp r0, #0x0
    ble .L023AB27E
    ldrb r0, [r4, #0x2]
    ldr r1, .L023AB28C
    ldr r2, .L023AB290
    ldr r3, .L023AB2E0
    blx r3
    cmp r0, #0x0
    beq .L023AB27E
    ldrb r0, [r4, #0x2]
    ldr r1, .L023AB28C
    ldr r2, .L023AB2A8
    ldr r3, .L023AB2E0
    blx r3
    cmp r0, #0x0
    beq .L023AB27E
    adds r0, r5, #0x0
    ldr r1, .L023AB2E4
    ldr r3, .L023AB2A4
    blx r3
    movs r0, #0x7f
    b .L023AB284
.L023AB27E:
    ldr r3, .L023AB2E8
    blx r3
    movs r0, #0x0
.L023AB284:
    add sp, #0xc
    pop {r4, r5, r6, r7, pc}
.L023AB288:
    .word 0x0229AAFC
.L023AB28C:
    .word 0x00001C39
.L023AB290:
    .word 0x00010000
.L023AB294:
    .word 0x0219C431
.L023AB298:
    .word 0x0229944C
.L023AB29C:
    .word 0x02299908
.L023AB2A0:
    .word 0x0219C511
.L023AB2A4:
    .word 0x0219A819
.L023AB2A8:
    .word 0x00020000
.L023AB2AC:
    .word 0x0225BDD9
.L023AB2B0:
    .word 0x0229DE54
.L023AB2B4:
    .word 0x021C7485
.L023AB2B8:
    .word 0x021C4A69
.L023AB2BC:
    .word 0x021A241D
.L023AB2C0:
    .word 0x0224A925
.L023AB2C4:
    .word 0x021CF389
.L023AB2C8:
    .word 0x021D28A5
.L023AB2CC:
    .word 0x00005C39
.L023AB2D0:
    .word 0x021A14E9
.L023AB2D4:
    .word 0x021D2585
.L023AB2D8:
    .word 0x021D2C1D
.L023AB2DC:
    .word 0x021AE645
.L023AB2E0:
    .word 0x02243FE1
.L023AB2E4:
    .word 0x00000139
.L023AB2E8:
    .word 0x021D2965

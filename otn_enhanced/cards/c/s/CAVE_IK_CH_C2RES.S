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
    ldr r6, .L023A9F84
    ldr r0, [r6, #0x70]
    cmp r0, #0x80
    bne .L023A9E32
    b .L023A9EF2
.L023A9E32:
    cmp r0, #0x7b
    bne .L023A9E38
    b .L023A9F28
.L023A9E38:
    cmp r0, #0x7a
    bne .L023A9E3E
    b .L023A9F3E
.L023A9E3E:
    movs r7, #0x0
    cmp r0, #0x7b
    bge .L023A9E48
    movs r7, #0x1
    adds r0, #0x6
.L023A9E48:
    cmp r0, #0x7f
    beq .L023A9E5C
    cmp r0, #0x7e
    beq .L023A9E76
    cmp r0, #0x7d
    beq .L023A9E94
    cmp r0, #0x7c
    bne .L023A9E5A
    b .L023A9EC4
.L023A9E5A:
    b .L023A9F50
.L023A9E5C:
    ldrh r0, [r4, #0xc]
    ldr r3, .L023A9F88
    blx r3
    lsls r0, r0, #16
    lsrs r0, r0, #16
    lsls r3, r7, #16
    orrs r3, r0
    adds r0, r5, #0x0
    movs r1, #0x6
    ldr r2, .L023A9F8C
    ldr r7, .L023A9F90
    blx r7
    b .L023A9EEC
.L023A9E76:
    ldr r3, .L023A9F94
    blx r3
    ldr r0, [r0, #0x0]
    lsls r1, r0, #17
    lsrs r1, r1, #31
    lsls r0, r0, #1
    lsrs r0, r0, #24
    lsls r0, r0, #1
    adds r2, r0, r1
    strh r2, [r4, #0x1c]
    adds r0, r5, #0x0
    adds r1, r5, #0x0
    ldr r3, .L023A9F98
    blx r3
    b .L023A9EEC
.L023A9E94:
    movs r1, #0xd
    cmp r7, #0x0
    bne .L023A9EAA
    adds r0, r5, #0x0
    ldrh r1, [r4, #0x1c]
    ldr r3, .L023A9F9C
    blx r3
    movs r1, #0xb
    cmp r0, #0x0
    bge .L023A9EAA
    movs r1, #0xe
.L023A9EAA:
    ldr r0, .L023A9FA0
    ldrh r0, [r0, #0x24]
    str r0, [sp, #0x0]
    movs r0, #0x1
    str r0, [sp, #0x4]
    movs r0, #0x0
    str r0, [sp, #0x8]
    adds r0, r5, #0x0
    ldrh r2, [r4, #0x1c]
    adds r3, r5, #0x0
    ldr r7, .L023A9FA4
    blx r7
    b .L023A9EEC
.L023A9EC4:
    ldrh r0, [r4, #0xc]
    ldr r3, .L023A9F88
    blx r3
    lsls r0, r0, #16
    lsrs r0, r0, #16
    adds r2, r0, #0x0
    ldr r0, .L023A9FA0
    ldrh r1, [r0, #0x24]
    lsls r1, r1, #24
    lsrs r1, r1, #16
    orrs r1, r5
    movs r3, #0xa
    adds r0, r5, #0x0
    ldr r7, .L023A9FA8
    blx r7
    ldr r0, [r6, #0x70]
    cmp r0, #0x7c
    beq .L023A9EEC
    movs r0, #0x71
    b .L023A9F56
.L023A9EEC:
    ldr r0, [r6, #0x70]
    subs r0, #0x1
    b .L023A9F56
.L023A9EF2:
    ldr r3, .L023A9FAC
    blx r3
    ldrb r0, [r4, #0x2]
    movs r1, #0xb
    ldr r2, .L023A9FB0
    movs r3, #0x1
    ldr r5, .L023A9FB4
    blx r5
    cmp r0, #0x0
    bne .L023A9F50
    ldrb r0, [r4, #0x2]
    ldr r1, .L023A9FB0
    movs r2, #0x1
    movs r3, #0x0
    ldr r5, .L023A9FB8
    blx r5
    ldrb r5, [r4, #0x2]
    adds r0, r4, #0x0
    ldr r3, .L023A9FBC
    blx r3
    cmp r0, #0x0
    beq .L023A9F50
    movs r7, #0x0
    bl 0x023A9F5A
    beq .L023A9F50
    b .L023A9F46
.L023A9F28:
    movs r7, #0x1
    bl 0x023A9F5A
    beq .L023A9F50
    adds r0, r4, #0x0
    movs r1, #0xfa
    ldrh r2, [r4, #0xc]
    ldr r3, .L023A9FC0
    blx r3
    movs r0, #0x7a
    b .L023A9F56
.L023A9F3E:
    ldr r0, .L023A9FC4
    ldr r0, [r0, #0x34]
    cmp r0, #0x0
    beq .L023A9F50
.L023A9F46:
    adds r0, r5, #0x0
    movs r1, #0x5e
    ldr r3, .L023A9FC8
    blx r3
    b .L023A9EEC
.L023A9F50:
    ldr r3, .L023A9FCC
    blx r3
    movs r0, #0x0
.L023A9F56:
    add sp, #0xc
    pop {r4, r5, r6, r7, pc}
    push {lr}
    adds r0, r5, #0x0
    ldr r3, .L023A9FD0
    blx r3
    cmp r0, #0x0
    ble .L023A9F7E
    ldrh r0, [r4, #0xc]
    ldr r3, .L023A9F88
    blx r3
    lsls r0, r0, #16
    lsrs r0, r0, #16
    lsls r2, r7, #16
    orrs r2, r0
    adds r0, r5, #0x0
    ldr r1, .L023A9F8C
    ldr r3, .L023A9FD4
    blx r3
    b .L023A9F80
.L023A9F7E:
    movs r0, #0x0
.L023A9F80:
    cmp r0, #0x0
    pop {pc}
.L023A9F84:
    .word 0x0229AAFC
.L023A9F88:
    .word 0x021A241D
.L023A9F8C:
    .word 0x000017EF
.L023A9F90:
    .word 0x0219C431
.L023A9F94:
    .word 0x0219C511
.L023A9F98:
    .word 0x0225BDD9
.L023A9F9C:
    .word 0x021A25A1
.L023A9FA0:
    .word 0x0229DE54
.L023A9FA4:
    .word 0x021C7485
.L023A9FA8:
    .word 0x021C4A69
.L023A9FAC:
    .word 0x021D28A5
.L023A9FB0:
    .word 0x000037EF
.L023A9FB4:
    .word 0x021A14E9
.L023A9FB8:
    .word 0x021D2585
.L023A9FBC:
    .word 0x021D2C1D
.L023A9FC0:
    .word 0x0219AAAD
.L023A9FC4:
    .word 0x0229DD94
.L023A9FC8:
    .word 0x0219A819
.L023A9FCC:
    .word 0x021D2965
.L023A9FD0:
    .word 0x021AE645
.L023A9FD4:
    .word 0x02243FE1

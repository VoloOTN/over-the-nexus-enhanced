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
    ldr r6, .L023ABE9C
    ldr r0, [r6, #0x70]
    cmp r0, #0x80
    bne .L023ABD02
    b .L023ABD3A
.L023ABD02:
    cmp r0, #0x7f
    bne .L023ABD08
    b .L023ABD7C
.L023ABD08:
    cmp r0, #0x7e
    bne .L023ABD0E
    b .L023ABD8E
.L023ABD0E:
    cmp r0, #0x7d
    bne .L023ABD14
    b .L023ABDAE
.L023ABD14:
    cmp r0, #0x7c
    bne .L023ABD1A
    b .L023ABDC0
.L023ABD1A:
    cmp r0, #0x7b
    bne .L023ABD20
    b .L023ABDEA
.L023ABD20:
    cmp r0, #0x7a
    bne .L023ABD26
    b .L023ABE2A
.L023ABD26:
    cmp r0, #0x79
    bne .L023ABD2C
    b .L023ABE40
.L023ABD2C:
    cmp r0, #0x78
    bne .L023ABD32
    b .L023ABE5E
.L023ABD32:
    cmp r0, #0x77
    bne .L023ABD38
    b .L023ABE7C
.L023ABD38:
    b .L023ABE90
.L023ABD3A:
    ldr r3, .L023ABEA0
    blx r3
    ldrb r0, [r4, #0x2]
    ldr r1, .L023ABEA4
    ldr r2, .L023ABEA8
    ldr r3, .L023ABEAC
    blx r3
    cmp r0, #0x0
    beq .L023ABD7A
    ldrb r0, [r4, #0x2]
    ldr r1, .L023ABEA4
    ldr r2, .L023ABEB0
    ldr r3, .L023ABEAC
    blx r3
    cmp r0, #0x0
    beq .L023ABD7A
    adds r0, r5, #0x0
    ldr r3, .L023ABEB4
    blx r3
    cmp r0, #0x0
    beq .L023ABD7A
    adds r0, r5, #0x0
    ldr r3, .L023ABEB8
    blx r3
    cmp r0, #0x0
    beq .L023ABD7A
    adds r0, r5, #0x0
    ldr r1, .L023ABEBC
    ldr r3, .L023ABEC0
    blx r3
    movs r0, #0x7f
    b .L023ABE96
.L023ABD7A:
    b .L023ABE90
.L023ABD7C:
    adds r0, r5, #0x0
    movs r1, #0x6
    ldr r2, .L023ABEA4
    movs r3, #0x4
    lsls r3, r3, #16
    ldr r7, .L023ABEC4
    blx r7
    movs r0, #0x7e
    b .L023ABE96
.L023ABD8E:
    ldr r3, .L023ABEC8
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
    ldr r1, .L023ABECC
    ldr r3, .L023ABEC0
    blx r3
    movs r0, #0x7d
    b .L023ABE96
.L023ABDAE:
    adds r0, r5, #0x0
    movs r1, #0x6
    ldr r2, .L023ABEA4
    movs r3, #0x5
    lsls r3, r3, #16
    ldr r7, .L023ABEC4
    blx r7
    movs r0, #0x7c
    b .L023ABE96
.L023ABDC0:
    ldr r3, .L023ABEC8
    blx r3
    adds r7, r0, #0x0
    ldr r0, [r0, #0x0]
    lsls r1, r0, #17
    lsrs r1, r1, #31
    lsls r0, r0, #1
    lsrs r0, r0, #24
    lsls r0, r0, #1
    adds r2, r0, r1
    strh r2, [r4, #0x1e]
    ldr r0, .L023ABED0
    str r0, [sp, #0x0]
    adds r0, r5, #0x0
    adds r1, r7, #0x0
    movs r2, #0x1
    movs r3, #0x2
    ldr r7, .L023ABED4
    blx r7
    movs r0, #0x7b
    b .L023ABE96
.L023ABDEA:
    adds r0, r5, #0x0
    ldrh r1, [r4, #0x1c]
    ldr r3, .L023ABED8
    blx r3
    cmp r0, #0x0
    blt .L023ABE28
    adds r0, r5, #0x0
    ldr r3, .L023ABEDC
    blx r3
    cmp r0, #0x0
    ble .L023ABE28
    ldrh r0, [r4, #0x1e]
    ldr r3, .L023ABEE0
    blx r3
    cmp r0, #0x0
    blt .L023ABE28
    lsls r1, r0, #24
    lsrs r1, r1, #24
    cmp r1, r5
    bne .L023ABE28
    lsls r0, r0, #16
    lsrs r0, r0, #24
    cmp r0, #0x4
    bgt .L023ABE28
    adds r0, r4, #0x0
    movs r1, #0xfa
    ldrh r2, [r4, #0xc]
    ldr r3, .L023ABEE4
    blx r3
    movs r0, #0x7a
    b .L023ABE96
.L023ABE28:
    b .L023ABE7C
.L023ABE2A:
    ldr r0, .L023ABEE8
    ldr r0, [r0, #0x34]
    cmp r0, #0x0
    beq .L023ABE28
    adds r0, r5, #0x0
    adds r1, r5, #0x0
    ldrh r2, [r4, #0x1c]
    ldr r3, .L023ABEEC
    blx r3
    movs r0, #0x79
    b .L023ABE96
.L023ABE40:
    ldr r0, .L023ABEF0
    ldrh r0, [r0, #0x24]
    str r0, [sp, #0x0]
    movs r0, #0x1
    str r0, [sp, #0x4]
    movs r0, #0x0
    str r0, [sp, #0x8]
    adds r0, r5, #0x0
    movs r1, #0xb
    ldrh r2, [r4, #0x1c]
    adds r3, r5, #0x0
    ldr r7, .L023ABEF4
    blx r7
    movs r0, #0x78
    b .L023ABE96
.L023ABE5E:
    ldrh r0, [r4, #0x1e]
    ldr r3, .L023ABEE0
    blx r3
    lsls r2, r0, #16
    lsrs r2, r2, #16
    ldr r0, .L023ABEF0
    ldrh r1, [r0, #0x24]
    lsls r1, r1, #24
    lsrs r1, r1, #16
    orrs r1, r5
    movs r3, #0xa
    adds r0, r5, #0x0
    ldr r7, .L023ABEF8
    blx r7
    b .L023ABE90
.L023ABE7C:
    adds r0, r5, #0x0
    ldrh r1, [r4, #0x1c]
    ldr r3, .L023ABED8
    blx r3
    cmp r0, #0x0
    blt .L023ABE90
    adds r1, r0, #0x0
    adds r0, r5, #0x0
    ldr r3, .L023ABEFC
    blx r3
.L023ABE90:
    ldr r3, .L023ABF00
    blx r3
    movs r0, #0x0
.L023ABE96:
    add sp, #0xc
    pop {r4, r5, r6, r7, pc}
    nop
.L023ABE9C:
    .word 0x0229AAFC
.L023ABEA0:
    .word 0x021D28A5
.L023ABEA4:
    .word 0x00001C39
.L023ABEA8:
    .word 0x00040000
.L023ABEAC:
    .word 0x02243FE1
.L023ABEB0:
    .word 0x00050000
.L023ABEB4:
    .word 0x021B9ECD
.L023ABEB8:
    .word 0x021AD871
.L023ABEBC:
    .word 0x00000139
.L023ABEC0:
    .word 0x0219A819
.L023ABEC4:
    .word 0x0219C431
.L023ABEC8:
    .word 0x0219C511
.L023ABECC:
    .word 0x0000011D
.L023ABED0:
    .word 0x16DB0000
.L023ABED4:
    .word 0x0226925D
.L023ABED8:
    .word 0x021A25A1
.L023ABEDC:
    .word 0x021AE645
.L023ABEE0:
    .word 0x021A241D
.L023ABEE4:
    .word 0x0219AAAD
.L023ABEE8:
    .word 0x0229DD94
.L023ABEEC:
    .word 0x0225BDD9
.L023ABEF0:
    .word 0x0229DE54
.L023ABEF4:
    .word 0x021C7485
.L023ABEF8:
    .word 0x021C4A69
.L023ABEFC:
    .word 0x021C6D91
.L023ABF00:
    .word 0x021D2965

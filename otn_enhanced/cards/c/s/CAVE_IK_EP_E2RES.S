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
    ldr r6, .L023AC0CC
    ldr r0, [r6, #0x70]
    cmp r0, #0x80
    bne .L023ABFD2
    b .L023ABFEC
.L023ABFD2:
    cmp r0, #0x7f
    bne .L023ABFD8
    b .L023AC050
.L023ABFD8:
    cmp r0, #0x7e
    bne .L023ABFDE
    b .L023AC062
.L023ABFDE:
    cmp r0, #0x7d
    bne .L023ABFE4
    b .L023AC082
.L023ABFE4:
    cmp r0, #0x7c
    bne .L023ABFEA
    b .L023AC0AE
.L023ABFEA:
    b .L023AC0C2
.L023ABFEC:
    ldr r3, .L023AC0D0
    blx r3
    ldrb r0, [r4, #0x2]
    movs r1, #0xb
    ldr r2, .L023AC0D4
    movs r3, #0x1
    ldr r5, .L023AC0D8
    blx r5
    cmp r0, #0x0
    bne .L023AC0C2
    ldrb r0, [r4, #0x2]
    ldr r1, .L023AC0D4
    movs r2, #0x1
    movs r3, #0x0
    ldr r5, .L023AC0DC
    blx r5
    adds r0, r4, #0x0
    movs r1, #0x0
    movs r2, #0x0
    ldr r3, .L023AC0E0
    blx r3
    cmp r0, #0x0
    beq .L023AC0C2
    adds r0, r4, #0x0
    movs r1, #0x0
    ldr r3, .L023AC0E4
    blx r3
    ldr r3, .L023AC0E8
    blx r3
    cmp r0, #0x0
    blt .L023AC0C2
    strh r0, [r4, #0x18]
    adds r0, r5, #0x0
    ldr r3, .L023AC0EC
    blx r3
    cmp r0, #0x0
    ble .L023AC0C2
    ldrb r0, [r4, #0x2]
    ldr r1, .L023AC0F0
    ldr r2, .L023AC0F4
    ldr r3, .L023AC0F8
    blx r3
    cmp r0, #0x0
    beq .L023AC0C2
    adds r0, r5, #0x0
    movs r1, #0x5e
    ldr r3, .L023AC0FC
    blx r3
    movs r0, #0x7f
    b .L023AC0C8
.L023AC050:
    adds r0, r5, #0x0
    movs r1, #0x6
    ldr r2, .L023AC0F0
    movs r3, #0x5
    lsls r3, r3, #16
    ldr r7, .L023AC100
    blx r7
    movs r0, #0x7e
    b .L023AC0C8
.L023AC062:
    ldr r3, .L023AC104
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
    ldr r3, .L023AC108
    blx r3
    movs r0, #0x7d
    b .L023AC0C8
.L023AC082:
    adds r0, r5, #0x0
    ldrh r1, [r4, #0x1c]
    ldr r3, .L023AC10C
    blx r3
    movs r1, #0xb
    cmp r0, #0x0
    bge .L023AC092
    movs r1, #0xd
.L023AC092:
    ldr r0, .L023AC110
    ldrh r0, [r0, #0x24]
    str r0, [sp, #0x0]
    movs r0, #0x1
    str r0, [sp, #0x4]
    movs r0, #0x0
    str r0, [sp, #0x8]
    adds r0, r5, #0x0
    ldrh r2, [r4, #0x1c]
    adds r3, r5, #0x0
    ldr r7, .L023AC114
    blx r7
    movs r0, #0x7c
    b .L023AC0C8
.L023AC0AE:
    ldr r0, .L023AC110
    ldrh r1, [r0, #0x24]
    lsls r1, r1, #24
    lsrs r1, r1, #16
    orrs r1, r5
    ldrh r2, [r4, #0x18]
    movs r3, #0xa
    adds r0, r5, #0x0
    ldr r7, .L023AC118
    blx r7
.L023AC0C2:
    ldr r3, .L023AC11C
    blx r3
    movs r0, #0x0
.L023AC0C8:
    add sp, #0xc
    pop {r4, r5, r6, r7, pc}
.L023AC0CC:
    .word 0x0229AAFC
.L023AC0D0:
    .word 0x021D28A5
.L023AC0D4:
    .word 0x000056DB
.L023AC0D8:
    .word 0x021A14E9
.L023AC0DC:
    .word 0x021D2585
.L023AC0E0:
    .word 0x022349B1
.L023AC0E4:
    .word 0x02234965
.L023AC0E8:
    .word 0x021A241D
.L023AC0EC:
    .word 0x021AE645
.L023AC0F0:
    .word 0x00001C39
.L023AC0F4:
    .word 0x00050000
.L023AC0F8:
    .word 0x02243FE1
.L023AC0FC:
    .word 0x0219A819
.L023AC100:
    .word 0x0219C431
.L023AC104:
    .word 0x0219C511
.L023AC108:
    .word 0x0225BDD9
.L023AC10C:
    .word 0x021A25A1
.L023AC110:
    .word 0x0229DE54
.L023AC114:
    .word 0x021C7485
.L023AC118:
    .word 0x021C4A69
.L023AC11C:
    .word 0x021D2965

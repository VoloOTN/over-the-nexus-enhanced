    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [r0, #0x10]
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5010
    cmp r1, r2
    bne .L023A4ED4
    ldrb r1, [r4, #0x3]
    cmp r1, #0xe
    bne .L023A4ED2
    ldr r0, .L023A5014
.L023A4ED2:
    b .L023A500A
.L023A4ED4:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5018
    cmp r1, r2
    bne .L023A4EE6
    ldrb r1, [r4, #0x3]
    cmp r1, #0xe
    bne .L023A4EE4
    ldr r0, .L023A5014
.L023A4EE4:
    b .L023A500A
.L023A4EE6:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A501C
    cmp r1, r2
    bne .L023A4EFE
    ldrb r1, [r4, #0x3]
    cmp r1, #0xe
    bne .L023A4EFC
    ldrb r1, [r4, #0x4]
    cmp r1, #0x6
    ble .L023A4EFC
    ldr r0, .L023A5014
.L023A4EFC:
    b .L023A500A
.L023A4EFE:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5020
    cmp r1, r2
    bne .L023A4F16
    ldrb r1, [r4, #0x3]
    cmp r1, #0xe
    bne .L023A500A
    ldrb r1, [r4, #0x4]
    cmp r1, #0x6
    ble .L023A500A
    movs r0, #0x0
    b .L023A500A
.L023A4F16:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5024
    cmp r1, r2
    bne .L023A4F2E
    ldrb r1, [r4, #0x3]
    cmp r1, #0xe
    bne .L023A500A
    ldrb r1, [r4, #0x4]
    cmp r1, #0x6
    ble .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F2E:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5028
    cmp r1, r2
    bne .L023A4F40
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F40:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A502C
    cmp r1, r2
    bne .L023A4F52
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F52:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5030
    cmp r1, r2
    bne .L023A4F64
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F64:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5034
    cmp r1, r2
    bne .L023A4F76
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F76:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5038
    cmp r1, r2
    bne .L023A4F8C
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    beq .L023A4F88
    cmp r1, #0x2
    bne .L023A500A
.L023A4F88:
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F8C:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A503C
    cmp r1, r2
    bne .L023A4F9E
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4F9E:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5040
    cmp r1, r2
    bne .L023A4FB0
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4FB0:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5044
    cmp r1, r2
    bne .L023A4FC2
    ldrb r1, [r4, #0x5]
    cmp r1, #0x2
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4FC2:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5048
    cmp r1, r2
    bne .L023A4FD4
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4FD4:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A504C
    cmp r1, r2
    bne .L023A4FE6
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4FE6:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5050
    cmp r1, r2
    bne .L023A4FF8
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A4FF8:
    ldrh r1, [r4, #0x0]
    ldr r2, .L023A5054
    cmp r1, r2
    bne .L023A500A
    ldrb r1, [r4, #0x5]
    cmp r1, #0x1
    bne .L023A500A
    ldr r0, .L023A5014
    b .L023A500A
.L023A500A:
    cmp r0, #0x0
    bx lr
    nop
.L023A5010:
    .word 0x0000160B
.L023A5014:
    .word 0x021E51E5
.L023A5018:
    .word 0x00000FDB
.L023A501C:
    .word 0x0000139A
.L023A5020:
    .word 0x00000FB1
.L023A5024:
    .word 0x0000224C
.L023A5028:
    .word 0x000023EB
.L023A502C:
    .word 0x0000126F
.L023A5030:
    .word 0x00001008
.L023A5034:
    .word 0x00000FC6
.L023A5038:
    .word 0x0000111F
.L023A503C:
    .word 0x00001160
.L023A5040:
    .word 0x00001297
.L023A5044:
    .word 0x000010A5
.L023A5048:
    .word 0x00001110
.L023A504C:
    .word 0x0000181F
.L023A5050:
    .word 0x00001106
.L023A5054:
    .word 0x000013A3

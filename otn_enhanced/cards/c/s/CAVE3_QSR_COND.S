    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, lr}
    adds r5, r0, #0x0
    adds r4, r1, #0x0
    bl 0x021D2B88
    cmp r0, #0x0
    bne .L021D864E
    ldrb r0, [r5, #0x2]
    movs r1, #0xb
    ldrh r2, [r5, #0x0]
    movs r3, #0x1
    bl 0x021A14E8
    cmp r0, #0x0
    bne .L021D8658
.L021D864E:
    adds r0, r5, #0x0
    adds r1, r4, #0x0
    bl 0x021FE72C
    pop {r4, r5, pc}
.L021D8658:
    movs r0, #0x0
    pop {r4, r5, pc}

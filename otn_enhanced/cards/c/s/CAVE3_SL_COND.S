    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, lr}
    adds r4, r0, #0x0
    movs r5, #0x1
    ldrb r0, [r4, #0x7]
    cmp r0, #0x0
    bne .L0221D7A8
    adds r0, r4, #0x0
    bl 0x021F2460
    cmp r0, #0x0
    beq .L0221D7C0
    adds r5, r0, #0x0
.L0221D7A8:
    adds r0, r4, #0x0
    bl 0x02234E78
    adds r2, r0, #0x0
    ldrb r0, [r4, #0x2]
    ldrh r1, [r4, #0x0]
    bl 0x02243FE0
    cmp r0, #0x0
    ble .L0221D7C0
    adds r0, r5, #0x0
    pop {r4, r5, pc}
.L0221D7C0:
    movs r0, #0x0
    pop {r4, r5, pc}

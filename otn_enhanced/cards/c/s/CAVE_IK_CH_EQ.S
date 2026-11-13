    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r0, r4, r5, lr}
    movs r4, #0x0
.L023A9CB4:
    movs r5, #0x0
.L023A9CB6:
    adds r0, r4, #0x0
    adds r1, r5, #0x0
    ldr r2, .L023A9CE8
    ldr r3, .L023A9CEC
    blx r3
    cmp r0, #0x0
    beq .L023A9CD2
    adds r0, r4, #0x0
    adds r1, r5, #0x0
    movs r2, #0x19
    lsls r3, r7, #16
    orrs r3, r6
    bl 0x021D3230
.L023A9CD2:
    adds r5, #0x1
    cmp r5, #0x4
    ble .L023A9CB6
    adds r4, #0x1
    cmp r4, #0x1
    ble .L023A9CB4
    ldr r1, .L023A9CF0
    ldr r0, [sp, #0x0]
    cmp r0, r1
    pop {r0, r4, r5, pc}
    nop
.L023A9CE8:
    .word 0x000017EF
.L023A9CEC:
    .word 0x021AC005
.L023A9CF0:
    .word 0x000013C3

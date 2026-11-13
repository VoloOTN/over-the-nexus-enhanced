    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, lr}
    bl 0x021D2B88
    cmp r0, #0x0
    bne .L02212252
    movs r5, #0x0
.L0221222C:
    ldr r0, .L02212258
    muls r0, r5
    ldr r1, .L0221225C
    adds r1, r1, r0
    movs r6, #0x0
.L02212236:
    lsls r0, r6, #2
    adds r0, r0, r6
    lsls r0, r0, #2
    ldrh r0, [r1, r0]
    cmp r0, #0x0
    bne .L02212252
    .hword 0x1C76    @ adds r6, r6, #0x1
    cmp r6, #0x5
    blt .L02212236
    .hword 0x1C6D    @ adds r5, r5, #0x1
    cmp r5, #0x2
    blt .L0221222C
    movs r0, #0x0
    pop {r4, r5, r6, pc}
.L02212252:
    movs r0, #0x1
    pop {r4, r5, r6, pc}
    movs r0, r0
.L02212258:
    .word 0x00000B3C
.L0221225C:
    .word 0x0229ACCE

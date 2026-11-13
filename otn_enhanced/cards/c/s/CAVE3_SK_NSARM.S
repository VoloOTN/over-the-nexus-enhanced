    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r4, #0x0
    beq .L0221233E
    adds r0, r4, #0x0
    bl 0x020230D4
    cmp r0, #0x0
    beq .L02212360
.L0221233E:
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L02212364
    movs r3, #0x1
    bl 0x021A14E8
    cmp r0, #0x0
    beq .L02212360
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L02212368
    bl 0x021A1430
    cmp r0, #0x0
    bne .L02212360
    ldr r0, .L02212368
    pop {r3, r4, r5, r6, r7, pc}
.L02212360:
    bl 0x021C74CC
.L02212364:
    .word 0x000013E5
.L02212368:
    .word 0x00003E50

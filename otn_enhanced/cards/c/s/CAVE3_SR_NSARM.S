    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r4, #0x0
    beq .L021C74DA
    adds r0, r4, #0x0
    bl 0x02023EE4
    cmp r0, #0x0
    beq .L021C74FE
.L021C74DA:
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L021C7504
    movs r3, #0x1
    bl 0x021A14E8
    cmp r0, #0x0
    beq .L021C74FE
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L021C7504
    movs r3, #0x2
    bl 0x021A14E8
    cmp r0, #0x0
    bne .L021C74FE
    ldr r0, .L021C7504
    pop {r3, r4, r5, r6, r7, pc}
.L021C74FE:
    bl 0x021D8754
    movs r0, r0
.L021C7504:
    .word 0x00000FF6

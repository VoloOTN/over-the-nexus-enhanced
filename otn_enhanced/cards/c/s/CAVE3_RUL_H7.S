    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r0, r2, r3, lr}
    adds r0, r5, #0x0
    bl 0x021F19E8
    lsrs r0, r0, #2
    bne .L021F1A1C
    ldr r0, [sp, #0x40]
    cmp r0, #0xf
.L021F1A1C:
    pop {r0, r2, r3}
    ldr r1, .L021F1A2C
    beq .L021F1A26
    cmp r5, r1
    pop {pc}
.L021F1A26:
    pop {r1}
    ldr r1, .L021F1A30
    bx r1
.L021F1A2C:
    .word 0x00001D98
.L021F1A30:
    .word 0x021D1D3F

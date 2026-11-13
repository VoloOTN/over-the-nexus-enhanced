    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    movs r0, #0x17
    lsls r0, r0, #8
    adds r0, #0x77
    cmp r5, r0
    bne .L021FAE40
    movs r0, #0x5b
    lsls r0, r0, #8
    pop {r3, r4, r5, r6, r7, pc}
.L021FAE40:
    bl 0x021F1BE0

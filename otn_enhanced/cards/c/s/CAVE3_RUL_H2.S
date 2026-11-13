    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    adds r0, r5, #0x0
    bl 0x021F19E8
    bmi .L021F1BEE
    adds r0, #0x40
    lsls r0, r0, #8
    pop {r3, r4, r5, r6, r7, pc}
.L021F1BEE:
    movs r0, #0x0
    subs r0, #0x1
    pop {r3, r4, r5, r6, r7, pc}

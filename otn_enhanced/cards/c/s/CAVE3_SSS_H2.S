    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    movs r0, #0x13
    lsls r0, r0, #8
    adds r0, #0xa
    cmp r5, r0
    bne .L021F16DC
    movs r0, #0x5f
    lsls r0, r0, #8
    pop {r3, r4, r5, r6, r7, pc}
.L021F16DC:
    bl 0x021FAE30

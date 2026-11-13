    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r0, r1, r2, r3, lr}
    bl 0x021F19E8
    bmi .L02220BDC
    bl 0x023A75A0
    add sp, #0x10
    pop {pc}
.L02220BDC:
    bl 0x021F1A34

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {lr}
    bl 0x021F19E8
    bmi .L023A6200
    lsls r0, r0, #6
    ldr r1, .L023A6204
    adds r0, r0, r1
    pop {pc}
.L023A6200:
    movs r0, #0x0
    pop {pc}
.L023A6204:
    .word 0x023A6BF0

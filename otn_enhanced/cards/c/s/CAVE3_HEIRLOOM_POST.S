    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021D85FC
    cmp r0, r1
    beq .L021D85FA
    ldr r1, .L021D8600
    cmp r0, r1
.L021D85FA:
    bx lr
.L021D85FC:
    .word 0x00002007
.L021D8600:
    .word 0x00002124

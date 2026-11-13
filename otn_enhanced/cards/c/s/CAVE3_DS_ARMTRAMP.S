    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021F5AE4
    cmp r4, r1
    bne .L021F5ADE
    ldr r1, .L021F5AE8
    bx r1
.L021F5ADE:
    ldr r0, .L021F5AEC
    cmp r4, r0
    bx lr
.L021F5AE4:
    .word 0x00001783
.L021F5AE8:
    .word 0x021CA641
.L021F5AEC:
    .word 0x00001A64

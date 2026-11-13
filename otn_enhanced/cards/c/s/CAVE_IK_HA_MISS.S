    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023AB760
    cmp r3, r1
    bne .L023AB75A
    cmp r3, r3
    bx lr
.L023AB75A:
    subs r1, r2, #0x3
    cmp r3, r1
    bx lr
.L023AB760:
    .word 0x00001F71

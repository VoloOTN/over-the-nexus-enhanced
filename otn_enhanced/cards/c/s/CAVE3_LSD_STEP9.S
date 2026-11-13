    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021F9458
    cmp r4, r1
    beq .L021F9456
    ldr r1, .L021F945C
    cmp r4, r1
.L021F9456:
    bx lr
.L021F9458:
    .word 0x000022D3
.L021F945C:
    .word 0x000018FA

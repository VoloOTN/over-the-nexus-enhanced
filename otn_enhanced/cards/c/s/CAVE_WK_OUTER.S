    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023A4960
    cmp r5, r1
    beq .L023A495C
    ldr r1, .L023A4964
    cmp r5, r1
    bx lr
.L023A495C:
    ldr r1, .L023A4968
    bx r1
.L023A4960:
    .word 0x00001458
.L023A4964:
    .word 0x0000221A
.L023A4968:
    .word 0x02248A41

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, .L023A4980
    cmp r5, r0
    beq .L023A497C
    ldr r0, .L023A4984
    cmp r5, r0
    bx lr
.L023A497C:
    ldr r0, .L023A4988
    bx r0
.L023A4980:
    .word 0x00001458
.L023A4984:
    .word 0x00001E9A
.L023A4988:
    .word 0x02248FD9

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023A6F1C
    cmp r0, r1
    beq .L023A6F18
    ldr r1, .L023A6F20
    cmp r0, r1
    beq .L023A6F18
    ldr r1, .L023A6F24
    cmp r0, r1
    beq .L023A6F18
    ldr r1, .L023A6F28
    cmp r0, r1
    beq .L023A6F18
    ldr r1, .L023A6F2C
    cmp r0, r1
    beq .L023A6F18
    ldr r1, .L023A6F30
    cmp r0, r1
    beq .L023A6F18
    movs r0, #0x0
    pop {r3, r4, r5, pc}
.L023A6F18:
    movs r0, #0x1
    pop {r3, r4, r5, pc}
.L023A6F1C:
    .word 0x000017CD
.L023A6F20:
    .word 0x0000115F
.L023A6F24:
    .word 0x00001145
.L023A6F28:
    .word 0x00001125
.L023A6F2C:
    .word 0x000010E6
.L023A6F30:
    .word 0x00001649

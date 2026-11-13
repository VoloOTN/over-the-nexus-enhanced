    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r4, #0x3c
    blt .L023A6EC2
    ldr r0, .L023A6EC4
    cmp r5, r0
    beq .L023A6EB8
    ldr r0, .L023A6EC8
    cmp r5, r0
    beq .L023A6EB8
    ldr r0, .L023A6ECC
    cmp r5, r0
    beq .L023A6EB8
    ldr r0, .L023A6ED0
    cmp r5, r0
    beq .L023A6EB8
    ldr r0, .L023A6ED4
    cmp r5, r0
    beq .L023A6EB8
    ldr r0, .L023A6ED8
    cmp r5, r0
    bne .L023A6EC2
.L023A6EB8:
    adds r0, r6, #0x0
    adds r1, r5, #0x0
    adds r2, r7, #0x0
    bl 0x0224C6C0
.L023A6EC2:
    pop {r3, r4, r5, r6, r7, pc}
.L023A6EC4:
    .word 0x000017CD
.L023A6EC8:
    .word 0x0000115F
.L023A6ECC:
    .word 0x00001145
.L023A6ED0:
    .word 0x00001125
.L023A6ED4:
    .word 0x000010E6
.L023A6ED8:
    .word 0x00001649

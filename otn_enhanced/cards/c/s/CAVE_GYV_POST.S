    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r4, #0x3c
    blt .L023A77A8
    ldr r0, .L023A77AC
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77B0
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77B4
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77B8
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77BC
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77C0
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77C4
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77C8
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77CC
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77D0
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77D4
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77D8
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77DC
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77E0
    cmp r5, r0
    beq .L023A779E
    ldr r0, .L023A77E4
    cmp r5, r0
    bne .L023A77A8
.L023A779E:
    adds r0, r6, #0x0
    adds r1, r5, #0x0
    adds r2, r7, #0x0
    bl 0x0224C6C0
.L023A77A8:
    pop {r3, r4, r5, r6, r7, pc}
    nop
.L023A77AC:
    .word 0x000017CD
.L023A77B0:
    .word 0x0000115F
.L023A77B4:
    .word 0x00001145
.L023A77B8:
    .word 0x00001125
.L023A77BC:
    .word 0x000010E6
.L023A77C0:
    .word 0x000013A3
.L023A77C4:
    .word 0x0000139A
.L023A77C8:
    .word 0x00001E04
.L023A77CC:
    .word 0x00000FC1
.L023A77D0:
    .word 0x00000FE6
.L023A77D4:
    .word 0x00000FD4
.L023A77D8:
    .word 0x00000FEB
.L023A77DC:
    .word 0x00001118
.L023A77E0:
    .word 0x000016DB
.L023A77E4:
    .word 0x00001649

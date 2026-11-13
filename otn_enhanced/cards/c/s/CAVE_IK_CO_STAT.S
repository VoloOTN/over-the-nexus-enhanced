    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r2, r3, r4, r6, r7, lr}
    ldr r0, [sp, #0x24]
    ldr r1, [sp, #0x28]
    ldr r3, .L023A9C80
    blx r3
    ldr r1, .L023A9C84
    cmp r0, r1
    beq .L023A9C66
    ldr r1, .L023A9C88
    cmp r0, r1
    bne .L023A9C7A
.L023A9C66:
    adds r0, r5, #0x0
    ldr r3, .L023A9C8C
    blx r3
    cmp r0, #0x17
    bge .L023A9C7A
    ldr r0, [sp, #0xc8]
    movs r1, #0x7d
    lsls r1, r1, #2
    adds r0, r0, r1
    str r0, [sp, #0xc8]
.L023A9C7A:
    adds r0, r5, #0x0
    ldr r1, .L023A9C90
    pop {r2, r3, r4, r6, r7, pc}
.L023A9C80:
    .word 0x021A36ED
.L023A9C84:
    .word 0x00001118
.L023A9C88:
    .word 0x000017EF
.L023A9C8C:
    .word 0x0202ABB9
.L023A9C90:
    .word 0x0226DFB0

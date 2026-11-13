    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023A9C24
    cmp r4, r1
    bne .L023A9C20
    ldr r1, [sp, #0x144]
    cmp r1, #0x0
    beq .L023A9C20
    push {r0, r2, r3, r4, r5, r6, r7, lr}
    ldr r0, [sp, #0xb8]
    ldr r1, .L023A9C28
    movs r2, #0x1
    movs r3, #0x0
    ldr r4, .L023A9C2C
    blx r4
    movs r1, #0x77
    lsls r1, r1, #6
    pop {r0, r2, r3, r4, r5, r6, r7, pc}
.L023A9C20:
    ldr r1, .L023A9C30
    bx r1
.L023A9C24:
    .word 0x00001118
.L023A9C28:
    .word 0x00007118
.L023A9C2C:
    .word 0x021D2585
.L023A9C30:
    .word 0x023A9531

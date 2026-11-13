    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, lr}
    adds r5, r0, #0x0
    adds r6, r1, #0x0
    ldrb r0, [r5, #0x2]
    movs r1, #0xb
    ldr r2, .L023A8124
    movs r3, #0x1
    ldr r4, .L023A8128
    blx r4
    cmp r0, #0x0
    bne .L023A8120
    adds r0, r5, #0x0
    adds r1, r6, #0x0
    ldr r4, .L023A812C
    blx r4
    pop {r4, r5, r6, pc}
.L023A8120:
    movs r0, #0x0
    pop {r4, r5, r6, pc}
.L023A8124:
    .word 0x00001E04
.L023A8128:
    .word 0x021A14E9
.L023A812C:
    .word 0x022043F5

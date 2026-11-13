    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, r7, lr}
    adds r4, r0, #0x0
    adds r5, r1, #0x0
    adds r6, r2, #0x0
    bl 0x0224829C
    adds r7, r0, #0x0
    cmp r7, #0x0
    beq .L023A1128
    adds r0, r5, #0x0
    adds r1, r6, #0x0
    bl 0x021A3320
    ldr r1, .L023A1134
    cmp r0, r1
    bne .L023A1128
    adds r0, r4, #0x0
    bl 0x02023DFC
    adds r7, r0, #0x0
.L023A1128:
    adds r0, r7, #0x0
    adds r1, r5, #0x0
    adds r2, r6, #0x0
    movs r3, #0x0
    pop {r4, r5, r6, r7, pc}
    movs r0, r0
.L023A1134:
    .word 0x0000106E

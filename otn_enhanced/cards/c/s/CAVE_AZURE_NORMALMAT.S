    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, r7, lr}
    movs r4, r1
    movs r5, r2
    movs r6, r3
    movs r7, r0
    bl 0x0224829C
    cmp r0, #0x0
    beq .L0239D01C
    ldr r3, .L0239D020
    cmp r7, r3
    bne .L0239D016
    movs r7, r0
    movs r0, r4
    movs r1, r5
    movs r2, r6
    bl 0x0219CAE4
    bl 0x0202ABF8
    cmp r0, #0x0
    beq .L0239D014
    cmp r0, #0xf
    beq .L0239D014
    movs r0, #0x0
    b .L0239D016
.L0239D014:
    movs r0, r7
.L0239D016:
    movs r1, r4
    movs r2, r5
    movs r3, r6
.L0239D01C:
    pop {r4, r5, r6, r7, pc}
    movs r0, r0
.L0239D020:
    .word 0x00001E9C

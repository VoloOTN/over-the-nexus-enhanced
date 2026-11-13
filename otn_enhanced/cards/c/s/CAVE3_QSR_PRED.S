    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r0, #0xb
    beq .L021F169E
    movs r5, #0x0
.L021F169E:
    ldr r3, .L021F16C0
    cmp r7, r3
    bne .L021F16B6
    ldr r3, .L021F16C4
    cmp r4, r3
    beq .L021F16BA
    movs r0, r4
    bl 0x0202ABF8
    subs r0, #0x11
    cmp r0, #0x2
    bhi .L021F16BA
.L021F16B6:
    ldr r3, .L021F16C8
    bx r3
.L021F16BA:
    movs r0, #0x0
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
    movs r0, r0
.L021F16C0:
    .word 0x0000211B
.L021F16C4:
    .word 0x00002346
.L021F16C8:
    .word 0x022482BD

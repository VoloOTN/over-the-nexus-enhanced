    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r0, #0x0
    bne .L0220A5A2
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L0220A5AC
    bl 0x021A1430
    cmp r0, #0x0
    beq .L0220A5A6
.L0220A5A2:
    adds r0, r4, #0x0
    pop {r3, r4, r5, r6, r7, pc}
.L0220A5A6:
    movs r0, #0x0
    bl 0x02212404
.L0220A5AC:
    .word 0x00003E51

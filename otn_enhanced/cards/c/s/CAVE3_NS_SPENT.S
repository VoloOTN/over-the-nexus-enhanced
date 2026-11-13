    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r0, #0x0
    bne .L0221D7E0
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L0221D7E4
    bl 0x021A1430
    cmp r0, #0x0
    bne .L0221D7E0
    movs r4, #0x0
.L0221D7E0:
    adds r0, r4, #0x0
    pop {r3, r4, r5, r6, r7, pc}
.L0221D7E4:
    .word 0x00000FFD

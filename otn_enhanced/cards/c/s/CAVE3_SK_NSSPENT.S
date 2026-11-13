    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r0, #0x0
    bne .L02212416
    adds r0, r5, #0x0
    movs r1, #0xb
    ldr r2, .L02212420
    bl 0x021A1430
    cmp r0, #0x0
    beq .L0221241A
.L02212416:
    adds r0, r4, #0x0
    pop {r3, r4, r5, r6, r7, pc}
.L0221241A:
    movs r0, #0x0
    bl 0x0221AE54
.L02212420:
    .word 0x00003E50

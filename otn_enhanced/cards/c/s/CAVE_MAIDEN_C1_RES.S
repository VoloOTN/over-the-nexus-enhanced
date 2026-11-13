    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, lr}
    adds r4, r0, #0x0
    adds r5, r1, #0x0
    ldrb r0, [r4, #0x2]
    ldrh r1, [r4, #0x0]
    movs r2, #0x1
    movs r3, #0x0
    ldr r6, .L0239CD3C
    blx r6
    adds r0, r4, #0x0
    adds r1, r5, #0x0
    ldr r6, .L0239CD40
    blx r6
    pop {r4, r5, r6, pc}
.L0239CD3C:
    .word 0x021D2585
.L0239CD40:
    .word 0x02206F41

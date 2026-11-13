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
    ldr r3, .L0221D968
    blx r3
    cmp r0, #0x0
    bne .L0221D962
    adds r0, r4, #0x0
    adds r1, r5, #0x0
    ldr r3, .L0221D96C
    blx r3
    pop {r4, r5, r6, pc}
.L0221D962:
    movs r0, #0x0
    pop {r4, r5, r6, pc}
    nop
.L0221D968:
    .word 0x021AE4AD
.L0221D96C:
    .word 0x0220731D

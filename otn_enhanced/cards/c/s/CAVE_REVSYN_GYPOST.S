    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    cmp r4, #0x3c
    bcc .L0239FC44
    ldr r0, .L0239FC48
    cmp r5, r0
    bne .L0239FC44
    adds r0, r6, #0x0
    adds r1, r5, #0x0
    adds r2, r7, #0x0
    bl 0x0224C6C0
.L0239FC44:
    pop {r3, r4, r5, r6, r7, pc}
    movs r0, r0
.L0239FC48:
    .word 0x00001649

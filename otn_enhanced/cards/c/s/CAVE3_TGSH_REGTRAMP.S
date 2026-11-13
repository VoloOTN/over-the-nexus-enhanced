    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, r7, lr}
    adds r7, r6, #0x0
    adds r6, r0, #0x0
    blx r2
    adds r4, r0, #0x0
    cmp r7, #0x0
    bne .L021F1E7C
    ldr r0, .L021F1E84
    ldr r0, [r0, #0x0]
    cmp r0, #0x0
    bne .L021F1E7C
    ldr r0, .L021F1E88
    ldr r0, [r0, #0x18]
    cmp r0, #0x0
    bne .L021F1E7C
    ldr r5, .L021F1E8C
.L021F1E6C:
    ldrh r1, [r5, #0x0]
    cmp r1, #0x0
    beq .L021F1E7C
    movs r0, #0x0
    ldr r2, .L021F1E90
    blx r2
    adds r5, #0x2
    b .L021F1E6C
.L021F1E7C:
    adds r0, r4, #0x0
    cmp r0, #0x0
    pop {r4, r5, r6, r7, pc}
    movs r0, r0
.L021F1E84:
    .word 0x0229DD94
.L021F1E88:
    .word 0x0229AB7C
.L021F1E8C:
    .word 0x0220A0D2
.L021F1E90:
    .word 0x02254221

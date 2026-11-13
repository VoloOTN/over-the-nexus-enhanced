    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021F1A08
    movs r2, #0x0
.L021F19EC:
    ldrh r3, [r1, #0x0]
    cmp r3, #0x0
    beq .L021F1A02
    cmp r3, r0
    beq .L021F19FC
    adds r1, #0x2
    adds r2, #0x1
    b .L021F19EC
.L021F19FC:
    adds r0, r2, #0x0
    cmp r0, #0x0
    bx lr
.L021F1A02:
    movs r0, #0x0
    subs r0, #0x1
    bx lr
.L021F1A08:
    .word 0x0220A368

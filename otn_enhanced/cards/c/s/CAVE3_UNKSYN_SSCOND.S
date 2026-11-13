    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, lr}
    adds r4, r0, #0x0
    movs r1, #0xb
    ldr r2, .L021E1C1C
    movs r3, #0x5
    bl 0x021A14E8
    cmp r0, #0x0
    bne .L021E1C16
    adds r0, r4, #0x0
    bl 0x021AD870
    cmp r0, #0x0
    beq .L021E1C16
    adds r0, r4, #0x0
    bl 0x021ACF68
    cmp r0, #0x0
    bne .L021E1C16
    movs r0, #0x1
    subs r0, r0, r4
    bl 0x021ACF68
    cmp r0, #0x0
    beq .L021E1C16
    movs r0, #0x1
    pop {r4, pc}
.L021E1C16:
    movs r0, #0x0
    pop {r4, pc}
    movs r0, r0
.L021E1C1C:
    .word 0x0000181C

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [sp, #0x4]
    cmp r0, #0xe
    bne .L023A1C58
    ldrh r0, [r7, #0x0]
    ldr r1, .L023A1C60
    cmp r0, r1
    bne .L023A1C58
    push {r4, r5, lr}
    ldr r2, [sp, #0x1c]
    push {r0}
    adds r0, r4, #0x0
    movs r1, #0x0
    movs r3, #0x10
    ldr r5, .L023A1C64
    blx r5
    pop {r0}
    ldr r0, .L023A1C68
    movs r1, #0x1
    strb r1, [r0, #0x0]
    movs r0, #0x1
    cmp r0, #0xf
    pop {r4, r5, pc}
.L023A1C58:
    ldr r0, [sp, #0x4]
    cmp r0, #0xf
    bx lr
    nop
.L023A1C60:
    .word 0x000021D5
.L023A1C64:
    .word 0x021D1DAD
.L023A1C68:
    .word 0x023A1CDC

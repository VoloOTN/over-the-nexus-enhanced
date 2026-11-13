    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, lr}
    adds r4, r0, #0x0
    bl 0x021D2BC8
    cmp r0, #0x0
    bne .L0239FD20
    ldrb r0, [r4, #0x2]
    ldr r1, .L0239FD24
    movs r2, #0x5
    movs r3, #0x0
    bl 0x021D2584
    adds r0, r4, #0x0
    bl 0x021EBA34
    pop {r4, pc}
.L0239FD20:
    movs r0, #0x1
    pop {r4, pc}
.L0239FD24:
    .word 0x00001649

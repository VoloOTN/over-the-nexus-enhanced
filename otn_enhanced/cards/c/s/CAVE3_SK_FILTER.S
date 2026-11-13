    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, lr}
    cmp r1, #0xb
    bne .L021F0FC6
    movs r3, #0x1
    ands r3, r0
    ldr r1, .L021F0FCC
    muls r3, r1
    ldr r1, .L021F0FD0
    adds r3, r1, r3
    lsls r1, r2, #2
    adds r3, r3, r1
    ldr r1, .L021F0FD4
    ldr r3, [r3, r1]
    lsls r0, r3, #18
    lsrs r0, r0, #18
    bl 0x020230D4
    cmp r0, #0x0
    beq .L021F0FC6
    movs r0, #0x10
    pop {r4, pc}
.L021F0FC6:
    movs r0, #0x0
    pop {r4, pc}
    nop
.L021F0FCC:
    .word 0x00000B3C
.L021F0FD0:
    .word 0x0229AC94
.L021F0FD4:
    .word 0x00000124

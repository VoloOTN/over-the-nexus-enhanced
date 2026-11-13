    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L021F107C
    cmp r0, r1
    beq .L021F107A
    push {r0, r2, r3, lr}
    bl 0x021F19E8
    lsrs r0, r0, #2
    bne .L021F1072
    movs r1, #0x0
    cmp r1, r1
    pop {r0, r2, r3, pc}
.L021F1072:
    ldr r0, [sp, #0x0]
    bl 0x021B57F0
    pop {r0, r2, r3, pc}
.L021F107A:
    bx lr
.L021F107C:
    .word 0x00001CF6

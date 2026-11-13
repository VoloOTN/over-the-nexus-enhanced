    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L0239FC70
    cmp r0, r1
    beq .L0239FC6A
    movs r0, #0x0
    pop {r3, r4, r5, pc}
.L0239FC6A:
    movs r0, #0x1
    pop {r3, r4, r5, pc}
    movs r0, r0
.L0239FC70:
    .word 0x00001649

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L0239D91C
    cmp r0, r3
    bne .L0239D916
    ldrb r3, [r5, #0x4]
    cmp r3, #0x8
    blt .L0239D916
    cmp r3, #0x9
    bgt .L0239D916
    movs r0, #0x1
    add sp, #0x4
    pop {r4, r5, r6, r7, pc}
.L0239D916:
    ldr r3, .L0239D920
    bx r3
    movs r0, r0
.L0239D91C:
    .word 0x000013E7
.L0239D920:
    .word 0x02022E15

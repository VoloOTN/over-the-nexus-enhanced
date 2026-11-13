    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L021F0670
    cmp r4, r3
    bne .L021F0666
    ldr r0, .L021F0674
    bx r0
.L021F0666:
    ldr r0, .L021F0678
    push {r0}
    ldr r3, .L021F067C
    cmp r4, r3
    pop {pc}
.L021F0670:
    .word 0x00001265
.L021F0674:
    .word 0x0224F669
.L021F0678:
    .word 0x0224F58D
.L021F067C:
    .word 0x00001C2C

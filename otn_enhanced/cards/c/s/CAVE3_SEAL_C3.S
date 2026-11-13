    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r0, r1, r2, lr}
    bl 0x021AC0C8
    cmp r0, #0x0
    bne .L021F6B54
    ldr r0, [sp, #0x0]
    ldr r1, .L021F6B58
    ldr r2, [sp, #0x8]
    bl 0x021AC0C8
.L021F6B54:
    add sp, #0xc
    pop {pc}
.L021F6B58:
    .word 0x000010F5

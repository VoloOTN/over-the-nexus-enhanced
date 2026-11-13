    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [sp, #0x8]
    ldr r1, .L021B2B28
    cmp r0, r1
    bne .L021B2B22
    movs r0, #0x0
    str r0, [sp, #0x4]
    str r0, [sp, #0x8]
    bl 0x021CC1CA
.L021B2B22:
    movs r0, #0x0
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
    movs r0, r0
.L021B2B28:
    .word 0x000010F5

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    subs r1, #0x66
    cmp r5, r1
    beq .L021F0698
    subs r1, #0x7a
    cmp r5, r1
    bne .L021F0698
    ldr r1, [sp, #0x34]
    subs r1, #0xb
    ldr r0, [sp, #0x10]
    subs r0, #0x1
    orrs r1, r0
    lsrs r1, r1, #31
.L021F0698:
    bx lr
    nop

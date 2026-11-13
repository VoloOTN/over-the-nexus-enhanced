    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    str r1, [sp, #0x8]
    push {r2}
    ldrh r1, [r4, #0x0]
    ldr r2, .L021F5754
    cmp r1, r2
    bne .L021F574C
    movs r1, #0xf
    b .L021F574E
.L021F574C:
    movs r1, #0xe
.L021F574E:
    pop {r2}
    bx lr
    nop
.L021F5754:
    .word 0x00001FFC

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [sp, #0xc]
    adds r2, #0x95
    .hword 0x4803    @ ldr r0, =pool 0x021B5930
    cmp r5, r0
    beq .L021B592C
    cmp r5, r2
    bx lr
.L021B592C:
    .hword 0x4801    @ ldr r0, =pool 0x021B5934
    bx r0
.L021B5930:
    .word 0x00001859
.L021B5934:
    .word 0x021D1527

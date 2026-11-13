    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r0, [sp, #0xc]
    .hword 0x4903    @ ldr r1, =pool 0x021B58F8
    cmp r0, r1
    bne .L021B58F2
    movs r0, #0xff
    pop {r3, r4, r5, pc}
.L021B58F2:
    .hword 0x4902    @ ldr r1, =pool 0x021B58FC
    cmp r0, r1
    bx lr
.L021B58F8:
    .word 0x000019B2
.L021B58FC:
    .word 0x00001D22

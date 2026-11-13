    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L02220B4C
    cmp r0, r3
    bne .L02220B46
    movs r0, #0x1
    bx lr
.L02220B46:
    ldr r3, .L02220B50
    bx r3
    nop
.L02220B4C:
    .word 0x00000FF4
.L02220B50:
    .word 0x02220B55
    .hword 0x4B03
    .hword 0x4298
    .hword 0xD101
    .hword 0x2001
    .hword 0x4770
    .hword 0x4B02
    .hword 0x4718
    .hword 0x46C0
.L02220B64:
    .word 0x0000115E
.L02220B68:
    .word 0x02220B6D
    .hword 0x4B03
    .hword 0x4298
    .hword 0xD101
    .hword 0x2001
    .hword 0x4770
    .hword 0x4B02
    .hword 0x4718
    .hword 0x46C0
.L02220B7C:
    .word 0x00000FEA
.L02220B80:
    .word 0x02220B85
    .hword 0x4B03
    .hword 0x4298
    .hword 0xD101
    .hword 0x2001
    .hword 0x4770
    .hword 0x4B02
    .hword 0x4718
    .hword 0x46C0
.L02220B94:
    .word 0x00001CC6
.L02220B98:
    .word 0x02237DA5

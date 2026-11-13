    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r3, .L02220BAC
    cmp r0, r3
    bne .L02220BA6
    movs r0, #0x1
    bx lr
.L02220BA6:
    ldr r3, .L02220BB0
    bx r3
    nop
.L02220BAC:
    .word 0x00000FF4
.L02220BB0:
    .word 0x02220BB5
    .hword 0x4B03
    .hword 0x4298
    .hword 0xD101
    .hword 0x2001
    .hword 0x4770
    .hword 0x4B02
    .hword 0x4718
    .hword 0x46C0
.L02220BC4:
    .word 0x0000115E
.L02220BC8:
    .word 0x021FADB9

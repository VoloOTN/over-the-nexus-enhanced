    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L022234D8
    cmp r0, r1
    bne .L022234CC
    movs r7, #0x2
    ldr r1, .L022234DC
    bx r1
.L022234CC:
    ldr r2, .L022234E0
    push {r2}
    ldr r1, .L022234E4
    cmp r0, r1
    pop {pc}
    nop
.L022234D8:
    .word 0x00001265
.L022234DC:
    .word 0x02262A53
.L022234E0:
    .word 0x02262967
.L022234E4:
    .word 0x00001C81
    .hword 0x4B03
    .hword 0x4298
    .hword 0xD001
    .hword 0x4B03
    .hword 0x4718
    .hword 0x2001
    .hword 0x4770
    .hword 0x46C0
.L022234F8:
    .word 0x00001265
.L022234FC:
    .word 0x02022E15

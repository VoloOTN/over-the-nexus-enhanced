    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    lsrs r5, r7, #31
    lsrs r0, r1, #31
    subs r7, r2, #0x3
    movs r0, r0

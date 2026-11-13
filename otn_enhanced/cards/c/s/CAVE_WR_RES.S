    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, lr}
    adds r4, r0, #0x0
    ldrb r0, [r4, #0x2]
    ldr r1, .L023A53AC
    movs r2, #0x1
    movs r3, #0x0
    ldr r5, .L023A53B0
    blx r5
    adds r0, r4, #0x0
    ldr r5, .L023A53B4
    blx r5
    movs r0, #0x0
    pop {r4, r5, r6, pc}
    nop
.L023A53AC:
    .word 0x0000190B
.L023A53B0:
    .word 0x021D2585
.L023A53B4:
    .word 0x022048FD

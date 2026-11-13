    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023A9598
    cmp r4, r1
    bne .L023A9594
    ldr r1, [sp, #0x44]
    cmp r1, #0x0
    beq .L023A9594
    ldr r1, [sp, #0x90]
    cmp r1, #0x0
    beq .L023A9594
    push {r0, r2, r3, r4, r5, r6, r7, lr}
    ldr r7, [sp, #0xb8]
    ldr r6, [sp, #0xc0]
    lsls r6, r6, #8
    orrs r6, r7
    movs r4, #0x0
.L023A954E:
    movs r5, #0x5
.L023A9550:
    adds r0, r4, #0x0
    adds r1, r5, #0x0
    ldr r2, .L023A959C
    blx r2
    cmp r0, #0x0
    beq .L023A9568
    adds r0, r4, #0x0
    adds r1, r5, #0x0
    ldr r2, .L023A95A0
    blx r2
    cmp r0, r6
    beq .L023A9582
.L023A9568:
    adds r5, #0x1
    cmp r5, #0x9
    ble .L023A9550
    adds r4, #0x1
    cmp r4, #0x1
    ble .L023A954E
    adds r0, r7, #0x0
    movs r1, #0xb
    ldr r2, .L023A95A4
    movs r3, #0x0
    ldr r4, .L023A95A8
    blx r4
    b .L023A958E
.L023A9582:
    adds r0, r7, #0x0
    ldr r1, .L023A95A4
    movs r2, #0x1
    movs r3, #0x0
    ldr r4, .L023A95AC
    blx r4
.L023A958E:
    movs r1, #0x77
    lsls r1, r1, #6
    pop {r0, r2, r3, r4, r5, r6, r7, pc}
.L023A9594:
    ldr r1, .L023A95B0
    bx r1
.L023A9598:
    .word 0x0000160B
.L023A959C:
    .word 0x021A36ED
.L023A95A0:
    .word 0x021A0DF9
.L023A95A4:
    .word 0x0000760B
.L023A95A8:
    .word 0x021C4975
.L023A95AC:
    .word 0x021D2585
.L023A95B0:
    .word 0x021FAC79

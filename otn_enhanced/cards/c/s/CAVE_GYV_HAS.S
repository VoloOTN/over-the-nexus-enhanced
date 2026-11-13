    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r1, .L023A7864
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7868
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A786C
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7870
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7874
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7878
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A787C
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7880
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7884
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7888
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A788C
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7890
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7894
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A7898
    cmp r0, r1
    beq .L023A785E
    ldr r1, .L023A789C
    cmp r0, r1
    beq .L023A785E
    movs r0, #0x0
    pop {r3, r4, r5, pc}
.L023A785E:
    movs r0, #0x1
    pop {r3, r4, r5, pc}
    nop
.L023A7864:
    .word 0x000017CD
.L023A7868:
    .word 0x0000115F
.L023A786C:
    .word 0x00001145
.L023A7870:
    .word 0x00001125
.L023A7874:
    .word 0x000010E6
.L023A7878:
    .word 0x000013A3
.L023A787C:
    .word 0x0000139A
.L023A7880:
    .word 0x00001E04
.L023A7884:
    .word 0x00000FC1
.L023A7888:
    .word 0x00000FE6
.L023A788C:
    .word 0x00000FD4
.L023A7890:
    .word 0x00000FEB
.L023A7894:
    .word 0x00001118
.L023A7898:
    .word 0x000016DB
.L023A789C:
    .word 0x00001649

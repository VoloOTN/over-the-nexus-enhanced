    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r2, .L0225F260
    cmp r0, r2
    beq .L0225F256
    ldr r2, .L0225F264
    cmp r0, r2
    beq .L0225F25A
    ldr r2, .L0225F268
    cmp r0, r2
    beq .L0225F25A
    ldr r2, .L0225F26C
    bx r2
.L0225F256:
    ldr r2, .L0225F270
    bx r2
.L0225F25A:
    ldr r2, .L0225F274
    bx r2
    nop
.L0225F260:
    .word 0x00001466
.L0225F264:
    .word 0x00000FB1
.L0225F268:
    .word 0x00001646
.L0225F26C:
    .word 0x02262AAF
.L0225F270:
    .word 0x02262A53
.L0225F274:
    .word 0x02262A5B
    .hword 0x4A06
    .hword 0x4290
    .hword 0xD007
    .hword 0x4A06
    .hword 0x4290
    .hword 0xD004
    .hword 0x4A05
    .hword 0xB404
    .hword 0x4A05
    .hword 0x4290
    .hword 0xBD00
    .hword 0x4A05
    .hword 0x4710
    .hword 0x46C0
.L0225F294:
    .word 0x00000FB1
.L0225F298:
    .word 0x00001646
.L0225F29C:
    .word 0x02262C2B
.L0225F2A0:
    .word 0x00001BC8
.L0225F2A4:
    .word 0x02262C8D

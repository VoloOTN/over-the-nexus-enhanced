    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    ldr r6, .L0239E81C
    ldr r0, [r6, #0x0]
    cmp r0, r4
    beq .L0239E7EC
    ldrb r0, [r4, #0x2]
    ldrb r1, [r4, #0x6]
    eors r0, r1
    ldr r1, .L0239E820
    muls r1, r0
    ldr r2, .L0239E824
    adds r1, r1, r2
    ldr r2, [r1, #0x14]
    cmp r2, #0x0
    beq .L0239E816
    subs r2, #0x1
    lsls r2, r2, #2
    ldr r3, .L0239E828
    adds r1, r1, r3
    ldr r0, [r1, r2]
    ldr r2, .L0239E82C
    ands r0, r2
    bl 0x0202ABD8
    cmp r0, #0x0
    beq .L0239E816
    adds r7, r0, #0x0
    ldr r6, .L0239E81C
    str r7, [r6, #0x4]
    ldrb r0, [r4, #0x2]
    ldrb r1, [r4, #0x3]
    bl 0x021B8064
    movs r5, #0x5
    cmp r0, r7
    bls .L0239E7CA
    movs r0, #0x2
    orrs r5, r0
.L0239E7CA:
    sub sp, #0x10
    ldr r0, .L0239E830
    str r0, [sp, #0x0]
    movs r0, #0x0
    str r0, [sp, #0x4]
    str r5, [sp, #0x8]
    adds r0, r4, #0x0
    ldr r1, .L0239E834
    ldr r2, .L0239E838
    ldr r3, .L0239E83C
    bl 0x0219ABB4
    add sp, #0x10
    ldr r6, .L0239E81C
    str r4, [r6, #0x0]
    movs r0, #0x7c
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
.L0239E7EC:
    movs r0, #0x0
    str r0, [r6, #0x0]
    ldr r7, [r6, #0x4]
    ldr r0, .L0239E840
    ldr r5, [r0, #0x34]
    adds r0, r5, #0x1
    strh r0, [r4, #0x18]
    cmp r5, #0x1
    bne .L0239E800
    negs r7, r7
.L0239E800:
    sub sp, #0x10
    lsls r0, r7, #16
    lsrs r0, r0, #16
    str r0, [sp, #0x0]
    ldrb r0, [r4, #0x2]
    ldrb r1, [r4, #0x3]
    ldr r2, .L0239E844
    movs r3, #0x3
    bl 0x021C479C
    add sp, #0x10
.L0239E816:
    movs r0, #0x64
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
    movs r0, r0
.L0239E81C:
    .word 0x0239E880
.L0239E820:
    .word 0x00000B3C
.L0239E824:
    .word 0x0229AC94
.L0239E828:
    .word 0x0000055C
.L0239E82C:
    .word 0x00003FFF
.L0239E830:
    .word 0x000001AC
.L0239E834:
    .word 0x00000103
.L0239E838:
    .word 0x0000016E
.L0239E83C:
    .word 0x0000016F
.L0239E840:
    .word 0x0229DD94
.L0239E844:
    .word 0x000022EB

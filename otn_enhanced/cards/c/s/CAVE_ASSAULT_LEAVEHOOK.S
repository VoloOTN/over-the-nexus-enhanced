    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r1, r2, r3, r4, r5, r6, r7, lr}
    ldr r0, [sp, #0x4c]
    cmp r0, #0x0
    beq .L0239F3BE
    ldr r0, [sp, #0xb4]
    cmp r0, #0x0
    beq .L0239F3BE
    ldr r0, [sp, #0xb8]
    cmp r0, r6
    bne .L0239F3BE
    ldr r0, [sp, #0x2c]
    movs r1, #0x1
    lsls r1, r1, #12
    tst r0, r1
    bne .L0239F388
    ldr r0, [sp, #0x220]
    lsls r0, r0, #9
    lsrs r0, r0, #28
    cmp r0, #0xf
    bne .L0239F3BE
.L0239F388:
    adds r0, r4, #0x0
    bl 0x0202ABB8
    cmp r0, #0x1
    bne .L0239F3BE
    adds r0, r4, #0x0
    bl 0x02023050
    cmp r0, #0x0
    beq .L0239F3BE
    ldr r1, [sp, #0xbc]
    movs r0, #0x40
    lsls r0, r0, #8
    orrs r1, r0
    adds r0, r6, #0x0
    movs r2, #0x1
    movs r3, #0x0
    bl 0x021D2584
    adds r0, r6, #0x0
    ldr r1, .L0239F3C4
    ldr r2, [sp, #0x3c]
    ldr r3, [sp, #0x220]
    lsrs r3, r3, #9
    lsls r3, r3, #9
    bl 0x021D3648
.L0239F3BE:
    ldr r0, [sp, #0x64]
    cmp r0, #0x0
    pop {r1, r2, r3, r4, r5, r6, r7, pc}
.L0239F3C4:
    .word 0x000013AE

    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, r5, r6, r7, lr}
    ldr r4, .L021F1210
    ldrh r1, [r4, #0xc]
    movs r0, #0x1
    ands r0, r1
    ldr r1, .L021F1214
    adds r2, r6, #0x0
    adds r3, r7, #0x0
    bl 0x021D36C0
    ldr r0, .L021F1218
    ldr r1, [r0, #0x78]
    pop {r4, r5, r6, r7, pc}
    movs r0, r0
.L021F1210:
    .word 0x02298A28
.L021F1214:
    .word 0x00000FA9
.L021F1218:
    .word 0x0229C294

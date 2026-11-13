    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r4, lr}
    adds r4, r0, #0x0
    ldr r2, .L021F19E4
    ldr r2, [r2, #0x70]
    cmp r2, #0x78
    beq .L021F19C8
    bl 0x02204C7C
    cmp r0, #0x0
    bne .L021F19C6
    movs r0, #0x78
.L021F19C6:
    pop {r4, pc}
.L021F19C8:
    ldrb r0, [r4, #0xb]
    cmp r0, #0x0
    bne .L021F19E0
    ldrb r0, [r4, #0x2]
    ldrh r1, [r4, #0x0]
    movs r2, #0x5
    movs r3, #0x0
    bl 0x021D2584
    adds r0, r4, #0x0
    bl 0x022048FC
.L021F19E0:
    movs r0, #0x0
    pop {r4, pc}
.L021F19E4:
    .word 0x0229AAFC

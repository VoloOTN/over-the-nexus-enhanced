    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r3, r4, r5, r6, r7, lr}
    adds r5, r0, #0x0
    adds r4, r1, #0x0
    beq .L0221B88E
    ldrb r0, [r4, #0x3]
    cmp r0, #0xa
    bgt .L0221B88E
    ldrb r0, [r4, #0x5]
    cmp r0, #0x0
    bne .L0221B88E
    adds r0, r4, #0x0
    movs r1, #0x1
    ldr r7, .L0221B894
    blx r7
    cmp r0, #0x0
    bne .L0221B88E
    ldrb r1, [r4, #0x2]
    ldrb r0, [r4, #0x6]
    adds r2, r1, #0x0
    eors r2, r0
    ldrb r1, [r5, #0x2]
    ldrb r0, [r5, #0x6]
    eors r0, r1
    cmp r2, r0
    beq .L0221B88E
    ldrh r0, [r4, #0x0]
    ldr r7, .L0221B898
    blx r7
    cmp r0, #0x0
    beq .L0221B88E
    adds r0, r5, #0x0
    adds r1, r4, #0x0
    ldr r7, .L0221B89C
    blx r7
    pop {r3, r4, r5, r6, r7, pc}
.L0221B88E:
    movs r0, #0x0
    pop {r3, r4, r5, r6, r7, pc}
    nop
.L0221B894:
    .word 0x021AB90D
.L0221B898:
    .word 0x02022FC9
.L0221B89C:
    .word 0x021F06E9

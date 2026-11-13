    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {lr}
    ldr r0, .L022232C4
    ldr r0, [r0, #0x58]
    lsls r0, r0, #25
    lsrs r0, r0, #24
    ldr r1, .L022232C8
    ldrh r0, [r1, r0]
    lsls r0, r0, #3
    ldr r1, .L022232CC
    ldr r0, [r1, r0]
    lsls r0, r0, #18
    lsrs r0, r0, #18
    ldr r1, .L022232D0
    cmp r0, r1
    ldr r1, [r6, #0x70]
    ldr r0, [r6, #0x7c]
    bne .L022232C0
    cmp r0, #0x3
    bcs .L022232C0
    movs r1, #0x3
.L022232C0:
    pop {pc}
    movs r0, r0
.L022232C4:
    .word 0x0229A9FC
.L022232C8:
    .word 0x0229AA58
.L022232CC:
    .word 0x0229C33C
.L022232D0:
    .word 0x0000106C

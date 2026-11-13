    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    push {r0, lr}
    ldrh r0, [r0, #0x0]
    bl 0x021F19E8
    bmi .L0221AC18
    pop {r0}
    movs r0, #0x0
    pop {pc}
.L0221AC18:
    pop {r0}
    bl 0x021EE0E0
    pop {pc}

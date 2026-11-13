    .syntax unified
    .thumb
    .section .text.entry
    .global entry
    .thumb_func
entry:
    pop {r0, r1, r2, r3}
    bl 0x02022E44
    pop {pc}

/* Return of the Monarchs: the 4-byte BL hook over `cmp r5,#0 ; beq 0x02265CD0` @0x02265C70 inside the summon-event dispatcher 0x02265768.
 * r4 = summon descriptor, r5 = the lists' verdict, r6 = event code (7 = Normal).  Hit -> return to LR (0x02265C74, the posting path);
 * miss -> LR + 0x5C (0x02265CD0, no event).  Build with -DTEST=<R_TEST stub address | 1>. */
    .syntax unified
    .thumb
    .section .text.entry,"ax"
    .global entry
    .thumb_func
entry:
    push {lr}
    cmp r5, #0
    bne hit                     @ a native list already matched: keep its verdict
    cmp r6, #7
    bne miss
    ldrh r0, [r4, #0x2c]
    cmp r0, #0
    beq miss                    @ no Tribute paid: not a Tribute Summon
    adds r0, r4, #0
    ldr r3, =TEST
    blx r3
    cmp r0, #0
    beq miss
    movs r5, #1
hit:
    pop {r1}
    bx r1
miss:
    pop {r1}
    adds r1, #0x5C
    bx r1
    .ltorg

    .syntax unified
    .thumb
    .include "shim.S"
    .section .text.entry
    .global entry
    FRONT_SHIM entry, sk_nsmatch, 0x021FAE59, r1
    .ltorg

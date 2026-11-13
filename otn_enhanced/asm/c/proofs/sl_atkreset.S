    .syntax unified
    .thumb
    .include "shim.S"
    .section .text.entry
    .global entry
    SPLICE_SHIM entry, sl_atkreset

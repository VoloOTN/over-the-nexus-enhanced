ENTRY(rig_boot)
SECTIONS
{
    . = RIG_BASE;
    .text : { *(.text*) }
    .data : { *(.rodata*) *(.data*) *(.bss*) *(COMMON) . = ALIGN(4); }
    /DISCARD/ : { *(.ARM.*) *(.comment) *(.note*) }
}

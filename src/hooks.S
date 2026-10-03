/* Entry stubs: save every volatile register, call the C hook, restore, then
 * run the instruction the Gecko/DOL hook replaced.  The last word is the slot
 * the hook installer turns into the branch back. */
    .macro SAVE
    stwu    1, -0xA0(1)
    stw     0, 0x0c(1)
    stmw    3, 0x10(1)          /* r3..r31 */
    mflr    0
    stw     0, 0x88(1)
    mfcr    0
    stw     0, 0x8c(1)
    mfctr   0
    stw     0, 0x90(1)
    mfxer   0
    stw     0, 0x94(1)
    .endm

    .macro RESTORE_ALL          /* everything but r0 */
    lwz     0, 0x94(1)
    mtxer   0
    lwz     0, 0x90(1)
    mtctr   0
    lwz     0, 0x8c(1)
    mtcr    0
    lwz     0, 0x88(1)
    mtlr    0
    lmw     3, 0x10(1)
    .endm

    .section .gcstart, "ax"
    b       _entry

    .section .gctail, "ax"
    .globl _entry
_entry:
#if defined(HOOK_SAMPLE)
    # KPADiRead before the sample-count check: r21 = the channel's KPAD block, r25 = channel
    SAVE
    mr      3, 21
    mr      4, 25
    bl      gc_sample
    RESTORE_ALL
    lwz     0, 0x0c(1)
    addi    1, 1, 0xA0
    lbz     0, 379(21)          # original instruction
#elif defined(HOOK_FRAME)
    # the game's controller manager, once a frame: r3..r8 are its arguments
    SAVE
    bl      gc_frame
    RESTORE_ALL
    lwz     0, 0x0c(1)
    addi    1, 1, 0xA0
    mflr    0                   # original instruction
#elif defined(HOOK_PROBE)
    # WPADProbe(chan, &type)
    SAVE
    bl      gc_probe
    stw     3, 0x08(1)
    RESTORE_ALL
    lwz     0, 0x08(1)
    addi    1, 1, 0xA0
    cmpwi   0, 0
    beq     1f
    li      3, 0
    blr
1:  stwu    1, -16(1)           # original instruction
#endif
    nop

"""Where the hook trampolines live in the injected low-memory section.

Every patch is a set of hooks: one instruction in the game is replaced by a
branch to a small self-contained routine that runs the displaced instruction
and branches back.  A Gecko code handler stores those routines itself (C2
codes); the patched DOL and the Riivolution patch need somewhere to put them,
so the patcher adds one text section at CAVE_BASE.

0x80001800-0x80003000 is the Wii's boot-time scratch area, which this game
never touches (the first 0x20 bytes are skipped: the word at 0x80001800 is
overwritten by the OS early on).  Each feature gets a fixed window so the
patches can be combined freely.  The GameCube controller hooks keep a few bytes
of state in a zeroed gap of the game's own first text section (STATE).
"""
CAVE_BASE = 0x80001820
CAVE_LIMIT = 0x80003000

CC_BASE = 0x80001820          # Classic Controller hook trampolines
CC_END = 0x80001C00
GC_BASE = 0x80001C00          # GameCube controller hook trampolines
GC_END = 0x80003000

WINDOWS = {'cc': (CC_BASE, CC_END), 'gc': (GC_BASE, GC_END)}

STATE = 0x80005D40            # zero in the retail DOL (0x80005AB4-0x80005F80 is padding)

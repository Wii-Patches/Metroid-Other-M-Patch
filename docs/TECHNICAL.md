# Technical notes

How the two patches work, where they hook, and how one set of data becomes a
patched `main.dol`, a Gecko code list and a Riivolution patch. For installing
and playing, see the [README](../README.md).

All five retail discs (USA Rev 0/1, Europe Rev 0/1, Japan) carry a
**byte-identical `main.dol`** (2,395,904 bytes), so every address here is valid for every release.

## One data set, three outputs

Every patch is a list of operations on `main.dol`:

| Operation | Static (`main.dol`) | Gecko | Riivolution |
| --- | --- | --- | --- |
| **Patch** — overwrite bytes in place | write them | `04` / `06` code | `<memory>` |
| **Hook** — replace one instruction with a branch to a routine that runs the displaced instruction and branches back | branch + trampoline in the injected section | `C2` code | `<memory>` (branch + trampoline) |

`tools/prebuilt/<feature>.json` holds those operations, including the retail
bytes expected at every site. `tools/ops.py` turns them into each format,
`tools/patcher.py` applies them (refusing a `main.dol` whose sites do not match),
and `tools/build.py` writes `codes/` and `riivolution/`. `tools/check.py` fails if
the committed files drift from the data (it also enforces the Gecko size budget
below); `tools/verify.py` applies the patches to a real `main.dol`.

Hooks are self-contained: a routine carries everything it needs and calls game
code through absolute addresses. The static build parks the trampolines in one new
text section at `0x80001820` (the Wii's boot-time scratch area, which this game
never touches). The GameCube hooks keep a few bytes of state at `0x80005D40`,
inside zero padding in the game's first text section.

**Dolphin's Gecko handler has room for about 3.2 KB of code** (`0x80002340`–
`0x80003000`). Past that, Dolphin silently drops whole codes, which is how the
first build lost every GameCube hook. `tools/check.py` keeps the list under that.

## Classic Controller

Vague Rant's published codes (`src/cc/other_m.txt`, unchanged). They patch the KPAD
library so a Classic Controller looks like the Wii Remote and Nunchuk: the sticks
are written where the game reads the Nunchuk stick and the IR pointer, and
`read_kpad_button` rewrites the Classic buttons into Wii Remote bits. Sites:

| Address | What |
| --- | --- |
| `0x800F73A0` | `read_kpad_button`: button injector |
| `0x800F73F8` | button edge detection |
| `0x800F797C` | accept a Classic Controller where a Nunchuk was required |
| `0x800F8AC0` | `calc_dpd_variable`: stick drives the pointer |
| `0x800F92DC`, `0x800F93B8`, `0x800F9470` | `read_kpad_ext`: stick redirection |

## GameCube controller

The game links the SI library but **not PAD** (no `RVL_SDK - PAD` string), so
nothing polls the GameCube port, and a game with no Wii Remote has no KPAD sample
for the Classic Controller code to read. `src/gcpad.c` fixes both and then lets
Vague Rant's code treat the pad as a Classic Controller. The approach comes from
Barrel Blast Patch and City Folk Patch.

| Hook | Site | Job |
| --- | --- | --- |
| `FRAME` | `0x8017C8F0`, the game's controller manager (once a frame) | drive the SI auto-poller; tell the game a controller connected or left |
| `SAMPLE` | `0x800FA504`, `KPADRead`'s "any samples queued?" check | write the pad into KPAD's sample ring as a Classic Controller |
| `PROBE` | `0x80123770`, `WPADProbe` entry | report "Classic Controller on channel 0" while a pad is plugged in |

**Why `FRAME` exists.** An earlier design polled from `KPADRead` and
`WPADProbe`, as City Folk does. Here that deadlocks: the game only calls those
once its own code has seen a *connect* event for the channel, and with no Wii
Remote that event never fires, so nothing polls, so no pad is ever seen. The
controller manager at `0x8017C8F0` runs every frame regardless.

**The connect event.** The game's "connected" flag is set from its KPAD connect
callback (`0x8013FB60`, result `0` = connected, `-1` = gone), which KPAD's handler
(`0x800FAFF0`) calls when WPAD reports a connection. `FRAME` calls that handler
itself, through the pointer WPAD keeps in the channel block (`+0x8E8`), when a pad
appears on a channel whose WPAD status is still "no controller" (`-1`), and again
with `-1` when it goes away. A real remote on the channel is left alone. (`+0x8EC` is the
*sampling* callback; calling it by mistake wrote a stray sample and changed nothing else.)

**SI polling** is Barrel Blast's: write the poll command (`0x00400300`) to the port,
acknowledge the error bits and latch it through `SISR`, set the enable bits in `SIPOLL`
and in the SDK's shadow copy that `SISetXY` rewrites every retrace, and handle unplug
(`NOREP`) and a wedged busy flag. Addresses for this game: SI type cache
`0x8023F648`, busy flag `0x8023F630`, `SIPOLL` shadow `0x8023F634`, `SIGetType`
`0x80119850`, `OSDisableInterrupts`/`OSRestoreInterrupts` `0x8010F160`/`0x8010F1A0`.
Use the Wii's SI base `0xCD006400`, not `0xCC...`.

**The sample.** `KPADRead` keeps the WPAD samples waiting to be read in the channel block
(`0x802DBEC0` + `0x688` per channel): a ring of 16 slots of `0x42` bytes at `+0x180`,
next slot to write at `+0x17A`, unread count at `+0x17B`. (The game calls `KPADInit`, so
the optional extra buffer is unused.) A Classic Controller sample sets, in the slot:

| Offset | Value |
| --- | --- |
| `+0x28` | `2`, extension = Classic Controller |
| `+0x29` | `0`, no extension error |
| `+0x2A` (u16) | Classic button bits |
| `+0x2C/+0x2E`, `+0x30/+0x32` (s16) | left / right stick, `(byte − 128) × 3`; the game clamps to ±1 itself |
| `+0x34` | `180` while L is held |
| `+0x40` | `8`, classic + accelerometer + pointer data (KPAD accepts 6–8 for a Classic Controller) |

Two samples are queued per frame, the older with the previous frame's buttons, because
the game's controller class reads sticks from the second status entry. With real samples
queued, a bare Wii Remote's slots get the pad as their extension; a real Nunchuk or Classic
Controller is never overridden.

## How it was tested

Dolphin, USA Rev 0, no Wii Remote, GameCube port 1 set to a standard controller, GDB stub
reading the KPAD block. The `FRAME` hook runs about once per frame; the game leaves
its "Communications with the Wii Remote have been interrupted" screen and reaches
"Hold the Wii Remote in a horizontal position". Pad input was fed through a debug
build (`DEBUG_FEED`, response written to the state area over the GDB stub) because
Dolphin's pipe input device did not deliver presses; the SI path itself only proved
detection. Result in the game's KPAD block: A → `0x0800`, B → `0x0100`, Y → `0x0200`,
Start → `0x0010`, control stick to ±1.00, C-stick to ±1.00. `tools/dev/` has the harness.
Nothing here has been run on a console.

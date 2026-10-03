#!/usr/bin/env python3
"""Regenerate tools/prebuilt/*.json from src/ (needs devkitPPC and a retail main.dol).

    OTHERM_DOL=/path/to/main.dol  python3 tools/gen_prebuilt.py

The JSON is what the patcher ships and reads; end users need neither devkitPPC
nor any game file.  All releases share one main.dol, so one dump will do.

Classic Controller: Vague Rant's published Gecko codes (src/cc/other_m.txt),
unchanged.  GameCube controller: src/gcpad.c, compiled once per hook.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
sys.path.insert(0, HERE)
from dol import Dol
from features import PREBUILT, dump
from layout import CC_BASE, CC_END, GC_BASE, GC_END, STATE
from ops import Feature, Hook

DEVKIT = os.environ.get('DEVKITPPC', '/opt/devkitpro/devkitPPC')
CC = DEVKIT + '/bin/powerpc-eabi-'

# addresses in the retail main.dol that the GameCube hooks use
SYMS = {
    'STATE': STATE,
    'SI_TYPES': 0x8023F648,         # SI's per-port device type cache
    'SI_BUSY': 0x8023F630,          # SI's "transfer in progress" word (-1 = idle)
    'SI_SHADOW': 0x8023F634,        # SI's copy of SIPOLL, rewritten to the register on every retrace
    'FN_SIGETTYPE': 0x80119850,
    'FN_OSDISABLE': 0x8010F160,
    'FN_OSRESTORE': 0x8010F1A0,
    'WPAD_TBL': 0x802EC810,         # table of per-channel WPAD control blocks
}
KPAD_SAMPLE = 0x800FA504            # KPADiRead: lbz r0,379(r21), "any samples queued?"
CTRL_FRAME = 0x8017C8F0             # the game's controller manager: mflr r0
WPAD_PROBE = 0x80123770             # WPADProbe: stwu r1,-16(r1)
GC_HOOKS = (('FRAME', CTRL_FRAME, 0x7C0802A6), ('SAMPLE', KPAD_SAMPLE, 0x8815017B), ('PROBE', WPAD_PROBE, 0x9421FFF0))


def parse_gecko(path):
    lines = [l.split() for l in open(path).read().splitlines()[1:] if l.strip()]
    ops, i = [], 0
    while i < len(lines):
        head = lines[i]
        if not head[0].startswith('C2'):
            raise SystemExit('unsupported code line %r' % head)
        n = int(head[1], 16)
        words = []
        for l in lines[i + 1:i + 1 + n]:
            words += [int(x, 16) for x in l]
        ops.append((0x80000000 | (int(head[0], 16) & 0x01FFFFFF), words))
        i += 1 + n
    return ops


def word(dol, va):
    return struct.unpack('>I', dol.read(va, 4))[0]


def build_cc(dol):
    ops, cur = [], CC_BASE
    for site, words in parse_gecko(os.path.join(SRC, 'cc', 'other_m.txt')):
        assert words[-1] == 0
        ops.append(Hook(site, word(dol, site), words, cur, note='Vague Rant: Classic Controller'))
        cur += len(words) * 4
    if cur > CC_END:
        raise SystemExit('cc code overflows its window: 0x%X > 0x%X' % (cur, CC_END))
    return Feature('cc', 'Classic Controller', 'all', ops)


def compile_hook(name):
    tmp = tempfile.mkdtemp(prefix='gcpad')
    defs = ['-D%s=0x%08Xu' % kv for kv in SYMS.items()] + ['-DHOOK_' + name]
    for flag in ('DEBUG_FEED', 'DEBUG_COUNT'):
        if os.environ.get(flag):
            defs.append('-D' + flag)
    cflags = ['-O2', '-fno-unroll-loops', '-mbig-endian', '-msoft-float', '-msdata=none', '-ffreestanding', '-fno-pic',
              '-fno-asynchronous-unwind-tables', '-fno-stack-protector', '-nostdlib', '-Wall']
    subprocess.check_call([CC + 'gcc'] + cflags + defs + ['-c', SRC + '/gcpad.c', '-o', tmp + '/g.o'])
    subprocess.check_call([CC + 'gcc', '-mbig-endian', '-c', '-x', 'assembler-with-cpp'] + defs +
                          [SRC + '/hooks.S', '-o', tmp + '/h.o'])
    subprocess.check_call([CC + 'ld', '-T', SRC + '/link.ld', '-o', tmp + '/b.elf', tmp + '/h.o', tmp + '/g.o'])
    subprocess.check_call([CC + 'objcopy', '-O', 'binary', tmp + '/b.elf', tmp + '/b.bin'])
    b = open(tmp + '/b.bin', 'rb').read()
    return list(struct.unpack('>%dI' % (len(b) // 4), b))


def build_gc(dol):
    ops, cur = [], GC_BASE
    for name, site, orig in GC_HOOKS:
        if word(dol, site) != orig:
            raise SystemExit('%s: 0x%08X holds 0x%08X, expected 0x%08X' % (name, site, word(dol, site), orig))
        w = compile_hook(name)
        assert w[-1] == 0x60000000      # the slot the installer turns into the branch back
        w[-1] = 0
        if len(w) % 2:
            w.insert(len(w) - 1, 0x60000000)
        note = {'FRAME': 'controller manager: drive the SI auto-poller for the GameCube port',
                'SAMPLE': 'KPADRead: queue the GameCube pad as a Classic Controller sample',
                'PROBE': 'WPADProbe: drive the SI poller; report a Classic Controller while a GameCube pad is plugged in'}[name]
        ops.append(Hook(site, orig, w, cur, note=note))
        cur += len(w) * 4
    if cur > GC_END:
        raise SystemExit('gc code overflows its window: 0x%X > 0x%X' % (cur, GC_END))
    if any(dol.read(STATE, 0x80)):
        raise SystemExit('the state area at 0x%08X is not zero in this DOL' % STATE)
    return Feature('gc', 'GameCube controller', 'all', ops)


def main():
    path = os.environ.get('OTHERM_DOL') or os.path.join(HERE, '..', 'work', 'dols', 'USA.dol')
    dol = Dol(path)
    os.makedirs(PREBUILT, exist_ok=True)
    for name, fn in (('cc', build_cc), ('gc', build_gc)):
        f = fn(dol)
        out = os.path.join(PREBUILT, name + '.json')
        with open(out, 'w') as fh:
            json.dump(dump(f), fh, indent=1)
            fh.write('\n')
        print('%-3s %d ops, %d bytes of hooks -> %s' % (name, len(f.ops), sum(len(o.payload) * 4 for o in f.ops),
                                                      os.path.relpath(out)))


if __name__ == '__main__':
    main()

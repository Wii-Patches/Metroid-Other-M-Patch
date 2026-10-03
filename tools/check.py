#!/usr/bin/env python3
"""Consistency checks that need no game files (CI runs this).

  * every prebuilt feature stays inside its window of the injected section, its
    trampolines do not overlap, and each ends in the slot that becomes the branch back
  * the committed codes/ and riivolution/ files are exactly what build.py generates
  * the Gecko list fits the room Dolphin's code handler has (about 3.2 KB of code)

    python3 tools/check.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build
import features
from layout import CAVE_BASE, CAVE_LIMIT, WINDOWS
from ops import Hook, b_insn
from regions import REGIONS

GECKO_BUDGET = 3200         # bytes of code lines Dolphin's handler has room for (measured: 0x80002340-0x80003000)
fail = []


def check(cond, msg):
    if not cond:
        fail.append(msg)
        print('  FAIL', msg)


def main():
    taken = []
    for name in features.FEATURES:
        f = features.load(name)
        lo, hi = WINDOWS[name]
        writes = dict(f.writes())
        for op in f.ops:
            if not isinstance(op, Hook):
                continue
            n = len(op.payload) * 4
            check(lo <= op.tramp and op.tramp + n <= hi, '%s: trampoline 0x%08X..0x%08X outside its window' % (name, op.tramp, op.tramp + n))
            check(CAVE_BASE <= op.tramp and op.tramp + n <= CAVE_LIMIT, '%s: trampoline outside the injected section' % name)
            check(op.payload[-1] == 0, '%s: hook 0x%08X has no branch-back slot' % (name, op.site))
            for a, b in taken:
                check(op.tramp + n <= a or b <= op.tramp, '%s: trampolines overlap at 0x%08X' % (name, op.tramp))
            taken.append((op.tramp, op.tramp + n))
            body = writes[op.tramp]
            back = struct.unpack('>I', body[-4:])[0]
            check(back == b_insn(op.site + 4, op.tramp + len(body) - 4), '%s: bad branch-back at 0x%08X' % (name, op.site))
        print('ok: %s (%d ops)' % (name, len(f.ops)))

    root = os.path.join(HERE, '..')
    for region in REGIONS:
        ini = build.gecko_ini(region)
        check(open(os.path.join(root, 'codes', region + '.ini')).read() == ini, 'codes/%s.ini is stale (run tools/build.py)' % region)
        check(open(os.path.join(root, 'riivolution', region + '.xml')).read() == build.riivolution_xml(region),
              'riivolution/%s.xml is stale (run tools/build.py)' % region)
        code = sum(8 for l in ini.splitlines() if l and l[0] in '0123456789ABCDEF')
        check(code <= GECKO_BUDGET, '%s: %d bytes of Gecko code, Dolphin has room for about %d' % (region, code, GECKO_BUDGET))
    print('FAILED: %d' % len(fail) if fail else 'ok: all checks passed')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()

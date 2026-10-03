#!/usr/bin/env python3
"""Sanity checks on tools/prebuilt/*.json (no game files needed)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features
from layout import CC_BASE, CC_END, GC_BASE, GC_END
from ops import Hook

WINDOWS = {
    'cc': (CC_BASE, CC_END),
    'gc': (GC_BASE, GC_END),
}


def check_feature(name):
    f = features.load(name)
    base, end = WINDOWS[name]
    tramps = []
    for op in f.ops:
        if isinstance(op, Hook):
            tramps.append((op.tramp, op.tramp + len(op.payload) * 4))
    tramps.sort()
    for a, b in tramps:
        assert a >= base and b <= end, '%s: hook [0x%X, 0x%X] exceeds window [0x%X, 0x%X]' % (name, a, b, base, end)
    for i in range(len(tramps) - 1):
        assert tramps[i][1] <= tramps[i + 1][0], '%s: overlapping hooks at 0x%X' % (name, tramps[i][1])
    print('OK: %s (%d ops)' % (name, len(f.ops)))


def main():
    for name in features.FEATURES:
        check_feature(name)


if __name__ == '__main__':
    main()

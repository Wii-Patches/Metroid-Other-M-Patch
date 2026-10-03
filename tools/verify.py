#!/usr/bin/env python3
"""Check that every patch applies cleanly to retail main.dols and round-trips.

    OTHERM_DOL=/path/to/main.dol python3 tools/verify.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dol import Dol
import features
import patcher
from regions import REGIONS


def main():
    path = os.environ.get('OTHERM_DOL') or os.path.join(HERE, '..', 'work', 'dols', 'USA.dol')
    if not os.path.isfile(path):
        sys.exit('Retail DOL not found at %s. Set OTHERM_DOL=/path/to/main.dol' % path)

    dol = Dol(path)
    region = patcher.detect_region(dol)
    print('Detected region: %s' % region)
    st = patcher.status(dol, region)
    print('Initial status: %s' % st)
    for feat, s in st.items():
        assert s == 'clean', '%s is not clean: %s' % (feat, s)

    # Test patching
    patched_dol = Dol(path)
    done = patcher.patch(patched_dol, region, ['cc', 'gc'])
    print('Applied: %s' % done)
    st_patched = patcher.status(patched_dol, region)
    print('Patched status: %s' % st_patched)
    for feat, s in st_patched.items():
        assert s == 'patched', '%s is not patched: %s' % (feat, s)

    print('Verification SUCCESS!')


if __name__ == '__main__':
    main()

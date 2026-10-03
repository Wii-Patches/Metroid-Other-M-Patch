"""xref.py dol target...  : list bl/b callers of each target"""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dol import Dol
d = Dol(sys.argv[1]); T = {int(x, 16) for x in sys.argv[2:]}
for off, base, size, idx in d.secs:
    if idx >= 7: continue
    w = struct.unpack('>%dI' % (size // 4), bytes(d.data[off:off + size]))
    for i, x in enumerate(w):
        if x >> 26 == 18:
            li = x & 0x03FFFFFC
            if li & 0x02000000: li -= 0x04000000
            t = (base + 4 * i + li) & 0xFFFFFFFF if not x & 2 else li
            if t in T: print('%08X -> %08X %s' % (base + 4 * i, t, 'bl' if x & 1 else 'b'))

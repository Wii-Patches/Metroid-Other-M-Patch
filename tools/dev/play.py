#!/usr/bin/env python3
"""play.py <image> <steps> <out prefix>  -- drive the game with a scripted GameCube pad, print KPAD state, save frames.

steps: comma list of <seconds>:<action>; action = PRESS:A | RELEASE:A | STICK:x,y | CSTICK:x,y   (x,y in -1..1)
Env: GECKO (ini, default codes/R3OE01.ini), VIDEO (default Metal), WIIMOTE=1 for an emulated remote.
"""
import glob, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get('VIDEO', 'Metal') != 'Null':
    os.environ.setdefault('FRAMEDUMP', '1')
import struct
import dolphin_gc as dg

BTN = dict(A=0x01000000, B=0x02000000, X=0x04000000, Y=0x08000000, S=0x10000000, Z=0x00100000, L=0x00400000,
           R=0x00200000, U=0x00080000, D=0x00040000, LT=0x00010000, RT=0x00020000)

def main():
    image, steps, out = sys.argv[1:4]
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    user = os.path.abspath(os.environ.get('USERDIR', os.path.join(root, 'work', 'dolphin_user')))
    dg.prepare(user, os.environ.get('GECKO', os.path.join(root, 'codes', 'R3OE01.ini')), 'R3OE01', wiimote=bool(os.environ.get('WIIMOTE')))
    dg.launch(user, image, os.environ.get('VIDEO', 'Metal'))
    g = dg.connect(); g.cont()
    st = dict(btn=0, m=(128, 128), c=(128, 128))
    def feed():
        # SIC0INBUFH/L as the hardware reports them: bit 23 set, buttons in 29..16, then the sticks
        h = 0x00800000 | st['btn'] | (st['m'][0] << 8) | st['m'][1]
        l = (st['c'][0] << 24) | (st['c'][1] << 16) | 0x00008080
        g.interrupt(); g.cmd('M%x,8:%s' % (dg.STATE + 0x20, struct.pack('>II', h, l).hex())); g.cont()
    feed()
    t0 = time.time(); marks = []
    try:
        for s in steps.split(','):
            pass
        plan = []
        for tok in steps.split(';'):
            t, act = tok.split(':', 1); plan.append((float(t), act))
        for t, act in plan:
            while time.time() - t0 < t: time.sleep(0.1)
            kind, _, arg = act.partition(':')
            if kind == 'PRESS': st['btn'] |= BTN[arg]
            elif kind == 'RELEASE': st['btn'] &= ~BTN[arg]
            elif kind in ('STICK', 'CSTICK'):
                x, y = [float(v) for v in arg.split(',')]
                key = 'm' if kind == 'STICK' else 'c'
                st[key] = (int(128 + 127 * x), int(128 + 127 * y))
            feed()
            time.sleep(1.5)
            g.interrupt(); k = dg.kpad(g); g.cont()
            print('%5.1fs %-14s hold=%08X cl=%08X dev=%d ls=(%.2f,%.2f) rs=(%.2f,%.2f)' % (
                time.time() - t0, act, k['hold'], k['cl_hold'], k['dev'], *k['lstick'], *k['rstick']), flush=True)
            fr = sorted(glob.glob(os.path.join(user, 'Dump', 'Frames', '**', '*.png'), recursive=True), key=os.path.getmtime)
            if len(fr) > 3: shutil.copy(fr[-3], '%s_%02d.png' % (out, len(marks)))
            marks.append(act)
    finally:
        dg.stop(user)
        shutil.rmtree(os.path.join(user, 'Dump'), ignore_errors=True)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""boot.py <image> [seconds]  -- boot the game with the Gecko build and print the pad state each second."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dolphin_gc as dg

def main():
    image = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    user = os.path.abspath(os.environ.get('USERDIR', os.path.join(root, 'work', 'dolphin_user')))
    ini = os.environ.get('GECKO', os.path.join(root, 'codes', 'R3OE01.ini'))
    dg.prepare(user, ini, os.environ.get('GID', 'R3OE01'), wiimote=bool(os.environ.get('WIIMOTE')))
    dg.launch(user, image, os.environ.get('VIDEO', 'Null'))
    g = dg.connect()
    g.cont()
    try:
        t0 = time.time()
        while time.time() - t0 < secs:
            time.sleep(2)
            g.interrupt()
            print('%5.0fs' % (time.time() - t0), dg.kpad(g), flush=True)
            g.cont()
    finally:
        dg.stop(user)

if __name__ == '__main__':
    main()

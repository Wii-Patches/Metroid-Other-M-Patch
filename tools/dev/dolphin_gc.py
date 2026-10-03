"""Dev harness: run Other M in Dolphin with the Gecko build, a scripted GameCube pad on port 1 and no Wii Remote,
and read the game's KPAD state back over the GDB stub.   (Not shipped; needs Dolphin and a disc image.)

  import dolphin_gc as dg; dg.prepare(user, gecko_ini_path, 'R3OE01', ...) ; dg.launch(user, image, 'Null')

Input goes through Dolphin's Pipe device (User/Pipes/gc).  With DEBUG_FEED builds (-DDEBUG_FEED) the pad response
can also be written straight into STATE+0x20/0x24 over the GDB stub.
"""
import os, shutil, struct, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gdbmem import Gdb

DOLPHIN = '/Applications/Dolphin.app/Contents/MacOS/Dolphin'
PORT = int(os.environ.get("GDBPORT", 2171))
KPAD0 = 0x802DBEC0           # per-channel KPAD block, stride 0x688
STATE = 0x80005D40


def prepare(user, gecko_ini, gid, wiimote=False, enable=('Classic Controller', 'GameCube controller'), extra_ini=''):
    shutil.rmtree(user, ignore_errors=True)
    for d in ('Config', 'GameSettings', 'Pipes'):
        os.makedirs(os.path.join(user, d))
    os.mkfifo(os.path.join(user, 'Pipes', 'gc'))
    open(os.path.join(user, 'Config', 'Dolphin.ini'), 'w').write(
        "[General]\nGDBPort = %d\n[Interface]\nConfirmStop = False\nUsePanicHandlers = False\n"
        "[Core]\nMMU = True\nCPUThread = False\nCPUCore = 4\nEnableDebugging = True\nEnableCheats = True\n"
        "WiimoteContinuousScanning = False\nWiimoteControllerInterface = False\nSIDevice0 = 6\nSIDevice1 = 0\n"
        "[Analytics]\nPermissionAsked = True\nEnabled = False\n" % PORT + extra_ini +
        ("[Movie]\nDumpFrames = True\nDumpFramesSilent = True\nDumpFramesAsImages = True\n" if os.environ.get('FRAMEDUMP') else ""))
    open(os.path.join(user, 'Config', 'GCPadNew.ini'), 'w').write(
        "[GCPad1]\nDevice = Pipe/0/gc\n" + "".join("Buttons/%s = `Button %s`\n" % (b, b) for b in 'ABXYZ') +
        "Buttons/Start = `Button START`\n" +
        "".join("D-Pad/%s = `Button D_%s`\n" % (d.title(), d.upper()) for d in ('up', 'down', 'left', 'right')) +
        "Triggers/L = `Button L`\nTriggers/R = `Button R`\nTriggers/L-Analog = `Axis L -+`\nTriggers/R-Analog = `Axis R -+`\n"
        "Main Stick/Up = `Axis MAIN Y +`\nMain Stick/Down = `Axis MAIN Y -`\nMain Stick/Left = `Axis MAIN X -`\nMain Stick/Right = `Axis MAIN X +`\n"
        "C-Stick/Up = `Axis C Y +`\nC-Stick/Down = `Axis C Y -`\nC-Stick/Left = `Axis C X -`\nC-Stick/Right = `Axis C X +`\n")
    open(os.path.join(user, 'Config', 'WiimoteNew.ini'), 'w').write("[Wiimote1]\nSource = %d\n" % (1 if wiimote else 0))
    if gecko_ini and gecko_ini != '-':
        body = open(gecko_ini).read().replace('[Gecko]\n', '', 1)
        open(os.path.join(user, 'GameSettings', gid + '.ini'), 'w').write(
            "[Gecko_Enabled]\n" + "".join("$%s\n" % n for n in enable) + "[Gecko]\n" + body)


def launch(user, image, video='Null'):
    subprocess.check_call(['open', '-n', '-a', '/Applications/Dolphin.app', '--args', '-b', '-u', user, '-e', image, '-v', video])
    time.sleep(2)


def pid(user):
    out = subprocess.run(['ps', '-axo', 'pid=,command='], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if user in ln and 'Dolphin' in ln and 'dolphin_gc' not in ln:
            return int(ln.split()[0])


def stop(user):
    p = pid(user)
    if p:
        os.kill(p, 15)
        time.sleep(2)
        if pid(user):
            os.kill(pid(user), 9)


def connect(tries=120):
    for _ in range(tries):
        try:
            return Gdb(timeout=30)
        except OSError:
            time.sleep(1)
    raise RuntimeError('no GDB stub')


class Pad:
    def __init__(self, user):
        self.f = os.open(os.path.join(user, 'Pipes', 'gc'), os.O_WRONLY | os.O_NONBLOCK)
    def cmd(self, s):
        os.write(self.f, (s + '\n').encode())
    def press(self, b):   self.cmd('PRESS ' + b)
    def release(self, b): self.cmd('RELEASE ' + b)
    def stick(self, which, x, y): self.cmd('SET %s %.3f %.3f' % (which, x, y))
    def trig(self, which, v): self.cmd('SET %s %.3f' % (which, v))


def kpad(g, chan=0):
    """The interesting bits of a channel's KPAD block."""
    base = KPAD0 + 0x688 * chan
    b = g.read_mem(base, 0x70)
    hold, trig, rel = struct.unpack('>III', b[0:12])
    return dict(hold=hold, trig=trig, rel=rel, dev=b[0x5C], err=b[0x5D], dpd=b[0x5E],
                cl_hold=struct.unpack('>I', b[0x60:0x64])[0],
                lstick=struct.unpack('>ff', g.read_mem(base + 0x6C, 8)), rstick=struct.unpack('>ff', g.read_mem(base + 0x74, 8)))

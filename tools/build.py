#!/usr/bin/env python3
"""Emit the Gecko code lists and Riivolution XML from the prebuilt features.

    python3 tools/build.py            # writes codes/<ID>.ini, codes/<ID>.txt, riivolution/<ID>.xml

The patched-DOL path (tools/patcher.py, the GUI) uses the very same ops, so the
install methods cannot disagree.  All releases share one main.dol, so the three
files per format differ only in their disc id.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features
from regions import REGIONS

ROOT = os.path.join(HERE, '..')

CREDIT = {
    'cc': 'Vague Rant',
    'gc': 'quatric',
}
BLURB = {
    'cc': ['Play with a Classic Controller (or a Wii Remote and Nunchuk): left stick walks and aims,',
           'right stick moves the pointer, L/R toggles pointer mode.'],
    'gc': ['Play with a GameCube controller in port 1 -- no Wii Remote needed.',
           'Needs the Classic Controller code above; the pad shows up to the game as one.'],
}
# The pad class in game.rel drops the pointer unless the event scripts have set the "pointing allowed" flag
# (li r3,8; bl IsFlag; cmpwi r3,0; bne +0xC; li r0,0; stw r0,396(r31) at 0x80571B8C).  At the first-person step
# of the training simulation that flag stays off for a Classic Controller, so L + aim did nothing there.  While
# channel 0 is a Classic Controller (our GameCube pad included) the bne becomes a b; the check is skipped whenever
# game.rel is not loaded.  game.rel is loaded at run time, so this has to be a conditional Gecko code.
GATE = [
    '* Let the Classic Controller pointer through the training simulation\'s first-person gate',
    '20571BA0 901F018C',
    '282DBF1C 00FF0200',
    '04571B98 4800000C',
    'E2100001 00000000',
    '04571B98 4082000C',
    'E2000002 00000000',
]
EXTRA = {'gc': GATE}

NOTE = [
    '*Keep these in this order and enable both.  Do not combine with a loader\'s own Gecko',
    '*code handler on a real Wii if you can avoid it; use the patched disc image instead.',
]


def gecko_ini(region):
    lines = ['[Gecko]']
    for name in features.FEATURES:
        f = features.load(name)
        lines.append('$%s' % f.title)
        lines.append('*By %s' % CREDIT[name])
        lines.append('*%s (%s)' % (REGIONS[region]['label'], region))
        lines += ['*' + b for b in BLURB[name]]
        lines += f.gecko_lines()
        lines += EXTRA.get(name, [])
    return '\n'.join(lines) + '\n'


def riivolution_xml(region):
    r = REGIONS[region]
    out = ['<!-- %s: GameCube controller by quatric, Classic Controller by Vague Rant -->' % r['label'],
           '<wiidisc version="1" root="/">',
           '  <id game="%s" />' % region,
           '  <options>',
           '    <section name="%s">' % r['label']]
    for name in features.FEATURES:
        out.append('      <option name="%s" default="1">' % features.TITLES[name])
        out.append('        <choice name="Enabled"><patch id="%s" /></choice>' % name)
        out.append('      </option>')
    out += ['    </section>', '  </options>']
    for name in features.FEATURES:
        f = features.load(name)
        out.append('  <patch id="%s">' % name)
        out += ['    ' + e for e in f.memory_elements()]
        out.append('  </patch>')
    out.append('</wiidisc>')
    return '\n'.join(out) + '\n'


def main():
    for d in ('codes', 'riivolution'):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    for region in REGIONS:
        ini = gecko_ini(region)
        with open(os.path.join(ROOT, 'codes', region + '.ini'), 'w') as fh:
            fh.write(ini)
        # same codes in the plain cheat-file layout loaders read (no [Gecko] header)
        with open(os.path.join(ROOT, 'codes', region + '.txt'), 'w') as fh:
            fh.write(ini.split('\n', 1)[1])
        with open(os.path.join(ROOT, 'riivolution', region + '.xml'), 'w') as fh:
            fh.write(riivolution_xml(region))
        print(region, REGIONS[region]['label'])


if __name__ == '__main__':
    main()

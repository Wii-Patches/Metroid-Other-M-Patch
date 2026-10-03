"""Load the prebuilt feature definitions (tools/prebuilt/<feature>.json).

Every release shares one main.dol, so a feature has one definition for all of
them."""
import json
import os
import sys

from ops import Blob, Feature, Hook, Patch

if getattr(sys, 'frozen', False):
    PREBUILT = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)), 'prebuilt')
else:
    PREBUILT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prebuilt')

FEATURES = ('cc', 'gc')
TITLES = {
    'cc': 'Classic Controller',
    'gc': 'GameCube controller',
}
# the GameCube pad is presented to the game as a Classic Controller, so it needs the Classic Controller code
REQUIRES = {'gc': ('cc',)}


def dump(feature):
    ops = []
    for op in feature.ops:
        if isinstance(op, Patch):
            ops.append(dict(t='patch', addr=op.addr, new=op.new.hex(), orig=op.orig.hex(), note=op.note))
        elif isinstance(op, Blob):
            ops.append(dict(t='blob', addr=op.addr, data=op.data.hex(), note=op.note))
        elif isinstance(op, Hook):
            ops.append(dict(t='hook', site=op.site, orig=op.orig, payload=op.payload, tramp=op.tramp, note=op.note))
    return dict(feature=feature.name, title=feature.title, region=feature.region, ops=ops)


def load_dict(j):
    ops = []
    for o in j['ops']:
        if o['t'] == 'patch':
            ops.append(Patch(o['addr'], bytes.fromhex(o['new']), bytes.fromhex(o['orig']), o.get('note', '')))
        elif o['t'] == 'blob':
            ops.append(Blob(o['addr'], bytes.fromhex(o['data']), o.get('note', '')))
        elif o['t'] == 'hook':
            ops.append(Hook(o['site'], o['orig'], o['payload'], o['tramp'], o.get('note', '')))
    return Feature(j['feature'], j['title'], j['region'], ops)


def load(name):
    with open(os.path.join(PREBUILT, '%s.json' % name)) as f:
        return load_dict(json.load(f))


def expand(which):
    """`which` plus whatever it depends on, in application order."""
    want = set(which)
    for n in list(want):
        want.update(REQUIRES.get(n, ()))
    return [n for n in FEATURES if n in want]

def available(name):
    return os.path.isfile(os.path.join(PREBUILT, '%s.json' % name))

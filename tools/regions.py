"""The retail releases of Metroid: Other M.

All five discs (USA and Europe each have a Rev 0 and a Rev 1, Japan has one)
carry a byte-identical main.dol -- the revisions differ only in files on the
disc -- so every address in this project is valid for every release and there
is a single set of patch data.
"""
REGIONS = {
    'R3OE01': dict(label='Metroid: Other M (USA)', short='USA', versions=(0, 1)),
    'R3OP01': dict(label='Metroid: Other M (Europe)', short='Europe', versions=(0, 1)),
    'R3OJ01': dict(label='Metroid: Other M (Japan)', short='Japan', versions=(0,)),
}

DOL_SIZE = 2395904

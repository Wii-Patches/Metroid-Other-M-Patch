"""Disassemble a range of a DOL with devkitPPC objdump: disasm.py dol start end"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dol import Dol
d = Dol(sys.argv[1]); a = int(sys.argv[2], 16); b = int(sys.argv[3], 16)
data = d.read(a, b - a)
with tempfile.NamedTemporaryFile(suffix='.bin') as f:
    f.write(data); f.flush()
    out = subprocess.run(['/opt/devkitpro/devkitPPC/bin/powerpc-eabi-objdump', '-D', '-EB', '-b', 'binary', '-m', 'powerpc:750',
                          '--adjust-vma=0x%X' % a, f.name], capture_output=True, text=True).stdout
print(out.split('<.data>:')[-1])

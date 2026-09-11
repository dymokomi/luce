#!/usr/bin/env python3
"""Captured Base callbacks retain owners, results and checked views correctly."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'build/luce'
FLAGS = [['--native', '--opt', str(level)] for level in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]

def run(*args, expected=0):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    assert expected != 0 or not result.stderr, result.stderr
    return result

with tempfile.TemporaryDirectory(prefix='luce-retained-callbacks-') as temporary:
    root = Path(temporary)
    shutil.copytree(ROOT / 'tests/interop/callbacks', root, dirs_exist_ok=True)
    entry = root / 'main.luc'
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    entry.write_text('''import events
pub func main(arguments: list[str]) -> int!:
    let captured = "a captured value"
    try events.wrong_thread(func (text: str) -> unit!:
        discard(captured + text)
    )
    return 0
''')
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'wrong-thread')
        assert 'another runtime thread' in run(root / 'wrong-thread', expected=1).stderr
print('PASS retained callbacks: captures, bound/native handlers, owned results/errors, frame expiry, cycles and wrong-thread rejection; six modes')

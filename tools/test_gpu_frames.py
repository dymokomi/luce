#!/usr/bin/env python3
"""Checked GPU frames and escaped bound methods cross into Luce without native links."""
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

compiler = Path(sys.argv[1] if len(sys.argv) > 1 else './build/luce').resolve()
source = Path(__file__).resolve().parents[1] / 'tests/interop/gpu_frames/main.luc'
modes = [['--native', '--opt', str(level)] for level in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]
with tempfile.TemporaryDirectory(prefix='luce-gpu-frames-') as temporary:
    binary = Path(temporary) / 'fixture'
    for flags in modes:
        subprocess.run([compiler, 'build', source, *flags, '-o', binary], check=True, timeout=120)
        result = subprocess.run([binary], capture_output=True, text=True, timeout=15)
        assert result.returncode == 0 and result.stdout == 'ok scoped GPU frames\n' and not result.stderr, result
        if platform.system() == 'Darwin':
            linked = subprocess.check_output(['otool', '-L', binary], text=True)
            assert all(name not in linked for name in ('AppKit', 'Metal', 'QuartzCore', 'libobjc')), linked
print('PASS standard GPU objects, retained bound methods and expiry from Luce; six modes')

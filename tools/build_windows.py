#!/usr/bin/env python3
"""Build Luce natively with a Windows Base compiler from the sibling checkout."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, default=Path(os.environ.get('LUCE_BASE_COMPILER', ROOT.parent / 'luce-base/build/luce-base.exe')))
args = parser.parse_args()
(ROOT / 'build').mkdir(exist_ok=True)
for script in ('embed_version.py', 'embed_runtime.py', 'embed_prelude.py'):
    subprocess.run([sys.executable, ROOT / 'tools' / script], cwd=ROOT, check=True)
subprocess.run([args.base.resolve(), 'build', 'src/main.lucb', '--native', '-o', ROOT / 'build/luce.exe'], cwd=ROOT, check=True)
print('built build/luce.exe')

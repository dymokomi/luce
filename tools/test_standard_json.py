#!/usr/bin/env python3
"""Use the standard Base JSON value directly from Luce in all execution modes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

compiler = Path(sys.argv[1] if len(sys.argv) > 1 else './build/luce').resolve()
source = Path(__file__).resolve().parents[1] / 'tests/interop/json_values/main.luc'
modes = [['--native', '--opt', str(level)] for level in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]
with tempfile.TemporaryDirectory(prefix='luce-json-') as temporary:
    binary = Path(temporary) / 'fixture'
    for flags in modes:
        subprocess.run([compiler, 'build', source, *flags, '-o', binary], check=True, timeout=120)
        result = subprocess.run([binary], capture_output=True, text=True, timeout=15)
        assert result.returncode == 0 and not result.stderr, result
        assert json.loads(result.stdout) == {'message': 'Hello, café!\n', 'count': 42,
                                            'items': [True, None]}, result.stdout
print('PASS standard JSON objects from Luce; six modes')

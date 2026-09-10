#!/usr/bin/env python3
"""Check Base record field ownership, mutability, and older descriptor compatibility."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'build/luce'
BASE = os.environ['LUCE_BASE']
FLAGS = [['--native', '--opt', str(n)] for n in range(4)] + [['--backend=c'], ['--backend=c', '--release']]


def run(command, success=True):
    result = subprocess.run(list(map(str, command)), cwd=ROOT, capture_output=True, timeout=120)
    assert (result.returncode == 0) == success, result.stdout.decode() + result.stderr.decode()
    if success:
        assert not result.stderr, result.stderr.decode()
    return result


with tempfile.TemporaryDirectory(prefix='luce-base-fields-') as temporary:
    root = Path(temporary)
    boundary = root / 'boundary.lucb'
    boundary.write_text('''pub struct Settings:
    pub var port: i64
    pub var label: str
    pub let version: i64

pub func defaults() -> Settings:
    return Settings(port = 80, label = "original", version = 1)

pub func describe(value: Settings) -> str:
    return value.label
''')
    supports_mutability = b'    mutable port\n' in run([BASE, 'describe', boundary]).stdout
    entry = root / 'main.luc'
    entry.write_text('''import boundary
pub func main(arguments: list[str]) -> int!:
    let original = boundary.defaults()
    var copy = original
    copy.port = 8080
    copy.label = "new " + str(copy.port)
    copy.label = copy.label
    assert(original.port == 80)
    assert(original.label == "original")
    assert(copy.port == 8080)
    assert(boundary.describe(copy) == "new 8080")
    return 0
''')
    for flags in FLAGS:
        result = run([COMPILER, 'build', entry, *flags, '-o', root / 'app'], supports_mutability)
        if supports_mutability:
            run([root / 'app'])
        else:
            assert b'immutable' in result.stderr or b'var' in result.stderr, result.stderr
    for declaration, assignment in [('var', 'version = 2'), ('let', 'port = 8080')]:
        entry.write_text(f'''import boundary
pub func main(arguments: list[str]) -> int!:
    {declaration} value = boundary.defaults()
    value.{assignment}
    return 0
''')
        result = run([COMPILER, 'check', entry], False)
        assert b'immutable' in result.stderr or b'var' in result.stderr, result.stderr
    print('PASS Base fields: mutable copies, immutable fields/bindings, all six modes'
          if supports_mutability else 'PASS legacy Base fields remain read-only, all six modes')

#!/usr/bin/env python3
"""Native object ownership and invalid crossings through a real package consumer."""
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


def run(*arguments, expected=0):
    result = subprocess.run(list(map(str, arguments)), cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 0:
        assert not result.stderr, result.stderr
    return result


with tempfile.TemporaryDirectory(prefix='luce-native-objects-') as temporary:
    root = Path(temporary)
    shutil.copytree(ROOT / 'tests/interop/objects', root, dirs_exist_ok=True)
    entry = root / 'main.luc'
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    for use, message in [
        ('value.value()', 'a native object is closed'),
        ('value.count', 'a native object is closed'),
        ('method()', 'a native object is closed')]:
        entry.write_text(f'''from objects import Counter
pub func main(arguments: list[str]) -> int!:
    let value = try Counter("closed")
    let method = value.value
    value.close()
    discard({use})
    return 0
''')
        for flags in FLAGS:
            run(COMPILER, 'build', entry, *flags, '-o', root / 'closed')
            assert message in run(root / 'closed', expected=1).stderr
    entry.write_text('''from objects import Counter
func worker(value: Counter) -> int:
    return value.value()
pub func main(arguments: list[str]) -> int!:
    let value = try Counter("thread")
    let job = spawn worker(value)
    return wait job
''')
    assert 'send' in run(COMPILER, 'check', entry, expected=1).stderr
    entry.write_text('''from objects import Counter
pub func main(arguments: list[str]) -> int!:
    let value = try Counter("temporary")
    value.child = value
    return 0
''')
    assert 'package method' in run(COMPILER, 'check', entry, expected=1).stderr
    # A by-value native object is not an owned result, even with a matching name.
    with (root / 'objects.lucb').open('a') as source:
        source.write('\npub func unowned(value: Counter) -> Counter:\n    return value\n')
    entry.write_text('''import objects
pub func main(arguments: list[str]) -> int!:
    let value = try objects.Counter("unowned")
    discard(objects.unowned(value))
    return 0
''')
    assert 'has no `unowned`' in run(COMPILER, 'check', entry, expected=1).stderr
print('PASS native objects: constructors, state, identity, aliases, fields, children, bound/static methods, close and rejected crossings; six modes')

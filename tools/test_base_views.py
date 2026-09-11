#!/usr/bin/env python3
"""Borrowed native views keep checks alive while expiry remains observable."""
from pathlib import Path
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


with tempfile.TemporaryDirectory(prefix='luce-native-views-') as temporary:
    root = Path(temporary)
    shutil.copytree(ROOT / 'tests/interop/views', root, dirs_exist_ok=True)
    entry = root / 'main.luc'
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    for expression in ['frame.read()', 'read()', 'captured()']:
        entry.write_text(f'''from views import Resource
import views
pub func main(arguments: list[str]) -> int!:
    let owner = try Resource("expired")
    let frame = try views.begin(owner)
    let read = frame.read
    let captured: func() -> str = () => frame.read()
    owner.end()
    discard({expression})
    return 0
''')
        for flags in FLAGS:
            run(COMPILER, 'build', entry, *flags, '-o', root / 'expired')
            assert 'a native view has expired' in run(root / 'expired', expected=1).stderr
    entry.write_text('''import views
pub func main(arguments: list[str]) -> int!:
    discard(views.BorrowedFrame())
    return 0
''')
    assert 'private initializer' in run(COMPILER, 'check', entry, expected=1).stderr
    entry.write_text('''import views
func worker(frame: views.Frame) -> str:
    return frame.read()
pub func main(arguments: list[str]) -> int!:
    let owner = try views.Resource("thread")
    let frame = try views.begin(owner)
    let job = spawn worker(frame)
    discard(wait job)
    return 0
''')
    assert 'not sendable' in run(COMPILER, 'check', entry, expected=1).stderr
print('PASS native views: owner/lease retention, expiry, bound/captured uses, owned snapshots and rejected construction/transfer; six modes')

#!/usr/bin/env python3
"""Real Base/Luce interface consumers: dispatch, owning results and mixed cycles."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'build/luce'
BASE = Path(os.environ.get('LUCE_BASE', ROOT / 'build/luce-base/build/luce-base')).resolve()
FLAGS = [['--native', '--opt', str(level)] for level in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]

def run(*arguments, expected=0):
    result = subprocess.run(list(map(str, arguments)), cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 0:
        assert not result.stderr, result.stderr
    return result

with tempfile.TemporaryDirectory(prefix='luce-native-interfaces-') as temporary:
    root = Path(temporary)
    shutil.copytree(ROOT / 'tests/interop/interfaces', root, dirs_exist_ok=True)
    for flags in FLAGS:
        for compiler, entry in [(BASE, 'base.lucb'), (COMPILER, 'main.luc')]:
            run(compiler, 'build', root / entry, *flags, '-o', root / 'consumer')
            run(root / 'consumer')
    entry = root / 'main.luc'
    entry.write_text("""import widgets
class Bad: widgets.NativeLabel:
    pub func label(self) -> str:
        return "temporary " + str(1)
pub func main(arguments: list[str]) -> int!:
    return 0
""")
    assert 'requires interop.Owned' in run(COMPILER, 'check', entry, expected=1).stderr
    entry.write_text("""import widgets
pub func main(arguments: list[str]) -> int!:
    let value = try widgets.Counter("raw")
    discard(widgets.raw(value))
    return 0
""")
    assert 'has no `raw`' in run(COMPILER, 'check', entry, expected=1).stderr
    entry.write_text("""import widgets
func worker(value: widgets.Widget) -> int:
    return value.value()
pub func main(arguments: list[str]) -> int!:
    let value = try widgets.Counter("worker")
    let widget = widgets.as_widget(value)
    let job = spawn worker(widget)
    return wait job
""")
    assert 'not sendable' in run(COMPILER, 'check', entry, expected=1).stderr
    for after, call, message in [
        ('owner.close()', 'bound()', 'a native object is closed'),
        ('owner.close()', 'bound()', 'a native view has expired')]:
        maker = 'widgets.frame_widget(try widgets.frame(owner))' if 'view' in message else 'widgets.as_widget(owner)'
        entry.write_text(f"""import widgets
pub func main(arguments: list[str]) -> int!:
    let owner = try widgets.Counter("expired")
    let widget = {maker}
    let bound = widget.title
    {after}
    discard({call})
    return 0
""")
        for flags in FLAGS:
            run(COMPILER, 'build', entry, *flags, '-o', root / 'closed')
            assert message in run(root / 'closed', expected=1).stderr
print('PASS native interfaces: Base/Luce consumers, mutation, owned results/errors, retention, identity and mixed cycles; six modes')

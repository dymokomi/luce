#!/usr/bin/env python3
"""Clean consumers use package exports and canonical Base standard modules."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'build/luce'
BASE = Path(os.environ['LUCE_BASE']).resolve()
FLAGS = [['--native', '--opt', str(level)] for level in range(4)] + [['--backend=c'], ['--backend=c', '--release']]

def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path

def run(*args, expected=0):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    assert expected != 0 or not result.stderr, result.stderr
    return result

with tempfile.TemporaryDirectory(prefix='luce public imports ü-') as temporary:
    root = Path(temporary)
    write(root, 'helper/luce.toml', '[package]\nname = "helper"\n[exports]\nmeasure = "helper.measure"\n')
    write(root, 'helper/src/helper/measure.lucb', 'pub interface Measured:\n    func length() -> i64\npub let invalid: ErrorCode = ErrorCode.package(1)\npub func length(text: str) -> i64:\n    return (i64)text.length\n')
    write(root, 'library/luce.toml', '[package]\nname = "luce_ui"\n[dependencies]\nhelper = "../helper"\n[exports]\nui = "luce_ui.ui"\ncontrols = "luce_ui.ui"\n')
    write(root, 'library/src/luce_ui/ui.lucb', 'import measure\nimport net\npub type Measured = measure.Measured\npub func version() -> net.IpVersion:\n    return net.IpVersion.ipv4\npub let invalid: ErrorCode = ErrorCode.package(1)\npub func distinct_errors() -> bool:\n    return invalid != measure.invalid\npub struct Button: measure.Measured:\n    var size: i64\n    pub func init(label: str):\n        self.size = measure.length(label)\n    pub func length() -> i64:\n        return self.size\n')
    write(root, 'app/luce.toml', '[package]\nname = "demo"\n[dependencies]\nluce_ui = "../library"\n')
    entry = write(root, 'app/src/main.luc', 'from ui import Button\nimport controls\nimport ui\nimport math\nimport net\nfunc length(value: ui.Measured) -> int:\n    return value.length()\npub func main(arguments: list[str]) -> int!:\n    let button: controls.Button = Button("pause")\n    assert(button.length() == 5 and length(button) == 5 and ui.distinct_errors())\n    assert(ui.version() == net.IpVersion.ipv4)\n    assert(math.pi > 3.0 and math.sin(0.0) == 0.0)\n    return 0\n')
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    original = entry.read_text()
    entry.write_text('import helper.measure\npub func main(arguments: list[str]) -> int:\n    return 0\n')
    rejected = run(COMPILER, 'build', entry, '-o', root / 'consumer', expected=1)
    assert 'neither local nor a public package export' in rejected.stderr, rejected.stderr
    entry.write_text(original)
    assert sorted(path.name for path in entry.parent.iterdir()) == ['main.luc']
    output = root / 'kept'
    run(COMPILER, 'build', entry, '--emit=base', '-o', output)
    emitted = Path(str(output) + '.base')
    assert not (emitted / 'math.lucb').exists()
    assert 'measure = "helper.measure"' in (emitted / 'luce.toml').read_text()
    relocated = root / 'relocated'
    shutil.move(emitted, relocated)
    shutil.rmtree(root / 'library')
    shutil.rmtree(root / 'helper')
    shutil.rmtree(root / 'app')
    for flags in FLAGS:
        run(BASE, 'build', relocated / 'main.lucb', *flags, '-o', root / 'consumer')
        run(root / 'consumer')
print('PASS public imports, private foreign interfaces, aliases, standard math and relocation; six modes')

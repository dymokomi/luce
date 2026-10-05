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
STD = Path(os.environ.get('LUCE_STD_PACKAGE', ROOT.parent / 'luce-std')).resolve()
USES_STD = f'    def dependency "luce-std" {{\n        str path = "{STD.as_posix()}"\n    }}\n'
FLAGS = [['--native', '--opt', str(level)] for level in range(4)] + [['--backend=c'], ['--backend=c', '--release']]

def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path

def run(*args, expected=0):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    assert expected != 0 or not result.stderr, result.stderr
    return result

with tempfile.TemporaryDirectory(prefix='luce public imports ü-') as temporary:
    root = Path(temporary)
    write(root, 'helper/package.prisma', '#prisma 4.0\ndef package "helper" {\n    str[] public = ["measure"]\n}\n')
    write(root, 'helper/src/measure.lucb', 'pub interface Measured:\n    func length() -> i64\npub let invalid: ErrorCode = ErrorCode.package(1)\npub func length(text: str) -> i64:\n    return (i64)text.length\n')
    write(root, 'library/package.prisma', '#prisma 4.0\ndef package "luce-ui" {\n' + USES_STD + '    def dependency "helper" {\n        str path = "../helper"\n    }\n    str[] public = ["ui", "widgets.label"]\n}\n')
    write(root, 'library/src/widgets/label.lucb', 'pub func width(text: str) -> i64:\n    return (i64)text.length * 2\n')
    write(root, 'library/src/ui.lucb', 'import helper.measure\nfrom luce_std import net\npub type Measured = measure.Measured\npub func version() -> net.IpVersion:\n    return net.IpVersion.ipv4\npub let invalid: ErrorCode = ErrorCode.package(1)\npub func distinct_errors() -> bool:\n    return invalid != measure.invalid\npub struct Button: measure.Measured:\n    var size: i64\n    pub func init(label: str):\n        self.size = measure.length(label)\n    pub func length() -> i64:\n        return self.size\n')
    write(root, 'app/package.prisma', '#prisma 4.0\ndef package "demo" {\n' + USES_STD + '    def dependency "luce-ui" {\n        str path = "../library"\n    }\n}\n')
    entry = write(root, 'app/src/main.luc', 'from luce_ui.ui import Button\nimport luce_ui.ui as controls\nfrom luce_ui import ui\nfrom luce_std import math, net\nfunc length(value: ui.Measured) -> int:\n    return value.length()\npub func main(arguments: list[str]) -> int!:\n    let button: controls.Button = Button("pause")\n    assert(button.length() == 5 and length(button) == 5 and ui.distinct_errors())\n    assert(ui.version() == net.IpVersion.ipv4)\n    assert(math.pi > 3.0 and math.sin(0.0) == 0.0)\n    return 0\n')
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    # a `from` import names a directory of modules and aliases what it brings
    aliases = write(root, 'app/src/aliases.luc', 'from luce_ui import ui as controls\nfrom luce_ui.widgets import label as text_label\nfrom luce_ui.ui import Button as Control\n\npub func main(arguments: list[str]) -> int!:\n    let button: controls.Button = Control("abc")\n    assert(text_label.width("ab") == 4 and button.length() == 3)\n    return 0\n')
    run(COMPILER, 'build', aliases, '-o', root / 'aliases')
    run(root / 'aliases')
    run(COMPILER, 'fmt', aliases, '--check')
    aliases.unlink()
    original = entry.read_text()
    entry.write_text('import helper.measure\npub func main(arguments: list[str]) -> int:\n    return 0\n')
    rejected = run(COMPILER, 'build', entry, '-o', root / 'consumer', expected=1)
    assert 'public module of a package it depends on' in rejected.stderr, rejected.stderr
    entry.write_text(original)
    assert sorted(path.name for path in entry.parent.iterdir()) == ['main.luc']
    output = root / 'kept'
    run(COMPILER, 'build', entry, '--emit=base', '-o', output)
    emitted = Path(str(output) + '.base')
    assert not (emitted / 'math.lucb').exists()
    # each Base package the program reaches is a package of its own under deps/
    workspace = (emitted / 'package.prisma').read_text()
    assert 'def dependency "luce_ui"' in workspace and 'def dependency "helper"' in workspace, workspace
    assert (emitted / 'deps' / 'luce_ui' / 'ui.lucb').exists() and (emitted / 'deps' / 'helper' / 'measure.lucb').exists()
    assert 'def dependency "helper"' in (emitted / 'deps' / 'luce_ui' / 'package.prisma').read_text()
    relocated = root / 'relocated'
    shutil.move(emitted, relocated)
    shutil.rmtree(root / 'library')
    shutil.rmtree(root / 'helper')
    shutil.rmtree(root / 'app')
    for flags in FLAGS:
        run(BASE, 'build', relocated / 'main.lucb', *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    # a key set twice in one element is refused at the second, by Luce as by luce-base
    write(root, 'twice/package.prisma', '#prisma 4.0\ndef package "twice" {\n    str source = "src"\n    def dependency "x" {\n        str path = "x"\n    }\n    str source = "src"\n}\n')
    twice = write(root, 'twice/src/main.luc', 'pub func main(arguments: list[str]) -> int!:\n    return 0\n')
    for command in (['run'], ['build', '-o', root / 'twice-out']):
        refused = run(COMPILER, *command[:1], twice, *command[1:], expected=1)
        assert 'package.prisma:7:9: `source` is set twice in one element; it was set on line 3' in refused.stderr, refused.stderr
print('PASS package modules: qualified imports, `from` directories and aliases, private foreign interfaces, standard packages, per-package emission and relocation, a manifest key set twice refused; six modes')

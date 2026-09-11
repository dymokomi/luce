#!/usr/bin/env python3
"""Native sources and libraries follow transitive package imports and path roots."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

base = Path(os.environ["LUCE_BASE"]).resolve()
luce = Path(sys.argv[1] if len(sys.argv) > 1 else "build/luce").resolve()


def run(*args):
    result = subprocess.run(list(map(str, args)), env=dict(os.environ, LUCE_BASE=str(base)),
                            capture_output=True, timeout=120)
    assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result.stdout


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


with tempfile.TemporaryDirectory(prefix='native-package-inputs-') as temporary:
    root = Path(temporary).resolve() / 'space, quote" and apostrophe\' directory'
    leaf = root / 'leaf'
    native = write(leaf, 'native/source,one.c', '#include <stdint.h>\nint64_t package_value(void) { return 40; }\n')
    archive_source = write(leaf, 'native/bonus.c', '#include <stdint.h>\nint64_t package_bonus(void) { return 2; }\n')
    archive = leaf / 'native/libpackage_bonus.a'
    run('cc', '-c', archive_source, '-o', leaf / 'native/bonus.o')
    run('ar', 'rcs', archive, leaf / 'native/bonus.o')
    write(leaf, 'luce.toml', '[package]\nname = "leaf"\nsource = "src"\n[exports]\nnative_core = "leaf.core"\n'
          '[native]\nsources = ["native/source,one.c"]\nlink_search = ["native"]\nlibraries = ["package_bonus"]\n')
    write(leaf, 'src/leaf/core.lucb', 'extern func package_value() -> i64\nextern func package_bonus() -> i64\n'
          'pub func answer() -> i64:\n    return package_value() + package_bonus()\n')
    middle = root / 'middle'
    write(middle, 'luce.toml', '[package]\nname = "middle"\nsource = "src"\n[dependencies]\nleaf = "../leaf"\n[exports]\napi = "middle.api"\n')
    write(middle, 'src/middle/api.lucb', 'from native_core import answer\npub func number() -> i64:\n    return answer()\n')
    app = root / 'app'
    write(app, 'luce.toml', '[package]\nname = "consumer"\nsource = "src"\n[dependencies]\nmiddle = "../middle"\n'
          '[native]\nsources = ["native/root.c"]\n')
    write(app, 'native/root.c', '#include <stdint.h>\nint64_t root_value(void) { return 1; }\n')
    write(app, 'src/own.lucb', 'extern func root_value() -> i64\npub func value() -> i64:\n    return root_value()\n')
    entry = write(app, 'src/main.lucb', 'from api import number\nimport own\npub func main(arguments: str[]) -> i32:\n'
                  '    print(f"{number() + own.value()}")\n    return 0\n')
    if luce:
        entry = write(app, 'src/main.luc', 'from api import number\nimport own\n'
                      'pub func main(arguments: list[str]) -> int!:\n    print(number() + own.value())\n    return 0\n')
    compiler = luce or base
    binary = root / 'app-bin'
    modes = [['--native', '--opt', str(level)] for level in range(4)] + [['--backend=c'], ['--backend=c', '--release']]
    for flags in modes:
        run(compiler, 'build', entry, *flags, '-o', binary)
        assert run(binary) == b'43\n'
        assert not Path(str(binary) + '.base').exists()
    if luce:
        run(luce, 'build', entry, '--emit=base', '-o', binary)
        staged = Path(str(binary) + '.base')
        manifest = (staged / 'luce.toml').read_text()
        assert manifest.count('[native]') == 1, manifest
        assert manifest.count('source,one.c') == 1, manifest
        assert json.dumps(str(native)) in manifest, manifest
        run(base, 'build', staged / 'main.lucb', '-o', binary)
        assert run(binary) == b'43\n'
    else:
        report = run(base, 'dependencies', entry)
        assert report.count(b'native\0sources\0') == 2, report
        assert str(native).encode() in report, report
print('PASS transitive native sources, archives, package-relative search paths, escaped paths and clean builds; six modes')

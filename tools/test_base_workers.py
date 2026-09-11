#!/usr/bin/env python3
"""Persistent native application workers and the compiler's transfer boundary."""
from pathlib import Path
import shutil
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'build/luce'
BASE = Path(os.environ.get('LUCE_BASE', ROOT / 'build/luce-base/build/luce-base')).resolve()
FLAGS = [['--native', '--opt', str(level)] for level in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]

def run(*args, expected=0):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    assert expected != 0 or not result.stderr, result.stderr
    return result

with tempfile.TemporaryDirectory(prefix='luce-application-workers-') as temporary:
    root = Path(temporary)
    shutil.copytree(ROOT / 'tests/interop/workers', root, dirs_exist_ok=True)
    entry = root / 'main.luc'
    for flags in FLAGS:
        for compiler, source in [(BASE, root / 'base.lucb'), (COMPILER, entry)]:
            run(compiler, 'build', source, *flags, '-o', root / 'consumer')
            for _ in range(3):
                run(root / 'consumer')

    captured = '''from workers import Service, Handler
import workers
pub func main(arguments: list[str]) -> int!:
    let captured = "source-thread state"
    let factory = func (prefix: str) -> Handler!:
        return func (message: str) -> str!:
            return captured + prefix + message
    let service = try Service(factory, "test")
    service.close()
    return 0
'''
    # Keep imports used and the closure's type valid; reject its provenance.
    entry.write_text(captured.replace('import workers\n', ''))
    assert 'named application factory' in run(COMPILER, 'check', entry, expected=1).stderr

    # An ordinary function value erases native parameter metadata. Its adapter
    # must still reject a captured factory before creating any worker thread.
    entry.write_text(captured.replace('let service = try Service(factory, "test")',
        'let create = workers.create_service\n    let service = try create(factory)').replace(
        'from workers import Service, Handler', 'from workers import Handler'))
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'captured')
        assert 'named application factory' in run(root / 'captured', expected=1).stderr

    payloads = [
        ('interop.Reference[workers.Service]', 'str', 'str', 'configuration'),
        ('str', '(str, interop.Reference[workers.Service]?)', 'str', 'messages'),
        ('str', 'str', 'interop.Reference[workers.Service]', 'results'),
        ('str', 'str', 'interop.Callback[str, str]', 'results'),
        ('interop.Owned[str]', 'str', 'str', 'ownership'),
    ]
    for configuration, message, result, diagnostic in payloads:
        (root / 'bad.lucb').write_text(f'''import interop
import workers
pub func rejected(factory: interop.WorkerEntry[{configuration}, {message}, {result}]):
    discard(factory)
pub func ordinary() -> i64:
    return 1
''')
        entry.write_text('''import bad
pub func main(arguments: list[str]) -> int!:
    assert(bad.ordinary() == 1)
    return 0
''')
        rejected = run(COMPILER, 'check', entry, expected=1)
        assert (('worker transfer payloads cannot contain native ownership carriers' if diagnostic == 'ownership'
                 else f'worker {diagnostic} must be transferable') in rejected.stderr), rejected.stderr

    # An acyclic chain past the traversal bound cannot hide an unsendable owner.
    declarations = ['class Owner:\n    var number: int = 0\n',
                    'struct Layer0:\n    let owner: Owner\n']
    declarations += [f'struct Layer{i}:\n    let inner: Layer{i - 1}\n' for i in range(1, 36)]
    declarations += ['func read(value: Layer35) -> int:\n    return 0\n',
                     'pub func main(arguments: list[str]) -> int!:\n    let item0 = Layer0(Owner())\n']
    declarations += [f'    let item{i} = Layer{i}(item{i - 1})\n' for i in range(1, 36)]
    declarations += ['    let job = spawn read(item35)\n    return wait job\n']
    entry.write_text(''.join(declarations))
    rejected = run(COMPILER, 'check', entry, expected=1)
    assert 'not sendable' in rejected.stderr, rejected.stderr

print('PASS native application workers: per-thread state/cycles, named factories, native values, owned replies/errors, cancellation, startup, transfer rejection and function-value guards; six modes')

#!/usr/bin/env python3
"""Windows gate for existing Luce fixtures, interpreter and all six compiled modes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
# Share the process-tree owner with the pinned Base validation tools.
sys.path.insert(0, str(ROOT.parent / 'luce-base/tools'))
from validation_process import run as run_owned, remove_directory
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, default=ROOT / 'build/luce.exe')
parser.add_argument('--base', type=Path, default=ROOT.parent / 'luce-base/build/luce-base.exe')
parser.add_argument('--jobs', type=int, default=2)
parser.add_argument('--match', default='')
parser.add_argument('--c-only', action='store_true', help='recheck the comparison backend after a C emitter change')
args = parser.parse_args()
os.environ['LUCE_BASE'] = str(args.base.resolve())
MODES = [['--native', '--opt', str(n)] for n in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]
if args.c_only:
    MODES = MODES[-2:]


def run(*command):
    return run_owned(command, cwd=ROOT, capture_output=True, timeout=120)


def evaluate(source, workspaces):
    name = source.relative_to(ROOT).as_posix()
    executions = 0
    try:
        if 'errors' in source.parts:
            messages = re.findall(r'^# error: (.+)$', source.read_text(encoding='utf-8', errors='replace'), re.M)
            if not messages:
                return dict(source=name, ok=True, executions=0)
            result = run(args.compiler, 'check', name)
            diagnostic = result.stderr.decode('utf-8', errors='replace')
            assert result.returncode == 1 and re.search(r'\.luc:\d+:\d+:', diagnostic), diagnostic
            assert all(message in diagnostic for message in messages), diagnostic
            return dict(source=name, ok=True, executions=1)
        result = run(args.compiler, 'parse', name)
        assert result.returncode == 0, result.stderr
        executions += 1
        fixture = next((source.with_suffix(suffix) for suffix in ('.expect', '.trap', '.tests')
                        if source.with_suffix(suffix).exists()), None)
        if fixture:
            expected = fixture.read_text(encoding='utf-8').encode('utf-8')
            trap = fixture.suffix == '.trap'
            tests = fixture.suffix == '.tests'
            wanted = 1 if trap or (tests and b' failed\n' in expected) else 0
            directory = tempfile.mkdtemp(prefix='luce-conformance-')
            workspaces.append(directory)
            binary = Path(directory) / 'case.exe'
            for mode in [None, *MODES]:
                if tests:
                    result = run(args.compiler, 'test', name, *(['--build', *mode] if mode else []))
                elif mode is None:
                    result = run(args.compiler, 'run', name)
                    if list(source.parent.glob('*.lucb')):
                        assert result.returncode == 1 and b'the interpreter runs Luce alone' in result.stderr, result
                        executions += 1
                        continue
                else:
                    built = run(args.compiler, 'build', name, *mode, '-o', binary)
                    assert built.returncode == 0, built.stderr
                    result = run(binary)
                assert result.returncode == wanted, (mode, result.returncode, result.stderr)
                actual = result.stdout + result.stderr if tests else result.stdout
                assert expected.strip() in result.stderr if trap else actual == expected, (mode, expected, actual, result.stderr)
                executions += 1
        doc = source.with_suffix('.doc')
        if doc.exists():
            result = run(args.compiler, 'doc', name)
            assert result.returncode == 0 and result.stdout == doc.read_text(encoding='utf-8').encode(), result
            executions += 1
        explain = source.with_suffix('.explain')
        if explain.exists():
            for line in explain.read_text(encoding='utf-8').splitlines():
                place, wanted = line.split('|', 1)
                result = run(args.compiler, 'explain', name + ':' + place)
                assert result.returncode == 0 and result.stdout.decode('utf-8').strip() == wanted, result
                executions += 1
        return dict(source=name, ok=True, executions=executions)
    except (AssertionError, OSError, subprocess.TimeoutExpired) as error:
        return dict(source=name, ok=False, executions=executions, error=str(error))


def check(source):
    workspaces = []
    try:
        result = evaluate(source, workspaces)
    except Exception as error:
        result = dict(source=source.relative_to(ROOT).as_posix(), ok=False,
                      executions=0, error=repr(error))
    for directory in workspaces:
        try:
            remove_directory(directory)
        except OSError as error:
            result = dict(source=result['source'], ok=False, executions=result['executions'],
                          phase='cleanup', error=str(error), retained_directory=directory,
                          previous=result)
    return result


sources = sorted(p for folder in ('conformance', 'programs')
                 for p in (ROOT / 'tests' / folder).rglob('*.luc') if args.match in str(p))
results = []
journal = ROOT / 'build/windows-conformance-results.jsonl'
journal.parent.mkdir(parents=True, exist_ok=True)
with journal.open('w', encoding='utf-8') as evidence, ThreadPoolExecutor(max_workers=args.jobs) as pool:
    pending = {pool.submit(check, source): source for source in sources}
    for future in as_completed(pending):
        result = future.result()
        results.append(result)
        evidence.write(json.dumps(result) + '\n')
        evidence.flush()
        if not result['ok']:
            print('FAIL', json.dumps(result), flush=True)
        elif len(results) % 20 == 0:
            print(f'{len(results)}/{len(sources)} source files checked', flush=True)
results.sort(key=lambda item: item['source'])
report = ROOT / 'build/windows-conformance-results.json'
report.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
failed = sum(not item['ok'] for item in results)
print(f'{sum(item["executions"] for item in results)} checks; {failed} failing source files', flush=True)
raise SystemExit(int(failed != 0))

#!/usr/bin/env python3
"""Short-lived Luce workers release ARC objects and their native bookkeeping buffers."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('compiler', nargs='?', type=Path, default=ROOT / 'build/luce')
parser.add_argument('--heap', action='store_true', help='also check native heap allocations; requires macOS and Base argument cleanup')
arguments = parser.parse_args()
COMPILER = arguments.compiler.resolve()
if arguments.heap and sys.platform != 'darwin':
    parser.error('--heap requires macOS')
FLAGS = [['--native', '--opt', str(n)] for n in range(4)] + [['--backend=c'], ['--backend=c', '--release']]
PROGRAM = '''class Node:
    let name: str
    var next: Node? = none
    func init(self, name: str):
        self.name = name

let failed = ErrorCode.package(1)

func work(value: int, fail: bool) -> str!:
    let first = Node(f"first {value}")
    let second = Node(f"second {value}")
    first.next = second
    second.next = first
    let text = [first.name, second.name].join(", ")
    if fail:
        error(failed, text)
    return text

pub func main(arguments: list[str]) -> int!:
    for value in 0..<32:
        let success = spawn work(value, false)
        let failure = spawn work(value, true)
        assert((try wait success) == f"first {value}, second {value}")
        var caught = false
        let recovered = wait failure catch problem:
            assert(problem.code == failed)
            assert(problem.message == f"first {value}, second {value}")
            caught = true
            recover ""
        assert(caught)
        assert(recovered == "")
    return 0
'''

with tempfile.TemporaryDirectory(prefix='luce-worker-heap-') as temporary:
    root = Path(temporary)
    source = root / 'main.luc'
    source.write_text(PROGRAM)
    executable = root / 'workers'
    for flags in FLAGS:
        subprocess.run([COMPILER, 'build', source, *flags, '-o', executable], cwd=ROOT, check=True, timeout=120)
        result = subprocess.run([executable], capture_output=True, timeout=30)
        assert result.returncode == 0 and not result.stdout and not result.stderr, (result.returncode, result.stdout, result.stderr)
        if arguments.heap:
            result = subprocess.run(['/usr/bin/leaks', '--quiet', '--noContent',
                '--atExit', '--', executable], capture_output=True, timeout=30)
            assert result.returncode == 0 and b'0 leaks for 0 total leaked bytes' in result.stdout and not result.stderr, (result.returncode, result.stdout, result.stderr)
        print(f'PASS worker heap: {" ".join(flags)}; 64 tasks, cycles, results and failures', flush=True)

#!/usr/bin/env python3
"""Compiled Luce defaults must work when Base-to-C translation is forbidden."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="luce-native-default-") as tmp:
    work = Path(tmp)
    source = work / "main.luc"
    source.write_text('test "native default":\n    assert(6 * 7 == 42)\n\npub func main(arguments: list[str]) -> int!:\n    print(42)\n    return 0\n')
    guard = work / "cc"
    guard.write_text("#!/usr/bin/env python3\nimport os, sys\n"
                     "if any(a.endswith('/gen.c') for a in sys.argv[1:]):\n"
                     "    sys.stderr.write('generated C blocked by native-default test\\n')\n"
                     "    sys.exit(97)\n"
                     "os.execv(os.environ['LUCE_REAL_CC'], [os.environ['LUCE_REAL_CC'], *sys.argv[1:]])\n")
    guard.chmod(0o755)
    env = dict(os.environ, LUCE_REAL_CC=shutil.which("cc"), PATH=f"{work}:{os.environ['PATH']}")

    def run(*args, expected=0):
        result = subprocess.run([sys.executable, root / "tools/run_case.py", "--expected", str(expected), "--", *map(str, args)],
                                cwd=root, env=env, capture_output=True)
        if result.returncode != expected:
            raise SystemExit(f"FAIL {args}: {result.returncode}\n{result.stdout.decode()}{result.stderr.decode()}")
        return result

    compiler = root / "build/luce"
    exe = work / "program"
    for flags in [[], ["--release"]]:
        run(compiler, "build", source, *flags, "-o", exe)
        assert run(exe).stdout == b"42\n"
    result = run(compiler, "test", source, "--build")
    assert b"1 passed" in result.stdout
    result = run(compiler, "build", source, "--backend=c", "-o", exe, expected=1)
    assert b"generated C blocked" in result.stderr
print("ok Luce native defaults: executable, release and built tests")

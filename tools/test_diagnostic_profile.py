#!/usr/bin/env python3
"""`--profile diagnostic` reaches luce-base from `build` and `test`, and on `test` it builds."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
compiler = root / "build/luce"
with tempfile.TemporaryDirectory(prefix="luce-diagnostic-") as tmp:
    work = Path(tmp)
    (work / "main.luc").write_text('test "diagnostic":\n    assert(6 * 7 == 42)\n\npub func main(arguments: list[str]) -> int!:\n    print(42)\n    return 0\n')

    def run(*args, expected=0):
        command = [sys.executable, root / "tools/run_case.py", "--expected", str(expected), "--", *map(str, args)]
        result = subprocess.run(command, cwd=work, capture_output=True)
        if result.returncode != expected:
            raise SystemExit(f"FAIL {args}: {result.returncode}\n{result.stdout.decode()}{result.stderr.decode()}")
        return result

    run(compiler, "build", "main.luc", "--profile", "diagnostic", "-o", "program")
    assert run(work / "program").stdout == b"42\n"
    # the interpreter has no profile, so asking for one runs the tests as a built program
    assert b"1 passed" in run(compiler, "test", "main.luc", "--profile", "diagnostic").stdout
    assert (work / "build/tests/main").exists(), "luce test --profile diagnostic did not build"
    # luce-base names the profiles it has
    result = run(compiler, "build", "main.luc", "--profile", "fast", "-o", "program", expected=1)
    assert b"unknown profile" in result.stderr, result.stderr
print("ok Luce diagnostic profile: build and built tests")

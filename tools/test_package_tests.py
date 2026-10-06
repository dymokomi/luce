#!/usr/bin/env python3
"""Which tests `luce test` runs, and how a failing one ends (§17.3), alike in the interpreter
and in a runner built natively and through C:

- `luce test FILE` runs the tests of the file and of the package's modules it imports;
- `--package`, which `luc test` passes, runs those of every module under the package's
  source root as well, imported or not, nested ones too, each after the modules it imports
  and the rest in the order of their paths; a dependency's tests never run;
- a false `assert` in a test fails that test and the run goes on, while one in a function a
  test calls traps and ends the run, as a trap does anywhere.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "build" / "luce"

FILES = {
    "package.prisma": (
        '#prisma 4.0\ndef package "geometry" {\n'
        '    def dependency "units" {\n        str path = "vendor/units"\n    }\n}\n'),
    "src/main.luc": (
        "import area\nfrom units import metres\n\n"
        "pub func main(arguments: list[str]) -> int!:\n"
        '    print(f"{area.square(metres.of(2))}")\n    return 0\n\n'
        'test "the entry\'s own":\n    assert(area.square(metres.of(2)) == 4)\n'),
    "src/area.luc": (
        "pub func square(side: int) -> int:\n    return side * side\n\n"
        'test "a square\'s area":\n    assert(square(3) == 9)\n'),
    "src/orphan.luc": (
        "import area\n\n"
        'test "an orphan fails":\n    assert(area.square(2) == 5, "two squared is not five")\n\n'
        'test "an orphan passes":\n    assert(area.square(1) == 1)\n'),
    "src/shapes/sides.luc": (
        "pub func triangle() -> int:\n    return 3\n\n"
        'test "a nested module\'s":\n    assert(triangle() == 3)\n'),
    "src/.hidden/ignored.luc": 'test "a hidden directory\'s":\n    assert(false)\n',
    "vendor/units/package.prisma": '#prisma 4.0\ndef package "units" {\n    str[] public = ["metres"]\n}\n',
    "vendor/units/src/metres.luc": (
        "pub func of(value: int) -> int:\n    return value\n\n"
        'test "a dependency\'s test":\n    assert(false)\n'),
    "traps/main.luc": (
        "func checked(n: int) -> int:\n    assert(n > 0)\n    return n\n\n"
        'test "a helper\'s assert traps":\n    assert(checked(-1) == -1)\n\n'
        'test "never runs":\n    assert(true)\n'),
}

IMPORTED = ["ok    a square's area", "ok    the entry's own", "2 passed"]
PACKAGE = [
    "ok    a square's area", "ok    the entry's own",
    # a module the entry does not import is named by its full path, as an imported one is
    "FAIL  an orphan fails", "      ROOT/src/orphan.luc:4:5: assert failed: two squared is not five",
    "ok    an orphan passes", "ok    a nested module's", "4 passed", "1 failed"]
RUNNERS = ([], ["--build"], ["--build", "--backend=c"])


def run(root: Path, *args: str, status: int = 0) -> subprocess.CompletedProcess:
    command = [sys.executable, str(ROOT / "tools/run_case.py"), "--expected", str(status), "--", str(COMPILER), *args]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    assert result.returncode == status, f"FAIL luce {' '.join(args)}: status {result.returncode}\n{result.stdout}{result.stderr}"
    return result


with tempfile.TemporaryDirectory(prefix="luce-package-tests-") as directory:
    root = Path(directory)
    for name, text in FILES.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    for runner in RUNNERS:
        imported = run(root, "test", "src/main.luc", *runner)
        assert imported.stdout.splitlines() == IMPORTED, f"FAIL luce test {runner}: {imported.stdout}{imported.stderr}"
        whole = run(root, "test", "src/main.luc", "--package", *runner, status=1)
        shown = whole.stdout.replace(str(root.resolve()), "ROOT")
        assert shown.splitlines() == PACKAGE, f"FAIL luce test --package {runner}: {whole.stdout}{whole.stderr}"
        trapped = run(root, "test", "traps/main.luc", *runner, status=1)
        assert trapped.stdout == "" and trapped.stderr == "trap: traps/main.luc:2:5: assert failed\n", \
            f"FAIL a helper's assert {runner}: {trapped.stdout}{trapped.stderr}"
print("ok luce test: the package's modules with --package, never a dependency's; a test's assert fails it, a helper's traps")

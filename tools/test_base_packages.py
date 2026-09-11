#!/usr/bin/env python3
"""Base dependencies must survive output relocation and generated-name collisions."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/luce"
BASE = os.environ["LUCE_BASE"]
FLAGS = [["--native", "--opt", str(level)] for level in range(4)] + [
    ["--backend=c"], ["--backend=c", "--release"]]


def run(arguments, expected=0, environment=None):
    result = subprocess.run(
        [sys.executable, ROOT / "tools/run_case.py", "--expected", str(expected),
         "--", *map(str, arguments)], cwd=ROOT, env=environment,
        capture_output=True)
    assert result.returncode == expected, result.stdout.decode() + result.stderr.decode()
    return result


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


with tempfile.TemporaryDirectory(prefix="luce-base-packages-") as temporary:
    work = Path(temporary)
    for collision in (False, True):
        package = work / ("collisions" if collision else "diamond")
        source = package / "source with spaces"
        write(package, "luce.toml", '[package]\nname = "packaging"\nsource = "source with spaces"\n')
        entry = write(source, "main.luc", "import api.boundary\n\n"
            'test "dependency closure":\n    assert(boundary.answer() == 42)\n\n'
            "pub func main(arguments: list[str]) -> int!:\n"
            "    let answer = boundary.answer\n    print(answer())\n"
            "    assert(boundary.limit == 42)\n"
            "    assert(boundary.echo(boundary.Pair(value = 42)).value == 42)\n"
            "    if true:\n        let resource = boundary.open()\n"
            "        assert(boundary.active() == 1)\n        resource.close()\n"
            "    assert(boundary.active() == 0)\n    return 0\n")
        if collision:
            write(source, "main.lucb", "pub func number() -> i64:\n    return 39\n")
            write(source, "rt/heap.lucb", "pub func number() -> i64:\n    return 1\n")
            write(source, "__luce_main_0.lucb", "pub func number() -> i64:\n    return 1\n")
            write(source, "__luce_runtime_0/marker.lucb", "pub func number() -> i64:\n    return 1\n")
            write(source, "api/boundary.lucb", "import main as data\nimport rt.heap\n"
                  "import __luce_main_0 as occupied\nimport __luce_runtime_0.marker\n"
                  "pub func answer() -> i64:\n"
                  "    return data.number() + heap.number() + occupied.number() + marker.number()\n")
            emitted_entry = "__luce_main_1.lucb"
        else:
            write(source, "shared.lucb", "pub func number() -> i64:\n    return 20\n")
            write(source, "internal/left.lucb", "import shared\n"
                  "pub func number() -> i64:\n    return shared.number()\n")
            write(source, "internal/right.lucb", "import shared\n"
                  "pub func number() -> i64:\n    return shared.number() + 2\n")
            write(source, "api/boundary.lucb", "import internal.left\nimport internal.right\n"
                  "pub func answer() -> i64:\n    return left.number() + right.number()\n")
            emitted_entry = "main.lucb"
        boundary = source / "api/boundary.lucb"
        boundary.write_text(boundary.read_text() + "\n"
            "pub let limit: i64 = 42\n\n"
            "pub struct Pair:\n    pub var value: i64\n\n"
            "pub func echo(value: Pair) -> Pair:\n    return value\n\n"
            "pub handle Token:\n    destroy close\n\n"
            "var live: i64 = 0\n\n"
            "pub func open() -> Token:\n    live += 1\n    return (Token)(void*)(usize)1\n\n"
            "pub func close(token: Token):\n    live -= 1\n\n"
            "pub func active() -> i64:\n    return live\n")
        output = work / "outputs" / package.name / "program"
        output.parent.mkdir(parents=True)
        original = {str(path.relative_to(source)): path.read_bytes() for path in source.rglob("*.lucb")}
        for flags in FLAGS:
            run([COMPILER, "build", entry, *flags, "-o", output])
            assert not Path(str(output) + ".base").exists(), "normal builds retained generated Base"
            assert run([output]).stdout == b"42\n"
            report = run([COMPILER, "test", entry, "--build", *flags])
            assert b"1 passed" in report.stdout
        kept = run([COMPILER, "build", entry, "--emit=base", "-o", output])
        assert kept.stdout == f"wrote {output}.base/{emitted_entry}\n".encode()
        emitted = Path(str(output) + ".base")
        for name, data in original.items():
            assert (emitted / name).read_bytes() == data, f"source changed: {name}"
        relocated = work / "relocated" / package.name
        relocated.parent.mkdir(exist_ok=True)
        shutil.move(emitted, relocated)
        # Successful rebuilding must not rely on the resolver finding originals
        # in a parent directory, nor on an absolute path into that source tree.
        shutil.rmtree(package)
        for flags in FLAGS:
            run([BASE, "build", relocated / emitted_entry, *flags, "-o", output])
            assert run([output]).stdout == b"42\n"
        print(f"PASS Base package {'collisions' if collision else 'diamond'}: all six modes, built tests, relocation", flush=True)

    source = work / "conflict"
    entry = write(source, "main.luc", "import a.first\nimport b.second\n"
                  "pub func main(arguments: list[str]) -> int!:\n"
                  "    print(first.number(), second.number())\n    return 0\n")
    for directory, module, number in [("a", "first", 1), ("b", "second", 2)]:
        write(source, f"{directory}/shared.lucb", f"pub func number() -> i64:\n    return {number}\n")
        write(source, f"{directory}/{module}.lucb", "import shared\n"
              "pub func number() -> i64:\n    return shared.number()\n")
    rejected = run([COMPILER, "build", entry, "-o", work / "ambiguous"], expected=1)
    assert b"conflicting Base module shared" in rejected.stderr
    assert not (work / "ambiguous.base").exists()
    print("PASS conflicting dependency names are diagnosed before package output")

    # A compiler protocol mismatch must be an explicit failure, never an incomplete
    # package that happens to compile by finding source in a parent directory.
    wrapper = work / "base-protocol-probe"
    wrapper.write_text(f"#!{sys.executable}\nimport os, sys\n"
                      "if sys.argv[1] == 'dependencies':\n"
                      "    sys.stdout.buffer.write(bytes.fromhex(os.environ['DEPENDENCY_RESPONSE']))\n"
                      "else:\n    os.execv(os.environ['REAL_BASE'], [os.environ['REAL_BASE'], *sys.argv[1:]])\n")
    wrapper.chmod(0o755)
    responses = [
        (b"wrong-version\0", b"unsupported dependency format"),
        (b"luce-base-dependencies-v3\0source\0shared\0unterminated", b"truncated dependency record"),
        (b"luce-base-dependencies-v3\0source\0../invalid\0unused\0", b"invalid source dependency"),
    ]
    for response, message in responses:
        environment = dict(os.environ, LUCE_BASE=str(wrapper), REAL_BASE=str(BASE),
                           DEPENDENCY_RESPONSE=response.hex())
        rejected = run([COMPILER, "build", entry, "-o", work / "invalid-response"],
                       expected=1, environment=environment)
        assert message in rejected.stderr, rejected.stderr
        assert not (work / "invalid-response.base").exists()
    print("PASS malformed dependency protocols are rejected before package output")

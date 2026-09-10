#!/usr/bin/env python3
"""Build products survive; generated packages and partial workspaces do not."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = (Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/luce").resolve()
BASE = Path(os.environ["LUCE_BASE"]).resolve()

with tempfile.TemporaryDirectory(prefix="luce-build-cleanup-") as temporary:
    work = Path(temporary)
    scratch = work / "temporary files"
    scratch.mkdir()
    environment = dict(os.environ, LUCE_BASE=str(BASE), TMPDIR=str(scratch))

    def run(arguments, expected=0, env=None):
        result = subprocess.run(list(map(str, arguments)), cwd=work,
            env=env or environment, capture_output=True, timeout=120)
        assert result.returncode == expected, (arguments, result.returncode, result.stdout, result.stderr)
        return result

    def clean():
        # Host tools may keep their own caches here (macOS xcrun_db). The Luce
        # workspace and every generated Base source must still be gone.
        assert not list(scratch.glob("luce-build-*")), list(scratch.iterdir())
        assert not list(scratch.rglob("*.lucb")), list(scratch.rglob("*.lucb"))

    source = work / "main.luc"
    source.write_text('test "cleanup":\n    assert(6 * 7 == 42)\n\n'
        'pub func main(arguments: list[str]) -> int!:\n    print(42)\n    return 0\n')
    output = work / "products with spaces" / "nested" / "program"
    run([COMPILER, "build", source, "-o", output])
    assert run([output]).stdout == b"42\n"
    assert list(output.parent.iterdir()) == [output]
    clean()
    result = run([COMPILER, "test", source, "--build"])
    assert b"1 passed" in result.stdout
    assert list((work / "build/tests").iterdir()) == [work / "build/tests/main"]
    clean()

    # Explicit emission remains inspectable and rebuildable. A later ordinary
    # build must not adopt or remove a directory it did not create.
    emitted = Path(str(output) + ".base")
    run([COMPILER, "build", source, "--emit=base", "-o", output])
    original = {p.relative_to(emitted): p.read_bytes() for p in emitted.rglob("*") if p.is_file()}
    assert Path("main.lucb") in original and Path("rt/heap.lucb") in original
    run([COMPILER, "build", source, "-o", output])
    assert original == {p.relative_to(emitted): p.read_bytes() for p in emitted.rglob("*") if p.is_file()}
    clean()

    missing = dict(environment, LUCE_BASE=str(work / "missing-compiler"))
    result = run([COMPILER, "build", source, "-o", output], expected=1, env=missing)
    assert b"cannot be run" in result.stderr
    clean()
    assert run([output]).stdout == b"42\n"

    outside = work / "unrelated"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("owned by the caller")
    records = work / "workspace-records"
    records.mkdir()
    wrapper = work / "base-probe"
    wrapper.write_text(f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import sys
import time
assert sys.argv[1] == "build", sys.argv
workspace = Path(sys.argv[2]).parent
assert workspace.parent == Path(os.environ["TMPDIR"])
assert workspace.stat().st_mode & 0o777 == 0o700
(Path(os.environ["WORKSPACE_RECORDS"]) / str(os.getpid())).write_text(str(workspace))
extra = workspace / "partial" / "nested"
extra.mkdir(parents=True)
(extra / "junk.o").write_bytes(b"partial output")
(extra / "link").symlink_to(os.environ["OUTSIDE"])
(extra / "dangling").symlink_to("missing")
if os.environ.get("FAIL_BUILD") == "1":
    sys.stderr.write("deliberate Base failure\\n")
    sys.exit(42)
time.sleep(.1)
os.execv(os.environ["REAL_BASE"], [os.environ["REAL_BASE"], *sys.argv[1:]])
''')
    wrapper.chmod(0o755)
    probe = dict(environment, LUCE_BASE=str(wrapper), REAL_BASE=str(BASE),
        WORKSPACE_RECORDS=str(records), OUTSIDE=str(outside))
    failed = dict(probe, FAIL_BUILD="1")
    result = run([COMPILER, "build", source, "-o", output], expected=1, env=failed)
    assert b"deliberate Base failure" in result.stderr and b"--emit=base" in result.stderr
    clean()
    result = run([COMPILER, "test", source, "--build"], expected=1, env=failed)
    assert b"deliberate Base failure" in result.stderr
    clean()
    assert sentinel.read_text() == "owned by the caller"
    assert list(outside.iterdir()) == [sentinel]

    def parallel(index):
        binary = work / "parallel" / f"program-{index}"
        run([COMPILER, "build", source, "-o", binary], env=probe)
        assert run([binary]).stdout == b"42\n"

    with ThreadPoolExecutor(max_workers=3) as builders:
        list(builders.map(parallel, range(3)))
    clean()
    used = [record.read_text() for record in records.iterdir()]
    assert len(used) == 5 and len(set(used)) == 5, used
    assert all(not Path(path).exists() for path in used)
    assert sentinel.read_text() == "owned by the caller"
    assert sorted(p.name for p in (work / "parallel").iterdir()) == ["program-0", "program-1", "program-2"]

print("PASS clean builds: executables, built tests, failures, explicit emission, independent workspaces")

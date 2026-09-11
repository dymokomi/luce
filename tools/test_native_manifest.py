#!/usr/bin/env python3
"""Native link settings survive normal builds, built tests, and explicit emission."""
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/luce"


def run(arguments):
    result = subprocess.run(list(map(str, arguments)), capture_output=True, timeout=120)
    assert result.returncode == 0, (arguments, result.stdout, result.stderr)
    return result.stdout


with tempfile.TemporaryDirectory(prefix="luce-native-manifest-") as temporary:
    project = Path(temporary)
    source = project / "source"
    source.mkdir()
    mac = platform.system() == "Darwin"
    native = '[native]\nframeworks = ["Foundation"]\n' if mac else '[native]\nlibraries = ["m"]\n'
    manifest = project / "luce.toml"
    manifest.write_text('[package]\nname = "native_manifest"\nsource = "source"\n\n' + native)
    if mac:
        boundary = 'extern func NSPageSize() -> usize\npub func answer() -> i64:\n    return 42 if NSPageSize() > 0 else 0\n'
    else:
        boundary = 'extern func cos(x: f64) -> f64\npub func answer() -> i64:\n    return 42 if cos(0.0) == 1.0 else 0\n'
    (source / "native.lucb").write_text(boundary)
    entry = source / "main.luc"
    entry.write_text('import native\ntest "native linkage":\n    assert(native.answer() == 42)\n\npub func main(arguments: list[str]) -> int!:\n    print(native.answer())\n    return 0\n')
    output = project / "products/app"
    for opt in range(4):
        run([COMPILER, "build", entry, "--native", "--opt", opt, "-o", output])
        assert run([output]) == b"42\n"
        assert not Path(str(output) + ".base").exists()
    assert b"1 passed" in run([COMPILER, "test", entry, "--build"])
    run([COMPILER, "build", entry, "--emit=base", "-o", output])
    kept = Path(str(output) + ".base")
    assert ('frameworks = ["Foundation"]' if mac else 'libraries = ["m"]') in (kept / "luce.toml").read_text()
    run([os.environ["LUCE_BASE"], "build", kept / "main.lucb", "--native", "-o", output])
    assert run([output]) == b"42\n"
print("PASS native manifest linkage and emitted configuration")

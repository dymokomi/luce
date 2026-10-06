#!/usr/bin/env python3
"""A built program knows its package: the name its package.prisma spells and its version
reach luce-base, whose `platform.program` and `platform.program_version` carry them (what
luce-std's crash reports are named by); a program outside any package is `app`."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/luce"
IDENTITY = ("import platform\n\n"
            "## The package the program was built from.\npub func name() -> str:\n    return platform.program\n\n"
            "## That package's version.\npub func version() -> str:\n    return platform.program_version\n")
MAIN = ("import identity\n\npub func main(arguments: list[str]) -> int!:\n"
        '    print(f"{identity.name()} {identity.version()}")\n    return 0\n')


def built_output(project: Path, entry: Path) -> str:
    binary = project / "program"
    subprocess.run([str(COMPILER), "build", str(entry), "-o", str(binary)], check=True, timeout=300, env=os.environ)
    return subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=60).stdout


with tempfile.TemporaryDirectory(prefix="luce-identity-") as temporary:
    work = Path(temporary)
    package = work / "package"
    (package / "src").mkdir(parents=True)
    (package / "package.prisma").write_text('#prisma 4.0\ndef package "luce-identity" {\n    str version = "4.5.6"\n}\n')
    (package / "src/identity.lucb").write_text(IDENTITY)
    (package / "src/main.luc").write_text(MAIN)
    answer = built_output(package, package / "src/main.luc")
    assert answer == "luce-identity 4.5.6\n", answer
    loose = work / "loose"
    loose.mkdir()
    (loose / "identity.lucb").write_text(IDENTITY)
    (loose / "main.luc").write_text(MAIN)
    answer = built_output(loose, loose / "main.luc")
    assert answer == "app \n", answer
print("PASS a built program carries its package's name and version")

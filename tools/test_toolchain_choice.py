#!/usr/bin/env python3
"""Luce runs the luce-base it was built with, wherever the path puts another, and refuses one
of any other version, saying so. A decoy luce-base answering `--version` with an older
release (and leaving a mark when asked to do anything else) stands first on the path, as an
earlier install does on Windows (%LOCALAPPDATA%\\luce\\bin):

  - Luce on its own, with nothing laid out beside it, finds the compiler it was built with
    (src/support/toolchain_build.lucb), not the decoy, and builds;
  - the decoy beside Luce, as a release lays luce-base out, is refused with both versions
    named, before it is asked to compile anything;
  - the decoy named by LUCE_BASE is refused the same way.

Usage: tools/test_toolchain_choice.py   (after build.sh or tools/build_windows.py)
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXE = ".exe" if os.name == "nt" else ""
LUCE = ROOT / "build" / ("luce" + EXE)
# the compiler this Luce was built with, as the build recorded it
RECORD = (ROOT / "src/support/toolchain_build.lucb").read_text()
BASE = Path(RECORD.split('pub let base_path: str = "', 1)[1].split('"\n', 1)[0].replace("\\\\", "\\"))
BUILT_WITH = subprocess.run([str(BASE), "--version"], capture_output=True, text=True, check=True).stdout.strip()

DECOY = '''import c

extern func fopen(path: c.str, mode: c.str) -> void*?
extern func fclose(file: void*) -> i32

pub func main(arguments: str[]) -> i32:
    if arguments.length == 2 and arguments[1] == "--version":
        print("luce-base 0.23.0")
        return 0
    # asked to do anything else: leave the mark the test looks for
    if let file = fopen("MARK", "w"):
        _ = fclose(file)
    return 3
'''

with tempfile.TemporaryDirectory(prefix="luce-toolchain-") as tmp:
    work = Path(tmp)
    decoys = work / "path"
    decoys.mkdir()
    (work / "decoy.lucb").write_text(DECOY.replace("MARK", str(work / "decoy-used").replace("\\", "/")))
    subprocess.run([str(BASE), "build", str(work / "decoy.lucb"), "--native", "-o", str(decoys / ("luce-base" + EXE))], check=True)
    alone = work / "alone"
    alone.mkdir()
    shutil.copy2(LUCE, alone / ("luce" + EXE))
    beside = work / "beside"
    beside.mkdir()
    shutil.copy2(LUCE, beside / ("luce" + EXE))
    shutil.copy2(decoys / ("luce-base" + EXE), beside / ("luce-base" + EXE))
    (work / "main.luc").write_text('pub func main(arguments: list[str]) -> int!:\n    print("built with the right Base")\n    return 0\n')
    environment = {k: v for k, v in os.environ.items() if k != "LUCE_BASE"}
    environment["PATH"] = str(decoys) + os.pathsep + environment["PATH"]

    def luce(home, extra=None):
        env = dict(environment, **(extra or {}))
        return subprocess.run([str(home / ("luce" + EXE)), "build", "main.luc", "-o", str(work / ("program" + EXE))], cwd=work, env=env, capture_output=True, text=True)

    built = luce(alone)
    if built.returncode != 0 or (work / "decoy-used").exists():
        sys.exit(f"FAIL: Luce alone did not build with {BUILT_WITH} (the decoy first on the path was {'used' if (work / 'decoy-used').exists() else 'not used'}):\n{built.stderr}")
    ran = subprocess.run([str(work / ("program" + EXE))], capture_output=True, text=True)
    if ran.stdout != "built with the right Base\n":
        sys.exit(f"FAIL: the program printed {ran.stdout!r}")
    for label, home, extra in (("beside Luce", beside, None), ("named by LUCE_BASE", alone, {"LUCE_BASE": str(decoys / ("luce-base" + EXE))})):
        refused = luce(home, extra)
        if refused.returncode == 0:
            sys.exit(f"FAIL: Luce built with the decoy {label}")
        if "luce-base 0.23.0" not in refused.stderr or BUILT_WITH not in refused.stderr:
            sys.exit(f"FAIL: Luce refused the decoy {label} without naming both versions:\n{refused.stderr}")
        if (work / "decoy-used").exists():
            sys.exit(f"FAIL: the decoy {label} was asked to compile before its version was checked")
print(f"PASS Luce runs the {BUILT_WITH} it was built with and refuses another version, wherever it is")

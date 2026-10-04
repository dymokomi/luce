#!/usr/bin/env python3
"""Every complete program in the guide runs, and prints what the guide says it prints.

A ```luce block that declares `func main(` is a program. It runs in the interpreter and is
built and run as a program, and both must print the ```output block that follows it, when
there is one. A program meant to fail says so in the line before the block,
`<!-- exits 1 -->`; its output block then shows standard output followed by standard
error, as a terminal would, or the compiler's message for a program it rejects. A program that needs files
beside it names them, `<!-- with shapes.luc checksum.lucb -->`, from blocks headed
`<!-- file shapes.luc -->` earlier on the same page; one that imports a Base module is only
built, since the interpreter runs Luce alone. One that uses another package says so,
`<!-- needs luce-std -->`, and is built as a project depending on that package: the
checkout the build made under build/, or else the one beside this repository. `<!-- fragment -->` marks a block that shows part of a
program, `...` and all, though it declares `main`. `<!-- tests -->` marks a module whose
tests are the point: it is run with `luce test`, in the interpreter and built, and the
report compared with the output block. Notes combine on consecutive lines, as a rejected
program that needs a companion module, `<!-- with shapes.luc -->` above `<!-- exits 1 -->`.

Usage: tools/doc_examples.py [COMPILER] [PAGE...]
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build" / "luce"
PAGES = [Path(p).resolve() for p in sys.argv[2:]] or sorted((ROOT / "docs" / "guide").rglob("*.md"))
FENCE = re.compile(r"^```(\w*)\s*$")
NOTE = re.compile(r"^<!--\s*(exits|with|file|needs|fragment|tests)\s*(.*?)\s*-->\s*$")


def blocks(text):
    """Each fenced block with its language, its text, the notes before it by kind and its
    line."""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if m and m.group(1):
            notes = {}
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            while j >= 0 and NOTE.match(lines[j]):
                kind, value = NOTE.match(lines[j]).groups()
                notes[kind] = value
                j -= 1
            k = i + 1
            while k < len(lines) and not lines[k].startswith("```"):
                k += 1
            out.append((m.group(1), "\n".join(lines[i + 1:k]) + "\n", notes, i + 1))
            i = k + 1
            continue
        i += 1
    return out


def package(name):
    """Where the package `name` is checked out: build/ first, where ./build.sh puts the
    revision the compiler pins, then beside this repository."""
    built = ROOT / "build" / name
    return built if (built / "package.prisma").exists() else ROOT.parent / name


def run(command, work, status):
    """Run a command in `work`, its standard input empty: what it showed (with standard
    error after the output for a program meant to fail), and the finished process."""
    ran = subprocess.run(command, capture_output=True, text=True, cwd=work, timeout=120, stdin=subprocess.DEVNULL)
    shown = ran.stdout + ran.stderr if status != 0 else ran.stdout
    return shown.replace(str(work) + os.sep, ""), ran


failures = 0
checked = 0
for page in PAGES:
    found = blocks(page.read_text())
    files = {}
    for index, (language, body, notes, line) in enumerate(found):
        if "file" in notes:
            files[notes["file"]] = body
            continue
        testing = "tests" in notes
        if language != "luce" or ("func main(" not in body and not testing) or "fragment" in notes:
            continue
        status = int(notes.get("exits", "0"))
        companions = notes.get("with", "").split()
        needs = notes.get("needs", "").split()
        expected = None
        if index + 1 < len(found) and found[index + 1][0] == "output":
            expected = found[index + 1][1]
        where = f"{page.relative_to(ROOT)}:{line}"
        checked += 1
        with tempfile.TemporaryDirectory() as work:
            work = Path(work).resolve()
            for name in companions:
                (work / name).parent.mkdir(parents=True, exist_ok=True)
                (work / name).write_text(files[name])
            if needs:
                dependencies = "".join(f'    def dependency "{name}" {{\n        str path = "{package(name)}"\n    }}\n' for name in needs)
                (work / "package.prisma").write_text(f'#prisma 4.0\ndef package "example" {{\n    str source = "."\n{dependencies}}}\n')
            (work / "main.luc").write_text(body)
            if testing:
                for mode, command in (("interpreted", [str(COMPILER), "test", "main.luc"]),
                                      ("built", [str(COMPILER), "test", "main.luc", "--build"])):
                    ran = subprocess.run(command, capture_output=True, text=True, cwd=work, timeout=300, stdin=subprocess.DEVNULL)
                    shown = (ran.stdout + ran.stderr).replace(str(work) + os.sep, "")
                    if expected is not None and shown != expected:
                        print(f"FAIL {where} ({mode}): report differs\n--- expected\n{expected}--- got\n{shown}")
                        failures += 1
                continue
            runs = []
            if not needs and not any(name.endswith(".lucb") for name in companions):
                runs.append(("interpreted", [str(COMPILER), "run", "main.luc"]))
            built = subprocess.run([str(COMPILER), "build", "main.luc", "-o", "program"],
                                   capture_output=True, text=True, cwd=work)
            if built.returncode != 0:
                # a program shown to be rejected: the compiler's message is its output
                rejected = built.stderr.replace(str(work) + os.sep, "")
                if status == 0 or (expected is not None and rejected != expected):
                    print(f"FAIL {where}: does not build\n{built.stderr}")
                    failures += 1
                continue
            # run as a reader would, from its directory: its first argument is `./program`
            runs.append(("built", ["./program"]))
            for mode, command in runs:
                shown, ran = run(command, work, status)
                if ran.returncode != status:
                    print(f"FAIL {where} ({mode}): exit {ran.returncode}, expected {status}\n{ran.stdout}{ran.stderr}")
                    failures += 1
                elif expected is not None and shown != expected:
                    print(f"FAIL {where} ({mode}): output differs\n--- expected\n{expected}--- got\n{shown}")
                    failures += 1
if failures:
    sys.exit(1)
print(f"ok guide examples: {checked} programs")

#!/usr/bin/env python3
"""Exercise the current description through checked, compiled package consumers."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/luce"
BASE = os.environ["LUCE_BASE"]
FLAGS = [["--native", "--opt", str(level)] for level in range(4)] + [
    ["--backend=c"], ["--backend=c", "--release"]]


def run(arguments, expected=0):
    result = subprocess.run(list(map(str, arguments)), cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 0:
        assert not result.stderr, result.stderr
    return result


with tempfile.TemporaryDirectory(prefix="luce-description-consumer-") as temporary:
    root = Path(temporary)
    (root / "points.lucb").write_text('''pub struct Point:
    pub var x: i64

pub enum Mode as u32:
    first = 0
    second = 1
''')
    (root / "api.lucb").write_text('''import points

pub type Position = points.Point

pub struct Record:
    pub var position: points.Point
    pub var mode: points.Mode

pub func make() -> points.Point:
    return points.Point(42)

pub func read(value: points.Point) -> i64:
    return value.x

pub func flip(mode: points.Mode) -> points.Mode:
    return points.Mode.second

pub func echo(record: Record) -> Record:
    return record
''')
    entry = root / "main.luc"
    entry.write_text('''import api
import points

pub func main(arguments: list[str]) -> int!:
    var position: api.Position = api.make()
    assert(position.x == 42)
    position.x = 43
    assert(api.read(position) == 43)
    assert(api.flip(points.Mode.first) == points.Mode.second)
    let record = api.Record(position = position, mode = points.Mode.first)
    let copy = api.echo(record)
    assert(copy.position.x == 43 and copy.mode == points.Mode.first)
    return 0
''')
    for flags in FLAGS:
        run([COMPILER, "build", entry, *flags, "-o", root / "consumer"])
        run([root / "consumer"])
        assert not Path(str(root / "consumer") + ".base").exists()

    (root / "hidden.lucb").write_text('''pub struct State:
    pub var visible: i64
    var secret: i64

pub func make() -> State:
    return State(4, 99)

pub func read(value: State) -> i64:
    return value.secret
''')
    entry.write_text('''import hidden

pub func main(arguments: list[str]) -> int!:
    let value = hidden.make()
    assert(hidden.read(value) == 99)
    return 0
''')
    for flags in FLAGS:
        run([COMPILER, "build", entry, *flags, "-o", root / "consumer"])
        run([root / "consumer"])
    print("PASS foreign records/enums/aliases, nested copies and private native state; six modes")

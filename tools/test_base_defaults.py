#!/usr/bin/env python3
"""Native calls keep named arguments, Base defaults, effects and nested identities."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'build/luce'
FLAGS = [['--native', '--opt', str(level)] for level in range(4)] + [
    ['--backend=c'], ['--backend=c', '--release']]


def run(*arguments, expected=0):
    result = subprocess.run(list(map(str, arguments)), cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 0:
        assert not result.stderr, result.stderr
    return result


with tempfile.TemporaryDirectory(prefix='luce-native-defaults-') as temporary:
    root = Path(temporary)
    (root / 'points.lucb').write_text('''pub struct Point:
    pub var x: i64

pub type Position = Point
''')
    (root / 'api.lucb').write_text('''import points
import luce

let hidden: i64 = -7 // 3
let greeting = "native default"
pub let invalid: ErrorCode = ErrorCode.package(1)
pub type Position = points.Position

pub func combine(first: i64, second: i64 = hidden, label: str = greeting) -> (i64, str)!:
    if first < 0:
        error(invalid, "negative first")
    return (first * 10 + second, label)

pub func nest(value: (Position?, str)) -> (points.Point?, (str, i64)):
    return (value.0, (value.1, 99))

pub func apply(operation: func(i64) -> i64, value: i64 = 7) -> i64:
    return operation(value)

pub func signed(value: i64?) -> i64?:
    return value

pub func size(value: usize?) -> usize?:
    return value

pub func location(file: str = luce.file, function: str = luce.function) -> (str, str):
    return (file, function)
''')
    (root / 'exports.luc').write_text('''import api

pub type Position = api.Position
''')
    entry = root / 'main.luc'
    entry.write_text('''from api import combine
import api
import exports
import points

func twice(value: int) -> int:
    return value * 2

pub func main(arguments: list[str]) -> int!:
    assert((try api.combine(4)) == (38, "native default"))
    assert((try combine(label = "named", second = 5, first = 4)) == (45, "named"))
    assert((try api.combine(label = "omitted middle", first = 4)) == (38, "omitted middle"))
    let combined = api.combine
    assert((try combined(4, 6, "value")) == (46, "value"))
    let point: exports.Position = points.Point(3)
    let maybe: points.Point? = point
    let empty: points.Point? = none
    let nested = api.nest((maybe, "owned text"))
    assert((nested.0 else points.Point(0)).x == 3)
    assert(nested.1 == ("owned text", 99))
    assert(api.nest((empty, "empty")).0 == none)
    assert(api.apply(twice) == 14)
    let signed: int? = -4
    let size: int? = 8
    assert(api.signed(signed) == -4)
    assert(api.size(size) == 8)
    let (file, function) = api.location()
    assert(file == "FILE" and function == "main")
    let answer = api.combine(-1) catch failure:
        assert(failure.code == api.invalid and failure.message == "negative first")
        return 0
    return 1
'''.replace('FILE', str(entry)))
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    print('PASS native defaults, named calls, reexports, nested types and errors; six modes')

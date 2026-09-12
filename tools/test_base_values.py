#!/usr/bin/env python3
"""Real Base initialization and complete native value storage at the Luce boundary."""
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


with tempfile.TemporaryDirectory(prefix='luce-native-values-') as temporary:
    root = Path(temporary)
    (root / 'values.lucb').write_text('''pub let invalid: ErrorCode = ErrorCode.package(1)
let default_count: i64 = 7

pub struct Counter:
    var hidden: i64
    pub let label: str
    pub var shown: i64

    pub func init(label: str, count: i64 = default_count) -> !:
        if count < 0:
            error(invalid, "invalid counter")
        self.hidden = count * 3
        self.label = label
        self.shown = count

    pub func value() -> i64:
        return self.hidden

    pub mutating func increase(amount: i64 = 2) -> i64!:
        self.hidden += amount
        self.shown += amount
        if amount < 0:
            error(invalid, self.label)
        return self.hidden

    pub static func scaled(count: i64 = 3) -> Counter!:
        return try Counter("scaled", count * 2)

pub type Count = Counter

pub struct Defaults:
    pub let label: str = "field default"
    pub var count: i64

pub struct Locked:
    var hidden: i64
    func init(value: i64):
        self.hidden = value

pub func lock(value: i64) -> Locked:
    return Locked(value)

pub func unlock(value: Locked) -> i64:
    return value.hidden

pub func read(value: Counter) -> (str, i64, i64):
    return (value.label, value.hidden, value.shown)

pub func echo(value: Counter) -> Counter:
    return value

pub enum Mode as u8:
    ready = 0
    busy = 1
    pub func name() -> str:
        return "ready" if self == Mode.ready else "busy"
    pub static func initial() -> Mode:
        return Mode.ready

pub struct Borrowed:
    var text: str

pub func borrow(text: str) -> Borrowed:
    return Borrowed(text)
''')
    entry = root / 'main.luc'
    entry.write_text('''from values import Counter, Defaults
import values

func on_worker(value: Counter) -> Counter:
    assert(value.value() == 21)
    return value

func make_bound() -> func() -> int:
    let value = Counter("escaped " + str(4), 4) catch failure:
        trap(failure.message)
    return value.value

pub func main(arguments: list[str]) -> int!:
    let original = try Counter("copy " + str(1))
    assert(values.read(original) == ("copy 1", 21, 7))
    var copy = original
    copy.shown = 42
    assert(values.read(copy) == ("copy 1", 21, 42))
    assert(values.read(original) == ("copy 1", 21, 7))
    let again = values.echo(copy)
    assert(values.read(again) == ("copy 1", 21, 42))
    assert(copy == again)
    var changed = original
    discard(try changed.increase(1))
    changed.shown = 7
    assert(changed != original)
    let named = try Counter(count = 9, label = "named")
    assert(values.read(named) == ("named", 27, 9))
    assert(original.value() == 21)
    let bound = copy.value
    assert((try copy.increase()) == 23)
    assert(copy.value() == 23 and bound() == 21)
    let update = copy.increase
    assert((try update(3)) == 26)
    assert(copy.value() == 23)
    assert(make_bound()() == 12)
    let alias = try values.Count("alias", 5)
    assert(alias.value() == 15)
    assert((try values.Count.scaled()).value() == 18)
    let work = spawn on_worker(original)
    let transferred = wait work
    assert(values.read(transferred) == ("copy 1", 21, 7))
    let scaled = try Counter.scaled()
    assert(scaled.value() == 18)
    let scale = Counter.scaled
    assert((try scale(4)).value() == 24)
    let failed_update = copy.increase(-1) catch failure:
        assert(failure.code == values.invalid and failure.message == "copy 1")
        assert(copy.value() == 22 and copy.shown == 43)
        return try finish()
    return 1

func finish() -> int!:
    let mode = values.Mode.busy
    assert(mode.name() == "busy")
    let name = mode.name
    assert(name() == "busy")
    let initial = values.Mode.initial
    assert(initial() == values.Mode.ready)
    let defaults = Defaults()
    assert(defaults.label == "field default" and defaults.count == 0)
    let fields = Defaults(count = 3, label = "given")
    assert(fields.label == "given" and fields.count == 3)
    let locked = values.lock(89)
    assert(values.unlock(locked) == 89)
    assert(locked == values.lock(89) and locked != values.lock(90))
    let failed = Counter("failed", -1) catch failure:
        assert(failure.code == values.invalid and failure.message == "invalid counter")
        return 0
    return 1
''')
    for flags in FLAGS:
        run(COMPILER, 'build', entry, *flags, '-o', root / 'consumer')
        run(root / 'consumer')
    for expression, message, result in [
        ('values.Locked(3)', 'private initializer', 'int!'),
        ('values.borrow("temporary")', 'has no `borrow`', 'int!'),
        ('Counter("hidden", hidden = 4)', 'no parameter or field named', 'int!'),
        ('Counter("unchecked")', 'this operation can fail', 'int')]:
        entry.write_text(f'''from values import Counter
import values
func value_result() -> {result}:
    let value = {expression}
    return 0
pub func main(arguments: list[str]) -> int!:
    return value_result()
''')
        failure = run(COMPILER, 'check', entry, expected=1)
        assert message in failure.stderr, failure.stderr
    print('PASS native value constructors, private state, text ownership and rejected crossings; six modes')

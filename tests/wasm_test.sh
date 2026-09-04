#!/bin/sh
# Execute WebAssembly modules the compiler built, under wasmtime, and compare
# with what the language says they must do. The unit tests pin the bytes;
# this script proves the bytes run. Skipped when wasmtime is not installed.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

if ! command -v wasmtime >/dev/null 2>&1; then
    echo "wasm: wasmtime not installed, skipping execution test"
    exit 0
fi

luce=${1:-./stage0/bin/luce-0}
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/luce-wasm.XXXXXX")
trap 'rm -rf -- "$test_dir"' EXIT HUP INT TERM

"$luce" build src/luce.luc -o "$test_dir/luce"
cli=$test_dir/luce
runtime_source=src/runtime/allocator.lucn
runtime_root=src/runtime

# expect STATUS EXPECTED_OUTPUT COMMAND...
expect() {
    wanted_status=$1; wanted_output=$2; shift 2
    set +e
    output=$("$@" 2>/dev/null); status=$?
    set -e
    if [ "$status" != "$wanted_status" ]; then
        echo "wasm: '$*' exited $status, expected $wanted_status" >&2
        echo "$output" >&2
        exit 1
    fi
    if [ "$output" != "$wanted_output" ]; then
        echo "wasm: '$*' printed '$output', expected '$wanted_output'" >&2
        exit 1
    fi
}

# A process entry: output through WASI fd_write, exit status through proc_exit.
"$cli" build --package org.luce.tests --root examples/full --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/hello.wasm" examples/full/hello.luc >/dev/null
expect 0 "Hello, world!" wasmtime run "$test_dir/hello.wasm"

printf 'pub func main(arguments: slice[str]) -> i32!:\n    print("one")\n    print("two")\n    return 3 * 2\n' > "$test_dir/status.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/status.wasm" "$test_dir/status.luc" >/dev/null
expect 6 "one
two" wasmtime run "$test_dir/status.wasm"

printf 'pub func main(arguments: slice[str]) -> i32!:\n    if arguments.length != 3u64: return 1\n    if arguments[1u64] != "alpha": return 2\n    if arguments[2u64] != "two words": return 3\n    print(arguments[2u64])\n    return 0\n' > "$test_dir/arguments.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/arguments.wasm" "$test_dir/arguments.luc" >/dev/null
expect 0 "two words" wasmtime run "$test_dir/arguments.wasm" alpha "two words"

printf 'let invalid: ErrorCode = ErrorCode.package(1)\npub func main(arguments: slice[str]) -> i32!: error(invalid, "failed")\n' > "$test_dir/entry_failure.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/entry_failure.wasm" "$test_dir/entry_failure.luc" >/dev/null
expect 1 "" wasmtime run "$test_dir/entry_failure.wasm"

# Exported functions: wasmtime invokes them by name and prints the result.
"$cli" build --package org.luce.tests --root examples/full --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/core.wasm" examples/full/compiled_core/main.luc >/dev/null
expect 0 "42" wasmtime run --invoke compiled_core.main.answer "$test_dir/core.wasm"

printf 'pub func answer() -> i64: return (2 + 3) * 4 - 6\npub func narrow() -> i32: return 2147483646i32 + 1i32\n' > "$test_dir/math.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/math.wasm" "$test_dir/math.luc" >/dev/null
expect 0 "14" wasmtime run --invoke math.answer "$test_dir/math.wasm"
expect 0 "2147483647" wasmtime run --invoke math.narrow "$test_dir/math.wasm"

# Slice 3a: locals, every operator family, narrow widths, conditionals. The
# same programs are oracle-checked in tests/common/differential_test.luc;
# here the wasm bytes actually run. (wasmtime prints i32 results signed, so
# wide unsigned values stay in the unit tests.)
cat > "$test_dir/scalars.luc" <<'LUCE'
pub func locals() -> i64:
    let a = 40
    var b = 1
    b += 1
    return a + b
pub func compound() -> i64:
    var v = 100
    v -= 58
    v *= 3
    v //= 2
    v %= 50
    return v
pub func bits() -> i64:
    var v = 0b1100
    v &= 0b1010
    v |= 1
    v ^= 0b1000
    v <<= 2
    v >>= 1
    return v
pub func floor_negative() -> i64: return 7 // -2
pub func rem_negative() -> i64: return 7 % -2
pub func floor_left() -> i64: return -7 // 2
pub func rem_left() -> i64: return -7 % 2
pub func rem_minimum() -> i64: return (-9223372036854775807 - 1) % -1
pub func shift_left() -> i64: return 1 << 62
pub func shift_right() -> i64: return -16 >> 2
pub func bit_not() -> i64: return ~5
pub func narrow_i8() -> i8:
    let v: i8 = -128
    return v + 127
pub func narrow_u8() -> u8:
    let v: u8 = 200
    return v + 55
pub func narrow_u16() -> u16:
    let v: u16 = 65535
    return v - 1
pub func narrow_shift_signed() -> i8:
    let v: i8 = 1
    return v << 7
pub func narrow_shift_unsigned() -> u8:
    let v: u8 = 1
    return v << 7
pub func narrow_not() -> u8:
    let v: u8 = 0
    return ~v
pub func conditional() -> i64:
    let x = 5
    return (10 if x == 5 else 20) + (1 if x != 5 else 2)
pub func short_and() -> i64: return 1 if false and 1 // 0 == 0 else 0
pub func short_or() -> i64: return 1 if true or 1 // 0 == 0 else 0
pub func chars() -> i64: return 1 if 'a' < 'b' and 'z' == 'z' else 0
pub func floats() -> i64: return 1 if 7.0 / 2.0 == 3.5 and 1.5f32 * 2.0f32 == 3.0f32 else 0
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/scalars.wasm" "$test_dir/scalars.luc" >/dev/null
check() { expect 0 "$2" wasmtime run --invoke "scalars.$1" "$test_dir/scalars.wasm"; }
check locals 42
check compound 13
check bits 2
check floor_negative -4
check rem_negative -1
check floor_left -4
check rem_left 1
check rem_minimum 0
check shift_left 4611686018427387904
check shift_right -4
check bit_not -6
check narrow_i8 -1
check narrow_u8 255
check narrow_u16 65534
check narrow_shift_signed -128
check narrow_shift_unsigned 128
check narrow_not 255
check conditional 12
check short_and 0
check short_or 1
check chars 1
check floats 1

# Slice 3b: loops, branches, early exits.
cat > "$test_dir/flow.luc" <<'LUCE'
pub func sum_to_ten() -> i64:
    var total = 0
    var i = 1
    while i <= 10:
        total += i
        i += 1
    return total
pub func break_continue() -> i64:
    var i = 0
    var hits = 0
    while true:
        i += 1
        if i > 100: break
        if i % 2 == 0: continue
        hits += 1
    return hits
pub func nested() -> i64:
    var outer = 0
    var count = 0
    while outer < 5:
        outer += 1
        var inner = 0
        while inner < 5:
            inner += 1
            if inner == 3: break
            if outer == 2: continue
            count += 1
    return count
pub func chain() -> i64:
    let x = 7
    if x < 3:
        return 1
    elif x < 6:
        return 2
    elif x < 9:
        return 3
    else:
        return 4
pub func early_return() -> i64:
    var i = 0
    while i < 1000:
        if i * i > 300:
            if i % 2 == 1:
                return i
        i += 1
    return -1
pub func fibonacci() -> i64:
    var a = 0
    var b = 1
    var n = 0
    while n < 30:
        let next = a + b
        a = b
        b = next
        n += 1
    return a
pub func collatz() -> i64:
    var n = 27
    var steps = 0
    while n != 1:
        if n % 2 == 0:
            n //= 2
        else:
            n = 3 * n + 1
        steps += 1
    return steps
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/flow.wasm" "$test_dir/flow.luc" >/dev/null
flow() { expect 0 "$2" wasmtime run --invoke "flow.$1" "$test_dir/flow.wasm"; }
flow sum_to_ten 55
flow break_continue 50
flow nested 8
flow chain 3
flow early_return 19
flow fibonacci 832040
flow collatz 111

# Slice 3c: parameters, calls, recursion, constants, and a two-module build.
cat > "$test_dir/calls.luc" <<'LUCE'
func factorial(n: i64) -> i64:
    if n <= 1: return 1
    return n * factorial(n - 1)
pub func fact10() -> i64: return factorial(10)
func fib(n: i64) -> i64:
    if n < 2: return n
    return fib(n - 1) + fib(n - 2)
pub func fib20() -> i64: return fib(20)
func mix(a: i8, b: u16, c: i64, d: bool) -> i64:
    var total = c
    if d: total += 1
    if a < 0: total -= 3
    if b == 65535: total += 65535
    return total
pub func mixed() -> i64: return mix(-3, 65535, 1000, true) + mix(5, 1, 0, false)
let base = 40
let extra: i64 = base + 1
pub func constants() -> i64: return extra + 1
func pick(first: i64, second: i64, third: i64) -> i64: return first * 100 + second * 10 + third
pub func named() -> i64: return pick(third = 3, first = 1, second = 2)
func ackermann(m: i64, n: i64) -> i64:
    if m == 0: return n + 1
    if n == 0: return ackermann(m - 1, 1)
    return ackermann(m - 1, ackermann(m, n - 1))
pub func ack() -> i64: return ackermann(2, 3)
func forever(n: i64) -> i64: return forever(n + 1) + 1
pub func overflow_stack() -> i64: return forever(0)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/calls.wasm" "$test_dir/calls.luc" >/dev/null
calls() { expect 0 "$2" wasmtime run --invoke "calls.$1" "$test_dir/calls.wasm"; }
calls fact10 3628800
calls fib20 6765
calls mixed 66533
calls constants 42
calls named 123
calls ack 9
set +e
wasmtime run --invoke calls.overflow_stack "$test_dir/calls.wasm" >/dev/null 2>&1; status=$?
set -e
if [ "$status" = 0 ]; then
    echo "wasm: unbounded recursion exited 0, expected a trap" >&2
    exit 1
fi

# Cross-module visibility and an exact ordinary function value execute through
# Wasm's function table without requiring managed runtime services.
printf 'pub let scale: i64 = 3\npub func double(x: i64) -> i64: return x * 2\nfunc hidden(x: i64) -> i64: return x + 1\npub func nudge(x: i64) -> i64: return hidden(x)\npub struct Pair:\n    pub let a: i64\n    pub let b: i64\n    pub func sum(self) -> i64: return self.a + self.b\n' > "$test_dir/math.luc"
printf 'import math\nfrom math import nudge\npub func answer() -> i64:\n    let p = math.Pair(a = 1, b = 2)\n    let operation: func(i64) -> i64 = math.double\n    return operation(20) + nudge(1) + p.sum()\n' > "$test_dir/main.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/modules.wasm" "$test_dir/math.luc" "$test_dir/main.luc" >/dev/null
expect 0 "45" wasmtime run --invoke main.answer "$test_dir/modules.wasm"

# The complete function-value example also exercises recoverable failure, so
# it names the same explicit sealed runtime as every installed product build.
"$cli" build --package org.luce.tests --root examples/full --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/function_values.wasm" examples/full/function_values.luc >/dev/null
expect 0 "42" wasmtime run --invoke function_values.answer "$test_dir/function_values.wasm"
expect 0 "" wasmtime run "$test_dir/function_values.wasm"

# Structs and methods: construction with defaults, field places, mutating
# methods writing through the caller's slot, type functions.
cat > "$test_dir/structs.luc" <<'LUCE'
struct Point:
    let x: i64
    let y: i64
pub func fields() -> i64:
    let p = Point(x = 3, y = 4)
    return p.x * 10 + p.y
struct Style:
    let width: i64 = 7
    let depth: i64
pub func defaults() -> i64:
    let s = Style(depth = 2)
    let t = Style(1, 2)
    return s.width * 10 + s.depth + t.width * 100
struct Cursor:
    var position: i64
pub func field_assignment() -> i64:
    var c = Cursor(position = 1)
    c.position = 5
    c.position += 10
    return c.position
struct Counter:
    var count: i64
    func origin() -> Counter: return Counter(count = 100)
    func doubled(self) -> i64: return self.count * 2
    mutating func bump(self, by: i64): self.count += by
pub func methods() -> i64:
    var c = Counter.origin()
    c.bump(by = 5)
    c.bump(1)
    return c.doubled()
struct Inner:
    var value: i64
    mutating func set(self, v: i64): self.value = v
struct Outer:
    var inner: Inner
    let tag: i64
pub func nested() -> i64:
    var o = Outer(inner = Inner(value = 1), tag = 3)
    o.inner.value = 20
    o.inner.set(o.inner.value + 1)
    return o.inner.value + o.tag
struct P:
    let x: i64
    let y: i64
func find(flag: bool) -> P?:
    if flag: return P(x = 1, y = 2)
    return none
pub func equality() -> i64:
    let a = P(x = 1, y = 2)
    let b = find(true) else P(x = 0, y = 0)
    let c = find(false) else P(x = 0, y = 0)
    var n = 0
    if a == b: n += 1
    if a != c: n += 10
    let (p, q) = (a, c)
    if p == a and q == c: n += 100
    return n
struct V:
    var x: i64
    var y: i64
    func sum(self) -> i64: return self.x + self.y
    func plus(self, other: V) -> V: return V(x = self.x + other.x, y = self.y + other.y)
    mutating func reset(self): self = V(x = 0, y = 0)
    mutating func add(self, other: V): self = self.plus(other)
func total(v: V) -> i64: return v.sum()
pub func self_replacement() -> i64:
    var v = V(x = 1, y = 2)
    v.add(V(x = 10, y = 20))
    let t = total(v)
    v.reset()
    return t * 10 + v.sum()
func scale(value: i64, factor: i64 = 3, offset: i64 = -1) -> i64: return value * factor + offset
pub func parameter_defaults() -> i64: return scale(2) + scale(2, 10) + scale(2, offset = 5)
struct CustomPair:
    let left: i64
    let right: i64
    func init(self, value: i64, swap: bool = false):
        if swap:
            self.left = value + 1
            self.right = value
        else:
            self.left = value
            self.right = value + 1
pub func custom_init() -> i64:
    let normal = CustomPair(3)
    let swapped = CustomPair(value = 8, swap = true)
    return normal.left * 1000 + normal.right * 100 + swapped.left * 10 + swapped.right
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/structs.wasm" "$test_dir/structs.luc" >/dev/null
structs() { expect 0 "$2" wasmtime run --invoke "structs.$1" "$test_dir/structs.wasm"; }
structs fields 34
structs defaults 172
structs field_assignment 15
structs methods 212
structs nested 24
structs equality 111
structs self_replacement 330
structs parameter_defaults 35
structs custom_init 3498

printf 'struct Named:\n    let name: str\n    var count: i64\npub func main(arguments: slice[str]) -> i32!:\n    var n = Named(name = "luce", count = 1)\n    print(n.name)\n    n.count += 1\n    return 0\n' > "$test_dir/struct_print.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/struct_print.wasm" "$test_dir/struct_print.luc" >/dev/null
expect 0 "luce" wasmtime run "$test_dir/struct_print.wasm"

# Milestone 4: tuples, optionals, owned strings, and print of a value.
# Owner-backed strings and bytes require the explicitly composed sealed runtime
# and execute through Wasmtime in tests/common/examples_test.luc.
cat > "$test_dir/composites.luc" <<'LUCE'
func pair() -> (i64, i64): return (3, 4)
pub func destructure() -> i64:
    let (a, b) = pair()
    return a * 10 + b
pub func nested() -> i64:
    let t = ((1, 2), (3, (4, 5)))
    let (x, y) = t
    let (p, q) = y
    let (r, s) = q
    let (m, n) = x
    return m + n + p + r + s
pub func tuple_equality() -> i64:
    let a = (1, true, 2.5)
    let b = (1, true, 2.5)
    let c = (1, false, 2.5)
    var n = 0
    if a == b: n += 1
    if a != c: n += 10
    if a == c: n += 100
    return n
func sum(p: (i64, i64)) -> i64:
    let (a, b) = p
    return a + b
pub func tuple_parameter() -> i64: return sum((20, 22))
pub func tuple_reassign() -> i64:
    var t = (1, 2)
    let (a, b) = t
    t = (b, a)
    let (c, d) = t
    return c * 10 + d
func maybe(flag: bool) -> i64?:
    if flag: return 7
    return none
pub func optional_else() -> i64: return (maybe(true) else 0) * 10 + (maybe(false) else 3)
pub func optional_equality() -> i64:
    let a: i64? = 5
    let b: i64? = 5
    let c: i64? = none
    let d: i64? = none
    var n = 0
    if a == b: n += 1
    if a != c: n += 10
    if c == d: n += 100
    return n
func find(flag: bool) -> (i64, i64)?:
    if flag: return (1, 2)
    return none
pub func optional_tuple() -> i64:
    let (a, b) = find(true) else (9, 9)
    let (c, d) = find(false) else (9, 9)
    return a + b + c + d
pub func optional_loop() -> i64:
    var best: i64? = none
    var i = 0
    while i < 5:
        if i == 3: best = i
        i += 1
    return best else -1
func conditional_read(value: i64?) -> i64:
    if let present = value:
        return present
    else:
        return 5
pub func conditional_binding() -> i64: return conditional_read(37) + conditional_read(none)
pub func string_equality() -> i64:
    let a = "hello"
    let b = "hello"
    let c = "help"
    let d = "hell"
    var n = 0
    if a == b: n += 1
    if a != c: n += 10
    if a == d: n += 100
    if "" == "": n += 1000
    return n
func pick(flag: bool) -> str:
    if flag: return "yes"
    return "no"
func is_yes(s: str) -> bool: return s == "yes"
pub func string_values() -> i64: return (1 if is_yes(pick(true)) else 0) + (2 if is_yes(pick(false)) else 0)
pub func string_in_tuple() -> i64:
    let a = ("x", 1)
    let b = ("x", 1)
    let c = ("y", 1)
    return (1 if a == b else 0) + (2 if a == c else 0)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/composites.wasm" "$test_dir/composites.luc" >/dev/null
composite() { expect 0 "$2" wasmtime run --invoke "composites.$1" "$test_dir/composites.wasm"; }
composite destructure 34
composite nested 15
composite tuple_equality 11
composite tuple_parameter 42
composite tuple_reassign 21
composite optional_else 73
composite optional_equality 111
composite optional_tuple 21
composite optional_loop 3
composite conditional_binding 42
composite string_equality 1011
composite string_values 1
composite string_in_tuple 1

printf 'func pick() -> str: return "yes"\npub func main(arguments: slice[str]) -> i32!:\n    let greeting = "hi there"\n    print(greeting)\n    print(pick())\n    print("done")\n    return 0\n' > "$test_dir/print_value.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/print_value.wasm" "$test_dir/print_value.luc" >/dev/null
expect 0 "hi there
yes
done" wasmtime run "$test_dir/print_value.wasm"

# Enums and `match`: the same programs as the enum fixtures in
# tests/common/differential_test.luc, executed.
cat > "$test_dir/enum_directions.luc" <<'LUCE'
enum Direction:
    north
    east
    south
    west
func turn(d: Direction) -> i64:
    match d:
        .north: return 1
        .east: return 2
        .south, .west: return 3
pub func answer() -> i64: return turn(Direction.north) * 100 + turn(.east) * 10 + turn(Direction.west)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_directions.wasm" "$test_dir/enum_directions.luc" >/dev/null
expect 0 "123" wasmtime run --invoke enum_directions.answer "$test_dir/enum_directions.wasm"

cat > "$test_dir/enum_commands.luc" <<'LUCE'
enum Command:
    open(path: i64)
    resize(width: i64, height: i64)
    quit
func size(c: Command) -> i64:
    return match c:
        .open(path) => path
        .resize(width, height) => width * height
        .quit => -1
pub func answer() -> i64: return size(Command.open(path = 7)) + size(Command.resize(3, 4)) + size(.quit)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_commands.wasm" "$test_dir/enum_commands.luc" >/dev/null
expect 0 "18" wasmtime run --invoke enum_commands.answer "$test_dir/enum_commands.wasm"

cat > "$test_dir/enum_moves.luc" <<'LUCE'
enum Move:
    left(steps: i64)
    right(steps: i64)
    stop
func amount(m: Move) -> i64:
    match m:
        .left(steps), .right(steps): return steps
        .stop: return 0
pub func answer() -> i64: return amount(.left(5)) + amount(Move.right(steps = 6)) + amount(.stop)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_moves.wasm" "$test_dir/enum_moves.luc" >/dev/null
expect 0 "11" wasmtime run --invoke enum_moves.answer "$test_dir/enum_moves.wasm"

cat > "$test_dir/enum_shapes.luc" <<'LUCE'
enum Shape:
    circle(radius: i64)
    square(side: i64)
    dot
func find(flag: bool) -> Shape?:
    if flag: return .circle(3)
    return none
pub func answer() -> i64:
    let a = Shape.circle(3)
    let b = find(true) else .dot
    let c = find(false) else .dot
    var n = 0
    if a == b: n += 1
    if a != c: n += 10
    if c == Shape.dot: n += 100
    if Shape.square(2) != Shape.square(3): n += 1000
    return n
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_shapes.wasm" "$test_dir/enum_shapes.luc" >/dev/null
expect 0 "1111" wasmtime run --invoke enum_shapes.answer "$test_dir/enum_shapes.wasm"

cat > "$test_dir/enum_scalars.luc" <<'LUCE'
func classify(v: i64) -> i64:
    match v:
        0: return 0
        1, 2: return 1
        3..<10: return 2
        10..=20: return 3
        -5..=-1: return 4
        _: return 5
func opt(v: i64?) -> i64:
    match v:
        .some(x): return x * 2
        .none: return -1
func flag(b: bool) -> i64:
    match b:
        true: return 1
        false: return 0
func letter(c: char) -> i64:
    return match c:
        'a'..='z' => 1
        '0'..='9' => 2
        _ => 3
func word(s: str) -> i64:
    return match s:
        "yes" => 1
        "no" => 0
        _ => -1
pub func answer() -> i64:
    return classify(0) + classify(2) * 10 + classify(7) * 100 + classify(15) * 1000 + classify(-3) * 10000 + classify(99) * 100000 + opt(4) + opt(none) + flag(true) + letter('q') + letter('5') + letter('!') + word("yes") + word("maybe")
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_scalars.wasm" "$test_dir/enum_scalars.luc" >/dev/null
expect 0 "543224" wasmtime run --invoke enum_scalars.answer "$test_dir/enum_scalars.wasm"

cat > "$test_dir/enum_lights.luc" <<'LUCE'
enum Light:
    red
    green
    func next(self) -> Light:
        match self:
            .red: return .green
            .green: return .red
    func start() -> Light: return .red
pub func answer() -> i64:
    var l = Light.start()
    var i = 0
    var greens = 0
    while i < 7:
        i += 1
        l = l.next()
        match l:
            .green:
                greens += 1
                continue
            .red:
                if i == 6: break
    return greens * 10 + i
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_lights.wasm" "$test_dir/enum_lights.luc" >/dev/null
expect 0 "36" wasmtime run --invoke enum_lights.answer "$test_dir/enum_lights.wasm"

cat > "$test_dir/enum_toggle.luc" <<'LUCE'
enum Light:
    red
    green
    mutating func toggle(self):
        match self:
            .red: self = .green
            .green: self = .red
pub func answer() -> i64:
    var l = Light.red
    l.toggle()
    l.toggle()
    l.toggle()
    return match l:
        .red => 0
        .green => 1
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_toggle.wasm" "$test_dir/enum_toggle.luc" >/dev/null
expect 0 "1" wasmtime run --invoke enum_toggle.answer "$test_dir/enum_toggle.wasm"

cat > "$test_dir/enum_pairs.luc" <<'LUCE'
enum Pair:
    two(a: i64, b: i64)
    one(a: i64)
func split(p: Pair) -> (i64, i64):
    return match p:
        .two(a, b) => (a, b)
        .one(a) => (a, 0)
pub func answer() -> i64:
    let (x, y) = split(.two(4, 5))
    let (z, w) = split(Pair.one(9))
    return x * 1000 + y * 100 + z * 10 + w
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_pairs.wasm" "$test_dir/enum_pairs.luc" >/dev/null
expect 0 "4590" wasmtime run --invoke enum_pairs.answer "$test_dir/enum_pairs.wasm"

cat > "$test_dir/enum_boxes.luc" <<'LUCE'
struct Box:
    var state: i64?
pub func answer() -> i64:
    var b = Box(state = none)
    var total = 0
    var i = 0
    while i < 4:
        let bonus = match b.state:
            .some(v) => v
            .none => 100
        total += bonus
        b.state = i
        i += 1
    return total
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/enum_boxes.wasm" "$test_dir/enum_boxes.luc" >/dev/null
expect 0 "103" wasmtime run --invoke enum_boxes.answer "$test_dir/enum_boxes.wasm"

# Integer range values and `for`, including a closed maximum endpoint and
# `continue` flowing through the increment block.
cat > "$test_dir/ranges.luc" <<'LUCE'
func span() -> range[i64]: return 2..=4
func sum(values: range[i64]) -> i64:
    var total = 0
    for value in values: total += value
    return total
pub func half_open() -> i64:
    var total = 0
    for i in 0..<5: total += i
    return total
pub func controlled() -> i64:
    var total = 0
    for i in 1..=5:
        if i == 2: continue
        if i == 5: break
        total += i
    return total
pub func maximum() -> u8:
    var last: u8 = 0
    for i in 253u8..=255u8: last = i
    return last
pub func passed() -> i64:
    let values = span()
    return sum(values) + (10 if values == 2..=4 else 0)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/ranges.wasm" "$test_dir/ranges.luc" >/dev/null
expect 0 "10" wasmtime run --invoke ranges.half_open "$test_dir/ranges.wasm"
expect 0 "8" wasmtime run --invoke ranges.controlled "$test_dir/ranges.wasm"
expect 0 "255" wasmtime run --invoke ranges.maximum "$test_dir/ranges.wasm"
expect 0 "19" wasmtime run --invoke ranges.passed "$test_dir/ranges.wasm"

# `defer` uses the same programs as the differential fixtures: captures happen
# at registration, cleanup is LIFO, and all ordinary scope exits run it.
cat > "$test_dir/defers.luc" <<'LUCE'
struct Label:
    let text: str
    func show(self): print(self.text)
func captured() -> str:
    print("capture")
    return "saved"
func show(value: str): print(value)
pub func captured_lifo() -> i64:
    var label = Label(text = "before")
    defer label.show()
    defer show(captured())
    defer print("last")
    label = Label(text = "after")
    print("body")
    return 7
func value() -> i64:
    print("value")
    return 9
pub func return_order() -> i64:
    defer print("cleanup")
    return value()
func inner():
    defer print("fallthrough")
func explicit():
    defer print("unit")
    return
enum Choice:
    yes
    no
pub func nested_scopes() -> i64:
    inner()
    explicit()
    defer print("outer")
    if true:
        defer print("inner")
        print("body")
    match Choice.yes:
        .yes:
            defer print("arm")
            print("match")
        .no: print("wrong")
    return 1
pub func loop_exits() -> i64:
    defer print("function")
    var visits = 0
    for i in 0..<4:
        defer print("iteration")
        visits += 1
        if i == 0: continue
        if i == 2: break
    return visits
pub func while_exits() -> i64:
    var visits = 0
    while visits < 4:
        defer print("while")
        visits += 1
        if visits == 1: continue
        if visits == 3: break
    return visits
func pair() -> (i64, i64):
    defer print("aggregate")
    return (4, 2)
pub func aggregate_return() -> i64:
    let (a, b) = pair()
    return a * 10 + b
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/defers.wasm" "$test_dir/defers.luc" >/dev/null
expect 0 "capture
body
last
saved
before
7" wasmtime run --invoke defers.captured_lifo "$test_dir/defers.wasm"
expect 0 "value
cleanup
9" wasmtime run --invoke defers.return_order "$test_dir/defers.wasm"
expect 0 "fallthrough
unit
body
inner
match
arm
outer
1" wasmtime run --invoke defers.nested_scopes "$test_dir/defers.wasm"
expect 0 "iteration
iteration
iteration
function
3" wasmtime run --invoke defers.loop_exits "$test_dir/defers.wasm"
expect 0 "while
while
while
3" wasmtime run --invoke defers.while_exits "$test_dir/defers.wasm"
expect 0 "aggregate
42" wasmtime run --invoke defers.aggregate_return "$test_dir/defers.wasm"

# Failure is source-visible data: propagation runs active defers, catch sees
# the stable code and message, and scalar/unit/aggregate/match success values
# all use the same caller-owned Error-slot protocol.
cat > "$test_dir/failures.luc" <<'LUCE'
let base: u32 = 3
pub let invalid: ErrorCode = ErrorCode.package((base + 1) * 2 - 1)
func checked(fail: bool) -> i64!:
    defer print("checked")
    if fail: error(invalid, "invalid value")
    return 21
func propagated(fail: bool) -> i64!:
    defer print("propagated")
    return try checked(fail)
pub func answer() -> i64:
    let success = checked(false) catch failure: recover 0
    let recovered = propagated(true) catch failure:
        defer print("handler")
        if failure.code == invalid and failure.message == "invalid value": recover 7
        recover 0
    return success + recovered * 3
func pair(fail: bool) -> (i64, i64)!:
    if fail: error(invalid, "pair failed")
    return (20, 22)
func recovered_pair(fail: bool) -> (i64, i64):
    return pair(fail) catch failure: recover (19, 23)
pub func aggregate_answer() -> i64:
    let (a, b) = recovered_pair(false)
    let (c, d) = recovered_pair(true)
    return a + b + c + d
func noop(): return
func action(fail: bool) -> unit!:
    if fail: error(invalid, "action failed")
func handled_action(fail: bool):
    action(fail) catch failure: recover noop()
pub func unit_answer() -> i64:
    handled_action(false)
    handled_action(true)
    return 42
func selected(flag: bool) -> i64!:
    return try match flag:
        true => checked(false)
        false => checked(true)
pub func match_answer() -> i64:
    let success = selected(true) catch failure: recover 0
    let recovered = selected(false) catch failure: recover 7
    return success + recovered * 3
func returned_from_handler() -> i64:
    return checked(true) catch failure:
        defer print("return handler")
        return 20
func contextual() -> i64!:
    return checked(true) catch failure:
        defer print("error handler")
        error(failure.code, "context")
pub func handler_answer() -> i64:
    let recovered = contextual() catch failure:
        if failure.code == invalid and failure.message == "context": recover 22
        recover 0
    return returned_from_handler() + recovered
struct Positive:
    let value: i64
    func init(self, value: i64) -> unit!:
        if value < 0: error(invalid, "negative")
        self.value = value
func checked_init(value: i64) -> i64:
    let positive = Positive(value) catch failure: return -1
    return positive.value
pub func initializer_answer() -> i64: return checked_init(43) + checked_init(-1)
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/failures.wasm" "$test_dir/failures.luc" >/dev/null
expect 0 "checked
checked
propagated
handler
42" wasmtime run --invoke failures.answer "$test_dir/failures.wasm"
expect 0 "84" wasmtime run --invoke failures.aggregate_answer "$test_dir/failures.wasm"
expect 0 "42" wasmtime run --invoke failures.unit_answer "$test_dir/failures.wasm"
expect 0 "checked
checked
42" wasmtime run --invoke failures.match_answer "$test_dir/failures.wasm"
expect 0 "checked
error handler
checked
return handler
42" wasmtime run --invoke failures.handler_answer "$test_dir/failures.wasm"
expect 0 "42" wasmtime run --invoke failures.initializer_answer "$test_dir/failures.wasm"

# Fixed arrays retain the same inline value semantics and checked place paths
# when the shared MIR reaches WebAssembly.
cat > "$test_dir/arrays.luc" <<'LUCE'
type Row = array[i64, 2]
struct Grid:
    var rows: array[Row, 2]
struct Cell:
    var value: i64
    mutating func bump(self, by: i64): self.value += by
func reverse(value: Row) -> Row: return [value[1u64], value[0u64]]
pub func answer() -> i64:
    var grid = Grid(rows = [[1, 2], [3, 4]])
    var copy = grid
    copy.rows[1u64][0u64] += 5
    let reversed = reverse(copy.rows[1u64])
    if grid == copy: return 0
    return grid.rows[1u64][0u64] * 100 + reversed[0u64] * 10 + reversed[1u64]
pub func empty() -> u64:
    let values: array[i64, 0] = []
    return values.length
pub func method() -> i64:
    var cells: array[Cell, 2] = [Cell(value = 1), Cell(value = 2)]
    cells[1u64].bump(5)
    return cells[1u64].value
pub func missing() -> i64:
    let values: Row = [1, 2]
    return values[2u64]
pub func missing_store() -> i64:
    var values: Row = [1, 2]
    values[2u64] = 3
    return 0
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/arrays.wasm" "$test_dir/arrays.luc" >/dev/null
expect 0 "348" wasmtime run --invoke arrays.answer "$test_dir/arrays.wasm"
expect 0 "0" wasmtime run --invoke arrays.empty "$test_dir/arrays.wasm"
expect 0 "7" wasmtime run --invoke arrays.method "$test_dir/arrays.wasm"
for name in missing missing_store; do
    set +e
    wasmtime run --invoke "arrays.$name" "$test_dir/arrays.wasm" >/dev/null 2>&1; status=$?
    set -e
    if [ "$status" = 0 ]; then
        echo "wasm: arrays.$name exited 0, expected a bounds trap" >&2
        exit 1
    fi
done

# Maps and sets retain one semantic shape through the maintained example; the
# composed runtime owns storage while Wasm supplies only layout and calls.
"$cli" build --package org.luce.tests --root examples/full --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/hash_collections.wasm" examples/full/maps_and_sets.luc >/dev/null
expect 0 "42" wasmtime run --invoke maps_and_sets.answer "$test_dir/hash_collections.wasm"
set +e
wasmtime run --invoke maps_and_sets.mutation_trap "$test_dir/hash_collections.wasm" >/dev/null 2>&1; status=$?
set -e
if [ "$status" = 0 ]; then
    echo "wasm: maps_and_sets.mutation_trap exited 0, expected an iteration mutation trap" >&2
    exit 1
fi

# Every trapping program must trap under wasmtime too.
cat > "$test_dir/traps.luc" <<'LUCE'
pub func i8_overflow() -> i8:
    let v: i8 = 127
    return v + 1
pub func u8_underflow() -> u8:
    let v: u8 = 0
    return v - 1
pub func u32_overflow() -> u32:
    let v: u32 = 4294967295
    return v + 1
pub func i16_negate() -> i16:
    let v: i16 = -32768
    return -v
pub func divide_by_zero() -> i64: return 7 // 0
pub func minimum_by_minus_one() -> i64: return (-9223372036854775807 - 1) // -1
pub func shift_too_far() -> i64: return 1 << 64
pub func shift_negative() -> i64: return 1 >> -1
pub func defer_trap() -> i64:
    defer print("must not run")
    return 1 // 0
LUCE
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/traps.wasm" "$test_dir/traps.luc" >/dev/null
for name in i8_overflow u8_underflow u32_overflow i16_negate divide_by_zero minimum_by_minus_one shift_too_far shift_negative; do
    set +e
    wasmtime run --invoke "traps.$name" "$test_dir/traps.wasm" >/dev/null 2>&1; status=$?
    set -e
    if [ "$status" = 0 ]; then
        echo "wasm: traps.$name exited 0, expected a trap" >&2
        exit 1
    fi
done

# An uncatchable trap skips cleanup, so this must fail without printing the
# deferred line. The exact nonzero status belongs to wasmtime, not Luce.
set +e
output=$(wasmtime run --invoke traps.defer_trap "$test_dir/traps.wasm" 2>/dev/null); status=$?
set -e
if [ "$status" = 0 ] || [ -n "$output" ]; then
    echo "wasm: traps.defer_trap exited $status and printed '$output', expected a silent trap" >&2
    exit 1
fi

# Checked arithmetic: overflow must trap (wasm `unreachable`), never wrap.
printf 'pub func main(arguments: slice[str]) -> i32!: return 2147483647 + 1\n' > "$test_dir/overflow.luc"
"$cli" build --package org.luce.tests --root "$test_dir" --runtime-root "$runtime_root" --runtime "$runtime_source" "$test_dir/overflow.wasm" "$test_dir/overflow.luc" >/dev/null
set +e
wasmtime run "$test_dir/overflow.wasm" >/dev/null 2>&1; status=$?
set -e
if [ "$status" = 0 ]; then
    echo "wasm: overflow.wasm exited 0, expected a trap" >&2
    exit 1
fi

echo "wasm: ok"

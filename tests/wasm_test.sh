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
"$cli" build "$test_dir/hello.wasm" examples/hello.luc >/dev/null
expect 0 "Hello, world!" wasmtime run "$test_dir/hello.wasm"

printf 'pub func main(arguments: slice[str]) -> i32:\n    print("one")\n    print("two")\n    return 3 * 2\n' > "$test_dir/status.luc"
"$cli" build "$test_dir/status.wasm" "$test_dir/status.luc" >/dev/null
expect 6 "one
two" wasmtime run "$test_dir/status.wasm"

# Exported functions: wasmtime invokes them by name and prints the result.
"$cli" build "$test_dir/core.wasm" examples/compiled_core/main.luc >/dev/null
expect 0 "42" wasmtime run --invoke main.answer "$test_dir/core.wasm"

printf 'pub func answer() -> i64: return (2 + 3) * 4 - 6\npub func narrow() -> i32: return 2147483646i32 + 1i32\n' > "$test_dir/math.luc"
"$cli" build "$test_dir/math.wasm" "$test_dir/math.luc" >/dev/null
expect 0 "14" wasmtime run --invoke math.answer "$test_dir/math.wasm"
expect 0 "2147483647" wasmtime run --invoke math.narrow "$test_dir/math.wasm"

# Slice 3a: locals, every operator family, narrow widths, conditionals. The
# same programs are oracle-checked in tests/compiler/differential_test.luc;
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
"$cli" build "$test_dir/scalars.wasm" "$test_dir/scalars.luc" >/dev/null
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
"$cli" build "$test_dir/flow.wasm" "$test_dir/flow.luc" >/dev/null
flow() { expect 0 "$2" wasmtime run --invoke "flow.$1" "$test_dir/flow.wasm"; }
flow sum_to_ten 55
flow break_continue 50
flow nested 8
flow chain 3
flow early_return 19
flow fibonacci 832040
flow collatz 111

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
LUCE
"$cli" build "$test_dir/traps.wasm" "$test_dir/traps.luc" >/dev/null
for name in i8_overflow u8_underflow u32_overflow i16_negate divide_by_zero minimum_by_minus_one shift_too_far shift_negative; do
    set +e
    wasmtime run --invoke "traps.$name" "$test_dir/traps.wasm" >/dev/null 2>&1; status=$?
    set -e
    if [ "$status" = 0 ]; then
        echo "wasm: traps.$name exited 0, expected a trap" >&2
        exit 1
    fi
done

# Checked arithmetic: overflow must trap (wasm `unreachable`), never wrap.
printf 'pub func main(arguments: slice[str]) -> i32: return 2147483647 + 1\n' > "$test_dir/overflow.luc"
"$cli" build "$test_dir/overflow.wasm" "$test_dir/overflow.luc" >/dev/null
set +e
wasmtime run "$test_dir/overflow.wasm" >/dev/null 2>&1; status=$?
set -e
if [ "$status" = 0 ]; then
    echo "wasm: overflow.wasm exited 0, expected a trap" >&2
    exit 1
fi

echo "wasm: ok"

#!/bin/sh
# Exercise the `luce` command line on any host: exit statuses, usage, and
# that every failure path prints its diagnostic instead of trapping.
# Like the native smoke tests, it builds its own `luce` from src/ with the
# Stage-0 compiler given as the first argument.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

luce=${1:-./stage0/bin/luce-0}
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/luce-cli.XXXXXX")
trap 'rm -rf -- "$test_dir"' EXIT HUP INT TERM

"$luce" build src/luce.luc -o "$test_dir/luce"
cli=$test_dir/luce

# expect STATUS EXPECTED_OUTPUT COMMAND...
expect() {
    wanted_status=$1; wanted_output=$2; shift 2
    set +e
    output=$("$@" 2>&1); status=$?
    set -e
    if [ "$status" != "$wanted_status" ]; then
        echo "cli: '$*' exited $status, expected $wanted_status" >&2
        echo "$output" >&2
        exit 1
    fi
    case "$output" in
        *"$wanted_output"*) ;;
        *)
            echo "cli: '$*' printed:" >&2
            echo "$output" >&2
            echo "cli: expected it to contain: $wanted_output" >&2
            exit 1
            ;;
    esac
}

printf 'pub func answer() -> i64: return 5\n' > "$test_dir/main.luc"
printf 'pub func answer() -> i64: return true\n' > "$test_dir/wrong.luc"
printf 'pub func main(arguments: slice[str]) -> i32!:\n    var count = 5i32\n    let read: func() -> i32 = () => count\n    return read()\n' > "$test_dir/shared.luc"
printf 'export c enum Status as i16:\n    ready = -2\n    done = 42\nexport c struct Pair:\n    let left: i32\n    let right: i32\nexport c func luce_pair(value: Pair) -> Status: return .done\npub func main(arguments: slice[str]) -> i32!: return 0i32\n' > "$test_dir/c_api.luc"

expect 0 "Luce v" "$cli" --version
expect 2 "usage:" "$cli"
expect 2 "unknown command" "$cli" frobnicate
expect 2 "expected \`--package ID --root DIR\`" "$cli" check
expect 2 "check: expected at least one FILE" "$cli" check --package org.luce.tests --root "$test_dir"
expect 2 "explain: expected at least one FILE" "$cli" explain --package org.luce.tests --root "$test_dir"
expect 2 "--generic-specializations expects a positive integer" "$cli" check --package org.luce.tests --root "$test_dir" --generic-specializations nope "$test_dir/main.luc"
expect 2 "--generic-specializations expects a positive integer" "$cli" check --package org.luce.tests --root "$test_dir" --generic-specializations 0 "$test_dir/main.luc"
expect 2 "--generic-specializations may be supplied once" "$cli" check --package org.luce.tests --root "$test_dir" --generic-specializations 2 --generic-specializations 3 "$test_dir/main.luc"
expect 2 "--standard sources require --standard-root DIR" "$cli" check --package org.luce.tests --root "$test_dir" --standard src/standard/c.luc "$test_dir/main.luc"
expect 2 "--standard-root requires at least one --standard FILE" "$cli" check --package org.luce.tests --root "$test_dir" --standard-root src/standard "$test_dir/main.luc"
expect 2 "run: entry must be MODULE.FUNCTION" "$cli" run --package org.luce.tests --root "$test_dir" main "$test_dir/main.luc"
expect 2 "build: unknown target" "$cli" build --package org.luce.tests --root "$test_dir" --target z80 out "$test_dir/main.luc"
expect 2 "build: --runtime expects a source path" "$cli" build --package org.luce.tests --root "$test_dir" --runtime
expect 2 "build: --c-header may be supplied once" "$cli" build --package org.luce.tests --root "$test_dir" --c-header one.h --c-header two.h out "$test_dir/main.luc"
expect 2 "bind: expected \`--name NAME --fiir PATH --raw PATH --adapter PATH\`" "$cli" bind
expect 2 "bind: --name may be supplied once" "$cli" bind --name first --name second

expect 0 "checked 1 file(s)" "$cli" check --package org.luce.tests --root "$test_dir" "$test_dir/main.luc"
expect 0 "warning[L1401]: mutable binding \`count\` is shared with this closure" "$cli" check --package org.luce.tests --root "$test_dir" "$test_dir/shared.luc"
expect 1 "cannot read" "$cli" check --package org.luce.tests --root "$test_dir" "$test_dir/missing.luc"
expect 1 "expected \`i64\`, found \`bool\`" "$cli" check --package org.luce.tests --root "$test_dir" "$test_dir/wrong.luc"
expect 1 "generic specialization budget of 2 was exceeded" "$cli" check --package org.luce.tests --root examples --generic-specializations 2 examples/generic_functions.luc
expect 0 "generic specializations for \`org.luce.tests\`: 5/5" "$cli" explain --package org.luce.tests --root examples --generic-specializations 5 examples/generic_functions.luc
expect 0 "expansion path:" "$cli" explain --package org.luce.tests --root examples examples/generic_functions.luc
expect 0 "interface costs for \`org.luce.tests\`: 5 box(es), 5 dynamic call(s)" "$cli" explain --package org.luce.tests --root examples examples/interfaces.luc

expect 0 "5" "$cli" run --package org.luce.tests --root "$test_dir" main.answer "$test_dir/main.luc"
expect 0 "help: use \`copy count = count\`" "$cli" run --package org.luce.tests --root "$test_dir" shared.main "$test_dir/shared.luc"
expect 1 "module \`main\` has no function \`nope\`" "$cli" run --package org.luce.tests --root "$test_dir" main.nope "$test_dir/main.luc"
expect 1 "unknown module \`other\`" "$cli" run --package org.luce.tests --root "$test_dir" other.main "$test_dir/main.luc"

expect 0 "built $test_dir/out.wasm" "$cli" build --package org.luce.tests --root examples/compiled_core "$test_dir/out.wasm" examples/compiled_core/main.luc
expect 0 "artifact: eliminated before backend emission" "$cli" build --package org.luce.tests --root examples --generic-specializations 5 --time-report --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/generic.wasm" examples/generic_functions.luc
expect 0 "built $test_dir/strings.wasm" "$cli" build --package org.luce.tests --root examples --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/strings.wasm" examples/strings.luc
expect 0 "warning[L1401]: mutable binding \`count\` is shared with this closure" "$cli" build --package org.luce.tests --root "$test_dir" --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/shared.wasm" "$test_dir/shared.luc"
expect 1 "executable: needs one public \`main\`" "$cli" build --package org.luce.tests --root examples/compiled_core --target native "$test_dir/out" examples/compiled_core/main.luc

expect 0 "built $test_dir/native" "$cli" build --package org.luce.tests --root examples --target native --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/native" examples/hello.luc
native_output=$("$test_dir/native")
if [ "$native_output" != "Hello, world!" ]; then
    echo "cli: native executable printed '$native_output', expected 'Hello, world!'" >&2
    exit 1
fi
expect 0 "backend-code byte(s)" "$cli" build --package org.luce.tests --root examples --generic-specializations 5 --time-report --target native --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/generic-native" examples/generic_functions.luc
expect 1 "C header and ABI report outputs require \`--target native\`" "$cli" build --package org.luce.tests --root "$test_dir" --c-header "$test_dir/api.h" "$test_dir/api.wasm" "$test_dir/c_api.luc"
expect 1 "C sources and arguments require \`--target native\`" "$cli" build --package org.luce.tests --root "$test_dir" --c-source examples/c_import/temperature.c "$test_dir/api.wasm" "$test_dir/c_api.luc"
expect 1 "C header output must differ from the primary artifact" "$cli" build --package org.luce.tests --root "$test_dir" --target native --c-header "$test_dir/collision" "$test_dir/collision" "$test_dir/c_api.luc"
expect 1 "C source must differ from the C header output" "$cli" build --package org.luce.tests --root "$test_dir" --target native --c-header "$test_dir/source.c" --c-source "$test_dir/source.c" "$test_dir/collision" "$test_dir/c_api.luc"
expect 0 "built $test_dir/c-api-native" "$cli" build --package org.luce.tests --root "$test_dir" --target native --c-header "$test_dir/api.h" --abi-report "$test_dir/api.abi.json" --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/c-api-native" "$test_dir/c_api.luc"
grep -q 'typedef struct Pair Pair;' "$test_dir/api.h"
grep -q '#define Status_done ((Status)(INT64_C(42)))' "$test_dir/api.h"
grep -q 'Status luce_pair(Pair value);' "$test_dir/api.h"
grep -q '"format": "luce-c-abi-1"' "$test_dir/api.abi.json"
grep -q '"target":' "$test_dir/api.abi.json"
grep -q '"offset": 4' "$test_dir/api.abi.json"

mkdir "$test_dir/temperature"
expect 0 "bound examples/c_import/temperature.h" "$cli" bind \
    --name temperature \
    --fiir "$test_dir/temperature.fiir.json" \
    --raw "$test_dir/temperature/raw.native.luc" \
    --adapter "$test_dir/temperature.adapter.c" \
    --clang-arg -std=c11 \
    --clang-arg -Wall \
    --clang-arg -Wextra \
    --clang-arg -Werror \
    examples/c_import/temperature.h
grep -q '"format": "luce-fiir-1"' "$test_dir/temperature.fiir.json"
grep -q '"target":' "$test_dir/temperature.fiir.json"
grep -q 'pub func luce_celsius_to_fahrenheit(celsius: c.double) -> c.double' "$test_dir/temperature/raw.native.luc"
grep -q 'pub func luce_half_celsius(celsius: c.float) -> c.float' "$test_dir/temperature/raw.native.luc"
grep -q 'pub func luce_adjust_celsius(celsius: c.int, delta: c.int) -> c.int' "$test_dir/temperature/raw.native.luc"
grep -q 'pub struct luce_degrees:' "$test_dir/temperature/raw.native.luc"
grep -q 'pub func luce_echo_degrees(celsius: luce_degrees) -> luce_degrees' "$test_dir/temperature/raw.native.luc"
grep -q 'pub struct luce_temperature_scale:' "$test_dir/temperature/raw.native.luc"
grep -q 'pub let LUCE_SCALE_CELSIUS: luce_temperature_scale' "$test_dir/temperature/raw.native.luc"
grep -q 'pub let LUCE_WATER_BOILING_CELSIUS: c.integer_constant = c.integer_constant(false, 100u64)' "$test_dir/temperature/raw.native.luc"
grep -q 'pub func luce_echo_scale(scale: luce_temperature_scale) -> luce_temperature_scale' "$test_dir/temperature/raw.native.luc"
grep -q 'pub func luce_is_freezing(enabled: c.boolean, celsius: c.double) -> c.boolean' "$test_dir/temperature/raw.native.luc"
grep -q '_Static_assert(FLT_RADIX == 2' "$test_dir/temperature.adapter.c"
grep -q 'FLT_MANT_DIG == 24' "$test_dir/temperature.adapter.c"
grep -q '_Static_assert(CHAR_BIT \* sizeof(_Bool)' "$test_dir/temperature.adapter.c"
grep -q 'if (celsius < -INT64_C(2147483648)' "$test_dir/temperature.adapter.c"
grep -q '_Generic(((luce_degrees)0), int: 1, default: 0)' "$test_dir/temperature.adapter.c"
grep -q '_Static_assert(_Generic((LUCE_WATER_BOILING_CELSIUS), int: 1, default: 0)' "$test_dir/temperature.adapter.c"
grep -q '_Static_assert(LUCE_WATER_BOILING_CELSIUS == UINT64_C(100)' "$test_dir/temperature.adapter.c"
cc -std=c11 -Wall -Wextra -Werror -I . -fsyntax-only "$test_dir/temperature.adapter.c"
cc -std=c11 -Wall -Wextra -Werror -fshort-enums -I . -fsyntax-only "$test_dir/temperature.adapter.c"

expect 0 "bound tests/fixtures/fiir/scalars.h" "$cli" bind \
    --name scalars \
    --fiir "$test_dir/scalars.fiir.json" \
    --raw "$test_dir/scalars.raw.native.luc" \
    --adapter "$test_dir/scalars.adapter.c" \
    --clang-arg -std=c11 \
    tests/fixtures/fiir/scalars.h
grep -q 'pub func luce_echo_boolean(value: c.boolean) -> c.boolean' "$test_dir/scalars.raw.native.luc"
grep -q 'pub func luce_echo_float(value: c.float) -> c.float' "$test_dir/scalars.raw.native.luc"
grep -q 'pub struct size_t:' "$test_dir/scalars.raw.native.luc"
grep -q 'pub struct luce_scalar_status:' "$test_dir/scalars.raw.native.luc"
grep -q 'pub func luce_echo_size(value: size_t) -> size_t' "$test_dir/scalars.raw.native.luc"
grep -q 'pub func luce_echo_int(value: c.int) -> c.int' "$test_dir/scalars.raw.native.luc"
grep -q 'pub func luce_echo_unsigned_long_long(value: c.unsigned_long_long)' "$test_dir/scalars.raw.native.luc"
cc -std=c11 -Wall -Wextra -Werror -I . -fsyntax-only "$test_dir/scalars.adapter.c"

cp examples/c_import/temperature.luc "$test_dir/temperature.luc"
printf 'from temperature import adjust_celsius, boiling_celsius, celsius_to_fahrenheit, echo_degrees, half_celsius, is_freezing, scale_round_trips\npub func main(arguments: slice[str]) -> i32!:\n    return 0 if celsius_to_fahrenheit(0.0) == 32.0 and half_celsius(84.0f32) == 42.0f32 and adjust_celsius(40, 2) == 42 and echo_degrees(42) == 42 and boiling_celsius() == 100 and scale_round_trips() and is_freezing(0.0) else 1\n' > "$test_dir/temperature_main.luc"
expect 0 "built $test_dir/temperature-native" "$cli" build \
    --package org.luce.c-import-test \
    --root "$test_dir" \
    --standard-root src/standard \
    --standard src/standard/c.luc \
    --target native \
    --runtime-root src/runtime \
    --runtime src/runtime/allocator.native.luc \
    --c-source "$test_dir/temperature.adapter.c" \
    --c-source examples/c_import/temperature.c \
    --c-arg -std=c11 \
    --c-arg -Wall \
    --c-arg -Wextra \
    --c-arg -Werror \
    --c-arg -I \
    --c-arg . \
    --c-arg -I \
    --c-arg examples/c_import \
    "$test_dir/temperature-native" \
    "$test_dir/temperature/raw.native.luc" \
    "$test_dir/temperature.luc" \
    "$test_dir/temperature_main.luc"
"$test_dir/temperature-native"

printf 'previous fiir' > "$test_dir/preserved.fiir.json"
printf 'previous raw' > "$test_dir/preserved.raw.native.luc"
printf 'previous adapter' > "$test_dir/preserved.adapter.c"
expect 1 "Clang FIIR toolchain: target query exited with status" "$cli" bind \
    --name temperature \
    --clang /luce-test/missing-clang \
    --fiir "$test_dir/preserved.fiir.json" \
    --raw "$test_dir/preserved.raw.native.luc" \
    --adapter "$test_dir/preserved.adapter.c" \
    examples/c_import/temperature.h
[ "$(cat "$test_dir/preserved.fiir.json")" = "previous fiir" ]
[ "$(cat "$test_dir/preserved.raw.native.luc")" = "previous raw" ]
[ "$(cat "$test_dir/preserved.adapter.c")" = "previous adapter" ]

# A host-tool failure must preserve an existing destination and report the
# tool that failed. An empty PATH makes qbe unavailable without relying on the
# host's installed tools.
mkdir "$test_dir/empty-path"
printf 'previous artifact' > "$test_dir/preserved"
expect 1 "qbe toolchain: qbe exited with status 127" /usr/bin/env PATH="$test_dir/empty-path" "$cli" build --package org.luce.tests --root examples --target native --runtime-root src/runtime --runtime src/runtime/allocator.native.luc "$test_dir/preserved" examples/hello.luc
preserved=$(cat "$test_dir/preserved")
if [ "$preserved" != "previous artifact" ]; then
    echo "cli: failed native build replaced the previous artifact" >&2
    exit 1
fi

echo "cli: ok"

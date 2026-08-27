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

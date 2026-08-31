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

printf 'pub func main() -> i64: return 5\n' > "$test_dir/main.luc"
printf 'pub func main() -> i64: return true\n' > "$test_dir/wrong.luc"

expect 0 "Luce v" "$cli" --version
expect 2 "usage:" "$cli"
expect 2 "unknown command" "$cli" frobnicate
expect 2 "expected \`--package ID\`" "$cli" check
expect 2 "check: expected at least one FILE" "$cli" check --package org.luce.tests
expect 2 "run: entry must be MODULE.FUNCTION" "$cli" run --package org.luce.tests main "$test_dir/main.luc"
expect 2 "build: unknown target" "$cli" build --package org.luce.tests --target z80 out "$test_dir/main.luc"
expect 2 "build: --runtime expects a source path" "$cli" build --package org.luce.tests --runtime

expect 0 "checked 1 file(s)" "$cli" check --package org.luce.tests "$test_dir/main.luc"
expect 1 "cannot read" "$cli" check --package org.luce.tests "$test_dir/missing.luc"
expect 1 "expected \`i64\`, found \`bool\`" "$cli" check --package org.luce.tests "$test_dir/wrong.luc"

expect 0 "5" "$cli" run --package org.luce.tests main.main "$test_dir/main.luc"
expect 1 "module \`main\` has no function \`nope\`" "$cli" run --package org.luce.tests main.nope "$test_dir/main.luc"
expect 1 "unknown module \`other\`" "$cli" run --package org.luce.tests other.main "$test_dir/main.luc"

expect 0 "built $test_dir/out.wasm" "$cli" build --package org.luce.tests "$test_dir/out.wasm" examples/compiled_core/main.luc
expect 0 "built $test_dir/strings.wasm" "$cli" build --package org.luce.tests --runtime src/runtime/allocator.native.luc "$test_dir/strings.wasm" examples/strings.luc
expect 1 "executable: needs one public \`main\`" "$cli" build --package org.luce.tests --target native "$test_dir/out" examples/compiled_core/main.luc

expect 0 "built $test_dir/native" "$cli" build --package org.luce.tests --target native "$test_dir/native" examples/hello.luc
native_output=$("$test_dir/native")
if [ "$native_output" != "Hello, world!" ]; then
    echo "cli: native executable printed '$native_output', expected 'Hello, world!'" >&2
    exit 1
fi

# A host-tool failure must preserve an existing destination and report the
# tool that failed. An empty PATH makes qbe unavailable without relying on the
# host's installed tools.
mkdir "$test_dir/empty-path"
printf 'previous artifact' > "$test_dir/preserved"
expect 1 "qbe toolchain: qbe exited with status 127" /usr/bin/env PATH="$test_dir/empty-path" "$cli" build --package org.luce.tests --target native "$test_dir/preserved" examples/hello.luc
preserved=$(cat "$test_dir/preserved")
if [ "$preserved" != "previous artifact" ]; then
    echo "cli: failed native build replaced the previous artifact" >&2
    exit 1
fi

echo "cli: ok"

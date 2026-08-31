#!/bin/sh
# Build a host executable through the product QBE path, then prove ordinary
# execution and language traps on every host supported by bootstrap.sh.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

luce=${1:-./stage0/bin/luce-0}
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/luce-native.XXXXXX")
trap 'rm -rf -- "$test_dir"' EXIT HUP INT TERM

"$luce" build src/luce.luc -o "$test_dir/luce"
runtime_source=src/runtime/allocator.native.luc
"$test_dir/luce" build --package org.luce.tests --target native --runtime "$runtime_source" "$test_dir/hello" examples/hello.luc

description=$(file "$test_dir/hello")
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)
        case "$description" in
            *"Mach-O 64-bit executable arm64"*) ;;
            *) echo "expected an ARM64 Mach-O executable, found: $description" >&2; exit 1 ;;
        esac
        trap_status=133
        ;;
    Linux-x86_64)
        case "$description" in
            *"ELF 64-bit LSB"*"x86-64"*) ;;
            *) echo "expected an x86-64 ELF executable, found: $description" >&2; exit 1 ;;
        esac
        trap_status=132
        ;;
    *)
        echo "native: unsupported test host $(uname -s)/$(uname -m)" >&2
        exit 1
        ;;
esac

output=$("$test_dir/hello")
if [ "$output" != "Hello, world!" ]; then
    echo "expected hello output, found: $output" >&2
    exit 1
fi

printf 'pub func main(arguments: slice[str]) -> i32: return 2147483647 + 1\n' > "$test_dir/overflow.luc"
"$test_dir/luce" build --package org.luce.tests --target native --runtime "$runtime_source" "$test_dir/overflow" "$test_dir/overflow.luc"
set +e
{ "$test_dir/overflow"; echo $? > "$test_dir/overflow.status"; } 2>/dev/null
set -e
status=$(cat "$test_dir/overflow.status")
if [ "$status" != "$trap_status" ]; then
    echo "expected overflow to trap with status $trap_status, found: $status" >&2
    exit 1
fi

echo "native QBE hello and overflow trap: ok"

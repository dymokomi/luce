#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

luce=${1:-./stage0/bin/luce-0}
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/luce-arm64-macos.XXXXXX")
trap 'rm -rf -- "$test_dir"' EXIT HUP INT TERM

"$luce" build src/luce.luc -o "$test_dir/luce"
"$test_dir/luce" build --target arm64-macos "$test_dir/hello" examples/hello.luc

description=$(file "$test_dir/hello")
case "$description" in
    *"Mach-O 64-bit executable arm64"*) ;;
    *)
        echo "expected an ARM64 Mach-O executable, found: $description" >&2
        exit 1
        ;;
esac

output=$("$test_dir/hello")
if [ "$output" != "Hello, world!" ]; then
    echo "expected hello output, found: $output" >&2
    exit 1
fi

# Integer overflow must trap (language section 7): the image dies by signal
# rather than returning a wrapped value. SIGTRAP on arm64, SIGILL on x86-64.
printf 'pub func main(arguments: slice[str]) -> i32: return 2147483647 + 1\n' > "$test_dir/overflow.luc"
"$test_dir/luce" build --target arm64-macos "$test_dir/overflow" "$test_dir/overflow.luc"
set +e
{ "$test_dir/overflow"; echo $? > "$test_dir/overflow.status"; } 2>/dev/null
set -e
status=$(cat "$test_dir/overflow.status")
if [ "$status" != 133 ]; then
    echo "expected the overflow to trap with status 133, found: $status" >&2
    exit 1
fi

echo "arm64-macos hello and overflow trap: ok"

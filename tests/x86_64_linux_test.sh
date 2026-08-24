#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

luce=${1:-./stage0/bin/luce-0}
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/luce-x86_64-linux.XXXXXX")
trap 'rm -rf -- "$test_dir"' EXIT HUP INT TERM

"$luce" build src/luce.luc -o "$test_dir/luce"
"$test_dir/luce" build --target x86_64-linux "$test_dir/hello" examples/hello.luc

description=$(file "$test_dir/hello")
case "$description" in
    *"ELF 64-bit LSB executable, x86-64"*) ;;
    *)
        echo "expected an x86-64 ELF executable, found: $description" >&2
        exit 1
        ;;
esac

output=$("$test_dir/hello")
if [ "$output" != "Hello, world!" ]; then
    echo "expected hello output, found: $output" >&2
    exit 1
fi

echo "x86_64-linux hello: ok"

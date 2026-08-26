#!/bin/sh
# Build the Luce compiler with the Stage-0 toolchain.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root"

# Always link against the runtime that belongs to this repository's toolchain.
unset LUCE_LIB

# Use the faster development compiler when available.
luce=./stage0/bin/luce-0-fast
[ -x "$luce" ] || luce=./stage0/bin/luce-0

if [ ! -x "$luce" ]; then
    echo "build: Stage-0 compiler not found; run ./bootstrap.sh first" >&2
    exit 1
fi

mkdir -p build
"$luce" build src/luce.luc -o build/luce
echo "build: compiler written to build/luce"

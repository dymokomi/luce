#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root"

# The in-repo stage-0 compiler must link against its own matching runtime.
# Clear any LUCE_LIB inherited from a separately installed toolchain, whose
# libluce_rt.a can be an older version missing symbols this compiler emits.
unset LUCE_LIB

# Prefer a locally built fast-codegen compiler (O1 + FastISel) for the
# edit/test loop; the shipped archive contains only luce-0.
luce=./stage0/bin/luce-0-fast
[ -x "$luce" ] || luce=./stage0/bin/luce-0

# 1. Unit tests: every tests/compiler/**/*_test.luc file.
"$luce" test

# 2. Command-line contract: exit statuses, usage, and that every failure
#    path prints its diagnostic (tests/cli_test.sh).
./tests/cli_test.sh ./stage0/bin/luce-0

# WebAssembly execution under wasmtime, when it is installed.
./tests/wasm_test.sh ./stage0/bin/luce-0

# 3. Native smoke test: build the compiler, build hello.luc for this host,
#    and run it.

if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
    ./tests/arm64_macos_test.sh ./stage0/bin/luce-0
fi

if [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ]; then
    ./tests/x86_64_linux_test.sh ./stage0/bin/luce-0
fi

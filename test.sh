#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root"
PATH="$repo_root/stage0/bin:$PATH"
export PATH

# The in-repo stage-0 compiler must link against its own matching runtime.
# Clear any LUCE_LIB inherited from a separately installed toolchain, whose
# libluce_rt.a can be an older version missing symbols this compiler emits.
unset LUCE_LIB

# Prefer a locally built fast-codegen compiler (O1 + FastISel) for the
# edit/test loop; the shipped archive contains only luce-0.
luce=./stage0/bin/luce-0-fast
[ -x "$luce" ] || luce=./stage0/bin/luce-0

if ! command -v qbe >/dev/null 2>&1; then
    echo "test: QBE 1.3 not found; run ./bootstrap.sh" >&2
    exit 1
fi

# 1. Architectural boundary: target and backend concepts begin at backends/.
# Frontend, HIR, and MIR are lowered once and must remain target-neutral.
if grep -R -n -E 'compiler\.backends|TargetLayout|LayoutRules|TypeLayout|pointer_(size|align)|arm64|x86_64|wasm32|macos|linux' \
    src/compiler/frontend src/compiler/hir src/compiler/mir; then
    echo "platform dependency found before the backend boundary" >&2
    exit 1
fi

# 2. Unit tests: every tests/compiler/**/*_test.luc file.
"$luce" test

# 3. Command-line contract: exit statuses, usage, and that every failure
#    path prints its diagnostic (tests/cli_test.sh).
./tests/cli_test.sh ./stage0/bin/luce-0

# WebAssembly execution under wasmtime, when it is installed.
./tests/wasm_test.sh ./stage0/bin/luce-0

# 4. Native smoke test: build the compiler, build hello.luc for this host,
#    and run it.

if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
    ./tests/arm64_macos_test.sh ./stage0/bin/luce-0
fi

if [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ]; then
    ./tests/x86_64_linux_test.sh ./stage0/bin/luce-0
fi

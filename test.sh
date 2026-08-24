#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root"

# Prefer the fast-codegen compiler (O1 + FastISel) for the edit/test loop;
# fall back to the shipping luce-0 when it is not installed.
luce=./stage0/bin/luce-0-fast
[ -x "$luce" ] || luce=./stage0/bin/luce-0
"$luce" test

if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
    ./tests/arm64_macos_test.sh ./stage0/bin/luce-0
fi

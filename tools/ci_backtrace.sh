#!/bin/bash
# Recover useful compiler frames even when bootstrap stops before its usual logs.
set -u
root=.
if [ -d build/luce-base/.git ]; then root=build/luce-base; fi
mkdir -p build
if [ "$(uname -s)" != Linux ]; then exit 0; fi
cd "$root"
for compiler in stage0 stage1 luce-base; do
    if [ -x "build/$compiler" ]; then
        timeout 180 gdb -q -batch -ex 'set pagination off' -ex run -ex 'thread apply all bt' -ex 'info registers' -ex 'x/16i $pc-32' -ex 'info symbol $pc' \
            --args "build/$compiler" build src/main.lucb --native --emit=asm -o build/diagnostic.s \
            > "build/backtrace-$compiler.log" 2>&1 || true
    fi
done

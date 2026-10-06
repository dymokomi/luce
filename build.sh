#!/bin/sh
# Build Luce natively with the Base compiler of the luce-base checkout beside this one
# (../luce-base, as it is; CI checks out main), building it there when it is missing or
# older than its sources. build/luce-base links to that checkout, where a development
# build of luce finds its Base compiler (support.toolchain).
# LUCE_BASE_COMPILER selects an already-built compiler instead.
set -eu
cd "$(dirname "$0")"
mkdir -p build
python3 tools/embed_version.py > /dev/null
python3 tools/embed_runtime.py > /dev/null
python3 tools/embed_prelude.py
if [ -n "${LUCE_BASE_COMPILER:-}" ]; then
    case "$LUCE_BASE_COMPILER" in
        /*) base=$LUCE_BASE_COMPILER ;;
        *) base=$PWD/$LUCE_BASE_COMPILER ;;
    esac
    [ -x "$base" ] || { echo "FAIL: LUCE_BASE_COMPILER is not executable: $base"; exit 1; }
    description="explicit Base compiler: $base"
else
    if [ ! -d ../luce-base ]; then
        echo "FAIL: luce builds with the luce-base checkout beside it; clone it (and luce-std):"
        echo "  git clone https://github.com/dymokomi/luce-base ../luce-base && python3 ../luce-base/tools/checkout_main.py ."
        exit 1
    fi
    [ -L build/luce-base ] || rm -rf build/luce-base build/luce-std
    ln -sfn ../../luce-base build/luce-base
    base=build/luce-base/build/luce-base
    if [ ! -x "$base" ] || [ -n "$(find ../luce-base/src ../luce-base/runtime ../luce-base/bootstrap -newer "$base" -type f | head -n 1)" ]; then
        (cd ../luce-base && ./build.sh > /dev/null)
    fi
    description="../luce-base $(git -C ../luce-base rev-parse --short HEAD 2>/dev/null || true)"
fi
# the compiler Luce is built with is the one it runs, and its version the one it accepts
python3 tools/embed_toolchain.py "$base" > /dev/null
"$base" build src/main.lucb --native -o build/luce
echo "built build/luce ($description)"

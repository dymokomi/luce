#!/bin/sh
# Build Luce natively with the exact Base commit in bootstrap/BASE. The isolated
# build/luce-base checkout makes normal builds independent of another working tree.
# LUCE_BASE_SOURCE selects the repository (default ../luce-base).
# LUCE_BASE_COMPILER selects an already-built compiler for dependency development.
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
    revision=$(cat bootstrap/BASE)
    [ "${#revision}" -eq 40 ] || { echo "FAIL: bootstrap/BASE must name a full commit SHA"; exit 1; }
    case "$revision" in *[!0-9a-f]*) echo "FAIL: invalid Base commit SHA"; exit 1 ;; esac
    source=${LUCE_BASE_SOURCE:-../luce-base}
    base=build/luce-base/build/luce-base
    if [ ! -x "$base" ] || [ "$(git -C build/luce-base rev-parse HEAD 2>/dev/null || true)" != "$revision" ]; then
        rm -rf build/luce-base
        git init -q build/luce-base
        git --git-dir=build/luce-base/.git fetch -q --depth 1 "$source" "$revision"
        git -C build/luce-base checkout -q --detach FETCH_HEAD
        [ "$(git -C build/luce-base rev-parse HEAD)" = "$revision" ]
        (cd build/luce-base && ./build.sh > /dev/null)
    fi
    description=$revision
fi
"$base" build src/main.lucb --native -o build/luce
echo "built build/luce ($description)"

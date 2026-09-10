#!/bin/sh
# Build luce. The compiler is a Base program, so luce-base builds it: the release named in
# bootstrap/BASE, built from its tag into build/luce-base/ so that this tree depends on a tag
# and never on another tree's working directory. LUCE_BASE_SOURCE names the luce-base
# repository to take the tag from (default ../luce-base). LUCE_BASE_COMPILER is an
# explicit executable override for testing an unreleased Base; normal builds stay pinned.
set -eu
cd "$(dirname "$0")"
mkdir -p build
python3 tools/embed_version.py > /dev/null
python3 tools/embed_runtime.py > /dev/null
if [ -n "${LUCE_BASE_COMPILER:-}" ]; then
    case "$LUCE_BASE_COMPILER" in
        /*) base=$LUCE_BASE_COMPILER ;;
        *) base=$PWD/$LUCE_BASE_COMPILER ;;
    esac
    [ -x "$base" ] || { echo "FAIL: LUCE_BASE_COMPILER is not executable: $base"; exit 1; }
    description="explicit Base compiler: $base"
else
    tag=$(cat bootstrap/BASE)
    source=${LUCE_BASE_SOURCE:-../luce-base}
    base=build/luce-base/build/luce-base
    if [ ! -x "$base" ] || [ "$(cat build/luce-base/TAG 2>/dev/null)" != "$tag" ]; then
        rm -rf build/luce-base
        git clone -q --depth 1 --branch "$tag" "$source" build/luce-base
        (cd build/luce-base && ./build.sh > /dev/null)
        echo "$tag" > build/luce-base/TAG
    fi
    description=$tag
fi
"$base" build src/main.lucb --native -o build/luce
echo "built build/luce ($description)"

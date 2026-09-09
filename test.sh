#!/bin/sh
# The gate. Green, or the tree does not move.
set -eu
cd "$(dirname "$0")"
./build.sh
base=build/luce-base/build/luce-base
export LUCE_BASE=$PWD/$base
python3 tools/embed_version.py --check
python3 tools/embed_runtime.py --check
for f in src/*.lucb src/*/*.lucb; do
    [ -e "$f" ] || continue
    echo "== check $f"
    "$base" check "$f"
    if grep -q '^test "' "$f"; then
        echo "== test $f"
        "$base" test "$f"
        "$base" test "$f" --native
    fi
done
echo "== luce --version"
./build/luce --version
tests/conformance/run.sh
python3 tools/fuzz.py --gate
echo ok

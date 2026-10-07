#!/bin/sh
# The conformance suite: one directory per chapter of docs/luce.md. A program beside its
# `.expect` runs through the interpreter and through the emitted Base under every generator
# luce-base has, and every execution must print the expectation. One beside a `.trap` must
# stop with that text on every execution. One under `errors/` must be rejected with the
# diagnostic its `# error:` line names, at a position. A program reads its `.input` as
# standard input, and an empty one when it has none. Every case runs in a directory of its
# own (case.sh), as many at once as the machine has cores (LUCE_JOBS overrides).
set -eu
cd "$(dirname "$0")/../.."
export LUCE_BASE=${LUCE_BASE:-$PWD/build/luce-base/build/luce-base}
jobs=${LUCE_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu)}
mkdir -p build/cases
cases=build/cases/list
: > "$cases"
# every program the suite holds parses, whatever slice runs it
find tests/conformance tests/programs -name '*.luc' -not -path '*/errors/*' | sort > build/cases/parse
xargs -P "$jobs" -n 1 python3 tools/run_case.py -- ./build/luce parse < build/cases/parse > /dev/null
parsed=$(wc -l < build/cases/parse | tr -d ' ')
# the proving programs under tests/programs are run the same way, each a directory
for dir in tests/conformance/[0-9]*/ tests/programs/; do
    for f in "$dir"*.expect "$dir"*/main.expect "$dir"*/src/main.expect; do
        [ -e "$f" ] && echo "expect $f" >> "$cases"
    done
    for kind in tests doc explain trap; do
        for f in "$dir"*."$kind"; do
            [ -e "$f" ] && echo "$kind $f" >> "$cases"
        done
    done
    for f in "$dir"errors/*.luc "$dir"errors/*/main.luc; do
        [ -e "$f" ] || continue
        # a program under errors/ without an `# error:` line is a module another one imports
        grep -q '^# error: ' "$f" && echo "error $f" >> "$cases"
    done
done
programs=$(grep -c -v '^error ' "$cases")
rejections=$(grep -c '^error ' "$cases")
xargs -P "$jobs" -n 2 sh tests/conformance/case.sh < "$cases" || { echo "FAIL conformance: the cases above"; exit 1; }
rm -rf build/cases
echo "ok conformance: $programs programs, $rejections rejections, $parsed parsed"

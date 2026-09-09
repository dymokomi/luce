#!/bin/sh
# The conformance suite: one directory per chapter of docs/luce.md. A program beside its
# `.expect` runs through the interpreter and through the emitted Base under every generator
# luce-base has, and every execution must print the expectation. One beside a `.trap` must
# stop with that text on every execution. One under `errors/` must be rejected with the
# diagnostic its `# error:` line names, at a position.
set -eu
cd "$(dirname "$0")/../.."
export LUCE_BASE=${LUCE_BASE:-$PWD/build/luce-base/build/luce-base}
programs=0
rejections=0
parsed=0
# every program the suite holds parses, whatever slice runs it
for f in $(find tests/conformance -name '*.luc' -not -path '*/errors/*' | sort); do
    ./build/luce parse "$f" > /dev/null
    parsed=$((parsed + 1))
done
# a program is a file beside its `.expect`, or a directory of modules whose entry is
# `main.luc` (§15), a `src/main.luc` under a manifest among them
for dir in tests/conformance/[0-9]*/; do
    for f in "$dir"*.expect "$dir"*/main.expect "$dir"*/src/main.expect; do
        [ -e "$f" ] || continue
        src="${f%.expect}.luc"
        echo "== $src"
        ./build/luce run "$src" > build/conformance.out
        cmp build/conformance.out "$f"
        # the emitted Base through every generator luce-base has
        for flags in "" "--release" "--native"; do
            ./build/luce build "$src" -o build/conformance $flags
            ./build/conformance > build/conformance.out
            cmp build/conformance.out "$f"
        done
        programs=$((programs + 1))
    done
    # a program beside a `.trap` file must stop with that text on every execution
    for f in "$dir"*.trap; do
        [ -e "$f" ] || continue
        src="${f%.trap}.luc"
        want=$(cat "$f")
        echo "== $src (traps)"
        if ./build/luce run "$src" > build/conformance.out 2> build/conformance.err; then
            echo "FAIL $src: expected a trap, the program finished"; exit 1
        fi
        grep -q "$want" build/conformance.err || { echo "FAIL $src: expected [$want], got [$(cat build/conformance.err)]"; exit 1; }
        for flags in "" "--native"; do
            ./build/luce build "$src" -o build/conformance $flags
            if ./build/conformance > build/conformance.out 2> build/conformance.err; then
                echo "FAIL $src ($flags): expected a trap, the compiled program finished"; exit 1
            fi
            grep -q "$want" build/conformance.err || { echo "FAIL $src ($flags): expected [$want], got [$(cat build/conformance.err)]"; exit 1; }
        done
        programs=$((programs + 1))
    done
    for f in "$dir"errors/*.luc "$dir"errors/*/main.luc; do
        [ -e "$f" ] || continue
        want=$(LC_ALL=C sed -n 's/^# error: //p' "$f")
        [ -n "$want" ] || continue
        got=$(./build/luce check "$f" 2>&1) && rc=0 || rc=$?
        if [ "$rc" -eq 0 ]; then echo "FAIL $f: accepted"; exit 1; fi
        if [ "$rc" -ne 1 ]; then echo "FAIL $f: status $rc: [$got]"; exit 1; fi
        case "$got" in
            *.luc:[0-9]*:[0-9]*:\ *) ;;
            *) echo "FAIL $f: a diagnostic without a position: [$got]"; exit 1;;
        esac
        case "$got" in
            *"$want"*) ;;
            *) echo "FAIL $f: expected [$want], got [$got]"; exit 1;;
        esac
        rejections=$((rejections + 1))
    done
done
echo "ok conformance: $programs programs, $rejections rejections, $parsed parsed"

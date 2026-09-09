#!/bin/sh
# The conformance suite: one directory per chapter of docs/luce.md. A program beside its
# `.expect` runs through the interpreter and through the emitted Base under every generator
# luce-base has, and every execution must print the expectation. One beside a `.trap` must
# stop with that text on every execution. One under `errors/` must be rejected with the
# diagnostic its `# error:` line names, at a position.
set -eu
cd "$(dirname "$0")/../.."
programs=0
rejections=0
parsed=0
# every program the suite holds parses, whatever slice runs it
for f in tests/conformance/[0-9]*/*.luc; do
    [ -e "$f" ] || continue
    ./build/luce parse "$f" > /dev/null
    parsed=$((parsed + 1))
done
for dir in tests/conformance/[0-9]*/; do
    for f in "$dir"*.expect; do
        [ -e "$f" ] || continue
        src="${f%.expect}.luc"
        echo "== $src"
        ./build/luce run "$src" > build/conformance.out
        cmp build/conformance.out "$f"
        programs=$((programs + 1))
    done
    for f in "$dir"errors/*.luc; do
        [ -e "$f" ] || continue
        want=$(LC_ALL=C sed -n 's/^# error: //p' "$f")
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

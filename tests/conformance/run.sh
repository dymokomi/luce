#!/bin/sh
# The conformance suite: one directory per chapter of docs/luce.md. A program beside its
# `.expect` runs through the interpreter and through the emitted Base under every generator
# luce-base has, and every execution must print the expectation. One beside a `.trap` must
# stop with that text on every execution. One under `errors/` must be rejected with the
# diagnostic its `# error:` line names, at a position.
set -eu
cd "$(dirname "$0")/../.."
export LUCE_BASE=${LUCE_BASE:-$PWD/build/luce-base/build/luce-base}
run() { python3 tools/run_case.py -- "$@"; }
reject() { python3 tools/run_case.py --expected 1 -- "$@"; }
programs=0
rejections=0
parsed=0
# every program the suite holds parses, whatever slice runs it
for f in $(find tests/conformance tests/programs -name '*.luc' -not -path '*/errors/*' | sort); do
    run ./build/luce parse "$f" > /dev/null
    parsed=$((parsed + 1))
done
# a program is a file beside its `.expect`, or a directory of modules whose entry is
# `main.luc` (§15), a `src/main.luc` under a manifest among them
# the proving programs under tests/programs are run the same way, each a directory
for dir in tests/conformance/[0-9]*/ tests/programs/; do
    for f in "$dir"*.expect "$dir"*/main.expect "$dir"*/src/main.expect; do
        [ -e "$f" ] || continue
        src="${f%.expect}.luc"
        echo "== $src"
        if ls "$(dirname "$src")"/*.lucb > /dev/null 2>&1; then
            # a program importing a Base module is built, never run in the interpreter (§16)
            if reject ./build/luce run "$src" > build/conformance.out 2> build/conformance.err; then
                echo "FAIL $src: the interpreter ran a program that imports a Base module"; exit 1
            else
                rc=$?
                [ "$rc" -eq 1 ] || { echo "FAIL $src: unexpected status $rc"; exit 1; }
            fi
            grep -q "the interpreter runs Luce alone" build/conformance.err || { echo "FAIL $src: [$(cat build/conformance.err)]"; exit 1; }
        else
            run ./build/luce run "$src" > build/conformance.out
            cmp build/conformance.out "$f"
        fi
        # the emitted Base through every generator luce-base has
        for flags in "" "--release" "--native"; do
            run ./build/luce build "$src" -o build/conformance $flags
            run ./build/conformance > build/conformance.out
            cmp build/conformance.out "$f"
        done
        programs=$((programs + 1))
    done
    # a program beside a `.tests` file prints that report under `luce test`, from the
    # interpreter and from a built runner alike (§17.3); the status is 1 when a test failed
    for f in "$dir"*.tests; do
        [ -e "$f" ] || continue
        src="${f%.tests}.luc"
        echo "== $src (tests)"
        if grep -q ' failed$' "$f"; then want_status=1; else want_status=0; fi
        for flags in "" "--build" "--build --native"; do
            python3 tools/run_case.py --expected "$want_status" -- ./build/luce test "$src" $flags > build/conformance.out 2>&1 && status=0 || status=$?
            [ "$status" -eq "$want_status" ] || { echo "FAIL $src ($flags): status $status, expected $want_status: [$(cat build/conformance.out)]"; exit 1; }
            cmp build/conformance.out "$f"
        done
        programs=$((programs + 1))
    done
    # a program beside a `.doc` file documents as it says (§17.4)
    for f in "$dir"*.doc; do
        [ -e "$f" ] || continue
        src="${f%.doc}.luc"
        echo "== $src (doc)"
        run ./build/luce doc "$src" > build/conformance.out
        cmp build/conformance.out "$f"
        programs=$((programs + 1))
    done
    # a program beside a `.explain` file: each line `LINE:COLUMN|answer` is what
    # `luce explain` says of that place (§17.5)
    for f in "$dir"*.explain; do
        [ -e "$f" ] || continue
        src="${f%.explain}.luc"
        echo "== $src (explain)"
        while IFS='|' read -r place want; do
            got=$(run ./build/luce explain "$src:$place" 2>&1) || { echo "FAIL $src:$place: [$got]"; exit 1; }
            [ "$got" = "$want" ] || { echo "FAIL $src:$place: expected [$want], got [$got]"; exit 1; }
        done < "$f"
        programs=$((programs + 1))
    done
    # a program beside a `.trap` file must stop with that text on every execution
    for f in "$dir"*.trap; do
        [ -e "$f" ] || continue
        src="${f%.trap}.luc"
        want=$(cat "$f")
        echo "== $src (traps)"
        if reject ./build/luce run "$src" > build/conformance.out 2> build/conformance.err; then
            echo "FAIL $src: expected a trap, the program finished"; exit 1
        else
            rc=$?
            [ "$rc" -eq 1 ] || { echo "FAIL $src: unexpected status $rc"; exit 1; }
        fi
        grep -q "$want" build/conformance.err || { echo "FAIL $src: expected [$want], got [$(cat build/conformance.err)]"; exit 1; }
        for flags in "" "--release" "--native"; do
            run ./build/luce build "$src" -o build/conformance $flags
            if reject ./build/conformance > build/conformance.out 2> build/conformance.err; then
                echo "FAIL $src ($flags): expected a trap, the compiled program finished"; exit 1
            else
                rc=$?
                [ "$rc" -eq 1 ] || { echo "FAIL $src: unexpected status $rc"; exit 1; }
            fi
            grep -q "$want" build/conformance.err || { echo "FAIL $src ($flags): expected [$want], got [$(cat build/conformance.err)]"; exit 1; }
        done
        programs=$((programs + 1))
    done
    for f in "$dir"errors/*.luc "$dir"errors/*/main.luc; do
        [ -e "$f" ] || continue
        want=$(LC_ALL=C sed -n 's/^# error: //p' "$f")
        [ -n "$want" ] || continue
        got=$(reject ./build/luce check "$f" 2>&1) && rc=0 || rc=$?
        if [ "$rc" -eq 0 ]; then echo "FAIL $f: accepted"; exit 1; fi
        if [ "$rc" -ne 1 ]; then echo "FAIL $f: status $rc: [$got]"; exit 1; fi
        case "$got" in
            *.luc:[0-9]*:[0-9]*:\ *) ;;
            *) echo "FAIL $f: a diagnostic without a position: [$got]"; exit 1;;
        esac
        # every `# error:` line names a diagnostic the run must print (§17.2)
        echo "$want" | while IFS= read -r line; do
            case "$got" in
                *"$line"*) ;;
                *) echo "FAIL $f: expected [$line], got [$got]"; exit 1;;
            esac
        done || exit 1
        rejections=$((rejections + 1))
    done
done
echo "ok conformance: $programs programs, $rejections rejections, $parsed parsed"

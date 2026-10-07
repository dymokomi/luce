#!/bin/sh
# One conformance case, in a directory of its own so cases run at once (run.sh):
# `case.sh expect|tests|doc|explain|trap|error FILE`. Its output is kept and printed whole:
# its header line when it passes, everything when it fails (status 1).
set -eu
cd "$(dirname "$0")/../.."
export LUCE_BASE=${LUCE_BASE:-$PWD/build/luce-base/build/luce-base}
kind=$1
f=$2
work=$(mktemp -d build/cases/case.XXXXXX)
log=$work/log
run() { python3 tools/run_case.py -- "$@"; }
reject() { python3 tools/run_case.py --expected 1 -- "$@"; }
compare() { diff -u "$1" "$work/out"; }
fail() { echo "$*" >> "$log"; cat "$log"; rm -rf "$work"; exit 1; }
# a program is a file beside its `.expect`, or a directory of modules whose entry is
# `main.luc` (§15), a `src/main.luc` under a manifest among them
expect() {
    src="${f%.expect}.luc"
    input="${f%.expect}.input"
    [ -e "$input" ] || input=/dev/null
    echo "== $src"
    # a directory program counts the Base modules of the packages it carries too
    if [ "$(basename "$src")" = main.luc ]; then
        bases=$(find "$(dirname "$src")" -name '*.lucb' | head -n 1)
    else
        bases=$(ls "$(dirname "$src")"/*.lucb 2>/dev/null | head -n 1)
    fi
    if [ -n "$bases" ]; then
        # a program importing a Base module is built, never run in the interpreter (§16)
        if reject ./build/luce run "$src" > "$work/out" 2> "$work/err"; then
            echo "FAIL $src: the interpreter ran a program that imports a Base module"; return 1
        else
            rc=$?
            [ "$rc" -eq 1 ] || { echo "FAIL $src: unexpected status $rc"; return 1; }
        fi
        grep -q "the interpreter runs Luce alone" "$work/err" || { echo "FAIL $src: [$(cat "$work/err")]"; return 1; }
    else
        echo "   interpreter"
        run ./build/luce run "$src" < "$input" > "$work/out" || return 1
        compare "$f" || return 1
    fi
    # Native optimization levels are independent correctness targets; C remains
    # a supplemental comparison for the emitted Base.
    for flags in "--native --opt 0" "--native --opt 1" "--native --opt 2" "--native --opt 3" "--backend=c" "--backend=c --release"; do
        echo "   compiled $flags"
        run ./build/luce build "$src" -o "$work/program" $flags || return 1
        run "$work/program" < "$input" > "$work/out" || return 1
        compare "$f" || return 1
    done
}
# a program beside a `.tests` file prints that report under `luce test`, from the
# interpreter and from a built runner alike (§17.3); the status is 1 when a test failed
tests() {
    src="${f%.tests}.luc"
    echo "== $src (tests)"
    if grep -q ' failed$' "$f"; then want_status=1; else want_status=0; fi
    for flags in "" "--build --native --opt 0" "--build --native --opt 1" "--build --native --opt 2" "--build --native --opt 3" "--build --backend=c" "--build --backend=c --release"; do
        python3 tools/run_case.py --expected "$want_status" -- ./build/luce test "$src" $flags > "$work/out" 2>&1 && status=0 || status=$?
        [ "$status" -eq "$want_status" ] || { echo "FAIL $src ($flags): status $status, expected $want_status: [$(cat "$work/out")]"; return 1; }
        cmp "$work/out" "$f" || return 1
    done
}
# a program beside a `.doc` file documents as it says (§17.4)
doc() {
    src="${f%.doc}.luc"
    echo "== $src (doc)"
    run ./build/luce doc "$src" > "$work/out" || return 1
    cmp "$work/out" "$f"
}
# a program beside a `.explain` file: each line `LINE:COLUMN|answer` is what
# `luce explain` says of that place (§17.5)
explain() {
    src="${f%.explain}.luc"
    echo "== $src (explain)"
    while IFS='|' read -r place want; do
        got=$(run ./build/luce explain "$src:$place" 2>&1) || { echo "FAIL $src:$place: [$got]"; return 1; }
        [ "$got" = "$want" ] || { echo "FAIL $src:$place: expected [$want], got [$got]"; return 1; }
    done < "$f"
}
# a program beside a `.trap` file must stop with that text on every execution
trapping() {
    src="${f%.trap}.luc"
    want=$(cat "$f")
    echo "== $src (traps)"
    if reject ./build/luce run "$src" > "$work/out" 2> "$work/err"; then
        echo "FAIL $src: expected a trap, the program finished"; return 1
    else
        rc=$?
        [ "$rc" -eq 1 ] || { echo "FAIL $src: unexpected status $rc"; return 1; }
    fi
    grep -q "$want" "$work/err" || { echo "FAIL $src: expected [$want], got [$(cat "$work/err")]"; return 1; }
    for flags in "--native --opt 0" "--native --opt 1" "--native --opt 2" "--native --opt 3" "--backend=c" "--backend=c --release"; do
        run ./build/luce build "$src" -o "$work/program" $flags || return 1
        if reject "$work/program" > "$work/out" 2> "$work/err"; then
            echo "FAIL $src ($flags): expected a trap, the compiled program finished"; return 1
        else
            rc=$?
            [ "$rc" -eq 1 ] || { echo "FAIL $src: unexpected status $rc"; return 1; }
        fi
        grep -q "$want" "$work/err" || { echo "FAIL $src ($flags): expected [$want], got [$(cat "$work/err")]"; return 1; }
    done
}
# a program under `errors/` is rejected with every diagnostic its `# error:` lines name, at
# a position (§17.2)
rejected() {
    want=$(LC_ALL=C sed -n 's/^# error: //p' "$f")
    echo "== $f (rejected)"
    got=$(reject ./build/luce check "$f" 2>&1) && rc=0 || rc=$?
    [ "$rc" -ne 0 ] || { echo "FAIL $f: accepted"; return 1; }
    [ "$rc" -eq 1 ] || { echo "FAIL $f: status $rc: [$got]"; return 1; }
    case "$got" in
        *.luc:[0-9]*:[0-9]*:\ *) ;;
        *) echo "FAIL $f: a diagnostic without a position: [$got]"; return 1;;
    esac
    echo "$want" | while IFS= read -r line; do
        case "$got" in
            *"$line"*) ;;
            *) echo "FAIL $f: expected [$line], got [$got]"; exit 1;;
        esac
    done
}
case "$kind" in
    expect) expect > "$log" 2>&1 || fail "FAIL $f";;
    tests) tests > "$log" 2>&1 || fail "FAIL $f";;
    doc) doc > "$log" 2>&1 || fail "FAIL $f";;
    explain) explain > "$log" 2>&1 || fail "FAIL $f";;
    trap) trapping > "$log" 2>&1 || fail "FAIL $f";;
    error) rejected > "$log" 2>&1 || fail "FAIL $f";;
    *) echo "case.sh: unknown kind $kind"; exit 2;;
esac
head -1 "$log"
rm -rf "$work"

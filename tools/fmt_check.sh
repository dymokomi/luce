#!/bin/sh
# Every program of the suite formats to a module the parser reads back into the same tree,
# and formatting the result again changes nothing (§17.6).
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/fmt
checked=0
for f in $(find tests/conformance -name '*.luc' -not -path '*/errors/*' | sort); do
    ./build/luce fmt "$f" > build/fmt/once.luc
    ./build/luce parse "$f" | sed -e 's/ @[0-9]*//g' -e '1s/(module .*/(module/' > build/fmt/before.txt
    ./build/luce parse build/fmt/once.luc | sed -e 's/ @[0-9]*//g' -e '1s/(module .*/(module/' > build/fmt/after.txt
    cmp build/fmt/before.txt build/fmt/after.txt || { echo "FAIL $f: formatting changed the tree"; exit 1; }
    ./build/luce fmt build/fmt/once.luc > build/fmt/twice.luc
    cmp build/fmt/once.luc build/fmt/twice.luc || { echo "FAIL $f: formatting twice differs from once"; exit 1; }
    checked=$((checked + 1))
done
echo "ok fmt: $checked programs"

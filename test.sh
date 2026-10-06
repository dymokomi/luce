#!/bin/sh
# The gate. Green, or the tree does not move.
set -eu
cd "$(dirname "$0")"
./build.sh
python3 tools/test_run_case.py
python3 tools/test_sandbox.py
sh tools/test_install_layout.sh
base=${LUCE_BASE_COMPILER:-build/luce-base/build/luce-base}
case "$base" in /*) ;; *) base=$PWD/$base ;; esac
export LUCE_BASE=$base
python3 tools/test_native_default.py
python3 tools/test_diagnostic_profile.py
python3 tools/test_package_tests.py
python3 tools/test_program_identity.py
python3 tools/test_toolchain_choice.py
python3 tools/test_build_cache.py
# the compile budget with both compilers named relative to here, a Luce entry first
# the shape of the tree never regresses (luce-base tools/shape.py, the limits in tools/shape.limits)
python3 "$(dirname "$base")/../tools/shape.py" --check --root .
python3 "$(dirname "$base")/../tools/compile_budget.py" --compiler "$base" --luce build/luce --seconds 240 --megabytes 2048 tests/programs/calc/main.luc
python3 tools/test_build_cleanup.py
python3 tools/test_base_packages.py
python3 tools/test_public_imports.py
python3 tools/test_native_manifest.py
python3 tools/test_native_packages.py
python3 tools/test_base_fields.py
python3 tools/test_base_description.py
python3 tools/test_base_defaults.py
python3 tools/test_base_values.py
python3 tools/test_base_objects.py
python3 tools/test_base_views.py
python3 tools/test_base_interfaces.py
python3 tools/test_base_callbacks.py
python3 tools/test_base_workers.py
python3 tools/test_gpu_frames.py
python3 tools/test_worker_heap.py
python3 tools/embed_version.py --check
python3 tools/embed_runtime.py --check
python3 tools/embed_prelude.py --check
# a file module by its file, a directory module (its ORDER and fragments) by its directory
for f in src/*.lucb src/*/*.lucb src/*/*/ORDER rt/*.lucb rt/*/ORDER; do
    [ -e "$f" ] || continue
    case "$f" in */ORDER) f=$(dirname "$f") ;; esac
    echo "== check $f"
    "$base" check "$f"
    if grep -rqs '^test "' "$f"; then
        echo "== test $f"
        "$base" test "$f"
        "$base" test "$f" --backend=c
    fi
done
echo "== luce --version"
./build/luce --version
# a program read from a pipe is read once: the import prescan and the check see one text
[ "$(printf 'pub func main(arguments: list[str]) -> int!:\n    print("piped")\n    return 0\n' | ./build/luce run /dev/stdin)" = "piped" ] || { echo "FAIL: luce run /dev/stdin"; exit 1; }
tests/conformance/run.sh
# the guide: every complete program in docs/guide runs in the interpreter and built, and
# prints what the page shows; the site built from docs/ has no link to a missing page
python3 tools/doc_examples.py
python3 tools/site.py build/site > /dev/null
tools/fmt_check.sh
python3 tools/fuzz.py --gate
# random object graphs through both collectors, collecting at every candidate too, under
# MallocScribble on macOS and valgrind on Linux (tools/cycles_fuzz.py)
python3 tools/cycles_fuzz.py --gate
echo ok

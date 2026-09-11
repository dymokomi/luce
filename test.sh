#!/bin/sh
# The gate. Green, or the tree does not move.
set -eu
cd "$(dirname "$0")"
./build.sh
python3 tools/test_run_case.py
base=${LUCE_BASE_COMPILER:-build/luce-base/build/luce-base}
case "$base" in /*) ;; *) base=$PWD/$base ;; esac
export LUCE_BASE=$base
python3 tools/test_native_default.py
python3 tools/test_build_cleanup.py
python3 tools/test_base_packages.py
python3 tools/test_public_imports.py
python3 tools/test_native_manifest.py
python3 tools/test_base_fields.py
python3 tools/test_base_description.py
python3 tools/test_base_defaults.py
python3 tools/test_base_values.py
python3 tools/test_base_objects.py
python3 tools/test_base_views.py
python3 tools/test_base_interfaces.py
python3 tools/test_base_callbacks.py
python3 tools/test_base_workers.py
python3 tools/test_standard_json.py
python3 tools/test_worker_heap.py
python3 tools/embed_version.py --check
python3 tools/embed_runtime.py --check
for f in src/*.lucb src/*/*.lucb rt/*.lucb; do
    [ -e "$f" ] || continue
    echo "== check $f"
    "$base" check "$f"
    if grep -q '^test "' "$f"; then
        echo "== test $f"
        "$base" test "$f"
        "$base" test "$f" --backend=c
    fi
done
echo "== luce --version"
./build/luce --version
tests/conformance/run.sh
tools/fmt_check.sh
python3 tools/fuzz.py --gate
echo ok

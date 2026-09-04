#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root"
PATH="$repo_root/stage0/bin:$PATH"
export PATH

# The in-repo stage-0 compiler must link against its own matching runtime.
# Clear any LUCE_LIB inherited from a separately installed toolchain, whose
# libluce_rt.a can be an older version missing symbols this compiler emits.
unset LUCE_LIB

# Prefer a locally built fast-codegen compiler (O1 + FastISel) for the
# edit/test loop; the shipped archive contains only luce-0.
luce=./stage0/bin/luce-0-fast
[ -x "$luce" ] || luce=./stage0/bin/luce-0

if ! command -v qbe >/dev/null 2>&1; then
    echo "test: QBE 1.3 not found; run ./bootstrap.sh" >&2
    exit 1
fi

# 1. Architectural boundary: target and backend concepts begin at backends/.
# Frontend, HIR, and MIR are lowered once and must remain target-neutral.
if grep -R -n -E 'compiler\.backends|TargetLayout|LayoutRules|TypeLayout|pointer_(size|align)|arm64|x86_64|wasm32|macos|linux' \
    src/compiler/frontend src/compiler/hir src/compiler/mir src/compiler/profiles/*/hir src/compiler/profiles/*/mir; then
    echo "platform dependency found before the backend boundary" >&2
    exit 1
fi
if grep -n -E 'arm64|x86_64|wasm32|macos|linux' src/compiler/backends/layout.luc; then
    echo "concrete target found in shared backend layout" >&2
    exit 1
fi

# 1b. Profile boundary (docs/compiler/plan.md §5.0): code only one profile
#     executes lives in its profile folder, the two folders never import each
#     other, and the shared folders name a profile only through profile.luc
#     and the one dispatch point per stage.
if grep -R -n 'compiler\.profiles\.base' src/compiler/profiles/full; then
    echo "the full profile imports the base profile" >&2
    exit 1
fi
if grep -R -n 'compiler\.profiles\.full' src/compiler/profiles/base; then
    echo "the base profile imports the full profile" >&2
    exit 1
fi
dispatch_points='src/compiler/hir/analyzer.luc
src/compiler/hir/body_checker.luc
src/compiler/hir/declarations.luc
src/compiler/hir/entry_points.luc
src/compiler/mir/function_lowerer.luc
src/compiler/backends/interpreter.luc
src/compiler/backends/mir_interpreter.luc
src/compiler/backends/qbe.luc
src/compiler/backends/qbe_toolchain.luc
src/compiler/backends/wasm.luc
src/compiler/backends/wasm_plan.luc'
profile_importers=$(grep -R -l 'compiler\.profiles\.' src/compiler/frontend src/compiler/hir src/compiler/mir src/compiler/backends src/compiler/c_api src/compiler/packages src/compiler/*.luc || true)
for importer in $profile_importers; do
    if ! printf '%s\n' "$dispatch_points" | grep -q -x "$importer"; then
        echo "$importer names a profile outside profile.luc and the dispatch points" >&2
        exit 1
    fi
done
# 1c. No dialect branches in shared code (decision of 2026-09-04, plan.md
#     §5.0): a shared stage asks `profile.luc` what a profile admits or hands
#     the decision to the profile's own class; it never compares profiles.
#     `mir/freestanding.luc` asks the admission table for one profile and
#     `packages/identity_codec.luc` decodes a stored authority tag.
if grep -R -n 'in_base_module()' src/compiler; then
    echo "a shared stage branches on the Base profile" >&2
    exit 1
fi
if grep -R -n -E 'Profile\.(base|full)|ModuleAuthority\.base' src/compiler/frontend src/compiler/hir src/compiler/mir src/compiler/backends src/compiler/c_api src/compiler/packages \
    | grep -v -E '^src/compiler/(mir/freestanding\.luc|packages/identity_codec\.luc|frontend/(parser|tokenizer)\.luc:[0-9]+: +pub init)'; then
    echo "a shared stage names a profile outside profile.luc and the admission tables" >&2
    exit 1
fi

# 2. Unit tests: every tests/compiler/**/*_test.luc file.
"$luce" test

# 3. Command-line contract: exit statuses, usage, and that every failure
#    path prints its diagnostic (tests/cli_test.sh).
./tests/cli_test.sh ./stage0/bin/luce-0

# WebAssembly execution under wasmtime, when it is installed.
./tests/wasm_test.sh ./stage0/bin/luce-0

# 4. Native smoke test: QBE and the host toolchain build and run the same
#    executable path on every supported bootstrap host.
./tests/native_test.sh ./stage0/bin/luce-0

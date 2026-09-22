#!/bin/sh
# Package the built compiler for this host: `tools/package.sh [OUT_DIR]`, OUT_DIR defaulting
# to build/release. The archive is `luce-VERSION-HOST.tar.gz` with a SHA-256 beside it,
# holding one tree, `luce-VERSION/`:
#
#   bin/luce                          the compiler (luce.exe on Windows)
#   bin/luce-base                     the Base compiler it emits to, from bootstrap/BASE
#   share/luce-base/std/              Base's standard library source, read with every build
#   share/luce/                       licences, VERSION, the language and runtime documents
#
# `luce` finds `luce-base` beside itself and luce-base finds the library beside its `bin`,
# so the tree runs from wherever it is unpacked; a program it builds links the library
# statically and needs nothing from the tree at run time. The Base tree is the one
# build.sh built under build/luce-base/build, or the one `LUCE_BASE_BUILD` names (the
# Windows build uses ../luce-base/build). Runs on macOS, Linux, and Windows in MSYS2.
set -eu
cd "$(dirname "$0")/.."
export COPYFILE_DISABLE=1
export LC_ALL=C
umask 022
out=${1:-build/release}
version=$(tr -d '[:space:]' < VERSION)
host=$(tools/host.sh)
case "$host" in
    x86_64-windows) exe=build/luce.exe; name=luce.exe; base_name=luce-base.exe; base_build=${LUCE_BASE_BUILD:-../luce-base/build};;
    *) exe=build/luce; name=luce; base_name=luce-base; base_build=${LUCE_BASE_BUILD:-build/luce-base/build};;
esac
std="$base_build/../src/std"
for f in "$exe" "$base_build/$base_name" "$std/ORDER"; do
    [ -f "$f" ] || { echo "package.sh: $f is missing; build first" >&2; exit 1; }
done
[ "$("$exe" --version)" = "luce $version" ] || { echo "package.sh: the built compiler is not version $version" >&2; exit 1; }
tree="luce-$version"
work="$out/tree"
rm -rf "$work"
mkdir -p "$work/$tree/bin" "$work/$tree/share/luce-base" "$work/$tree/share/luce/docs"
cp "$exe" "$work/$tree/bin/$name"
cp "$base_build/$base_name" "$work/$tree/bin/$base_name"
chmod 755 "$work/$tree/bin/$name" "$work/$tree/bin/$base_name"
# Bundle luc, the project tool, so installing the language installs it too. It is built with
# the Base compiler in this tree, from the luce-luc checkout (LUCE_LUC_SOURCE, default
# ../luce-luc); a release always has it, a bare dev package warns and ships without it.
luc_source=${LUCE_LUC_SOURCE:-../luce-luc}
if [ -f "$luc_source/build.sh" ]; then
    case "$host" in x86_64-windows) luc_name=luc.exe;; *) luc_name=luc;; esac
    # luc's build.sh reports its failures on stdout; keep them visible in a release log.
    LUCE_BASE_COMPILER="$PWD/$base_build/$base_name" "$luc_source/build.sh" >&2
    cp "$luc_source/build/$luc_name" "$work/$tree/bin/$luc_name"
    chmod 755 "$work/$tree/bin/$luc_name"
    echo "package.sh: bundled $("$work/$tree/bin/$luc_name" --version)"
else
    echo "package.sh: no luce-luc at $luc_source; the archive will not include luc" >&2
fi
cp -R "$std" "$work/$tree/share/luce-base/std"
cp LICENSE LICENSE-MIT LICENSE-APACHE VERSION "$work/$tree/share/luce/"
cp docs/luce.md docs/RUNTIME.md "$work/$tree/share/luce/docs/"
"$base_build/$base_name" --version > "$work/$tree/share/luce/BASE"
archive="luce-$version-$host.tar.gz"
mkdir -p "$out"
rm -f "$out/$archive" "$out/$archive.sha256"
(cd "$work" && tar -czf "../$archive" "$tree")
rm -rf "$work"
if command -v sha256sum > /dev/null 2>&1; then
    (cd "$out" && sha256sum "$archive" > "$archive.sha256")
else
    (cd "$out" && shasum -a 256 "$archive" > "$archive.sha256")
fi
echo "packaged $out/$archive ($(wc -c < "$out/$archive" | tr -d ' ') bytes)"

#!/bin/sh
# Install the pinned tools this repository builds and tests with: the Stage-0
# 0.28 compiler/runtime and QBE 1.3. Every downloaded archive is verified
# before it is unpacked; the resulting executables live under ./stage0/bin/.
set -eu

release_tag=stage0
repo=dymokomi/luce-stage-0
stage0_version=0.28
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix="$here/stage0"

os=$(uname -s)
arch=$(uname -m)
case "$os-$arch" in
    Darwin-arm64) flavor=macos-aarch64 ;;
    Linux-x86_64) flavor=linux-x86_64 ;;
    *) echo "bootstrap: no stage-0 archive for $os/$arch" >&2; exit 1 ;;
esac

# Checksums, one per flavor. bootstrap refuses to install an archive it
# cannot verify.
#
# These are the digests published with the 0.28 release assets built from
# source commit d5b458355179c059ce9c506c37990612c2c8f68f.
checksum_macos_aarch64=2ad464b80e8b314eac66dbbe8c3468f337a049ae1b1da068fc749f57366ce7a1
checksum_linux_x86_64=8871dad25cd5c23b63d76183f55cfa48ec483331e39edb4947544288a9665d16

eval "expected=\$checksum_$(printf %s "$flavor" | tr - _)"
[ "$expected" != TBD ] || { echo "bootstrap: checksum missing for $flavor" >&2; exit 1; }

archive="luce-$stage0_version-$flavor.tar.gz"
url="https://github.com/$repo/releases/download/$release_tag/$archive"
qbe_archive=qbe-1.3.tar.xz
qbe_url="https://c9x.me/compile/release/$qbe_archive"
qbe_checksum=d587905d620dc5e1d2bfa7c2cc642b9b837aa89a3188c6e37b53d756cf66e320
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "bootstrap: fetching $archive"
curl -fsSL -o "$work/$archive" "$url"
actual=$(shasum -a 256 "$work/$archive" | awk '{print $1}')
[ "$actual" = "$expected" ] || {
    echo "bootstrap: checksum mismatch for $archive" >&2
    echo "  expected $expected" >&2
    echo "  got      $actual" >&2
    exit 1
}

rm -rf "$prefix"
mkdir -p "$prefix"
tar -xzf "$work/$archive" -C "$prefix" --strip-components=1
echo "bootstrap: stage-0 installed at $prefix"
"$prefix/bin/luce-0" --version

echo "bootstrap: fetching $qbe_archive"
curl -fsSL -o "$work/$qbe_archive" "$qbe_url"
actual=$(shasum -a 256 "$work/$qbe_archive" | awk '{print $1}')
[ "$actual" = "$qbe_checksum" ] || {
    echo "bootstrap: checksum mismatch for $qbe_archive" >&2
    echo "  expected $qbe_checksum" >&2
    echo "  got      $actual" >&2
    exit 1
}
tar -xJf "$work/$qbe_archive" -C "$work"
make -C "$work/qbe-1.3"
cp "$work/qbe-1.3/qbe" "$prefix/bin/qbe"
echo "bootstrap: QBE 1.3 installed at $prefix/bin/qbe"

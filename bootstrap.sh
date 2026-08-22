#!/bin/sh
# Install the pinned stage-0 Luce toolchain this repository builds with.
# Downloads the archive for this machine from the stage0 release of
# dymokomi/luce-stage-0, verifies its checksum, and unpacks to ./stage0/.
set -eu

release_tag=stage0
repo=dymokomi/luce-stage-0
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix="$here/stage0"

os=$(uname -s)
arch=$(uname -m)
case "$os-$arch" in
    Darwin-arm64) flavor=macos-aarch64 ;;
    Linux-x86_64) flavor=linux-x86_64 ;;
    Linux-aarch64) flavor=linux-aarch64 ;;
    *) echo "bootstrap: no stage-0 archive for $os/$arch" >&2; exit 1 ;;
esac

# Pinned checksums, one per flavor — filled in when the release is cut.
# bootstrap refuses to install an archive it cannot verify.
checksum_macos_aarch64=eaee9afc1b8da7979b7fcf770c423fda3499b23335c11cd6b165a8d8b66dc2e6
checksum_linux_x86_64=af6bee70c40760add351b4b28c9ce9ab6ef7bc0e94ba0ff4c0ee5c5d1e421f60
checksum_linux_aarch64=ff504ec72d3f8bd78778016e65fd924eeb08daedce6354440009ab29ca2f490c

eval "expected=\$checksum_$(printf %s "$flavor" | tr - _)"
[ "$expected" != TBD ] || { echo "bootstrap: checksum for $flavor not pinned yet" >&2; exit 1; }

archive="luce-0.18-$flavor.tar.gz"
url="https://github.com/$repo/releases/download/$release_tag/$archive"
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

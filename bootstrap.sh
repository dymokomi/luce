#!/bin/sh
# Install the Stage-0 0.25 toolchain this repository builds with.
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
    *) echo "bootstrap: no stage-0 archive for $os/$arch" >&2; exit 1 ;;
esac

# Checksums, one per flavor. bootstrap refuses to install an archive it
# cannot verify.
checksum_macos_aarch64=2d2ada820983b6d8869ade6e43b67b41178ab319bb8e8a4cec6c588c21d934c5
checksum_linux_x86_64=15be55f292dd466da8ee276d107541a3e4013b34eaa6b6db7e9c4c6d11f1acbd

eval "expected=\$checksum_$(printf %s "$flavor" | tr - _)"
[ "$expected" != TBD ] || { echo "bootstrap: checksum missing for $flavor" >&2; exit 1; }

archive="luce-0.25-$flavor.tar.gz"
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

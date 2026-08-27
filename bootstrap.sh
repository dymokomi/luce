#!/bin/sh
# Install the Stage-0 0.23 toolchain this repository builds with.
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
checksum_macos_aarch64=eb0a3c0e5cfa2b137cf06634bc907a6a0314d5d7494042cbbb86e3ba2c38713b
checksum_linux_x86_64=e64166529c256ff20c955032bc9fd254496a43ca38caa93875c3fdc16cbcdcdf

eval "expected=\$checksum_$(printf %s "$flavor" | tr - _)"
[ "$expected" != TBD ] || { echo "bootstrap: checksum missing for $flavor" >&2; exit 1; }

archive="luce-0.23-$flavor.tar.gz"
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

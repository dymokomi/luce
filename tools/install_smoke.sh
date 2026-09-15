#!/bin/sh
# Prove a packaged archive works where it is unpacked: `tools/install_smoke.sh ARCHIVE
# WORK_DIR`. The checksum is verified, the tree unpacked under WORK_DIR, and `luce` there
# runs a program in its interpreter and builds it natively through the bundled Base
# compiler, with only its own tree and the host's C toolchain, as an installed copy would.
set -eu
archive=$1
work=$2
[ -f "$archive" ] || { echo "install_smoke.sh: $archive is missing" >&2; exit 1; }
rm -rf "$work"
mkdir -p "$work"
directory=$(dirname "$archive")
name=$(basename "$archive")
if command -v sha256sum > /dev/null 2>&1; then
    (cd "$directory" && sha256sum -c "$name.sha256")
else
    (cd "$directory" && shasum -a 256 -c "$name.sha256")
fi
tar -xzf "$archive" -C "$work"
tree=$(ls "$work")
bin="$work/$tree/bin"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) compiler="$bin/luce.exe"; program="$work/hello.exe";; *) compiler="$bin/luce"; program="$work/hello";; esac
unset LUCE_BASE
"$compiler" --version
printf 'pub func main(arguments: list[str]) -> int!:\n    print("hello from luce,", 2 ** 10)\n    return 0\n' > "$work/hello.luc"
[ "$("$compiler" run "$work/hello.luc")" = "hello from luce, 1024" ]
"$compiler" build "$work/hello.luc" -o "$program"
[ "$("$program")" = "hello from luce, 1024" ]
echo "ok install smoke: $tree runs and builds a program with the bundled Base compiler"

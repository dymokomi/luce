#!/bin/sh
# The host as a target name of base.md §19.5, from uname: `arm64-macos`, `x86_64-linux`,
# `x86_64-macos`, `x86_64-windows` (from Git's or MSYS2's bash).
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) echo arm64-macos;;
    Darwin-x86_64) echo x86_64-macos;;
    Linux-x86_64) echo x86_64-linux;;
    MINGW64_NT-*-x86_64|MSYS_NT-*-x86_64|CYGWIN_NT-*-x86_64) echo x86_64-windows;;
    *) echo "host.sh: unknown host $(uname -s)-$(uname -m)" >&2; exit 1;;
esac

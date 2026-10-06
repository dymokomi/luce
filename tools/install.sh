#!/bin/sh
# Install the Luce compiler on macOS or Linux.
#
#   curl -fsSL https://luce.luciaos.com/install.sh | sh && . "$HOME/.local/luce/env"
#
# The release archive for this machine is downloaded from the GitHub release, its SHA-256
# checked against the published digest, its contents checked, and only then does it
# replace ~/.local/luce; an interrupted run leaves the previous installation in
# place. ~/.local/luce/env puts bin/ and ~/.luce/bin (where `luc install` links
# applications) on PATH; the shell's startup profile sources it, and sourcing it by hand,
# as the command above does, makes the current terminal ready at once. Running it again
# installs a fresh copy of the same release; `luc update` runs it for the tree luc is in.
#
# Overrides, for testing and managed layouts, all absolute paths:
#   LUCE_INSTALL_DIR      where to install (default ~/.local/luce)
#   LUC_HOME              where luc keeps what it installs (default ~/.luce); env sets it
#   LUCE_INSTALL_VERSION  the release to install (default the one below)
#   LUCE_INSTALL_URL      the directory the archives are read from; a file:// URL works
#   LUCE_INSTALL_PROFILE  the startup file to edit (default the login shell's)
#   LUCE_INSTALL_NO_PATH  1 leaves every startup file alone
# A startup file is edited for the default place alone, ~/.local/luce with ~/.luce, or
# when LUCE_INSTALL_PROFILE names one: an install anywhere else is sourced from its env.
set -eu

version=0.14.0
product=luce
version=${LUCE_INSTALL_VERSION:-$version}
base_url=${LUCE_INSTALL_URL:-https://github.com/dymokomi/luce/releases/download/luce-$version}
install_root=${LUCE_INSTALL_DIR:-$HOME/.local/luce}
luc_home=${LUC_HOME:-$HOME/.luce}
profile_override=${LUCE_INSTALL_PROFILE:-}

system=$(uname -s)
machine=$(uname -m)
case "$system:$machine" in
    Darwin:arm64|Darwin:aarch64) host=arm64-macos; host_name='macOS on Apple Silicon' ;;
    Darwin:*)
        echo "$product: this macOS release is for Apple Silicon; use a native arm64 shell, not a Rosetta one" >&2
        exit 1 ;;
    Linux:x86_64|Linux:amd64) host=x86_64-linux; host_name='Linux x86-64' ;;
    Linux:aarch64|Linux:arm64) host=arm64-linux; host_name='Linux ARM64' ;;
    Linux:*)
        echo "$product: released for Linux x86-64 and ARM64, not Linux $machine; build from source instead" >&2
        exit 1 ;;
    *)
        echo "$product: this installer is for macOS and Linux; on Windows run: irm https://luce.luciaos.com/install.ps1 | iex" >&2
        exit 1 ;;
esac
archive_name="$product-$version-$host.tar.gz"

for tool in awk curl dirname grep mkdir mktemp mv rm tar tr uname; do
    command -v "$tool" > /dev/null 2>&1 || { echo "$product: required command not found: $tool" >&2; exit 1; }
done
if command -v sha256sum > /dev/null 2>&1; then
    checksum_tool=sha256sum
elif command -v shasum > /dev/null 2>&1; then
    checksum_tool=shasum
else
    echo "$product: SHA-256 verification needs sha256sum or shasum" >&2
    exit 1
fi

# The compilers drive the host's C toolchain to assemble and link; without it, a
# successful install would leave a compiler that cannot build its first program.
missing=""
for tool in cc as ar nm; do
    command -v "$tool" > /dev/null 2>&1 || missing="$missing $tool"
done
if [ -n "$missing" ] || ! cc --version > /dev/null 2>&1; then
    echo "$product: a C toolchain is required (missing:${missing:- a working cc})" >&2
    case "$system" in
        Darwin) echo "$product: install it with: xcode-select --install" >&2 ;;
        Linux)
            echo "$product: Debian/Ubuntu: sudo apt install build-essential" >&2
            echo "$product: Fedora/RHEL:   sudo dnf install gcc" >&2
            echo "$product: Arch:          sudo pacman -S base-devel" >&2 ;;
    esac
    echo "$product: install the toolchain, then run this command again" >&2
    exit 1
fi
if [ "$system" = Linux ]; then
    glibc=$(getconf GNU_LIBC_VERSION 2> /dev/null | awk '{ print $2 }')
    if [ -z "$glibc" ] || ! printf '%s\n' "$glibc" | awk -F. '{ ok = ($1 > 2 || ($1 == 2 && $2 >= 35)) } END { exit ok ? 0 : 1 }'; then
        echo "$product: this Linux release needs glibc 2.35 or newer (found ${glibc:-none}); build from source on this system" >&2
        exit 1
    fi
fi

# An override may not turn a user installer into a request to replace a system tree,
# and what the profile will quote may not carry shell syntax into a later `source`.
check_path() {
    label=$1
    value=$2
    case "$value" in
        /*) ;;
        *) echo "$product: $label must be an absolute path: $value" >&2; exit 1 ;;
    esac
    case "$value" in
        /|/bin|/bin/*|/boot|/boot/*|/dev|/dev/*|/etc|/etc/*|/lib|/lib/*|/lib64|/lib64/*|/proc|/proc/*|/run|/run/*|/sbin|/sbin/*|/sys|/sys/*|/usr|/usr/*|/var|/var/*|/System|/System/*|/Library|/Library/*)
            echo "$product: refusing a system directory for $label: $value" >&2; exit 1 ;;
    esac
    cleaned=$(printf '%s' "$value" | tr -d '\001-\037\177')
    if [ "$cleaned" != "$value" ] || ! awk 'BEGIN {
        value = ARGV[1]
        forbidden = "`$\\\"();&|<>[]{}"
        for (i = 1; i <= length(forbidden); i++)
            if (index(value, substr(forbidden, i, 1)) != 0) exit 1
    }' "$value"; then
        echo "$product: $label contains shell-sensitive characters: $value" >&2
        exit 1
    fi
}
check_path LUCE_INSTALL_DIR "$install_root"
check_path LUC_HOME "$luc_home"
[ -z "$profile_override" ] || check_path LUCE_INSTALL_PROFILE "$profile_override"

parent=$(dirname "$install_root")
mkdir -p "$parent"
tmp=$(mktemp -d "$parent/.$product-install.XXXXXX")
backup_dir=$(mktemp -d "$parent/.$product-old.XXXXXX")
cleanup() { rm -rf "$tmp" "$backup_dir"; }
trap cleanup 0 HUP INT TERM

echo "==> downloading $product $version for $host_name"
archive="$tmp/$archive_name"
curl --fail --location --silent --show-error --retry 3 "$base_url/$archive_name" -o "$archive"
curl --fail --location --silent --show-error --retry 3 "$base_url/$archive_name.sha256" -o "$archive.sha256"

expected=$(awk 'NF { print $1; exit }' "$archive.sha256" | tr 'A-F' 'a-f')
if ! printf '%s\n' "$expected" | awk 'length($0) == 64 && $0 !~ /[^0-9a-f]/ { ok = 1 } END { exit ok ? 0 : 1 }'; then
    echo "$product: the published checksum is not a SHA-256 digest" >&2
    exit 1
fi
case "$checksum_tool" in
    sha256sum) actual=$(sha256sum "$archive" | awk '{ print $1 }') ;;
    shasum) actual=$(shasum -a 256 "$archive" | awk '{ print $1 }') ;;
esac
if [ "$actual" != "$expected" ]; then
    echo "$product: the archive's checksum does not match the published digest" >&2
    exit 1
fi

# The checksum authenticates the bytes; the archive is still confined to its own
# directory, with no links or device entries, before anything is written.
tree="$product-$version"
if ! tar -tzf "$archive" | awk -v root="$tree" '
    function unsafe(path, count, parts, i) {
        if (path ~ /^\//) return 1
        count = split(path, parts, "/")
        for (i = 1; i <= count; i++) if (parts[i] == "..") return 1
        return 0
    }
    {
        path = $0
        sub(/\/$/, "", path)
        if (path == "" || unsafe(path)) bad = 1
        if (path != root && index(path, root "/") != 1) bad = 1
    }
    END { exit bad ? 1 : 0 }
'; then
    echo "$product: the archive contains an unsafe member path" >&2
    exit 1
fi
if ! tar -tvzf "$archive" | awk 'length($0) > 0 && substr($0, 1, 1) !~ /^[-d]$/ { bad = 1 } END { exit bad ? 1 : 0 }'; then
    echo "$product: the archive contains a link or a special file" >&2
    exit 1
fi
unpack="$tmp/unpack"
mkdir "$unpack"
tar -xzf "$archive" -C "$unpack"
release="$unpack/$tree"
[ -d "$release" ] || { echo "$product: the archive has no $tree directory" >&2; exit 1; }
[ "$(tr -d '[:space:]' < "$release/share/$product/VERSION")" = "$version" ] || { echo "$product: the archive's VERSION is not $version" >&2; exit 1; }
# `luce` compiles a program to Base and runs the `luce-base` beside it; both ship in the tree
for tool in luce luce-base; do
    [ -x "$release/bin/$tool" ] || { echo "$product: the archive has no bin/$tool" >&2; exit 1; }
done
# luc, the project tool, ships beside the compilers; Base's standard library is read from
# source under share/luce-base/std with every build, so the archive carries the tree, not a
# prebuilt library.
[ -x "$release/bin/luc" ] || { echo "$product: the archive has no bin/luc" >&2; exit 1; }
[ -d "$release/share/luce-base/std" ] || { echo "$product: the archive has no share/luce-base/std" >&2; exit 1; }
[ "$("$release/bin/luce" --version)" = "luce $version" ] || { echo "$product: the compiler in the archive does not report $version" >&2; exit 1; }

# Replace only now, and put the old tree back if the rename fails.
if [ -e "$install_root" ] || [ -L "$install_root" ]; then
    mv "$install_root" "$backup_dir/current"
fi
if ! mv "$release" "$install_root"; then
    [ ! -e "$backup_dir/current" ] || mv "$backup_dir/current" "$install_root"
    echo "$product: could not replace $install_root" >&2
    exit 1
fi

# The default locations are spelled with $HOME so the files stay right however the home
# directory is spelled in a later shell.
default_layout=0
if [ "$install_root" = "$HOME/.local/$product" ]; then
    spelled_root="\$HOME/.local/$product"
    [ "$luc_home" != "$HOME/.luce" ] || default_layout=1
else
    spelled_root="$install_root"
fi
if [ "$luc_home" = "$HOME/.luce" ]; then
    spelled_home="\$HOME/.luce"
else
    spelled_home="$luc_home"
fi

# env and env.fish: the compiler's commands and the applications luc installs, each
# added once however often the file is sourced, and luc's home when it is not the default.
write_env() {
    {
        printf '%s\n' "# Luce: the compiler's commands, and the applications luc installs."
        printf '%s\n' "case \":\$PATH:\" in *\":$spelled_root/bin:\"*) ;; *) PATH=\"$spelled_root/bin:\$PATH\" ;; esac"
        printf '%s\n' "case \":\$PATH:\" in *\":$spelled_home/bin:\"*) ;; *) PATH=\"$spelled_home/bin:\$PATH\" ;; esac"
        printf '%s\n' "export PATH"
        [ "$luc_home" = "$HOME/.luce" ] || printf '%s\n' "export LUC_HOME=\"$luc_home\""
    } > "$install_root/env"
    {
        printf '%s\n' "# Luce: the compiler's commands, and the applications luc installs."
        printf '%s\n' "fish_add_path --prepend \"$spelled_root/bin\" \"$spelled_home/bin\""
        [ "$luc_home" = "$HOME/.luce" ] || printf '%s\n' "set -gx LUC_HOME \"$luc_home\""
    } > "$install_root/env.fish"
}
write_env

add_to_profile() {
    kind=posix
    if [ -n "$profile_override" ]; then
        profile=$profile_override
    else
        shell_name=${SHELL:-/bin/sh}
        shell_name=${shell_name##*/}
        case "$shell_name" in
            zsh) profile="${ZDOTDIR:-$HOME}/.zprofile"; [ "$system" = Darwin ] || profile="${ZDOTDIR:-$HOME}/.zshrc" ;;
            bash) profile="$HOME/.bashrc"; [ "$system" != Darwin ] || profile="$HOME/.bash_profile" ;;
            fish) profile="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"; kind=fish ;;
            *) profile="$HOME/.profile" ;;
        esac
    fi
    mkdir -p "$(dirname "$profile")"
    if [ "$kind" = fish ]; then
        env_file="$spelled_root/env.fish"
        line="source \"$env_file\""
    else
        env_file="$spelled_root/env"
        line=". \"$env_file\""
    fi
    if grep -Fq "$env_file" "$profile" 2> /dev/null; then
        echo "==> $profile already sets up Luce"
    elif printf '\n# Luce\n%s\n' "$line" >> "$profile"; then
        echo "==> $profile now sets up Luce in every new shell"
    else
        echo "$product: installed, but could not update $profile; add $install_root/bin and $luc_home/bin to PATH" >&2
    fi
}
if [ "${LUCE_INSTALL_NO_PATH:-0}" = 1 ]; then
    :
elif [ "$default_layout" = 1 ] || [ -n "$profile_override" ]; then
    add_to_profile
else
    echo "==> startup files left alone for an install outside ~/.local/$product with ~/.luce"
fi

echo "==> $product $version installed at $install_root"
case "${SHELL:-}" in
    */fish) activate="source \"$install_root/env.fish\"" ;;
    *) activate=". \"$install_root/env\"" ;;
esac
case ":$PATH:" in
    *":$install_root/bin:"*) ;;
    *) echo "    to use it in this terminal now, run:"
       echo "        $activate" ;;
esac
echo "    luce --version"
echo "    luc --version   # the project tool, installed with it"

#!/bin/sh
# tools/install.sh installs where it is told and edits a startup file only for its default
# layout: a stub release archive (its tools only report the version) served from a file://
# URL is installed into a scratch HOME three ways, the default place, another tree (as
# `luc update` asks for the tree it runs from), and the default tree with LUC_HOME elsewhere,
# and each env file is sourced to see what it puts on PATH.
set -eu
cd "$(dirname "$0")/.."
case "$(uname -s)" in
    Darwin) host=arm64-macos; [ "$(uname -m)" = arm64 ] || { echo "skip install layout: not Apple Silicon"; exit 0; } ;;
    Linux) case "$(uname -m)" in x86_64|amd64) host=x86_64-linux ;; *) host=arm64-linux ;; esac ;;
    *) echo "skip install layout: the shell installer is for macOS and Linux"; exit 0 ;;
esac
work=$(mktemp -d)
trap 'rm -rf "$work"' 0 HUP INT TERM
work=$(cd "$work" && pwd -P)
version=9.9.9
tree="$work/archive/luce-$version"
mkdir -p "$tree/bin" "$tree/share/luce" "$tree/share/luce-base/std"
echo "$version" > "$tree/share/luce/VERSION"
for tool in luce luce-base luc; do
    printf '#!/bin/sh\necho "%s %s"\n' "$tool" "$version" > "$tree/bin/$tool"
    chmod +x "$tree/bin/$tool"
done
archive="$work/serve/luce-$version-$host.tar.gz"
mkdir -p "$work/serve"
(cd "$work/archive" && tar -czf "$archive" "luce-$version")
if command -v sha256sum > /dev/null 2>&1; then
    sha256sum "$archive" | awk '{ print $1 }' > "$archive.sha256"
else
    shasum -a 256 "$archive" | awk '{ print $1 }' > "$archive.sha256"
fi

# install HOME [VAR=VALUE...]: the installer run with a scratch HOME and zsh as the shell
install() {
    home=$1
    shift
    mkdir -p "$home"
    env -i PATH="$PATH" HOME="$home" SHELL=/bin/zsh LUCE_INSTALL_VERSION=$version \
        LUCE_INSTALL_URL="file://$work/serve" "$@" sh tools/install.sh > "$home.log" 2>&1 \
        || { cat "$home.log"; echo "FAIL install layout: the installer failed"; exit 1; }
}
profile_of() {
    [ "$(uname -s)" = Darwin ] && echo "$1/.zprofile" || echo "$1/.zshrc"
}
path_after() {
    env -i PATH=/usr/bin:/bin HOME="$1" sh -c ". '$2' && printf '%s|%s' \"\$PATH\" \"\${LUC_HOME:-}\""
}

# the default layout: ~/.local/luce and ~/.luce, sourced from the login shell's profile
home="$work/default"
install "$home"
grep -Fq '. "$HOME/.local/luce/env"' "$(profile_of "$home")" || { echo "FAIL install layout: the default install did not set up the profile"; exit 1; }
[ "$(path_after "$home" "$home/.local/luce/env")" = "$home/.luce/bin:$home/.local/luce/bin:/usr/bin:/bin|" ] || { echo "FAIL install layout: default env"; exit 1; }

# another tree, as `luc update` names the one it runs from: no startup file is touched
home="$work/elsewhere"
install "$home" LUCE_INSTALL_DIR="$work/elsewhere-tree"
[ -x "$work/elsewhere-tree/bin/luc" ] || { echo "FAIL install layout: not installed into LUCE_INSTALL_DIR"; exit 1; }
[ ! -e "$home/.local/luce" ] || { echo "FAIL install layout: installed into the default place too"; exit 1; }
[ -z "$(ls -A "$home")" ] || { echo "FAIL install layout: the home was written: $(ls -A "$home")"; exit 1; }
[ "$(path_after "$home" "$work/elsewhere-tree/env")" = "$home/.luce/bin:$work/elsewhere-tree/bin:/usr/bin:/bin|" ] || { echo "FAIL install layout: elsewhere env"; exit 1; }

# the default tree with luc's home elsewhere: env keeps LUC_HOME, the profile stays as it is
home="$work/scratch-home"
install "$home" LUC_HOME="$work/luc-home"
[ ! -e "$(profile_of "$home")" ] || { echo "FAIL install layout: a LUC_HOME install edited the profile"; exit 1; }
[ "$(path_after "$home" "$home/.local/luce/env")" = "$work/luc-home/bin:$home/.local/luce/bin:/usr/bin:/bin|$work/luc-home" ] || { echo "FAIL install layout: LUC_HOME env"; exit 1; }
echo "ok install layout: the default place sets up the profile; another tree or LUC_HOME leaves it alone, and env names both"

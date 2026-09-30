#!/usr/bin/env python3
"""Refuse a release whose pinned library packages are older than their newest registry
release. Every package luce's bootstrap/PACKAGES names, and every package luc's bootstrap pins
(when a luce-luc checkout is given), must be the commit of the newest `v<version>` tag on
pkg.luciaos.com: what an installed package resolves. Luce 0.8.22 pinned luce-std 0.1.1 while
packages needed 0.1.4, so anything building with luce's pins failed.

Usage: tools/check_pins.py [LUC_CHECKOUT]
Exits 1, naming each old pin, when any is behind; 0 when all are current."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "https://pkg.luciaos.com/git/dymokomi/"
# luc's bootstrap files and the packages they pin
LUC_PINS = {"STD": "luce-std", "PKG": "luce-pkg", "CRYPTO": "luce-crypto", "GIT": "luce-git",
            "HTTP_CLIENT": "luce-http-client", "TLS": "luce-tls", "COMPRESS": "luce-compress",
            "PRISM": "luce-prism"}


def newest(repo):
    """The newest release of `repo` on the registry: (version, commit)."""
    text = subprocess.run(["git", "ls-remote", "--tags", REGISTRY + repo], capture_output=True,
                          text=True, timeout=120, check=True).stdout
    tags = {}
    for line in text.splitlines():
        commit, ref = line.split("\t")
        match = re.fullmatch(r"refs/tags/v(\d+)\.(\d+)\.(\d+)(\^\{\})?", ref)
        if match:
            version = tuple(int(part) for part in match.group(1, 2, 3))
            # an annotated tag's `^{}` line names the commit; a light tag's line is the commit
            if match.group(4) or version not in tags:
                tags[version] = commit
    if not tags:
        raise SystemExit(f"check_pins: {repo} has no release on the registry")
    version = max(tags)
    return ".".join(map(str, version)), tags[version]


def main():
    pins = []
    for line in (ROOT / "bootstrap/PACKAGES").read_text().splitlines():
        if line.strip():
            name, commit = line.split()
            pins.append(("luce/PACKAGES", name, commit))
    if len(sys.argv) > 1:
        luc = Path(sys.argv[1]) / "bootstrap"
        for file, repo in LUC_PINS.items():
            if (luc / file).exists():
                pins.append((f"luc/{file}", repo, (luc / file).read_text().strip()))
        if (luc / "PACKAGES").exists():
            for line in (luc / "PACKAGES").read_text().splitlines():
                if line.strip():
                    name, commit = line.split()
                    pins.append(("luc/PACKAGES", name, commit))
    old = 0
    for where, repo, commit in pins:
        version, released = newest(repo)
        if commit == released:
            print(f"ok   {where} {repo} {version}")
        else:
            print(f"OLD  {where} {repo} pins {commit[:7]}; the newest release, {version}, is {released[:7]}")
            old += 1
    return 1 if old else 0


if __name__ == "__main__":
    sys.exit(main())

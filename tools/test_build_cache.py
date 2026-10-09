#!/usr/bin/env python3
"""Luce builds share luce-base's build cache across builds, though each runs in a new workspace.

With neither `--cache-dir` nor `LUCE_CACHE`, the cache is the user's (`~/.luce/cache`, or
`%LOCALAPPDATA%\\luce\\cache` on Windows):

  - the first build keeps one build there (an object, or a list of pieces);
  - the same program built again, from another directory, to another output, keeps
    nothing new (its key is the same) and still runs;
  - a comment keeps nothing new (Luce emits the same program); an edit keeps a second;
  - `LUCE_CACHE=none` keeps nothing, and neither the workspace nor the output directory
    holds a cache;
  - past `LUCE_CACHE_LIMIT` the files written longest ago go, whatever their kind.

Usage: tools/test_build_cache.py   (after build.sh or tools/build_windows.py)
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXE = ".exe" if os.name == "nt" else ""
LUCE = ROOT / "build" / ("luce" + EXE)

with tempfile.TemporaryDirectory(prefix="luce-build-cache-") as tmp:
    work = Path(tmp)
    home = work / "home"
    home.mkdir()
    cache = home / ("luce/cache" if os.name == "nt" else ".luce/cache")
    environment = {k: v for k, v in os.environ.items() if k != "LUCE_CACHE"}
    environment["LOCALAPPDATA" if os.name == "nt" else "HOME"] = str(home)
    source = work / "project" / "main.luc"
    source.parent.mkdir()
    source.write_text('pub func main(arguments: list[str]) -> int!:\n    print("cached")\n    return 0\n')

    expected = "cached\n"

    def build(output, cwd, extra=None):
        env = dict(environment, **(extra or {}))
        result = subprocess.run([str(LUCE), "build", str(source), "-o", str(output)], cwd=cwd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            sys.exit(f"FAIL: the build failed:\n{result.stderr}")
        ran = subprocess.run([str(output)], capture_output=True, text=True)
        if ran.stdout != expected:
            sys.exit(f"FAIL: the program printed {ran.stdout!r}")

    def kept():
        return sorted(p.name for p in cache.iterdir() if p.is_file()) if cache.is_dir() else []

    # a native build is kept whole (`-n.o`) or as pieces under a list (`-n.m`)
    def builds():
        return [n for n in kept() if n.endswith("-n.o") or n.endswith("-n.m")]

    elsewhere = work / "elsewhere"
    elsewhere.mkdir()
    build(work / "one" / ("program" + EXE), work)
    first = kept()
    if len(builds()) != 1:
        sys.exit(f"FAIL: the first build kept {first} in {cache}")
    build(work / "two" / ("program" + EXE), elsewhere)
    if kept() != first:
        sys.exit(f"FAIL: the same program built again kept something new: {kept()}")
    # by name: Windows spells the same path with either separator
    if sorted(p.name for p in (work / "two").iterdir()) != ["program" + EXE]:
        sys.exit(f"FAIL: the output directory holds more than the program: {list((work / 'two').iterdir())}")
    # a comment changes nothing Luce emits, so it keeps nothing new; a changed program does
    source.write_text(source.read_text() + "# a comment\n")
    build(work / "three" / ("program" + EXE), work)
    if kept() != first:
        sys.exit(f"FAIL: a comment kept something new: {kept()}")
    source.write_text(source.read_text().replace('"cached"', '"edited"'))
    expected = "edited\n"
    build(work / "five" / ("program" + EXE), work)
    if len(builds()) != 2:
        sys.exit(f"FAIL: an edit did not keep a second build: {kept()}")
    edited = kept()
    build(work / "four" / ("program" + EXE), work, {"LUCE_CACHE": "none"})
    if kept() != edited:
        sys.exit(f"FAIL: LUCE_CACHE=none kept something: {kept()}")
    # past LUCE_CACHE_LIMIT megabytes the files written longest ago go, objects or not, the
    # newest stay, and directories are left
    for n, year in (("a-n.o", 2020), ("b-f.pack", 2021), ("c-n.o", 2022)):
        old = cache / n
        old.write_bytes(bytes(1048576))
        stamp = __import__("datetime").datetime(year, 1, 1).timestamp()
        os.utime(old, (stamp, stamp))
    (cache / "staging").mkdir()
    kept_before = kept()
    build(work / "six" / ("program" + EXE), work, {"LUCE_CACHE_LIMIT": "2"})
    left = kept()
    if "a-n.o" in left or "b-f.pack" in left or not (cache / "staging").is_dir():
        sys.exit(f"FAIL: trimming kept the wrong files: {left}")
    if not set(kept_before) - {"a-n.o", "b-f.pack", "c-n.o"} <= set(left) | {"c-n.o"}:
        sys.exit(f"FAIL: trimming removed this build's objects: {left}")
print("PASS Luce builds reuse the user's build cache across workspaces, keep a new build for an edit, none with LUCE_CACHE=none, and stay within LUCE_CACHE_LIMIT")

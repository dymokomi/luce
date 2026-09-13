#!/usr/bin/env python3
"""Unicode package roots, both path separators, CRLF and compiler scratch cleanup."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, default=ROOT / 'build/luce.exe')
parser.add_argument('--base', type=Path, default=ROOT.parent / 'luce-base/build/luce-base.exe')
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='luce-パス-😀-') as directory:
    root = Path(directory)
    scratch = root / 'temporary files'
    scratch.mkdir()
    source = root / 'src'
    source.mkdir()
    (root / 'luce.toml').write_text('[package]\nname = "unicode"\nsource = "src"\n', encoding='utf-8')
    (source / 'helper.luc').write_text('pub func message() -> str:\n    return "日本語 😀"\n', encoding='utf-8', newline='\r\n')
    entry = source / 'main.luc'
    entry.write_text('import helper\npub func main(arguments: list[str]) -> int!:\n'
                     '    print(helper.message())\n    return 0\n', encoding='utf-8', newline='\r\n')
    environment = dict(os.environ, LUCE_BASE=str(args.base.resolve()), TEMP=str(scratch), TMP=str(scratch))
    for spelling in (str(entry), entry.as_posix()):
        for flags in (['--native'], ['--backend=c']):
            binary = root / '結果.exe'
            subprocess.run([args.compiler.resolve(), 'build', spelling, *flags, '-o', binary],
                           env=environment, check=True, timeout=180)
            result = subprocess.run([binary], capture_output=True, check=True, timeout=15)
            assert result.stdout == '日本語 😀\n'.encode('utf-8') and not result.stderr, result
            assert not list(scratch.iterdir()), list(scratch.iterdir())
print('PASS Unicode package and TEMP paths, both separators, CRLF and clean compilation; native and C')

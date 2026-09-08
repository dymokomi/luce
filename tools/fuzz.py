#!/usr/bin/env python3
"""Fuzz the compiler: mutated programs must be accepted or rejected with a positioned
diagnostic; generated programs must agree across the interpreter and the emitted Base. The
generator arrives with slice 4; until then this is the mutate mode over the conformance corpus.

Usage: tools/fuzz.py [--seed N] [--mutations N] [--minutes M] [--gate]
"""
import os, random, re, subprocess, sys, time, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
os.chdir(root)
compiler = root / "build" / "luce"
out = root / "build" / "fuzz"
out.mkdir(parents=True, exist_ok=True)
position = re.compile(r"[^ :]+\.luc:\d+:\d+: ")
token = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|\d+|\S", re.S)


def run(args, timeout):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, b"", b"hang"


class Findings:
    def __init__(self):
        self.count = 0

    def report(self, kind, text, detail):
        self.count += 1
        path = out / f"finding_{self.count:03d}_{kind}.luc"
        path.write_bytes(text)
        print(f"FINDING {kind}: {detail}\n  input: {path}", flush=True)


def corpus():
    files = sorted(root.glob("tests/conformance/*/*.luc")) + sorted(root.glob("tests/conformance/*/*/*.luc"))
    return [f for f in files if f.stat().st_size < 60000]


def mutate(text, rng):
    for _ in range(rng.randint(1, 3)):
        if len(text) == 0:
            text = b"pub func main(arguments: list[str]) -> int!:\n    return 0\n"
        i = rng.randrange(len(text))
        k = rng.randrange(10)
        if k == 0:
            text = text[:i] + bytes([rng.randrange(256)]) + text[i + 1:]
        elif k == 1:
            text = text[:i] + text[min(len(text), i + rng.randint(1, 40)):]
        elif k == 2:
            j = min(len(text), i + rng.randint(1, 40)); text = text[:j] + text[i:j] + text[j:]
        elif k == 3:
            text = text[:i]
        elif k == 4:
            toks = [m.span() for m in token.finditer(text)]
            if len(toks) > 2:
                a, b = sorted(rng.sample(range(len(toks)), 2))
                (a0, a1), (b0, b1) = toks[a], toks[b]
                text = text[:a0] + text[b0:b1] + text[a1:b0] + text[a0:a1] + text[b1:]
        elif k == 5:
            depth = rng.choice([64, 300, 2000, 20000])
            o, c = rng.choice([(b"(", b")"), (b"[", b"]"), (b"-", b""), (b"not ", b"")])
            text = text[:i] + o * depth + b"1" + c * depth + text[i:]
        elif k == 6:
            text = text[:i] + rng.choice([b"a" * 5000, b"9" * 5000, b'"' + b"x" * 8000 + b'"']) + text[i:]
        elif k == 7:
            text = text[:i] + rng.choice([b"\xff\xfe", b"\xc0\x80", b"\xe2\x80\xae", b"\x00"]) + text[i:]
        elif k == 8:
            lines = text.split(b"\n"); j = rng.randrange(len(lines))
            lines[j] = rng.choice([b"    " * 40, b"\t", b" ", b""]) + lines[j].lstrip(); text = b"\n".join(lines)
        else:
            word = rng.choice([b"func", b"class", b"return", b"if", b"else", b"match", b"with", b"try", b"catch", b"import", b"from", b"pub", b"self", b"none", b"=>", b"..<", b"[", b"]", b":"])
            text = text[:i] + b" " + word + b" " + text[i:]
    return text


def check_one(text, timeout, findings, label):
    path = out / "current.luc"
    path.write_bytes(text)
    status, so, se = run([str(compiler), "check", str(path)], timeout)
    message = (so + se).decode("utf-8", "replace")
    if status == -1:
        findings.report("hang", text, f"{label}: the checker did not finish in {timeout}s")
    elif status < 0 or status >= 128:
        findings.report("crash", text, f"{label}: signal {status} {message[:200]!r}")
    elif status == 1 and not position.search(message):
        findings.report("bare", text, f"{label}: a rejection without a position: {message[:200]!r}")
    elif status not in (0, 1):
        findings.report("status", text, f"{label}: exit status {status}: {message[:200]!r}")


def main():
    args = sys.argv[1:]
    seed, mutations, minutes = 1, 300, 0
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--seed": seed = int(args[i + 1]); i += 2
        elif a == "--mutations": mutations = int(args[i + 1]); i += 2
        elif a == "--minutes": minutes = float(args[i + 1]); i += 2
        elif a == "--gate": seed, mutations = 7, 60; i += 1
        else:
            print(__doc__); return 2
    rng = random.Random(seed)
    findings = Findings()
    files = corpus()
    if not files:
        print("fuzz: no corpus yet, 0 findings")
        return 0
    deadline = time.time() + minutes * 60 if minutes > 0 else None
    done = 0
    while True:
        for _ in range(mutations):
            f = rng.choice(files)
            check_one(mutate(f.read_bytes(), rng), 20, findings, f"mutation {done + 1} of {f.name} (seed {seed})")
            done += 1
            if deadline and time.time() > deadline:
                break
        if not deadline or time.time() > deadline:
            break
        print(f"fuzz: {done} mutations, {findings.count} findings, {int(deadline - time.time()) // 60} min left", flush=True)
    for name in ("current.luc",):
        p = out / name
        if p.exists():
            p.unlink()
    print(f"fuzz: {done} mutations, {findings.count} findings (seed {seed})", flush=True)
    return min(findings.count, 100)


if __name__ == "__main__":
    sys.exit(main())

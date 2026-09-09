#!/usr/bin/env python3
"""Fuzz the compiler. Two modes, both deterministic for a seed:

  mutate    every program of the conformance corpus is mutated at random and given to
            `luce check`; the only acceptable outcomes are an acceptance and a rejection
            with a positioned diagnostic. A signal, a hang, or a bare message is a finding.

  generate  well-typed programs over the value language (checked `int` arithmetic on
            masked operands, `float`, text, `bool`, structs, enums under `match`,
            optionals, results with `try` and `catch`, loops, functions) print a checksum
            and run four ways: the interpreter, and the emitted Base through luce-base's
            C, C `-O2` and native generators. The outputs must agree.

Usage: tools/fuzz.py [--seed N] [--mutations N] [--programs N] [--minutes M] [--gate]
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


# ---- generation ----------------------------------------------------------------------

class Gen:
    """A well-typed Luce program that prints a checksum. Nothing it writes traps: checked
    operands are masked, divisors are never zero, every index is in range."""

    def __init__(self, rng):
        self.rng = rng
        self.funcs = []
        self.loops = 0
        self.locals = []
        # inside a helper function, where only its parameters and literals are in scope
        self.in_helper = False

    def leaf(self, ty):
        r = self.rng
        if self.in_helper:
            own = [n for n, t in self.locals if t == ty]
            if own and r.random() < 0.6:
                return r.choice(own)
            if ty == "int": return str(r.randint(-999, 999))
            if ty == "float": return r.choice(["0.5", "2.25", "-1.5", "3.0", "10.0"])
            if ty == "str": return r.choice(['"ab"', '"xyz"', '"hé"', '""'])
            return r.choice(["true", "false"])
        pool = {
            "int": ["a", "b", "c", "p.x", "len(s)", "int(d)", "q.n"],
            "float": ["d", "e", "float(a % 256)", "p.f"],
            "str": ["s", "t", "p.name"],
            "bool": ["flag", "(a > b)"],
        }[ty] + [n for n, t in self.locals if t == ty]
        if r.random() < 0.3:
            if ty == "int": return str(r.randint(-999, 999))
            if ty == "float": return r.choice(["0.5", "2.25", "-1.5", "3.0", "10.0"])
            if ty == "str": return r.choice(['"ab"', '"xyz"', '"hé"', '""'])
            return r.choice(["true", "false"])
        return r.choice(pool)

    def expr(self, depth, ty="int"):
        r = self.rng
        if depth <= 0 or r.random() < 0.3:
            return self.leaf(ty)
        k = r.randrange(10)
        if ty == "int":
            if k < 3:
                return f"(({self.expr(depth - 1)} % 4096) {r.choice(['+', '-', '*'])} ({self.expr(depth - 1)} % 4096))"
            if k == 3:
                return f"(({self.expr(depth - 1)} % 1024) {r.choice(['//', '%'])} (({self.expr(depth - 1)} % 64) + 1))"
            if k == 4:
                return f"(({self.expr(depth - 1)} % 8) ** {r.randint(0, 5)})"
            if k == 5:
                return f"({self.expr(depth - 1)} if {self.expr(depth - 1, 'bool')} else {self.expr(depth - 1)})"
            if k == 6:
                return f"int({self.expr(depth - 1, 'float')} * 0.5)"
            if k == 7:
                return f"({self.expr(depth - 1, 'str')} + {self.expr(depth - 1, 'str')}).length"
            if k == 8 and self.funcs:
                name, n = r.choice(self.funcs)
                return f"{name}({', '.join(self.expr(depth - 1) for _ in range(n))})"
            if self.in_helper:
                return f"({self.expr(depth - 1)} % 4096)"
            return f"(o else {self.expr(depth - 1)})"
        if ty == "float":
            # every form is a contraction of bounded inputs, so a float stays finite and
            # small however many times a loop feeds it back: `int(...)` of it never traps
            if k < 3:
                return f"(({self.expr(depth - 1, 'float')} {r.choice(['+', '-'])} {self.expr(depth - 1, 'float')}) * 0.5)"
            if k < 5:
                return f"({self.expr(depth - 1, 'float')} / {r.choice(['2.0', '4.0', '-8.0'])})"
            if k == 5:
                return f"({self.expr(depth - 1, 'float')} * {r.choice(['0.5', '0.25', '-0.5'])})"
            if k == 6:
                return f"float({self.expr(depth - 1)} % 256)"
            if k == 7:
                return f"({self.expr(depth - 1, 'float')} if {self.expr(depth - 1, 'bool')} else {self.expr(depth - 1, 'float')})"
            return f"(-{self.expr(depth - 1, 'float')})"
        if ty == "str":
            if k < 4:
                return f"({self.expr(depth - 1, 'str')} + {self.expr(depth - 1, 'str')})"
            if k < 6:
                return f"str({self.expr(depth - 1)})"
            if k == 6:
                return f"f\"{{{self.expr(depth - 1)}}}-{{{self.expr(depth - 1, 'str')}}}\""
            if k == 7:
                return f"({self.expr(depth - 1, 'str')} if {self.expr(depth - 1, 'bool')} else {self.expr(depth - 1, 'str')})"
            return f"describe(Shape.circle(radius = {self.expr(depth - 1, 'float')}))"
        if k < 4:
            return f"({self.expr(depth - 1)} {r.choice(['<', '<=', '==', '!=', '>=', '>'])} {self.expr(depth - 1)})"
        if k < 6:
            return f"({self.expr(depth - 1, 'bool')} {r.choice(['and', 'or'])} {self.expr(depth - 1, 'bool')})"
        if k == 6:
            return f"(not {self.expr(depth - 1, 'bool')})"
        if k == 7:
            return f"({self.expr(depth - 1, 'str')} == {self.expr(depth - 1, 'str')})"
        if k == 8 or self.in_helper:
            return f"({self.expr(depth - 1, 'str')} in {self.expr(depth - 1, 'str')})"
        return f"(o == none)"

    def statements(self, depth, indent):
        r = self.rng
        lines = []
        pad = "    " * indent
        saved = list(self.locals)
        for _ in range(r.randint(1, 4)):
            k = r.randrange(14)
            if k < 2:
                lines.append(f"{pad}{r.choice(['a', 'b', 'c'])} = {self.expr(3)}")
            elif k == 2:
                lines.append(f"{pad}{r.choice(['d', 'e'])} = {self.expr(2, 'float')}")
            elif k == 3:
                # `short` keeps a text bounded: `s = s + s` in nested loops grows without limit
                lines.append(f"{pad}{r.choice(['s', 't'])} = short({self.expr(2, 'str')})")
            elif k == 4:
                lines.append(f"{pad}flag = {self.expr(2, 'bool')}")
            elif k == 5:
                lines.append(r.choice([f"{pad}p = Point(x = {self.expr(2)}, f = {self.expr(1, 'float')}, name = {self.expr(1, 'str')})", f"{pad}p.x = {self.expr(2)}", f"{pad}p = p.moved({self.expr(2)})", f"{pad}q = Counter(n = {self.expr(2)})", f"{pad}q.bump({self.expr(1)} % 16)"]))
            elif k == 6:
                lines.append(r.choice([f"{pad}o = {self.expr(2)}", f"{pad}o = none", f"{pad}o = find({self.expr(2)})", f"{pad}a = o else {self.expr(2)}"]))
            elif k == 7 and depth > 0:
                n = self.loops; self.loops += 1
                lines.append(f"{pad}if let v{n} = o:")
                self.locals.append((f"v{n}", "int"))
                lines += self.statements(depth - 1, indent + 1)
                self.locals.pop()
                if r.random() < 0.5:
                    lines.append(f"{pad}else:")
                    lines += self.statements(depth - 1, indent + 1)
            elif k == 8:
                lines.append(f"{pad}{r.choice(['a', 'b', 'c'])} = risky({self.expr(2)}) catch failure:")
                lines.append(f"{pad}    recover {self.expr(2)} + (1 if failure.code == bad else 0)")
            elif k == 9 and depth > 0:
                # bindings carry the nesting number: a nested arm cannot rebind `radius` (§2.4)
                n = self.loops; self.loops += 1
                lines.append(f"{pad}match shape({self.expr(2)}):")
                lines.append(f"{pad}    .circle(radius{n}):")
                self.locals.append((f"radius{n}", "float"))
                lines += self.statements(depth - 1, indent + 2)
                self.locals.pop()
                lines.append(f"{pad}    .rect(w{n}, h{n}):")
                self.locals += [(f"w{n}", "int"), (f"h{n}", "int")]
                lines += self.statements(depth - 1, indent + 2)
                self.locals.pop(); self.locals.pop()
                lines.append(f"{pad}    .empty:")
                lines += self.statements(depth - 1, indent + 2)
            elif k == 10:
                lines.append(f"{pad}a = match ({self.expr(2)} % 16):")
                lines.append(f"{pad}    0 => {self.expr(2)}")
                lines.append(f"{pad}    1..<5 => {self.expr(2)}")
                lines.append(f"{pad}    5..=9 => {self.expr(2)}")
                lines.append(f"{pad}    _ if {self.expr(1, 'bool')} => {self.expr(2)}")
                lines.append(f"{pad}    _ => {self.expr(2)}")
            elif k == 11 and depth > 0:
                n = self.loops; self.loops += 1
                lines.append(f"{pad}for i{n} in 0..<{r.randint(1, 6)}:")
                self.locals.append((f"i{n}", "int"))
                lines += self.statements(depth - 1, indent + 1)
                self.locals.pop()
            elif k == 12 and depth > 0:
                lines.append(f"{pad}if {self.expr(2, 'bool')}:")
                lines += self.statements(depth - 1, indent + 1)
                if r.random() < 0.5:
                    lines.append(f"{pad}else:")
                    lines += self.statements(depth - 1, indent + 1)
            elif k == 13 and depth > 0:
                n = self.loops; self.loops += 1
                lines.append(f"{pad}var k{n} = 0")
                lines.append(f"{pad}while k{n} < {r.randint(1, 8)}:")
                self.locals.append((f"k{n}", "int"))
                lines += self.statements(depth - 1, indent + 1)
                self.locals.pop()
                lines.append(f"{pad}    k{n} += 1")
            else:
                lines.append(f"{pad}c = {self.expr(2)}")
            lines.append(f"{pad}sum = (sum * 31 + mix()) % 1000000007")
        self.locals = saved
        return lines

    def program(self):
        r = self.rng
        text = ["## generated by tools/fuzz.py", "let bad = ErrorCode.package(1)", "",
                "struct Point:", "    var x: int", "    var f: float", "    var name: str", "",
                "    func moved(self, dx: int) -> Point:", "        return Point(x = self.x + (dx % 4096), f = self.f, name = self.name)", "",
                "struct Counter:", "    var n: int", "", "    func bump(self, by: int):", "        self.n = (self.n % 4096) + by", "",
                "enum Shape:", "    circle(radius: float)", "    rect(w: int, h: int)", "    empty", "",
                "func shape(x: int) -> Shape:", "    match x % 4:", "        0: return Shape.empty", "        1: return Shape.circle(radius = float(x % 256))", "        _: return Shape.rect(w = x % 256, h = (x % 16) + 1)", "",
                "func short(text: str) -> str:", "    return text if text.length < 64 else \"long\"", "",
                "func describe(s: Shape) -> str:", "    match s:", "        .circle(radius): return f\"c{radius}\"", "        .rect(w, h): return f\"r{w}x{h}\"", "        .empty: return \"e\"", "",
                "func len(text: str) -> int:", "    return text.length", "",
                "func find(x: int) -> int?:", "    if (x % 4) == 0:", "        return none", "    return x % 1024", "",
                "func risky(x: int) -> int!:", "    if (x % 8) == 3:", "        error(bad, \"three\")", "    return (x % 4096) + 11", "",
                "var_block"]
        return "\n".join(text)


def generate(rng):
    """The program as text: the state lives in locals of `main`, a function per helper."""
    g = Gen(rng)
    header = g.program().split("\n")
    body = []
    for k in range(rng.randint(0, 3)):
        n = rng.randint(1, 3)
        params = ", ".join(f"n{i}: int" for i in range(n))
        g.locals = [(f"n{i}", "int") for i in range(n)]
        g.in_helper = True
        e = g.expr(3)
        g.in_helper = False
        g.locals = []
        body.append(f"func g{k}({params}) -> int:")
        body.append(f"    return {e}")
        body.append("")
        g.funcs.append((f"g{k}", n))
    body.append("pub func main(arguments: list[str]) -> int!:")
    body.append(f"    var a = {rng.randint(-50, 50)}")
    body.append(f"    var b = {rng.randint(-50, 50)}")
    body.append(f"    var c = {rng.randint(-50, 50)}")
    body.append(f"    var d = {rng.choice(['1.5', '-2.25', '0.0', '100.0'])}")
    body.append(f"    var e = {rng.choice(['0.5', '3.0', '-7.75'])}")
    body.append('    var s = "abc"')
    body.append('    var t = "de"')
    body.append("    var flag = false")
    body.append("    var o: int? = none")
    body.append('    var p = Point(x = 1, f = 0.5, name = "pt")')
    body.append("    var q = Counter(n = 3)")
    body.append("    var sum = 0")
    body.append("    func_mix")
    lines = g.statements(3, 1)
    body += lines
    body.append('    print(f"{sum} {a} {b} {c} {d} {e} {s} {t} {flag} {o else -1} {p} {q.n}")')
    body.append("    return 0")
    text = "\n".join(header + body) + "\n"
    # `mix` reads the locals: written as a nested reading of the same names through a
    # helper that takes them all
    mix = "func mix_of(a: int, b: int, c: int, d: float, e: float, s: str, t: str, flag: bool, o: int?, p: Point, q: Counter) -> int:\n    return (a + b + c + int(d * 4.0) + int(e) + s.length + t.length + (1 if flag else 0) + (o else -1) + p.x + q.n) % 1000000007\n"
    text = text.replace("var_block\n", mix).replace("    func_mix\n", "")
    text = text.replace("mix()", "mix_of(a, b, c, d, e, s, t, flag, o, p, q)")
    return text


def differential(text, timeout, findings, label):
    path = out / "generated.luc"
    path.write_text(text)
    exe = out / "generated"
    outputs = {}
    status, so, se = run([str(compiler), "run", str(path)], timeout)
    if status != 0:
        findings.report("run-interp", text.encode(), f"{label}: the interpreter stopped with {status}: {(so + se).decode('utf-8', 'replace')[:300]!r}")
        return
    outputs["interp"] = so
    for name, flags in (("c", []), ("release", ["--release"]), ("native", ["--native"])):
        status, so, se = run([str(compiler), "build", str(path), "-o", str(exe), *flags], timeout * 4)
        if status != 0:
            findings.report("build-" + name, text.encode(), f"{label}: the build ({name}) failed: {(so + se).decode('utf-8', 'replace')[:300]!r}")
            return
        status, so, se = run([str(exe)], timeout)
        if status != 0:
            findings.report("run-" + name, text.encode(), f"{label}: the program ({name}) stopped with {status}: {se.decode('utf-8', 'replace')[:200]!r}")
            return
        outputs[name] = so
    if len(set(outputs.values())) > 1:
        detail = "; ".join(f"{k}: {v.decode('utf-8', 'replace').strip()}" for k, v in outputs.items())
        findings.report("disagree", text.encode(), f"{label}: the executions disagree: {detail}")


def main():
    args = sys.argv[1:]
    seed, mutations, programs, minutes = 1, 300, 40, 0
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--seed": seed = int(args[i + 1]); i += 2
        elif a == "--mutations": mutations = int(args[i + 1]); i += 2
        elif a == "--programs": programs = int(args[i + 1]); i += 2
        elif a == "--minutes": minutes = float(args[i + 1]); i += 2
        elif a == "--gate": seed, mutations, programs = 7, 60, 6; i += 1
        else:
            print(__doc__); return 2
    os.environ.setdefault("LUCE_BASE", str(root / "build" / "luce-base" / "build" / "luce-base"))
    rng = random.Random(seed)
    findings = Findings()
    files = corpus()
    deadline = time.time() + minutes * 60 if minutes > 0 else None
    done_m = done_p = 0
    round_ = 0
    while True:
        round_ += 1
        if deadline and round_ > 1:
            print(f"fuzz: round {round_}, {done_m} mutations, {done_p} programs, {findings.count} findings, {int(deadline - time.time()) // 60} min left", flush=True)
        for _ in range(mutations if files else 0):
            f = rng.choice(files)
            check_one(mutate(f.read_bytes(), rng), 20, findings, f"mutation {done_m + 1} of {f.name} (seed {seed})")
            done_m += 1
            if deadline and time.time() > deadline:
                break
        for _ in range(programs):
            differential(generate(random.Random(rng.randrange(1 << 30))), 20, findings, f"program {done_p + 1} (seed {seed})")
            done_p += 1
            if deadline and time.time() > deadline:
                break
        if not deadline or time.time() > deadline:
            break
    for name in ("current.luc", "generated.luc", "generated", "generated.base"):
        p = out / name
        if p.is_dir():
            import shutil; shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    print(f"fuzz: {done_m} mutations, {done_p} generated programs, {findings.count} findings (seed {seed})", flush=True)
    return min(findings.count, 100)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Rewrite Luce sources for the lean core names of Luce 0.10 (docs/luce.md §2.4, §6.8).

The core names `abs`, `min`, `max`, `round`, `ord`, `chr`, `input`, `hash` and `discard` and
the keyword `try` left the language. A source is rewritten mechanically, in code only (never
in a string's text or a comment):

    discard(x)        _ = x                     (a statement; `catch` after it stays)
    try f(x)          f(x)                      (failures propagate by themselves)
    hash(x)           x.hash()                  ((x).hash() when x is not one operand)
    abs(x)            math.abs(x)               and `import math`; likewise min, max, round
    ord(s)            text.code_of(s)           and `import text`
    chr(n)            text.from_code(n)         and `import text`
    input(p)          console.read_line(p)      and `import console`
    func hashed(self) func hash(self)           (Hashable's requirement), and `.hashed()`

A module that already binds `math`, `text` or `console` to something else (`from luce_std
import math`, a local named `text`) imports the functions by name instead, `from math import
abs`, and keeps the bare call, `abs(x)` (`code_of(s)` for `ord(s)`). The import goes after
the module's last import, or before its first declaration.

In Markdown, the ```luce blocks are rewritten; a block that declares `func main(` gets its
imports too. Whatever cannot be rewritten mechanically (a `discard(...)` inside a larger
expression, `ord(text = ...)` named by its old parameter) is reported with its line, and
the file is left for a person to finish there.

Usage: tools/migrate_lean_names.py [--check] PATH...
Each PATH is a `.luc` or `.md` file or a directory searched for both. `--check` changes
nothing and exits 1 when a file would change. Running it again changes nothing more.
"""
from pathlib import Path
import re
import sys

# the old call, the module that has it now, and its name there
MOVED = {
    "abs": ("math", "abs"), "min": ("math", "min"), "max": ("math", "max"),
    "round": ("math", "round"), "ord": ("text", "code_of"), "chr": ("text", "from_code"),
    "input": ("console", "read_line"),
}
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FENCE = re.compile(r"^```(\w*)\s*$")
IMPORT = re.compile(r"^(import|from)\s")
# what opens a suite on the line it is on: a compound statement, a handler, or a match arm
SUITE_HEAD = re.compile(r"^((pub\s+)?(for|if|elif|else|while|with|func|test)\b.*|.*\bcatch(\s+\w+)?|(\.?\w+(\(.*\))?|_|\"[^\"]*\"|-?\d+)(\s+if\s.*)?):$")


# mark: Reading code ===========================================================================

def code_mask(src):
    """For each character of `src`, whether it is code: not a comment, not a string's text.
    The fields of a formatted string are code, and their strings are strings."""
    mask = [True] * len(src)
    i = 0
    n = len(src)

    def string(i, formatted):
        """Mark the string starting at its quote `i`; the index after it."""
        triple = src.startswith('"""', i)
        quote = '"""' if triple else '"'
        raw = i > 0 and src[i - 1] in "rR"
        j = i + len(quote)
        while j < n:
            if src.startswith(quote, j):
                for k in range(i, j + len(quote)):
                    mask[k] = False
                return j + len(quote)
            if src[j] == "\\" and not raw:
                j += 2
                continue
            if src[j] == "\n" and not triple:
                break
            if formatted and src[j] == "{":
                if src.startswith("{{", j):
                    j += 2
                    continue
                # a field: code up to its `}`, its own strings plain
                for k in range(i, j + 1):
                    mask[k] = False
                j += 1
                while j < n and src[j] != "}" and src[j] != "\n":
                    if src[j] == '"':
                        j = string(j, False)
                        continue
                    j += 1
                i = j
                continue
            j += 1
        for k in range(i, min(j, n)):
            mask[k] = False
        return j

    while i < n:
        c = src[i]
        if c == "#":
            while i < n and src[i] != "\n":
                mask[i] = False
                i += 1
            continue
        if c == '"':
            prefix = src[max(0, i - 2):i]
            formatted = prefix.endswith("f") or prefix.endswith("F")
            i = string(i, formatted)
            continue
        i += 1
    return mask


def closing(src, mask, open_at):
    """The index of the `)` that closes the `(` at `open_at`, counting code brackets only."""
    depth = 0
    for i in range(open_at, len(src)):
        if not mask[i]:
            continue
        if src[i] in "([{":
            depth += 1
        elif src[i] in ")]}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def calls(src, mask, name):
    """The code positions of `name(` as a call of the bare name: not a member, not declared."""
    for m in re.finditer(r"\b%s\(" % name, src):
        at = m.start()
        if not mask[at]:
            continue
        before = src[:at].rstrip(" ")
        if before.endswith(".") or before.endswith("func"):
            continue
        yield at


def one_operand(text):
    """Whether `text` is one postfix operand, so `.hash()` may follow it bare."""
    text = text.strip()
    if not text or text[0] in "-+" or text.startswith("not "):
        return False
    mask = code_mask(text)
    depth = 0
    for i, c in enumerate(text):
        if not mask[i]:
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and not (c.isalnum() or c in "_.\"'"):
            return False
    return True


# mark: Rewriting ==============================================================================

class Rewrite:
    """One source's text being rewritten, the modules its calls now need, and what could not
    be rewritten."""

    def __init__(self, src, path, first_line=1):
        self.src = src
        self.path = path
        self.first_line = first_line
        self.needs = {}
        self.problems = []

    def line_of(self, at):
        return self.first_line + self.src.count("\n", 0, at)

    def problem(self, at, what):
        self.problems.append(f"{self.path}:{self.line_of(at)}: {what}")

    def run(self):
        # decided before anything is rewritten: whether a module's name is free here
        self.taken = self.bound_names()
        self.drop_try()
        self.discards()
        self.hashes()
        for old in MOVED:
            self.moved(old)
        self.src = re.sub(r"\bfunc hashed\(self\)", "func hash(self)", self.src)
        self.src = re.sub(r"\.hashed\(\)", ".hash()", self.src)
        return self

    def drop_try(self):
        mask = code_mask(self.src)
        out = []
        last = 0
        for m in re.finditer(r"\btry\b( +|(?=\())", self.src):
            at = m.start()
            if not mask[at] or self.src[:at].rstrip(" ").endswith("."):
                continue
            out.append(self.src[last:at])
            last = m.end()
        out.append(self.src[last:])
        self.src = "".join(out)

    def discards(self):
        skip = 0
        while True:
            mask = code_mask(self.src)
            found = [at for at in calls(self.src, mask, "discard") if at >= skip]
            if not found:
                return
            at = found[0]
            open_at = at + len("discard")
            close = closing(self.src, mask, open_at)
            line_start = self.src.rfind("\n", 0, at) + 1
            line_end = self.src.find("\n", close)
            line_end = len(self.src) if line_end < 0 else line_end
            rest = self.src[close + 1:line_end].strip()
            # a statement: on a line of its own or after a suite's `:` on the same line, and
            # followed by nothing, by the brackets of a block lambda around it, or by `catch`
            prefix = self.src[line_start:at].strip()
            statement = prefix == "" or SUITE_HEAD.match(prefix)
            ending = re.match(r"^[)\]}]*\s*(#.*)?$", rest) or rest.startswith("catch")
            if close < 0 or not statement or not ending:
                self.problem(at, "`discard(...)` inside an expression: bind the value, or `_ = ...` on a line of its own")
                skip = at + 1
                continue
            inner = self.src[open_at + 1:close].strip()
            self.src = self.src[:at] + "_ = " + inner + self.src[close + 1:]

    def hashes(self):
        while True:
            mask = code_mask(self.src)
            found = list(calls(self.src, mask, "hash"))
            if not found:
                return
            at = found[0]
            open_at = at + len("hash")
            close = closing(self.src, mask, open_at)
            inner = self.src[open_at + 1:close].strip()
            value = inner if one_operand(inner) else f"({inner})"
            self.src = self.src[:at] + value + ".hash()" + self.src[close + 1:]

    def moved(self, old):
        module, new = MOVED[old]
        if old in self.own_names():
            # the module's own function, or one it imports, by a name the core gave up
            return
        mask = code_mask(self.src)
        positions = list(calls(self.src, mask, old))
        if not positions:
            return
        qualified = module not in self.taken or self.imports_module(module)
        for at in reversed(positions):
            close = closing(self.src, mask, at + len(old))
            args = self.src[at + len(old) + 1:close]
            if old in ("ord", "chr") and re.search(r"\b(text|code)\s*=", args):
                self.problem(at, f"`{old}(...)` names its old parameter: `text.code_of(s = ...)`, `text.from_code(n = ...)`")
            call = f"{module}.{new}" if qualified else new
            self.src = self.src[:at] + call + self.src[at + len(old):]
        self.needs.setdefault(module, set())
        if not qualified:
            self.needs[module].add(new)

    def own_names(self):
        """The functions this module declares, and the names its `from` imports bring in."""
        names = set(re.findall(r"^(?:pub )?func (\w+)", self.src, re.M))
        for m in re.finditer(r"^from \S+ import (.*)$", self.src, re.M):
            for item in m.group(1).split(","):
                names.add(item.split(" as ")[-1].strip())
        return names

    def bound_names(self):
        """Every bare word the code uses, a member's name aside: a module name among them is
        taken by an import, a declaration or a local."""
        mask = code_mask(self.src)
        words = set()
        for m in WORD.finditer(self.src):
            if mask[m.start()] and not self.src[:m.start()].endswith("."):
                words.add(m.group(0))
        return words

    def imports_module(self, module):
        return re.search(r"^import %s\s*$" % module, self.src, re.M) is not None

    def add_imports(self):
        lines = self.src.split("\n")
        wanted = []
        for module in sorted(self.needs):
            names = sorted(self.needs[module])
            if names:
                wanted.append(f"from {module} import {', '.join(names)}")
            elif not self.imports_module(module):
                wanted.append(f"import {module}")
        if not wanted:
            return
        last_import = -1
        first_declaration = len(lines)
        for i, line in enumerate(lines):
            if IMPORT.match(line):
                last_import = i
            elif line and not line.startswith("#") and not line.startswith(" ") and not IMPORT.match(line):
                first_declaration = i
                break
        if last_import >= 0:
            lines[last_import + 1:last_import + 1] = wanted
        else:
            # before the declaration's doc comment, after the module's
            at = first_declaration
            while at > 0 and lines[at - 1].startswith("##"):
                at -= 1
            lines[at:at] = wanted + [""]
        self.src = "\n".join(lines)


# mark: Files ==================================================================================

def migrate_luce(text, path):
    r = Rewrite(text, path).run()
    r.add_imports()
    return r.src, r.problems


def migrate_markdown(text, path):
    lines = text.split("\n")
    out = []
    problems = []
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        out.append(lines[i])
        i += 1
        if not m or m.group(1) != "luce":
            continue
        start = i
        while i < len(lines) and not FENCE.match(lines[i]):
            i += 1
        block = "\n".join(lines[start:i])
        r = Rewrite(block, path, start + 1).run()
        if "func main(" in block:
            r.add_imports()
        elif r.needs:
            needed = ", ".join(sorted(r.needs))
            problems.append(f"{path}:{start + 1}: a fragment now calls into {needed}; its program imports it")
        out.extend(r.src.split("\n"))
        problems.extend(r.problems)
        if i < len(lines):
            out.append(lines[i])
            i += 1
    return "\n".join(out), problems


def sources(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.suffix in (".luc", ".md") and f.is_file() and "/build/" not in f.as_posix() and "/.git/" not in f.as_posix():
                    yield f
        else:
            yield p


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if a != "--check"]
    if not paths:
        print(__doc__)
        return 2
    changed = 0
    problems = []
    for f in sources(paths):
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            # a source that is not UTF-8 is a lexer's test, not a program to migrate
            continue
        migrate = migrate_markdown if f.suffix == ".md" else migrate_luce
        new, found = migrate(text, str(f))
        problems.extend(found)
        if new != text:
            changed += 1
            print(("would change " if check else "changed ") + str(f))
            if not check:
                f.write_text(new)
    for p in problems:
        print("manual: " + p)
    if check and changed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# 9. Projects and packages

## Modules

Each `.luc` file is a *module*, as each `.py` file is in Python. In a project, a module is
named by its path under `src/`, with dots between directories:

```text
proj/
  package.prisma
  src/
    main.luc            the module main
    text/words.luc      the module text.words
```

`src/text/words.luc`:

<!-- file text/words.luc -->
```luce
## Counting words.

## How many times each word appears in `text`.
pub func count(text: str) -> map[str, int]:
    let counts: map[str, int] = {}
    for word in text.split(" "):
        if word != "":
            counts[word] = (counts[word] else 0) + 1
    return counts

test "counts repeated words":
    let counts = count("a b a")
    assert(counts["a"] == 2)
```

`src/main.luc`:

<!-- with text/words.luc -->
```luce
from text.words import count

pub func main(arguments: list[str]) -> int!:
    print(count("the cat and the hat"))
    return 0
```

```output
{the: 2, cat: 1, and: 1, hat: 1}
```

`luc run`, in the project's directory, builds the program and prints the line above.

Imports read as in Python, with two forms:

- `from text.words import count` brings `count` in by name.
- `import text.words` keeps it qualified: `words.count(...)`. `import text.words as w`
  gives the module another name.

Unlike Python:

- **Declarations are private to their module unless marked `pub`.** Python's leading
  underscore is a convention; Luce's `pub` is checked.
- **An import must be used.** An import that nothing uses is an error.
- **Modules cannot import each other in a circle**, even indirectly.
- **There are no wildcard imports** (`from x import *`) and no relative ones (`from . import
  x`).
- **A module runs no code when imported.** A module holds declarations: types, functions,
  tests and constants (`let` at the top level). There are no global variables; state lives in
  objects that `main` creates and passes along.

`##` comments document what follows them, as Python's docstrings do: the first block in the
file documents the module, and one directly above a declaration documents that
declaration. `luce doc` prints them.

## Tests

A `test` block, like the one in `words.luc`, is a test: a named block that runs under
`luc test` and is left out of the program otherwise. Tests sit next to the code they test,
in the same module, so they can use private declarations too.

```sh
luc test
```

```output
ok    counts repeated words
1 passed
```

A test fails when it ends with an error, and the run reports the failure and continues with
the next test. `assert` traps, as everywhere, so a failed `assert` stops the run at that
test. [Testing](../topics/14-testing.md) has the details.

## Dependencies

Packages come from the registry at [pkg.luciaos.com](https://pkg.luciaos.com).
`luc add` adds one to the project:

```sh
luc add dymokomi/luce-std
```

This writes the dependency into `package.prisma`:

```text
def dependency "luce-std" {
    str owner = "dymokomi"
    str version = "^0.5.0"
}
```

and records the exact version, with a checksum of its source, in `luc.lock`, which belongs
in version control. `^0.5.0` accepts any later `0.5.x`. The next build downloads what is
missing; after that, builds work offline.

`luce-std` is the standard library: files, paths, processes, networking, maths and Unicode.
Its modules are imported through the package's name, with `-` written as `_`:

<!-- fragment -->
```luce
from text.words import count
from luce_std import files

pub func main(arguments: list[str]) -> int!:
    files.write_text("note.txt", "the cat and the hat")
    print(count(files.read_text("note.txt")))
    return 0
```

`write_text` and `read_text` can fail, as when the file cannot be created, and in `main` a
failure ends the program with its message, as [Chapter 7](07-absence-and-failure.md)
described. [The standard library](../topics/15-standard-library.md) lists what each module
offers.

A package is imported by its modules, never as a whole: `import luce_std` is an error, since
`luce_std` is a package, not a module.

## Where next

[Chapter 10](10-workers-and-where-next.md) covers running work in parallel and where to go
after the Tour.

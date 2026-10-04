# 1. Hello, Luce

## Install

On macOS or Linux:

```sh
curl -fsSL https://luce.luciaos.com/install.sh | sh && . "$HOME/.local/luce/env"
```

On Windows, in PowerShell:

```sh
irm https://luce.luciaos.com/install.ps1 | iex
```

This puts the compiler, `luce`, and the project tool, `luc`, on your `PATH`. Building a
program uses the C toolchain on your machine to assemble and link, so it needs one: the
Xcode command line tools on macOS (`xcode-select --install`), `gcc` or `clang` on Linux,
and MSYS2's UCRT64 `gcc` on Windows. The installer tells you if it is missing. Check that it
worked:

```sh
luce --version
```

## A first program

Save this as `hello.luc`:

```luce
pub func main(arguments: list[str]) -> int!:
    print("Hello, Luce!")
    return 0
```

```output
Hello, Luce!
```

Run it:

```sh
luce run hello.luc
```

If you know Python, most of this reads as you would expect:

- **Indentation marks blocks**, as in Python: a line ending in `:` opens a block indented
  four spaces.
- **`main` is where the program starts.** Python runs a file from top to bottom; a Luce
  program starts at `main`, which receives the command-line arguments as a list of strings
  and returns the exit status. Its signature is always the one above.
- **Types are written after names**, as in Python's type hints, and a function's result
  type after `->`. Unlike Python's hints, they are checked before the program runs: a
  program with a type error does not start.
- **The `!` in `int!`** means that `main` can fail. [Chapter 7](07-absence-and-failure.md)
  explains it; until then, every `main` in the Tour is written this way.
- **`pub` makes a declaration visible** outside its file. `main` must be `pub`.

## Running and building

`luce run` runs the program straight away, in an interpreter. `luce build` compiles it to a
native executable that runs on its own, without Luce installed:

```sh
luce build hello.luc -o hello
./hello
```

The two print the same thing. Use `luce run` while you work, and `luce build` for a program
to keep or hand to someone else.

## Formatted strings and arguments

`print` takes any number of values and separates them with spaces, as in Python. Formatted
strings are written as in Python too, with an `f` before the quote:

```luce
pub func main(arguments: list[str]) -> int!:
    let language = "Luce"
    let year = 2026
    print(f"Hello from {language}, {year}.")
    print("Arguments:", arguments.length, arguments)
    return 0
```

```output
Hello from Luce, 2026.
Arguments: 0 []
```

The braces hold any expression, with Python's format specification after a colon when you
want one: `{price:.2f}`, `{count:>5}`. One difference from Python: `arguments` holds only
the arguments, without the program's name that Python's `sys.argv[0]` holds. Run it as
`luce run hello.luc one two` and the second line reads `Arguments: 2 [one, two]`.

Notice also that a list prints its strings without quotes: `[one, two]`, where Python would
print `['one', 'two']`.

## A project

A single file is enough for a small program. A program with several files or with
dependencies is a *project*, and `luc` creates one:

```sh
luc new greeter --tool --luce
cd greeter
luc run
```

`luc new` writes three files:

```text
greeter/
  package.prisma      the project's name, version, kind and dependencies
  src/main.luc        the entry point
  .gitignore
```

`package.prisma` describes the project, much as `pyproject.toml` does for Python:

```text
#prisma 4.0
def package "greeter" {
    str owner = "you"
    str version = "0.1.0"
    str kind = "tool"
    str language = "luce"
    str entry = "src/main.luc"
}
```

`luc run` builds the program into `build/greeter` and runs it. The other everyday commands:

| Command | What it does |
| --- | --- |
| `luc build` | build without running; `--release` optimises |
| `luc test` | run the tests |
| `luc check` | type-check without building |
| `luc fmt` | format the sources |

`--tool` makes a command-line program, `--application` a desktop application, and
`--package` a library for other projects to use. [Chapter 9](09-projects-and-packages.md)
covers projects and dependencies.

## The compiler on its own

For single files, `luce` works without `luc`:

| Command | What it does |
| --- | --- |
| `luce run file.luc` | run it in the interpreter |
| `luce build file.luc -o out` | build an executable; `--release` optimises |
| `luce check file.luc` | type-check only |
| `luce test file.luc` | run the file's tests |
| `luce fmt file.luc --write` | format the file in place |

Run `luce` with no arguments for the full list.

## Where next

[Chapter 2](02-values.md) covers the building blocks: bindings, numbers and text.

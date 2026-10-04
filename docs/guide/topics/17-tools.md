# Tools

[Reference: Tooling](../../luce.md#17-tooling).

## The `luce` command

| Command | Does |
| --- | --- |
| `luce run file.luc [arguments]` | run the program in the interpreter |
| `luce build file.luc -o name` | compile to a native executable |
| `luce check file.luc` | check the program and print every problem found, without running it |
| `luce test file.luc` | run the tests ([Testing](14-testing.md)) |
| `luce fmt file.luc` | print the file in the standard layout; `--write` rewrites it, `--check` only reports |
| `luce doc file.luc` | print the public declarations and their documentation, as Markdown |
| `luce explain file.luc:line:column` | say what the name at that position is |
| `luce --version` | the compiler's version |

In a project, `luc build`, `luc run`, `luc test`, `luc check` and `luc fmt` run these on the
whole package ([Modules and packages](13-modules-and-packages.md#building-and-running-a-package)).

### `run` and `build`

The interpreter, `luce run`, starts at once and is the quickest way to try code. `luce build`
translates the program to Luce Base, compiles that to machine code, and links an executable
that runs without Luce installed. Both print the same output and stop with the same traps;
the compiler's test suite holds them to it.

| Option of `build` and `test --build` | Effect |
| --- | --- |
| `--release` | optimise; checks and traps stay |
| `--emit=base` | also keep the generated Base package, as `name.base`, to read |
| `--backend=c` | compile the generated Base through C, for comparison |

Use `luce build` (or `luc run`) when the program imports Base modules, which the interpreter
cannot run, and for anything where speed matters: a built program runs many times faster than
the interpreter.

## Messages

Every problem is reported as `file:line:column: message`, after `luce:`, and makes the
command exit with status 1. Most messages end with the section of the
[Reference](../../luce.md) that states the rule, `(§7.1)`:

```text
luce: shapes.luc:12:5: not every path returns a value (§7.1)
luce: shapes.luc:20:18: expected `int`, got `str`
```

`luce check` reports a problem in each declaration that has one, so one run shows several. A
syntax error stops the run at that point.

## Formatting

`luce fmt` puts a file in the one standard layout, as `black` does for Python: four spaces
per level, one statement per line, one space around binary operators and after commas, none
inside brackets, a blank line between declarations and before each method, at most one blank
line in a row, and comments kept where they were. Formatting a formatted file changes nothing.
`luce fmt --check` exits with status 1 when a file is not formatted, for use in CI. The file
must check: `fmt` does not format a program with errors.

## Documentation

`luce doc file.luc` prints Markdown for the public declarations of the program's modules:
a heading for each module and declaration, the signature, and the `##` comment above it,
with a type's fields, methods and cases listed underneath with their own comments.

## Explanations

`luce explain file.luc:line:column` names what the identifier at that position is, with its
type and where it was declared:

```text
shapes.luc:18:5: `r` is a `let` binding of type `Rect`, declared at shapes.luc:18:5
shapes.luc:19:13: `area` is a method of type `func() -> float`, declared at shapes.luc:10:9
```

## When a program stops

A trap prints its position and message to standard error and exits with status 1:

```text
trap: main.luc:3:5: index out of range
```

The position is the statement that was running, in the innermost function, and is the same in
the interpreter and a built program. A failure that reaches the end of `main` prints
`error: message` and also exits with status 1. Any other status comes from `main`'s
`return`.

A desktop application has no terminal to print a trap to; `luce-std`'s `crash` module writes
crash reports instead ([The standard library](15-standard-library.md#crash)).

## The sandbox

`luce run --sandbox ROOT program.luc -- arguments` runs a program in the interpreter under
confinement, for code you did not write, such as scripts that tools download. The program
must be under `ROOT` and may import only Luce modules there. Before the program is even
read, the operating system is told to deny the process the file system, other processes and
the network; it runs with limits of 30 seconds, 256 MiB of memory and 1 MiB of output, and
anything it prints is its result. `luce --sandbox-policy` prints the policy's name,
`luce-sandbox/1`, which lockfiles record. Where the operating system cannot provide the
confinement, the command refuses to run.

## Environment

| Variable | Meaning |
| --- | --- |
| `LUCE_BASE` | the Base compiler to use, if not the `luce-base` installed beside `luce` |

`luc update` installs the newest `luce`, `luce-base` and `luc` together.

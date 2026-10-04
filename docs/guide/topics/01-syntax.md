# Syntax

[Reference: Source text](../../luce.md#2-source-text).

## Layout

Luce is laid out as Python is: a line ending in `:` opens a block, and the block is the lines
indented under it. The rules are stricter in three ways:

- **Indentation is exactly four spaces** per level. Tabs are an error.
- **A one-line block holds one simple statement**: `if cached: return result` is fine, but
  the statement after the colon cannot itself open a block, and a second statement cannot
  follow it on the same line.
- **There is no `\` line continuation.** Inside brackets, parentheses and braces, newlines
  and indentation do not count, so a long expression is wrapped in parentheses, as PEP 8
  recommends for Python:

```luce
pub func main(arguments: list[str]) -> int!:
    let total = (1 + 2 + 3
        + 4 + 5)
    let names = [
        "Ada",
        "Grace",
    ]
    if total > 10: print(total, names)
    return 0
```

```output
15 [Ada, Grace]
```

There are no semicolons, and one statement goes on each line. `luce fmt` puts a file in the
standard layout ([Tools](17-tools.md#formatting)).

## Comments

`#` starts a comment that runs to the end of the line. A block of `##` lines is
*documentation*: directly above a declaration, it documents the declaration; at the very top
of a file, followed by a blank line, it documents the module. This is what Python's
docstrings do, written before the declaration rather than inside it.

```luce
## Geometry helpers.

## The area of a rectangle, in square units.
func area(width: float, height: float) -> float:
    return width * height   # no checks: negative sizes give negative areas

pub func main(arguments: list[str]) -> int!:
    print(area(2.0, 3.0))
    return 0
```

```output
6.0
```

`luce doc` prints the documentation of a program's public declarations
([Tools](17-tools.md#documentation)). A comment is never an instruction to the compiler:
there are no pragmas or type-checker directives.

## Names

A name starts with a letter or `_`, continues with letters, digits and `_`, and uses ASCII
letters only: `café` is not a valid name, though text and comments may contain any
characters. Case matters. The conventions, which the standard library follows:

| Kind | Convention | Examples |
| --- | --- | --- |
| functions, bindings, fields, enum cases, modules | `snake_case` | `read_text`, `max_width`, `.circle` |
| types and interfaces | `CapitalCase` | `Point`, `HttpClient`, `Display` |
| constants | `snake_case` too | `bad_input`, `default_port` |

There is no `UPPER_CASE` for constants: a top-level `let` is already constant.

### A name is never shadowed

A name is visible from where it is bound to the end of its block, and **no other binding may
take the same name while it is visible**: not a local in an inner block, not a parameter
with the name of a top-level function, not a local with the name of an import. Python
allows all of these and quietly picks the innermost; in Luce they are errors, so a name means
one thing wherever it can be seen.

<!-- exits 1 -->
```luce
pub func main(arguments: list[str]) -> int!:
    let count = 3
    if count > 2:
        let count = 4
    return 0
```

```output
luce: main.luc:4:9: `count` is already in scope; a name is not shadowed (§2.4)
```

Bindings in sibling blocks do not overlap, so each branch of an `if` can bind its own
`count`.

## Reserved words

These words are the language's own and cannot be used as names:

```text
and as break catch class continue elif else enum false for from func if import in
interface is let match none not or pub recover return self spawn struct test true type
var wait while with
```

The names of the built-in types and of the few functions every program has cannot name a
function, a type, a variable or a parameter either: `assert`, `error`, `print`, `trap`,
`int`, `float`, `bool`, `str`, `bytes`, `unit`, `never`, `list`, `map`, `set`, `Error`,
`ErrorCode`, `Weak` and `task`. So `let list = [1]` and a parameter named `str` are errors.
Python lets you reuse `list` and `str` and then breaks in surprising places; Luce refuses.

A field, a method or an enum case may take any of those names, since it is always reached
through its value or its type: `report.print()` and `Token.str` cannot be mistaken for the
built-ins. Everything else, `abs`, `min`, `max`, `round` and `input` among them, lives in a
module ([Types and values](02-types-and-values.md#standard-modules)), so those are ordinary
names: `let max = 3` is fine.

`init`, `deinit`, `close` and `main` are ordinary names that have a meaning in one place each:
a class's constructor and destructor, the method `with` calls, and the program's entry point.

## Statements and values

A statement that computes a value and then ignores it is an error:

<!-- exits 1 -->
```luce
func width() -> int:
    return 3

pub func main(arguments: list[str]) -> int!:
    width()
    return 0
```

```output
luce: main.luc:5:10: this value is unused; bind it, or drop it with `_ = ...` (§5.3)
```

Python silently drops it. Luce asks you to say so, `_ = width()`, because a result that is
computed and dropped is more often a mistake than a choice. `_` is the name Python uses for
a value nobody reads, too; in Luce it is never bound, so it can be assigned any number of
times.

Assignment is a statement, not an expression, and there is no walrus operator (`:=`); the
places where Python uses it are covered by `if let` and `while let` ([Control
flow](06-control-flow.md#if-let-and-while-let)).

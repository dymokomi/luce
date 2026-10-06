# Types and values

[Reference: Types](../../luce.md#4-types), [Bindings](../../luce.md#5-bindings).

## The built-in types

| Type | Values | Python's nearest |
| --- | --- | --- |
| `int` | whole numbers from −2⁶³ to 2⁶³ − 1; overflow traps | `int`, without the unlimited size |
| `float` | 64-bit IEEE floating point | `float` |
| `bool` | `true`, `false` | `bool` |
| `str` | text, UTF-8, unchangeable | `str` |
| `bytes` | a sequence of bytes, unchangeable | `bytes` |
| `unit` | the "nothing" a function without a result returns | `None` as a return value |
| `list[T]`, `map[K, V]`, `set[T]` | collections ([Collections](04-collections.md)) | `list`, `dict`, `set` |
| `(A, B)` | tuples | `tuple` |
| `T?` | a `T` or `none` ([Optionals](10-optionals-and-errors.md#optionals)) | `Optional[T]` |
| `func(A) -> R` | a function value | `Callable[[A], R]` |

`T!`, the result of a function that can fail, is not a type you can store: it appears only
as a function's result ([Errors](10-optionals-and-errors.md#errors)). Your own types are
structs, enums, classes and interfaces ([Structs and enums](08-structs-and-enums.md),
[Classes](09-classes-and-memory.md), [Interfaces](11-interfaces-and-generics.md)).

There are no other number types: no unsigned integers, no 32-bit floats, no decimals. A
program that needs them uses a Base module ([Luce and Base](16-base.md)).

## Values and objects

Every type is one of two kinds, and the kind decides what assignment does:

- **Values** are copied when assigned or passed: numbers, `bool`, `str`, `bytes`, tuples,
  structs, enums, optionals. A copy is independent of the original.
- **Objects** are shared: classes, lists, maps and sets. Assigning one gives another name
  for the same object, and a change through either name shows through both. `is` tells
  whether two names refer to the same object.

Python has only objects, and an immutable object behaves like a value since nothing can
change it. The difference in Luce is structs and enums, which can have `var` fields and
still copy. [Structs and enums](08-structs-and-enums.md#values-copy) shows the consequences.

## Inference

A binding's type comes from its value. The type can be written after the name, and must be
when the value alone does not say:

```luce
type Scores = map[str, list[int]]

pub func main(arguments: list[str]) -> int!:
    let count = 3
    let ratio: float = 0.5
    let names: list[str] = []
    let missing: int? = none
    let scores: Scores = {"ada": [90, 85]}
    print(count, ratio, names, missing, scores)
    return 0
```

```output
3 0.5 [] none {ada: [90, 85]}
```

The type must be written for `[]`, `{}` and `none` on their own, which have no element type
to infer from. Function parameters and results are always written: Luce infers inside a
function, never across a signature.

`type Name = ...` declares an *alias*, another name for the same type, as Python's
`TypeAlias` does. An alias does not make a new type: a `Scores` is a `map[str, list[int]]`.

## Literals

```luce
pub func main(arguments: list[str]) -> int!:
    print(42, 1_000_000, 0xFF, 0o17, 0b101)
    print(0.5, 6.022e23, 1e-7, 100.0)
    print(true, "text", (1, "one"), [1, 2], {"a": 1}, {1, 2})
    return 0
```

```output
42 1000000 255 15 5
0.5 6.022e23 1e-7 100.0
true text (1, one) [1, 2] {a: 1} {1, 2}
```

Underscores separate digits. A number with a point or an exponent is a `float`, any other is
an `int`; there are no suffixes. A float prints as the shortest text that reads back as the
same number, with `.0` when it has no point, so `print(0.1 + 0.2)` shows
`0.30000000000000004`, as in Python. `(1,)` is a tuple of one value, as in Python, and `()`
is the `unit` value. Strings and bytes have more forms ([Text and bytes](03-text-and-bytes.md)).

## Equality and ordering

`==` and `!=` compare values by their contents: numbers, text, tuples, collections, and
structs and enums whose fields can be compared. `<`, `<=`, `>` and `>=` order numbers, text
(by Unicode scalar value, so `"B" < "a"`), bytes, and tuples of those, element by element.

```luce
struct Point:
    let x: int
    let y: int

pub func main(arguments: list[str]) -> int!:
    print([1, 2] == [1, 2], {"a": 1} == {"a": 1}, Point(x = 1, y = 2) == Point(x = 1, y = 2))
    print((1, "a") < (1, "b"), "B" < "a", "apple" < "banana")
    return 0
```

```output
true true true
true true true
```

Two differences from Python:

- **Different types are never equal.** `1 == 1.0` is an error, not `true`, since an `int`
  and a `float` are never compared or mixed.
- **Class objects have no `==` of their own**, only identity, `is`. A class that should
  compare by contents declares `Equatable` ([Interfaces](11-interfaces-and-generics.md#the-built-in-interfaces)).

Comparisons do not chain: `a < b < c` is an error, written `a < b and b < c`.

## Hashing

`x.hash()` gives an `int` for any value that can be compared with `==`, consistently with it:
equal values have equal hashes. It is Python's `hash(x)`, written as a method, as `len(x)` is
`x.length`. Map keys and set elements must be hashable. Unlike Python, whose string hashes
change from run to run, a value's hash is the same number in every run of every Luce
program.

## Printing

`print`, `str(x)` and f-strings show any value that has a *display*. Numbers, text, `bool`,
tuples, collections, optionals, and structs and enums made of those have one:

```luce
struct Point:
    let x: float
    let y: float

enum Light:
    red
    green

pub func main(arguments: list[str]) -> int!:
    let maybe: int? = 3
    let nothing: int? = none
    print(Point(x = 1.0, y = 2.0), Light.red, maybe, nothing)
    print(["a", "b"], ("a", 1), str(2.5) + "!")
    return 0
```

```output
Point(x = 1.0, y = 2.0) Light.red 3 none
[a, b] (a, 1) 2.5!
```

Text is shown without quotes, also inside collections, so `print(["a", "b"])` shows
`[a, b]` where Python shows `['a', 'b']`. There is no separate `repr`. A class has no display
until it declares `Display`. Nor, outside its own module, has a struct with a private field,
since its display would show that field; it declares `Display` to be printed there
([Visibility](13-modules-and-packages.md#visibility)).

## Conversions

There are no implicit conversions, and no casts. Converting is a call:

| Call | Result |
| --- | --- |
| `int(x)` for a `float` | the `float` without its fraction, toward zero; traps if it is NaN or does not fit |
| `int(s)` for a `str` | the decimal number in the text, spaces around it and `_` between digits allowed; fails with `not an integer` |
| `int(s, base)` for a `str` | the number in that base, 2 to 36, with `0x`, `0o` or `0b` allowed for 16, 8 and 2, as Python's `int(s, base)` |
| `float(i)` for an `int` | the nearest `float` |
| `float(s)` for a `str` | the decimal number, with an optional fraction and exponent; fails if it is not one |
| `str(x)` | the display of `x` |
| `bool(s)` for a `str` | `"true"` or `"false"`; fails with `not a boolean` otherwise |

The conversions from text can fail, so their results are `int!`, `float!` and `bool!`
([Errors](10-optionals-and-errors.md#errors)). Python's `int("3.5")` and `bool("no")` differ:
the first raises in both languages, the second is `True` in Python, since any non-empty
string is true there, and a failure in Luce.

## Standard modules

Besides `print` and the conversions, a few of Python's built-in functions come with Luce, in
four small modules imported like any other: `math`, `text`, `console` and `time`.

```luce
import console
import math
import text

pub func main(arguments: list[str]) -> int!:
    print(math.abs(-7), math.abs(-2.5), math.min(3, 8), math.max("pear", "apple"))
    print(math.round(2.675, 2), math.round(2.5), math.round(1234.5, -2))
    print(text.code_of("é"), text.from_code(233), int("ff", 16), int("0b101", base = 2))
    let name = console.read_line("Your name? ") else "nobody"
    print(f"hello, {name}")
    return 0
```

```output
7 2.5 3 pear
2.67 2.0 1200.0
233 é 255 5
Your name? hello, nobody
```

| Call | Python's | Result |
| --- | --- | --- |
| `math.abs(x)` | `abs(x)` | the magnitude of an `int` or a `float`; of the smallest `int` it traps |
| `math.min(a, b)`, `math.max(a, b)` | `min(a, b)`, `max(a, b)` | the lesser or greater of two values of the same ordered type; of two equal, the first |
| `math.round(x, digits = 0)` | `round(x, digits)` | a `float` rounded to `digits` decimals, half to even on the exact value |
| `text.code_of(s)` | `ord(s)` | the number of a one-character text |
| `text.from_code(n)` | `chr(n)` | the one-character text of a number; one that names no character traps |
| `console.read_line(prompt = "")` | `input(prompt)` | writes the prompt and reads a line without its line end: a `str?`, `none` at the end of the input |
| `time.sleep(seconds)` | `time.sleep(seconds)` | waits at least that long, an `int` or a `float` of seconds; a negative one traps |
| `time.now()` | `time.monotonic_ns()` | nanoseconds from a fixed point, for measuring how long something took |
| `time.unix()` | `int(time.time())` | whole seconds since 1970 |

`from math import abs` brings one function in by its name, as in Python, and then `abs(x)`
calls it. An import that is not used is an error, as for any module
([Modules](13-modules-and-packages.md)).

Compared with Python:

- **`math.round` always gives a `float`** and takes only a `float`: `math.round(2.5)` is
  `2.0`, where Python gives the `int` 2. Like Python, it rounds a half to the even neighbour,
  on the number's exact binary value, so `math.round(2.675, 2)` is `2.67`. Convert with
  `int(...)` for an `int`.
- **`math.min` and `math.max` take two values.** A list has its own: `values.min()` and
  `values.max()` ([Collections](04-collections.md#lists)).
- **`console.read_line` answers `none` at the end of the input**, where Python's `input`
  raises `EOFError`, so `while let line = console.read_line():` reads every line. The
  program above ran with no input, so it printed the prompt and went on with `nobody`.
- **`math.abs` and `math.round` follow the no-mixing rule**: `math.round(3)` is an error,
  since an `int` is whole already.
- **`time.now()` counts nanoseconds as an `int`**, like Python's `time.monotonic_ns()`, so
  an interval is a subtraction:

```luce
import time

pub func main(arguments: list[str]) -> int!:
    let start = time.now()
    time.sleep(0.01)
    let elapsed = time.now() - start
    print(elapsed >= 10000000)
    return 0
```

```output
true
```

The names these functions had in Python are free: a variable may be called `max` or
`input`. Square roots, trigonometry and the like are in luce-std's `math`, a package
([Standard library](15-standard-library.md#math)).

## `unit` and `never`

A function without `->` returns `unit`, which has one value, `()`. You rarely write it, but it
appears in function types: `func(str)` is short for `func(str) -> unit`.

`never` is the type of an expression that does not finish: `return`, `trap(...)` and
`error(...)`. It fits anywhere a value is expected, which is why
`let user = find(name) else return` type-checks.

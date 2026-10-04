# 2. Values

## `let` and `var`

A name is bound with `let` or `var`:

```luce
pub func main(arguments: list[str]) -> int!:
    let name = "Ada"
    var visits = 1
    visits += 1
    print(name, visits)
    return 0
```

```output
Ada 2
```

`let` binds a name once; assigning to it again is an error. `var` can be assigned again,
but only with a value of the same type: once `visits` holds an `int`, it cannot hold a
string. Python has neither keyword, and allows both. In Luce:

- **Every binding has a value from the start.** There is no declaring now and assigning
  later, and no default zero.
- **The type comes from the value**, as in Python, so `let name = "Ada"` makes `name` a
  `str`. You can write it out when you want to: `let name: str = "Ada"`.
- **A name cannot be reused inside its scope.** A second `let name` in the same function,
  even in an inner block, is an error. Python would let the second one replace the first;
  Luce asks you to pick another name, so that one name means one thing for as long as it is
  visible.

Use `let` unless the value really changes. Most bindings in a Luce program are `let`.

## Numbers

Luce has one integer type, `int` (64 bits, signed), and one floating-point type, `float`
(64 bits, as Python's `float` is). Arithmetic mostly behaves as in Python:

```luce
pub func main(arguments: list[str]) -> int!:
    print(7 / 2, 6 / 3)
    print(7 // 2, -7 // 2, -7 % 2)
    print(2 ** 10, 0.1 + 0.2)
    print(1_000_000, 0xFF, 6.022e23)
    return 0
```

```output
3.5 2.0
3 -4 1
1024 0.30000000000000004
1000000 255 6.022e23
```

`/` always gives a `float`, `//` divides and rounds down, `%` takes the sign of the divisor,
and `**` is a power, all as in Python. Three things differ:

- **`int` and `float` do not mix.** `count * 1.5` is an error when `count` is an `int`.
  Convert one side: `float(count) * 1.5`. Python converts for you; Luce asks you to say
  which you meant.
- **An `int` has a limit.** Python's integers grow without bound; Luce's `int` holds values
  up to about 9.2 × 10¹⁸. Going past that is not a silent wrap-around, as in C: the program
  stops with a message. [Chapter 7](07-absence-and-failure.md) covers this kind of stop, a
  *trap*.
- **There are no bit operations** (`&`, `|`, `<<`) and no other integer sizes. Programs
  that need them are written in Luce Base, the language Luce is built on; [Chapter
  10](10-workers-and-where-next.md) introduces it.

## Text

A `str` is text, and works much as Python's does:

```luce
pub func main(arguments: list[str]) -> int!:
    let word = "café"
    print(word.length, word.upper(), word + "!")
    print(word[0..<3], word.starts_with("ca"), "fé" in word)
    print("a,b,,c".split(","))
    let block = """
        Two lines,
          the second indented.
        """
    print(block)
    return 0
```

```output
4 CAFé café!
caf true true
[a, b, , c]
Two lines,
  the second indented.
```

- `length` counts characters, as Python's `len` does. Since `length` is a property, it is
  written without parentheses.
- **Slices are written with a range**, `word[0..<3]`, where Python writes `word[0:3]`. `..<`
  means "up to, but not including".
- A triple-quoted string drops the indentation its lines share, so it can sit at the
  indentation of the code around it.
- `upper()` and `lower()` change only the ASCII letters `a` to `z`, which is why the `é`
  stays lowercase. Case rules for all languages are in the standard library's `unicode`
  module.

Strings cannot be changed in place, as in Python. Methods such as `upper()` and
`replace()` return a new string.

## Booleans and conditions

`true` and `false` are lowercase, and the operators are the words `and`, `or` and `not`, as
in Python. Unlike Python, **a condition must be a `bool`**: `if count:` and `if name:` are
errors. Write what you mean, `if count > 0:` or `if name != "":`.

## Conversions

Converting between types is a call, as in Python:

```luce
pub func main(arguments: list[str]) -> int!:
    let count = 3
    print(float(count) * 1.5, int(2.9), int(-2.9))
    print(int("42") + 1, float("2.5"), str(12) + " items")
    return 0
```

```output
4.5 2 -2
43 2.5 12 items
```

`int(2.9)` drops the fraction, rounding toward zero as Python does. `int("42")` reads a
number from text, and it can fail, since the text might not be a number. In `main` the
failure ends the program with a message:

<!-- exits 1 -->
```luce
pub func main(arguments: list[str]) -> int!:
    print(int("forty-two"))
    return 0
```

```output
error: not an integer
```

[Chapter 7](07-absence-and-failure.md) shows how to handle the failure instead.

## Where next

[Chapter 3](03-collections-and-loops.md) puts values together: lists, maps, sets and tuples,
and the loops that go through them.

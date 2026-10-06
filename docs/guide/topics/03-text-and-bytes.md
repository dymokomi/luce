# Text and bytes

[Reference: Literals](../../luce.md#3-literals), [Collections and text](../../luce.md#11-collections-and-text).

## String literals

```luce
pub func main(arguments: list[str]) -> int!:
    print("tab\there", "quote \" and backslash \\", "\u{1F600}")
    print(r"C:\temp\new")
    let poem = """
        Two lines,
          the second indented.
        """
    print(poem)
    return 0
```

```output
tab	here quote " and backslash \ 😀
C:\temp\new
Two lines,
  the second indented.
```

| Form | Meaning |
| --- | --- |
| `"..."` | a string, with the escapes `\\`, `\"`, `\n`, `\r`, `\t`, `\0` and `\u{1F600}` |
| `r"..."` | a raw string: backslashes are kept as written |
| `"""..."""` | a string over several lines; the indentation its lines share is removed, and so is the first line break |
| `f"..."` | a formatted string (below) |
| `b"..."` | bytes (below) |

Single quotes are not strings: `'a'` is an error. There is no separate character type either:
one character is a `str` of length one. A plain `"..."` string cannot span lines; use
`"""` or `+`.

## Formatted strings

`f"..."` puts the value of each `{expression}` into the text, using the value's display, as
`print` does:

```luce
pub func main(arguments: list[str]) -> int!:
    let name = "Ada"
    let scores = [90, 85]
    print(f"{name} has {scores.length} scores: {scores}")
    print(f"{name if name != "" else "nobody"} {{in braces}}")
    return 0
```

```output
Ada has 2 scores: [90, 85]
Ada {in braces}
```

- Any expression with a display can go in the braces, including calls and conditional
  expressions. A string inside the braces uses plain double quotes, as in Python 3.12.
- `{{` and `}}` stand for literal braces.
- An expression in braces cannot itself contain braces, so a set or map literal is bound to
  a name first.
- A formatted string is a single line: `f"""` is not available. Join lines with `+` or
  `"\n"`.

### Format specifications

A colon after the expression starts a *format specification*, Python's format
mini-language:

```luce
pub func main(arguments: list[str]) -> int!:
    let price = 1234.5
    let count = 42
    print(f"{price:.2f} {price:,.2f} {price:e} {0.256:.1%}")
    print(f"[{count:>6}] [{count:<6}] [{count:^6}] [{count:06}] [{count:+}]")
    print(f"{255:x} {255:#X} {5:08b} {1234567:_}")
    print(f"[{"name":>8}] [{"name":*^10}] [{"truncated":.5}] [{[1, 2]:>8}]")
    return 0
```

```output
1234.50 1,234.50 1.234500e+03 25.6%
[    42] [42    ] [  42  ] [000042] [+42]
ff 0XFF 00000101 1_234_567
[    name] [***name***] [trunc] [  [1, 2]]
```

The specification is `[[fill]align][sign][z][#][0][width][grouping][.precision][type]`, as
in Python: a fill character and `<`, `>`, `^` or `=` to align, `+` or a space for a sign,
`0` to pad a number with zeros, a width, `,` or `_` between thousands, a precision, and a type:
`d`, `b`, `o`, `x`, `X` or `c` for an `int`; `f`, `e`, `g` (and their capitals) or `%` for a
`float`; `s` for anything else. Numbers align right by default, everything else left. A
float's digits are rounded half to even on its exact value, as in Python, so
`f"{2.675:.2f}"` is `2.67`.

The differences from Python:

- **The specification must fit the value's type**, and the compiler checks it: `{price:x}`
  and `{count:.2f}` are errors, since `x` formats an `int` and `.2f` a `float`. Write
  `{float(count):.2f}`, as `int` and `float` never mix.
- **A float with no type and no precision shows as `print` shows it**: `{1e16:>8}` gives
  `    1e16`, where Python gives `   1e+16`.
- **A specification is literal text**: no `{width}` inside it, and no `!r` or `=` before it.
- Anything that is not a number, `bool` included, is formatted from its display, so
  `{true:>5}` gives ` true`; width and precision count characters, not bytes.

## Operations on `str`

A `str` is UTF-8 text that cannot be changed: every operation that "changes" a string makes a
new one. `==` compares contents, and `<` compares by Unicode scalar value, not by locale.

```luce
pub func main(arguments: list[str]) -> int!:
    let word = "héllo"
    print(word.length, word.byte_count, word[1..<3])
    print(word.upper(), word.contains("ll"), word.index_of("l"), word.index_of("z"))
    print("a,b,,c".split(","), " pad ".trim() + "|", "ab".repeat(3))
    print("one\ntwo\n".lines(), "a-b".replace("-", "+"), "x" + "y")
    print("  many   spaces  ".split(), "banana".count("an"), "banana".last_index_of("an"))
    print(word.reversed(), word.characters(), "report.txt".remove_suffix(".txt"))
    print("[" + "7".pad_left(3, "0") + "|" + "ab".center(6, "*") + "]", "hello world".title())
    print("2026".is_digit(), "abc".is_alpha(), "".is_empty)
    return 0
```

```output
5 6 él
HéLLO true 2 none
[a, b, , c] pad| ababab
[one, two] a+b xy
[many, spaces] 2 3
olléh [h, é, l, l, o] report
[007|**ab**] Hello World
true true true
```

| Operation | Meaning |
| --- | --- |
| `length` | the number of Unicode scalars (what Python's `len` counts); counts through the string |
| `byte_count` | the number of UTF-8 bytes; immediate |
| `is_empty` | whether there is nothing in it, Python's `not text` |
| `text[a..<b]` | the scalars from `a` up to `b`, as a new string; out of range traps |
| `a + b` | the two joined |
| `for c in text`, `characters()` | each scalar, as a one-character `str`; `characters()` makes a list of them |
| `contains(s)`, `starts_with(s)`, `ends_with(s)` | searches; `s in text` is `contains` |
| `index_of(s)`, `last_index_of(s)` | the scalar index of the first or last occurrence, an `int?` (Python's `find` and `rfind`, with `none` for -1) |
| `count(s)` | how many times `s` occurs, without overlapping |
| `split()` | the words between runs of white space, as Python's `split()` |
| `split(separator)` | the pieces between every occurrence of a non-empty separator, empty pieces kept |
| `lines()` | split at `\n`, dropping a `\r` before it; a final newline does not add an empty line |
| `trim()`, `trim_start()`, `trim_end()` | without white space at both ends, or one (Python's `strip`, `lstrip`, `rstrip`) |
| `remove_prefix(s)`, `remove_suffix(s)` | without `s` at that end, when it is there |
| `upper()`, `lower()`, `capitalize()`, `title()` | ASCII letters only changed; `é` stays `é` |
| `replace(a, b)` | every occurrence of `a` replaced, left to right |
| `repeat(n)` | `n` copies joined, Python's `text * n` |
| `reversed()` | the characters in reverse order, Python's `text[::-1]` |
| `pad_left(width, fill = " ")`, `pad_right(...)`, `center(...)` | padded to `width` characters: Python's `rjust`, `ljust` and `center` |
| `is_digit()`, `is_alpha()`, `is_alnum()`, `is_space()` | whether every character is an ASCII digit, letter, either, or white space, and there is one |
| `bytes()` | the UTF-8 encoding, as `bytes` |

Compared with Python:

- **A string is not indexed by position**: `word[0]` is an error. Take a one-character slice,
  `word[0..<1]`, or go through it with `for`. Indexing UTF-8 by position would cost a walk
  from the start, which Luce prefers to make visible.
- **`split(" ")` keeps empty pieces**: `"a  b".split(" ")` is `[a, , b]`, as in Python.
  `split()` with no argument splits on runs of white space.
- **The names follow the rest of Luce**: `trim` for `strip`, `index_of` for `find`,
  `pad_left` for `rjust`, `starts_with` for `startswith`. A search that finds nothing
  answers `none`, not `-1`, and `count("")` traps rather than counting the gaps.
- **`join` is a method of the list**, the other way round from Python:
  `["a", "b"].join(", ")`.
- `upper()`, `lower()`, `capitalize()`, `title()` and the `is_` tests follow ASCII only:
  `"élan".title()` is `élan`, where Python gives `Élan`. Case conversion for all of
  Unicode, and normalisation, are in the standard library's `unicode` module.

Building a long string by `+` in a loop copies it each time. For many pieces, collect them
in a `list[str]` and `join` once at the end.

## Bytes

`bytes` is a sequence of bytes that cannot be changed, as in Python. It is what file and
network functions hand you when the data is not text.

```luce
pub func main(arguments: list[str]) -> int!:
    let data = b"\x00\x01AB"
    print(data, data.length, data[2], data[1..<3])
    print(data + b"C", "hé".bytes())
    let text = b"hello".text()
    print(text)
    let broken = b"\xff".text() catch failure:
        recover failure.message
    print(broken)
    return 0
```

```output
b"\x00\x01\x41\x42" 4 65 b"\x01\x41"
b"\x00\x01\x41\x42\x43" b"\x68\xc3\xa9"
hello
invalid UTF-8
```

A `bytes` literal is written `b"..."`, with `\xNN` for any byte. Indexing gives an `int`
from 0 to 255, and `for` goes through the bytes as `int`s. `text()` decodes UTF-8 and fails
on invalid input. Bytes display as a `b"..."` literal with every byte escaped.

Luce's bit operators work on these `int`s, so a byte's fields come apart as in Python:
`(byte >> 4) & 15`. Code that reads fixed-size binary formats in bulk is usually written in
Base, and hands Luce the result ([Luce and Base](16-base.md)).

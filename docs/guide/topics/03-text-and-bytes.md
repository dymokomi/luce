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
- **There is no format specification**: `{price:.2f}`, `{n:>8}` and `{n:x}` are not
  available. A float prints in its shortest exact form; to show fewer digits, round it first
  with the standard library's `math.round` ([The standard library](15-standard-library.md)).
- An expression in braces cannot itself contain braces, so a set or map literal is bound to
  a name first.
- A formatted string is a single line: `f"""` is not available. Join lines with `+` or
  `"\n"`.

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
    var reversed = ""
    for character in word:
        reversed = character + reversed
    print(reversed)
    return 0
```

```output
5 6 él
HéLLO true 2 none
[a, b, , c] pad| ababab
[one, two] a+b xy
olléh
```

| Operation | Meaning |
| --- | --- |
| `length` | the number of Unicode scalars (what Python's `len` counts); counts through the string |
| `byte_count` | the number of UTF-8 bytes; immediate |
| `text[a..<b]` | the scalars from `a` up to `b`, as a new string; out of range traps |
| `a + b` | the two joined |
| `for c in text` | each scalar, as a one-character `str` |
| `contains(s)`, `starts_with(s)`, `ends_with(s)` | searches; `s in text` is `contains` |
| `index_of(s)` | the scalar index of the first occurrence, an `int?` |
| `split(separator)` | the pieces between every occurrence of a non-empty separator, empty pieces kept |
| `lines()` | split at `\n`, dropping a `\r` before it; a final newline does not add an empty line |
| `trim()` | without spaces, tabs and line breaks at both ends |
| `upper()`, `lower()` | ASCII letters only changed; `é` stays `é` |
| `replace(a, b)` | every occurrence of `a` replaced, left to right |
| `repeat(n)` | `n` copies joined |
| `bytes()` | the UTF-8 encoding, as `bytes` |

Compared with Python:

- **A string is not indexed by position**: `word[0]` is an error. Take a one-character slice,
  `word[0..<1]`, or go through it with `for`. Indexing UTF-8 by position would cost a walk
  from the start, which Luce prefers to make visible.
- **`split` needs a separator.** `"a  b".split(" ")` keeps the empty piece between the two
  spaces, unlike Python's `split()` with no argument. Split on `" "` and filter out the
  empty pieces to split on runs of spaces.
- **`join` is a method of the list**, the other way round from Python:
  `["a", "b"].join(", ")`.
- `upper()` and `lower()` follow ASCII only. Case conversion for all of Unicode, and
  normalisation, are in the standard library's `unicode` module.

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

Luce has no bit operations, so code that takes binary formats apart byte by byte is usually
written in Base, and hands Luce the result ([Luce and Base](16-base.md)).

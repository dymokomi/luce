# The standard library

The language has its built-in types and their methods, covered in the earlier chapters. The
rest of the standard library is a package, `luce-std`, which a project adds as a
dependency:

```sh
luc add dymokomi/luce-std
```

and whose modules are imported through the package's name:

<!-- fragment -->
```luce
from luce_std import files, paths, math
```

`luce-std` is written in Luce Base, so a program that uses it is built (`luc run`,
`luce build`) rather than run in the interpreter. Its modules also serve Base programs, and
offer them more than Luce can use: functions that take or return Base-only types, such as
pointers or byte buffers, are not visible from Luce ([Luce and Base](16-base.md)). This
chapter lists what a Luce program can call.

## `files`

Reading, writing and organising files and directories:

<!-- needs luce-std -->
```luce
from luce_std import files, paths

pub func main(arguments: list[str]) -> int!:
    files.ensure_directory("notes")
    files.write_text(paths.join("notes", "a.txt"), "first\nsecond\n")
    files.create_text(paths.join("notes", "b.txt"))
    var names: list[str] = []
    with files.Entries("notes") as entries:
        for index in 0..<entries.count():
            names.append(entries.name(index))
    print(names.sorted())
    let text = files.read_text("notes/a.txt")
    print(text.lines(), files.path_kind("notes"))
    let missing = files.read_text("nowhere.txt") catch failure:
        recover f"failed: {failure.message}, missing: {failure.code == files.missing}"
    print(missing)
    files.delete_path("notes", recursive = true)
    return 0
```

```output
[a.txt, b.txt]
[first, second] FileKind.directory
failed: the file could not be opened, missing: true
```

| Function | Does |
| --- | --- |
| `read_text(path, limit = 4 MiB)` | the file's contents, as UTF-8 text |
| `write_text(path, text)` | create or replace the file with `text` |
| `create_text(path, text = "")` | create a new file; fails if it exists |
| `ensure_directory(path)` | create the directory and its parents if they are missing |
| `make_directory(path)` | create one directory; fails if it exists |
| `copy_path(source, destination)`, `move_path(source, destination)` | copy or move a file or directory |
| `delete_path(path, recursive = false)` | delete a file, or a directory (with its contents when `recursive`) |
| `path_kind(path)` | a `FileKind`: `.regular`, `.directory`, `.symlink` and others |
| `absolute_path(path)` | the absolute form of `path` |
| `home_directory()` | the user's home directory |
| `Entries(path)` | the names in a directory: `count()`, `name(index)`, `close()` |

Every function that touches the file system can fail. The error codes are constants of the
module, for comparing with `failure.code`: `missing`, `permission_denied`, `already_exists`,
`no_space`, `not_directory`, `is_directory`, `not_empty`, `too_large`, `read_only_filesystem`,
`name_too_long`, `symlink_loop`, `cross_device` and `failed`.

## `paths`

Working with paths as text, without touching the file system:

| Function | Result for `"/a/b/c.txt"` or as noted |
| --- | --- |
| `base(path)` | `c.txt` |
| `directory(path)` | `/a/b` |
| `stem(path)`, `extension(path)` | `c` and `.txt` |
| `join(left, right)` | `join("a", "b.txt")` is `a/b.txt` |
| `normalize(path)` | `normalize("a/./b/../c")` is `a/c` |
| `is_absolute(path)`, `is_rooted(path)`, `root(path)` | about the path's start |

`join` and `normalize` can fail on paths too long or malformed for the platform. The
separator is `\` on Windows and `/` elsewhere.

## `math`

<!-- needs luce-std -->
```luce
from luce_std import math

pub func main(arguments: list[str]) -> int!:
    print(math.sqrt(16.0), math.round(2.5), math.floor(-1.5), math.abs(-3.0))
    print(math.imax(3, 7), math.iabs(-4), round(3.14159, 2))
    return 0
```

```output
4.0 3.0 -2.0 3.0
7 4 3.14
```

| Functions | Notes |
| --- | --- |
| `floor`, `ceil`, `round`, `trunc` | `math.round` rounds halves away from zero; the built-in `round(x, digits)` rounds them to even, as Python's |
| `sqrt`, `cbrt`, `hypot`, `pow`, `exp`, `exp2`, `log`, `log2`, `log10`, `log1p`, `expm1`, `fma` | as in C and Python's `math` |
| `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh` | radians |
| `abs`, `sign`, `copysign`, `min`, `max`, `clamp` | for `float` |
| `iabs`, `imin`, `imax`, `iclamp`, `div_floor`, `mod_floor` | for `int` |
| `checked_iabs`, `checked_div_floor`, `checked_mod_floor` | `int?`: `none` instead of a trap |
| `is_nan`, `is_finite`, `is_infinite`, `signbit` | tests |
| `mod`, `remainder`, `modf`, `nextafter`, `next_up`, `next_down` | for numerical work |

`math32` has the same functions for single-precision floats, for Base programs.

## `unicode`

Text operations that follow the Unicode standard, where the built-in `upper()` and `lower()`
handle ASCII only:

| Function | Does |
| --- | --- |
| `to_upper(text)`, `to_lower(text)` | full case mapping: `to_upper("straße")` is `STRASSE` |
| `case_fold(text)` | a form for case-insensitive comparison |
| `normalize(text, form = .nfc)` | Unicode normalisation |

## `process`

`process.Command(program, arguments)` starts a program and collects its output. Its methods:
`is_finished()`, `exit_code()` (an `int?`, `none` while it runs), `output()` and
`error_message()` (the captured standard output and error), `cancel()` and `close()`.

## `crash`

`crash.enable("my-app", "1.0.0")` turns on crash reports: when the program traps or crashes,
a report with a stack trace is written to `crash.directory()`, and the next run can read it
with `crash.take_report("my-app")`. This is for applications started from a desktop, which
have no terminal to print a trap to.

## Other packages

Graphics, user interfaces, images, cryptography, compression and more are separate packages
on [pkg.luciaos.com](https://pkg.luciaos.com). `luc add owner/name` adds one; each package's
page there lists its modules.

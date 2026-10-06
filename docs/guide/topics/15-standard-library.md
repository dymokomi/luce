# The standard library

The language has its built-in types and their methods, covered in the earlier chapters, and
three small modules that come with the compiler, `math`, `text` and `console`, which hold
Python's `abs`, `min`, `max`, `round`, `ord`, `chr` and `input`
([Types and values](02-types-and-values.md#standard-modules)). They need no package and run
in the interpreter. The rest of the standard library is a package, `luce-std`, which a
project adds as a dependency:

```sh
luc add dymokomi/luce-std
```

and whose modules are imported through the package's name:

<!-- fragment -->
```luce
from luce_std import files, paths, process, net, clock, random
```

`luce-std` is written in Luce Base, so a program that uses it is built (`luc run`,
`luce build`) rather than run in the interpreter. Its modules also serve Base programs, and
offer them more than Luce can use: functions that take or return Base-only types, such as
pointers or byte buffers, are not visible from Luce ([Luce and Base](16-base.md)). This
chapter lists what a Luce program can call.

What these modules answer belongs to the program, as any Luce value does: a list of names, a
file's text, a program's output. Files, connections and temporary directories are objects
that hold something of the system's; like Python's file objects they close with `with`, or
with `close()`, and close by themselves when the last reference goes away.

Every function that touches the system can fail. The failure carries a code, a constant of
the module, for comparing with `failure.code`, and a message.

## `files`

Reading and writing whole files, and organising directories:

<!-- needs luce-std -->
```luce
from luce_std import files, paths

pub func main(arguments: list[str]) -> int!:
    with files.TemporaryDirectory() as scratch:
        let notes = paths.join(scratch.path(), "notes")
        files.ensure_directory(paths.join(notes, "old"))
        files.write_text(paths.join(notes, "a.txt"), "first\nsecond\n")
        files.write(paths.join(notes, "b.bin"), b"\x00\x01")
        print(files.list(notes), files.walk(notes))
        print(files.read_text(paths.join(notes, "a.txt")).lines(), files.read(paths.join(notes, "b.bin")))
        let info = files.metadata(paths.join(notes, "a.txt"))
        print(info.size, info.kind, files.exists(paths.join(notes, "c.txt")))
        files.copy(paths.join(notes, "a.txt"), paths.join(notes, "c.txt"))
        files.rename(paths.join(notes, "c.txt"), paths.join(notes, "old/c.txt"))
        files.remove_tree(paths.join(notes, "old"))
        let missing = files.read_text(paths.join(notes, "nowhere.txt")) catch failure:
            recover f"failed: {failure.message}, missing: {failure.code == files.missing}"
        print(missing)
    return 0
```

```output
[a.txt, b.bin, old] [a.txt, b.bin, old]
[first, second] b"\x00\x01"
13 FileKind.regular false
failed: the file could not be opened, missing: true
```

| Function | Does |
| --- | --- |
| `read_text(path, limit = 4 MiB)` | the file's contents as text; a file that is not UTF-8 fails |
| `read(path)` | the file's contents as `bytes` |
| `write_text(path, text)` | replace the file with `text`, all at once: a reader sees the old file or the new one |
| `write(path, data)` | create or truncate the file and write `data` |
| `create_text(path, text = "")` | create a new file; fails with `already_exists` if there is one |
| `exists(path)` | whether something is there |
| `metadata(path)` | a `Metadata`: `kind` (a `FileKind`: `.regular`, `.directory`, `.symlink`…), `size`, `permissions`, and `modified`, `accessed` and `changed` times, each `seconds` and `nanoseconds` since 1970 |
| `list(path)` | the names in a directory, sorted |
| `walk(path)` | every path below a directory, relative to it and sorted, as `a/b.txt` |
| `ensure_directory(path)` | create the directory and its missing parents, as `mkdir -p` does |
| `create_directory(path)` | create one directory; its parent must exist |
| `copy(source, destination, replace = false)` | copy a file |
| `rename(source, destination, replace = true)` | move or rename, at once, on one filesystem |
| `remove_file(path)`, `remove_directory(path)` | remove a file, or an empty directory |
| `remove_tree(path)` | remove a directory and everything in it |
| `canonical(path)` | the absolute path, with links resolved |
| `home_directory()` | the user's home directory |

The error codes are `missing`, `permission_denied`, `already_exists`, `no_space`,
`not_directory`, `is_directory`, `not_empty`, `too_large`, `read_only_filesystem`,
`name_too_long`, `symlink_loop`, `cross_device`, `invalid_options`, `invalid_text` and
`failed`.

### Files opened for reading and writing

`files.open(path)` opens a file for reading, as Python's `open(path)` does, and answers a
`File`. A second argument opens it otherwise: `files.OpenMode.replace` to write a new
file over any old one, `.append` to add to the end, `.create_new` to write a file that must
not exist yet, `.read_write` for both on an existing file.

<!-- needs luce-std -->
```luce
from luce_std import files, paths

pub func main(arguments: list[str]) -> int!:
    with files.TemporaryDirectory() as scratch:
        let log = paths.join(scratch.path(), "log.txt")
        with files.open(log, files.OpenMode.append) as file:
            file.write_text("started\n")
            file.write_text("stopped\r\n")
        with files.open(log) as file:
            while let line = file.read_line():
                print(f"[{line}]")
        with files.open(log) as file:
            print(file.read_text(4), file.read_bytes(3), file.read_text().length)
    return 0
```

```output
[started]
[stopped]
star b"\x74\x65\x64" 10
```

| Method | Does |
| --- | --- |
| `read_line()` | the next line without its `\n` or `\r\n`, or `none` at the end |
| `read_text(maximum = -1)` | up to `maximum` bytes as text, ending on a whole character; all the rest by default |
| `read_bytes(maximum = -1)` | up to `maximum` bytes; all the rest by default |
| `write_text(text)`, `write_bytes(data)` | write all of it |
| `seek(offset, origin = .start)` | move to `offset` from the start, the current place (`.current`) or the end (`.end`) |
| `metadata()`, `truncate(length)`, `sync()` | as for a path; `sync` waits until the data is on the device |
| `close()` | close the file; `with` does it at the end of its block |

Writes are not buffered in the program: each write reaches the system, and `close` has
nothing left to flush.

`files.TemporaryDirectory()` makes a fresh directory under the system's temporary directory
(or under the path it is given); `path()` names it, and closing it removes it with
everything in it. A file opened with `files.OpenMode.create_temporary` has no name once it
is open and disappears when it closes.

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

## `process`

Running other programs, and the program's own environment:

<!-- needs luce-std -->
```luce
from luce_std import process

pub func main(arguments: list[str]) -> int!:
    let done = process.run("sh", ["-c", "echo out; echo err >&2; exit 3"])
    print(done.exit_code, done.output.trim(), done.error_output.trim())
    with process.Command("sh", ["-c", "echo working; exit 7"]) as command:
        print(command.wait(), command.output().trim())
    process.set_variable("GREETING", "hello")
    print(process.variable("GREETING"), process.variable("NOT_SET_ANYWHERE"))
    process.unset_variable("GREETING")
    return 0
```

```output
3 out err
7 working
hello none
```

`run(program, arguments)` runs a program, without a shell, waits for it, and answers a
`Completed` with its `exit_code`, `output` and `error_output`, as Python's
`subprocess.run(..., capture_output=True)` does. The program is found on `PATH` when its
name has no directory; `directory = path` runs it elsewhere, and
`environment = ["NAME=value"]` sets variables for it alone.

`Command(program, arguments)` starts a program in the background and collects what it
writes, standard output and error together, up to `output_limit` bytes (1 MiB). Its
methods:

| Method | Does |
| --- | --- |
| `wait()` | wait until the program ends; its exit code. A program that could not start, was cancelled or wrote past its limit fails |
| `is_finished()`, `exit_code()` | without waiting: whether it ended, and its code (`none` while it runs) |
| `output()` | what it wrote so far |
| `error_message()` | why it failed, when it did |
| `cancel()` | stop it |
| `close()` | stop it if it still runs, and let it go; `with` does it |

| Function | Does |
| --- | --- |
| `variable(name)` | an environment variable's value, or `none` |
| `set_variable(name, value)`, `unset_variable(name)` | change the environment, for this program and those it starts |
| `variables()` | every variable, as `NAME=value` texts |
| `current_directory()`, `change_directory(path)` | the working directory |
| `id()` | this process's identifier |
| `exit(code)` | end the program at once with `code` |

The error code is `failed`.

## `net`

TCP connections, by host name or address. This program listens, connects to itself, and
talks both ways:

<!-- needs luce-std -->
```luce
from luce_std import net

pub func main(arguments: list[str]) -> int!:
    with net.listen("127.0.0.1", 0) as listener:
        with net.connect("localhost", listener.port(), timeout = 5.0) as client:
            with listener.accept_connection() as server:
                client.write_text("hello\nworld\n")
                print(server.read_line(), server.read_line())
                server.write_text("bye")
                server.shutdown(net.ShutdownDirection.write)
                print(client.read_text(), client.read_text() == "")
    print("127.0.0.1" in net.lookup("localhost"))
    return 0
```

```output
hello world
bye true
true
```

`connect(host, port, timeout = 0.0)` tries each address `host` has until one answers; a
positive `timeout`, in seconds, bounds each try. `listen(host, port)` waits for connections
on `host` (`"0.0.0.0"` for every interface, `"127.0.0.1"` for this machine only); port 0
takes any free port, which `port()` tells. `accept_connection()` waits for the next
connection. `lookup(host)` answers its addresses as text.

| `Connection` method | Does |
| --- | --- |
| `read_line()` | the next line without its line ending, or `none` once the other side has finished |
| `read_text(maximum = 65536)`, `read_bytes(maximum = 65536)` | what arrives next, waiting until something does; empty once the other side has finished |
| `write_text(text)`, `write_bytes(data)` | send all of it |
| `shutdown(net.ShutdownDirection.write)` | tell the other side nothing more is coming, and keep reading |
| `peer_address()`, `local_address()` | the two ends; `text()` writes one as `127.0.0.1:80`, and its `ip.text()` the address alone |
| `set_no_delay(true)`, `set_keepalive(true)` | socket options |
| `close()` | close the connection; `with` does it |

The error codes include `connection_refused`, `timed_out`, `unknown_host`,
`network_unreachable`, `address_in_use`, `closed` and `failed`.

For HTTP, the `luce-http-client` and `luce-server` packages build on this module.

## `clock`

Time: measuring it, waiting, and calendar dates.

<!-- needs luce-std -->
```luce
from luce_std import clock

pub func main(arguments: list[str]) -> int!:
    let start = clock.now()
    clock.sleep(0.05)
    print(start.elapsed().seconds() >= 0.05)
    let span = clock.Duration.of_seconds(1.5).plus(clock.Duration.of_milliseconds(250))
    print(span.seconds(), span.milliseconds())
    let meeting = clock.DateTime(2026, 10, 4, 9, 30, offset = 2 * 3600)
    print(meeting.text(), meeting.weekday(), meeting.to_utc().text())
    let later = clock.DateTime.parse("2026-10-04T18:00Z")
    print(later.since(meeting).seconds() / 3600.0, meeting.is_before(later), later.date_text())
    return 0
```

```output
true
1.75 1750
2026-10-04T09:30:00+02:00 Weekday.sunday 2026-10-04T07:30:00Z
10.5 true 2026-10-04
```

`clock.now()` reads a clock that only goes forward, for measuring; `elapsed()` is the time
since. `sleep(seconds)` waits. `timestamp()` is the system's time as seconds since 1970, as
Python's `time.time()`.

A `Duration` is made with `Duration.of_seconds`, `Duration.of_milliseconds` or
`Duration(nanoseconds = n)`, read back with `seconds()`, `milliseconds()` or its
`nanoseconds` field, and combined with `plus`, `minus` and `times`.

A `DateTime` is a date and time of day at an offset from UTC, as Python's `datetime` with a
time zone is:

| | |
| --- | --- |
| `DateTime(year, month, day, hour = 0, minute = 0, second = 0, nanosecond = 0, offset = 0)` | a given date and time; `offset` is seconds east of UTC |
| `DateTime.now()`, `DateTime.now_utc()` | now, in local time or UTC |
| `DateTime.parse(text)`, `text()` | ISO 8601 both ways: `2026-10-04T09:30:00+02:00`; a text without an offset is UTC |
| `DateTime.from_timestamp(seconds)`, `timestamp()`, `unix_seconds()` | to and from seconds since 1970 |
| `to_utc()`, `to_local()`, `at_offset(seconds)` | the same moment elsewhere |
| `plus(duration)`, `since(other)`, `is_before(other)` | arithmetic and comparison |
| `year`, `month`, `day`, `hour`, `minute`, `second`, `nanosecond`, `offset`, `weekday()`, `day_of_year()`, `date_text()` | its parts |

A date the calendar does not have fails with `clock.invalid`.

## `random`

A pseudo-random generator, `random.Random(seed)`. The same seed gives the same numbers on
every platform; without a seed, the system seeds it.

<!-- needs luce-std -->
```luce
from luce_std import random

pub func main(arguments: list[str]) -> int!:
    var dice = random.Random(2026)
    var rolls: list[int] = []
    for i in 0..<10:
        rolls.append(dice.int(1, 6))
    print(rolls)
    let names = ["ada", "grace", "linus"]
    print(names[dice.index(names.length)], dice.float() < 1.0)
    var fresh = random.Random()
    let spread = fresh.uniform(0.0, 10.0)
    print(spread >= 0.0 and spread < 10.0)
    return 0
```

```output
[6, 5, 1, 1, 1, 5, 3, 6, 4, 4]
ada true
true
```

| Method | Does |
| --- | --- |
| `int(low, high)` | a whole number from `low` to `high`, both included, as Python's `randint` |
| `index(count)` | a position in a list of `count` items |
| `float()`, `uniform(low, high)` | a float from 0.0, or `low`, up to but not including 1.0, or `high` |
| `chance(probability)` | `true` with that probability |
| `normal(mean = 0.0, deviation = 1.0)` | a value from the normal distribution |
| `bytes(count)` | random bytes |

The generator is xoshiro256**: fast and good for simulations, games and sampling, and not
for secrets, for which a cryptography package is the place.

## `math`

<!-- needs luce-std -->
```luce
from luce_std import math

pub func main(arguments: list[str]) -> int!:
    print(math.sqrt(16.0), math.round(2.5), math.floor(-1.5), math.abs(-3.0))
    print(math.imax(3, 7), math.iabs(-4), math.round(3.14159 * 100.0) / 100.0)
    return 0
```

```output
4.0 3.0 -2.0 3.0
7 4 3.14
```

| Functions | Notes |
| --- | --- |
| `floor`, `ceil`, `round`, `trunc` | `round` rounds halves away from zero |
| `sqrt`, `cbrt`, `hypot`, `pow`, `exp`, `exp2`, `log`, `log2`, `log10`, `log1p`, `expm1`, `fma` | as in C and Python's `math` |
| `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh` | radians |
| `abs`, `sign`, `copysign`, `min`, `max`, `clamp` | for `float` |
| `iabs`, `imin`, `imax`, `iclamp`, `div_floor`, `mod_floor` | for `int` |
| `checked_iabs`, `checked_div_floor`, `checked_mod_floor` | `int?`: `none` instead of a trap |
| `is_nan`, `is_finite`, `is_infinite`, `signbit` | tests |
| `mod`, `remainder`, `modf`, `nextafter`, `next_up`, `next_down` | for numerical work |

`math32` has the same functions for single-precision floats, for Base programs.

This `math` is not the language's own `math` module, which has `abs`, `min`, `max` and a
`round` that rounds halves to even. The name `math` alone always means the language's; this
one is reached through its package, and when a module wants both, it gives this one another
name:

<!-- needs luce-std -->
```luce
import math
from luce_std import math as fmath

pub func main(arguments: list[str]) -> int!:
    print(fmath.sqrt(math.abs(-16.0)), math.round(2.5), fmath.round(2.5))
    return 0
```

```output
4.0 2.0 3.0
```

## `unicode`

Text operations that follow the Unicode standard, where the built-in `upper()` and `lower()`
handle ASCII only:

| Function | Does |
| --- | --- |
| `to_upper(text)`, `to_lower(text)` | full case mapping: `to_upper("straße")` is `STRASSE` |
| `case_fold(text)` | a form for case-insensitive comparison |
| `normalize(text, form = .nfc)` | Unicode normalisation |

## `crash`

`crash.enable()` turns on crash reports: when the program traps or crashes, a report with a
stack trace is written to `crash.directory()` (`~/.luce/crashes`), named after the package
and version in the program's `package.prisma`. This is for applications started from a
desktop, which have no terminal to print a trap to. A UI application built with luce-ui needs
none of this: its reports are on, and after a crash it shows the report in a window of its
own, with Copy, Reopen and Quit.

A program can save its work when it traps, the way an editor writes an autosave file:

<!-- fragment -->
```luce
from luce_std import crash
from luce_std import paths

class Editor:
    var scene: Scene

    func save_for_recovery() -> unit!:
        let path = paths.join(crash.recovery_directory(), "scene.recovered")
        self.scene.write(path)
        crash.note_recovery(path)

func start(editor: Editor) -> unit!:
    crash.on_crash(editor.save_for_recovery)
```

| Function | Does |
| --- | --- |
| `enable(app = "", version = "")` | turn reports on, named after the package unless given a name |
| `on_crash(hook)` | run `hook` after a trap, before the program ends: five seconds for all hooks |
| `recovery_directory()` | `~/.luce/recovery/<program>`, made when missing: where a hook saves |
| `note_recovery(path)` | from a hook: the report, and the crash window, say where the copy is |
| `relaunch_on_crash()` | after a crash, start the program again to show the report (luce-ui does this) |
| `report_to_show()` | in that new process, the report's path; empty text in an ordinary run |
| `read_report(path)`, `take_report(app)` | a report's text, marked as seen; the newest unseen one |
| `reopen()` | start the program again as an ordinary run |

Hooks run on the thread that trapped. A fatal signal, such as an invalid memory access, runs
none: nothing but the report can be written safely from it, so a program that must not lose
work also saves as it goes and looks in `recovery_directory()` when it starts. Reports stay
on the computer; nothing is sent anywhere.

## Other packages

Graphics, user interfaces, images, cryptography, compression and more are separate packages
on [pkg.luciaos.com](https://pkg.luciaos.com). `luc add owner/name` adds one; each package's
page there lists its modules.

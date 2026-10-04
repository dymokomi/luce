# Workers

[Reference: Workers](../../luce.md#14-workers).

## `spawn` and `wait`

`spawn f(arguments)` starts a call to `f` on another worker and immediately gives back a
`task[T]`, where `T` is `f`'s result type. `wait task` waits for the call to finish and gives
its result:

```luce
struct Range:
    let start: int
    let stop: int

func sum_of_squares(range: Range) -> int:
    var total = 0
    for n in range.start..<range.stop:
        total += n * n
    return total

pub func main(arguments: list[str]) -> int!:
    let low = spawn sum_of_squares(Range(start = 0, stop = 500000))
    let high = spawn sum_of_squares(Range(start = 500000, stop = 1000000))
    print(wait low + wait high)
    return 0
```

```output
333332833333500000
```

The two halves run at the same time on different processor cores. A built program runs each
worker on its own thread; the interpreter, `luce run`, runs each task to completion when it
is spawned, which gives the same results more slowly.

## Workers share nothing

A worker receives **copies** of its arguments and gives back a **copy** of its result. It
cannot see the caller's variables or objects, and the caller cannot see the worker's. So two
workers can never change the same data at once, and Luce needs no locks, no atomic
variables and no thread-safe collections. This is the model of Python's `multiprocessing`,
without the cost of separate processes or of pickling.

What can be sent, as an argument or a result:

- numbers, `bool`, `str` and `bytes`;
- tuples, structs and enums made of sendable values;
- lists, maps and sets of sendable values, which are copied with their contents;
- optionals and `Result`s of those.

What cannot: class objects, closures, `Weak` references, and resources such as open files.
These are shared or tied to the worker that made them by nature. Passing one is an error when
the program is checked:

<!-- exits 1 -->
```luce
class Counter:
    var count: int = 0

func read(counter: Counter) -> int:
    return counter.count

pub func main(arguments: list[str]) -> int!:
    let reading = spawn read(Counter())
    print(wait reading)
    return 0
```

```output
luce: main.luc:8:37: a `Counter` is not sendable: a worker takes scalars, texts, tuples, structs, enums and copies of collections of those (§14)
```

Copy what the worker needs into a struct, and send that.

## The rules for tasks

- **`f` must be a named function** of the program: not a method, a lambda or a closure,
  which could carry shared state with them.
- **A task is waited exactly once, by the function that spawned it.** It cannot be returned,
  stored in a field or captured by a lambda. Waiting twice traps.
- **A function does not return while its tasks run.** Tasks it did not wait for are waited
  for when it returns. If it fails or returns early, the remaining tasks' results are
  discarded when they finish.
- **Output interleaves.** What workers `print` appears in whatever order they print it.

## Failures

If the spawned function can fail, its failure arrives at `wait`, and is handled like the
failure of a call:

```luce
let invalid = ErrorCode.package(1)

func check(name: str) -> str!:
    if name == "":
        error(invalid, "an empty name")
    return name.upper()

pub func main(arguments: list[str]) -> int!:
    let good = spawn check("ada")
    let bad = spawn check("")
    print(wait good)
    let result = wait bad catch failure:
        recover f"failed: {failure.message}"
    print(result)
    return 0
```

```output
ADA
failed: an empty name
```

A trap in a worker stops the whole program, as a trap anywhere does.

## Dividing work

Since tasks are bound by name and waited in the same function, a program spawns a fixed
number of them at a time: split the work into as many parts as you want running at once,
spawn one task per part, then wait for each. Spawning and waiting inside a loop runs the
iterations one after another, since each `wait` comes before the next `spawn`.

Workers suit work that takes long enough to be worth the copies: computing over large
inputs, encoding, parsing several files. A program that waits on the network or on user
input usually does so through a library's own events rather than through workers.

# Control flow

[Reference: Control flow](../../luce.md#8-control-flow).

## `if`

`if`, `elif` and `else` are Python's, with one rule added: **the condition must be a
`bool`**. Python treats `0`, `""`, `[]` and `None` as false; Luce has no such
"truthiness", so `if items:` is an error. Write the question out: `if items.length > 0:`,
`if name != "":`, `if value != none:`.

A statement after a `return`, `break` or failure that always happens is an error ("this
statement is never reached"), rather than dead code left in place.

## `if let` and `while let`

`if let` binds the value inside an optional when there is one, and runs its block only then.
`while let` repeats as long as there is one:

```luce
pub func main(arguments: list[str]) -> int!:
    let ages = {"Ada": 36}
    if let age = ages["Ada"]:
        print(f"Ada is {age}")
    else:
        print("no age for Ada")
    let queue = [1, 2, 3]
    while let item = queue.last:
        print(queue.pop())
    print(queue)
    return 0
```

```output
Ada is 36
3
2
1
[]
```

These cover what Python's walrus operator is used for, `if (m := pattern.match(s)):`, and
the bound name is visible only in the block where it has a value.

## `for`

`for` goes through:

| Over | Gives |
| --- | --- |
| a range, `0..<n` or `1..=n` | each `int` |
| a `list` or `set` | each element, in order |
| a `map` | each `(key, value)` tuple, in insertion order |
| a `str` | each character, as a one-character `str` |
| `bytes` | each byte, as an `int` from 0 to 255 |
| `values.indexed()` | each `(index, element)` |
| a value of a type that declares `Iterable[T]` | what its iterator gives (below) |

A tuple in the `for` takes each item apart: `for (name, age) in ages:`. Changing the size of
the collection being iterated traps ([Collections](04-collections.md#what-they-share)).

`break` leaves the innermost loop and `continue` goes on to its next round. A loop can carry a
*label*, and `break` and `continue` can name it, to leave or continue an outer loop from an
inner one, which Python can only do with a flag or an exception:

```luce
pub func main(arguments: list[str]) -> int!:
    let grid = [[1, 2], [3, 4], [5, 6]]
    var found = (-1, -1)
    search: for (row, cells) in grid.indexed():
        for (column, cell) in cells.indexed():
            if cell == 4:
                found = (row, column)
                break search
    print(found)
    return 0
```

```output
(1, 1)
```

There is no `for ... else` and no `while ... else`.

### Iterating your own types

A type that declares `Iterable[T]` can be used in a `for`. Its `iterator()` method returns a
class that declares `Iterator[T]`, whose `next()` answers each element in turn and `none`
at the end. This is Python's `__iter__` and `__next__`, with `none` in place of
`StopIteration`:

```luce
class Countdown: Iterable[int]:
    let start: int

    func init(self, start: int):
        self.start = start

    func iterator(self) -> Iterator[int]:
        return Ticker(self.start)

class Ticker: Iterator[int]:
    var current: int

    func init(self, current: int):
        self.current = current

    func next(self) -> int?:
        if self.current == 0:
            return none
        self.current -= 1
        return self.current + 1

pub func main(arguments: list[str]) -> int!:
    for n in Countdown(3):
        print(n)
    let ticker = Ticker(2)
    while let n = ticker.next():
        print(f"tick {n}")
    return 0
```

```output
3
2
1
tick 2
tick 1
```

The iterator is a class because `next()` changes it. There are no generators (`yield`).

## `match`

`match` compares a value against patterns and runs the first arm that fits. Its statement
form has a block for each arm; its expression form has `=>` and a value for each:

```luce
func classify(point: (int, int)) -> str:
    return match point:
        (0, 0) => "origin"
        (0, _) => "on the y axis"
        (x, 0) => f"on the x axis at {x}"
        _ => "elsewhere"

func describe(value: int?) -> str:
    match value:
        none:
            return "nothing"
        n if n < 0:
            return "negative"
        n:
            return f"the number {n}"

pub func main(arguments: list[str]) -> int!:
    print(classify((0, 0)), classify((0, 4)), classify((3, 0)), classify((1, 1)))
    print(describe(none), describe(-3), describe(7))
    let word = "two"
    let number = match word:
        "one" => 1
        "two" => 2
        _ => 0
    print(number)
    return 0
```

```output
origin on the y axis on the x axis at 3 elsewhere
nothing negative the number 7
2
```

| Pattern | Matches |
| --- | --- |
| `42`, `"two"`, `true` | that value |
| `1..<10`, `1..=9` | a number in the range |
| `.circle(radius)` | that enum case, binding its data by position |
| `.empty` | that enum case, without data |
| `(p, q)` | a tuple whose members match `p` and `q` |
| `none` | an empty optional |
| `name` | anything, bound to `name`; for an optional, a value that is present, unwrapped |
| `_` | anything, bound to nothing |
| `pattern if condition` | the pattern, when the condition also holds |

**A `match` must cover every possible value.** For an enum, that means every case, or a `_`;
for numbers and text, a final `_` or name. A missing case is reported where the `match` is,
so adding a case to an enum shows every place that needs to handle it. Python's `match` has
no such check.

Python's `match` also matches classes by their attributes and sequences of any length; Luce's
patterns are the ones in the table.

## `with`

`with expression as name:` runs its block and then calls `name.close()`, however the block
ends: at its end, by `return` or `break`, or because a failure is passing through.

```luce
let failed = ErrorCode.package(1)

class Resource:
    let name: str

    func init(self, name: str):
        self.name = name

    func close(self):
        print(f"close {self.name}")

func work(fail: bool) -> int!:
    with Resource("a") as a, Resource("b") as b:
        print(f"using {a.name} and {b.name}")
        if fail:
            error(failed, "the work failed")
    return 0

pub func main(arguments: list[str]) -> int!:
    let result = work(true) catch failure:
        print(failure.message)
        recover 1
    print(result)
    return 0
```

```output
using a and b
close b
close a
the work failed
1
```

Several resources are closed in reverse order. Any value whose type has a `close()` method
that takes nothing and returns nothing can be used, which includes the resources Base
packages provide ([Luce and Base](16-base.md#handles)). There is no `__enter__`: the
expression itself produces the resource.

Luce has no `try`/`finally` and no `defer`; `with` is how cleanup is tied to a block.

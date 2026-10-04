# 3. Collections and loops

## Lists

A list is written as in Python, and grows and shrinks as Python's does:

```luce
pub func main(arguments: list[str]) -> int!:
    let primes = [2, 3, 5, 7]
    primes.append(11)
    print(primes, primes.length)
    print(primes[0], primes[-1], primes[1..<3])
    print(primes.contains(5), primes.index_of(7))
    return 0
```

```output
[2, 3, 5, 7, 11] 5
2 11 [3, 5]
true 3
```

Indexing starts at 0, and a negative index counts from the end. A slice is written with a
range, `primes[1..<3]`, and makes a new list. An index past the end stops the program,
much as Python's `IndexError` does, except that it cannot be caught.

Two rules that Python does not have:

- **All elements have one type.** `[1, "a"]` is an error. A list of integers is a
  `list[int]`.
- **An empty list needs its type written**, since there is nothing to infer it from:
  `let names: list[str] = []`.

Notice that `primes` is a `let` and still changed. A list is an object that bindings
*share*, exactly as in Python: `let` stops `primes` from being bound to another list, but
not the list from changing. A second binding refers to the same list:

```luce
pub func main(arguments: list[str]) -> int!:
    let first = ["Ada"]
    let second = first
    second.append("Grace")
    print(first)
    let third = first.copy()
    third.append("Barbara")
    print(first, third)
    return 0
```

```output
[Ada, Grace]
[Ada, Grace] [Ada, Grace, Barbara]
```

`copy()` makes an independent list, as `list(x)` or `x.copy()` do in Python.

## Maps

A map is Python's `dict`: keys to values, kept in the order they were inserted.

```luce
pub func main(arguments: list[str]) -> int!:
    let ages = {"Ada": 36, "Grace": 45}
    ages["Barbara"] = 40
    print(ages, ages.length, "Ada" in ages)
    print(ages["Ada"], ages["Linus"])
    let age = ages["Linus"] else 0
    print(age + 1)
    return 0
```

```output
{Ada: 36, Grace: 45, Barbara: 40} 3 true
36 none
1
```

Looking up a key that is not there is not an error, as Python's `KeyError` would be.
`ages["Linus"]` answers `none`, "no value", and its type says so: it is an `int?`, an
*optional* `int`, rather than an `int`. You cannot do arithmetic on it until you say what
should happen when it is missing. `else` supplies a value for that case, and
`ages.get("Linus", 0)` is there too, as in Python. [Chapter 7](07-absence-and-failure.md)
covers optionals in full.

## Sets and tuples

A set holds each value once, as in Python, and also keeps insertion order. A tuple groups
a fixed number of values that may have different types:

```luce
pub func main(arguments: list[str]) -> int!:
    let seen = {3, 1, 2}
    seen.insert(3)
    print(seen, 2 in seen, seen.union({9}))
    let pair = (1, "one")
    let (number, name) = pair
    print(pair, pair.0, number, name)
    return 0
```

```output
{3, 1, 2} true {3, 1, 2, 9}
(1, one) 1 1 one
```

A tuple's members are `.0`, `.1` and so on, or taken apart with `let (a, b) = ...` as in
Python. `{}` is an empty map, as in Python, so an empty set is written with its type:
`let seen: set[int] = {}`.

## Loops

`for` goes through a list, a set, a map, a string, or a range of numbers:

```luce
pub func main(arguments: list[str]) -> int!:
    for i in 0..<3:
        print(i)
    let ages = {"Ada": 36, "Grace": 45}
    for (name, age) in ages:
        print(f"{name} is {age}")
    for (index, name) in ["Ada", "Grace"].indexed():
        print(index, name)
    return 0
```

```output
0
1
2
Ada is 36
Grace is 45
0 Ada
1 Grace
```

- **Ranges** are written `0..<3` (0, 1 and 2, like Python's `range(3)`) or `1..=3` (1, 2
  and 3, the end included); `(0..<10).step(2)` and `(1..=3).reversed()` are Python's other
  forms of `range`.
- **A map gives key and value pairs**, as Python's `ages.items()` does, where Python's
  `for name in ages` gives only the keys. Use `ages.keys()` for the keys alone.
- **`indexed()`** pairs each element with its position, as Python's `enumerate` does.

`while`, `break` and `continue` work as in Python. One more rule: **changing a list's
length while a `for` goes through it stops the program**, instead of skipping or repeating
elements as it can in Python. Collect the changes and apply them after the loop.

## `if` and `match`

`if`, `elif` and `else` are Python's. `match` chooses between cases, like Python's `match`
statement or a chain of `elif`s, and it also works as an expression, producing a value:

```luce
pub func main(arguments: list[str]) -> int!:
    for n in [0, 7, 42, -1]:
        let word = match n:
            0 => "zero"
            1..<10 => "a digit"
            _ if n < 0 => "negative"
            _ => "many"
        print(n, word)
    return 0
```

```output
0 zero
7 a digit
42 many
-1 negative
```

Each arm is a pattern, an `=>` and a value. A pattern can be a literal, a range, `_` (any
value), and can carry a condition, `if n < 0`. The arms are tried in order and the first
that matches gives the value. A `match` must cover every possible value, which is why the
last arm here is `_`. [Chapter 5](05-structs-and-enums.md) shows where `match` is most
useful: choosing between the cases of an enum.

## Where next

[Chapter 4](04-functions.md) is about functions: declaring them, calling them with named
arguments, and passing them around as values.

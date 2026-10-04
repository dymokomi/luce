# 4. Functions

## Declaring and calling

A function is declared with `func`, its parameters' types, and its result type after `->`:

```luce
func greet(name: str, greeting: str = "Hello", punctuation: str = "!") -> str:
    return f"{greeting}, {name}{punctuation}"

func log(message: str):
    print(f"[log] {message}")

pub func main(arguments: list[str]) -> int!:
    print(greet("Ada"))
    print(greet("Grace", greeting = "Hi"))
    print(greet(name = "Linus", punctuation = "."))
    log("done")
    return 0
```

```output
Hello, Ada!
Hi, Grace!
Hello, Linus.
[log] done
```

Calls work as in Python: arguments by position first, then by name, and a parameter with a
default may be left out. A function that returns nothing, like `log`, has no `->`.

What Python has and Luce does not:

- **Types are required** on every parameter and on the result. Inside a function, the types
  of `let` and `var` are inferred, but a signature is always written out, so that a call can
  be checked against it.
- **No `*args` or `**kwargs`.** A function that takes any number of things takes a list.
- **One function per name.** There is no overloading, by type or by number of arguments.

The order of functions in a file does not matter: `main` can call a function declared
below it.

## A default is made fresh for each call

Python evaluates a default once, when the function is defined, so a default list is shared
between calls, a well-known trap. In Luce each call that leaves the argument out gets a new
one:

```luce
func add_item(item: str, into: list[str] = []) -> list[str]:
    into.append(item)
    return into

pub func main(arguments: list[str]) -> int!:
    print(add_item("a"), add_item("b"))
    return 0
```

```output
[a] [b]
```

A default must be a constant, such as a number, a string or an enum case, or an empty
collection.

## Functions as values

A function can be passed and stored like any value. Its type is written
`func(parameter types) -> result`:

```luce
func twice(n: int) -> int:
    return n * 2

func apply(f: func(int) -> int, value: int) -> int:
    return f(value)

pub func main(arguments: list[str]) -> int!:
    print(apply(twice, 4))
    print(apply((n) => n + 1, 4))
    let words = ["kiwi", "fig", "banana"]
    print(words.map((w) => w.length))
    print(words.filter((w) => w.length > 3))
    return 0
```

```output
8
5
[4, 3, 6]
[kiwi, banana]
```

`(n) => n + 1` is a *lambda*, Python's `lambda n: n + 1`. Its parameter types come from where
it is used: `apply` expects a `func(int) -> int`, so `n` is an `int`. Luce has no list
comprehensions; `map` and `filter` with a lambda do the same job.

A lambda holds one expression. For more, write a block lambda, with its types spelled out:

```luce
pub func main(arguments: list[str]) -> int!:
    let describe = func (n: int) -> str:
        if n % 2 == 0:
            return "even"
        return "odd"
    print([1, 2, 3].map(describe))
    return 0
```

```output
[odd, even, odd]
```

## Closures

A lambda can use the local variables around it. It *captures* them, as a nested function
does in Python. A captured `var` is shared between the function and the lambda, so a lambda
can keep a count without Python's `nonlocal`:

```luce
func counter() -> func() -> int:
    var count = 0
    return func () -> int:
        count += 1
        return count

pub func main(arguments: list[str]) -> int!:
    let next = counter()
    print(next(), next(), next())
    let other = counter()
    print(other())
    return 0
```

```output
1 2 3
1
```

Each call to `counter` makes a new `count`, so `other` starts again from 1. Memory for
captured values is managed for you: `count` lives as long as some closure still refers to
it.

## Where next

[Chapter 5](05-structs-and-enums.md) introduces your own types: structs, enums, and their
methods.

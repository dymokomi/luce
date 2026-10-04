# Functions

[Reference: Functions](../../luce.md#7-functions).

## Declaring a function

```luce
func area(width: float, height: float = 1.0) -> float:
    return width * height

func log(message: str):
    print(f"[log] {message}")

func factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

pub func main(arguments: list[str]) -> int!:
    print(area(2.0, 3.0), area(2.0), area(height = 3.0, width = 2.0))
    log("starting")
    print(factorial(20))
    return 0
```

```output
6.0 2.0 6.0
[log] starting
2432902008176640000
```

- **Every parameter has a type, and the result type follows `->`.** A function with no `->`
  returns nothing (`unit`). Types are never inferred across a signature, so a function can be
  understood, and checked, from its declaration alone.
- **Every path through a function with a result must `return` a value**; the compiler checks
  this.
- **Parameters cannot be assigned.** Bind a `var` from one to change it.
- **Functions are declared at the top level of a module**, in any order, or as methods
  inside a type. A function cannot be declared inside another function; use a lambda
  (below).
- Recursion works as usual. There is no tail-call guarantee, so very deep recursion can run
  out of stack.

## Arguments

Arguments are passed by position, then by name. A named argument may follow positional ones
but not precede them, and names may come in any order. A parameter with a default may be
left out.

Each call that leaves out a default gets a fresh value: a default `[]` is a new list every
time, never one shared between calls as in Python. A default must be a constant: a literal,
an enum case, an empty collection, or a struct built from those.

There are no variadic parameters (`*args`, `**kwargs`), no keyword-only or positional-only
markers, and no overloading: one name, one function. A function that takes any number of
values takes a list; one that has several variants takes defaults, or has several names.

## Methods

A function declared inside a struct, enum or class is a method. Its first parameter is
`self`, written without a type, as in Python:

```luce
struct Counter:
    var count: int = 0

    func value(self) -> int:
        return self.count

    func increment(self):
        self.count += 1

    func starting_at(count: int) -> Counter:
        return Counter(count = count)

pub func main(arguments: list[str]) -> int!:
    var counter = Counter.starting_at(5)
    counter.increment()
    let read = counter.value
    print(counter.value(), read())
    return 0
```

```output
6 6
```

- A method that assigns to a field of `self` *changes* it. For a struct or enum, such a
  method can only be called on a `var` ([Structs and enums](08-structs-and-enums.md#methods-that-change-self)).
  The compiler works this out; there is nothing to mark.
- A function in a type that does not use `self` is a *type function*, called through the
  type: `Counter.starting_at(5)`. It plays the part of Python's `@staticmethod` and
  `@classmethod`, and of alternative constructors.
- `counter.value`, without parentheses, is the method bound to `counter`, a function value
  like any other. For a struct, the bound method keeps its own copy of the receiver.
- There are no properties (`@property`) and no operator overloading beyond the built-in
  interfaces ([Interfaces](11-interfaces-and-generics.md#the-built-in-interfaces)).

## Function values

A function's type is written `func(parameter types) -> result`. Named functions, bound
methods and lambdas are all values of such types:

```luce
func plain(n: int) -> int:
    return n + 1

func run(f: func(int) -> int!, value: int) -> int!:
    return f(value)

pub func main(arguments: list[str]) -> int!:
    let transforms: list[func(int) -> int] = [plain, (n) => n * 3]
    print(transforms.map((f) => f(2)))
    let describe = func (n: int) -> str:
        if n % 2 == 0:
            return "even"
        return "odd"
    print(describe(7), run(plain, 1))
    return 0
```

```output
[3, 6]
odd 2
```

There are two kinds of lambda:

- **`(params) => expression`**, an expression lambda, like Python's `lambda`. Its parameter
  types come from where it is used; when nothing says, write them: `(n: int) => n + 1`.
- **`func (params) -> R:`** with a block, for anything longer. Its types are always written.

A function that cannot fail can be passed where a fallible one is expected, as `plain` is
to `run` above; the reverse is an error. A generic function cannot be used as a value, only
called ([Generics](11-interfaces-and-generics.md#generic-functions)).

## Closures

A lambda can use local variables of the function around it. How it captures each depends on
what the variable is:

- **A `let` value** is copied into the lambda.
- **An object** (a class instance or a collection) is shared, as everywhere.
- **A `var`** is shared between the function and every lambda that captures it, so a change
  made by either is seen by both. Python needs `nonlocal` for this; Luce does it by itself.

```luce
func make_counter(start: int) -> func() -> int:
    var count = start
    return func () -> int:
        count += 1
        return count

pub func main(arguments: list[str]) -> int!:
    var total = 0
    let add = func (n: int):
        total += n
    add(3)
    add(4)
    print(total)
    let next = make_counter(10)
    print(next(), next())
    return 0
```

```output
7
11 12
```

A closure lives as long as something refers to it, and keeps what it captured alive with it.
Closures cannot be sent to workers ([Workers](12-workers.md)), and Base code receives only
named functions, never closures ([Luce and Base](16-base.md)).

Python's classic loop trap, every closure created in a loop seeing the loop variable's last
value, does not arise: the loop variable is a fresh `let` in each round, and is copied.

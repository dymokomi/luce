# Structs and enums

[Reference: Values](../../luce.md#9-values).

Structs and enums are Luce's *value types*: like numbers, they are copied when assigned or
passed. Classes, the other kind of user type, are shared; [Classes and
memory](09-classes-and-memory.md) covers them and when to choose which.

## Structs

```luce
struct Rectangle:
    let width: float
    let height: float
    var label: str = "untitled"

    func area(self) -> float:
        return self.width * self.height

pub func main(arguments: list[str]) -> int!:
    let a = Rectangle(width = 2.0, height = 3.0)
    let b = Rectangle(2.0, 3.0, "door")
    print(a, a.area())
    print(b.label, a == b, a == Rectangle(2.0, 3.0))
    return 0
```

```output
Rectangle(width = 2.0, height = 3.0, label = untitled) 6.0
door false true
```

- **Fields** are `let` or `var`, with a type and an optional default. A default is a
  constant or an empty collection, made afresh for each struct built.
- **Construction** gives the fields by position, in declaration order, or by name; fields
  with defaults may be left out. This is what Python's `@dataclass` generates.
- **Equality, hashing and printing** are worked out from the fields: two structs are equal
  when all their fields are, and a struct prints as `Name(field = value, ...)`. They exist
  when every field supports them; a struct with a class field, for instance, has no `==`
  unless that class declares `Equatable`.
- A struct can declare interfaces, `struct Circle: Shape:`, and replace the generated
  equality, ordering or display by declaring `Equatable`, `Ordered` or `Display`
  ([Interfaces](11-interfaces-and-generics.md#the-built-in-interfaces)).

A struct cannot contain itself directly, `var next: Node?` inside `struct Node`, since a
value would then have no fixed size. A list of itself is allowed, `var children: list[Tree]`,
and so is a class that refers to itself.

## Values copy

Assigning a struct, passing it, returning it or putting it in a collection copies it:

```luce
struct Point:
    var x: int
    var y: int

func moved_right(point: Point) -> Point:
    var copy = point
    copy.x += 1
    return copy

pub func main(arguments: list[str]) -> int!:
    let a = Point(x = 0, y = 0)
    var b = a
    b.x = 5
    let c = moved_right(b)
    let points = [a, b]
    b.y = 9
    print(a, b, c, points)
    return 0
```

```output
Point(x = 0, y = 0) Point(x = 5, y = 9) Point(x = 6, y = 0) [Point(x = 0, y = 0), Point(x = 5, y = 0)]
```

In Python, `b = a` makes `b` another name for the same object, and `b.x = 5` would change
`a` too. Here each name has its own point. The same goes for `points`: the list holds copies
made when it was built, so the later `b.y = 9` does not reach it.

The copy is shallow: a struct that holds a list or a class object holds a reference to it,
and the copies share that object.

```luce
struct Inventory:
    let owner: str
    var items: list[str] = []

pub func main(arguments: list[str]) -> int!:
    let first = Inventory(owner = "Ada")
    var second = first
    second.items.append("lamp")
    print(first.items, second.items)
    return 0
```

```output
[lamp] [lamp]
```

A `let` struct cannot change at all: none of its fields can be assigned, `var` fields
included. To change a struct, bind it with `var`.

## Methods that change `self`

A method that assigns to a field of `self` changes the value it is called on. The compiler
recognises such methods by themselves, and allows calling them only on something that can
change: a `var`, or a `var` field of a `var`.

```luce
struct Counter:
    var count: int = 0

    func increment(self):
        self.count += 1

pub func main(arguments: list[str]) -> int!:
    var counter = Counter()
    counter.increment()
    counter.increment()
    print(counter.count)
    return 0
```

```output
2
```

With `let counter = Counter()`, the call `counter.increment()` is an error: "the method
`increment` changes its receiver, which must be a `var`". Swift writes such methods as
`mutating`; Luce infers it.

## Enums

An enum is a closed set of cases, each with optional data:

```luce
enum Token:
    number(value: int)
    word(text: str)
    end

    func describe(self) -> str:
        return match self:
            .number(value) => f"the number {value}"
            .word(text) => f"the word {text}"
            .end => "the end"

pub func main(arguments: list[str]) -> int!:
    let tokens = [Token.number(3), .word(text = "hi"), .end]
    for token in tokens:
        print(token, token.describe())
    print(Token.word("hi") == Token.word(text = "hi"), {Token.end: 1})
    return 0
```

```output
Token.number(value = 3) the number 3
Token.word(text = hi) the word hi
Token.end the end
true {Token.end: 1}
```

- A case's data is declared like parameters, and given by position or by name.
- `Token.number(3)` names the type; `.number(3)` is enough where the type is known: an
  argument, a list of tokens, a `match` arm, a comparison.
- Enums are values: copied, compared, hashed and printed through their data, like structs.
- An enum can have methods and declare interfaces.
- The only way to read a case's data is `match`, which binds it. There is no `.value`
  attribute and no `isinstance` test.

An enum replaces several Python idioms at once: an `Enum` of constants (cases without
data), a `Union` of dataclasses (cases with data), and a string that should only take a few
values. A case is never `none`: `none` means an empty optional, so it cannot name a case.

Python's `Enum` values can be numbers or strings. Luce's cannot: a case is just itself.
Enums that must match numbers, for a file format or a C library, are declared in Base
([Luce and Base](16-base.md#what-crosses)).

### The standard enum `Result`

`Result[T]`, with the cases `.success(value: T)` and `.failure(reason: Error)`, is an
ordinary enum available everywhere. It stores the outcome of an operation that can fail;
[Optionals and errors](10-optionals-and-errors.md#storing-an-outcome-result) shows how to use it.

## Generic structs and enums

Structs and enums can take type parameters:

```luce
struct Pair[A, B]:
    let first: A
    let second: B

enum Tree[T]:
    leaf(value: T)
    node(left: list[Tree[T]], right: list[Tree[T]])

pub func main(arguments: list[str]) -> int!:
    let pair = Pair(first = 1, second = "one")
    let tree = Tree.node(left = [Tree.leaf(1)], right = [Tree.leaf(2)])
    print(pair, tree)
    return 0
```

```output
Pair(first = 1, second = one) Tree.node(left = [Tree.leaf(value = 1)], right = [Tree.leaf(value = 2)])
```

The type arguments are inferred from the values, or written: `Pair[int, str]`.
[Interfaces and generics](11-interfaces-and-generics.md#generic-types) has the rules.

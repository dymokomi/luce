# Interfaces and generics

[Reference: Interfaces and generics](../../luce.md#13-interfaces-and-generics).

## Interfaces

An interface is a list of method signatures:

```luce
interface Shape:
    func area(self) -> float
    func name(self) -> str

struct Circle: Shape:
    let radius: float

    func area(self) -> float:
        return 3.14159 * self.radius * self.radius

    func name(self) -> str:
        return "circle"

enum Polygon: Shape:
    square(side: float)
    triangle(base: float, height: float)

    func area(self) -> float:
        return match self:
            .square(side) => side * side
            .triangle(base, height) => base * height / 2.0

    func name(self) -> str:
        return "polygon"

func report(shape: Shape):
    print(f"{shape.name()}: {shape.area()}")

pub func main(arguments: list[str]) -> int!:
    let shapes: list[Shape] = [Circle(radius = 1.0), Polygon.square(side = 2.0)]
    for shape in shapes:
        report(shape)
    return 0
```

```output
circle: 3.14159
polygon: 4.0
```

- **Conformance is declared**: `struct Circle: Shape:`. A type that has the right methods
  but does not declare the interface does not conform. This is the opposite of Python's
  `Protocol`, which matches by shape, and the same as an abstract base class you inherit.
  Several interfaces are separated by commas.
- **Each method must match the signature exactly**, names and types.
- **Structs, enums and classes** can all conform.
- A struct's or enum's methods for an interface may not change `self`: an interface value is
  read through the interface, never changed through it. A class's may.

### Interface values

A value of a conforming type can be used wherever the interface is expected, as `report`
and the list above show. The interface value holds a copy of a struct or enum, or a
reference to a class object, and a call goes to that type's own method.

An interface value supports only the interface's methods: it has no `==`, no display and no
hash of its own, and there is no way to ask which concrete type it holds or to convert it
back (no `isinstance`, no downcast). When code needs to know the variant, an enum is the
right tool, since `match` handles every case explicitly.

Interfaces have no default method bodies, no fields, and no inheritance between interfaces.

## Generic functions

A generic function has type parameters in square brackets, each with optional *bounds*,
the interfaces its type arguments must have:

```luce
func largest[T: Ordered](values: list[T]) -> T?:
    var best = values.first else return none
    for value in values:
        if value > best:
            best = value
    return best

func describe[T: Ordered & Display](values: list[T]) -> str:
    return values.sorted().map((value) => str(value)).join(" < ")

func pick[T](values: list[T], index: int) -> T:
    return values[index]

pub func main(arguments: list[str]) -> int!:
    print(largest([3, 9, 2]), largest(["pear", "apple"]))
    print(describe([3, 1, 2]), pick[str](["a", "b"], 1))
    return 0
```

```output
9 pear
1 < 2 < 3 b
```

- **A generic function is checked once**, against its bounds, not at each call. Inside it, a
  `T` supports only what the bounds promise: `<` with `Ordered`, `==` with `Equatable`,
  display with `Display`, `hash` with `Hashable`, and the methods of any other interface named.
  Every type supports being bound, passed, returned, and put in tuples, optionals and
  collections.
- **Type arguments are usually inferred** from the arguments. When they cannot be, write
  them: `pick[str](...)`, `largest[int](empty)`.
- Several bounds are joined with `&`.
- A generic function is called, never used as a function value; and a method cannot have type
  parameters of its own (its type can).

Each distinct set of type arguments produces its own compiled copy of the function, so a
generic function costs nothing at run time compared with writing it out for each type.

## Generic types

Structs, enums, classes and interfaces take type parameters the same way:

```luce
interface Source[T]:
    func read(self) -> T?

class Counter: Source[int]:
    var current: int = 0

    func read(self) -> int?:
        if self.current == 3:
            return none
        self.current += 1
        return self.current

class Stack[T]:
    var items: list[T] = []

    func push(self, item: T):
        self.items.append(item)

func drain[T: Display](source: Source[T]) -> str:
    var parts: list[str] = []
    while let item = source.read():
        parts.append(str(item))
    return parts.join(",")

pub func main(arguments: list[str]) -> int!:
    print(drain[int](Counter()))
    let stack = Stack[str]()
    stack.push("a")
    print(stack.items)
    return 0
```

```output
1,2,3
[a]
```

`Stack[str]` is a type of its own, with `T` replaced by `str`. When construction does not
fix the type arguments, as for a `Stack` built with no arguments, they are written:
`Stack[str]()`. A bound can name a generic interface, `[S: Source[int]]`. Type arguments are
not inferred through a conversion to an interface, which is why `drain[int]` is written out
above.

## The built-in interfaces

The language knows six interfaces, because operators, `print`, `for`, maps and sets use them:

| Interface | Method to write | Enables |
| --- | --- | --- |
| `Equatable` | `equals(self, other: Self) -> bool` | `==`, `!=`, `in`, `contains`, `index_of` |
| `Hashable` | `hashed(self) -> int` | map keys, set elements, `hash(x)` |
| `Ordered` | `compare(self, other: Self) -> int` | `<`, `<=`, `>`, `>=`, `sort`, `sorted` |
| `Display` | `display(self) -> str` | `print`, `str(x)`, f-strings |
| `Iterable[T]` | `iterator(self) -> Iterator[T]` | `for` |
| `Iterator[T]` | `next(self) -> T?` | `for`, `while let` |

(`Self` in the table stands for the declaring type: in `struct Version`, it is written
`Version`.)

Structs, enums, tuples and the built-in types already have equality, hashing, ordering where
it makes sense, and display, worked out from their contents. A struct or enum declares one of
these interfaces only to replace that behaviour. A class has none of them until it declares
them:

```luce
class Key: Equatable, Hashable, Display:
    let id: int

    func init(self, id: int):
        self.id = id

    func equals(self, other: Key) -> bool:
        return self.id == other.id

    func hashed(self) -> int:
        return self.id

    func display(self) -> str:
        return f"#{self.id}"

pub func main(arguments: list[str]) -> int!:
    let names = {Key(1): "one", Key(2): "two"}
    print(names[Key(1)], Key(1) == Key(1), Key(1) is Key(1), names)
    return 0
```

```output
one true false {#1: one, #2: two}
```

The rules that keep these consistent:

- `Hashable` and `Ordered` are declared together with `Equatable`, so that equal values hash
  alike and compare as neither less nor greater.
- `compare` answers a negative number, zero or a positive number.
- These interfaces describe what a type can do; they are not types of values: `let x:
  Equatable = ...` is an error, and a program cannot declare its own interface with these
  names.

# 8. Interfaces and generics

## Interfaces

An interface names the methods a type must have, like a Python `Protocol` or an abstract
base class with only abstract methods:

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

class Square: Shape:
    var side: float

    func init(self, side: float):
        self.side = side

    func area(self) -> float:
        return self.side * self.side

    func name(self) -> str:
        return "square"

func total(shapes: list[Shape]) -> float:
    var sum = 0.0
    for shape in shapes:
        sum += shape.area()
    return sum

pub func main(arguments: list[str]) -> int!:
    let shapes: list[Shape] = [Circle(radius = 1.0), Square(2.0)]
    for shape in shapes:
        print(shape.name(), shape.area())
    print(total(shapes))
    return 0
```

```output
circle 3.14159
square 4.0
7.14159
```

A type says which interfaces it has when it is declared, `struct Circle: Shape:`, and must
then provide each method with exactly the declared signature. Unlike Python's duck typing,
a type that merely happens to have an `area` method is not a `Shape`. Structs, enums and
classes can all have interfaces, and a value of any of them can be used where a `Shape` is
expected, as in the list above.

Interfaces take the place of inheritance. There are no base classes, no default method
bodies in an interface, and no way to turn a `Shape` back into a `Circle`; code that needs to
know the exact type uses an enum instead.

## Generic functions

A generic function works on any type, named by a *type parameter* in square brackets:

```luce
func largest[T: Ordered](values: list[T]) -> T?:
    var best = values.first else return none
    for value in values:
        if value > best:
            best = value
    return best

pub func main(arguments: list[str]) -> int!:
    print(largest([3, 9, 2]))
    print(largest(["pear", "apple"]))
    let empty: list[float] = []
    print(largest(empty))
    return 0
```

```output
9
pear
none
```

`T: Ordered` says what `T` must be able to do: here, be compared with `<` and `>`. Inside
the function, a `T` can only be used in the ways its bounds allow, so `largest` is checked
once, when it is declared, and every call with an ordered type is then known to work. Python
type checkers do something similar with `TypeVar(bound=...)`; in Luce it is part of the
language and always checked.

Several bounds are joined with `&`: `[T: Ordered & Display]`.

## Generic types

Structs, enums and classes take type parameters the same way:

```luce
class Stack[T]:
    var items: list[T] = []

    func push(self, item: T):
        self.items.append(item)

    func pop(self) -> T?:
        if self.items.length == 0:
            return none
        return self.items.pop()

pub func main(arguments: list[str]) -> int!:
    let stack = Stack[str]()
    stack.push("a")
    stack.push("b")
    print(stack.pop(), stack.pop(), stack.pop())
    return 0
```

```output
b a none
```

`list[T]`, `map[K, V]` and `set[T]` are generic types of this kind.

## The built-in interfaces

A few interfaces are known to the language, because operators and `print` use them:

| Interface | Method | Gives the type |
| --- | --- | --- |
| `Equatable` | `equals(self, other: Self) -> bool` | `==` and `!=` |
| `Hashable` | `hashed(self) -> int` | use as a map key or in a set |
| `Ordered` | `compare(self, other: Self) -> int` | `<`, `>`, `sort()` |
| `Display` | `display(self) -> str` | `print`, `str(x)` and f-strings |
| `Iterable[T]` | `iterator(self) -> Iterator[T]` | `for` |

They play the part of Python's `__eq__`, `__hash__`, `__lt__`, `__str__` and `__iter__`.
Structs and enums already have equality, hashing and printing, worked out from their fields;
they declare these interfaces only to replace that. A class has none of them until it
declares them:

```luce
struct Version: Equatable, Ordered, Display:
    let major: int
    let minor: int

    func equals(self, other: Version) -> bool:
        return self.major == other.major and self.minor == other.minor

    func compare(self, other: Version) -> int:
        if self.major != other.major:
            return self.major - other.major
        return self.minor - other.minor

    func display(self) -> str:
        return f"{self.major}.{self.minor}"

pub func main(arguments: list[str]) -> int!:
    let versions = [Version(major = 1, minor = 10), Version(major = 1, minor = 2)]
    print(versions.sorted())
    print(Version(major = 1, minor = 2) < Version(major = 1, minor = 10))
    return 0
```

```output
[1.2, 1.10]
true
```

`compare` answers a negative number, zero or a positive number for less, equal and greater.
`Ordered` is always declared together with `Equatable`, so that "neither less nor greater"
and "equal" agree.

## Where next

[Chapter 9](09-projects-and-packages.md) moves from single files to projects: modules,
packages, dependencies and tests.

# 5. Structs and enums

## Structs

A struct is a type with named fields, much like a Python dataclass:

```luce
struct Point:
    var x: float
    var y: float = 0.0

    func moved(self, dx: float, dy: float) -> Point:
        return Point(x = self.x + dx, y = self.y + dy)

    func move(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    func origin() -> Point:
        return Point(x = 0.0, y = 0.0)

pub func main(arguments: list[str]) -> int!:
    let a = Point(x = 1.0, y = 2.0)
    let b = Point(3.0)
    print(a, b, Point.origin())
    print(a.moved(1.0, 1.0), a == Point(1.0, 2.0))
    return 0
```

```output
Point(x = 1.0, y = 2.0) Point(x = 3.0, y = 0.0) Point(x = 0.0, y = 0.0)
Point(x = 2.0, y = 3.0) true
```

- **Fields** are declared with `let` (never changes) or `var`, and a type. A field with a
  default can be left out when constructing.
- **Construction** is `Point(...)`, with the fields in order or by name. No `__init__` is
  needed.
- **Methods** take `self` first, as in Python. A function without `self`, like `origin`, is
  called on the type, `Point.origin()`, like a Python `@staticmethod`.
- **Equality and printing come for free**: two points are `==` when their fields are, and
  `print` shows the fields, like a dataclass's generated `__eq__` and `__repr__`.

## Structs are values

This is the main difference from Python, where every object is shared. A struct is a
*value*, like a number: assigning it or passing it to a function makes a copy, and changing
the copy leaves the original alone.

```luce
struct Point:
    var x: float
    var y: float

    func move(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

pub func main(arguments: list[str]) -> int!:
    let a = Point(x = 1.0, y = 2.0)
    var b = a
    b.move(1.0, 1.0)
    print(a, b)
    return 0
```

```output
Point(x = 1.0, y = 2.0) Point(x = 2.0, y = 3.0)
```

`move` changes the point it is called on, so it can only be called on a `var`: `a.move(1.0,
1.0)` is an error, since `a` is a `let`, and a `let` struct never changes, fields included.
Luce works out which methods change `self`; you do not mark them.

Use a struct for data that is naturally a value: a point, a color, a date, a configuration.
For something with an identity that several parts of a program share and change, such as an
open document or a network connection, use a class, which [Chapter 6](06-classes.md)
covers.

## Enums

An enum is a type whose value is one of a fixed set of *cases*. Each case can carry its own
data:

```luce
enum Shape:
    circle(radius: float)
    rectangle(width: float, height: float)
    empty

    func area(self) -> float:
        return match self:
            .circle(radius) => 3.14159 * radius ** 2.0
            .rectangle(width, height) => width * height
            .empty => 0.0

pub func main(arguments: list[str]) -> int!:
    let shapes = [Shape.circle(radius = 1.0), .rectangle(width = 2.0, height = 3.0), .empty]
    for shape in shapes:
        print(shape, shape.area())
    return 0
```

```output
Shape.circle(radius = 1.0) 3.14159
Shape.rectangle(width = 2.0, height = 3.0) 6.0
Shape.empty 0.0
```

Python's `Enum` gives each case a fixed value; a Luce enum is closer to a small family of
dataclasses, one per case, of which a value is exactly one. A case is written
`Shape.circle(...)`, or just `.circle(...)` where the type is already known, as in the rest
of the list above.

`match` takes an enum apart. Each arm names a case and binds its data to names, `radius`
here, which the arm can use. **A `match` must handle every case**: if you add a `triangle`
case to `Shape`, every `match` that does not handle it becomes an error, which shows you each
place to update. Like structs, enums are values and are copied.

`match` also has a statement form, with a block for each arm in place of `=>`:

```luce
enum Command:
    move(steps: int)
    turn(degrees: int)
    stop

pub func main(arguments: list[str]) -> int!:
    let command = Command.move(steps = 3)
    match command:
        .move(steps):
            print(f"moving {steps} steps")
        .turn(degrees):
            print(f"turning {degrees} degrees")
        .stop:
            print("stopping")
    return 0
```

```output
moving 3 steps
```

## Where next

[Chapter 6](06-classes.md) introduces classes: objects that are shared rather than copied,
and how their memory is managed.

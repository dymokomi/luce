# Classes and memory

[Reference: Classes](../../luce.md#10-classes), [The runtime](../../RUNTIME.md).

## Classes

A class is a type whose values are shared objects with an identity, as every object in
Python is:

```luce
class Document:
    let title: str
    var dirty: bool = false
    var pages: list[str] = []

    func init(self, title: str):
        self.title = title

    func add_page(self, text: str):
        self.pages.append(text)
        self.dirty = true

    func untitled() -> Document:
        return Document("Untitled")

pub func main(arguments: list[str]) -> int!:
    let document = Document("Notes")
    let same = document
    same.add_page("first")
    print(document.dirty, document.pages, document is same)
    print(Document.untitled().title)
    return 0
```

```output
true [first] true
Untitled
```

### Construction

- **`init(self, ...)`** is the constructor, Python's `__init__`, and `Document("Notes")`
  calls it. A class has at most one `init`; other ways to make one are type functions
  returning the class, like `Document.untitled()`.
- **`init` must assign every field that has no default, exactly once**, and cannot pass
  `self` anywhere before it has. Fields with defaults get them before `init` runs.
- **A class without `init`** whose fields all have defaults is constructed with no
  arguments, `Document()`.
- **An `init` that can fail** is declared `-> unit!` and fails with `error` like any
  function; the construction then fails, and the half-made object is released without its
  `deinit` running.

```luce
let bad_path = ErrorCode.package(1)

class Config:
    let path: str

    func init(self, path: str) -> unit!:
        if path == "":
            error(bad_path, "a configuration needs a path")
        self.path = path

pub func main(arguments: list[str]) -> int!:
    let config = Config("") catch failure:
        print(failure.message)
        recover Config("default.toml")
    print(config.path)
    return 0
```

```output
a configuration needs a path
default.toml
```

### Fields and methods

A `let` field is assigned in `init` and never again. A `var` field can be assigned through
any reference to the object, and methods can always assign to `var` fields: unlike structs,
there is no restriction to `var` bindings, since `let` only fixes which object a name refers
to.

Python lets you add attributes to an object at any time; a Luce class has exactly the fields
it declares.

### No inheritance

Classes are *final*: a class cannot extend another, so there are no base classes, `super()`,
overriding or abstract classes. What inheritance is used for in Python is done in Luce by:

- **interfaces**, for several types that answer the same methods
  ([Interfaces](11-interfaces-and-generics.md));
- **composition**, a field holding the object whose behaviour you would have inherited;
- **enums**, for a closed family of variants.

### Identity, equality and display

`is` and `is not` compare identity. `==`, hashing and printing are not defined for a class
until it declares `Equatable`, `Hashable` or `Display`, since Luce cannot know whether two
objects with the same fields are "the same". In Python, `==` falls back to identity and
`print` to `<Document object at 0x...>`; Luce asks you to choose.

### Structs or classes?

| Use a struct when | Use a class when |
| --- | --- |
| the value is data: a point, a color, a date, a record | the object has an identity: a document, a window, a connection |
| copies should be independent | several parts of the program should see the same object change |
| it should be sent to a worker | it holds a resource to close, or must run code when destroyed |

Most Python classes that are mainly data become structs in Luce.

## Memory

You never allocate or free memory in Luce. Strings, collections, closures and class objects
are freed when nothing refers to them any more, as in Python.

Luce counts references, as CPython does, and frees an object **at the moment** its last
reference goes away. That moment is predictable:

- a binding releases its reference at the end of its block, or when it is reassigned;
- a field releases its value when it is reassigned or when its object is destroyed;
- a temporary, such as an object made inside an expression and not bound to a name, is
  released at the end of the statement that made it.

### `deinit`

A class can declare `deinit(self)`, which runs once, when the object is destroyed, as
Python's `__del__` does:

```luce
class Tracked:
    let name: str

    func init(self, name: str):
        self.name = name

    func deinit(self):
        print(f"{self.name} destroyed")

func work():
    let local = Tracked("local")
    print("working")

pub func main(arguments: list[str]) -> int!:
    work()
    var slot = Tracked("first")
    slot = Tracked("second")
    print(Tracked("temporary").name)
    print("end of main")
    return 0
```

```output
working
local destroyed
first destroyed
temporary
temporary destroyed
end of main
second destroyed
```

`deinit` takes no arguments, returns nothing, and cannot fail, start a worker, or store
`self` anywhere. After it runs, the object's fields are released, last declared first.

### Cycles

Two objects that refer to each other keep each other's count above zero: a parent that lists
its children, each child pointing back at its parent. Luce, like Python, runs a *cycle
collector* to find such groups when nothing outside them refers to them, and frees them.

```luce
class Parent:
    var children: list[Child] = []

    func deinit(self):
        print("parent destroyed")

class Child:
    let parent: Parent

    func init(self, parent: Parent):
        self.parent = parent

    func deinit(self):
        print("child destroyed")

func family():
    let parent = Parent()
    parent.children.append(Child(parent))
    print("family made")

pub func main(arguments: list[str]) -> int!:
    family()
    print("end of main")
    return 0
```

```output
family made
end of main
parent destroyed
child destroyed
```

The collector runs when enough possible cycles have accumulated, and when `main` returns, so
objects in a cycle are freed later than others, at a moment that depends on the rest of the
program. The back reference can be a plain field, as here; there is no need for weak
references to avoid leaks. Objects whose types cannot form a cycle, such as text, lists of
numbers, or classes whose fields hold only such values, are never examined by the collector.

### Weak references

`Weak(object)` holds a reference that does not keep the object alive, like Python's
`weakref.ref`. `get()` answers the object, or `none` once it has been destroyed:

```luce
class Window:
    let title: str

    func init(self, title: str):
        self.title = title

pub func main(arguments: list[str]) -> int!:
    var window: Window? = Window("main")
    let watcher = Weak(window else return 1)
    if let seen = watcher.get():
        print(f"still open: {seen.title}")
    window = none
    print(watcher.get() == none)
    return 0
```

```output
still open: main
true
```

Weak references are for caches and observer lists: things that should not keep what they
point to alive. A `Weak` is a value: copying it copies the reference. It has no display and
no equality.

## Closing resources

An object that holds a file, a socket or a window should be released at a point you choose,
not whenever its last reference happens to go. The convention is a `close()` method, and
`with` calls it at the end of a block ([Control flow](06-control-flow.md#with)):

<!-- fragment -->
```luce
with Connection("example.org") as connection:
    connection.send("hello")
```

A class that holds a resource should offer `close()`, and treat `deinit` as the safety net
for when nobody called it. Resources from Base packages, such as open files from
`luce-std`, already work this way ([Luce and Base](16-base.md#handles)).

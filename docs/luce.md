# Luce

## The application language of the Luce project

Luce is Python's ease with a compiler's guarantees: one integer, one float, text, values
that copy, classes that share, memory that manages itself, failure that is visible, and
nothing about machines. Everything about machines is Luce Base (`base.md`), the systems
language this compiler is written in and the only door to C. A Luce program reaches Base by
import, and it compiles to Base, so every backend, optimiser and target Base has is Luce's.

The language sentence:

> **Values copy. Classes share. Nothing is freed by hand. Failure is a type. The machine is
> a Base package away.**

The product sentence:

> **Readable like Python, checked like a compiler, fast like the systems language under it.**

This document is the complete contract of the language. `base.md` is the contract of the
language under it, and chapter 16 is the contract between the two. Where an implementation
and this document disagree, the document is right and the implementation is a bug; where
this document is silent, the behaviour is not promised.

## 1. Principles

**Eight concepts.** Every Luce program is made of bindings, functions and control, values,
classes, collections, failure, abstraction, and workers. Arrays, strings, files, sockets and
windows are types and libraries built from those; methods are functions inside a type;
closures are functions with an environment; iteration is an interface plus `for`; errors are
one value carried by `T!`; tests are registered fallible functions; packages are modules plus
a manifest. Nothing else is a concept.

**One number of each kind.** `int` is a 64-bit signed integer and `float` a 64-bit IEEE
double. There is no other width, no unsigned integer, no wrapping or saturating arithmetic,
and no bit operation. Code that needs them is Base code.

**The machine is elsewhere.** Luce has no pointer, span, fixed array, union, allocator,
`asm`, atomic, or foreign declaration. A Base package has all of them and exposes a Luce
program only the crossable types of chapter 16. This is what keeps Luce small: a need for
the machine is a reason to write a Base package, never a reason to add a feature.

**Memory is not the programmer's.** Objects are reference-counted and a cycle collector
reclaims what counting cannot, exactly Python's model. There is no word for allocation,
release, ownership or weakness in the language. Resources close with `with`.

**Failure is visible.** A function that can fail says so in its type, a caller handles it or
passes it on, and a violated rule is a trap with a source trace, never an exception.

**A feature enters only when it removes more complexity than it adds**, counting syntax,
semantics, the compiler, the runtime, diagnostics, tooling, documentation and what a
programmer must remember. When a need appears it is solved at the cheapest correct layer: a
diagnostic, a library, a tool, then the language.

**Two executions must agree.** The interpreter is the definition of behaviour, and the Base
the compiler emits must print the same bytes through every generator Base has. A feature is
not implemented until they agree on its programs and its traps.

## 2. Source text

### 2.1 Encoding

Source is UTF-8. A byte-order mark is accepted only at byte zero. NUL bytes, invalid UTF-8,
the Unicode bidirectional format characters (U+202A to U+202E and U+2066 to U+2069), and
characters confusable with ASCII punctuation are rejected with a diagnostic naming the line
and column. CRLF is normalised for parsing. These rules are base.md §3.1's.

Identifiers are ASCII: a letter or `_`, then letters, digits or `_`, at most 128 bytes. The
standalone `_` is the pattern wildcard. Unicode is fully supported inside text and comments.

### 2.2 Layout

A statement suite after `:` is either one simple statement on the same line or a newline
followed by a block indented by exactly four spaces. Type and interface bodies always use
the indented form. Tabs are rejected. A same-line suite holds no compound statement and no
second statement. Inside brackets, newlines and indentation do not count. A file may nest
suites, brackets and operators a hundred levels deep, and a chain of calls or operators
may be three hundred links long; deeper nesting is a diagnostic, never a crash.

```luce
if cached: return result

if image.width > maximum:
    let scale = maximum / image.width
    image.resize(scale)
```

### 2.3 Comments and documentation

`#` starts a comment to the end of the line. A run of `##` lines directly above a declaration
is its documentation, read by `luce doc`. A comment is never a directive.

### 2.4 Names and scope

Names are case-sensitive. Scope is static and lexical: a module, then a function, then each
suite. A name is visible from its binding to the end of its suite. Shadowing is an error: a
local may not reuse the name of another visible local, parameter, or top-level declaration,
and an import may not be shadowed. Conventions, enforced by `luce fmt` and warned by the
checker: `snake_case` for functions, bindings and fields; `CapitalCase` for types and enum
cases; `UPPER_CASE` for nothing.

The core names are reserved everywhere and cannot be declared at any level: `assert`,
`discard`, `error`, `hash`, `print`, `trap`, `int`, `float`, `bool`, `str`, `bytes`, `unit`,
`never`, `list`, `map`, `set`, `Error`, `ErrorCode`, `Weak`, `task`.

### 2.5 Reserved words

```text
and as break catch class continue elif else enum false for from func if import in
interface is let match none not or pub recover return self spawn struct test true try
type var wait while with
```

`init`, `deinit`, `close`, and `main` are ordinary names with a meaning in one position each.

## 3. Literals

### 3.1 Boolean and absence

`true`, `false`, and `none`. `none` takes its optional type from context and is never a
universal null.

### 3.2 Numbers

```luce
let count = 42
let mask = 1_000_000
let hex = 0xFF
let ratio = 0.5
let large = 6.022e23
```

An integer literal is an `int` and a literal with a point or an exponent is a `float`. There
are no suffixes and no other widths. Underscores separate digits; based prefixes `0x`, `0o`
and `0b` are lowercase. A literal outside its type's range is a compile error. `-` before a
literal is negation, and `-9223372036854775808` is accepted.

### 3.3 Text and bytes

```luce
let name = "Ada"
let path = r"C:\temp"
let greeting = f"hello {name}, you are {age + 1}"
let block = """
    two lines
    of text
    """
let data = b"\x00\x01"
```

A `str` literal is UTF-8 with the escapes `\\ \" \n \r \t \0 \u{HEX}`. A raw literal `r"..."`
has no escapes. A formatted literal `f"..."` interpolates any expression whose type has a
display (§10.5); a format spec after `:` is not part of the language and a `{` is written
`{{`. A triple-quoted literal strips the common indentation of its lines. A `bytes` literal
`b"..."` admits `\xNN` and is the only place a byte is spelled.

There is no character literal: a text of one scalar is a `str` of length one.

### 3.4 Collections

```luce
let primes = [2, 3, 5, 7]
let ages = {"Ada": 36, "Grace": 45}
let seen = {1, 2, 3}
let empty_map: map[str, int] = {}
let empty_list: list[str] = []
```

`[...]` is a `list`, `{k: v, ...}` a `map`, `{v, ...}` a `set`; `{}` is an empty map. The
element type comes from context or from the elements, which must agree. A literal creates a
new collection each time it is evaluated.

### 3.5 Tuples

`(1, "one")` is a tuple; `(1,)` is a tuple of one; `()` is `unit`.

## 4. Types

### 4.1 Scalars

| Type | Values |
| --- | --- |
| `int` | signed 64-bit integers; arithmetic traps on overflow (§6.2) |
| `float` | IEEE binary64 |
| `bool` | `true`, `false` |
| `str` | immutable UTF-8 text with value semantics |
| `bytes` | immutable byte sequence with value semantics |
| `unit` | the one value `()` of a function that returns nothing |
| `never` | the type of an expression that does not produce a value: `return`, `trap`, `error` |

There is no implicit conversion between any two of these. `int(x)`, `float(x)`, `str(x)` and
`bool(x)` convert explicitly (§6.5).

### 4.2 Composite types

| Spelling | Meaning |
| --- | --- |
| `(A, B)` | tuple, a value |
| `struct Name` | a named value with fields (§9.1) |
| `enum Name` | a closed set of cases, each with an optional payload (§9.2) |
| `class Name` | a shared object with identity (§10) |
| `list[T]`, `map[K, V]`, `set[T]` | mutable collections with identity (§11) |
| `T?` | `T` or `none` (§12.1) |
| `T!` | `T` or an `Error` (§12.2) |
| `func(A, B) -> R` | a function value, possibly a closure (§7.4) |
| `interface Name` | a capability a type declares it has (§13) |
| `task[T]` | a running worker's future result (§14) |
| `Weak[T]` | a non-owning reference to a class instance (§10.4) |

A type name is resolved in the module's scope. `type Name = Type` declares an alias, which is
the same type. Every type has a spelling `luce explain` can print.

### 4.3 Inference

Inference is local. A binding takes its type from its initialiser; a call's type arguments
come from its arguments; a literal takes its type from the context it sits in, and defaults
to `int`, `float`, `str`, `list[T]` of its elements. Signatures are always written: a
function's parameters and result never infer from the body. `T?` and `T!` are written where
they are meant and never inferred from a `none` or an `error`.

### 4.4 Equality, ordering and hashing

Every value type has `==` and `!=` by structure: scalars, `str`, `bytes`, tuples, structs
whose fields have it, enums whose payloads have it, optionals of it, and collections of it.
`<`, `<=`, `>`, `>=` are defined for `int`, `float`, `str` (scalar-value order, not locale),
`bytes`, and tuples of those, and for a struct that declares `Ordered` (§13.3). `hash` is
defined for every equatable value, consistently with `==`, and is the same number in every
execution (`docs/RUNTIME.md` states the function). Classes have identity, not
equality: `is` and `is not` compare identity, and `==` on a class is an error unless it
declares `Equatable` (§13.3).

### 4.5 Recursion

A struct or enum may not contain itself by value. A class may refer to itself through any
field, and a struct or enum may contain a class or a collection of itself.

## 5. Bindings

### 5.1 `let` and `var`

```luce
let limit = 10
var count = 0
count += 1
let point: Point = Point(x = 1.0, y = 2.0)
```

`let` binds once and cannot be assigned again. `var` may be assigned again with a value of
the same type. Every binding has an initialiser; there is no uninitialised variable and no
zero value. A binding's type may be written after `:`, and must be when the initialiser is
`none`, `[]` or `{}`.

A `let` of a class or collection prevents rebinding, not mutation: the object is shared and
its `var` fields and its elements change through any binding. A `let` of a struct is
immutable through and through.

### 5.2 Tuples and destructuring

```luce
let (quotient, remainder) = divide(17, 5)
let (name, _) = pair
```

A tuple destructures into as many bindings as it has members; `_` discards one.

### 5.3 Assignment

`=` assigns a `var`, a `var` field through any path, an element of a list or map, or a tuple
of those from a tuple. `+=`, `-=`, `*=`, `/=`, `//=`, `%=` read then write once. The place is
evaluated before the value.

## 6. Expressions

### 6.1 Evaluation order

Operands, arguments and elements evaluate left to right, once. `and` and `or` short-circuit.
A conditional expression evaluates only the arm it picks.

### 6.2 Arithmetic

| Operator | On `int` | On `float` |
| --- | --- | --- |
| `+ - *` | checked: overflow traps | IEEE |
| `/` | a `float` quotient, as Python's | IEEE |
| `//` | floor division; by zero traps | floor division |
| `%` | remainder with the divisor's sign, as Python's; by zero traps | IEEE remainder |
| `**` | checked power with an `int` exponent that is not negative | `float` power |
| unary `-` | checked | IEEE |

`int` and `float` never mix in one operation: `count * 1.5` is an error and is written
`float(count) * 1.5`. There is no bit operation, shift, wrapping or saturating form; a
program that needs them calls a Base package.

### 6.3 Comparison and logic

`== != < <= > >=` produce `bool` by §4.4 and do not chain. `and`, `or`, `not` take `bool`
only: an `int`, a `str` or an optional is never a condition by itself. `x in collection` is
membership: an element of a list or set, a key of a map, a substring of a `str`.

### 6.4 Conditional expression

`a if condition else b`, with both arms of one type.

### 6.5 Conversions

| Call | Meaning |
| --- | --- |
| `int(f)` | truncates a `float` toward zero; traps on NaN or out of range |
| `int(s)` | parses a `str` as a decimal integer; `int!` |
| `float(i)` | the nearest `float` |
| `float(s)` | parses a `str`; `float!` |
| `str(x)` | the display of any value with one (§10.5) |
| `bool(x)` | only from `str`: `"true"` or `"false"`, else fails |

There is no cast. A conversion is a call, and one that can fail says so.

### 6.6 Members, calls, indexing, slicing

`value.field`, `value.method(args)`, `Type.function(args)`, `callable(args)`, `list[i]`,
`map[key]`, `list[a..<b]`, `text[a..<b]`. Indexing a list with an `int` out of range traps;
reading `map[key]` yields `V?`; a slice of a list or a `str` is a copy (§11). Ranges `a..<b`
and `a..=b` are values of type `range` that iterate `int`s.

### 6.7 Precedence

From tightest: member, call, index; unary `-`; `**`; `* / // %`; `+ -`; `..<` `..=`; `in`,
`is`, `is not`, comparisons; `not`; `and`; `or`; `if`-`else`; `=>`; assignment. `not` sits
below the comparisons so that `not a == b` negates the comparison, as in Python.

## 7. Functions

### 7.1 Declaration

```luce
func area(width: float, height: float = 1.0) -> float:
    return width * height

func log(message: str):
    print(message)
```

Parameters are `let` bindings. A result type after `->`; none means `unit`. A default is a
constant expression or a constructor of one. Every path through a function with a result
returns a value; the compiler proves it. A function may be recursive.

### 7.2 Calls

```luce
let a = area(2.0, 3.0)
let b = area(width = 2.0)
let c = area(2.0, height = 3.0)
```

Arguments are positional, then named; a named argument names a parameter once; a parameter
with a default may be omitted. There is no overloading and no variadic parameter; a function
that wants any number of things takes a `list`.

### 7.3 Methods

A function declared inside a struct, enum or class is a method; its receiver is `self`. A
method of a struct that assigns to a field of `self` is a mutating method, and may be called
only on a `var`; the compiler infers this, nothing is written. A method of a class may always
assign to `var` fields. A function declared inside a type without `self` in its body and
called through the type, `Point.origin()`, is a type function.

### 7.4 Function values, lambdas and closures

```luce
let positive: func(int) -> bool = (n) => n > 0
let doubled = numbers.map((n) => n * 2)

let counter = func () -> int:
    count += 1
    return count
```

A named function, a method bound to a receiver, and a lambda are values of a function type.
`(params) => expression` is an expression lambda whose parameter types come from the expected
function type; `func (params) -> R:` with a suite is a block lambda with everything written.
A lambda that refers to an outer local captures it: a `let` value is copied, an object is
shared, and a `var` becomes one cell shared by the scope and every closure that captures it,
so a captured counter counts. Closures may be stored, returned and passed anywhere a function
value is expected, and live as long as the last reference to them.

## 8. Control flow

### 8.1 `if`, `elif`, `else`

```luce
if n < 0:
    sign = -1
elif n == 0:
    sign = 0
else:
    sign = 1
```

### 8.2 Conditional binding

```luce
if let user = find(users, id):
    greet(user)
else:
    print("no such user")

while let line = reader.next():
    process(line)
```

`if let` and `while let` bind the payload of a `T?` when it is present.

### 8.3 `while`, `for`

```luce
for i in 0..<10:
    print(i)
for name in names:
    print(name)
for (index, name) in names.indexed():
    print(f"{index}: {name}")
for (key, value) in ages:
    print(f"{key} is {value}")
for character in "héllo":
    print(character)
```

`for` iterates a range, a list, a set, a map (as key-value tuples), a `str` (as one-scalar
strings), `bytes` (as `int`s 0 to 255), or any value of a type that declares `Iterable`
(§13.3). `break` and `continue` apply to the innermost loop; a loop may be labelled,
`outer: for ...`, and `break outer` leaves it. Structurally mutating a collection while a
`for` runs over it traps.

### 8.4 `match`

```luce
match shape:
    .circle(radius):
        return 3.14159 * radius ** 2
    .rectangle(width, height):
        return width * height
    .empty:
        return 0.0

let word = match n:
    0 => "zero"
    1..<10 => "digit"
    _ if n < 0 => "negative"
    _ => "many"
```

`match` is exhaustive over an enum's cases, and over anything else with `_` or a name.
Patterns are enum cases with bound payloads, literals, ranges, tuples of patterns, `none`, a
name, which binds the whole value or the payload of an optional that is present, and `_`,
each with an optional guard. The statement form has suites; the expression form has `=>` arms of
one type.

A match expression over a tuple or over `bytes` reads its subject in every arm, so the
subject is a name, a literal, or a tuple of those, and its arms bind no names; bind the
value or use the statement form otherwise.

### 8.5 `return`, `defer`-less cleanup, `with`

`return` leaves the function with a value. There is no `defer`. A resource is closed by
`with`:

```luce
with files.open(path) as file:
    for line in file.lines():
        process(line)
```

`with expression as name:` binds the value, runs the suite, and calls `name.close()` when
the suite ends, however it ends: normally, by `return`, by `break`, or by a failure passing
through. Any value whose type has a `close()` method returning `unit` may be used; a Base
handle (§16.4) always has one. `with` may bind several, `with a as x, b as y:`, closed in
reverse order.

## 9. Values

### 9.1 Structs

```luce
struct Point:
    var x: float
    var y: float

    func distance(self, other: Point) -> float:
        return ((self.x - other.x) ** 2.0 + (self.y - other.y) ** 2.0) ** 0.5

    func moved(self, dx: float, dy: float) -> Point:
        return Point(x = self.x + dx, y = self.y + dy)

let origin = Point(x = 0.0, y = 0.0)
var p = origin
p.x = 5.0
```

A struct is a value: assignment and passing copy it, and the copy is independent. Its fields
are `let` or `var`, and a `var` field may be assigned through a `var` binding. Construction
is memberwise, `Point(x = 0.0, y = 0.0)`, positional or named; a field with a default may be
omitted. A struct with a custom `init(self, ...)` is constructed through it instead. Structs
have structural `==` and `hash` when their fields do, and a display when their fields do.

### 9.2 Enums

```luce
enum Shape:
    circle(radius: float)
    rectangle(width: float, height: float)
    empty

let s = Shape.circle(radius = 2.0)
let t: Shape = .empty
```

An enum is a closed set of cases, each with an optional named payload. Cases are constructed
through the type or, where the type is known, with a leading `.`. Enums are values, with
structural equality and hashing when their payloads have them. An enum may declare methods.
There is no integer-backed enum in Luce; one that must cross to Base is declared in Base.

### 9.3 Tuples

`(1, "one")` is a value of type `(int, str)`; members are `.0`, `.1`, or destructured. Tuples
have structural equality and ordering.

### 9.4 Optionals and results as values

`T?` and `T!` are values wherever `T` is (§12).

## 10. Classes

### 10.1 Declaration and construction

```luce
class Document:
    let title: str
    var dirty: bool = false
    var pages: list[Page] = []

    func init(self, title: str):
        self.title = title

    func append(self, page: Page):
        self.pages.append(page)
        self.dirty = true

let document = Document("Notes")
```

A class is a shared object: assignment and passing share it, and it lives while anything
refers to it. Construction is `Name(args)`, the same spelling as a struct; the declaration,
not the use, says which is which. A class has one `init(self, ...)`, which assigns every
field without a default exactly once before it ends and cannot publish `self` before that;
`init` may be `!` when construction can fail, and then construction is `try Name(args)`. A
class without an `init` and with defaults for every field is constructed with no arguments.
Classes are final: no inheritance, no override, no base class. Alternative construction is a
type function returning the class, `Document.from_file(path)`.

### 10.2 Identity and mutation

```luce
let first = Document("Draft")
let second = first
second.dirty = true
assert(first.dirty)
assert(first is second)
```

`is` and `is not` compare identity. `==` is not defined for a class unless it declares
`Equatable`. A `let` field is assigned in `init` and never again; a `var` field is assigned
through any binding of the object.

### 10.3 Lifetime

Nothing in the language allocates, retains, releases or frees; the compiler and the runtime
do. An object is destroyed when the last reference to it goes away, deterministically: a
binding releases its reference when it leaves its scope or is reassigned, a field when it is
reassigned or its owner is destroyed, and an object that no binding took, the result of a
call or a construction inside an expression, at the end of the statement that produced it.
A cycle of objects that nothing else refers to is reclaimed by the runtime's cycle
collector, which runs at the end of the program and periodically before; `docs/RUNTIME.md`
states the exact order.
A class may declare `deinit(self)`, run once at destruction, taking no arguments, returning
`unit`, unable to fail, spawn, or publish `self`. Fields are then released in reverse
declaration order. A class that holds a resource also offers `close()`, so that `with` can
close it on time; `deinit` is the safety net.

### 10.4 Weak references

`Weak[T]` is a library type holding a non-owning reference to a class instance: `Weak(object)`
makes one and `.get()` yields `T?`, `none` once the object is gone. A `Weak` is a value:
copying it copies the reference, and it has no display and no equality. It is for observer
lists and caches. An ordinary back edge, a child's parent, may be a plain field; the
collector handles the cycle.

### 10.5 Display

Every scalar, `str`, `bytes`, tuple, struct and enum of displayable members, optional, and
collection of displayable elements has a display used by `print`, `str(x)` and f-strings. A
class or struct may declare its own by conforming to `Display` (§13.3). `print(x)` writes the
display and a newline to standard output; `print(a, b)` separates with a space.

## 11. Collections and text

### 11.1 `list[T]`

`list` is a growable ordered collection with identity: two bindings of one list are the same
list, `is` says so, and `.copy()` makes an independent shallow copy. Indexing is checked.

| Operation | Meaning |
| --- | --- |
| `length` | a property, O(1) |
| `values[i]`, `values[i] = x` | get and set; `i` out of range traps; negative indexes count from the end |
| `values[a..<b]`, `values[a..]`, `values[..<b]` | a new list of the elements; bounds checked |
| `append(x)`, `insert(i, x)`, `remove_at(i) -> T`, `pop() -> T`, `clear()` | shape changes |
| `first`, `last` | `T?` |
| `contains(x)`, `index_of(x) -> int?` | search, `x` equatable |
| `sort()`, `sorted()`, `reverse()`, `reversed()` | in place and as a copy; elements ordered |
| `map(f)`, `filter(f)`, `join(separator)` | with a function value; `join` on `list[str]` |
| `a + b` | a new list of both |
| `copy()` | a shallow copy |

### 11.2 `map[K, V]` and `set[T]`

Maps and sets have identity, keep insertion order, and require equatable and hashable keys.
`m[key]` is `V?`; `m[key] = v` inserts or replaces; `m.remove(key) -> V?`; `key in m`;
`m.keys()`, `m.values()`, `m.items()` iterate. `s.insert(x)`, `s.remove(x) -> bool`,
`x in s`, `s.union(t)`, `s.intersection(t)`, `s.difference(t)`. Both have `length`,
`clear()`, `copy()`.

### 11.3 `str`

`str` is immutable UTF-8 with value semantics and content equality.

| Operation | Meaning |
| --- | --- |
| `length` | scalars, O(n); `byte_count` is O(1) |
| `a + b`, `f"..."` | concatenation and formatting |
| `text[a..<b]` | a substring by scalar index; bounds checked |
| `for c in text` | one-scalar strings |
| `contains`, `starts_with`, `ends_with`, `index_of -> int?` | search |
| `split(separator) -> list[str]`, `lines()`, `trim()`, `upper()`, `lower()`, `replace(a, b)`, `repeat(n)` | the common transforms |
| `bytes()` | the UTF-8 as `bytes` |

`split(separator)` cuts at every occurrence of a non-empty separator, keeping empty pieces,
so `"a,,b".split(",")` is `["a", "", "b"]`; an empty separator traps. `lines()` cuts at
`"\n"`, drops a `"\r"` before it, and a trailing newline ends the last line rather than
opening an empty one. `trim()` removes spaces, tabs and newlines at both ends; `upper()`
and `lower()` map the ASCII letters; `replace(a, b)` replaces every non-overlapping
occurrence left to right and traps on an empty `a`; `repeat(n)` traps on a negative `n`.
Normalisation, grapheme segmentation, collation and locale are library operations.

### 11.4 `bytes`

Immutable, with `length`, `data[i]` as an `int` 0 to 255, slicing, `+`, equality, and
`text()`, which decodes UTF-8 and is `str!`, failing with the message `invalid UTF-8`. Bytes are what a Base package hands a Luce
program when the data is not text; a Luce program does not compute on bytes, it passes them.

## 12. Absence and failure

### 12.1 Optionals

```luce
let found: User? = find(users, id)
let name = found.name if found != none else "nobody"
let user = find(users, id) else return
let count = counts[key] else 0
```

`T?` holds a `T` or `none`. It is read with `if let`, `while let`, `match`, or `else`, whose
fallback is a `T`, a `return`, or an `error`. There is no force unwrap and no `T??`.
Comparison with `none` is allowed; nothing else reads through an optional.

### 12.2 Results

```luce
func parse(text: str) -> Config!:
    if text == "":
        error(bad_input, "empty configuration")
    return Config(...)

let config = try parse(text)
let config2 = parse(text) catch failure:
    recover default_config()
let config3 = parse(text) catch failure:
    if failure.code == bad_input:
        recover default_config()
    error(failure.code, f"cannot load: {failure.message}")
```

`T!` holds a `T` or an `Error`. `try` unwraps in a function whose own result is `!`,
passing the failure up. `catch failure:` handles it in a suite that must end in `recover
value`, `return`, or `error`. `error(code, message)` fails the current function, which must
be `!`. A `T!` cannot be ignored: it is tried, caught, or bound to a `!` variable.

### 12.3 Errors

`Error` has a `code: ErrorCode` and a `message: str`. Codes are declared as constants,
`let bad_input = ErrorCode.package(3)`, unique within a package by the package's name, so
codes from two packages never collide. A Base package's errors cross unchanged (§16.3).

### 12.4 Traps

A trap ends the program with a message and a source trace, and cannot be caught: `int`
overflow, division by zero, an index out of range, an `int(x)` that does not fit, an
`assert` that fails, a mutation during iteration, a `trap("message")`, and out of memory.
`assert(condition)` and `assert(condition, "message")` stay in every build.

## 13. Interfaces and generics

### 13.1 Interfaces

```luce
interface Shape:
    func area(self) -> float
    func name(self) -> str

struct Circle: Shape:
    var radius: float

    func area(self) -> float:
        return 3.14159 * self.radius ** 2.0

    func name(self) -> str:
        return "circle"
```

An interface is a set of method signatures. A struct, enum or class declares its conformance
at its declaration, `: Shape`, and provides every method with the exact signature. A struct's
or enum's method for a requirement does not change `self`: an interface value is read
through the interface, never changed through it. There are no default methods, no
inheritance between interfaces beyond listing several, no associated types, and no downcast
from an interface value to a concrete type.

### 13.2 Interface values and generics

```luce
func total(shapes: list[Shape]) -> float:
    var sum = 0.0
    for shape in shapes:
        sum += shape.area()
    return sum

func largest[T: Ordered](values: list[T]) -> T?:
    ...

func show_sorted[T: Ordered & Display](values: list[T]) -> str:
    ...
```

A value of a conforming type converts to an interface value where one is expected: a copy
of the value behind the interface, with the ownership of a value (§10.5, `docs/RUNTIME.md`),
so a class behind it lives while any copy of the interface value does. A call dispatches to
the value's own method; an interface value has no `==`, no ordering, no hash and no display
of its own, and an optional of one is compared with `none` like any optional. A generic
function takes type parameters in `[...]`, each optionally bounded by interfaces joined
with `&`, and is checked once against its bounds; inside it, a value of a parameter type
has the bounds' methods, `==` with `Equatable`, `<` with `Ordered`, `hash` with `Hashable`,
display with `Display`, and the operations every type has: it is bound, passed, returned,
and held in tuples, optionals and collections. Type arguments are inferred from the
arguments, those given to a parameter of a bare parameter type first, or written,
`largest[int](values)`; each must satisfy its bounds. The program gets one instance of the
function per distinct type arguments; a generic function is called, never read as a value,
and a method has no type parameters of its own.

A struct, enum, class or interface takes type parameters the same way, `struct Pair[A, B]`,
`enum Option[T]`, `class Stack[T]`, `interface Container[T]`, and `Pair[int, str]` names
an instance, a type of its own with the parameters replaced. A construction infers the
arguments from the expected type or from the values given to the fields, `init` or the
case's payload, `Pair(first = 1, second = "one")`; `Option.empty` needs the expected type
known or the arguments written, `Option[int].empty`; a class with an `init` taking no
value that fixes a parameter is written `Stack[int]()`. An instance displays as
`Pair(first = 1, second = one)`, its generic name; a bound may name an instance,
`[I: Iterable[int]]`.

### 13.3 The closed protocols

The compiler knows these interfaces, and syntax uses them:

| Interface | Methods | Used by |
| --- | --- | --- |
| `Equatable` | `equals(self, other: Self) -> bool` | `==`, `!=`, `in`, keys |
| `Hashable` | `hashed(self) -> int` with `Equatable` | map keys, set elements |
| `Ordered` | `compare(self, other: Self) -> int` | `<` and friends, `sort` |
| `Display` | `display(self) -> str` | `print`, `str(x)`, f-strings |
| `Iterable[T]` | `iterator(self) -> Iterator[T]` | `for` |
| `Iterator[T]` | `next(self) -> T?` | `for`, `while let` |

Values get `Equatable`, `Hashable`, `Ordered` and `Display` structurally as §4.4 and §10.5
say; a type declares one only to replace the structural meaning, and a class must declare
them to have them at all. `for x in v` over a value declaring `Iterable[T]` calls
`v.iterator()` once and `next()` before every pass until it answers `none`; the iterator
is a class, since a struct's method for a requirement may not change `self` (§13.1), and
`while let x = it.next()` walks it by hand. A closed protocol names what a type declares, never a value's
type: `let e: Equatable = x` is an error, and no program may declare one itself. A type that
declares `Equatable` keys a map or sits in a set only when it declares `Hashable` beside
it, so its hash agrees with its `equals`; `Hashable` and `Ordered` are declared beside
`Equatable`, never alone. A value with a declared `hashed` hashes as the `int` it returns
(`docs/RUNTIME.md`).

## 14. Workers

```luce
let work = spawn render(scene)
let other = spawn render(other_scene)
let (a, b) = (wait work, wait other)
```

`spawn f(args)` starts `f` on another worker with copies of its arguments and yields a
`task[T]`; `wait task` yields its result, or its failure if `f` is `!`. Arguments and results
are sendable: scalars, `str`, `bytes`, tuples, structs and enums of sendable members,
optionals and results of them, and copies of collections of them. A class instance, a
closure, or a collection identity never crosses. `f` is a named function of the program,
never a method, a closure or a Base function. A task is bound and waited, once, by the
function that spawned it: it is not stored in a field or a collection, returned, or
captured. A worker's tasks are waited before the function that spawned them returns; a
failure or a `return` cancels the rest, whose results are discarded when they end.
Workers share nothing, so there are no locks and no races in the language; what a worker
prints interleaves with other output in an order the program does not fix, and the
interpreter runs each task when it is spawned.

## 15. Modules and packages

### 15.1 Files and modules

One `.luc` file is one module; its path under the package's source root is its name:
`src/image/color.luc` is `image.color`. A file's name is an identifier. A `.lucb` file in the
same package is a Base module (§16). Module cycles are errors. The source root is the one the
package's manifest names (§15.5); a program run without a manifest has its entry module's
directory as the root and `app` as its package name.

### 15.2 Imports and visibility

```luce
import image.color
import data.serialization as serial
from image.geometry import Point, Size
```

`import` keeps a module qualified, with an optional alias; `from ... import` brings the named
public declarations in. Imports come first and are used; a name is imported once and never
declared beside its import. Declarations, fields and methods are private to their module
unless `pub`: a `pub` type with no `pub` member can be named and passed but not read or
called from another module. A public signature mentions only public types. A module's name
is read only to reach a member, `shapes.origin`, `shapes.Point`; the closed protocols
(§13.3) are visible in every module without an import.

### 15.3 Top level

A module contains imports, then `struct`, `enum`, `class`, `interface`, `type`, `func`,
`test`, and `let` constants. A top-level `let` is a constant expression: literals, arithmetic,
tuples, enum cases, and constructors of structs of those. There is no module initialisation
and no global `var`; mutable state lives in an object the program constructs.

### 15.4 Entry point

```luce
pub func main(arguments: list[str]) -> int!:
    return 0
```

### 15.5 Packages

A package is a directory with a `luce.toml` naming the package, its source root, its tests,
and its dependencies exactly. There is no build script and no network during a build. The
manifest is the same document for the Base modules the package contains.

```toml
[package]
name = "demo"
source = "src"
```

`name` is the package's identity (§12.3); `source` is the root the modules are named
from, `src` unless written. The nearest manifest above the entry module is the program's.

## 16. The Base boundary

### 16.1 What a Luce module sees of a Base module

A Luce module imports a Base module by the same `import`, a `.lucb` file under the source
root. It sees the module's `pub` functions, `pub let` constants, `pub` structs and
integer-backed enums whose fields are crossable, and `pub handle` types, through the
description luce-base prints for the module (base.md §17.7): the compiler never parses
Base. It does not see pointers, spans, arrays, unions, atomics, `c` types, `extern`
declarations, generic declarations, or any function, constant or struct whose signature
mentions one of those: those are the Base package's own, and the package writes the
function a Luce program can call. A program that imports a Base module is built; the
interpreter runs Luce alone and refuses it (§17.1).

### 16.2 Crossable types

| Luce | Base | Crossing |
| --- | --- | --- |
| `int` | `i64` | by value |
| `float` | `f64` | by value |
| `bool` | `bool` | by value |
| `str` | `str` | lent as Base's view of the bytes; a Base result is copied into an owned `str` |
| `bytes` | `const u8[]` | lent; a Base result is copied |
| `list[T]` of `int`, `float`, `bool` or `str` | `const T[]` | lent as a span over the elements (texts as views that live to the end of the statement), never kept by Base; a Base span never crosses back |
| struct of crossable fields | the same struct, declared in Base | by value |
| integer-backed `enum` declared in Base | that enum | by value |
| `T?` | `T?` | by value |
| `T!` | `T!` | the code and the message |
| `func(A) -> R` of scalars, `str` and `bytes` answering a scalar or nothing | `func(A) -> R` | a named function, never a closure; Base calls a thunk that copies the texts for the call |
| handle | `pub handle` | as an object (§16.4) |

Nothing else crosses in either direction. A `usize` in Base is an `int` in Luce and a
negative or oversized value traps at the crossing. A Base enum value that names no
declared case traps as it crosses.

### 16.3 Errors and traps

A Base `T!` failing is a Luce failure with the same code and message. A Base trap is a Luce
trap. A Base function that returns `unit` returns `unit`.

### 16.4 Handles

```luce
# in base: files.lucb
pub handle File:
    destroy close

pub func open(path: str) -> File!: ...
pub func read_line(file: File) -> str?: ...
```

```luce
# in luce
with files.open(path) as file:
    while let line = files.read_line(file):
        print(line)
```

A Base module declares a `handle` for a resource it owns: a pointer-sized value whose
`destroy` names the Base function that releases it. A Luce program sees the handle as a class
with identity, no fields, and a `close()` that calls `destroy` once; the runtime calls it at
the last reference if the program did not. A handle is never constructed in Luce, only
answered by the module's functions; a closed handle handed back to Base traps. Every
file, socket, window, texture and device is a handle behind a Base package, and this one
form is all Luce knows about resources.

### 16.5 What Base sees of Luce

Nothing. A Base module cannot name a Luce declaration, call a Luce function, or hold a Luce
object; a callback into Luce is a capture-free Luce function passed as a function value.

## 17. Tooling

### 17.1 The command

| Command | Does |
| --- | --- |
| `luce run program.luc` | runs it in the interpreter, the definition of behaviour; a program importing a Base module (§16) is refused, since the interpreter runs Luce alone |
| `luce build program.luc -o name` | emits a Base package and compiles it with Base's compiler; `--emit=base` keeps the package |
| `luce check`, `luce test`, `luce fmt`, `luce doc`, `luce explain` | as named |

### 17.2 Diagnostics

Every diagnostic is `file:line:column: message`, one per line, the first one first, and a
rejection exits with status 1. A crash, a hang, or a message without a position is a
compiler bug. The interpreter and the emitted Base trap with the same message and the Luce
position, which the emitted Base carries through base.md's position directive.

### 17.3 Tests

```luce
test "parsing an empty document fails":
    let result = parse("")
    assert(result is_error)
```

A `test` is a registered function that runs under `luce test` and never in a build. It may
`try`, `assert`, and `error`; a test that fails or traps is reported with its name and
position.

## 18. Deliberate exclusions

Not in Luce, with the reason: integer widths and unsigned integers (one number of each kind);
bit operations, shifts, wrapping and saturating arithmetic (Base); `char` (a scalar is a
`str` of one); fixed arrays, slices as views, unions, pointers, spans, atomics, `asm`,
allocators, `defer`, `new`, `free`, `weak` as a word (memory is not the programmer's);
inheritance, overloading, variadics, default interface methods, associated types, downcasts
(one way to do each thing); exceptions, force unwrap, nullable-by-default (failure is
visible); `extern`, `cfunc`, C++ bridges, an audited tier (the machine is a Base package);
macros, reflection, conditional compilation, build scripts (the language is the language).

## 19. Grammar summary

```text
module      = {import} {declaration}
import      = "import" path ["as" NAME] | "from" path "import" NAME {"," NAME}
declaration = ["pub"] (func | struct | enum | class | interface | alias | constant | test)
func        = "func" NAME [generics] "(" [params] ")" ["->" type] ":" suite
struct      = "struct" NAME [generics] [":" NAME {"," NAME}] ":" NEWLINE INDENT {field | func} DEDENT
class       = "class" NAME [generics] [":" NAME {"," NAME}] ":" NEWLINE INDENT {field | func} DEDENT
enum        = "enum" NAME [generics] [":" NAME {"," NAME}] ":" NEWLINE INDENT {case | func} DEDENT
interface   = "interface" NAME [generics] ":" NEWLINE INDENT {signature} DEDENT
field       = ("let" | "var") NAME ":" type ["=" expression]
case        = NAME ["(" params ")"]
alias       = "type" NAME "=" type
constant    = "let" NAME [":" type] "=" expression
test        = "test" STRING ":" suite
params      = param {"," param}           param = NAME ":" type ["=" expression]
generics    = "[" generic {"," generic} "]"     generic = NAME [":" NAME {"&" NAME}]
type        = path ["[" type {"," type} "]"] | "(" [type {"," type}] ")"
            | "func" "(" [type {"," type}] ")" ["->" type] | type "?" | type "!"
suite       = simple NEWLINE | NEWLINE INDENT {statement} DEDENT
statement   = simple NEWLINE | if | while | for | match | with
simple      = binding | assignment | expression | "return" [expression] | "break" [NAME]
            | "continue" [NAME] | "recover" expression | "error" "(" expression "," expression ")"
binding     = ("let" | "var") (NAME | "(" NAME {"," NAME} ")") [":" type] "=" expression
if          = "if" (expression | "let" NAME "=" expression) ":" suite
              {"elif" ... ":" suite} ["else" ":" suite]
while       = [NAME ":"] "while" (expression | "let" NAME "=" expression) ":" suite
for         = [NAME ":"] "for" (NAME | "(" NAME {"," NAME} ")") "in" expression ":" suite
match       = "match" expression ":" NEWLINE INDENT {pattern ["if" expression] ":" suite} DEDENT
with        = "with" expression "as" NAME {"," expression "as" NAME} ":" suite
expression  = lambda | conditional
lambda      = "(" [params] ")" "=>" expression | "func" "(" [params] ")" ["->" type] ":" suite
conditional = or ["if" or "else" expression]
or          = and {"or" and}             and = not {"and" not}       not = "not" not | compare
compare     = range [("==" | "!=" | "<" | "<=" | ">" | ">=" | "in" | "is" | "is" "not") range]
range       = add [("..<" | "..=") add]
add         = mul {("+" | "-") mul}       mul = unary {("*" | "/" | "//" | "%") unary}
unary       = "-" unary | power           power = postfix ["**" unary]
postfix     = primary {"." NAME | "(" [args] ")" | "[" expression "]" | "[" [expression] ".." ["<" expression] "]"}
primary     = literal | NAME | "self" | "." NAME | "(" expression ")" | tuple | list | map
            | "try" expression | expression "catch" NAME ":" suite | expression "else" expression
            | "match" expression ":" arms | "spawn" call | "wait" expression
```

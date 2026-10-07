# Luce and Base

[Reference: The Base boundary](../../luce.md#16-the-base-boundary).

## Two languages, one program

Luce is built on **Luce Base**, a systems language in the spirit of C: fixed-size integers
and floats, pointers, arrays, manual memory management, bit operations, threads, inline
assembly, and direct calls to C libraries. The Luce compiler translates every Luce program
into Base, and Base compiles it to machine code.

The two divide the work. Luce leaves the machine out on purpose: it has one integer type, no
pointers, and no way to call C. When a program needs those, that part is written in Base, and
the Luce code imports it. In practice this means:

- **Most Luce programs never contain Base.** The libraries they use, from `luce-std` to user
  interface and graphics packages, are Base packages written once and imported like any other
  package.
- **A project can add its own Base modules** for code that needs speed, bit-level work, or a C
  library: files ending `.lucb` beside the `.luc` ones.

The [Luce Base documentation](https://luce-base.luciaos.com) covers the language itself. This
chapter covers what happens at the boundary.

## Importing a Base module

A Base module is imported by the same `import` as a Luce one. This module and program show
each kind of thing that crosses:

<!-- file native.lucb -->
```lucb
## Helpers written in Base.

pub let odd_number: ErrorCode = ErrorCode.package(1)

pub enum Level as u8:
    low = 1
    high = 2

pub struct Size:
    pub var width: i64
    pub var height: i64

    pub func area() -> i64:
        return self.width * self.height

pub handle Counter:
    destroy release

struct CounterState:
    var count: i64

pub func open_counter(start: i64) -> Counter:
    let state = new CounterState(count = start) catch failure: trap("out of memory")
    return (Counter)(void*)state

pub func increment(counter: Counter) -> i64:
    let state = (CounterState*)(void*)counter
    state.count += 1
    return state.count

pub func release(counter: Counter):
    print("counter released")
    free((CounterState*)(void*)counter)

pub func half(n: i64) -> i64!:
    if n % 2 != 0:
        error(odd_number, "an odd number has no whole half")
    return n // 2

pub func sum(values: const i64[]) -> i64:
    var total: i64 = 0
    for value in values:
        total += value
    return total

pub func apply(f: func(i64) -> i64, value: i64) -> i64:
    return f(value)

pub func describe(level: Level) -> str:
    return "low" if level == .low else "high"
```

<!-- with native.lucb -->
```luce
import native

func triple(n: int) -> int:
    return n * 3

pub func main(arguments: list[str]) -> int!:
    var size = native.Size(width = 2, height = 3)
    size.width = 4
    print(size, size.area())
    with native.open_counter(10) as counter:
        print(native.increment(counter), native.increment(counter))
    let half = native.half(3) catch failure:
        print(failure.message, failure.code == native.odd_number)
        recover 0
    print(half, native.sum([1, 2, 3]), native.apply(triple, 5))
    print(native.describe(native.Level.high), native.Level.low)
    return 0
```

```output
Size(width = 4, height = 3) 12
11 12
counter released
an odd number has no whole half true
0 6 15
high Level.low
```

A program that imports a Base module must be built, with `luce build` or `luc run`. The
interpreter runs Luce alone and refuses it. `luce test` builds its tests by itself, as
`--build` would, and `luc test` runs the Base modules' own tests too.

## What crosses

A Luce module sees a Base module's `pub` functions, constants, structs, enums with integer
values, handles, and object types, as long as their signatures use only types that cross:

| Base | In Luce | How |
| --- | --- | --- |
| `i64`, and `i8` to `u64`, `isize`, `usize` | `int` | by value; an `int` too large or too small for a narrower type traps as it crosses |
| `f64`, `f32` | `float` | by value |
| `bool` | `bool` | by value |
| `str` | `str` | a Luce string is lent to Base for the call; a Base result is copied into a new Luce string |
| `c.str` (C text) | `str` | lent as a copy ending in a zero byte; a string holding a zero byte traps |
| `const u8[]` | `bytes` | lent; a result is copied |
| `const T[]` | `list[T]` of numbers, `bool`, `str` or handles | lent for the duration of the call |
| `interop.Owned[const T[]]`, as a result | `list[T]` | the elements copied into a new list |
| a struct of crossing fields | the same struct, with its fields and `pub` methods | copied, like any Luce struct |
| an enum `as u8` (or another integer type) | the same enum | by value; a number that names no case traps |
| `T?`, `T!`, tuples | `T?`, `T!`, tuples | each part crossing |
| a function type over numbers, `str` and `bytes` | a function type | a *named* Luce function, never a closure |
| `handle` | a class with `close()` | below |
| `interop.Type[T]` and its relatives | a class with its methods | below |
| `ErrorCode` constants | `ErrorCode` constants | for comparing with `failure.code` |

Anything else, such as pointers, spans that are not `const`, fixed arrays, unions, atomics,
generic declarations, or C types, does not cross, and **a function whose signature mentions
one is invisible to Luce**. The Base package then offers a Luce-friendly function beside it.
This is why the standard library shows Luce fewer functions than it shows Base programs
([The standard library](15-standard-library.md)).

The rule for memory is that Luce never holds a pointer into memory that Base manages: what
Luce lends to Base is valid for the call, and what Base returns is copied into Luce values.

### Errors and traps

A Base failure arrives in Luce as an ordinary failure with the same code and message, and a
Luce program compares its code with the module's constants, as above. A trap in Base code is
a trap of the program, reported the same way.

### Handles

A *handle* is how a Base module hands Luce a resource it owns: an open file, a native window,
the counter above. The module declares it with the function that releases it:

<!-- fragment -->
```lucb
pub handle Counter:
    destroy release
```

Luce sees `Counter` as a class with no fields and a `close()` method that calls `release`
once. It closes by itself when its last reference goes away, and at the end of a `with`
block, as `counter` does above. Calling it after it is closed traps. A handle is only ever
returned by the module's functions; Luce cannot construct one.

### Objects

A Base type declared with `interop.Type[T]` appears in Luce as a class with a constructor and
methods, `files.TemporaryDirectory()` for example, or is answered by a function, as
`files.open(path)` answers a `File`. It is shared and closed like a handle, with methods
instead of module functions; its `close()` is the function its declaration names. Writing
such types is covered in the Base documentation.

### Callbacks

Base can call back into Luce through a function value, but only a named Luce function whose
parameters and result are numbers, `bool`, `str` or `bytes`, as `triple` above. Closures do
not cross: a Base library that needs state with its callback takes it as a separate argument.
A Base module cannot otherwise name a Luce declaration; dependencies go from Luce to Base,
never back.

### Workers

Values that cross are sendable to workers when their Luce types are. Handles and objects from
Base are not: they belong to the worker that made them.

## When to write Base

Reach for a Base module when:

- the code needs **fixed-size integers or floats**, or wrapping arithmetic: parsers of binary
  formats, hashes, checksums, compression, image pixels;
- it is a **hot loop** over many numbers, where control over memory layout matters;
- it **calls a C library**: Base can call C directly, and declares the C functions it uses;
- it manages a **native resource**, exposed to Luce as a handle or object.

Keep the boundary narrow: a few functions that take and return plain values and handles.
Luce code then stays simple and checked, and the Base part stays small enough to review
carefully.

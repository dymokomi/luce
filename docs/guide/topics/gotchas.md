# Gotchas

The things most likely to surprise you, especially coming from Python. Each links to the
chapter that explains it.

## Names and layout

- **A name cannot be reused while it is visible.** A second `let count` in an inner block, a
  parameter named like a top-level function, or a local named like an import, is an error.
  [Syntax](01-syntax.md#a-name-is-never-shadowed)
- **The built-in names are reserved**: `list`, `map`, `set`, `str`, `int`, `task`, `unit`,
  `print`, `error` and the others cannot name a variable, parameter or function; a field or
  a method may take one. [Syntax](01-syntax.md#reserved-words)
- **`abs`, `min`, `max`, `round`, `ord`, `chr` and `input` are in modules**: `import math`
  for `math.abs(x)`, `import text` for `text.code_of(s)`, `import console` for
  `console.read_line()`. [Types and values](02-types-and-values.md#standard-modules)
- **`hash(x)` is a method**, `x.hash()`. [Types and values](02-types-and-values.md#hashing)
- **Names are ASCII.** `café` is not a valid name; text and comments may hold anything.
- **Indentation is four spaces; tabs are errors.** There is no `\` line continuation: wrap
  in parentheses. [Syntax](01-syntax.md#layout)
- **An unused result is an error.** Write `_ = f()` to drop it on purpose.
  [Syntax](01-syntax.md#statements-and-values)
- **An unused import is an error**, and imports must come before declarations.
  [Modules and packages](13-modules-and-packages.md#imports)
- **Code after an unconditional `return` or `error` is an error**, not dead code.

## Values and types

- **Structs and enums are copied** on assignment and when passed, unlike Python objects.
  Use a class for something shared. [Structs and enums](08-structs-and-enums.md#values-copy)
- **A `let` struct cannot change at all**; a `let` list, map or class object can, since `let`
  only fixes which object the name refers to. [Collections](04-collections.md#maps)
- **A method that changes a struct needs a `var`** receiver.
  [Structs and enums](08-structs-and-enums.md#methods-that-change-self)
- **A class has no `==` or `print` until it declares `Equatable` or `Display`.**
  [Classes](09-classes-and-memory.md#identity-equality-and-display)
- **There is no inheritance.** Use interfaces, composition, or an enum.
  [Classes](09-classes-and-memory.md#no-inheritance)
- **An empty `[]`, `{}` or `none` needs its type written**: `let names: list[str] = []`.
  [Types and values](02-types-and-values.md#inference)
- **`{}` is an empty map**; an empty set is `let s: set[int] = {}`.
- **Strings print without quotes**, also inside lists: `[a, b]`, not `['a', 'b']`.
  [Types and values](02-types-and-values.md#printing)
- **A fallible `init` is written `-> unit!`.** [Classes](09-classes-and-memory.md#construction)

## Numbers

- **`int` and `float` never mix**: `count * 1.5` and `1 == 1.0` are errors. Convert with
  `float(count)`. [Expressions](05-expressions.md#arithmetic)
- **`int` overflow traps.** Integers have 64 bits, not Python's unlimited size.
- **`1 / 0` is `inf`**, since `/` is a float division; `1 // 0` traps.
- **`2 ** -1` traps**; write `2.0 ** -1.0`.
- **No bit operations** (`&`, `|`, `<<`, ...), unsigned integers or other sizes. Use a Base
  module. [Luce and Base](16-base.md#when-to-write-base)
- **A format specification must fit its value's type**: `f"{count:.2f}"` of an `int` is an
  error; write `f"{float(count):.2f}"`. [Text and bytes](03-text-and-bytes.md#format-specifications)
- **`math.round` takes and gives a `float`**: `math.round(2.5)` is `2.0`, and
  `math.round(3)` is an error. [Types and values](02-types-and-values.md#standard-modules)
- **`math.min` and `math.max` take two values**; a list has `values.min()` and
  `values.max()`.
- **`math` alone is the language's module**; luce-std's is `from luce_std import math`, under
  another name when a module wants both. [Standard library](15-standard-library.md#math)

## Text

- **A string cannot be indexed**: `word[0]` is an error; use `word[0..<1]` or a `for`.
  [Text and bytes](03-text-and-bytes.md#operations-on-str)
- **Slices use ranges**: `text[1..<3]`, `values[2..]`, not `[1:3]`.
- **`upper()` and `lower()` change ASCII letters only.** Use `unicode.to_upper` for all of
  Unicode.
- **`split(",")` keeps empty pieces**, as in Python; `split()` splits on runs of white space.
- **Searches answer `none`, not `-1`**: `index_of`, `last_index_of`. [Text and bytes](03-text-and-bytes.md#operations-on-str)
- **`join` is a list method**: `["a", "b"].join(", ")`.
- **Formatted strings are one line**; `f"""` is not available.
- **Single quotes are not strings.**

## Collections

- **`m[key]` answers an optional**, never raises `KeyError`: write `m[key] else default`
  or `m.get(key, default)`.
  [Collections](04-collections.md#maps)
- **A `for` over a map gives `(key, value)` pairs**, not keys. [Collections and loops](../tour/03-collections-and-loops.md#loops)
- **Changing a collection's size inside a `for` over it traps.**
- **`sorted`, `min`, `max`, `sum`, `any` and `zip` over a list are methods**: `values.sorted(key = f)`,
  not `sorted(values, key=f)`. [Collections](04-collections.md#lists)
- **A step is a method of the range**: `(0..<10).step(2)`, not `range(0, 10, 2)`.
  [Control flow](06-control-flow.md#for)
- **No comprehensions**: use `map` and `filter`.
- **An out-of-range slice traps** instead of shortening.

## Absence and failure

- **A `T?` must be unwrapped before use**, with `if let`, `else` or `match`; checking
  `!= none` does not unwrap it. [Optionals and errors](10-optionals-and-errors.md#optionals)
- **There is no `?.`** and no forced unwrap.
- **A failure passes up by itself inside a `!` function**, but a function without `!` must
  `catch` every fallible call. [Optionals and errors](10-optionals-and-errors.md#failures-pass-up-by-themselves)
- **`int("x")` and `float("x")` can fail**: in a function without `!`, catch them.
- **A trap cannot be caught**, and `assert` traps, in every build.
  [Optionals and errors](10-optionals-and-errors.md#traps)
- **In a test, a failed `assert` ends the whole run**; `error(...)` fails just that test.
  [Testing](14-testing.md#failures-and-traps)
- **`T!` cannot be stored**; use `Result[T]`. [Optionals and errors](10-optionals-and-errors.md#storing-an-outcome-result)

## Functions

- **Parameters cannot be assigned**; bind a `var` copy.
- **Functions cannot be nested**; use a lambda. [Functions](07-functions.md#declaring-a-function)
- **An expression lambda needs its parameter types from context**, or written:
  `(n: int) => n + 1`. [Functions](07-functions.md#function-values)
- **Generic type arguments are not inferred through an interface**: write `drain[int](x)`.
  [Generics](11-interfaces-and-generics.md#generic-types)

## Workers, modules and Base

- **Workers take copies of values; class objects and closures cannot be sent.**
  [Workers](12-workers.md#workers-share-nothing)
- **No global variables**, and a top-level `let` must be a constant.
  [Modules and packages](13-modules-and-packages.md#what-a-module-contains)
- **A package is not a module**: `import luce_std` is an error; `from luce_std import files`.
- **Another module cannot print a struct with a private field**, nor set that field or call
  an `init` that is not `pub`; the struct declares `Display`, or its module offers a `pub`
  function. [Visibility](13-modules-and-packages.md#visibility)
- **A program that imports Base must be built**: `luce run` refuses it. [Luce and Base](16-base.md#importing-a-base-module)
- **Base functions with pointers or other Base-only types are invisible to Luce.**
  [Luce and Base](16-base.md#what-crosses)

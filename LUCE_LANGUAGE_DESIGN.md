# Luce Next Language Design

## Complete implementable language specification

Status: normative design draft for the clean-break language

Language epoch: 1

Bootstrap: frozen Stage-0 0.19 is only the seed and imposes no compatibility requirement

Primary proving programs: the Luce compiler/tooling, LuciaOS evaluators and Views, and serious native applications

Companion documents: `LUCE_NEXT_BLUEPRINT.md`, `LUCE_UX_ADOPTION_REQUIREMENTS.md`, and `LUCE_CPP_INTEROP_DESIGN.md`

## 0. Executive decision

Luce is a small, statically typed, native language with Python-like visual clarity, value/reference semantics, ARC-managed identity, explicit recoverable failure, explicit host effects, isolated concurrency, and first-class C/C++ coexistence.

The language is not trying to be minimal by deleting facilities that real programs need. It is trying to reach the **minimum complete language**: the smallest coherent surface that can implement its own compiler, build LuciaOS components, and integrate with native libraries without compiler-only magic or widespread boilerplate.

The governing test is:

> **A feature enters the language only when it removes more total complexity than it adds.**

Total complexity includes syntax, semantics, compiler implementation, runtime behavior, diagnostics, tooling, documentation, interoperability, and the number of distinctions a programmer must remember.

The language sentence is:

> **Values copy. References share identity. ARC keeps references alive. Weak edges break cycles. Resources close at the last strong release. Workers never share mutable object identity. Effects are declared. Failure is visible.**

The product sentence is:

> **Python-readable native code with explicit effects, predictable resources, and compiler-guided correctness.**

## 1. The permanent complexity budget

Every ordinary Luce program is built from nine concepts.

| Concept | User-facing mechanism | What it replaces |
| --- | --- | --- |
| Bindings and mutation | `let`, `var` | Implicit mutability, initialization states, shadowing conventions |
| Functions and control | `func`, calls, `if`, loops, `match`, `return`, `defer` | Multiple callable/object/control dialects |
| Value modeling | primitives, tuples, `struct`, payload-capable `enum` | Null sentinels, tag integers, manual layout conventions, separate enum/union hierarchies |
| Shared identity and resources | final `class`, ARC, `weak`, `deinit` | Manual retain/release/free and general lifetime syntax |
| Absence and failure | `T?`, `T!`, `try`, `catch`, `recover`, traps | Nullability-by-default and implicit exceptions |
| Reusable abstraction | generics and nominal `interface` | Duplication, inheritance, operator protocols, metaprogramming |
| Host effects | `uses` | Ambient files/network/process/clock/device authority |
| Isolated concurrency | `spawn`, `task`, `wait` | Shared heaps, locks, data races, async coloring |
| Native coexistence | C ABI, Clang-powered C++ bridges, audited `native` code | Rewrites and unrestricted raw-pointer programming |

The following are not separate concepts:

- arrays, lists, maps, sets, strings, builders, arenas, files, sockets, windows, and GPU resources are types and libraries built on values/references/resources;
- methods are functions declared inside a type;
- closures are functions plus a captured environment;
- iteration is an interface plus `for` syntax;
- errors are one standard value carried by `T!`;
- tests are statically registered fallible functions plus a harness profile, not a second callable/control dialect;
- packages are named collections of modules plus a manifest and lock;
- compiler backends do not alter the source language.

### 1.1 Feature placement rule

When a need appears, solve it at the cheapest correct layer:

1. documentation or diagnostic;
2. ordinary library API;
3. compiler/tooling query or transformation;
4. standard-library protocol recognized by syntax;
5. language feature only when the previous layers cannot preserve safety, clarity, or performance.

### 1.2 What “small” does not mean

Small does not mean:

- everything is a primitive;
- difficult computer facts are hidden;
- unsafe code is shorter than safe code;
- common programs rebuild closures, generics, error handling, modules, or packaging themselves;
- the standard library is intentionally weak;
- tooling compensates for ambiguous semantics.

## 2. Feature disposition at a glance

| Area | Epoch 1 decision |
| --- | --- |
| Layout | Four-space blocks; statement suites may stay on one line; no tabs or semicolons; canonical formatter |
| Names | Static lexical scopes, case-sensitive, no local shadowing |
| Bindings | Immutable `let`, mutable `var`; initializer required |
| Numerics | Fixed-width integers/floats, explicit conversions, checked safe arithmetic |
| Text | UTF-8 immutable `str`, Unicode-scalar `char`, immutable `bytes` |
| Functions | Named/default arguments, tuples for multiple results, no overloads/variadics |
| Control | `if`, conditional expression, `for`, `while`, `match`, `break`, `continue`, `return`, `defer` |
| Values | Tuples, structs, payload-capable enums, fixed arrays |
| Identity | Final ARC classes, explicit `new`, weak references, deterministic `deinit` |
| Collections | Reference `list`/`map`/`set`; immutable owner-retaining `slice`; stable iteration order |
| Absence | One-layer `T?` with the three-arm `else` fallback; no force unwrap or nullable-by-default types |
| Failure | `T!`, `try`, `catch`, `recover`, stable `Error`; no exceptions |
| Traps | Uncatchable checked-rule/host termination with source trace |
| Closures | Explicit `func` literal, deterministic capture rules, snapshot/weak capture list |
| Generics | Type parameters, nominal bounds, monomorphization, bounded instantiation |
| Interfaces | Explicit conformance, methods only, no inheritance/defaults/associated types/casts |
| Effects | Public `uses` sets, private inference, loader validation |
| Concurrency | Isolated `spawn`, copied sendable value graphs, structured `task.wait()` |
| Modules | One source file per module, explicit imports, private by default |
| Packages | Manifest + exact lock + content identities; no ambient build scripts |
| Testing | Static `test` declaration, ordinary safety/effects, isolated deterministic harness, complete production erasure |
| Native | Direct safe C subset; generated C++ bridges; raw pointers only in audited `native` code |
| Backends | Interpreter, fast Luce backends, optional LLVM; identical semantics |

## 3. Source text, layout, and names

### 3.1 Encoding

- Source is UTF-8.
- A UTF-8 BOM may be accepted and ignored only at byte zero.
- NUL, invalid UTF-8, misleading bidirectional controls, and look-alike syntax punctuation are rejected.
- CRLF is normalized for parsing while source spans retain correct byte/line mappings.
- Identifiers are ASCII in epoch 1. Unicode remains fully supported inside text and comments. Unicode identifiers require a later spoofing and normalization design.
- An identifier begins with an ASCII letter or `_` and continues with ASCII letters, digits, or `_`. The standalone `_` token remains the pattern wildcard; `_unused` is an ordinary name.

### 3.2 Indentation and lines

- A statement suite after `:` is either exactly one simple statement on the same physical line or a newline followed by a block indented exactly four spaces. Type, enum, and interface bodies always use the indented form.
- A same-line suite cannot contain a compound statement (`if`, `while`, `for`, or `match`), a nested suite such as a closure or `catch` handler, or a second statement. With no semicolons, the newline closes it unambiguously.
- Same-line and indented suites create the same lexical scope. A following `elif` or `else` begins on its own line aligned with the original header.
- Tabs are errors with a machine-applicable replacement.
- Newlines terminate statements except inside `()`, `[]`, or `{}`, where they are ordinary spacing.
- Inside delimiters, a `:` that ends its line (comments aside) opens an indented suite, so a block closure, `catch` handler, or `match` expression can be written as an argument or element. The suite's lines indent four spaces past the line holding the `:`; it ends when a line dedents back to that indentation or when the enclosing delimiter closes, which may follow the last statement on its line. Between the suite's end and the closing delimiter, newlines are spacing again.
- A same-line suite written inside delimiters, as in `run(func (): return 1)`, ends where its delimiter closes; it cannot be followed by `,` and another element on the same line.
- There is no semicolon and no backslash line continuation.
- A trailing comma is accepted in multi-line parameter, argument, tuple, array/list, map, and case-payload lists; the formatter inserts/preserves it where it stabilizes diffs.
- Blank lines do not affect meaning.
- The formatter is the single authority for line breaking and indentation.
- The formatter preserves a valid same-line suite while it remains one statement on one physical line. If the statement must wrap, the formatter expands it to an indented suite.

```luce
if cached: return result

if image.width > maximum_width:
    let scale = maximum_width / f64(image.width)
    image.resize(scale)

buffer.with_mutable_slice(func (view: mutable_slice[u8]):
    fill(view, 0)
)
```

### 3.3 Comments and documentation

```luce
# Ordinary comment.

## Public summary used by `luce doc`.
## Additional paragraphs remain plain Markdown.
pub func area(width: f64, height: f64) -> f64:
    return width * height
```

- `#` begins an ordinary comment outside a string.
- Consecutive `##` comments immediately preceding a declaration form its documentation.
- A `##` block at the top of a file that stands apart from what follows — a blank line, an `import`, or nothing — is the module's documentation. A top-of-file block that touches the first declaration documents that declaration.
- Documentation is non-executable. There are no doctest directives hidden in comments; fenced `luce` examples are tested by the documentation tool explicitly.

### 3.4 Naming

Canonical style:

- types and interfaces: `PascalCase`;
- functions, methods, bindings, fields, cases, modules, and packages: `snake_case`;
- acronyms are treated as words: `HttpClient`, `parse_json`;
- imported native APIs may receive generated idiomatic names while retaining the foreign spelling in metadata.

Style violations are formatter/linter diagnostics, not alternate language semantics.

### 3.5 Scope and shadowing

- Names are resolved lexically.
- Module declarations share one namespace: a type, function, constant, interface, or imported name cannot reuse the same visible name. Members have their own per-type namespace.
- A local name may not shadow another still-visible local, parameter, capture, or imported name.
- A case/catch/loop binding owns its nested scope and disappears afterward.
- Type members and local variables may share a spelling because member access is qualified through `self` or another value.
- Module declarations are order-independent. Local statements are sequential.
- Use before declaration is rejected for locals.
- The tiny compiler-known core namespace (`assert`, `discard`, `error`, `hash`, and `trap`, plus core type names) cannot be redeclared. These operations parse as ordinary calls; only their checked types and semantics are special.

The no-shadowing rule removes a refactoring hazard and makes compiler explanations stable. Renaming, not shadowing, is the repair.

## 4. Lexical forms and literals

### 4.1 Boolean and absence literals

```luce
true
false
none
```

`none` receives its optional type from context. It is not a universal null pointer.

### 4.2 Integer literals

```luce
42
1_000_000
0xff
0o755
0b1010_1100
255u8
-20i32
```

- Underscores may separate digits but not begin/end a number or repeat.
- Based integer prefixes use the canonical lowercase spellings `0x`, `0o`, and `0b`; uppercase `0X`, `0O`, and `0B` are rejected.
- Context chooses the integer type; absent context, the default is `i64`.
- A suffix names an exact built-in numeric type.
- A literal outside the contextual type's range is a compile error.
- Negative numeric literals are parsed as unary negation applied to a positive literal, with a special representability rule for the minimum signed value.

### 4.3 Floating literals

```luce
1.0
6.022e23
0.5f32
1_000.25
```

- Context chooses the float type; absent context, the default is `f64`.
- Decimal-to-binary conversion is correctly rounded.
- `nan`, positive infinity, and negative infinity use named constructors/constants rather than spelling-dependent literals.

### 4.4 Character, string, byte, and raw literals

```luce
'A'                         # one Unicode scalar: char
"hello"                     # UTF-8 str
b"\x89PNG"                  # immutable bytes
r"C:\studio\shots"          # raw str
f"frame {frame}: {status}"   # formatted str
"""multiline
text"""
```

- A character literal contains exactly one Unicode scalar after escapes.
- A string is always valid UTF-8.
- A byte literal contains byte escapes and ASCII source characters; non-ASCII source must be encoded explicitly or converted.
- Raw strings disable escapes and interpolation.
- Triple-quoted strings use formatter-defined indentation trimming based on the closing delimiter.
- Interpolation evaluates expressions left-to-right and uses the closed standard formatting interface. It is not a macro. The lexer splits a formatted string into text and fields, and each field is parsed as an ordinary expression in place; a field cannot be empty and carries no format specifier.
- A field inside a triple-quoted formatted string may contain an ordinary line comment. Because `#` owns the rest of its physical line, the field's closing `}` must appear on a later line.
- Text/character escapes are `\\`, `\"`, `\'`, `\n`, `\r`, `\t`, `\0`, and Unicode scalar `\u{HEX}`. Byte literals additionally allow exactly two-digit `\xNN`; a text escape must still produce valid Unicode.
- Formatted strings use `{{` and `}}` for literal braces. Formatting policies are ordinary calls inside the field (for example `format.hex(value)`), not an embedded mini-language.

### 4.5 Collection literals

```luce
let numbers = [1, 2, 3]                    # list[i64] by default
let pixels: array[u8, 4] = [255, 0, 0, 255]
let names = {"primary": "red", "accent": "blue"}
```

- `[...]` is a list unless context requires a fixed array or slice-compatible constant.
- `{key: value, ...}` is a map.
- Set construction uses `set[T](...)`; there is no separate set-literal grammar.
- An empty list needs a contextual element type; an empty map/set uses `map[K, V]()` or `set[T]()`.
- Elements must resolve to one element/key/value type; Luce never infers a hidden heterogeneous or numeric-union collection.
- Literal elements evaluate left-to-right.
- Duplicate literal map keys are compile errors when statically equal; runtime duplicates replace the earlier value using ordinary insertion semantics.

## 5. Type system

### 5.1 Typing model

Luce is statically and nominally typed. Every expression has one compile-time type. Local inference removes redundant spelling; it never introduces a dynamic `any` type.

There is no class/type subtyping. The only implicit lifts are a concrete value/reference to an interface it explicitly implements, `T` to successful `T?`, and `T` to successful `T!` where context requires them. Numeric and representation conversions are explicit.

### 5.2 Built-in scalar types

| Type | Meaning |
| --- | --- |
| `bool` | `true` or `false`; no numeric conversion |
| `u8`, `u16`, `u32`, `u64` | fixed-width unsigned integers |
| `i8`, `i16`, `i32`, `i64` | fixed-width two's-complement signed integers |
| `f16`, `f32`, `f64` | IEEE 754 binary floating-point |
| `char` | one Unicode scalar value |
| `str` | immutable valid UTF-8 text |
| `bytes` | immutable byte sequence |
| `unit` | the single no-result value `()` |
| `never` | an expression that cannot complete normally |

There is no target-sized public integer in portable Luce. Collection lengths and indices use `u64`; a native adapter performs checked conversion to `size_t` or another platform type.

### 5.3 Composite type forms

```luce
(i64, str)                    # tuple
array[f32, 16]                # fixed-size value array
slice[f32]                    # immutable owner-retaining sequence view
mutable_slice[f32]            # non-escaping callback-scoped mutable view
list[Point]                   # mutable reference collection
map[str, Material]            # insertion-ordered reference map
set[AssetId]                  # insertion-ordered reference set
range[u64]                   # integer range value used by `for`
Point?                        # one-layer optional
Image!                        # recoverably fallible Image result
func(i64, i64) -> i64         # function value
func(str) -> bytes! uses files
Reader                        # interface existential
Weak[Node]                    # storable weak handle to a class
task[Image]                   # isolated task handle; wait is fallible
```

Generic brackets always contain types except the built-in `array[T, N]`, whose second argument is a non-negative compile-time integer.

### 5.4 Type aliases

```luce
pub type Pixel = array[f32, 4]
type SymbolTable = map[str, Symbol]
```

A type alias is another spelling for exactly the same type. It does not create a domain distinction and cannot have independent methods or conformance.

Epoch 1 aliases are non-generic and non-recursive. If a family deserves parameters or behavior, declare the corresponding generic struct/enum/class instead of building an alias language.

For a domain distinction, use a one-field struct:

```luce
pub struct UserId:
    pub let value: u64
```

Structs receive memberwise construction and structural operations when valid, so a domain type does not require a separate “newtype” feature in epoch 1.

### 5.5 Type inference

Inference is local:

- from an initializer to its binding;
- from arguments to generic parameters;
- from a function's declared return type into return expressions;
- from a collection literal's context/elements;
- from `none` and enum-case shorthand into an expected type.

Inference does not cross public API boundaries. Public functions, public fields, public constants, and public type layouts spell their types.

### 5.6 Equality, ordering, and hashing

- `==` and `!=` exist for built-in values, tuples, arrays, structs, enums, optionals, strings, bytes, frozen value collections, and the content of core lists/maps/sets when every component supports equality. List order matters; map/set insertion order does not affect equality.
- Classes do not gain value equality. A class can expose a named `equals` method if its domain needs value comparison.
- `is` compares identity for shared reference kinds such as classes and mutable collections. It is never a runtime type test.
- Ordering operators exist only for numeric scalars, `char`, `str`, `bytes`, and types explicitly covered by a standard interface through named algorithms. User code cannot overload operators.
- Structs and enums receive structural hashing when every component is hashable.
- Floating-point equality follows IEEE 754; named standard functions provide total ordering and bitwise comparison.
- Map/set hashing uses a process-protected seed, while iteration order remains insertion order and therefore deterministic.

### 5.7 Recursive types

Directly recursive value layouts are rejected:

```luce
struct Invalid:
    let next: Invalid?       # infinite-size value
```

Use a class reference, index/handle, or collection to introduce indirection.

## 6. Bindings, assignment, and initialization

### 6.1 Immutable and mutable bindings

```luce
let width = 1920
let title: str = "Preview"

var frame = 0
frame += 1
```

- `let` is assigned exactly once.
- `var` may be reassigned but never changes type.
- Every local binding requires an initializer.
- Parameters are immutable bindings.
- There is no implicit declaration through assignment.
- There are no uninitialized safe locals.

### 6.2 Assignment semantics

- The right-hand side is fully evaluated before the destination changes.
- Values copy according to their language semantics.
- Class, closure, collection, task, and resource references share identity and update ARC.
- Tuple binding destructuring evaluates its right-hand side once, then initializes names from left to right. It is allowed with `let` or `var`; epoch 1 has no general destructuring-assignment or struct pattern syntax.

```luce
let (width, height) = image.size()
var current = initial
current = next
```

A field/index mutation path is one checked lvalue evaluated once. The root binding must be `var` for a value, every traversed value field must permit mutation, and a core mutable collection may expose its element slot directly:

```luce
var cursor = Cursor(position: 1)
cursor.position = 4
items[index].selected = true
```

The last line updates the struct value stored in the mutable list. It does not create a reference to a temporary, and the lvalue cannot be captured or returned.

Assignment is a statement, not an expression. There are no `++` or `--` operators.

### 6.3 Definite initialization

- Safe locals are initialized at declaration.
- Struct construction initializes every field.
- Class `init` must initialize every field exactly once before `self` escapes.
- An immutable field may be assigned only during initialization.
- Reading a field before its initialization, calling an instance method before complete initialization, or storing `self` externally is rejected.

## 7. Expressions and operators

### 7.1 Evaluation order

Luce evaluates expressions left-to-right, including:

- function receiver and arguments;
- collection literal elements;
- interpolation fields;
- binary operands;
- assignment right-hand sides;
- constructor arguments.

Optimization may reorder only when behavior, traps, destruction order, and declared effects remain observationally identical.

### 7.2 Arithmetic

| Operators | Meaning |
| --- | --- |
| `+`, `-`, `*` | checked integer or IEEE float arithmetic |
| `/` | floating-point division; operands must be floating |
| `//` | integer floor division |
| `%` | modulo paired with floor division |
| unary `-`, `+` | numeric sign operations |

- Integer overflow and invalid shifts trap in every normal build profile.
- Divide-by-zero traps for integers; floating division follows IEEE 754.
- Unary minus is invalid for unsigned values.
- `minimum_signed // -1` traps as overflow. Exponentiation is a named standard-library operation (`math.pow` for floating values and checked integer power functions) rather than a special operator with another precedence and numeric-policy family.
- Constant folding uses the same width, rounding, overflow, NaN, and trap semantics as runtime evaluation.
- Wrapping, saturating, checked-result, and truncating operations are named standard functions/methods such as `wrapping_add`, `saturating_add`, and `truncating_div`.
- `+` also concatenates two `str`, two `bytes`, or two same-element core lists and may allocate; builders are preferred in loops. This is a closed built-in operation, not user overloading.
- No user type overloads arithmetic.

Floating contraction/reassociation is disabled in normal and `release-safe` semantics unless a named fast-math library operation explicitly requests a weaker contract. The target/profile report states NaN, subnormal, fused-operation, and reproducibility behavior; a backend cannot quietly choose it.

### 7.3 Bit operations

Fixed-width integers support `&`, `|`, `^`, `~`, `<<`, and `>>`. Shift counts outside the bit width trap. Signed right shift is arithmetic; unsigned right shift is logical.

### 7.4 Comparison and logic

```luce
if ready and not cancelled:
    start()

let same_object = left is right
```

- Conditions require `bool`; there is no truthiness.
- `and` and `or` short-circuit left-to-right.
- `not` operates only on `bool`.
- Chained comparisons are rejected. Write `minimum <= x and x < maximum`.
- Ambiguous forms such as `not a == b` are rejected; write `not (a == b)`.
- `is` compares compatible shared reference identity. It is not a runtime type test.

### 7.5 Explicit conversion

Conversions use destination construction:

```luce
let count = u32(length)
let ratio = f64(done) / f64(total)
let byte = u8(value)       # traps if a runtime value is out of range
```

- A compile-time impossible conversion is an error.
- A checked runtime conversion traps when the value is not representable.
- Named `checked`, `clamped`, or `bit_cast` APIs provide other policies.
- `bit_cast` and representation reinterpretation are restricted to audited native facilities unless both types are explicitly safe value representations.

### 7.6 Conditional expression

```luce
let label = "ready" if ready else "waiting"
```

The conditional expression accepts one expression per branch and requires a Boolean condition. Both branches must resolve to one type. Multi-statement work uses an ordinary `if` statement. This one compact expression avoids adding value-producing blocks.

### 7.7 Member, call, and indexing expressions

```luce
image.width
image.resize(scale: 0.5)
pixels[10]
pixels[10..<20]
```

- `.` accesses a member or module declaration.
- Calls use `()`.
- Indexing is checked in all normal profiles.
- Slicing uses a half-open range: `[start..<end]`. `[..<end]` starts at zero and `[start..]` ends at the sequence length. A slice states at least one bound. There is no slice-step grammar.
- Negative indexing is not supported.
- User-defined operator overloading, including indexing, is absent. Standard collection types and closed standard interfaces receive the syntax explicitly.

### 7.8 Expression statements and discarded values

Function/method calls may appear as statements. A non-`unit` result is discarded, and the linter warns by default because this often loses a count, handle, or status. Writing `discard(call())` uses the generic compiler-known `discard[T](value: T)` operation and states the intent explicitly. A fallible result must still be handled or propagated before it can be discarded.

## 8. Functions and calls

### 8.1 Declaration

```luce
pub func clamp(value: f64, minimum: f64, maximum: f64) -> f64:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value
```

- `func` declares a function.
- Parameter types and every non-`unit` public result are explicit.
- A missing return arrow explicitly means `unit`; `-> unit` is equivalent and may be clearer in function types/interfaces.
- Every reachable path of a non-`unit` function returns.
- Function bodies never return their final expression implicitly.
- Nested named function declarations are absent; use a module function or closure.

### 8.2 Arguments and defaults

```luce
func render(scene: Scene, samples: u32 = 64, denoise: bool = true) -> Image!:
    # ...

let image = try render(scene, samples: 256, denoise: false)
```

- Parameters are positional-or-named.
- Positional arguments precede named arguments.
- Named arguments may then appear in any order.
- A parameter may have a pure compile-time default; parameters after the first default must also have defaults.
- A default cannot refer to another parameter, `self`, runtime state, effects, or a fallible expression; it is embedded as a typed constant at the call site.
- There are no positional-only, named-only, variadic, splat, or keyword-dictionary parameters in epoch 1.
- Duplicate, unknown, or omitted required arguments are compile errors with fixes.

### 8.3 No overloads

One visible scope contains at most one callable declaration with a given name. Constructors are not overloaded. Alternative operations receive semantic names:

```luce
Image.from_file(path)
Image.from_bytes(data)
Image.solid(width, height, color)
```

This keeps completion, references, documentation, function values, and C++ mapping deterministic.

### 8.4 Multiple results and tuples

```luce
func divide(value: i64, divisor: i64) -> (i64, i64):
    return (value // divisor, value % divisor)

let (quotient, remainder) = divide(17, 5)
```

Tuples are fixed-size anonymous values intended for local grouping and multiple results. Public domain data should usually use a named struct.

### 8.5 Function values

```luce
let operation: func(i64, i64) -> i64 = add
let result = operation(2, 3)
```

A function type includes parameter types, result/fallibility, and effect set. Argument labels are not part of a function value's type. Function values do not overload or dynamically inspect signatures.

Function conversion keeps parameter/success types exact. A non-fallible function may lift to the corresponding fallible function type, and a function with fewer effects may lift to one permitting a superset. The reverse conversions are rejected; epoch 1 has no general parameter/result variance rules.

### 8.6 Methods

Methods are functions declared inside a type. An explicit first `self` parameter makes a function an instance method:

```luce
struct Point:
    pub let x: f64
    pub let y: f64

    func distance_to(self, other: Point) -> f64:
        let dx = self.x - other.x
        let dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    func origin() -> Point:
        return Point(0.0, 0.0)
```

- `point.distance_to(other)` passes `point` as `self`.
- A type function without `self` is called through the type: `Point.origin()`.
- There is no separate `static` keyword.
- Method names cannot overload.
- `value.member` without `()` always names a stored field. Epoch 1 has no computed properties, setters, or user-defined subscripts; use an ordinary method whose call and possible work are visible.

### 8.7 Mutating value methods

```luce
struct Cursor:
    pub var position: u64

    mutating func advance(self, amount: u64):
        self.position += amount
```

- `mutating` is valid only for value-type methods.
- The receiver binding at the call site must be `var`.
- A mutating method may assign `var` struct fields or replace `self` with another value of the same type; a nonmutating method can do neither.
- Classes do not use `mutating`; their identity and `var` fields already state shared mutation.
- Epoch 1 has no general `inout` parameters. Algorithms return updated values or use a mutating receiver/reference collection. Add call-scoped `inout` only if real compiler/native workloads prove this insufficient.

### 8.8 Recursion

Recursion is allowed. Tail-call optimization is never a semantic guarantee. Standalone runtime policy and LuciaOS host profiles may impose stack/call-depth budgets; exceeding one is an uncatchable host termination with a source trace.

## 9. Control flow

Control flow is structured. Luce has no labels, `goto`, exceptions, or implicit nonlocal exits.

### 9.1 `if`

```luce
if temperature > 30.0:
    fan.start()
elif temperature < 10.0:
    heater.start()
else:
    climate.hold()
```

Conditions must have type `bool`. Branch bodies introduce lexical scopes. An `if` statement need not have an `else`.

Luce also has one compact conditional expression:

```luce
let label = "ready" if is_ready else "waiting"
```

It always has both alternatives. Their types must be equal or have a single unambiguous common type. Multi-line computation belongs in an `if` statement, not in an expression block.

### 9.2 Conditional binding

```luce
if let user = cache.find(name):
    greet(user)
else:
    log("not found")
```

`if let name = optional` unwraps a `T?` only inside the successful branch. It does not test arbitrary patterns and it does not mutate the optional. Negated binding and comma-separated condition lists are omitted; nested `if` statements remain explicit.

### 9.3 `while`

```luce
while cursor.has_more():
    parse_one(cursor)
```

`while` accepts one Boolean condition. There is no `do while`; write the first operation before the loop when it must occur at least once.

### 9.4 `for`

```luce
for item in items:
    render(item)

for index in 0..<image.width:
    draw_column(index)
```

`for` consumes the standard `Iterable[T]` protocol described in section 17. Iteration order is part of a collection type's contract. The iteration variable is an immutable binding scoped to the body.

The built-in range expressions are:

- `start..<end`: half-open, excluding `end`;
- `start..=end`: closed, including `end` when reachable.

Ranges require equal integer types and ascend by one. Descending or stepped traversal is spelled through library iterators such as `range.down(...)` and `range.step(...)`, keeping range syntax unsurprising.

A range is an immutable value `range[T]`. A closed range whose end is the integer type's maximum stops after yielding that end rather than overflowing.

### 9.5 `break` and `continue`

`break` exits the innermost loop. `continue` starts its next iteration. Neither takes a label or value. Deeply nested control flow should be extracted into a named function.

### 9.6 `match`

`match` is the sole pattern-selection construct:

```luce
match command:
    .open(path): open_document(path)
    .save(path):
        validate_destination(path)
        save_document(path)
    .quit: return
```

An arm body is an ordinary suite. A single simple statement may follow the arm's `:` on the same line; multi-statement and nested control flow use the indented form. Compactness changes no semantics: `'0': return 0` is an explicit `return`, not a value silently produced by the arm.

```luce
func bit_value(c: char) -> u8?:
    match c:
        '0', '1': return 0 if c == '0' else 1
        _: return none
```

Epoch 1 patterns are deliberately closed:

- enum cases, with bindings for any payload;
- `.some(value)` and `.none` for optionals;
- Boolean, numeric, character, or string literals; numeric patterns may carry a leading `-`;
- half-open `lower..<upper` and closed `lower..=upper` integer or character
  literal ranges;
- comma-separated alternatives that share one arm body;
- `_` as a catch-all.

A range's bounds have the same concrete type and are checked at compile time.
Half-open ranges require `lower < upper`; closed ranges require
`lower <= upper`. Ranges ascend in source order and use the same `..<` and
`..=` boundary meanings as range expressions.

Alternatives are separated by `,` and mean “any of these patterns”; they are
not evaluated expressions and have no left-to-right side effects:

```luce
return match c:
    '0'..='9' => "digit"
    'a'..='z', 'A'..='Z' => "letter"
    ' ', '\t', '\n' => "spacing"
    _ => "other"
```

When alternative enum or optional patterns bind payloads, every alternative
must introduce the same binding names with the same types, so the shared body
has one lexical environment. A binding is immutable and scoped to its arm.
Cases do not fall through. Guards, nested destructuring, and user-defined
pattern protocols are omitted. Compute a predicate before the match or use an
`if` inside an arm.

Every `match` is exhaustive. The compiler names missing enum/optional/Boolean
cases; integer, character, and string matches normally end in `_`. Literal and
range coverage participates in exhaustiveness where the complete finite domain
is provable. Duplicate values, overlapping ranges, and patterns made unreachable
by an earlier alternative or arm are errors. A catch-all is permitted for a
closed type, but the linter warns when spelling every case would preserve future
diagnostics.

`match` is both a statement and an expression. As a statement each arm opens
a `:` suite; where an expression is expected each arm instead **yields** a
value with `=>`, and the whole `match` is the value the chosen arm yields.
The two forms do not mix within one `match`: every arm is `:` or every arm is
`=>`.

This adopts the expression form the earlier freeze left open (it was gated on
"substantial Luce code proves that exhaustive value selection needs too much
helper or mutable staging code" — dogfooding the self-hosting compiler proved
exactly that). It enters under a coherent rule that keeps the three arrows
distinct, not as punctuation-only shorthand: **`->` declares a type**
(a result, a function type), **`=>` yields a value** (a lambda body, a match
arm), and **`:` opens a suite** of statements. An expression `match` takes its
single result type from where it lands (a typed binding, a `return`, a declared
argument) rather than from arm-type unification, is exhaustive by the same rule
as the statement form, evaluates its scrutinee once, and `=>` yields into the
surrounding expression — it is not an implicit `return`. It desugars to a
hidden slot the chosen arm assigns and the surrounding expression reads, so it
adds no new runtime instruction and no second family of return rules.

Use the expression form when surrounding code consumes the selected value. If
every arm immediately exits the function, statement arms such as
`'b', 'B': return is_binary(c)` communicate that control flow more directly.

### 9.7 `return`

`return expression` exits the current function. A unit-returning function uses bare `return` or reaches its end. Every reachable path of any other function must return or terminate through `error`, `trap`, or `never`.

### 9.8 `defer`

```luce
let handle = try files.open(path)
defer handle.close()

try process(handle)
```

`defer expression` registers a unit-producing call for the end of the current lexical scope. Deferred calls run in last-in, first-out order on normal exit, `return`, `break`, `continue`, and error propagation.

- The expression's receiver and arguments are captured when the `defer` is registered.
- A deferred call may not `return`, `recover`, or replace an in-flight error.
- A failure-capable cleanup must be handled inside a non-failing wrapper or performed explicitly before the successful return.
- `defer` does not run after process abort, power loss, or an uncatchable host termination.

ARC handles ordinary memory lifetime. `defer` is for lexical operations such as unlocking a native handle or rolling back a transaction, not a substitute for object cleanup.

## 10. Value data modeling

Luce provides two named value forms: `struct` and `enum`. Both copy by value and have no hidden identity.

Both may declare methods/type functions and implement interfaces. Structs store a product of named fields; enums store exactly one case, optionally with a payload. Luce deliberately has no second ordinary `union` declaration: a payload-free enum and a tagged union are the same closed-sum concept with the same construction, matching, visibility, layout, generic, and compatibility rules. Raw C unions remain a native-boundary concern rather than a third source-language data model.

### 10.1 Structs

```luce
pub struct Point:
    pub let x: f64
    pub let y: f64
    var cached_length: f64?
```

A struct is a fixed collection of fields:

- Every field uses the same binding words as a local: `let` for immutable or `var` for mutable.
- A field is private to its module unless declared `pub`.
- Fields have declaration order; that order is not a stable external ABI unless the type is explicitly exported through a native boundary.
- A struct cannot inherit from another type.
- A struct cannot directly contain itself. Recursive value data uses a class reference, list, or another indirection.

The compiler synthesizes a memberwise initializer when no `init` is declared:

```luce
let point = Point(x: 10.0, y: 20.0, cached_length: none)
```

The synthesized initializer is public only when the struct and every required field are public. Field defaults may omit arguments:

```luce
pub struct Style:
    pub let color: Color = Color(red: 0.0, green: 0.0, blue: 0.0, alpha: 1.0)
    pub let line_width: f64 = 1.0
```

A custom initializer uses a type function named `init`:

```luce
pub struct Percentage:
    let value: f64

    pub func init(self, value: f64) -> unit!:
        if value < 0.0 or value > 100.0:
            error(percent.out_of_range, "percentage must be 0 through 100")
        self.value = value

let opacity = try Percentage(75.0)
```

Declaring any `init` suppresses the synthesized memberwise initializer. A struct initializer assigns every field exactly once through `self` and returns `unit` or `unit!`; the construction expression itself produces `Struct` or `Struct!`. Constructors never overload; use named factories for alternatives.

### 10.2 Struct update

Structs have no object-spread syntax. A mutable local can update `var` fields, while immutable-domain transformations use named methods:

```luce
var cursor = Cursor(position: 0)
cursor.position = 8

let moved = point.translated(dx: 4.0, dy: 2.0)
```

This keeps copying visible through assignment and named APIs instead of hiding it behind a second construction language.

### 10.3 Tuples

Tuples are anonymous, positional values:

```luce
let pixel: (u8, u8, u8) = (12, 40, 255)
let (red, green, blue) = pixel
```

They have no named fields, methods, conformance, or one-element form. Use a struct for public or evolving data. The empty tuple `()` is the sole value of `unit`.

### 10.4 Fixed arrays

```luce
let magic: array[u8, 4] = [0x4c, 0x55, 0x43, 0x45]
```

`array[T, N]` is a fixed-size value whose length is part of its type. `N` must be a nonnegative compile-time integer. Arrays copy element-by-element, may live inline in another value, and convert explicitly to `slice[T]`. Epoch 1 has no user-defined compile-time value parameters; fixed array length is the one built-in exception.

### 10.5 Enums

An enum is a closed sum. A case may have no payload or may carry named values:

```luce
pub enum Direction:
    north
    east
    south
    west

pub enum Command:
    open(path: str)
    save(path: str)
    resize(width: u32, height: u32)
    quit
```

Cases are constructed as `Direction.north` and `Command.open(path)`, or as `.north` and `.open(path)` when the expected type is known. A payload is available only by exhaustive `match`; safe Luce exposes no discriminator integer or unchecked field projection.

Cases and payload labels/types are public when the enum is public. Adding a public case or changing a payload is a source-compatibility change because external exhaustive matches must be updated; API diff reports it explicitly. Numeric representations are assigned only in an explicit C export/import declaration; ordinary source must not depend on ordinals.

Payloads are stored inline when layout permits. A generic enum uses the same type-parameter rules as a generic struct or class. If a recursively defined tree requires indirection, place the recursive node in a class, handle, or collection; the compiler reports an infinite layout cycle and suggests the missing indirection.

### 10.6 Structural operations on values

The compiler synthesizes equality and hashing when every stored component supports them:

- `==` and `!=` compare full value structure.
- `hash(value)` is stable only within one process execution unless a type's library contract explicitly says otherwise.
- Floating-point fields retain IEEE equality behavior; this often makes such types unsuitable as map keys.

There is no user-defined operator overload. A domain needing unusual equality or ordering exposes named functions such as `same_identity`, `approximately_equal`, or `compare`.

### 10.7 Visibility and representation

`pub` controls source API visibility, not memory-layout exposure. An ordinary public struct may change its private layout between package versions. Stable native representation requires a dedicated `export c` declaration checked by the compiler. There is no general-purpose layout attribute in ordinary Luce source.

## 11. Reference identity and classes

A class represents shared identity. It is reference-counted, final, and never copied merely by assignment.

### 11.1 Declaration and construction

```luce
pub class Document:
    pub let title: str
    pub var dirty: bool
    var pages: list[Page]

    pub func init(self, title: str):
        self.title = title
        self.dirty = false
        self.pages = []

    pub func append(self, page: Page):
        self.pages.append(page)
        self.dirty = true
```

Construction is explicit:

```luce
let document = new Document("Notes")
```

Rules:

- Every class declares exactly one `init(self, ...)`; it returns `unit` or `unit!`, may have default parameters, but cannot be overloaded. A fallible construction is written `try new Class(...)`.
- `new` is used only for classes. Struct/enum construction does not use it.
- `init` returns no value and cannot publish `self` before all fields are initialized.
- Every field is assigned exactly once during initialization; later assignment requires `var`.
- Classes are final. There are no base classes, virtual overrides, protected members, or implicit interfaces.
- Alternative construction uses type functions returning the class, such as `Document.from_file(path)`.

### 11.2 Assignment and identity

```luce
let first = new Document("Draft")
let second = first

assert(first is second)
second.dirty = true
assert(first.dirty)
```

Class assignment retains and shares the same object. `is`/`is not` test identity. `==` is not available for classes; a class that needs domain equality supplies a named `equals` method. The closed value `Equatable` protocol does not turn identity objects into values.

A `let` binding prevents rebinding but does not freeze a class object. Mutation authority is stated on the class field and governed by any host/effect rules. This distinction is explained by diagnostics whenever a newcomer attempts to assign through an immutable field.

### 11.3 ARC lifetime

Each class reference is strong unless marked `weak`:

- Creating/copying a strong reference retains the object.
- Destroying/overwriting the reference releases it.
- The object is destroyed deterministically when its last strong reference is released.
- ARC operations are inserted by the compiler and may be optimized when observable behavior is preserved.

Normal source contains no `retain`, `release`, `free`, ownership transfer, or borrow annotations. The allocation inspector and generated intermediate representation can reveal ARC traffic when performance work requires it.

### 11.4 Weak references and cycles

```luce
class TreeNode:
    pub let name: str
    pub var children: list[TreeNode]
    pub weak var parent: TreeNode?

    func init(self, name: str):
        self.name = name
        self.children = []
        self.parent = none
```

A weak reference:

- never keeps its object alive;
- must have optional type `T?` where `T` is a class;
- becomes `none` atomically before destruction is observable;
- is read by taking a temporary strong reference for the resulting expression/scope.

A stored weak edge uses `weak var`; it must be able to become `none` when the object dies. `weak let` is therefore invalid. A weak closure capture is exposed as an immutable optional local because the hidden weak slot, not the local binding, changes.

For observer registries and other dynamic weak collections, the compiler-known value `Weak[T]` stores the same kind of slot:

```luce
let observers = list[Weak[Observer]]()
observers.append(Weak(observer))

for entry in observers:
    if let observer = entry.get():
        observer.refresh()
```

`T` must be a class; `get()` returns `T?`. Copying a `Weak[T]` copies the weak slot behavior and never retains the object. `Weak[T]` cannot cross workers or native safe-value boundaries.

Strong cycles leak because no count reaches zero. Every ownership graph must have a clear back-edge policy. The compiler diagnoses cycles it can prove directly, such as storing a closure on an object while the closure strongly captures that object, and suggests `weak` capture. Runtime leak tools report probable strongly connected components with allocation sites.

Luce does not add a tracing collector as an invisible second lifetime model. If real workloads demonstrate unavoidable dynamic cycles, an explicit library-managed cycle domain may be considered without changing ordinary class semantics.

### 11.5 Destruction and resources

```luce
class FileHandle:
    let native: native.file_handle
    var closed: bool

    func init(self, handle: native.file_handle):
        self.native = handle
        self.closed = false

    func close(self):
        if not self.closed:
            native.close_file(self.native)
            self.closed = true

    func deinit(self):
        self.close()
```

`deinit(self)` is an optional, non-failing class method run exactly once when the final strong reference disappears.

- It takes no arguments and returns `unit`.
- It cannot fail, spawn, publish `self`, or resurrect the object.
- Fields remain readable; calling arbitrary user code is linted because it can create reentrancy hazards.
- Field destruction follows the body in reverse declaration order.
- It cannot acquire ambient capability authority. A generated resource wrapper may invoke its audited non-failing release primitive using authority already embodied by the stored handle; that final release is lifetime behavior, not a new caller effect.

Resource types should offer an idempotent explicit `close` for prompt error-aware shutdown and use `deinit` as the safety net. `defer handle.close()` provides lexical cleanup when required. Thus resources close at the last release without making every programmer write ownership syntax.

### 11.6 No inheritance

Reuse is expressed through:

- composition for stored behavior/state;
- interfaces for interchangeable capability;
- generic functions for static reuse;
- plain helper functions for algorithms.

The absence of inheritance removes constructor chains, slicing, override rules, variance puzzles, fragile base classes, and a second identity-conversion system. C++ inheritance can be wrapped behind a flat generated interface but does not enter Luce's object model.

## 12. Allocation, storage, and collections

Allocation is predictable without forcing allocator parameters into every call. The language defines where allocation may occur; tooling exposes the actual sites and ARC operations.

### 12.1 Allocation rules

The following operations may allocate:

- `new Class(...)`;
- growing `list`, `map`, or `set` storage;
- constructing or concatenating dynamically sized strings/bytes;
- creating a closure environment or mutable capture cell;
- boxing a concrete value as an interface value when it does not fit the inline representation;
- spawning a worker and copying its input graph;
- native/imported calls whose contract declares allocation.

Plain scalar, tuple, struct, enum, optional, and fixed-array operations do not allocate by definition unless one of their stored members performs one of the operations above.

The optimizer may remove allocations but may not introduce an externally visible allocation failure or lifetime change where the source operation did not permit one.

### 12.2 Allocation failure

Ordinary allocation is not typed as `T!`. Out-of-memory is an uncatchable host/resource termination, because making every list append, string build, closure, and class construction syntactically fallible would poison the whole API graph without enabling reliable recovery in most hosts.

Programs that require bounded recovery use one of these explicit mechanisms:

- reserve/check capacity through library operations that return `T!`;
- allocate from a bounded arena or pool with a fallible API;
- run inside a LuciaOS host budget and treat exhaustion as task/process failure;
- stream data instead of materializing it.

This is a deliberate simplicity trade: recoverable scarcity is modeled by an explicit resource object, catastrophic heap exhaustion by the host.

### 12.3 Stack versus heap

Source does not promise a physical stack location for values. The semantic rules are:

- value types have value identity and copy semantics;
- class instances have stable reference identity;
- references captured or stored past a call remain valid;
- slices retain the storage owner described below.

The compiler may place values in registers, stack frames, inline object storage, or heap boxes while preserving those rules. The allocation inspector reports actual placement for a selected build/backend. No escape-analysis accident becomes public API.

### 12.4 `list[T]`

```luce
var names: list[str] = []
names.append("Ada")
names.append("Grace")
```

`list[T]` is a mutable, growable, ARC-backed collection with reference identity. Copying a list binding shares the same list; use `names.copy()` for an explicit shallow copy. Elements retain their ordinary value/reference semantics.

As with a class, a `let` list binding prevents rebinding, not mutation of the shared collection. `var` is needed only when the binding itself will point to a different list. The same rule applies to `map` and `set`; APIs use frozen collections when deep immutability is required.

Core operations include `length`, indexed get/set, `append`, `insert`, `remove_at`, `clear`, `reserve`, `copy`, and immutable slicing. Bounds are checked. Reallocation does not invalidate safe slices because slices retain a specific immutable storage snapshot; mutating a list may first detach that snapshot (copy-on-write storage is an implementation detail, not list value semantics).

Structural modification during active iteration traps with a precise diagnostic in checked builds. Element field mutation that does not change collection shape is allowed when its type permits it.

### 12.5 `map[K, V]` and `set[T]`

Maps and sets are mutable ARC-backed reference collections. They preserve insertion order for iteration, making logs, tests, and user interfaces deterministic. Keys/elements must support structural equality and hashing.

```luce
let counts = map[str, u64]()
counts["apple"] = 3

let tags = set[str]()
tags.insert("important")
```

Map lookup returns `V?`; indexing does not silently insert a default. Mutating during iteration follows the same rule as list. Explicit `.copy()` creates a shallow independent collection.

Deterministic insertion order is not a promise of stable hash values or serialized representation. Serialization is an explicit library operation with a specified format.

### 12.6 Immutable slices

`slice[T]` is an immutable, bounds-checked view of a contiguous sequence:

```luce
let header: slice[u8] = packet.bytes()[0..<16]
```

A safe slice contains a pointer-like location, a length, and enough hidden ownership to keep its storage alive. It can be returned, stored, or passed without a user-visible lifetime parameter. Slicing is half-open and O(1).

- Reading an element follows `T`'s normal semantics.
- A slice cannot resize or replace elements.
- A slice made from mutable storage observes the immutable snapshot captured at creation, not later structural mutation.
- A native borrowed span is copied or wrapped in an explicit native-lifetime object before it becomes an unrestricted safe slice.

Algorithms needing temporary mutable access use closure-scoped library APIs:

```luce
buffer.with_mutable_slice(func (view: mutable_slice[u8]):
    fill(view, 0)
)
```

`mutable_slice[T]` is a compiler-known, non-storable callback parameter type: it cannot be returned, captured, placed in a field, or cross a worker/native boundary. This one restricted facility supports efficient I/O and compiler work without exposing general lifetime algebra. It is not part of ordinary public data modeling.

### 12.7 Strings, characters, and bytes

`str` is an immutable, valid UTF-8 string. `char` is one Unicode scalar value. User-perceived grapheme clusters are a Unicode-library concept, not a primitive type.

Important consequences:

- A string has `byte_count` in O(1).
- `str.length()` counts Unicode scalar values and is O(n).
- `for character in text` iterates Unicode scalar values.
- `str` does not support integer indexing; code must iterate, use an explicit scalar iterator, or operate on UTF-8 bytes.
- `text[a..<b]` is unavailable for integer indices because byte and scalar boundaries differ. Library operations return validated substrings from explicit indices/iterators.

Strings preserve the scalar sequence supplied; they are not normalized implicitly. Equality compares exact scalar/UTF-8 content, and built-in ordering is deterministic scalar-value order—not locale collation. Unicode normalization, grapheme segmentation, case folding, locale display, and collation are explicit versioned library operations.

`bytes` is an immutable byte sequence with O(1) length, indexing, and slicing. Text decoding is explicit and fallible:

```luce
let text = try utf8.decode(data)
let data = utf8.encode(text)
```

Concatenation may allocate. Builders in the standard library are preferred for repeated assembly. Strings and bytes use content equality/hash.

### 12.8 Arenas and special storage

An arena, pool, memory map, GPU allocation, or native buffer is a standard-library/native resource, not a language allocation mode. A typical arena API returns typed generational handles rather than unrestricted borrowed references:

```luce
let node_id: arena.Handle[Node] = try nodes.insert(node)
if let current = nodes.get(node_id):
    visit(current)
```

Generation checks prevent stale handle reuse. Closure-scoped access can provide temporary mutable views. This gives compilers and games compact storage without importing borrow annotations into every Luce API.

### 12.9 Cost inspection

The first-party toolchain must answer, for a source range:

- which operations allocate and why;
- value copy size and whether it was elided;
- ARC retain/release sites and whether they were optimized;
- interface boxing/dynamic dispatch;
- bounds checks and whether they were removed;
- worker-copy volume;
- native bridge crossings.

These facts are available as editor hints, structured compiler output, and an explain command. Predictable cost comes from observable tooling plus simple semantics, not from making low-level syntax mandatory everywhere.

## 13. Absence, failure, and traps

Luce separates three conditions that languages often blur:

1. **absence** is ordinary data, represented by `T?`;
2. **recoverable failure** crosses a function boundary as `T!` plus `Error`;
3. **a trap or host termination** means a violated invariant or exhausted execution environment and is not catchable.

There are no nullable references, thrown objects, exception hierarchies, typed error-set algebra, or implicit error conversions.

`error`, `trap`, and `assert` are compiler-known core functions, not statement keywords. Their ordinary call shape keeps the grammar small; their `never` result and context rules provide the required control-flow precision.

### 13.1 Optional values

`T?` contains either `.some(T)` or `.none`:

```luce
func find_user(id: UserId) -> User?

let user = find_user(id)
if let found = user:
    show(found)
```

`none` must have an expected optional type. A non-optional value may be promoted to `T?` where expected. The reverse always requires conditional binding, `match`, or the explicit `else` fallback below.

Optionals are one layer: applying `?` to an optional type is rejected. If a domain genuinely distinguishes “outer absent” from “present but inner absent,” it declares an enum with names for those states. A fallible function returning an optional is written `T?!`: success carries `T?`, failure carries `Error`.

Epoch 1 adopts stage-0's `else` form — one keyword, three arms, each a statement of intent at the point of absence:

```luce
let count = parse_i64(text) else 0                        # fallback value
let n = parse_i64(text) else trap("not a number")         # assert with a stated reason
let w = create_window() else error("no window")           # absence becomes failure, in a `!` function
```

`a else b` yields `a` when present and `b` otherwise; the arm may instead diverge through `trap(…)` or `error(…)`. The diverging arms are what keep boundary code flat: acquisition sequences (window, then surface, then device) nest under `if let` but read line by line under `else`. Ruled in 2026-08-24 on native-interop evidence, satisfying the reconsideration clause this section previously carried; stage-0 practice showed no second-expression-language effect.

Optional chaining and a bare force-unwrap operator remain omitted. `else trap("reason")` is the explicit spelling of an assert-unwrap — it exists precisely so an unstated `x!` never needs to.

### 13.2 Recoverable function failure

`T!` means “returns `T` or a recoverable `Error`”:

```luce
func load_config(path: str) -> Config! uses files:
    let data = try files.read(path)
    return try config.parse(data)
```

`try expression` is valid only when the expression has type `T!`. On success it produces `T`; on failure it returns the same error from the current fallible function. A non-fallible caller must handle the failure with `catch`.

A unit-returning fallible function is written `unit!`. Fallibility is part of function type and public API compatibility.

Applying `!` to a fallible type is rejected. Failure does not nest; a handler either recovers to the success type or propagates one `Error`.

### 13.3 Creating an error

The built-in terminator is:

```luce
error(files.not_found, "configuration file does not exist")
```

It is legal only within a fallible function or a `catch` handler. Its code is a stable domain-qualified `ErrorCode`; its message is human-readable diagnostic context. The expression has type `never`.

The standard error value is deliberately small:

```luce
pub struct Error:
    pub let code: ErrorCode
    pub let message: str
```

`ErrorCode` is a small structural value containing a package-stable domain identifier and a `u32` value. The compiler/package tool assigns the domain identity and preserves a symbol table in diagnostics; declarations such as `files.not_found` are typed public constants. Codes do not allocate, collide across packages, or depend on localized text.

A package declares a code as a public top-level constant:

```luce
pub let not_found: ErrorCode = ErrorCode.package(1)
```

`ErrorCode.package(number)` is a restricted compile-time constructor that tags the number with the declaring package identity. The package checker requires numbers to be unique within that identity and publishes their symbolic module-qualified names. Runtime code cannot manufacture another package's code.

Runtimes may attach a source trace and causal metadata outside the source-visible value. Libraries publish their codes as names such as `files.not_found`, never magic integers or message parsing.

If callers need structured domain data—an HTTP status, parser span, or validation fields—the public result should be an enum whose cases carry those values. `Error` is for propagation and diagnostics, not a dynamically typed payload container.

### 13.4 Local recovery with `catch`

```luce
let text = files.read(path) catch failure:
    if failure.code == files.not_found:
        recover ""
    error(failure.code, f"cannot load settings: {failure.message}")
```

`fallible_expression catch error_name:` handles only failure from that expression:

- The handler executes only on failure.
- `error_name` is an immutable `Error` binding.
- `recover value` completes the whole construct successfully with the original success type.
- The handler must either `recover`, terminate with `error`/`trap`, or return from the surrounding function on every path.
- If the handler re-emits an error, the surrounding function must be fallible.

`catch` binds more weakly than every ordinary operator, so parentheses are rarely needed. It is expression-local rather than a statement wrapping arbitrary code; this keeps the failing operation and its recovery adjacent and removes stack-unwinding region semantics.

### 13.5 Error context

Propagation preserves error code and source trace. Libraries add context only when it helps a human locate the operation:

```luce
func read_project(path: str) -> Project! uses files:
    let text = files.read_text(path) catch failure:
        error(failure.code, f"reading project at {path}: {failure.message}")
    return try project.parse(text)
```

The linter flags errors discarded without an explicit policy. A package may define a small context helper, but error wrapping never changes the stable code accidentally.

### 13.6 Traps

`trap(message)` unconditionally stops the current execution domain and has type `never`. The compiler also inserts traps for safety violations that cannot occur in correct typed code, including:

- out-of-bounds access;
- integer overflow in a checked operation;
- division by zero;
- failed internal invariant checks;
- invalid native contract use detected by a checked wrapper — including a
  null token crossing a non-nullable extern slot (`null_foreign`) and C
  text that is not valid UTF-8 arriving where a `str` was declared
  (`invalid_utf8`), both checked at the boundary in every profile
  (§21.16).

Traps are not recoverable errors. They produce a diagnostic with source location and stack trace, then terminate the task/process according to host policy. Turning them into catchable exceptions would allow execution after memory or program invariants were already suspect.

### 13.7 Host termination

Out-of-memory, stack/call budget exhaustion, forced cancellation, instruction-budget exhaustion, and host revocation are uncatchable host terminations. LuciaOS records them as structured task/process outcomes so supervisors can restart or report them, but user code cannot suppress them inside the affected domain.

### 13.8 Assertions

```luce
assert(index < items.length, "index must have been validated")
```

`assert` traps when its Boolean condition is false. Assertions are never removed in a way that changes memory safety; release profiles may omit assertions explicitly marked as diagnostic-only through a testing/library API, not through a general language attribute.

## 14. Closures and capture

A closure is an anonymous function plus an environment. A single-expression
closure uses `=>` to yield its value:

```luce
let positive: func(i64) -> bool = (value) => value > 0
```

The expected function type supplies the parameter and result types, so passing
a lambda remains statically checked:

```luce
func accepts(value: i64, predicate: func(i64) -> bool) -> bool:
    return predicate(value)

let large = accepts(8, (value) => value > 5)
```

A parameter may include its type for clarity, as in
`(value: i64) => value > 0`, but an expression lambda still requires an
expected function type. `=>` yields from the lambda; it does not return from
the enclosing function. The block form handles multiple statements, explicit
capture policy, or an explicit result/effect signature:

```luce
let double = func (value: i64) -> i64:
    return value * 2
```

Both forms use the capture rules below. Block-closure parameter and return
rules are identical to named functions. Effects and fallibility are written
when required by the expected type or inferred for a local closure and then
checked at conversion.

### 14.1 Default captures

When a closure refers to an outer local:

- an outer `let` value is copied into the closure;
- an outer class/reference value is retained strongly;
- an outer `var` local is promoted to one shared mutable ARC-managed cell seen by the scope and every capturing closure.

This makes the common counter/callback case work without reference syntax while preserving visible `var` mutation:

```luce
var count = 0
let next = func () -> i64:
    count += 1
    return count
```

Creating a shared cell may allocate. The compiler's cost explanation identifies it and suggests an explicit value snapshot when sharing was accidental.

### 14.2 Capture list

Capture policy can be made explicit:

```luce
let handler = func [copy snapshot = counter, weak owner] (event: Event):
    if let target = owner:
        target.handle(event, snapshot)
```

- `copy name = expression` evaluates once and stores a value snapshot under `name`.
- `weak name` weakly captures a class reference and exposes it inside as an optional.
- `weak self` is the receiver-specific spelling of the same weak capture and is used to break a closure cycle with its owning class.
- Capture expressions evaluate left-to-right when the closure is formed.

There is no capture-by-borrow, capture-default punctuation, or ownership-transfer capture. Native callback lifetimes use generated adapters and explicit resource objects.

### 14.3 Escaping and cycles

Closures are safe to store and return. Their environments live as long as the last closure reference. A closure can therefore participate in ARC cycles:

```luce
class Controller:
    var callback: (func() -> unit)?

    func init(self):
        self.callback = none
```

If a closure stored by `Controller` strongly captures that same controller, the compiler diagnoses the direct cycle and offers `weak controller`. More dynamic cycles remain visible to leak tooling.

### 14.4 Sendability

Closures never cross worker boundaries in epoch 1, even when their captures appear copyable. The spawned function is a statically named function, and its arguments form the copied message. This restriction makes code shipment, effects, lifetime, and determinism auditable.

## 15. Generics

Generics provide reusable static algorithms without runtime reflection or template metaprogramming.

### 15.1 Generic declarations

```luce
func first[T](values: slice[T]) -> T?:
    if values.length == 0:
        return none
    return values[0]

struct Pair[A, B]:
    pub let first: A
    pub let second: B
```

Type parameters are declared once in square brackets. Calls normally infer them from arguments; explicit arguments use the same notation when inference is impossible: `decode[Header](bytes)`.

Type parameters have no defaults. A generic struct/enum/class is constructed through its ordinary initializer after arguments are inferred or written; there is no separate template-call syntax.

Generic public functions must type-check from their declaration and written constraints alone. They do not accept arbitrary syntax that happens to compile for one instantiation.

### 15.2 Constraints

```luce
func maximum[T: Comparable](left: T, right: T) -> T:
    if left.compare(right) >= 0:
        return left
    return right

func encode_key[T: Hashable & Encodable](value: T) -> bytes!:
    return try value.encode()
```

A constraint is one or more interfaces joined by `&`. There are no negative constraints, specialization clauses, concepts-as-predicates, or arbitrary compile-time expressions.

### 15.3 Implementation model

Generic code is monomorphized by default for concrete value types. The compiler may share machine code for representation-compatible instantiations when behavior, diagnostics, and optimization remain equivalent. This is not source-visible.

Separate compilation uses serialized typed generic bodies in package artifacts. Users do not include source text manually, and ABI tooling distinguishes source compatibility from already-specialized binary compatibility.

The compiler tracks every instantiation's origin, code size, check/codegen time, and recursive type expansion. It rejects an infinite instantiation chain and reports a configurable package build budget before generic expansion can silently consume unbounded time or disk. `luce explain` shows the call/type path that created each instance.

### 15.4 Deliberate limits

Epoch 1 has:

- type parameters, but no general value/const parameters;
- no variadic generics;
- no higher-kinded types;
- no generic parameter packs;
- no conditional members or partial specialization;
- no compile-time reflection or code execution;
- no user-specified variance;
- no associated types in user interfaces.

`array[T, N]` is the only compiler-built fixed value parameter. Standard protocols that need an element type use a compiler-understood generic interface such as `Iterable[T]`, not associated-type machinery.

## 16. Interfaces and dynamic abstraction

An interface is a nominal set of callable requirements. It contains behavior, never storage or inherited implementation.

### 16.1 Declaration and conformance

```luce
pub interface Writer:
    func write(self, data: slice[u8]) -> u64! uses files
    func flush(self) -> unit! uses files

pub class FileWriter implements Writer:
    # fields and implementations
```

Rules:

- User-defined conformance is declared explicitly in the type definition with `implements`. The only exception is compiler-derived structural recognition for the closed value `Equatable`/`Hashable` protocols described in section 17.2.
- A type may implement multiple interfaces, written `implements First, Second`.
- Every required method is supplied directly by the type with the exact signature.
- An implementation may be non-fallible where a requirement is fallible and may use a subset of the requirement's effects; adapters lift it safely. It may never add failure or effects hidden by the interface.
- Interfaces cannot inherit from interfaces.
- Interfaces cannot provide default method bodies.
- A package cannot retroactively make another package's type conform.
- There are no optional requirements, dynamic member lookup, or reflection over conformances.
- Interface requirements are instance methods and implicitly public; interfaces contain no constructors, type functions, fields, properties, generic methods, or nested declarations.

These restrictions keep conformance globally discoverable and avoid “action at a distance.” Reusable default behavior is an ordinary generic function constrained by the interface.

### 16.2 Static use

```luce
func write_header[W: Writer](writer: W, header: Header) -> unit! uses files:
    discard(try writer.write(header.bytes()))
```

A constrained generic is statically dispatched and normally monomorphized. It does not allocate merely because an interface is named in the constraint.

### 16.3 Interface values

```luce
func active_writer() -> Writer! uses files:
    return new FileWriter(...)
```

Using an interface directly as a type creates an interface value containing a concrete value/reference plus a method table. Calls dynamically dispatch. Small values may be stored inline; larger values may be boxed. A value conformer retains value-copy semantics (a shared hidden box detaches before mutation); a class conformer retains its existing shared identity. Physical boxing never changes the source type's semantics.

Calling a `mutating` requirement through an interface value requires that interface binding to be `var`. A boxed value is uniquely updated after any required detach; a class conformer mutates its ordinary identity. The compiler exposes both cases in cost/type hover.

The allocation/cost inspector reports boxing and dynamic calls. Equality, hashing, serialization, downcasting, and concrete-type inspection are not automatically available on interface values. Add the required operation to a domain interface or keep the concrete type.

### 16.4 No downcasts

Safe Luce has no general `is Type`, `as Type`, or reflective downcast from an interface. Identity `is` compares compatible shared references; it is not a type test. An abstraction whose users routinely need to recover concrete cases should be a closed enum, or should expose the needed operation in its interface.

Native imported polymorphism may expose an explicit generated query function returning an optional wrapper, but that remains a named foreign operation rather than universal runtime type inspection.

## 17. Closed standard protocols

The compiler and standard library jointly define a very small set of protocols needed by syntax. They obey ordinary interface semantics but are versioned with the language epoch.

### 17.1 Iteration

```luce
pub interface Iterator[T]:
    mutating func next(self) -> T?

pub interface Iterable[T]:
    func iterator(self) -> Iterator[T]
```

`for item in source` is specified as repeated `next()` calls on a private mutable iterator returned by `source.iterator()`. `mutating` requires a value iterator to update itself; a class iterator satisfies the requirement with an ordinary identity-mutating method. Implementations may receive compiler optimizations, but observable order and mutation checks remain the same.

Epoch 1 uses this generic form instead of user-defined associated types. An iterable exposes one canonical element type. Alternative traversals are named adapter methods returning other iterable values.

### 17.2 Equality, hashing, and ordering

`Equatable`, `Hashable`, and `Comparable` are standard compiler-known interfaces used by generic libraries.

- `Equatable`/`Hashable` are recognized structurally for tuples, arrays, structs, enums, optionals, and frozen collections when every component qualifies. This derived behavior cannot be customized; unusual domain comparison uses a named function.
- `Hashable` supplies process-local hashing and is deliberately not an inherited interface; key APIs require both `Equatable & Hashable`.
- `Comparable` supplies a three-way `compare` with a total-order contract and requires explicit conformance/implementation; composite ordering is too domain-dependent to synthesize automatically.

The derived structural recognition is closed compiler behavior, not a retroactive-conformance system. No interface enables arbitrary operators. The compiler owns the small built-in operator mapping, and diagnostics explain the named requirement it uses.

### 17.3 Formatting and encoding

Debug formatting, user-facing display, and serialization are distinct library interfaces. String interpolation uses `Display` for public values and a diagnostic fallback only in debug tooling. It never invokes reflection over private fields in production code.

The list of compiler-known protocols is closed for epoch 1. New syntax cannot secretly opt into user-defined behavior through naming conventions.

## 18. Effects and host capabilities

Effects state which host-controlled capabilities a function may use. They are not exceptions, asynchronous markers, or a general academic effect calculus.

### 18.1 Declaring effects

```luce
pub func fetch_manifest(url: Url) -> Manifest! uses network, clock, log:
    let response = try network.get(url)
    log.debug(f"received at {clock.now()}")
    return try manifest.parse(response.body)
```

A public function that directly or transitively uses host capability must declare its effect set with `uses`. The complete epoch 1 standard effect vocabulary is:

- `files`
- `network`
- `clock`
- `random`
- `process`
- `environment`
- `terminal`
- `log`
- `graphics`
- `audio`
- `device`
- `unsafe_native`

Packages may define finer capability interfaces, but not new effect grammar. A host profile maps imported capability values/modules to this closed auditable vocabulary.

### 18.2 Inference and checking

Private function effects may be inferred, and the editor displays them. Public functions spell them so an API review sees host authority without inspecting the body.

- Calling a function requires the caller to allow every callee effect.
- Effects propagate transitively unless a host boundary explicitly supplies/contains the capability.
- A function with no `uses` clause is pure with respect to host capabilities.
- Local allocation, ARC, arithmetic traps, and ordinary mutation are not effects.
- Fallibility and effects are orthogonal: a function may have either, both, or neither.

Function types include their effect set:

```luce
let loader: func(str) -> bytes! uses files = files.read
```

A less-effectful function may be used where a superset is permitted, never the reverse.

### 18.3 Capability access

Effect names do not conjure ambient global authority. Standalone entry points receive a runtime context, while LuciaOS components import capabilities granted by their manifest/host. The surface API may feel module-like (`files.read`), but resolution is to a host-provided capability handle recorded in the component's typed environment.

Tests replace capabilities with deterministic implementations without global monkey-patching. Package manifests request capabilities; the launcher shows and enforces the resulting grant set.

### 18.4 Unsafe native effect

Raw native operations — the pointer verbs of §21.12: loads, stores, address arithmetic, ABI casts — require `uses unsafe_native`. A safe wrapper validates invariants and exposes an ordinary effect such as `files` or no host effect at all. The compiler can therefore show exactly where memory-safety trust enters the program.

**An extern call is not a raw native operation** (ruled 2026-08-24). The checked boundary of §21.16 — the `null_foreign` trap, validated text, the optional decode — is the safety story for the common shape, so calling a declared extern requires no `unsafe_native`: the trust is visible in the declaration, not gated at the call. What the call *does* carry is whatever ordinary effect its wrapper declares; the raw-memory vocabulary stays reserved for operations that actually touch memory Luce cannot check.

### 18.5 Why effects remain small

Epoch 1 does not model every mutation, allocation, lock, error, or I/O subtype as an effect. The purpose is adoption and host security: make externally meaningful authority reviewable. If an effect cannot be enforced or productively used by the host/toolchain, it does not belong in the language.

## 19. Isolated concurrency

Luce epoch 1 has tasks without shared-memory concurrency. A task runs a named function in an isolated worker with copied input values.

### 19.1 Spawning and waiting

```luce
func render_scene(scene: Scene) -> Image! uses graphics:
    # CPU/GPU work

let work: task[Image] = spawn render_scene(scene)
let image = try work.wait()
```

`spawn function(arguments...)`:

1. verifies that the callee is a statically named function allowed by the current host profile;
2. verifies the complete argument graph is sendable;
3. copies/serializes that graph into a new worker domain;
4. begins execution and returns `task[T]` immediately.

The spawn expression carries the named function's effect set: the parent must declare/be granted it, and the worker receives only those host capabilities. `task[T].wait()` returns `T!`. The worker's return value is copied back when it succeeds. A worker error crosses as `Error`; a trap or host termination maps to stable codes such as `task.trapped`, `task.cancelled`, or `task.resource_exhausted` with its remote trace attached as diagnostic metadata. Repeated waits on the same task return a value copy of the cached result/error.

### 19.2 Sendable data

A type is sendable when its entire reachable representation is immutable copied data:

- numbers, Boolean, character, string, bytes;
- tuples, fixed arrays, structs, enums, and optionals whose contents are sendable;
- immutable snapshots of lists/maps/sets created explicitly for transfer;
- host-defined transferable resource tokens with generated semantics.

These are not sendable:

- class references and weak references;
- mutable collection identity;
- closures and mutable capture cells;
- interface values;
- tasks;
- native pointers/borrows;
- open resources unless the host defines an explicit transferable token.

The compiler derives sendability structurally and prints the exact field/path that prevents it. There is no `unsafe Sendable` conformance in ordinary source.

### 19.3 Collection transfer

Calling `collection.snapshot()` produces an immutable sendable value graph by recursively copying elements and rejecting non-sendable ones. The cost inspector estimates transfer bytes. The language never silently shares collection backing storage between workers.

### 19.4 Task lifetime and cancellation

A task is structured without introducing general ownership syntax:

- Every `spawn` belongs to the current function invocation's implicit task group. Extract work into a helper function when a narrower lifetime is desired.
- `task[T]` handles may be aliased locally, waited more than once, and stored in a local list for dynamic fan-out. A task or any local container holding one cannot be returned, stored in an object, captured by an escaping closure, passed to an unknown callee, or sent to another worker.
- On function exit, the runtime requests cancellation of unfinished children and joins all of them before function-scope resources/deferred cleanup are released; this includes return and error paths.
- `work.cancel()` requests early cancellation without detaching the child.
- Host cancellation is cooperative at safe points, but forced budget termination remains possible and uncatchable inside the worker.

There is no detached spawn in epoch 1. Long-lived services are owned by LuciaOS/process supervisors, not orphaned language tasks. The non-escaping task rule is compiler-known in the same narrow spirit as temporary mutable slices and does not create user-written lifetime parameters.

### 19.5 Deliberate omissions

Epoch 1 has no `async`/`await`, futures combinator language, threads, locks, atomics, channels, actors, or shared heap. Evented I/O can be implemented by the host/runtime behind synchronous-looking fallible APIs, while CPU parallelism uses isolated workers.

This is intentionally conservative. Concurrency features multiply interactions with ARC, closures, native code, errors, effects, and debugging. Add a message-channel abstraction only after compiler/runtime workloads demonstrate that spawn/wait plus host event loops cannot express a required design.

## 20. Modules, packages, and visibility

The module system makes dependencies explicit and keeps build behavior reproducible. It is not a second programmable language.

### 20.1 Files and modules

One `.luc` file defines one module. Its module path is derived from its package-relative path:

```text
src/image/color.luc  -> image.color
```

There is no module declaration boilerplate in the file and no source-level re-export. The manifest lists the package's public module paths; consumers import the module that owns a declaration.

Module dependency cycles are compile errors. The diagnostic prints the shortest cycle and suggests the declaration that can be moved into a lower-level module.

### 20.2 Imports

```luce
import image.color
import data.serialization as serial
from image.geometry import Point

let foreground = image.color.black()
let result = serial.decode[Project](bytes)
let origin = Point(x: 0.0, y: 0.0)
```

`import` keeps a module qualified, with an optional short module alias. `from`
imports one or more named public declarations into the current module. Selective
imports have no per-name alias; when names collide, import the module with an
alias and keep the use qualified. Epoch 1 has no wildcard, relative, re-export,
or implicit prelude imports. The small built-in type/function set is always in
scope; everything else has a visible origin at the leading import block.

Imports must appear before declarations. Unused and duplicate imports are errors in checked package source, with automatic removal fixes.

### 20.3 Visibility

Declarations and stored fields are module-private by default. `pub` exposes a declaration through the package's source API. The short spelling mirrors `func`: visibility is explicit without dominating an intentionally small API.

```luce
pub func parse(text: str) -> Document!
```

There is no `protected`, package-private keyword, friend declaration, or visibility hierarchy. A package can group implementation into a module or expose a small public facade.

Public signatures may mention only public types from declared public dependencies. The compiler produces a machine-readable API surface and compatibility diff.

### 20.4 Top-level declarations

A module may contain type, type-alias, function, interface, import, test, and constant declarations, plus the native boundary forms: `export c` (section 21.5) and `extern` (section 21.16) declarations. Except for closures, declarations do not nest: functions contain statements, and types contain only fields/methods. A module may not contain executable statements or mutable globals.

```luce
pub let max_header_size: u64 = 16 * 1024
```

A top-level `let` initializer is a restricted compile-time constant expression containing literals, arithmetic, tuples/fixed arrays, enum cases, memberwise construction of constant value types, and named compiler constructors such as `ErrorCode.package`. It cannot allocate dynamic storage, call arbitrary user code, fail, use effects, or depend on initialization order.

Global mutable state belongs in an explicitly constructed class owned by the application/host. This removes module initialization races and makes tests independent.

### 20.5 Entry points

A standalone executable exports one conventional entry function:

```luce
pub func main(arguments: slice[str]) -> i32! uses files, environment:
    return 0
```

The compiler validates its profile-specific signature. LuciaOS components instead export manifest-declared handlers with generated typed capability inputs. There is no arbitrary top-level execution.

### 20.6 Package manifest

Every package has one declarative `luce.toml` manifest and one exact generated `luce.lock`. The manifest records:

- package name, version, language epoch, and source roots;
- products (library, executable, LuciaOS component, native bridge);
- exact dependency requirements and public/private dependency status;
- requested host capabilities;
- native headers/libraries and binding recipes;
- supported target/profile constraints;
- test source roots, test-only dependencies/capability policy, and documentation products.

Resolution produces a content-addressed lockfile. Builds are hermetic by default. There are no package build scripts, compiler plugins, arbitrary command hooks, environment-variable probing, or network access during compilation. Native generation uses first-party declarative binding rules; exceptional code generation happens as an explicit pre-build project step whose output is checked into or supplied as source.

Test-only dependencies are resolved and locked by the same package graph but are visible only to modules in declared test source roots. Inline tests in product modules may use the compiler-known `testing` standard module and the product's ordinary dependencies; they cannot smuggle an external test dependency into production source. A production build computes reachability after removing test declarations, so test-only imports, dependencies, capabilities, symbols, and description strings are absent from its artifact.

### 20.7 Dependency identity

One build graph contains one resolved identity/version for each package unless dependencies are explicitly namespaced as separate packages. Type identity includes package and module, preventing accidental equivalence between same-spelled types.

The package manager reports why every dependency is present, audits licenses/advisories, and can emit a minimal reproducible source bundle. Adoption depends as much on trustworthy packages as on syntax.

### 20.8 Platform variation

Epoch 1 has no conditional-compilation directive in source. `luce.toml` may select target-specific source roots and native bindings through declarative target predicates; each selected module must still present the public API promised by the package. Ordinary code depends on a portable interface module whose implementation is chosen by the package graph.

Runtime variation is queried through explicit library/capability APIs, not compile-time name tests. This avoids preprocessor dialects while still supporting operating-system and architecture adapters.

## 21. Native interoperability

Native interop is a first-class compiler subsystem with a safe generated layer, not a promise that arbitrary foreign code is automatically safe. C follows Zig's directness; C++ follows Swift's importer/bridging approach while preserving Luce's smaller semantics.

### 21.1 Architecture

All native imports pass through a backend-independent **Foreign Interface IR (FIIR)**:

```text
C/Objective headers --Clang--> FIIR --Luce importer--> raw module --> safe wrapper
C++ headers ---------Clang--> FIIR --bridge generator--> C ABI thunks + raw module --> safe wrapper
```

FIIR records declarations, layouts, calling convention, ownership, nullability, mutability, lifetimes at the boundary, exceptions, target conditions, and source provenance. The Luce type checker consumes FIIR; LLVM is not required to understand C++.

This distinction is fundamental: Swift's C++ interop comes primarily from Clang's parser/type system/importer plus generated ABI-aware calls—not from LLVM itself. Luce can keep the same front-end model while targeting LLVM, its own backend, or both.

### 21.2 The three layers

Every substantial binding has three visible layers:

1. **Foreign declaration**: Clang's exact understanding of the header.
2. **Raw native module**: mechanically generated Luce-shaped access, marked unsafe.
3. **Safe wrapper module**: reviewed ordinary Luce API with ownership, absence, failure, slices, and resource behavior made explicit.

Generated files identify their source header, flags, target, generator version, and binding recipe. Users debug through them and can regenerate deterministically.

### 21.3 C import

A package manifest declares a C binding target:

```toml
[native.sqlite]
language = "c"
headers = ["sqlite3.h"]
libraries = ["sqlite3"]
```

Source imports its generated module normally:

```luce
import sqlite.raw
```

The C importer supports:

- integer/floating types with target-correct widths;
- enums, structs, unions, constants, and function declarations;
- pointers, arrays, function pointers, and opaque types;
- calling conventions and platform conditions;
- explicit variadic functions only through generated typed adapters.

C types live under clearly named native types such as `c.int`, `c.size`, and `native_ptr[T]`; they never silently equal portable Luce integers. Conversions are explicit and checked.

### 21.4 C ownership and nullability

C headers rarely contain enough lifetime information. A declarative binding recipe supplies facts the header cannot:

```toml
[[native.sqlite.function]]
name = "sqlite3_open_v2"
result = "status"
out.0 = "owned sqlite3 via sqlite3_close"
string.1 = "utf8 borrowed for call"
```

The generator uses this to produce:

- `T?` for nullable pointers;
- owner classes with idempotent close/deinit for acquired resources;
- `slice[T]` or closure-scoped mutable views for pointer-plus-length pairs;
- `T!` plus stable errors for status-code APIs;
- explicit callbacks with lifetime tokens;
- copied values when a foreign borrow cannot safely escape.

Raw access remains available only in an `unsafe_native` function. Missing ownership facts are a generation error for safe wrappers, never a guessed convention.

### 21.5 C export

```luce
export c struct Pixel:
    let red: u8
    let green: u8
    let blue: u8
    let alpha: u8

export c func luce_blend(left: Pixel, right: Pixel) -> Pixel:
    # ...

export c enum BlendStatus as u32:
    ok = 0
    invalid_color = 1
```

`export c` accepts only a closed C-compatible subset with fixed representation. The compiler generates a header and ABI report. Fallible exported functions use generated status/result forms; classes, strings, collections, interface values, and Luce ARC never leak directly across the ABI.

Exported enums spell a fixed integer representation and every numeric value; exported structs use declaration-order C layout and only C-compatible fields. Every exported struct field is inherently part of both the generated source API and native ABI, so a redundant `pub` modifier is rejected. An exported function uses a declared C calling convention, cannot unwind, and receives explicit handles/callbacks for host authority. A Luce trap at an export boundary follows the product's fatal-trap policy and is never presented to C as an ordinary error.

Opaque exported handles carry runtime/worker-domain affinity. The generated C API either validates that a call enters the owning domain, marshals a declared sendable request through a runtime entry queue, or rejects the operation; it never permits two foreign threads to mutate one ordinary Luce object concurrently.

ABI checking compares size, alignment, field offsets, symbol names, calling convention, and target. An incompatible change fails release validation unless the package deliberately changes its native ABI version.

### 21.6 C++ import strategy

C++ bindings use Clang to understand declarations and a generated bridge compiled by the platform C++ compiler. The stable Luce-facing baseline is a flat C ABI thunk surface:

```text
Luce call -> generated C ABI thunk -> C++ method/function
```

An LLVM backend may later optimize or LTO across the bridge when toolchains match, but correctness and source semantics cannot depend on that. A custom x64/ARM64 backend calls the same thunks and therefore retains full supported interop.

### 21.7 Supported C++ subset

The importer should support, in staged order:

- free functions, namespaces, enums, POD/value structs, and constants;
- constructors/destructors and methods through opaque owner wrappers;
- references/pointers with recipe-specified borrow/ownership;
- `std::string`/`string_view`, spans, vectors, optionals, and expected-like types through blessed adapters;
- explicit template instantiations listed in the manifest;
- callbacks represented by generated context-pointer thunks and lifetime tokens;
- selected virtual interfaces wrapped behind generated flat functions.

The following do not become Luce language features:

- C++ inheritance and overload sets;
- operator overloads and implicit conversions;
- reference/lifetime syntax;
- templates/metaprogramming;
- exceptions or RTTI/downcasts;
- header macros.

The importer maps an overload set to stable semantic names, using binding-recipe overrides when mechanical names are poor. It wraps inheritance through composition/interface-shaped APIs. Users see Luce, not transliterated C++.

A C++ default argument becomes an ordinary Luce default only when Clang/FIIR proves it is a safe portable constant. Otherwise the generator emits a semantically named wrapper that supplies it inside C++, avoiding hidden foreign evaluation at each call.

### 21.8 C++ exceptions and failure

No C++ exception crosses a Luce frame. Every generated thunk catches according to its recipe:

- known exceptions map to stable error codes/messages;
- unknown `std::exception` values map to a package bridge error with `what()` as context;
- non-standard exceptions map to an opaque bridge failure;
- functions declared/verified `noexcept` can omit the catch path.

The safe wrapper exposes `T!`. Exception translation cost is included in native-bridge inspection.

### 21.9 C++ objects and lifetime

An owned C++ object is normally represented by a final Luce class containing an opaque native handle. Its `deinit` invokes the generated destructor thunk. Borrowed subobjects cannot escape unless the recipe provides a stable shared owner; otherwise they are exposed only to a closure-scoped callback or copied.

Common ownership adapters are fixed and inspectable: `unique_ptr<T>`/owned raw results become one Luce owner class; `shared_ptr<T>` becomes an ARC wrapper holding one C++ shared owner; `weak_ptr<T>` becomes an optional generated weak-handle operation; stable `span`/`string_view` borrows retain a suitable owner or remain callback-scoped. The generator never assumes that a reference implies any one of these policies.

Move-only C++ values stay behind owner wrappers. Luce does not add a universal `move` operation to imitate them. Explicit methods such as `take_buffer()` may invalidate a wrapper and return a new owner when a library requires transfer; use-after-transfer is diagnosed by the wrapper's state checks.

### 21.10 Templates

The manifest lists each concrete template specialization to expose:

```toml
[[native.geometry.template]]
name = "geom::Vector"
arguments = ["float", "3"]
luce_name = "Vector3f"
```

The generator asks Clang to instantiate and bridge it. Luce generics do not instantiate arbitrary C++ templates, and C++ templates do not leak into Luce's type system. This keeps compile time, errors, and ABI reproducible.

### 21.11 Callbacks, threads, and reentrancy

A generated callback adapter owns a context object that retains its Luce closure until the foreign API invokes the paired unregister/destructor operation. The binding recipe declares whether calls are synchronous, reentrant, retained, and which thread may invoke them.

- Same-worker synchronous callbacks may call the closure directly.
- A callback arriving on a foreign thread enters generated native-side adapter code — never a raw Luce `cfunc`, which a thread Luce never entered cannot invoke (§21.19) — that copies validated sendable arguments into the owning worker's ingress queue; ordinary Luce identity is never touched concurrently.
- A foreign API requiring an immediate return from an arbitrary thread accepts only a generated or handwritten audited native adapter. Capture-freedom is not enough: even a trivial Luce body can trap, print, and allocate, so it runs only on a thread that carries its runtime (§21.19).
- Unregister races use the generated lifetime token; a callback cannot observe a freed context.
- Reentrant callbacks are marked in FIIR and shown by `luce explain` so wrapper code can avoid invalid intermediate states.

Unsupported threading/lifetime contracts make safe wrapper generation fail. The tool never silently calls an ordinary Luce closure concurrently.

### 21.12 Unsafe native source

Low-level operations are confined to functions declared with the `unsafe_native` effect and normally generated into `.native.luc` modules. They may use compiler-known types:

- `native_ptr[T]` and `native_mut_ptr[T]`;
- opaque native handles;
- explicit load/store/copy operations;
- ABI casts validated for size/alignment;
- generated call-convention declarations.

Pointer arithmetic, dereference, and foreign calls are named intrinsics rather than overloaded operators. Raw pointers cannot be stored in ordinary public safe values, captured by escaping closures, or sent to workers. Epoch 1 has no inline assembly; backend/platform intrinsics live in reviewed runtime modules.

### 21.13 Export to C++

Luce does not expose a separate unstable C++ ABI. A C++ consumer receives the generated C header plus an optional header-only RAII/type-safe facade:

- constructors/destructors wrap opaque Luce-owned handles;
- fallible calls map to the selected expected/status convention without letting exceptions cross Luce;
- strings/spans use explicit adapters;
- callbacks use the same generated context/lifetime machinery;
- ABI symbols remain C even when the facade feels idiomatic in C++.

This provides good C++ UX while keeping one stable foreign boundary and all backends equivalent.

### 21.14 Support tiers

- **Tier A — automatic safe:** scalars, fixed values, enums, strings/spans, unambiguous ownership, ordinary functions/methods, blessed containers.
- **Tier B — declaratively safe:** recipe-specified ownership, nullable/borrowed views, status/exception mapping, overload naming, callbacks, explicit templates.
- **Tier C — native adapter:** exotic templates, macro-generated APIs, complex inheritance, undocumented lifetime/thread rules, compiler-specific extensions.

Documentation reports the tier for every imported declaration. “Unsupported automatically” means “write/audit one adapter,” not “change the Luce language.”

### 21.15 Binding UX requirements

`luce bind` must provide:

- a binding preview before files are generated;
- unmapped/unsafe declaration reports;
- source links back to header locations;
- ownership/nullability questions expressed as actionable recipe edits;
- cached incremental Clang parsing and bridge compilation;
- API diffs when a native dependency changes;
- a test harness that compares layouts and calls a probe binary.

Interop quality is measured by how quickly a user reaches a small safe wrapper and how little C++ knowledge leaks into ordinary Luce—not by the percentage of exotic header syntax imported mechanically.

Every binding cache key fingerprints header contents, transitive include graph, defines/flags, target triple, C/C++ language mode, Clang/bridge generator, C++ standard library/ABI, recipe, linked library identity, and safe-wrapper generator. `luce bind` explains which input invalidated a cache entry.

Dynamic libraries are resolved from explicit package/bundle locations and recorded deployment dependencies. Builds do not depend on an ambient working directory, undocumented system search path, or whichever C++ runtime happens to load first. The first-party driver may use a bundled compiler/linker or a manifest-declared compatible platform SDK; `luce doctor` verifies that contract before a build.

### 21.16 The extern declaration surface (adopted from stage-0 0.21, ruled 2026-08-24)

Generated raw modules are ordinary Luce source, so the language itself carries the boundary declaration forms — the generator emits them, and a hand-written binding (the bootstrap case, and every Tier C adapter) writes them directly. The forms, semantics proven in stage-0 0.21:

```luce
extern type Window                    # nominal opaque handle, pointer-shaped
extern type Device = i32              # integer-shaped handle; the four boundary widths u32/i32/u64/i64 are the closed set

extern func SDL_GetError() -> str
extern func SDL_CreateWindow(title: str, w: i32, h: i32, flags: u64) -> Window?
extern func SDL_GetWindowSize(window: Window, out w: i32, out h: i32) -> bool
extern blocking func SDL_Delay(ms: u32)
extern var SDL_version_number: i32

extern struct Rect:
    x: i32
    y: i32
    w: i32
    h: i32
```

The governing rules, stated once (the stage-0 FFI document is the detailed contract):

- **Friction sorts by frequency.** The common shape (scalars, strings, arrays, structs, null, out-parameters, handles) crosses invisibly — the declaration states the C shape and the compiler translates. The rare shape (buffers, raw reads, ownership transfer) is one visible scoped verb. The exotic shape (variadics, bitfields, by-value aggregates) is generated away by `luce bind` thunks and never appears in user code.
- **Nothing crosses silently wrong.** A pointer-shaped handle without `?` is an enforced contract: a zero crossing traps `null_foreign` in every profile. `?` on a handle decodes C's null to `none` — an ordinary optional, no sentinel representation. A `str` result is copied immediately and UTF-8-validated; text arguments cross as NUL-terminated temporaries borrowed for the call. Integer-shaped handles carry no trap: their zero is a value.
- **`out` parameters become extra results**, received by ordinary destructuring in declaration order after the declared return.
- **`extern struct` is C layout, crossing by pointer** in both directions; by-value aggregates wait for generated shims (§21.17). `cfunc(params) -> R` is C's function pointer: capture-free functions and extern function names convert to it, struct fields and results of that type are callable, and the ARC-carrying trampoline is the generator's machinery, not the language's (§21.19). **`list[H]` parameters cross as C's pointer-beside-count arrays**, borrowed for the call (§21.20).
- **`blocking` opts the call out of the effect lock** and takes on the thread-safety contract: the callee promises its own safety and may park the thread, because workers will reach it concurrently. **`extern var` binds a C global** of boundary-scalar or handle type; reads and writes are direct loads and stores of the symbol, and anything fancier is a shim (§21.18).
- **Visibility applies to extern declarations as to any declaration.** `pub extern` exports through the module surface — generated raw modules are ordinary Luce modules and their declarations must be reachable by the safe wrapper that imports them.
- These declarations are the *raw* layer. FIIR, recipes, and the safe-wrapper generator (§21.1–21.15) stand above them unchanged; nothing here relaxes the ownership-recipe or unsafe-visibility rules.

The finer rulings, each proven by a differential spec during the stage-0 implementation and carried forward as language law:

- **There is no `null` literal, ever.** Absence is `none`; C's `NULL` is a boundary encoding detail. The conversion at absence is the ordinary optional toolkit: `let w = create_window() else error(last_error())` is the whole idiom.
- **The niche lives in the ABI, never in the type.** A nullable handle is an ordinary `{token, present}` optional with no sentinel representation, because a *present zero token* and `none` must remain distinguishable — a zero token is a value a C library may legitimately traffic in, and a sentinel lowering would make the two engines disagree on `x == none` for exactly that value. The boundary is the decoder: one comparison decodes C's 0 to `none` on the way in and encodes `none` as 0 on the way out.
- **The zero token is constructible and inert in-language.** An uninitialized handle variable holds it, it compares, it stores; only a *boundary crossing* through a non-`?` slot traps. A nonzero integer constant is never admitted as a handle value — that would be a forged pointer, and hostile modules offering one are refused at verification.
- **An empty buffer's address is C's null.** A buffer-address operation over zero elements answers the zero token — there is nothing to point at — so a callee accepting C's null-with-zero-count convention declares its pointer parameter nullable, and a bare handle slot correctly traps on the empty case. This fell out of the trap's first run against the existing test corpus and is the design working as intended, not an accommodation.
- **Text results validate or trap.** `-> str` copies immediately — NUL-scan, copy, UTF-8 validation — and invalid text traps (`invalid_utf8`) rather than laundering the `str` contract. An API that answers arbitrary bytes is not a `str` API; it is read with the byte-copy verb. Text arguments cross as NUL-terminated temporaries **borrowed for the call only**; a callee that keeps the pointer is undefined behavior, and an API that stores its argument needs a wrapper that keeps the buffer alive (recipe territory).
- **Reading C-owned memory is a copy, spelled once.** Three library verbs — copy `count` bytes from a token; copy-and-validate the C string at a token; take-and-dispose the *owned* C string (next bullet) — are the tier-two door for inbound memory. Copies need no borrow rules, no lifetimes, and no escape analysis. The outbound scoped-buffer form extends to dense numeric arrays, which is the door a BLAS binding walks through.
- **The owned C string is one call.** The take verb (`take_str`) copies and validates the NUL-terminated text at a token — `null_foreign` on zero, before the disposer runs; `invalid_utf8` on bad bytes — hands the token to a `cfunc(foreign)` disposer, and answers the copy: the `LLVMPrintModuleToString` / `LLVMDisposeMessage` convention as a single expression, with the disposer slot fed directly by the extern's own name (§21.19). A `foreign?`-accepting variant was considered and deliberately not added: flow narrowing already turns a checked `foreign?` into the bare token at every use site, so the verb as written serves the `char **` out-slot convention too.
- **The two boundary traps are unconditional.** `null_foreign` (a zero token through a bare slot, either direction) and `invalid_utf8` fire in every build profile — profiles cannot change error behavior, and each costs one comparison at a crossing that was never free. The mis-declared extern produces a trap with a trace at the exact call, never a corrupt pointer inside C.

### 21.17 `extern struct`: one layout fact on an ordinary value struct (ruled 2026-08-24)

An `extern struct` is an **ordinary value struct** carrying one additional fact: its fields also have C's layout — declaration order, the target's alignment and padding, no reordering. Everything structs already do stays available: memberwise construction, field access, copies, equality, printing, zero values, methods, field defaults, and interface conformance. The C byte form is not the struct's representation; it exists **only at a boundary crossing**, where the call site packs each field at its C offset into a call-scoped slot and reads an `out` slot's bytes back field by field afterward.

- **Crossing is by pointer, both directions.** A parameter of extern struct type passes the packed bytes' address as C's `const T *`, **borrowed for the call only** — a callee that retains the pointer is undefined behavior by contract. An `out` parameter passes a writable `T *`. **By-value aggregate passing and returning is refused** at the declaration, and the refusal names the out-parameter road: by-value crossing requires per-target ABI classification (the SysV eightbyte algorithm and kin), and the binding generator's C shims are the planned door. This pointer discipline covers the SDL- and Vulkan-shaped APIs completely.
- **Layout is natural alignment**, computed once by the compiler and identical across supported targets; the stage-0 implementation pinned it against Clang on every emitted target.
- **The field vocabulary is closed**: the boundary scalars, named handles, bare `foreign`, bare `cfunc` pointers (§21.19), and nested extern structs, inline. No `str`, no ordinary structs, no `weak`, no fixed arrays — stage-0 arrays carry runtime shape and have no C-layout form, so array fields are deferred to the binding generator — and no empty struct: C has no zero-size aggregate.
- **An extern struct is not nullable.** `Rect?` is refused: nullability at the boundary is pointer-shaped, and the struct is the pointee, never the pointer.
- **A field read is not a boundary slot.** A pointer-shaped handle field read back out of an `out` struct carries no automatic trap: C's null arrives as the ordinary zero token, inert in-language exactly as §21.16 states, and the `null_foreign` trap fires where the bare-slot rules always fire — the next non-`?` crossing that uses it.

### 21.18 `extern var`: C globals (ruled 2026-08-24)

`extern var name: T` binds a C global as a name in the value namespace, exactly where a file-scope constant lives; `pub` composes as on any declaration. The type vocabulary is **the boundary scalars and the handles only** — no `str`, no optionals, no aggregates — because a C global loads and stores one word, and anything fancier is a shim.

- **Reads and writes are direct loads and stores** of the external symbol at its exact C width, with **bare semantics**: no trap and no `?` decode in either direction — a pointer-shaped handle's zero is a value here, as in every non-slot position.
- **Writing follows `var` mutability**, compound assignment included.
- **No initializer.** The C side owns the value.
- **Never folded, never dead-removed.** A C global is state the language cannot see move; every read and write is observable behavior.

### 21.19 `cfunc`: the C function pointer, both directions (ruled 2026-08-24)

`cfunc(params) -> R` is C's function pointer as a Luce type. The word is **contextual, not a keyword**: `cfunc(` is recognized only in type position, and programs keep the identifier (§29.5).

- **A capture-free function, lambda, or closure converts** wherever a `cfunc` is wanted. The refusals state their reasons: a closure over a local or a method reference carries an environment C has no slot for — the trampoline that smuggles one through `userdata` is the generator's machinery, later — and a **fallible** function does not convert, nor can `!` appear anywhere in a cfunc signature: C has no error channel, and a status-answering wrapper is one line away.
- **An extern function's own name converts too**, wherever a `cfunc` is wanted, when its signature matches the row shape for shape — an extern *is* a C function pointer already, so the value is the symbol's address (on the oracle, its dlsym pointer) and no wrapper stands between. This is what makes disposers first-class: `LLVMDisposeMessage` lands directly in a `cfunc(foreign)` slot. A shape mismatch is refused like any other, and an extern with `out` slots does not convert — the out convention belongs to the declared call site, and its C signature (pointer slots, results read back) differs from the declared shape a cfunc type would spell. `blocking` does not block the conversion: it is a call-site contract, not a fact about the address, and a call through the converted value carries the cfunc call's own semantics.
- **Pointers arriving from C are callable directly.** A `cfunc` may be an extern result, an `out` slot, or an extern-struct field, and is invoked with ordinary call syntax; the call carries the same boundary semantics as any extern call. This is the function-pointer-call primitive (`vkGetInstanceProcAddr`, `OrtApi`).
- **Nullability is pointer-shaped.** `cfunc?` takes the handles' decode: `?` turns C's null into `none`, a bare cfunc slot carrying zero traps `null_foreign` at the call, and an extern-struct field read is bare — the zero arrives as a value and the call is where it traps. As with `func` types, a result consumes its own `?`, so a cfunc that answers something is parenthesized to be nullable: `(cfunc(u32) -> u32)?`.
- **The signature vocabulary is closed**: the boundary scalars, named handles, `foreign`, and the pointer-shaped optionals. No `str`, no extern structs, no nested cfunc, no `out` — a callback trampoline moves words, and the richer crossings arrive with the generator's shims.
- **In the language a cfunc is a pointer-sized value with a zero and nothing else**: no equality or ordering — a code address is the linker's accident, not a program fact — and no worker crossing, the function-value rule exactly.

**The callback thread contract.** A callback runs **synchronously against the runtime of the Luce thread that handed it to C** — the `qsort`-comparator discipline. Every Luce thread, workers included, publishes its runtime context on the way into a foreign call; an invocation arriving on a thread Luce never entered stops the process, loudly. A trap inside a callback cannot unwind through the C frames above it: it reports and stops the program at the boundary rather than returning corrupt data into C. Capture-freedom does not weaken this contract — even a trivial body can trap, print, and allocate, so there is no runtime-free callback; the contract is thread identity, not body purity. Cross-thread asynchronous callbacks are deliberately deferred to the binding-generator era: the ARC-carrying trampoline and ingress-queue marshaling of §21.11 stand above this primitive, never inside it.

### 21.20 Borrowed `list[H]` parameters: the pointer-beside-count shape (ruled 2026-08-24)

C's second-most-common shape after text is "a pointer to N of these beside the N" — `LLVMFunctionType` takes an `LLVMTypeRef *` and its length, `LLVMBuildCall2` the same. An extern **parameter** may be declared `list[H]` where H is a named handle, `foreign`, or a boundary scalar, and the call site is an ordinary list — a literal will do.

- **The elements cross as a contiguous C array of the exact element representation**, and the address passes as the parameter, **borrowed for the call only** — the `str`-temporary law exactly; a callee that keeps the pointer is undefined behavior by contract. Nothing is packed and nothing is copied: the runtime already stores every admissible element type densely at its C width (a `list[LLVMTypeRef]` *is* `LLVMTypeRef[n]`, a `list[i32]` *is* `int[n]`), which is exactly why the element vocabulary is these types and no others — the translation is inspectable because there isn't one.
- **The count still crosses separately — C's way.** The declaration states both parameters and the caller passes both; the boundary does not invent a fused pointer+length convention C itself does not have.
- **An empty list passes C's null pointer and takes no `null_foreign` trap.** This slot carries a list value, not a token, so the bare-slot trap does not apply; the §21.16 empty-buffer law — over zero elements there is nothing to point at, so the address is C's null — extends to it, and the count parameter tells the callee the story.
- **Direction is Luce→C, read-only.** C writing into a caller's array — the `LLVMGetParams` shape — is deliberately deferred: it needs a capacity/count-writeback contract this phase has no evidence to design, and the binding generator's shims are the planned road. A `list` in an `out` slot is refused saying so.
- **No `list` results, no lists in extern structs, no nested lists, no `list[str]`.** Each would need ownership rules the borrow does not earn: a returned list has an allocator question, a struct field a lifetime question, a nested list no dense form, `list[str]` a per-element NUL-temporary question. Every one is refused with its reason; a C-owned array is read with the byte-copy verb of §21.16.

## 22. Standard library boundary

A small language does not require a tiny standard library. It requires the language and library to have an obvious boundary, stable conventions, and no feature duplication.

### 22.1 Built into the language/compiler

The compiler owns only:

- primitive numeric/Boolean/character types and literal rules;
- tuples, fixed arrays, functions, optionals, structs/enums/classes;
- `list`, `map`, `set`, `str`, `bytes`, `range`, safe `slice`, and restricted `mutable_slice` core representation/operations;
- `T!`, `Error`/`ErrorCode`, ARC/`Weak`, tasks, interfaces/generics/effects;
- the closed protocols required by syntax;
- modules, native declarations, and control flow.

Even when a core type is compiler-known, most of its algorithms are ordinary versioned library code.

### 22.2 Standard library modules

The epoch 1 standard library should provide at least:

- `math`, checked numeric conversion, ranges, and deterministic random interfaces;
- Unicode text, UTF encodings, builders, parsing, and formatting;
- immutable/mutable collection algorithms and frozen sendable collections;
- files/paths, streams, clocks/durations, environment/process capability APIs;
- networking primitives appropriate to host profiles;
- serialization building blocks with explicit formats;
- arenas, pools, generational handles, and byte buffers;
- testing, assertions, property/fuzz hooks, and benchmarks;
- logging and structured diagnostics;
- native resource/callback adapters;
- LuciaOS component/runtime APIs.

`frozen_list[T]`, `frozen_map[K, V]`, and `frozen_set[T]` are immutable sendable library values returned by collection `snapshot()` operations. They iterate deterministically and may use persistent/shared storage inside one worker, but transfer performs a value-graph copy.

### 22.3 API design conventions

First-party APIs follow language-wide rules:

- one operation name per scope; semantic factory names instead of overloads;
- nouns for values/types, verbs for actions, `is_`/`has_` for Boolean queries;
- optionals for normal absence, `T!` for recoverable operational failure;
- no sentinel values;
- quantities include units in type/name;
- borrowing is either safe owner-retaining data or closure-scoped;
- iteration order and allocation behavior are documented;
- effects and thread/worker transfer behavior appear in signatures/docs.

The standard library is part of the learning curve. Consistency matters more than mimicking each platform API.

### 22.4 No magical extension system

Epoch 1 has no extension methods or retroactive conformances. Library algorithms are ordinary qualified functions when the type cannot own them:

```luce
let encoded = json.encode(project)
```

This preserves discoverability and ownership of APIs. Method syntax is reserved for behavior declared with the type.

## 23. Runtime, ABI, artifacts, and backends

The language contract is independent of one code generator. Execution backends consume semantically analyzed typed HIR; compiled backends consume the canonical MIR lowered from it. Neither backend kind decides language semantics, and all native targets share the runtime ABI.

### 23.1 Compiler pipeline

```text
source
-> tokens/layout
-> source syntax
-> name/signature resolution
-> typed HIR
-> flow/effect/ownership checking
-> canonical MIR
-> MIR verification
-> optimization
-> MIR verification
-> target legalization/instruction selection
-> artifact emission
```

The canonical MIR makes evaluation order, copies, ARC operations, failures, traps, effects, worker transfers, and native calls explicit. Optimizations operate after these semantics are fixed, and verification runs both before and after optimization so neither lowering nor a transform can hand malformed MIR to a backend.

Typed HIR is the semantic boundary before that machine representation. It keeps structured source-level control flow while replacing source spellings with program-wide `SymbolId` and `TypeId` identities, tagged operations, structured effect sets, decoded constants, and retained source spans. Type names remain only as diagnostic metadata; interpreters and lowerers never infer language meaning from them. Whole-program semantic analysis returns a distinct `AnalyzedProgram`, making it impossible for execution or MIR lowering to consume raw checker output accidentally.

The reference interpreter branches after semantic analysis and executes typed HIR directly. It intentionally remains independent of MIR lowering so differential tests can expose lowering and backend defects. A separate MIR interpreter may exist for MIR debugging without replacing that semantic oracle.

The compiler is written in Luce after the Stage-0 0.19 bootstrap compiler is frozen. Each self-hosting stage must reproduce the next stage's observable compiler behavior, with bootstrapping artifacts and hashes published.

### 23.2 Backend interface

Backends implement a versioned interface for:

- target data layout and calling convention;
- scalar/vector operations and checked traps;
- control flow and function calls;
- ARC/runtime calls and stack maps as required;
- native C ABI calls;
- debug/unwind information;
- object/executable emission and linking.

No backend decides language typing, ARC semantics, error propagation, C++ import shape, or module behavior.

### 23.3 Backend portfolio

The intended sequence is:

1. **typed interpreter** as a rapid semantic oracle and development runner;
2. **LLVM backend** for target reach, optimization, debug formats, and initial production quality;
3. **direct x64 backend** optimized for very fast debug/edit-run builds;
4. **direct ARM64 backend** when the x64 design and runtime ABI are stable;
5. optional additional/wasm backends based on product evidence.

LLVM remains a supported backend, not the architecture. Direct backends may trade peak optimization for extremely low latency. Release/build profiles can choose per target without changing source or native wrapper APIs.

The distribution owns ordinary object emission, archive/link driving, target libraries, and cross-target discovery; a normal Luce/C build does not assemble itself through an ambient `cc`. C++ bridging is the explicit exception that may require a manifest-declared compatible platform C++ SDK/compiler because it is the ABI semantic oracle, and `luce doctor` verifies it up front.

### 23.4 Runtime services

The runtime is small and explicit enough to replace per host. It supplies:

- ARC object allocation, weak-reference tables, and destruction;
- traps, source traces, and host termination reporting;
- core dynamic collection/string storage;
- isolated worker creation, value graph transfer, cancellation, and joining;
- capability handle resolution;
- native bridge support and platform startup;
- optional profiling/leak/allocation hooks.

It does not provide dynamic reflection, a tracing heap, exception unwinding, a shared-thread scheduler, runtime generic instantiation, or JIT semantics required by ordinary programs.

### 23.5 Artifact model

The durable project inputs are UTF-8 `.luc` source, `luce.toml`, `luce.lock`, package content identities, language epoch, and explicit target/profile choices.

The compiler may emit a deterministic portable `.lc` component containing verified canonical IR, public type/function interfaces, required effects/host profile, package identities, and optional source origins. `.lc` is useful for LuciaOS distribution, caching, and hostile-input verification, but source remains the long-term authority and any `.lc` may be rejected/rebuilt when its format/runtime contract is unsupported.

Native `.o`, static/dynamic libraries, executables, debug symbols, and application bundles are explicit target-specific outputs. They are keyed by the portable component plus backend, target, runtime ABI, profile, linker, and native bridge identities. They are never confused with portable/source artifacts and are always disposable caches unless intentionally published as a product.

One release manifest generates the compiler's build identity, language epoch, portable format, runtime/native ABI versions, supported targets/backends, standard modules, and bundled package versions. Release validation fails if tools, installers, docs, or artifacts disagree with that source of truth.

### 23.6 ABI layers

Luce distinguishes:

- **C ABI**, stable where explicitly exported;
- **runtime ABI**, versioned with compiler/runtime distribution;
- **package binary ABI**, initially compiler-version-specific;
- **source API**, checked by generated interface descriptions;
- **serialized generic/IR format**, an internal versioned artifact.

Epoch 1 does not promise a permanent native Luce ABI. Premature ABI freezing would fossilize class/interface/generic layouts. Cross-version/system boundaries use C ABI or a declared serialization/protocol format.

### 23.7 Build profiles

Standard profiles are:

- `check`: parse/type/effect/ownership validation, no codegen;
- `debug`: fast codegen, full checks, rich traces;
- `release-safe`: optimized with all language safety checks;
- `release-fast`: optimized; may use explicitly requested unchecked library algorithms but never silently removes core memory safety;
- `size`: optimized for artifact size.

Testing is an overlay on these profiles rather than a sixth semantic mode: it adds the statically discovered test graph, harness, deterministic test context, and observability while preserving the selected profile's language rules. The default `luce test` profile is fully checked `debug`; CI may additionally select `release-safe` to expose optimization/backend defects.

Profile differences cannot change overflow semantics, evaluation order, error behavior, data-race model, or public API. Unsafe speedups are named APIs or manifest decisions visible in review.

### 23.8 Determinism and caching

Given the same source, lockfile, compiler/runtime version, target, profile, native inputs, and declared environment, a build must be bit-reproducible where platform linkers permit. Cache keys include all of those inputs. The compiler reports cache misses with the exact changed key component.

Incremental compilation works at declaration/typed-IR granularity. A private function-body change should not rebuild unrelated modules or native bridges. Fast feedback is a language-product requirement, not a future optimization.

## 24. Tooling and diagnostic contract

The toolchain is part of the language design. A syntax feature is incomplete until formatting, completion, diagnostics, documentation, testing, cost inspection, and migration understand it.

### 24.1 Persistent compiler service

The compiler is a library and a long-lived semantic service first, then a CLI. One incremental query graph owns source/package identity, parsing, names, types, generics, effects, captures, sendability, public API fingerprints, and cost facts.

- The parser produces a lossless, error-tolerant syntax tree with stable identities for incomplete editor buffers.
- Declaration/function-body queries invalidate only transitive dependents; every miss can explain why.
- Diagnostics, formatting, completion, hover, definition/references, rename, match completion, named-argument fixes, effects, cost, API diff, and build consume the same facts.
- File-system, LuciaOS blob, generated-native, and editor-buffer sources enter through one byte/source-identity loader interface.
- Requests are cancellable and revisioned; a stale answer is never published over a newer buffer.
- Tools and agents receive versioned structured data, never scrape colored terminal prose.

### 24.2 One first-party command

The `luce` command owns:

- `luce new` — create a package from a maintained template;
- `luce fmt` — canonical formatting;
- `luce check` — fastest semantic validation;
- `luce run` — build/run the selected product;
- `luce build` — reproducible artifacts;
- `luce test` — static unit/integration discovery plus property/fuzz/snapshot/benchmark modes and structured reports;
- `luce doc` — API/reference docs with runnable examples;
- `luce add/remove/update` — dependency management;
- `luce package fetch/vendor/audit/publish` — reproducible ecosystem operations;
- `luce bind` — C/C++ import and wrapper generation;
- `luce query` — structured semantic/diagnostic/API data for editors and agents;
- `luce explain` — type, effect, ownership, allocation, ARC, bounds, worker, and native costs;
- `luce api diff` — source/native API compatibility;
- `luce fix` — apply deterministic compiler suggestions;
- `luce migrate` — epoch/version migrations;
- `luce doctor` — verify host/target SDK, native bridge, debugger, cache, and installation health.

The language server and command line use the same incremental compiler database, diagnostics, formatter, and package graph. Editor behavior must never disagree with the build because it reimplemented the language.

### 24.3 Diagnostic shape

Every error contains:

1. a one-sentence description in programmer vocabulary;
2. the smallest primary source span;
3. relevant secondary spans showing origins/declarations;
4. actual versus required type/effect/ownership fact;
5. a concrete fix when one is mechanically safe;
6. an optional deeper explanation and stable diagnostic code.

Example:

```text
error[L0421]: `document` cannot be sent to a worker
  --> app.luc:18:37
   |
18 | let job = spawn index_document(document)
   |                                     ^ class `Document` has shared identity
   |
   = workers accept copied value graphs, not class references
   = help: pass `document.snapshot()` if `DocumentSnapshot` is sendable
```

Diagnostics must trace generic constraints, effect propagation, import origins, and non-sendable field paths without dumping internal compiler types. “Expected X, found Y” alone is not sufficient.

### 24.4 Formatter

`luce fmt` is canonical and intentionally minimally configurable. It owns indentation, line breaks, spaces, imports, and trailing delimiters. Stability across versions is a compatibility goal; format churn requires an epoch/migration rationale.

A legal same-line suite remains compact only while its body is one simple statement on one physical line. The formatter expands it to the ordinary four-space form rather than wrapping after `:`; it never joins an existing indented suite automatically.

There is no formatter-disable directive in ordinary source. Generated native files are recognized as generated and formatted by the generator.

### 24.5 Tests

`test` is a real module-level declaration, not an annotation or naming convention. It earns one keyword because it removes reflection discovery, test classes, generated registries, and a second test language.

```luce
test "parser reports missing closing bracket":
    let parsed = parser.parse("[") catch failure:
        assert(failure.code == parser.unclosed_group)
        recover Document.empty()
    assert(parsed.is_empty())

test "configuration reads through the granted test file system" uses files:
    let text = try files.read_text("settings.luce")
    assert(text == "theme = dark")
```

The complete declaration form is `test STRING_LITERAL [uses effects]: suite`. A test:

- has a nonempty description unique within its module; its stable identity is package + module + description;
- is compiled as a hidden zero-argument `unit!` function, so `try` may propagate directly into the harness and reaching the end means pass;
- must declare every host effect with the ordinary `uses` clause;
- cannot be `pub`, generic, nested, parameterized, or returned from; reusable setup is an ordinary private function;
- is checked with exactly the same typing, initialization, overflow, bounds, ARC, effect, and native-safety rules as production code.

An unhandled `Error`, failed assertion, trap, host termination, leaked checked resource, or failed test-library expectation fails the test with its structured source trace. `return` is rejected inside a test so an accidental early pass cannot skip assertions.

#### 24.5.1 The bounded test scope

A test has useful privileges, but no safety privilege:

1. An inline test belongs to its source module and may therefore access that module's private declarations and fields. It gains no access to another module's private API.
2. The test profile exposes the `testing` standard module for equality/diff expectations, deterministic seeds, temporary resources, fake capability implementations, allocation/ARC/live-resource census, property generation, fuzz inputs, snapshots, and benchmark measurement.
3. The runner observes the isolated test domain's error, trap, trace, output, capability log, allocation/ARC ledger, and final resource state. These observations are harness metadata, not reflection available to production code.
4. A manifest may grant a test deterministic fake capabilities or explicitly opt a test product into real host capabilities. The source still declares them with `uses`; `test` never creates ambient files, network, clock, random, process, or `unsafe_native` authority.

The scope never relaxes type checking, imports private declarations across module/package boundaries, makes traps catchable, permits mutable globals, changes production semantics, or implies `unsafe_native`. Raw native test code follows the same audited-module and manifest rules as any other raw native code.

`testing.expect_trap(function)` accepts a noncapturing function value, emits a test-only child entry, runs it in a child execution domain, and checks the domain outcome:

```luce
import testing

test "bounds violations trap":
    let index_past_end = func ():
        let values = [1, 2, 3]
        discard(values[3])
    try testing.expect_trap(index_past_end)
```

The function must capture nothing and exists only in the test artifact; this is a harness entry transformation, not permission for an ordinary closure to cross a worker boundary. Its effects must be a subset of the enclosing test's declared effects, and the child receives only the same test capability implementations. The trap is not caught or resumed inside Luce. This preserves the language rule that a violated invariant terminates its domain while still making safety behavior testable.

#### 24.5.2 Unit and integration boundaries

- Inline `test` declarations in a product module are unit tests: they can exercise that module's private implementation and use its ordinary imports.
- Modules under a manifest-declared test source root are integration tests: they are absent from the product graph, may import locked test-only dependencies, and see the package under test only through its public modules.
- The `testing` standard module is test-only. An import used exclusively by test declarations is valid during `luce check`/`luce test` and is pruned with those declarations from production; using `testing` from reachable product code is an error.

This gives authors white-box tests without a `friend`/`@testable` visibility feature, and black-box tests without weakening package boundaries.

#### 24.5.3 Discovery and execution

`luce test` asks the compiler for statically typed test declarations in the selected package/test products. It does not run dependency packages' tests, scan names, load reflection metadata, or execute module initialization. The compiler emits the registry only into the test artifact.

Each test runs in a fresh supervised execution domain. A trap terminates that domain, the harness records it, and the remaining suite continues. Tests have no shared Luce globals; order is unspecified, parallel execution is permitted, and code must not depend on a working directory, wall clock, random seed, or prior test. The runner supplies a deterministic seed by default and always prints it on failure.

The stable CLI surface includes listing, name filtering, seed selection, job count, fail-fast policy, profile selection, snapshot-update intent, and versioned structured reports. Property, fuzz, snapshot, benchmark, coverage, and allocation modes are runner/library facilities over the same `test` declaration—not more language keywords. A basic run stays one command:

```text
luce test
```

`luce check` includes product source, inline tests, and declared integration-test modules by default so test code does not silently rot; production `luce build` removes the entire test graph before code generation. There is no `mock`, `fixture`, `before_each`, benchmark declaration, annotation, reflection hook, or magic filename rule in the language.

### 24.6 Documentation

`##` comments attach to the next public declaration. Documentation checks:

- every public symbol has a summary;
- parameter/result/failure/effect contracts are rendered from the signature;
- code examples compile and can be marked runnable;
- native wrappers link to their foreign declarations and recipes;
- allocation/order/complexity notes use structured doc sections;
- docs search by operation, type, effect, error code, and package.

The generated language reference is versioned by epoch and includes grammar, examples, and rationale links. Beginner material introduces only the concepts needed for the next working program.

### 24.7 Debugging and observability

Debug builds provide source-level stepping across Luce and generated bridge frames, value renderers that respect privacy, task/worker histories, effect/capability logs, ARC object graphs, allocation flame graphs, and deterministic error traces.

Generated native thunks may be collapsed in the default stack view but are never hidden from an expanded trace. Users must be able to locate cost and failure at an interop boundary.

### 24.8 Compiler performance budgets

The project tracks cold check, incremental check, debug build, clean release build, peak memory, package-resolution, and native-binding latency on representative repositories—including the Luce compiler itself. Regressions block release once budgets are established.

The direct debug backend exists to make edit/check/run feel immediate; LLVM remains available when reach or peak optimization matters. Backend choice is explicit in build output and cache keys, not source code.

### 24.9 Correctness and security gates

A release requires:

- lexer/parser/type/MIR-verifier fuzzing, including hostile `.lc` inputs;
- expected-diagnostic, expected-trap, and cleanup-on-every-exit suites;
- interpreter/LLVM/direct-backend differential behavior over the same corpus;
- ARC balance, weak/cycle, allocation-failure, worker-transfer, cancellation, and resource-finalization stress tests;
- C/C++ ABI layout/call/exception/callback probes across supported platform tiers;
- reproducible bootstrap and build records;
- formatter idempotence and fix/migration semantic preservation;
- package-resolution/provenance/advisory tests with offline/vendored builds;
- explicit audit of the small runtime/native unsafe substrate.

Supported host/target tiers state compiler, linker, debugger, native bridge, package, and CI coverage. A platform is not marketed as supported when only trivial code generation works.

## 25. Deliberate exclusions

Smallness comes more from saying “no” than from shortening keywords. The following are not merely postponed implementation tasks; they are absent from the epoch 1 language unless evidence passes section 26's gate.

### 25.1 Object/type-system exclusions

- class inheritance, abstract/protected/virtual/override members;
- structural typing and duck typing;
- open/anonymous union or intersection types beyond declared enums and interface constraints;
- runtime type reflection, downcasts, type-name branching;
- user-defined variance, higher-kinded types, associated types;
- extension methods and retroactive conformances;
- method/function/constructor/operator overloading;
- implicit numeric, string, pointer, or truthiness conversions;
- user-defined operators.

### 25.2 Metaprogramming exclusions

- textual/preprocessor macros;
- AST/procedural macros;
- compile-time user-code execution;
- arbitrary attributes/annotations;
- compiler plugins loaded from packages;
- package build scripts;
- reflection-based serialization or dependency injection.

Repetition is first attacked through generics, functions, data tables, declarative manifests, and first-party generators that emit inspectable Luce.

### 25.3 Memory/concurrency exclusions

- user-visible borrow/lifetime algebra;
- general ownership/move/consume/clone syntax;
- manual retain/release/free in safe code;
- nullable raw references;
- tracing garbage collection as ordinary class semantics;
- shared-memory threads, locks, atomics, shared actors;
- detached tasks and implicit background work;
- async/await language coloring in epoch 1.

### 25.4 Control/error exclusions

- exceptions, `throw`, stack-region `try/catch`, and exception classes;
- typed error-set unions;
- `goto`, labels, loop values, match fallthrough/guards (expression-valued
  `match` was later adopted — §9.6);
- force unwrap and implicit optional chaining;
- implicit return of final expressions;
- statement/expression blocks with competing value rules.
- test annotations, test classes, reflection discovery, catchable expected-trap syntax, and relaxed test-only language semantics.

### 25.5 Surface and ecosystem exclusions

- semicolons, brace-delimited suite alternatives, formatter dialects;
- wildcard imports and ambient preludes;
- mutable globals and module initialization code;
- multiple package managers/manifests/lock formats;
- user-configurable hidden build hooks;
- platform APIs copied directly into the core language.

### 25.6 Native exclusions

- pretending all C/C++ is safely importable without ownership recipes;
- exposing C++ inheritance, overload sets, templates, exceptions, RTTI, or macros as Luce features;
- depending on LLVM for the meaning of native interop;
- leaking backend-specific pointer/IR concepts into safe APIs;
- inline assembly in portable Luce.

## 26. Feature admission and evolution

Language evolution uses an evidence gate so “just one convenience” cannot slowly destroy the design.

### 26.1 Admission test

A proposed language feature must answer all of these:

1. What important, repeated real-world task cannot be expressed clearly with current composition/library/tooling?
2. How many concepts and interactions does the feature add?
3. Which existing complexity does it remove?
4. Can a diagnostic, library API, generator, manifest field, or editor action solve it instead?
5. Is its runtime cost and failure behavior visible?
6. How does it interact with values/classes, `T?`, `T!`, ARC, closures, generics/interfaces, effects, workers, and native code?
7. Can it be taught before its edge cases?
8. Can the formatter, language server, debugger, docs, migration tool, every backend, and C/C++ boundary support it completely?
9. Is there corpus/UX/performance evidence from the compiler, standard library, LuciaOS, and external pilot packages?
10. If admitted, what older mechanism can be removed or kept out?

A feature is rejected when its benefit is mainly terseness, familiarity from another language, or theoretical completeness.

### 26.2 Epoch changes

Language epochs are rare, explicit package-manifest choices. Within an epoch:

- parsing and type semantics remain compatible;
- new warnings do not silently become release-breaking errors without a staged migration;
- public runtime/native ABI versions are explicit;
- compiler improvements may optimize but not change observable behavior.

An epoch migration ships with `luce migrate`, an API/behavior report, formatter stabilization, and side-by-side documentation. Stage-0 0.19 is the frozen bootstrap seed, not a compatibility constraint on Luce Next source.

### 26.3 Reconsideration candidates

The following may be researched after epoch 1, in this order and only with evidence:

1. ~~one optional default/coalescing operation~~ — **adopted 2026-08-24** as the `else` form (§13.1), on native-interop evidence;
2. call-scoped `inout` if compiler/native algorithms otherwise allocate or obscure intent;
3. a structured message channel if spawn/wait cannot support required pipelines;
4. a host-integrated async model if synchronous capability APIs cannot deliver necessary scale/debugging;
5. a constrained declarative derive/generator system if source generation becomes a dominant maintenance burden;
6. additional direct backends and SIMD intrinsics;
7. 128-bit integers (`u128`/`i128`) as ordinary checked scalars, if numerics or native interop produce the evidence (owner note, 2026-08-24).

None is promised. Each must reduce total system complexity, not only local character count.

## 27. Complete implementation sequence

The compiler should be built in vertical slices that always leave one usable, testable language. Syntax breadth without diagnostics, runtime, and tools is not progress.

### Phase 0 — freeze and semantic harness

- Freeze Stage-0 0.19 as the bootstrap compiler; publish exact source/artifact hashes.
- Create the Luce Next lexer/parser/typed-IR packages in the subset Stage-0 0.19 can compile.
- Build golden syntax/diagnostic tests and differential interpreter tests.
- Define language epoch, target description, package identity, and compiler artifact formats.
- Treat this document's feature table and exclusions as change-controlled decisions.

Exit: the bootstrap can build the new compiler skeleton reproducibly; source locations and diagnostics are stable enough for tooling.

### Phase 1 — minimal executable value language

- UTF-8 source/layout/comments/names and canonical formatter.
- primitive literals/types, tuples, fixed arrays, `let`/`var`, assignments/conversions/operators.
- functions, calls, `if`/`while`/`for` over ranges, return/break/continue/defer.
- structs and payload-capable enums, exhaustive `match`, optionals.
- modules/imports/public declarations/top-level constants.
- typed interpreter and `luce check/run/test` basics, including static test discovery, implicit test fallibility, isolation, and production erasure.

Exit: small deterministic command-line programs run without classes, generics, or native code.

### Phase 2 — identity, failure, and core storage

- ARC runtime storage; dynamic strings/bytes/UTF-8, lists/maps/sets/slices.
- final classes, `new`/`init`/`deinit`, `Weak`, resource wrappers, cycle/leak foundations.
- `T!`, `Error`, `ErrorCode`, `try`, expression-local `catch`/`recover`, traps/assertions.
- standard formatting, paths/files, streams, builders, deterministic testing capabilities, and structured test reports.
- effect declarations/inference and capability-backed standalone runtime.
- diagnostic fixes, documentation extraction, package manifest/lockfile.

Exit: useful file-processing tools can be written, packaged, tested, and documented; identity/resource lifetime is observable and needs no native escape hatch.

### Phase 3 — closures and reusable abstraction

- closures, capture cells/lists, direct cycle diagnostics and completed leak tooling.
- generics, constraints, interfaces, interface values/boxing.
- closed iteration/equality/hash/compare/display protocols.
- generic-instantiation limits and serialized typed generic bodies.
- allocation/ARC/copy/bounds/dynamic-dispatch explain data.

Exit: compiler-sized modular applications can express callbacks and reusable algorithms; abstraction/ARC costs are visible and bounded.

### Phase 4 — C foundation

- FIIR schema and Clang-based C importer.
- target layouts, raw native modules, recipe validation, wrapper generator.
- C ABI call support in interpreter/runtime and LLVM backend.
- owner/resource, slice, callback, status/error adapters.
- `export c`, header generation, ABI probe/diff tests.

Exit: representative libc, SQLite, image, compression, and OS APIs have small safe wrappers with reproducible bindings.

### Phase 5 — self-host and LLVM production path

- Port remaining compiler stages/tooling from Stage-0 0.19 constraints into Luce Next.
- LLVM debug/release code generation, link/debug/unwind support.
- serialized generics/typed package artifacts and declaration-level incrementality.
- reproducible compiler bootstrap comparison and performance budgets.
- language server, formatter, docs, test, package, cost, and API tools reach release quality.

Exit: the Luce compiler builds itself and the standard library; LLVM artifacts support initial production targets.

### Phase 6 — C++ bridge

- C++ FIIR declarations and staged supported subset.
- generated C ABI thunks, exception translation, owner/borrow recipes.
- blessed STL adapters, explicit template instantiation, callback lifetimes.
- overload renaming and composition/interface wrapper generation.
- header-change API diffs and mixed-source debugging.

Exit: substantial real C++ libraries can be consumed through ordinary small Luce APIs without C++ object-model syntax leaking into user code.

### Phase 7 — isolated workers and LuciaOS integration

- structural sendability derivation and frozen collection snapshots.
- worker graph copying, task result/failure, structured cancellation/join.
- capability manifests, grants, component entry points, resource budgets.
- deterministic task histories and worker transfer-cost tooling.

Exit: LuciaOS applications can safely run parallel work and host-limited components without a shared heap.

### Phase 8 — fast direct backends

- stabilize canonical IR/runtime ABI from LLVM/self-host experience.
- direct x64 debug backend, object/link/debug support, C ABI bridge calls.
- benchmark and optimize incremental edit/check/run path.
- direct ARM64 backend after x64 correctness/tooling coverage.
- keep LLVM selectable for unsupported targets and peak optimization.

Exit: common targets get very fast debug compilation with identical language/native semantics across backends.

### Phase 9 — adoption release

- complete tutorial sequence and searchable reference from this specification.
- migration guide from 0.18 concepts (without source-compatibility fiction).
- maintained examples: CLI, GUI/LuciaOS app, compiler subsystem, C library, C++ library.
- package provenance/advisory/license tooling and reproducible release bundles.
- external pilot feedback, usability tests, diagnostic comprehension tests.
- freeze epoch 1 only when all supported features have formatter/LSP/debug/docs/backend/native coverage.

Exit: “small” describes the concept count a learner carries, not missing production infrastructure.

## 28. Learning order

The official teaching path follows the semantic dependency graph:

1. literals, values, `let`, `var`, and functions;
2. `if`, loops, lists, strings, and modules;
3. structs, payload-capable enums, and `match`;
4. absence with `T?`, then recoverable failure with `T!`;
5. classes only when shared identity is actually needed;
6. closures and explicit capture consequences;
7. generic functions, then interfaces for abstraction;
8. effects as visible host authority;
9. isolated workers as copied values;
10. native wrappers, with raw native operations last.

`test` is introduced immediately after the first pure function, before classes, allocation control, effects, generics, or native code. A learner should be able to state an expectation and run `luce test` during the first hour; advanced test capabilities arrive only alongside the production concept they observe.

Each stage produces a useful program before adding another concept. Tutorials should not begin with package ceremony, ownership vocabulary, generic theory, or a class named `HelloWorld`.

The installed/offline learning set includes a five-minute first program, task-oriented recipes, complete maintained applications, and “Lucelings” repair exercises driven by real stable diagnostics. Tracks for Python, C/C++, Zig, Rust, and Luce 0.18 explain only the unfamiliar distinctions rather than reteaching programming. Examples are compiled in release CI against the documentation's declared epoch.

## 29. Compact surface reference

This section is a checklist for parser, formatter, documentation, and editor coverage—not a replacement for the preceding semantics.

### 29.1 Declarations

```luce
let name: Type = value
var name: Type = value
pub let constant: Type = constant_value

func name(parameters) -> Type:
pub func name[T: Interface](parameters) -> Type! uses effect:
mutating func name(self, parameters):

struct Name:
enum Name:
class Name:
interface Name:

test "description":
test "description" uses effect:
import module.path
import module.path as alias
from module.path import Name, function
export c struct Name:
export c enum Name as u32:
export c func name(parameters) -> Type:
extern type Name
extern type Name = u32
extern func name(parameters) -> Type
extern blocking func name(parameters)
extern var name: Type
extern struct Name:
```

### 29.2 Statements

```luce
if condition:
if condition: return value
elif condition:
else:
if let value = optional:
while condition:
for value in iterable:
match value:
    .first, .second: return value
    0..<10: return value
break
continue
return value
defer cleanup()
recover value
```

### 29.3 Expressions

```luce
literal
name
(a, b)
[a, b]
{key: value}
value.member
value[index]
value[start..<end]
function(arguments)
new Class(arguments)
(parameters) => expression
func [captures] (parameters) -> Type: ...
match value:
    pattern, lower..=upper => expression
try fallible_expression
fallible_expression catch failure: ...
value if condition else alternative
optional_expression else fallback
spawn named_function(arguments)
```

### 29.4 Operators

From tightest to loosest grouping:

1. member/call/index: `.`, `()`, `[]`;
2. unary/prefix: `try`, `not`, unary `-`, unary `+`, bitwise `~`;
3. multiply: `*`, `/`, `//`, `%`;
4. add/concatenate: `+`, `-`;
5. shifts: `<<`, `>>`;
6. bitwise: `&`, then `^`, then `|`;
7. range: `..<`, `..=` (non-chainable);
8. comparison/identity: `==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `is not` (non-chainable);
9. Boolean: `and`, then `or`;
10. conditional expression;
11. the `else` fallback form (section 13.1), whose arm associates to the right;
12. `catch`.

Assignment forms (`=`, `+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`) are statements and evaluate the target once. An augmented assignment is available only when the corresponding built-in operation returns exactly the target type.

`->`, `=>`, and `:` are grammar delimiters rather than precedence-bearing
operators: `->` declares a type, `=>` yields a value, and `:` opens a statement
suite or the indented arm list of a `match` expression.

### 29.5 Reserved words

```text
and as break catch class continue defer elif else enum export extern false
for from func if implements import in interface is let match mutating new none not or
pub recover return self spawn struct test true try type uses var weak while
```

`c`, capture-list `copy`, extern-declaration `blocking`/`out`/`cfunc`, primitive/core type names, and standard effect names are contextual words in the syntactic positions that require them. Future keywords are introduced only by a language epoch; the lexer does not reserve a large speculative list.

### 29.6 Grammar skeleton

This EBNF fixes the parser shape. Semantic restrictions in the earlier sections remain normative; for example, the grammar can form a `weak` field, while type checking requires its target to be an optional class. `NEWLINE`, `INDENT`, and `DEDENT` are emitted by the layout lexer. Repetition is `{...}`, optional syntax is `[...]`, and quoted text is a token.

```ebnf
module          = { import_decl }, { top_decl }, EOF ;

import_decl     = "import", module_path, [ "as", IDENT ], NEWLINE
                | "from", module_path, "import", IDENT,
                  { ",", IDENT }, NEWLINE ;
module_path     = IDENT, { ".", IDENT } ;

top_decl        = [ "pub" ],
                  ( constant_decl
                  | type_alias
                  | function_decl
                  | struct_decl
                  | enum_decl
                  | class_decl
                  | interface_decl
                  | extern_decl )
                | test_decl
                | export_c_decl ;

constant_decl   = "let", IDENT, [ ":", type ], "=", expression, NEWLINE ;
type_alias      = "type", IDENT, "=", type, NEWLINE ;

function_decl   = [ "mutating" ], "func", IDENT, [ generic_params ],
                  parameter_list, result_clause, effect_clause, ":", suite ;
function_sig    = [ "mutating" ], "func", IDENT, [ generic_params ],
                  parameter_list, result_clause, effect_clause, NEWLINE ;

generic_params  = "[", generic_param, { ",", generic_param }, [ "," ], "]" ;
generic_param   = TYPE_IDENT, [ ":", interface_type, { "&", interface_type } ] ;

parameter_list  = "(", [ parameter, { ",", parameter }, [ "," ] ], ")" ;
parameter       = "self"
                | IDENT, ":", type, [ "=", constant_expression ] ;
                  (* "self" and "mutating" are accepted only on a type member *)
result_clause   = [ "->", type ] ;
effect_clause   = [ "uses", EFFECT_IDENT, { ",", EFFECT_IDENT } ] ;

implements_clause
                = [ "implements", interface_type,
                    { ",", interface_type } ] ;
struct_decl     = "struct", TYPE_IDENT, [ generic_params ],
                  implements_clause, ":", type_suite ;
class_decl      = "class", TYPE_IDENT, [ generic_params ],
                  implements_clause, ":", type_suite ;
type_suite      = NEWLINE, INDENT, type_member, { type_member }, DEDENT ;
type_member     = [ "pub" ], ( field_decl | function_decl ) ;
field_decl      = [ "weak" ], ( "let" | "var" ), IDENT, ":", type,
                  [ "=", constant_expression ], NEWLINE ;

enum_decl       = "enum", TYPE_IDENT, [ generic_params ],
                  implements_clause, ":", NEWLINE, INDENT,
                  enum_case, { enum_case },
                  { [ "pub" ], function_decl }, DEDENT ;
enum_case       = IDENT, [ payload_list ], NEWLINE ;
payload_list    = "(", [ payload, { ",", payload }, [ "," ] ], ")" ;
payload         = IDENT, ":", type ;

interface_decl  = "interface", TYPE_IDENT, [ generic_params ], ":", NEWLINE,
                  INDENT, function_sig, { function_sig }, DEDENT ;

test_decl       = "test", STRING_LITERAL, effect_clause, ":", suite ;

export_c_decl   = "export", "c", ( export_c_struct
                                  | export_c_enum
                                  | export_c_function ) ;
export_c_struct = "struct", TYPE_IDENT, ":", NEWLINE, INDENT,
                  export_c_field, { export_c_field }, DEDENT ;
export_c_field  = "let", IDENT, ":", c_compatible_type, NEWLINE ;
export_c_enum   = "enum", TYPE_IDENT, "as", integer_type, ":", NEWLINE, INDENT,
                  c_enum_case, { c_enum_case }, DEDENT ;
c_enum_case     = IDENT, "=", INTEGER_LITERAL, NEWLINE ;
export_c_function
                = "func", IDENT, parameter_list, result_clause, ":", suite ;

extern_decl     = "extern", ( extern_type_decl
                            | extern_func_decl
                            | extern_var_decl
                            | extern_struct_decl ) ;
extern_type_decl
                = "type", TYPE_IDENT,
                  [ "=", ( "u32" | "i32" | "u64" | "i64" ) ], NEWLINE ;
extern_func_decl
                = [ "blocking" ], "func", IDENT,
                  extern_parameter_list, result_clause, NEWLINE ;
extern_parameter_list
                = "(", [ extern_parameter, { ",", extern_parameter },
                  [ "," ] ], ")" ;
extern_parameter
                = [ "out" ], IDENT, ":", type ;
extern_var_decl = "var", IDENT, ":", type, NEWLINE ;
extern_struct_decl
                = "struct", TYPE_IDENT, ":", NEWLINE, INDENT,
                  extern_field, { extern_field }, DEDENT ;
extern_field    = IDENT, ":", type, NEWLINE ;

suite           = simple_stmt
                | NEWLINE, INDENT, statement, { statement }, DEDENT ;

statement       = simple_stmt
                | if_stmt
                | while_stmt
                | for_stmt
                | match_stmt ;

simple_stmt     = binding_stmt
                | assignment_stmt
                | "break", NEWLINE
                | "continue", NEWLINE
                | return_stmt
                | defer_stmt
                | recover_stmt
                | expression_stmt ;

binding_stmt    = ( "let" | "var" ), binding_pattern,
                  [ ":", type ], "=", expression, NEWLINE ;
binding_pattern = IDENT
                | "(", IDENT, ",", IDENT, { ",", IDENT }, [ "," ], ")" ;

assignment_stmt = lvalue, ASSIGN_OP, expression, NEWLINE ;
lvalue          = IDENT, { ( ".", IDENT ) | ( "[", expression, "]" ) } ;
ASSIGN_OP       = "=" | "+=" | "-=" | "*=" | "/=" | "//=" | "%="
                | "&=" | "|=" | "^=" | "<<=" | ">>=" ;

if_stmt         = "if", expression, ":", suite,
                  { "elif", expression, ":", suite },
                  [ "else", ":", suite ]
                | "if", "let", IDENT, "=", expression, ":", suite,
                  [ "else", ":", suite ] ;
while_stmt      = "while", expression, ":", suite ;
for_stmt        = "for", IDENT, "in", expression, ":", suite ;

match_stmt      = "match", expression, ":", NEWLINE, INDENT,
                  match_arm, { match_arm }, DEDENT ;
match_arm       = pattern_list, ":", suite ;
pattern_list    = pattern, { ",", pattern } ;
pattern         = "_"
                | literal_pattern
                | case_pattern ;
literal_pattern = pattern_literal,
                  [ ( "..<" | "..=" ), pattern_literal ] ;
pattern_literal = literal | "-", ( INTEGER_LITERAL | FLOAT_LITERAL ) ;
case_pattern    = ".", IDENT,
                  [ "(", [ IDENT, { ",", IDENT } ], ")" ] ;

return_stmt     = "return", [ expression ], NEWLINE ;
defer_stmt      = "defer", call_expression, NEWLINE ;
recover_stmt    = "recover", expression, NEWLINE ;
expression_stmt = expression, NEWLINE ;

expression      = else_expr,
                  [ "catch", IDENT, ":", suite ] ;
else_expr       = conditional_expr, [ "else", else_expr ] ;
conditional_expr
                = boolean_or_expr,
                  [ "if", boolean_or_expr, "else", conditional_expr ] ;

boolean_or_expr = boolean_and_expr, { "or", boolean_and_expr } ;
boolean_and_expr
                = comparison_expr, { "and", comparison_expr } ;
comparison_expr = range_expr, [ COMPARE_OP, range_expr ] ;
range_expr      = bit_or_expr, [ ( "..<" | "..=" ), bit_or_expr ] ;
bit_or_expr     = bit_xor_expr, { "|", bit_xor_expr } ;
bit_xor_expr    = bit_and_expr, { "^", bit_and_expr } ;
bit_and_expr    = shift_expr, { "&", shift_expr } ;
shift_expr      = additive_expr, { ( "<<" | ">>" ), additive_expr } ;
additive_expr   = multiply_expr, { ( "+" | "-" ), multiply_expr } ;
multiply_expr   = unary_expr, { ( "*" | "/" | "//" | "%" ), unary_expr } ;
unary_expr      = { "try" | "not" | "+" | "-" | "~" }, postfix_expr ;

postfix_expr    = primary_expr, { postfix_part } ;
postfix_part    = ".", IDENT
                | argument_list
                | generic_call_part
                | "[", index_or_slice, "]" ;
generic_call_part
                = type_arguments, argument_list ;
call_expression = postfix_expr ;
argument_list   = "(", [ argument, { ",", argument }, [ "," ] ], ")" ;
argument        = [ IDENT, ":" ], expression ;
index_or_slice  = expression
                | expression, "..<", [ expression ]
                | "..<", expression
                | expression, ".." ;

primary_expr    = literal
                | IDENT
                | ".", IDENT, [ argument_list ]
                | tuple_or_group
                | list_literal
                | map_literal
                | lambda_expr
                | match_expr
                | closure_expr
                | "new", base_type, argument_list
                | "spawn", module_path, argument_list ;

tuple_or_group  = "(", expression,
                  [ ",", expression, { ",", expression }, [ "," ] ], ")"
                | "(" , ")" ;
list_literal    = "[", [ expression, { ",", expression }, [ "," ] ], "]" ;
map_literal     = "{", expression, ":", expression,
                  { ",", expression, ":", expression }, [ "," ], "}" ;

lambda_expr     = lambda_parameter_list, "=>", expression ;
lambda_parameter_list
                = "(", [ lambda_parameter, { ",", lambda_parameter }, [ "," ] ], ")" ;
lambda_parameter
                = IDENT, [ ":", type ] ;

match_expr      = "match", expression, ":", NEWLINE, INDENT,
                  match_value_arm, { match_value_arm }, DEDENT ;
match_value_arm = pattern_list, "=>", expression, NEWLINE ;

closure_expr    = "func", [ capture_list ], parameter_list,
                  result_clause, effect_clause, ":", suite ;
capture_list    = "[", capture, { ",", capture }, [ "," ], "]" ;
capture         = "weak", IDENT
                | "copy", IDENT, "=", expression ;

type            = base_type, [ "?" ], [ "!" ]
                | function_type
                | cfunc_type ;
base_type       = type_name, [ type_arguments ]
                | "(", type, ")"
                | "(", type, ",", type, { ",", type }, [ "," ], ")" ;
type_name       = TYPE_PATH | CORE_TYPE ;
type_arguments  = "[", type_or_array_length,
                  { ",", type_or_array_length }, [ "," ], "]" ;
type_or_array_length
                = type | INTEGER_LITERAL ;
function_type   = "func", "(", [ type, { ",", type } ], ")",
                  "->", type, effect_clause ;
cfunc_type      = "cfunc", "(", [ type, { ",", type } ], ")",
                  "->", type ;

interface_type  = type_name, [ type_arguments ] ;
integer_type    = "u8" | "u16" | "u32" | "u64"
                | "i8" | "i16" | "i32" | "i64" ;
literal         = INTEGER_LITERAL | FLOAT_LITERAL | CHAR_LITERAL
                | STRING_LITERAL | BYTE_LITERAL | "true" | "false" | "none" ;
formatted_string
                = FORMAT_START, { FORMAT_TEXT | "{", expression, "}" }, FORMAT_END ;
```

`module` begins with an optional detached `##` block (section 3.3) that the parser stores as module documentation. `formatted_string` is a `primary_expr`; `FORMAT_START`, `FORMAT_TEXT`, and `FORMAT_END` are the lexer's pieces of one `f"..."` spelling (section 4.4), and the case name after `.` in `case_pattern` and `primary_expr` also admits the reserved word `none`.

Parser implementation uses the explicit declaration/statement productions and a Pratt parser with section 29.4's precedence for expressions. Semantic analysis then rejects grammar-general forms that violate the narrower contracts—for example, a non-call expression statement, a non-class after `new`, a generic argument count mismatch, an open-ended range outside indexing, or `recover` outside a catch handler.

`constant_expression` and `c_compatible_type` are named semantic subsets rather than separate parsers: the former is section 20.4's effect-free restricted expression set, and the latter is the fixed-representation subset validated by section 21.5. `TYPE_PATH`, `CORE_TYPE`, `EFFECT_IDENT`, and the literal tokens are lexer/parser categories with the naming and literal rules from sections 3–5.

Inside delimiters the layout lexer resumes NEWLINE/INDENT/DEDENT after a `:` that ends its line (section 3.2), which is how `suite` appears within `argument_list`, `list_literal`, and their kin.

In expression position, brackets immediately followed by an argument list are parsed as generic arguments when their contents form types (`decode[Header](data)`, `list[Node]()`); otherwise brackets are indexing/slicing. PascalCase type-parameter naming and core-type tokens make the common cases syntactically decisive. An actually ambiguous generated/native spelling requires qualification, and the diagnostic shows both parses rather than guessing.

An opening `(` begins a lambda only when a valid lambda parameter list is
immediately followed by `=>`; otherwise it begins an ordinary group or tuple.

In type position, a parenthesized single type is grouping, never a one-element
tuple: it exists so an optional function type can be spelled, as in
`(func() -> unit)?` (section 14.3).

## 30. Research and Luce reconciliation

This specification is not a blank-sheet style exercise. It distills the two interviews, the public Luce 0.18 language/tool/compiler record, the clean-break/self-hosting decision, and the C/C++/backend research into one implementable surface.

### 30.1 Interview lessons made concrete

| Research lesson | Concrete requirement in this specification |
| --- | --- |
| Do more with less permanent language complexity ([Zig interview, 10:16–12:20](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=616s)) | Nine-concept budget, layer-placement rule, exclusions, evidence-based feature admission |
| Tool limitations must not dictate the product; owning load-bearing compiler pieces enabled speed ([Zig interview, 04:07–06:10](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=247s), [23:38–26:42](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=1418s)) | Backend-independent canonical IR, typed interpreter, supported LLVM path, fast direct backends, shared semantics |
| A self-contained toolchain changes adoption ([Zig interview, 47:10–48:48](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=2830s)) | One release/command owns check, format, build, link, LSP, test, docs, package, bind, explain, migrate, and doctor |
| Repair exercises and short feedback loops teach better than ceremonial setup ([Zig interview, 52:16–55:15](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=3136s)) | First-hour `test`, static discovery, compiler-teacher failures, deterministic test context, and no reflection/annotation framework |
| Strict rules can save time when tools provide trustworthy fixes ([Zig interview, 48:11–50:14](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=2891s)) | No shadowing/implicit conversions plus structured causal diagnostics and deterministic fixes |
| Safety, performance, and usability are one product problem ([Rust interview, 00:00–01:01](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=0s)) | Safe defaults remain in release; ARC avoids pervasive lifetime syntax; cost/ARC/allocation inspection prevents hidden performance |
| Adoption is constrained by existing code, libraries, builds, telemetry, debugging, and trained people ([Rust interview, 03:02–09:06](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=182s)) | C import/export first, Clang-informed C++ bridge, packages, debugger/profiler/docs, incremental component adoption |
| Expressive types prevent domain errors ([Rust interview, 22:21–24:22](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=1341s)) | Low-boilerplate structs, distinct wrappers, payload-capable enums, exhaustive matching, optionals, stable error codes |
| Hard concepts require helpful concise compiler errors ([Rust interview, 50:12–57:17](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=3012s)) | Compiler-as-teacher diagnostics, dependency-ordered learning, computer facts before syntax folklore |
| Compile time, monomorphization, disk, debugging, and macro costs are real UX ([Rust interview, 59:19–64:24](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=3559s)) | No macro/comptime system in epoch 1, generic budgets/explanations, incremental service, direct debug backend |
| A theoretically clean language does not win without useful flexibility ([Rust interview, 70:33–71:34](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=4233s)) | “Minimum complete,” not toy minimalism: classes, closures, generics, interfaces, resources, interop, and a serious library remain |

### 30.2 What 0.18 proved and what changes

The page-by-page baseline remains the public [Luce documentation](https://luce.luciaos.com/) and [compiler engineering atlas](https://lucelang.org/), reconciled in `LUCE_UX_ADOPTION_REQUIREMENTS.md`. The clean break treats implementation experience as evidence, not compatibility law.

| 0.18 evidence | Epoch 1 disposition |
| --- | --- |
| Python-familiar indentation, `let`/`var`, explicit functions/control | Keep and specify canonically |
| Values copy; references use ARC; `weak` breaks cycles; final release closes resources | Keep as the permanent memory model; add allocation/ARC/cycle inspection |
| `T?`, `T!`, and traps are distinct | Keep; add stable programmatic `ErrorCode` and local recovery semantics |
| Typed HIR, verified MIR, interpreter/native differentiation | Keep the representation ladder; make canonical IR/backend interfaces independent and hostile-input verified |
| Host table/capability seam and isolated workers | Keep; make public effects stable and worker value transfer structural/observable |
| Exact local packages and no build scripts | Keep; finish lock, hashing, fetch/vendor/audit/publish, provenance, and public API diff |
| No user generics | Reverse before self-hosting; compilers and ecosystems need restrained reusable data structures |
| LLVM-only production path | Keep LLVM as supported reach/optimization, add fast Luce-owned direct backends behind identical IR |
| Generated runtime C ABI but no complete user FFI | Replace with first-class C import/export and safe ownership/error/callback adapters |
| C++ question unanswered | Add Clang/FIIR discovery, generated C ABI thunks, idiomatic safe wrappers; do not import the C++ object model |
| Multiple public-version/document truths and incomplete editor tooling | One release manifest and one persistent compiler service generate every surface |
| 0.18 source/artifact/API details | Retain as historical evidence; freeze Stage-0 0.19 as the reproducible seed; promise no compatibility |

### 30.3 Decisions intentionally reopened by implementation evidence

The compiler and standard library are the first pressure tests. If they expose a concrete shortfall, revisit the smallest adjacent mechanism—not the whole doctrine. Examples include measuring whether ARC/copy elision is sufficient before proposing regions, whether one-statement arms avoid helper or mutable staging code before proposing expression-valued `match` (evidence that has since arrived — §9.6), whether closure-scoped mutable views cover parsing/codegen before proposing `inout`, and whether generated C++ thunks meet performance budgets before coupling the language to one backend.

The companion documents retain the deeper product requirements and C++ fixtures. This document is the normative source-surface/runtime/tool contract; where an older proposal conflicts with it, this clean-break specification wins after the conflict is recorded as a design decision.

## 31. The epoch 1 / 1.0 release gate

Do not label the language 1.0 merely because the parser accepts every construct. Epoch 1 becomes a stable adoption promise only when all of these are true:

- the frozen Stage-0 0.19 seed reproducibly builds the transition compiler, which builds a fixed-point self-hosted compiler;
- the compiler, formatter, language server, package manager, documentation generator, native binder, and core standard library are themselves substantial Luce programs;
- the interpreter, LLVM backend, and every claimed direct backend pass the same behavior/trap/cleanup corpus;
- warm editor/check latency, clean build time, peak compiler memory, generic expansion, runtime ARC/allocation, artifact size, and native bridge costs meet published budgets on named hardware;
- C import/export is stable and production-proven; the promised C++ tier is qualified against representative libraries and supported platform ABIs;
- package lock/provenance/vendor/audit/offline workflows and a security response process are operational;
- diagnostics and the first-hour learning path have been tested with people who did not design Luce;
- inline/private and integration/public test boundaries, deterministic isolation, structured reports, expected-trap child domains, and complete production erasure have conformance coverage;
- at least the compiler, a LuciaOS application, a standalone native application, a C integration, and a C++ integration have survived real maintenance rather than demo-only development;
- source/API/epoch migration policy, support tiers, licensing/patent terms, governance, and succession are clear enough for an organization to estimate adoption risk;
- every admitted feature has formatter, compiler-service, debugger, docs, tests, cost model, all-backend, migration, and native-boundary coverage.

Until then, epochs/pre-1.0 releases may deliberately break with an automatic migration where practical. Stability is earned evidence, not a date.

## 32. The sweet spot

Luce Next is small because a programmer can predict it from a compact set of sentences:

- Bindings are immutable unless marked `var`.
- Values copy; final classes and mutable collections share identity through ARC.
- `weak` breaks identity cycles; final release performs cleanup.
- Absence is `T?`; recoverable failure is `T!`; violated invariants trap.
- Structs and payload-capable enums model data; interfaces and generic functions model reusable behavior.
- Host authority is visible in effects.
- Workers receive copied immutable value graphs, never a shared heap.
- C is imported directly and safely wrapped; C++ is flattened through generated Clang-informed bridges.
- One toolchain formats, checks, explains, binds, builds, tests, documents, and migrates the same language.

The design refuses local convenience when it creates global ambiguity. Its expressiveness comes from composition: functions over explicit data, closed enums plus exhaustive matching, generic algorithms over nominal capabilities, final identity objects at the edges, and a substantial consistent library. The result should feel high-level during ordinary work and become mechanically transparent when cost, ownership, capability, or native ABI matters.

## 33. Final austerity and joy audit

This is the last whole-design audit before implementation. It applies the interviews' “do more with less,” safety/performance/usability, adoption-through-coexistence, compiler-as-teacher, toolchain, and stability lessons to the complete surface rather than to isolated syntax proposals.

### 33.1 Cuts made by the audit

| Candidate complexity | Final decision | Net result |
| --- | --- | --- |
| Separate payload-free `enum` and payload-carrying `union` declarations | One payload-capable `enum` | Removes one keyword, declaration grammar, generic/layout rule family, teaching distinction, and tooling path without losing any data model. |
| `**` exponent operator | Named checked integer power and `math.pow` APIs | Removes a precedence level and several mixed numeric/overflow rules; the uncommon operation remains clear and searchable. |
| `=>` as shorthand for a short `match` arm | ~~The existing `:` plus a one-statement suite~~ — **later adopted (§9.6)** as the arm delimiter of the expression-valued `match` | A post-freeze revision took the expression form the audit had gated on dogfooding evidence. `=>` is not shorthand for `:`: it means "yields a value", the same role it plays in a lambda body, under a coherent `-> `/`=>`/`:` rule. |
| Mandatory module qualification at every use | Explicit-name `from` imports alongside qualified module imports | Adds one keyword but removes repeated path noise and local forwarding shims; omitting wildcards and per-name aliases keeps origin and collision repair obvious. |
| Long `public` visibility modifier | `pub` | Keeps exported boundaries explicit while matching concise `func` and reducing noise in modules with several intentional API declarations. |
| `error` and `trap` as reserved syntax words | Compiler-known core calls returning `never` | Keeps exact failure semantics while shrinking the lexer/parser and making all terminators visibly call-shaped. |
| A testing framework assembled from attributes, reflection, naming conventions, and privileged helpers | One static `test` declaration plus ordinary library/manifest facilities | Adds one high-yield keyword while removing several ecosystem mechanisms and making discovery, isolation, effects, and production erasure compiler-verifiable. |

The resulting epoch 1 lexer has 43 reserved words, the ordinary data model has two named value declarations (`struct`, `enum`) plus final `class` identity, and expression precedence has 12 levels. These are budgets, not vanity metrics: any increase must identify the older concept or system complexity it removes.

### 33.2 Features that survive the budget

| Mechanism | Why it remains in a small language |
| --- | --- |
| `let` / `var`, explicit functions, narrow control flow | They make the first useful program obvious and leave little style dialect. |
| `T?`, `T!`, and uncatchable traps | Three real computer states need three visible policies; merging them creates sentinel, exception, or recovery ambiguity. |
| Final ARC classes plus `weak` | Shared GUI/resource identity is necessary; ARC supplies deterministic lifetime without making every ordinary function a lifetime proof. |
| Closures with deterministic capture | Callbacks and traversal are unavoidable in the compiler, UI, and native libraries; explicit capture consequences prevent invisible shared state. |
| Restrained generics plus nominal interfaces | Static reuse and dynamic boundaries are different needs. Keeping both, with no associated types/defaults/specialization/reflection, is less total complexity than duplication or metaprogramming. |
| Closed host effects | LuciaOS must audit authority. A small enforced vocabulary exposes real host power without turning allocation and mutation into an academic effect calculus. |
| Isolated `spawn` / `task.wait()` | Parallel work is needed, but copied value graphs and structured lifetime avoid the much larger language/runtime of shared heaps, locks, actors, and async coloring. |
| C plus generated C++ bridges | Coexistence is an adoption mechanism, not syntax luxury. C is the stable boundary; Clang-informed C++ thunks prevent the C++ object model from infecting Luce. |
| Interpreter, direct debug backends, and LLVM | One canonical semantics with swappable code generators gives fast feedback, optimization/target reach, and independence without source-language modes. |

### 33.3 Clockwork invariants

The implementation must preserve all of these simultaneously:

1. **One obvious ordinary path.** Correct common code is the shortest code; advanced control is the code that gains explicit syntax.
2. **One spelling, one meaning.** No overload sets, truthiness, shadowing, ambient imports, profile-dependent arithmetic, or backend-dependent semantics.
3. **No invisible authority or failure.** Host effects appear in public signatures, recoverable failure appears as `!`, and invariant failure terminates a domain.
4. **Costs are either obvious or inspectable.** Allocation, copies, ARC, boxing, bounds checks, generic expansion, worker transfer, and native crossings have stable `luce explain` data.
5. **Tests are production Luce under observation.** They receive isolation and test facilities, never a weaker type/safety/effect language.
6. **Every strict rule teaches and repairs.** A diagnostic names the cause, explains the computer rule, points to the origin, and offers a deterministic fix when one exists.
7. **Every backend is replaceable; semantics are not.** Interpreter, LLVM, x64, and ARM64 agree on behavior, traps, errors, destruction, and native contracts.
8. **Every adoption step is reversible.** A project can add one Luce component behind C/C++ boundaries without rewriting its build, runtime, or object model.
9. **Stability is earned after the whole product works.** The formatter, test runner, packages, debugger, docs, binder, migration tools, and governance are part of 1.0.

### 33.4 Implementation acceptance checks

Before the epoch 1 surface freezes:

- every reserved word, grammar production, core type, operator, declaration, and deliberate exclusion has positive and negative conformance cases;
- every specification example and first-hour tutorial fragment is compiled in CI, and every documented diagnostic is tested structurally;
- production artifacts prove that test descriptions, test code, test dependencies, test capabilities, and test registries were erased;
- representative newcomers can write a pure function and test, diagnose an optional/fallible mismatch, and understand value versus class identity without external help;
- the self-hosted compiler, LuciaOS application, standalone program, C library integration, and C++ integration exercise the same public mechanisms users receive—no compiler-only language escape hatch;
- edit/check/test latency, memory, artifact size, allocation/ARC, and native bridge budgets are measured on named hardware and block regressions;
- any proposed convenience that violates an invariant above is first attempted as a library API, diagnostic/fix, manifest rule, generator, or editor action.

The intended feeling is not cleverness. It is inevitability: the next line is easy to predict, the compiler's objection is easy to act on, the cost can be found, the native boundary can be inspected, and a test is always one `luce test` away.

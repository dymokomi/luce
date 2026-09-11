# The runtime

`rt/kernel.lucb` supplies Luce's managed values. Base's standard `ownership` module
supplies their shared intrusive lifetime protocol, also available to Base libraries
with explicit retain/release. Every compiled Luce program links these modules. The
interpreter (`luce run`) follows the same contract with its own data structures, and the
conformance suite holds the two to it: the order in which objects die is observable through
`deinit`, so it is specified here rather than left to either implementation.

## Objects

A class instance is a heap block: a header, then the fields in declaration order.

| Header field | Meaning |
| --- | --- |
| `strong` | references that keep the object alive |
| `weak` | `Weak` references; the storage stays while any remain |
| `flags` | the collector's colour, whether the object is in the root buffer, whether it is dead |
| `info` | the class's descriptor: its name, size, `deinit`, field release, field trace |
| `generation`, `context` | unique allocation and runtime-thread identities |
| `allocation_size`, `allocator` | the actual block and its recorded allocation owner |

The descriptor's `drop` releases the fields in reverse declaration order and tolerates a
field that was never assigned (an `init` that failed). Its `trace` visits every strong
reference the object holds, fields in declaration order, elements of a collection in index
order, through structs, tuples, enums and optionals.

## Ownership

Every reference is either owned by a binding, a field, an element or a temporary, or is
borrowed for the duration of a call. The rules, which the emitter applies to every statement
and the interpreter follows in its evaluator:

1. A `let`, `var`, `for`, `with`, `if let`, `while let` or pattern binding owns one
   reference to each object its value holds. The reference is released when the binding
   leaves its scope (the end of its block, innermost first, later bindings first, every pass
   of a loop body) or when the binding is reassigned: the new value is computed and stored,
   then the old value is released.
2. A field or element owns its value. It is released when the field is reassigned (after the
   store) or when the owner is destroyed: a class's fields last first, a collection's
   elements in order.
3. A parameter borrows: calling a function does not retain the arguments, and the callee
   retains what it stores. `self` borrows likewise.
4. A call returns an owned reference to the caller; a construction is owned; a read of a
   field, an element or a captured variable is a retained copy. A read of a local binding is
   borrowed.
5. An owned value that no binding takes is a temporary. Temporaries are released at the end
   of the statement that produced them, in the order they were produced, after the
   statement's own effects (a reassignment's release of the old value comes first). A
   temporary produced in the condition of an `if` or a `while` dies before the branch or
   the body runs; the subject of a `match` and the sequence of a `for` live until the
   statement ends; one produced in a `return` dies after the value is computed and before
   the function's bindings.
6. Passing a struct, tuple or enum copies it bitwise; copying a value that holds references
   retains them, and dropping it releases them, members in declaration order.
7. `with a as x, b as y:` nests: when the suite ends, `y` is closed and released, then `x`.
   A pattern binding in a `match` statement and the binding of an `if let` or `while let`
   own a copy of what they bind.

## Imported native values

A copied Base struct contains its complete native representation and a public
projection whose text/data references belong to Luce. Native entry starts from the
complete representation and rebases public fields onto that projection. Rebasing
also initializes immutable field storage in this new copy; it does not mutate the
caller's value or bypass its initializer. A private borrowed field is not eligible
for this representation.

Mutating native methods defer writeback of the complete value on success and
failure. Writeback copies new public references before releasing the old ones.
Errors are given owned text before that cleanup can invalidate a native message
borrow. Bound methods retain an independent value copy. Equality compares rebased
native values, so private fields participate and stale projections do not. Worker
transfer preserves private scalar storage and creates new public text/data owners
on the destination thread.

## Destruction

When an object's strong count reaches zero it is destroyed: `deinit` runs if declared, the
fields are released in reverse declaration order, and the storage is freed unless weak
references remain, in which case the object is dead and `Weak.get()` yields `none` until
the last weak reference frees the shell. `deinit` may not fail, spawn, or publish `self`; a
method called on `self` inside `deinit` may not retain it past the call.

An `init` that fails releases the fields assigned so far, frees the storage, and runs no
`deinit`: the object never existed.

## Cycles

The collector is synchronous trial deletion (Bacon and Rajan, 2001). A release that leaves
the count above zero makes the object a possible root; roots are kept in a buffer, each
object once. The collector runs when the buffer holds 1024 candidates and after `main`
returns; each run:

1. marks every candidate's graph grey, subtracting internal references from the counts;
2. scans: a grey object whose count is still above zero is reached from outside, and it and
   everything it reaches are revived (black); the rest are white, garbage;
3. collects the white objects in discovery order (a depth-first walk from each candidate in
   buffer order, fields in declaration order): every `deinit` first, then every object's
   fields released, where a reference to a live object is an ordinary release and a
   reference to another white object is simply dropped, then the storage freed.

Both executions discover in the same order, so the deinits of a cycle print in the same
order.

## Weak references

`Weak(object)` is a value holding a non-owning reference: constructing or copying it raises
the weak count, dropping it lowers the count, and `.get()` returns the object with a fresh
strong reference, or `none` once it is dead.

## Text and bytes

A compiled program's `str` is a `Text` object: a header, then the bytes, held and released
like any object, so that a run leaves no text behind and the exit check covers it. `bytes`
is the same shape. Every operation that makes text (`+`, an f-string, a slice, `trim`,
`upper`, `split`, a display) makes a new object owned by whoever asked. A literal is an
immortal object: its count never moves, it is never released, and it is never counted as
alive; a literal read is therefore borrowed. Iterating a text yields a new one-scalar text
per step, owned by the loop's binding. The interpreter's texts are plain values and are
not counted; the two executions agree because neither reports a text at exit.

## Closures

A function value is a closure object: a header, then the address of a function taking the
object first and the parameters after, then whatever the closure captured. A lambda's
object holds a copy of every `let` it captured, taken when the lambda was evaluated, and
the cell of every `var`: a captured `var` is a cell object holding the value, shared by
the scope that declared it and every closure that captured it, so all of them see every
assignment. A named function used as a value is an immortal closure holding nothing; a
method bound to a receiver is a closure holding the receiver. A closure is released like
any object, and lets its captures go when it goes; the collector traces through them.

When an operand of a construction, a collection literal or a map store sits beside another
whose `try` may fail (or, in a map literal, beside a call), every operand is evaluated ahead
of the statement into a temporary, in source order, and the taker gets a copy of it: a
failure then drains what was made, and nothing is copied for a taker that never took it.

## Traps

A trap writes `trap: file:line:column: message` and exits with status 1 (luce.md §12.4).
The position is the Luce statement running: the compiled program keeps it in the kernel's
per-thread `heap.site`, which every emitted function's statements set and a deferred
`restore_site` gives back to the caller, and the kernel's own traps report it through
`heap.stop`; a trap Base inserts into the emitted code, an overflow or a division by zero,
reports the same position through the `#:` directive written before each statement
(base.md §3.3). The interpreter keeps the statement per frame and checks its own
arithmetic, so it stops with the same text.

## Interface values

An interface value (§13.2) is a pointer to a box: an object whose header is followed by a
pointer to the table of the boxed type's methods for that interface, then the value itself,
a copy taken when the conversion happened. Copies of the interface value share the box;
a box is never changed, so sharing is invisible. A call through the interface is one
indirect call through the table. Releasing the last copy drops the boxed value, which is
how a class behind an interface value goes when the value does; the collector traces
through the box, so a cycle through interface values is found like any cycle. Every
box of one interface and one conforming type shares one table, emitted once.

## Workers

A task (§14) is an object of the spawner's heap holding the arguments, the worker's copies
of them, and the result. Every thread has a heap of its own: the object counts, the
temporaries pool and the collector's candidates are thread-local. The worker copies the
arguments onto its heap (a text or bytes anew, a collection with its elements copied, a
struct, enum, tuple or optional member by member) and only then does `spawn` return, so
the spawner may change what it passed; it runs the call, keeps the result or the failure's
code and message, and signals. `wait` copies the result onto the waiter's heap, or raises
the failure, and lets the worker release its copies and end; a worker that leaves objects
alive stops the program with `luce: N objects alive when a task ended`. A task is waited
once; a second `wait` traps. Releasing a task not yet waited waits for it and discards the
result. After draining temporaries and collecting cycles, a finished worker also frees
the backing arrays for temporaries, candidate roots, and white objects. Empty object
counts alone do not account for that native storage; retaining those arrays would
leak when thread-local roots disappear. A successful `main` cleanup releases its
arrays as well. The interpreter runs the call at `spawn`, with copies in and out the same way.

## Handles

A handle (§16.4) is an object holding the Base value and whether it was closed. `close()`
calls the module's `destroy` once and remembers it; releasing the last reference calls
`close()`; a closed handle handed to Base traps. The handle's declared destroy function
is reached through a shim that calls the wrapper's `close()`
instead of handing its raw value to Base, so direct and automatic destruction share the
same closed state. Other Base functions are reached through a
shim per function that lends texts and lists as views, converts structs, enums and
optionals member by member, copies a text or bytes answered, and wraps a handle answered.

## Hashing

`hash(x)` (§4.4) is the same number in both executions: FNV-1a over 64 bits (offset
14695981039346656037, prime 1099511628211) of the value's canonical bytes, and the result
reinterpreted as an `int`. The canonical bytes: an `int` is its eight bytes little-endian;
a `float` the eight bytes of its IEEE encoding, with `-0.0` written as `0.0`; a `bool` one
byte, 0 or 1; a `str` or `bytes` its bytes then the byte 255 (so that `("a", "b")` and
`("ab", "")` differ); `unit` nothing; a tuple or struct its members in order; an enum its
case's index as an `int` then its payload; an optional the byte 0 for `none` or the byte 1
then the value; a range its two bounds and a byte for inclusion; a list its elements in
order; a set its elements' hashes summed (as unsigned arithmetic, wrapping); a map each
entry's key hash times 31 plus its value hash, summed the same way; an `ErrorCode` its
number. A type that declares `Hashable` (§13.3) hashes as the `int` its `hashed` returns
(so `hash(v)` is the hash of that `int`, and `v` inside a tuple or list mixes the same way);
a class hashes only that way, never structurally.

Maps and sets keep insertion order, and removing an entry keeps the order of the rest, so
iteration and display never depend on the hash.

## Temporaries in emitted Base

A statement whose expression produces temporaries is wrapped:

```
let L_mark = kernel.mark()
errdefer kernel.drain(L_mark)
<the statement, each temporary passed through kernel.pool>
kernel.drain(L_mark)
```

`kernel.pool` copies the value into the pool with its release function and hands it on;
`drain` releases everything above the mark in the order it was pooled. A second `drain` to
the same mark is a no-op, which is why the `errdefer` is safe.

## What a run leaves alive

After `main` returns and the collector has run, no object may be alive: the language has no
global mutable state. Both executions count live objects and, when the count is not zero,
print `luce: N objects alive at exit` to standard error and exit with status 3. The
conformance suite therefore proves, for every program, that everything was released.

## Error message ownership

A caught `Error` owns a counted text. Copying the error retains that text; dropping the
last copy releases it. Errors saved in collections or returned from a catch follow the
same ownership rules as other values containing references.

While Base propagates its borrowed error view, a thread-local chain holds a reference
to each raised Luce message. A catch takes that reference and removes the chain entry;
a Base or builtin failure supplies a copied text. Nested catches during cleanup cannot
replace a message still propagating. No dynamic text becomes immortal or leaves the
heap's live-object accounting.

A worker keeps its failure until the waiter copies the text to its own heap. The worker
then releases it, including when a task is abandoned. Sending an `Error` as an ordinary
argument or result also copies its text. Unhandled main and test failures release their
messages before the final heap check.

A module function used as a Luce value is an immortal closure over its existing call
adapter. Fallible closure calls propagate Base failures explicitly. Named functions
with callback-compatible signatures also carry a static Base entry; an indirect call
to a Base function taking a raw function pointer uses that entry. It remains valid if Base stores
it. Capturing closures and bound methods have no such entry and trap if an indirect
Base call attempts to pass them as callbacks. Direct calls retain the named-function
check in the checker.

## Retained native callbacks

`interop.Callback[A, R]` crosses as a captured `func(A) -> R!`; a `unit` argument
means no arguments. The native carrier retains the closure's existing owner and
traces its captures. Returned native callbacks have a traced closure wrapper;
round trips unwrap the original carrier/closure. The source thread is checked
even for a named function with immortal storage. Raw native function pointers keep
their capture-free contract.

Invocations return `Outcome[R]`. Reverse calls place managed results in traced
`Owned` storage, and transfer dynamic failures out of Luce's pending-error chain.
Native callers can handle and release them directly. Captured checked views retain
their lease and still expire at the original scope boundary.

`interop.Signal[A]` owns retained callbacks and returns standard `Connection`
owners. Each emission snapshots registration order, skips removed connections and
defers additions to the next emission. The active callback stays retained through
return. Closing the signal skips remaining delivery; failure stops the emission
with an owned error. Connections and callback captures participate in the shared
cycle graph. See [the lifecycle contract](../../luce-base/docs/CALLBACKS-WORKERS.md).

## Native application workers

A Base library takes `interop.WorkerEntry[C, M, R]` where Luce supplies a named
factory returning its local `Callback[M, R]` handler. The descriptor contains code
and runtime entry/exit hooks, with no retained source-thread graph. The generated
factory adapter runs after the worker enters its runtime, copies configuration
into that graph and returns an owned handler. A `unit` configuration or message
maps to a factory or handler with no arguments.

The standard worker owns bounded input/reply queues. Transfer policies copy native
payloads into neutral packets before publication, and copy replies before releasing
the worker's local Outcome. Package methods convert received packets into owned
results on the receiving thread. `sema.transfer` applies the same recursive rule to
language tasks and native workers, and rejects thread-bound payloads even if an
ordinary function value later erases the native signature. Direct calls reject
captured factories statically; indirect adapters check their capture-free immutable
representation before thread creation.

Cancellation wakes blocked queue operations and rejects late dispatch. The current
handler may finish; queued work and replies are discarded. Native blocking package
operations use the worker's cancellation signal. Shutdown releases application
state and collects local cycles on the worker, verifies zero live owners, and joins
before freeing queues. Startup failure follows the same joined cleanup and copies
its diagnostic to the creator's scoped temporary pool. The Base lifecycle contract
specifies manual ownership, queue backpressure and concurrent caller responsibilities.

## Declared native objects

An imported `interop.Type[T]` declaration makes its Base struct an owned Luce
class. Generated class types alias `interop.Owner[T]`; there is no second wrapper
or independent count. `Reference[T]` parameters borrow that owner and returned
carriers transfer one reference. Native containers clone retained edges and expose
them to the shared tracer. Bound methods hold the same owner; value-bound methods
continue to hold independent copies.

Constructors reserve an unpublished owner, initialize the actual native allocation
and publish only after success. Initializer failure frees its allocation and the
unpublished owner without running successful-object disposal. Close publishes the
terminal state before cleanup; every alias sees it. An active method retains its
receiver until return. Fallible access to a closed object returns the standard
interop error, while infallible access traps. Weak references keep only the shell.

Public field reads copy text/data or acquire child references. Direct field writes
are limited to native `i64`, `f64` and `bool`; replacing owned/borrowed native storage
requires a package method. Native owner objects cannot cross to workers.

The boundary emitter keeps native conversions in `back.crossings`. It shares an
output writer and lifetime registrations with the expression emitter, but never
evaluates application expressions itself. Native signature keys include carrier
ownership and scalar spelling, including `usize` versus `i64` inside nested types.

Reference spans are temporary arrays backed by the call's pool. The source list
keeps its elements alive, and a Base callee clones any reference it retains. This
applies to explicit owners, checked views, interfaces and opaque handle arguments.
Opaque handles have no general clone operation: their direct results transfer one
destruction obligation, and they cannot be exposed as borrowed fields or payloads
of retained result carriers. A reverse interface call requires parameters whose
borrowed values can be copied or cloned into Luce. Raw handles, raw callbacks and
spans lack that reverse adapter and are rejected for managed implementations.

## Package link inputs

The source bundle resolves native inputs through Base's current dependency
protocol. Base owns interpretation of `[native]`; Luce merges the returned
sources, libraries, search directories, frameworks and pkg-config entries into
one generated manifest. Source/search paths are absolute paths resolved against
the declaring package. Both direct Luce packages and transitive Base packages
participate. Normal builds discard the temporary source bundle on success and
failure; explicit Base emission retains it for inspection and keeps references
to original native inputs.

Standard window/GPU backends supply their own system requirements. Base selects
those from the actual generated object, so a Luce application need not copy
platform framework lists. Portable `gpu.Frame` recording and checked targets can
be used without a window or graphics library; an attached surface supplies the
presentation operations. Retained target methods share the frame's checked lease
and fail after presentation or closure.

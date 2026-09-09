# The runtime

`rt/kernel.lucb` is the Base package every compiled Luce program is linked with. The
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
   store) or when the owner is destroyed.
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

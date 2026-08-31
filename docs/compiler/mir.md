# Canonical MIR — a guided tour

This document explains the compiler's *machine intermediate representation*:
the form a Luce program takes after the front end has understood it and
before a backend turns it into machine code.

If you have read the top-level README you know the pipeline:

```
source → tokens → syntax tree → typed HIR → canonical MIR → backend
                                    │                    ├→ QBE
                                    └→ reference         ├→ wasm
                                        interpreter     └→ future native encoders
```

Typed HIR is the program *as the language sees it*: names resolved, types
known, still shaped like source code. MIR is the program *as a machine sees
it*: explicit registers, explicit memory, explicit control flow. Every
compiled backend starts from MIR, so MIR is where the compiler decides,
what the machine will do. The word *canonical* means exactly that: there is
one MIR, and the backends may only translate it, never reinterpret it.

The language rules MIR must obey live in [`../language/1.0.md`](../language/1.0.md);
section numbers below (§7, §13, …) point there.

---

## Part one: the story

### A program to follow

Here is the program we will carry through the whole tour. It is small, but
it touches almost everything MIR has to handle: a local variable, a loop, a
condition, a call, and a way to fail.

```luce
func sum_to(limit: i64) -> i64:
    var total = 0
    var i = 1
    while i <= limit:
        total += i
        i += 1
    return total

func checked_sum(limit: i64) -> i64!:
    if limit < 0:
        error(math.negative, "limit must not be negative")
    return sum_to(limit)
```

Keep it in mind. Each section below lowers a little more of it.

### Registers

Start with the simplest line, `total += i`. In HIR that is an assignment
whose value is a resolved `Add(i64)` of two references. In MIR it becomes:

```
r4: i64 = Load i64, r1          ; read `total` from its slot
r5: i64 = Load i64, r2          ; read `i`
r6: i64 = Add r4, r5
Store i64, r1, r6               ; write `total` back
```

Two things just appeared. The first is the **register**: `r4`, `r5`, `r6`.
A register is a named, typed value. Each register is written exactly once —
there is no `r6 = r6 + 1` — so when you see `r6` anywhere in a function you
know precisely which instruction produced it and what type it has. 

The second is the pair `Load`/`Store` around `r1`. If registers are
write-once, where does a *mutable* variable like `total` live? In memory.
Every `var` gets a **slot**, a small piece of the function's stack frame,
and its address sits in a register (`r1` here, produced by `Alloca` at the
top of the function). Reading the variable is a `Load`, writing it is a
`Store`. This looks wasteful, and for a machine it would be — but MIR is not
the machine. A later optimization pass can notice that `total` never has its
address taken and promote it back into registers. MIR chooses the simple,
obviously correct form and lets optimization earn the fast one.

> **Why not an operand stack?** The first slice of this compiler used a
> stack machine (`push 2, push 3, add`) because WebAssembly is one. But
> the two directions are not equally hard. Turning registers into wasm
> locals is one line per register. Turning a stack into registers means
> simulating the stack — tracking its depth and spilling it — just to
> rediscover the values it holds, and every native backend would do that
> work. So MIR uses registers: the form that is cheap for *both* kinds of
> target. If the wasm backend later wants wasm's operand stack for
> expression trees, that is an optimization inside the wasm backend.
>
> Control flow, in the next section, goes the other way — MIR keeps the
> structured shape WebAssembly wants, because *that* is the form cheap to
> translate in both directions. MIR is not designed to be easy for one
> target; on each axis it takes whichever form the other side can absorb
> for free.

### Control flow: keeping the shape the source already has

Now the loop. Here is `sum_to` in full:

```
func sum_to(r0: i64) -> i64
    r1: Ptr = Alloca slot0            ; total
    r2: Ptr = Alloca slot1            ; i
    r3: i64 = Const 0
    Store i64, r1, r3
    r4: i64 = Const 1
    Store i64, r2, r4
    Block                             ; ┐ leaving this block ends the loop
      Loop                            ; │ ┐ branching here restarts it
        r5: i64  = Load i64, r2       ; │ │
        r6: Bool = Le r5, r0          ; │ │  i <= limit
        r7: Bool = BoolNot r6         ; │ │
        BrIf r7, 1                    ; │ │  not (i <= limit) → exit the Block
        r8: i64  = Load i64, r1       ; │ │
        r9: i64  = Add r8, r5         ; │ │  total += i
        Store i64, r1, r9             ; │ │
        r10: i64 = Const 1            ; │ │
        r11: i64 = Add r5, r10        ; │ │  i += 1
        Store i64, r2, r11            ; │ │
        Br 0                          ; │ │  back to the Loop
      End                             ; │ ┘
    End                               ; ┘
    r12: i64 = Load i64, r1
    Return r12
```

Notice what is *not* here: no labels, no `goto`, no jump to an address.
Control flow in MIR is **structured**. `Block` and `Loop` open regions that
their matching `End` closes; `Br 0` means "branch to the innermost enclosing
region" and `BrIf r7, 1` means "if `r7`, branch to the one outside that".
Branching to a `Loop` restarts it; branching to a `Block` leaves it. `If`
(with an `Else` between its arms) and `Switch` (with a `Case` before each
arm and a `Default`) nest the same way. That is the whole control-flow
vocabulary — and the listing above *is* the representation: a function body
is one flat list of instructions in which `Block`, `Loop`, `If`, `Switch`,
`Else`, `Case`, `Default`, and `End` are ordinary entries. Nothing nests in
memory; nesting is a property of the sequence, exactly as in a WebAssembly
function body.

A region can also *produce* values — the conditional expression
`a if flag else b` is an `If` whose two arms each end in `Yield` with their
value, and the `If` names the register that holds the result afterwards.
Because registers are write-once, the arms do not assign that register
themselves; they hand a value to the region, and the region defines it.
That is the structured form of what graph-based compilers call a phi.

If you know WebAssembly you will recognise this exactly, and that is not a
coincidence — but it is not the reason either. The reason is that **Luce has
no `goto`** (§9). Every Luce program's control flow is already a nest of
blocks, loops, and ifs. If MIR flattened that into a graph of basic blocks
and jumps, the native backends would be happy, but the wasm backend would
have to *rebuild* the structure from the graph. That reconstruction — the
"relooper" problem — is real work and a well-known source of subtle bugs.
Going the other direction is trivial: a native backend turns each `Block`
end into a label and each `Br` into a jump, in a dozen lines.

So MIR keeps the structure the source came with. The cost is honest: a few
optimizations that like an explicit graph (jump threading, block layout) are
awkward on structured code. When a native backend needs them, it can build a
graph *after* canonical MIR as its own private step. Canonical MIR does not
change.

Custom struct initialization reuses the aggregate protocol without adding a
MIR instruction. HIR's `Initialize` allocates fresh caller-owned struct
storage, passes its address as parameter 0 (`self`) to the initializer, and
yields that address after the unit-returning call succeeds. A fallible
initializer places the caller-owned `Error` slot before `self`, exactly like
every other fallible call. Definite initialization has already been proved in
typed HIR, so MIR never represents a partially initialized value outside that
call.

### Failing: errors are just values

On to `checked_sum`, which can fail. In Luce a function returning `T!`
returns either a `T` or an `Error` (§13.2). Many compilers implement that
with exceptions, unwinding, and landing pads. MIR does something plainer:

```
func checked_sum(r0: Ptr, r1: i64) -> (i64, Ptr)
    ; r0 is storage for one Error, owned by this call's caller
    r2: Bool = Lt r1, 0
    If r2
      r3: Ptr = FieldAddress Error, r0, 0       ; error.code
      r4: Ptr = DataAddress data0               ; constant math.negative
      Memcpy r3, r4, ErrorCode
      r5: Ptr = FieldAddress Error, r0, 1       ; error.message
      r6: Ptr = DataAddress data1               ; constant str value
      Memcpy r5, r6, str
      Raise r0
    End
    r7: i64 = Call sum_to, r1                   ; sum_to cannot fail: one result
    r8: Ptr = Const null
    Return r7, r8                               ; value present, error absent
```

A fallible scalar function receives a hidden **caller-owned `Error` slot** as
parameter 0 and has two results: the value and a pointer to that slot. The
pointer is null on success; on failure it is exactly parameter 0. `Raise r0`
is `Return` with an absent value and the filled slot. The callee never returns
a pointer into its own frame and failure needs no heap allocation or hidden
runtime ownership.

Now look at how a fallible *caller* propagates it:

```
r9: Ptr = Alloca error_slot
r10: i64, r11: Ptr = Call checked_sum, r9, r1
r12: Ptr = Const null
r13: Bool = Ne r11, r12
If r13
  Memcpy r0, r11, Error                         ; copy into our caller's slot
  Raise r0                                     ; `try` runs active defers first
End
```

`try` is a call followed by one conditional branch. `catch` is the same
branch, aimed at the handler instead. There is no hidden state, nothing to
unwind, nothing a backend has to know beyond calls and branches. Errors are
data flowing through registers like everything else.

`defer` fits the same picture. A deferred statement must run on every way
out of its scope — normal return, `try` propagation, `break` out of a loop.
In structured control flow every one of those exits is an explicit `Br` or
`Return`, so the lowerer simply *copies* the deferred statements in front
of each one. Duplicated code, yes; but mechanical, verifiable, and free of
any runtime mechanism. Traps (§13.4) do not run deferred code, exactly as
the language says.

### Memory: structure in MIR, byte layout in the backend

Our example only has integers, so let us add a struct:

```luce
struct Point:
    let x: i64
    let y: i32
```

Scalars and pointers live in registers. **Anything with more than one
part lives in memory** — that one rule decides where every value goes. A
`Point` local is a slot; reading `p.y` is:

```
r3: Ptr = FieldAddress Point, r2, 1     ; address of field 1
r4: i32 = Load i32, r3
```

`FieldAddress` names field 1; it does not contain the byte offset. MIR's
`Struct` stores the fields in declaration order and `Enum` stores its tag and
case payload types. That is the language-visible structure. The selected
backend computes and caches sizes, alignments, field offsets, enum payload
placement, and pointer width while encoding the program.

This boundary is strict. Lowering runs once, before a backend is selected,
and the same `MirProgram` can be handed to wasm, QBE, or a future native
encoder. The C boundary does not weaken that rule: a `c` signature records
the C-representable shape and the backend applies that target's ABI and data
layout. Target names, ABI placement, and byte layout never occur in HIR or
MIR.

Raw storage pointers are untyped: `Ptr` is just address authority. The stored
type travels on the `Load`, `Store`, or address operation that uses it, which
is what a backend actually needs. Language reference handles are different:
`List(element)` retains the source element identity in canonical MIR even
though each backend represents the handle with pointer-sized bits. It is not
interchangeable with `Ptr`, cannot be forged by a null constant, and lets the
verifier prove that every creation, access, and shape mutation uses one
canonical element type.
Type identities may therefore point forward. The verifier walks the layout
dependency graph and rejects only a genuine by-value cycle; a reference break
such as `Node { children: list[Node] }` is well-founded.

### The runtime: explicit calls and typed service bindings

The typed allocation substrate and first list operations are canonical MIR
now. Application lowering emits list operations only after HIR has established
the collection's element identity; reviewed runtime source emits typed storage
requests while implementing the private header and growth policy.

Where does memory for a `list` come from? Who counts references for a
class? Who prints? Ownership and I/O remain **calls to a small, fixed set of
runtime symbols**. Allocation is the one operation that must retain its
structural type until the backend boundary:

```
r0: u64 = Const 3
r1: Ptr = AllocateStorage Point, r0
CallExtern luce_rt_retain, r1
CallExtern luce_rt_write, r2, 13
```

`AllocateStorage` means storage for `r0` consecutive `Point` values. It does
not contain `sizeof(Point)` or `alignof(Point)`. `MirProgram.runtime_bindings`
maps the semantic `storage_allocator` service to one exact private Luce
`FunctionId` with signature `(u64 byte_count, u64 byte_alignment) -> Ptr`.
The selected backend performs checked count-by-size legalization from its
layout cache and calls that definition directly. It never searches a function
or linker name. This is the same boundary that already turns `FieldAddress`
into a target byte offset; the lowerer and canonical program remain identical
for Wasm and QBE.

Lists follow the same separation without duplicating the element type on each
instruction. A `List(T)` register is the semantic handle; `ListCreate`,
`ListCopy`, `ListLength`, slot insertion/removal, reservation, clearing, and
`ListElementAddress` derive `T` from that register. Operations that move or
address elements ask the backend to pass its computed size/alignment to the
exact composed runtime service. Bounds checking is part of canonical list
indexing, insertion, and removal; private runtime functions perform only the
unchecked storage operation after the backend guard. Capacity, header layout,
and geometric growth remain ordinary freestanding Luce runtime policy.

The spec (§23.4) lists what the runtime provides — allocation, ARC,
weak references, dynamic strings and collections, traps, worker spawn and
join — and says it should be "small and explicit enough to replace per
host". The sealed `libluce_rt` source package is composed with application MIR
before optimization and verification, so QBE receives one complete program;
supporting backends may consume that same program where applicable. Only the
tiny stable-arena provider remains backend-owned: Wasm may grow its memory,
while native may reserve/commit virtual storage. Neither fact appears in HIR
or canonical MIR. The full service list is in the appendix.

Composition is an identity remap, not a source import or a link step. The
application's tables remain the prefix unchanged. The runtime's canonical
builtin prefix maps back to those same builtin identities; its remaining
types, functions, globals and data are appended, its equal external
declarations are interned, and every reference in its instructions and
service bindings is rewritten once. A conflict is reported before
verification. The composer rejects application-owned service bindings and a
runtime entry, public function or artifact export, preserving the sealed
boundary structurally. The combined program alone then enters verification,
reachability and backend encoding.

The source package descriptor makes the first identity selection explicitly:
`(RuntimeService, module, function)` is resolved during sealed-runtime HIR
generation to a private native `SymbolId` with the service's checked source
signature. Lowering maps that symbol through the ordinary callable table to a
`FunctionId`. Composition, optimization and backends therefore never repeat
the spelling lookup. The shared `runtime_contract.luc` vocabulary contains no
ABI, layout, capacity or platform information.

The source side of runtime state is equally closed. An explicit
`PackageRole.sealed_runtime` compilation may declare private
`var next_offset: u64` cells with structural zero initialization. HIR keeps
their reads and writes observable; lowering maps them to canonical
`MirGlobal` storage and `GlobalAddress` without choosing an address. QBE
places each cell in target data, while supporting backends such as Wasm may
place it in their own linear-memory plan. Applications cannot declare or
import runtime cells.

Native source authority is already resolved metadata before HIR generation.
HIR keeps `native_ptr[T]` and `native_mut_ptr[T]` distinct, including the
pointee `TypeId`, so native operations can be checked structurally without
knowing a pointer width or layout. Public source shapes cannot contain either
form. When HIR becomes canonical MIR, the address value itself maps to `Ptr`;
the typed operations that consume it retain their structural value type. Thus
authority checking ends before MIR while layout still begins only in a
backend.

The first closed operations reuse MIR that already expresses their complete
meaning: `native.load` becomes typed `Load`, `native.store` becomes typed
`Store`, and element-count `native.advance` becomes `ElementAddress`. A
contextually typed `native.rebind` changes only the audited HIR pointee view
and therefore erases to its unchanged `Ptr` register. Overlap-safe
`native.move` becomes `MoveElements`, retaining one element `TypeId` and a
`u64` count so each backend alone computes and checks its byte count. The HIR
checker proves address mutability and matching pointees before pointer-type
erasure. No native-operation symbol, byte offset, pointer width, or target
layout survives into MIR.

The sealed-runtime-only `native.allocate[T](count)` becomes the existing
`AllocateStorage(T, count)` instruction. Its HIR result keeps the typed mutable
pointer needed by reviewed runtime source; lowering erases only that address
shape to `Ptr`, while the stored `TypeId` and element count remain structural.
The verifier requires the exact private storage-allocator binding, and each
backend alone legalizes the request using its layout rules.

The sealed arena adds no memory-layout instruction. HIR admits
`native.arena(end)` only for a native module in the runtime package and lowers
it to the verified runtime-convention service `(u64) -> Ptr`. Canonical MIR
therefore records only a stable-base/prefix request. The MIR oracle chooses a
small deterministic capacity; QBE reserves backend-owned zero-filled storage
and guards the requested end. A future Wasm implementation may grow linear
memory. Capacity, page size, reservation API and commit granularity never
appear before a backend.

Retain and release calls are placed by the lowerer using the ownership facts
that `SemanticAnalyzer` will attach to HIR (§11.3). Until that analysis
exists, the lowerer uses the simplest rule that is never wrong — retain on
copy, release at scope end — and leaves it to an optimizer to remove
balanced pairs.

### Things that are gone before MIR sees them

A few language features never reach MIR at all; they are rewritten into
things MIR already has.

- **Generics** are monomorphized (§15): each use with concrete types becomes
  its own plain function.
- **Closures** become a struct holding the captures plus an ordinary
  function whose first parameter is that struct. A captured `var` is a
  runtime cell shared by reference (§14.1).
- **Interface values** are a pair of pointers — the data and a *witness
  table*, a constant block of function pointers in requirement order
  (§16.3). Calling through an interface is loading a pointer from the table
  and calling it.
- **Names** are gone: functions, globals, and data are numbers. The strings
  survive only for artifacts and diagnostics.

Each of these could have been an instruction. Each would have made every
backend implement it. As data-plus-calls they cost nothing new.

### Meaning is fixed here, not in the backend

One more thing about that `Add` in `sum_to`. Luce integer arithmetic
**traps on overflow** (§7: "integer overflow and invalid shifts trap in
every normal build profile"). `//` is floor division; `minimum // -1`
traps. So `Add` in MIR *means* checked addition. That is a rule about what
MIR says, not about how a target does it.

WebAssembly's `i64.add` wraps silently. Its division truncates. Its shifts
mask the count. None of that changes what the Luce program means, so the
wasm backend must *legalize*: emit the add, test for overflow, trap. A
native backend can use the overflow flag. What no backend may do is decide
that wrapping is fine. This is the same rule the HIR interpreter already
follows — which is why the interpreter can be the oracle for the compiled
path.

### How we know any of this is right

Three independent executions of every test program:

1. the **HIR interpreter**, which executes typed HIR and has never heard of
   MIR — so a lowering bug cannot hide in it;
2. a **MIR interpreter**, a few hundred lines that walk the structured
   instructions above using explicit backend layout rules and no host ABI;
3. the **compiled artifact**: a wasm module under `wasmtime`, or a native
   executable.

When all three agree, good. When one disagrees, the other two tell you which
stage is wrong. The MIR interpreter also doubles as the constant folder,
because §7 demands that folding use runtime semantics, and sharing the code
makes that true by construction.

Underneath the testing sits the **verifier**, which runs before and after
optimization and proves the structural rules: every register defined once
and before use, types match, branch depths in range, aggregate type references
are well founded, fallible paths end in `Return` or `Raise`, and C-convention
signatures carry only C-representable types. Byte layout is not a verifier
input because it does not exist in MIR. Backends assume the verified meaning
and choose its target representation.

### QBE native backend

Stage 1 uses [QBE](https://c9x.me/compile/) 1.3 as its native oracle. The
backend translates canonical MIR directly into QBE IL:

| Canonical MIR | QBE IL | Effort |
|---|---|---|
| write-once registers | temporaries; QBE builds SSA itself | trivial |
| `Alloca` / `Load` / `Store` slots | `alloc8` / `loadl` / `storel`; QBE promotes non-escaping slots | trivial — the promotion pass becomes QBE's |
| external-global load/store | typed load/store through `extern $symbol` | QBE's dynamic constant owns GOT/PIC access |
| `Block` / `Loop` / `If` / `Br` | labels, `jmp`, `jnz` | a dozen lines |
| `Block` result registers | assign a temp on each path; QBE inserts the phi | trivial |
| structural `Struct` / `Enum` | memory plus backend-computed offsets and `blit` | direct |
| `convention = c` | QBE ABI extension types and platform ABI lowering | scalar and nominal-handle imports/exports complete; richer translations remain |
| `CallExtern`, `FunctionAddress`, `ExternAddress`, `DataAddress` | direct C call, defined/imported callable tokens, named data | direct |
| checked `Add`, trapping shifts, floor `//` | no overflow flags in QBE: compare sequences | the one place QBE costs more than hand-written native code |
| typed `List(T)` operations | `l` handle plus direct calls to exact composed runtime functions | QBE layout supplies `sizeof(T)`/alignment; MIR stays structural |
| fallible `(value, error pointer)` plus caller-owned error parameter | error pointer return plus a private scalar-result out pointer | backend-local ABI |
| narrow integer types | `w` temporaries plus explicit extension, guards, and sub-word memory operations | direct legalization |

The QBE backend owns target layout, lowers
structured control flow to QBE's graph, and relies on QBE for ABI lowering,
instruction selection, and register allocation. The first implementation
uses the real QBE toolchain as both oracle and product native path. IL is fed
to QBE over stdin and its assembly is fed to the host C driver over stdin. The
linked candidate is the only intermediate file; it lives in an atomically
owned directory beside the requested output and replaces that output by an
atomic same-filesystem rename. A later Luce-native backend can be
differential-tested against this baseline. Both paths consume the same
canonical MIR; neither adds target-specific lowering before the backend
boundary.

Two consequences for the design record:

- The result pair of a fallible scalar function states MIR's *meaning*.
  Error storage and its lifetime are already fixed by the explicit parameter;
  each backend only picks how to return the scalar-and-pointer pair: wasm
  multi-value, QBE an error-pointer return plus a private result out-pointer.
- Narrow integer types remain exact in canonical MIR. QBE holds them in `w`
  or `l` temporaries and uses explicit extension, range guards, and sub-word
  loads/stores at the backend boundary.

### What comes next

- **wasm** maps one-to-one: regions to `block`/`loop`/`if`, registers to
  locals, externs to imports; it legalizes checked arithmetic. Its host
  contract is WASI preview 1 — `luce_rt_write` becomes `fd_write`, an
  entry gains `_start` and `proc_exit` — so a module runs under any wasm
  runtime with no bespoke host.
- **QBE native** links C externs and the future `libluce_rt` through the host
  toolchain. Luce-native backends begin only after the language and runtime
  baseline is complete, and must prove the same canonical MIR against QBE.
- The order of work: new `mir/canonical.luc` and verifier → MIR interpreter
  and the three-way harness (both done: `tests/compiler/differential_test.luc`)
  → the lowerer in vertical slices (scalars and locals, control flow, calls and constants — done;
  enums and `match`, structs and ARC, closures and interfaces, failure and
  `defer`, collections, the C boundary, workers) → wasm encoder tracking
  each slice → native backends from MIR once it stops moving.

---

## Part two: the reference

### The program

```
MirProgram
    types       list[MirType]       every target-neutral type used
    externs     list[MirExtern]     imported symbols: C functions and the runtime
    external_globals list[MirExternalGlobal] C-owned observable scalar state
    globals     list[MirGlobal]     module-level mutable state
    data        list[MirData]       address-free constant bytes, such as string payloads
    functions   list[MirFunction]
    entry       FunctionId?         process entry when the artifact is an executable
```

Identities are indices: `TypeId`, `FunctionId`, `ExternId`,
`ExternalGlobalId`, `GlobalId`, `DataId`. A call names a function *or* an
extern; the artifact decides how each is bound (wasm import versus linker
symbol).

### Types

| MirType | Meaning |
|---|---|
| `Int(bits, signed)` | `i8`…`i64`, `u8`…`u64`; source widths are kept |
| `Float(bits)` | `f32`, `f64` |
| `Bool` | one byte, 0 or 1 |
| `Ptr` | abstract address, untyped; its width is a backend fact |
| `List(element)` | typed mutable reference collection handle |
| `Slice(element)` | typed immutable snapshot handle |
| `Struct(fields)` | fields in declaration order; byte placement is a backend fact |
| `Array(element, count)` | fixed arrays |
| `Enum(tag, cases)` | tag is an `Int`; each case is a `Struct` payload |
| `Func(signature)` | what a function pointer points at |

How language types map onto them: `bool` → `Bool`; `char` → `Int(32,
unsigned)`; `str` and `bytes` → a `{Ptr, u64}` `Struct` (address and
length; a literal's bytes are a data item); `list[T]` → `List(T)` and
`slice[T]` → `Slice(T)`, both opaque reference-sized handles whose concrete
headers are runtime/backend facts; future `map` and `set` handles follow the
same typed-reference rule; `T?` → a two-case `Enum` with a `u8` tag (a null niche for
future managed class references is still open, but foreign handles stay
tagged internally); a scalar `T!` result → a scalar and error pointer, never a
type;
tuples → anonymous `Struct`; `array[T, N]` → `Array(T, N)` with `N` retained
as a target-neutral type fact and element placement deferred to the backend;
class references and `weak` → `Ptr` managed by
the runtime; interface values → a two-`Ptr` `Struct`.

Aggregates never sit in a register. The lowerer's protocol: a register of
aggregate type holds the value's *address* (a slot, a field, a parameter's
pointer), copies are explicit `Memcpy`s, a function returning an aggregate
takes a hidden leading `Ptr` parameter for the caller's result slot and
returns nothing, and an aggregate parameter is passed by pointer (safe
because parameters are immutable). A fallible function reserves parameter 0
for the error slot; when its success value is an aggregate, the result slot is
parameter 1. Source parameters follow both hidden parameters.

### Functions, externs, globals, data

```
MirFunction
    name          `module.function`, or the export symbol
    convention    luce | c
    params        list[TypeId]
    results       list[TypeId]        0, 1, or 2 (value, error pointer)
    fallible      bool                parameter 0 owns Error; last result reports it
    registers     list[TypeId]        every register, by index
    slots         list[TypeId]          backend computes size and alignment
    body          list[Instruction]   structured, see below
    is_public     bool                  source-package API visibility
    is_exported   bool                  explicit artifact symbol, independent of `pub`
    span          SourceSpan

MirExtern     name, convention (c | runtime), params, results, fallible
MirExternalGlobal name, value type
MirGlobal     type, initial: DataId?, is_mutable
MirData       bytes, minimum alignment
```

`convention = c` marks an export (§21.5) or a callback handed to C. Such a
signature may contain only C-representable types; the backend then applies
the target's C ABI. `MirData` is address-free raw payload. Address-bearing
constants will use a typed, structural MIR representation when the language
needs them; target-sized relocation slots do not belong in canonical MIR.

`is_public` retains source-package API visibility without turning it into a
native ABI promise. `is_exported` records the orthogonal artifact decision
made by an explicit boundary declaration; a process entry is the independent
`MirProgram.entry` root. Reachability keeps all three root families separate.
Wasm can expose its package API while QBE/native exports only explicit C
symbols and the entry. A rootless private library is preserved because its
eventual consumer set is not yet known.

Source-level C imports are not a second HIR call system. A `HirFunction` has
one symbol and one closed implementation choice: defined Luce body, defined C
export, or host-supplied C function. All three use the ordinary `Call` node
and argument placement. The lowerer performs the only split, mapping that
identity to either a MIR `FunctionId` or `ExternId`; Wasm then chooses its
`env` namespace and QBE/native interprets the same extern name as a linker
symbol. Neither namespace nor ABI byte placement appears before a backend.

An `extern type` is nominal in HIR and therefore cannot be constructed from,
converted to, or used as its backing representation. The lowerer's ordinary
type mapping is the single erasure point: an integer-shaped handle becomes its
declared exact MIR integer, while a pointer-shaped handle becomes MIR's
abstract `Ptr`. Calls and comparisons then need no handle-specific MIR
instruction, and no pointer width or ABI fact has entered the pipeline.

A nullable pointer handle remains the ordinary tagged optional everywhere in
Luce. Only a C import or export boundary adapts it to one raw `Ptr`: zero
decodes to `none`, and `none` encodes to zero. A bare pointer-handle slot emits
the canonical `Trap("null_foreign")` guard in either direction. An exported C
function is therefore two MIR functions: a private Luce-convention body used
by source calls and a public C-convention wrapper owning those adapters. Wasm,
QBE, and the MIR interpreter consume that same wrapper; only the artifact
backend decides the pointer width and C ABI placement.

An extern `out` declaration is retained in HIR as an ordered, target-neutral
C slot contract beside the ordinary source callable signature. Inputs refer
to source parameter indices; outputs name a source type but are not callable
parameters. The lowerer allocates one call-owned raw slot per output, passes
its abstract pointer in declaration order, then loads and applies the same C
value decoder used for declared results. The declared non-void result comes
first, followed by outputs; zero components produce `unit`, one is returned
directly, and multiple components use the ordinary aggregate-result protocol.
The HIR host returns these raw output values explicitly. The MIR host instead
writes through a narrow `MirExternMemory` view, which tests the actual pointer
contract without exposing the interpreter's storage or a target layout.

An `extern var` is not a compiler-owned `MirGlobal`: it names mutable storage
owned by C or the embedding host. HIR uses explicit load and store nodes, and
canonical MIR retains a `MirExternalGlobal` identity plus an explicit
instruction for every access, so reads are observable and optimization can
never mistake the object for constant local data. The source type is checked
before nominal handles erase to scalar MIR types. Equal declarations share
one linker identity; conflicting types and function/object symbol collisions
fail in the lowerer. The HIR and MIR interpreters bind separate variable-host
interfaces, QBE emits direct object loads/stores, and Wasm imports a mutable
global from `env`. No namespace, address, pointer width, layout, or ABI fact
enters HIR or MIR. Unlike a pointer handle crossing a C function boundary, a
bare zero handle stored in an external object is ordinary state and does not
trap or acquire optional semantics.

### Instructions

Every instruction carries a `SourceSpan`. `r` is a register operand; `->
rN: T` defines a register. Depth `d` counts enclosing regions outward from
the innermost.

**Constants and copies**

```
Const(value, type)             -> r
Copy(r)                        -> r      makes a value copy explicit (§6)
```

**Arithmetic and comparison** — operands share one type; results are that
type, or `Bool` for comparisons. Integer operations are checked (§7).

```
Add Sub Mul                    ints, floats
Div                            floats (`/`)
FloorDiv Rem                   ints (`//`, `%`); trap on zero and on minimum // -1
Neg                            signed ints, floats
And Or Xor Not                 ints
ShiftLeft ShiftRight           ints; trap on out-of-range count; signed right shift is arithmetic
Eq Ne                          ints, floats, Bool, Ptr
Lt Le Gt Ge                    ints, floats
BoolNot                        Bool
Extend(r, to)  Wrap(r, to)     integer width changes; Wrap is emitted only where the language allows truncation
IntToFloat  FloatToInt         explicit; FloatToInt traps out of range
```

Short-circuit `and`/`or` are control flow (`If`), not instructions.

**Memory**

```
Alloca(slot)                              -> r: Ptr
Load(type, address)                       -> r: type
Store(type, address, value)
FieldAddress(struct_type, base, index)    -> r: Ptr
EnumPayloadAddress(enum_type, base)       -> r: Ptr
ElementAddress(element_type, base, index) -> r: Ptr     scaled by element size
Memcpy(destination, source, type)                       one value of `type`
MoveElements(destination, source, element_type, count)  overlap-safe typed range move
AllocateStorage(element_type, count: u64) -> r: Ptr     typed runtime storage (§12)
ListCreate()                            -> r: List(T)    T is the result-register type
ListCopy(value: List(T))                -> r: List(T)    shallow, independent storage
ListLength(value: List(T))              -> r: u64
ListAppendSlot(value: List(T))          -> r: Ptr       uninitialized typed slot
ListInsertSlot(value: List(T), index: u64) -> r: Ptr    checked uninitialized slot
ListRemoveAt(value: List(T), index: u64)                 checked shape mutation
ListClear(value: List(T))
ListReserve(value: List(T), minimum_capacity: u64)
ListElementAddress(value: List(T), index: u64) -> r: Ptr checked element address
ListMutableElementAddress(value: List(T), index: u64) -> r: Ptr checked write barrier
ListSlice(value: List(T), start: u64, end: u64) -> r: Slice(T) checked O(1) snapshot
SliceLength(value: Slice(T))             -> r: u64
SliceElementAddress(value: Slice(T), index: u64) -> r: Ptr checked read-only address
DataAddress(DataId)                       -> r: Ptr
GlobalAddress(GlobalId)                   -> r: Ptr
LoadExternalGlobal(ExternalGlobalId)      -> r: type
StoreExternalGlobal(ExternalGlobalId, value)
FunctionAddress(FunctionId)               -> r: Ptr     opaque exact-function call token
ExternAddress(ExternId)                   -> r: Ptr     opaque C-symbol call token
```

**Calls** — a fallible target takes the caller's error-slot pointer as its
first argument. Its last result is null on success or that same pointer on
failure. A scalar success result precedes it; aggregate success data uses the
separate hidden result-slot argument described above.

```
Call(FunctionId, args)                       -> results
CallExtern(ExternId, args)                   -> results
CallIndirect(signature, convention, target, args) -> results
```

An exact source `func(P...) -> R` is an opaque pointer-shaped value in
canonical MIR; its type is carried by the `CallIndirect` operation, not
recovered from its representation. `FunctionAddress` creates the token for a
defined Luce function. QBE currently represents it as a code address, while
Wasm represents it as a slot in an on-demand funcref table. A source `cfunc`
uses the same opaque token and indirect operation, but the operation retains
the C convention; `ExternAddress` names an exact imported C symbol, while a
converted Luce definition's `FunctionAddress` names its generated C adapter.
Table indices, code addresses and ABI placement are not HIR/MIR facts. A later
closure slice may make an ordinary-function backend token refer to a
managed code-and-environment descriptor without changing source type checking
or introducing target layout before the backend boundary.

**Control flow** — a body is one flat instruction list; these open,
separate, and close regions in that list:

```
Block(results)  ... End           Br to it exits it; `results` are the registers it defines
Loop  ... End                     Br to it restarts it; a Loop has no results; falling off its End leaves it
If(condition, results)  ... Else  ... End     Else may be absent when there are no results
Switch(tag)  Case(v) ...  Case(v) ...  Default ...  End     falling off an arm leaves the Switch; Default is required
Br(depth, values)                 leave region `depth`, supplying its results
BrIf(condition, depth, values)
Yield(values)                     leave the innermost region normally, supplying its results (a Br 0 that reads as an exit)
Return(values)
Raise(failure)                    Return absent value(s) and r0, the filled caller-owned Error slot
Trap(reason)                      unconditional; runs no deferred code
Unreachable                       after a diverging call; verifier-only
```

The flat encoding is a shape decision, not a convenience: every consumer —
verifier, interpreter, each backend — walks a function as one linear pass
with a small region stack, and a `MirInstruction` is a plain value stored
inline in the body's list, so a body is one contiguous allocation rather than
a tree of heap objects. The `End` of an `If` with results is where those
registers become defined; a `Yield` or `Br` into a region is the only way to
supply them, and the verifier rejects an arm that falls off without doing so.
Operand lists (`results`, `arguments`, `values`) are `RegisterRun`s — a start
and count into the function's `operands` array — so an instruction is a
fixed-size value and a body is two contiguous arrays: instructions and
operands.

### Runtime services

Emitted by the lowerer or runtime composer, never by user code; the verifier
knows their signatures and bindings.

```
AllocateStorage(TypeId, u64 count) -> Ptr     canonical typed request
  bound private function: (u64 byte_count, u64 byte_align) -> Ptr
ListCreate() -> List(T)                      typed semantic handle
ListCopy(List(T)) -> List(T)                 backend supplies size/alignment
ListLength(List(T)) -> u64
ListAppendSlot(List(T)) -> Ptr               backend supplies size/alignment
ListInsertSlot(List(T), u64) -> Ptr           backend checks index <= length
ListRemoveAt(List(T), u64)                    backend checks index < length
ListClear(List(T))
ListReserve(List(T), u64)                     backend supplies size/alignment
ListElementAddress(List(T), u64) -> Ptr       backend checks bounds, supplies size
ListMutableElementAddress(List(T), u64) -> Ptr backend checks bounds, supplies size/alignment; runtime detaches a captured buffer
ListSlice(List(T), u64, u64) -> Slice(T)      backend checks start <= end <= length and supplies size
SliceLength(Slice(T)) -> u64
SliceElementAddress(Slice(T), u64) -> Ptr     backend checks bounds and supplies size
luce_rt_retain(Ptr)                         luce_rt_release(Ptr)
luce_rt_weak_make(Ptr) -> Ptr            luce_rt_weak_get(Ptr) -> Ptr
luce_rt_trap(message, u64 length)        luce_rt_write(bytes, u64 length)
luce_rt_str_*  luce_rt_list_*  luce_rt_map_*  luce_rt_set_*         dynamic storage (§12)
luce_rt_spawn(function, input) -> Ptr    luce_rt_wait(Ptr) -> Ptr    luce_rt_cancel(Ptr)
luce_rt_transfer(value, type_info) -> Ptr                             value-graph copy (§19.2)
```

### What the verifier proves

- every register is defined once, before use, with its declared type;
- every operand type matches the instruction;
- `Br`/`BrIf` depths are in range, and `Block`/`If` result registers are
  defined on every path to the join;
- every type identity exists and the layout-dependency graph has no by-value
  cycle; forward references through pointer-shaped handles are valid;
- a fallible signature takes a `Ptr` as parameter 0 and returns a `Ptr` last;
  fallible calls pass the caller-owned error slot and define the reported
  error pointer; a fallible `Return` reports null and `Raise` returns r0;
  every fallible path ends in one of those terminators;
- `c`-convention signatures contain only C-representable types;
- runtime symbols are called with their known signatures;
- runtime bindings are unique private Luce functions with the service's exact
  signature, and every `AllocateStorage` has a storage-allocator binding;
- globals and data items name existing initializers and valid minimum alignments.

### Open questions

- **Optionals of future managed class references** — null-pointer niche or a
  uniform two-case enum? This does not include pointer-shaped foreign handles:
  those are uniformly tagged in MIR and adapted to raw null only at an
  explicit `c`-convention boundary.

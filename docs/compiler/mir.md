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
`ListCopy`, `ListConcat`, `ListLength`, slot insertion/removal, reservation,
clearing, iteration begin/end, and `ListElementAddress` derive `T` from that register. Operations
that move or address elements ask the backend to pass its computed
size/alignment to the exact composed runtime service. Bounds checking is part
of canonical list indexing, insertion, and removal; private runtime functions
perform only the unchecked storage operation after the backend guard.
Capacity, header layout, concatenation allocation/copy policy, and geometric
growth remain ordinary freestanding Luce runtime policy.

Maps and sets preserve the same boundary with distinct `Map(K,V)` and
`Set(T)` handles and one `Hash*` instruction family. Candidate discovery uses
compiler-produced `u64` hashes, but generated MIR performs every key equality
and typed retain/release callback. The sealed runtime owns dense
insertion-order entries, private seeded buckets, collision chains, growth,
iteration depth, and the mutation guard itself. QBE and Wasm contribute only
layout numbers, callback descriptors, and the ordinary call encoding.

Structural list equality is expanded by the shared lowerer, not delegated to
a backend. Finite list element shapes use one ordinary canonical loop and
allocate no comparison state. A type graph recursive through a list reserves
one private generated equality function per concrete recursive HIR type before
emitting any body, so `Node -> list[Node] -> Node` closes with a call instead
of recursively expanding the compiler stack. The root operation creates one
opaque equality context; `EqualityContextVisit` records an ordered pair of
list handles and reports whether that pair was already visited. Generated MIR
still performs identity, length, tag, field, and element comparisons. The
sealed runtime owns only the pair-set storage policy, and each backend only
passes its concrete list handles to the exact bound service. No target layout,
callback representation, or backend comparison rule enters canonical MIR.

Existential storage follows the same boundary. `InterfaceCreate` names one
canonical conformance and the address of its concrete source storage. The
conformance supplies the concrete type; backend legalization supplies that
type's size/alignment and its generated structural retain/release helpers to
the sealed runtime. The private header retains the
conformance/witness identity and enough policy to detach a shared value before
mutation. `InterfaceDetach` consumes the caller's one reference and returns
either the same unique handle or a retained copy. `InterfacePayload` exposes
only an opaque address to a normalized witness thunk. A class payload remains
the same shared class identity after wrapper detachment, while a value payload
is independently mutated. Header fields, inline capacity, box placement, and
witness-table encoding never enter canonical MIR.

`ListIterationBegin` registers one active traversal on the semantic list
identity and returns the element count captured at entry. The lowerer emits a
matching `ListIterationEnd` through its lexical cleanup stack on return/error
transfer, while exhaustion and `break` converge on one common end; `continue`
does not end traversal. Append, insert, removal, and clear consult the exact
`list_iteration_active` runtime service at each backend boundary and trap
before calling the unchecked shape mutator. Element replacement and reserve
remain valid, so the loop requests the current element address on every pass
instead of retaining a relocated storage pointer. The active depth is
semantic shared-identity state; its concrete header field is runtime-private.

`ListMutableSliceBegin` first detaches every pre-existing immutable snapshot,
then produces one `MutableSlice(T)` register and enters that same identity-wide
shape barrier. `MutableSliceLength` and `MutableSliceElementAddress` always
revisit the owner identity, so backend/runtime relocation is not retained as
a canonical address. A write may detach again when the callback itself created
an immutable snapshot. `MutableSliceEnd` closes the barrier after the one
synchronous closure call. The verifier admits the type only as a direct
function parameter or a result of `ListMutableSliceBegin`; it rejects storage,
function results, forged origins, use after end, closing a borrowed parameter,
and every normal path that bypasses the matching end. Trapping paths need no
cleanup because a trap terminates the program. No pointer width, list header,
element offset, or ABI fact enters this transaction.

`Task(T)` is a locally storable, non-owning handle into the current invocation's
structured task group. `TaskGroup` is compiler-internal and cannot appear in a
source signature or value. A function that contains a spawn begins one group;
`TaskSpawn` records the exact concrete `FunctionId` and a `TransferRun` into the
function-local typed transfer arena. Each transfer retains both its evaluated
register and its source `TypeId`; aggregate call arguments are represented by
`Ptr`, so the structural type is indispensable for proving and performing an
isolated copy. `Task(T, Error)` likewise retains the structural failure type:
the ordinary error result is a raw caller-owned pointer only at the call ABI,
not at the task boundary. `TaskWait` returns a copied successful value plus the
ordinary failure channel, and `TaskCancel` requests cancellation. `TaskWaitAll`
is the typed bulk form over `List(Task(T))`; its ordering and first-failure
rules are fixed by §19 rather than a backend runtime API. Its successful empty
`List(Never)` uses canonical `Uninhabited`, a zero-size element marker distinct
from the empty struct used for `unit`; it can never occupy a register.

The lowerer emits `TaskGroupFinish` on every ordinary return and propagated
error before it runs the function-scope cleanup suffix. It cancels and joins
only children that the current invocation spawned; task parameters remain
owned by their caller's group. Traps and forced termination do not execute the
finish operation, matching the language's no-cleanup trap rule. The verifier
proves one group origin, exact spawn signature/result agreement, sendable
transfer types, task-handle provenance, and a finish on every ordinary exit.
Task handles require no independent retain/release: the group keeps each child
record alive through the invocation, while local aliases and collections carry
the same opaque identity.

HIR and MIR define transfer as a recursive value-graph copy and cache a
completed outcome for repeated waits. Neither representation contains a
thread, process, pipe, signal, scheduler, serializer format, pointer width, or
host cancellation primitive. The semantic interpreters may schedule workers
deterministically while preserving isolation and observable task behavior.
The MIR oracle serializes verified sendable values into a pointer-free semantic
tree, executes the exact worker in a fresh interpreter domain, then decodes its
cached result or Error into caller-owned storage. Parent memory addresses,
collection identities, buffer owners, globals, and managed handle tables can
therefore never cross the oracle boundary accidentally. Scalars, structs,
arrays, enums, optionals, buffers, immutable slices, and frozen collections all
use this one type-directed copy rather than feature-specific task paths.
QBE chooses its native worker domain and transfer encoding behind the backend
boundary; a backend without an isolated-worker facility reports the feature as
unsupported without changing canonical MIR.

User-defined iteration does not add a second MIR protocol. HIR has already
selected the exact compiler-known interface application and resolved
`iterator()`/`next()` as static, constrained, or dynamic interface calls. The
function lowerer evaluates `iterator()` once into one private owned slot, then
expresses repeated `next()` using the existing call, optional-tag/payload,
`Block`, `Loop`, and branch operations. Fallible iteration is the same shape
with the existing HIR `Try` around each fallible `next()`, so ordinary MIR
failure transfer runs the active cleanup suffix. The private slot uses the
same generated ownership helper as any lexical interface local and is released
on exhaustion, `break`, return, or propagation. No iterator layout, ABI, or
target choice enters canonical MIR.

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

`native.deallocate(pointer, count)` is its structural inverse:
`DeallocateStorage(pointer, T, count)`. The verifier requires the exact private
deallocator binding, the MIR oracle reuses blocks under its explicit test
layout, and each artifact backend derives the same physical byte count and a
pointer-safe recycling alignment it used for allocation. Count zero performs
no call. The runtime therefore owns size classes and free lists without a
source `sizeof`, while canonical MIR retains no byte count, pointer width, or
target alignment.

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

- **Generics** are monomorphized (§15): each free-function or nominal-method
  use with concrete types becomes its own plain function.
- **Closure syntax and capture resolution** are gone, but their semantic
  contract remains explicit. `MirClosure` names a hidden body, source-visible
  signature, typed capture schema, and destroyer. A captured `var` is a typed
  ARC-managed `Cell(T)` shared by the enclosing scope and every closure
  (§14.1). Backends alone choose descriptor and environment layout.
- **Interface syntax and source conformance lookup** are gone, but the
  existential contract is not flattened prematurely. `Interface(id)` is an
  opaque managed handle; `MirInterface` fixes normalized requirement
  signatures and `MirConformance` fixes witness functions in declaration
  order. Create/payload/detach/retain/release and `CallInterface` remain
  semantic MIR operations. A backend may represent the handle as data plus a
  witness-table pointer, inline a small value, or box it; HIR/MIR never choose
  pointer count, inline capacity, offsets, or table layout (§16.3).
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
| `TaskSpawn` / `TaskWait` / `TaskWaitAll` | supervised POSIX worker plus generated typed codec | process and transport policy exists only in the native backend |
| fallible `(value, error pointer)` plus caller-owned error parameter | error pointer return plus a private scalar-result out pointer | backend-local ABI |
| narrow integer types | `w` temporaries plus explicit extension, guards, and sub-word memory operations | direct legalization |

The QBE backend owns target layout, lowers
structured control flow to QBE's graph, and relies on QBE for ABI lowering,
instruction selection, and register allocation. The first implementation
uses the real QBE toolchain as both oracle and product native path. IL,
assembly, diagnostics, and the linked candidate live in an atomically owned
directory beside the requested output. Regular files connect the host tools:
fully feeding one pipe before draining the other can deadlock once both fill.
Only the linked candidate leaves scratch, replacing the requested output by an
atomic same-filesystem rename. A later Luce-native backend can be
differential-tested against this baseline. Both paths consume the same
canonical MIR; neither adds target-specific lowering before the backend
boundary.

For a task-bearing product, the QBE toolchain links one small POSIX companion
beside the generated assembly. A spawn forks immediately after the backend has
captured the worker's QBE call values, so copy-on-write supplies a snapshot of
the complete source runtime domain without teaching HIR or MIR about a host
process. Only a framed outcome returns through the pipe. Compiler-generated,
type-directed codecs rebuild scalars, aggregates, buffers, slices, and frozen
collections into new parent-owned storage; mutable identities and raw pointers
are excluded earlier by sendability. The companion owns `fork`, `pipe`,
`waitpid`, signals, cached bytes, and process records, but knows nothing about
MIR layout or the sealed collection runtime. The ordinary emitter and worker
codecs share one QBE representation module, including exact narrow loads,
stores, alignment, symbols, and binary16 memory encoding.

Repeated waits decode fresh values from the cached frame. `wait_all` joins
every distinct process, then decodes in input order or reports the first input
failure after all joins. Function-scope group finish cancels and reaps every
unobserved child before source cleanup; nested workers form independent groups
inside their own copied domains. Source traps publish their message as
`task.trapped`, explicit cancellation becomes `task.cancelled`, and host
allocation/transport exhaustion becomes `task.resource_exhausted`.

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
  runtime with no bespoke host. Frozen snapshots remain ordinary canonical
  handles and encode normally. Isolated tasks are rejected explicitly at this
  backend boundary because WASI preview 1 provides no worker-domain primitive;
  MIR is not weakened or specialized to accommodate that target.
- **QBE native** links C externs and the current compiled `libluce_rt` through the host
  toolchain. Luce-native backends begin only after the language and runtime
  baseline is complete, and must prove the same canonical MIR against QBE.
- The order of work: new `mir/canonical.luc` and verifier → MIR interpreter
  and the three-way harness (both done: `tests/compiler/differential_test.luc`)
  → the lowerer in vertical slices (scalars and locals, control flow, calls and constants — done;
  enums and `match`, structs and classes/ARC, closures and interfaces, failure and
  `defer`, collections, the C boundary, workers) → wasm encoder tracking
  each slice → native backends from MIR once it stops moving.

---

## Part two: the reference

### The program

```
MirProgram
    types       list[MirType]       every target-neutral type used
    classes     list[MirClass]      nominal payload schemas and destroyers
    runtime_bindings list[MirRuntimeBinding] sealed service → function identities
    externs     list[MirExtern]     imported symbols: C functions and the runtime
    external_globals list[MirExternalGlobal] C-owned observable scalar state
    globals     list[MirGlobal]     module-level mutable state
    data        list[MirData]       address-free constant bytes, such as string payloads
    functions   list[MirFunction]
    process_entry MirProcessEntry?  language entry plus semantic ownership identities
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
| `BufferOwner` | opaque immutable string/byte storage owner; pointer-shaped only after backend legalization |
| `List(element)` | typed mutable reference collection handle |
| `Map(key, value)` | typed insertion-ordered mutable hash-map handle |
| `Set(element)` | typed insertion-ordered mutable hash-set handle |
| `Slice(element)` | typed immutable snapshot handle |
| `Class(identity)` | owning nominal identity handle; payload layout remains a backend fact |
| `WeakClass(identity)` | non-owning handle for the same nominal identity |
| `Struct(fields)` | fields in declaration order; byte placement is a backend fact |
| `Array(element, count)` | fixed arrays |
| `Enum(tag, cases)` | tag is an `Int`; each case is a `Struct` payload |
| `Func(signature)` | what a function pointer points at |

How language types map onto them: `bool` → `Bool`; `char` → `Int(32,
unsigned)`; both `str` and `bytes` → an owning
`{BufferOwner, Ptr, u64 byte_length}` `Struct`. A literal's payload is a data
item with an inert null owner, while a dynamic value names sealed-runtime
storage. HIR retains the language distinction; semantic string and byte MIR
operations do not reinterpret one as the other.
`list[T]` → `List(T)`, `map[K, V]` → `Map(K, V)`, `set[T]` → `Set(T)`,
`slice[T]` → `Slice(T)`, and callback-scoped `mutable_slice[T]` →
`MutableSlice(T)`, all opaque reference-sized handles whose concrete
headers are runtime/backend facts; `T?` → a two-case `Enum` with a `u8` tag, including
class optionals (foreign handles also stay tagged internally); a scalar `T!`
result → a scalar and error pointer, never a
type;
tuples → anonymous `Struct`; `array[T, N]` → `Array(T, N)` with `N` retained
as a target-neutral type fact and element placement deferred to the backend;
class references → `Class(id)` and both weak field storage and source
`Weak[T]` values → `WeakClass(id)`, with their field schema and generated
`(class, initialized)` destroyer in
`MirProgram.classes`; interface values → `Interface(id)`, an opaque typed
managed handle whose requirement and conformance tables are program metadata.

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
`MirProgram.process_entry` root. It retains the unchanged fallible
`(slice[str]) -> i32!` function, argument/failure types, and exact ownership
helpers; argc/argv, WASI memory, pointer widths, and host calling conventions
begin only in a backend adapter. Reachability keeps all three root families separate.
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
Extend(r, to)  Wrap(r, to)     integer width changes; checked construction guards before Wrap
IntReinterpret(r, to)          equal-width signedness change after representability guards
IntToFloat  FloatToInt         explicit; FloatToInt traps out of range
FloatBits(r) -> u64            exact IEEE encoding; binary32 occupies low 32 bits
```

Short-circuit `and`/`or` are control flow (`If`), not instructions.
Source `hash(value)` is otherwise fully expanded once by the shared lowerer:
ordinary integer, control, field, element, and memory instructions traverse
the resolved structural value. `FloatBits` is the sole primitive because exact
IEEE encodings are also required by the sealed runtime's shortest-decimal
conversion. Lowering normalizes equal signed zeros before hashing. Backends
only select their native bit reinterpretation; they never choose aggregate
hashing semantics, decimal presentation, or re-walk HIR types.

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
EqualityContextCreate() -> r: Ptr                        one recursive comparison transaction
EqualityContextRelease(Ptr)
EqualityContextVisit(Ptr, Collection(T), Collection(T)) -> r: bool
                                            true when the ordered identity pair was visited
HashCreate()                             -> r: Map(K,V) or Set(T)
HashCopy(value, key_retain, value_retain) -> r: same type
HashLength(value)                        -> r: u64
HashIterationBegin(value)                -> r: u64       enter traversal and capture length
HashIterationEnd(value)                                  leave one traversal depth
HashFindFirst(value, hash: u64)          -> r: u64       candidate index + 1, or zero
HashFindNext(value, current: u64)        -> r: u64       next candidate index + 1, or zero
HashKeyAddress(value, index: u64)        -> r: Ptr
HashValueAddress(Map(K,V), index: u64)   -> r: Ptr
HashInsertEntry(value, hash: u64)        -> r: u64       uninitialized entry index
HashRemoveEntry(value, index: u64)                       raw removal after typed cleanup
HashClear(value, key_release, value_release)
HashReserve(value, minimum_capacity: u64)
ListCreate()                            -> r: List(T)    T is the result-register type
ListCopy(value: List(T))                -> r: List(T)    shallow, independent storage
ListConcat(left: List(T), right: List(T)) -> r: List(T)  fresh shallow ordered result
ListLength(value: List(T))              -> r: u64
ListIterationBegin(value: List(T))      -> r: u64       enter traversal and capture length
ListIterationEnd(value: List(T))                       leave one traversal depth
ListMutableSliceBegin(value: List(T)) -> r: MutableSlice(T) enter scoped access
MutableSliceLength(value: MutableSlice(T)) -> r: u64
MutableSliceElementAddress(value: MutableSlice(T), index: u64) -> r: Ptr
MutableSliceEnd(value: MutableSlice(T))                 leave scoped access
ListAppendSlot(value: List(T))          -> r: Ptr       uninitialized typed slot
ListInsertSlot(value: List(T), index: u64) -> r: Ptr    checked uninitialized slot
ListRemoveAt(value: List(T), index: u64)                 checked shape mutation
ListClear(value: List(T))
ListReserve(value: List(T), minimum_capacity: u64)
ListElementAddress(value: List(T), index: u64) -> r: Ptr checked element address
ListMutableElementAddress(value: List(T), index: u64) -> r: Ptr checked write barrier
ListSlice(value: List(T), start: u64, end: u64) -> r: Slice(T) checked O(1) snapshot
BufferRetain(value: BufferOwner)
BufferRelease(value: BufferOwner)
BufferConcat(left_data: Ptr, left_length: u64, right_data: Ptr, right_length: u64) -> r: BufferOwner
BufferData(owner: BufferOwner)                 -> r: Ptr
StringScalarCount(data: Ptr, byte_length: u64) -> r: u64
StringDecode(data: Ptr, byte_length: u64, offset: u64) -> character: u32, width: u64
BytesSlice(owner: BufferOwner, data: Ptr, length: u64, start: u64, end: u64) -> r: Slice(u8)
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
CallClosure(signature, descriptor, args)          -> results
CallInterface(InterfaceId, requirement, handle, args) -> results
```

An exact source `func(P...) -> R` is a canonical aggregate descriptor with a
code identity and nullable managed environment. `FunctionNull`,
`FunctionValue`, and `ClosureCreate` initialize caller-owned descriptor
storage; all carry or reference the exact source-visible signature so the
verifier can reject mismatched code before a backend. Capture-free values use
a null environment and allocate nothing. `CallClosure` invokes the descriptor;
the hidden environment parameter is inserted immediately after a fallible
error slot, or first for an infallible call. Function retain/release operations
own only the environment.

A source `cfunc` remains an opaque raw callable token used by
convention-bearing `CallIndirect`. `FunctionAddress` names a generated C
adapter and `ExternAddress` names an imported C symbol. QBE chooses native
addresses and two-word ordinary descriptors; Wasm chooses table indices and
linear-memory descriptors. Those representations, table placement, code
addresses, and ABI details never enter HIR or MIR.

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
DeallocateStorage(Ptr, TypeId, u64 count)      canonical typed release
  bound private function: (Ptr, u64 byte_count, u64 byte_align) -> unit
EqualityContextCreate() -> Ptr
  bound private function: () -> Ptr
EqualityContextRelease(Ptr)
  bound private function: (Ptr) -> unit
EqualityContextVisit(Ptr, List(T), List(T)) -> bool
  bound private function: (Ptr, Ptr, Ptr) -> bool; backends pass list handles
ListCreate() -> List(T)                      typed semantic handle
ListCopy(List(T)) -> List(T)                 backend supplies size/alignment
ListConcat(List(T), List(T)) -> List(T)       backend supplies size/alignment
ListLength(List(T)) -> u64
ListIterationBegin(List(T)) -> u64             enter and capture length
ListIterationEnd(List(T))                    leave one traversal depth
ListAppendSlot(List(T)) -> Ptr               backend supplies size/alignment
ListInsertSlot(List(T), u64) -> Ptr           backend checks index <= length
ListRemoveAt(List(T), u64)                    backend checks index < length
ListClear(List(T))
ListReserve(List(T), u64)                     backend supplies size/alignment
ListElementAddress(List(T), u64) -> Ptr       backend checks bounds, supplies size
ListMutableElementAddress(List(T), u64) -> Ptr backend checks bounds, supplies size/alignment; runtime detaches a captured buffer
ListSlice(List(T), u64, u64) -> Slice(T)      backend checks start <= end <= length and supplies size
BufferRetain(BufferOwner) / BufferRelease(BufferOwner)
BufferConcat(Ptr, u64, Ptr, u64) -> BufferOwner
BufferData(BufferOwner) -> Ptr
StringScalarCount(Ptr, u64) -> u64
StringDecode(Ptr, u64, u64) -> (u32 scalar, u64 byte_width)
BytesSlice(BufferOwner, Ptr, u64, u64, u64) -> Slice(u8)  backend checks start <= end <= length
SliceLength(Slice(T)) -> u64
SliceElementAddress(Slice(T), u64) -> Ptr     backend checks bounds and supplies size
ClassCreate(ClassId) -> Class(T)              backend supplies payload size/alignment
ClassMarkInitialized(Class(T))
ClassRetain(Class(T)) / ClassRelease(Class(T))
ClassFieldAddress(Class(T), field) -> Ptr     backend supplies payload offset
WeakClassCreate(Class(T)) -> WeakClass(T)
WeakClassRetain(WeakClass(T)) / WeakClassRelease(WeakClass(T))
WeakClassPromote(WeakClass(T), Class(T)?)     atomic owned optional result
CellCreate(T, destroyer) -> Cell(T)           shared mutable capture storage
CellMarkInitialized(Cell(T))
CellRetain(Cell(T)) / CellRelease(Cell(T))
CellValueAddress(Cell(T), T) -> Ptr
FunctionNull(Ptr destination, Func(T))
FunctionValue(Ptr destination, Func(T), FunctionId)
ClosureCreate(Ptr destination, Func(T), ClosureId) -> Ptr environment
ClosureMarkInitialized(Ptr environment)
ClosureCaptureAddress(Ptr environment, ClosureId, capture) -> Ptr
FunctionRetain(Ptr descriptor) / FunctionRelease(Ptr descriptor)
InterfaceCreate(ConformanceId, Ptr source storage) -> Interface(I)
InterfaceRetain(Interface(I)) / InterfaceRelease(Interface(I))
InterfaceDetach(Interface(I)) -> Interface(I)   consumes one reference; COW before mutation
InterfacePayload(Interface(I)) -> Ptr           erased receiver storage
CallInterface(InterfaceId, requirement, Interface(I), args) -> results
list_iteration_active(List(T)) -> bool        backend guards every shape mutation
luce_rt_trap(message, u64 length)        luce_rt_write(bytes, u64 length)
luce_rt_str_*  private list/hash runtime services                    dynamic storage (§12)
luce_rt_spawn(function, input) -> Ptr    luce_rt_wait(Ptr) -> Ptr    luce_rt_cancel(Ptr)
luce_rt_transfer(value, type_info) -> Ptr                             value-graph copy (§19.2)
```

A source trap calls the target-neutral `luce_rt_trap` contract and then ends
its canonical region with `Unreachable`. Only the backend chooses the
diagnostic channel and concrete terminating instruction.

A source assertion evaluates its Boolean and ordinary string message before
opening a structured `If` for the failed path. That path uses the same trap
contract and `Unreachable`; success reaches `End` and continues with `unit`.
There is no assertion MIR form because its complete semantics are already
expressed by canonical control flow and the trap contract.

### What the verifier proves

- every register is defined once, before use, with its declared type;
- every operand type matches the instruction;
- `Br`/`BrIf` depths are in range, and `Block`/`If` result registers are
  defined on every path to the join;
- every type identity exists and the layout-dependency graph has no by-value
  cycle; forward references through pointer-shaped handles are valid;
- every closure body is private Luce code with exactly one hidden environment
  parameter in the canonical position; every closure/cell destroyer has its
  exact private lifecycle signature; descriptor initializers match their
  canonical `Func` signature and capture accesses stay within their schema;
- a fallible signature takes a `Ptr` as parameter 0 and returns a `Ptr` last;
  fallible calls pass the caller-owned error slot and define the reported
  error pointer; a fallible `Return` reports null and `Raise` returns r0;
  every fallible path ends in one of those terminators;
- `c`-convention signatures contain only C-representable types;
- runtime symbols are called with their known signatures;
- runtime bindings are unique private Luce functions with the service's exact
  signature, and every `AllocateStorage` has a storage-allocator binding;
- every nominal class has exactly one strong and one weak canonical type, a
  valid private `(Class, bool) -> unit` destroyer, type-correct fields, and
  exact class identities on create/field/weak/promotion instructions;
- globals and data items name existing initializers and valid minimum alignments.

### Settled optional representation

Class optionals use the same uniform two-case `u8`-tagged enum as every other
`T?`. A null `Class` or `WeakClass` handle is permitted only as an internal
sentinel for partially initialized storage and absent weak slots; it is never
a source value. Pointer-shaped foreign handles are also tagged in MIR and are
adapted to raw null only at an explicit `c`-convention boundary.

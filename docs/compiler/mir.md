# Canonical MIR — a guided tour

This document explains the compiler's *machine intermediate representation*:
the form a Luce program takes after the front end has understood it and
before a backend turns it into machine code.

If you have read the top-level README you know the pipeline:

```
source → tokens → syntax tree → typed HIR → canonical MIR → wasm / arm64 / x86-64
                                    │
                                    └→ the reference interpreter
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
Control flow in MIR is **structured**. `Block` and `Loop` are nested
regions; `Br 0` means "branch to the innermost enclosing region" and
`BrIf r7, 1` means "if `r7`, branch to the one outside that". Branching to
a `Loop` restarts it; branching to a `Block` leaves it. `If` and `Switch`
(for `match`) nest the same way. That is the whole control-flow vocabulary.

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

### Failing: errors are just values

On to `checked_sum`, which can fail. In Luce a function returning `T!`
returns either a `T` or an `Error` (§13.2). Many compilers implement that
with exceptions, unwinding, and landing pads. MIR does something plainer:

```
func checked_sum(r0: i64) -> (i64, Ptr)        ; second result: the error slot
    r1: Bool = Lt r0, 0
    If r1
      r2: Ptr = DataAddress data0              ; "limit must not be negative"
      r3: Ptr = CallExtern luce_rt_error_make, <math.negative>, r2, 27
      Raise r3
    End
    r4: i64 = Call sum_to, r0                  ; sum_to cannot fail: one result
    Return r4, null                            ; value present, error absent
```

A fallible function has **two results**: the value and an *error slot*, a
pointer that is null when nothing went wrong. `Raise` is `Return` with an
absent value and a present error. Now look at how a *caller* would use it:

```
r6: i64, r7: Ptr = Call checked_sum, r0
r8: Bool = Ne r7, null
BrIf r8, 2                                     ; `try`: propagate to the function's raise path
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

### Memory: structs, enums, and why MIR knows the target

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

`FieldAddress` needs to know that field 1 sits at offset 8. Who decides
that? Not the backend — **MIR does, and stores the answer**. Every `Struct`
and `Enum` type in a MIR program carries its field offsets, size, and
alignment, computed by the lowerer from a `TargetLayout` (pointer width,
alignment rules, the platform's C ABI conventions).

This is the one place MIR is *not* target-independent, and it is deliberate.
Luce talks to C (§21). An `extern struct` must have exactly the layout the C
compiler gave it *on that platform*, and the only way every backend agrees
is for MIR to say the offsets out loud and for the verifier to check them
against the layout. So a wasm32 build and an arm64 build of the same source
produce two different MIR programs — the same instructions, different
offsets — and that is correct. It is also why `build` takes a target
*before* lowering.

Pointers themselves are untyped: `Ptr` is just an address. The type travels
on the `Load`, `Store`, or `FieldAddress` that uses it, which is what a
backend actually needs, and typed pointers would only say it twice.

### The runtime: things MIR asks for by name

Where does memory for a `list` come from? Who counts references for a
class? Who prints? MIR does not have instructions for any of it. It has
**calls to a small, fixed set of runtime symbols**:

```
r1: Ptr = CallExtern luce_rt_alloc, 24, 8
CallExtern luce_rt_retain, r1
CallExtern luce_rt_write, r2, 13
```

The spec (§23.4) lists what the runtime provides — allocation, ARC,
weak references, dynamic strings and collections, traps, worker spawn and
join — and says it should be "small and explicit enough to replace per
host". Naming those services as symbols keeps MIR identical for every
target and gives each backend exactly one job for them: wasm imports the
symbols (or links a runtime compiled to wasm); native links `libluce_rt`.
The full symbol list is in the appendix.

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
   instructions above — no target, no runtime, runs on any machine;
3. the **compiled artifact**: a wasm module under `wasmtime`, or a native
   executable.

When all three agree, good. When one disagrees, the other two tell you which
stage is wrong. The MIR interpreter also doubles as the constant folder,
because §7 demands that folding use runtime semantics, and sharing the code
makes that true by construction.

Underneath the testing sits the **verifier**, which runs before and after
optimization and proves the structural rules: every register defined once
and before use, types match, branch depths in range, struct offsets agree
with the layout, fallible paths end in `Return` or `Raise`, C-convention
signatures carry only C-representable types. Backends assume all of it and
check nothing.

### Native backends, and QBE

The native plan does not assume LLVM. The likely path is [QBE](https://c9x.me/compile/)
— used as is, or rewritten in Luce — and canonical MIR was checked against
its intermediate language:

| Canonical MIR | QBE IL | Effort |
|---|---|---|
| write-once registers | temporaries; QBE builds SSA itself | trivial |
| `Alloca` / `Load` / `Store` slots | `alloc8` / `loadl` / `storel`; QBE promotes non-escaping slots | trivial — the promotion pass becomes QBE's |
| `Block` / `Loop` / `If` / `Br` | labels, `jmp`, `jnz` | a dozen lines |
| `Block` result registers | assign a temp on each path; QBE inserts the phi | trivial |
| `Struct` with stored offsets | `type :name = { … }` aggregates | direct |
| `convention = c` | QBE performs the SysV / Apple arm64 / RISC-V ABI lowering | direct |
| `CallExtern`, `FunctionAddress`, data relocations | `call $sym`, `$sym` as a value, `data $x = { l $f }` | direct |
| checked `Add`, trapping shifts, floor `//` | no overflow flags in QBE: compare sequences | the one place QBE costs more than hand-written native code |
| fallible `(value, error)` | one return value: an aggregate, or an out-pointer for the error | a per-backend ABI choice |
| narrow integer types | sub-word ops spelled out (`extsb`, `storeh`); widths only in signatures | see the open question below |

Nothing in the design fights QBE, and two of its decisions — stored layout
and backend-owned C ABI — are exactly what QBE expects. A QBE rewritten in
Luce would be the CFG-plus-SSA layer the *Control flow* section reserves for
native targets, built from canonical MIR and free to assume everything the
verifier proved. Either way native output goes through an assembler and
linker, which is why the plan below says "object file", not "executable".

Two consequences for the design record:

- The "two results" of a fallible function state MIR's *meaning*. Each
  backend picks the ABI: wasm multi-value, QBE an out-pointer or aggregate.
- The narrow-integer question tilts toward normalizing to `i32`/`i64` early,
  keeping exact widths only in `Struct` fields and `c` signatures — the form
  both wasm and QBE want. Still decided at the first lowerer slice.

### What comes next

- **wasm** maps one-to-one: regions to `block`/`loop`/`if`, registers to
  locals, externs to imports; it legalizes checked arithmetic. Its host
  contract is WASI preview 1 — `luce_rt_write` becomes `fd_write`, an
  entry gains `_start` and `proc_exit` — so a module runs under any wasm
  runtime with no bespoke host.
- **arm64 and x86-64** will emit an object file and call the system
  linker — the only way `extern` C functions and `libluce_rt` link. The
  current direct executable writers stay as a no-dependency path and are
  not extended.
- The order of work: new `canonical_ir.luc` and verifier → MIR interpreter
  and the three-way harness (both done: `tests/compiler/differential_test.luc`)
  → the lowerer in vertical slices (scalars and locals — done; control flow, calls,
  enums and `match`, structs and ARC, closures and interfaces, failure and
  `defer`, collections, the C boundary, workers) → wasm encoder tracking
  each slice → native backends from MIR once it stops moving.

---

## Part two: the reference

### The program

```
MirProgram
    layout      TargetLayout        pointer width, alignments, C ABI rules
    types       list[MirType]       every type used, with computed size/align
    externs     list[MirExtern]     imported symbols: C functions and the runtime
    globals     list[MirGlobal]     module-level mutable state
    data        list[MirData]       constant bytes: strings, witness tables, jump tables
    functions   list[MirFunction]
    entry       FunctionId?         process entry when the artifact is an executable
```

Identities are indices: `TypeId`, `FunctionId`, `ExternId`, `GlobalId`,
`DataId`. A call names a function *or* an extern; the artifact decides how
each is bound (wasm import versus linker symbol).

### Types

| MirType | Meaning |
|---|---|
| `Int(bits, signed)` | `i8`…`i64`, `u8`…`u64`; source widths are kept |
| `Float(bits)` | `f32`, `f64` |
| `Bool` | one byte, 0 or 1 |
| `Ptr` | pointer-width address, untyped |
| `Struct(fields, size, align)` | fields are `(type, offset)`; offsets follow `layout` |
| `Array(element, count)` | fixed arrays |
| `Enum(tag, cases, size, align)` | tag is an `Int`; each case is a `Struct` payload |
| `Func(signature)` | what a function pointer points at |

How language types map onto them: `bool` → `Bool`; `char` → `Int(32,
unsigned)`; `str`, `bytes`, `list`, `map`, `set` → `Ptr` to runtime storage;
`T?` → two-case `Enum`, or a null niche when `T` is a reference; a `T!`
result → two registers, never a type; tuples → anonymous `Struct`; class
references and `weak` → `Ptr` managed by the runtime; interface values → a
two-`Ptr` `Struct`.

### Functions, externs, globals, data

```
MirFunction
    name          `module.function`, or the export symbol
    convention    luce | c
    params        list[TypeId]
    results       list[TypeId]        0, 1, or 2 (value, error)
    fallible      bool                the last result is the error slot
    registers     list[TypeId]        every register, by index
    slots         list[(TypeId, align)]
    body          list[Instruction]   structured, see below
    is_public     bool
    span          SourceSpan

MirExtern     name, convention (c | runtime), params, results, fallible
MirGlobal     type, initial: DataId?, is_mutable
MirData       bytes, align, relocations: list[(offset, FunctionId | DataId | GlobalId)]
```

`convention = c` marks an export (§21.5) or a callback handed to C. Such a
signature may contain only C-representable types; the backend then applies
the target's C ABI. Relocations let constant data hold addresses (a witness
table, a string table) before final addresses exist.

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
ElementAddress(element_type, base, index) -> r: Ptr     scaled by element size
Memcpy(destination, source, type)                       one value of `type`
DataAddress(DataId)                       -> r: Ptr
GlobalAddress(GlobalId)                   -> r: Ptr
FunctionAddress(FunctionId)               -> r: Ptr     for closures, witness tables, C callbacks
```

**Calls** — a fallible target defines two registers; the second is the
error slot, null when absent.

```
Call(FunctionId, args)                       -> results
CallExtern(ExternId, args)                   -> results
CallIndirect(signature, target, args)        -> results
```

**Control flow**

```
Block(results, body)              Br to it exits it; `results` are the registers it defines
Loop(body)                        Br to it restarts it; a Loop has no results
If(condition, results, then, else)
Switch(tag, cases, default)       dense tags become a jump table
Br(depth, values)                 leave region `depth`, supplying its results
BrIf(condition, depth, values)
Yield(values)                     leave the innermost region normally, supplying its results
Return(values)
Raise(failure)                    Return with an absent value and a present error
Trap(reason)                      unconditional; runs no deferred code
Unreachable                       after a diverging call; verifier-only
```

### Runtime symbols

Emitted by the lowerer, never by user code; the verifier knows their
signatures.

```
luce_rt_alloc(size, align) -> Ptr        luce_rt_retain(Ptr)         luce_rt_release(Ptr)
luce_rt_weak_make(Ptr) -> Ptr            luce_rt_weak_get(Ptr) -> Ptr
luce_rt_trap(message, length)            luce_rt_write(bytes, length)
luce_rt_str_*  luce_rt_list_*  luce_rt_map_*  luce_rt_set_*         dynamic storage (§12)
luce_rt_error_make(code, message) -> Ptr luce_rt_error_code(Ptr) -> i64
luce_rt_spawn(function, input) -> Ptr    luce_rt_wait(Ptr) -> Ptr    luce_rt_cancel(Ptr)
luce_rt_transfer(value, type_info) -> Ptr                             value-graph copy (§19.2)
```

### What the verifier proves

- every register is defined once, before use, with its declared type;
- every operand type matches the instruction;
- `Br`/`BrIf` depths are in range, and `Block`/`If` result registers are
  defined on every path to the join;
- struct and enum offsets and sizes agree with `layout`;
- fallible calls define their error register; every path of a fallible
  function ends in `Return` or `Raise`;
- `c`-convention signatures contain only C-representable types;
- runtime symbols are called with their known signatures;
- relocations point at existing items.

### Open questions

- **Narrow integers** — kept as distinct MIR types (as written here) or
  normalized to `i32`/`i64` early with explicit `Extend`/`Wrap`, keeping
  exact widths only in `Struct` fields and `c` signatures? Both wasm and
  QBE want the second; the C boundary needs widths either way. Decided at
  the first lowerer slice.
- **Optionals of references** — null-pointer niche (the plan) or a uniform
  two-case enum? The niche must not leak into `c`-convention signatures.
- **Fallible results per backend** — wasm multi-value returns (the plan;
  universally supported now), QBE an out-pointer or aggregate. Not an error
  global: that would reintroduce hidden state.

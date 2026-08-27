# Canonical MIR

This is the design record for the compiler's canonical machine
representation: the form every compiled backend consumes and the form the
lowerer produces from typed HIR. It fixes the decisions; `src/compiler/
canonical_ir.luc` is the code that follows from them, and `mir_verifier.luc`
is the code that enforces them. When the two disagree with this page, one of
the three is wrong and this page is where the argument is settled.

The language rules MIR has to honour are in [`../language/1.0.md`](../language/1.0.md);
section numbers below refer to it. Section 23.1 states the contract in one
sentence: canonical MIR *makes evaluation order, copies, ARC operations,
failures, traps, worker transfers, and native calls explicit*, so that
optimization and every backend work on fixed semantics.

## 1. Decisions

### 1.1 Structured control flow, not a basic-block graph

MIR keeps control flow structured: `Block`, `Loop`, `If`, `Switch`, and
branches that name an enclosing construct by depth. There is no `goto` and
no arbitrary edge.

Why: Luce has no `goto` (§9), so every program's control flow is structured
at the source. WebAssembly *requires* structured control flow; native targets
merely tolerate it. Lowering structured control flow to labels and jumps is a
few lines; recovering structure from an arbitrary graph is the "relooper"
problem and a reliable source of bugs. Keeping the structure the source
already has costs nothing and removes a whole stage from the wasm path.

What it costs: transforms that thrive on an explicit graph (jump threading,
tail merging, aggressive block layout) are awkward on structured IR. The day
a native backend needs them, it builds a graph *after* canonical MIR as a
target-side lowering. The canonical form does not change.

### 1.2 Typed virtual registers, not an operand stack

Every value an instruction produces lands in a numbered, typed register that
is written once. Instructions name their operands by register.

Why: registers are what a native register allocator consumes, and a wasm
backend maps them onto wasm locals without effort. The operand-stack form
the first slice used is a wasm bias; it forces native backends to simulate a
stack before they can do anything. Stackifying expression trees back onto
wasm's operand stack is an optimization the wasm encoder may do later, not a
property of MIR.

Write-once registers make the verifier simple (a register has one type, set
at its definition) and make data flow visible without a separate analysis.
Mutable locals that need multiple assignments are memory (`Alloca` +
`Load`/`Store`); a later mem-to-reg pass can promote them.

### 1.3 Canonical given a target layout

MIR is target-independent in its instructions but **not** in its memory
layout. `MirProgram` carries the `TargetLayout` it was lowered against:
pointer width, natural alignments, and the C ABI struct rules for that
platform. Field offsets, sizes, and enum tag placement are computed once, in
the lowerer, from that layout.

Why: C interoperability (§21). An `extern struct` must match what the C
compiler produced for the same target, and the only way every backend agrees
on offsets is for MIR to state them. A wasm32 module and an arm64 executable
lowered from the same HIR are *different* MIR programs; that is correct, and
it is the reason `build` takes a target before lowering.

### 1.4 The runtime is a set of symbols, not instructions

Allocation, retain/release, weak references, dynamic strings and
collections, traps, terminal output, worker spawn/wait/cancel, and value
transfer are calls to a small, fixed runtime ABI (`luce_rt_*` symbols).
MIR expresses a retain as `Call luce_rt_retain`, not as a `Retain`
instruction.

Why: §23.4 lists the runtime services and says the runtime is "small and
explicit enough to replace per host". Naming them as symbols keeps MIR the
same for every target and gives each backend one legalization point: wasm
imports the symbols (or links a runtime compiled to wasm); native links
`libluce_rt`. The symbol set is itself part of the canonical contract and is
listed in §4.

### 1.5 Failure is data

A fallible function (`T!`, §13.2) has two results in MIR: the value and an
error slot. A call to it yields both; `try` is that call followed by a
conditional branch to the propagation path; `catch` is the same branch into
the handler. There is no unwinding, no landing pad, no hidden state.

`defer` (§9) is lowered by *duplicating* the deferred statements on every
exit path of the enclosing scope — normal return, `try` propagation, and
`break`/`continue` that leave the scope. Structured control flow makes each
exit an explicit branch, so the duplication is mechanical. Traps (§13.4) do
not run deferred code, matching the language.

### 1.6 Semantics are fixed in MIR; backends legalize

`Add(i32)` in MIR means *checked* addition that traps on overflow (§7). A
shift with an out-of-range count traps. `//` is floor division and `%`
pairs with it. `minimum // -1` traps. Narrow integers keep their source
width in MIR types.

Backends translate that meaning into whatever the target offers: wasm has
wrapping arithmetic, truncating division, and masked shift counts, so each
integer operation becomes a short checked sequence; a native backend can use
overflow flags. What a backend may *not* do is change the meaning. This is
the same rule the HIR interpreter already follows, which is what makes the
interpreter a usable oracle for the compiled path.

### 1.7 What MIR does not contain

- **Generics.** Monomorphized before lowering (§15: "monomorphized by default
  for concrete value types"). MIR functions are concrete.
- **Closures as a construct.** A closure is an environment record plus a
  function whose first parameter is that record. Captures are explicit fields;
  a captured `var` is a runtime cell (§14.1).
- **Interfaces as a construct.** An interface value is a pair (data pointer,
  witness table pointer); the witness table is constant data of function
  pointers in requirement order (§16.3). A call through an interface is an
  indirect call.
- **Names.** Functions, globals, data, and externs are numbered; their symbol
  strings exist only for artifacts and diagnostics.
- **Source spans** beyond one per instruction, for diagnostics and traces.

## 2. The program

```
MirProgram
    layout:     TargetLayout                pointer width, alignments, C ABI rules
    types:      list[MirType]               every type used, with computed size/align
    externs:    list[MirExtern]             imported symbols with C or runtime signatures
    globals:    list[MirGlobal]             mutable module state, typed, with initializer data
    data:       list[MirData]               constant bytes: strings, witness tables, jump tables
    functions:  list[MirFunction]           defined functions, including exports
    entry:      FunctionId?                 process entry when the artifact is an executable
```

Identities are indices into these lists: `TypeId`, `FunctionId`,
`ExternId`, `GlobalId`, `DataId`. An `extern` and a `function` are distinct
kinds, and a call names one or the other; the artifact decides how each is
bound (wasm import versus linker symbol).

### 2.1 Types

```
MirType
    Int(bits, signed)           i8 i16 i32 i64 u8 u16 u32 u64
    Float(bits)                 f32 f64
    Bool                        one byte; 0 or 1
    Ptr                         pointer-width address; untyped at the MIR level
    Struct(fields, size, align) fields carry (type, offset); offsets follow `layout`
    Array(element, count)
    Enum(tag, payloads, size, align)
                                tag is an Int type; payloads are the case structs
    Func(signature)             a function pointer's signature
```

Rules:

- `Struct`/`Enum` offsets and sizes are *stored*, not recomputed. The
  verifier checks them against `layout`, so a backend can trust them and a
  C-exported struct is provably C-compatible for its target.
- Language-level types map onto these: `bool` → `Bool`, `char` → `Int(32,
  unsigned)`, `str`/`bytes`/`list`/`map`/`set` → `Ptr` to runtime storage,
  `T?` → `Enum` with two cases (or a niche in `Ptr` when `T` is a reference),
  `T!` results → two registers, never a type, tuples → anonymous `Struct`,
  class references and `weak` → `Ptr` managed through the runtime,
  interface values → a two-field `Struct` of `Ptr`s.
- `Ptr` is untyped on purpose: memory operations carry the type they load or
  store, which is what a backend needs, and typed pointers would only
  duplicate that.

### 2.2 Functions

```
MirFunction
    name:        str                    `module.function` or an export symbol
    convention:  luce | c               how parameters and results are passed
    params:      list[TypeId]
    results:     list[TypeId]           0, 1, or 2 (value, error) entries
    fallible:    bool                   true when the last result is the error slot
    registers:   list[TypeId]           every virtual register, indexed
    slots:       list[Slot]             Alloca storage: (type, alignment)
    body:        list[Instruction]      structured; see §3
    is_public:   bool                   exported from a wasm module / visible to the linker
    span:        SourceSpan
```

`convention = c` marks an exported function (§21.5) or a callback handed to
C. The verifier rejects ARC-managed, interface, closure, task, or fallible
types in a `c` signature; a backend then applies the target's C ABI (how a
struct travels in registers) without further checks.

### 2.3 Externs, globals, data

```
MirExtern    name, convention (c | runtime), params, results, fallible
MirGlobal    type, initial: DataId?, is_mutable
MirData      bytes, alignment, relocations: list[(offset, FunctionId | DataId | GlobalId)]
```

Relocations let constant data hold addresses (a witness table of function
pointers, a string table of offsets) without the lowerer knowing final
addresses. Wasm resolves them to table indices and data offsets; native
resolves them to relocations in the object file.

## 3. Instructions

Every instruction has a `SourceSpan`. `r` denotes a register operand; `->
rN: T` a defined register. Depth `d` counts enclosing `Block`/`Loop`/`If`
constructs outward from the innermost, as in WebAssembly.

### 3.1 Constants and registers

```
Const(value: Value, type)              -> r
Copy(r)                                -> r        same type; makes a value copy explicit (§6)
```

### 3.2 Arithmetic and comparison

All operands share one type; the result type is that type for arithmetic
and `Bool` for comparisons. Integer operations are checked as §1.6 states.

```
Add Sub Mul                            ints and floats
Div                                    floats only (`/`)
FloorDiv Rem                           ints only (`//`, `%`); traps on zero and on minimum // -1
Neg                                    signed ints and floats
And Or Xor Not ShiftLeft ShiftRight    ints; shifts trap on out-of-range count;
                                       signed ShiftRight is arithmetic
Eq Ne Lt Le Gt Ge                      ints, floats, Bool (Eq/Ne), Ptr (Eq/Ne)
BoolNot                                Bool
Extend(r, to)  Wrap(r, to)             integer width changes; Wrap is the only
                                       non-trapping narrowing and is emitted only
                                       where the language allows truncation
IntToFloat FloatToInt                  explicit conversions; FloatToInt traps out of range
```

Short-circuit `and`/`or` are control flow (`If`), not instructions.

### 3.3 Memory

```
Alloca(slot)                           -> r: Ptr     address of a stack slot
Load(type, address: r)                 -> r: type
Store(type, address: r, value: r)
FieldAddress(struct_type, base: r, field_index)   -> r: Ptr
ElementAddress(element_type, base: r, index: r)   -> r: Ptr   scaled by element size
Memcpy(destination: r, source: r, type)           copies one value of `type`
DataAddress(DataId)                    -> r: Ptr
GlobalAddress(GlobalId)                -> r: Ptr
FunctionAddress(FunctionId)            -> r: Ptr     for closures, witness tables, C callbacks
```

Structs and enums are always addressed; scalars and pointers live in
registers. That one rule decides where every value goes and keeps the
instruction set small. Enum construction is `Alloca` + `Store` of the tag
and payload fields; `match` reads the tag and `Switch`es.

### 3.4 Calls

```
Call(FunctionId, args)                 -> results     0, 1, or (value, error)
CallExtern(ExternId, args)             -> results
CallIndirect(signature, target: r, args) -> results  target is a Ptr from FunctionAddress
                                                      or loaded from a witness table
```

A call to a fallible target defines two registers; the second is the error
slot (`Ptr` to a runtime `Error`, null when absent). `Return(values)` of a
fallible function likewise supplies both. `Raise(error: r)` is `Return` of
an absent value with a present error and exists so a verifier can check that
every error path is explicit.

### 3.5 Control flow

```
Block(result_types, body)              a labelled region; Br to it exits after it
Loop(body)                             Br to it restarts it
If(condition: r, result_types, then, else)
Switch(tag: r, cases: list[(value, body)], default)   dense tags become a jump table
Br(depth)
BrIf(condition: r, depth)
Return(values)
Raise(error: r)
Trap(reason: Value.Text)               unconditional; runs no deferred code
Unreachable                            after a diverging call; verifier-only
```

`Block` and `If` may leave values: their `result_types` name registers
defined at the join, the structured equivalent of a phi. The verifier checks
that every path to the join defines them.

### 3.6 Runtime interactions

These are `CallExtern` to fixed symbols and are listed here because the
lowerer, not user code, emits them and the verifier knows their signatures:

```
luce_rt_alloc(size, align) -> Ptr          luce_rt_retain(Ptr)      luce_rt_release(Ptr)
luce_rt_weak_make(Ptr) -> Ptr              luce_rt_weak_get(Ptr) -> Ptr
luce_rt_trap(message: Ptr, length)         luce_rt_write(bytes: Ptr, length)
luce_rt_str_*  luce_rt_list_*  luce_rt_map_*  luce_rt_set_*   (dynamic storage, §12)
luce_rt_error_make(code, message) -> Ptr   luce_rt_error_code(Ptr) -> i64
luce_rt_spawn(function: Ptr, input: Ptr) -> Ptr    luce_rt_wait(Ptr) -> Ptr   luce_rt_cancel(Ptr)
luce_rt_transfer(value: Ptr, type_info: Ptr) -> Ptr   (§19.2 value graph copy)
```

Retain and release calls are placed by the lowerer from the ownership facts
`SemanticAnalyzer` attaches to HIR (§11.3). Until that analysis exists the
lowerer places them by the simplest correct rule — retain on copy, release at
scope end — and an optimizer may remove balanced pairs.

## 4. Verification

`MirVerifier` proves, before and after optimization:

- every register is defined once, before use, with the declared type;
- every instruction's operand types match its signature;
- `Br`/`BrIf` depths are in range and `Block`/`If` result registers are
  defined on every path to the join;
- struct and enum offsets/sizes agree with `layout`;
- fallible calls define their error register and every fallible function
  ends each path in `Return` or `Raise`;
- `c`-convention signatures contain only C-representable types;
- runtime symbols are called with their known signatures;
- relocations point at existing items.

Backends may assume all of it and check nothing; the native encoders'
current defensive re-checks disappear when they move onto this MIR.

## 5. Interpreters and testing

The **HIR interpreter stays the semantic oracle**. It executes typed HIR and
never sees MIR, so a lowering bug cannot hide inside it (§23.1).

A **MIR interpreter** is added alongside the MIR definition. Structured
control flow plus registers interprets in a few hundred lines, needs no
target runtime, and gives three independent executions of every test
program: HIR interpreter, MIR interpreter, and a compiled artifact. Two
agreeing against one locates the faulty stage. The MIR interpreter is also
the constant folder: §7 requires folding to use runtime semantics, and
sharing the code makes that true by construction.

Compiled artifacts are executed in host-gated shell tests like the native
ones today: wasm through `wasmtime` with a tiny host supplying the runtime
imports, native by running the executable.

## 6. Backends after this MIR

- **wasm** — one-to-one on control flow and registers-as-locals; legalizes
  checked arithmetic and narrow integers; externs are imports; data goes in
  the data section with relocations resolved to offsets and table indices.
- **arm64 / x86-64** — emit an object file per program and invoke the
  system linker; that is the only way `extern` C functions and `libluce_rt`
  link on native targets. The current direct executable writers remain as the
  no-dependency path for programs that need neither, and are not extended.
- **A MIR-to-C backend** is a cheap third compiled target and a strong
  check on the MIR's completeness; it is not planned but nothing here
  prevents it.

## 7. Order of work

1. Replace `canonical_ir.luc` and `mir_verifier.luc` with this design; keep
   the old stack-machine slice compiling only until the wasm encoder is
   moved over (one commit, no dual support).
2. MIR interpreter; three-way differential test harness over the existing
   examples.
3. Grow the lowerer in vertical slices, each gated by the harness:
   scalars and locals → control flow → calls and constants → enums and
   `match` → structs, classes, ARC → closures and interfaces → failure and
   `defer` → collections and strings through the runtime → C boundary →
   workers.
4. Wasm encoder tracks the lowerer; `wasmtime` execution test.
5. Native backends restart from MIR through object files once the MIR stops
   moving.

## 8. Open questions

- **Narrow integers**: kept as distinct MIR types (this document) versus
  normalized to `i32`/`i64` with explicit `Extend`/`Wrap` early. Kept, because
  the C boundary needs exact widths anyway; revisit after the first lowerer
  slice shows how much backend legalization it costs.
- **Optionals of references**: niche representation (null pointer means
  absent) versus a uniform two-case enum. Niche is the plan; it must not
  leak into the `c` convention.
- **Multi-value results on wasm**: use the multi-value proposal for
  fallible calls, or return the error through a global. Multi-value is
  universally supported now and keeps failure as data; a global would
  reintroduce hidden state.

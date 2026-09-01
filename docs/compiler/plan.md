# Compiler plan and decision record

This is the plan half of the compiler's planning pair: the decisions behind
the design and the work still ahead, written so work can resume from it
without the conversations that produced it. The other half,
[`done.md`](done.md), records what exists, what each milestone proved, the
bugs the harness caught, and where the project came from. `mir.md` explains
the machine representation in depth. Update this file when a decision
changes; move items to `done.md` when they are ticked. Do not let either
drift into a wish list.

Last updated: 2026-09-01 (Stage-0 0.30).

## Recovery audit of the unpublished native branch

The 83 commits after `origin/main` grew the compiler by 32,954 lines across
144 files. Architecture-specific source alone reached about 17,400 lines,
with another 2,100 lines of shared native machinery, before its tests and
design document. That is larger than QBE itself without yet providing QBE's
coverage. The experiment is preserved at
`recovery/native-backends-2026-08-30`; its unfinished framework-linking work
is preserved in stash `pre-stage1-qbe-recovery`. Neither belongs in stage 1.

The clean continuation is branch `stage1-qbe`, based on `origin/main`. Its
first commit, `eb6dbfd`, made the permanent stage boundaries visible as
`frontend/`, `hir/`, `mir/`, and `backends/`. The two old seed encoders were
removed once the QBE product path replaced them; their history remains in
`origin/main` without occupying the stage-1 architecture.

`stage1-qbe` is the sole development line through complete planned 1.0
coverage. Do not merge partial slices back into the current `main`. Once every
planned source feature passes the frontend/HIR/MIR/QBE gates, with Wasm
regressions wherever that supporting backend applies, audit the finished
branch as a whole, make that history the new local `main`, and pause before
beginning Luce-owned native backends.

Every unpublished change has this disposition:

| Commit or range | Audit finding | Disposition |
|---|---|---|
| `99d91dc` | The C import/export capability is required, but the implementation duplicated function and extern symbols, imports, lookup, and impossible sentinel states. It also gave common HIR/MIR fields WebAssembly-specific meaning. | Rewrite around one callable-resolution path and a platform-neutral ABI boundary. |
| `efac149` | Whole-program reachability belongs in MIR, but `pub` visibility was treated as artifact export and all data was retained, making the root model incomplete. | Rewrite after export identity is explicit. |
| `7e54621` | The bounded heap model is target-neutral, but allocator policy was placed in the compiler and used linear metadata searches before runtime requirements existed. | Defer to `libluce_rt`; retain the behavioral tests as design evidence. |
| `cb54a92` | Deterministic generated programs are useful, but are strongest once HIR, MIR, Wasm, and QBE all execute the same corpus. | Reintroduce as a cross-backend gate with QBE. |
| `0ff695f` | The document specifies the superseded in-tree QBE-shaped compiler. | Replace; do not retain. |
| `b8b167f..3ecf059` | Native CFG, slot promotion, and the start of target ABI machinery duplicate work QBE already owns. | Remove from stage 1. |
| `192b308` | Independently verified Stage-0 0.27 adoption; unrelated to native architecture. | Reapply independently. |
| `3616b97..14d3fb8` | Full ARM64 selection, allocation, encoding, layout, and execution stack. Cleanly tested in isolation, but premature and much too large for stage 1. | Preserve only on the recovery branch; do not port. |
| `8b28f54..06d5df0` | A second near-copy of the same stack for x86-64 confirmed the abstraction boundary was wrong. | Preserve only on the recovery branch; do not port. |
| `970c08f`, `109caeb` | IEEE encoding and shared artifact-corpus ideas are target-neutral exceptions embedded in the native series. | Re-evaluate when QBE tests need them; copy no code speculatively. |
| `c63630b..51a6a89` | Mach-O signing, dyld binding, C import/export, and the unfinished framework draft are backend/linker work built on the discarded stack. | Use tests as later requirements; implement stage 1 through QBE and the host toolchain. |

## 1. Testing strategy (the part that must not be lost)

Every language feature is proven by **three independent executions** that
must agree:

1. the HIR interpreter — the definition of behaviour, never sees MIR;
2. the MIR interpreter — the lowerer's first consumer, using explicit
   backend layout rules rather than the host platform;
3. a compiled artifact through pinned QBE 1.3 — the required stage-1
   portability oracle and product path across QBE's supported targets.

Wasm is an additional independent regression backend wherever it naturally
supports a slice. It must never dictate HIR/MIR shape, delay complete QBE
coverage, or become a second platform abstraction. Stage 1 is complete when
the full language supplies one sufficient canonical MIR to QBE; Luce-owned
platform backends then replace QBE behind that same boundary.

When two agree and one differs, the stage between them is wrong. Every
lowerer slice adds fixtures to `differential_test.luc` and executes them
through QBE, plus programs that must trap on all three required executions.
Add the same case to the Wasm gate when that backend supports the feature
without changing canonical shape. The triangle has found real bugs in every
stage, including its "reference" implementations. Keep it.

Rules: a spec semantics question (overflow, `//`, shifts, `~` on unsigned)
is settled by reading `1.0.md` §7, implemented in the HIR interpreter first,
and then everything else is made to agree. Backends legalize; they never
choose semantics. Design is written down before code — in the file header
and, for gates, in the spec — and a slice is ticked only on a green
`./test.sh` with the commit in.

The stage-0 `examples/` corpus is a standing progress input. Its audited matrix
lives in `examples/README.md`: adopt only cohesive sources that become an
automated parser/HIR/MIR/artifact gate, modernize them to the current 1.0
surface, and pin the first unsupported stage until it advances. Do not bulk
copy generated caches or duplicate programs merely to increase the count.

### Stage-1 completion contract

`examples/FEATURES.md` is the single conformance ledger for
`docs/language/1.0.md`, not merely a parser showcase. It must account for every
specified declaration, statement, expression, operator, reserved word,
semantic rule, diagnostic rule, and deliberate rejection. Each row names its
positive and negative tokenizer/parser tests, HIR resolution tests, canonical
MIR/verifier tests, and real QBE artifact test where the rule is executable.
An absent layer is marked unsupported with the first missing stage; it is never
silently omitted or counted as complete.

The example corpus is the human-readable half of the same proof. Together its
small focused programs must express every executable language capability,
build through the product QBE path, run, and compare their observable output
with checked expectations. Parser-only tours remain useful fixtures but do not
prove implementation. Stage 1 is complete only when the ledger has no
unsupported 1.0 rows, all applicable examples execute through QBE, the full
diagnostic corpus is green, and the architecture audit still finds no target
fact before the backend boundary. Wasm results are additional evidence, never
a substitute for or prerequisite to this QBE-complete claim.

## 2. Canonical MIR — the decisions (details in `mir.md`)

- **Structured control flow** (`Block`/`Loop`/`If`/`Switch`/`Br`/`BrIf`/`Yield`), not a basic-block graph. Luce has no `goto`; structure → jumps is trivial for native, jumps → structure (the relooper) is the hard direction and is avoided entirely. **Encoded flat**: a body is one instruction list with `Else`/`Case`/`Default`/`End` markers — the wasm encoding — so every consumer is a single linear pass with a region stack and a body is one contiguous allocation.
- **Typed write-once registers**, not an operand stack. Registers map to wasm locals for free and to native registers directly. Mutable locals live in `Alloca` slots; a later pass promotes them.
- **Canonical before target layout**: MIR aggregate types retain field and case
  structure, while pointers stay abstract. `FieldAddress` names a field and
  `ElementAddress` names an element type and index; no byte offset, pointer
  width, or target-natural alignment is stored in MIR. Each backend computes
  and caches its layout when encoding. The same MIR program therefore feeds
  Wasm, QBE, and later native backends.
- **Aggregates never sit in a register**: a register of aggregate type holds an address; copies are explicit `Memcpy`; aggregate results go through a hidden leading pointer parameter; aggregate parameters are passed by pointer, written through only by a `mutating` receiver.
- **Runtime services as explicit calls and bindings.** Ownership, weak
  references, I/O and traps use verified semantic operations. Operations whose
  structural type must survive legalization—typed storage, collections,
  classes, closures, and interface values—remain canonical instructions. A
  program-level runtime binding names each exact private Luce implementation by
  `FunctionId`; backend legalization alone supplies physical layout and calls
  that identity. There is no runtime symbol lookup and no target fact in MIR.
- **Failure as data with explicit ownership**: a fallible function receives a caller-owned `Error` slot as hidden parameter 0 and returns `(value, null)` on success or `(absent, error_out)` on failure. `try` is a call plus one conditional branch; propagation copies into the current function's slot after active `defer`s; no allocation or unwinding.
- **Semantics fixed in MIR**: `Add` means checked add; `floor_div`/`rem` are floor semantics; shifts trap on count, drop bits shifted out. Checks are removed only by proof, never by build mode.
- **Not in MIR**: generic declarations/parameters (monomorphized), source
  interface lookup/conformance syntax, and semantic names. Interface values do
  reach MIR as nominal handles, normalized requirement/conformance metadata,
  and dynamic calls; their box and witness-table layout belong only to a
  backend. Closures likewise retain typed descriptors and environment metadata
  without choosing a physical layout.
- **`Yield`** is the structured phi: a region that produces values names them on every exit.
- **Narrow integers stay MIR types** (Prism `DType` and the C ABI need exact widths).
- **Settled**: optionals, including `Class?`, remain uniform `u8`-tagged enums
  in canonical MIR. Null class/weak handles are private storage sentinels and
  never source values. Pointer-shaped foreign handles are likewise tagged
  internally and raw-null only at a C boundary. Fallible ABI is per backend
  (wasm multi-value, QBE
  out-pointer/aggregate — never a global).

## 3. Backends, QBE, and the linker — the decisions

**Stage 1 uses real QBE as the native backend and semantic oracle.** Luce emits
QBE IL from verified canonical MIR, invokes QBE, and lets the host assembler
and linker produce the executable. QBE owns SSA destruction, instruction
selection, register allocation, ABI lowering, and assembly emission. Luce
does not duplicate those passes in stage 1.

- HIR and canonical MIR remain shared. Target divergence starts at the backend
  boundary: Wasm, QBE, and eventually Luce-native backends consume the same
  verified MIR contract. Their output shapes intentionally do not share a fake
  byte-only interface.
- The QBE backend is one compact MIR-to-QBE translation layer. Host process
  invocation and output paths are a separate materialization concern;
  target-specific ABI and layout facts stay inside the backend.
- Tests execute the same generated and hand-written programs through the HIR
  interpreter, MIR interpreter, Wasm, and QBE. A later native backend must
  agree with QBE before it can replace it.
- Our own machine-code encoders and image writers are a later backend project,
  after the language, runtime, MIR, and QBE oracle are stable. They begin from
  the shared MIR boundary, not by introducing target passes into the core.
- `libluce_rt` is Luce compiled as ordinary MIR. During stage 1 QBE links it
  through the host toolchain; later native backends may own that final link.

### WebAssembly

- Host contract is **WASI preview 1** (`fd_write` via a scratch iovec at offset 0, `_start` → `proc_exit`, `memory` exported). Tests use `wasmtime`, installed in CI.
- Registers → locals; narrow values kept canonical inside i32; shadow stack in linear memory with an overflow guard; checked arithmetic legalized in four shapes; exactly one wasm structured instruction per MIR region so MIR depth equals wasm label depth; float constants assembled arithmetically (Stage-0 has no bit casts).

## 4. The proving programs

**1 — the guest in Luce (wasm).** The seed guest commands (`echo_guest.c`, `lucia_guest.h` + 11 seeds) rewritten in Luce, compiled to wasm32, running unmodified under the existing `WasmHost` ABI (imports `lucia_call(ptr,len) -> i64`, `lucia_log`, `lucia_yield`; exports `lucia_alloc`, `lucia_main`). The first place "safe by construction" can be shown to a non-programmer. Why this one: `done.md` §4.2.

**2 — the host in Luce (native).** Terminal, realm, storage, crypto, network and `WasmHost` as real executables on macOS (libSystem, Cocoa/Metal via dyld) and Linux (libc/OpenSSL), with the wasm engine as a Luce library — decoder + interpreter with fuel beside the existing encoder, differential-tested against `wasmtime` while both exist. Owning the engine settles the preemption blocker and frees the compiler tests from `wasmtime`.

## 5. What is next — the checklist

Each item is a vertical slice gated by §1. Gates (§6) are settled in the spec *before* the feature lands in `hir_gen`. Ticked items move to `done.md` §2.

### Proving program 1 — the guest

- [x] **Recover the compact compiler shape** (2026-08-30): preserve the
  unpublished native experiment, restart from `origin/main`, and organize the
  existing code by frontend/HIR/MIR/backend ownership without compatibility
  wrappers (`eb6dbfd`).
- [x] **Enforce the backend boundary** (2026-08-30): remove concrete targets,
  pointer width/alignment, aggregate offsets/sizes, slot alignment, and raw
  target-sized relocations from canonical MIR. Lower once; compute cached byte
  layout in each backend. The architecture gate rejects future platform leaks
  before `backends/` (`b09ac68`).
- [x] **QBE backend oracle** (2026-08-30): translate verified canonical MIR
  directly to QBE IL, compile and execute the complete existing differential
  corpus, and require the checksum-pinned QBE 1.3 tool in the full test gate.
  No target IR or platform layout was added before the backend boundary
  (`facc3c3`).
- [x] **QBE product materialization** (2026-08-30, hardened 2026-08-31):
  `--target native` writes canonical-MIR-derived IL, QBE assembly, diagnostics,
  and the linked candidate inside an atomically unique, owner-only directory
  beside the output. Regular files connect QBE and the host C driver because
  feeding one child pipe completely before draining the other can deadlock on
  large programs. Same-filesystem rename installs only the finished candidate
  atomically; failures preserve the prior artifact and remove all scratch.
  The complete differential corpus and native smoke gate use this path.

- [x] **Decompose the stateful compiler passes before the next major
  managed-language family.** The former 4,299-line HIR class is now a
  369-line orchestration facade, a 2,308-line program-wide declaration
  collector, a 1,194-line shared typed transaction/model, a 3,008-line body
  checker, and focused 743- and 291-line generic function/nominal owners.
  Declaration defaults cross that boundary through
  one constant-expression contract; type, symbol, and node tables remain
  singular. Statements, expressions, and patterns remain together because
  their traversal is mutually recursive; splitting them today would add a
  callback graph rather than a responsibility boundary. The former 3,659-line
  MIR lowerer is likewise a 186-line whole-program coordinator, one 865-line
  identity/type/state transaction, and one 4,025-line function walk.
  Statements, expressions, patterns, calls, aggregates, and cleanup remain
  together because they are mutually recursive and share one lexical
  transaction. The class slice completed that ownership review: class ARC,
  destruction, weak sinks, places, calls, and structured control all mutate
  that same register/region/defer transaction, so extracting them would add a
  forwarding graph or duplicate ownership state rather than establish a new
  owner. The later closure review kept the recursive evaluator cohesive, while
  existential interface resolution established an independently testable HIR
  boundary. Standard iteration established focused 137-line declaration and
  210-line operation owners in `hir/interfaces/`; only lexical body scope
  restoration remains in the mutually recursive checker. Independently
  generic methods reused the generic-function owner
  and the existing declaration transaction rather than adding another pass.
  Generic accounting established a separate 263-line cross-stage reporting
  owner and a 28-line backend emission record instead of coupling presentation
  to HIR, MIR, QBE, or Wasm. Its out-of-band function provenance follows
  package composition and optimizer remapping without adding source or generic
  facts to canonical MIR. The declaration collector and now 4,434-line
  function walk were reviewed again after recursive equality. The 57-line HIR
  protocol owner and generated-helper identity queue are independent, but MIR
  hashing and equality recursively share the same register, slot,
  aggregate-address, call, and structured-region transaction as the enclosing
  expression walk. Extracting either marked section today would duplicate that
  machinery or add a forwarding interface, so they remain cohesive until a
  reusable function-emission owner can replace—not wrap—the shared helpers.
  The incoming-cfunc slice raised that shared function walk to 5,206 lines
  and the Wasm encoder to 2,475 lines; both were reviewed again at the slice
  boundary. Keep the parser and Wasm encoder sectioned
  until new work establishes real component boundaries; do not split any pass
  into arbitrary helper files just to lower a line count.

- [x] **Enums and `match`** (2026-08-28, `done.md` §2). `Switch` is still unused by the lowerer: `match` is an `If` chain, because a wasm `Switch` needs `br_table` plumbing that breaks the one-region-one-label invariant; jump tables come with the native pass.
- [x] **`for`, integer ranges, and standard iteration protocols** (2026-08-31, `done.md` §2). Built-in ranges/lists/strings retain their canonical semantic paths. User values use compiler-known `Iterable[T]`/`FallibleIterable[T]` contracts through concrete, constrained-generic, or existential dispatch; `try for` applies the ordinary failure model to each `next()`. HIR resolves one target-independent loop driver, MIR reuses calls/optionals/structured control, and both oracles, QBE, and Wasm prove execution and lexical iterator cleanup.
- [x] **Compiler-derived structural markers and immutable hashing**
  (2026-08-31, `done.md` §2). `Equatable` and `Hashable` are closed,
  constraint-only proofs with no source conformance or runtime witness.
  `hash(value)` evaluates once and resolves to one HIR operation; shared MIR
  lowering expands every structural aggregate into ordinary typed control and
  memory operations. Only execution-local IEEE scalar coding remains a
  verified canonical primitive. Both semantic oracles, QBE, Wasm, and
  `examples/hashing.luc` prove equal-value consistency without freezing a
  numeric hash algorithm.
- [x] **Cycle-aware structural list equality** (2026-08-31,
  `done.md` §2). Recursive value declarations may close through list
  indirection, so one source comparison owns an opaque ordered-pair
  transaction. Finite types remain one allocation-free canonical loop;
  recursive types use lazily reserved private helpers that close the compiler
  type graph without expanding it. Element/tag/shape semantics stay in HIR and
  canonical MIR, while the sealed runtime owns only pair-set storage and QBE
  and Wasm only pass their list handles. Both semantic oracles, verifier and
  optimizer gates, the differential native corpus, and `examples/lists.luc`
  prove identity, finite contents, self/deep cycles, mismatches, alias-topology
  independence, and context growth, providing the settled equality/hash
  baseline used by maps and sets.
- [x] **Insertion-ordered maps and sets** (2026-08-31, `done.md` §2).
  Inferred/explicit construction, typed lookup and mutation, insertion order,
  copy, identity, recursive order-independent equality, iteration guards, and
  complete key/value ownership run through both semantic oracles, canonical
  MIR, the sealed hash-table runtime, QBE, and Wasm. `Map(K,V)` and `Set(T)`
  remain target-neutral through MIR; generated code owns hashing/equality and
  structural ownership callbacks, while runtime/backend code owns only table
  storage, process-private bucket seeding, layout, and descriptors.
- [x] **`defer`** (2026-08-29, `done.md` §2). Receiver and arguments are captured at registration; lexical cleanup is LIFO and runs on fallthrough, `return`, `break`, and `continue`, but not traps. The lowerer duplicates cleanup calls at each ordinary exit, ready for error propagation to become one more exit edge.
- [x] **`try`/`catch`, `Error`** (2026-08-29, `done.md` §2). `T!` is an outer function-result effect, `ErrorCode` carries explicit package identity, calls use caller-owned Error slots, and propagation/recovery run active `defer`s. Scalar, unit, aggregate, conditional, and match-produced fallible values pass the three executions.
- [x] **Custom struct `init`** (2026-08-29, `done.md` §2). Construction has an explicit HIR identity; `SemanticAnalyzer` proves every successful path initializes each field exactly once before `self` is read or escapes; fresh caller-owned receiver storage composes with the ordinary `T!` error-slot path.
- [x] **Conditional binding** (2026-08-30, `done.md` §2). `if let`
  checks its optional subject once and canonicalizes directly to the existing
  exhaustive optional `Match` HIR. Payload scope, ownership, flow analysis,
  MIR lowering, and backend behavior therefore have one implementation rather
  than a conditional-binding-specific path.
- [x] **Explicit `discard[T]`** (2026-08-31, `done.md` §2). One compiler-known
  HIR node records intent, rejects unhandled `T!`, and preserves `never` flow.
  Lowering evaluates the operand once and then uses the existing
  full-expression ownership cleanup; there is deliberately no MIR/backend
  discard instruction. The matching §7.8 `L0701` advisory now reports every
  silently discarded non-`unit` result and points intentional code to the
  explicit spelling. Flat HIR carries one cold source-module identity beside
  each node's type/span, so this and future advisories remain linear scans
  with exact file provenance rather than duplicate recursive walkers.
- [x] **Dynamic source `trap(message)`** (2026-08-31, `done.md` §2). One
  never-valued HIR form evaluates an ordinary `str` and terminates without
  lexical cleanup. Shared lowering uses the existing target-neutral
  `luce_rt_trap(Ptr, u64)` contract followed by canonical `Unreachable`; QBE
  and Wasm alone choose stderr and their terminating instruction. Complete
  source-location/stack diagnostics remain part of the §13 audit.
- [x] **Source-level `never` callables and bottom flow** (2026-08-31,
  `done.md` §2). `-> never` and `-> never!` survive direct, generic,
  function-value, closure, and interface signatures. HIR records contextual
  bottom coercion and the exact eager prefix before a terminating operand;
  canonical MIR records only target-neutral `returns_never` and structured
  termination. Illegal storage is rejected before lowering, including after
  generic/interface substitution and inside native-pointer pointees. Both
  oracles, the verifier, QBE, Wasm, and the focused trap example agree.
- [x] **Source `assert(condition, message?)` execution** (2026-08-31,
  `done.md` §2). One unit-valued HIR form preserves ordinary eager argument
  order and supplies the exact default `"assertion failed"` message. Shared
  lowering emits a structured failed arm around the existing trap contract;
  there is no assertion MIR instruction or backend-specific lowering. The
  remaining effect-free-condition proof waits for real operational summaries,
  and source-location/stack reporting remains in the §13 diagnostic audit.
- [x] **Complete explicit numeric construction for every scalar width**
  (2026-09-01). One `NumericConvert` HIR node covers every integer/integer,
  integer/float, float/integer, and f16/f32/f64 pair without
  source-family duplication. §7.5 now states the policy explicitly:
  integer-to-float and float narrowing round to nearest/ties-to-even,
  float-to-integer truncates toward zero after rejecting NaN, infinity, and
  values outside the destination interval, and only finite floating narrowing
  overflow traps. HIR constants and operations round at their declared width;
  canonical MIR retains typed `Convert` operations and target-independent
  guards. QBE and Wasm legalize f16 only behind their backend boundaries,
  with exact IEEE rounding and two-byte storage. Both oracles, structural
  hashing and display, the full differential corpus, and
  `examples/numeric_conversions.luc` agree through native QBE and Wasm. Direct
  f16 C ABI crossings remain part of the generated rich-boundary adapter work;
  the compiler rejects them instead of silently widening the signature.
- [ ] **`extern` import/export** through one source-level callable model;
  C signatures verified by the MIR verifier, with Wasm namespaces and native
  symbols interpreted only by their backends. The direct scalar-function rung
  is complete: ordinary definitions, `export c func`, and `extern func` share
  one HIR function table, symbol kind, import path, argument checker, and
  `Call` node; lowering performs the sole split into MIR definitions/externs.
  HIR/MIR hosts, Wasm `env` imports, exact exports, QBE ABI extension types,
  and real libc linkage are covered. Integer- and pointer-represented nominal
  handles are also complete: HIR preserves identity and opacity; ordinary
  optionals remain tagged; one canonical MIR boundary adapter alone
  encodes/decodes C null and traps `null_foreign` for bare zero tokens. C
  exports are ordinary Luce bodies behind shared MIR wrappers, so source calls
  never acquire boundary behavior. `out` slots are also complete: HIR retains
  their ordered source contract, one lowerer adapter passes call-owned raw
  pointers and shapes declared-result-then-output values, the semantic hosts
  cover both sides of that memory boundary, and real QBE/libc
  `posix_memalign` proves a nullable pointer output. Real QBE/libc `getpid` and
  `malloc`/`free` execution prove both handle representations. The anonymous
  raw data-pointer type `foreign` is complete on the same protocol: HIR retains
  one atomic opaque/equatable token, ordinary optionals stay tagged, and the
  sole HIR-to-MIR lowering maps it to canonical target-neutral `pointer`.
  Direct, optional, out, cfunc-signature, and extern-struct-field crossings
  share the existing null adapter; real QBE/libc `malloc`/`writev`/`free`
  proves the end-to-end layout and call path. Direct C `str` inputs, results,
  and `out` slots are complete without widening the closed `cfunc`, C-export,
  extern-struct, or extern-variable vocabularies. Inputs receive exact
  call-scoped NUL-terminated copies; results trap on null, scan immediately,
  validate UTF-8, and become ordinary owned string buffers before any input
  temporary is released. HIR and MIR hosts cover valid, null, malformed, and
  unterminated values; the differential harness reaches both artifact
  encoders; real QBE/libc `strchr` proves a result borrowed from its input.
  Borrowed `list[H]` inputs are complete for the closed scalar, named-handle,
  and `foreign` element row. The existing list identity remains intact through
  HIR and MIR; the call adapter exposes its dense first-element address, uses
  null for an empty value, and leaves the separately declared count untouched.
  It emits no copy, packing path, new MIR instruction, or backend-specific
  representation. Bare pointer elements receive a target-neutral validation
  loop before the call. Both semantic hosts prove ordered and empty values,
  Wasm and QBE encode the same canonical MIR, and real QBE/libc `memcmp` reads
  the storage directly. List results, output slots, nested/text/optional
  elements, extern-struct fields, cfunc signatures, and C exports remain
  deliberately refused. External variables are also complete: HIR retains
  explicit observable loads/stores,
  canonical MIR owns a distinct external-global table and instructions, both
  semantic oracles use explicit variable hosts, QBE binds the C object symbol,
  and Wasm imports one mutable `env` global. Bare pointer-handle zero is
  ordinary global state; null translation remains confined to callable C
  boundaries. Exact named `cfunc` values are complete in the separate rung
  below. The field-only `extern struct` declaration is now executable too:
  HIR keeps one nominal value-struct capability, MIR stays structurally
  target-neutral, and the call adapter recursively packs inputs and unpacks
  outputs field by field into call-owned pointer slots. Both semantic oracles,
  focused MIR verification, backend-generic aggregate legalization, and real
  QBE/libc `clock_gettime` execution prove the path. By-value results and
  nullable extern structs are refused. The prose in language §21.17 also says
  methods, field defaults, and interface conformance remain available while
  the grammar and parser deliberately admit only plain fields; that
  specification inconsistency must be resolved before calling §21.17 closed.
  Incoming bare/nullable C function pointers and cfunc fields are now complete
  in the separate rung below. Exported structs/enums, generated adapters, the
  explicit inbound-memory verbs, and callback runtime enforcement remain on
  this item.
- [x] **Checked byte access and the first adopted native example**
  (2026-08-30): `bytes.length`, `str.byte_count`, and checked `bytes[u64]`
  have explicit target-neutral HIR semantics and lower to the existing
  structural MIR field/element operations plus an explicit trap edge. String
  and byte counts are now the spec's `u64` throughout canonical MIR and the
  runtime seam. The adapted Stage-0 recursive-descent calculator scans UTF-8
  bytes (never integer-indexes `str`), checks, compiles and links through the
  product QBE path, then executes successfully. Wasm and both semantic oracles
  agree on successful access and out-of-bounds traps.
- [x] **Closed-world MIR reachability** (2026-08-30): package `pub` visibility
  and explicit artifact export are orthogonal MIR facts, so `pub` no longer
  masquerades as a native ABI promise. Package APIs, the explicit process
  entry and explicit C-export wrappers root a deterministic graph over direct
  calls and function addresses. Surviving identities are remapped in source
  order; externs, C globals, Luce globals and data reachable only from
  discarded functions are pruned and remapped too. A rootless private library
  is conservatively unchanged because it is not a closed world. The same
  optimized, reverified canonical MIR feeds Wasm and QBE; only the backends
  choose whether package-public functions are exposed by their artifact model.
- [x] **Fixed value arrays and the second adopted native example**
  (2026-08-30): `array[T, N]` is a canonical HIR type; contextual literals,
  value copies, structural equality, `.length`, checked `u64` reads, and
  mutable mixed field/element places—including mutating method receivers—lower
  once to canonical MIR `Array` and `ElementAddress`; equality uses a
  count-independent MIR loop. HIR, MIR, Wasm, and real QBE agree on nested
  arrays, zero length, aggregate calls/results, and bounds traps. The adapted
  Stage-0 sort program uses allocation-free fixed storage and is a native QBE gate.
- [x] **Fixed arrays convert to ownership-safe immutable slices**
  (2026-08-31). `array[T, N][lower..<upper]` evaluates its source and bounds
  once in source order, validates them before allocation, and snapshots only
  the selected value range. Shared lowering reserves one runtime buffer,
  copies through a count-independent loop with structural retain helpers,
  captures the existing canonical `slice[T]`, and releases the temporary list
  identity. Inline frame storage never escapes, reference elements stay
  shallow, and no array layout or slice representation enters HIR/MIR.
  Scalar and managed-element escapes, post-snapshot mutation, zero/partial
  ranges, invalid bounds, both oracles, native QBE, and Wasm all agree.
- [x] **The adopted Brainfuck example is a whole-program integration gate**
  (2026-08-30): Stage-0's interpreter algorithm now runs with explicit fixed
  tape/output capacities, retaining its bytecode loop, forward/backward
  bracket search, nested `while`/`match`, wrapping `u8` cells and output
  verification. HIR execution, optimized canonical MIR, Wasm encoding and the
  native QBE product path all agree. This is deliberately an example gate,
  not a second array implementation or a hidden builder; growable output still
  waits for the target-neutral allocation/runtime contract.
- [x] **Exact ordinary function values** (2026-08-30): named Luce functions
  become statically typed HIR `FunctionAddress` values and calls through
  locals, constants, fields, parameters, results, conditionals and imported
  module members become `IndirectCall`. Labels/defaults remain declaration-call
  facts; function-value calls are positional and exact. The closure slice
  generalized canonical MIR ordinary functions to typed code/environment
  descriptors and `CallClosure`; capture-free names retain a null environment
  and allocate nothing. QBE and Wasm alone choose descriptor/table layout.
  Both semantic oracles, optimized MIR, Wasmtime, real QBE and
  `examples/function_values.luc` agree, including aggregate/fallible named
  protocols, defer capture and evaluation order. Infallible-to-fallible lift
  remains separate work.
- [x] **Exact named `cfunc` values and C-convention indirect calls**
  (2026-08-30): the contextual type is now a canonical HIR form, while calls
  reuse the same positional `IndirectCall` node as ordinary function values.
  A matching capture-free Luce name selects one demand-generated C adapter;
  an exact extern name becomes an external-symbol address without a wrapper.
  Canonical MIR adds only the facts that actually diverge at this boundary:
  `CallIndirect` carries its calling convention and `ExternAddress` names a C
  symbol. C null adaptation for nullable pointer-handle parameters/results is
  shared with direct C calls. The verifier, optimizer and MIR oracle cover the
  new identity/convention edges; Wasm maps definitions then addressed imports
  into its backend-owned table; real QBE executes both libc addresses and a
  generated adapter invoked back from libc through `atexit`. Stored fields,
  parameters/results, aliases and selection run in
  the differential corpus and `examples/cfunc_values.luc`. This rung does
  originally did **not** claim pointers dynamically returned by C, nullable
  cfunc slots, or lambda/closure conversion; the next rung closes those
  representation questions explicitly.
- [x] **Incoming and nullable `cfunc` pointers remain opaque until invocation**
  (2026-09-01). HIR distinguishes compiler-resolved adapters/symbols from an
  arbitrary C-supplied code token; raw pointers never masquerade as source
  symbols. Direct results, `out` slots, nullable results, and extern-struct
  fields preserve that identity through both semantic oracles and canonical
  MIR's existing abstract pointer. A separate function-pointer host executes
  an exact verified C signature, while the MIR memory view lets tests populate
  a logical aggregate field without learning backend byte offsets. Bare zero
  remains inert when read and traps `null_foreign` only at invocation or the
  next bare input crossing; nullable zero decodes to `none`. Capture-free names
  and lambdas share generated adapters, while captured closures remain rejected.
  Focused HIR/MIR tests, the differential corpus, and real libc `signal`
  round-tripping prove the path. The callback thread/runtime-context contract
  and the remaining C-export callback matrix stay open.
- [x] **Settle the target-neutral runtime allocation contract before coding
  it** (2026-08-30, spec §§21.12 and 23.4). Canonical MIR requests storage for
  a runtime count of one structural `TypeId`; it never manufactures target
  byte size/alignment. Only a backend legalizes that request to the bound
  private allocator's byte-count signature using its existing layout cache
  and checked multiplication. The allocation starts with one strong
  storage owner; retain/release share it and the last release returns the
  opaque block after element cleanup. The HIR oracle keeps semantic values;
  the MIR oracle uses explicit test layout. `libluce_rt` is a sealed Luce
  package composed with application MIR before optimization, while its
  `.native.luc` substrate exposes only typed load/store/advance/copy and a
  stable, host-sized, monotonically committed byte arena. Wasm growth and
  native reservation are backend implementations of that provider. No
  pointer/integer casts, source `sizeof`, target layout, allocator policy, or
  application-native authority enters HIR/MIR or the compiler. The sealed
  package alone may own module-private mutable allocator state; it lowers as
  an ordinary structural MIR global and cannot escape into application source.
- [x] **Implement the canonical typed-storage substrate through every
  backend oracle** (2026-08-30). `AllocateStorage` carries only a structural
  `TypeId` and runtime `u64` count. `MirProgram.runtime_bindings` identifies
  the one private Luce allocator definition by `FunctionId`; the verifier
  proves uniqueness, privacy and `(u64, u64) -> Ptr`, and reachability follows
  the implicit edge only from live allocations. The MIR oracle allocates by
  semantic test layout without executing allocator policy. QBE and Wasm each
  compute their own layout, guard multiplication, implement null for count
  zero and one byte for positive zero-size layout, and call the composed
  function directly. Real QBE and Wasmtime execute fixed-buffer allocator
  fixtures, including overflow traps. The obsolete byte-shaped
  `luce_rt_alloc` MIR extern is removed, leaving no route around the typed
  operation. This is substrate, not yet source collection lowering or the
  production allocator.
- [x] **Compose a sealed runtime as canonical MIR before optimization**
  (2026-08-30). `compose_runtime` preserves every application identity and
  remaps the runtime's type, function, extern, external-global, global and
  data tables exactly once. Canonical builtins are validated, equal external
  declarations share one identity, conflicts fail before a backend, and
  runtime service bindings follow the remapped private function. Applications
  cannot supply bindings; the runtime cannot define an entry, package API or
  artifact export. The combined program is then verified and optimized as one
  closed world, where live allocation is the edge that retains its allocator.
  This proves the composition mechanism with hand-built MIR; loading and
  compiling the production sealed source package remains the next rung.
- [x] **Make native source authority an explicit frontend fact** (2026-08-30).
  The package reader alone recognizes `.native.luc`, removes the authority
  suffix from module identity, and carries a closed `ModuleAuthority` through
  parsed source into HIR. `native_ptr[T]` and `native_mut_ptr[T]` retain their
  pointee and mutability in HIR, are unavailable in safe modules, and cannot
  escape through a public alias, aggregate or function signature. Importing a
  safe wrapper does not transfer authority. The target-neutral address token
  erases to canonical MIR `Ptr` only in the shared lowerer. Typed native
  operations and the sealed arena capability remain the next slice.
- [x] **Lower the first typed native operations through the shared MIR path**
  (2026-08-30). `native.load`, `native.store` and `native.advance` are
  compiler-known HIR forms admitted only by native authority. Their checker
  preserves source evaluation order, pointee identity and pointer mutability;
  immutable stores, labels, wrong arity and non-pointer operands fail before
  lowering. They become the existing canonical `Load`, `Store` and
  `ElementAddress` instructions, so all backends consume one representation
  and choose layout only at their existing boundary. The sealed arena
  provider remains the next runtime capability.
- [x] **Keep native reinterpretation and overlapping moves structural through
  MIR** (2026-08-30). Contextual `native.rebind` changes an audited HIR pointee
  view without changing an address or escalating mutability, then erases to
  the same canonical `Ptr`. `native.move` checks equal pointees and a mutable
  destination, and lowers to `MoveElements(TypeId, u64)` with overlap-safe
  semantics. QBE alone scales the count and calls `memmove`; Wasm independently
  bounds the backend-computed byte count to its 32-bit address space before
  `memory.copy`. Both execute overlapping ranges, and MIR composition remaps
  the retained structural type. This is the last pointer substrate needed by
  runtime-backed contiguous collections; it does not implement a collection.
- [x] **Give sealed runtime state an explicit source-to-QBE path**
  (2026-08-30). `PackageRole` is a compiler input rather than a package-name
  convention. Only that role may declare private, structurally zeroable
  `var name: Type` module cells; applications cannot declare or import them.
  HIR keeps observable `GlobalLoad`/`GlobalStore` nodes and its oracle owns one
  isolated state instance. Shared lowering emits ordinary canonical
  `MirGlobal`/`GlobalAddress`/`Load`/`Store`; reachability retains live cells,
  and the existing verifier and composer remain their sole MIR authorities.
  QBE lays out and mutates the same program successfully. Wasm also places
  cells after immutable data in linear memory as a supporting regression,
  without leaking an offset or pointer width before its backend plan.
- [x] **Give the sealed runtime one stable arena capability** (2026-08-30).
  `native.arena(end)` requires both native module authority and the explicit
  runtime package role. Its HIR result retains `native_mut_ptr[u8]`; shared
  lowering emits one verified `(u64) -> Ptr` runtime-convention call, with no
  capacity, page, pointer width or host API in canonical MIR. The MIR oracle
  supplies a deterministic fixed test arena. QBE alone reserves a 64 MiB
  zero-filled BSS region, guards the requested prefix and returns its stable
  base; repeated calls observe the same storage and over-capacity terminates.
  A fully precommitted BSS reservation satisfies the monotonic-prefix
  contract while allowing the host loader to commit pages lazily. Wasm is not
  required for this QBE-complete slice and may later legalize the same service
  with memory growth.
- [x] **Compile the first freestanding Luce allocator through QBE**
  (2026-08-30). A shared target-neutral `RuntimeService` contract lets the
  sealed package descriptor resolve one private native source function to a
  HIR `SymbolId`; lowering preserves it as the exact MIR `FunctionId` without
  name lookup. The pipeline independently compiles and composes
  `src/runtime/allocator.native.luc`. Its checked aligned bump policy reserves
  byte zero and commits state only after arena success. Verification and
  reachability retain the binding, function, global and provider as one unit;
  real QBE proves distinct typed allocations and exhaustion.
- [x] **Expose typed allocation only to reviewed runtime source**
  (2026-08-30). `native.allocate[T](count)` requires both native module
  authority and the sealed runtime package role, preserves `T` and the `u64`
  element count in HIR, and produces a typed mutable native pointer. Shared
  lowering maps it directly to the already-verified target-neutral
  `AllocateStorage(TypeId, u64)` contract. Application native modules cannot
  call it, and no other native operation accepts generic arguments. This is
  the source bridge needed by runtime collection headers; it adds no layout,
  byte arithmetic, allocator policy, collection operation, or new MIR form.
- [ ] **Complete `libluce_rt` in freestanding Luce**. Typed deallocation and
  power-of-two intrusive free-list reuse are complete (`done.md` §2): the
  canonical request retains `TypeId`/count, backends derive matching physical
  classes, and allocator policy remains compiled Luce. Structural list/slice
  ownership services and managed element destruction are complete too
  (`done.md` §2). One compiler-owned sealed-runtime descriptor now maps the
  closed service vocabulary to source identities; callers supply only the
  resource location, so tests and future installations cannot drift into
  separate manifests. The CLI accepts repeated explicit `--runtime FILE`
  inputs and composes that reviewed package before either backend. Automatic
  discovery in an installed toolchain still awaits a Stage-0 host
  `std.os.executable_path()` capability rather than embedding a
  checkout-relative path, environment convention, or platform syscall in the
  compiler.
  Public builder/codec APIs and the remaining standard-library policy remain.
  Extend the checked runtime as those semantic services become expressible;
  do not move policy into the compiler or a backend.
- [ ] **Complete runtime-backed collections and text.** Runtime-backed
  `list[T]` construction, identity, indexed access, append, insert,
  `remove_at`, clear, reserve, aggregate elements, growth, and immutable list
  snapshot slicing now execute
  through HIR, canonical MIR, and QBE (`done.md` §2). Shallow `copy` with
  independent collection storage and shallow `+` concatenation are complete
  too. Ordered list iteration and alias-wide shape-invalidation traps are
  complete, as are recursive list/slice ARC, copy-on-write buffer ownership,
  managed element destruction, and reclamation through QBE and Wasm
  (`done.md` §2). Immutable `bytes` concatenation, lexicographic comparison,
  and ownership-retaining `slice[u8]` views are complete through both semantic
  oracles, QBE, and Wasm (`done.md` §2). Immutable `str` now shares that owned
  buffer substrate; escaping concatenation, scalar length and iteration, and
  deterministic scalar ordering are complete through the same gates. Ordinary
  and raw text, character, and byte spellings now pass through one linear,
  target-independent semantic decoder with the complete escape vocabulary.
  Triple-quoted text and bytes now use one formatter-owned normalization pass:
  the closing delimiter establishes the space baseline, physical line endings
  become LF, and escape decoding happens only after trimming. HIR therefore
  receives the same canonical immutable value as an ordinary spelling and no
  triple-specific node survives the source boundary. Cycle-aware
  structural list/map equality and insertion-ordered maps/sets are complete
  without making runtime or backend callbacks responsible for value
  semantics. The target-neutral affine buffer-builder substrate and formatted
  strings are complete through both semantic oracles, QBE, and Wasm
  (`done.md` §2). Continue with public text/bytes builder APIs, codecs, and the
  rest of the formatter.
  The bytes implementation follows §12.6 for both static and dynamic sources:
  `{BufferOwner, data, length}` keeps literal owners inert and dynamic owners
  retainable without exposing runtime layout. Do not promote the broad §12
  row until every operation has its own conformance
  evidence.
- [ ] **Prism text codec in Luce** (`.prisma` encode/decode) as the first library; the guest request/reply round-trip typed.
- [ ] **The guest itself**: `lucia_main` in Luce, the seed verbs, running under `WasmHost`; a program a non-programmer can read.

### Proving program 2 — the host

- [x] **Core classes with ARC, weak fields, and `deinit`** (2026-08-31).
  Nominal identities stay abstract through HIR and MIR; only backends choose
  payload layout. The semantic analyzer proves complete initialization and
  prevents publication from `init` and resurrection from `deinit`, including
  transitive borrowed receiver helpers. Strong/weak runtime counts, atomic
  weak zeroing, fallible-initializer cleanup, and reverse field destruction
  agree through both oracles, QBE, Wasm, and `examples/classes.luc`.
- [x] **Compiler-known `Weak[T]` values** (2026-08-31). `T` is an exact class
  identity, `Weak(value)` creates no strong edge, copies retain only the weak
  handle, and `get()` atomically returns owned `T?`. Dynamic weak collections,
  stored weak value fields, destruction-time creation from borrowed `self`,
  and C-boundary rejection agree through HIR, MIR, QBE, and Wasm without user
  generic machinery or target layout.
- [ ] **Finish the remaining §11 resource contract.** Direct self-field,
  self-owned collection, stored-closure, immutable-alias, and weak-back-edge
  cases now have a precise negative matrix. `deinit` follows known same-class
  cleanup transitively and emits structured `L1101` advisories only where
  defined/indirect user code can reenter; direct external C cleanup is not
  guessed to be user code. Resource-shape advisories and runtime leak census remain.
  Do not infer ownership from a bare extern/native handle: finish those rules
  when the richer C boundary records owned/borrowed resource semantics.
- [x] **Core managed closures** (2026-08-31). Expression and block closures,
  capture-free elision, explicit value snapshots, default immutable captures,
  shared mutable cells, nested escaping environments, and weak class captures
  agree through HIR, canonical MIR, both semantic oracles, QBE, Wasm, and
  `examples/closures.luc`. MIR retains only typed descriptor/environment
  contracts; physical layout begins in each backend. *Gate passed: capture
  rule.*
- [ ] **Finish the remaining §14 worker contract.** Fallible
  invocation, infallible-to-fallible function lifting, `weak self`, managed
  values in fields/collections, and directly provable stored strong cycles are
  complete (`done.md` §2). The accidental shared-cell advisory now flows as a
  structured, non-fatal analysis result through check, run, compilation, build,
  and CLI presentation; it neither changes valid capture semantics nor prints
  from HIR generation. Sendability closes with workers.
- [x] **Interface values** (2026-08-31). Existential conversion and dynamic
  requirement calls retain nominal interface/conformance identities through
  HIR and target-neutral MIR. The sealed runtime owns erased payload lifetime
  and value COW; class payloads preserve shared identity. QBE and Wasm choose
  their own descriptor/witness encodings, and both semantic oracles plus the
  executable interface example agree on generic interfaces, struct/class/enum
  conformers, nested ownership, returned existentials, mutation, fallibility
  adaptation, and propagation (`done.md` §2).
- [ ] **Finish the remaining generic surface.** Memberwise generic structs,
  enums, and classes, including their owner-parameterized
  value/mutating/lifecycle methods, independently generic instance methods,
  custom initializers and type functions, and concrete conformances are
  complete through both oracles and artifact backends (`done.md` §2).
  Package/CLI budget configuration, immediate infinite-expansion detection,
  source-parent paths, HIR/MIR size, check/codegen timing, backend code-size
  accounting, `luce explain`, and `build --time-report` are also complete.
  Serialized typed bodies in package artifacts remain and belong to the
  package-artifact owner, not HIR or canonical MIR. Keep monomorphization out
  of canonical MIR.
- [ ] **Workers** (`spawn`, tasks, sendability, `wait_all`).
- [ ] **Luce-native backends**, only after QBE is a stable harness column;
  implement one target behind the existing MIR backend boundary, then prove it
  against QBE before adding another.
- [ ] **Native image/link support** after native code generation is justified.
- [ ] **C import (FIIR)** from headers via Clang, for Cocoa/Metal, OpenSSL/Monocypher, wasm3 during transition.
- [ ] **Wasm engine in Luce**: decoder + validator + interpreter with fuel at back-edges and calls; differential-tested against `wasmtime`; then the compiler tests drop `wasmtime`.
- [ ] **Host slices**: storage journal + acceptance rule → crypto → terminal headless shell → `WasmHost` running proving program 1 → realm/network → UI/Metal.
- [x] **`luce build --time-report` for generics** (2026-08-31). Report source
  expansion paths and front-end cost before backend selection, then join
  optimized MIR size and backend-local function emission bytes/time by
  concrete executable identity (`done.md` §2).
- [ ] **`luce api diff`** and **`luce describe`** as compiler products.
- [ ] **Fuel/preemption as a wasm backend option** (when guests need it and the engine is not ours).

### Self-hosting and compile speed

- [ ] Compiler builds itself under the Stage-0-subset rule; one pinned prior compiler kept forever for bootstrapping; bootstrap reproducibility checked in CI.
- [x] **Dialect gap closed 2026-08-29 — our sources are legal in both compilers.** The tree is written in Stage-0's dialect, and the two spellings that differed from the 1.0 spec were resolved in the spec's favour of Stage-0: file-scope `const` became `let` (247 sites), and the named argument became `name = value` in the spec (§8.2), the parser, and every example and fixture. `=` won over `:` because `:` already means *has this type*; using it for *takes this value* put two relations behind one mark exactly where a reader confuses them (`Point(x: 10.0)` beside `x: f64`). Nothing else in the tree is known to differ; confirm by feeding our own sources to our own parser once it can parse them all.
- [ ] **Measure first**: lines per second of the compiler compiling itself, before any layout work. Stage-0's codegen and ARC dominate until then, so layout changes are invisible before this point.
- [x] **Data-oriented layout — shape now, tuning at the measurement.** (Items 1–5 done; 6 waits for the measurement.) Decided 2026-08-28 (`done.md` §2 for what landed): (1) ~~ids to `u32`~~; (2) ~~MIR as a flat instruction array with `Else`/`Case`/`Default`/`End` markers~~; (3) ~~spans as four `u32`s~~; ~~(4) HIR as one flat node table~~ done 2026-08-28: `HirProgram.nodes: list[HirNode]` stored inline, `HirNode.form` keeps the named union payload so `match` stays, children are `NodeId(u32)`, child lists are `Operands{start, count}` into `HirProgram.extra`, literals in `values`, and the two cold fields live in parallel arrays (`node_spans`, `node_types`) so a node is tag + payload; ~~(5) MIR operand lists as `RegisterRun`s into `MirFunction.operands`~~ done 2026-08-28; (6) tiny tokens and a flat syntax tree only if the front end shows up in the self-hosting measurement — both are walked once, unlike HIR and MIR. **Why this shape and not Zig's `{tag, lhs, rhs}`**: Zig's readability in that form is generated by `comptime`, which Luce does not have; a union payload with named fields gives the same contiguity and, with the cold fields split out, the same density, while keeping pattern matching. Going to the raw form later is mechanical because every link is already an index. Generic structure-of-arrays is a library/tooling question (hand-written for the hot tables, or generated from `luce describe`), never a reason to add compile-time execution.
- [x] **Decompose stable pass ownership before large files become permanent.**
  Give every cohesive source/test region a `# mark:` heading as it is touched.
  File length is reviewed at each vertical-slice audit; roughly 2,000 lines
  triggers an ownership review, not an arbitrary mechanical split. Wasm
  module planning has its own owner, leaving the related instruction/section
  encoder cohesive at 2,305 lines; its byte plumbing is
  too small to justify another module today.
  HIR generation now separates program declarations from mutually recursive
  body semantics over one typed transaction. MIR lowering separates the
  whole-program coordinator and shared identity/type transaction from one
  cohesive function walk. Neither split duplicates pass state or introduces
  forwarding-only collaborators. Generic callables established a further
  honest boundary: abstract probing, structural inference, and concrete
  function/method specialization live in `hir/generics/functions.luc` and
  borrow a narrow semantic interface without duplicating the generation
  transaction. The 2,671-line declaration collector now owns one cohesive,
  marked interface declaration/conformance section because it directly shares
  name, type, method, visibility, generic-specialization, and adapter
  resolution; its generic-conformance threshold review found that splitting
  it today would create a forwarding cycle rather than a new owner.
  Existential representation and dynamic calls established the focused
  108-line `hir/interfaces/values.luc` owner rather than extending the
  declaration collector. Standard protocol identity and iteration selection
  established sibling 137- and 210-line owners. Structural marker use adds a
  focused 57-line sibling. The remaining 3,013-line HIR body checker and
  5,206-line MIR function lowerer stay intact after the cfunc review above;
  the lowerer's next major slice must include another transaction-boundary
  review. The 3,048-line HIR interpreter likewise remains one semantic state
  machine: expression evaluation,
  mutable-place access, calls, and control transfer recurse through each
  other, while their stack-heavy arms already live in focused helpers.
  The class audit found no such seam: lifecycle semantics are inseparable from
  the same expression/place/call transaction, and a class-only helper would
  be forwarding rather than ownership. The 2,001-line MIR interpreter reached
  the same review threshold in the incoming-cfunc slice: host contracts,
  logical extern-memory writes, instruction execution, and backend-owned
  layout form one oracle boundary, while region planning and value helpers are
  already marked independent sections. Splitting only the public host
  contracts would create another data-only forwarding module. Line count
  alone does not. Parser
  grammar is already frozen; separate its
  byte/token plumbing only where one owner can retain the cursor and
  diagnostic state.
- [ ] **Bound recursion the way shipping compilers do** — [`recursion.md`](recursion.md) §4. Phase 1 (a 256-deep cap on expression nesting) landed 2026-08-29; phases 2–5 remain: `frame_limit` derived at startup from the host rather than declared, thinner interpreter frames, and a stack reservation on the ELF path. Statement and type nesting have their own recursions and are **unmeasured** — no evidence they crash, so they wait for evidence rather than a speculative counter.
- [ ] Generated programs and fuzzing as release gates (not yet built; do not claim them).
- [ ] Language freeze after the compiler and one host slice depend on every feature.

### Deferred by decision (do not start without new evidence)

- System profile (atomics, volatile, interrupt ABIs, drivers): bare metal is a non-goal; runtime threading stays in `libluce_rt` via C interop.
- Effects / `uses` clauses: removed (spec §18). Authority is a capability *value* from the platform; operational facts are compiler-internal summaries, never in function types.
- Native rung 3, transactional heap, general effect rows, dependent types, macros, reflection, compile-time execution, incremental binary patching.

## 6. Decision gates and standing rules

Gates — settle in `1.0.md` before the feature lands in `hir_gen`:

| Gate | Before | Evidence |
|---|---|---|
| ~~Fallible iteration protocol (item / end / error, propagation visible at the loop)~~ | `for` | **met**: `try for` + `FallibleIterable[T]`, `next() -> T?!` (spec §§9.4, 17.1) |
| Owned (non-copyable, consuming) values — state transitions, destruction on every exit | classes / ARC | keys wiped in destructors, guest handles, journal lock fd |
| Scoped values generalised from `mutable_slice`/`task` | closures | borrowed `const Element*`, `thread_local const char*` |
| Closure capture: explicit vs §14.1 implicit shared cell, by the both-ways corpus test | closures | the compiler and all three C++ repos are closure-light corpora |
| ~~Whether 1.0 has general const generics~~ | generics | **met**: §15.4 excludes them; `array[T, N]` is the sole compiler-built fixed value parameter |
| ~~`hir_gen` keeps doc comments, parameter names, defaults~~ | structs | **met** (`done.md` §2) |

Standing rules:

- **Indices, not pointers, across stages.** Every program-wide table (`types`, `symbols`, `structs`, `functions`, `data`, registers, slots, and — once §5 item 4 lands — HIR nodes) is addressed by a `u32` id into a flat list; no stage hands another a pointer graph. New tables follow this. A `u32` id indexes a table directly since Stage-0 0.26; the `i64(...)` widening every index site used to carry is gone (98 of them, 2026-08-29).
- **Layout truth comes from C1, not Stage-0.** Whether Stage-0 stores a `list[struct]` with a union payload inline is unknown and does not matter: our own `make_struct_type`/`make_enum_type` lay them out inline, so the shapes chosen now become real memory when the compiler compiles itself. Of the three Stage-0 conveniences worth requesting, two landed in 0.25–0.26 (any-integer indexing, `match` arms naming several members); inline storage remains, and blocks nothing but a measurement before C1.
- One source for wasm and native, with a module system that can *exclude* code rather than stub it, is a language requirement.
- `assert` traps in every build and its condition is effect-free; checks are removed only by proof.
- Never claim testing that is not running.
- Phases 2–6 of `vision.md` reuse Prism `Compose`/`EventLog` and the journal rather than reinvent snapshot/patch/intent; "patch" and "proposal" as a guest-facing API are the first thing the Luce guest library provides.

## 7. Cautionary tales (Bun's Rust rewrite, Kelley's reply, Cro's essays)

| Lesson | Rule for Luce |
|---|---|
| Bun's use-after-free/double-free/leak catalogue clustered at the GC↔manual-memory seam; ownership there was a style guide | Ownership across every seam is compiler knowledge: generated C bindings carry ownership and nullability, the guest ABI passes values and lengths, errors cross as data |
| Kelley: bugs are removed by engineering time, not by the language-vs-style-guide framing; Bun claimed fuzzing it wasn't doing | The harness is real; fuzzing is listed as future work, not current practice |
| A `debug_assert!` with a side effect broke hot reload; disabled asserts "gaslight you" | Asserts trap in every build, conditions are effect-free (spec §13.8) |
| Port regressions were semantic drift (`trunc` vs `floor`, debug/release bounds checks) | Semantics settled by the spec in the HIR interpreter first; identical in every profile |
| `comptime` abuse needed a time report; LTO/binary-size wins were overdue engineering | No compile-time execution; monomorphization budgets; `--time-report` on the tooling list; whole-program MIR makes LTO free |
| 64 concurrent AI instances, "hacks on top of hacks", drive-by AI PRs | Small green commits, the harness as gate, readability audits, honest plan entries; a contributor policy before the first outside PR |
| Upstream relationship (ZSF) decayed | Stage-0 is our upstream: reproductions with `run.sh`, workarounds removed when fixes ship |
| The language was not Bun's problem; values and effort were | Luce's claim is that the seams are unenforceable in C++ and a language can enforce them; the proof is the proving programs passing the harness |

## 8. Stage-0 constraints

The compiler must stay buildable by Stage-0 (the frozen seed) until it builds
itself. Stage-0 0.30 is pinned by the published checksums for both supported
hosts; the release was built from source commit
`a5c3a099de3631024e739093066a4df388706b6f`. Remaining constraints:

- Reserved identifiers (`error`, `bytes`, `i8`…, `pass`, `never`), and no top-level function sharing a name with a pattern binding.
- A dropped result is an error (`luce.sema.unused`): write `discard(...)` around a value nothing receives, with any `catch` outside it — `discard(risky()) catch reason:`.
- Divergence must be declared `-> never`; a fallible helper still reads `error(...)` inline, and a `-> !` call is not a diverging arm.
- Mixed-width arithmetic still needs an explicit conversion (`u32` + `i64` is refused), so the eight compound index expressions keep their `i64(...)`. Indexing itself no longer does: a `u32` id indexes a table directly.
- Stack, not frame count, is the real recursion limit — see §8.1 — and since 0.26 the ceiling also depends on the build mode; `recursion.md` §3 has the numbers.
- Lifted in 0.26, do not re-introduce the workarounds: `i64`-only indexing, bare `pub name: T` fields, file-scope `const`, single-member match arms, and the absence of `pass`/`never`/`list[T?]`.
- Rule: reproduce a suspected Stage-0 defect as a standalone program and confirm it fails on the installed `luce-0` before reporting or working around it. History in `done.md` §5.
- There are no open Stage-0 requests. Stage-0 0.30 closed the remaining stack
  exhaustion report; the historical request and reproductions remain in
  [`stage0-0.26.md`](stage0-0.26.md) and `build/stage0-0.25-repro/`.

### 8.1 The depth budget is a stack budget

Stage-0 advertises 1,000,000 frames on a 512 MiB stack. That pairing assumes
about 512 bytes per frame, which compiler-shaped code does not obey, so the
advertised count alone is not the number to plan against. Stage-0 0.30 closes
the safety gap: every generated function also checks a host-provided stack
floor with a 256 KiB diagnostic reserve, including functions entered through
`cfunc` callbacks and ARC deinitializers. The count keeps thin recursion
deterministic; the floor catches fat frames first.

Measured on 0.25/arm64-macOS (method: bisect the depth at which a built program takes SIGBUS, then divide the 512 MiB reservation by it):

| shape | bytes per frame | frames before the guard page |
| --- | --- | --- |
| 2-arm match building a value struct | 715 | ~750,000 |
| 10-arm | 2,664 | ~201,000 |
| 30-arm | 8,343 | ~64,000 |
| one HIR-interpreter call (six host frames) | ~32,000 | ~16,600 |

The cost is linear in the number of match arms that build a value struct —
about 270 bytes per arm, never reused across arms that cannot both run. Before
0.30, passing the measured ceiling took SIGBUS because the frame counter never
fired. The 0.30 release's published reproduction now reports
`call_depth_exceeded` before the guard page.

Consequences we hold to: both interpreters still cap at `frame_limit = 2000`,
a sixfold margin under the measured fat-callee ceiling of 12,875 and above the
deepest fixture (`down(1500)`). That language-level limit remains deterministic
while Stage-0's independent floor makes a wrong estimate safe. Re-measure when
the reservation or interpreter shape changes. Historical reproduction:
`build/stage0-0.25-repro/`.

### 8.2 What everyone else does, and where we are short

Checked against the implementations rather than argued from first principles.

| | stack | declared limit | probes the stack pointer |
| --- | --- | --- | --- |
| Clang | 8 MiB, raised by `setrlimit` at startup | bracket depth 256, template depth 1024 | yes — warns, then continues on a fresh stack |
| Swift | 8 MiB, the OS default | parser nesting 256, fatal | no — the cap is what keeps it safe |
| rustc | 16 MiB on a *spawned* thread, for control over the size | `recursion_limit` 128 | no longer — it now lets the OS handle growth |
| Zig | 46 MiB for the compiler, 60 MiB per worker | none in the parser | no — and deep nesting segfaults, filed as urgent |
| CPython | 16 MiB linked on macOS, 64 MiB under sanitizers | 1000 Python frames | yes, since 3.14, against queried stack bounds |
| Luce seed (Stage-0 0.30) | 512 MiB | 1,000,000 host frames plus our `frame_limit` 2000 | yes — host-provided floor |
| Luce QBE/Wasm output | host policy through QBE; 1 MiB Wasm shadow stack | source recursion limits remain open | Wasm yes; QBE native no |

Three patterns hold across all of them. A declared count limit exists so the error is deterministic across machines. The safety factor on that count is ten to a hundred, not the six we run, because per-frame cost depends on the input's shape. And the ones that degrade gracefully rather than crashing all probe the stack pointer; the one that does not, Zig, has an open urgent bug for exactly the crash we reproduced.

Where we are short, in the order it will bite. The design record that turns this list into work is [`recursion.md`](recursion.md):

- ~~The front end has no nesting guard.~~ **Closed 2026-08-29.** Expression nesting is capped at 256; 26,250 nested parentheses used to take SIGBUS. Statement and type nesting are still unguarded and still unmeasured.
- **`frame_limit` is declared, not derived.** It is right for Stage-0's 512 MiB
  host and unproven for executables linked by the QBE host toolchain. Stage-0
  0.30 proves the portable input is a host-provided floor, not a platform query;
  our runtime must carry the equivalent fact when Luce owns the native path.
- **32 KiB per interpreted call is eight to thirty times the norm** (a lean tree-walker spends 1–4 KiB). It is Stage-0's per-arm slot inflation in our wide `match` walkers. Thinner frames are a linear multiplier on depth that costs no address space, which is why this is the fix rather than a bigger constant.
- **The QBE baseline inherits the host stack policy.** Stage 1 deliberately
  does not rebuild linker/loader policy around the oracle. An explicit stack
  contract belongs to the later runtime and Luce-owned backend project.

## 9. Conventions worth keeping

- Every source file opens with a header that says what it is, why, where it sits, and how to read it; `# mark:` sections follow the header's promised order; comments explain *why*; magic numbers get a mnemonic or field name beside them.
- `README.md` → `docs/README.md` → `1.0.md` (spec, not status) → `examples/` → `tests/` is the reading order; the README's "What works today" is the single definition of the implemented slice.
- Diagnostics: `path:line:column: message` from the front end, a stage prefix (`interpreter:`, `MIR verifier:`, `executable:`, `<target> backend …`) from later stages; unsupported input never traps.
- Errors from every stage reach the CLI as text with exit 1; usage errors exit 2 (`tests/cli_test.sh` pins this).
- Commits: short plain lowercase messages after each green step.

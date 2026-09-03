# Compiler plan and decision record

This is the plan half of the compiler's planning pair: the decisions behind
the design and the work still ahead, written so work can resume from it
without the conversations that produced it. The other half,
[`done.md`](done.md), records what exists, what each milestone proved, the
bugs the harness caught, and where the project came from. `mir.md` explains
the machine representation in depth. Update this file when a decision
changes. Checked items stay here only when their condensed decision or
dependency context is needed to understand the remaining sequence;
`done.md` owns the full evidence. Do not let either drift into a wish list.

Last updated: 2026-09-03 (Stage-0 0.30).

## Current resumption snapshot

The only active development line is `stage1-qbe`. Its purpose is the complete
Luce 1.0 source-to-QBE checkpoint: one target-neutral HIR and canonical MIR,
three agreeing semantic/artifact executions, executable examples for every
demonstrable capability, and stable diagnostics for every deliberate
rejection. Do not merge the superseded native-backend work from `main`, and do
not begin a Luce-owned machine backend before this checkpoint is complete and
audited.

The repository currently proves 968 compiler tests across 36 files, plus the
CLI, Wasmtime, QBE differential, and host-native gates. The latest FIIR slice
imports direct pointers to typedef-backed incomplete C records as nominal raw
handles without introducing C layout or platform facts into HIR or MIR. The
next implementation slice is **S21 binding recipes and safe wrapper
ownership**, beginning at the unchecked row under “Complete C import (FIIR)”
below.

There are three deliberately non-overlapping sources of truth:

1. [`done.md`](done.md) records only committed, full-gate-green behavior and
   the evidence behind it.
2. This file records architecture decisions and implementation order. Within
   it, the nested FIIR list below is the exact S21 order.
3. [`../../examples/FEATURES.md`](../../examples/FEATURES.md) is the normative
   section-by-section conformance ledger. Its “Exact open stage-1 checklist”
   is the exhaustive blocker list for the 1.0 source-to-QBE checkpoint.

At this snapshot the open blocker groups are:

| Order | Ledger IDs | Work remaining |
| --- | --- | --- |
| 1 | S21, S23, S24 | Finish FIIR recipes and declaration vocabulary, resolve the extern-struct grammar contract, and enforce callback runtime/thread rules. |
| 2 | S12, S13, S30 | Finish public text/bytes/codecs and required runtime services, complete error/trace/fatal diagnostics, and run the remaining proving examples through QBE. |
| 3 | S02, S26, S27 | Implement source `test` semantics and isolation, then close its namespace rules, required command modes, structured diagnostics, and canonical formatting. |
| 4 | S01, S28 | Close the naming/style audit and map every deliberate exclusion to a stable negative fixture. |
| 5 | S29 | Compile the compiler with stage 1, compare observable behavior, and preserve the frozen bootstrap chain. |
| 6 | all rows | Run the final conformance, architecture, ownership, file-size, performance, examples, and multi-backend audit; then pause for review. |

The longer proving-program and host roadmap in §§4–5 is design context, not an
implicit expansion of this checkpoint. A task there blocks 1.0 only when the
conformance ledger names it (currently through S30). The Wasm engine, complete
host application, Luce-owned native backends, image/link writers, persistent
services, and post-1.0 packaging/release work explicitly begin after the
source-to-QBE review.

Local milestones use brief commit subjects and the sole author/committer
`Dy Mokomi <dy@dymokomi.com>`. Keep the branch local until Dy explicitly asks
for a push.

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

## 5. Active roadmap

This section intentionally contains open work only. Completed implementation
and proof belong in [done.md](done.md); the conformance ledger identifies the
normative gap. Architecture decisions that constrain future work remain in
§§2–3 and §6 rather than masquerading as unfinished tasks.

### 5.1 Source-to-QBE closure order

- [ ] **S21 — finish C import through FIIR.** Follow the dependency plan in
  §5.2. Every slice must preserve one target-neutral HIR/MIR shape and prove
  generated raw source, both semantic oracles, Wasm encoding where applicable,
  and real linked QBE/C execution.
- [ ] **S23 — settle the extern-struct grammar contract.** Resolve the
  field-only grammar versus richer prose conflict in the language document,
  then close the resulting positive/negative matrix without creating a second
  nominal-record implementation.
- [ ] **S24 — enforce callback runtime and thread rules.** Complete the
  remaining C-export callback matrix using the existing exact cfunc identity.
  Context, lifetime, thread entry, and runtime attachment must be explicit
  recipe/runtime contracts, not backend guesses.
- [ ] **S12/S30 — finish the standard/runtime surface required by the
  examples.** Public text and bytes builders, UTF codecs, numeric
  parsing/formatting policy, remaining arena/pool/generational-handle
  contracts, automatic standard-module loading, required host libraries, and
  source-test resource reports remain. Existing lists, maps, sets, immutable
  strings/bytes, affine internal formatting, classes, tasks, and explicit
  standard-source provenance are the proven foundation.
- [ ] **S13 — close errors, fatal outcomes, and diagnostic provenance.** Add
  error context/source traces, structured fatal reporting, complete trap source
  locations, and the remaining stack-budget reporting. Finish the measured
  recursion work in [recursion.md](recursion.md) only where evidence identifies
  an unsafe recursive owner.
- [ ] **S26/S02 — implement source tests and their scopes.** Lower source
  test declarations through HIR/MIR into an isolated registry and runner;
  implement test-only import pruning, selection/reporting, and
  testing.expect_trap; then close the namespace/lifetime matrix that depends on
  that model.
- [ ] **S27/S01 — finish the first-party command and formatting contract.**
  Complete the required command modes, structured diagnostic/fix shape,
  canonical formatter, and naming/style diagnostics. The existing check, run,
  and build core is not the complete §24 contract.
- [ ] **S28 — prove every deliberate exclusion.** Give each §25 exclusion a
  stable negative fixture at its first rejecting stage; absence of an
  implementation is not evidence.
- [ ] **S29 — prove self-hosting and the bootstrap chain.** Compile the compiler
  with stage 1, compare observable behavior with the pinned Stage-0 0.30 build,
  retain one prior compiler forever, and measure source throughput before any
  speculative representation tuning.
- [ ] **Add generated-program and fuzzing gates.** Run deterministic generated
  valid/invalid programs through the same HIR/MIR/QBE triangle, record seeds,
  minimize failures, and never claim coverage that is not executing.
- [ ] **Perform the final checkpoint audit and pause.** Reconcile every
  conformance row, run every example and diagnostic gate, inspect ownership and
  lifecycle seams, re-run the no-platform-before-backend check, review large
  files and pass boundaries, measure the compiler, and run the complete test
  suite. Then stop for Dy's review before changing main or beginning another
  backend.

### 5.2 FIIR dependency plan (S21)

The proven baseline is recorded in [done.md](done.md): C Boolean, every
fundamental integer, exact IEEE binary16/32/64 values, the supported binary64
long-double model, scalar typedef chains, open named/typedef-backed enums,
constant-only anonymous enums, plain nested records, header-local scalar/enum
constants, selected scalar macros, live scalar/enum objects, fixed functions,
and direct pointers to typedef-backed incomplete records all pass Clang facts
through deterministic FIIR/raw/C products, both semantic oracles, Wasm, and
linked QBE/C. The most recent handle rung retains nullability, pointee
mutability, origin, and unspecified ownership/lifetime; typed pointers and
layout terminate in the C adapter.

Unsupported declarations must continue to fail before HIR rather than acquire
an approximate carrier. Resume in this order; each row is one independently
committable vertical slice and updates the spec, examples, conformance ledger,
and diagnostics with its tests:

- [ ] **Binding recipes and safe wrapper ownership.** Separate facts Clang
  proves from facts a recipe supplies. Generate nullable, borrowed-for-call,
  returned-borrow, owned-plus-disposer, and status/error wrappers. Missing safe
  ownership facts are generation errors; only the audited raw layer may retain
  explicit “unspecified” facts.
- [ ] **Complete opaque-handle spellings and directions.** Add direct tagged
  struct pointers, pointer typedef chains, const/read-only results, and
  pointer-to-pointer/out-handle forms on the recipe model. Prove a SQLite-style
  T-double-pointer output plus disposer without a general raw pointer in HIR or
  MIR.
- [ ] **Pointer-plus-count arrays and strings.** Map borrowed inputs, writable
  call-scoped outputs, count/capacity/writeback relations, C-string copies, and
  owned returned buffers onto the existing target-neutral list, slice, bytes,
  string, and foreign-memory contracts. Arrays in records and returned storage
  stay closed until ownership is explicit.
- [ ] **Imported function pointers and callbacks.** Decode exact Clang
  signatures into the existing cfunc model, including nullable slots and
  context/lifetime recipes, then close S24's runtime/thread enforcement.
- [ ] **Unions, bit-fields, and aggregate storage.** Prefer generated C thunks
  with logical Luce carriers; never copy C byte layout into HIR/MIR. Admit
  aggregate constants/objects only with complete value and writeback semantics.
- [ ] **Atomic and thread-local objects.** Require explicit operation and
  execution-domain recipes. Neither qualifier may become an ordinary shared
  load/store.
- [ ] **Pointer, array, and string macro constants.** Reuse the completed
  storage/ownership carriers and keep Clang as the sole evaluator of
  preprocessing and constant semantics.
- [ ] **Typed variadic adapters.** Generate fixed, checked C thunks from an
  explicitly requested signature; no untyped vararg operation enters Luce,
  HIR, or MIR.
- [ ] **Extended floating carriers.** Define a lossless logical carrier before
  admitting any non-binary16/32/64 target model. Narrowing remains forbidden.
- [ ] **Support tiers and deterministic regeneration diagnostics.** Record why
  each declaration is direct, thunked, recipe-dependent, or unsupported;
  compare regenerated products structurally and report stable declaration
  origins. Freeze the FIIR format only after the vocabulary is represented;
  no backward-compatibility layer is required while the project is in building
  mode.

### 5.3 Constraints while closing the checkpoint

- Keep the shared frontend, HIR, canonical MIR, verifier, optimizer, and
  lowerer free of target names, pointer widths, byte layouts, ABI classes, and
  platform policy. QBE, Wasm, and later native backends begin from the same MIR.
- Add a # mark: section heading whenever a touched file gains a distinct
  cohesive region. Roughly 2,000 lines triggers an ownership review. Split only
  at a real state/transaction boundary; a forwarding-only file is not a
  refactor.
- Extend the freestanding Luce runtime only when a remaining semantic service
  needs it. Runtime discovery must not embed checkout paths or platform
  syscalls in the compiler; automatic installed-toolchain discovery remains
  part of S30.
- Every source feature needs positive and negative frontend/HIR coverage,
  independent HIR and MIR execution, optimized QBE execution, a focused example
  when demonstrable, and Wasm evidence where the existing backend naturally
  supports it.
- Keep small green commits with the sole author/committer
  Dy Mokomi <dy@dymokomi.com>, and do not push without explicit instruction.

### 5.4 Explicitly after the source-to-QBE review

These are real project goals, but they do not extend the current completion
contract unless the conformance ledger explicitly promotes one:

- Luce-owned native backends, one target first, proved against QBE before a
  second target;
- native image/link writers after native code generation justifies them;
- a Luce Wasm decoder/validator/interpreter and the complete host application;
- storage, crypto, terminal, realm/network, UI/Metal, and the full guest/host
  proving products beyond the examples required by S30;
- luce api diff, luce describe, and optional Wasm fuel/preemption;
- post-1.0 package, cache, profile, persistent-service, documentation, and
  release-policy work.

Do not freeze the language or add backward-compatibility machinery until Dy
explicitly ends building mode. Also keep the standing deferrals: no bare-metal
system profile, effects/uses clauses, dependent types, source macros,
reflection, compile-time execution, transactional heap, or incremental binary
patching without new evidence and a deliberate plan change.

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

- **Indices, not pointers, across stages.** Every program-wide table (`types`, `symbols`, `structs`, `functions`, `data`, HIR nodes, registers, and slots) is addressed by a `u32` id into a flat list; no stage hands another a pointer graph. New tables follow this. A `u32` id indexes a table directly since Stage-0 0.26; the `i64(...)` widening every index site used to carry is gone (98 of them, 2026-08-29).
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

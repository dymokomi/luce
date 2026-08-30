# Compiler plan and decision record

This is the plan half of the compiler's planning pair: the decisions behind
the design and the work still ahead, written so work can resume from it
without the conversations that produced it. The other half,
[`done.md`](done.md), records what exists, what each milestone proved, the
bugs the harness caught, and where the project came from. `mir.md` explains
the machine representation in depth. Update this file when a decision
changes; move items to `done.md` when they are ticked. Do not let either
drift into a wish list.

Last updated: 2026-08-30 (Stage-0 0.28).

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
planned source feature passes the frontend/HIR/MIR/QBE/Wasm gates, audit the
finished branch as a whole, make that history the new local `main`, and pause
before beginning Luce-owned native backends.

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
3. a compiled artifact — wasm under `wasmtime`, and native through pinned
   QBE 1.3 for the complete current lowerer corpus.

When two agree and one differs, the stage between them is wrong. Every
lowerer slice adds fixtures to `differential_test.luc` *and* the same
programs to `tests/wasm_test.sh`, plus programs that must trap on all
three. The triangle has found six real bugs so far (`done.md` §3), four of
them in "reference" implementations. Keep it.

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
- **Runtime as symbols** (`luce_rt_*`), never instructions. wasm imports them; native links `libluce_rt`.
- **Failure as data with explicit ownership**: a fallible function receives a caller-owned `Error` slot as hidden parameter 0 and returns `(value, null)` on success or `(absent, error_out)` on failure. `try` is a call plus one conditional branch; propagation copies into the current function's slot after active `defer`s; no allocation or unwinding.
- **Semantics fixed in MIR**: `Add` means checked add; `floor_div`/`rem` are floor semantics; shifts trap on count, drop bits shifted out. Checks are removed only by proof, never by build mode.
- **Not in MIR**: generics (monomorphized), closures (env struct + function), interfaces (data pointer + witness table), names.
- **`Yield`** is the structured phi: a region that produces values names them on every exit.
- **Narrow integers stay MIR types** (Prism `DType` and the C ABI need exact widths).
- **Open**: optionals are a uniform `u8`-tagged enum today; whether future
  managed class references may use a null niche is undecided. Pointer-shaped
  foreign handles are settled: tagged internally and raw-null only at a C
  boundary. Fallible ABI is per backend (wasm multi-value, QBE
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
- [x] **QBE product materialization** (2026-08-30): `--target native` streams
  canonical-MIR-derived IL into QBE and QBE assembly into the host C driver.
  Only the linked candidate touches disk, inside an atomically unique,
  owner-only directory beside the output; same-filesystem rename installs it
  atomically. QBE and linker stderr become explicit diagnostics, failed builds
  preserve the prior artifact, and the product path owns no `.ssa` or `.s`
  files. The complete differential corpus and native smoke gate use this path.

- [x] **Enums and `match`** (2026-08-28, `done.md` §2). `Switch` is still unused by the lowerer: `match` is an `If` chain, because a wasm `Switch` needs `br_table` plumbing that breaks the one-region-one-label invariant; jump tables come with the native pass.
- [x] **`for` and integer ranges** (2026-08-29, `done.md` §2). The fallible-iteration gate is settled: ordinary `for` uses `Iterable[T]`; `try for` uses `FallibleIterable[T]`, whose `next()` answers `T?!`. Built-in `range[T]` values and infallible range iteration run through all three executions now. User-defined protocol dispatch waits for interfaces/generics; executable `try for` waits for the next failure-as-data slice.
- [x] **`defer`** (2026-08-29, `done.md` §2). Receiver and arguments are captured at registration; lexical cleanup is LIFO and runs on fallthrough, `return`, `break`, and `continue`, but not traps. The lowerer duplicates cleanup calls at each ordinary exit, ready for error propagation to become one more exit edge.
- [x] **`try`/`catch`, `Error`** (2026-08-29, `done.md` §2). `T!` is an outer function-result effect, `ErrorCode` carries explicit package identity, calls use caller-owned Error slots, and propagation/recovery run active `defer`s. Scalar, unit, aggregate, conditional, and match-produced fallible values pass the three executions.
- [x] **Custom struct `init`** (2026-08-29, `done.md` §2). Construction has an explicit HIR identity; `SemanticAnalyzer` proves every successful path initializes each field exactly once before `self` is read or escapes; fresh caller-owned receiver storage composes with the ordinary `T!` error-slot path.
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
  `malloc`/`free` execution prove both handle representations. Strings, extern
  structs and variables, exported structs/enums, and `cfunc` remain on this
  item.
- [ ] **Dead-function reachability pass** on MIR from the entry and exports (small; smaller artifacts; the first "never compile what isn't reached" step).
- [ ] **`libluce_rt` in Luce, freestanding**: bump/free-list allocator over linear memory, `write`, `trap`, string/bytes primitives; through the MIR interpreter's stub runtime first, then compiled.
- [ ] **Lists, maps, sets and strings via the runtime**; formatted strings.
- [ ] **Prism text codec in Luce** (`.prisma` encode/decode) as the first library; the guest request/reply round-trip typed.
- [ ] **The guest itself**: `lucia_main` in Luce, the seed verbs, running under `WasmHost`; a program a non-programmer can read.

### Proving program 2 — the host

- [ ] **Classes with ARC, weak references, `deinit`** — `SemanticAnalyzer` starts producing ownership facts. *Gates: owned values; scoped values.*
- [ ] **Closures.** *Gate: capture rule.*
- [ ] **Interfaces** (data pointer + witness table) and **generics** (monomorphization, memoized per instantiation, with a budget). *Gate: const-generic grammar.*
- [ ] **Workers** (`spawn`, tasks, sendability, `wait_all`).
- [ ] **Luce-native backends**, only after QBE is a stable harness column;
  implement one target behind the existing MIR backend boundary, then prove it
  against QBE before adding another.
- [ ] **Native image/link support** after native code generation is justified.
- [ ] **C import (FIIR)** from headers via Clang, for Cocoa/Metal, OpenSSL/Monocypher, wasm3 during transition.
- [ ] **Wasm engine in Luce**: decoder + validator + interpreter with fuel at back-edges and calls; differential-tested against `wasmtime`; then the compiler tests drop `wasmtime`.
- [ ] **Host slices**: storage journal + acceptance rule → crypto → terminal headless shell → `WasmHost` running proving program 1 → realm/network → UI/Metal.
- [ ] **`luce api diff`** and **`luce describe`** as compiler products; `luce build --time-report` once generics exist.
- [ ] **Fuel/preemption as a wasm backend option** (when guests need it and the engine is not ours).

### Self-hosting and compile speed

- [ ] Compiler builds itself under the Stage-0-subset rule; one pinned prior compiler kept forever for bootstrapping; bootstrap reproducibility checked in CI.
- [x] **Dialect gap closed 2026-08-29 — our sources are legal in both compilers.** The tree is written in Stage-0's dialect, and the two spellings that differed from the 1.0 spec were resolved in the spec's favour of Stage-0: file-scope `const` became `let` (247 sites), and the named argument became `name = value` in the spec (§8.2), the parser, and every example and fixture. `=` won over `:` because `:` already means *has this type*; using it for *takes this value* put two relations behind one mark exactly where a reader confuses them (`Point(x: 10.0)` beside `x: f64`). Nothing else in the tree is known to differ; confirm by feeding our own sources to our own parser once it can parse them all.
- [ ] **Measure first**: lines per second of the compiler compiling itself, before any layout work. Stage-0's codegen and ARC dominate until then, so layout changes are invisible before this point.
- [x] **Data-oriented layout — shape now, tuning at the measurement.** (Items 1–5 done; 6 waits for the measurement.) Decided 2026-08-28 (`done.md` §2 for what landed): (1) ~~ids to `u32`~~; (2) ~~MIR as a flat instruction array with `Else`/`Case`/`Default`/`End` markers~~; (3) ~~spans as four `u32`s~~; ~~(4) HIR as one flat node table~~ done 2026-08-28: `HirProgram.nodes: list[HirNode]` stored inline, `HirNode.form` keeps the named union payload so `match` stays, children are `NodeId(u32)`, child lists are `Operands{start, count}` into `HirProgram.extra`, literals in `values`, and the two cold fields live in parallel arrays (`node_spans`, `node_types`) so a node is tag + payload; ~~(5) MIR operand lists as `RegisterRun`s into `MirFunction.operands`~~ done 2026-08-28; (6) tiny tokens and a flat syntax tree only if the front end shows up in the self-hosting measurement — both are walked once, unlike HIR and MIR. **Why this shape and not Zig's `{tag, lhs, rhs}`**: Zig's readability in that form is generated by `comptime`, which Luce does not have; a union payload with named fields gives the same contiguity and, with the cold fields split out, the same density, while keeping pattern matching. Going to the raw form later is mechanical because every link is already an index. Generic structure-of-arrays is a library/tooling question (hand-written for the hot tables, or generated from `luce describe`), never a reason to add compile-time execution.
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
| Const-generic grammar `[T, const n: u64]` reserved in the parser | generics | `Spectrum` = 32 inline floats, fixed guest buffers |
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
itself. Stage-0 0.28 is pinned by the published checksums for both supported
hosts; the release was built from source commit
`d5b458355179c059ce9c506c37990612c2c8f68f`. Remaining constraints:

- Reserved identifiers (`error`, `bytes`, `i8`…, `pass`, `never`), and no top-level function sharing a name with a pattern binding.
- A dropped result is an error (`luce.sema.unused`): write `discard(...)` around a value nothing receives, with any `catch` outside it — `discard(risky()) catch reason:`.
- Divergence must be declared `-> never`; a fallible helper still reads `error(...)` inline, and a `-> !` call is not a diverging arm.
- Mixed-width arithmetic still needs an explicit conversion (`u32` + `i64` is refused), so the eight compound index expressions keep their `i64(...)`. Indexing itself no longer does: a `u32` id indexes a table directly.
- Stack, not frame count, is the real recursion limit — see §8.1 — and since 0.26 the ceiling also depends on the build mode; `recursion.md` §3 has the numbers.
- Lifted in 0.26, do not re-introduce the workarounds: `i64`-only indexing, bare `pub name: T` fields, file-scope `const`, single-member match arms, and the absence of `pass`/`never`/`list[T?]`.
- Rule: reproduce a suspected Stage-0 defect as a standalone program and confirm it fails on the installed `luce-0` before reporting or working around it. History in `done.md` §5.
- Open requests to the Stage-0 team: [`stage0-0.26.md`](stage0-0.26.md), with reproductions in `build/stage0-0.25-repro/` and `build/stage0-0.26-repro/`.

### 8.1 The depth budget is a stack budget

Stage-0 advertises 1,000,000 frames on a 512 MiB stack. That pairing assumes about 512 bytes per frame, which compiler-shaped code does not obey, so the advertised number is not the number to plan against. It still stands in 0.26: the stack-pointer guard that would fix it was built, worked, and was reverted for aborting a `cfunc` callback, so this remains the one open request.

Measured on 0.25/arm64-macOS (method: bisect the depth at which a built program takes SIGBUS, then divide the 512 MiB reservation by it):

| shape | bytes per frame | frames before the guard page |
| --- | --- | --- |
| 2-arm match building a value struct | 715 | ~750,000 |
| 10-arm | 2,664 | ~201,000 |
| 30-arm | 8,343 | ~64,000 |
| one HIR-interpreter call (six host frames) | ~32,000 | ~16,600 |

The cost is linear in the number of match arms that build a value struct — about 270 bytes per arm, never reused across arms that cannot both run. Past the ceiling the process takes SIGBUS; Stage-0's frame counter never fires, so the promised trap does not appear.

Consequences we hold to: both interpreters cap at `frame_limit = 2000`, a sixfold margin under the measured fat-callee ceiling of 12,875 and above the deepest fixture (`down(1500)`), so exhaustion is *reported* rather than fatal. The number is recorded with its measurement in `backends/interpreter.luc`. Re-measure when the reservation or the interpreter's shape changes. Reproduction for the Stage-0 team: `build/stage0-0.25-repro/`.

### 8.2 What everyone else does, and where we are short

Checked against the implementations rather than argued from first principles.

| | stack | declared limit | probes the stack pointer |
| --- | --- | --- | --- |
| Clang | 8 MiB, raised by `setrlimit` at startup | bracket depth 256, template depth 1024 | yes — warns, then continues on a fresh stack |
| Swift | 8 MiB, the OS default | parser nesting 256, fatal | no — the cap is what keeps it safe |
| rustc | 16 MiB on a *spawned* thread, for control over the size | `recursion_limit` 128 | no longer — it now lets the OS handle growth |
| Zig | 46 MiB for the compiler, 60 MiB per worker | none in the parser | no — and deep nesting segfaults, filed as urgent |
| CPython | 16 MiB linked on macOS, 64 MiB under sanitizers | 1000 Python frames | yes, since 3.14, against queried stack bounds |
| Luce (us) | 512 MiB from Stage-0; 64 MiB in what we emit | `frame_limit` 2000 | no |

Three patterns hold across all of them. A declared count limit exists so the error is deterministic across machines. The safety factor on that count is ten to a hundred, not the six we run, because per-frame cost depends on the input's shape. And the ones that degrade gracefully rather than crashing all probe the stack pointer; the one that does not, Zig, has an open urgent bug for exactly the crash we reproduced.

Where we are short, in the order it will bite. The design record that turns this list into work is [`recursion.md`](recursion.md):

- ~~The front end has no nesting guard.~~ **Closed 2026-08-29.** Expression nesting is capped at 256; 26,250 nested parentheses used to take SIGBUS. Statement and type nesting are still unguarded and still unmeasured.
- **`frame_limit` is declared, not derived.** It is right for Stage-0's 512 MiB
  host and unproven for executables linked by the QBE host toolchain. The fix
  is to compute it at startup from real stack bounds, as CPython does.
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

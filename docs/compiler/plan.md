# Compiler plan and decision record

This is the plan half of the compiler's planning pair: the decisions behind
the design and the work still ahead, written so work can resume from it
without the conversations that produced it. The other half,
[`done.md`](done.md), records what exists, what each milestone proved, the
bugs the harness caught, and where the project came from. `mir.md` explains
the machine representation in depth. Update this file when a decision
changes; move items to `done.md` when they are ticked. Do not let either
drift into a wish list.

Last updated: 2026-08-28 (Stage-0 0.23).

## 1. Testing strategy (the part that must not be lost)

Every language feature is proven by **three independent executions** that
must agree:

1. the HIR interpreter — the definition of behaviour, never sees MIR;
2. the MIR interpreter — the lowerer's first consumer, no target;
3. a compiled artifact — wasm under `wasmtime` (and native where the slice
   allows).

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

## 2. Canonical MIR — the decisions (details in `mir.md`)

- **Structured control flow** (`Block`/`Loop`/`If`/`Switch`/`Br`/`BrIf`/`Yield`), not a basic-block graph. Luce has no `goto`; structure → jumps is trivial for native, jumps → structure (the relooper) is the hard direction and is avoided entirely.
- **Typed write-once registers**, not an operand stack. Registers map to wasm locals for free and to native registers directly. Mutable locals live in `Alloca` slots; a later pass promotes them.
- **Canonical given a `TargetLayout`**: struct/enum offsets are computed by the lowerer and stored in MIR; the verifier checks them. Required for C interop. A wasm32 program and an arm64 program are different MIR programs.
- **Aggregates never sit in a register**: a register of aggregate type holds an address; copies are explicit `Memcpy`; aggregate results go through a hidden leading pointer parameter; aggregate parameters are passed by pointer, written through only by a `mutating` receiver.
- **Runtime as symbols** (`luce_rt_*`), never instructions. wasm imports them; native links `libluce_rt`.
- **Failure as data**: a fallible function returns `(value, error_ptr)`; `try` is a call plus one conditional branch; `defer` is duplicated onto every exit; no unwinding.
- **Semantics fixed in MIR**: `Add` means checked add; `floor_div`/`rem` are floor semantics; shifts trap on count, drop bits shifted out. Checks are removed only by proof, never by build mode.
- **Not in MIR**: generics (monomorphized), closures (env struct + function), interfaces (data pointer + witness table), names.
- **`Yield`** is the structured phi: a region that produces values names them on every exit.
- **Narrow integers stay MIR types** (Prism `DType` and the C ABI need exact widths).
- **Open**: optionals are a uniform `u8`-tagged enum today; a null niche for references is undecided. Fallible ABI is per backend (wasm multi-value, QBE out-pointer/aggregate — never a global).

## 3. Native backends, QBE, and the linker — the decisions

**Own the whole native toolchain: no LLVM, no external assembler or linker at build time.**

- **Codegen**: a QBE-shaped pass written in Luce, using QBE (MIT, ~12k lines C) as *reference*, not a port — SSA construction, slot promotion, C ABI incl. Apple arm64, instruction selection, spilling, the simple register allocator — with our own machine-code encoders (seeds: the mnemonic constants in `arm64_macos.luc` / `x86_64_linux.luc`).
- **Timing**: after enums land (MIR settles). First read QBE and write `docs/compiler/native.md`; then the arm64 pass as a fourth column in the harness; x86-64 afterwards.
- **Linker rungs**: rung 0 (today) one image, raw syscalls; **rung 1 (required for the host)** Mach-O dyld imports of libSystem and frameworks, stubs/GOT, bind info, own ad-hoc code signature — ELF stays fully static; rung 2 links our own object files when separate compilation exists; rung 3 (a real linker for foreign `.o`/`.a`) deferred indefinitely.
- **`libluce_rt`** is Luce, compiled into every program as more MIR, bottoming out in syscalls on Linux and libSystem on macOS. It is the layer *above* the OS library.
- **Dependency-free verdict**: Linux fully; macOS at build time fully, with the normal run-time dependency on libSystem. Clang is used only to *generate* C bindings.
- **Size estimate** beyond today: ~15–25k lines of Luce (lowerer rest, runtime, codegen, encoders, image writers).

### WebAssembly

- Host contract is **WASI preview 1** (`fd_write` via a scratch iovec at offset 0, `_start` → `proc_exit`, `memory` exported). Tests use `wasmtime`, installed in CI.
- Registers → locals; narrow values kept canonical inside i32; shadow stack in linear memory with an overflow guard; checked arithmetic legalized in four shapes; exactly one wasm structured instruction per MIR region so MIR depth equals wasm label depth; float constants assembled arithmetically (Stage-0 has no bit casts).

## 4. The proving programs

**1 — the guest in Luce (wasm).** The seed guest commands (`echo_guest.c`, `lucia_guest.h` + 11 seeds) rewritten in Luce, compiled to wasm32, running unmodified under the existing `WasmHost` ABI (imports `lucia_call(ptr,len) -> i64`, `lucia_log`, `lucia_yield`; exports `lucia_alloc`, `lucia_main`). The first place "safe by construction" can be shown to a non-programmer. Why this one: `done.md` §4.2.

**2 — the host in Luce (native).** Terminal, realm, storage, crypto, network and `WasmHost` as real executables on macOS (libSystem, Cocoa/Metal via dyld) and Linux (libc/OpenSSL), with the wasm engine as a Luce library — decoder + interpreter with fuel beside the existing encoder, differential-tested against `wasmtime` while both exist. Owning the engine settles the preemption blocker and frees the compiler tests from `wasmtime`.

## 5. What is next — the checklist

Each item is a vertical slice gated by §1. Gates (§6) are settled in the spec *before* the feature lands in `hir_gen`. Ticked items move to `done.md` §2.

### Proving program 1 — the guest

- [ ] **Enums and `match`**: payloads inline, exhaustiveness, `Switch` lowering (first real use of `Switch` in MIR), bindings.
- [ ] **`for` and ranges.** *Gate: fallible iteration protocol.*
- [ ] **`defer`, `try`/`catch`, `Error`**: failure-as-data ABI, `defer` duplicated onto every exit, `catch` forms; custom struct `init` rides on this.
- [ ] **`extern` import/export** with wasm namespaces (`kino`/`lucia` imports, `lucia_alloc`/`lucia_main` exports); C signatures verified by the MIR verifier.
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
- [ ] **`docs/compiler/native.md`**, then the **arm64 QBE-shaped pass** as a fourth harness column, then **x86-64**.
- [ ] **Native rung 1** (dyld imports + own signing). Required for the host.
- [ ] **C import (FIIR)** from headers via Clang, for Cocoa/Metal, OpenSSL/Monocypher, wasm3 during transition.
- [ ] **Wasm engine in Luce**: decoder + validator + interpreter with fuel at back-edges and calls; differential-tested against `wasmtime`; then the compiler tests drop `wasmtime`.
- [ ] **Host slices**: storage journal + acceptance rule → crypto → terminal headless shell → `WasmHost` running proving program 1 → realm/network → UI/Metal.
- [ ] **`luce api diff`** and **`luce describe`** as compiler products; `luce build --time-report` once generics exist.
- [ ] **Fuel/preemption as a wasm backend option** (when guests need it and the engine is not ours).

### Self-hosting and compile speed

- [ ] Compiler builds itself under the Stage-0-subset rule; one pinned prior compiler kept forever for bootstrapping; bootstrap reproducibility checked in CI.
- [ ] **Measure first**: lines per second of the compiler compiling itself, before any layout work. Stage-0's codegen and ARC dominate until then, so layout changes are invisible before this point.
- [ ] **Data-oriented layout, in this order, each behind the measurement**: (1) ids and spans to `u32` (`TypeId`, `SymbolId`, `RegisterId`, `FunctionId`, `DataId`, `SourceSpan` start/end; line/column derived) — deferred from 2026-08-28 because Stage-0 indexes lists with `i64` only and has no `u32`↔`i64` mixing, which would cost ~180 conversions of noise today; (2) tiny tokens (`kind: u8, start: u32`, text recomputed); (3) MIR flattened to a linear instruction array with region-end markers — the wasm encoding, which also makes the verifier and backends single passes; (4) HIR/AST as flat node tables with an extra-data array, only if (1)–(3) leave it as the bottleneck. Generic structure-of-arrays is a library/tooling question (hand-written for the hot tables, or generated from `luce describe`), never a reason to add compile-time execution.
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
| Fallible iteration protocol (item / end / error, propagation visible at the loop) | `for` | query results, journal folds, directory verbs all have three outcomes |
| Owned (non-copyable, consuming) values — state transitions, destruction on every exit | classes / ARC | keys wiped in destructors, guest handles, journal lock fd |
| Scoped values generalised from `mutable_slice`/`task` | closures | borrowed `const Element*`, `thread_local const char*` |
| Closure capture: explicit vs §14.1 implicit shared cell, by the both-ways corpus test | closures | the compiler and all three C++ repos are closure-light corpora |
| Const-generic grammar `[T, const n: u64]` reserved in the parser | generics | `Spectrum` = 32 inline floats, fixed guest buffers |
| ~~`hir_gen` keeps doc comments, parameter names, defaults~~ | structs | **met** (`done.md` §2) |

Standing rules:

- **Indices, not pointers, across stages.** Every program-wide table (`types`, `symbols`, `structs`, `functions`, `data`, registers, slots) is addressed by an integer id into a flat list; no stage hands another a pointer graph. New tables follow this. (Tree *nodes* are still ARC classes today — see the layout items in §5.)
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

The compiler must stay buildable by Stage-0 (the frozen seed) until it builds itself. Stage-0 0.23 is pinned. Remaining constraints:

- Call depth is 32768 host frames; both interpreters cap at `frame_limit = 2000`.
- Reserved identifiers (`error`, `bytes`, `i8`…), single-member enum `match` arms, class fields spelled `pub name: T`, no top-level function sharing a name with a pattern binding, no optional list elements (`list[T?]`), `continue` is not an empty match arm, lists index with `i64` only and no `u32`↔`i64` mixing, no `-> !` call as a diverging match arm (use `error(...)`).
- Rule: reproduce a suspected Stage-0 defect as a standalone program and confirm it fails on the installed `luce-0` before reporting or working around it. History in `done.md` §5.

## 9. Conventions worth keeping

- Every source file opens with a header that says what it is, why, where it sits, and how to read it; `# mark:` sections follow the header's promised order; comments explain *why*; magic numbers get a mnemonic or field name beside them.
- `README.md` → `docs/README.md` → `1.0.md` (spec, not status) → `examples/` → `tests/` is the reading order; the README's "What works today" is the single definition of the implemented slice.
- Diagnostics: `path:line:column: message` from the front end, a stage prefix (`interpreter:`, `MIR verifier:`, `executable:`, `<target> backend …`) from later stages; unsupported input never traps.
- Errors from every stage reach the CLI as text with exit 1; usage errors exit 2 (`tests/cli_test.sh` pins this).
- Commits: short plain lowercase messages after each green step.

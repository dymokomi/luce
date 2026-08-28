# Compiler plan and decision record

This page is the standing plan for the Luce compiler and the record of the
decisions behind it, written so work can resume from it without the
conversations that produced it. `mir.md` explains the machine
representation in depth; this page says what is done, what is next, what
was decided and why, and what is deliberately deferred. Update it when a
decision changes; do not let it drift into a wish list.

Last updated: 2026-08-27 (Stage-0 0.23).

## 1. Where things stand

| Layer | State |
|---|---|
| Tokenizer, parser, syntax tree | Complete for the 1.0 surface (`docs/language/1.0.md`); every syntax form has parser coverage. |
| HIR generation (`hir_gen.luc`) | Functions, calls, parameters, locals, assignment, all scalar types, `str`/`bytes`/`char` literals, tuples, optionals with `else`, module constants, type aliases, `if`/`elif`/`else`, `while`, `break`/`continue`, `return`, `print` of a literal. **Not yet**: structs, classes, enums, `match`, `for`, closures, interfaces, generics, `defer`, `try`/`catch`, method calls, field access, lists/maps/sets, formatted strings, extern/export. Each fails with "not implemented yet" and a span. |
| HIR interpreter (`backends/interpreter.luc`) | The semantic oracle. Executes everything HIR generation produces. Runs `main(arguments: slice[str])` with an empty slice. |
| Canonical MIR (`canonical_ir.luc`) | Designed for the whole language (see `mir.md`); verifier (`mir_verifier.luc`) proves every rule; MIR interpreter (`backends/mir_interpreter.luc`) executes every instruction. |
| Lowerer (`lowerer.luc`) | Slices 3a–3c and milestone 4 done: scalars and locals, control flow, calls, constants, tuples, optionals, `str`/`bytes` values and equality, `print` of a value. Not yet: everything HIR does not generate. |
| WebAssembly backend | Everything the lowerer emits, with spec semantics (checked arithmetic, floor division, trapping shifts), WASI preview 1 host contract, shadow stack with overflow guard. Executed under `wasmtime` in tests. |
| Native backends (arm64 Mach-O, x86-64 ELF) | The original slice only: constants, checked add/sub/mul, `print` of a literal, `return` from `main`. Direct executable writers, no linker. **Not extended on purpose** (see §4). |
| Tests | 362 unit tests; CLI contract script; `wasmtime` execution script; native smoke script (arm64 hello + overflow trap). `tests/compiler/differential_test.luc` runs ~90 fixtures through HIR interpreter, MIR interpreter, and every encoder and requires agreement. |
| Toolchain | Stage-0 0.23 pinned in `bootstrap.sh`. Known Stage-0 constraints in §7. |

## 2. Testing strategy (the part that must not be lost)

Every language feature is proven by **three independent executions** that
must agree:

1. the HIR interpreter — the definition of behaviour, never sees MIR;
2. the MIR interpreter — the lowerer's first consumer, no target;
3. a compiled artifact — wasm under `wasmtime` (and native where the slice
   allows).

When two agree and one differs, the stage between them is wrong. Every
lowerer slice adds fixtures to `differential_test.luc` *and* the same
programs to `tests/wasm_test.sh`, plus programs that must trap on all
three. This triangle found five real bugs during slices 3a–3c, four of them
in the "reference" implementations, and milestone 4 found a sixth (in the
MIR interpreter's loop exits). Keep it.

Rules: a spec semantics question (overflow, `//`, shifts, `~` on unsigned)
is settled by reading `1.0.md` §7, implemented in the HIR interpreter first,
and then everything else is made to agree. Backends legalize; they never
choose semantics.

## 3. Canonical MIR — the decisions (details in `mir.md`)

- **Structured control flow** (`Block`/`Loop`/`If`/`Switch`/`Br`/`BrIf`/`Yield`), not a basic-block graph. Luce has no `goto`; structure → jumps is trivial for native, jumps → structure (the relooper) is the hard direction and is avoided entirely.
- **Typed write-once registers**, not an operand stack. Registers map to wasm locals for free and to native registers directly; a stack would make native simulate it. Mutable locals live in `Alloca` slots; a later pass promotes them.
- **Canonical given a `TargetLayout`**: struct/enum offsets are computed by the lowerer from pointer width and alignment rules and stored in MIR; the verifier checks them. Required for C interop. A wasm32 program and an arm64 program are different MIR programs.
- **Runtime as symbols** (`luce_rt_*`), never instructions: allocation, ARC, weak refs, strings/collections, traps, `write`, workers. wasm imports them; native links `libluce_rt`.
- **Failure as data**: a fallible function returns `(value, error_ptr)`; `try` is a call plus one conditional branch; `defer` is duplicated onto every exit; no unwinding.
- **Semantics fixed in MIR**: `Add` means checked add; `floor_div`/`rem` are floor semantics; shifts trap on count, drop bits shifted out.
- **Not in MIR**: generics (monomorphized), closures (env struct + function), interfaces (data pointer + witness table), names.
- **`Yield`** was added during implementation: with write-once registers, a region that produces values needs every exit to supply them explicitly (`Br`/`BrIf` carry values; `Yield` is the normal exit). It is the structured phi.
- **Open questions**: narrow integers as MIR types (current) vs normalized to i32/i64 with widths only at struct fields and C signatures (what wasm and QBE want) — decide when the native pass starts; optionals are a uniform `u8`-tagged enum today, a null niche for references is still open; fallible ABI per backend (wasm multi-value, QBE out-pointer/aggregate — never a global).

## 4. Native backends, QBE, and the linker — the decisions

**Path chosen: own the whole native toolchain, no LLVM, no external assembler or linker at build time.**

- **Codegen** will be a QBE-shaped pass written in Luce, using QBE (MIT, ~12k lines C, ~5–6k relevant) as *reference*, not a port: SSA construction (easy from structured write-once MIR), slot promotion (`mem.c`), C ABI incl. Apple arm64 (`abi.c`), instruction selection (`arm64/isel.c`), spilling and the simple register allocator (`spill.c`, `rega.c`). QBE's `emit.c` (assembly text) is replaced by our own machine-code encoders, whose seeds are the mnemonic-named constants already in `arm64_macos.luc` / `x86_64_linux.luc`. Expect a rewrite: QBE is pointer-linked C.
- **Timing**: after the lowerer reaches structs/enums (MIR settles), not before. A native pass built against the current slice would be reworked as slices land. First read QBE and write `docs/compiler/native.md` (pass pipeline mapped onto MIR, `.s`-vs-`.o` decision, what `abi.c` says about Apple arm64); then the arm64 pass as a fourth column in the differential harness; x86-64 afterwards (shares most).
- **Linker rungs**:
  - Rung 0 (today): one image, raw syscalls, no linker. Dead end for C interop; kept as the no-dependency path for the current slice.
  - **Rung 1 (next native work, small, ~2–3k lines)**: the Mach-O writer grows dyld imports — `LC_LOAD_DYLIB /usr/lib/libSystem.B.dylib`, `LC_LOAD_DYLINKER`, stubs/GOT, bind info — plus our own ad-hoc code signature (SHA-256 code directory), removing the `codesign` shell-out. This is mandatory on macOS (libSystem cannot be statically linked; raw syscalls are unsupported and broke Go) and it unlocks `extern` for files, sockets, threads with zero external tools. ELF on Linux needs none of it: fully static, raw syscalls.
  - Rung 2 (when separate compilation exists): link our own object files — concatenation plus a symbol table, ~1k lines.
  - Rung 3 (optional, ~5–10k lines): a real linker for clang-produced `.o`/`.a`. Deferred indefinitely; the middle path is "foreign `.dylib`/`.so` import for free through dyld, foreign `.a` via shelling out to the system `ld` if ever needed".
- **`libluce_rt`** is written in Luce and compiled into every program as more MIR (whole-program), bottoming out in syscalls on Linux and libSystem imports on macOS. It is the layer *above* the OS library, not a replacement for it. A `.a` form appears only with separate compilation.
- **Dependency-free verdict**: Linux fully (static ELF); macOS at build time fully, with the unavoidable and normal run-time dependency on libSystem. The single planned external tool is Clang, only when *generating* C bindings (spec §21 FIIR); building against generated bindings needs nothing.
- **Size estimate** beyond today: lowerer for the rest of the language ~4–6k, runtime ~5–8k, native codegen ~5–7k arm64 + ~2k x86-64, encoders ~1–1.5k each, image writers ~2–3k Mach-O / ~1k ELF. Total ~15–25k lines of Luce.

## 5. WebAssembly decisions

- Host contract is **WASI preview 1**: `luce_rt_write` → `fd_write` through a 16-byte scratch iovec at memory offset 0; entry programs get `_start` → `proc_exit`; `memory` exported. Any wasm runtime runs the modules; tests use `wasmtime` (host-gated, installed in CI via `bytecodealliance/actions`).
- Registers → locals (Int ≤ 32/Bool/Ptr → i32, Int 64 → i64, floats native); narrow values kept canonical (sign/zero-extended) inside i32.
- Shadow stack in linear memory: `__stack_pointer` global, 16 pages, data from offset 16 upward, stack down from the top, prologue traps when a frame would reach the data.
- Checked arithmetic legalized in four shapes (i32/i64 overflow tests; narrow computed in i32 and range-checked; u32 in i64; u64 with a negative-result trap). Floor division by branch-free adjustment; wasm's own traps on zero divisor and `min/-1` are relied upon.
- Exactly one wasm structured instruction per MIR region, so MIR branch depth equals wasm label depth (invariant stated in the file).
- Float constants are assembled into IEEE bit patterns arithmetically (Stage-0 has no bit casts).

## 6. Order of work — the checklist

Each item is a vertical slice gated by the three-way harness (§2) plus executed wasm; tick it only when `./test.sh` is green and the commit is in. Spec gates from §9 are listed where they block an item; settle them in `1.0.md` *before* the feature lands in `hir_gen`.

### Done

- [x] Tokenizer, parser, syntax tree for the whole 1.0 surface, with per-form tests.
- [x] HIR generation for scalars, locals, control flow, calls, constants, tuples, optionals, `str`/`bytes`/`char` literals, `print` of a literal.
- [x] HIR interpreter as oracle (spec §7 arithmetic, `frame_limit = 2000`).
- [x] Canonical MIR contract, verifier, MIR interpreter (`mir.md`).
- [x] Lowerer 3a–3c: scalars and locals, control flow, calls/parameters/constants.
- [x] Wasm backend for everything the lowerer emits; WASI host contract; executed under `wasmtime` in `tests/wasm_test.sh`.
- [x] Native rung 0 (arm64 Mach-O, x86-64 ELF) for the original slice only.
- [x] Stage-0 0.23 pinned; deep-recursion fixtures restored.
- [x] Decision record: `vision.md`, gap audit, lineage evidence, proving programs (§9).

### Proving program 1 — the guest in Luce (wasm)

Target: the seed guest commands (`echo_guest.c`, `lucia_guest.h` + 11 seeds) rewritten in Luce, compiled to wasm32, running unmodified under the existing `WasmHost` ABI (imports `lucia_call(ptr,len) -> i64`, `lucia_log`, `lucia_yield`; exports `lucia_alloc`, `lucia_main`).

- [x] **Milestone 4 — composites the HIR already has.** Tuples as anonymous structs in slots (`FieldAddress`, `Memcpy`); optionals as `u8`-tagged two-case enums (payload after the tag; null niche for references later); `str`/`bytes` as `{pointer, i64 length}` with structural equality (inline byte loop); `print` of a `str` value. Aggregate protocol: a register of aggregate type holds an address, copies are `Memcpy`, aggregate results go through a hidden leading pointer parameter, aggregate parameters are passed by pointer (`lowerer.luc` header). Found and fixed a MIR-interpreter bug (a `Loop` consumed a branch depth twice, dropping values carried out of the loop).
- [ ] **Structs and methods** in `hir_gen` → lowerer → wasm: fields, `init`, mutating value methods, struct update. *Gate: `hir_gen` keeps doc comments, parameter names, defaults.*
- [ ] **Enums and `match`**: payloads inline, exhaustiveness, `Switch` lowering, bindings.
- [ ] **`for` and ranges.** *Gate: fallible iteration protocol (item / end / error) decided in the spec first.*
- [ ] **`defer`, `try`/`catch`, `Error`**: failure-as-data ABI, `defer` duplicated onto every exit, `catch` forms.
- [ ] **`extern` import/export** with wasm namespaces (`kino`/`lucia` imports, `lucia_alloc`/`lucia_main` exports); C signatures verified by the MIR verifier.
- [ ] **`libluce_rt` in Luce, freestanding**: bump/free-list allocator over linear memory, `write`, `trap`, string/bytes primitives; through the MIR interpreter's stub runtime first, then compiled.
- [ ] **Lists, maps, sets and strings via the runtime**; formatted strings.
- [ ] **Prism text codec in Luce** (`.prisma` encode/decode) as the first library; the guest request/reply round-trip typed.
- [ ] **The guest itself**: `lucia_main` in Luce, the seed verbs, running under `WasmHost`; a program a non-programmer can read.

### Proving program 2 — the host in Luce (native)

Target: terminal, realm, storage, crypto, network and `WasmHost` in Luce as real executables on macOS (libSystem, Cocoa/Metal via dyld) and Linux (libc/OpenSSL), with the wasm engine as a Luce library.

- [ ] **Classes with ARC, weak references, `deinit`** — `SemanticAnalyzer` starts producing ownership facts. *Gates: owned/consuming values specified; scoped values generalised from `mutable_slice`/`task`.*
- [ ] **Closures.** *Gate: capture rule (explicit vs §14.1 shared cell) decided by the both-ways corpus test.*
- [ ] **Interfaces** (data pointer + witness table) and **generics** (monomorphization). *Gate: const-generic grammar reserved in the parser.*
- [ ] **Workers** (`spawn`, tasks, sendability, `wait_all`).
- [ ] **`docs/compiler/native.md`**: QBE read, pass pipeline mapped onto MIR, `.s`-vs-`.o` decision, Apple arm64 ABI notes.
- [ ] **arm64 QBE-shaped pass** (SSA, slot promotion, ABI, isel, spill, regalloc, own encoders) as a fourth column in the harness; then **x86-64**.
- [ ] **Native rung 1**: Mach-O dyld imports of libSystem and frameworks, stubs/GOT, bind info, own ad-hoc code signature; ELF static with raw syscalls. Required for the host.
- [ ] **C import (FIIR)** from headers via Clang, for Cocoa/Metal, OpenSSL/Monocypher, wasm3 during transition.
- [ ] **Wasm engine in Luce**: decoder + validator + interpreter with fuel at back-edges and calls; differential-tested against `wasmtime`; then the compiler tests drop `wasmtime`.
- [ ] **Host slices**: storage journal + acceptance rule → crypto → terminal headless shell → `WasmHost` running proving program 1 → realm/network → UI/Metal.
- [ ] **`luce api diff`** and **`luce describe`** as compiler products (source, runtime contract, C ABI, schema, descriptor dimensions).
- [ ] **Fuel/preemption as a wasm backend option** (when guests need it and the engine is not ours).

### Self-hosting

- [ ] Compiler builds itself under the Stage-0-subset rule; one pinned prior compiler kept forever for bootstrapping; bootstrap reproducibility checked in CI.
- [ ] Language freeze after the compiler and one host slice depend on every feature.

### Deferred by decision (do not start without new evidence)

- System profile (atomics, volatile, interrupt ABIs, drivers): bare metal is a non-goal; runtime threading stays in `libluce_rt` via C interop.
- Effects / `uses` clauses: removed (spec §18).
- Native rung 3 (foreign `.a` linker), transactional heap, general effect rows, dependent types, macros, reflection.

## 7. Stage-0 state and constraints

The compiler must stay buildable by Stage-0 (the frozen seed) until it builds itself. Stage-0 0.23 is pinned. Its remaining known constraints:

- **Call depth is 32768 host frames** (0.23; was 128 in 0.22). Both interpreters cap at `frame_limit = 2000` interpreted frames, a few host frames each.
- Fixed in 0.23: the temporary-receiver / optional-field use-after-free (reproduction kept in `build/stage0-0.22-repro.tar.gz`; `differential_test` and `lowerer.luc` no longer work around it).
- Reserved identifiers (`error`, `bytes`, `i8`…), single-member enum `match` arms, class fields spelled `pub name: T`, no top-level function sharing a name with a pattern binding.
- Fixed in 0.22: errors through interface-typed calls (tested by `pipeline_test.luc`).
- Withdrawn after checking: "`return` in a statement-form `catch` does not return" — it does.

Rule: reproduce a suspected Stage-0 defect as a standalone program and confirm it fails on the installed `luce-0` before reporting or working around it.

## 8. Conventions worth keeping

- Every source file opens with a header that says what it is, why, where it sits, and how to read it; `# mark:` sections follow the header's promised order; comments explain *why*; magic numbers get a mnemonic or field name beside them.
- `README.md` → `docs/README.md` → `1.0.md` (spec, not status) → `examples/` → `tests/` is the reading order; the README's "What works today" is the single definition of the implemented slice.
- Diagnostics: `path:line:column: message` from the front end, a stage prefix (`interpreter:`, `MIR verifier:`, `executable:`, `<target> backend …`) from later stages; unsupported input never traps.
- Errors from every stage reach the CLI as text with exit 1; usage errors exit 2 (`tests/cli_test.sh` pins this).

## 9. Why the language matters — the proving program and the decision gates

Recorded 2026-08-27 after reading `docs/vision.md`, `docs/language/1.0-gap-audit.md`, kinogaki.com, the Sweeney/Fridman transcript (Verse, correctness, concurrency, UE6), and the three predecessor repositories in `~/dev` (`prism`, `kinogaki`, `luciaos_v1`; read by subagents, nothing built or run).

### 9.1 Where this came from

Four repositories, one lineage, each stopped at a planning boundary rather than a bug:

| Repo | Dates | What it is | Why it ended |
|---|---|---|---|
| `prism` | 2026-06-13 → 06-19 | SwiftUI/Metal spectral raytracer that grew a USD-shaped Stage/Prim/Path model, rewrote it in C++, then dropped Swift entirely ("three live representations" of the scene; `PRISMCORE_CPP_PLAN.md`) | core extracted into kinogaki |
| `kinogaki` | 06-20 → 07-12 | The C++20 platform: Prism core (Value = dtype+shape+flat buffer, `Compose.h` diff/overlay/merge/conflicts/renames, `Schema.h`, `EventLog.h`, `Query.h`, codecs), UI, platform, storage journal, crypto, auth, ai/MCP, wasm guest host; ~120k LOC, ~5k test assertions, 22 nested repos | last commits are `planning/`; `APP_PLATFORM.md` frozen "next critic is implementation" |
| `luciaos_v1` | 07-13 → 07-24 | Same core generalised into an OS: terminal / realm / documents; programs are `app` elements holding sealed wasm; run document in, out document out; signed journal with one acceptance rule; ~98k LOC, ~1.2k tests, no Python | last commit is `planning/REALM.md` with zero implementing commits; `BOOTSTRAP.md` already names "Lucia language as the authoring layer; compiler itself as a command document" |
| `luce` | 08-21 → | the language | — |

Correction to the earlier draft of this section: the durable world is **not** on paper. Diff/overlay/merge/schema/event log, the signed journal and acceptance rule, store-and-forward sync with rebase-and-replay, per-reader sealing, and wasm guest confinement all exist with tests. What is paper: `kino://` addresses (zero hits in code), cross-realm capability links, sibling-version conflicts, fuel metering and kill-switch ("wasm3 CANNOT interrupt a pure compute loop"), the kernel/process table, and the whole authoring ladder. `APP_PLATFORM.md` explicitly rejected a bespoke VM in favour of wasm — Luce is consistent with that: a language that *compiles to* wasm, not a new instruction substrate.

### 9.2 The pain point, from the code rather than the vision

1. **The guest seam is the worst code in the lineage, and it is the exact place ordinary people would write.** `kinogaki-os/tests/fixtures/echo_guest.c` and `luciaos_v1/software/terminal/commands/lucia_guest.h` + 11 seed commands: freestanding C, `-nostdlib`, a bump allocator that never frees, `.prisma` requests as string literals and replies parsed by substring search into fixed `char[512]`/`[8192]`/`[65536]` buffers; `grep.c` supports 4 roots because that is an array size. The guest ABI is tiny and frozen: imports `lucia_call(ptr,len) -> i64 (ptr<<32|len)`, `lucia_log`, `lucia_yield`; exports `lucia_alloc`, `lucia_main`; one tool namespace `lucia:os/doc` with verbs open/list/find/put/mkdir/rm/move/connect/disconnect. **The guest has no typed property access at all** — `put(path, text)` is the only write; the rich typed vocabulary (`set_property(path, name, value, dtype)`, `define_element`, validate, commit) lives only in the trusted in-process MCP tools (`kinogaki-ai/src/DocTools.cpp`), which already do copy → mutate → `applyAuto` → roll back on refusal.
2. **Errors die at every seam.** `capiTry` swallows everything to NULL/false/NaN; `os::Abi` collapses every failure to `unavailable` (deliberate anti-oracle, but a guest cannot tell "denied" from "you passed garbage"); core mixes `optional`, thrown `invalid_argument`, and stringly `Committed{id,error}` (419 `optional`, 0 `expected`). Silent swallowing is the most repeated theme in the issue tracker.
3. **Serialization and tables by hand, everywhere.** ~2.1k LOC of text/binary/package codecs plus LZSS and f16 bit-twiddling; 110 `case Type::` arms for a 10-variant `Value`; every value type re-encoded at the C, ctypes, JSON-schema, and MCP layers; enums kept in three copies; verb tables in three copies (`Shell.cpp` dispatch + `mut[]` + help + completion); the same worker-thread + queue + main-drain shape written three times; every shader three times.
4. **Borrowed pointers documented, not enforced.** The C ABI hands back `const char*` from two process-wide `thread_local` strings (call any two getters and the first dangles); query results are borrowed `const Element*` "invalidated by the owner's lifetime"; COW correctness rests on `use_count()!=1`. Zero memory-safety bugs were filed — the code is careful — but it is careful by convention.
5. **One source for wasm and native is not achievable in C++.** `#if __EMSCRIPTEN__` swaps whole class internals; `webstubs.cpp` exists only to `abort()` in link-reachable dead paths because the build cannot say "this build has no Shell"; 18 packages × 2 hand-maintained build systems + emscripten.
6. **The named OS blocker is a compiler job.** `OS_ARCHITECTURE.md` stalls the kernel on per-instruction fuel and preemption that wasm3 cannot provide. A backend that inserts fuel checks at loop back-edges and calls makes any engine preemptible; `wasmtime` also has native fuel/epochs.

Sweeney's four pains map onto this concretely: a behavior that receives a snapshot and returns a diff cannot break anything (1, with `Compose::diff`/`Schema::validate` finally reachable from the guest); workers get O(1) snapshots and emit diffs, `merge` reports conflicts — the transaction at document granularity with no STM; live upgrade is `luce api diff` on code plus schema diff on data over signed commits; and safety for the C++ replacement is the language's job.

### 9.3 What this changes

Not the order in §6 and not MIR (every gap-audit item is additive to the IR; failure-as-data is exactly the error model the seams lack). It fixes the **proving program precisely**: rewrite the seed guest commands (`echo_guest.c`, `lucia_guest.h` and the 11 seeds) in Luce, compiled to wasm32, running unmodified under the existing `WasmHost` ABI (`lucia_alloc`/`lucia_main`/`lucia_call`). That needs, in order: milestone 4 (strings/bytes as values), structs/enums/`match`, `extern` import/export with the wasm namespace, a freestanding allocator in `libluce_rt`, and the first real library — Prism text encode/decode in Luce. It replaces a real user of the platform within the existing plan order; it is also the first place "safe by construction" can be shown to a non-programmer. The typed vocabulary follows: `luce describe` output (gap audit §10) drives generated Prism encoders and schema-typed views, which is the concrete form of "feels like the language, not a library".

**The host is the second proving program, and it is native.** The terminal, realm, storage, crypto, network, and `WasmHost` will also be Luce, so Luce must produce real executables linked against libSystem/Cocoa/Metal on macOS and libc/OpenSSL on Linux. Two consequences: native rung 1 (dyld imports + signing) and C interop are **required**, not optional; and the wasm engine becomes a Luce library — a decoder and interpreter beside the existing encoder (`backends/wasm.luc`), differential-tested against `wasmtime` while both exist. Owning the engine settles the fuel/preemption blocker directly (checks at back-edges and calls in our own loop), removes the compiler tests' dependence on `wasmtime`, and needs classes/ARC, collections, and workers — so it lands after the guest, not before. Order: guest in Luce (wasm) → host in Luce (native) with the engine as its core.

**Decision gates (must be settled in the spec before the feature lands in `hir_gen`).**

| Gate | Before | Evidence from the lineage |
|---|---|---|
| Fallible iteration protocol (item / end / error, propagation visible at the loop) | `for` | query results, journal folds, directory/list verbs all have three outcomes |
| Owned (non-copyable, consuming) values — state transitions, destruction on every exit | classes / ARC | keys wiped in destructors (`crypto_wipe`), guest handles, journal lock fd |
| Scoped values generalised from `mutable_slice`/`task` | closures | borrowed `const Element*`, `thread_local const char*`, `PrimHandle` |
| Closure capture: explicit vs §14.1 implicit shared cell, by the both-ways corpus test | closures | the compiler and all three C++ repos are closure-light corpora |
| Const-generic grammar `[T, const n: u64]` reserved in the parser | generics | `Spectrum` = 32 inline floats, `Float3`, fixed guest buffers |
| `hir_gen` keeps doc comments, parameter names, defaults | structs / methods | needed for `luce describe`, derived Prism codecs, `luce api diff` |
| Fuel/preemption as a backend option (checks at back-edges and calls) | wasm backend, when guests run | the single named kernel blocker |

**Standing rules.**

- Effects stay removed (spec §18). Authority is a capability *value* from the platform (the acceptance rule and `Guest::inScope` already are that); operational facts are compiler-internal summaries, never in function types.
- Narrow integers stay MIR types (Prism `DType` has i8…u64/f16; C ABI needs exact widths). Closes the `mir.md` open question.
- The system profile (atomics, volatile, interrupt ABIs, drivers) is **demoted**: `luciaos_v1` declares bare metal a non-goal and contains zero atomics/volatile; Linux/macOS are the substrate. Runtime needs (one writer thread, queue/future) stay in `libluce_rt` via C interop until measured otherwise.
- One source for wasm and native, with a module system that can *exclude* code rather than stub it, is a language requirement, not a build-script problem.
- Phases 2–6 of `vision.md` reuse Prism `Compose`/`EventLog` and the journal rather than reinvent snapshot/patch/intent; "patch" and "proposal" as a guest-facing API do not exist yet anywhere and are the first thing the Luce guest library should provide.

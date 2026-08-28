# Compiler record — what is done and why we believe it

This is the record half of the compiler's planning pair. It says what exists,
what each milestone proved, which bugs the harness caught, and where the
project came from. The other half, [`plan.md`](plan.md), holds the decisions
and the work that is still ahead; read that one to resume work, read this
one to check a claim. Every tick here has a commit and a green `./test.sh`
behind it.

Last updated: 2026-08-28 (Stage-0 0.23).

## 1. Where things stand

| Layer | State |
|---|---|
| Tokenizer, parser, syntax tree | Complete for the 1.0 surface (`docs/language/1.0.md`); every syntax form has parser coverage. |
| HIR generation (`hir_gen.luc`) | Functions, calls, parameter defaults, locals, assignment, all scalar types, `str`/`bytes`/`char` literals, tuples, optionals with `else`, structs with fields/defaults/methods/`mutating`/type functions, field access and field assignment, module constants, type aliases, `if`/`elif`/`else`, `while`, `break`/`continue`, `return`, `print` of a literal or `str` value; documentation and defaults retained. **Not yet**: custom `init`, classes, enums, `match`, `for`, closures, interfaces, generics, `defer`, `try`/`catch`, lists/maps/sets, formatted strings, extern/export. Each fails with "not implemented yet" and a span. |
| HIR interpreter (`backends/interpreter.luc`) | The semantic oracle. Executes everything HIR generation produces. Runs `main(arguments: slice[str])` with an empty slice. |
| Canonical MIR (`canonical_ir.luc`) | Designed for the whole language (`mir.md`); verifier (`mir_verifier.luc`) proves every rule; MIR interpreter (`backends/mir_interpreter.luc`) executes every instruction. |
| Lowerer (`lowerer.luc`) | Scalars and locals, control flow, calls, constants, tuples, optionals, `str`/`bytes` values and equality, structs, methods, `mutating`, field places, `print` of a value. Not yet: everything HIR does not generate. |
| WebAssembly backend (`backends/wasm.luc`) | Everything the lowerer emits, with spec semantics (checked arithmetic, floor division, trapping shifts), WASI preview 1 host contract, shadow stack with overflow guard, `memory.copy` for aggregates. Executed under `wasmtime` in tests. |
| Native backends (arm64 Mach-O, x86-64 ELF) | The original slice only: constants, checked add/sub/mul, `print` of a literal, `return` from `main`. Direct executable writers, no linker. Not extended on purpose (`plan.md` §3). |
| Tests | 368 unit tests; CLI contract script; `wasmtime` execution script; native smoke script (arm64 hello + overflow trap). `tests/compiler/differential_test.luc` runs ~100 fixtures through HIR interpreter, MIR interpreter, and every encoder and requires agreement. |
| Toolchain | Stage-0 0.23 pinned in `bootstrap.sh`. Remaining constraints in `plan.md` §8. |

## 2. Done, in order

- [x] Tokenizer, parser, syntax tree for the whole 1.0 surface, with per-form tests.
- [x] HIR generation for scalars, locals, control flow, calls, constants, tuples, optionals, `str`/`bytes`/`char` literals, `print` of a literal.
- [x] HIR interpreter as oracle (spec §7 arithmetic, `frame_limit = 2000`).
- [x] Canonical MIR contract, verifier, MIR interpreter (`mir.md`).
- [x] Lowerer 3a–3c: scalars and locals, control flow, calls/parameters/constants.
- [x] Wasm backend for everything the lowerer emits; WASI host contract; executed under `wasmtime` in `tests/wasm_test.sh`.
- [x] Native rung 0 (arm64 Mach-O, x86-64 ELF) for the original slice only.
- [x] Stage-0 0.22 → 0.23: interface-error trap and temporary-receiver use-after-free reported with reproductions (`build/stage0-0.22-repro.tar.gz`), fixed upstream, workarounds removed; call depth raised, deep-recursion fixtures restored.
- [x] Decision record: `docs/vision.md`, `docs/language/1.0-gap-audit.md`, lineage evidence (§4 below), proving programs and gates (`plan.md` §5–6), cautionary tales (`plan.md` §7).
- [x] **Milestone 4 — composites** (`b6f24f4`). Tuples as anonymous structs in slots (`FieldAddress`, `Memcpy`); optionals as `u8`-tagged two-case enums with the payload after the tag; `str`/`bytes` as `{pointer, i64 length}` with structural equality (inline byte loop); `print` of a `str` value. Established the **aggregate protocol**: a register of aggregate type holds an address, copies are explicit `Memcpy`, aggregate results go through a hidden leading pointer parameter, aggregate parameters are passed by pointer (`lowerer.luc` header, `mir.md`).
- [x] **Structs and methods** (`78dd669`). Fields with `let`/`var`/`pub` and constant defaults; the synthesized memberwise initializer with the spec §10.1 visibility rule; field access and `root.a.b = v` places; methods with `self`; `mutating` methods (receiver must be a mutable place; lowered as stores through the pointer the aggregate protocol already passes); type functions; struct equality; structs inside tuples/optionals; cross-module `module.Struct`. Gate met: `HirStruct`/`HirField`/`HirFunction`/`HirModule` retain documentation, `HirParameter` retains `default_value`, defaults are embedded at call sites. Deferred to the failure slice: custom `init`.

## 3. Bugs the three-way harness found

Kept as evidence that the testing strategy (`plan.md` §1) earns its cost. Four of the six were in "reference" implementations.

1. HIR oracle: `~0u8` produced `-1` (signed complement on an unsigned type).
2. HIR oracle: i64 arithmetic computed before the range check, tripping the host.
3. MIR interpreter: `shift_left` trapped on bits shifted out; `min % -1` trapped (spec says 0).
4. Wasm: u32 constants above the i32 maximum emitted an invalid LEB; a function ending in an `If` with returning arms failed validation (needs a trailing `unreachable`).
5. Both interpreters: `1 << 63` overflowed the host — replaced by `shift_left_within`.
6. MIR interpreter: a `Loop` consumed a branch depth twice, so a `BrIf` carrying values out of a loop dropped them. Invisible until milestone 4's string equality (`while` branches carry nothing). Pinned by `test_branch_out_of_a_loop_delivers_its_values_to_the_block`.

## 4. Where this came from — the lineage and the evidence

Recorded 2026-08-27 after reading `docs/vision.md`, `docs/language/1.0-gap-audit.md`, kinogaki.com, the Sweeney/Fridman transcript (Verse, correctness, concurrency, UE6), and the three predecessor repositories in `~/dev` (`prism`, `kinogaki`, `luciaos_v1`; read by subagents, nothing built or run).

### 4.1 Four repositories, one lineage

Each stopped at a planning boundary rather than a bug:

| Repo | Dates | What it is | Why it ended |
|---|---|---|---|
| `prism` | 2026-06-13 → 06-19 | SwiftUI/Metal spectral raytracer that grew a USD-shaped Stage/Prim/Path model, rewrote it in C++, then dropped Swift entirely ("three live representations" of the scene; `PRISMCORE_CPP_PLAN.md`) | core extracted into kinogaki |
| `kinogaki` | 06-20 → 07-12 | The C++20 platform: Prism core (Value = dtype+shape+flat buffer, `Compose.h` diff/overlay/merge/conflicts/renames, `Schema.h`, `EventLog.h`, `Query.h`, codecs), UI, platform, storage journal, crypto, auth, ai/MCP, wasm guest host; ~120k LOC, ~5k test assertions, 22 nested repos | last commits are `planning/`; `APP_PLATFORM.md` frozen "next critic is implementation" |
| `luciaos_v1` | 07-13 → 07-24 | Same core generalised into an OS: terminal / realm / documents; programs are `app` elements holding sealed wasm; run document in, out document out; signed journal with one acceptance rule; ~98k LOC, ~1.2k tests, no Python | last commit is `planning/REALM.md` with zero implementing commits; `BOOTSTRAP.md` already names "Lucia language as the authoring layer; compiler itself as a command document" |
| `luce` | 08-21 → | the language | — |

The durable world is **not** on paper: diff/overlay/merge/schema/event log, the signed journal and acceptance rule, store-and-forward sync with rebase-and-replay, per-reader sealing, and wasm guest confinement all exist with tests. What is paper: `kino://` addresses (zero hits in code), cross-realm capability links, sibling-version conflicts, fuel metering and kill-switch ("wasm3 CANNOT interrupt a pure compute loop"), the kernel/process table, and the whole authoring ladder. `APP_PLATFORM.md` explicitly rejected a bespoke VM in favour of wasm — Luce is consistent with that: a language that *compiles to* wasm, not a new instruction substrate.

### 4.2 The pain point, from the code rather than the vision

1. **The guest seam is the worst code in the lineage, and it is the exact place ordinary people would write.** `kinogaki-os/tests/fixtures/echo_guest.c` and `luciaos_v1/software/terminal/commands/lucia_guest.h` + 11 seed commands: freestanding C, `-nostdlib`, a bump allocator that never frees, `.prisma` requests as string literals and replies parsed by substring search into fixed `char[512]`/`[8192]`/`[65536]` buffers; `grep.c` supports 4 roots because that is an array size. The guest ABI is tiny and frozen: imports `lucia_call(ptr,len) -> i64 (ptr<<32|len)`, `lucia_log`, `lucia_yield`; exports `lucia_alloc`, `lucia_main`; one tool namespace `lucia:os/doc` with verbs open/list/find/put/mkdir/rm/move/connect/disconnect. **The guest has no typed property access at all** — `put(path, text)` is the only write; the rich typed vocabulary (`set_property(path, name, value, dtype)`, `define_element`, validate, commit) lives only in the trusted in-process MCP tools (`kinogaki-ai/src/DocTools.cpp`), which already do copy → mutate → `applyAuto` → roll back on refusal.
2. **Errors die at every seam.** `capiTry` swallows everything to NULL/false/NaN; `os::Abi` collapses every failure to `unavailable`; core mixes `optional`, thrown `invalid_argument`, and stringly `Committed{id,error}` (419 `optional`, 0 `expected`). Silent swallowing is the most repeated theme in the issue tracker.
3. **Serialization and tables by hand, everywhere.** ~2.1k LOC of text/binary/package codecs plus LZSS and f16 bit-twiddling; 110 `case Type::` arms for a 10-variant `Value`; every value type re-encoded at the C, ctypes, JSON-schema, and MCP layers; enums and verb tables kept in three copies; the same worker-thread + queue + main-drain shape written three times; every shader three times.
4. **Borrowed pointers documented, not enforced.** The C ABI hands back `const char*` from two process-wide `thread_local` strings (call any two getters and the first dangles); query results are borrowed `const Element*` "invalidated by the owner's lifetime"; COW correctness rests on `use_count()!=1`. Zero memory-safety bugs were filed — the code is careful by convention.
5. **One source for wasm and native is not achievable in C++.** `#if __EMSCRIPTEN__` swaps whole class internals; `webstubs.cpp` exists only to `abort()` in link-reachable dead paths; 18 packages × 2 hand-maintained build systems + emscripten.
6. **The named OS blocker is a compiler job.** `OS_ARCHITECTURE.md` stalls the kernel on per-instruction fuel and preemption that wasm3 cannot provide. A backend that inserts fuel checks at loop back-edges and calls makes any engine preemptible.

Sweeney's four pains (code from millions of authors upgrading live; "if it compiles it works"; concurrency nobody writes by hand; security as the language's job) map onto this concretely: a behavior that receives a snapshot and returns a diff cannot break anything; workers get O(1) snapshots and emit diffs and `merge` reports conflicts — the transaction at document granularity with no STM; live upgrade is `luce api diff` on code plus schema diff on data over signed commits; and safety for the C++ replacement is the language's job.

### 4.3 What that fixed in the plan

The proving programs (`plan.md` §4): first the seed guest commands rewritten in Luce and run unmodified under the existing `WasmHost` ABI, then the host itself — terminal, realm, storage, crypto, network, `WasmHost` — as native Luce with the wasm engine as a Luce library. Every gap-audit item was additive to MIR; failure-as-data is exactly the error model the seams lack.

## 5. Stage-0 history

- 0.20: errors through interface-typed calls silently trapped — worked around in the pipeline, reported, fixed in 0.22; regression test `test_backend_errors_cross_the_interface_boundary`.
- 0.22: call depth 128 host frames; temporary-receiver / optional-field use-after-free — reproductions bundled in `build/stage0-0.22-repro.tar.gz`, fixed in 0.23; depth raised to 32768.
- Withdrawn after checking: "`return` in a statement-form `catch` does not return" — it does.

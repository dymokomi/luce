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
| Lowerer (`lowerer.luc`) | Slices 3a–3c done: scalars and locals, control flow, calls/parameters/constants. Not yet: tuples, optionals, strings as values, and everything HIR does not generate. |
| WebAssembly backend | Everything the lowerer emits, with spec semantics (checked arithmetic, floor division, trapping shifts), WASI preview 1 host contract, shadow stack with overflow guard. Executed under `wasmtime` in tests. |
| Native backends (arm64 Mach-O, x86-64 ELF) | The original slice only: constants, checked add/sub/mul, `print` of a literal, `return` from `main`. Direct executable writers, no linker. **Not extended on purpose** (see §4). |
| Tests | 355 unit tests; CLI contract script; `wasmtime` execution script; native smoke script (arm64 hello + overflow trap). `tests/compiler/differential_test.luc` runs ~70 fixtures through HIR interpreter, MIR interpreter, and every encoder and requires agreement. |
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
in the "reference" implementations. Keep it.

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
- **Open questions**: narrow integers as MIR types (current) vs normalized to i32/i64 with widths only at struct fields and C signatures (what wasm and QBE want) — decide when the native pass starts; optionals of references as null niche (plan) vs uniform enum; fallible ABI per backend (wasm multi-value, QBE out-pointer/aggregate — never a global).

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

## 6. Order of work from here

1. **Lowerer milestone 4 — composites the HIR already has**: tuples (anonymous structs in slots, `FieldAddress`, `Memcpy`), optionals (two-case enums with tag + `Switch`, or the null niche for references), `str`/`bytes` as values and `print` of a variable (string representation through the runtime). First real use of aggregate layout on both interpreters and wasm.
2. **Grow HIR generation**, each feature landing on the lowerer once composites settle: structs and methods, enums and `match`, `for` and ranges, `defer`, `try`/`catch` and `Error`, classes with ARC (this is where `SemanticAnalyzer` starts producing ownership facts), closures, interfaces, generics (monomorphization), lists/maps/sets and strings via the runtime, formatted strings, `spawn`/tasks, extern/export.
3. **Runtime `libluce_rt`** in Luce alongside step 2, first through the MIR interpreter's stub runtime, then compiled.
4. **Native rung 1** (dyld imports + signing) once `extern` exists in HIR — small and independently valuable.
5. **`docs/compiler/native.md`** and the arm64 QBE-shaped pass once MIR stops moving; then x86-64.
6. Self-hosting follows from 2–5 plus the Stage-0-subset rule; one pinned prior compiler is kept forever for bootstrapping.

Each step is a vertical slice gated by the three-way harness plus executed wasm. Commit after every green step with a short message.

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

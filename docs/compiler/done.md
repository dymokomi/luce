# Compiler record — what is done and why we believe it

This is the record half of the compiler's planning pair. It says what exists,
what each milestone proved, which bugs the harness caught, and where the
project came from. The other half, [`plan.md`](plan.md), holds the decisions
and the work that is still ahead; read that one to resume work, read this
one to check a claim. Every tick here has a commit and a green `./test.sh`
behind it.

Last updated: 2026-08-30 (Stage-0 0.28).

## 1. Where things stand

| Layer | State |
|---|---|
| Tokenizer, parser, syntax tree | Complete for the 1.0 surface (`docs/language/1.0.md`); every syntax form has parser coverage. Throughput is linear (~450 KB/s); expression nesting is capped at 256 with a diagnostic. |
| HIR generation (`hir/generator.luc`) | Functions, direct calls, exact named `func`/`cfunc` values and shared indirect calls, parameter defaults, locals, assignment, all scalar types, `str`/`bytes`/`char` literals, `bytes.length`, checked `bytes[u64]`, `str.byte_count`, fixed value arrays with contextual literals/copies/equality/length/checked access and mixed field/element assignment places, tuples, optionals with `else`, integer ranges and `for`, lexical `defer`, `ErrorCode`/`Error` with `try`/`catch`, structs and enums with custom initialization, methods/`mutating`/type functions, field access, `match` (statement and expression, exhaustive), restricted module constants, type aliases, direct scalar `extern func`/`export c func`, ordered C `out` results, nominal integer- and pointer-represented extern handles, and observable scalar `extern var` state, `if`/`elif`/`else`, `while`, `break`/`continue`, `return`, `print` of a literal or `str` value; documentation and defaults retained. **Not yet**: classes, closure environments and infallible-function lifting, interfaces, generics, executable `try for`, lists/maps/sets, formatted strings, and the remaining rich C boundary (strings, extern structs, exported structs/enums, dynamically supplied/nullable cfunc pointers). Each unsupported form fails with a span. |
| HIR interpreter (`backends/interpreter.luc`) | The semantic oracle. Executes everything HIR generation produces. Runs `main(arguments: slice[str])` with an empty slice. |
| Canonical MIR (`mir/canonical.luc`) | Target-neutral and designed for the whole language (`mir.md`); verifier (`mir/verifier.luc`) proves every rule; target-neutral reachability removes unreachable closed-world functions and their resources before backends; MIR interpreter (`backends/mir_interpreter.luc`) executes every instruction under explicit backend layout rules. |
| Lowerer (`mir/lowerer.luc`) | Everything HIR generates: scalars and locals, control flow, direct and exact Luce/C indirect calls, constants, tuples, fixed arrays, optionals, `str`/`bytes` values, structural equality, lengths and checked sequence indexing, integer ranges and `for`, lexical `defer`, caller-owned failure propagation and recovery, structs, enums, `match`, methods, `mutating`, mixed aggregate places, direct scalar C imports/exports and external variables, nominal handle erasure, pointer/null and output-slot boundary adapters, demand-generated cfunc adapters, and shared C-export wrappers, `print` of a value. |
| WebAssembly backend (`backends/wasm.luc`) | Everything the lowerer emits, with spec semantics (checked arithmetic, floor division, trapping shifts), exact Luce/C indirect calls through an on-demand definition-and-import table, WASI preview 1 host contract, C calls and mutable C globals as `env` imports, exact exports, shadow stack with overflow guard, `memory.copy` for aggregates. Executed under `wasmtime` in tests. |
| QBE backend (`backends/qbe.luc`, `qbe_toolchain.luc`) | Direct canonical-MIR → QBE 1.3 IL with backend-owned 64-bit layout, structured-control flattening, checked arithmetic, direct/indirect calls, memory and aggregate operations, QBE C ABI extension types, exact C function/object symbols, and a private caller-owned fallible-result ABI. The product path streams IL and assembly through memory, links in secure same-directory scratch, and atomically installs the executable. The complete differential corpus uses this path. |
| Tests | 462 unit tests across 15 files, plus CLI, `wasmtime`, QBE differential, and host-native smoke gates. `tests/compiler/differential_test.luc` runs the complete non-trapping and trapping corpus through HIR, optimized MIR, and the QBE product toolchain and checks values, output, and traps. |
| Toolchain | Stage-0 0.28 and official QBE 1.3 source are checksum-pinned in `bootstrap.sh`. Remaining constraints are in `plan.md` §8. |

## 2. Done, in order

- [x] Tokenizer, parser, syntax tree for the whole 1.0 surface, with per-form tests.
- [x] HIR generation for scalars, locals, control flow, calls, constants, tuples, optionals, `str`/`bytes`/`char` literals, `print` of a literal.
- [x] HIR interpreter as oracle (spec §7 arithmetic, `frame_limit = 2000`, measured rather than inherited — `plan.md` §8.1).
- [x] Canonical MIR contract, verifier, MIR interpreter (`mir.md`).
- [x] **Canonical MIR is target-neutral** (2026-08-30). Removed target names,
  pointer width/alignment, aggregate byte sizes and offsets, slot alignment,
  and target-sized data relocations from MIR. `FieldAddress`,
  `ElementAddress`, and `EnumPayloadAddress` retain logical structure; one
  lowering now feeds every backend. Backend-owned `TypeLayout` computes and
  caches byte placement. `test.sh` rejects backend imports and concrete target
  concepts in frontend/HIR/MIR, and the full 392-test plus CLI/Wasm/native
  diagnostic suite is green.
- [x] **QBE is the native oracle** (2026-08-30). One compact backend translates
  verified canonical MIR directly into QBE IL; it computes 64-bit aggregate
  layout locally, flattens structured regions without a second shared IR, and
  legalizes Luce arithmetic and failure results. Official QBE 1.3 is pinned by
  checksum and installed by `bootstrap.sh`; `test.sh` refuses to silently skip
  it. All current non-trapping fixtures compile, link, and agree on result and
  output; every trapping fixture first compiles successfully and then traps
  (`facc3c3`).
- [x] **QBE is the product native path** (2026-08-30). `luce build --target
  native` feeds IL and assembly through child-process stdin, captures tool
  diagnostics, links inside Stage-0 0.28's atomically owned temporary
  directory beside the destination, and installs by same-filesystem rename.
  Missing-QBE and missing-linker regressions prove cleanup and preservation of
  an existing artifact. The partial handwritten Mach-O/ELF encoders and their
  duplicated platform smoke scripts were removed after QBE replaced them.
- [x] **C callables have one HIR identity** (2026-08-30). The first
  extern/export rung—direct scalar functions—uses one function table, symbol,
  import resolver, argument checker, and `Call` node for Luce definitions,
  C exports, and C imports. A closed implementation union makes the three
  origins explicit; lowering is the only point that maps the identity to a
  MIR `FunctionId` or `ExternId`. Equal C declarations share one MIR extern
  and conflicting signatures fail before a backend. Both semantic oracles
  use explicit hosts, Wasm alone chooses the `env` namespace, and QBE links
  libc while preserving exact exports and narrow signedness at its ABI edge.
- [x] **Integer extern handles stay nominal until MIR** (2026-08-30).
  `extern type Pid = i32` has a distinct HIR `TypeId`, module visibility, and
  retained documentation. Literals and arithmetic cannot forge or inspect a
  handle; equality and ordinary calls use the existing typed HIR paths. The
  lowerer performs the sole erasure to its declared integer representation,
  after which unchanged canonical MIR feeds explicit MIR hosts, Wasm `env`
  imports, and QBE. A real libc `getpid` fixture compiles, links, and executes.
- [x] **Pointer extern handles translate null only at C boundaries**
  (2026-08-30). HIR uses a distinct opaque foreign token while `Window?`
  remains the ordinary tagged optional. The single target-neutral MIR lowerer
  converts that optional to and from a raw pointer at imports and shared C
  export wrappers; a zero token crossing any bare pointer-handle slot traps
  `null_foreign`. Source calls to an exported function still call its private
  Luce-convention body. Both semantic oracles cover null/live imports and
  exports; Wasm consumes the same MIR; real QBE/libc `malloc`/`free` execution
  proves live, nullable-null, and trapping-bare paths.
- [x] **C output parameters use the same target-neutral boundary adapter**
  (2026-08-30). HIR keeps one ordered contract whose input slots refer to
  ordinary source parameters and whose output slots become source results;
  the declared non-void result precedes outputs, with ordinary scalar/tuple
  shaping. MIR allocates raw call-owned slots, passes abstract pointers, and
  decodes their loads after the call—no layout or ABI placement enters the
  lowerer. The HIR oracle returns explicit output values while the MIR host
  writes through a narrow memory view. Wasm encodes the same MIR, and a real
  QBE/libc `posix_memalign(void **, ...)` execution proves nullable pointer
  output, allocation, and cleanup end to end.
- [x] **External C variables remain observable state through every shared IR**
  (2026-08-30). One HIR table and explicit load/store nodes preserve source
  identity and mutation; one canonical MIR external-global table and explicit
  operations keep the object distinct from compiler-owned storage without an
  address, ABI, or platform fact. Equal cross-module declarations share one C
  identity; type conflicts and function/global/runtime namespace collisions
  fail before a backend. Separate HIR/MIR variable hosts prove the semantics,
  Wasm imports mutable `env` globals without disturbing its independent
  function index space or shadow stack, and QBE uses its explicit GOT/PIC
  dynamic-symbol form to link and mutate libc-owned process state. Bare
  pointer-handle zero remains ordinary global state rather than acquiring
  callable-boundary null behavior.
- [x] **Stage-0 examples became measured compiler-progress inputs**
  (2026-08-30). The 0.28 corpus at `d5b4583` is catalogued by capability in
  `examples/README.md` instead of copied wholesale. The adapted
  recursive-descent calculator parses under the current 1.0 surface and pins
  its first HIR gap. The inventory independently confirms that collections,
  indexing/slicing, and string/runtime primitives unlock most small and medium
  real programs, matching the existing runtime-before-collections plan.
- [x] **The first adopted Stage-0 program is a native QBE execution gate**
  (2026-08-30). Core byte access uses two explicit HIR nodes for sequence
  length and checked indexing; lowering reads the existing structural
  `{Ptr, u64}` representation, compares a `u64` index, and reaches the byte
  through `ElementAddress` with an explicit trap arm. No byte offset or target
  fact entered HIR/MIR, and `str` integer indexing remains deliberately
  rejected. The calculator was adapted to scan UTF-8 `bytes`, typed errors and
  the current entry contract; it now checks, builds through the product QBE
  toolchain, links, executes, and returns success. HIR, MIR, Wasm and QBE
  differential fixtures cover byte length, UTF-8 byte count, indexing and the
  out-of-bounds trap.
- [x] **Closed-world reachability has explicit roots** (2026-08-30). The
  recovery implementation was not reused: its `pub`/artifact-export
  conflation was removed from canonical MIR. Package visibility, explicit C
  export and the independently selected process entry are separate facts. The
  optimizer traces their calls and function addresses, preserves original
  order, remaps every surviving identity, and removes unreachable functions,
  externs, external globals, globals and data. Rootless private libraries
  remain intact rather than pretending an absent root set means an empty
  program. Pre/post verification and the complete differential QBE corpus
  exercise the pass; Wasm alone chooses to expose package-public functions.
- [x] **Fixed arrays use the existing aggregate protocol end to end**
  (2026-08-30). `array[T, N]` is interned by element identity and nonnegative
  count in HIR; bracket literals require that context and check exact arity.
  Arrays are inline values with structural equality, constant `u64` length,
  checked reads, value copies, zero-length support, mutable nested places, and
  mutating method receivers reached through array elements. Equality lowers
  to one canonical MIR loop rather than expanding with the type's count.
  `PlaceAssignment` replaces the field-only assignment form with compact
  resolved `(field | element, payload)` steps, so `grid.rows[i][j]` has one
  semantic path and index expressions still evaluate once in source order.
  The lowerer maps this directly to canonical MIR `Array`, `Memcpy`, and
  `ElementAddress`; layout remains entirely backend-owned. Both semantic
  oracles, Wasmtime encoding/execution, and real QBE cover aggregate
  parameters/results, nested mutation, copy isolation, equality, and bounds
  traps. The execution gate exposed and fixed Wasm's zero-size-frame case:
  logical zero-size slots still receive an initialized address local without
  moving the shadow-stack pointer. Stage-0's `sort` example is adapted to fixed
  storage as `examples/stage0_sort.luc` and checks, links, and executes through
  the native product path. The runtime audit also recorded the next honest
  dependency: allocator work waits for a target-neutral allocation contract
  instead of putting heap policy or target byte layout in the compiler.
- [x] **Stage-0 Brainfuck is an allocation-free whole-program gate**
  (2026-08-30). `examples/stage0_brainfuck.luc` retains the upstream
  interpreter's bytecode loop, bidirectional bracket matching, nested control
  flow, `match`, wrapping `u8` cells and output validation. Only storage
  ownership changed: fixed tape/output capacities replace the original
  runtime-sized array and builder, without adding a compiler-only collection
  path. The HIR oracle answers 42, the same canonical MIR builds as Wasm, and
  the installed native QBE executable exits successfully.
- [x] **The runtime allocation boundary is settled before implementation**
  (2026-08-30). The lowerer will request a runtime count of a structural MIR
  type, never target bytes or alignment; backend legalization alone converts
  that request to the bound private allocator's byte signature. Allocation
  ownership,
  zero-count/zero-size behavior, overflow and exhaustion are explicit in spec
  §23.4. The sealed, freestanding `libluce_rt` package owns allocator policy
  and is composed with application MIR before optimization. Reviewed
  `.native.luc` modules retain typed pointee identities and can reach only a
  stable, monotonically committed arena capability; Wasm growth and native
  reservation remain backend implementations. This checkpoint recorded the
  guardrails implemented by the following substrate; it did not claim the
  production allocator.
- [x] **Typed storage now crosses canonical MIR and both artifact backends**
  (2026-08-30). `AllocateStorage(TypeId, u64)` preserves element structure
  until a backend computes bytes and alignment. One verified program-level
  binding points to the exact private `(u64, u64) -> Ptr` Luce allocator
  function; optimizer reachability follows and remaps it only from live
  allocation instructions. The MIR oracle uses semantic test memory without
  executing allocator policy. QBE and Wasm directly call the composed
  function after enforcing zero-count null, positive zero-size one-byte
  storage and count-by-size overflow traps; native QBE and Wasmtime execute
  all three cases. The former `luce_rt_alloc` extern route is gone, so MIR
  cannot smuggle target byte layout around the typed instruction. The
  production sealed runtime and source collection lowering remain pending.
- [x] **Sealed runtime composition is an explicit MIR stage** (2026-08-30).
  The application keeps all of its canonical identities while the separately
  compiled runtime has every structural type and table reference remapped
  once. Identical external declarations are interned; conflicting C
  function/object shapes fail during composition. Only the runtime may supply
  service bindings, and it may expose neither a process entry nor public or
  artifact functions. Verification and reachability run on the one combined
  program, retaining the private allocator through a live typed-allocation
  edge and pruning unrelated runtime code. Tests cover every remapped table,
  input immutability, service identity, external interning and sealed-boundary
  diagnostics. Production runtime source and its freestanding analysis are
  still pending.
- [x] **Exact ordinary function values reuse the canonical callable model**
  (2026-08-30). A named, capture-free Luce declaration has an exact `func`
  type and explicit `FunctionAddress` HIR form; calls through values are
  positional `IndirectCall`s, distinct from declaration labels/defaults and
  from method resolution. Values can be constants, selected conditionally,
  stored in structs, passed and returned, deferred, and imported from another
  module, with scalar, aggregate, unit or fallible signatures. HIR and MIR
  oracles agree on callee-before-arguments evaluation. Lowering maps the type
  to canonical MIR's opaque pointer-shaped call token and emits the existing
  `FunctionAddress`/`CallIndirect` protocol once; reachability retains and
  remaps address-only targets. QBE executes the complete new differential
  corpus natively. Wasm interns indirect signatures and emits a funcref table
  and element segment only for modules that use them; a hand-built verified
  module executes under Wasmtime. `examples/function_values.luc` checks,
  executes semantically, builds to Wasm, links through QBE and exits cleanly.
  Closure environments, method captures, and non-fallible-to-fallible adapters
  remain explicit later work rather than hidden compatibility code.
- [x] **Exact named cfunc values preserve one call shape until MIR**
  (2026-08-30). `cfunc(P...) -> R` is a distinct canonical HIR type, but its
  invocation is the same positional `IndirectCall` used by `func`. Contextual
  conversion of a named Luce definition requests one C-convention adapter;
  conversion of an exact extern name retains the symbol itself. Only canonical
  MIR records the split with a convention-bearing `CallIndirect` and
  `ExternAddress`. C-shaped nullable handle slots use the existing boundary
  encoder/decoder rather than a duplicate callback lowering. Optimizer
  reachability follows both address kinds. Both semantic oracles, verified
  MIR, Wasm's backend-owned function table, native QBE/libc symbol calls and
  a real libc-to-generated-adapter callback,
  the differential corpus, and `examples/cfunc_values.luc` agree. Dynamic and
  nullable function pointers arriving from C, plus lambda/closure conversion,
  remain explicit later rungs.
- [x] Lowerer 3a–3c: scalars and locals, control flow, calls/parameters/constants.
- [x] Wasm backend for everything the lowerer emits; WASI host contract; executed under `wasmtime` in `tests/wasm_test.sh`.
- [x] Native rung 0 proved direct image writing for the original slice; removed
  after the QBE product path superseded it, so stage 1 has one native path.
- [x] Stage-0 0.22 → 0.23: interface-error trap and temporary-receiver use-after-free reported with reproductions (`build/stage0-0.22-repro.tar.gz`), fixed upstream, workarounds removed; call depth raised, deep-recursion fixtures restored.
- [x] Decision record: `docs/vision.md`, `docs/language/1.0-gap-audit.md`, lineage evidence (§4 below), proving programs and gates (`plan.md` §5–6), cautionary tales (`plan.md` §7).
- [x] **Milestone 4 — composites** (`b6f24f4`). Tuples as anonymous structs in slots (`FieldAddress`, `Memcpy`); optionals as `u8`-tagged two-case enums with the payload after the tag; `str`/`bytes` as `{pointer, u64 length}` with structural equality (inline byte loop); `print` of a `str` value. Established the **aggregate protocol**: a register of aggregate type holds an address, copies are explicit `Memcpy`, aggregate results go through a hidden leading pointer parameter, aggregate parameters are passed by pointer (`mir/lowerer.luc` header, `mir.md`).
- [x] **Structs and methods** (`78dd669`). Fields with `let`/`var`/`pub` and constant defaults; the synthesized memberwise initializer with the spec §10.1 visibility rule; field access and `root.a.b = v` places; methods with `self`; `mutating` methods (receiver must be a mutable place; lowered as stores through the pointer the aggregate protocol already passes); type functions; struct equality; structs inside tuples/optionals; cross-module `module.Struct`. Gate met: `HirStruct`/`HirField`/`HirFunction`/`HirModule` retain documentation, `HirParameter` retains `default_value`, defaults are embedded at call sites.
- [x] **Enums and `match`** (2026-08-28). Enums as closed sums with named payloads, `Enum.case`, `.case` from context (through an optional too), `module.Enum.case`, enum methods and type functions (receivers now name an owner `TypeId`, shared with structs), structural enum equality, self-containment rejected. `match` as statement and expression: enum/optional case patterns with payload bindings (alternatives share one binding set), literal and range patterns for integers/chars/bools/strings, `_`; exhaustiveness for enums, optionals and bools; duplicate, overlapping and unreachable patterns rejected. Lowered as an `If` chain that tests the subject once, arms nesting in each other's `Else`; expression form yields through a `Block`. The oracle's recursive walkers were split into small functions after the unbounded-recursion fixture overflowed the host stack (frames grew with the new arms).
- [x] **MIR instructions are fixed-size** (2026-08-28). `Call`/`CallExtern`/`CallIndirect`/`Block`/`If`/`Br`/`BrIf`/`Yield`/`Return` name `RegisterRun{start, count}` into `MirFunction.operands` instead of holding a `list[RegisterId]`; `OperandBuilder` collects runs while a body is built; consumers read `register_at`. With flat regions this makes a MIR body two contiguous arrays.
- [x] **HIR is one flat node table** (2026-08-28). Statements and expressions are `HirNode`s stored inline in `HirProgram.nodes`; `form` is the named union (pattern matching unchanged), children are `NodeId`s, child lists are `Operands` runs in `extra` (suites, call argument pairs, if-branch triples, resolved place paths), literal values in `values`, result types and spans in parallel arrays. `hir_gen` builds bottom-up with `push_node`; the oracle and lowerer read through `node_form`/`node_at`/`entry_at`. Zero harness differences.
- [x] **MIR is flat** (2026-08-28). `Block`/`Loop`/`If`/`Switch` open a region in the body list, `Else`/`Case`/`Default` separate arms, `End` closes; `MirInstruction` is a struct stored inline. Verifier, MIR interpreter, and wasm backend became single linear passes with a region stack (`mir/verifier.luc`, `mir_interpreter.luc` `plan_regions`, `wasm.luc` `encode_body`); the lowerer emits regions in place. The harness caught one bug in the rewrite (loop-restart branch popped every region). Design: `mir.md` "Control flow".
- [x] **Layout decisions recorded** (2026-08-28, `plan.md` §5 self-hosting and §6 rules): shape now, tuning at the self-hosting measurement; hybrid flat tables (named union payloads, `u32` links, cold fields in parallel arrays) rather than Zig's raw `{tag, lhs, rhs}`, because Luce has no `comptime` to generate the readability back.
- [x] **Spans are 16 bytes** (2026-08-28). `SourceSpan` is four `u32`s instead of four `i64`s; it sits in every token, syntax node, HIR node, and MIR instruction. Tokens keep their `str` text for now (front-end-only cost).
- [x] **Ids are `u32`** (2026-08-28). `TypeId`, `SymbolId`, `ModuleId`, `RegisterId`, `FunctionId`, `ExternId`, `GlobalId`, `DataId` hold a `u32` index; `no_register` (`u32` max) replaces the `-1` sentinel. The first data-oriented-layout item (`plan.md` §5). The `i64(...)` widening every index site needed under Stage-0 went away in 0.26, which indexes with any integer: 98 conversions deleted 2026-08-29.
- [x] **Stage-0 0.26 adopted** (2026-08-29). Six `discard(...)` sites for the new unused-result rule, and a parser refactor that made 113 more unnecessary — `expect_symbol`/`expect_kind`/`expect_keyword` answer nothing now, `step()` moves past a token where `advance()` answers the one it moved past, and the eleven callers that wanted the token read `current()` first. Installed from the pre-release archive at `86b97fac`; `bootstrap.sh` holds the Linux checksum at `TBD` until CI publishes it. The exchange, including the request list and what the team answered, is in `stage0-0.26.md`.
- [x] **Stage-0 0.27 adopted** (2026-08-30). Both release archives are
  pinned by published checksums. The reported quadratic `str` traversal is
  fixed upstream: the unchanged 20k–160k-character reproduction takes
  0.12–0.15 s per complete case. The clean 392-test, CLI, Wasm, and native
  gate passed; evidence is in `stage0-0.27.md`.
- [x] **Stage-0 0.28 adopted** (2026-08-30). Both host archives are pinned by
  their published checksums. The release adds the atomic, owner-only
  `files.make_temporary_directory` operation needed by QBE product
  materialization. The complete 405-test, QBE differential, CLI, Wasm, and
  native gate passes under the new module-format 73 and host-ABI 32 toolchain.
- [x] **The front end is linear** (2026-08-29, `recursion.md` §5). It was quadratic in file size: 8,000 statements took 179 s, 8,000 comment lines took 25 s. Three causes — bracket matching scanned per nesting level, `len(self.source)` sat inside the scanning loops, and `str` indexing walks the string in Stage-0 (`text[i]` is O(i), `for c in text` is O(n²), `text[a:b]` is O(a)). The tokenizer now decodes `bytes(source)` once into a `list[char]`, scans that, and builds token text with `text_between`; the parser precomputes bracket matches in `match_brackets`. Same inputs: 0.42 s and 0.07 s, and 1.4 MB in 3.1 s. Reported upstream for 0.27 with a reproduction (`build/stage0-0.27-repro/`), since the `str` cost is Stage-0's and it bounded self-hosting.
- [x] **Expression nesting is bounded** (2026-08-29). 26,250 nested parentheses took SIGBUS; 25,000 did not. `parse_expression` counts its depth and refuses past 256 — Swift's and Clang's number, from the C++ standard's recommended minimums — with `expression nests deeper than 256`. Pinned by `test_expression_nesting_is_bounded`. The crash had been invisible because the old tokenizer took minutes to reach that depth: fixing throughput is what exposed it.
- [x] **Integer ranges and `for`** (2026-08-29). `range[T]` is an immutable `{lower, upper, inclusive}` value for every implemented integer width; it can be bound, compared, passed, and returned under the aggregate protocol. `for` binds each element immutably, handles empty and closed ranges, and gives `continue` an inner block so it reaches the increment rather than restarting the same value. A closed range ending at the type maximum stops before incrementing. The HIR oracle, MIR interpreter, and wasm agree on half-open/closed/empty/max ranges, nesting, break/continue, early return, and range aggregate calls. The gate is settled separately in the spec: `try for` selects `FallibleIterable[T]` and makes propagation visible; its executable path waits for the failure ABI.
- [x] **Lexical `defer`** (2026-08-29). A unit-producing call's receiver and arguments are copied into hidden HIR bindings when registered, so later mutation cannot change the cleanup. The oracle runs actions LIFO at the end of each lexical scope. The lowerer duplicates the captured calls on fallthrough, `return`, `break`, and `continue`, with loop boundaries preventing an inner exit from running an outer cleanup; return values are evaluated before cleanup. Traps deliberately skip cleanup. HIR/MIR/wasm fixtures cover capture timing, ordering, nested scopes, unit fallthrough, both loop forms, and silent traps.
- [x] **Fallible MIR has explicit ownership** (2026-08-29). Every fallible function receives its caller-owned `Error` slot in r0, reports null on `Return`, and returns that same r0 on `Raise`; no error points into a dead callee frame or needs runtime allocation. The verifier proves the signature and terminator rules, the MIR interpreter executes them, and wasm restores its shadow frame before returning the default value plus error pointer. A wasmtime regression covers success, failure, and wasm's reverse multi-result stack assignment.
- [x] **Source failure is explicit data and control** (2026-08-29). `ErrorCode.package` accepts restricted constant `u32` expressions, rejects duplicates package-wide, and embeds an explicit compilation identity rather than a path-derived name. `T!` is confined to the outer result of a function; parameters, bindings, constants, fields, payloads, nested effects, and unhandled values are rejected. The HIR oracle models raise/recover as explicit transfers, never host-language errors. Lowering covers scalar, unit, aggregate, conditional, and match-produced fallible values; `try` copies failure into the caller's slot, `catch` binds ordinary `Error` data, and both run the correct deferred suffix. Differential and wasmtime fixtures prove success, propagation, recovery, code/message inspection, and defer order. The compiler API takes `PackageInput`; the raw CLI requires `--package ID`.
- [x] **Custom struct initialization** (2026-08-29). A receiver has one closed protocol (`type_function`, value method, mutating method, or initializer), and construction is an explicit `Initialize` HIR node rather than a call whose result is reinterpreted later. `SemanticAnalyzer` now performs the first whole-program flow proof: a three-state field lattice joins continuing `if`/`match`/`catch` paths, rejects writes in repeatable regions, and proves every successful exit initialized each field exactly once before any read, method call, or escape of partial `self`. The HIR interpreter creates a private incomplete record; MIR passes fresh caller-owned aggregate storage as initializer `self`; fallible initializers add the existing caller-owned Error slot without a second ABI. Differential and wasmtime fixtures cover default/named arguments, branch initialization, success, and failure.

## 3. Bugs the multi-backend harness found

Kept as evidence that the testing strategy (`plan.md` §1) earns its cost.

1. HIR oracle: `~0u8` produced `-1` (signed complement on an unsigned type).
2. HIR oracle: i64 arithmetic computed before the range check, tripping the host.
3. MIR interpreter: `shift_left` trapped on bits shifted out; `min % -1` trapped (spec says 0).
4. Wasm: u32 constants above the i32 maximum emitted an invalid LEB; a function ending in an `If` with returning arms failed validation (needs a trailing `unreachable`).
5. Both interpreters: `1 << 63` overflowed the host — replaced by `shift_left_within`.
6. MIR interpreter: a `Loop` consumed a branch depth twice, so a `BrIf` carrying values out of a loop dropped them. Invisible until milestone 4's string equality (`while` branches carry nothing). Pinned by `test_branch_out_of_a_loop_delivers_its_values_to_the_block`.
7. QBE parser: floor-division adjustment mixed `w` and `l`, and unreachable
   structured tails could place a second terminator in the same block.
8. QBE execution: a then-arm fallthrough edge was not recorded when its else
   arm terminated, so a reachable join became `hlt`.
9. QBE execution: division by zero relied on target behavior, and `u64`
   arithmetic used the machine's full range instead of MIR's current `i64`
   ceiling. The trapping corpus caught both.

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
- 0.25: the batch we asked for landed — `pass`, multi-member match arms, file-scope `let`, `never`, `let`/`var` fields, `list[T?]`, 1,000,000 frames on 512 MiB, cached `luce test` artifacts. There is no 0.24: it was published and reverted the same day, and 0.25 folds it in.
- 0.25 adoption, in commits: `bootstrap on stage-0 0.25`, `fields say let or var` (480 fields, 440 immutable and 40 mutable — the compiler found every mutation), `empty arms say pass` (21 arms that said `continue` and meant nothing), `drop the parallel supplied lists`, `interpreter depth from a measured stack budget`.
- Bare `pub name: T` fields are accepted for 0.25 only and read as `var`, which is why the field migration was not deferred.
- 0.25's depth/stack pairing does not hold for compiler-shaped code; the measurement and its consequences are in `plan.md` §8.1.
- 0.26: every remaining request landed except the depth guard (§1). Adopted the same day from the pre-release archive: six `discard(...)` sites, the parser refactor that made 113 of them unnecessary, and 98 index conversions deleted. Suite green at each step. `stage0-0.26.md` carries the exchange, including their §1a reproduction of our two-ingredient finding and their reverted stack-pointer guard.
- 0.26 changed the default build to O1+FastISel, which costs about a quarter more stack per interpreted call than `--release`; `frame_limit = 2000` still clears the worst mode by 5×.
- 0.27 fixed the reported quadratic `str` traversal; measurements and the
  adoption gate are recorded in `stage0-0.27.md`.
- 0.28 added atomic temporary-directory creation and made string encoding
  metadata and callback context explicit. It also advanced the module format
  to 73 and host ABI to 32; the full compiler gate passes on the new formats.
- Withdrawn after checking: "`return` in a statement-form `catch` does not return" — it does.

# Compiler record — what is done and why we believe it

This is the record half of the compiler's planning pair. It says what exists,
what each milestone proved, which bugs the harness caught, and where the
project came from. The other half, [`plan.md`](plan.md), holds the decisions
and the work that is still ahead; read that one to resume work, read this
one to check a claim. Every tick here has a commit and a green `./test.sh`
behind it.

Last updated: 2026-09-03 (Stage-0 0.30).

## 1. Where things stand

| Layer | State |
|---|---|
| Tokenizer, parser, syntax tree | Complete for the 1.0 surface (`docs/language/1.0.md`); every syntax form has parser coverage. Throughput is linear (~450 KB/s); expression nesting is capped at 256 with a diagnostic. |
| HIR generation (`hir/generator.luc`, `declarations.luc`, `imports.luc`, `public_api.luc`, `body_checker.luc`, `generation_model.luc`, `generics/`, `interfaces/`; `profiles/full/hir/`) | Functions, generics, nominal values/classes, interfaces and protocols, closures, collections and slices, failure/control, exact function/C-function values, native authority, the exact process-entry contract, and the complete executable surface described below. Structured tasks admit only named Luce workers, prove both transfer directions recursively, keep handles inside their creating invocation, and expose frozen collection snapshots as immutable sendable graphs. Documentation and defaults are retained. Fixed-representation C enums and exported C structs remain ordinary semantic values with separate closed boundary metadata. Explicit inbound C-memory copies are closed standard-source intrinsics behind ordinary public wrappers. **Not yet**: the remaining FIIR-generated rich adapters and callback runtime enforcement. Each unsupported form fails with a span. |
| HIR interpreter (`backends/interpreter.luc`, `hir_values.luc`, `hir_execution_model.luc`; `profiles/full/backends/hir_execution.luc`) | The semantic oracle. Executes safe HIR generation, including exact scalar rounding, protocols, structural hashing/equality, closures, managed classes, sealed-runtime collections, frozen snapshots, and deterministic isolated tasks with copied arguments/results, cached waits, failures, traps, cancellation, and ordered `wait_all`. Its process runner accepts explicit arguments as the ordinary `slice[str]` semantic shape. |
| Canonical MIR (`mir/canonical.luc`; oracle in `backends/mir_interpreter.luc`, `mir_execution_model.luc`, `profiles/full/backends/mir_execution.luc`) | Target-neutral and designed for the whole language (`mir.md`), including typed mutable/frozen collections and slices, nominal interfaces/classes/weak handles, closures/cells, generated ownership helpers, structured task groups and typed transfer runs, with no physical layout or execution-domain policy. The verifier proves every rule, reachability removes unreachable closed-world resources while retaining only each transfer graph's semantic service closure, and the MIR interpreter executes every instruction under explicit test layout rules. |
| Lowerer (`mir/lowerer.luc`, `lowering_model.luc`, `function_lowerer.luc`; `profiles/full/mir/lowering.luc`) | Everything HIR generates, including protocols, structural hashing and cycle-aware equality, interfaces, scalars/aggregates, managed collections/classes/closures, failure/cleanup, C boundaries, immutable snapshots, and structured tasks with a finish on every ordinary exit. Generic declarations and marker proofs are fully erased before this boundary. |
| WebAssembly backend (`backends/wasm.luc`, `wasm_plan.luc`, `wasm_encoding.luc`, `wasm_float16.luc`; `profiles/full/backends/wasm_emission.luc`, `wasm_planning.luc`) | Supporting regression backend for the current lowerer surface, with spec arithmetic, backend-local binary16/legalized layout, calls/interfaces, WASI preview 1, C imports/globals, managed values, and immutable snapshots. It explicitly rejects isolated tasks at the backend boundary because WASI preview 1 has no worker-domain primitive. It is not the stage-1 portability boundary. |
| QBE backend (`backends/qbe.luc`, `qbe_representation.luc`, `qbe_toolchain.luc`; `profiles/full/backends/qbe_emission.luc`, `qbe_tasks.luc`, `qbe_task_support.luc`) | The required stage-1 portability and artifact oracle: direct canonical-MIR → QBE 1.3 IL with one shared native representation module, backend-owned layout/ABI, the compiled Luce runtime, C symbols, and process-isolated workers. Typed codecs copy only verified sendable graphs through framed pipes; cached waits, nested workers, cancellation, traps, failures, group cleanup, and ordered `wait_all` execute through real native artifacts. The product path atomically installs only the linked executable. |
| FIIR/C import (`fiir/`, `backends/clang_fiir.luc`, `backends/c_fiir.luc`) | Clang-derived, versioned facts generate target-neutral raw Luce plus checked C adapters for fundamental scalars, scalar typedefs, open enums, scalar constants/macros, live scalar/enum objects, logical nested records, and direct typedef-backed opaque-record handles. A separate reviewed recipe section generates ordinary safe Luce owners, checked borrows, returned-borrow anchors, and status failures. Both layers have semantic-oracle and linked QBE/C proofs. **Not yet**: broader pointer/array/string/callback forms, unions/bit-fields, aggregate/atomic/thread-local storage, typed variadics, extended floating carriers, and support/regeneration policy. |
| Tests | 986 unit tests across 49 files, plus CLI, `wasmtime`, QBE differential, and host-native smoke gates. `tests/common/differential_test.luc` runs the complete non-trapping and trapping corpus through HIR, optimized MIR, and the QBE product toolchain and checks values, output, and traps. |
| Toolchain | Stage-0 0.30 and official QBE 1.3 source are checksum-pinned in `bootstrap.sh`. Remaining constraints are in `plan.md` §8. |

## 2. Implemented milestones and evidence

- [x] Tokenizer, parser, syntax tree for the whole 1.0 surface, with per-form tests.
- [x] HIR generation for scalars, locals, control flow, calls, constants, tuples, optionals, `str`/`bytes`/`char` literals, `print` of a literal.
- [x] HIR interpreter as oracle (spec §7 arithmetic, `frame_limit = 2000`, measured rather than inherited — `plan.md` §8.1).
- [x] Canonical MIR contract, verifier, MIR interpreter (`mir.md`).
- [x] **Modules, imports, visibility, and stored constants close §§20.1–20.4**
  (2026-09-01). The package reader derives every dotted module identity from
  an explicit package-relative source root; native authority remains suffix
  metadata rather than part of the name. Selective and qualified imports
  resolve through one declaration namespace spanning values and types, record
  actual semantic use, reject unused names, and report the globally shortest
  directed dependency cycle with the exact declaration to move. A separate
  recursive public-API pass rejects every private nominal type reachable
  through public functions, generic constraints, aliases, constants, fields,
  enum payloads, interfaces, or extern variables. Top-level constants accept
  only the closed data subset and no longer confuse declaration-only function
  defaults with storable compile-time data. Focused positive/negative tests,
  multi-module package fixtures, examples, both semantic oracles, QBE, Wasm,
  CLI, and native product gates agree.
- [x] **Exact §20.5 process entry stays semantic through MIR**
  (2026-09-02). One focused HIR owner selects and validates exactly
  `pub func main(arguments: slice[str]) -> i32!` in the ordinary root package;
  private methods, dependency `main`s, and sealed-runtime helpers remain
  ordinary functions. Typed artifacts preserve the selected `SymbolId` and
  validate its complete source contract. MIR keeps the source parameter and
  fallible result unchanged and records only the target-neutral slice/error
  types and ownership functions needed by a product boundary. Both semantic
  oracles accept real argument values through the normal slice representation.
  QBE constructs owned strings from C `argc`/`argv`; Wasm imports WASI
  `args_sizes_get`/`args_get`; each backend releases the slice, releases an
  unhandled `Error`, and exits with the source status or deterministic failure
  status 1. Focused invalid-contract tests, package round trips, differential
  execution, real QBE arguments, Wasmtime arguments/failure, CLI, and native
  product gates cover the slice without introducing platform facts before
  `backends/`.
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
- [x] **QBE is the product native path** (2026-08-30; pipe hardening
  2026-08-31). `luce build --target native` keeps IL, assembly, captured tool
  diagnostics, and the linked candidate inside Stage-0 0.28's atomically owned
  temporary directory beside the destination, and installs by same-filesystem rename.
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
  `{BufferOwner, Ptr, u64}` representation, compares a `u64` index, and reaches the byte
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
- [x] **CLI runtime composition is explicit and location-only** (2026-08-31).
  Repeated `luce build --runtime FILE` inputs name the reviewed sealed runtime
  sources; the compiler-owned descriptor still fixes every permitted service,
  module, and function identity. Both product backends consume the same
  composed, verified, optimized MIR, and reachability removes unused runtime
  services. The CLI does not embed a checkout path, environment convention,
  or platform lookup. Automatic installed-resource discovery remains a host
  capability/package-layout task, not compiler semantics.
- [x] **Native authority is source metadata, not a second language mode**
  (2026-08-30). The package reader marks `.native.luc` before parsing and
  keeps its ordinary module name; `SourceModule` and `HirModule` carry the
  explicit, non-transitive authority. The two closed native pointer forms
  retain pointee identity and mutability in HIR, fail in safe modules, and are
  rejected anywhere a public alias, aggregate or function could leak them.
  Shared lowering erases both to canonical `Ptr`, without introducing pointer
  width, layout or platform facts. Tests cover suffix recognition, safe
  wrapper imports, escape diagnostics and HIR-to-MIR identity erasure.
- [x] **Typed native load, store and advance add no parallel MIR**
  (2026-08-30). The three closed HIR operations require native authority,
  exact positional shapes, typed pointers and mutable destination capability.
  Shared lowering maps them directly to canonical `Load`, `Store` and
  `ElementAddress`, retaining the structural pointee `TypeId` until backend
  layout. Tests prove diagnostics, HIR shapes, evaluation order and the exact
  verified MIR instruction sequence. Arena access remains an explicit later
  capability.
- [x] **Native rebind and move preserve the backend boundary** (2026-08-30).
  `native.rebind` requires a contextual native-pointer result, validates its
  source pointee and cannot turn an immutable pointer mutable; because the
  address is unchanged it erases entirely when pointer shapes become
  canonical `Ptr`. `native.move` requires equal pointees, a mutable
  destination and a `u64` element count, then retains exactly that structural
  information as overlap-safe `MoveElements`. The MIR verifier pins malformed
  pointers/counts, the composer remaps its `TypeId`, and the MIR oracle uses
  snapshot semantics. QBE computes checked bytes and executes libc `memmove`;
  Wasm separately enforces its 32-bit byte bound and executes `memory.copy`.
  No byte count, pointer width, layout, ABI, or platform fact enters HIR/MIR.
- [x] **Sealed runtime state lowers once into canonical globals**
  (2026-08-30). A closed `PackageRole` compiler input, never an inferred
  package name, admits module-private zero-initialized state only while
  compiling `libluce_rt`. Opaque pointers, callables, foreign handles and
  nominal invariant-bearing values cannot be forged through zero state.
  Application source cannot declare or import these cells. Explicit HIR
  loads/stores give the semantic oracle isolated persistent state; shared
  lowering produces existing `MirGlobal`, `GlobalAddress`, `Load` and `Store`
  forms. Optimized MIR and the real QBE product path agree on mutation. Wasm
  additionally lays globals out after data in linear memory, copies explicit
  initializers into disjoint cells, and sizes its static memory from the same
  backend-owned layout. No platform fact enters frontend, HIR or MIR.
- [x] **The 1.0 completion claim has an explicit conformance ledger**
  (2026-08-30). `examples/FEATURES.md` now separates frontend syntax, HIR
  semantics, canonical MIR, real QBE artifacts and human-readable examples,
  and records the first missing stage instead of treating parser coverage as
  implementation. One automated example inventory exercises all 42 reserved
  words and the seven contextual grammar words in parser-valid modules;
  another rejects every reserved word at the shared identifier boundary. A
  focused native example adds the previously absent `extern`, `blocking` and
  `out` surface. Broad partial rows must split into named positive/negative
  rules before they can close, and complete stage 1 requires every executable
  1.0 capability to run through QBE with checked observable behavior.
- [x] **The sealed runtime has one target-neutral stable-arena request**
  (2026-08-30). Only a native module compiled with the explicit runtime role
  can form `native.arena(end)`. HIR retains its mutable byte-pointee identity;
  lowering turns it into the fixed verified runtime service `(u64) -> Ptr`,
  leaving capacity, pages and host APIs absent from canonical MIR. The MIR
  oracle reserves a small deterministic arena and proves repeated calls share
  storage. QBE owns a 64 MiB aligned zero-filled BSS reservation, guards the
  requested prefix, returns one stable base and traps above capacity. Real
  QBE execution proves cross-call mutation and exhaustion. The provider owns
  no allocator policy; byte-zero reservation, alignment, free lists and reuse
  remain ordinary Luce runtime work.
- [x] **The first production allocator is compiled Luce, not compiler policy**
  (2026-08-30). `compiler/runtime_contract.luc` is the single target-neutral
  service vocabulary shared by package binding, HIR and MIR. An explicit
  sealed-package descriptor resolves `(service, module, function)` once to a
  checked private native `SymbolId`; lowering maps that identity to the exact
  `FunctionId`, and all later stages remain name-blind. The pipeline compiles
  `src/runtime/allocator.native.luc` independently and composes it before
  verification and closed-world optimization. Its checked aligned bump
  policy reserves byte zero, mutates its offset only after the arena request
  succeeds, and contains no layout or platform fact. Real optimized QBE
  execution proves two allocations do not alias and provider exhaustion
  traps. Reclamation, free-list reuse, ownership services, and the other
  freestanding primitives remain pending rather than being claimed here.
- [x] **Reviewed runtime source can request typed storage without learning its
  layout** (2026-08-30). `native.allocate[T](count)` is admitted only with
  native authority inside the sealed runtime package. HIR retains the stored
  type, `u64` element count, and mutable typed result; shared lowering emits
  the existing `AllocateStorage` instruction and relies on its exact runtime
  service binding. Tests pin the authority boundary, type-argument surface,
  structural HIR shape, remapped aggregate MIR type, and verifier-clean
  lowering. No byte count, alignment, allocator policy, or platform fact was
  added before a backend.
- [x] **Typed reclamation and free-list reuse stay behind the same structural
  boundary** (2026-08-30). Sealed runtime source alone can form
  `native.deallocate(pointer, count)` and test its inert pointer roots with
  `native.is_null`; HIR retains pointee identity and shared lowering emits
  `DeallocateStorage(Ptr, TypeId, u64)`. The verifier requires one exact
  private deallocator binding, reachability follows it only from a live
  release, and MIR composition remaps its structural type. QBE and Wasm derive
  the same checked byte count as allocation and independently raise alignment
  to their pointer requirement; neither fact enters HIR/MIR. The freestanding
  allocator normalizes requests into power-of-two classes and links each freed
  block through its first cell, with a zero-initialized fixed head table in
  ordinary runtime global storage. The MIR oracle reuses matching blocks under
  its explicit test layout; real optimized QBE proves a 32 MiB block can be
  released and reacquired inside the 64 MiB arena where a second bump would
  trap. Managed element destruction and list ARC remain the next ownership
  slice; this checkpoint claims storage reuse, not safe-value lifetime.
- [x] **The first runtime-backed `list[T]` slice preserves one semantic shape**
  (2026-08-30). HIR gives lists reference identity and resolves contextual or
  inferred literals, empty construction, `length`, checked indexed get/set,
  `append`, and mutating aggregate elements through `let` bindings. Canonical
  MIR retains `List(element: TypeId)` as a typed opaque handle; list
  instructions derive their element structure from that handle, so a raw
  pointer cannot forge or reinterpret a list. The composed freestanding Luce
  runtime alone owns its header and geometric growth policy. Each backend
  turns the structural element type into size/alignment at its boundary;
  neither HIR nor MIR contains a byte offset, pointer width, capacity rule,
  ABI, or platform fact. Nominal MIR types reserve identity before their
  fields are lowered, and the verifier rejects actual by-value layout cycles
  rather than harmless forward identities, so `Node { children: list[Node] }`
  works without making MIR target-dependent. The HIR and MIR oracles, Wasm
  legalization, real QBE growth/reallocation with aggregate elements, and a
  product-level bounds trap agree on `examples/lists.luc`. `insert`,
  `remove_at`, `clear`, `reserve`, `copy`, slicing, iteration invalidation,
  ARC, and reclamation remain open and are not claimed by this checkpoint.
- [x] **List shape mutation stays canonical and runtime-backed** (2026-08-30).
  `insert`, `remove_at`, `clear`, and `reserve` are resolved HIR operations
  with exact positional types and left-to-right evaluation before mutation.
  Canonical MIR derives element structure from the typed list handle; only
  QBE/Wasm legalization supplies size/alignment, while the compiled Luce
  runtime owns capacity, geometric growth, overlapping shifts, and commit
  timing. Aggregate removal copies into independent caller storage before the
  runtime closes the slot. Both semantic oracles, malformed-MIR rejection,
  Wasm legalization, the expanded example, real QBE execution, and insertion,
  removal, and access bounds traps agree. Copying, immutable snapshots,
  iteration invalidation, ARC, and reclamation remain separate later slices.
- [x] **List copying has explicit shallow semantics and independent storage**
  (2026-08-30). `list.copy()` resolves to one typed HIR operation and one
  canonical `ListCopy` instruction; neither representation contains capacity,
  layout, or a byte count. Both semantic oracles create a fresh collection
  identity, preserve element order, copy value elements independently, and
  retain nested reference identities. QBE and Wasm derive size/alignment only
  at legalization, and the sealed runtime creates a fresh header and storage
  before overlap-safe byte copying. Exact runtime-signature validation,
  malformed-MIR rejection, differential execution, and `examples/lists.luc`
  prove independent shape/slot mutation and shallow nested-list behavior.
  Immutable snapshots, iteration invalidation, ARC, and reclamation remain
  separate later slices.
- [x] **Immutable list slices are O(1) shallow snapshots** (2026-08-30).
  `list[T]` accepts half-open explicit or one-sided bounds and produces a
  canonical `slice[T]` handle. HIR evaluates the receiver and explicit bounds
  once from left to right; both semantic oracles enforce
  `start <= end <= length`. Canonical MIR separates read-only list addressing
  from `ListMutableElementAddress`, the sole write barrier, so direct stores
  and nested `mutating` value receivers detach the list buffer before writing.
  The sealed runtime owns buffer/header policy; QBE and Wasm supply only
  backend-local element layout and bounds guards. Scalar, structural, and
  shape mutation preserve captured values while nested reference elements
  retain identity. Malformed MIR, reversed/past-end bounds, slice indexing,
  aggregate mutation, both semantic oracles, Wasm legalization, and real QBE
  execution are covered. Byte-backed slices are recorded separately below.
- [x] **Immutable bytes own dynamic storage without burdening literals**
  (2026-08-30). Canonical bytes are `{BufferOwner, Ptr, u64}`: static literals
  carry a null inert owner, while `+` allocates one immutable sealed-runtime
  buffer and ordinary structural ownership retains/releases its opaque handle.
  `bytes` comparisons are unsigned lexicographic operations. Half-open slices
  produce the same canonical `Slice(u8)` used by lists; a generalized runtime
  slice header stores stable data plus an exact owner-release callback, so a
  slice returned from a function safely outlives a temporary concatenation.
  No allocator header, pointer width, or layout fact enters HIR or MIR.
  Bounds and malformed owner/data/result types are verified, and static,
  dynamic, prefix-ordering, reversed/past-end, and escaping-owner cases agree
  through HIR, MIR, QBE, and Wasm. `examples/bytes.luc` is the executable
  conformance example.
- [x] **Strings own dynamic UTF-8 storage and expose scalar semantics**
  (2026-08-31). `str` and `bytes` share the target-neutral
  `{BufferOwner, Ptr, u64 byte_length}` storage protocol without sharing HIR
  operations. Literals retain an inert owner; concatenation allocates once,
  and an owned result can cross calls and aggregate lifetimes. `byte_count`
  remains O(1), while `length()` and `for character in text` decode valid
  UTF-8 into Unicode scalar values. Exact equality, scalar-preserving UTF-8
  lexicographic ordering, prefix ordering, no integer indexing/slicing, and
  continuation/break behavior have positive and negative HIR evidence,
  malformed MIR evidence, both semantic oracles, and real QBE and Wasm
  execution. `examples/strings.luc` is the product conformance example.
- [x] **Literal spelling decoding is one linear semantic pass** (2026-08-31).
  A focused HIR utility now converts exact tokenizer spellings into character,
  UTF-8 text, or byte values without source, type, target, or backend
  knowledge. Ordinary text covers every §4.4 simple and Unicode escape; raw
  strings preserve backslashes and braces; character escapes produce exactly
  one scalar; byte `\xNN` contributes one exact byte while `\u{HEX}` contributes
  the scalar's canonical UTF-8. The body checker only adds source diagnostics
  and types, so literal `print` and value expressions cannot drift. Focused
  malformed/value tests, HIR inspection, both semantic oracles, real QBE,
  Wasm, and `examples/strings.luc` agree. Triple-quoted values remain a
  formatter slice because §4.4 defines their indentation trimming there.
- [x] **Explicit integer construction is checked end to end** (2026-08-31).
  `Destination(value)` for every implemented integer source/destination pair
  now shares one `NumericConvert` HIR node. MIR compares against the destination
  interval before narrowing or changing signedness, then uses canonical
  `extend`, `wrap`, or equal-width `int_reinterpret`; out-of-range values trap
  consistently through the oracles, QBE, and Wasm.
- [x] **`u64` keeps its complete domain until the backend boundary**
  (2026-08-31). Source decoding accumulates unsigned literals directly in
  `u64`; HIR values and canonical MIR constants/oracle values distinguish
  signed from unsigned semantics instead of capping both at `i64.max`.
  Arithmetic, comparison, shifts, closed ranges, checked construction, memory
  round trips, verifier intervals, indices, lengths, and explicit hosts all
  preserve that distinction. Only QBE and Wasm reinterpret the top bit as
  machine bits: QBE uses unsigned carry/borrow/quotient checks, while Wasm
  emits their equivalent native-width operations. Boundary tests cover
  `u64.max`, the whole upper half, maximum-ended ranges, signed/unsigned
  construction, exact storage, successful QBE/Wasmtime execution, and true
  overflow at `u64.max + 1`; the complete 560-test product gate is green.
- [x] **Floating construction has one explicit checked IEEE policy for every
  scalar width** (2026-09-01). `NumericConvert` covers integer/float,
  float/integer, and f16/f32/f64 width changes. Contextual literals and every
  operation round at their declared width rather than leaking the oracles'
  f64 carrier. Narrowing
  uses nearest/ties-to-even and traps only finite overflow; NaN and infinity
  remain IEEE values. Float-to-integer truncates toward zero after rejecting
  NaN, infinity, and the destination interval's exterior. Canonical MIR adds
  only typed `float_resize`; target-independent lowering supplies semantic
  guards. QBE and Wasm each keep f16 legalization private to the backend,
  carrying live values in f32 while storing exact two-byte IEEE encodings;
  neither representation enters HIR or MIR. Host seams canonicalize all three
  widths. Direct f64 narrowing operates on the original binary64 bits, avoiding
  a binary32 midpoint double-round. Positive, ties-to-even, subnormal,
  signed-zero, structural-hash and display, finite-overflow, two-byte storage,
  native QBE, Wasmtime, and executable-example evidence agree. Direct f16 C
  ABI crossings remain rejected unless they pass through the FIIR-generated
  adapter below; direct extern declarations never pretend f16 is f32.
- [x] **Generated C `_Float16` bindings preserve semantic f16 without exposing
  its ABI** (2026-09-02). The selected-header graph requests Clang-evaluated
  binary16 size, radix, significand, and exponent facts only when reachable.
  FIIR serializes the distinct fundamental identity; generated public typedefs,
  function parameters/results, and record fields remain nominal over `f16`.
  The raw adapter edge uses `f32` as an exact value transport and the generated
  C product casts to/from `_Float16` while asserting the recorded format. Both
  semantic oracles, Wasm generation, native QBE/C execution, CLI binding, and
  the checked-in C-import example cover direct and nested crossings. A target
  enum-layout variant is re-inspected before compilation, proving target facts
  change FIIR/C products without changing generated Luce semantics.
- [x] **Named IEEE special values establish the first ordinary `math` surface**
  (2026-09-01). `src/standard/math.luc` declares width-explicit NaN, positive
  infinity, and negative infinity constants for f16/f32/f64 using only the
  language's existing constant expressions and checked conversions. The HIR
  import value union now includes constants: qualified and selective access
  enforce public visibility, reject missing values and local shadowing, and
  converge on the same program-wide symbol and typed initializer. No import
  spelling or library identity reaches MIR. Both semantic oracles, verified
  MIR, Wasm execution, real native QBE, exact import diagnostics, and the
  updated `examples/numeric_conversions.luc` prove every width and sign. The
  standard module remains an explicit source input because manifest and
  dependency discovery are deliberately post-1.0; no implicit prelude or
  checkout path is embedded in the compiler. The 2,710-line declaration
  collector's touched import section already owns the one value-namespace
  transaction; extracting this small variant extension would split that
  exhaustive resolution without creating independent state. The 3,467-line
  body checker adds one constant-reference convergence helper inside its
  marked recursive expression/call transaction, so its prior ownership
  decision remains unchanged.
- [x] **Type aliases, inference boundaries, copying, and mutable places close
  the §§5–6 core audit** (2026-09-01). Alias and constant identities are now
  collected before any typed signature: forward chains and aliases used by
  functions, fields, and interface requirements are order-independent, mutual
  recursion reaches one exact diagnostic, and a qualified public alias from
  any source order resolves to the underlying `TypeId` while private aliases
  remain inaccessible. Public constants must spell their API type; private
  constants and locals retain local inference. One MIR lowering defect found
  by the audit is fixed at its semantic boundary: list, map, and class
  parameters are reference values, so mutation may traverse their shared
  storage without manufacturing an address that would make the immutable
  parameter itself assignable. Aggregate parameters still arrive as existing
  caller-owned addresses. No HIR/MIR operation or backend case was added.
  `examples/types_and_bindings.luc` proves tuple RHS evaluation, transparent
  aliases, contextual generic values, recursive class indirection, generic
  nested value mutation, value-copy independence, and shared list/class
  identity through both oracles, verified MIR, native QBE, Wasm, and Wasmtime.
  The touched 2,733-line declaration collector still owns one ordered
  declaration transaction; splitting its mutually dependent passes would hide
  their required sequencing. The 5,310-line function lowerer changed only its
  existing resolved-place transaction, whose register/ownership helpers are
  mutually recursive; a holistic post-coverage decomposition remains safer
  than introducing a callback-heavy fragment now.
- [x] **Expressions and functions close their §§7–8 rule audit** (2026-09-01).
  The audit found one declaration-order defect: ordinary parameter defaults
  were checked while signatures were collected, before import bindings
  existed, so a legal pure imported constant was invisible. Signature
  collection now records only the typed parameter identity and trailing-
  default shape. A dedicated post-import, post-constant pass resolves each
  ordinary default in its module scope with body locals absent; generic
  templates keep their existing abstract and concrete specialization passes.
  Qualified and selective imports, inaccessible runtime/parameter state,
  positional-before-named calls, arbitrary named order, duplicates, unknowns,
  omissions, and source-order placement now have exact fixtures. The new
  `examples/expressions_and_calls.luc` observes receiver, argument, list,
  interpolation, binary, assignment-RHS, and constructor order and combines
  defaults, tuples, exact function values, recursion, and mutating `self`
  replacement. Both semantic oracles, verified canonical MIR, native QBE,
  Wasm, and Wasmtime agree without a new HIR/MIR form or backend case. The
  2,780-line declaration collector remains the owner of its ordered signature
  transaction; extracting only this short second phase would add navigation
  without independent state, so holistic post-coverage decomposition remains
  the cleaner boundary.
- [x] **Fixed-array slices own a selected value snapshot** (2026-08-31).
  HIR admits array slicing as the explicit `array[T, N]` to `slice[T]`
  conversion and its oracle copies the selected values into immutable backing.
  Shared lowering checks `lower <= upper <= N` before allocation, reserves the
  exact selected count once, copies through one structural loop, captures the
  existing list-buffer slice, and releases the temporary list identity.
  References nested in elements are retained shallowly; source-array mutation
  and function return cannot affect or invalidate the view. The implementation
  adds no MIR instruction and no backend branch. Evaluation-order, scalar,
  managed-element, escape, invalid-bound, native QBE, Wasm, and executable
  example evidence agree.
- [x] **Explicit discard preserves effects and ownership** (2026-08-31).
  Compiler-known `discard[T](value)` is a distinct target-neutral HIR
  operation with an inferred operand type and `unit` result. It evaluates once
  in the HIR oracle, rejects unhandled fallible values while admitting
  `discard(try value)`, and preserves a `never` operand's terminating flow.
  The shared module/import/local binder now also enforces the spec's closed
  compiler-known core namespace instead of allowing resolution-time shadowing.
  Lowering emits the operand's ordinary MIR effects and consumes its managed
  result through existing full-expression cleanup, so canonical MIR and both
  backends need no discard opcode or special lifetime path. Scalar, fallible,
  and owned-string fixtures agree through both oracles, real QBE, Wasm, and
  `examples/strings.luc`.
- [x] **Silently discarded results are structured advisories** (2026-08-31).
  Semantic analysis emits `L0701` for every non-`unit`, non-diverging
  expression statement and suggests `discard(...)`; unit calls, explicit
  discard, and `never` termination remain quiet. Each flat HIR node now keeps
  its cold source `ModuleId` parallel to type and span, making the diagnostic
  a cache-friendly linear scan with exact multi-module paths and no duplicate
  statement walker. Exact rendering and positive/negative cases are pinned;
  execution and canonical MIR are unchanged.
- [x] **Source traps carry dynamic diagnostics through one semantic path**
  (2026-08-31). Compiler-known `trap(message)` eagerly checks and evaluates
  one ordinary `str`, has type `never`, and terminates without running
  deferred cleanup. The HIR oracle reports the dynamic text. Shared lowering
  loads the canonical owner-backed string's structural data and `u64` length,
  calls the already reserved `luce_rt_trap` extern, and marks the remaining
  flow `Unreachable`; it adds no trap opcode or platform fact to MIR. QBE
  legalizes the service to stderr writes plus `hlt`, while Wasm uses WASI
  stderr plus `unreachable`; both append one backend-owned diagnostic newline.
  Malformed signatures, flow typing, dynamic ownership, no-defer behavior,
  exact backend output, differential trapping, and `examples/traps.luc` are
  covered. Rich source locations and stack traces remain an explicit §13
  diagnostic audit rather than being claimed here.
- [x] **`never` is complete target-neutral control flow, not a zero-result
  value** (2026-08-31). Source functions, fallible functions, exact function
  values, closures, generic specializations, interface requirements, and
  dynamic witnesses preserve an explicit uninhabited successful result.
  Storage validation rejects `never` directly or transitively in parameters,
  fields, bindings, containers, aggregates, callable parameters, and native
  pointees, and revalidates concrete generic/interface substitutions; a
  callable returning `never` remains an ordinary storable descriptor. HIR
  makes bottom coercion explicit and replaces an unreachable outer operation
  with its exact left-to-right eager prefix, without flattening conditional or
  short-circuit operands. Whole-program initialization and deinitializer
  analysis traverse that form. Canonical MIR carries `returns_never` beside
  the shared signature, has no `never` value type, rejects successful returns
  or results for that signature, and emits structured `Unreachable` only
  after calls that cannot return. Owned compile-time temporary records on a
  terminating path are forgotten without emitting unreachable cleanup, while
  lexical `defer` retains the terminator's existing policy. Direct, indirect,
  closure, generic, interface, conditional, match, optional fallback,
  short-circuit, fallible, nested eager-call, malformed-MIR, both-oracle,
  native QBE, Wasm, and focused-example evidence agree.
- [x] **Source assertions reuse the trap seam without creating backend work**
  (2026-08-31). Compiler-known `assert(condition, message?)` checks one
  Boolean, eagerly evaluates the optional ordinary string message, inserts the
  exact `"assertion failed"` default in HIR, and continues as `unit` only when
  the condition is true. The HIR oracle models that control flow directly.
  Shared lowering emits `If`, the existing target-neutral trap extern,
  `Unreachable`, and `End`; canonical MIR needs no assertion opcode. An owned
  dynamic message is released after the successful join, while failure skips
  both that unreachable cleanup and lexical `defer`. Positive/default and
  malformed source forms, both semantic oracles, differential QBE execution,
  Wasm, exact backend diagnostics, and `examples/assertions.luc` are covered.
  A separate HIR operational pass now classifies allocation, observable
  mutation, I/O, external access, unresolved dynamic calls, and termination,
  then closes those facts over direct recursive call graphs. Assertion
  conditions accept only an empty closed summary and rejected transitive calls
  print their exact cross-module source path. Pure mutual recursion and
  read-only methods remain accepted; rich runtime source traces remain in the
  same §13 diagnostic audit as traps.
- [x] **WebAssembly module planning has one backend-local owner**
  (2026-08-30). `backends/wasm_plan.luc` now settles Wasm signatures,
  imports, function/table indices, 32-bit type layout, and aligned static
  addresses before encoding begins. The 1,728-line semantic encoder consumes
  that complete immutable plan without forwarding wrappers or duplicated
  pass state. A focused plan test pins index/layout/address ownership while
  the complete Wasm execution suite continues to validate emitted bytes.
- [x] **List identity is an explicit semantic comparison** (2026-08-30).
  Source `is` and `is not` resolve only for implemented shared-identity
  lists; value types and immutable slices are rejected rather than exposing
  backend handle addresses. HIR keeps identity distinct from structural
  equality, while canonical MIR reuses typed-handle `eq`/`ne` without losing
  the list type or adding target facts. Both semantic oracles, malformed-MIR
  rejection, Wasm's backend-local i32 legalization, and real QBE execution in
  `examples/lists.luc` distinguish aliases from independent shallow copies.
- [x] **List concatenation is one shallow runtime operation** (2026-08-30).
  Source `list[T] + list[T]` evaluates both operands left-to-right and creates
  a fresh identity with independent element slots in left-then-right order,
  including empty and aliased operands. HIR retains its resolved `Add`; shared
  lowering emits one typed canonical `ListConcat` rather than exposing a copy
  plus append loop. The sealed runtime loads both inputs, performs checked
  arithmetic, allocates one result buffer, and bulk-copies both prefixes;
  only QBE/Wasm legalization supplies element size and alignment. Value
  elements copy independently while reference elements remain shallow.
  Diagnostics, malformed MIR, both semantic oracles, exact Wasm calls, and
  real QBE execution of `examples/lists.luc` cover the operation.
- [x] **List iteration invalidates shape mutation through every alias**
  (2026-08-30). Built-in lists reuse the resolved HIR `ForStatement` and bind
  their element type without adding a collection-specific frontend tree.
  Canonical `ListIterationBegin`/`ListIterationEnd` operations retain one
  target-neutral traversal depth on the list identity; begin captures length,
  while every pass reacquires its checked element address so permitted
  `reserve` relocation remains safe. Exhaustion and `break` share one cleanup,
  `continue` retains traversal, and return/error paths use the lowerer's
  lexical semantic-cleanup stack. Append, insert, remove, and clear evaluate
  operands normally, then QBE/Wasm query the exact active-iteration service
  and trap before unchecked runtime mutation. Nested read-only iteration,
  element replacement, value/reference-element mutation, reserve, alias
  rejection, evaluation and bounds precedence, malformed MIR, both semantic
  oracles, backend legalization, and real QBE execution/traps are covered.
- [x] **Recursive collection ownership is explicit and target-independent**
  (2026-08-30). Every managed expression produces or retains one owned value;
  bindings, assignments, returns, match payloads, loop bindings, conditionals,
  custom-initializer failure, and lexical exits transfer or destroy it through
  one LIFO cleanup model. The lowerer generates one private retain/release pair
  per structural MIR type. Canonical list operations carry those exact
  callback identities, the verifier proves their signatures and privacy, and
  reachability preserves and remaps them. The freestanding runtime separately
  counts list identities and shared list/slice buffers, retains managed
  elements on shallow copies and copy-on-write detachment, destroys them in
  reverse order, and returns final storage to the existing typed free lists.
  Null is permitted only as an inert compiler-internal managed slot during a
  partial custom initializer. HIR/MIR oracles, nested managed-element escapes,
  optimizer remapping, actual QBE execution, and runtime-composed Wasm execution
  agree. HIR and MIR still contain only typed handles and callbacks; layout,
  alignment, arenas, and physical headers begin behind each backend boundary.
- [x] **Exact ordinary function values reuse the canonical callable model**
  (2026-08-30). A named, capture-free Luce declaration has an exact `func`
  type and explicit `FunctionAddress` HIR form; calls through values are
  positional `IndirectCall`s, distinct from declaration labels/defaults and
  from method resolution. Values can be constants, selected conditionally,
  stored in structs, passed and returned, deferred, and imported from another
  module, with scalar, aggregate, unit or fallible signatures. HIR and MIR
  oracles agree on callee-before-arguments evaluation. The managed-closure
  slice generalized canonical MIR `func` values to typed code/environment
  descriptors: capture-free names use a null environment and allocate
  nothing, while `CallClosure` provides one invocation protocol for named and
  anonymous Luce functions. Reachability retains and remaps address-only
  targets. QBE and Wasm choose their own descriptor/table representation, and
  `examples/function_values.luc` executes through both artifact paths.
- [x] **Core managed closures preserve one target-neutral semantic shape**
  (2026-08-31). Expression and block closures resolve into one HIR closure
  table with source-visible signatures and ordered capture policies. Immutable
  defaults and explicit `copy` captures snapshot values; captured `var` locals
  are promoted once into typed shared ARC cells; weak class captures expose an
  optional without keeping the referent alive; nested environments escape and
  compose. Capture-free lambdas collapse to ordinary function values.
  Canonical MIR records typed descriptor initializers, environment/capture
  metadata, cell operations and exact private destroyers without size,
  alignment, offsets, pointer width, or ABI. Its verifier proves every hidden
  signature and payload access before QBE or Wasm selects layout. The HIR and
  MIR oracles, optimizer/composer remapping, real native QBE, runtime-composed
  Wasm, malformed-MIR tests, the differential corpus, and
  `examples/closures.luc` agree. Fallible closure coverage,
  infallible-to-fallible lifting, `weak self`, stored/collection closure
  ownership evidence and direct-cycle diagnostics remain explicit follow-up
  work in the checkpoint below; shared-cell advisories are complete in the
  following checkpoint.
- [x] **Complete the executable closure conversion, storage, and cycle matrix**
  (2026-08-31). Fallible captured functions use the existing failure-as-data
  call path. An infallible function value converts once into a private managed
  adapter environment that forwards the exact arguments and returns only the
  successful path; named and already-capturing values therefore share one
  implementation. `weak self` promotes through the same optional weak-capture
  operation as a named class local. Function descriptors retain and release
  correctly through class/struct fields and list copy/clear operations.
  Closure formation also retains enough immutable-alias provenance to reject
  a class storing a closure that strongly captures that same root, while weak
  capture and unrelated ordinary class assignments remain valid. Expanding
  `examples/closures.luc` exposed a contextual-typing defect where checking a
  closure against `func?` peeled the optional for its signature and then lost
  it from the resulting HIR; the final expectation is now kept distinct and
  the explicit `Some` survives through both oracles, Wasm, and QBE. Focused
  HIR structure/diagnostic tests, the differential corpus, and the executable
  example cover the completed matrix. Sendability waits for workers.
- [x] **Structured analysis diagnostics identify accidental shared cells**
  (2026-08-31). `frontend/source.luc` defines one presentation-independent
  diagnostic value with stable severity/code, primary and secondary labels,
  and actionable help. Semantic analysis follows nested shared-cell capture
  provenance back to the original mutable binding, emits `L1401` once per
  promoted cell, and leaves valid default capture semantics unchanged.
  `AnalyzedProgram`, `RunResult`, `CompiledProgram`, and `BuildResult` preserve
  reports across check, HIR execution, sealed-runtime composition, MIR
  verification, and backend materialization; only the CLI renders them.
  Focused tests pin deduplication, nested provenance, exact source location,
  explicit `copy` suppression, rendering, and check/run/build propagation.
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
- [x] **Conditional binding is optional match sugar, not another control-flow
  family** (2026-08-30). HIR evaluates the optional subject once and emits the
  same exhaustive `.some(payload)`/`.none` `Match` used by source `match`.
  The immutable payload exists only in the successful suite; the absent arm
  contains the fallback or an empty suite. Existing flow analysis, ownership
  cleanup, verified MIR lowering, QBE, and Wasm consume that single shape.
  Positive and negative HIR tests cover typing, scope, and duplicate names;
  differential fixtures cover evaluation order, both branches, no fallback,
  and an owner-backed dynamic `bytes` payload whose escaping slice must retain
  storage. `examples/conditional_binding.luc` executes through both semantic
  oracles and both current artifact backends.
- [x] **HIR generation has program and function responsibilities, not one
  giant class** (2026-08-31). `HirGenerator` now only orders phases and
  publishes the finished program. `DeclarationCollector` owns modules,
  imports, aliases, signatures, nominal declarations, C contracts, and sealed
  runtime bindings. `HirBodyChecker` owns constants and mutually recursive
  function-local statement/expression/pattern semantics. Both consume one
  `HirGenerationState`, so the refactor introduced no copied type, symbol,
  source, or flat-node tables. Parameter and field defaults use the only
  reverse contract: type one constant expression into that shared arena.
  Every component has documented `# mark:` sections, collector internals stay
  private, and the complete semantic/backend gate is unchanged.
- [x] **MIR lowering has one program coordinator and one function walk, not
  one giant class** (2026-08-31). `Lowerer` fixes callable, C, global,
  runtime, and generated-helper order and publishes the canonical program.
  `MirLoweringState` owns the only identity/type tables and active function
  transaction. `FunctionLowerer` owns mutually recursive statements,
  expressions, patterns, calls, aggregates, ownership, and lexical cleanup.
  Generated ownership helpers reserve identities in the shared transaction
  and are emitted through the same function machinery, so the split adds no
  duplicate lowering or backend path. Every component has documented
  `# mark:` sections; the focused 72-test lowerer suite and complete gate are
  unchanged.
- [x] **Core classes preserve nominal identity until the backend boundary**
  (2026-08-31). HIR resolves one required `init`, optional `deinit`, class
  methods/type functions, shared mutable fields, `is`/`is not`, and optional
  `weak var` fields without layout. Definite-initialization analysis rejects
  early publication; destruction analysis rejects resurrection and records a
  transitive proof for same-class helper methods receiving the dying borrowed
  `self`. Canonical MIR adds nominal `Class`/`WeakClass` types, one payload
  schema and exact destroyer per identity, and semantic create/ARC/field/weak
  operations only. The compiled Luce runtime owns strong/weak control blocks,
  marks death before deinit, skips user deinit after failed construction, and
  destroys initialized fields in reverse order. A weak sink adapts
  `some(self)`, conditional, and `else` sources directly without constructing
  an owning optional that could resurrect the object. HIR and MIR oracles,
  QBE, Wasm, the differential corpus, and `examples/classes.luc` agree.
  Backend layout is the only physical class layout; the architecture audit
  found no target fact before `backends/`. The 2K-line ownership review also
  found no honest class-only split in the mutually recursive function walk.
  The following closure slice did establish an independent capture-context
  owner in `profiles/full/hir/closure_context.luc`. Remaining §11 work is tracked separately
  rather than hidden behind this core milestone.
- [x] **First-class weak handles reuse the nominal class lifetime protocol**
  (2026-08-31). `Weak[T]` remains one compiler-known type family rather than
  premature user-generic infrastructure. HIR records the exact class identity,
  construction, and atomic `get()`; canonical MIR reuses `WeakClass(id)` and
  its existing create/retain/release/promote operations. Copies in lists and
  class fields retain only weak storage, dead promotion returns `none`, and a
  deinitializer may publish borrowed `self` only through `Weak(self)`. Both
  oracles, QBE, Wasm, and the extended class example agree; C boundaries reject
  the non-representable handle with a source diagnostic.
- [x] **Direct class cycles and deinitializer reentrancy are distinguished**
  (2026-08-31). Source-local ownership provenance now rejects a class stored
  through its own strong field, including immutable aliases and structural
  wrappers, and rejects insertion of that root into a list it owns. Weak
  fields and `Weak[T]` remain the explicit back edges. Field/element extraction
  copies only the selected value and is deliberately not mistaken for retaining
  its owner, closing a false-positive edge exposed by `Trace.record`.
  Destruction analysis follows same-class cleanup methods transitively without
  warning, but emits structured `L1101` advisories at defined, constructed, or
  indirect user-code calls that can reenter during final release; external C
  cleanup is not mislabeled as Luce user code. Resurrection remains a hard error.
  Focused positive/negative tests pin every distinction. These are frontend/HIR
  ownership facts, so canonical MIR and both backend paths remain singular and
  unchanged.
- [x] **Dynamic class leaks have one target-neutral census** (2026-09-01).
  `ResourceCensus` records live source-class identities, exact allocation
  sites, collapsed strong class-to-class edges, and probable strongly
  connected components. Both semantic oracles walk their own private value
  storage through optionals, aggregates, lists/maps/sets/slices,
  closures/cells, and interface boxes while omitting weak slots; focused tests
  prove identical HIR/MIR reports for direct, container, interface, and
  closure-cell cycles. Snapshot slices correctly retain the complete backing
  ownership graph even outside their visible range. SCC traversal is
  iterative, report ordering is stable, and sparse allocation identities do
  not allocate a dense index. Census runs are explicit isolated unit domains
  and reclaim deliberately leaked oracle
  graphs after copying metadata. QBE compiles and executes the same dynamic
  ownership graph, while the production runtime carries no test counter,
  branch, reflection API, target fact, or tracing collector. The class example
  now proves idempotent `close`, lexical `defer`, and `deinit` fallback. No
  diagnostic guesses that `deinit` or a bare foreign handle denotes an owned
  resource; that policy waits for explicit owned/borrowed boundary metadata.
- [x] Lowerer 3a–3c: scalars and locals, control flow, calls/parameters/constants.
- [x] Wasm backend for everything the lowerer emits; WASI host contract; executed under `wasmtime` in `tests/wasm_test.sh`.
- [x] Native rung 0 proved direct image writing for the original slice; removed
  after the QBE product path superseded it, so stage 1 has one native path.
- [x] Stage-0 0.22 → 0.23: interface-error trap and temporary-receiver use-after-free reported with reproductions (`build/stage0-0.22-repro.tar.gz`), fixed upstream, workarounds removed; call depth raised, deep-recursion fixtures restored.
- [x] Decision record: `docs/vision.md`, `docs/language/1.0-gap-audit.md`, lineage evidence (§4 below), proving programs and gates (`plan.md` §5–6), cautionary tales (`plan.md` §7).
- [x] **Milestone 4 — composites** (`b6f24f4`). Tuples as anonymous structs in slots (`FieldAddress`, `Memcpy`); optionals as `u8`-tagged two-case enums with the payload after the tag; the original `str`/`bytes` `{pointer, u64 length}` representation with structural equality (later superseded for `bytes` by the owner-backed milestone above); `print` of a `str` value. Established the **aggregate protocol**: a register of aggregate type holds an address, copies are explicit `Memcpy`, aggregate results go through a hidden leading pointer parameter, aggregate parameters are passed by pointer (`mir/lowerer.luc` header, `mir.md`).
- [x] **Structs and methods** (`78dd669`). Fields with `let`/`var`/`pub` and constant defaults; the synthesized memberwise initializer with the spec §10.1 visibility rule; field access and `root.a.b = v` places; methods with `self`; `mutating` methods (receiver must be a mutable place; lowered as stores through the pointer the aggregate protocol already passes); type functions; struct equality; structs inside tuples/optionals; cross-module `module.Struct`. Gate met: `HirStruct`/`HirField`/`HirFunction`/`HirModule` retain documentation, `HirParameter` retains `default_value`, defaults are embedded at call sites.
- [x] **Enums and `match`** (2026-08-28). Enums as closed sums with named payloads, `Enum.case`, `.case` from context (through an optional too), `module.Enum.case`, enum methods and type functions (receivers now name an owner `TypeId`, shared with structs), structural enum equality, self-containment rejected. `match` as statement and expression: enum/optional case patterns with payload bindings (alternatives share one binding set), literal and range patterns for integers/chars/bools/strings, `_`; exhaustiveness for enums, optionals and bools; duplicate, overlapping and unreachable patterns rejected. Lowered as an `If` chain that tests the subject once, arms nesting in each other's `Else`; expression form yields through a `Block`. The oracle's recursive walkers were split into small functions after the unbounded-recursion fixture overflowed the host stack (frames grew with the new arms).
- [x] **MIR instructions are fixed-size** (2026-08-28). `Call`/`CallExtern`/`CallIndirect`/`Block`/`If`/`Br`/`BrIf`/`Yield`/`Return` name `RegisterRun{start, count}` into `MirFunction.operands` instead of holding a `list[RegisterId]`; `OperandBuilder` collects runs while a body is built; consumers read `register_at`. With flat regions this makes a MIR body two contiguous arrays.
- [x] **HIR is one flat node table** (2026-08-28). Statements and expressions are `HirNode`s stored inline in `HirProgram.nodes`; `form` is the named union (pattern matching unchanged), children are `NodeId`s, child lists are `Operands` runs in `extra` (suites, call argument pairs, if-branch triples, resolved place paths), literal values in `values`, result types and spans in parallel arrays. `hir_gen` builds bottom-up with `push_node`; the oracle and lowerer read through `node_form`/`node_at`/`entry_at`. Zero harness differences.
- [x] **MIR is flat** (2026-08-28). `Block`/`Loop`/`If`/`Switch` open a region in the body list, `Else`/`Case`/`Default` separate arms, `End` closes; `MirInstruction` is a struct stored inline. Verifier, MIR interpreter, and wasm backend became single linear passes with a region stack (`mir/verifier.luc`, `mir_interpreter.luc` `plan_regions`, `wasm.luc` `encode_body`); the lowerer emits regions in place. The harness caught one bug in the rewrite (loop-restart branch popped every region). Design: `mir.md` "Control flow".
- [x] **Layout decisions recorded** (2026-08-28, `plan.md` §6): shape now, tuning at the self-hosting measurement; hybrid flat tables (named union payloads, `u32` links, cold fields in parallel arrays) rather than Zig's raw `{tag, lhs, rhs}`, because Luce has no `comptime` to generate the readability back.
- [x] **Spans are 16 bytes** (2026-08-28). `SourceSpan` is four `u32`s instead of four `i64`s; it sits in every token, syntax node, HIR node, and MIR instruction. Tokens keep their `str` text for now (front-end-only cost).
- [x] **Ids are `u32`** (2026-08-28). `TypeId`, `SymbolId`, `ModuleId`, `RegisterId`, `FunctionId`, `ExternId`, `GlobalId`, `DataId` hold a `u32` index; `no_register` (`u32` max) replaces the `-1` sentinel. The `i64(...)` widening every index site needed under Stage-0 went away in 0.26, which indexes with any integer: 98 conversions deleted 2026-08-29.
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
- [x] **Stage-0 0.30 adopted** (2026-08-31). Both host archives and source
  identity are pinned from the official release. Its host-provided stack-floor
  guard closes the last open Stage-0 request without changing the language,
  module format 73, or host ABI 32. The complete 690-test, differential, CLI,
  Wasm, and native QBE gate passes; exact adoption evidence is in
  `stage0-0.30.md`.
- [x] **The front end is linear** (2026-08-29, `recursion.md` §5). It was quadratic in file size: 8,000 statements took 179 s, 8,000 comment lines took 25 s. Three causes — bracket matching scanned per nesting level, `len(self.source)` sat inside the scanning loops, and `str` indexing walks the string in Stage-0 (`text[i]` is O(i), `for c in text` is O(n²), `text[a:b]` is O(a)). The tokenizer now decodes `bytes(source)` once into a `list[char]`, scans that, and builds token text with `text_between`; the parser precomputes bracket matches in `match_brackets`. Same inputs: 0.42 s and 0.07 s, and 1.4 MB in 3.1 s. Reported upstream for 0.27 with a reproduction (`build/stage0-0.27-repro/`), since the `str` cost is Stage-0's and it bounded self-hosting.
- [x] **Expression nesting is bounded** (2026-08-29). 26,250 nested parentheses took SIGBUS; 25,000 did not. `parse_expression` counts its depth and refuses past 256 — Swift's and Clang's number, from the C++ standard's recommended minimums — with `expression nests deeper than 256`. Pinned by `test_expression_nesting_is_bounded`. The crash had been invisible because the old tokenizer took minutes to reach that depth: fixing throughput is what exposed it.
- [x] **Integer ranges and `for`** (2026-08-29). `range[T]` is an immutable `{lower, upper, inclusive}` value for every implemented integer width; it can be bound, compared, passed, and returned under the aggregate protocol. `for` binds each element immutably, handles empty and closed ranges, and gives `continue` an inner block so it reaches the increment rather than restarting the same value. A closed range ending at the type maximum stops before incrementing. The HIR oracle, MIR interpreter, and wasm agree on half-open/closed/empty/max ranges, nesting, break/continue, early return, and range aggregate calls. The protocol and executable `try for` continuation is recorded in the later compiler-known iteration milestone below.
- [x] **Lexical `defer`** (2026-08-29). A unit-producing call's receiver and arguments are copied into hidden HIR bindings when registered, so later mutation cannot change the cleanup. The oracle runs actions LIFO at the end of each lexical scope. The lowerer duplicates the captured calls on fallthrough, `return`, `break`, and `continue`, with loop boundaries preventing an inner exit from running an outer cleanup; return values are evaluated before cleanup. Traps deliberately skip cleanup. HIR/MIR/wasm fixtures cover capture timing, ordering, nested scopes, unit fallthrough, both loop forms, and silent traps.
- [x] **Fallible MIR has explicit ownership** (2026-08-29). Every fallible function receives its caller-owned `Error` slot in r0, reports null on `Return`, and returns that same r0 on `Raise`; no error points into a dead callee frame or needs runtime allocation. The verifier proves the signature and terminator rules, the MIR interpreter executes them, and wasm restores its shadow frame before returning the default value plus error pointer. A wasmtime regression covers success, failure, and wasm's reverse multi-result stack assignment.
- [x] **Source failure is explicit data and control** (2026-08-29). `ErrorCode.package` accepts restricted constant `u32` expressions, rejects duplicates package-wide, and embeds an explicit compilation identity rather than a path-derived name. `T!` is confined to the outer result of a function; parameters, bindings, constants, fields, payloads, nested effects, and unhandled values are rejected. The HIR oracle models raise/recover as explicit transfers, never host-language errors. Lowering covers scalar, unit, aggregate, conditional, and match-produced fallible values; `try` copies failure into the caller's slot, `catch` binds ordinary `Error` data, and both run the correct deferred suffix. Differential and wasmtime fixtures prove success, propagation, recovery, code/message inspection, and defer order. The compiler API takes `PackageInput`; the raw CLI requires `--package ID`.
- [x] **Custom struct initialization** (2026-08-29). A receiver has one closed protocol (`type_function`, value method, mutating method, or initializer), and construction is an explicit `Initialize` HIR node rather than a call whose result is reinterpreted later. `SemanticAnalyzer` now performs the first whole-program flow proof: a three-state field lattice joins continuing `if`/`match`/`catch` paths, rejects writes in repeatable regions, and proves every successful exit initialized each field exactly once before any read, method call, or escape of partial `self`. The HIR interpreter creates a private incomplete record; MIR passes fresh caller-owned aggregate storage as initializer `self`; fallible initializers add the existing caller-owned Error slot without a second ABI. Differential and wasmtime fixtures cover default/named arguments, branch initialization, success, and failure.

- [x] **Unconstrained generic functions** (2026-08-31). Generic declarations
  retain nominal abstract type-parameter identities and are checked once from
  their signatures alone, including unused declarations and generic-to-generic
  calls. Abstract probe nodes are transactionally discarded. Calls perform
  structural inference or accept explicit type arguments; contextual `func` or
  `cfunc` values infer from the complete expected signature. Concrete
  specializations are memoized ordinary HIR functions, including defaults and
  recursion, so canonical MIR and every backend remain generic-free. An
  explicit `HirGenerator` budget bounds recursive expansion. The dedicated
  `hir/generics/functions.luc` owner prevents the mutually recursive body
  checker from absorbing this concern and borrows semantic services without a
  reference cycle. HIR/MIR oracles, Wasm, native QBE, and
  `examples/generic_functions.luc` agree. Generic nominals, conformances, and
  independently generic methods and detailed expansion accounting are
  recorded in later milestones below; serialized typed bodies remain.

- [x] **Memberwise generic structs** (2026-08-31). One abstract declaration
  schema now produces canonical applied HIR TypeIds with structurally inferred
  or explicit arguments, delayed bound validation after conformances, and
  concrete field-default specialization. A single TypeId-ordered fixed-point
  pass publishes target-neutral applied nominal and interface schemas; runtime
  storage fields deliberately exclude source-only defaults. Canonical MIR is
  still generic-free and keys struct lowering by concrete application rather
  than declaration, so representation-distinct applications cannot alias.
  `hir/generics/nominals.luc` owns inference and memberwise construction instead
  of extending the general body checker. HIR/MIR oracles, Wasm encoding, and
  native QBE execution agree on nested constrained generic functions and an
  omitted `T? = none` field default. Classes and enums remain explicit
  diagnostics; generic-struct conformances are recorded in the later
  milestone below.

- [x] **Generic struct value and mutating methods** (2026-08-31). A method
  inherits its nominal owner's one abstract type identity and is checked once
  from those parameters and bounds. Calling it through an applied receiver
  memoizes an ordinary concrete function with a substituted receiver,
  parameters, result, and defaults; recursive and method-to-method calls reuse
  that identity. Free-function lookup excludes method templates, while member
  lookup matches nominal declaration identity before selecting concrete owner
  arguments. HIR retains the abstract receiver for tooling, but canonical MIR
  and both artifact backends receive only concrete functions. Cross-module
  visibility, field-name conflicts, invalid abstract bodies, constrained owner
  calls, mutation, defaults, recursion, and distinct `Box[i64]`/`Box[str]`
  specializations are covered. The extended
  `examples/constrained_generics.luc` runs through both semantic oracles, Wasm,
  and native QBE. Independently generic methods and generic-nominal custom
  construction are recorded in later milestones; concrete generic-struct
  conformances are recorded in the next milestone.

- [x] **Generic struct conformances** (2026-08-31). A generic declaration
  retains one abstract conformance schema and validates every requirement
  against its owner-parameterized method signatures even when the declaration
  is unused. Each concrete nominal application materializes an ordinary
  `HirConformance` whose implementations are concrete specialized functions;
  static constraints and existential conversion share that same identity, and
  abstract probe artifacts are rolled back before executable HIR is published.
  Direct and mutating requirements, generic interface substitution,
  infallible-to-fallible adapters, cross-module visibility, and witness methods
  that return their own interface all follow the existing interface contract.
  Canonical MIR and both backends required no generic form or new lowering:
  they consume the same concrete witness tables already used by non-generic
  conformers. Both semantic oracles, native QBE, Wasm, focused diagnostics,
  and the extended `examples/constrained_generics.luc` agree. The 2,121-line
  declaration collector was reviewed at the size threshold; conformance
  publication remains inseparable from its type, method, visibility, and
  adapter resolution transaction, while one shared nominal-application matcher
  removed the prior parallel method-only form switch.

- [x] **Generic enums** (2026-08-31). Case construction infers or accepts
  concrete application arguments from payloads and context, validates the same
  nominal bounds and visibility rules as structs, and specializes value and
  mutating methods plus conformance witnesses into ordinary concrete HIR.
  Matching, payload binding, equality, ownership analysis, and native-surface
  containment now consume fully substituted case schemas. Canonical MIR keys
  enum types by concrete HIR TypeId rather than source declaration, preventing
  representation-distinct applications such as `Choice[i64]` and
  `Choice[str]` from aliasing. Struct and enum constructor children now use
  placed `(field, node)` runs, preserving named-argument evaluation order
  independently of declaration-order storage. Both semantic oracles, native
  QBE, Wasm, cross-module and diagnostic matrices, and
  `examples/generic_enums.luc` agree. The 2,146-line declaration collector and
  3,930-line function lowerer were reviewed again: the new behavior reused
  their existing declaration/application and aggregate-lowering transactions;
  extracting forwarding-only files would weaken rather than clarify ownership.

- [x] **Generic classes** (2026-08-31). One abstract class declaration now
  specializes initializer, value methods, deinitializer, fields, bounds, and
  conformance witnesses for every concrete application. HIR application
  metadata owns the substituted payload and exact deinitializer; the semantic
  oracle keys managed storage by concrete TypeId. Canonical MIR reserves a
  distinct target-neutral class identity for each concrete application, so
  representation-distinct `Box[i64]` and `Box[str]` payloads cannot alias while
  weak fields and captures retain the exact referent identity. Inference from
  initializer arguments and contextual result types, explicit arguments,
  cross-module visibility, recursive weak edges, existential dispatch,
  fallible construction cleanup, and unused-signature lifecycle
  materialization agree through both semantic oracles, native QBE, Wasm,
  focused diagnostics, and `examples/generic_classes.luc`. Collection records
  ordinary versus generic lifecycle callable identities as a union instead of
  overloading an integer table index. The 2,207-line declaration collector and
  3,950-line function lowerer were reviewed at the size threshold; this slice
  reused their cohesive declaration and class-operation transactions and
  introduced no platform, layout, ABI, or backend facts into HIR or MIR.

- [x] **Independently generic instance methods** (2026-08-31). A method on a
  concrete or generic struct, class, or enum may declare its own type
  parameters. Generic-owner and method parameters are remapped into one
  abstract identity with an explicit owner prefix: the receiver fixes that
  prefix, while inference and explicit member-call arguments address only the
  method suffix. This keeps abstract body checking, owner-dependent
  constraints, defaults, recursion, memoization, and specialization inside the
  existing generic transaction rather than layering a second substitution
  system over it. Member lookup retains the source name; the concrete symbol
  supplies a unique executable name when two method applications share one
  receiver. Canonical MIR therefore receives only distinct ordinary concrete
  functions and no generic form. Visibility, mutating receivers, evaluation
  order, invalid abstract bodies, constraint failures, owner/method name
  collisions, and the rule that generic methods cannot satisfy non-generic
  interface requirements have stable diagnostics. Both semantic oracles,
  native QBE, Wasm, focused lowering checks, and
  `examples/generic_methods.luc` agree across concrete and generic structs,
  classes, and enums. Generic nominal construction is recorded immediately
  below.

- [x] **Generic nominal custom construction and type functions** (2026-08-31).
  A custom initializer on a generic struct now specializes through the same
  callable transaction already used by generic class initialization; inferred,
  explicit, constrained, defaulted, and contextual construction all produce
  the exact concrete nominal result. Type functions on generic structs,
  classes, and enums infer their owner application from arguments or result
  context, including optional result injection, and accept explicit owner
  arguments after the function name when inference is impossible. Initializers
  and type functions use the enclosing nominal parameters and cannot declare a
  second independent scope; only instance methods have an applied receiver
  from which a separate suffix can be inferred. Call-head resolution is now a
  closed union of direct functions, struct construction, enum construction,
  and generic type functions instead of a sentinel record with mutually
  impossible fields. Abstract bodies, constraints, visibility, arity, and the
  declaration restriction have stable diagnostics. Concrete specialization
  names remain distinct, canonical MIR sees no generic declaration, and both
  semantic oracles, native QBE, Wasm, focused lowering checks, and
  `examples/generic_construction.luc` agree.

- [x] **Generic specialization budgets and accounting** (2026-08-31).
  Every concrete instance retains its declaration, source origin, parent
  instance, checked HIR-node count, and monotonic checking duration in
  target-neutral HIR reporting metadata. Re-entering an active template with
  a fresh type key is diagnosed immediately as infinite structural expansion;
  the package-wide fallback budget is configurable through the pipeline and
  raw CLI, and both failures print the complete source call/type path.
  `luce explain` presents those facts without selecting a backend.
  `luce build --time-report` carries each concrete function identity through
  package composition and reachability outside canonical MIR, then joins the
  surviving identity to backend-owned emission measurements:
  exact Wasm function-body bytes or QBE IL-function bytes plus translation
  time. Closed-world-eliminated instances stay visible without invented code
  sizes. The backends report only `FunctionId`, bytes, and time; generic/source
  meaning remains outside canonical MIR and the backend boundary. Serialized
  typed bodies remain with the future package-artifact owner.

- [x] **HIR package identities are composable semantic identities**
  (2026-09-01). A typed program now owns a compact package table and an
  explicit root `PackageId`; every module names its owning package. Most
  importantly, `ErrorCodeLiteral` retains the declaring package identity
  directly, so the HIR oracle and canonical-MIR lowering no longer recover
  the error domain from a whole-program string. This is the first package-
  artifact prerequisite: importing independently checked declarations cannot
  silently retag dependency errors as application errors. The representation
  remains target-neutral and adds no package, ABI, or layout policy to MIR.
  Serialized public APIs and typed generic bodies are still the open S16 work.

- [x] **Abstract generic checks own isolated flat HIR arenas** (2026-09-01).
  The generation transaction now distinguishes its published program arena
  from each temporary template arena while retaining exactly one `HirNodeForm`
  and one flat node/extra/value representation. Abandoning a checked template
  restores one arena instead of truncating six coupled tables. Package
  constants derive reference types from their canonical symbols, and the
  focused arena owner clones already-typed declaration defaults—including
  nested ordinary and placed operand runs—into the consuming arena without
  replaying source. Regression tests cover unused bodies, package error codes,
  function defaults, struct defaults, identity remapping, and detached table
  ownership. The 808-test, CLI, Wasm, and native-QBE gate was green. This
  isolated storage owner is the prerequisite used by the retained-body
  milestone below.

- [x] **Generic declarations retain typed HIR bodies** (2026-09-01). Every
  abstractly checked template now publishes its ordinary flat arena, body run,
  parameter-aligned typed defaults, body-local symbols, closures, shared
  cells, and generated closure functions. Types and symbols remain canonical
  package identities; only node, operand, and closure-table indexes are local
  to the retained body. Generic calls, initializers, contextual function
  addresses, omitted defaults, and constraint requirement calls are explicit
  resolved template-only HIR forms. They preserve declaration identities,
  inferred `TypeId`s, placed arguments, and requirement positions without
  retaining source syntax or performing speculative concrete specialization.
  Executable effect analysis traps if any template-only form crosses its
  boundary. Focused tests cover arena isolation, every deferred form, stable
  local-symbol ownership, and capturing/shared-cell closure metadata. The
  complete 811-test, CLI, Wasm, differential-QBE, and native-QBE gate is
  green. Concrete specialization still rechecks source in this checkpoint;
  the following milestone replaces that final replay path.

- [x] **Concrete generics specialize retained typed HIR without source replay**
  (2026-09-01). A focused `hir/generics/specializer.luc` recursively copies
  only reachable template nodes, substitutes every explicit and embedded
  `TypeId`, remaps body-local symbols and closure namespaces, and publishes
  distinct generated closure functions, captures, and shared cells for every
  concrete instance. Defaults specialize before their callable is exposed;
  a generic function value inside a default therefore resolves through the
  same memoized transaction as calls and initializers.

  Template-only generic calls, function addresses, omitted defaults, and
  requirement calls become ordinary executable HIR. Existential conversions
  deliberately ignore the abstract probe's rolled-back conformance index and
  resolve a concrete conformance from the substituted value/interface pair.
  The former source-span requirement replay table and concrete source-checking
  path are removed; a closed `Specialized` function-source variant makes
  accidentally re-entering the source checker a trap. Structural tests prove
  no template-only form reaches the executable arena, defaults target the
  concrete function identity, and two closure specializations own disjoint
  symbols and metadata. Differential fixtures execute generic defaults and
  generic closures through HIR, canonical MIR, Wasm encoding, and real QBE.
  The complete 814-test and product gate is the checkpoint proof.

- [x] **Retained generic HIR has one canonical strict package section**
  (2026-09-01). Focused literal, node, body, generic-declaration, and graph-
  validation owners encode the existing HIR directly; there is no package-
  specific lowering or backend representation. Every `HirNodeForm`, unary,
  binary, assignment, iteration, capture, default, flat operand run, local
  symbol, closure, shared cell, and generated closure function has one closed
  wire spelling. Compile-time floating literals round-trip canonical IEEE bits
  through a host-bitcast-free semantic inverse, preserving signed zero,
  subnormals, infinities, and canonical NaN.

  The decoder validates parallel arena lengths, postorder child ownership,
  nested run shapes, table bounds, generic type arguments and placed parameter
  positions, interface requirement arity, declaration/default alignment, and
  complete closure ownership before import can observe a body. Runtime-only
  `Value` carriers and unknown tags fail closed. Abstract existential
  conversions now retain `GenericInterfaceValue` instead of a temporary
  conformance index created and rolled back by template checking; the HIR
  specializer alone resolves the concrete conformance. Byte-stable round trips
  cover generator-produced defaults, calls, requirements, conformances, and
  closures, all six executable generic examples, every node and operation tag,
  and deliberately malformed decoded graphs. The complete 822-test and
  product gate is the checkpoint proof.

- [x] **The canonical typed HIR package payload is complete** (2026-09-01).
  One envelope composes the existing package identity, canonical type,
  nominal declaration, interface/conformance, executable, and retained-generic
  sections and reconstructs the exact existing `HirProgram`; it introduces no
  package-only IR and no backend or layout fact. The executable section owns
  the ordinary and C function variants, complete C boundary slots, constants,
  extern types and variables, globals, runtime bindings, closures, shared
  cells, specialization provenance, and the program's ordinary flat HIR arena.

  Encoding and decoding both validate the complete graph before exposing it:
  envelope/root identity, sealed-runtime ownership, every cross-table index,
  closure/function ownership, generic-instance provenance, exact function and
  nominal call identities, aggregate positions, and the strict separation
  between executable and template-only HIR nodes. Rich generated programs are
  byte-stable after reconstruction; one reconstructed program is re-analyzed
  and executed by the HIR oracle, and all six generic examples plus the broad
  executable corpus round-trip through the complete payload. The 830-test,
  CLI, Wasm, differential-QBE, and native-QBE gate is green. Import-time
  identity allocation/remapping and dependency-origin specialization remain
  the next package transaction.

- [x] **Typed HIR packages compose without dependency source replay**
  (2026-09-01). Artifact format 2 now carries the two semantic tables the
  first complete-payload pass exposed as import requirements: transparent
  aliases and abstract generic-nominal conformances. One import-plan owner
  allocates package, module, symbol, declaration, generic, conformance,
  closure, and specialization identities; structurally interns types and
  compiler-known interfaces; and rewrites ordinary plus retained-template HIR
  through those mappings. The importer validates the source, constructs a
  detached candidate, validates the complete composed graph, and publishes
  nothing on failure. Cross-table validation also preserves the one module
  declaration namespace and exact generic-conformance ownership.

  HIR generation seeds this validated graph before collecting root source.
  Imported aliases, visibility, signatures, defaults, bodies, closures,
  generic schemas, and conformance adaptations are consumed as semantic HIR;
  no dependency syntax is available. The last hidden replay path—generic
  struct field defaults—now specializes its already-typed arena node through
  the same HIR specializer as callable defaults. A separately compiled
  dependency proves public aliases, a generic interface, generic nominal
  conformance, generic closure capture, function defaults, and field defaults
  through root-source type checking, package re-encoding, both semantic
  oracles, Wasm emission, and real QBE execution. A dependency-private field
  also produces its exact source diagnostic from imported module metadata.
  The complete 835-test, CLI, Wasm, differential-QBE, and native-QBE gate is
  the checkpoint proof. S16 is closed; no generic form reaches MIR.

- [x] **The executable §15 generic rule audit is closed** (2026-09-01).
  Named type parameters, local inference, explicit arguments, nominal owner
  and independent method scopes, constraints/intersections, abstract body
  checking, concrete specialization, recursion, defaults, lifecycle,
  conformance replay, budgets, expansion paths, and cost accounting already
  had positive execution coverage. The final audit adds explicit exclusions
  for every §15.4 non-feature and proves integer generic arguments are rejected
  outside compiler-owned `array[T, N]`. The S16 remainder is now exactly one
  architectural feature: canonical serialized typed package bodies and their
  strict import transaction.

- [x] **Interfaces and constrained static generics** (2026-08-31). Interface
  declarations retain nominal, generic requirement identities in HIR; explicit
  struct, class, and enum conformances are validated package-wide after every
  member signature is known. Exact labels/types and mutability are enforced,
  while an ordinary generated Luce adapter implements the one permitted
  infallible-to-fallible lift. Generic bodies resolve calls solely from their
  written constraint intersections, retain that abstract resolution by
  declaration/source identity, and replay the selected conformance during
  specialization. This preserves the correct witness when two abstract
  parameters become the same concrete type and preserves fallibility instead
  of rediscovering a same-named concrete method. Concrete specializations are
  still ordinary functions, so HIR/MIR oracles, Wasm, native QBE, and
  `examples/constrained_generics.luc` agree without adding interface or target
  concepts to canonical MIR. Independently generic methods are recorded above
  and existential values separately below; serialized typed bodies remain on
  the generic/package-artifact boundary.

- [x] **Existential interface values and dynamic witnesses** (2026-08-31).
  Contextual conversion requires one explicit concrete conformance and HIR
  retains only the nominal interface, conformance, and requirement position.
  Canonical MIR preserves opaque interface handles, normalized erased-receiver
  witness signatures, structural ownership callbacks, and dynamic calls while
  excluding box sizes, offsets, pointer widths, ABI, and witness encoding. The
  sealed Luce runtime owns erased payload lifetime and wrapper COW: value
  mutation detaches, while class payloads keep shared identity. Fallible
  witness thunks propagate caller-owned errors and explicitly return null on
  success. QBE emits function-descriptor witness tables; Wasm emits equivalent
  linear-memory tables and indirect-call signatures. Both semantic oracles,
  verifier failures, both artifact backends, and `examples/interfaces.luc`
  cover generic interfaces, struct/class/enum conformers, returned and nested
  existentials, mutation, safe fallibility lifts, and genuine failure. The
  execution gate also exposed a backend allocator invariant: reclaimed
  payloads must be pointer-aligned because their first word stores the free
  link; QBE and Wasm now normalize managed payload alignment only at their
  backend boundaries.

- [x] **The executable §16 interface rule audit is closed** (2026-09-01).
  Interface calls now borrow the ordinary declaration-call placement
  transaction, so arbitrary named order, source evaluation order, exact
  labels, duplicate/missing arguments, and diagnostics have one owner. HIR
  stores source-ordered `(requirement parameter, node)` pairs consistently;
  typed-package validation/import/specialization, effect analysis, both
  semantic oracles, canonical MIR, QBE, and Wasm consume that same shape. A
  separately encoded dependency executes a reordered dynamic call after
  identity remapping. The rule matrix also proves exact arity, receiver
  mutability and instance-method requirements, the one safe fallibility lift,
  no interface inheritance/defaults/optional requirements/retroactive
  conformance/interface-to-interface conversion, and no automatic equality,
  hashing, type tests, or downcasts. `luce explain` now reports every concrete
  existential box and dynamic call, including value COW versus shared class
  identity, while statically constrained generic dispatch reports no
  existential cost. `examples/interfaces.luc` exercises the full product path.

- [x] **Compiler-known iteration protocols and executable `try for`**
  (2026-08-31). `Iterator[T]`, `Iterable[T]`, `FallibleIterator[T]`, and
  `FallibleIterable[T]` are closed language-owned interface identities
  materialized only when used, then follow ordinary conformance and witness
  semantics. One focused HIR owner selects concrete, constrained-generic, or
  existential dispatch; the loop retains a single resolved driver with a
  private mutable iterator, while fallible `next()` is the existing `Try`
  node. Nominals declaring multiple element types are rejected during
  conformance collection, and loop spelling diagnoses attempts to cross the
  infallible/fallible boundary. MIR adds no protocol instruction: existing
  calls, optionals, structured control, error propagation, and ownership
  helpers express the complete loop. `examples/iteration.luc` and focused
  negative/structural tests prove item/end/error separation, generic and
  existential use, break/continue, and observable iterator destruction on
  exhaustion, break, return, and error through HIR, MIR, native QBE, and Wasm.

- [x] **Compiler-derived structural markers and immutable hashing**
  (2026-08-31). `Equatable` and `Hashable` are closed standard marker
  interfaces used only in generic constraint lists: users cannot implement or
  store them as existential values, and their proofs produce no conformance or
  witness metadata in canonical MIR. Eligibility follows the resolved type
  graph recursively for scalars, strings/bytes, ranges, arrays, optionals,
  tuples, structs, enums, `ErrorCode`, and `Error`; mutable reference
  collections and classes remain excluded from hashing. `hash(value) -> u64`
  evaluates its operand once and becomes one typed HIR operation. The HIR
  oracle traverses semantic values, while the shared lowerer expands the same
  structure once into ordinary canonical integer, control, field, element,
  and memory operations. Only exact float encoding remains as a verified
  `FloatBits` scalar primitive; binary32 occupies the low 32 bits and signed
  zero is normalized first for hashing. QBE and Wasm legalize only that
  primitive and never reimplement aggregate semantics. Focused HIR, lowerer,
  verifier, differential, QBE, Wasm, and `examples/hashing.luc` gates prove
  that equal values hash equally across every admitted family. The 4,255-line
  function lowerer was reviewed at the ownership threshold: this recursive
  expansion shares its register/slot/region/address transaction with aggregate
  equality, so extracting it now would duplicate emission machinery or create
  forwarding-only indirection; it remains one marked 230-line section until a
  genuine shared function-emission owner replaces those helpers.

- [x] **Compiler-known exact-same-type ordering** (2026-09-01).
  `Comparable` is an ordinary language-owned interface with one implicit
  conforming-type argument and one requirement,
  `compare(self, other: Self) -> i64`. The owner binds `Self` while collecting
  a generic constraint or explicit nominal conformance; ordinary interface
  substitution, abstract generic checking, conformance replay, and concrete
  specialization handle everything after that point. Source cannot supply the
  hidden argument or store a heterogeneous existential, so the contract needs
  no downcast, associated-type, or reflection machinery.

  The audit also removed the final positional-only constrained-requirement
  argument checker. Static generic calls now use the same source-order and
  declaration-placement transaction as direct and dynamic calls, with
  reversed named arguments proving observable order through HIR, MIR, QBE,
  and Wasm. Exact signature, missing implementation, source-argument,
  existential, and reserved-name diagnostics are pinned. A generic nominal
  conformance, byte-stable typed package, separately encoded dependency
  conformance, both semantic oracles, and `examples/comparable.luc` execute
  without adding a MIR operation, runtime service, backend branch, layout
  fact, or platform condition.

- [x] **Cycle-aware structural list equality** (2026-08-31). `Equatable`
  recognition now closes recursive value proofs through list indirection while
  still rejecting any non-equatable outgoing component. The HIR oracle defines
  one coinductive transaction over ordered list-identity pairs. Shared lowering
  keeps finite list equality as an allocation-free canonical loop; genuinely
  recursive HIR types reserve private helper identities before body generation,
  preventing both compiler-stack and runtime recursion. Canonical MIR adds only
  opaque context create/release/visit operations. The sealed Luce runtime owns
  pair-set allocation and growth, while the generated MIR owns identity,
  length, tag, field, and element semantics; QBE and Wasm merely pass their
  backend-local list handles to the exact composed functions. HIR diagnostics,
  both interpreters, malformed-MIR verification, optimizer reachability,
  backend encoding, the complete native differential corpus, and the extended
  `examples/lists.luc` gate cover finite equality, identity, self/deep cycles,
  mismatches, alias-topology independence, and growth beyond initial context
  capacity. The 4,434-line function walk was reviewed again: the generated
  identity queue is independently owned, but equality emission shares the
  enclosing register/slot/region/address transaction and is kept as a marked
  cohesive section until a real common function-emission owner can replace
  forwarding-only extraction. Maps and sets now have their equality/hash
  prerequisite.

- [x] **Insertion-ordered maps and sets** (2026-08-31). Source map literals,
  explicit empty maps, and variadic set construction resolve once into typed
  HIR operations with complete arity, key/element hashability, assignment,
  and method diagnostics. Both semantic oracles define shared identity,
  optional lookup/removal, deduplication, insertion order, shallow copying,
  order-independent equality, recursive map equality, and alias-wide shape
  mutation guards. Canonical MIR preserves `Map(K,V)` and `Set(T)` handles and
  one hash-table protocol: generated MIR owns structural hashing, key equality,
  and typed retain/release callbacks, while the sealed runtime owns only dense
  insertion-order storage, private seeded buckets, collision chains, growth,
  and reclamation. QBE and Wasm supply layout and callback descriptors only.
  Verifier, optimizer, composition, both artifact backends, managed-value
  lifecycle tests, native/Wasm mutation traps, differential execution, and
  `examples/maps_and_sets.luc` cover the complete §12.5 contract. Recursive
  inline-layout checking now correctly treats map/set storage as indirection.
  The 4,991-line function walk was reviewed at the completed slice boundary:
  collection lowering shares its ownership, expression, region, and recursive
  equality transaction with the enclosing emitter. A separate file today
  would be a forwarding shell or duplicate state, so extraction remains
  deferred until the planned common function-emission owner can replace those
  dependencies cohesively.

- [x] **Collection literals close §4.5 without another representation**
  (2026-09-01). `[...]` now selects inferred or contextual lists, exact fixed
  arrays, and contextual immutable slices, including every legal empty form.
  A slice literal is the existing typed list literal followed by the existing
  immutable snapshot operation, so its construction order and escaping buffer
  ownership share one HIR/MIR/runtime implementation. Map and set literals
  keep their existing insertion protocol; static duplicate-map-key rejection
  now proves equality for scalar/bytes constants and recursively literal
  optional, tuple, and fixed-array keys, while computed duplicates still
  replace at execution. Focused diagnostics reject heterogeneous/numeric-union
  elements, invalid contextual values, `{}`, and duplicate literal keys.
  Observable differential output proves exact left-to-right evaluation for
  list, array, slice, map keys/values, and set arguments through both semantic
  oracles and the real QBE product; Wasm consumes the same unchanged MIR. The
  adjacent §9.6 audit also corrected its shared literal comparison boundary:
  negative floats are valid numeric patterns, signed zero duplicates, and
  `bytes` is not a scalar/string pattern. No MIR form, runtime service, backend
  path, target fact, or new file was added. The 3,456-line body checker remains
  one recursive typed-expression transaction; aggregate construction and the
  closed static literal proof are marked cohesive sections, and extraction
  would currently introduce a forwarding owner rather than separate state.

- [x] **Triple-quoted literals normalize once at the source boundary**
  (2026-08-31). `str`, raw `str`, and `bytes` triples share one linear
  formatter-owned pass in `compiler/formatting/triple_strings.luc`. A closing
  delimiter on its own line defines the space baseline; opening/closing
  structural line breaks disappear, CRLF/CR become LF, blank lines may be
  shorter, and a nonblank outdented line is rejected. Escape decoding runs
  afterward, so raw triples preserve backslashes and byte triples retain exact
  byte/scalar rules. The decoder then emits the existing canonical text/bytes
  constant: no triple fact enters HIR, MIR, runtime, or a backend. Focused
  decoder/HIR rejection tests, both semantic oracles, QBE, Wasm, and
  `examples/strings.luc` prove the contract.

- [x] **Formatted strings and closed `Display` execute end to end**
  (2026-08-31). One formatter-owned stream pass preserves interpolation field
  boundaries while applying the existing triple indentation and line-ending
  law to literal fragments. HIR evaluates fields once in source order, keeps
  builtin scalar conversion explicit, and resolves user values through the
  same static, constrained-generic, or existential `Display` requirement
  machinery as ordinary interface calls. Canonical MIR retains one linear,
  target-neutral create/append/finish builder plus typed display services; a
  focused affine verifier rejects forged, reused, unfinished, branch-escaping,
  or cross-region builders and permits abandonment only on trapping paths.
  The sealed Luce runtime owns growth, Unicode/decimal rendering, and a Luce
  translation of Ryū for width-specific shortest binary32/binary64 output.
  Its only representation capability is the exact, verified `FloatBits`
  scalar operation; target layout and byte order remain backend-owned. HIR and
  MIR oracles, verifier negatives, the full differential QBE product corpus,
  Wasmtime, and `examples/formatted_strings.luc` cover nested construction,
  braces and triples, evaluation order, concrete/generic/dynamic dispatch,
  integer extrema, Unicode, signed zero, fixed/scientific boundaries,
  subnormals, infinities, NaN, and representative upstream Ryū boundary and
  regression vectors. The gate found and pinned a negative-integer conversion
  trap in the runtime and Wasm's incomplete subnormal/boundary constant
  encoder. The general MIR verifier is now 1,773 lines after its
  independent affine proof moved to `mir/builder_verifier.luc`. The 1,616-line
  runtime source remains one strongly marked module because Luce deliberately
  has module-private declarations and no package-private visibility; splitting
  private services today would expose them or add forwarding indirection. The
  5,067-line function lowerer was reviewed at the same boundary: formatting is
  an 86-line marked section, but it shares the emitter's register, slot,
  region, address, and ownership transaction. Its planned holistic extraction
  still waits for a real shared function-emission owner rather than another
  forwarding shell.

- [x] **Extern structs remain ordinary values until the C pointer boundary**
  (completed 2026-09-02). The terse raw fields normalize into the existing
  nominal member model with one boundary capability; documentation, constant
  defaults, methods, custom initializers, interface conformance, construction,
  field access, copies, equality where every field is equatable, zero values,
  visibility, HIR execution, and structural MIR lowering reuse the ordinary
  value paths. Fields are immutable and implicitly public for raw-wrapper
  access; methods retain ordinary visibility, receiver, and body rules.
  HIR rejects nullable extern structs, by-value C results, ordinary/nonnative
  aggregate fields, recursive storage, and every field outside the currently
  executable scalar/handle/nested-extern/cfunc vocabulary. Canonical MIR records no
  layout: its call adapter recursively copies semantic fields into fresh input
  storage and reads fresh output storage back field by field, while QBE and
  Wasm alone choose offsets, alignment, pointer width, and stack placement.
  The semantic oracle models the same crossing as a fresh checked record;
  focused parser/HIR/package/MIR diagnostics and a real QBE/libc
  `clock_gettime` execution followed by an ordinary Luce method prove natural
  host layout, writable `out` crossing, and immediate return to value
  semantics. The executable `native_interop.native.luc` example carries the
  product proof.

- [x] **Incoming and nullable `cfunc` pointers remain opaque until invocation**
  (2026-09-01). HIR now distinguishes one declared C adapter/symbol from an
  arbitrary code token supplied by C, and each semantic oracle has a separate
  explicit function-pointer host. Direct results, `out` slots, optionals, and
  extern-struct fields preserve raw identity; zero decodes to `none` only for
  nullable slots, while a bare zero traps at invocation or its next C input
  crossing. Canonical MIR reuses its target-neutral pointer and exact verified
  C signature. Its extern memory interface can populate a logical struct field
  while byte offsets remain private to the backend's `TypeLayout`. Capture-free
  names and lambdas share the generated C-adapter path; captured closures stay
  rejected. HIR execution, source-lowered MIR execution, verifier coverage,
  the differential corpus, and real libc `signal` round-tripping through QBE
  prove the contract. Callback thread/runtime-context enforcement and the
  remaining C-export callback matrix remain open.

- [x] **Anonymous `foreign` data pointers reuse one target-neutral boundary
  protocol** (2026-09-01). HIR adds one atomic, opaque, equatable type distinct
  from every nominal `extern type`; it has no literal, arithmetic, ordering,
  hashing, or representation. Ordinary `foreign?` values retain the canonical
  tagged optional shape. The semantic oracle and the sole HIR-to-MIR boundary
  adapter encode/decode null only for C slots, reject zero in bare direct
  crossings, and leave zero read from an extern-struct field inert until its
  next bare crossing. Canonical MIR reuses its existing abstract pointer, so
  neither MIR nor the frontend acquired pointer width, alignment, or platform
  layout. Focused HIR and MIR hosts cover direct, nullable, output, cfunc
  signature, export, and extern-struct fields; Wasm consumes the same verified
  MIR; real QBE/libc `malloc`, zero-length `writev`, and `free` prove the native
  data-pointer path. `native_interop.native.luc` carries the product example.
  The ownership review added no files or backend special cases: the 22-line
  semantic-oracle addition remains inside its marked C-boundary transaction,
  and the canonical lowerer changed only the shared pointer predicate.

- [x] **Borrowed C strings copy through one owned text boundary**
  (2026-09-01). `extern func` alone now admits direct `str` inputs, results,
  and `out` slots; `cfunc`, C exports, extern structs, and extern variables
  retain their deliberately closed surfaces. The HIR oracle exposes exact
  NUL-terminated UTF-8 bytes to its explicit host and scans host bytes only to
  the first terminator. Canonical MIR keeps the ordinary
  `{owner, data, byte_length}` string shape: its adapter builds input storage
  with existing typed allocation/move instructions, decodes every result
  before releasing those call-scoped allocations, and uses the single
  target-neutral `CStringCopy` operation to scan, validate, and publish a
  fresh immutable owner. The sealed Luce runtime owns the scan and complete
  UTF-8 validation; null traps `null_foreign` and malformed text traps
  `invalid_utf8`. Focused HIR/MIR hosts cover input encoding, result and `out`
  copying, null, malformed UTF-8, and missing termination; the MIR verifier,
  differential Wasm/QBE encoders, real QBE/libc `strchr`, and the expanded
  `native_interop.native.luc` example prove the vertical slice. The real C
  result deliberately aliases its input, pinning decode-before-cleanup rather
  than merely checking the final text. No source file or parallel lowering
  path was added. The size review records the shared function lowerer at 5,250
  lines and the stateful MIR oracle at 2,038: this slice is respectively a
  46-line addition inside the existing marked C-boundary transaction and one
  instruction plus the oracle's narrow foreign-memory view. Splitting either
  now would divide a single register/memory ownership transaction; their
  planned holistic ownership refactor remains preferable to forwarding files.

- [x] **Inbound C memory copies through three standard helpers without a new
  backend path** (2026-09-02). Compiler-supplied standard source now carries
  explicit, non-transitive authority to use the closed `Builtin` namespace;
  project spelling, paths, and imports cannot acquire it. The ordinary public
  `c.bytes_at`, `c.cstring_at`, and `c.take_str` wrappers expose exact-copy,
  validated-text, and copy-then-dispose semantics. Omitting a `cfunc` result
  now denotes `unit`, matching the disposer spelling in the language contract.

  HIR retains only opaque foreign tokens, logical counts, and two semantic
  copy operations. Its oracle receives a narrow explicit foreign-memory host,
  rejects zero before reading even a zero-length range, checks exact byte
  counts, and validates UTF-8 before a disposer can run. Shared lowering reuses
  the existing affine buffer builder for exact bytes and the existing
  `CStringCopy` transaction for text, so canonical MIR, its runtime contract,
  QBE, and Wasm gained no new instruction, service, or backend case. Both
  semantic oracles prove successful copies, `null_foreign`, `invalid_utf8`,
  and dispose-after-copy ordering; a real linked QBE/C harness proves the byte
  contents and exactly one successful disposal. Typed-package identity/node
  round trips preserve standard provenance and both HIR forms. The complete
  906-test, CLI, Wasmtime, and native-QBE gate is green. Automatic inclusion
  of standard modules in compiler products remains S30.

- [x] **The first Clang-to-QBE FIIR binding is an executable product path**
  (2026-09-02). Backend-independent FIIR now records exact source origins,
  calling convention, scalar value/object representations, boundary contract
  fields, the Clang target and complete argument vector. Its validator rejects
  incomplete facts before generation. Backend-owned Clang inspection uses the
  same command and arguments for target, predefined-macro, and JSON-AST
  queries; every host-tool failure reports captured stderr and removes its
  owner-only temporary directory.

  The first deliberately narrow generator accepts only exact IEEE binary64 C
  `double`. It emits deterministic JSON, a raw native Luce module whose public
  surface uses nominal `c.double`, and a C adapter with compile-time size and
  floating-model assertions. HIR and canonical MIR therefore see only the
  ordinary nominal wrapper and an exact `f64` adapter call; no target width,
  layout, triple, compiler flag, or platform condition enters either shared
  representation. Unsupported integer, pointer, variadic, and exotic-float
  boundaries fail with explicit generation diagnostics.

  `luce bind` installs explicit FIIR/raw/adapter destinations atomically per
  product. Package loading gives compiler-supplied standard modules their own
  root and provenance, so the generated module imports stable module `c`
  independently of the application layout. Native `luce build` accepts
  explicit C sources and compiler arguments only for QBE materialization; the
  same arguments select the C target and compile/link the sources, and linker
  failure still preserves the previous executable. Focused FIIR tests, the
  HIR/MIR/Wasm/QBE semantic triangle, direct generated-adapter execution, and
  the CLI's `temperature.h` → bind → native build → C execution fixture prove
  the product loop. The remaining §21 importer vocabulary and binding recipes
  stay open under S21.

- [x] **Fundamental C integers preserve one semantic shape through the QBE
  boundary** (2026-09-02). FIIR distinguishes the eleven fundamental C integer
  families independently of their target widths and records plain `char`
  signedness explicitly. Compiler-supplied `c` source exposes a distinct
  nominal wrapper for each family; signed values use an `i64` logical carrier,
  unsigned values use `u64`, and plain `char` always uses `i64`. These are
  values, not C layouts, so the generated raw Luce module is byte-identical
  for artificial 16- and 32-bit `int` targets.

  The generated C adapter owns every representation fact. Compile-time
  assertions pin Clang's recorded size, signedness, and range; input carriers
  are checked before the foreign call and report `native_integer_range`
  through ordinary generated Luce control flow; C results widen losslessly.
  Every integer family has generator coverage and a real Clang/C11
  `-Wall -Wextra -Werror` fixture. Valid and overflowing `int` calls agree in
  the HIR and MIR oracles, emit through Wasm/QBE, and execute against the real
  C temperature fixture through QBE. No target width, limit, triple, or C
  spelling enters HIR or canonical MIR.

- [x] **C Boolean preserves semantic identity through FIIR and QBE**
  (2026-09-02). The generated public surface uses nominal `c.boolean` over one
  Luce `bool`; no integer width, truthiness conversion, or target object layout
  enters HIR or canonical MIR. FIIR retains Clang's `_Bool` width, while the
  backend-owned C adapter asserts it and exposes `_Bool` only at the physical
  boundary. Artificial 8- and 16-bit facts produce byte-identical raw Luce and
  distinct FIIR/C products. Focused generation, both semantic oracles,
  Wasm/QBE encoding, the CLI binding path, and a real linked QBE/C call cover a
  Boolean parameter and result.

- [x] **Fundamental C floating families keep their identities and exact
  formats** (2026-09-02). FIIR now records `float`, `double`, and `long double`
  independently of radix, precision, exponent range, and storage width. Exact
  IEEE binary32 `float` uses nominal `c.float` over `f32`; exact IEEE binary64
  `double` and `long double` use distinct nominal wrappers over `f64`. The
  backend-owned adapter alone selects the C spelling, asserts the complete
  model, and casts an exact binary64 `long double` without changing canonical
  shape. Extended `long double` is rejected instead of being narrowed. The
  temperature binding carries a real C `float` through Clang, both semantic
  oracles, Wasm/QBE encoding, CLI build/run, and linked QBE/C execution;
  focused synthetic facts prove same-representation family identity and the
  explicit extended-format refusal.

- [x] **Scalar C typedefs retain target-independent boundary identities**
  (2026-09-02). FIIR records each typedef as a validated, acyclic edge to an
  earlier scalar type with its exact declaration origin. The generated raw
  module exposes a nominal carrier over the lossless Boolean, integer, or
  floating domain; the C adapter alone spells the typedef, asserts its size
  and compatible target, performs integer range checks, and calls C. Nested
  aliases and a referenced dependency-owned `size_t` are handled without
  importing unrelated dependency declarations. Synthetic targets prove that
  both underlying integer family and width may change while generated Luce is
  byte-identical. The real `luce_degrees` example executes through HIR, MIR,
  Wasm/QBE encoding, CLI materialization, and linked QBE/C; malformed edges,
  pointer targets, and Luce-keyword names fail explicitly.

- [x] **Imported C enums remain target-independent open foreign values**
  (2026-09-02). FIIR records named and typedef-backed enumeration identity,
  exact source origins, forward/anonymous declaration relationships, and the
  complete signed-`i64`/unsigned-`u64` enumerator domain. Implicit successors
  are evaluated deterministically and duplicate-valued enumerators remain
  equal constants. The generated raw module uses one nominal private
  sign-magnitude carrier with public typed constants; enum typedefs are
  transparent names for that carrier rather than duplicate semantic types.

  One shared expanded-signature plan feeds the Luce declaration and C adapter.
  The adapter maps only declared constants to the header's exact enum type,
  initializes every output before validation, and reports invalid inputs,
  invalid results, and impossible statuses without leaking uninitialized data.
  No enum size, compatible integer type, layout, or ABI class enters HIR or
  canonical MIR. Synthetic named, anonymous, forward, duplicate, implicit,
  full-`u64`, malformed-layout, and `-fshort-enums` fixtures cover the model.
  The real temperature binding executes a negative enumerator through both
  semantic oracles, Wasm/QBE encoding, CLI build/run, and linked QBE/C; a real
  C result outside the declared set traps `native_enum_value`.

- [x] **Constant-only anonymous C enums become constants, not phantom types**
  (2026-09-02). The Clang decoder retains every enumerator's evaluated value,
  selected integer type, and source origin in a first-class FIIR constant
  declaration. FIIR validation checks the complete signed-`i64`/unsigned-`u64`
  domain against that declared C type. The raw module emits one universal
  `c.integer_constant` sign-and-magnitude value, while target sizes, selected
  integer families, and range assertions remain in FIIR and the backend-owned
  C product. That product asserts every constant's exact C type and value, so a
  stale raw module cannot compile against a changed header silently; synthetic
  width and family changes leave generated Luce byte-identical. Named and
  typedef-backed enums remain on the separate
  open-enum carrier path. Focused malformed/full-domain fixtures, both
  semantic oracles, Wasm/QBE encoding, the real linked QBE/C gate, and the
  `c_import` example exercise the constants. Recipe-classified bitmasks remain.

- [x] **Header-local fundamental-integer C objects become evaluated FIIR constants**
  (2026-09-02). The importer accepts only selected-header `static const`
  definitions with initializers, including const-qualified typedefs, and asks
  Clang to prove and evaluate each value. Four bounded 16-bit target facts
  reconstruct the entire signed-`i64`/unsigned-`u64` union without depending
  on target endianness or signed object representation. Boolean, floating,
  aggregate, mutable, external, and nonconstant objects fail explicitly
  instead of being copied into generated source with changed semantics.

  FIIR reuses its typed sign/magnitude constant declaration; generated Luce
  therefore remains byte-identical when the target's accepted C integer family
  changes. The backend-owned C adapter asserts the exact header type and value.
  Full-domain synthetic fixtures, both semantic oracles, Wasm/QBE encoding,
  CLI materialization, warning-clean C11, and the real linked temperature
  example cover the path. No new HIR, MIR, backend instruction, runtime type,
  or platform branch was introduced.

- [x] **Explicitly selected fundamental-integer C macros become evaluated FIIR constants**
  (2026-09-03). The repeatable `luce bind --macro-constant NAME` option is the
  complete import set and preserves request order. Clang's normalized
  preprocessing stream establishes each final active object-like definition
  and source location; absent, function-like, invalid, and duplicate selections
  fail explicitly. A filtered local-`__auto_type` AST preserves exact typedef
  spelling without requiring a constant initializer, then a separate filtered
  value AST proves constant evaluation and supplies four bounded 16-bit words.
  At this milestone the separation gave non-integer macros stable importer
  diagnostics; the later scalar-macro milestone extends the same probes while
  leaving every C expression and preprocessing rule owned by Clang.

  FIIR now identifies anonymous-enumeration, object, and macro provenance for
  each standalone constant. Generated Luce retains the same universal
  sign/magnitude carrier; the backend C product asserts the selected macro's
  exact type and value. The filtered probe roots avoid reparsing entire included
  header ASTs and keep selected imports near the existing inspection cost.
  Pure preprocessing/type/value failures, full-domain values, source origins,
  CLI materialization, HIR/MIR oracles, Wasm/QBE encoding, warning-clean C11,
  and real linked execution cover the path. No macro replacement text is
  interpreted by Luce, and no target fact enters HIR or MIR. The completed
  repository gate is 957/957 compiler tests plus CLI, Wasm, and native QBE
  shell gates.

- [x] **Declaration-only external scalar C objects remain live through FIIR
  accessors** (2026-09-03). The Clang decoder now separates header-local
  compile-time values from external storage. FIIR records each external
  object's scalar or scalar-typedef type, read-only versus read-write access,
  volatility, and source origin. Generated raw Luce exposes a reader and, for
  non-const storage, a writer; target-sized integers reuse the existing
  checked status protocol before any store.

  The backend-owned C product statically verifies the exact object type and
  const/volatile qualifiers, then performs every actual read or write. Shared
  HIR and MIR consequently see only ordinary calls carrying `bool`, `i64`,
  `u64`, `f16`, `f32`, or `f64`; they contain no object layout, address,
  volatile instruction, ABI classification, or platform branch. Const
  storage has no writer. Definitions, volatile would-be constants, atomics
  including typedef-hidden atomics, thread-local storage, arrays, and other
  nonscalar shapes fail with owned diagnostics.

  Synthetic validation and target-variation tests prove byte-identical raw
  Luce across alternate C integer layouts. The temperature example reads a
  linked const capacity and mutates a linked volatile typedef object through
  HIR and MIR semantic hosts, Wasm/QBE emission, the real QBE/C executable,
  and the `luce bind` → native CLI path. No HIR, MIR, runtime, or handwritten
  backend feature was added. The completed repository gate is 960/960
  compiler tests plus CLI, Wasm, and native QBE shell gates.

- [x] **External C enumeration objects reuse one checked value boundary**
  (2026-09-03). FIIR now admits named and typedef-backed enumerations as live
  declaration-only objects without acquiring any new storage representation.
  Generated raw readers and mutable writers use the existing target-neutral
  Boolean-plus-magnitude carrier. The backend-owned C product maps only
  declared enumerators to or from the exact object type, returning the existing
  input/result statuses for undeclared values; raw Luce turns either status
  into `native_enum_value` before a foreign value reaches application code.
  Const objects remain read-only, and volatile access remains a C effect.

  The implementation factors scalar and enumeration object rendering at the
  value-adapter boundary rather than adding an HIR/MIR object case. Generated C
  parameter/local names are selected against the imported symbol, closing a
  shadowing corner for scalar objects named `value` and enumeration objects
  named like expanded carrier fields. Focused FIIR tests, corrupted-object HIR
  and MIR hosts, Wasm/QBE emission, the real example and CLI, warning-clean
  ordinary and `-fshort-enums` native C builds, and a linked object containing
  undeclared value `7` cover the slice. The completed repository gate is
  962/962 compiler tests plus CLI, Wasm, and native QBE shell gates.

- [x] **Header-local C Boolean and exact-IEEE objects become semantic
  constants** (2026-09-03). The Clang target-fact probe uses constant-evaluated
  bit casts to capture `_Bool`, binary16 `_Float16`, binary32 `float`, and
  binary64 `double`/`long double` without decimal or host-representation loss.
  FIIR gives Boolean and floating values distinct validated cases and retains
  floating encodings exactly in its auditable JSON product. Unsupported
  extended formats and malformed high bits fail before generation.

  Generated raw Luce reconstructs nominal `c.boolean`, `c.float16`, `c.float`,
  `c.double`, or `c.long_double` semantic values. Finite values, infinities,
  and signed zero survive exactly; all NaN payloads intentionally map to the
  language's single observable NaN. The backend-owned C product independently
  checks the exact declared type and semantic value, including zero sign and
  special-value class. HIR and MIR therefore receive only their existing
  `bool`, `f16`, `f32`, and `f64` shapes—no C bits, layout, ABI rule, or new
  instruction.

  Pure FIIR validation/generation, both semantic oracles, Wasm/QBE encoding,
  `luce bind`, warning-clean C11, and a real linked QBE/C executable cover the
  slice. Slow real-Clang and atomic-installation tests now have a dedicated
  198-line owner, keeping the pure FIIR test file below its 2,000-line review
  threshold. The completed repository gate is 964/964 compiler tests across
  35 files plus CLI, Wasm, and native QBE shell gates.

- [x] **Header-local C enumeration objects retain open nominal constant
  values** (2026-09-03). FIIR gives named, typedef-backed, and alias-backed
  `static const` enumeration definitions a distinct validated constant case.
  Clang supplies one semantic sign fact and four bounded words from C's
  defined `uint64_t` conversion, preserving the complete supported
  signed-`i64`/unsigned-`u64` union without inferring a target enum width.
  Values without a corresponding enumerator remain valid C enum values rather
  than being rejected, collapsed to a case identity, or reclassified as
  integer constants.

  Generated raw Luce constructs the existing nominal Boolean-plus-magnitude
  carrier and retains the constant's declared typedef spelling. The
  backend-owned C product independently asserts the exact declared type and
  semantic value. HIR and canonical MIR therefore gain no foreign, target, or
  platform concept. Pure invalid-sign and negative-zero coverage, real Clang
  inspection, both semantic oracles, Wasm/QBE emission, warning-clean C11,
  ordinary and `-fshort-enums` linked QBE execution, and the complete CLI
  bind/build/run example cover both declared value `-2` and unnamed open value
  `7`. Object-constant fixtures and regressions now have a dedicated 546-line
  owner; the general Clang suite is 1,575 lines. The completed repository gate
  is 965/965 compiler tests across 36 files plus CLI, Wasm, and native QBE
  shell gates.

- [x] **Selected scalar C macros reuse the exact FIIR constant vocabulary**
  (2026-09-03). The explicit `--macro-constant` inventory now admits Boolean,
  fundamental-integer, exact IEEE binary16/binary32/binary64,
  typedef-backed, and named-enumeration values. One shared Clang value-probe
  renderer and decoder serves both header-local objects and selected macros;
  the macro path retains its separate preprocessing and `__auto_type` type
  products, so Luce still never parses replacement text or guesses C types.
  Exact floating bits preserve finite values, signed zero, infinities, and the
  language-observable NaN class. Enumeration macros retain their nominal open
  Boolean-plus-magnitude carrier, including unnamed value `7`.

  Generated Luce uses only the existing scalar and enum carriers. The
  backend-owned C product independently reasserts each macro's exact type and
  semantic value. Synthetic malformed-state tests and the real temperature
  header cover type rejection, nonconstant values, missing binary16 facts,
  invalid Boolean/enum facts, full generated products, both semantic oracles,
  Wasm/QBE emission, warning-clean C11, ordinary and `-fshort-enums` linked QBE
  execution, and the complete bind/build/run CLI path. Pointer, array, and
  string macros remain rejected until their storage/lifetime contracts land.
  Each full C expression is evaluated once before four bounded 16-bit facts
  refer to it; this reduces Clang's filtered object/record fact JSON from 1.84
  MiB to 1.42 MiB and the nine-macro product from 1.86 MiB to 0.99 MiB without
  changing the durable FIIR format. No HIR, MIR, runtime, platform branch, or
  backend instruction was added. The completed repository gate is 967/967
  compiler tests across 36 files plus CLI, Wasm, and native QBE shell gates.

- [x] **Plain C records cross FIIR through logical field carriers, never
  frontend layout** (2026-09-02). The Clang decoder catalogs complete structs,
  resolves anonymous typedefs and forward declarations, and recursively keeps
  dependency-owned records only when a selected header declaration reaches
  them. A second deterministic Clang AST probe evaluates `sizeof`, alignment,
  and every `offsetof`; validated FIIR retains those target facts for audit.
  Bit-fields and unions are rejected at the reachable record boundary, while
  unrelated unsupported dependency records remain ignored.

  Generated Luce exposes an ordinary declaration-order value record plus a
  private fixed-carrier `extern struct`. Shared fieldwise encode/decode helpers
  preserve Boolean, integer, exact floating, typedef, enumeration, and nested
  record semantics. The backend-owned C adapter alone defines the fixed
  carrier's C storage, asserts the exact record size/alignment/offset/type
  facts, reconstructs the header type, and lets the C compiler perform the
  by-value ABI call. Static converters are emitted only for records that cross
  a function boundary, keeping standalone declaration products warning-clean.
  No target layout, ABI class, triple, or C spelling entered frontend, HIR, or
  canonical MIR.

  Focused tests cover target-layout variation with byte-identical generated
  Luce, malformed/missing layout, nested dependency reachability, unrelated
  bit-fields, and standalone records. The real temperature fixture combines
  an anonymous typedef record with a forward-declared tagged record containing
  a scalar typedef and enum. It executes through the HIR and MIR semantic
  hosts, Wasm and QBE encoders, `luce bind`, warning-clean C11 (including
  `-fshort-enums`), and linked native QBE/C calls. The MIR oracle gained only a
  symmetric logical field-read host view beside its existing field-write view;
  byte placement remains backend-owned. This added 15 cohesive lines to the
  existing 2,776-line oracle, which remains a candidate for the planned
  behavior-preserving backend refactor; splitting this one memory-boundary
  operation now would separate it from the storage authority it must use.

- [x] **Borrowed C lists expose their one existing dense representation**
  (2026-09-01). `extern func` input parameters now admit `list[H]` exactly
  where `H` is a boundary scalar, named handle, or `foreign`; results, `out`
  slots, nested/text/optional elements, extern-struct fields, cfunc signatures,
  and C exports remain closed with focused diagnostics. HIR keeps the ordinary
  shared list identity and gives its explicit semantic host a read-only
  C-shaped sequence. Canonical MIR keeps the same typed list handle and lowers
  the boundary using only existing `ListLength`, `ListElementAddress`,
  structured control, and the raw C call: nonempty values lend the first dense
  element, empty values lend null, and the source-declared count crosses as its
  own untouched argument. No packing, element copy, new MIR operation, or
  backend-specific lowering was added. A target-neutral loop rejects zero in
  every bare pointer-shaped element before C observes it. Focused admission,
  HIR, lowering, null-element, and logical-memory tests cover the contract;
  the differential harness reaches Wasm and QBE; real QBE/libc `memcmp` and
  `native_interop.native.luc` prove ordered bytes are read directly from the
  runtime list buffer. The ownership/size review added no files: the 49-line
  lowerer transaction remains inside its marked C-boundary section (now 5,300
  lines), while the MIR oracle's 20-line read-only host view remains inside
  its existing external-memory boundary (now 2,058 lines). Splitting either
  would separate the adapter from the ownership and register transaction it
  documents; both remain candidates for the planned holistic refactor.

- [x] **The complete §9.6 match matrix is closed** (2026-09-01). Existing
  enum, optional, Boolean, literal, range, alternative, statement, expression,
  and payload-binding paths now have the missing finite-domain proof: adjacent
  non-overlapping singleton/range intervals close every signed or unsigned
  integer width and the Unicode-scalar domain without enumerating values.
  Character predecessor/successor explicitly cross the surrogate gap rather
  than constructing an invalid `char`. Once earlier patterns cover a complete
  domain, a later arm is rejected as unreachable. A legal enum `_` now emits
  structured `L0901`, because it would hide the exhaustiveness error for a
  future case; fixed Boolean and optional domains remain quiet. Both semantic
  oracles, verified canonical MIR, Wasm encoding, and real QBE execution agree
  on the new full-domain fixtures. No MIR instruction, backend path, target
  fact, source file, or runtime service was added. The body checker remains one
  mutually recursive lexical/type transaction; its 3,365-line ownership was
  reviewed at this boundary, and extracting only the 247-line marked match
  section would replace direct expression/statement checking with a forwarding
  interface rather than establish an independent owner.

- [x] **The rest of §9 is closed as one target-neutral control-flow contract**
  (2026-09-01). The audit found one semantic asymmetry: an uncontextualized
  conditional previously chose its first arm's type and forced the second arm
  into it, so swapping `never`, `T`/`T?`, or infallible/fallible function arms
  could change acceptance. HIR now computes one symmetric join, while an outer
  expected type still checks both arms directly. Equal types, bottom removal,
  optional injection, conversion to an interface type established by one arm,
  and the sole function-fallibility lift are the closed implicit cases;
  unrelated or doubly context-dependent arms receive stable diagnostics.
  Focused HIR structure tests and the differential corpus execute every join
  through both semantic oracles, verified MIR, Wasm, and real QBE.

  The rule-by-rule pass also pins Boolean conditions, lexical branch and
  conditional-binding scope, immutable range/protocol elements, illegal loop
  exits, descending and maximum-closed ranges, nested `break`/`continue`, and
  bare/value/every-path returns. Existing defer execution already covered
  registration-time receiver/argument capture, LIFO fallthrough, return,
  both loop exits, propagation/recovery, and trap suppression; new negatives
  make the failure-capable-cleanup rule explicit and prove that handling it in
  a non-failing wrapper is accepted. `conditional_binding.luc` now exercises
  order-independent optional joins without adding another example file, while
  `iteration.luc` and the defer corpus retain the broader product proof. No
  MIR instruction, backend path, runtime service, source file, target fact, or
  Stage-0 workaround was added. The body checker is now 3,577 lines; its
  mutually recursive expression/scope transaction remains a deliberate
  post-coverage holistic refactor candidate rather than being split into a
  small forwarding file during this audit.

- [x] **The complete §10 value-data model is closed before the backend
  boundary** (2026-09-01). The rule audit pins struct field mutability,
  declaration order, synthesized and custom initialization, recursive-value
  rejection, source visibility, tuple positionality, fixed-array length and
  copy semantics, owned array-to-slice snapshots, enum construction and
  exhaustive payload matching, derived equality/hashability, and every
  deliberate omission: inheritance, object spread, ordinary unions, tuple or
  enum projections, implicit array views, user value parameters, source
  ordinals, operator overloads, and ordinary layout attributes. Existing
  examples already form the readable proof, so the audit adds no duplicate
  showcase program.

  The audit found one real canonical-MIR defect: ordinary enums were rejected
  above 256 cases because their internal selector was hard-coded to `u8`.
  HIR now documents case position as semantic identity rather than an ABI tag;
  MIR selects the smallest sufficient Luce unsigned scalar, the verifier
  requires that scalar to represent every case, and construction, ownership,
  pattern matching, equality, and hashing all read the type's selected tag.
  A generated 257-case fixture selects, compares, hashes, matches, Wasm-encodes,
  and executes through real QBE without adding a 257-line source fixture.
  Optional tags remain their independent specified two-case `u8` form.

  No target, layout, ABI, runtime service, backend branch, source example file,
  or Stage-0 workaround was added. The 5,331-line function lowerer grew only
  inside its existing aggregate/ownership transaction and now names optional
  versus ordinary enum tag operations explicitly. Its holistic split remains
  preferable to extracting a forwarding helper during the coverage audit.

- [x] **Restricted mutable slices are complete through QBE and Wasm**
  (2026-09-01). `list[T].with_mutable_slice` evaluates its receiver and
  callback once, detaches existing immutable snapshots, lends one synchronous
  `mutable_slice[T]`, and closes the identity-wide shape barrier afterward.
  Indexed reads/writes, ordinary aliases, snapshots made before and during the
  callback, bounds traps, and shape-mutation traps agree through both semantic
  oracles and real artifacts.

  The source type is admitted only as a direct function parameter. Exact
  diagnostics reject construction through storage, fields, enum payloads,
  containers, returns, hidden `defer` storage, implicit/explicit capture,
  ordinary generic erasure, and every current native boundary. Explicit
  `mutable_slice[T]` generic parameters retain structural inference. Canonical
  MIR preserves `MutableSlice(T)` and four semantic operations; a focused
  lifetime verifier proves one origin/end on every normal path and rejects
  storage, result escape, forgery, double/end-after-use, closing borrowed
  parameters, and element mismatch. QBE and Wasm alone supply layout while the
  freestanding runtime owns copy-on-write and shape state. The audit caught
  and closed both generic-erasure and hidden-`defer` escape routes before the
  slice was declared complete. The following worker slice consumes the same
  non-storable predicate and rejects mutable-slice transfer at its exact path.

- [x] **Frozen snapshots and structured tasks are complete through the native
  QBE oracle** (2026-09-01). HIR accepts only statically named Luce workers,
  recursively proves sendable arguments and results, gives every invocation
  one lexical task group, and rejects task escape through returns, persistent
  storage, closures, dynamic calls, foreign boundaries, and hidden generic
  substitutions. Frozen list/map/set snapshots expose immutable lookup,
  iteration, equality, and hashing without sharing mutable source identity.

  Canonical MIR retains `Task(T, Error)`, `TaskGroup`, typed `TransferRun`s,
  snapshot operations, and an explicit finish before every ordinary exit. It
  contains no scheduler, process, pipe, signal, serializer, pointer width, or
  target layout. The verifier closes task provenance, target signatures,
  sendability, transfer structure, group lifetime, and the uninhabited empty
  `list[never]` case. The MIR oracle copies through a pointer-free semantic
  tree; reachability retains only the runtime services required by each
  concrete transfer graph.

  QBE realizes each worker as an immediate POSIX `fork` snapshot and returns
  one framed, compiler-generated typed encoding through a pipe. Parent-side
  decoding always creates fresh buffers, slices, and frozen collections;
  repeated waits decode fresh copies from cached bytes. Real artifacts prove
  scalars including exact binary16, structs/arrays/enums/optionals, strings,
  bytes, slices, frozen list/map/set graphs, nested spawning, ordinary errors,
  source traps, idempotent cancellation, unobserved group cleanup, repeated
  handles, empty `wait_all`, and first-input failure ordering. Wasm encodes
  frozen snapshots but rejects tasks explicitly under WASI preview 1. The QBE
  emitter was reduced below 2,000 lines by sharing physical representation
  decisions with worker codecs; the architecture audit finds no platform fact
  before `backends/`.

- [x] **Fixed-representation C enums remain semantic enums until a C edge**
  (2026-09-02). `export c enum Name as Integer` now retains documentation,
  ordinary payload-free cases, construction, matching, equality, and compact
  positional storage through HIR and MIR. A separate exact case-to-integer map
  accepts every signed/unsigned width, rejects noninteger representations,
  suffix mismatches, range overflow and duplicate values, and survives typed
  package format 5 plus dependency identity remapping.

  The HIR oracle and canonical-MIR C adapters encode the fixed value on
  outbound extern/cfunc/export crossings, decode it on inbound crossings, and
  trap an integer that names no case. MIR gained no C-enum type or target
  layout: the ordinary aggregate enum and its semantic tag are unchanged, and
  only an explicit C slot is scalar. Focused malformed/behavior/verification
  tests, Wasm encoding, and real QBE calls through libc in both directions
  prove the slice. C globals intentionally remain closed until their distinct
  storage adapter exists; C-record fields now use the exported-struct adapter
  below. Generated headers and ABI reports were completed by the later parent
  C-boundary product milestone.

- [x] **Exported C structs are ordinary values with a backend-owned ABI**
  (2026-09-02). `export c struct` normalizes into the one HIR nominal-struct
  model with public immutable fields and a closed recursively owned boundary
  vocabulary: C scalars, fixed C enums, and other exported records. Ordinary
  construction, field access, copying, and function bodies therefore need no
  parallel implementation. Typed package format 5 preserves the explicit
  external-versus-exported role and validates malformed records on both encode
  and decode; dependency import remaps the same semantic type graph.

  Canonical MIR derives a declaration-order structural C record only at an
  explicit extern, cfunc, or export edge. Its fieldwise adapter translates
  nested records and enum values while retaining no target, byte size,
  alignment, offset, or platform ABI class. Aggregate signatures preserve
  that structural type while registers carry storage addresses. QBE alone
  emits aggregate ABI declarations and classifies by-value parameters/results,
  including types reachable only through indirect callback signatures. The
  HIR oracle, MIR verifier, package/import tests, and a real linked C harness
  prove nested records, signed fixed-enum values, floating fields, extern and
  exported arguments/results, and aggregate-bearing indirect C calls.
  `examples/c_api.luc` is the checked source half of that executable proof.

- [x] **Exported C products have one neutral model and one backend layout**
  (2026-09-02). Checked HIR now projects the root package's exact C surface
  into a compact `c_api` graph containing names, documentation, nullability,
  fixed integer values, and declaration-order fields—but no size, alignment,
  offset, target, or placement class. Exact names must be portable in the
  header's C and C++ inclusion modes, share one collision-free external
  namespace across Luce modules, and cannot expose dependency-owned native
  declarations through a guessed include.

  The header renderer emits standalone C11: opaque handle forwards,
  exact-width integer/enum typedefs, exact `Enum_case` macros, dependency-first
  record definitions, and C++ linkage guards. QBE ABI reporting reuses the
  emitter's backend-owned 64-bit layout rules and the shared `TypeLayout`, then
  structurally compares every reported signature with the optimized C wrapper
  QBE will actually receive. Its versioned JSON records the C compiler's exact
  target triple, size, alignment, field offsets, fixed values, nullability,
  symbol names, and calling convention.

  `luce build --target native --c-header PATH --abi-report PATH` installs each
  requested product through an owned temporary directory. The QBE toolchain
  now queries the linker target and selects QBE's target explicitly rather
  than relying on the QBE binary's build-time default. Golden graph/header/
  report tests, a strict real C11 compile, optimized-MIR agreement, CLI output,
  and existing native QBE execution cover the product path.

- [x] **Direct pointers to incomplete C records become nominal raw handles**
  (2026-09-03). The Clang importer recognizes exactly one direct pointer to a
  typedef-backed incomplete record. FIIR interns one layout-free
  `OpaqueHandle` identity and retains each boundary's nullability, pointee
  mutability, and source origin. Ownership and lifetime are deliberately absent
  from Clang-derived boundary facts and belong to the later recipe milestone.
  `_Nonnull` produces a bare handle, while `_Nullable`, `_Null_unspecified`,
  and unannotated pointers produce the ordinary tagged optional. Indirect
  result declarators, complete-record pointers, pointer typedefs, and multiple
  indirection still fail before HIR with focused diagnostics.

  Generated raw Luce contains one `pub extern type`; it contains no C pointer
  spelling, size, alignment, target, or ABI fact. The checked C adapter alone
  casts between its `void *` carrier and the exact typed C pointer. Pointee
  mutability remains an auditable raw-boundary fact rather than being promoted
  into a safe capability, and ownership/lifetime cannot be invented from C
  syntax.

  Pure schema/declarator tests cover qualifier order, malformed state,
  unsupported pointer shapes, nullable/bare generation, stable JSON, and
  target-independent raw source. The temperature example adds real open/find/
  read/echo functions and exercises absent and live handles through generated
  HIR, canonical MIR, Wasm/QBE encoding, the CLI bind/build/run path, and
  ordinary plus `-fshort-enums` linked QBE/C execution. No HIR type, MIR
  instruction, runtime operation, layout rule, or platform branch was added.
  The completed repository gate is 968/968 compiler tests across 36 files plus
  CLI, Wasm, and native QBE shell gates.

- [x] **FIIR recipes generate checked safe ownership without changing HIR or
  MIR** (2026-09-03). FIIR 2 removes ownership and lifetime from the
  Clang-derived boundary value and stores a reviewed binding recipe as a
  separate durable section with exact source origins. Its deliberately closed
  TOML subset classifies opaque parameters as borrowed for one call, opaque
  results as owned through one validated disposer or borrowed from one
  same-type input owner, and C-integer results as status values with a stable
  package error. Unknown properties, duplicate entries, missing opaque facts,
  nonexistent functions/parameters/disposers, incompatible handle types,
  nullable lifetime anchors, invalid disposer shapes, out-of-range success
  values, and duplicate recipe error codes all fail before source generation.

  `luce bind --recipe PATH --safe PATH` treats the reviewed input and safe
  output as one explicit pair while preserving raw-only generation. All four
  candidates are rendered before installation and the serialized FIIR remains
  the completion marker. Generated safe source uses ordinary Luce classes,
  optionals, and failure: an owner clears its raw handle before its idempotent
  disposer call, automatic `deinit` closes it, a borrow retains the owner and
  checks every call after explicit close, a returned borrow retains the same
  owner, and a non-success integer becomes the recipe's `ErrorCode` and
  message. No target, pointer layout, C type spelling, ABI rule, new HIR node,
  MIR instruction, runtime service, or backend branch was added.

  Deterministic recipe/schema/generator tests use an in-memory FIIR fixture;
  the real temperature header supplies allocated nullable/non-null handles,
  disposal, returned borrows, optional inputs, and status success/failure. The
  generated safe module runs through the HIR and MIR oracles, encodes through
  Wasm, and compiles/links/runs with the real C implementation through QBE.
  CLI tests generate and inspect all four products and execute both the raw and
  safe examples. The completed repository gate is 972/972 compiler tests
  across 37 files plus CLI, Wasm, and native QBE shell gates.

- [x] **Compile-time indexes, linear QBE emission, and named native traps**
  (2026-09-03). A whole-compiler audit found the design sound and the
  implementation naive in one consistent way: every lookup was a linear scan
  and the QBE IL was one growing string. Type interning is now a hash of a
  structural key in HIR, lowering, and package import; `contains_type_parameter`
  and the five structural type walkers are memoized (the walkers under a
  generation that every republished nominal bumps); HIR name, method, function,
  constant, local, helper, and shared-cell lookups are indexed; the verifier
  keeps an undo log instead of copying the defined-register set per region,
  and the capability verifiers run only for functions that hold a capability.
  The QBE emitter collects IL fragments and joins once. Measured: emitting 800
  synthetic functions fell from 33.5 s to 0.45 s, a 200-struct type-heavy
  check from 150 s to 1.3 s, and the differential file from 10 min 22 s to
  6 min 02 s after compiling the sealed runtime once per sweep.

  The lowerer gained one counted-loop helper (twelve hand-written traversal
  loops), one signature assembler (four copies), and one call-result placement
  helper (six copies); `ir.luc` gained `node_children`, the one place that
  knows every node form's operands, and the prologue, effects, initialization,
  and deinitializer walkers now match only the forms they treat specially.
  Native traps name their reason on stderr with the same text the MIR oracle
  reports, and the trapping sweep asserts that agreement. Three bugs were
  found and fixed with fixtures: `recover` of a managed value double-released
  it (native and Wasm printed garbage), `INT64_MIN * -1` did not trap natively
  on arm64, and a recursive frozen container used as a map key exhausted the
  compiler's call depth. The repository gate stays at 972/972 compiler tests
  across 37 files plus CLI, Wasm, and native QBE shell gates; `main` is now the
  former `stage1-qbe` line.
- [x] **One folder per language profile, one dispatch point per stage (B0)**
  (2026-09-03). `profile.luc` names the two profiles, the suffix that selects
  each, the three reserved words only full Luce spells, and type admission
  over the existing structural keys. Everything only full Luce executes moved
  out of the six shared stage files into `profiles/full/{hir,mir,backends}/`
  as classes over the shared state: the HIR checks for closures, collections,
  classes, and workers (`hir/checker.luc`, with `closure_context.luc` and
  `sendability.luc` beside it); their lowering (`mir/lowering.luc`, 1.8k
  lines out of `function_lowerer`); reference execution and the run state it
  owns (`backends/hir_execution.luc`); the MIR oracle's handle tables and
  runtime instructions (`mir_execution.luc`); QBE legalization, worker
  codecs, and the process entry (`qbe_emission.luc`, `qbe_tasks.luc`,
  `qbe_task_support.luc`); and Wasm encoding plus the module plan's runtime
  queries (`wasm_emission.luc`, `wasm_planning.luc`). Each shared stage keeps
  one `full` field and asks it at the arms it no longer owns; the profile
  answers through a host interface declared beside the shared state
  (`HirSemanticChecker` grew five services; `FunctionLoweringHost`,
  `HirExecutionHost`, `MirExecutionHost`, and `QbeEmissionHost` are new),
  so no import cycle exists and stage 1 can still reject module cycles.
  Vocabulary both sides need moved to shared model files rather than being
  duplicated: `hir_values.luc` (the value operations of the HIR oracle),
  `hir_execution_model.luc`, `mir_execution_model.luc` (now the home of
  `MirValue`), `qbe_emission_model.luc`, and `wasm_encoding.luc` (the byte
  vocabulary and shared emitters). `test.sh` enforces both folder rules and
  extends the target-neutrality grep to `profiles/*/hir` and `profiles/*/mir`;
  `tests/common/profiles/` mirrors the layout with the closure, class,
  worker, collection, slice, and hash sections of the generator, lowerer, and
  interpreter tests, which now share fixtures through `*_support.luc`
  modules. No behavior changed: the QBE IL of all 34 compilable examples is
  byte-identical to the pre-split tree, and the full gate is green at
  976 compiler tests across 47 files. `body_checker` is 3.0k lines and
  `function_lowerer` 3.7k, down from 3.8k and 5.3k. One Stage-0 observation
  was recorded in `stage0-0.30.md`: a test module named exactly after the
  source module it tests (`compiler.profile_test`) fails three assertions
  under 0.30, so the profile test is `language_profile_test.luc`.

- [x] **The Base module kind: `.lucb` selects the profile, `.lucn` is the
  audited tier (B1, first slice)** (2026-09-03). `ModuleAuthority` gained
  `base`; the suffix table is `.luc`, `.lucn`, `.lucb`, derived in one place
  (`source_modules.authority_for_path`) and encoded in typed packages. The
  runtime allocator and the native interop example carry the `.lucn` name.
  A Base module imports only Base modules (base.md §16.2), and every
  runtime-backed spelling it could make is refused at its dispatch point with
  a diagnostic naming the construct and the tier: `class` declarations, the
  collection type names and literals, `list`/`map`/`set`/`Weak`/`wait_all`
  heads, `new`, `spawn`, block closures, and lambdas that capture; the shared
  scalar, struct, enum, and capture-free lambda subset checks unchanged in
  both profiles. After lowering, a package whose modules are all `.lucb` is
  checked freestanding: no function may hold a value whose canonical type
  only full Luce admits (`mir/freestanding.luc`, answered by `profile.luc`
  over `mir_type_key`). `examples/base/hello.lucb` checks, runs through the
  HIR oracle, and builds a freestanding Wasm library through the pipeline.
  Gate: 986 compiler tests across 49 files.

- [x] **One lexer, two spellings: the Base tokens and reserved words (B1,
  second slice)** (2026-09-03). `profile.luc` lists the Base-only operator
  and marker spellings longest first (`+%=`, `-%=`, `*%=`, `+|=`, `-|=`,
  `*|=`, `---`, `...`, `+%`, `-%`, `*%`, `+|`, `-|`, `*|`, `+?`, `-?`, `*?`,
  `@`) and the eleven Base-only reserved words. The tokenizer takes the
  module's profile from the package reader: in a `.lucb` module those
  spellings are one token each and the words are keywords; in a `.luc` module
  a Base spelling is a diagnostic naming Luce Base and the words stay
  ordinary names, so `with`, `free`, and `union` remain valid identifiers in
  full Luce. The full-only words `class`, `spawn`, and `weak` stay keywords in
  both profiles and are refused by HIR in Base. The grammar for the new
  tokens arrives with the slices that give them meaning; until then a Base
  module that spells one gets a parse diagnostic, pinned by a fixture.
  Gate: 993 compiler tests across 50 files.
- [x] **Pointer-width integers and layout questions without a width in the IR
  (B1, third slice)** (2026-09-03). `usize` and `isize` resolve only in a
  `.lucb` module (a `.luc` module naming them is told they belong to Luce
  Base) as the HIR form `PointerInteger` and the canonical MIR type
  `PointerInt`, which carries no width: `bits_of` and the bound helpers
  answer 0, and `TypeLayout` supplies the target width (`integer_bits`,
  `int_minimum`, `int_maximum`, `uint_maximum`) so the MIR interpreter
  checks arithmetic at its layout's pointer width, QBE emits `l`, and Wasm
  emits `i32`. The HIR model treats the type as 64 bits wide for literal
  typing; a constant that fits only the wider target is refused by the
  backend that knows the width (the oracle under 4-byte rules and wasm32,
  each naming the constant and the width). The verifier skips the range
  check for the widthless register and refuses any `Convert` touching it,
  and the lowerer refuses numeric conversions and hashing of the type with a
  diagnostic, until the Base cast family fixes their rules. Layout is
  pointer size and alignment; the C boundary maps the type to
  `size_t`/`ptrdiff_t` and the header now includes `<stddef.h>`.
  `sizeof(T)`, `sizeof(value)`, `alignof(T)`, and `offsetof(T, field)` are
  core names in a `.lucb` module (ordinary names in full Luce) that check as
  `usize` and become the HIR node `LayoutConstant` and the canonical MIR
  instruction of the same name, both carrying the question (`LayoutQuery` in
  `layout_query.luc`, the one shared vocabulary) and the type, never a byte
  count. `TypeLayout.answer` folds it in each backend from its own rules, so
  `sizeof(usize)` is 4 in the MIR oracle's 4-byte rules and on wasm32 and 8
  under QBE. The reference interpreter is a backend for these questions
  (design §23.3): it lowers the type with the lowerer's own type mapping and
  answers under its layout rules, host pointers by default, so `luce run`
  matches the native build; a test may pass narrower rules. The checker
  names a missing field, a non-struct `offsetof`, a value handed to
  `alignof`, and the arity of each question; the verifier requires a
  storable subject, a struct subject with an in-range field for `offset`,
  and a `usize` result. Folding `usize` expressions into array lengths and
  module-level `assert`s (base.md §5.1) waits for the Base constant
  evaluator. `examples/base/pointer_width.lucb` asks all three questions and
  answers 42 at either pointer width through check, run, and a Wasm build.
  Gate: 1009 compiler tests across 51 files.
- [x] **C's division and implicit widening (B1, fourth slice)** (2026-09-03).
  In a `.lucb` module `//` and `%` are the HIR operations `TruncDivide` and
  `TruncRemainder` and the canonical `trunc_div`/`trunc_rem`: the quotient
  truncates toward zero and the remainder carries the dividend's sign, as in
  C (base.md §7.2), while a `.luc` module keeps floor division; the same
  source answers `-312` in Base and `-393` in full Luce through both
  oracles. Division by zero and `minimum // -1` trap as before and
  `minimum % -1` is 0. QBE emits its truncating `div`/`rem` without the
  floor adjustment; Wasm uses `div_s`/`rem_s` directly. An integer widens
  implicitly to a wider integer of one signedness in Base (base.md §7.5):
  the checker inserts the conversion at every context (`require_type`) and
  between binary operands, widening the narrower side. Widening to or from
  the pointer width lowers to the new canonical `widen` conversion, which is
  value-preserving on every target because a pointer-width integer is 32 to
  64 bits wide: fixed widths up to 32 widen into it and it widens into 64.
  The verifier admits `widen` only for such pairs; QBE extends or copies at
  64 bits, Wasm at 32, and the oracle keeps the value. Narrowing, a change
  of signedness, and `u64` into `usize` stay spelled and are refused by
  name. `examples/base/c_arithmetic.lucb` checks, runs, and builds.
  Gate: 1016 compiler tests across 52 files.
- [x] **The overflow operator family (B1, fifth slice)** (2026-09-03). `+%`,
  `-%`, `*%`, and unary `-%` wrap in two's complement, `+|`, `-|`, `*|`
  saturate at the type's bounds, and `+?`, `-?`, `*?` answer `T?` with
  `none` on overflow (base.md §7.2); the augmented `+%=`-family assigns. The
  parser places them at their checked spelling's precedence, the checker
  requires integer operands, and HIR carries one operation per spelling
  (`WrapAdd` … `CheckedMultiply`, `WrapNegate`). Canonical MIR gains
  `add_wrap`/`sub_wrap`/`mul_wrap`, `add_sat`/`sub_sat`/`mul_sat`, the
  overflow tests `add_overflows`/`sub_overflows`/`mul_overflows` that answer
  `bool`, and `neg_wrap`; a checked form lowers to the overflow test, the
  wrapped value, and an `If` that stores the optional's tag. Both oracles
  compute wrapping through `backends/wrapping.luc`, which forms every result
  modulo 2^64 without a host overflow Stage-0 would trap on. QBE's checked
  arithmetic now computes its overflow condition into one flag and traps on
  it, so saturation selects a bound with the same flag (`maximum + sign`
  wraps to the minimum) and the overflow test copies it; Wasm leaves the
  flag on the stack for a `select`, dividing for the multiply test only when
  the divisor is neither zero nor `-1`. `examples/base/c_arithmetic.lucb`
  spells all three behaviours, and the shared Base fixtures
  (`tests/base/fixtures.luc`: C division, widening,
  wrapping, saturating, checked, layout) answer one number each through the
  reference interpreter, the MIR oracle at both pointer widths, both
  encoders, and a native QBE build linked to a C driver.
  Gate: 1023 compiler tests across 53 files.
- [x] **C's cast between numbers (B1, sixth slice)** (2026-09-03). `(T)x`
  parses when the parenthesised text is a scalar type name followed by an
  operand, so `(value)` stays a group and `(Point)(x)` a call (base.md §7.5);
  a `.luc` module is told the cast belongs to Luce Base. Between integers the
  cast keeps the destination's low bits, from a float it truncates toward
  zero and saturates with NaN as 0, and into a float it rounds as IEEE does;
  nothing traps. HIR carries `Cast`, and canonical MIR two conversions the
  backend legalizes at its own widths, `cast_int` (wrap, copy, or extend by
  the source's signedness, so `(u32)size` is a copy on wasm32 and a wrap on
  QBE) and `float_to_int_saturating` (Wasm's `trunc_sat` family plus a
  narrow clamp; QBE compares against the bounds first). Pointer, enum, and
  text casts arrive with their types (B2, B3). The shared fixtures gain a
  cast fixture and `examples/base/c_arithmetic.lucb` casts twice.
  Gate: 1025 compiler tests across 53 files.
- [x] **Pointers: `T*`, `&`, `*`, and `.` through them (B2, first slice)**
  (2026-09-03). A `.lucb` module names `T*`, `const T*`, and `volatile T*`
  (the qualifier prefixes the pointee and attaches to the `*` that follows;
  `*?` is a nullable pointer in the type grammar, whose niche representation
  is the next slice), takes `&place` with the qualifier of the path's root
  (a `var` binding or a `T*` pointee gives `T*`, anything else `const T*`),
  loads with `*p`, stores with `*p = v` and `p.field = v` through a `T*`
  only, reads `p.field` without `->`, converts `T*` to `const T*`
  implicitly, and compares addresses with `==`/`!=` across qualifiers
  (base.md §5.3, §6.6, §7.7). HIR carries `Pointer` types and the nodes
  `AddressOf` (a local, global, or pointee root plus `PlaceAssignment`
  steps), `Deref`, `PointerStore`, and `QualifyPointer`; the lowerer maps a
  pointer to the canonical `Ptr`, an address to the local's frame slot or
  the field and element addresses of its path, and a store to the existing
  place-store path with the pointee as root. The reference interpreter
  models a pointer as a place in a call frame (`Value.Address`: frame,
  root, path) over a frame stack it now keeps, so a callee can read and
  write a caller's local through the pointer it was handed. A `.luc` module
  is told pointers belong to Luce Base. The shared fixtures gain a pointer
  fixture and `examples/base/pointers.lucb` checks, runs, and builds. Open
  in B2: the `T*?` niche, `void*`, pointer arithmetic and ordering, arrays
  and spans, `str` views, and the escape rule.
  Gate: 1029 compiler tests across 53 files.
- [x] **The nullable pointer niche (B2, second slice)** (2026-09-03). `T*?`
  is an ordinary optional in HIR and one word in canonical MIR: the new
  `NullablePtr` type (`ptr?`), pointer-sized, whose zero is `none`, never an
  address operand, with `ptr_to_nullable` and `nullable_to_ptr` conversions
  the verifier types and every backend copies (base.md §5.3, §19.2). The
  lowerer keeps one path per optional operation, asking `optional_present`
  and `optional_payload` which representation the type has, so `none`,
  `Some`, `else`, `if let`, `match`, iteration, equality, and hashing all
  serve both; a struct holding a `Node*?` has its C layout. The reference
  interpreter is unchanged: `Absent`/`Present` over the frame-place
  pointer. The shared fixtures gain a linked-list fixture walked through
  `Node*?`.
  Gate: 1031 compiler tests across 53 files.
- [x] **Pointer arithmetic, ordering, `void*`, and address casts (B2, third
  slice)** (2026-09-04). `p + n` and `p - n` are element-scaled and
  unchecked (`PointerOffset`, lowered to the unchecked `ElementAddress`
  with a signed count), `p[i]` is `*(p + i)` for reads and stores, `p - q`
  is the element difference as `isize` (the new canonical
  `PointerDifference`, which each backend divides by the element size from
  its layout), and `<`/`<=`/`>`/`>=` order addresses totally, across
  objects (the verifier admits ordered comparison of `ptr`, QBE compares
  unsigned, Wasm already did). `void*` is the pointer to `unit`, spelled
  `void*`, that any object pointer converts to implicitly and that cannot be
  dereferenced, indexed, or offset. The cast rows for pointers land:
  `(U*)p` between any pointers, `(usize)p` (`ptr_to_int`), and `(T*?)n`
  from `usize` (`int_to_ptr`, into the niche). The reference interpreter
  moves a place along the array it indexes and refuses arithmetic that
  leaves one, orders places lexicographically, and names the two casts it
  cannot answer because its addresses are places, not numbers (base.md
  §19.3); the MIR oracle and both backends answer them. The shared
  fixtures gain an arithmetic fixture and `examples/base/pointers.lucb`
  walks an array.
  Gate: 1034 compiler tests across 53 files.
- [x] **Arrays as `T[N]`, spans as `T[]`, and the escape rule (B2, fourth
  slice)** (2026-09-04).
  After a complete type, `[N]` is the fixed array (the existing `array[T, N]`
  form, now spelled C's way) and `[]` a span, `const T[]` a read-only one; a
  bracket that starts with a type stays a generic argument list (base.md
  §5.4). A span is two words, the element pointer and a `usize` length, as
  the HIR type `Span` and a canonical struct of `ptr` and `usize`. An array
  in a place converts to a span implicitly (its first element's address and
  its length), a span to a read-only span, `s[i]` is a checked element
  address (`SpanElementAddress`, read through `Deref` or stored through the
  pointer path), `s[a..<b]` and `s[a..=b]` are checked sub-spans
  (`SpanSlice`: `start <= end <= length` or a trap), `s.length` and
  `s.data` read the two words, `T[](pointer, count)` builds one from its
  parts, and `for x in items` iterates an array or a span by value in a
  Base module while `for x in &items` yields a pointer to each element,
  `T*` through a `var` array or a mutable span and `const T*` otherwise
  (base.md §8.3), one index loop in the lowerer for all of them. The
  reference interpreter holds a span as its first element's place and a
  length, so a store through a span reaches the array it views. The shared
  fixtures gain a span fixture and `examples/base/spans.lucb` checks, runs,
  and builds. The parser now takes the module's profile, so `T[N]`, `T[]`,
  `(T)x`, and `T[](p, n)` are Base grammar that a `.luc` module never
  reads (base.md §3.2). The escape rule lands in the same slice: `hir/escape.luc`
  reads each finished Base function once: a value that is, or contains, the
  address of a local (`&x`, a span over a local array, a struct holding one,
  and every `let` alias of those within the function) may be passed to a
  call but is refused when returned, passed as the message of `error(...)`,
  stored in a global, or stored through a pointer parameter (base.md §6.6).
  The pass runs in the semantic analyzer for `.lucb` modules only, names
  the function and the use, and follows aliases but stops at calls, as the
  rule promises.
  Gate: 1041 compiler tests across 54 files.
- [x] **`str` as a view in Base (B2, fifth slice)** (2026-09-04). A `.lucb`
  module's `str` is the HIR type `StringView`, distinct from full Luce's
  owned string: a `const u8*` and a `usize` byte count, the same two words
  as `const u8[]` in canonical MIR, that owns nothing and never reaches the
  runtime (base.md §5.5). A literal is a view of program data, `text.length`
  is the byte count, `text.bytes` the same words as a read-only byte span,
  `(str)bytes` reads a byte span as text with no check, and `==`, `!=`, and
  the orderings compare bytes through the loops the owned string already
  uses, now shared by `text_data`/`text_length` over either shape. Integer
  indexing and `+` are refused by name. The reference interpreter holds a
  view as a span over a per-literal program-data place (frame -1) and
  compares views by reading their bytes. `for character in text` decodes
  UTF-8 inline in the lowerer, one scalar per pass from the lead byte's
  width and six bits per continuation byte, so it needs no runtime service;
  the reference interpreter reads the view's bytes as text. `cstr` and
  `str(bytes)` wait for the `c` module and the standard library (B4, B5).
  Gate: 1042 compiler tests across 54 files.
- [x] **Zero values and `---` (B3, first slice)** (2026-09-04). In a `.lucb`
  module a `var` with a written type and no initialiser holds that type's
  zero (base.md §6.1): the parser reads the missing initialiser as the
  expression `ZeroValue` and `= ---` as `Uninitialized`, the checker admits
  the zero only for a zeroable type and names the first component that has
  none (a bare pointer, a function, an interface view, or an aggregate
  holding one), and refuses both spellings on a `let`. The lowerer emits
  the new canonical `Zero(address, type)` for the zero and nothing for
  `---`; QBE writes zero words then the tail, Wasm uses `memory.fill`, and
  the MIR oracle clears the bytes. The reference interpreter's zero value
  gains structs, spans, and text (an empty view of a dangling place).
  Gate: 1044 compiler tests across 54 files.
- [x] **Integer-backed enums (B3, second slice)** (2026-09-04). In a `.lucb`
  module `enum Access as u32:` with `case = value` lines declares an enum
  that is its representation (base.md §10.3): the parser reuses the
  `export c enum` body, the declaration carries `is_integer_backed` beside
  the value table, and the C export surfaces skip it until B4 settles its
  header form (§17.6). `|`, `&`, `^`, and `~` produce the enum and run on
  the representation, `(u32)e` and `(Access)n` are casts, `Access(n)` is
  the checked conversion (`EnumFromInteger`, a flat compare chain ending in
  a trap), and `match` requires `_`. MIR lowers the type to its integer, a
  case to its constant, and a case pattern to an equality; both oracles hold
  the integer, so hashing, equality, and the zero value follow the scalar
  paths.
  Gate: 1049 compiler tests across 54 files.
- [x] **Unions (B3, third slice)** (2026-09-04). In a `.lucb` module
  `union Name:` declares a record whose `name: type` members overlap at one
  address (base.md §10.4): the parser reuses the struct body with the bare
  member spelling, `HirStruct` carries `HirRecordLayout` (sequential or
  overlapping), and canonical MIR gains `Union(members)`, laid out as the
  largest member rounded to the strictest alignment with every member at
  offset zero. Construction writes exactly one member, the type has no
  equality, hash, or interfaces, and it is zeroed as bytes. The MIR oracle
  now stores floats as their IEEE bytes instead of a side table, so writing
  a float member and reading its integer or byte members sees the bits C
  sees; the reference interpreter keeps every member of a union value
  consistent with one little-endian byte image after each write, including
  writes through pointers and into nested array elements, and refuses to
  read a member after one with no byte image (a pointer, a span) was written.
  Gate: 1052 compiler tests across 54 files.
- [x] **Module globals (B3, fourth slice)** (2026-09-04). A `.lucb` module
  declares `var name: T`, `var name: T = constant`, and `thread_local var`
  at top level (base.md §6.3): the global is zero before `main` or holds
  the constant its initialiser names, so there is nothing to order. The
  checker admits the §6.4 constant vocabulary (layout questions, casts,
  enum cases, struct and array construction, the address of a global) and
  refuses a type with no zero value unless it is initialised. The lowerer's
  new `ConstantFolder` folds the initialiser with the reference
  interpreter's value arithmetic into `MirInitializer`, a target-neutral
  value tree that replaces the byte-image `DataId` initial of `MirGlobal`;
  QBE, Wasm, and the MIR oracle lay it out under their own rules, QBE
  spells `thread_local` as `thread data`, and the optimizer and composer
  follow its address leaves. A `sizeof`/`alignof`/`offsetof` initialiser
  is a `Layout` leaf the backend answers, so MIR never learns a width; a
  layout answer inside an expression is refused with a diagnostic. The
  slice also moved the language's value arithmetic out of the backends
  into `hir/evaluation.luc` (the folder and the reference interpreter share
  it) and `wrapping.luc` beside it, which the gate's boundary rule
  demanded. Also records a Stage-0 0.30 retain leak (an indexed read of a
  struct holding an optional list-carrying union) in `stage0-0.30.md`.
  Gate: 1062 compiler tests across 54 files.
- [x] **Labels, match guards, and `errdefer` (B3, fifth slice)**
  (2026-09-04). In a `.lucb` module a label `rows:` before `while` or
  `for` lets `break rows`/`continue rows` leave nested loops (base.md
  §8.5): the checker resolves the label to a loop count that
  `BreakStatement`/`ContinueStatement` now carry, the lowerer walks that
  many loop regions and runs the deferred actions of every scope left, and
  the reference interpreter's `Broke`/`Continued` transfers count down.
  A match arm may carry `pattern if condition:` (§8.4): the guard is checked
  and lowered after the pattern binds, and a guarded arm sees a copy of the
  coverage so it never counts toward exhaustiveness. `errdefer call` (§8.8)
  is checked (Base only, fallible functions only), lowered as an
  `ErrorSource` deferred action that only the error exit runs, and modelled
  in the reference interpreter.
  Gate: 1062 compiler tests across 54 files.
- [x] **The Base failure model (B3, sixth slice)** (2026-09-04). In a
  `.lucb` module `Error` is `{ code: ErrorCode, message: str }` with the
  text a view (base.md §11.3), and `ErrorCode`'s package identity is a view
  too: the checker types `error(code, message)` and `failure.message` with
  the view, and the lowerer, told the module's profile by `enter_module`,
  lays both records out with `{ptr, usize}` texts, spells a package
  identity as program data, and compares codes field by field through the
  byte loop text views already use. Nothing else changes: the caller-owned
  error slot, `Raise`, `try`, `catch`, and `recover` lower as before, so a
  freestanding Base program raises and recovers without the runtime in both
  oracles, Wasm, and native QBE, and `errdefer` now has its end-to-end
  fixture. The reference interpreter reads a view message back as text when
  a failure escapes.
  Gate: 1067 compiler tests across 54 files.
- [x] **`packed` and `align(N)` (B3, seventh slice)** (2026-09-04). In a
  `.lucb` module `packed struct` removes padding, `align(N) struct` raises
  the record's alignment, and `align(N)` before a field raises that field's
  (base.md §5.11). The parser reads the contextual words, `HirStruct` and
  `HirField` carry them, and the lowerer folds them into `MirField`'s
  `alignment` (raise to at least) and `is_packed` (pin to one byte), which
  the shared `TypeLayout.field_align` honours for every backend and both
  oracles, so `sizeof`, `alignof`, `offsetof`, field addresses, and union
  byte images all agree. The checker refuses the address of a packed field
  whose alignment is not one, through any place that reaches it; a packed
  struct itself, and any field of one-byte scalars, stays addressable.
  Gate: 1067 compiler tests across 54 files.
- [x] **Interface views (B4, first slice)** (2026-09-04). In a `.lucb`
  module an interface used as a type is a two-word view, the conformer's
  address and its witness table's (base.md §14.3): the checker forms one
  from `T*`, or from `const T*` when no requirement mutates, and refuses a
  bare value; a view fixes its mutability when formed, so a `let` view may
  still call a `mutating` requirement. The lowerer lays the view out as
  `{ptr, ptr}`, materialises each conformance's witness table on first use
  as a global initialised with the addresses of the witness thunks the
  full profile already lowers (`MirInitializer.FunctionAddress`, so no new
  instruction), and dispatches with `ElementAddress`, a load, and a
  `CallIndirect` whose erased receiver is the conformer's address. The
  reference interpreter reads the conformer through the view's address and
  writes it back after a mutating call; the escape rule treats a view of a
  local like a pointer to it. `Writer?` on the data-word niche waits.
  Gate: 1071 compiler tests across 54 files.
- [x] **`volatile` accesses (B4, second slice)** (2026-09-04). A scalar
  load or store through `volatile T*` (base.md §15.2), whether of the
  pointee or of a field reached through it, lowers to the new canonical
  `VolatileLoad`/`VolatileStore`; a compound `+=` through such a pointer
  is a volatile load, the operation, and a volatile store. QBE legalizes
  both through the relaxed `__atomic_load_N`/`__atomic_store_N` calls of
  §19.3, since its load optimiser forwards stores and drops repeated
  loads, extending sub-word results with its `sb`/`ub`/`sh`/`uh` classes
  and carrying floats as their bits; the MIR oracle and Wasm perform the
  plain access, which is what a single thread with no cache observes. An
  array element indexed through a volatile pointer keeps the plain access
  for now, and an aggregate copies member by member as before.
  Gate: 1071 compiler tests across 54 files.
- [x] **Atomics (B4, third slice)** (2026-09-04). `@T` (base.md §5.9,
  §15.1) is a HIR type that stores as `T` and admits integers, `bool`,
  `usize`/`isize`, and pointers. The checker reads an atomic place as a
  sequentially consistent `AtomicLoad` wherever a value is wanted, turns
  `=` into `AtomicStore` and `+=`/`-=`/`|=`/`&=`/`^=` into wrapping
  `AtomicUpdate`s, and resolves the methods `load`, `store`, `add`, `sub`,
  `set`, `clear` (an `and` with the complement), `flip`, `swap`, and `cas`
  with their `.relaxed`…`.seq_cst` orders, `cas` answering `(bool, T)`.
  Canonical MIR gains the four atomic instructions with C11 orders; QBE
  bridges them through `__atomic_load_N`, `__atomic_store_N`,
  `__atomic_fetch_*_N`, `__atomic_exchange_N`, and
  `__atomic_compare_exchange_N` (base.md §19.3), while the MIR oracle,
  the reference interpreter, and Wasm perform the plain wrapping
  operations of a single thread. The lowerer also learned the address of
  a global at run time. `max`/`min`, `wait`/`wake`, and `atomic.fence`
  are diagnosed as not implemented yet; fences wait for `asm`.
  Gate: 1074 compiler tests across 54 files.
- [x] **Allocation (B3, last slice)** (2026-09-04). The standard `memory`
  module (`src/standard/memory.lucb`, base.md §12) is Base source the
  loader supplies beside the package: the `Allocator` interface, the
  `exhausted` code, the thread-local `allocator` view, and `FixedBuffer`.
  `new T(...)`, `new T`, `new T[n]`, `alloc T[n]`, and `alloc(size, align)`
  check to one HIR `Allocate` node whose request is the interface call
  `allocate(size, align)` on the chosen allocator, the current view or the
  one `in` names, with the count and raw size hoisted into a prelude so
  they are evaluated once; the lowerer branches on the answered optional,
  stores the constructed value or zeroes the elements, and yields the
  pointer or span, or an `Error` carrying `memory.exhausted` (§11.4) that
  `try`/`catch` handle like any other failure. `free(x)` is the `release`
  call on a `u8[]` view of the block; `with a:` is `WithAllocator`, which
  saves the thread-local, stores the view, and restores it through a
  `RestoreValue` deferred action on every exit. A `.lucb` module without
  the `memory` module in its package, a value that is not an allocator,
  a `new T` whose `T` has no zero value, and a `free` of a non-pointer
  are diagnosed. The reference interpreter keeps allocated cells in a
  heap that `Address` values reach through a heap frame; no new canonical
  instruction was needed. `PageAllocator`, `CAllocator`, `Arena`, and the
  §12.5 linter wait for the runtime port.
  Gate: 1077 compiler tests across 54 files.
- [x] **Declaration attributes (B4, fourth slice)** (2026-09-04). The
  closed word set of base.md §9.8 (`inline`, `noinline`, `cold`, `naked`,
  `weak`, `used`, `section("name")`) parses between `pub` and `func`,
  `var`, `thread_local var`, or `export c func` in a Base module, each
  word once, `inline` and `noinline` excluding each other and the
  function-only words refused before a global. One `SymbolAttributes`
  value (`compiler/symbol_attributes.luc`) rides on the syntax tree,
  `HirFunction`/`HirGlobal`, the package codec, and `MirFunction`/
  `MirGlobal`, where an exported function's C wrapper carries the words
  as well. `used` is a root for the optimizer's pruning; `section`
  becomes QBE `section` linkage on the data or function; `weak` and
  `used` become the assembler directives QBE cannot express, appended to
  its output by the toolchain as `.weak_definition`/`.no_dead_strip` for
  Mach-O and `.weak` for ELF. The inlining and coldness hints are carried
  and ignored, as the spec allows. `naked` is refused until `asm` lands,
  and `weak` on anything but an exported function until globals export.
  Gate: 1085 compiler tests across 57 files.
- [x] **Atomic `max`/`min` and volatile indexing (B4, fifth slice)**
  (2026-09-04). `max(v, order)` and `min(v, order)` on an atomic integer
  are two more `AtomicUpdate` operations, compared in the type's own
  signedness: the oracles and Wasm pick the extreme and store it, while
  QBE, which has no `__atomic_fetch_max`, emits a load and a
  compare-exchange loop that retries until the location still holds what
  it read. `wait`/`wake` now say they wait for the runtime's futex. An
  array element indexed through a `volatile` pointer, `regs.slots[i]`,
  reads and writes as a volatile access like the field it sits in.
  An optional interface view, `Writer?`, is now the view itself on the
  null-data niche (base.md §5.6): `none` is two zero words, presence is a
  null test on the data word, `x == none` needs no equality on the
  payload, an absent constant initialiser folds to zero storage, and the
  reference interpreter answers layout questions under Base's
  representations, so `sizeof` agrees with the backends. The thread-local
  `memory.allocator` is the first such optional.
  Gate: 1087 compiler tests across 58 files.
- [x] **Fences (B4, sixth slice)** (2026-09-04). The standard `atomic`
  module (`src/standard/atomic.lucb`, base.md §15.1, §16.6) declares
  `Ordering` and `fence`; a call `atomic.fence(.order)` on the imported
  module is checked to the HIR `AtomicFence` node and lowered to the
  canonical `Fence(order, is_signal)` instruction rather than a call, so
  `fence` is one vocabulary from source to backend. QBE calls
  `luce_atomic_thread_fence` or, for `.signal`, `luce_atomic_signal_fence`,
  two one-line C shims over the compiler builtins that the toolchain
  links whenever a program fences (§19.3), since the builtins have no
  linkable symbol; the oracles and Wasm, which run one thread, perform
  nothing.
  A non-case order, an unknown order, and a missing order are diagnosed.
  Gate: 1088 compiler tests across 58 files.
- [x] **Base exports, first slice (B4)** (2026-09-04). `export func` is
  the Base spelling (base.md §17.6); `export c func` stays full Luce's.
  The C-representable rule now admits Base pointers `T*` and `const T*`,
  nullable pointers `T*?`, integer-backed enums, and Base structs whose
  fields are representable, passed and returned by value. The C API
  model gains a `Pointer` type form, discovers the Base structs and
  integer-backed enums an export reaches, and publishes them under their
  own names; the header spells `T *`, `const T *`, `struct Name { ... }`,
  and `typedef uint32_t Access;` with `#define Access_read` values, the
  same form an exported C enum takes. The one boundary check (§17.1)
  guards a bare Base pointer in both directions, and the ABI report
  agrees on nullable words. A native test calls both exports from a C
  `main`. Methods as `Type_method`, spans in parameter position, function
  pointers, unions, and the fallible status form remain open.
  Gate: 1092 compiler tests across 58 files.
- [x] **Calling C from Base, first slice (B4)** (2026-09-04). Calling C
  belongs to Luce Base alone (decision in `plan.md` B4). `extern func` in
  a `.lucb` module now admits the Base boundary types an export admits:
  `T*`, `const T*`, `T*?`, integer-backed enums, and Base structs by
  value, with the one null check on a bare pointer in both directions
  (base.md §17.1). `cstr` resolves to `const u8*` until the distinct
  `c.char` lands; `(cstr)text` is the view's data word, a text literal
  where `cstr` is wanted is that cast, and every text literal's data now
  carries a NUL after its length so the literal is C text (§17.2). The
  reference interpreter reports that a `cstr` has no value there. A
  native test calls `abs` and `strlen` from Base under QBE. The `c` types
  module, `as "symbol"`, `extern union`, and variadic calls remain open.
  Gate: 1096 compiler tests across 58 files.
- [x] **Variadic C calls, `as "symbol"`, and the `c` types module (B4)**
  (2026-09-04). `extern func printf(format: cstr, ...)` declares a
  variadic function (base.md §17.2); a call to it is the HIR
  `CVariadicCall` node, whose declared arguments are placed as for any
  call and whose extras are promoted by the checker as C promotes them:
  an untyped integer literal is `int`, an untyped float literal `double`,
  a string literal `cstr`, `char` and the narrow integers `int`, `f32`
  `double`, an integer-backed enum its representation, and every other
  integer, float, or pointer itself; `str`, spans, structs, and optionals
  are refused, and a `bool` asks for `(i32)` for now. The canonical
  signature carries `is_variadic`, the verifier admits the extras, QBE
  writes the `...` marker, and Wasm says it has no variadic calls.
  `extern func absolute as "abs"(...)` binds a C symbol under a Base name.
  The standard `c` module (`src/standard/c.lucb`, §5.2) holds the alias
  types; the distinct `char`, `long`, and `wchar`, `va_list`, and the
  `errno`/`stdio` accessors wait. A native test calls `snprintf`, `atoi`,
  and `abs` from Base.
  Gate: 1096 compiler tests across 58 files.
- [x] **The Base entry point (B4)** (2026-09-04). `pub func
  main(arguments: str[])` or `cstr[]`, returning `i32` or `i32!`, is the
  Base process entry (base.md §9.7). The canonical process entry now
  records its element type, and Base's own startup shim
  (`profiles/base/backends/base_qbe_emission.luc`) is emitted through
  the QBE host: `main(argc, argv)` builds the span over one stack array,
  a text view per argument with its `strlen`, or a `cstr`, calls the
  entry, and turns an unhandled failure into exit status 1. The entry
  contract of each profile lives in its own module
  (`profiles/{base,full}/hir/*entry.luc`), selected once by the shared
  entry pass, and the reference interpreter builds a Base `main`'s span
  in `profiles/base/backends/base_execution.luc` over a heap cell the
  host allocates; Wasm reports that a Base entry waits.
  `examples/base/main.lucb` is the first Base program that builds and
  runs natively on its own, printing through `printf`. This slice is the
  first written under the no-dialect-branches rule (`plan.md` §5.0).
  Gate: 1099 compiler tests across 58 files.
- [x] **The Base profile split** (2026-09-04). Every `in_base_module()`
  and `Profile.base` branch that B1–B4 had left in the shared parser,
  tokenizer, checker, declaration collector, interfaces, lowering model,
  function lowerer, analyzer, C exports, and C API is gone. `profile.luc`
  now holds the admission tables: `GrammarFeature`/`admits_grammar` for
  the one parser's profile-only spellings (plan.md §6's one-grammar
  gate), `Construct`/`admits_construct`/`construct_diagnostic` for the
  constructs only one tier has, with every "belongs to" diagnostic in
  one place, and `admits_import`. Behaviour that differs by profile is a
  class in the profile's folder behind a shared interface:
  `ProfileChecks` (`profiles/{base,full}/hir/*_checks.luc`: text
  literals, slices, pointer arithmetic and widening, integer division,
  layout builtins, `Error` text, implicit conversions, interface values
  and receivers), `ProfileDeclarations` (globals and the profile's own
  type names), `ProfileRepresentation` and `ProfileLowering`
  (`profiles/{base,full}/mir`: interface and optional layout, `Error`
  text, and Base's view lowering), with the escape pass now
  `profiles/base/hir/base_escape.luc`. Each shared stage selects the
  profile once, by module authority, at its dispatch point (`analyzer`,
  `body_checker`, `declarations`, `entry_points`, `function_lowerer`,
  the interpreters, the backends). `test.sh` rule 1c refuses the old
  spellings in the shared folders.
  Gate: 1099 compiler tests across 58 files.
- [x] **Tests and examples in three folders** (2026-09-04). `tests/` and
  `examples/` now split the way the compiler does (plan.md §5.0):
  `common` for what both dialects share, `base` for Luce Base, and `full`,
  the working name, for the rest of the language. `tests/base` and
  `tests/full` came out of `tests/compiler/profiles`, the remaining
  compiler tests moved under `tests/common` with their helper imports
  renamed, and every full-Luce example moved under `examples/full`, with
  the package roots, module names, shell scripts, `FEATURES.md` rows, and
  READMEs following. `examples/common` waits for the first program that
  runs unchanged as `.luc` and `.lucb`. `tests/common` still holds many
  tests of full-Luce features; sorting those into `tests/full` is a
  follow-up, not a blocker.
  Gate: 1101 compiler tests across 58 files.
- [x] **Exported methods (B4)** (2026-09-04). `export func` and `export
  mutating func` on a Base struct method give it C linkage as
  `Type_method` with `self` first, a `const Type *` for a plain method
  and a `Type *` for a mutating one (base.md §9.5, §17.6). The C API model
  and header, the export namespace check, and the C wrapper share one
  `exported_c_name`; the wrapper takes `self` as the pointer the body
  already expects and applies the one null check. A type function has no
  `self` and is refused with a pointer to the module-level form.
  Gate: 1101 compiler tests across 58 files.
- [x] **Spans, function pointers, and the status form at the C boundary
  (B4)** (2026-09-04). A span in parameter position crosses an export or
  an `extern` call as `T *name, size_t name_count`; the wrapper builds
  the span, reads `(NULL, 0)` as the empty span, and traps `null_foreign`
  on a null pointer with a count (base.md §17.6). A Base `func` type is a
  C function pointer in both directions, rendered as a C declarator in
  the header. A fallible export takes the status form: the C function
  returns `int`, 0 on success and 1 on failure, and writes the value
  through a final `out` pointer; full Luce still refuses fallible
  exports. The ABI report lowers the new type forms and matches the
  wrapper's expanded parameter list. A native test calls all three from
  a C `main`.
  `extern union Name:` declares C layout whose members overlap at one
  address (base.md §17.1), the same overlapping record a Base `union`
  is, under the external C kind. A Base `func(A) -> R` type now resolves
  to the C function pointer type (base.md §5.7) through
  `ProfileDeclarations`, so it is one pointer word, calls through the C
  convention, and crosses exports and `extern` calls as a function
  pointer; full Luce keeps its two-word function value and its closed C
  surface. Base diagnostics still spell that type `cfunc`, a wording to
  revisit. A `bool` in a variadic position is promoted to `int` as 1 or
  0 (§17.2).
  Gate: 1104 compiler tests across 58 files.
- [x] **Standard modules found on their own (B6, first step)**
  (2026-09-04). A command line with a `.lucb` source and no
  `--standard-root` loads every `.lucb` module of the standard root,
  `LUCE_STANDARD_ROOT` or a checkout's `src/standard`, so
  `luce build --target native out examples/base/main.lucb` builds and
  runs a Base program with nothing else on the line (base.md §16.6).
  Full-Luce packages keep their explicit flags, and discovery from the
  installed toolchain's own location waits for the library port.
  `luce build --target native --lib out.o sources` produces a library,
  one relocatable object without needing `main`, beside `--c-header`'s
  header, so a C program links against a Base package (base.md §17.6,
  §19.6); a program that needs the fence or task shims is refused, since
  the object is one translation unit.
  Gate: 1106 compiler tests across 58 files.
- [x] **Formatted output in Base (B4)** (2026-09-04). `print(f"...")` in
  a Base module writes each piece to standard output as it goes and never
  forms a string (base.md §5.5, §14.4): the checker holds `io.stdout()`
  once and turns every text piece and field into one call on the standard
  `io` module's display functions, `write_text`, `write_signed`,
  `write_unsigned` (integers widened to 64 bits), `write_bool`,
  `write_char` (UTF-8), and `write_pointer` (`0x` hex), each under a
  `catch` that recovers `unit`, so a failed write is ignored as §14.4
  says. Those functions are Base code in `src/standard/io.lucb`, which
  also declares `Writer` and answers `stdout()`/`stderr()` as views of
  two globals; the only intrinsics are `Builtin.write_output` and
  `Builtin.write_error`, admitted in a Base module the standard loader
  supplied (provenance on `SourceModule`/`HirModule`, never spelling) and
  carried as the target-neutral HIR node `WriteBytes`, which lowers to
  the shim's `luce_rt_write`/`luce_rt_write_error` externs; QBE writes
  descriptors 1 and 2, Wasm `fd_write`, and both oracles append to their
  output. `u32(c)` is the checked conversion from `char` in both
  profiles. A formatted string anywhere else in Base, a field with no
  display, a float field (the shortest-round-trip printer is open), and
  a program without the `io` module are each refused with a diagnostic.
  Every Base fixture now also proves what it printed through the MIR
  oracle and natively. Known: a native Base build may end with
  `luce: N objects leaked` from the compiler's own process; the count
  depends on which declarations the standard modules carry, it predates
  this slice (a struct global with an initialiser that a function uses
  reproduces it at aa51dd2), `check` and the Wasm path do not show it, and
  the artifact is correct. Isolating it is open.
  Gate: 1113 compiler tests across 59 files.
- [x] **Formatted strings reach every sink (B4)** (2026-09-04).
  `writer.write(f"...")` on an `io.Writer` view and
  `format(buffer, f"...") -> str!` join `print` as the ways a Base module
  consumes a formatted string (base.md §5.5). Both become one HIR
  `FallibleSequence`: a prelude that binds the sink once, the display
  calls of the pieces as fallible steps, and a result, typed `T!`; the
  first failing step is the expression's failure, so `try` and `catch`
  see a full buffer or a failed write as they would any call. The lowerer
  turns it into nested `if`s on the error of each step with one `Yield`
  per path, and the HIR oracle runs the steps in order. `format` writes
  through `io.BufferWriter` over the caller's `u8[]`, fails with
  `io.full` when the text does not fit, appends a NUL when there is room,
  and answers a view of the text; a `write` receiver that is not the
  standard `Writer` keeps the ordinary call path and its diagnostic.
  Gate: 1117 compiler tests across 59 files.
- [x] **Distinct `c.char`, `c.long`, `c.ulong`, `c.wchar` (B4)**
  (2026-09-04). C's target-dependent integers (base.md §5.2) are their own
  HIR type family, `TypeForm.CInteger(kind)`, beside the pointer-width
  integers, and MIR `CInt(kind)`; only a backend fixes their width
  (`LayoutRules.long_size`: 8 under QBE, 4 on wasm32; `char` 1 and
  `wchar_t` 4 everywhere the compiler builds for, `char` signed). The
  standard `c` module aliases them (`pub type long = c_long`), the one
  place that may name the identities, so the spelling is `c.long`. A
  constant must fit on every supported target (`c.long` takes the 32-bit
  range, `c.char` 0..127, `c.wchar` 0..32767), implicit widening is
  admitted only where no target loses a value (`i8`..`i32` to `c.long`,
  `c.long` to `i64`, `c.char` to any signed type, `c.wchar` to 32 bits or
  more), and the MIR verifier's `widen` rule says the same for the
  canonical conversion. Exports and externs carry them as `char`, `long`,
  `unsigned long`, and `wchar_t` in the header, formatted output displays
  them through their 64-bit form, and `sizeof` answers the backend's
  width. `cstr` stays `const u8*` until the text rules move to `c.char`,
  and a checked conversion to or from a C integer (`c.long(x)`) still
  waits for the cast family's canonical form (B1d).
  Gate: 1122 compiler tests across 60 files.
- [x] **Two fixes from the Base slices** (2026-09-04). The
  `luce: N objects leaked` report at the end of a native Base build came
  from `qbe_symbol_directives`, which copied each `MirGlobal` into a local
  while looking at its attributes; a struct holding a recursive union
  (`MirInitializer`) leaks its copy under stage-0 0.30. The scan now reads
  the attribute in place, and a scratch driver over the compiler library
  proved every pipeline stage clean. `p.method(...)` through a Base
  pointer now dereferences to the pointee as `p.field` does (base.md
  §7.7): a mutating method needs `T*`, and `const T*` is refused naming
  the pointer type; a fixture proves the call in both oracles and natively.
  Gate: 1124 compiler tests across 61 files.
- [x] **`cstr` is `const c.char*`, and checked conversions reach every
  integer (B1d, B4)** (2026-09-04). `cstr` now names `const c.char*`
  (base.md §5.2, §17.1), so a C header spells it `const char *` and the
  literal, cast, and boundary rules test that pointee. A checked conversion
  to or from a target-width integer, `usize(n)`, `u32(size)`, `c.long(n)`,
  `i16(size)`, `c.char(n)`, has a canonical form: the operand widens to 64
  bits of its own signedness, the destination's inclusive bounds are
  computed from a `LayoutConstant` of its size (`~0 >> (64 - bits)`, and
  `65 - bits` with `-1 - max` below for a signed destination) or are the
  fixed width's constants, the compares trap with "integer conversion out
  of range", and `cast_int` narrows a value known to fit; every step is
  target-neutral MIR that the verifier's width rules admit. `c.long(n)`
  resolves because a module's alias of a numeric type is that type's
  conversion, and the import counts as used. A fixture proves the
  conversions in both oracles at two pointer widths and natively; a QBE
  test proves the trap.
  Gate: 1125 compiler tests across 61 files.
- [x] **`location()` (B4)** (2026-09-04). `Location` is the standard `io`
  module's struct, `file`, `line`, and `function`, spelled bare in a Base
  module through the profile's builtin type names (base.md §9.1);
  `location()` answers a `StructValue` of the module path, the span's line,
  and the function being checked. Written as a parameter default it stays
  the marker node `CallSiteLocation`, admitted as a constant expression,
  and `check_function_arguments` replaces the marker with the caller's
  location at every call site that omits the argument, so a logging helper
  reports where it was called. A fixture prints locations through both
  oracles and natively. Constructing one by hand is `io.Location(...)`.
  Gate: 1128 compiler tests across 63 files.
- [x] **Float display and `bits()` (B4)** (2026-09-04). A float field in a
  formatted string displays as the shortest decimal that reads back the
  same value (base.md §14.4): the full-Luce runtime's Ryū, portable 64-bit
  words and compact power-of-five tables included, is now also Base code
  in `src/standard/io.lucb` (`write_float64`, `write_float32`), building
  the text in a stack buffer and writing it once; `-0.0` and whole values
  keep their `.0`, magnitudes outside the fixed window take the `e` form,
  and `inf`/`nan` are spelled so. `value.bits()` reads an `f32` as `u32`
  and an `f64` as `u64` (§7.5) through the existing `NativeFloatBits`
  node, admitted by the Base profile's scalar-method hook. `trap(message)`
  now types its message as the profile's text, so a Base module may trap
  with a literal. A fixture prints the edge cases through both oracles and
  natively.
  Gate: 1128 compiler tests across 63 files.
- [x] **`str(bytes)` and `str(text)` (B4)** (2026-09-04). The two checked
  text conversions of base.md §5.5 are Base code in the standard `io`
  module: `text_from_bytes` validates UTF-8 (no overlong forms, surrogates,
  or values past U+10FFFF) and answers the bytes as a view, `text_from_c`
  scans a `cstr` to its NUL first, and both fail with `io.invalid_text`.
  The Base checker maps `str(x)` onto them by the argument's type and
  refuses anything else with the two spellings named. A fixture proves
  both through the oracles and natively, including the refusal. Also:
  `luce build --lib` no longer refuses a package that uses `atomic.fence`;
  the fence shims are compiled beside the assembly and merged into the one
  object with `ld -r`, so every Base example now builds as a library or an
  executable.
  Gate: 1129 compiler tests across 63 files.
- [x] **Base polish: bare `Location(...)` and `luce run` for a Base `main`**
  (2026-09-05). `Location(...)` constructs the standard `io` module's struct
  under its bare name, as the type is spelled (base.md §9.1), through the
  profile's `builtin_struct_index`. `luce run --package ID --root DIR
  MODULE.main FILE... -- ARG...` runs a Base program's process entry in the
  reference interpreter with the arguments after `--`, the entry module's
  path standing in for C's `argv[0]` so `arguments.length` agrees with the
  native shim; any other function keeps the plain `run`. The CLI test runs
  `examples/base/format.lucb` both ways.
  Gate: 1130 compiler tests across 63 files.
- [x] **`fmt` parameters (B4)** (2026-09-05). A parameter of type `fmt`
  accepts a formatted string or a `str` and may be printed, written to a
  `Writer`, formatted into a buffer, or passed on (base.md §9.1). `fmt` is
  the span `const io.Piece[]`: at the call site the checker lays the
  caller's pieces, a text view or one field value with its kind, in a
  hidden array on the caller's stack and passes the span, a pointer to the
  caller's values with no allocation and no generated function; a `str`
  argument is one text piece. Inside the callee `print(message)`,
  `sink.write(message)`, and `format(buffer, message)` call
  `io.write_pieces`, which dispatches each piece to the display function of
  its kind, and forwarding is passing the span. The new HIR `Sequence`
  node (statements, then a value) carries the hidden array. A fixture proves
  every use through the oracles and natively. `fmt` is a span, so nothing
  stops a program from storing one past the caller's frame; the spec's
  "cannot be stored" rule is not yet enforced.
  Gate: 1130 compiler tests across 63 files.
- [x] **`f64.bits(n)`, `f32.bits(n)`, and `char(n)` (B1, B4)** (2026-09-05).
  The two conversions base.md §7.5 still lacked: `f64.bits(n)` and
  `f32.bits(n)` build a float from its IEEE pattern through the new HIR
  `FloatFromBits` node and MIR `FloatFromBits` instruction (QBE `cast`,
  Wasm `reinterpret`, the oracles through the shared IEEE decoder), typed
  by the Base profile's builtin-type-function hook; `char(n)` is the
  checked conversion from any integer to a Unicode scalar value, widened,
  refused above U+10FFFF and in the surrogate range with the integer
  conversion trap, and narrowed to the `u32` a `char` is in MIR, with the
  HIR oracle applying the same rule. A fixture proves both through the
  oracles and natively; a QBE test proves the surrogate trap.
  Gate: 1132 compiler tests across 63 files.

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
9. QBE execution: division by zero relied on target behavior, and an earlier
   intentionally capped `u64` model was not enforced at legalization. The
   trapping corpus caught both; the cap itself was later removed by the full
   unsigned-domain milestone above.
10. Full-domain `u64`: QBE addition and multiplication, and Wasm arithmetic,
    still treated the sign bit as overflow after HIR/MIR stopped doing so.
    The expanded differential corpus caught QBE wrapping `u64.max + 1`; exact
    backend tests also pinned non-overflowing upper-half multiplication and
    unsigned carry, borrow, and quotient checks.
11. QBE product materialization: writing all child stdin before draining
    stdout intermittently deadlocked on the compiled runtime-list program when
    both pipes filled. Isolated runs often passed, while the complete gate
    stalled with empty tool diagnostics. IL and assembly now cross between
    host tools as regular files inside the already atomically owned scratch
    directory; the differential corpus and cleanup tests exercise that path.
12. QBE task codecs initially loaded an enum's byte tag with `loadw`, so nearby
    padding could select a nonexistent case. Exact shared narrow-memory
    operations now prevent padded reads.
13. Static string/byte literals carry null runtime owners. Traversing the owner
    in a worker crashed; codecs now serialize the canonical data/length fields
    and always construct a fresh owned destination buffer.
14. Binary16 is an `s` call value in QBE but a two-byte IEEE memory value. A
    shared representation module and an executable worker round-trip now pin
    that distinction for both ordinary emission and task codecs.
15. Lowerer: `recover <managed value>` registered the recovered value as a
   handler temporary and released it before the catch result took ownership,
   so QBE and Wasm both printed freed memory while the HIR oracle was right.
16. QBE: the checked 64-bit multiply verified `computed / right == left`,
   which arm64 `sdiv` satisfies for `INT64_MIN * -1`; the oracle trapped and
   the native binary printed the minimum.
17. HIR: `is_hashable_type` had no visited set, so a struct holding a
   `frozen_list` of itself as a map key recursed until the compiler hit its
   call-depth guard.

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
- 0.30 added a host-provided stack floor beside the frame counter and checks
  both at every generated function entry, including C callbacks and ARC
  deinitializers. It closes the fat-frame SIGBUS report; adoption identity and
  the 690-test project gate are recorded in `stage0-0.30.md`.
- Withdrawn after checking: "`return` in a statement-form `catch` does not return" — it does.

# Compiler record — what is done and why we believe it

This is the record half of the compiler's planning pair. It says what exists,
what each milestone proved, which bugs the harness caught, and where the
project came from. The other half, [`plan.md`](plan.md), holds the decisions
and the work that is still ahead; read that one to resume work, read this
one to check a claim. Every tick here has a commit and a green `./test.sh`
behind it.

Last updated: 2026-08-31 (Stage-0 0.28).

## 1. Where things stand

| Layer | State |
|---|---|
| Tokenizer, parser, syntax tree | Complete for the 1.0 surface (`docs/language/1.0.md`); every syntax form has parser coverage. Throughput is linear (~450 KB/s); expression nesting is capped at 256 with a diagnostic. |
| HIR generation (`hir/generator.luc`, `declarations.luc`, `body_checker.luc`, `generation_model.luc`, `generics/functions.luc`, `interfaces/values.luc`) | Functions, generic functions with abstract checking, interface constraints and bounded memoized concrete instances, nominal interface declarations, explicit struct/class/enum conformance, static requirement dispatch, existential conversion/dynamic calls, and infallible-to-fallible conformance adapters; direct calls, exact named `func`/`cfunc` values and shared indirect calls; managed closures, classes, collections, failure, control flow, native authority, and the remaining executable slice described below. Documentation and defaults are retained. **Not yet**: `f16`, assertion-condition effect proofs, resource-shape/leak tooling and closure sendability, generic nominal types, executable `try for`, maps/sets, formatted/triple strings, and the remaining rich C boundary (strings, extern structs, exported structs/enums, dynamically supplied/nullable cfunc pointers). Each unsupported form fails with a span. |
| HIR interpreter (`backends/interpreter.luc`) | The semantic oracle. Executes safe HIR generation, including existential interface storage, dynamic calls and value/class mutation semantics; escaping/nested closures, shared mutable capture cells and weak captures; shared class identity, atomic weak promotion/zeroing, fallible construction cleanup, deterministic deinitialization, and isolated sealed-runtime state. Runs `main(arguments: slice[str])` with an empty slice. |
| Canonical MIR (`mir/canonical.luc`) | Target-neutral and designed for the whole language (`mir.md`), including nominal interface handles and normalized requirement/conformance metadata, typed function descriptors, closure schemas, mutable cells, nominal strong/weak class handles, payload schemas, and generated ownership helpers with no physical layout; the verifier proves every rule, reachability removes unreachable closed-world functions/resources, and the MIR interpreter executes every instruction under explicit test layout rules. |
| Lowerer (`mir/lowerer.luc`, `lowering_model.luc`, `function_lowerer.luc`) | Everything HIR generates, including normalized erased-receiver interface witnesses, existential ownership/COW operations and dynamic calls; scalars, aggregates, managed collections/classes/closures, control and failure transfer, structural ownership on every value edge, C boundaries, exact runtime bindings, native operations, and output. Generic declarations are fully specialized before this boundary. |
| WebAssembly backend (`backends/wasm.luc`) | Supporting regression backend for the current lowerer surface, with spec arithmetic, exact indirect and interface calls, backend-owned witness descriptors, WASI preview 1, C imports/globals, shadow-stack aggregates, typed moves, and backend-local managed layout. The interface, reclaiming-list, and managed-class examples execute under Wasmtime. It is not the stage-1 portability boundary. |
| QBE backend (`backends/qbe.luc`, `qbe_toolchain.luc`) | The required stage-1 portability and artifact oracle: direct canonical-MIR → QBE 1.3 IL with backend-owned aggregate/class/interface layout and descriptor tables, structured-control flattening, checked arithmetic, direct/indirect/dynamic calls, typed memory, internal globals, a stable guarded arena, the compiled Luce runtime, C symbols, and a private caller-owned fallible-result ABI. The product path streams IL and assembly through memory, links in secure same-directory scratch, and atomically installs the executable. The complete differential corpus uses this path. |
| Tests | 623 unit tests across 16 files, plus CLI, `wasmtime`, QBE differential, and host-native smoke gates. `tests/compiler/differential_test.luc` runs the complete non-trapping and trapping corpus through HIR, optimized MIR, and the QBE product toolchain and checks values, output, and traps. |
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
- [x] **Floating construction has one explicit checked IEEE policy**
  (2026-08-31). `NumericConvert` also covers integer/float, float/integer, and
  f32/f64 width changes. Contextual f32 literals and every binary32 operation
  round at binary32 rather than leaking the oracles' f64 carrier. Narrowing
  uses nearest/ties-to-even and traps only finite overflow; NaN and infinity
  remain IEEE values. Float-to-integer truncates toward zero after rejecting
  NaN, infinity, and the destination interval's exterior. Canonical MIR adds
  only typed `float_resize`; target-independent lowering supplies semantic
  guards, QBE legalizes its otherwise target-defined integer conversions and
  uses `truncd`/`exts`, while Wasm uses its native trapping and promote/demote
  operations. Host seams canonicalize f32 too. Positive, rounding-boundary,
  non-finite, constant-error, runtime-trap, verifier, native QBE, Wasm, and
  executable-example evidence agree. `f16` remains the separate missing width.
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
  The spec's call-effect proof remains deliberately open until operational
  summaries can prove callees effect-free; rich source traces remain in the
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
  owner in `hir/closure_context.luc`. Remaining §11 work is tracked separately
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
  `examples/generic_functions.luc` agree. Constraints, generic nominal types,
  serialized typed bodies, and detailed expansion accounting remain.

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
  concepts to canonical MIR. Existential values are recorded separately below;
  generic nominal types, serialized bodies, and detailed expansion accounting
  remain on the generic side.

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

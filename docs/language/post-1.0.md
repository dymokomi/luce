# Luce Language Design — post-1.0 platform

Status: design material deferred past 1.0. Companion to [`1.0.md`](1.0.md), which is the normative 1.0 language specification.

1.0 is the language: source surface, semantics, the C boundary, tests, the interpreter and one native backend, and the tooling a single command needs. Everything below is specified so the language does not paint itself into a corner, but it ships, stabilizes, and is measured after 1.0. Section numbers are kept identical to the 1.0 document so cross-references stay valid; each section here is marked "deferred" at its original position there.

Contents: package manifest and dependency identity (§20.6–20.8); the C++ bridge, support tiers, and binding UX (§21.6–21.11, §21.13–21.15); the backend portfolio, artifact/ABI model, build profiles, and caching (§23.2–23.3, §23.5–23.8); the persistent compiler service, documentation, debugging, performance and security gates (§24.1, §24.6–24.9).

## 20. Modules, packages, and visibility

### 20.6 Package manifest

Every package has one declarative `luce.toml` manifest and one exact generated `luce.lock`. The manifest records:

- package name, version, language version, and source roots;
- products (library, executable, native bridge);
- exact dependency requirements and public/private dependency status;
- native headers/libraries and binding recipes;
- supported target/profile constraints;
- test source roots, test-only dependencies, and documentation products.

Resolution produces a content-addressed lockfile. Builds are hermetic by default. There are no package build scripts, compiler plugins, arbitrary command hooks, environment-variable probing, or network access during compilation. Native generation uses first-party declarative binding rules; exceptional code generation happens as an explicit pre-build project step whose output is checked into or supplied as source.

Test-only dependencies are resolved and locked by the same package graph but are visible only to modules in declared test source roots. Inline tests in product modules may use the compiler-known `testing` standard module and the product's ordinary dependencies; they cannot smuggle an external test dependency into production source. A production build computes reachability after removing test declarations, so test-only imports, dependencies, capabilities, symbols, and description strings are absent from its artifact.

### 20.7 Dependency identity

One build graph contains one resolved identity/version for each package unless dependencies are explicitly namespaced as separate packages. Type identity includes package and module, preventing accidental equivalence between same-spelled types.

The package manager reports why every dependency is present, audits licenses/advisories, and can emit a minimal reproducible source bundle. Adoption depends as much on trustworthy packages as on syntax.

### 20.8 Platform variation

1.0 has no conditional-compilation directive in source. `luce.toml` may select target-specific source roots and native bindings through declarative target predicates; each selected module must still present the public API promised by the package. Ordinary code depends on a portable interface module whose implementation is chosen by the package graph.

Runtime variation is queried through explicit library APIs, not compile-time name tests. This avoids preprocessor dialects while still supporting operating-system and architecture adapters.

## 21. Native interoperability

### 21.6 C++ import strategy

C++ bindings use Clang to understand declarations and a generated bridge compiled by the platform C++ compiler. The stable Luce-facing baseline is a flat C ABI thunk surface:

```text
Luce call -> generated C ABI thunk -> C++ method/function
```

An LLVM backend may later optimize or LTO across the bridge when toolchains match, but correctness and source semantics cannot depend on that. A custom x64/ARM64 backend calls the same thunks and therefore retains full supported interop.

### 21.7 Supported C++ subset

The importer should support, in staged order:

- free functions, namespaces, enums, POD/value structs, and constants;
- constructors/destructors and methods through opaque owner wrappers;
- references/pointers with recipe-specified borrow/ownership;
- `std::string`/`string_view`, spans, vectors, optionals, and expected-like types through blessed adapters;
- explicit template instantiations listed in the manifest;
- callbacks represented by generated context-pointer thunks and lifetime tokens;
- selected virtual interfaces wrapped behind generated flat functions.

The following do not become Luce language features:

- C++ inheritance and overload sets;
- operator overloads and implicit conversions;
- reference/lifetime syntax;
- templates/metaprogramming;
- exceptions or RTTI/downcasts;
- header macros.

The importer maps an overload set to stable semantic names, using binding-recipe overrides when mechanical names are poor. It wraps inheritance through composition/interface-shaped APIs. Users see Luce, not transliterated C++.

A C++ default argument becomes an ordinary Luce default only when Clang/FIIR proves it is a safe portable constant. Otherwise the generator emits a semantically named wrapper that supplies it inside C++, avoiding hidden foreign evaluation at each call.

### 21.8 C++ exceptions and failure

No C++ exception crosses a Luce frame. Every generated thunk catches according to its recipe:

- known exceptions map to stable error codes/messages;
- unknown `std::exception` values map to a package bridge error with `what()` as context;
- non-standard exceptions map to an opaque bridge failure;
- functions declared/verified `noexcept` can omit the catch path.

The safe wrapper exposes `T!`. Exception translation cost is included in native-bridge inspection.

### 21.9 C++ objects and lifetime

An owned C++ object is normally represented by a final Luce class containing an opaque native handle. Its `deinit` invokes the generated destructor thunk. Borrowed subobjects cannot escape unless the recipe provides a stable shared owner; otherwise they are exposed only to a closure-scoped callback or copied.

Common ownership adapters are fixed and inspectable: `unique_ptr<T>`/owned raw results become one Luce owner class; `shared_ptr<T>` becomes an ARC wrapper holding one C++ shared owner; `weak_ptr<T>` becomes an optional generated weak-handle operation; stable `span`/`string_view` borrows retain a suitable owner or remain callback-scoped. The generator never assumes that a reference implies any one of these policies.

Move-only C++ values stay behind owner wrappers. Luce does not add a universal `move` operation to imitate them. Explicit methods such as `take_buffer()` may invalidate a wrapper and return a new owner when a library requires transfer; use-after-transfer is diagnosed by the wrapper's state checks.

### 21.10 Templates

The manifest lists each concrete template specialization to expose:

```toml
[[native.geometry.template]]
name = "geom::Vector"
arguments = ["float", "3"]
luce_name = "Vector3f"
```

The generator asks Clang to instantiate and bridge it. Luce generics do not instantiate arbitrary C++ templates, and C++ templates do not leak into Luce's type system. This keeps compile time, errors, and ABI reproducible.

### 21.11 Callbacks, threads, and reentrancy

A generated callback adapter owns a context object that retains its Luce closure until the foreign API invokes the paired unregister/destructor operation. The binding recipe declares whether calls are synchronous, reentrant, retained, and which thread may invoke them.

- Same-worker synchronous callbacks may call the closure directly.
- A callback arriving on a foreign thread enters generated native-side adapter code — never a raw Luce `cfunc`, which a thread Luce never entered cannot invoke (§21.19) — that copies validated sendable arguments into the owning worker's ingress queue; ordinary Luce identity is never touched concurrently.
- A foreign API requiring an immediate return from an arbitrary thread accepts only a generated or handwritten audited native adapter. Capture-freedom is not enough: even a trivial Luce body can trap, print, and allocate, so it runs only on a thread that carries its runtime (§21.19).
- Unregister races use the generated lifetime token; a callback cannot observe a freed context.
- Reentrant callbacks are marked in FIIR and shown by the binding generator so wrapper code can avoid invalid intermediate states.

Unsupported threading/lifetime contracts make safe wrapper generation fail. The tool never silently calls an ordinary Luce closure concurrently.

### 21.13 Export to C++

Luce does not expose a separate unstable C++ ABI. A C++ consumer receives the generated C header plus an optional header-only RAII/type-safe facade:

- constructors/destructors wrap opaque Luce-owned handles;
- fallible calls map to the selected expected/status convention without letting exceptions cross Luce;
- strings/spans use explicit adapters;
- callbacks use the same generated context/lifetime machinery;
- ABI symbols remain C even when the facade feels idiomatic in C++.

This provides good C++ UX while keeping one stable foreign boundary and all backends equivalent.

### 21.14 Support tiers

- **Tier A — automatic safe:** scalars, fixed values, enums, strings/spans, unambiguous ownership, ordinary functions/methods, blessed containers.
- **Tier B — declaratively safe:** recipe-specified ownership, nullable/borrowed views, status/exception mapping, overload naming, callbacks, explicit templates.
- **Tier C — native adapter:** exotic templates, macro-generated APIs, complex inheritance, undocumented lifetime/thread rules, compiler-specific extensions.

Documentation reports the tier for every imported declaration. “Unsupported automatically” means “write/audit one adapter,” not “change the Luce language.”

### 21.15 Binding UX requirements

`luce bind` must provide:

- a binding preview before files are generated;
- unmapped/unsafe declaration reports;
- source links back to header locations;
- ownership/nullability questions expressed as actionable recipe edits;
- cached incremental Clang parsing and bridge compilation;
- API diffs when a native dependency changes;
- a test harness that compares layouts and calls a probe binary.

Interop quality is measured by how quickly a user reaches a small safe wrapper and how little C++ knowledge leaks into ordinary Luce—not by the percentage of exotic header syntax imported mechanically.

Every binding cache key fingerprints header contents, transitive include graph, defines/flags, target triple, C/C++ language mode, Clang/bridge generator, C++ standard library/ABI, recipe, linked library identity, and safe-wrapper generator. `luce bind` explains which input invalidated a cache entry.

Dynamic libraries are resolved from explicit package/bundle locations and recorded deployment dependencies. Builds do not depend on an ambient working directory, undocumented system search path, or whichever C++ runtime happens to load first. The first-party driver may use a bundled compiler/linker or a manifest-declared compatible platform SDK; `luce doctor` verifies that contract before a build.

## 23. Runtime, ABI, artifacts, and backends

### 23.2 Backend interface

Backends implement a versioned interface for:

- target data layout and calling convention;
- scalar/vector operations and checked traps;
- control flow and function calls;
- ARC/runtime calls and stack maps as required;
- native C ABI calls;
- debug/unwind information;
- object/executable emission and linking.

No backend decides language typing, ARC semantics, error propagation, C++ import shape, or module behavior.

### 23.3 Backend portfolio

The intended sequence is:

1. **typed interpreter** as a rapid semantic oracle and development runner;
2. **LLVM backend** for target reach, optimization, debug formats, and initial production quality;
3. **direct x64 backend** optimized for very fast debug/edit-run builds;
4. **direct ARM64 backend** when the x64 design and runtime ABI are stable;
5. optional additional/wasm backends based on product evidence.

LLVM remains a supported backend, not the architecture. Direct backends may trade peak optimization for extremely low latency. Release/build profiles can choose per target without changing source or native wrapper APIs.

The distribution owns ordinary object emission, archive/link driving, target libraries, and cross-target discovery; a normal Luce/C build does not assemble itself through an ambient `cc`. C++ bridging is the explicit exception that may require a manifest-declared compatible platform C++ SDK/compiler because it is the ABI semantic oracle, and `luce doctor` verifies it up front.

### 23.5 Artifact model

The durable project inputs are UTF-8 `.luc` source, `luce.toml`, `luce.lock`, package content identities, language version, and explicit target/profile choices.

The compiler may emit a deterministic portable `.lc` artifact containing verified canonical IR and public type/function interfaces, useful for caching and distribution; source remains the long-term authority and any `.lc` may be rejected and rebuilt when its format is unsupported.

Native `.o`, static/dynamic libraries, executables, debug symbols, and application bundles are explicit target-specific outputs. They are keyed by the portable component plus backend, target, runtime ABI, profile, linker, and native bridge identities. They are never confused with portable/source artifacts and are always disposable caches unless intentionally published as a product.

One release manifest generates the compiler's build identity, language version, portable format, runtime/native ABI versions, supported targets/backends, standard modules, and bundled package versions. Release validation fails if tools, installers, docs, or artifacts disagree with that source of truth.

### 23.6 ABI layers

Luce distinguishes:

- **C ABI**, stable where explicitly exported;
- **runtime ABI**, versioned with compiler/runtime distribution;
- **package binary ABI**, initially compiler-version-specific;
- **source API**, checked by generated interface descriptions;
- **serialized generic/IR format**, an internal versioned artifact.

1.0 does not promise a permanent native Luce ABI. Premature ABI freezing would fossilize class/interface/generic layouts. Cross-version/system boundaries use C ABI or a declared serialization/protocol format.

### 23.7 Build profiles

Standard profiles are:

- `check`: parse/type/ownership validation, no codegen;
- `debug`: fast codegen, full checks, rich traces;
- `release-safe`: optimized with all language safety checks;
- `release-fast`: optimized; may use explicitly requested unchecked library algorithms but never silently removes core memory safety;
- `size`: optimized for artifact size.

Testing is an overlay on these profiles rather than a sixth semantic mode: it adds the statically discovered test graph, harness, deterministic test context, and observability while preserving the selected profile's language rules. The default `luce test` profile is fully checked `debug`; CI may additionally select `release-safe` to expose optimization/backend defects.

Profile differences cannot change overflow semantics, evaluation order, error behavior, data-race model, or public API. Unsafe speedups are named APIs or manifest decisions visible in review.

### 23.8 Determinism and caching

Given the same source, lockfile, compiler/runtime version, target, profile, native inputs, and declared environment, a build must be bit-reproducible where platform linkers permit. Cache keys include all of those inputs. The compiler reports cache misses with the exact changed key component.

Incremental compilation works at declaration/typed-IR granularity. A private function-body change should not rebuild unrelated modules or native bridges. Fast feedback is a language-product requirement, not a future optimization.

## 24. Tooling and diagnostic contract

### 24.1 Persistent compiler service

The compiler is a library and a long-lived semantic service first, then a CLI. One incremental query graph owns source/package identity, parsing, names, types, generics, captures, sendability, public API fingerprints, and cost facts.

- The parser produces a lossless, error-tolerant syntax tree with stable identities for incomplete editor buffers.
- Declaration/function-body queries invalidate only transitive dependents; every miss can explain why.
- Diagnostics, formatting, completion, hover, definition/references, rename, match completion, named-argument fixes, cost, API diff, and build consume the same facts.
- File-system, generated-native, and editor-buffer sources enter through one byte/source-identity loader interface.
- Requests are cancellable and revisioned; a stale answer is never published over a newer buffer.
- Tools and agents receive versioned structured data, never scrape colored terminal prose.

### 24.6 Documentation

`##` comments attach to the next public declaration. Documentation checks:

- every public symbol has a summary;
- parameter/result/failure contracts are rendered from the signature;
- code examples compile and can be marked runnable;
- native wrappers link to their foreign declarations and recipes;
- allocation/order/complexity notes use structured doc sections;
- docs search by operation, type, error code, and package.

The generated language reference is versioned by language version and includes grammar, examples, and rationale links. Beginner material introduces only the concepts needed for the next working program.

### 24.7 Debugging and observability

Debug builds provide source-level stepping across Luce and generated bridge frames, value renderers that respect privacy, task/worker histories, ARC object graphs, allocation flame graphs, and deterministic error traces.

Generated native thunks may be collapsed in the default stack view but are never hidden from an expanded trace. Users must be able to locate cost and failure at an interop boundary.

### 24.8 Compiler performance budgets

The project tracks cold check, incremental check, debug build, clean release build, peak memory, package-resolution, and native-binding latency on representative repositories—including the Luce compiler itself. Regressions block release once budgets are established.

The direct debug backend exists to make edit/check/run feel immediate; LLVM remains available when reach or peak optimization matters. Backend choice is explicit in build output and cache keys, not source code.

### 24.9 Correctness and security gates

A release requires:

- lexer/parser/type/MIR-verifier fuzzing, including malformed `.lc` inputs;
- expected-diagnostic, expected-trap, and cleanup-on-every-exit suites;
- interpreter/LLVM/direct-backend differential behavior over the same corpus;
- ARC balance, weak/cycle, allocation-failure, worker-transfer, cancellation, and resource-finalization stress tests;
- C/C++ ABI layout/call/exception/callback probes across supported platform tiers;
- reproducible bootstrap and build records;
- formatter idempotence and fix/migration semantic preservation;
- package-resolution tests with offline/vendored builds;
- explicit audit of the small runtime/native unsafe substrate.

Supported host/target tiers state compiler, linker, debugger, native bridge, package, and CI coverage. A platform is not marketed as supported when only trivial code generation works.

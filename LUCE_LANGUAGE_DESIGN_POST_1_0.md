# Luce Language Design — post-1.0 platform

Status: design material deferred past 1.0. Companion to `LUCE_LANGUAGE_DESIGN.md`, which is the normative 1.0 language specification.

1.0 is the language: source surface, semantics, the C boundary, tests, the interpreter and one native backend, and the tooling a single command needs. Everything below is specified so the language does not paint itself into a corner, but it ships, stabilizes, and is measured after 1.0. Section numbers are kept identical to the 1.0 document so cross-references stay valid; each section here is marked "deferred" at its original position there.

Contents: package manifest and dependency identity (§20.6–20.8); the C++ bridge, support tiers, and binding UX (§21.6–21.11, §21.13–21.15); the backend portfolio, artifact/ABI model, build profiles, and caching (§23.2–23.3, §23.5–23.8); the persistent compiler service, documentation, debugging, performance and security gates (§24.1, §24.6–24.9); reconsideration candidates (§26.3); implementation phases 6–9; the research reconciliation record (§30); and the platform release gate (§31).

## 20. Modules, packages, and visibility

### 20.6 Package manifest

Every package has one declarative `luce.toml` manifest and one exact generated `luce.lock`. The manifest records:

- package name, version, language epoch, and source roots;
- products (library, executable, LuciaOS component, native bridge);
- exact dependency requirements and public/private dependency status;
- requested host capabilities;
- native headers/libraries and binding recipes;
- supported target/profile constraints;
- test source roots, test-only dependencies/capability policy, and documentation products.

Resolution produces a content-addressed lockfile. Builds are hermetic by default. There are no package build scripts, compiler plugins, arbitrary command hooks, environment-variable probing, or network access during compilation. Native generation uses first-party declarative binding rules; exceptional code generation happens as an explicit pre-build project step whose output is checked into or supplied as source.

Test-only dependencies are resolved and locked by the same package graph but are visible only to modules in declared test source roots. Inline tests in product modules may use the compiler-known `testing` standard module and the product's ordinary dependencies; they cannot smuggle an external test dependency into production source. A production build computes reachability after removing test declarations, so test-only imports, dependencies, capabilities, symbols, and description strings are absent from its artifact.

### 20.7 Dependency identity

One build graph contains one resolved identity/version for each package unless dependencies are explicitly namespaced as separate packages. Type identity includes package and module, preventing accidental equivalence between same-spelled types.

The package manager reports why every dependency is present, audits licenses/advisories, and can emit a minimal reproducible source bundle. Adoption depends as much on trustworthy packages as on syntax.

### 20.8 Platform variation

Epoch 1 has no conditional-compilation directive in source. `luce.toml` may select target-specific source roots and native bindings through declarative target predicates; each selected module must still present the public API promised by the package. Ordinary code depends on a portable interface module whose implementation is chosen by the package graph.

Runtime variation is queried through explicit library/capability APIs, not compile-time name tests. This avoids preprocessor dialects while still supporting operating-system and architecture adapters.

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
- Reentrant callbacks are marked in FIIR and shown by `luce explain` so wrapper code can avoid invalid intermediate states.

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

The durable project inputs are UTF-8 `.luc` source, `luce.toml`, `luce.lock`, package content identities, language epoch, and explicit target/profile choices.

The compiler may emit a deterministic portable `.lc` component containing verified canonical IR, public type/function interfaces, required effects/host profile, package identities, and optional source origins. `.lc` is useful for LuciaOS distribution, caching, and hostile-input verification, but source remains the long-term authority and any `.lc` may be rejected/rebuilt when its format/runtime contract is unsupported.

Native `.o`, static/dynamic libraries, executables, debug symbols, and application bundles are explicit target-specific outputs. They are keyed by the portable component plus backend, target, runtime ABI, profile, linker, and native bridge identities. They are never confused with portable/source artifacts and are always disposable caches unless intentionally published as a product.

One release manifest generates the compiler's build identity, language epoch, portable format, runtime/native ABI versions, supported targets/backends, standard modules, and bundled package versions. Release validation fails if tools, installers, docs, or artifacts disagree with that source of truth.

### 23.6 ABI layers

Luce distinguishes:

- **C ABI**, stable where explicitly exported;
- **runtime ABI**, versioned with compiler/runtime distribution;
- **package binary ABI**, initially compiler-version-specific;
- **source API**, checked by generated interface descriptions;
- **serialized generic/IR format**, an internal versioned artifact.

Epoch 1 does not promise a permanent native Luce ABI. Premature ABI freezing would fossilize class/interface/generic layouts. Cross-version/system boundaries use C ABI or a declared serialization/protocol format.

### 23.7 Build profiles

Standard profiles are:

- `check`: parse/type/effect/ownership validation, no codegen;
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

The compiler is a library and a long-lived semantic service first, then a CLI. One incremental query graph owns source/package identity, parsing, names, types, generics, effects, captures, sendability, public API fingerprints, and cost facts.

- The parser produces a lossless, error-tolerant syntax tree with stable identities for incomplete editor buffers.
- Declaration/function-body queries invalidate only transitive dependents; every miss can explain why.
- Diagnostics, formatting, completion, hover, definition/references, rename, match completion, named-argument fixes, effects, cost, API diff, and build consume the same facts.
- File-system, LuciaOS blob, generated-native, and editor-buffer sources enter through one byte/source-identity loader interface.
- Requests are cancellable and revisioned; a stale answer is never published over a newer buffer.
- Tools and agents receive versioned structured data, never scrape colored terminal prose.

### 24.6 Documentation

`##` comments attach to the next public declaration. Documentation checks:

- every public symbol has a summary;
- parameter/result/failure/effect contracts are rendered from the signature;
- code examples compile and can be marked runnable;
- native wrappers link to their foreign declarations and recipes;
- allocation/order/complexity notes use structured doc sections;
- docs search by operation, type, effect, error code, and package.

The generated language reference is versioned by epoch and includes grammar, examples, and rationale links. Beginner material introduces only the concepts needed for the next working program.

### 24.7 Debugging and observability

Debug builds provide source-level stepping across Luce and generated bridge frames, value renderers that respect privacy, task/worker histories, effect/capability logs, ARC object graphs, allocation flame graphs, and deterministic error traces.

Generated native thunks may be collapsed in the default stack view but are never hidden from an expanded trace. Users must be able to locate cost and failure at an interop boundary.

### 24.8 Compiler performance budgets

The project tracks cold check, incremental check, debug build, clean release build, peak memory, package-resolution, and native-binding latency on representative repositories—including the Luce compiler itself. Regressions block release once budgets are established.

The direct debug backend exists to make edit/check/run feel immediate; LLVM remains available when reach or peak optimization matters. Backend choice is explicit in build output and cache keys, not source code.

### 24.9 Correctness and security gates

A release requires:

- lexer/parser/type/MIR-verifier fuzzing, including hostile `.lc` inputs;
- expected-diagnostic, expected-trap, and cleanup-on-every-exit suites;
- interpreter/LLVM/direct-backend differential behavior over the same corpus;
- ARC balance, weak/cycle, allocation-failure, worker-transfer, cancellation, and resource-finalization stress tests;
- C/C++ ABI layout/call/exception/callback probes across supported platform tiers;
- reproducible bootstrap and build records;
- formatter idempotence and fix/migration semantic preservation;
- package-resolution/provenance/advisory tests with offline/vendored builds;
- explicit audit of the small runtime/native unsafe substrate.

Supported host/target tiers state compiler, linker, debugger, native bridge, package, and CI coverage. A platform is not marketed as supported when only trivial code generation works.

## 26. Feature admission and evolution

### 26.3 Reconsideration candidates

The following may be researched after epoch 1, in this order and only with evidence:

1. ~~one optional default/coalescing operation~~ — **adopted 2026-08-24** as the `else` form (§13.1), on native-interop evidence;
2. call-scoped `inout` if compiler/native algorithms otherwise allocate or obscure intent;
3. a structured message channel if spawn/wait cannot support required pipelines;
4. a host-integrated async model if synchronous capability APIs cannot deliver necessary scale/debugging;
5. a constrained declarative derive/generator system if source generation becomes a dominant maintenance burden;
6. additional direct backends and SIMD intrinsics;
7. 128-bit integers (`u128`/`i128`) as ordinary checked scalars, if numerics or native interop produce the evidence (owner note, 2026-08-24).

None is promised. Each must reduce total system complexity, not only local character count.

## 27. Complete implementation sequence

### Phase 6 — C++ bridge

- C++ FIIR declarations and staged supported subset.
- generated C ABI thunks, exception translation, owner/borrow recipes.
- blessed STL adapters, explicit template instantiation, callback lifetimes.
- overload renaming and composition/interface wrapper generation.
- header-change API diffs and mixed-source debugging.

Exit: substantial real C++ libraries can be consumed through ordinary small Luce APIs without C++ object-model syntax leaking into user code.

### Phase 7 — isolated workers and LuciaOS integration

- structural sendability derivation and frozen collection snapshots.
- worker graph copying, task result/failure, structured cancellation/join.
- capability manifests, grants, component entry points, resource budgets.
- deterministic task histories and worker transfer-cost tooling.

Exit: LuciaOS applications can safely run parallel work and host-limited components without a shared heap.

### Phase 8 — fast direct backends

- stabilize canonical IR/runtime ABI from LLVM/self-host experience.
- direct x64 debug backend, object/link/debug support, C ABI bridge calls.
- benchmark and optimize incremental edit/check/run path.
- direct ARM64 backend after x64 correctness/tooling coverage.
- keep LLVM selectable for unsupported targets and peak optimization.

Exit: common targets get very fast debug compilation with identical language/native semantics across backends.

### Phase 9 — adoption release

- complete tutorial sequence and searchable reference from this specification.
- migration guide from 0.18 concepts (without source-compatibility fiction).
- maintained examples: CLI, GUI/LuciaOS app, compiler subsystem, C library, C++ library.
- package provenance/advisory/license tooling and reproducible release bundles.
- external pilot feedback, usability tests, diagnostic comprehension tests.
- freeze epoch 1 only when all supported features have formatter/LSP/debug/docs/backend/native coverage.

Exit: “small” describes the concept count a learner carries, not missing production infrastructure.

## 30. Research and Luce reconciliation

This specification is not a blank-sheet style exercise. It distills the two interviews, the public Luce 0.18 language/tool/compiler record, the clean-break/self-hosting decision, and the C/C++/backend research into one implementable surface.

### 30.1 Interview lessons made concrete

| Research lesson | Concrete requirement in this specification |
| --- | --- |
| Do more with less permanent language complexity ([Zig interview, 10:16–12:20](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=616s)) | Nine-concept budget, layer-placement rule, exclusions, evidence-based feature admission |
| Tool limitations must not dictate the product; owning load-bearing compiler pieces enabled speed ([Zig interview, 04:07–06:10](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=247s), [23:38–26:42](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=1418s)) | Backend-independent canonical IR, typed interpreter, supported LLVM path, fast direct backends, shared semantics |
| A self-contained toolchain changes adoption ([Zig interview, 47:10–48:48](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=2830s)) | One release/command owns check, format, build, link, LSP, test, docs, package, bind, explain, migrate, and doctor |
| Repair exercises and short feedback loops teach better than ceremonial setup ([Zig interview, 52:16–55:15](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=3136s)) | First-hour `test`, static discovery, compiler-teacher failures, deterministic test context, and no reflection/annotation framework |
| Strict rules can save time when tools provide trustworthy fixes ([Zig interview, 48:11–50:14](https://www.youtube.com/watch?v=iqddnwKF8HQ&t=2891s)) | No shadowing/implicit conversions plus structured causal diagnostics and deterministic fixes |
| Safety, performance, and usability are one product problem ([Rust interview, 00:00–01:01](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=0s)) | Safe defaults remain in release; ARC avoids pervasive lifetime syntax; cost/ARC/allocation inspection prevents hidden performance |
| Adoption is constrained by existing code, libraries, builds, telemetry, debugging, and trained people ([Rust interview, 03:02–09:06](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=182s)) | C import/export first, Clang-informed C++ bridge, packages, debugger/profiler/docs, incremental component adoption |
| Expressive types prevent domain errors ([Rust interview, 22:21–24:22](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=1341s)) | Low-boilerplate structs, distinct wrappers, payload-capable enums, exhaustive matching, optionals, stable error codes |
| Hard concepts require helpful concise compiler errors ([Rust interview, 50:12–57:17](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=3012s)) | Compiler-as-teacher diagnostics, dependency-ordered learning, computer facts before syntax folklore |
| Compile time, monomorphization, disk, debugging, and macro costs are real UX ([Rust interview, 59:19–64:24](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=3559s)) | No macro/comptime system in epoch 1, generic budgets/explanations, incremental service, direct debug backend |
| A theoretically clean language does not win without useful flexibility ([Rust interview, 70:33–71:34](https://www.youtube.com/watch?v=nOSxuaDgl3s&t=4233s)) | “Minimum complete,” not toy minimalism: classes, closures, generics, interfaces, resources, interop, and a serious library remain |

### 30.2 What 0.18 proved and what changes

The page-by-page baseline remains the public [Luce documentation](https://luce.luciaos.com/) and [compiler engineering atlas](https://lucelang.org/), reconciled in `LUCE_UX_ADOPTION_REQUIREMENTS.md`. The clean break treats implementation experience as evidence, not compatibility law.

| 0.18 evidence | Epoch 1 disposition |
| --- | --- |
| Python-familiar indentation, `let`/`var`, explicit functions/control | Keep and specify canonically |
| Values copy; references use ARC; `weak` breaks cycles; final release closes resources | Keep as the permanent memory model; add allocation/ARC/cycle inspection |
| `T?`, `T!`, and traps are distinct | Keep; add stable programmatic `ErrorCode` and local recovery semantics |
| Typed HIR, verified MIR, interpreter/native differentiation | Keep the representation ladder; make canonical IR/backend interfaces independent and hostile-input verified |
| Host table/capability seam and isolated workers | Keep; make public effects stable and worker value transfer structural/observable |
| Exact local packages and no build scripts | Keep; finish lock, hashing, fetch/vendor/audit/publish, provenance, and public API diff |
| No user generics | Reverse before self-hosting; compilers and ecosystems need restrained reusable data structures |
| LLVM-only production path | Keep LLVM as supported reach/optimization, add fast Luce-owned direct backends behind identical IR |
| Generated runtime C ABI but no complete user FFI | Replace with first-class C import/export and safe ownership/error/callback adapters |
| C++ question unanswered | Add Clang/FIIR discovery, generated C ABI thunks, idiomatic safe wrappers; do not import the C++ object model |
| Multiple public-version/document truths and incomplete editor tooling | One release manifest and one persistent compiler service generate every surface |
| 0.18 source/artifact/API details | Retain as historical evidence; freeze Stage-0 0.19 as the reproducible seed; promise no compatibility |

### 30.3 Decisions intentionally reopened by implementation evidence

The compiler and standard library are the first pressure tests. If they expose a concrete shortfall, revisit the smallest adjacent mechanism—not the whole doctrine. Examples include measuring whether ARC/copy elision is sufficient before proposing regions, whether one-statement arms avoid helper or mutable staging code before proposing expression-valued `match` (evidence that has since arrived — §9.6), whether closure-scoped mutable views cover parsing/codegen before proposing `inout`, and whether generated C++ thunks meet performance budgets before coupling the language to one backend.

The companion documents retain the deeper product requirements and C++ fixtures. This document is the normative source-surface/runtime/tool contract; where an older proposal conflicts with it, this clean-break specification wins after the conflict is recorded as a design decision.

## 31. The platform release gate (post-1.0)

The 1.0 document carries the language gate. The full platform promise below is the bar for calling the *platform* stable; it is the original epoch-1 gate, retained unchanged.

Do not label the language 1.0 merely because the parser accepts every construct. Epoch 1 becomes a stable adoption promise only when all of these are true:

- the frozen Stage-0 0.19 seed reproducibly builds the transition compiler, which builds a fixed-point self-hosted compiler;
- the compiler, formatter, language server, package manager, documentation generator, native binder, and core standard library are themselves substantial Luce programs;
- the interpreter, LLVM backend, and every claimed direct backend pass the same behavior/trap/cleanup corpus;
- warm editor/check latency, clean build time, peak compiler memory, generic expansion, runtime ARC/allocation, artifact size, and native bridge costs meet published budgets on named hardware;
- C import/export is stable and production-proven; the promised C++ tier is qualified against representative libraries and supported platform ABIs;
- package lock/provenance/vendor/audit/offline workflows and a security response process are operational;
- diagnostics and the first-hour learning path have been tested with people who did not design Luce;
- inline/private and integration/public test boundaries, deterministic isolation, structured reports, expected-trap child domains, and complete production erasure have conformance coverage;
- at least the compiler, a LuciaOS application, a standalone native application, a C integration, and a C++ integration have survived real maintenance rather than demo-only development;
- source/API/epoch migration policy, support tiers, licensing/patent terms, governance, and succession are clear enough for an organization to estimate adoption risk;
- every admitted feature has formatter, compiler-service, debugger, docs, tests, cost model, all-backend, migration, and native-boundary coverage.

Until then, epochs/pre-1.0 releases may deliberately break with an automatic migration where practical. Stability is earned evidence, not a date.

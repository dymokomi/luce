# Language Conformance Ledger

The target is the complete 1.0 contract in
[`docs/language/1.0.md`](../docs/language/1.0.md). This is the authoritative
progress ledger for the source-to-QBE baseline. A parser-valid spelling is not
an implemented language feature, and a backend encoding that has no semantic
oracle is not proof of correctness.

## How a capability closes

Every applicable capability must have all of these before its row becomes
complete:

1. positive and negative tokenizer/parser fixtures;
2. positive semantic resolution and stable rejection diagnostics in HIR;
3. independent HIR execution for observable semantics;
4. target-neutral canonical MIR lowering, verification, and MIR execution;
5. optimized MIR compiled and run through the real QBE 1.3 product path;
6. a focused `.luc` example when the capability can be demonstrated by a
   program, with its status/output checked automatically.

`complete` means every normative rule in the cited section has that evidence.
`partial` names the first known missing stage. `syntax` means the spelling and
its malformed forms are covered, but semantic implementation has not begun.
`n/a` is used only where a layer genuinely cannot apply, such as QBE execution
for source-encoding rejection. Wasm is useful additional evidence and is not a
column because it does not determine stage-1 completion.

## Current 1.0 audit

| Spec | Capability | Frontend | HIR/oracle | MIR/oracle | QBE | Example | First open work |
| --- | --- | --- | --- | --- | --- | --- | --- |
| §3 | UTF-8 source, layout, comments, documentation, names, scope | complete | partial | n/a | n/a | partial | Generic-nominal and source-test scopes remain with those features. |
| §4 | Boolean, absence, numeric, character, string, byte, raw, formatted, triple, and collection literals | complete | complete | complete | complete | complete | Every normative literal rule and the width-explicit `math` special-value surface execute through both oracles and QBE/Wasm. |
| §5 | Scalar, composite, alias, inference, structural operations, and recursive type rules | complete | partial | partial | partial | partial | The S05 alias/inference/recursion/copying audit, restricted `mutable_slice`, explicit total-order contract, and task handles are complete; the remaining work belongs to the other partial rows. |
| §6 | Immutable/mutable bindings, assignment, initialization | complete | complete | complete | complete | complete | Every binding, tuple, copy/reference, checked-place, and definite-initialization rule has positive, negative, oracle, and artifact evidence. |
| §7 | Evaluation order, arithmetic, bits, comparisons, conversions, calls, indexing, and discarded values | complete | partial | partial | partial | partial | The S06 eager-order/operator audit is complete; named arithmetic-policy APIs remain in S30. |
| §8 | Functions, arguments/defaults, tuples, methods, mutation, recursion, and function values | complete | complete | complete | complete | complete | Exact direct/generic/function/closure callables, defaults, tuples, methods, mutation, and recursion execute through both oracles, QBE, and Wasm. |
| §9 | `if`, conditional binding, loops, exhaustive match, return, and `defer` | complete | complete | complete | complete | complete | Every branch, loop, match, return, and lexical-cleanup rule has stable negative and executable product evidence. |
| §10 | Structs, tuples, fixed arrays, enums, copying, visibility | complete | complete | complete | complete | complete | Every ordinary value-data rule has positive, negative, oracle, and artifact evidence; explicit native representation remains the §21 boundary concern. |
| §11 | Classes, identity, ARC, weak references, destruction | complete | complete | complete | complete | complete | Exact lifecycle semantics, weak edges, direct-cycle diagnostics, reentrancy advisories, opt-in SCC/location census, and explicit resource shutdown have oracle and product evidence. |
| §12 | Allocation, lists, maps, sets, slices, strings/bytes, arenas | complete | partial | partial | partial | partial | Lists, restricted mutable slices, insertion-ordered maps/sets, owned strings/bytes, and the affine internal formatting builder reach QBE and Wasm. Public builders/codecs and the remaining arena contract remain. |
| §13 | Optionals, recoverable failure, errors, traps, fatal termination, assertions | complete | partial | partial | partial | partial | Dynamic `trap(str)` and eager `assert(bool, str?)` reach both oracles and QBE/Wasm with no deferred cleanup on failure; closed operational summaries prove assertion conditions effect-free. Error context, fatal termination, and an exhaustive source-location/stack diagnostic audit remain. |
| §14 | Lambdas, closures, captures, escape, cycles, sendability | complete | complete | complete | complete | complete | The executable capture/lifting/storage/direct-cycle matrix, shared-cell advisory, and recursive worker-boundary sendability proof are complete. |
| §15 | Generic declarations, constraints, monomorphization, limits | complete | complete | complete | complete | complete | Abstract checking, specialization, limits/accounting, retained typed bodies, and dependency-origin package specialization are complete through QBE. |
| §16 | Interfaces, conformance, static use, interface values | complete | complete | complete | complete | complete | Every declaration, conformance, static-dispatch, existential, mutation, fallibility, and deliberate no-downcast rule has positive/negative proof. `luce explain` reports boxing, dynamic calls, and value-versus-class payload semantics. |
| §17 | Iteration, equality, hashing, ordering, formatting, encoding protocols | complete | partial | partial | partial | partial | Iteration, closed derived equality/hashability, cycle-aware collection equality, immutable structural hashing, explicit `Comparable`, and closed `Display` formatting execute; encoding remains. |
| §18 | Effects are deliberately absent | complete | complete | n/a | n/a | n/a | Keep exclusion tests and prevent effect syntax from entering the grammar. |
| §19 | Isolated workers, transfer, cancellation, task lifetime | complete | complete | complete | complete | complete | Named workers, recursive graph-copy transfer, frozen snapshots, cached observation, ordered `wait_all`, cancellation, traps/errors, nested workers, and lexical supervision execute through both oracles and native QBE. |
| §20 | Modules, imports, visibility, entry points, and compile-time constants | complete | complete | complete | complete | complete | Package-relative module identity, one declaration import namespace, unused-import and shortest-cycle diagnostics, recursive public-API visibility, the complete stored-constant subset, and the exact process-entry contract execute through QBE and Wasm. Manifest discovery and platform variation are explicitly post-1.0. |
| §21 | C/native imports and exports, ownership/nullability, raw native source | complete | partial | partial | partial | partial | Scalar/handle/nested external and exported structs, strings, borrowed dense lists, anonymous `foreign` data pointers, incoming bare/nullable cfunc pointers, and explicit inbound-memory copies retain target-neutral HIR/MIR shape, with real QBE/C proofs. Standalone C11 export products execute through the CLI. Clang emits versioned FIIR plus generated nominal fundamental, scalar-typedef, sign-magnitude enum, logical record, and direct typedef-backed incomplete-record handle carriers. Constant-only anonymous enums, Clang-evaluated header-local scalar/enum objects, and explicitly selected scalar macros become typed constants. Exact floating encodings preserve finite values, infinities, and signed zero while canonicalizing unobservable NaN payloads. Declaration-only external scalar and enumeration objects stay live behind generated fixed-carrier readers and mutable writers; const and volatile remain C-product facts. Direct opaque pointers retain Clang-proven nullability and pointee mutability, while a separate reviewed recipe records ownership, call borrows, returned-borrow anchors, disposers, and integer-status failures. Generated safe owner/borrow wrappers execute through both semantic oracles and linked QBE/C; only the adapter sees typed C pointers. Checked C adapters compile, link, run, assert exact representations and constant semantics, reject target-range overflow and undeclared enum values, and keep target facts out of HIR/MIR. IEEE binary16 `_Float16` remains semantic `f16` through an exact private `f32` adapter carrier. Other extended floats, broader pointer/array/callback declarations, unions/bit-fields, richer storage, and callback runtime/lifetime rules remain. |
| §22 | Compiler/runtime versus standard-library boundary | complete | partial | partial | partial | partial | `math` and the inbound-memory `c` wrappers are ordinary compiler-supplied source with explicit provenance; automatic standard-module loading and the remaining example-facing modules remain. |
| §23 | Semantic pipeline and runtime services | complete | partial | partial | partial | partial | Source traces/fatal outcomes, source-test integration of resource reports, self-hosting, and the final full-language QBE artifact proof remain. Backend portfolio, artifact, ABI, profile, and cache policy are explicitly post-1.0. |
| §24 | First-party command, diagnostics, formatter, and source `test` declarations | complete | partial | partial | n/a | partial | Structured non-fatal analysis reports reach check/run/build and the CLI; source tests, formatter, the required command modes, and the remaining stable diagnostic contract remain. Persistent service, docs, observability, budgets, and release gates are explicitly post-1.0. |
| §25 | Deliberate exclusions | partial | partial | n/a | n/a | partial | Map every exclusion to a stable negative fixture; do not infer coverage from lack of implementation. |
| §28 | Compact declarations/statements/expressions/operators/grammar reference | complete | partial | partial | partial | partial | This surface closes only when the semantic rows above close. |

The evidence for frontend completeness is concentrated in
`tests/compiler/frontend/tokenizer_test.luc` and
`tests/compiler/frontend/parser_test.luc`. HIR acceptance/rejection lives in
`tests/compiler/hir/generator_test.luc`; lowering and verification live under
`tests/compiler/mir/`; semantic and artifact agreement lives in
`tests/compiler/differential_test.luc` and `tests/compiler/backends/qbe_test.luc`.
As implementation advances, broad `partial` rows are split until every
normative rule has a named positive and negative fixture. No broad row may be
promoted merely because its common case works.

## Exact open stage-1 checklist

This is the resumption list for the source-to-QBE baseline. Each row is one
bounded closure unit: it either names the exact missing behavior or names the
specific subsection whose already-broad implementation still needs a complete
positive/negative audit. A row closes only under the six gates above. The
identifiers are stable planning labels, not diagnostic codes.

| ID | Spec | Closure unit | Current state / dependency |
| --- | --- | --- | --- |
| S01 | §3.4, §24.4 | Canonical naming/style diagnostics and formatter ownership | Formatter not implemented. |
| S02 | §3.5 | Exhaustive module/member/local/import/capture/test namespace and lifetime matrix | Ordinary scopes are implemented; source-test scopes wait for S26. |
| S12 | §§12.7–12.8, §22.2 | Public text/bytes builders, UTF codecs, parsing/formatting, arenas/pools/generational handles | Internal affine builder and owned text/bytes substrate are complete. **Written in Base** (plan.md §5.1, B6) after the runtime port; not extended in safe Luce. |
| S13 | §§13.3–13.7 | Error context/source traces, complete trap provenance, structured fatal outcomes, and stack-budget reporting | Error data/control and dynamic traps execute; trace/fatal runtime path is incomplete. |
| S14 | §13.8 | Prove assertion conditions effect-free from operational summaries | Complete: target-neutral closed summaries accept pure recursion/reads and report the exact path to allocation, mutation, I/O, foreign access, dynamic calls, or termination. |
| S15 | §14.4 | Closure/value sendability and all worker-boundary capture rejections | Complete: recursively sendable values and immutable collection graphs cross tasks; mutable/reference/callable/borrowed capabilities and closures are rejected on exact transfer paths. |
| S16 | §15 | Final generic rule audit and serialized typed bodies in package artifacts | Complete: typed artifacts compose and dependency-origin generics specialize without source replay. |
| S17 | §16 | Final interface rule audit, including no-downcast exclusions and every static/existential adaptation | Complete: one declaration-call placement protocol reaches typed packages, both oracles, QBE, and Wasm; exclusions and interface-cost reporting are covered. |
| S18 | §17.2 | Explicit `Comparable` conformance and total-order `compare` contract | Complete: exact-Self constraints/conformances specialize to ordinary calls; existential/argument/synthesis exclusions, typed dependencies, both oracles, QBE, and Wasm are covered. |
| S19 | §§19.1–19.5 | Workers, `task[T]`, graph-copy transfer, sendability, `wait_all`, cancellation, and supervised lifetime | Complete through both semantic oracles and native QBE; Wasm rejects isolated tasks explicitly under WASI preview 1. |
| S20 | §§20.1–20.5 | Module-cycle, import-use, public-signature, constant-expression, and complete entry-point diagnostics | Complete: exact root-package selection, retained `slice[str]` arguments, fallible status handling, typed-package identity, and backend-owned QBE/WASI host argument materialization are covered. |
| S21 | §§21.1–21.5, §21.12, §§21.14–21.15 | FIIR, C import and wrapper/thunk generation, recipes, provenance, and support diagnostics | Export-side C11 products are complete. Import-side C `_Bool`, exact IEEE binary16 `_Float16`, exact IEEE binary32 `float`, exact IEEE binary64 `double`/`long double`, every fundamental C integer family, scalar typedef chains, named/typedef-backed C enums, constant-only anonymous enums, Clang-evaluated header-local scalar/enum objects, explicitly selected scalar macros, declaration-only external fundamental-scalar/enumeration objects, plain nested records, and direct pointers to typedef-backed incomplete records pass Clang facts → validated/serialized FIIR → generated raw/C products → both semantic oracles and real QBE/C execution. Scalar families, typedef names, enums, and opaque handles remain nominal; `_Float16` uses an exact private f32 carrier; integer/enum constants use target-neutral sign-magnitude carriers while Boolean and floating constants retain semantic kind and exact IEEE bits; external storage uses fixed-carrier accessors; records use logical fields. FIIR 2 separates Clang-proven nullability/mutability from reviewed recipe ownership and lifetime facts. The closed first recipe vocabulary validates borrowed-for-call parameters, owned results with exact disposers, returned borrows anchored to an input owner, and C-integer status failures; `luce bind --recipe/--safe` generates ordinary owner/borrow/failure Luce, and semantic-oracle plus linked QBE/C tests exercise absence, success, failure, explicit close, automatic deinit, and use-after-close trapping. Layout and typed C pointers stay in FIIR/C. Extended `long double` fails rather than narrowing. Alternate primitive/typedef targets, enum flags, object qualifiers, record layout facts, and handle qualifiers preserve identical Luce semantics. Direct tagged-record pointers, pointer typedefs, multiple indirection/out handles, pointer-plus-count arrays/strings, imported callbacks, unions/bit-fields, aggregate/atomic/thread-local objects, pointer/array/string macros, typed variadics, extended floating carriers, support tiers, and regeneration diagnostics remain; C++ §§21.6–21.11 and §21.13 are deferred past 1.0. **Frozen at this baseline** (plan.md §5.3): the remaining vocabulary closes in the Base binder, not in FIIR. |
| S22 | §21.16 | Raw memory copy/take verbs and the generated `_Float16` shim | Complete: `c.bytes_at`, `c.cstring_at`, and `c.take_str` execute through both semantic oracles and real linked QBE/C; direct and nested generated `_Float16` bindings preserve public f16 through an exact private f32 carrier. Automatic standard-module product loading remains in S30. |
| S23 | §21.17 | Resolve the field-only grammar/prose conflict, then close the remaining extern-struct matrix | Scalar/handle/`foreign`/nested/cfunc fields and pointer crossings execute; the syntax-versus-prose decision remains. Frozen with S21; the contract is settled by Base `extern struct` (base.md §17.1). |
| S24 | §21.19 | Enforce the callback thread/runtime contract and close the remaining C-export callback matrix | Raw incoming and nullable `cfunc` pointers, capture-free names/lambdas, null invocation, and generated C adapters execute. Frozen with S21; the contract is settled by Base function pointers and the §18.7 callback rule. |
| S25 | §21.5 | Exported C records remain ordinary semantic values and become by-value aggregates only at the backend | Complete: nested scalar/fixed-enum/exported-record shapes survive typed packages and imports, fieldwise C adapters remain target-neutral in MIR, and real QBE/C execution proves arguments and results in both directions. Aggregate-bearing indirect calls are emitted; the public callback contract remains S24. The native CLI emits a standalone C11 header and a versioned ABI report validated against optimized MIR. |
| S26 | §§24.2, 24.5 | Source `test` HIR/MIR/registry, isolated execution, test-only scope/import pruning, CLI selection/reporting, and `testing.expect_trap` | Parser surface only. |
| S27 | §§24.2–24.4 | Required first-party command modes, complete structured diagnostic shape/fixes, and canonical formatter | `check`, `run`, and `build` have a working core; remaining modes/contracts are absent. |
| S28 | §25 | Stable negative fixtures for every deliberate exclusion | Representative tokenizer/parser exclusions exist; exhaustive mapping remains. |
| S29 | §23.1 | Compile the compiler with stage-1, compare observable behavior, and preserve the frozen bootstrap chain | Stage-0 0.30 builds and tests the tree; self-hosting proof remains. Depends on the Base standard library (B6). |
| S30 | §§22–23 | Finish the standard modules and runtime services required by the proving examples, then run the full corpus through QBE | Core runtime storage/collections/text/classes/tasks and explicit standard-source provenance are executable; automatic standard-module loading, public codecs, host libraries, and source-test resource-report integration remain. **Written in Base** (B6); automatic loading discovers the installed toolchain. |

## Luce Base checklist

[`docs/language/base.md`](../docs/language/base.md) is the second half of the
stage-1 checkpoint (plan.md §5.1). Each row closes under the same six gates,
with `asm` programs proved by the compiled backends only (base.md §8.9), and
each Base-only rule also needs the full-Luce negative fixture where the two
profiles differ (base.md §23).

| ID | Spec | Closure unit | Current state / dependency |
| --- | --- | --- | --- |
| B0 | plan.md §5.0 | Profile layout: `profile.luc`, `profiles/full/` and `profiles/base/`, full-only code moved out of the shared stages, folder rules in `test.sh` | Complete (2026-09-03): the six stages dispatch to `profiles/full/{hir,mir,backends}/` through host interfaces, `test.sh` enforces both folder rules, `tests/compiler/profiles/` mirrors the layout, and every example's QBE IL is byte-identical to the pre-split tree. No behavior change. |
| B1 | base.md §§1–4, 5.1–5.2, 7.2–7.5, 16.2, 19.1 | The Base profile: suffix selection, `.lucn` rename, Base tokens and reserved words, tier rejections, freestanding reachability, `usize`/`isize`, implicit widening, C division, the cast family | Partial (2026-09-03): `.lucb` selects the Base profile, the audited tier is `.lucn`, a Base module imports only Base modules, every runtime-backed spelling (classes, collections and their literals, `new`, `spawn`, `wait_all`, `Weak`, capturing lambdas, block closures) is refused naming the tier, and a Base package is checked freestanding after lowering; `examples/base/hello.lucb` checks, runs, and builds. The Base spellings (`+% -% *% +| -| *| +? -? *?` and their augmented forms, `---`, `...`, `@`) and the Base reserved words are admitted by the one lexer only in `.lucb` modules and named in a diagnostic elsewhere; their grammar lands with the slices that give them meaning. `usize`/`isize` resolve only in `.lucb` modules as one widthless canonical type that the layout widens (32 bits in the oracle's 4-byte rules and on wasm32, 64 under QBE), with constants that fit only the wider target refused by name where the width is known; `examples/base/pointer_width.lucb` checks, runs, and builds. `sizeof`/`alignof`/`offsetof` check as `usize` and travel through HIR and MIR as a symbolic `LayoutConstant` that each backend, the reference interpreter included, folds from its own layout rules. `//` and `%` truncate toward zero in `.lucb` modules and an integer widens implicitly to a wider one of the same signedness, including to and from the pointer width through the canonical `widen` conversion; `examples/base/c_arithmetic.lucb` checks, runs, and builds. Open: the wrapping/saturating/checked operator family, the `(T)x` cast family, and folding `usize` constants into array lengths and module-level asserts. |
| B2 | base.md §§5.3–5.5, 6.6, 7.7, 8.3 | Pointers, qualifiers, the null niche, spans, `str` views, `cstr`, address-of and the escape rule, pointer arithmetic and ordering, `for x in &items` | Depends on B1. |
| B3 | base.md §§6.1–6.5, 8.4–8.8, 10.3–10.4, 11.7, 12 | Zero values, `---`, globals, unions, integer-backed enums, `packed`/`align`, `new`/`alloc`/`free`/`with`/`in`, `Allocator`, `errdefer`, labels, guards | Depends on B2. |
| B4 | base.md §§8.9, 9.1–9.8, 14.3, 15, 17 | Interface views, atomics, `volatile`, `asm`, attributes, `extern`, variadic C calls, `fmt`, `location()`, `export` | Depends on B3. |
| B5 | base.md §18.13 | The sealed runtime as a Base package with two `.lucn` intrinsics, passing the complete differential corpus | Depends on B4. |
| B6 | base.md §§16.5–16.6, 18 | The standard library in Base with the §18 crossing rules and `--costs`; automatic standard-module loading | Depends on B5; closes S12 and S30. |

The following spec sections do **not** block language-spec completion because the 1.0
document explicitly defers them: §§20.6–20.8, 23.2–23.3, 23.5–23.8, 24.1,
and 24.6–24.9. This prevents post-1.0 package, backend-portfolio, artifact,
service, documentation, and release-policy work from silently expanding the
language baseline. Separately requested engineering gates, including generated
programs and fuzzing, remain in `docs/compiler/plan.md` and still precede the
final architecture audit.

## Current type-and-binding evidence

The closed S05 surface is resolved before MIR: aliases disappear into their
underlying type identity, and every assignment destination is one checked HIR
place. MIR therefore receives neither alias spelling nor source lvalue syntax.

| §§5–6 rule | Frontend/HIR | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Aliases are non-generic, transparent, order-independent, and non-recursive; qualified access enforces visibility | one lazily resolved identity and recursion guard | alias spelling erased | unchanged, plus Wasm | `types_and_bindings.luc` and cross-module fixtures | complete |
| Inference is local to private bindings, arguments, returns, collections, `none`, and enum shorthand; public constants spell their type | exact expected/inferred `TypeId`; stable missing-context/API diagnostics | concrete types only | yes, plus Wasm | `types_and_bindings.luc`, generic examples | complete |
| Recursive value layouts are rejected; class and collection edges provide explicit indirection | nominal cycle proof and focused negatives | finite concrete shapes | yes, plus Wasm | `types_and_bindings.luc`, class/collection examples | complete |
| `let`, `var`, immutable parameters, and tuple binding preserve one RHS evaluation and left-to-right initialization | one hidden tuple value and resolved local symbols | typed slots and ordered stores | yes, plus Wasm | `types_and_bindings.luc` | complete |
| Struct/tuple/array/enum values copy; class/closure/collection references share identity and ownership | typed value/reference operations | structural copies versus retain/release | yes, plus Wasm | `types_and_bindings.luc` and ownership examples | complete |
| A field/index destination is checked and evaluated once; value roots/fields require mutation authority while shared storage remains mutable through `let` and parameters | one target-neutral `PlaceAssignment` path with exact diagnostics | one address walk; reference parameters remain values | yes, plus Wasm | `types_and_bindings.luc` and focused list/map/aggregate fixtures | complete |
| Struct/class initialization assigns every field once before reads, calls, escape, loops, or successful exit | whole-program three-state flow proof | initialized ownership-bearing storage | yes, plus Wasm | class/generic construction examples and analyzer negatives | complete |

## Current value-data-modeling evidence

The closed §10 surface ends before physical representation. HIR retains
nominal meaning and semantic declaration order; canonical MIR retains typed
products and sums; only a backend or explicit native boundary chooses offsets,
alignment, and ABI representation.

| §10 rule | Frontend/HIR | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Struct fields use `let`/`var`, private-by-default visibility, declaration order, defaults, and a synthesized memberwise initializer only when no custom `init` exists | exact fields, receiver kinds, argument placement, visibility, and whole-program definite initialization | structural fields, caller-owned value storage, and ownership initialization | yes, plus Wasm | `types_and_bindings.luc`, generic construction examples | complete |
| Value mutation requires a mutable place; immutable transformations are named methods; inheritance and object spread are absent | stable mutation diagnostics and parser exclusions | one checked address walk | yes, plus Wasm | `types_and_bindings.luc`, `generic_methods.luc` | complete |
| Tuples are anonymous positional values with destructuring, no named projections, and no one-element form | exact arity/type diagnostics and parser exclusions | structural aggregate copy | yes, plus Wasm | `types_and_bindings.luc`, `expressions_and_calls.luc` | complete |
| `array[T, N]` has one nonnegative literal length in its type, copies elementwise, and converts to `slice[T]` only by an owned snapshot | no user value parameter or implicit-view path; checked indexing/slicing | canonical arrays and scalable typed snapshot loop | yes, plus Wasm | `stage0_sort.luc`, `array_slices.luc` | complete |
| Enums are closed sums with contextual/named construction and exhaustive payload matching; no union, ordinal, discriminator, or unchecked payload projection is exposed | exact construction/match/recursion/visibility diagnostics | ordinary tags scale to the smallest sufficient target-neutral unsigned scalar and are verified; optionals retain their specified `u8` shape | generated 257-case fixture executes, plus Wasm encoding | `generic_enums.luc`, `language_tour.luc` | complete |
| Struct, tuple, array, and enum assignment is value copy; embedded references retain their ordinary shallow shared identity | independent HIR value/reference operations | structural copy versus explicit retain/release | yes, plus Wasm | `types_and_bindings.luc` | complete |
| Equality and hashing derive only when every stored component supports them; ordinary source exposes neither operator overloads nor layout attributes | closed `Equatable`/`Hashable` proof and exclusions | one structural equality/hash expansion | yes, plus Wasm | `hashing.luc` | complete |
| `pub` controls source access, including synthesized/custom initialization and enum payloads, without promising memory layout | cross-module positive and stable private-access diagnostics | no source visibility or platform layout survives | unchanged | cross-module fixtures | complete; explicit C representation is tracked in §21 |

## Current expression-and-call evidence

The closed S06 surface keeps source evaluation order in resolved HIR operand
runs. MIR consumes those runs once and places values into declaration slots
only after evaluation; a backend therefore receives neither argument labels
nor permission to choose an order.

| §§7–8 rule | Frontend/HIR | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Receiver, argument, literal element, interpolation field, binary operand, assignment RHS, and constructor argument order | source-ordered nodes with declaration-slot indexes | source-ordered evaluation followed by slot placement | yes, plus Wasm | `expressions_and_calls.luc` and output fixtures | complete |
| Checked integer/IEEE arithmetic, floor division/remainder, bit operations, short-circuit logic, comparisons, identity, and conditional expressions | closed typed operations and stable domain diagnostics | typed operations, guards, and structured results | yes, plus Wasm | `operators_and_literals.luc`, `numeric_conversions.luc`, and trapping corpus | complete except named policy APIs in S30 |
| Positional-before-named calls, arbitrary named order, duplicates/unknowns/omissions, and trailing pure defaults | one shared direct-call placement contract; exact diagnostics | declaration-order operands after source-order evaluation | yes, plus Wasm | `expressions_and_calls.luc` and focused call fixtures | complete |
| Same-module, qualified-import, and selective-import constants in ordinary defaults | post-import default-resolution pass; body locals absent | constants embedded before lowering | yes, plus Wasm | cross-module differential fixture | complete |
| Tuples/results, exact callable values, infallible lift, methods/type functions, value mutation/self replacement, and recursion | resolved callable identity and receiver kind | canonical direct/closure calls and caller-owned value mutation | yes, plus Wasm | `expressions_and_calls.luc`, function/closure/generic examples | complete |
| Non-unit public results are explicit; every reachable path returns; nested named functions and overloads are absent | declaration/flow diagnostics | only complete concrete functions lower | n/a | focused parser/HIR negatives | complete |

## Current control-flow evidence

The closed S08 surface retains structured control and lexical cleanup in HIR.
MIR lowers those facts once into regions and explicit exit edges; neither
backend reconstructs source scope, range semantics, or deferred actions.

| §§9.1–9.5, §§9.7–9.8 rule | Frontend/HIR | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Boolean `if`/`elif` and `while`, lexical branch scope, and optional-only `if let` payload scope | exact typed branches and stable rejections | structured regions | yes, plus Wasm | `conditional_binding.luc` and control-flow fixtures | complete |
| Conditional expressions choose one symmetric type through equality, bottom, optional injection, an established interface, or function-fallibility lift | one explicit common `TypeId`; ambiguous/missing context rejected | typed region result | yes, plus Wasm | `conditional_binding.luc` and differential joins | complete |
| Built-in integer ranges ascend by one, descending bounds are empty, and a closed maximum stops after yielding it | exact `range[T]` and immutable loop symbol | typed range loop with overflow-free closed termination | yes, plus Wasm | `iteration.luc` and range corpus | complete |
| Ordinary and fallible protocol iteration keep item/end/error distinct; `break` and `continue` target the innermost loop | resolved interface operation and lexical loop depth | structured branch depths and explicit failure edge | yes, plus Wasm | `iteration.luc` | complete |
| Bare/unit and value returns, including every closed branch and terminating `error`/`trap`/`never` path | structural completion proof and exact diagnostics | signature-checked returns | yes, plus Wasm | control-flow and trapping corpus | complete |
| Deferred unit calls capture receiver/arguments at registration, execute LIFO on fallthrough/return/loop exit/error, and do not run after traps | hidden typed captures; failing cleanup rejected unless wrapped | cleanup duplicated on every ordinary lexical exit | yes, plus Wasm | `iteration.luc`, list/class examples, and defer corpus | complete |

## Current `match` evidence

`match` remains structured HIR and lowers once to ordinary canonical MIR
control. Exhaustiveness is a source semantic fact; neither MIR nor a backend
receives a pattern-coverage representation.

| §9.6 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Enum, optional, Boolean, numeric, character, and string patterns; alternatives and payload scope | yes | existing structured control | yes, plus Wasm | `language_tour.luc` and differential corpus | complete |
| Statement suites and contextual expression results evaluate one subject once | yes | one lowered subject value | yes, plus Wasm | `language_tour.luc` and differential corpus | complete |
| Missing enum/optional/Boolean cases and scalar `_` requirements | stable diagnostics | n/a | n/a | focused HIR fixtures | complete |
| Duplicate literals/cases, overlapping ranges, and arms after complete coverage | stable diagnostics | n/a | n/a | focused HIR fixtures | complete |
| Complete signed/unsigned integer and Unicode-scalar domains proven from adjacent literals/ranges | yes, without enumeration | unchanged | yes, plus Wasm | differential finite-domain fixtures | complete |
| Enum `_` remains legal but emits structured `L0901`; Boolean/optional `_` stays quiet | structured advisory | n/a | n/a | focused analysis fixtures | complete |

## Current `never` evidence

`never` has no runtime representation. HIR preserves contextual bottom flow
and eager source order; MIR preserves only the callable's inability to return
successfully. Neither stage introduces a target or platform fact.

| §5.2/§8/§13 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Direct and fallible `never` results; exact function, closure, generic, and interface callables | yes | yes | yes, plus Wasm | `traps.luc` and focused signature fixtures | complete |
| Bottom coercion in returns, conditionals, matches, optional fallback, and short-circuit flow | yes | yes | yes, plus Wasm | differential control-flow corpus | complete |
| Eager prefix runs once; unreachable outer/later operands do not run | yes | yes | yes, exact output | `traps.luc` and differential trapping corpus | complete |
| Direct, nested, generic-substituted, callable-parameter, and native-pointee storage rejection | stable diagnostics | n/a | n/a | focused HIR negative fixtures | complete |
| No successful MIR value/return; malformed signatures and calls rejected | n/a | yes | yes, plus Wasm | verifier/backend fixtures | complete |

## Current numeric-construction evidence

The broad §7 row remains partial. Explicit construction now has one resolved
HIR identity and one canonical MIR conversion family; width, signedness, and
IEEE rounding remain semantic facts while only instruction selection belongs
to QBE or Wasm.

| §7.5 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Every signed/unsigned integer pair checks the destination interval | yes | yes | yes, plus Wasm | `numeric_conversions.luc` and differential boundaries | complete |
| Integer-to-float rounds to nearest, ties to even | yes | yes | yes, plus Wasm | `numeric_conversions.luc` | complete for f16/f32/f64 |
| Float-to-integer truncates toward zero and traps NaN/infinity/out-of-range | yes | yes | yes, plus Wasm | `numeric_conversions.luc` and trapping corpus | complete for f16/f32/f64 |
| f16/f32/f64 widening and checked narrowing; contextual literals and per-operation width rounding | yes | yes | yes, plus Wasm | `numeric_conversions.luc` | complete |
| f16 canonical bits, structural hash, display, and two-byte aggregate storage | yes | yes | yes, plus Wasm | `numeric_conversions.luc` and differential corpus | complete |

## Current fixed-array slice evidence

An array is inline value storage, while an unrestricted `slice[T]` may escape.
The conversion therefore snapshots values into the existing immutable owned
slice protocol; it never leaks a frame address or introduces target layout.

| §10.4/§12.6 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Explicit partial/full slicing with checked `u64` bounds | yes | yes | yes, plus Wasm | `array_slices.luc` | complete |
| Source, lower, and upper evaluate once from left to right | yes | yes | yes | differential output fixture | complete |
| Mutation after capture cannot alter the value snapshot | yes | yes | yes, plus Wasm | `array_slices.luc` | complete |
| A slice returned after inline array destruction retains scalar and managed elements | yes | yes | yes, plus Wasm | `array_slices.luc` | complete |
| Copy loop and MIR size are independent of `N`; selected capacity reserves once | n/a | yes | yes | lowerer inspection | complete |

## Current closure evidence

Core §14 has one target-neutral managed representation and its executable
conversion/storage/diagnostic matrix is complete. The broad row stays partial
only for worker sendability.

| §14 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Capture-free expression/block closures become allocation-free function values | yes | yes | yes, plus Wasm | `closures.luc` and differential corpus | complete |
| Default immutable and explicit `copy` captures snapshot at formation in source order | yes | yes | yes, plus Wasm | `closures.luc` | complete |
| Captured `var` is one shared ARC cell visible to the scope and every closure | yes, plus structured `L1401` advisory | yes | yes, plus Wasm | `closures.luc` | complete |
| Nested environments escape without backend facts in HIR/MIR | yes | yes | yes, plus Wasm | `closures.luc` | complete |
| Weak class capture does not retain and promotes to an owned optional | yes | yes | yes, plus Wasm | `closures.luc` | complete for named locals and `weak self` |
| Fallible closures and infallible-to-fallible function lift | yes | yes | yes, plus Wasm | `closures.luc` and differential corpus | complete |
| Closure ownership in fields/collections and direct stored strong-cycle diagnosis | yes | yes | yes, plus Wasm | `closures.luc` and focused negative fixtures | complete |
| Closures cannot cross worker boundaries | syntax | n/a | n/a | worker corpus pending | opens with workers |

## Current `list[T]` evidence

The broad §12 row remains partial. This smaller matrix prevents the first
working list path from being mistaken for the complete §12.4 contract.

| §12.4 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Reference identity via `is`/`is not`; `let` prevents rebinding, not mutation | yes | yes | yes | `lists.luc` | complete for current operations |
| Contextual/inferred literals, empty construction, left-to-right elements | yes | yes | yes | `lists.luc` | complete |
| `length`, checked get/set, `append` | yes | yes | yes, including bounds trap | `lists.luc` | complete |
| Value, aggregate, and collection-recursive elements across growth/reallocation | yes | yes | yes | `lists.luc` | complete |
| `insert`, `remove_at`, `clear`, `reserve`; operands before mutation | yes | yes | yes, including bounds traps | `lists.luc` | complete |
| Shallow `copy` with independent collection identity/storage | yes | yes | yes | `lists.luc` | complete |
| Shallow `+` concatenation with fresh identity, ordered operands/elements, and independent slots | yes | yes | yes | `lists.luc` | complete |
| Immutable snapshot slicing | yes | yes | yes, including bounds traps | `lists.luc` | complete for lists |
| Ordered iteration; nested reads; alias-wide shape mutation trap; cleanup on exhaustion/continue/break/return/error | yes | yes | yes, including mutation traps | `lists.luc` | complete for built-in lists |
| Typed storage reclamation and allocator block reuse | runtime HIR | yes | yes, real exhaustion/reuse gate | internal runtime fixture | storage substrate complete |
| Recursive ARC of list identities, shared buffers, slices, and managed elements; last-owner reclamation | semantic value lifetime | yes | yes, plus Wasm | `lists.luc` | complete |
| Ordered content `==`/`!=`, identity fast path, recursive structs, self/deep cycles, scalar/shape mismatch, and alias-topology independence | yes | yes, including verified opaque pair transaction | yes, plus Wasm | `lists.luc` | complete |

## Current restricted mutable-slice evidence

`mutable_slice[T]` remains a distinct target-neutral HIR and MIR type until a
backend chooses the representation of the owner handle. It is a scoped
capability, not a second mutable collection or a general borrow system.

| §12.6 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Direct callback parameter with `length`, checked read, and replacement | yes | typed `MutableSlice(T)` and scoped operations | yes, plus Wasm | `mutable_slices.luc` | complete |
| Receiver then callback evaluated once; callback invoked synchronously | yes, observable order | one begin/call/end transaction | yes | differential fixtures | complete |
| Ordinary list aliases observe replacement | yes | owner identity retained | yes, plus Wasm | `mutable_slices.luc` | complete |
| Immutable snapshots made before or during access retain captured contents | copy-on-write oracle | typed retain callback at detach | yes, plus Wasm | `mutable_slices.luc` | complete |
| Shape change through any alias and out-of-bounds access trap | yes | runtime identity-wide barrier and checked address | yes | trapping corpus | complete |
| No construction, binding, field, payload, container, return, defer, or closure capture | exact diagnostics | non-storable type plus affine lifetime proof | n/a | focused HIR/MIR fixtures | complete |
| Explicitly scoped generic algorithms work; an ordinary generic `T` cannot erase the restriction | structural inference and specialization check | concrete scoped signature | yes | `mutable_slices.luc` | complete |
| Extern, exported C, and `cfunc` boundaries reject the view | exact boundary diagnostics | C verifier retains closed vocabulary | n/a | focused HIR fixtures | complete |
| Worker transfer cannot admit the non-storable type | exact rejection before HIR construction | no invalid worker MIR can be formed | n/a | focused sendability fixtures | complete |

## Current `map[K, V]` and `set[T]` evidence

Maps and sets share one target-neutral hash-table protocol. HIR and MIR retain
their semantic key/value types; only a backend supplies byte size, alignment,
pointer representation, and function descriptors to the sealed runtime.

| §5.6/§12.5 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Inferred/nonempty and explicit/empty construction; left-to-right evaluation | yes | yes | yes, plus Wasm | `maps_and_sets.luc` | complete |
| Reference identity, aliasing, insertion order, `length`, lookup/`contains` | yes | yes | yes, plus Wasm | `maps_and_sets.luc` | complete |
| Map replacement/insertion and optional-valued removal | yes | yes | yes, plus Wasm | `maps_and_sets.luc` | complete |
| Set deduplicating construction and boolean insertion/removal | yes | yes | yes, plus Wasm | `maps_and_sets.luc` | complete |
| `reserve`, `clear`, and shallow independent `copy` | yes | yes | yes, plus Wasm | `maps_and_sets.luc` | complete |
| Ordered iteration; value replacement allowed; alias-wide shape mutation trap | yes | yes | yes, including native/Wasm traps | `maps_and_sets.luc` | complete |
| Order-independent content equality and recursive map graphs | yes | yes, including opaque pair transaction | yes, plus Wasm | `maps_and_sets.luc` | complete |
| Exact ownership for keys/values across replace, remove, copy, clear, and final release | semantic value lifetime | typed generated callbacks | yes, plus Wasm | `maps_and_sets.luc` and focused lifecycle fixtures | complete |
| Private seeded buckets with dense insertion-order entries and collision-chain lookup | linear semantic oracle | typed hash candidates; generated equality | real runtime table | internal runtime/QBE fixtures | complete |
| Non-hashable key/element, arity/type, duplicate static key, compound assignment, and unknown-method diagnostics | stable rejection | n/a | n/a | focused HIR fixtures | complete |

## Current `bytes` evidence

`bytes` now has one source-level value model for static and dynamic storage.
The hidden owner is a target-neutral canonical MIR identity; only a backend
chooses its pointer representation and only the sealed runtime owns allocation
policy.

| §12.6/§7 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Literal value, `u64` length, checked `u64` indexing | yes | yes | yes, including bounds trap | `bytes.luc` and calculator/Brainfuck examples | complete |
| ASCII source, exact `\xNN`, and Unicode-scalar-to-UTF-8 escapes | yes | constants unchanged | yes, plus Wasm | `strings.luc` | complete |
| Immutable concatenation with fresh owned storage and left-to-right operands | yes | yes | yes, plus Wasm | `bytes.luc` | complete |
| Equality and unsigned lexicographic ordering | yes | yes | yes, plus Wasm | `bytes.luc` | complete |
| Content hashing | yes | yes | yes, plus Wasm | `hashing.luc` | complete for immutable bytes |
| Half-open O(1) slicing with checked bounds | yes | yes | yes, including traps | `bytes.luc` | complete for bytes |
| Slice returned across a temporary dynamic source's destruction retains that source owner | yes | yes, including forged-owner rejection | yes, plus Wasm execution | `bytes.luc` | complete |

## Current `str` evidence

`str` uses the same immutable owner/data/byte-length substrate as `bytes`, but
HIR keeps the language types and their legal operations distinct.

| §12.7/§7 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Valid UTF-8 literal, O(1) `byte_count`, O(n) scalar `length()` | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Ordinary and raw spellings with complete simple/Unicode escapes | yes | constants unchanged | yes, plus Wasm | `strings.luc` | complete |
| Triple spellings use closing-delimiter indentation, canonical LF, then ordinary/raw escape semantics | normalized before HIR | constants unchanged | yes, plus Wasm | `strings.luc` | complete |
| Immutable concatenation with escaping owned storage | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Unicode scalar iteration with ordinary loop exits | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Exact equality and deterministic scalar-value/prefix ordering | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Integer indexing and slicing remain unavailable | stable rejection | n/a | n/a | focused negative fixtures | complete |
| Content hashing | yes | yes | yes, plus Wasm | `hashing.luc` | complete for immutable strings |

## Current standard-iteration evidence

The broad §9 and §17 rows remain partial for unrelated pattern and protocol
families. The complete §9.4/§17.1 iteration contract has this narrower proof:

| §9.4/§17.1 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Compiler-known `Iterator[T]`/`Iterable[T]` and fallible counterparts have ordinary interface semantics | yes | normalized interface metadata | yes, plus Wasm | `iteration.luc` | complete |
| Concrete, constrained-generic, and existential `Iterable[T]` dispatch | yes | existing direct/dynamic calls | yes, plus Wasm | `iteration.luc` | complete |
| `try for` applies `try` to each fallible `next()` and distinguishes item/end/error | yes | existing optional and failure control | yes, plus Wasm | `iteration.luc` | complete |
| Source is evaluated once; one private mutable iterator drives repeated `next()` calls | yes | one owned slot and structured loop | yes | focused HIR/MIR tests | complete |
| One canonical element type per nominal and no implicit infallible/fallible conversion | stable declaration/use diagnostics | n/a | n/a | focused negative fixtures | complete |
| Iterator cleanup on exhaustion, `break`, `return`, and propagated error | observable class `deinit` | lexical ownership helper | yes, plus Wasm | `iteration.luc` | complete |

## Current IEEE special-value evidence

The §4.3 named surface is ordinary `math` module source. Imports resolve once
to existing constant symbols, after which the same typed initializer tree feeds
both oracles and the unchanged MIR/backend paths.

| §4.3/§20.2/§22.2 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| `nan`, positive infinity, and negative infinity have explicit f16/f32/f64 constants | exact public constant types | existing typed constants/conversions | yes, plus Wasm | `numeric_conversions.luc` | complete |
| Qualified and selective imports resolve to one program-wide constant symbol | one imported-value namespace; exact visibility diagnostics | import spelling erased | unchanged | focused multi-module fixtures | complete |
| NaN remains unordered and both infinity signs survive width conversion | yes | yes | yes, plus Wasm execution | `numeric_conversions.luc` | complete |
| No token, prelude name, HIR form, MIR form, runtime service, or backend special case is added | ordinary module source and `Reference` | unchanged | unchanged | architecture gate | complete |
| The shipped module path is an explicit package input until post-1.0 manifest/dependency discovery | pipeline source identity | n/a | n/a | product example gate | complete |

## Current collection-literal evidence

The §4.5 source contract has this closed proof:

| §4.5 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| `[...]` selects inferred/contextual `list[T]`, fixed `array[T, N]`, or immutable `slice[T]`, including contextual empties | one typed aggregate path | slices reuse list snapshot operations | yes, plus Wasm | `lists.luc`, `array_slices.luc` | complete |
| Map literals and explicit empty map/set construction retain one homogeneous key/value/element type | stable positive and negative resolution | existing hash protocol | yes, plus Wasm | `maps_and_sets.luc` | complete |
| Hidden heterogeneous and numeric-union collections, count/range errors, and `{}` are rejected | exact source diagnostics | n/a | n/a | focused frontend/HIR fixtures | complete |
| Every element, key, and value evaluates exactly once, left-to-right | observable effects | source order retained | captured native output | differential fixture | complete |
| Statically equal scalar, bytes, optional, tuple, and fixed-array map keys fail; computed duplicates replace in insertion order and sets deduplicate | recursive literal proof only | ordinary hash insertion | yes, plus Wasm | `maps_and_sets.luc` | complete |
| No literal-specific target fact or backend path exists | canonical typed HIR | unchanged target-neutral MIR | unchanged encoder | architecture gate | complete |

## Current structural hashing evidence

The broad §5/§12/§17 rows remain partial for ordering and encoding. The closed immutable hashing
family has this narrower proof:

| §10.6/§17.2 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| `Equatable`/`Hashable` are compiler-derived constraint-only markers | yes, including stable rejection | erased before MIR | n/a | `hashing.luc` | complete |
| Scalars, strings/bytes, ranges, arrays, optionals, tuples, structs, and enums derive recursively | yes | one canonical expansion | yes, plus Wasm | `hashing.luc` | complete |
| `hash(value)` evaluates its operand exactly once | yes, observable effect | yes | yes | differential fixture | complete |
| Equal values hash equally, including IEEE signed zero | yes | yes | yes, plus Wasm | `hashing.luc` | complete |
| IEEE scalar codes are exact; aggregate mixing remains in shared lowering | yes | `FloatBits` only | bit reinterpretation only | focused source tests | complete |
| Mutable reference collections/classes are not hashable keys | stable rejection | n/a | n/a | focused negative fixtures | complete |

## Current explicit-ordering evidence

`Comparable` is a source-level semantic contract, not an operator or backend
facility. Its implicit exact `Self` operand is bound by the generic parameter
or conforming nominal before ordinary interface substitution runs.

| §17.2 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Compiler-known `compare(self, other: Self) -> i64` uses negative/zero/positive ordering | one hidden owner-bound interface argument | concrete calls only | yes, plus Wasm | `comparable.luc` | complete |
| Conformance and implementation are explicit; no field-order synthesis or operator enabling occurs | exact conformance validation | no special ordering form | unchanged | focused HIR negatives | complete |
| Generic constraints dispatch statically through ordinary specialization, including generic nominal conformances | exact requirement identity and substitution | direct concrete call | yes, plus Wasm | `comparable.luc` | complete |
| `Comparable` has no source type arguments, existential value, associated type, reflection, or downcast path | stable rejection | n/a | n/a | focused HIR/parser fixtures | complete |
| Typed package reconstruction and dependency-origin conformances preserve the hidden same-type binding | byte-stable artifact/import remapping | concrete imported specialization | yes | package importer/codec fixtures | complete |

## Current formatted-string evidence

The broad §12/§17 rows remain partial for unrelated public-builder, ordering,
and encoding work. The complete interpolation contract has this narrower proof:

| §4.4/§17.3 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Fields evaluate exactly once from left to right; nesting preserves order | yes, observable effects | one linear affine builder | yes, plus Wasm | `formatted_strings.luc` | complete |
| Literal escapes, braces, Unicode, and triple normalization share source-boundary policy | yes | canonical text fragments only | yes, plus Wasm | focused decoder and example tests | complete |
| `str`, integer, float, `bool`, and `char` have closed builtin display | yes | typed display services | yes, plus Wasm | `formatted_strings.luc` | complete |
| Concrete, constrained-generic, and existential values use the same `Display` requirement | yes | existing direct/dynamic calls | yes, plus Wasm | `formatted_strings.luc` | complete |
| Integer extrema and width-specific shortest IEEE output are locale-independent | yes | exact `FloatBits`; malformed forms rejected | yes, plus Wasm | differential boundary corpus | complete |
| A builder is created and finished exactly once on every normal lexical path | n/a | focused affine proof and negative fixtures | yes | verifier tests | complete |

## Current generic evidence

Only §15.3 separate-compilation artifacts remain open. The source and
executable generic contract is closed rule by rule:

| §15 rule | HIR/oracle | MIR/verifier | QBE product | Evidence | State |
| --- | --- | --- | --- | --- | --- |
| Functions and struct/enum/class declarations use named type parameters without defaults | abstract checked signatures and stable duplicate/arity failures | concrete applications only | yes, plus Wasm | parser and HIR generic fixtures | complete |
| Calls infer locally or accept explicit types; nominal owner arguments and independently declared method arguments stay distinct | one structural inference transaction and memoized specialization identity | concrete direct calls | yes, plus Wasm | all six generic examples | complete |
| Interface intersections alone constrain abstract operations; unused bodies still check from written constraints | abstract requirement identity and exact conformance replay | concrete witnesses/calls | yes, plus Wasm | constrained-generic positives and negatives | complete |
| Concrete applications specialize functions, methods, initializers, lifecycle, conformances, defaults, recursion, and contextual function values | exact concrete `TypeId`/`SymbolId` graph | no generic forms cross the boundary | yes, plus Wasm | HIR/MIR/oracle/backend fixtures | complete |
| Infinite structural expansion and the package budget report complete source-parent paths and checking/codegen cost | deterministic front-end rejection/report | identity retained out of band through reachability | backend-owned exact emitted sizes | focused reporting fixtures | complete |
| Value parameters (except compiler-owned `array[T, N]`), variadics, higher kinds, packs, conditional/partial specialization, compile-time execution/reflection, variance, and associated types have no user grammar or semantic path | explicit parser/HIR exclusions | n/a | n/a | `test_generic_deliberate_limits_have_no_source_grammar` and nominal integer-argument rejection | complete |

## Reserved and contextual words

The 42 reserved words are:

```text
and as break catch class continue defer elif else enum export extern false
for from func if implements import in interface is let match mutating new none
not or pub recover return self spawn struct test true try type var weak while
```

`test_all_reserved_words_are_keywords` checks the exact lexer set.
`test_every_reserved_word_is_rejected_as_an_identifier` checks every word at
the shared declared-name boundary. `test_examples_cover_every_reserved_and_contextual_word`
then proves that every reserved word, plus contextual `c`, `copy`, `blocking`,
`out`, `cfunc`, `init`, and `deinit`, occurs in a complete parser-valid example
module. This is positive and negative coverage, not a comment/text search.

## Executable example inventory

| Example | Capability | Current highest proof |
| --- | --- | --- |
| `hello.luc` | Native entry and terminal output | Native QBE product smoke; output still needs an explicit captured assertion. |
| `semantic_core/` | Modules, calls, scalar control flow | HIR execution (`42`); QBE example gate pending. |
| `compiled_core/` | Checked arithmetic export | MIR/Wasm artifact; native QBE entry example pending. |
| `stage0_calculator.luc` | Byte scanning, recursion, tuples, failure | Native QBE execution/status. |
| `stage0_sort.luc` | Fixed arrays, copies, mutation, sorting | Native QBE execution/status. |
| `stage0_brainfuck.luc` | Bytes, nested flow/match, bounded interpreter | HIR, MIR, Wasm, and native QBE execution. |
| `function_values.luc` | Exact named function values and indirect calls | HIR, MIR, Wasm, and native QBE execution. |
| `generic_functions.luc` | Unconstrained generic functions, inference, defaults, recursion, contextual values, and memoized concrete instances | HIR and MIR oracles plus Wasm and native QBE execution. |
| `generic_methods.luc` | Owner/method scope separation, suffix inference and explicit arguments, owner-dependent constraints, defaults, recursion, mutation, and concrete/generic struct, class, and enum receivers | HIR and MIR oracles plus Wasm and native QBE execution. |
| `generic_construction.luc` | Custom generic-struct initialization and inferred, contextual, and explicit generic struct/class/enum type functions | HIR and MIR oracles plus Wasm and native QBE execution. |
| `constrained_generics.luc` | Generic interfaces, explicit and generic-struct conformance, static requirement dispatch, concrete existential witnesses, and infallible-to-fallible requirement adaptation | HIR and MIR oracles plus Wasm and native QBE execution. |
| `generic_enums.luc` | Inferred/explicit/contextual generic enum applications, concrete methods and conformances, matching, existential dispatch, distinct payload shapes, and named-payload evaluation order | HIR and MIR oracles plus Wasm and native QBE execution. |
| `generic_classes.luc` | Inferred/explicit/contextual generic class applications, distinct managed payload/lifecycle identities, weak recursive edges, fallible construction, conformances, and existential dispatch | HIR and MIR oracles plus Wasm and native QBE execution. |
| `types_and_bindings.luc` | Transparent aliases, local/contextual inference, tuple binding, value copies, shared reference identity, recursive indirection, and nested generic mutable places | HIR and MIR oracles plus Wasm and native QBE execution. |
| `interfaces.luc` | Generic existential conversion, struct/class/enum witness dispatch, named requirement-argument placement, nested ownership, value COW, class identity, and fallibility adaptation/propagation | HIR and MIR oracles plus Wasm and native QBE execution; `luce explain` asserts five boxes and five dynamic calls. |
| `iteration.luc` | Compiler-known infallible/fallible iteration through concrete, constrained-generic, and existential values, including lexical iterator cleanup | HIR and MIR oracles plus Wasm and native QBE execution. |
| `hashing.luc` | Compiler-derived structural constraints and execution-local hashing across immutable value families | HIR and MIR oracles plus Wasm and native QBE execution. |
| `closures.luc` | Managed copied/shared/weak captures, fallibility lifting, nested escape, collection/field ownership, and weak-self cycle breaking | HIR and MIR oracles plus Wasm and native QBE execution. |
| `cfunc_values.luc` | Exact C-callable values and adapters | HIR, MIR, Wasm, and native QBE execution. |
| `conditional_binding.luc` | Optional conditional binding, branch-only payload scope, and absent fallback | HIR, MIR, Wasm, and native QBE execution. |
| `numeric_conversions.luc` | Checked integer/float construction, binary32 contextual rounding, width conversion, and truncation | HIR and MIR oracles plus native QBE and Wasm execution. |
| `array_slices.luc` | Immutable owned snapshots from inline fixed arrays, including escaping managed elements | HIR and MIR oracles plus native QBE and Wasm execution. |
| `classes.luc` | Nominal identity, shared mutation, strong/weak ARC, first-class weak collections, borrowed deinitialization, failed construction, reverse destruction, and idempotent explicit resource shutdown | HIR and MIR oracles plus native QBE and Wasm execution; focused harness tests report dynamic SCCs and allocation sites. |
| `lists.luc` | Shared list identity, cycle-aware structural equality, shallow independent copies and concatenation, immutable snapshots, ordered invalidating iteration, checked access/shape mutation, aggregate elements, recursive ARC/reclamation, and growth | HIR and MIR oracles plus native QBE and Wasm execution, bounds and iteration traps. |
| `maps_and_sets.luc` | Insertion-ordered map/set identity, lookup, mutation, copy, recursive equality, managed ownership, and alias-wide iteration invalidation | HIR and MIR oracles plus native QBE and Wasm execution and mutation traps. |
| `tasks.luc` | Named isolated workers, immutable graph transfer, ordered/cached observation, and lexical supervision | HIR and MIR oracles plus native QBE execution; Wasm emits an explicit unsupported-target diagnostic. |
| `bytes.luc` | Immutable owned byte concatenation/comparison and ownership-retaining escaping slices | HIR and MIR oracles plus native QBE and Wasm execution. |
| `strings.luc` | Ordinary/raw/triple text and bytes, owned UTF-8 concatenation/discard, Unicode scalar length/iteration, and scalar-preserving ordering | HIR and MIR oracles plus native QBE and Wasm execution. |
| `formatted_strings.luc` | Builtin/concrete/generic/existential `Display`, nested affine construction, triples/braces, Unicode, integer extrema, and both IEEE widths | HIR and MIR oracles plus native QBE and Wasm execution. |
| `traps.luc` | Dynamic nonrecoverable diagnostics, `never` callables, nested eager-prefix termination, and skipped deferred cleanup | HIR and MIR oracles plus captured native QBE and Wasm failure diagnostics. |
| `assertions.luc` | Default/dynamic assertion messages, successful continuation, and failed no-cleanup termination | HIR and MIR oracles plus captured native QBE and Wasm failure diagnostics. |
| `language_tour.luc` | Broad 1.0 declaration/control/managed surface | Parser only; each section migrates into focused executable examples as it lands. |
| `operators_and_literals.luc` | Literal, collection, type, and operator surface | Parser only beyond the already executable scalar subset. |
| `checkout/` | Multi-module application shape | Parser only until collections/strings are complete. |
| `c_api.luc` | C export surface | HIR/MIR/QBE plus a real linked C round trip; the native CLI also emits its checked C11 header and ABI report. |
| `c_import/` | Generated C import architecture | C Boolean, integer, IEEE float/double, scalar typedef, named/typedef-backed enumeration values, constant-only anonymous-enum values, live external scalar/enumeration objects, simple/nested plain records, and direct nullable/non-null typedef-backed opaque-record pointers pass Clang/FIIR generation, HIR and MIR oracles, Wasm/QBE encoding, and an end-to-end `luce bind` → native build → linked C execution gate. Object access, record layout, and typed pointers remain Clang/FIIR/C-only. Remaining FIIR vocabulary is tracked by S21. |
| `base/hello.lucb` | The shared scalar/struct subset in a Luce Base module | HIR execution and a freestanding Wasm build through the pipeline; the Base process entry waits for spans (B2). |
| `base/c_arithmetic.lucb` | C's `//` and `%` and implicit same-signedness widening in a Luce Base module | HIR execution and a freestanding Wasm build through the pipeline; the same arithmetic floors in a `.luc` module (base.md §7.2, §7.5). |
| `base/pointer_width.lucb` | `usize`/`isize`, `sizeof`, `alignof`, and `offsetof` in a Luce Base module | HIR execution and a freestanding Wasm build through the pipeline; the width and the layout answers are the target's, folded by each backend (base.md §5.1, §5.11). |
| `native_interop.lucn` | `extern` declarations, anonymous `foreign` pointers, borrowed dense lists, fieldwise extern-struct crossing, incoming C function pointers, and audited pointer rebind/move | Checks and executes `clock_gettime`, a zero-length `writev` over `foreign` memory, `memcmp` over Luce-owned list storage, and a returned `signal` handler through native QBE/libc; pointer primitives execute in focused compiler tests. |

## Stage-0 corpus

The upstream corpus audit and adoption status live in
[`README.md`](README.md). Programs are adopted only when they become durable
automated semantic and QBE gates. Generated caches and duplicate sources are
not coverage.

Luce 1.0 has no separate `union` declaration: payload enums are its closed
tagged unions. It also has no wildcard import; selective imports always name
the declarations they introduce. Both exclusions require stable negative
fixtures under §25.

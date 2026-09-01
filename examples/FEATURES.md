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
| §5 | Scalar, composite, alias, inference, structural operations, and recursive type rules | complete | partial | partial | partial | partial | Every scalar width executes; managed forms beyond the completed generic-class/list/map/set/slice/bytes/interface ownership graphs remain. |
| §6 | Immutable/mutable bindings, assignment, initialization | complete | partial | partial | partial | partial | Class/custom-construction definite initialization, shared mutable closure cells, and interface value/class mutation execute; generic-nominal managed places remain. |
| §7 | Evaluation order, arithmetic, bits, comparisons, conversions, calls, indexing, and discarded values | complete | partial | partial | partial | partial | Explicit `discard` executes and silent non-unit discards emit structured `L0701`; dynamic sequence operations and floating/capability-dependent conversions remain. |
| §8 | Functions, arguments/defaults, tuples, methods, mutation, recursion, and function values | complete | partial | partial | partial | partial | Exact named values, core managed function environments, generic functions and independently generic methods, interface-requirement fallibility lifts, and dynamic interface calls execute; the complete default-argument audit remains. |
| §9 | `if`, conditional binding, loops, exhaustive match, return, and `defer` | complete | partial | partial | partial | partial | The complete §9.6 pattern/exhaustiveness contract and both standard iteration spellings execute; the remaining control-flow/return/defer rule audit is S08. |
| §10 | Structs, tuples, fixed arrays, enums, copying, visibility | complete | partial | partial | partial | partial | Struct/enum fundamentals, generic struct/enum/class applications and methods, explicit interface conformance, ownership-safe fixed-array slicing, and immutable structural hashing execute; the remaining rule-by-rule audit keeps the broad row open. |
| §11 | Classes, identity, ARC, weak references, destruction | complete | partial | partial | partial | partial | Core class lifetime reaches both oracles, QBE, and Wasm; direct strong-cycle rejection and `deinit` reentrancy advisories are complete. Resource-shape diagnostics and leak census remain. |
| §12 | Allocation, lists, maps, sets, slices, strings/bytes, arenas | complete | partial | partial | partial | partial | Lists, insertion-ordered maps/sets, owned strings/bytes, and the affine internal formatting builder reach QBE and Wasm. Public builders/codecs and the remaining arena contract remain. |
| §13 | Optionals, recoverable failure, errors, traps, fatal termination, assertions | complete | partial | partial | partial | partial | Dynamic `trap(str)` and eager `assert(bool, str?)` reach both oracles and QBE/Wasm with no deferred cleanup on failure. Assertion condition-effect proofs, error context, fatal termination, and an exhaustive source-location/stack diagnostic audit remain. |
| §14 | Lambdas, closures, captures, escape, cycles, sendability | complete | partial | partial | partial | partial | The executable capture/lifting/storage/direct-cycle matrix and shared-cell advisory are complete; worker sendability remains. |
| §15 | Generic declarations, constraints, monomorphization, limits | complete | partial | partial | partial | partial | Generic functions, generic structs/enums/classes with memberwise or custom construction where defined, owner-parameterized type functions, owner-parameterized and independently generic instance methods, concrete conformances, interface constraints/intersections, abstract body checking, structural inference, contextual values, defaults, recursion, memoized instances, configurable package budgets, infinite-expansion detection, source paths, and HIR/MIR/backend size/time accounting reach QBE; serialized typed bodies in package artifacts remain. |
| §16 | Interfaces, conformance, static use, interface values | complete | partial | partial | partial | partial | Nominal requirements, generic interfaces, explicit struct/class/enum conformance, static constrained calls, fallibility adapters, and existential value/class dispatch with value COW reach both oracles, QBE, and Wasm. The remaining rule-by-rule interface audit and dynamic-call cost reporting remain. |
| §17 | Iteration, equality, hashing, ordering, formatting, encoding protocols | complete | partial | partial | partial | partial | Iteration, closed derived equality/hashability, cycle-aware collection equality, immutable structural hashing, and closed `Display` formatting execute; ordering and encoding remain. |
| §18 | Effects are deliberately absent | complete | complete | n/a | n/a | n/a | Keep exclusion tests and prevent effect syntax from entering the grammar. |
| §19 | Isolated workers, transfer, cancellation, task lifetime | complete | syntax | — | — | syntax | Sendability checking, worker MIR operations, runtime, and QBE execution. |
| §20 | Modules, imports, visibility, entry points, and compile-time constants | complete | partial | partial | partial | partial | Module-cycle and import-use diagnostics, the public-signature/API-surface matrix, the complete constant subset, and the package/entry diagnostic matrix remain. Manifest, dependency identity, and platform variation are explicitly post-1.0. |
| §21 | C/native imports and exports, ownership/nullability, raw native source | complete | partial | partial | partial | partial | Scalar/handle/nested extern structs, strings, borrowed dense lists, anonymous `foreign` data pointers, and incoming bare/nullable cfunc pointers retain target-neutral HIR/MIR shape, with real QBE/libc proofs. FIIR generation, explicit inbound-memory verbs, the f16 C adapter, exported aggregates, and callback runtime/lifetime rules remain. |
| §22 | Compiler/runtime versus standard-library boundary | complete | partial | partial | partial | partial | Implement and execute the standard modules required by the language examples. |
| §23 | Semantic pipeline and runtime services | complete | partial | partial | partial | partial | Worker services, source traces/fatal outcomes, optional resource instrumentation, self-hosting, and the final full-language QBE artifact proof remain. Backend portfolio, artifact, ABI, profile, and cache policy are explicitly post-1.0. |
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
| S05 | §§5–6 | Rule audit for aliases, inference, recursive indirection, value/reference copying, and generic-nominal mutable places | Common and managed cases execute; promote only after every rule has a named fixture. |
| S06 | §§7–8 | Rule audit for eager order, operators, calls/defaults, tuples, methods, mutation, recursion, and exact callable values | Major paths execute; named arithmetic-policy APIs belong to S30. |
| S08 | §§9.1–9.5, §§9.7–9.8 | Rule audit for conditional/loop exits, return coverage, and every defer exit/error restriction | Major paths execute through both oracles and QBE. |
| S09 | §10 | Rule audit for struct/tuple/array/enum construction, copying, recursion, visibility, and all deliberate omissions | Major paths and generic applications execute; native representation is S21–S25. |
| S10 | §11.4–§11.5 | Resource-shape diagnostics and runtime leak/live-resource census | ARC, weak references, cycle diagnostics, destruction, and reentrancy advisories execute. |
| S11 | §12.6 | Restricted non-storable `mutable_slice[T]` plus closure-scoped mutable access | Syntax only; requires a scoped runtime operation and escape/send/native checks. |
| S12 | §§12.7–12.8, §22.2 | Public text/bytes builders, UTF codecs, parsing/formatting, arenas/pools/generational handles | Internal affine builder and owned text/bytes substrate are complete. |
| S13 | §§13.3–13.7 | Error context/source traces, complete trap provenance, structured fatal outcomes, and stack-budget reporting | Error data/control and dynamic traps execute; trace/fatal runtime path is incomplete. |
| S14 | §13.8 | Prove assertion conditions effect-free from operational summaries | Runtime assertion semantics execute; static proof is absent. |
| S15 | §14.4 | Closure/value sendability and all worker-boundary capture rejections | Core closure contract is complete; closes with workers. |
| S16 | §15 | Final generic rule audit and serialized typed bodies in package artifacts | Executable generic surface and specialization accounting are complete. |
| S17 | §16 | Final interface rule audit, including no-downcast exclusions and every static/existential adaptation | Concrete/generic/existential dispatch executes; audit remains. |
| S18 | §17.2 | Explicit `Comparable` conformance and total-order `compare` contract | Derived equality/hashability are complete; ordering protocol is absent. |
| S19 | §§19.1–19.5 | Workers, `task[T]`, graph-copy transfer, sendability, `wait_all`, cancellation, and supervised lifetime | Syntax only. |
| S20 | §§20.1–20.5 | Module-cycle, import-use, public-signature, constant-expression, and complete entry-point diagnostics | Imports/modules/constants/entry work in common paths; exact matrix remains. |
| S21 | §§21.1–21.15 | FIIR, C/C++ import and wrapper/thunk generation, recipes, provenance, and support diagnostics | Architecture is specified; generator is absent. |
| S22 | §21.16 | Raw memory copy/take verbs and the f16 generated shim | Direct `str` inputs/results/out slots and UTF-8 validation execute; the three explicit inbound-memory verbs and generated f16 adapter remain. |
| S23 | §21.17 | Resolve the field-only grammar/prose conflict, then close the remaining extern-struct matrix | Scalar/handle/`foreign`/nested/cfunc fields and pointer crossings execute; the syntax-versus-prose decision remains. |
| S24 | §21.19 | Enforce the callback thread/runtime contract and close the remaining C-export callback matrix | Raw incoming and nullable `cfunc` pointers, capture-free names/lambdas, null invocation, and generated C adapters execute. |
| S26 | §§24.2, 24.5 | Source `test` HIR/MIR/registry, isolated execution, test-only scope/import pruning, CLI selection/reporting, and `testing.expect_trap` | Parser surface only. |
| S27 | §§24.2–24.4 | Required first-party command modes, complete structured diagnostic shape/fixes, and canonical formatter | `check`, `run`, and `build` have a working core; remaining modes/contracts are absent. |
| S28 | §25 | Stable negative fixtures for every deliberate exclusion | Representative tokenizer/parser exclusions exist; exhaustive mapping remains. |
| S29 | §23.1 | Compile the compiler with stage-1, compare observable behavior, and preserve the frozen bootstrap chain | Stage-0 0.30 builds and tests the tree; self-hosting proof remains. |
| S30 | §§22–23 | Finish the standard modules and runtime services required by the proving examples, then run the full corpus through QBE | Core runtime storage/collections/text/classes are executable; workers, codecs, host libraries, and resource tooling remain. |

The following spec sections do **not** block language-spec completion because the 1.0
document explicitly defers them: §§20.6–20.8, 23.2–23.3, 23.5–23.8, 24.1,
and 24.6–24.9. This prevents post-1.0 package, backend-portfolio, artifact,
service, documentation, and release-policy work from silently expanding the
language baseline. Separately requested engineering gates, including generated
programs and fuzzing, remain in `docs/compiler/plan.md` and still precede the
final architecture audit.

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
| `interfaces.luc` | Generic existential conversion, struct/class/enum witness dispatch, nested ownership, value COW, class identity, and fallibility adaptation/propagation | HIR and MIR oracles plus Wasm and native QBE execution. |
| `iteration.luc` | Compiler-known infallible/fallible iteration through concrete, constrained-generic, and existential values, including lexical iterator cleanup | HIR and MIR oracles plus Wasm and native QBE execution. |
| `hashing.luc` | Compiler-derived structural constraints and execution-local hashing across immutable value families | HIR and MIR oracles plus Wasm and native QBE execution. |
| `closures.luc` | Managed copied/shared/weak captures, fallibility lifting, nested escape, collection/field ownership, and weak-self cycle breaking | HIR and MIR oracles plus Wasm and native QBE execution. |
| `cfunc_values.luc` | Exact C-callable values and adapters | HIR, MIR, Wasm, and native QBE execution. |
| `conditional_binding.luc` | Optional conditional binding, branch-only payload scope, and absent fallback | HIR, MIR, Wasm, and native QBE execution. |
| `numeric_conversions.luc` | Checked integer/float construction, binary32 contextual rounding, width conversion, and truncation | HIR and MIR oracles plus native QBE and Wasm execution. |
| `array_slices.luc` | Immutable owned snapshots from inline fixed arrays, including escaping managed elements | HIR and MIR oracles plus native QBE and Wasm execution. |
| `classes.luc` | Nominal identity, shared mutation, strong/weak ARC, first-class weak collections, borrowed deinitialization, failed construction, and reverse destruction | HIR and MIR oracles plus native QBE and Wasm execution. |
| `lists.luc` | Shared list identity, cycle-aware structural equality, shallow independent copies and concatenation, immutable snapshots, ordered invalidating iteration, checked access/shape mutation, aggregate elements, recursive ARC/reclamation, and growth | HIR and MIR oracles plus native QBE and Wasm execution, bounds and iteration traps. |
| `maps_and_sets.luc` | Insertion-ordered map/set identity, lookup, mutation, copy, recursive equality, managed ownership, and alias-wide iteration invalidation | HIR and MIR oracles plus native QBE and Wasm execution and mutation traps. |
| `bytes.luc` | Immutable owned byte concatenation/comparison and ownership-retaining escaping slices | HIR and MIR oracles plus native QBE and Wasm execution. |
| `strings.luc` | Ordinary/raw/triple text and bytes, owned UTF-8 concatenation/discard, Unicode scalar length/iteration, and scalar-preserving ordering | HIR and MIR oracles plus native QBE and Wasm execution. |
| `formatted_strings.luc` | Builtin/concrete/generic/existential `Display`, nested affine construction, triples/braces, Unicode, integer extrema, and both IEEE widths | HIR and MIR oracles plus native QBE and Wasm execution. |
| `traps.luc` | Dynamic nonrecoverable diagnostics, `never` callables, nested eager-prefix termination, and skipped deferred cleanup | HIR and MIR oracles plus captured native QBE and Wasm failure diagnostics. |
| `assertions.luc` | Default/dynamic assertion messages, successful continuation, and failed no-cleanup termination | HIR and MIR oracles plus captured native QBE and Wasm failure diagnostics. |
| `language_tour.luc` | Broad 1.0 declaration/control/managed surface | Parser only; each section migrates into focused executable examples as it lands. |
| `operators_and_literals.luc` | Literal, collection, type, and operator surface | Parser only beyond the already executable scalar subset. |
| `checkout/` | Multi-module application shape | Parser only until collections/strings are complete. |
| `c_api.luc` | C export surface | Parser only as a whole; focused C function export tests execute elsewhere. |
| `c_import/` | Manifest-generated C import architecture | Parser/C-source checks; FIIR generation and end-to-end linking pending. |
| `native_interop.native.luc` | `extern` declarations, anonymous `foreign` pointers, borrowed dense lists, fieldwise extern-struct crossing, incoming C function pointers, and audited pointer rebind/move | Checks and executes `clock_gettime`, a zero-length `writev` over `foreign` memory, `memcmp` over Luce-owned list storage, and a returned `signal` handler through native QBE/libc; pointer primitives execute in focused compiler tests. |

## Stage-0 corpus

The upstream corpus audit and adoption status live in
[`README.md`](README.md). Programs are adopted only when they become durable
automated semantic and QBE gates. Generated caches and duplicate sources are
not coverage.

Luce 1.0 has no separate `union` declaration: payload enums are its closed
tagged unions. It also has no wildcard import; selective imports always name
the declarations they introduce. Both exclusions require stable negative
fixtures under §25.

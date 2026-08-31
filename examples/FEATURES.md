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
| §3 | UTF-8 source, layout, comments, documentation, names, scope | complete | partial | n/a | n/a | partial | Class, closure, generic, interface, and test scopes remain with those features. |
| §4 | Boolean, absence, numeric, character, string, byte, raw, formatted, triple, and collection literals | complete | partial | partial | partial | partial | Ordinary/raw text, character, byte escapes, and list literals execute; map, formatted, and formatter-trimmed triple literals remain. |
| §5 | Scalar, composite, alias, inference, structural operations, and recursive type rules | complete | partial | partial | partial | partial | `f16`, maps/sets, classes, interfaces, generics, hashing, structural list equality, and recursive managed forms beyond the completed list/slice/bytes ownership graph. |
| §6 | Immutable/mutable bindings, assignment, initialization | complete | partial | partial | partial | partial | Definite initialization for class/custom-construction and future managed places. |
| §7 | Evaluation order, arithmetic, bits, comparisons, conversions, calls, indexing, and discarded values | complete | partial | partial | partial | partial | Explicit `discard` executes and releases owned temporaries; dynamic sequence operations, future reference identity, and floating/capability-dependent conversions remain. |
| §8 | Functions, arguments/defaults, tuples, methods, mutation, recursion, and function values | complete | partial | partial | partial | partial | Generic functions and managed function environments; audit all default-argument rules. |
| §9 | `if`, conditional binding, loops, exhaustive match, return, and `defer` | complete | partial | partial | partial | partial | Protocol iteration/`try for` and the remaining pattern families. |
| §10 | Structs, tuples, fixed arrays, enums, copying, visibility | complete | partial | partial | partial | partial | Struct/enum fundamentals and ownership-safe fixed-array slicing execute; generics, interface conformance, hashing, and the remaining rule-by-rule audit keep the broad row open. |
| §11 | Classes, identity, ARC, weak references, destruction | complete | syntax | — | — | syntax | HIR ownership model and semantic oracle. |
| §12 | Allocation, lists, maps, sets, slices, strings/bytes, arenas | complete | partial | partial | partial | partial | Lists, immutable list snapshots, recursive list/slice ownership and reclamation, owned bytes with escaping slices, and Unicode string fundamentals reach QBE and Wasm. Maps/sets, structural list equality, builders/codecs, and content hashing remain. |
| §13 | Optionals, recoverable failure, errors, traps, fatal termination, assertions | complete | partial | partial | partial | partial | Dynamic `trap(str)` and eager `assert(bool, str?)` reach both oracles and QBE/Wasm with no deferred cleanup on failure. Assertion condition-effect proofs, error context, fatal termination, and an exhaustive source-location/stack diagnostic audit remain. |
| §14 | Lambdas, closures, captures, escape, cycles, sendability | complete | syntax | — | — | syntax | Managed function environments and capture/ownership analysis. |
| §15 | Generic declarations, constraints, monomorphization, limits | complete | syntax | — | — | syntax | HIR generic identities and bounded monomorphization. |
| §16 | Interfaces, conformance, static use, interface values | complete | syntax | — | — | syntax | HIR requirements/conformance and witness representation. |
| §17 | Iteration, equality, hashing, ordering, formatting, encoding protocols | complete | partial | partial | partial | partial | Closed protocol model beyond built-in range/list iteration and value equality. |
| §18 | Effects are deliberately absent | complete | complete | n/a | n/a | n/a | Keep exclusion tests and prevent effect syntax from entering the grammar. |
| §19 | Isolated workers, transfer, cancellation, task lifetime | complete | syntax | — | — | syntax | Sendability checking, worker MIR operations, runtime, and QBE execution. |
| §20 | Modules, imports, visibility, entry points, manifests, dependency identity | complete | partial | partial | partial | partial | Manifest/dependency graph and the complete package/entry diagnostic matrix. |
| §21 | C/native imports and exports, ownership/nullability, raw native source | complete | partial | partial | partial | partial | FIIR generation, extern structs/richer boundary adapters, and remaining callback/lifetime rules. |
| §22 | Compiler/runtime versus standard-library boundary | complete | partial | partial | partial | partial | Implement and execute the standard modules required by the language examples. |
| §23 | Semantic pipeline, runtime services, ABI, artifacts, backends | complete | partial | partial | partial | partial | Arena/runtime completion and full-language QBE artifact proof. Deferred subsections stay deferred by the spec. |
| §24 | Command/diagnostic contract, formatter, source `test` declarations | complete | syntax | — | — | syntax | Source tests, formatter, and the remaining stable CLI/diagnostic contracts; spec-deferred subsections remain deferred. |
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

## Current numeric-construction evidence

The broad §7 row remains partial. Explicit construction now has one resolved
HIR identity and one canonical MIR conversion family; width, signedness, and
IEEE rounding remain semantic facts while only instruction selection belongs
to QBE or Wasm.

| §7.5 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Every signed/unsigned integer pair checks the destination interval | yes | yes | yes, plus Wasm | `numeric_conversions.luc` and differential boundaries | complete |
| Integer-to-float rounds to nearest, ties to even | yes | yes | yes, plus Wasm | `numeric_conversions.luc` | complete for f32/f64 |
| Float-to-integer truncates toward zero and traps NaN/infinity/out-of-range | yes | yes | yes, plus Wasm | `numeric_conversions.luc` and trapping corpus | complete for f32/f64 |
| f32/f64 widening and checked narrowing; contextual f32 literals and per-operation f32 rounding | yes | yes | yes, plus Wasm | `numeric_conversions.luc` | complete |
| f16 construction and arithmetic | rejected at first missing stage | n/a | n/a | focused negative fixture | open with f16 |

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
| Half-open O(1) slicing with checked bounds | yes | yes | yes, including traps | `bytes.luc` | complete for bytes |
| Slice returned across a temporary dynamic source's destruction retains that source owner | yes | yes, including forged-owner rejection | yes, plus Wasm execution | `bytes.luc` | complete |

## Current `str` evidence

`str` uses the same immutable owner/data/byte-length substrate as `bytes`, but
HIR keeps the language types and their legal operations distinct.

| §12.7/§7 rule | HIR/oracle | MIR/verifier | QBE product | Example | State |
| --- | --- | --- | --- | --- | --- |
| Valid UTF-8 literal, O(1) `byte_count`, O(n) scalar `length()` | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Ordinary and raw spellings with complete simple/Unicode escapes | yes | constants unchanged | yes, plus Wasm | `strings.luc` | complete |
| Immutable concatenation with escaping owned storage | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Unicode scalar iteration with ordinary loop exits | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Exact equality and deterministic scalar-value/prefix ordering | yes | yes | yes, plus Wasm | `strings.luc` | complete |
| Integer indexing and slicing remain unavailable | stable rejection | n/a | n/a | focused negative fixtures | complete |
| Content hashing | — | — | — | — | waits for the structural hashing protocol |

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
| `cfunc_values.luc` | Exact C-callable values and adapters | HIR, MIR, Wasm, and native QBE execution. |
| `conditional_binding.luc` | Optional conditional binding, branch-only payload scope, and absent fallback | HIR, MIR, Wasm, and native QBE execution. |
| `numeric_conversions.luc` | Checked integer/float construction, binary32 contextual rounding, width conversion, and truncation | HIR and MIR oracles plus native QBE and Wasm execution. |
| `array_slices.luc` | Immutable owned snapshots from inline fixed arrays, including escaping managed elements | HIR and MIR oracles plus native QBE and Wasm execution. |
| `lists.luc` | Shared list identity, shallow independent copies and concatenation, immutable snapshots, ordered invalidating iteration, checked access/shape mutation, aggregate elements, recursive ARC/reclamation, and growth | HIR and MIR oracles plus native QBE and Wasm execution, bounds and iteration traps. |
| `bytes.luc` | Immutable owned byte concatenation/comparison and ownership-retaining escaping slices | HIR and MIR oracles plus native QBE and Wasm execution. |
| `strings.luc` | Raw/escaped text and bytes, owned UTF-8 concatenation/discard, Unicode scalar length/iteration, and scalar-preserving ordering | HIR and MIR oracles plus native QBE and Wasm execution. |
| `traps.luc` | Dynamic nonrecoverable diagnostics and skipped deferred cleanup | HIR and MIR oracles plus captured native QBE and Wasm failure diagnostics. |
| `assertions.luc` | Default/dynamic assertion messages, successful continuation, and failed no-cleanup termination | HIR and MIR oracles plus captured native QBE and Wasm failure diagnostics. |
| `language_tour.luc` | Broad 1.0 declaration/control/managed surface | Parser only; each section migrates into focused executable examples as it lands. |
| `operators_and_literals.luc` | Literal, collection, type, and operator surface | Parser only beyond the already executable scalar subset. |
| `checkout/` | Multi-module application shape | Parser only until collections/strings are complete. |
| `c_api.luc` | C export surface | Parser only as a whole; focused C function export tests execute elsewhere. |
| `c_import/` | Manifest-generated C import architecture | Parser/C-source checks; FIIR generation and end-to-end linking pending. |
| `native_interop.native.luc` | `extern` declarations plus audited pointer rebind/move | Parser conformance as a whole; supported pointer operations execute in focused compiler tests. |

## Stage-0 corpus

The upstream corpus audit and adoption status live in
[`README.md`](README.md). Programs are adopted only when they become durable
automated semantic and QBE gates. Generated caches and duplicate sources are
not coverage.

Luce 1.0 has no separate `union` declaration: payload enums are its closed
tagged unions. It also has no wildcard import; selective imports always name
the declarations they introduce. Both exclusions require stable negative
fixtures under §25.

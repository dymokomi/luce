# Examples

These programs target the 1.0 language in `docs/language/1.0.md`. Every
example is parser-checked; `semantic_core/` also passes through HIR
generation and the interpreter, and `compiled_core/` and `hello.luc` compile
to artifacts. "What works today" in the [top-level README](../README.md)
defines those slices; each example's leading comment names the slice it
belongs to. [`FEATURES.md`](FEATURES.md) is the authoritative conformance
ledger: parser coverage alone never counts as source-to-QBE completion.

- `hello.luc` is the smallest native executable; it also builds as WebAssembly.
- `semantic_core/` is the small multi-module function-and-control-flow slice
  currently executable beyond parsing.
- `compiled_core/` is the arithmetic slice exported from a WebAssembly module.
- `language_tour.luc` covers declarations, data modeling, functions, control
  flow, closures, failure recovery, workers, and static tests.
- `operators_and_literals.luc` is a focused reference for the remaining value,
  literal, collection, type, and operator forms.
- `checkout/` is one program split across modules. From this package root,
  `checkout/catalog.luc` has the module path `checkout.catalog`; its entry point
  demonstrates both selective and aliased imports.
- `c_api.luc` demonstrates the narrow C export surface.
- `c_import/` contains a real C library and the Luce boundary that consumes its
  manifest-generated raw module. See its README for the current implementation
  boundary.
- `stage0_calculator.luc` is the stage-0 recursive-descent calculator adapted
  to the 1.0 syntax, explicit UTF-8-byte scanning, and entry contract. It
  checks, compiles through QBE, links, and executes as a native gate.
- `stage0_sort.luc` adapts Stage-0's list sort to explicit fixed storage. It
  proves array value copies, aggregate calls/results, checked mutation, and
  structural equality through native QBE without depending on the future
  collection runtime.
- `stage0_brainfuck.luc` preserves Stage-0's interpreter loop and bracket
  search with explicit fixed tape/output capacities. Bytes, nested control
  flow, exhaustive matching, wrapping cells, checked mutation and aggregate
  results execute through HIR, Wasm and native QBE.
- `function_values.luc` is an end-to-end exact-function-value example. Named
  function addresses, selection, aliases, fields, parameters/results and
  fallible calls execute through the semantic oracle and native QBE, and the
  same canonical MIR builds as WebAssembly.
- `generic_functions.luc` proves abstract body checking, argument inference,
  explicit structural specialization, contextual generic function values,
  defaults, recursion, and memoized monomorphization through both semantic
  oracles, Wasm, and native QBE. It is also the compact input used to inspect
  expansion provenance with `luce explain` and HIR/MIR/backend costs with
  `luce build --time-report`, including one checked specialization removed by
  closed-world reachability before backend emission.
- `generic_methods.luc` proves that an applied receiver fixes its generic-owner
  arguments while independently declared method parameters are inferred or
  supplied explicitly. Owner-dependent constraints, defaults, recursion,
  mutation, and concrete/generic struct, class, and enum receivers specialize
  to ordinary functions through both semantic oracles, Wasm, and native QBE.
- `generic_construction.luc` proves custom initialization of generic structs
  and type functions on generic structs, classes, and enums. Owner arguments
  are inferred from arguments or result context, or supplied explicitly, and
  every construction specializes to ordinary functions through both semantic
  oracles, Wasm, and native QBE.
- `constrained_generics.luc` proves nominal interface requirements, explicit
  conformance, statically dispatched generic constraints, a constrained
  generic-struct method specialized from its applied receiver, concrete
  generic-struct conformance and existential dispatch, and the safe lift from
  an infallible implementation to a fallible requirement through both
  semantic oracles, Wasm, and native QBE.
- `generic_enums.luc` proves inferred, explicit, contextual and
  representation-distinct enum applications; concrete value/mutating methods,
  matching, conformance witnesses and existential dispatch; and source-order
  evaluation of named payloads through both semantic oracles, Wasm, and native
  QBE.
- `generic_classes.luc` proves inferred, explicit and contextual managed
  applications with substituted fields and lifecycle methods, distinct
  concrete identity, weak recursive references, fallible construction,
  conformance witnesses and existential dispatch through both semantic
  oracles, Wasm, and native QBE.
- `types_and_bindings.luc` closes the core type-and-binding audit with
  transparent aliases, explicit public API types, local/contextual inference,
  single-evaluation tuple binding, value-copy independence, shared list/class
  identity, recursive class indirection, and nested generic mutable places
  through both semantic oracles, Wasm, and native QBE. Together with
  `array_slices.luc`, `generic_enums.luc`, and `hashing.luc`, it is the
  readable product proof for the complete ordinary §10 value-data model.
- `mutable_slices.luc` proves the restricted `mutable_slice[T]` contract.
  A list lends synchronous indexed mutation to an explicitly typed callback;
  ordinary aliases observe replacement, immutable slices retain both pre-call
  and callback-time snapshots, and the same scoped HIR/MIR transaction runs
  through both semantic oracles, Wasm, and native QBE. Storage, capture,
  return, generic erasure, and native-boundary exclusions are enforced
  by the compiler rather than represented as user-visible lifetime machinery.
- `expressions_and_calls.luc` closes the core expression/function audit with
  observable receiver, argument, literal, interpolation, binary, assignment,
  and constructor order; pure defaults, named placement, tuples, exact
  callable values, recursion, and value-receiver replacement through both
  semantic oracles, Wasm, and native QBE.
- `interfaces.luc` proves existential conversion and dynamic dispatch for
  value and class conformers. Value payload mutation detaches with copy-on-
  write, class payload mutation preserves shared identity, and infallible
  implementations adapt to fallible requirements while a genuinely failing
  witness preserves caller-owned error propagation. Generic interface
  applications, enum conformers, returned existentials, and existentials in
  managed collections travel through both semantic oracles, Wasm, and native
  QBE using the same HIR and MIR shapes.
- `iteration.luc` proves the four compiler-known iteration interfaces through
  concrete, constrained-generic, and existential dispatch. Ordinary `for`,
  propagating `try for`, item/end/error separation, break/continue, and the
  private iterator's cleanup on exhaustion, break, return, and error all run
  through both semantic oracles, Wasm, and native QBE. Protocol loops lower to
  existing calls, optionals, failure transfer, and structured control rather
  than adding a backend-specific iteration representation.
- `conditional_binding.luc` proves optional binding scope and both outcomes,
  plus source-order-independent conditional joins through optional promotion.
  The same HIR executes through both semantic oracles, Wasm, and native QBE.
- `hashing.luc` proves compiler-derived `Equatable`/`Hashable` constraints and
  execution-local structural hashing across scalars, strings/bytes, arrays,
  ranges, tuples, optionals, structs, and payload enums. Equal-value behavior
  runs through both semantic oracles, Wasm, and native QBE without pinning a
  backend's numeric hash code.
- `numeric_conversions.luc` imports the shipped ordinary `math` module and
  proves its width-explicit NaN and signed-infinity constants alongside checked
  conversions across every integer and IEEE width, including binary16 literal
  and per-operation rounding, finite-overflow traps, and adjacent two-byte f16
  aggregate storage through both semantic oracles, Wasm, and native QBE.
- `closures.luc` proves capture-free and managed anonymous functions,
  explicit value snapshots, shared mutable capture cells, fallible calls and
  infallible-value lifting, nested escaping environments, function ownership
  in collections and class fields, and named/`self` weak captures through both
  semantic oracles, Wasm, and native QBE. Default mutable capture also emits
  the non-fatal structured shared-cell advisory through check, run, and build.
  Worker sendability stays explicit in the compiler plan.
- `cfunc_values.luc` exercises the matching C-callable value shape through
  aliases, fields, parameters/results and selection. Capture-free named Luce
  functions use generated C adapters; HIR/MIR, Wasm and native QBE all run the
  same example. Dynamic and nullable pointers arriving from C remain later
  boundary work.
- `classes.luc` proves explicit class construction, alias identity and shared
  mutation, zeroing weak fields, first-class `Weak[T]` collections,
  destruction-time weak stores and dead-weak fallback, transitive borrowed
  `deinit` helper methods, reverse field destruction, idempotent explicit
  `close` through both `defer` and the `deinit` safety net, and
  failed-initializer cleanup through both semantic oracles, Wasm, and native
  QBE. Focused conformance fixtures additionally reject direct strong
  field/list/closure cycles, distinguish same-class cleanup from reentrant
  user callbacks, and report dynamic SCCs with allocation sites as isolated
  harness metadata rather than production reflection.
- `lists.luc` is the first runtime-backed collection example. It proves
  shared identity through aliases, `let` fields, and `is`/`is not`, checked
  indexed mutation, ordered structural equality for finite and recursive
  contents—including self/deep cycles, mismatches, pair-set growth, and alias
  topology independent from value—
  typed list parameters/results, mutating aggregate elements, insertion,
  removal, clearing, reservation, shallow independent copying and `+`
  concatenation, O(1) immutable snapshot slicing, ordered iteration with
  nested reads, alias-wide shape invalidation and cleanup across structured
  exits, evaluation order, and
  geometric growth, recursive ARC, and storage reclamation through the HIR
  and MIR oracles, Wasm, and a real native QBE artifact.
- `maps_and_sets.luc` proves insertion-ordered map/set identity, lookup,
  replacement, insertion, removal, reservation, clearing, shallow copying,
  order-independent and recursive equality, alias-wide iteration guards, and
  exact managed-value release through both semantic oracles, Wasm, and native
  QBE.
- `strings.luc` proves exact raw and escaped text/byte spellings, escaping
  owned concatenation and explicit disposal of an owned temporary, distinct
  byte/scalar lengths, Unicode scalar iteration, and lexicographic ordering
  through both compiled backends and the semantic oracles.
- `formatted_strings.luc` proves one closed `Display` protocol for builtin,
  concrete, constrained-generic, and existential values. Nested builders,
  Unicode and escaped braces, triple normalization, integer extrema, and both
  float widths execute through both semantic oracles, native QBE, and Wasm.
- `traps.luc` proves that a `never` callable accepts dynamically owned text,
  preserves the eager owned prefix of a nested call while omitting its
  unreachable outer operation, reports through each execution path, and does
  not run deferred cleanup.
- `assertions.luc` proves the optional default and eager dynamic assertion
  messages, unit-valued successful continuation, captured QBE/Wasm failure
  diagnostics, and skipped deferred cleanup.
- `native_interop.native.luc` checks and executes raw `extern` types,
  anonymous `foreign` data pointers, borrowed dense lists, functions, output
  parameters, variables, and ordinary value-shaped extern structs. Its
  `clock_gettime`, zero-length `writev`, and list-backed `memcmp` calls cross
  real QBE/libc data boundaries, while two `signal` calls return and invoke an
  opaque C function pointer; the same file keeps the audited native rebind/move
  surface visible.

## Stage-0 example corpus as a progress gate

The upstream corpus was audited at stage-0 commit
[`d5b4583`](https://github.com/dymokomi/luce-stage-0/tree/d5b458355179c059ce9c506c37990612c2c8f68f/examples).
It is a capability map, not a directory to copy wholesale. We adopt one
cohesive program when it can become a durable gate, update it to the current
1.0 surface, and preserve its source lineage. Generated editor caches and
artifacts are never imported.

| Upstream program | What it measures | Current disposition |
|---|---|---|
| `hello` | entry arguments, strings, output | Intent represented by `hello.luc`; compiled on both artifact paths. |
| `calc` | byte scanning, checked indexing, recursion, tuples, recoverable failure | Adopted as `stage0_calculator.luc`; native QBE execution green. |
| `sort`, `stats` | lists, iteration, indexing, sorting, numeric library | `sort` remains adopted as the fixed-array `stage0_sort.luc`; growable lists, iteration, and removal now work, while the numeric library and remaining source/API differences still block the original shape and `stats`. |
| `bf` | arrays, byte indexing, nested loops/match, wrapping cells, output construction | Adopted as allocation-free `stage0_brainfuck.luc`; the interpreter executes through every current product path. The general runtime builder now has separate formatting coverage. |
| `dice` | RNG, arrays/lists, formatted strings, files | Collections and formatting are complete; adoption now waits for deterministic RNG, files, and the corresponding standard-library surface. |
| `life` | two-dimensional arrays, terminal input/output, timing | Fixed-array storage is now covered; the full program still waits for terminal and timing host services. |
| `wordcount` | maps, string scanning, builders, files | Maps and internal builders are complete; adoption waits for the remaining string-scanning and file APIs. |
| `zipper` | byte/list processing, filesystem safety, ZIP library | Collections are complete; adoption waits for filesystem safety and the ZIP/stream library surface. |
| `adventure` | a cohesive multi-module application with collections, text, files, and input | Catalogued as the first broad application gate after those foundations. |
| `editor` | classes/ARC, closures, collections, terminal UI, files, LSP client | Catalogued for the host proving-program phase. |
| `lsp` | interfaces, classes, JSON, byte framing, I/O, processes | Catalogued for the host proving-program phase. |

The fixed-array slice, Brainfuck gate, and first runtime-backed list slice
remove allocation-free dense storage, nontrivial byte-driven interpreter
control flow, and basic growable sequence storage from this map. The remaining
small and medium programs still need numeric/text algorithms, files, and host
services. Canonical MIR never manufactures
target byte sizes or prescribes memory growth; allocator and collection policy
remain in the runtime rather than HIR, MIR, or the compiler itself.

`FEATURES.md` maps the complete 1.0 contract to frontend, HIR, MIR, QBE, and
example evidence. Payload enums are Luce's tagged unions; there is
intentionally no second `union` declaration.

Declarations without `pub` are intentionally module-private. Build the
1.0 compiler, then exercise the semantic slice or all parser fixtures:

```sh
./build/luce check --package org.luce.examples examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce run --package org.luce.examples main.answer examples/semantic_core/math.luc examples/semantic_core/main.luc   # prints 42
./build/luce build --package org.luce.examples build/answer.wasm examples/compiled_core/main.luc
./build/luce build --package org.luce.examples --target native build/hello examples/hello.luc
./build/hello                                                                                 # prints Hello, world!
./stage0/bin/luce-0 test tests/compiler/examples_test.luc
```

`luce.toml` in this directory declares the C binding target used by
`c_import/`; nothing else reads it yet.

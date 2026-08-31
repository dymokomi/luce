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
  same canonical MIR builds as WebAssembly. Closure environments and the
  infallible-to-fallible adapter remain a later managed-runtime slice.
- `cfunc_values.luc` exercises the matching C-callable value shape through
  aliases, fields, parameters/results and selection. Capture-free named Luce
  functions use generated C adapters; HIR/MIR, Wasm and native QBE all run the
  same example. Dynamic and nullable pointers arriving from C remain later
  boundary work.
- `lists.luc` is the first runtime-backed collection example. It proves
  shared identity through aliases, `let` fields, and `is`/`is not`, checked
  indexed mutation,
  typed list parameters/results, mutating aggregate elements, insertion,
  removal, clearing, reservation, shallow independent copying and `+`
  concatenation, O(1) immutable snapshot slicing, ordered iteration with
  nested reads, alias-wide shape invalidation and cleanup across structured
  exits, evaluation order, and
  geometric growth through the HIR
  and MIR oracles and a real native QBE artifact. ARC and reclamation remain
  explicit later list slices.
- `strings.luc` proves escaping owned concatenation, distinct byte/scalar
  lengths, Unicode scalar iteration, and lexicographic ordering through both
  compiled backends and the semantic oracles.
- `native_interop.native.luc` is the focused parser-conformance example for
  raw `extern` types, blocking functions, output parameters, variables, and
  structs. Implemented boundary pieces have separate executable tests; the
  whole example advances only with FIIR and richer C layout support.

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
| `bf` | arrays, byte indexing, nested loops/match, wrapping cells, output construction | Adopted as allocation-free `stage0_brainfuck.luc`; the interpreter executes through every current product path, while general builders still wait for the runtime. |
| `dice` | RNG, arrays/lists, formatted strings, files | Catalogued; waits for collections, formatting, and the standard runtime. |
| `life` | two-dimensional arrays, terminal input/output, timing | Fixed-array storage is now covered; the full program still waits for terminal and timing host services. |
| `wordcount` | maps, string scanning, builders, files | Catalogued; waits for collections and string operations. |
| `zipper` | byte/list processing, filesystem safety, ZIP library | Catalogued; waits for collections and the standard runtime. |
| `adventure` | a cohesive multi-module application with collections, text, files, and input | Catalogued as the first broad application gate after those foundations. |
| `editor` | classes/ARC, closures, collections, terminal UI, files, LSP client | Catalogued for the host proving-program phase. |
| `lsp` | interfaces, classes, JSON, byte framing, I/O, processes | Catalogued for the host proving-program phase. |

The fixed-array slice, Brainfuck gate, and first runtime-backed list slice
remove allocation-free dense storage, nontrivial byte-driven interpreter
control flow, and basic growable sequence storage from this map. The remaining
small and medium programs still need collection iteration, maps/sets, bytes slicing,
text construction, files, and host services. Canonical MIR never manufactures
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

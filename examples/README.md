# Examples

These programs target the 1.0 language in `docs/language/1.0.md`. Every
example is parser-checked; `semantic_core/` also passes through HIR
generation and the interpreter, and `compiled_core/` and `hello.luc` compile
to artifacts. "What works today" in the [top-level README](../README.md)
defines those slices; each example's leading comment names the slice it
belongs to.

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
| `sort`, `stats` | lists, iteration, indexing, sorting, numeric library | `sort` adopted as allocation-free `stage0_sort.luc` using fixed arrays; the growable-list form and `stats` still wait for collections/runtime. |
| `bf` | arrays, string/array indexing, characters, string builder | Catalogued; waits for dense storage and string operations. |
| `dice` | RNG, arrays/lists, formatted strings, files | Catalogued; waits for collections, formatting, and the standard runtime. |
| `life` | two-dimensional arrays, terminal input/output, timing | Fixed-array storage is now covered; the full program still waits for terminal and timing host services. |
| `wordcount` | maps, string scanning, builders, files | Catalogued; waits for collections and string operations. |
| `zipper` | byte/list processing, filesystem safety, ZIP library | Catalogued; waits for collections and the standard runtime. |
| `adventure` | a cohesive multi-module application with collections, text, files, and input | Catalogued as the first broad application gate after those foundations. |
| `editor` | classes/ARC, closures, collections, terminal UI, files, LSP client | Catalogued for the host proving-program phase. |
| `lsp` | interfaces, classes, JSON, byte framing, I/O, processes | Catalogued for the host proving-program phase. |

The fixed-array slice removes allocation-free dense storage from this map.
The remaining small and medium programs are dominated by growable
collections, slicing, text construction, files, and host services. Their
runtime work starts only after the target-neutral allocation contract is
settled: canonical MIR cannot manufacture target byte sizes or prescribe
WebAssembly linear-memory growth. Allocator policy does not belong in HIR,
MIR, or the compiler itself.

`FEATURES.md` maps the complete parser-supported 1.0 source surface to
these files. Payload enums are Luce's tagged unions; there is intentionally no
second `union` declaration.

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

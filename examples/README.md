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
  to the 1.0 syntax and entry contract. It parses today and intentionally pins
  the first HIR gap (`len`/string operations) until that frontier advances.

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
| `calc` | string scanning/slicing, recursion, tuples, recoverable failure | Adopted as `stage0_calculator.luc`; parser green, HIR frontier pinned. |
| `sort`, `stats` | lists, iteration, indexing, sorting, numeric library | Catalogued; waits for collections and their runtime. |
| `bf` | arrays, string/array indexing, characters, string builder | Catalogued; waits for dense storage and string operations. |
| `dice` | RNG, arrays/lists, formatted strings, files | Catalogued; waits for collections, formatting, and the standard runtime. |
| `life` | two-dimensional arrays, terminal input/output, timing | Catalogued; waits for arrays and host services. |
| `wordcount` | maps, string scanning, builders, files | Catalogued; waits for collections and string operations. |
| `zipper` | byte/list processing, filesystem safety, ZIP library | Catalogued; waits for collections and the standard runtime. |
| `adventure` | a cohesive multi-module application with collections, text, files, and input | Catalogued as the first broad application gate after those foundations. |
| `editor` | classes/ARC, closures, collections, terminal UI, files, LSP client | Catalogued for the host proving-program phase. |
| `lsp` | interfaces, classes, JSON, byte framing, I/O, processes | Catalogued for the host proving-program phase. |

The dominant near-term evidence is unambiguous: collections plus indexing,
slicing, and string/runtime primitives unlock most of the small and medium
programs. That agrees with the compiler plan's ordering—runtime first, then
lists/maps/sets and strings—without moving platform policy into HIR or MIR.

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

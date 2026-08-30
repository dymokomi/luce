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

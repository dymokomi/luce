# Examples

These programs target the epoch-1 language in `LUCE_LANGUAGE_DESIGN.md`. Every
example is parser-checked; `semantic_core/` also passes through the current
name-resolution, type-checking, and interpreter slice.

- `hello.luc` is the smallest executable module.
- `semantic_core/` is the small multi-module function-and-control-flow slice
  currently executable beyond parsing.
- `language_tour.luc` covers declarations, data modeling, functions, control
  flow, closures, failure recovery, effects, workers, and static tests.
- `operators_and_literals.luc` is a focused reference for the remaining value,
  literal, collection, type, and operator forms.
- `checkout/` is one program split across modules. From this package root,
  `checkout/catalog.luc` has the module path `checkout.catalog`; its entry point
  demonstrates both selective and aliased imports.
- `c_api.luc` demonstrates the deliberately narrow C export surface.
- `c_import/` contains a real C library and the Luce boundary that consumes its
  manifest-generated raw module. See its README for the current implementation
  boundary.

`FEATURES.md` maps the complete parser-supported epoch-1 source surface to
these files. Payload enums are Luce's tagged unions; there is intentionally no
second `union` declaration.

Declarations without `pub` are intentionally module-private. Build the
epoch-1 compiler, then exercise the semantic slice or all parser fixtures:

```sh
./build/luce check examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce run main.answer examples/semantic_core/math.luc examples/semantic_core/main.luc
./stage0/bin/luce-0 test src/compiler/examples_test.luc
```

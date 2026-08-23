# Examples

These programs target the epoch-1 language in `LUCE_LANGUAGE_DESIGN.md`. The
compiler is still in its parsing phase, so the examples currently validate
source structure rather than execute.

- `hello.luc` is the smallest executable module.
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
epoch-1 compiler, then parse individual programs or the complete module set:

```sh
./build/luce build examples/language_tour.luc
./build/luce build examples/operators_and_literals.luc
./build/luce build examples/checkout/catalog.luc examples/checkout/pricing.luc examples/checkout/main.luc
./build/luce build examples/c_api.luc
./build/luce build examples/c_import/temperature.luc examples/c_import/main.luc
```

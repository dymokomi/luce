# Language Feature Coverage

The target is the epoch-1 source surface in `LUCE_LANGUAGE_DESIGN.md` §29.6.
Every syntax-tree form accepted by the current tokenizer and parser appears in
at least one parser-checked example. Runtime guarantees, package resolution, and
deliberately excluded syntax are outside this parser-era coverage claim.
The narrower `semantic_core/` fixture is also checked and interpreted.

| Surface | Examples |
| --- | --- |
| Module imports, aliases, and `from` imports | `checkout/main.luc`, `c_import/main.luc` |
| `pub` boundaries, private defaults, constants, aliases, and documentation | `language_tour.luc`, `checkout/catalog.luc` |
| Structs, mutating methods, defaults, and interface conformance | `language_tour.luc` |
| Payload enums (tagged unions), cases, and exhaustive matching | `language_tour.luc`, `checkout/pricing.luc` |
| Classes, identity, initialization, destruction, and weak edges | `language_tour.luc`, `operators_and_literals.luc` |
| Generic declarations, constraints, inferred and explicit arguments | `language_tour.luc` |
| Interface requirements, static constraints, and interface values | `language_tour.luc` |
| `let`, `var`, tuple binding, assignment, and every assignment operator | `language_tour.luc`, `operators_and_literals.luc` |
| `if`, `if let`, `elif`, `while`, `for`, `break`, and `continue` | `language_tour.luc`, `checkout/main.luc` |
| Statement and expression `match`, including `:` and `=>` arms | `language_tour.luc`, `checkout/pricing.luc` |
| Returns, calls as statements, `defer`, `try`, `catch`, and `recover` | `language_tour.luc` |
| Lists, maps, sets, fixed arrays, tuples, indexing, and all slice forms | `operators_and_literals.luc` |
| Lambdas, block closures, default/copy/weak capture, and function types | `language_tour.luc` |
| Conditional expressions, construction, generic calls, and labeled calls | `language_tour.luc` |
| Spawned named workers, task waiting, and cancellation | `language_tour.luc` |
| Boolean, absence, number, character, string, raw, formatted, triple, and byte literals | `operators_and_literals.luc` |
| Arithmetic, bitwise, range, comparison, identity, and Boolean operators | `operators_and_literals.luc` |
| Optional, fallible, combined, tuple, function, and applied types | `language_tour.luc`, `operators_and_literals.luc` |
| Static `test` declarations and assertions | `language_tour.luc`, `operators_and_literals.luc` |
| C import through generated raw bindings | `c_import/` |
| C struct, enum, and function export | `c_api.luc` |

Epoch 1 has no separate `union` declaration: payload enums are its closed
tagged unions. It also has no wildcard import; selective imports always name
the declarations they introduce.

# The Guide

One topic per chapter, each complete: where the Tour shows the common case, the Guide covers
every form, rule and exception, with the reasons where they are not obvious. The chapters can
be read in any order. Each one links to the matching part of the
[Reference](../../luce.md), the specification, for the exact rules.

1. [Syntax](01-syntax.md): layout, comments, names, and the words Luce reserves
2. [Types and values](02-types-and-values.md): the built-in types, inference, equality, printing and conversions
3. [Text and bytes](03-text-and-bytes.md): `str`, formatted strings, and `bytes`
4. [Collections](04-collections.md): `list`, `map`, `set` and tuples, with every operation
5. [Expressions](05-expressions.md): arithmetic, comparison, membership, precedence and assignment
6. [Control flow](06-control-flow.md): `if`, loops, labels, `match` and its patterns, `with`
7. [Functions](07-functions.md): parameters, methods, lambdas and closures
8. [Structs and enums](08-structs-and-enums.md): value types in full
9. [Classes and memory](09-classes-and-memory.md): objects, lifetime, cycles, weak references and resources
10. [Optionals and errors](10-optionals-and-errors.md): `T?`, `T!`, `catch`, `Result`, traps
11. [Interfaces and generics](11-interfaces-and-generics.md): interfaces, type parameters, the built-in interfaces
12. [Workers](12-workers.md): running work in parallel
13. [Modules and packages](13-modules-and-packages.md): files, imports, manifests, dependencies and publishing
14. [Testing](14-testing.md): `test` blocks and how they run
15. [The standard library](15-standard-library.md): what `luce-std` offers a Luce program
16. [Luce and Base](16-base.md): Base modules, what crosses between the languages, handles
17. [Tools](17-tools.md): the `luce` command, diagnostics, traps, builds and formatting

[Gotchas](gotchas.md) collects the surprises, each with a link to where it is explained.

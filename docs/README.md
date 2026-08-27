# Documentation

- [Luce 1.0 language](language/1.0.md) — the specification. It describes the
  whole 1.0 language; the implemented subset is listed under "What works
  today" in the [top-level README](../README.md).
- [Post-1.0 platform](language/post-1.0.md) — packages, C++, backends, and
  tooling deferred past 1.0, under the same section numbers.
- [Canonical MIR](compiler/mir.md) — the compiler's design record for the
  machine representation every compiled backend consumes: the decisions,
  the instruction set, and the order of work.

The specification is organised from the executive decision and complexity
budget, through source text, types, expressions, control flow, data modeling,
failure, concurrency, modules, and native interoperability, to the runtime,
tooling, exclusions, and a compact surface reference. See the headings in
`1.0.md`; the surface reference at the end is the fastest orientation.

After the specification, [the examples](../examples/README.md) show the same
language as runnable files, and [the tests](../tests/compiler) show what each
compiler stage accepts today.

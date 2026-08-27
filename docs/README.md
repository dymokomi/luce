# Documentation

- [Luce 1.0 language](language/1.0.md) — the specification. It describes the
  whole 1.0 language; the implemented subset is listed under "What works
  today" in the [top-level README](../README.md).
- [Post-1.0 platform](language/post-1.0.md) — packages, C++, backends, and
  tooling deferred past 1.0, under the same section numbers.
- [Compiler plan](compiler/plan.md) — where every layer stands, the
  decisions taken (MIR shape, WebAssembly, native backends, QBE, the
  linker, the runtime), the order of work, and the Stage-0 constraints.
  Start here to resume work.
- [Canonical MIR](compiler/mir.md) — the design record for the machine
  representation every compiled backend consumes: the decisions, the
  instruction set, and the reasons.

The specification is organised from the executive decision and complexity
budget, through source text, types, expressions, control flow, data modeling,
failure, concurrency, modules, and native interoperability, to the runtime,
tooling, exclusions, and a compact surface reference. See the headings in
`1.0.md`; the surface reference at the end is the fastest orientation.

After the specification, [the examples](../examples/README.md) show the same
language as runnable files, and [the tests](../tests/compiler) show what each
compiler stage accepts today.

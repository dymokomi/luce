# Documentation

- [Vision: From Machine Control to Human Intent](vision.md) — the directional
  proposal for how Luce can connect safe native execution, durable information,
  human-scale behaviors, AI-assisted authoring, and federation, with staged
  experiments and continuation gates.
- [Luce 1.0 language-gap audit](language/1.0-gap-audit.md) — the proposed
  language and compiler capabilities required by the wider operating-system
  vision, why each crosses the library boundary, and where each decision enters
  the implementation roadmap.
- [Luce 1.0 language](language/1.0.md) — the specification. It describes the
  whole 1.0 language; the implemented subset is listed under "What works
  today" in the [top-level README](../README.md).
- [Post-1.0 platform](language/post-1.0.md) — packages, C++, backends, and
  tooling deferred past 1.0, under the same section numbers.
- [Compiler plan](compiler/plan.md) — the decisions and what is next;
  its pair [Compiler record](compiler/done.md) says what exists, what each
  milestone proved, the bugs the harness caught, and where the project came
  from.
- [Recursion and stacks](compiler/recursion.md) — the promise that running
  out of stack is an error and not a crash, what other compilers do, and the
  phased work to get there.
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

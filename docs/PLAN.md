# Plan

What remains, in the order it is built. A slice closes when the gate is green with its
programs in, and nothing is written here about what was done: the tree and the suite are the
record. The compiler today lexes, parses, checks, interprets and compiles the whole of
`docs/luce.md`: the value language, classes, collections and text, closures, interfaces
and generics, modules and packages, the Base boundary, workers, the tooling, and traps that
name their statement, over the runtime of `docs/RUNTIME.md`, with four executions agreeing
on every conformance program and every run proving it left nothing alive.

The table is empty: every slice of the plan closed, and the next work is decided with the
language's author rather than listed here. What stands ready for it: `tests/programs/`
holds the proving programs, `tools/fuzz.py --minutes 60` runs the generator for an hour,
and the standing rules below hold for whatever comes next.

## Standing rules

- Two executions agree or the feature is not done.
- The interpreter is fixed first; the emitter follows it.
- Every rejection names a position; every literal is checked where it sits.
- luce-base is a pinned release; a change it needs is made there, released, and pinned.
- No history here: this file says what to do, `git log` says what was done.

Native compilation is the production path and the main hardening target. Prioritize
native ABI/optimizer checks and ARC/worker lifetime stress. Base C-backend comparisons
and sanitizer checks are supplemental evidence, not substitutes for native validation.

# Plan

What remains, in the order it is built. A slice closes when the gate is green with its
programs in, and nothing is written here about what was done: the tree and the suite are the
record. The compiler today lexes, parses, checks, interprets and compiles the whole of
`docs/luce.md`: the value language, classes, collections and text, closures, interfaces
and generics, modules and packages, the Base boundary, workers, the tooling, and traps that
name their statement, over the runtime of `docs/RUNTIME.md`, with four executions agreeing
on every conformance program and every run proving it left nothing alive.

| Slice | Scope | Gate |
| --- | --- | --- |
| 13. Proving programs and the generator | applications big enough to break a compiler; the fuzzer's generator widened to the whole language | each program under the gate; an hour of the generator clean |

## Standing rules

- Two executions agree or the feature is not done.
- The interpreter is fixed first; the emitter follows it.
- Every rejection names a position; every literal is checked where it sits.
- luce-base is a pinned release; a change it needs is made there, released, and pinned.
- No history here: this file says what to do, `git log` says what was done.

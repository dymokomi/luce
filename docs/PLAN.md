# Plan

What remains, in the order it is built. A slice closes when the gate is green with its
programs in, and nothing is written here about what was done: the tree and the suite are the
record. The compiler today lexes, parses, checks, interprets and compiles the value language
of §2 to §9 and §12, the classes of §10 and the collections and text of §11 over the runtime
of `docs/RUNTIME.md`, every text a counted object, closures over cells, with four
executions agreeing on every conformance program and every run proving it left nothing
alive.

| Slice | Scope | Gate |
| --- | --- | --- |
| 9. Trap positions | §17.2: base.md gains a position directive and traps that name their position; luce-base and the seed report `file:line:column` on every trap; luce's emitted Base carries the Luce position through the directive, so the interpreter and the compiled program trap alike (§15 modules, §16 the boundary, handles and `luce-base describe` are done) | trap programs whose `.trap` files name the position, in every execution |
| 10. Workers | §14 | §14 programs |
| 11. Tooling | §17: `luce test`, `luce fmt`, `luce doc`, `luce explain`, several diagnostics per run | §17 |
| 12. Proving programs and the generator | applications big enough to break a compiler; the fuzzer's generator widened to the whole language | each program under the gate; an hour of the generator clean |

## Standing rules

- Two executions agree or the feature is not done.
- The interpreter is fixed first; the emitter follows it.
- Every rejection names a position; every literal is checked where it sits.
- luce-base is a pinned release; a change it needs is made there, released, and pinned.
- No history here: this file says what to do, `git log` says what was done.

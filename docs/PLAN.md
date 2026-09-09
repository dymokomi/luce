# Plan

What remains, in the order it is built. A slice closes when the gate is green with its
programs in, and nothing is written here about what was done: the tree and the suite are the
record. The compiler today lexes, parses, checks, interprets and compiles the value language
of §2 to §9 and §12, with four executions agreeing on every conformance program.

| Slice | Scope | Gate |
| --- | --- | --- |
| 5. The runtime and classes | `rt/` to its contract; §10: classes, `init`, identity, destruction, `deinit`, `Weak`, the cycle collector; `with` | §10 programs, incl. what a run leaves alive |
| 6. Collections and text | §11: `list`, `map`, `set`, `str`, `bytes` and their operations, the iteration guard | §11 programs and traps |
| 7. Closures | §7.4: captures, cells, escaping closures | §7 programs |
| 8. Interfaces and generics | §13: conformance, interface values, bounds, the closed protocols, `for` over `Iterable` | §13 programs and rejections |
| 9. The Base boundary | §16: importing a Base module through luce-base's description, the crossings, handles; luce-base gains `pub handle`, the position directive and the description command first | §16 programs against a Base package in the tree |
| 10. Workers | §14 | §14 programs |
| 11. Tooling | §17: `luce test`, `luce fmt`, `luce doc`, `luce explain`, several diagnostics per run | §17 |
| 12. Proving programs and the generator | applications big enough to break a compiler; the fuzzer's generator widened to the whole language | each program under the gate; an hour of the generator clean |

## Standing rules

- Two executions agree or the feature is not done.
- The interpreter is fixed first; the emitter follows it.
- Every rejection names a position; every literal is checked where it sits.
- luce-base is a pinned release; a change it needs is made there, released, and pinned.
- No history here: this file says what to do, `git log` says what was done.

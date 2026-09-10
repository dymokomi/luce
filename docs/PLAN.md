# Plan

What remains, in the order it is built. A slice closes when the gate is green with its
programs in, and nothing is written here about what was done: the tree and the suite are the
record. The compiler today lexes, parses, checks, interprets and compiles the whole of
`docs/luce.md`: the value language, classes, collections and text, closures, interfaces
and generics, modules and packages, the Base boundary, workers, the tooling, and traps that
name their statement, over the runtime of `docs/RUNTIME.md`. The conformance gate
checks native optimization levels 0–3, both Base C comparison modes, and the interpreter
where applicable; every runtime execution checks that it left nothing alive.

The active stage is **luce-server**. Base standard-library work shipped in 0.12.0;
TLS is paused at the user's request while HTTP and file serving proceed. The canonical [ecosystem roadmap](https://github.com/dymokomi/luce-base/blob/main/docs/ECOSYSTEM.md)
defines each stage's completion gate. Standard-library work stays in `luce-base`;
`luce-tls`, `luce-server` and `luce-pkg` are three separate new repositories,
created as their work begins. The server is written in Luce. The package-manager
stage adds `luce install` and `luce-base install`, a shared `luce.yaml` manifest with
explicit migration from `luce.toml`, and deployment to `pkg.luciaos.com`.
The package manager still requires both server and TLS completion; compiler/runtime
changes are made as needed to support the active stage. What stands ready for it: `tests/programs/`
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

## Interpreter stack budget

The server's JSON regression on 2026-09-10 exposed a native-built interpreter stack
overflow at 65 nested arrays, before the JSON parser could report its configured
64-level limit. The compiled Luce program accepts depth 64 and rejects depth 65 as
expected. LLDB stops at `Interp.member`'s frame prologue on the default macOS stack;
that function alone reserves 12,656 bytes. The interpreter's current logical call
limit of 4,000 does not protect its physical stack. Reduce interpreter frame pressure
and make exhaustion diagnostic; retain the server nesting case as a regression.
This does not block the native HTTP server or reduce its JSON depth contract.

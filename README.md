# Luce

Luce is a work-in-progress systems programming language. The goal is simple:
Luce code is easy to read, its behavior is predictable, and talking to C is
straightforward. The compiler follows the same rule. You can open a source file
and understand what it is doing without an archaeological dig.

This repository is where Luce 1.0 and its compiler are being built. The compiler
is written in Luce and is bootstrapped with a small, frozen
[Stage-0 toolchain](https://github.com/dymokomi/luce-stage-0).

Luce is under active development. It is not a production-ready language yet.
The frontend understands most of the planned 1.0 source language, while the
parts that can be type-checked, run, and compiled are growing in smaller
end-to-end slices. Unsupported features fail with a clear diagnostic.

## Getting started

The bootstrap script supports Apple silicon macOS and x86-64 Linux. It downloads
Stage-0 0.28 and the official QBE 1.3 source, verifies both checksums, and builds
the QBE oracle. `./stage0` is the resulting pinned toolchain, not this
repository's source.

```sh
./bootstrap.sh
./build.sh
./test.sh
```

`stage0/VERSION` reports the installed toolchain version.

The compiler is now available at `build/luce`. It can check source files, run a
function through the HIR interpreter, or build an artifact:

```sh
./build/luce check --package org.luce.examples examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce run --package org.luce.examples main.answer examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce build --package org.luce.examples build/answer.wasm examples/compiled_core/main.luc
```

The package identity is explicit because it is embedded in stable `ErrorCode`
values. It must remain the same when the source tree moves.

Features backed by the reviewed Luce runtime pass its source explicitly; the
compiler owns the sealed service manifest, so callers provide locations only:

```sh
./build/luce build --package org.luce.examples --runtime src/runtime/allocator.native.luc build/strings.wasm examples/strings.luc
```

Native output uses the pinned QBE toolchain for the current host:

```sh
./build/luce build --package org.luce.examples --target native build/hello examples/hello.luc
./build/hello
```

`bootstrap.sh` installs QBE; the host C driver supplies assembly and linking.

## Vocabulary

A few terms recur in the source and in this README:

- **Stage-0** — the frozen seed compiler in `./stage0` that builds this
  repository. The compiler source must stay inside the language subset it
  understands until Luce can build itself.
- **HIR** — the High-level Intermediate Representation: source after names and
  types have meaning (`src/compiler/hir/ir.luc`). The interpreter runs it directly.
- **MIR / canonical IR** — the flat, target-independent instruction stream the
  compiled backends consume (`src/compiler/mir/canonical.luc`).
- **Slice** — the part of the 1.0 language a stage implements today. The parser
  covers most of 1.0; HIR generation, the interpreter, and the compiled path
  each cover a smaller, growing slice.
- **Artifact** — the file `luce build` installs: a WebAssembly module or a
  native executable.

## What works today

This section is the single description of what each stage implements; the
examples and tests link back here rather than restating it.

- The tokenizer and parser cover the planned 1.0 grammar, including
  indentation-based layout, declarations, types, control flow, patterns,
  closures, generics, and the C boundary syntax.
- HirGenerator produces typed HIR with stable symbol and type identities. The
  currently executable language slice includes functions, calls, parameter
  defaults, bindings, assignment, scalars, strings, checked byte indexing and
  byte-sequence lengths, fixed arrays, reference lists (literals, shared
  identity, length, checked get/set, append, insert, removal, clear, and
  reserve, plus shallow independent copies and immutable snapshots), tuples,
  optionals,
  structs with memberwise or custom (including fallible) initialization,
  enums, methods and `mutating`, exhaustive `match`,
  constants, type aliases, conditionals, integer ranges and `for`, lexical
  `defer`, recoverable `Error` values with `try`/`catch`, nominal pointer- and
  integer-represented C handles, C `out` parameters as ordinary results,
  loops, and returns.
- The HIR interpreter is the reference implementation of language behavior for
  the slice it supports.
- Canonical MIR is designed for the whole language (typed registers,
  explicit memory with structural aggregates, target-neutral control flow, calls to a
  named runtime, failure as data — see [docs/compiler/mir.md](docs/compiler/mir.md))
  and has a verifier and its own interpreter covering every instruction.
- The compiled slice — every scalar type with checked arithmetic, locals,
  every operator, `if`/`while`, functions and calls across modules, module
  constants, tuples, optionals, integer ranges and `for`, structs (including
  custom initialization), enums and `match`, methods, lexical `defer`,
  caller-owned failure propagation and recovery, `str`/`bytes` values with
  equality, `bytes.length`, checked `bytes[index]`, `str.byte_count`, fixed
  value arrays with contextual literals, structural equality, copies,
  checked indexing and nested mutable places, plus runtime-backed list
  literals, identity, checked access and shape mutation, aggregate elements,
  growth, shallow copies, immutable snapshot slices, ordered list iteration
  with alias-wide shape-mutation invalidation, and collection-recursive
  value shapes with structural retain/release and storage reclamation, direct
  scalar C imports/exports and variables with nominal integer and pointer
  handles (including boundary-only null translation), ordered `out` results,
  exact named C-callable values with generated adapters or extern addresses,
  and `print` of a
  literal or a `str` value — is lowered to canonical
  MIR and encoded as WebAssembly and QBE IL. The complete list runtime executes
  through QBE and Wasm; each backend supplies its stable arena and legalizes
  target layout only after canonical MIR.
  The complete differential corpus is compiled, linked, and executed through
  QBE 1.3 as both the native oracle and the product native path. QBE IL and
  assembly travel through memory; only a candidate executable is written in a
  uniquely owned same-directory scratch area, then atomically renamed over the
  destination. Native executables start at `main`; MIR keeps package `pub`
  visibility separate from explicit artifact exports. Wasm exposes the
  package API, while QBE exports only the entry and explicit C boundaries.
- The test suite exercises the frontend, semantic model, both interpreters,
  lowering, MIR verification, each artifact encoder, the command line's exit
  statuses and diagnostics, and runs every fixture through the HIR
  interpreter, the MIR interpreter, and real QBE to prove they agree. On
  a supported native host it also builds and
  runs a smoke-test executable.

The parser is ahead of HIR generation and backends. A
program appearing in the language tour does not necessarily mean every stage
can execute it yet.

## Running and adding tests

`./test.sh` runs everything: the unit tests, the command-line contract, and a
native smoke test on a supported host. To run one file:

```sh
./stage0/bin/luce-0 test tests/compiler/frontend/parser_test.luc
```

A test is a zero-argument `pub func test_*` function; Stage-0 discovers them
by name. `tests/luce.yaml` maps the `luce.compiler.*` imports used by the tests
onto `../src`, so tests exercise the compiler source directly. Add a new test
next to the stage it proves, under the `# mark:` section that matches its
topic.

## Where to go next

Read in this order; each stop hands off to the next.

1. [docs/README.md](docs/README.md) introduces the design documents; the
   [compiler plan](docs/compiler/plan.md) is where to resume work, and its pair
   [done.md](docs/compiler/done.md) is where to check what exists.
   [The language design](docs/language/1.0.md) is the 1.0 specification, not a
   description of what happens to be implemented today; [the post-1.0
   notes](docs/language/post-1.0.md) hold ideas outside the current language.
2. [The examples](examples/README.md) show the source language, the
   executable semantic slice, and the small compiled slice as runnable files.
3. [pipeline.luc](src/compiler/pipeline.luc) is the shortest useful tour of
   the compiler. Its `build`, `check`, and `run` functions show how the stages
   fit together, and every stage file's header says where it sits.
4. [tests/compiler](tests/compiler) holds precise examples of what each stage
   currently accepts, rejects, and produces; each file's sections read as that
   stage's specification.

## Finding your way around

- `src/luce.luc` is the command-line program.
- `src/compiler/frontend/` owns source spans, tokens, syntax, and parsing.
- `src/compiler/hir/` turns syntax into resolved, typed program meaning and
  owns semantic flow analysis.
- `src/compiler/runtime_contract.luc` is the target-neutral service vocabulary
  shared by sealed-package binding, HIR, and MIR.
- `src/compiler/backends/interpreter.luc` runs typed HIR directly.
- `src/compiler/mir/` owns lowering, canonical MIR, verification, and
  target-independent optimization.
- `src/compiler/backends/` contains the Wasm emitter, QBE emitter and host
  materializer, backend-owned layout, and the two semantic execution engines.
- `src/runtime/` is the separately compiled freestanding Luce runtime; it owns
  checked allocation, typed reclamation and block reuse, plus the ownership
  and collection policy being built above the backend arena.

## Contributing constraints

- Compiler source must remain buildable by the Stage-0 language subset until
  Luce can reliably build itself without that seed compiler. If Stage-0
  rejects a construct, rewrite the construct rather than waiting for 1.0.
- When Stage-0 miscompiles a construct, reproduce it in a five-line program,
  fix Stage-0, and bump `bootstrap.sh`; do not work around it in the
  compiler source.
- Every stage fails with a `path:line:column:` diagnostic or a stage-prefixed
  message for anything outside its slice; never let unsupported input trap.

Luce is dual-licensed under Apache 2.0 and MIT. See [LICENSE](LICENSE).

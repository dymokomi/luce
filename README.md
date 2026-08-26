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
end-to-end slices. Unsupported features fail with a clear diagnostic instead
of silently doing the wrong thing.

## Getting started

The bootstrap script supports Apple silicon macOS and x86-64 Linux. It downloads
Stage-0 0.21, the pinned seed compiler for the current machine, and verifies its
checksum. `./stage0` is that downloaded toolchain, not this repository's source.

```sh
./bootstrap.sh
./build.sh
./test.sh
```

The compiler is now available at `build/luce`. It can check source files, run a
function through the HIR interpreter, or build an artifact:

```sh
./build/luce check examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce run main.answer examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce build build/answer.wasm examples/compiled_core/main.luc
```

Native output is also available for Apple silicon macOS and x86-64 Linux:

```sh
./build/luce build --target arm64-macos build/hello examples/hello.luc
./build/luce build --target x86_64-linux build/hello examples/hello.luc
```

Use the target that matches the machine where the executable will run.

## What works today

- The tokenizer and parser cover most of the planned 1.0 grammar, including
  indentation-based layout, declarations, types, control flow, patterns,
  closures, generics, and the C boundary syntax.
- The checker produces typed HIR with stable symbol and type identities. The
  currently executable language slice includes functions, calls, bindings,
  assignment, basic scalar operations, conditionals, loops, and returns.
- The HIR interpreter is the reference implementation of language behavior for
  the slice it supports.
- The compiled slice lowers to a small canonical MIR and can be emitted directly
  as WebAssembly, ARM64 Mach-O, or x86-64 ELF.
- The test suite exercises the frontend, semantic model, interpreter, lowering,
  MIR verification, and each artifact encoder. On a supported native host it
  also builds and runs a smoke-test executable.

The parser is intentionally ahead of the semantic checker and backends. A
program appearing in the language tour does not necessarily mean every stage
can execute it yet.

## Where to go next

- Read [the language design](docs/language/1.0.md) for the current 1.0
  language. It is the specification, not a description of what happens to be
  implemented today.
- Read [the post-1.0 notes](docs/language/post-1.0.md) for ideas that are
  deliberately outside the current language.
- Browse [the examples](examples/README.md) to see the source language, the
  executable semantic slice, and the small compiled slice.
- Open [pipeline.luc](src/compiler/pipeline.luc) for the shortest useful tour of
  the compiler. Its `build`, `check`, and `run` functions show how the stages fit
  together.
- Look under [tests/compiler](tests/compiler) for precise examples of what each
  stage currently accepts, rejects, and produces.

## Finding your way around

- `src/luce.luc` is the command-line program.
- `src/compiler/source.luc` is the shared source span and diagnostic format.
- `src/compiler/tokenizer.luc`, `parser.luc`, and `syntax.luc` are the source
  frontend.
- `src/compiler/checker.luc` and `hir.luc` turn source syntax into resolved,
  typed program meaning.
- `src/compiler/semantic_analyzer.luc` is the home for flow, effect, and
  ownership analysis as those checks are implemented.
- `src/compiler/backends/interpreter.luc` runs typed HIR directly.
- `src/compiler/lowerer.luc`, `canonical_ir.luc`, `mir_verifier.luc`, and
  `optimizer.luc` form the target-independent compiled path.
- `src/compiler/backends/` contains the WebAssembly, Mach-O, and ELF emitters.

Compiler source must remain buildable by the pinned Stage-0 language subset
until Luce can reliably build itself without that seed compiler.

Luce is dual-licensed under Apache 2.0 and MIT. See [LICENSE](LICENSE).

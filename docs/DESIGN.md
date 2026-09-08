# Design

Luce is written in Luce Base and compiled by luce-base. This document is the shape of the
compiler; `luce.md` is the language and is right where the two disagree.

## The chain

```text
luce-seed   C++      builds luce-base once; nothing else ever touches it
luce-base   Base     the systems language: compiler, std, targets, the only door to C
luce        Base     this tree: front end, interpreter, Base emitter, the runtime, the facades
an app      Luce     plus any Base packages it imports, built as one Base package
```

`bootstrap/BASE` names the luce-base release this tree is written against. `build.sh` builds
that release from its tag into `build/luce-base/`, so the compiler this tree uses is never a
binary another tree's gate may be rewriting, and a build here depends on a tag, not on a
working directory.

## The pipeline

```text
source (.luc)
  -> tokens and layout          front.lexer
  -> syntax tree                front.parser
  -> typed tree                 sema.check, sema.bodies    -> hir.interp   (luce run)
  -> Base package               back.base, back.package    -> luce-base    (luce build)
```

The compiler is a front end and a translator. It has no backend, no target, no linker, no
allocator, and no C. Its whole output is a Base package: the program's modules written as
Base, the runtime, and the Base modules the program imported, which luce-base compiles as
the one package they are. `luce build --emit=base` keeps the package, and it is the first
thing to read when a program misbehaves.

## Two executions

1. **The interpreter** executes the typed tree directly. It is the definition of behaviour,
   it is `luce run`, and it shares no code with the emitter: it models objects, collections
   and text as semantic values and never sees an address.
2. **The emitted Base**, through every generator luce-base has: C, C under `-O2`, and native.

A feature is implemented when both print the same bytes for its programs and trap for the
same reason on its trapping programs. The fuzzer's generator writes programs the language
admits and demands the same agreement, from the first slice.

## What the language needs that Base does not have

| Luce | Where |
| --- | --- |
| classes, identity, destruction | the runtime's object header, retain and release, the cycle collector; the emitter places every retain and release |
| `list`, `map`, `set`, owned `str`, `bytes` | generic Base types in the runtime; the emitter names them, never their storage |
| closures | an environment struct per closure and a shared cell per captured `var`, both runtime objects |
| interface values | an object holding the payload and a Base interface view into it |
| generics | Base generics, one to one; luce-base instantiates |
| `T?`, `T!`, traps, arithmetic | Base's own, which mean the same; `/` on `int` and `**` are the two the emitter spells out |
| workers | the runtime's workers over Base's threads; the checker proves sendability |
| handles | a Base `pub handle`, seen as a class whose `close` is its `destroy` |

## Modules

`src/<area>/<module>.lucb`, one file per concern.

| Module | Owns |
| --- | --- |
| `front.source` | file bytes, positions, the encoding gate |
| `front.token`, `front.lexer` | tokens, layout, the bounds of §2 |
| `front.ast`, `front.parser` | the tree and the grammar of §19 |
| `sema.types` | the type table: interned ids, spellings, structural facts |
| `sema.check` | declarations, imports, visibility, cycles, resolution |
| `sema.bodies` | every statement and expression typed, with initialisation, exhaustiveness, generics, conformance and capture |
| `sema.base` | what a Base module offers, read from luce-base's description of it |
| `hir.value`, `hir.interp` | the interpreter |
| `back.base`, `back.package` | the typed tree as Base; the package handed to luce-base |
| `support.*` | list, buffer, the version, the runtime's embedded source |
| `main` | the `luce` command |

## The runtime

`rt/` is a Base package compiled by luce-base with the program. It provides the object
header, retain and release, the cycle collector, the weak table, `deinit` dispatch, owned
text and bytes, the three collections, closure cells, workers, and the trap reporter, and
nothing else. `docs/RUNTIME.md` is its written contract once it exists.

## Diagnostics and robustness

Every diagnostic is `file:line:column: message`. A rejection is exit status 1; a crash, a
hang or a bare message is a defect. Nesting has a stated bound, identifiers have a stated
length, every literal is checked where it sits, a file's name is an identifier, and the
fuzzer's mutate mode enforces all of it from slice 1.

## The harness

`tests/conformance/NN_chapter/` mirrors `luce.md`: a program beside its `.expect` runs through
both executions; one beside a `.trap` must trap with that text on both; one under `errors/`
must be rejected with the diagnostic its `# error:` line names, at a position. `test.sh` is
the gate and the only truth: it builds, runs every module's tests, the conformance suite, the
proving programs, and the fuzzer's short pass, and it is green or the tree does not move.

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
| interface values | a box: an object holding the payload behind a table of the conforming type's methods, one table per interface and type |
| generics | instantiated by the checker: one copy of a generic function per distinct type arguments, checked with the parameters bound, so the interpreter and the emitter see only concrete declarations |
| `T?`, `T!`, traps, arithmetic | Base's own, which mean the same; `/` on `int` and `**` are the two the emitter spells out |
| workers | the runtime's workers over Base's threads; the checker proves sendability |
| handles | a Base `pub handle`, seen as a class whose `close` is its `destroy` |
| the Base boundary | what `luce-base describe` prints of a module, read into bodiless declarations; a shim per Base function converts at the crossing, so a call into Base is an ordinary call |

## Modules

`src/<area>/<module>.lucb`, one file per concern.

| Module | Owns |
| --- | --- |
| `front.source` | file bytes, positions, the encoding gate |
| `front.token`, `front.lexer` | tokens, layout, the bounds of §2 |
| `front.ast`, `front.parser` | the tree and the grammar of §19 |
| `sema.types` | the type table: interned ids, spellings, structural facts |
| `sema.check` | declarations, imports, visibility, cycles, resolution |
| `sema.boundary`, `sema.native_availability` | public Base descriptions and availability across imported declarations |
| `back.crossings` | native conversions, borrowed spans, owning result carriers and their queued support functions |
| `back.native_types` | native signature identity and type-node construction |
| `back.emission` | shared output, type spelling and lifetime-function registration |
| `back.native_objects`, `back.native_interfaces` | canonical owner layouts and interface witness storage |
| `back.native_callbacks` | retained callable layouts, tracing and callback round trips |
| `sema.transfer` | shared task/worker transfer rules and native worker payload validation |
| `sema.bodies` | every statement and expression typed, with initialisation, exhaustiveness, generics, conformance and capture |
| `sema.base` | what a Base module offers, read from luce-base's description of it |
| `hir.value`, `hir.interp` | the interpreter |
| `back.base`, `back.package` | the typed tree as Base; the package handed to luce-base |
| `support.*` | list, buffer, the version, the runtime's embedded source |
| `main` | the `luce` command |

## The runtime

`rt/` is a Base package compiled by luce-base with the program. It provides the object
header, retain and release, the temporaries pool, the cycle collector, weak references,
`deinit` dispatch, owned text and bytes, the three collections, closure cells, workers, and
the trap reporter, and nothing else. `docs/RUNTIME.md` is its written contract, and the
interpreter follows the same contract so that the two executions destroy objects in the same
order.

## Diagnostics and robustness

Every diagnostic is `file:line:column: message`. A rejection is exit status 1; a crash, a
hang or a bare message is a defect. Nesting has a stated bound, identifiers have a stated
length, every literal is checked where it sits, a file's name is an identifier, and the
fuzzer's mutate mode enforces all of it.

## The harness

`tests/conformance/NN_chapter/` mirrors `luce.md`: a program beside its `.expect` runs through
both executions; one beside a `.trap` must trap with that text on both; one under `errors/`
must be rejected with the diagnostic its `# error:` line names, at a position. `test.sh` is
the gate and the only truth: it builds, runs every module's tests, the conformance suite, the
proving programs, and the fuzzer's short pass, and it is green or the tree does not move.


## Packaging Base dependencies

Before writing an emitted package, Luce asks the pinned Base compiler for each
imported module's resolved source dependency closure. The versioned, NUL-delimited
`dependencies` response preserves path bytes and uses Base's parser and resolver.
`back.sources` owns and deduplicates the collected source bytes; different contents
under the same module name are diagnosed before output is created. The source set
is released after emission, including acquisition and protocol failures.

`back.package` writes the complete set under its original dotted module paths.
Private dependencies remain byte-for-byte unchanged. The emitter gives every direct
Base import an explicit alias based on its checker module index, so dotted paths and
identical leaf names do not become ambiguous Base references.

Generated entry and runtime names are chosen after collecting those paths. The usual
layout is `main.lucb` and `rt/`; when imported source owns those names, generation
selects unused names and updates only generated runtime imports. `--emit=base` prints
the actual generated entry path. Executables and built test runners use the same
collection and naming rules, and emitted packages rebuild after relocation without
the original Base source tree. This source query does not resolve native libraries
or implement package-manager dependency selection.

Normal builds and compiled test runners use `back.workspace`: one uniquely
created directory beneath `TMPDIR` (or `/tmp`). The owner removes generated Base,
runtime modules, copied dependencies, and partial tool output on success or
failure. Cleanup never adopts an existing `OUT.base` directory and does not follow
symlinks into other source trees. `--emit=base` explicitly writes a persistent
package at `OUT.base` instead. The final executable stays at the requested path.

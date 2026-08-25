# Luce

Luce is the epoch-1 compiler, written in the language it is building. The
frozen [Stage-0 0.19 toolchain](https://github.com/dymokomi/luce-stage-0)
provides the seed compiler and differential oracle.

## Mental model

```text
source -> Tokenizer -> Parser -> Checker -> typed HIR -> SemanticAnalyzer
                                                       |-> HirInterpreter -> value
                                                       \-> Lowerer -> canonical MIR
                                                                    -> MirVerifier
                                                                    -> Optimizer
                                                                    -> MirVerifier
                                                                    -> ArtifactBackend -> bytes
```

- `luce.luc` owns the command-line interface.
- `pipeline.luc` is the visible compiler spine and composes every stage.
- `tokenizer.luc` turns source text into layout-aware tokens.
- `parser.luc` validates grammar and builds the source-faithful tree in
  `syntax.luc`.
- `checker.luc` resolves module and lexical names, checks the implemented type
  rules, and produces `hir.luc`.
- `hir.luc` is the semantic center: program-wide functions and symbols,
  canonical type identities, resolved operations, structured effects, and
  source spans in one readable representation.
- `semantic_analyzer.luc` is the permanent flow/effect/ownership boundary; it
  currently preserves the HIR data but returns a distinct `AnalyzedProgram`, so
  execution and lowering cannot bypass that boundary.
- `lowerer.luc` fixes evaluation order in the backend-independent instruction
  stream defined by `canonical_ir.luc`.
- `mir_verifier.luc` checks canonical MIR before and after `optimizer.luc`.
- `backend.luc` defines separate execution and artifact boundaries.
- `backends/interpreter.luc` executes HIR by semantic tags and resolved symbol
  identity, independently of MIR lowering.
- `backends/wasm.luc` directly encodes canonical instructions as WebAssembly.
- `backends/arm64_macos.luc` directly encodes ARM64 instructions and Mach-O.
- `tests/` is a separate Stage-0 package containing only tests.

The parser covers the epoch-1 source surface. The executable vertical slice is
currently `bool`, `i64`, `f64`, and `unit` functions with calls, bindings,
assignment, basic operators, `if`, `while`, and returns. Other parsed forms fail
explicitly until their semantic rules are implemented.

The compiled slice is intentionally tiny: integer literals, `+`, `-`, `*`,
constant `print`, and `return`. WebAssembly covers zero-argument `i64`
functions; the direct Apple-silicon path covers the conventional
`main(slice[str]) -> i32 uses terminal` entry. Unsupported lowering fails
explicitly so both paths remain readable end to end.

## Develop

```sh
./bootstrap.sh
./stage0/bin/luce-0 check src/luce.luc
./test.sh
mkdir -p build
./stage0/bin/luce-0 build src/luce.luc -o build/luce
./build/luce check examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce run main.answer examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce build build/answer.wasm examples/compiled_core/main.luc
./build/luce build --target arm64-macos build/hello examples/hello.luc
./build/hello
node -e 'const fs=require("node:fs"); WebAssembly.instantiate(fs.readFileSync("build/answer.wasm")).then(({instance}) => console.log(instance.exports["main.answer"]().toString()))'
```

Tests import source through the local `luce` package declared in
`tests/luce.yaml`. They test public contracts; private helpers remain private
and are covered through the behavior that uses them. No Stage-0 test-access
exception is required.

`LUCE_LANGUAGE_DESIGN.md` is the normative epoch-1 specification. Source under
`src/` must still use the Stage-0 0.19 subset so the seed compiler can
build it.

## Examples

`examples/` contains epoch-1 programs ranging from `hello.luc` to multi-module
and native-C interop examples. They are parsed as part of the test suite; see
`examples/FEATURES.md` for complete source-surface coverage.

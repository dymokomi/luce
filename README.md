# Luce

Luce is the epoch-1 compiler, written in the language it is building. The
frozen [Stage-0 0.19 toolchain](https://github.com/dymokomi/luce-stage-0)
provides the seed compiler and differential oracle.

## Mental model

```text
source -> Tokenizer -> Parser -> Checker -> typed IR -> ExecutionBackend -> value
                                            \-> Lowerer -> canonical IR
                                                           -> ArtifactBackend -> bytes
```

- `luce.luc` owns the command-line interface.
- `pipeline.luc` is the visible compiler spine and composes every stage.
- `tokenizer.luc` turns source text into layout-aware tokens.
- `parser.luc` validates grammar and builds the source-faithful tree in
  `syntax.luc`.
- `checker.luc` resolves module and lexical names, checks the implemented type
  rules, and produces `typed_ir.luc`.
- `lowerer.luc` fixes evaluation order in the backend-independent instruction
  stream defined by `canonical_ir.luc`.
- `backend.luc` defines separate execution and artifact boundaries.
- `backends/interpreter.luc` executes typed IR by resolved symbol identity.
- `backends/wasm.luc` directly encodes canonical instructions as WebAssembly.
- `tests/` is a separate Stage-0 package containing only tests.

The parser covers the epoch-1 source surface. The executable vertical slice is
currently `bool`, `i64`, `f64`, and `unit` functions with calls, bindings,
assignment, basic operators, `if`, `while`, and returns. Other parsed forms fail
explicitly until their semantic rules are implemented.

The initial compiled slice is intentionally tiny: zero-argument `i64`
functions with literals, `+`, `-`, `*`, and `return`. Unsupported lowering
fails explicitly. This keeps the complete source-to-WASM path small enough to
read end to end before the canonical IR grows.

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

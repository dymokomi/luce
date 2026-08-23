# Luce

Luce is the epoch-1 compiler, written in the language it is building. The
frozen [Stage-0 0.19 toolchain](https://github.com/dymokomi/luce-stage-0)
provides the seed compiler and differential oracle.

## Mental model

`luce.luc` → `pipeline.luc` → `Tokenizer` → `Parser` → `Checker` → typed IR → `ExecutionBackend`

- `luce.luc` owns the command-line interface.
- `pipeline.luc` applies compiler stages to each input file.
- `tokenizer.luc` turns source text into layout-aware tokens.
- `parser.luc` validates grammar and builds the source-faithful tree in
  `syntax.luc`.
- `checker.luc` resolves module and lexical names, checks the implemented type
  rules, and produces `typed_ir.luc`.
- `backend.luc` defines the swappable execution boundary used by `luce run`.
- `interpreter.luc` is the default backend and executes typed IR by resolved
  symbol identity.
- `*_test.luc` files sit beside the code they test.

The parser covers the epoch-1 source surface. The executable vertical slice is
currently `bool`, `i64`, `f64`, and `unit` functions with calls, bindings,
assignment, basic operators, `if`, `while`, and returns. Other parsed forms fail
explicitly until their semantic rules are implemented.

`ExecutionBackend` covers running a checked program. Artifact production will
get a separate boundary after canonical IR exists, so C/JS emitters are not
forced into an interpreter-shaped API.

## Develop

```sh
./bootstrap.sh
./stage0/bin/luce-0 check src/luce.luc
./stage0/bin/luce-0 test src
mkdir -p build
./stage0/bin/luce-0 build src/luce.luc -o build/luce
./build/luce check examples/semantic_core/math.luc examples/semantic_core/main.luc
./build/luce run main.answer examples/semantic_core/math.luc examples/semantic_core/main.luc
```

`LUCE_LANGUAGE_DESIGN.md` is the normative epoch-1 specification. Source under
`src/` must still use the Stage-0 0.19 subset so the seed compiler can
build it.

## Examples

`examples/` contains epoch-1 programs ranging from `hello.luc` to multi-module
and native-C interop examples. They are parsed as part of the test suite; see
`examples/FEATURES.md` for complete source-surface coverage.

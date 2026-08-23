# Luce

Luce is the epoch-1 compiler, written in the language it is building. The
frozen [Stage-0 0.19 toolchain](https://github.com/dymokomi/luce-stage-0)
provides the seed compiler and differential oracle.

## Mental model

`src/luce.luc` → `src/compiler/pipeline.luc` → `src/compiler/tokenizer.luc`

- `luce.luc` owns the command-line interface.
- `pipeline.luc` applies compiler stages to each input file.
- `tokenizer.luc` turns source text into layout-aware tokens.
- `*_test.luc` files sit beside the code they test.

The compiler is intentionally early: `luce build` currently reads and tokenizes
each input. New stages should extend the pipeline without leaking compiler logic
into the CLI.

## Develop

```sh
./bootstrap.sh
./stage0/bin/luce-0 check src/luce.luc
./stage0/bin/luce-0 test src
mkdir -p build
./stage0/bin/luce-0 build src/luce.luc -o build/luce
```

`LUCE_LANGUAGE_DESIGN.md` is the normative epoch-1 specification. Source under
`src/` must still use the Stage-0 0.19 subset so the seed compiler can
build it.

# Calling C from Luce

This example follows the native pipeline in the language design:

```text
temperature.h -> luce bind -> temperature.raw -> temperature.luc -> main.luc
```

- `temperature.c` and `temperature.h` are the native library.
- `../luce.toml` declares the `temperature` C binding target.
- `temperature/raw.native.luc` and `temperature.adapter.c` are generated from
  the header and are not checked in.
- `temperature.luc` performs explicit `c.double` conversions and exposes a
  safe Luce-facing function.
- `main.luc` selectively imports and calls the Luce-facing function.

The first executable importer rung supports exact IEEE binary64 C `double`.
It records Clang's target and scalar facts in FIIR, generates a nominal
`c.double` raw module plus a checked C adapter, and links that adapter only at
the QBE backend boundary. Integer types, pointers, records, recipes, and the
f16 shim remain explicit generation errors until their complete contracts are
implemented.

Generate the binding products with explicit destinations:

```sh
mkdir -p build/temperature
./build/luce bind --name temperature \
  --fiir build/temperature.fiir.json \
  --raw build/temperature/raw.native.luc \
  --adapter build/temperature.adapter.c \
  --clang-arg -std=c11 \
  examples/c_import/temperature.h
```

The CLI regression suite then builds and runs this example through the real
QBE product path with `src/standard/c.luc`, the generated raw module and
adapter, and `temperature.c` supplied as distinct inputs. Keeping each input
visible is intentional: package/manifest discovery is deferred past 1.0, and
the compiler does not guess source roots, sidecar names, include paths, or
libraries.

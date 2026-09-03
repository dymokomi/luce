# Calling C from Luce

This example follows the native pipeline in the language design:

```text
temperature.h -> luce bind -> temperature.raw -> temperature.luc -> main.luc
```

- `temperature.c` and `temperature.h` are the native library.
- `../luce.toml` declares the `temperature` C binding target.
- `temperature/raw.native.luc` and `temperature.adapter.c` are generated from
  the header and are not checked in.
- `temperature.luc` performs explicit `c.boolean`, `c.float`, `c.double`,
  `c.int`, generated `luce_degrees`, and generated
  `luce_temperature_scale` crossings, plus a generated anonymous-enum integer
  constant and fieldwise simple/nested record crossings, and exposes safe
  Luce-facing functions.
- `main.luc` selectively imports and calls the Luce-facing function.

The executable importer supports C `_Bool`, exact IEEE binary32 `float`, exact
IEEE binary64 `double` and `long double`, and every fundamental C integer
family, plus scalar typedef chains over those types. It records Clang's target
and scalar facts in FIIR, and also accepts named or typedef-backed C enums. It
generates nominal `c`, typedef, and sign-magnitude enum carriers plus a checked
C adapter, and links that adapter only at the QBE backend boundary. Plain named
or anonymous-typedef C records become logical Luce records and private
fixed-carrier adapter records; Clang-evaluated layout stays in FIIR and the C
product. A constant-only anonymous enum contributes universal
sign-and-magnitude constants
instead of an unusable synthetic type or a target-selected integer carrier.
Boolean retains one Luce `bool` shape; floating types retain `f32` or `f64`;
integer and typedef carriers retain one lossless portable shape; enum carriers
retain one `bool` plus `u64` shape and expose the header's constants. The
adapter alone asserts scalar representations, verifies integer target ranges,
maps declared enum values to the target's exact C type, and verifies record
size, alignment, offsets, and field types. Extended floating formats, pointers,
unions, bit-fields, macro/object constants, recipes, and the f16 shim remain
explicit generation errors until their complete contracts are implemented.

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

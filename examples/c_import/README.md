# Calling C from Luce

This example follows the native pipeline in the language design:

```text
temperature.h + temperature.recipe.toml -> luce bind
    -> FIIR + temperature.raw + temperature.safe + C adapter
    -> handwritten Luce boundaries -> main.luc
```

- `temperature.c` and `temperature.h` are the native library.
- `../luce.toml` declares the `temperature` C binding target.
- `temperature/raw.native.luc` and `temperature.adapter.c` are generated from
  the header and are not checked in.
- `temperature.recipe.toml` is the reviewed ownership/lifetime/status input;
  the generated `temperature/safe.luc` is also not checked in.
- `temperature.luc` performs explicit `c.boolean`, `c.float`, `c.double`,
  `c.float16`, `c.int`, generated `luce_degrees`, and generated
  `luce_temperature_scale` crossings, plus a generated anonymous-enum integer
  constant, two header-local enumeration object constants, two header-local
  fundamental-integer object constants, six header-local Boolean/exact-IEEE
  object constants, two selected fundamental-integer macros, and seven
  selected Boolean/exact-IEEE/open-enumeration macros, live mutable and
  read-only external scalar and enumeration objects, and fieldwise
  simple/nested record crossings. It also passes direct nullable and non-null
  pointers to the typedef-backed incomplete `luce_temperature_sensor` record
  through the generated nominal raw handle. It exposes reviewed Luce-facing
  functions. The raw sensor functions remain an audited low-level example;
  `safe_temperature.luc` separately exercises generated ownership, checked
  borrows, a returned borrow, absence, status failure, and idempotent close.
- `main.luc` selectively imports and calls the Luce-facing function.

The executable importer supports C `_Bool`, exact IEEE binary16 `_Float16`,
exact IEEE binary32 `float`, exact IEEE binary64 `double` and `long double`,
and every fundamental C integer family, plus scalar typedef chains over those
types. `_Float16` remains nominal over Luce `f16` in the public module and uses
an exact private `f32` value transport; the generated C adapter alone converts
to the target ABI. It records Clang's target
and scalar facts in FIIR, and also accepts named or typedef-backed C enums. It
generates nominal `c`, typedef, and sign-magnitude enum carriers plus a checked
C adapter, and links that adapter only at the QBE backend boundary. Plain named
or anonymous-typedef C records become logical Luce records and private
fixed-carrier adapter records; Clang-evaluated layout stays in FIIR and the C
product. A constant-only anonymous enum contributes universal
sign-and-magnitude constants
instead of an unusable synthetic type or a target-selected integer carrier.
Header-local `static const` fundamental-integer objects use that same carrier
after Clang proves and evaluates their complete value. Boolean and supported
exact-IEEE floating constants have separate FIIR value kinds; floating bits
are retained exactly through inspection and serialization, then reconstructed
as semantic Luce values. Signed zero and infinities remain distinct while NaN
payloads collapse to Luce's one observable NaN. Named and typedef-backed
enumeration object constants retain the enum's nominal carrier and complete
open sign-and-magnitude value, so an unnamed but valid C value is not silently
rejected or collapsed to an integer constant. Declaration-only external
scalar objects remain runtime storage: the raw module exposes readers and
mutable writers, while the generated C product performs the actual access.
The example's offset is volatile, so every read and write remains observable;
its `const` sensor capacity has no generated writer. Boolean and floating
objects exercise the direct scalar writer path alongside the checked integer
writer. The mutable unit object exercises the enum's checked
Boolean-plus-magnitude reader and writer without exposing its C storage width.
Object-like macros enter only through repeated `--macro-constant` selections;
Clang establishes their active definition, exact type, source origin, and
value without Luce interpreting replacement text. Selected macros use the same
complete scalar value vocabulary as header-local constants: Boolean,
fundamental integer, supported exact-IEEE floating, typedef-backed scalar, and
open named-enumeration values.
Direct pointers to typedef-backed incomplete records become one layout-free
nominal `extern type`. `_Nonnull` is bare, `_Nullable` is optional, and absent
or `_Null_unspecified` nullability is conservatively optional. FIIR retains
pointee mutability; ownership and lifetime are absent from Clang-derived
boundaries and live in the separately reviewed recipe. Only the C adapter
contains the typed pointer spelling and casts. The safe generator turns the
recipe into an owner class, checked borrow class, and status wrapper without
changing HIR, MIR, or backend layout.
Boolean retains one Luce `bool` shape; floating types retain `f16`, `f32`, or
`f64`; integer and typedef carriers retain one lossless portable shape; enum
carriers retain one `bool` plus `u64` shape and expose the header's constants.
The adapter alone asserts scalar representations, verifies integer target ranges,
maps declared enum values to the target's exact C type, reasserts constant
semantic values, and verifies record size, alignment, offsets, and field
types. Other extended floating formats, broader pointer forms, unions,
bit-fields, pointer/array/string macro constants, aggregate, atomic, or
thread-local external objects, and the broader pointer/array/callback recipe
vocabulary remain explicit generation errors until their complete contracts
are implemented.

Generate the binding products with explicit destinations:

```sh
mkdir -p build/temperature
./build/luce bind --name temperature \
  --fiir build/temperature.fiir.json \
  --raw build/temperature/raw.native.luc \
  --adapter build/temperature.adapter.c \
  --recipe examples/c_import/temperature.recipe.toml \
  --safe build/temperature/safe.luc \
  --clang-arg -std=c11 \
  --macro-constant LUCE_TEMPERATURE_ABSOLUTE_ZERO \
  --macro-constant LUCE_TEMPERATURE_SENSOR_LIMIT \
  --macro-constant LUCE_TEMPERATURE_MACRO_ENABLED \
  --macro-constant LUCE_TEMPERATURE_MACRO_HALF_STEP \
  --macro-constant LUCE_TEMPERATURE_MACRO_NEGATIVE_ZERO \
  --macro-constant LUCE_TEMPERATURE_MACRO_REFERENCE_RATIO \
  --macro-constant LUCE_TEMPERATURE_MACRO_POSITIVE_INFINITY \
  --macro-constant LUCE_TEMPERATURE_MACRO_UNDEFINED \
  --macro-constant LUCE_TEMPERATURE_MACRO_OPEN_SCALE \
  examples/c_import/temperature.h
```

The CLI regression suite then builds and runs this example through the real
QBE product path with `src/standard/c.luc`, the generated raw and safe modules
and adapter, `safe_temperature.luc`, and `temperature.c` supplied as distinct
inputs. The same generated safe module executes through both semantic oracles,
Wasm encoding, and real linked QBE/C tests. Keeping each input visible is
intentional: package/manifest discovery is deferred past 1.0, and the compiler
does not guess source roots, sidecar names, include paths, or libraries.

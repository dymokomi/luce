# Calling C from Luce

This example follows the native pipeline in the language design:

```text
temperature.h -> luce bind -> temperature.raw -> temperature.luc -> main.luc
```

- `temperature.c` and `temperature.h` are the native library.
- `../luce.toml` declares the `temperature` C binding target.
- `temperature.raw` is generated from the header and is not checked in.
- `temperature.luc` performs explicit `c.double` conversions and exposes the
  `unsafe_native` boundary.
- `main.luc` selectively imports and calls the Luce-facing function.

The compiler currently stops after parsing, before FIIR generation, native
binding, or linking. Until those stages land, validate the two source sides
independently:

```sh
cc -std=c11 -Wall -Wextra -Werror -fsyntax-only examples/c_import/temperature.c
./build/luce build examples/c_import/temperature.luc examples/c_import/main.luc
```

Once `luce bind` is implemented, this directory becomes the first end-to-end C
import fixture rather than changing its source design.

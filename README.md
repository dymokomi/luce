# luce

The application language of the Luce project, and its compiler. Luce is Python's ease with a
compiler's guarantees: one integer, one float, text, values that copy, classes that share,
memory that manages itself, failure that is a type, and nothing about machines. The machine
is [Luce Base](https://github.com/dymokomi/luce-base), the systems language this compiler is
written in, and a Luce program compiles to Base, so every backend Base has is Luce's.

- `docs/luce.md` is the language. It is the whole contract.
- `docs/DESIGN.md` is the shape of the compiler.
- `docs/RUNTIME.md` is the contract of the runtime: when objects die, in what order.
- `docs/PLAN.md` is what remains, in order, each step with the gate that closes it.

A released `luce`, with the Base compiler and its standard library bundled beside it,
installs in one line from [luce.luciaos.com](https://luce.luciaos.com): `curl -fsSL
https://luce.luciaos.com/install.sh | sh && . "$HOME/.local/luce/env"` on macOS and Linux
(the second half readies the terminal it runs in; new shells are set up by the profile),
`irm https://luce.luciaos.com/install.ps1 | iex` in PowerShell on Windows. The installers
are `tools/install.sh` and `tools/install.ps1`; the site serves copies. `LUCE_INSTALL_DIR`
installs elsewhere and `LUC_HOME` moves luc's home from `~/.luce`; a startup file (the user
PATH on Windows) is edited only for the default layout, and `luc update` reinstalls into the
tree it runs from (`tools/test_install_layout.sh`). It needs the host's
C toolchain, which Base drives to assemble and link; a program it builds links the
standard library statically and runs on its own. `luce` finds `luce-base` beside itself
(`support.toolchain`); `LUCE_BASE` names another. The `Release` workflow builds the
archives, one per host, from a tag `luce-VERSION`.

```text
./build.sh          builds build/luce with the Base compiler of ../luce-base
./test.sh           the gate: every execution of every program must agree
build/luce run  program.luc          the interpreter, the definition of behaviour
build/luce run --sandbox ROOT program.luc -- ARGS
                                      the interpreter confined to ROOT, for recipes
build/luce --sandbox-policy           print the lockfile-visible sandbox policy identity
build/luce build program.luc -o app  Base out, then the Base compiler, native in
```

`./build.sh` builds the luce-base checkout beside this one (`../luce-base`, with
`../luce-std` beside it) when its compiler is missing or older than its sources, and
builds Luce with it. There are no commit pins: CI checks out main of luce-base and every
package (`python3 ../luce-base/tools/checkout_main.py luce`); versions are fixed only when
a batch of releases is cut.

Licensed under MIT or Apache-2.0, at your option.

Compiled Luce programs and `luce test --build` use Base’s native backend by default.
Luce emits Base; it does not emit C. `--backend=c` is an explicit diagnostic comparison
through Base’s retained C backend. Native compilation is the production path.

Normal builds and compiled tests remove their temporary generated Base packages,
including failed compilations. The output directory contains the requested build
products. Use `--emit=base` explicitly to keep an inspectable package at `OUT.base`.

The conformance gate executes native builds at optimization levels 0–3, alongside
the interpreter where applicable and both Base C comparison modes.


`LUCE_BASE_COMPILER=/absolute/path/to/luce-base ./test.sh` builds and tests Luce with
that native Base executable instead of `../luce-base`'s. Both compilers advance together
on main; CI records the luce-base commit it built in its provenance artifacts.

## Windows x64

Build sibling `luce-base` and `luce` checkouts with `python tools/build_windows.py` in each compiler repository. Set `LUCE_BASE` to the absolute path of `luce-base/build/luce-base.exe` when using Luce, then run `python tools/test_windows.py` for interpreter, native opt 0–3 and C conformance.

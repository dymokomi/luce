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

```text
./build.sh          builds build/luce with the Base compiler bootstrap/BASE names
./test.sh           the gate: every execution of every program must agree
build/luce run  program.luc          the interpreter, the definition of behaviour
build/luce build program.luc -o app  Base out, then the Base compiler, native in
```

Licensed under MIT or Apache-2.0, at your option.

Compiled Luce programs and `luce test --build` use Base’s native backend by default.
Luce emits Base; it does not emit C. `--backend=c` is an explicit diagnostic comparison
through Base’s retained C backend. Native compilation is the production path.

Normal builds and compiled tests remove their temporary generated Base packages,
including failed compilations. The output directory contains the requested build
products. Use `--emit=base` explicitly to keep an inspectable package at `OUT.base`.

The conformance gate executes native builds at optimization levels 0–3, alongside
the interpreter where applicable and both Base C comparison modes.


For dependency development, `LUCE_BASE_COMPILER=/absolute/path/to/luce-base ./test.sh`
builds and tests Luce with that exact native Base executable. Omitting the override
uses the exact commit in `bootstrap/BASE`, fetched into an isolated checkout. The manually dispatched correctness workflow accepts a full
Base commit SHA for the same purpose and records the checkout and explicit compiler
selection in its provenance artifacts. Both compilers advance together; dependency
pins make builds reproducible without requiring release tags.

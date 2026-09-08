# luce

The application language of the Luce project, and its compiler. Luce is Python's ease with a
compiler's guarantees: one integer, one float, text, values that copy, classes that share,
memory that manages itself, failure that is a type, and nothing about machines. The machine
is [Luce Base](https://github.com/dymokomi/luce-base), the systems language this compiler is
written in, and a Luce program compiles to Base, so every backend Base has is Luce's.

- `docs/luce.md` is the language. It is the whole contract.
- `docs/DESIGN.md` is the shape of the compiler.
- `docs/PLAN.md` is what remains, in order, each step with the gate that closes it.

```text
./build.sh          builds build/luce with the Base compiler bootstrap/BASE names
./test.sh           the gate: every execution of every program must agree
build/luce run  program.luc          the interpreter, the definition of behaviour
build/luce build program.luc -o app  Base out, then the Base compiler, native in
```

Licensed under MIT or Apache-2.0, at your option.

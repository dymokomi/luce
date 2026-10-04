# Modules and packages

[Reference: Modules and packages](../../luce.md#15-modules-and-packages).

A *module* is one source file. A *package* is a project: a directory with a
`package.prisma` manifest, its modules, and its dependencies. `luc` builds packages and
fetches their dependencies.

## Modules

A module is named by its path under the package's source directory, `src/`, as Python names
modules by their path under a package:

| File | Module |
| --- | --- |
| `src/main.luc` | `main` |
| `src/image/color.luc` | `image.color` |
| `src/net/http/client.luc` | `net.http.client` |

A file's name, without `.luc`, must therefore be a valid name: `color_space.luc`, not
`color-space.luc`. A directory needs no `__init__` file. A program run as a single file
without a manifest, `luce run tool.luc`, has the file's directory as its source directory.

### What a module contains

A module holds, at its top level: imports, then types (`struct`, `enum`, `class`,
`interface`, `type`), functions, `test` blocks, and constants (`let`). The order of
declarations does not matter.

- **A top-level `let` is a constant**: a literal, arithmetic on constants, a tuple, an enum
  case, an error code, or a struct built from those. It cannot call a function or build a
  list.
- **There are no global variables.** A top-level `var` is an error. State lives in objects
  that `main` creates and passes to what needs them.
- **Importing a module runs nothing.** Python executes a module's top level when it is first
  imported; a Luce module has no code to run, only declarations.

### Visibility

Everything is private to its module unless marked `pub`: types, functions, constants, and
also fields and methods:

```text
pub struct Point:
    pub let x: float           # readable from other modules
    pub let y: float
    let cache: float = 0.0     # only this module reads it

    pub func length(self) -> float: ...
    func refresh(self): ...    # only this module calls it
```

- A `pub` function's signature may mention only `pub` types.
- A `pub` type without `pub` members can still be named, passed and stored by other
  modules, but they cannot read its fields or call its methods: an *opaque* type.
- `main` must be `pub`.

Python marks private names with a leading underscore by convention; Luce checks `pub`.

A private field stays private in every way a field could be seen, not only `p.cache`:

- **Construction.** Another module builds the struct from its `pub` fields alone, and the
  private ones take their defaults. A private field without a default means only the
  struct's own module can build it; it offers a `pub` function that does. An `init` is
  a method like any other, so another module calls it only when it is `pub`.
- **Printing.** `print`, `str(x)` and f-strings show every field of a struct, so another
  module can print a struct with a private field only if the struct declares `Display`.
  The same goes for a list, an optional or another struct holding one. Inside its own
  module the struct prints as usual.

`==` and `hash` still compare and hash every field, private ones included; they reveal no
values.

`shapes.luc`:

<!-- file shapes.luc -->
```luce
pub struct Point:
    pub let x: float
    pub let y: float
    let cache: float = 0.0

pub struct Label: Display:
    pub let text: str
    let width: int

    pub func make(text: str) -> Label:
        return Label(text = text, width = text.length)

    pub func display(self) -> str:
        return f"{self.text} ({self.width} wide)"

pub func describe(p: Point) -> str:
    return str(p)
```

`main.luc`:

<!-- with shapes.luc -->
```luce
import shapes

pub func main(arguments: list[str]) -> int!:
    let p = shapes.Point(x = 1.0, y = 2.0)
    print(p.x, p == shapes.Point(x = 1.0, y = 2.0))
    print(shapes.describe(p))
    print(shapes.Label.make("door"))
    return 0
```

```output
1.0 true
Point(x = 1.0, y = 2.0, cache = 0.0)
door (4 wide)
```

`describe` prints the point inside `shapes`, where every field is visible. `main` cannot
print the point itself, nor build a `Label`, whose `width` has no default:

<!-- with shapes.luc -->
<!-- exits 1 -->
```luce
import shapes

pub func main(arguments: list[str]) -> int!:
    print(shapes.Point(x = 1.0, y = 2.0))
    return 0
```

```output
luce: main.luc:4:23: `Point` has fields private to the module `shapes`; to be printed outside it, it declares `Display` (§10.5)
```

## Imports

| Form | Makes available |
| --- | --- |
| `import image.color` | the module, as `color` (its last name): `color.Rgb(...)` |
| `import image.color as palette` | the module, as `palette` |
| `from image.color import Rgb` | the declaration `Rgb`, by its own name |
| `from image.color import Rgb, Hsv as Cone` | several declarations, one renamed |
| `from image import color` | the module `image.color`, as `color` |
| `from luce_std import files` | the module `files` of the package `luce-std` |
| `from luce_std import files, math` | several modules of one package |

The rules:

- **Imports come first** in a module, before any declaration.
- **Every import must be used**; an unused one is an error.
- **A name is imported once**, and no declaration in the module may take an imported name.
- **Modules cannot import each other in a cycle**, directly or through others. Move what they
  share into a third module.
- **A package is not a module**: `import luce_std` is an error. Import one of its modules.
- There are no wildcard imports (`from x import *`) and no relative imports
  (`from . import x`).

A module of your own package is imported by its name, whether `pub` or not; only its `pub`
declarations are visible. A module of another package is imported through the package's
name, with `-` written `_`, and only if that package lists it as public (below).

The built-in interfaces (`Equatable`, `Display` and the others), `Result`, `Error`,
`ErrorCode` and `Weak` are available in every module without an import.

## Packages

A package is a directory with a manifest, `package.prisma`, and sources under `src/`:

```text
shapes/
  package.prisma
  luc.lock
  src/
    shapes.luc
    geometry/circle.luc
    internal.luc
```

The manifest is written in Prisma, a small configuration format:

```text
#prisma 4.0
def package "shapes" {
    str owner = "you"
    str version = "0.1.0"
    str kind = "package"
    str language = "luce"
    str[] public = ["shapes", "geometry.circle"]

    def dependency "luce-std" {
        str owner = "dymokomi"
        str version = "^0.2.1"
    }
}
```

| Field | Meaning |
| --- | --- |
| `package "name"` | the package's name; `shapes-lib` is imported as `shapes_lib` |
| `owner`, `version` | who publishes it, and its version, `major.minor.patch` |
| `kind` | `package` (a library), `tool` (a command-line program) or `application` (a desktop program) |
| `language` | `luce` |
| `entry` | for a tool or application, the main module's file, `src/main.luc` |
| `str[] public` | the modules other packages may import |
| `str source` | the source directory, if not `src` |
| `def dependency` | a package this one uses (below) |
| `def task` | a named command for `luc run <task>` |

The package's name is also the namespace of its error codes: `ErrorCode.package(1)` in
`shapes` is a different code from `ErrorCode.package(1)` in any other package.

`luc new name --luce` creates a package with `--tool` (the default), `--application` or
`--package`; `luc init` does the same in the current directory.

### Dependencies

A dependency comes from the registry, [pkg.luciaos.com](https://pkg.luciaos.com), or from a
directory beside the project:

```text
def dependency "luce-std" {
    str owner = "dymokomi"
    str version = "^0.2.1"
}

def dependency "shapes" {
    str path = "../shapes"
}
```

`luc add owner/name` adds the newest release of a registry package with a caret version:
`^0.2.1` accepts any `0.2.x` from `0.2.1` on, and any `1.x` after `^1.0.0`. `luc add
../path` adds a local package, which is convenient while developing two packages together.

`luc.lock` records the exact version and the SHA-256 checksum of every registry package in
the build; commit it, as you would `poetry.lock` or `package-lock.json`. Registry packages
are unpacked into `.luc/deps/`, which should not be committed. A build downloads only what is
missing, and works offline after that. Reading from the registry needs no account.

| Command | Does |
| --- | --- |
| `luc add owner/name` | add a registry package and lock it |
| `luc add ../path` | add a package checked out beside this one |
| `luc remove name` | remove a dependency |
| `luc lock` | resolve every dependency and rewrite `luc.lock` |
| `luc sync [--offline]` | make `.luc/deps/` match `luc.lock` |

## Building and running a package

| Command | Does |
| --- | --- |
| `luc build [--release]` | build into `build/<name>` |
| `luc run [--release] [-- arguments]` | build and run, passing the arguments to the program |
| `luc test` | run the tests of every module ([Testing](14-testing.md)) |
| `luc check` | type-check without building |
| `luc fmt [--check]` | format the sources, or check that they are formatted |
| `luc clean` | remove `build/` |
| `luc run <task>` | run a task declared in the manifest |

A task runs a shell command, after the tasks it depends on:

```text
def task "assets" {
    str cmd = "python3 tools/pack_assets.py"
}
def task "release" {
    str cmd = "luc build --release"
    str[] depends = ["assets"]
}
```

## Installing and publishing

`luc install owner/name` downloads, builds and installs a `tool` (its command goes into
`~/.luce/bin`) or an `application` (into the system's applications folder). `luc list`
shows what is installed, `luc latest owner/name` the newest release, and `luc uninstall name`
removes one. `luc update` reinstalls the newest `luce` and `luc` themselves.

Publishing to pkg.luciaos.com needs an account: `luc register name` creates one and
`luc login` signs in. Then `luc publish -m "what changed"` checks that the work is committed,
tags the version in `package.prisma` as `v<version>`, and pushes the tag; the registry
publishes the source of that tag as the release. Raise `version` and commit before publishing
the next one.

## Base modules in a package

A package can contain Base modules, `.lucb` files, beside its Luce ones, and import them by
name like any module. A Base package, such as `luce-std`, is imported the same way. [Luce and
Base](16-base.md) covers what a Luce module can use from a Base one.

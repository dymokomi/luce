# 10. Workers, and where next

## Workers

`spawn` runs a function on another *worker*, in parallel with the code that started it, and
`wait` collects its result:

```luce
func count_primes(below: int) -> int:
    var count = 0
    for n in 2..<below:
        var prime = true
        var d = 2
        while d * d <= n:
            if n % d == 0:
                prime = false
                break
            d += 1
        if prime:
            count += 1
    return count

pub func main(arguments: list[str]) -> int!:
    let first = spawn count_primes(100000)
    let second = spawn count_primes(200000)
    print(wait first, wait second)
    return 0
```

```output
9592 17984
```

`spawn count_primes(100000)` starts the call and gives back a *task* at once; `wait first`
waits for the task to finish and gives its result. The two counts run at the same time, on
separate processor cores.

Workers are closer to Python's `multiprocessing` than to its threads: **a worker shares
nothing with the code that started it.** It receives copies of its arguments and sends back
a copy of its result, so there is nothing two workers can change at the same time, and
there are no locks. In exchange:

- Only values that can be copied cross: numbers, text, structs, enums, tuples, and lists and
  maps of those. A class object cannot be passed to a worker, since it is shared by nature.
- The function is a named function of the program, not a method or a lambda.
- Every task is waited for by the function that spawned it, before that function returns.

If the function can fail, `wait` gives its failure as well, which passes up as any other
failure does.

## Luce Base

Luce is built on a second language, **Luce Base**: a systems language, close to C, in
which programs manage memory themselves and have fixed-size integers, pointers, bit
operations and direct access to C libraries. Everything Luce leaves out on purpose lives
there. A Luce project can contain Base modules, files ending in `.lucb`, and import them like
any other module:

<!-- file checksum.lucb -->
```lucb
## A checksum, written in Base for its 32-bit arithmetic.

## The Adler-32 checksum of `text`.
pub func adler32(text: str) -> u32:
    var a: u32 = 1
    var b: u32 = 0
    for byte in text.bytes:
        a = (a + byte) % 65521
        b = (b + a) % 65521
    return (b << 16) | a
```

<!-- with checksum.lucb -->
```luce
import checksum

pub func main(arguments: list[str]) -> int!:
    print(checksum.adler32("hello"))
    return 0
```

```output
103547413
```

The `u32` result arrives in Luce as an `int`. Since the interpreter runs Luce alone, a
program that imports a Base module is built with `luce build` or `luc run`, not run with
`luce run`. You rarely write Base yourself: most of what an application needs, from files to
networking, comes as packages whose Base modules are already written, as `luce-std` is.
[Luce and Base](../topics/16-base.md) explains what crosses between the two, and the
[Luce Base documentation](https://luce-base.luciaos.com) covers Base itself.

## Where next

You have seen most of the language. From here:

- **[The Guide](../topics/README.md)** covers each topic in full, including what the Tour
  passed over: text and bytes in detail, the complete list and map operations, closures,
  `Result`, weak references, and the tools.
- **[Gotchas](../topics/gotchas.md)** lists what most often surprises newcomers, especially
  from Python.
- **[The Reference](../../luce.md)** is the specification, for exact rules.
- **[The standard library](../topics/15-standard-library.md)** lists what `luce-std`
  offers.

# Optionals and errors

[Reference: Absence and failure](../../luce.md#12-absence-and-failure).

Luce separates three situations that Python handles with `None` and exceptions:

| Situation | Luce | Example |
| --- | --- | --- |
| there may be no value, and that is normal | an optional, `T?` | a key not in a map |
| an operation can fail, and the caller may want to react | an error, `T!` | text that is not a number, a missing file |
| the program is wrong | a trap, which stops it | an index past the end, an overflow |

## Optionals

`T?` holds either a `T` or `none`. It is the only way to have "no value": a `str` is always
a string, a `User` always a user. Python's `Optional[User]` is a hint that a type checker may
or may not enforce; Luce's `User?` cannot be used as a `User` until it is unwrapped.

```luce
struct User:
    let name: str
    let email: str

func find(users: list[User], name: str) -> User?:
    for user in users:
        if user.name == name:
            return user
    return none

func email_of(users: list[User], name: str) -> str:
    let user = find(users, name) else return "unknown"
    return user.email

pub func main(arguments: list[str]) -> int!:
    let users = [User(name = "Ada", email = "ada@example.org")]
    if let user = find(users, "Ada"):
        print(user.email)
    print(email_of(users, "Linus"))
    let found = find(users, "Grace")
    match found:
        none:
            print("no Grace")
        user:
            print(user.name)
    for values in [[1, 3], [2, 4]]:
        let first = values.first else continue
        print(first)
    return 0
```

```output
ada@example.org
unknown
no Grace
1
2
```

The ways to read an optional:

| Form | Does |
| --- | --- |
| `if let x = optional:` | runs the block with the value bound, if there is one |
| `while let x = optional:` | repeats while there is one |
| `optional else fallback` | the value, or the fallback: another value, or `return`, `break`, `continue`, `error(...)` or `trap(...)` |
| `match optional:` with a `none` arm and a name arm | either case, with the value bound in the second |
| `optional == none`, `optional != none` | whether there is a value, without unwrapping |
| `optional == value` | whether there is a value and it equals `value` |

`else` is the most common: `ages[name] else 0` for a default, `find(...) else return` to
leave early, as `if x is None: return` does in Python.

There is no way to unwrap without checking (Swift's `!`, Rust's `unwrap()`), and no
optional chaining (`user?.email`). Optionals do not nest: there is no `T??`. Comparing with
`none` tells you whether a value is there, but does not unwrap it; the compiler does not
narrow the type after an `if x != none:`, so use `if let`.

Optionals print their value, or `none`, and are equal when both are `none` or both hold
equal values.

## Errors

A function that can fail declares `!` after its result type: `-> int!`, or `-> unit!` for
one that returns nothing. It fails by calling `error(code, message)`:

<!-- exits 1 -->
```luce
let missing = ErrorCode.package(1)

func lookup(ages: map[str, int], name: str) -> int!:
    let age = ages[name] else error(missing, f"no age for {name}")
    return age

func describe(ages: map[str, int], name: str) -> str!:
    let age = lookup(ages, name)
    return f"{name} is {age}"

pub func main(arguments: list[str]) -> int!:
    let ages = {"Ada": 36}
    print(describe(ages, "Ada"))
    print(describe(ages, "Bob"))
    return 0
```

```output
Ada is 36
error: no age for Bob
```

### An error is a code and a message

A failure is an `Error` with two parts: a `code`, for programs to test, and a `message`, for
people to read. Codes are declared once per package, as top-level constants:

<!-- fragment -->
```luce
pub let missing = ErrorCode.package(1)
pub let invalid = ErrorCode.package(2)
```

`ErrorCode.package(n)` is code `n` *of this package*: two packages can both use 1 without
their codes being equal, so a caller can compare `failure.code == files.missing` and know it
came from `files`. Declare codes `pub` when callers should be able to test for them. Python's
exception classes play this part; Luce has no exception hierarchy, just codes.

### Failures pass up by themselves

Inside a fallible function, a call that fails makes the function fail with the same error,
without anything written at the call, as an exception propagates in Python. `describe`
above calls `lookup` that way. When a failure reaches the end of `main`, the program prints
`error: ` and the message to standard error and exits with status 1.

The difference from exceptions is that the path is visible in signatures: **a function
without `!` cannot let a failure through.** Calling a fallible function there is an error
unless the failure is handled:

<!-- exits 1 -->
```luce
func parse(text: str) -> int:
    return int(text)

pub func main(arguments: list[str]) -> int!:
    print(parse("3"))
    return 0
```

```output
luce: main.luc:2:15: this operation can fail; declare `-> T!` or handle it with `catch` (§12.2)
```

Every fallible operation is either inside a fallible function or handled. A failure is never
silently dropped.

Nothing marks the call itself: `let age = lookup(ages, name)` reads like any other line. As
in Python, where an exception passes up through every call that does not catch it, a
failure passes up by itself; what Luce adds is the `!` in the signature, so a reader knows
which functions it can pass through.

## Handling a failure: `catch`

`expression catch name:` runs its block when the expression fails, with the failure bound to
`name`:

```luce
let invalid = ErrorCode.package(1)

func save(name: str) -> unit!:
    if name == "":
        error(invalid, "a name is required")
    print(f"saved {name}")

func parse_or_zero(text: str) -> int:
    return int(text) catch failure:
        recover 0

func checked_total(a: str, b: str) -> int!:
    return int(a) + int(b) catch failure:
        error(failure.code, f"cannot add {a} and {b}: {failure.message}")

pub func main(arguments: list[str]) -> int!:
    save("") catch failure:
        print(f"not saved: {failure.message}")
    print(parse_or_zero("12"), parse_or_zero("twelve"))
    let total = checked_total("1", "x") catch failure:
        print(failure.message)
        recover -1
    print(total)
    return 0
```

```output
not saved: a name is required
12 0
cannot add 1 and x: not an integer
-1
```

The block decides what happens next, and must end in one of these:

| Ending | Effect |
| --- | --- |
| `recover value` | the expression takes `value` after all |
| `return ...` | leave the function |
| `error(code, message)` | fail in turn, usually with added context; it goes to the caller, or to an enclosing `catch` |
| `break`, `continue` | leave or continue an enclosing loop |
| `trap(...)` | stop the program |
| the end of the block | only when the expression has no value, like a call to a `unit!` function, or its value is dropped with `_ = ...` |

A value nobody needs is dropped with `_ = ...`, and so is a handled one: in
`_ = int(text) catch failure: print(failure.message)` the block may simply end, since there
is no value to recover. It is Python's `try: int(text)` with an `except` that only reports.

- **`catch` covers its whole expression**: in `int(a) + int(b) catch ...`, either conversion
  failing runs the block.
- **The innermost `catch` handles a failure first.** A failure inside the block itself goes
  outward: to an enclosing `catch`, or to the caller.
- **Nothing is rolled back.** Changes made before the failure stay made.
- **A lambda is its own context**: its body can let failures through only if its own type has
  `!`.

## Storing an outcome: `Result`

`T!` can only be a function's result: a `let`, a field or a list cannot hold a failure. To
keep an outcome for later, or to collect several, use the enum `Result[T]`, with the cases
`.success(value: T)` and `.failure(reason: Error)`:

```luce
let missing = ErrorCode.package(1)

func lookup(ages: map[str, int], name: str) -> int!:
    let age = ages[name] else error(missing, f"no age for {name}")
    return age

pub func main(arguments: list[str]) -> int!:
    let ages = {"Ada": 36}
    let outcomes = ["Ada", "Bob"].map((name) => Result[int].capture(() => lookup(ages, name)))
    for outcome in outcomes:
        match outcome:
            .success(age):
                print(f"found {age}")
            .failure(reason):
                print(f"failed: {reason.message}, missing: {reason.code == missing}")
    let first = outcomes[1].get() catch failure:
        recover 0
    print(first)
    return 0
```

```output
found 36
failed: no age for Bob, missing: true
0
```

`Result[T].capture(f)` calls `f`, a `func() -> T!`, once, and stores what it returned or
the error it failed with. `outcome.get()` turns it back into a `T!`: the value, or the same
failure. `Result[unit]` stores an operation without a value. Results can be sent to and from
workers when their values can.

## Traps

A trap stops the program at once, printing `trap:`, the position and a message to standard
error, and exiting with status 1. Traps are for mistakes in the program, not for situations to
handle, and **cannot be caught**:

| Trap | Message |
| --- | --- |
| `int` arithmetic overflows | `integer overflow` |
| integer `//` or `%` by zero | `division by zero` |
| an index or slice out of range | `index out of range`, `slice out of range` |
| `pop` or `remove_at` on an empty list | `pop of an empty list` |
| `int(x)` of a float that does not fit, or NaN | `integer conversion out of range` |
| a collection changed while a `for` goes through it | `the list changed while it was iterated` |
| `assert(condition)` with a false condition | `assert failed`, the condition, then the message if one was given |
| `trap("message")` | the message |
| running out of memory | |

<!-- exits 1 -->
```luce
pub func main(arguments: list[str]) -> int!:
    let limit = 3
    assert(limit > 5, "the limit is too small")
    return 0
```

```output
trap: main.luc:3:5: assert failed: limit > 5: the limit is too small
```

The position is the statement that was running, in the innermost function. `assert` stays in
every build, including `--release`. Write `assert` for what must be true if the program is
correct; return an error for what may legitimately go wrong.

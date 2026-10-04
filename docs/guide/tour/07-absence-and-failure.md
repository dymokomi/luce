# 7. Absence and failure

Python uses `None` for "no value" and exceptions for "something went wrong", and neither
shows in a function's signature. Luce puts both in the type: `T?` for a value that may be
missing, `T!` for a result that may be a failure. The compiler then checks that every caller
deals with them.

## Optionals

`T?` holds a `T` or `none`:

```luce
struct User:
    let name: str
    let email: str

func find(users: list[User], name: str) -> User?:
    for user in users:
        if user.name == name:
            return user
    return none

pub func main(arguments: list[str]) -> int!:
    let users = [User(name = "Ada", email = "ada@example.org")]
    if let user = find(users, "Ada"):
        print(user.email)
    else:
        print("no such user")
    let other = find(users, "Linus")
    print(other == none)
    let someone = find(users, "Linus") else User(name = "nobody", email = "")
    print(someone.name)
    return 0
```

```output
ada@example.org
true
nobody
```

In Python, forgetting to check for `None` shows up when the program runs, as an
`AttributeError`. In Luce, a `User?` is not a `User`: you cannot read `.email` from it until
you have checked. The ways to check:

- **`if let`** binds the value when there is one, as in `if (user := find(...)) is not
  None:`. `while let` does the same in a loop.
- **`else`** gives a fallback, as for `someone` above, or `ages["Linus"] else 0`. The
  fallback can also be a `return`,
  which leaves the function when the value is missing:
  `let user = find(users, name) else return`.
- **`match`**, with a `none` arm.
- **Comparing with `none`**, `other == none`, tells you whether there is a value, but does
  not unwrap it.

There is no way to force an optional open and fail if it is empty, like a `!` or a `.get()`
in other languages. A missing value is always handled where it is read.

## Errors

A function that can fail has `!` after its result type, and fails by calling `error` with an
*error code* and a message:

<!-- exits 1 -->
```luce
let bad_age = ErrorCode.package(1)

func parse_age(text: str) -> int!:
    let age = int(text)
    if age < 0 or age > 150:
        error(bad_age, f"{age} is not an age")
    return age

pub func main(arguments: list[str]) -> int!:
    print(parse_age("36"))
    print(parse_age("200"))
    print("not reached")
    return 0
```

```output
36
error: 200 is not an age
```

Two things happen here that Python does with exceptions:

- **A failure passes up by itself.** `int(text)` can fail, and inside `parse_age`, which is
  itself fallible, a failure of `int(text)` simply becomes a failure of `parse_age`. The same
  happens in `main`. You write nothing at each call, as with an exception in Python.
- **The signature says so.** A function without `!` cannot let a failure through: calling a
  fallible function there is an error unless you handle the failure. Every failure that can
  reach a caller is visible in a signature on the way.

When a failure reaches the end of `main`, the program prints `error:` and the message, and
exits with status 1.

An error code is declared once, at the top of a file, as a constant: `ErrorCode.package(1)`
is code 1 of the package the file belongs to. Codes of two different packages never clash,
so a caller can tell whose error it has.

## Handling a failure

`catch` handles a failure, like Python's `except`:

```luce
let bad_age = ErrorCode.package(1)

func parse_age(text: str) -> int!:
    let age = int(text)
    if age < 0 or age > 150:
        error(bad_age, f"{age} is not an age")
    return age

func age_or_zero(text: str) -> int:
    return parse_age(text) catch failure:
        print(f"ignoring {text}: {failure.message}")
        recover 0

func describe(text: str) -> str!:
    let age = parse_age(text) catch failure:
        if failure.code == bad_age:
            return "out of range"
        error(failure.code, f"cannot read {text}: {failure.message}")
    return f"{age} years"

pub func main(arguments: list[str]) -> int!:
    print(age_or_zero("36"), age_or_zero("old"))
    print(describe("36"), describe("200"))
    return 0
```

```output
ignoring old: not an integer
36 0
36 years out of range
```

`expression catch failure:` runs its block when the expression fails, with the failure
bound to `failure`, which has a `code` and a `message`. The block must then decide what
happens:

- **`recover value`** gives the expression a value after all, as `age_or_zero` does.
- **`return`** leaves the function.
- **`error(...)`** fails in turn, here with a message that adds context.

`age_or_zero` has no `!`, so it must handle the failure of `parse_age`: without the `catch`,
it does not compile.

## Traps

Some failures are not meant to be handled, because they mean the program itself is wrong:
an `int` overflowing, an index past the end of a list, division of integers by zero, a list
changed while a loop goes through it. These *trap*: the program stops at once and prints
where.

<!-- exits 1 -->
```luce
pub func main(arguments: list[str]) -> int!:
    let numbers = [1, 2, 3]
    print(numbers[3])
    return 0
```

```output
trap: main.luc:3:5: index out of range
```

A trap cannot be caught. That is the difference between the two kinds: an error is a
situation the program expects and can handle, such as text that is not a number or a file
that is missing; a trap is a mistake to fix in the code. `assert(condition)` traps when the
condition is false, and `trap("message")` traps with a message of your own.

## Where next

[Chapter 8](08-interfaces-and-generics.md) shows how to write code that works with many
types: interfaces and generics.

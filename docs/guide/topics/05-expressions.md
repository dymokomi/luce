# Expressions

[Reference: Expressions](../../luce.md#6-expressions).

## Arithmetic

```luce
pub func main(arguments: list[str]) -> int!:
    print(7 + 2, 7 - 2, 7 * 2, 7 / 2, 7 // 2, 7 % 2, 7 ** 2)
    print(-7 // 2, -7 % 2, 7 % -2)
    print(7.5 // 2.0, -7.0 % 2.0, 2.0 ** 0.5, 2.0 ** -1.0)
    print(1.0 / 0.0, -1.0 / 0.0, 0.0 / 0.0)
    return 0
```

```output
9 5 14 3.5 3 1 49
-4 1 -1
3.0 1.0 1.4142135623730951 0.5
inf -inf nan
```

| Operator | On `int` | On `float` |
| --- | --- | --- |
| `+`, `-`, `*` | exact; traps when the result does not fit | IEEE |
| `/` | a `float` quotient, as in Python | IEEE |
| `//` | rounds down, as in Python; traps when dividing by zero | rounds down |
| `%` | takes the sign of the divisor, as in Python; traps for zero | likewise |
| `**` | exact; the exponent must not be negative | IEEE power |
| unary `-` | traps for the smallest `int` | IEEE |

The operators follow Python's definitions. What differs:

- **`int` and `float` never mix** in one operation, `**` included: `2 ** 0.5` is an error,
  written `2.0 ** 0.5`. Convert with `float(n)` or `int(x)`.
- **`int` arithmetic traps on overflow** rather than growing as Python's integers do. The
  limit is 2⁶³ − 1, about 9.2 × 10¹⁸.
- **`1 / 0` is `inf`**, not an error, since `/` converts both sides to `float` first. `1 // 0`
  and `1 % 0` trap.
- `2 ** -1` traps; write `2.0 ** -1.0` for a fractional result.
- **There are no bit operations** (`&`, `|`, `^`, `~`, `<<`, `>>`), and no wrapping or
  saturating arithmetic. These belong to Base ([Luce and Base](16-base.md)).

Float arithmetic is IEEE 754, as in Python: dividing a float by zero gives `inf` or `nan`,
and `nan` is not equal to itself.

`abs(x)`, `min(a, b)`, `max(a, b)` and `round(x, digits)` are built-in functions, as in
Python, and follow the same rule: `min(1, 2.5)` is an error, and `round` takes a `float`
([Types and values](02-types-and-values.md#built-in-functions)).

## Comparison and logic

`==`, `!=`, `<`, `<=`, `>` and `>=` compare two values of the same type and give a `bool`
([Types and values](02-types-and-values.md#equality-and-ordering)). They do not chain:
`a < b < c` is an error.

`and`, `or` and `not` take and give `bool` only, and `and` and `or` stop as soon as the answer
is known, as in Python. Unlike Python, they never return one of their operands: `name or
"default"` is an error, since `name` is not a `bool`. For "this or a default", use an
optional and `else` ([Optionals](10-optionals-and-errors.md#optionals)).

`not` binds more loosely than comparisons, as in Python, so `not a == b` means
`not (a == b)`.

## Membership and identity

```luce
pub func main(arguments: list[str]) -> int!:
    let names = ["Ada", "Grace"]
    let ages = {"Ada": 36}
    print("Ada" in names, "Ada" in ages, "ra" in "Grace", 3 in 1..<5, 5 in {1, 5})
    let same = names
    print(same is names, names is not ["Ada", "Grace"], names == ["Ada", "Grace"])
    return 0
```

```output
true true true true true
true true true
```

`x in c` asks whether a list or set contains `x`, whether a map has the key `x`, whether a
string contains the substring `x`, or whether a range contains the number `x`, its step
counted: `4 in (0..<10).step(3)` is `false`. `is` and
`is not` compare identity, for objects: classes and collections.

## The conditional expression

`a if condition else b` is Python's conditional expression. Both arms must have the same type:
`1 if ok else "none"` is an error.

`match` is also an expression, for choices with more than two arms ([Control
flow](06-control-flow.md#match)).

## Assignment

`=` assigns to a `var`, a `var` field, an element of a list or a map, or several places at
once from a tuple:

```luce
struct Point:
    var x: int
    var y: int

pub func main(arguments: list[str]) -> int!:
    var a = 1
    var b = 2
    (a, b) = (b, a)
    var point = Point(x = 0, y = 0)
    point.x = 5
    let values = [1, 2, 3]
    values[0] = 10
    var count = 10
    count += 5
    count //= 4
    print(a, b, point, values, count)
    return 0
```

```output
2 1 Point(x = 5, y = 0) [10, 2, 3] 3
```

The compound forms are `+=`, `-=`, `*=`, `/=`, `//=` and `%=`; each reads the place once,
computes, and writes it back. There is no `**=`. Assignment is a statement: it cannot appear
inside an expression, and there is no `:=`.

## Evaluation order

Operands, arguments and elements are evaluated left to right, each once. `and`, `or`, `else`
and the conditional expression evaluate only the parts they need.

`print(a, b)` displays each argument as it is evaluated, so a later argument that changes a
collection does not change how an earlier one printed.

## Precedence

From tightest to loosest:

| Level | Operators |
| --- | --- |
| 1 | `.member`, calls `f(x)`, indexing `v[i]` |
| 2 | `**` (right to left: `2 ** 3 ** 2` is `2 ** 9`) |
| 3 | unary `-` |
| 4 | `*`, `/`, `//`, `%` |
| 5 | `+`, `-` |
| 6 | `..<`, `..=` |
| 7 | `in`, `is`, `is not`, `==`, `!=`, `<`, `<=`, `>`, `>=` |
| 8 | `not` |
| 9 | `and` |
| 10 | `or` |
| 11 | `a if c else b` |
| 12 | `=>` (lambdas) |

This is Python's order. As there, `**` binds tighter than a minus sign before it, so
`-2 ** 2` is `-4`, and `(-2) ** 2` is `4`.

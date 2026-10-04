# Collections

[Reference: Collections and text](../../luce.md#11-collections-and-text).

Luce has three collection types, `list[T]`, `map[K, V]` and `set[T]`, which correspond to
Python's `list`, `dict` and `set`, and tuples for fixed groups of values.

## What they share

- **Collections are objects.** Assigning or passing one shares it, as in Python; `copy()`
  makes an independent *shallow* copy, whose elements are the same as the original's. `is`
  tells whether two names refer to the same collection, and `==` compares contents.
- **Every element has one type**, and keys of a map or elements of a set must be hashable:
  numbers, text, tuples, and structs and enums made of those, or classes that declare
  `Hashable` ([Interfaces](11-interfaces-and-generics.md#the-built-in-interfaces)).
- **A literal makes a new collection** each time it runs. An empty one needs its type:
  `let names: list[str] = []`.
- **Changing a collection's size while a `for` goes through it traps**, for lists, maps and
  sets. Changing an element in place, `values[i] = x`, is allowed.
- **Maps and sets keep insertion order**, as Python's `dict` does. Sets in Python do not.
- `length` is a property, written without parentheses, and immediate for every collection.

## Lists

```luce
pub func main(arguments: list[str]) -> int!:
    let values = [5, 3, 8]
    values.insert(0, 1)
    values.append(13)
    print(values, values[0], values[-1], values[1..<3], values[2..], values[..<2])
    print(values.remove_at(1), values.pop(), values)
    print(values.first, values.last, values.contains(3), values.index_of(8))
    print(values.sorted(), values.reversed(), values + [21])
    values.sort()
    print(values, values.map((n) => n * 10), values.filter((n) => n > 2))
    print(["b", "a"].join("+"))
    return 0
```

```output
[1, 5, 3, 8, 13] 1 13 [5, 3] [3, 8, 13] [1, 5]
5 13 [1, 3, 8]
1 8 true 2
[1, 3, 8] [8, 3, 1] [1, 3, 8, 21]
[1, 3, 8] [10, 30, 80] [3, 8]
b+a
```

| Operation | Meaning |
| --- | --- |
| `values[i]`, `values[i] = x` | read or replace an element; a negative `i` counts from the end; out of range traps |
| `values[a..<b]`, `values[a..]`, `values[..<b]` | a new list of those elements; out of range traps |
| `append(x)`, `insert(i, x)` | add at the end, or before position `i` |
| `remove_at(i)`, `pop()` | remove and return the element at `i`, or the last; an empty list traps |
| `clear()` | remove everything |
| `first`, `last` | the first and last element, as an optional: `none` for an empty list |
| `contains(x)`, `index_of(x)` | search; `index_of` answers an `int?`; `x in values` is `contains` |
| `sort()`, `reverse()` | in place |
| `sorted()`, `reversed()` | as a new list |
| `map(f)`, `filter(f)` | a new list of `f`'s results, or of the elements for which `f` is true |
| `join(separator)` | for a `list[str]`, the strings joined |
| `indexed()` | in a `for`, each element with its index: `for (i, x) in values.indexed()` |
| `a + b` | a new list of both |
| `copy()` | a shallow copy |

Sorting needs ordered elements: numbers, text, tuples of those, or a type that declares
`Ordered`. **There is no `key=` argument**: to sort records by a field, declare `Ordered` on
the struct, or sort a list of tuples whose first member is the key, since tuples compare
member by member. There is also no `del`, no slice assignment, and no list comprehension;
`map` and `filter` replace the last.

A slice never fails silently: `values[2..<10]` on a three-element list traps, where Python
would quietly return what exists.

## Maps

```luce
pub func main(arguments: list[str]) -> int!:
    let ages = {"Ada": 36, "Grace": 45}
    ages["Linus"] = 28
    ages["Ada"] = 37
    print(ages, ages.length, "Ada" in ages)
    print(ages["Grace"], ages["Nobody"], ages["Nobody"] else 0)
    print(ages.remove("Linus"), ages.remove("Linus"))
    print(ages.keys(), ages.values(), ages.items())
    for (name, age) in ages:
        print(f"{name}: {age}")
    return 0
```

```output
{Ada: 37, Grace: 45, Linus: 28} 3 true
45 none 0
28 none
[Ada, Grace] [37, 45] [(Ada, 37), (Grace, 45)]
Ada: 37
Grace: 45
```

| Operation | Meaning |
| --- | --- |
| `m[key]` | the value, as an optional: `none` when the key is missing |
| `m[key] = value` | insert, or replace the value of an existing key in its place |
| `key in m` | whether the key is present |
| `remove(key)` | remove and return the value, an optional |
| `keys()`, `values()`, `items()` | lists of the keys, the values, and key-value tuples |
| `for (key, value) in m` | each entry, in insertion order |
| `clear()`, `copy()`, `length` | as for lists |

The main difference from Python is that **a missing key is not an error**: `m[key]` is a
`V?`, which you must unwrap. Python's `m.get(key, default)` is `m[key] else default`. To
count, write `counts[word] = (counts[word] else 0) + 1`.

A map is changed through `m[key] = value` even when bound with `let`, since `let` fixes which
map the name refers to, not its contents. The same holds for lists and sets.

## Sets

```luce
pub func main(arguments: list[str]) -> int!:
    let seen = {3, 1, 2}
    seen.insert(3)
    seen.insert(4)
    print(seen, 2 in seen)
    let first = seen.remove(1)
    let second = seen.remove(1)
    print(first, second, seen)
    print(seen.union({9}), seen.intersection({2, 7}), seen.difference({2}))
    let empty: set[str] = {}
    print(empty.length)
    return 0
```

```output
{3, 1, 2, 4} true
true false {3, 2, 4}
{3, 2, 4, 9} {2} {3, 4}
0
```

| Operation | Meaning |
| --- | --- |
| `insert(x)` | add `x` if it is not there |
| `remove(x)` | remove `x`, answering whether it was there |
| `x in s` | membership |
| `union(t)`, `intersection(t)`, `difference(t)` | a new set; Python's `|`, `&` and `-` |
| `clear()`, `copy()`, `length` | as for lists |

`{}` is an empty *map*; an empty set is written with its type, `let empty: set[str] = {}`.

## Tuples

A tuple is a fixed group of values, possibly of different types. Unlike the collections it
is a value, copied like a number, and it cannot be changed.

```luce
func divide(a: int, b: int) -> (int, int):
    return (a // b, a % b)

pub func main(arguments: list[str]) -> int!:
    let (quotient, remainder) = divide(17, 5)
    let pair = (1, "one")
    let (_, name) = pair
    print(quotient, remainder, pair.0, pair.1, name)
    print((1, "b") < (2, "a"), divide(9, 3) == (3, 0), (1,))
    return 0
```

```output
3 2 1 one one
true true (1,)
```

Members are read as `.0`, `.1` and so on, or taken apart with `let (a, b) = ...`, where `_`
skips one. `(x,)` is a tuple of one value, as in Python. Returning a tuple is how a function gives several results. Tuples compare member
by member, which makes them useful as sort keys and as map keys.

## Nesting

Collections nest freely: `list[list[int]]`, `map[str, list[str]]`, a list of structs. Since
the inner collections are objects too, an element taken out of a collection is shared with
it:

```luce
pub func main(arguments: list[str]) -> int!:
    let grid = [[0, 0], [0, 0]]
    grid[0][1] = 5
    let groups = {"admins": ["ada"]}
    if let admins = groups["admins"]:
        admins.append("grace")
    print(grid, groups)
    return 0
```

```output
[[0, 5], [0, 0]] {admins: [ada, grace]}
```

`[[0] * 3] * 3`, the Python trap of three references to one row, has no equivalent:
`*` does not apply to lists.

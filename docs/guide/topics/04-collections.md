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
- `length` and `is_empty` are properties, written without parentheses, and immediate for
  every collection. `is_empty` is what Python writes `not values`.

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
| `extend(other)` | add copies of `other`'s elements at the end |
| `remove_at(i)`, `pop()` | remove and return the element at `i`, or the last; an empty list traps |
| `remove(x)` | remove the first element equal to `x`, answering whether there was one |
| `clear()` | remove everything |
| `first`, `last` | the first and last element, as an optional: `none` for an empty list |
| `contains(x)`, `index_of(x)`, `count(x)` | search; `index_of` answers an `int?`; `x in values` is `contains` |
| `sort(key = f, reverse = false)`, `reverse()` | in place |
| `sorted(key = f, reverse = false)`, `reversed()` | as a new list |
| `min(key = f)`, `max(key = f)` | the first least or greatest element, an optional: `none` for an empty list |
| `sum()` | the total of a `list[int]` or a `list[float]` |
| `map(f)`, `filter(f)`, `flat_map(f)` | a new list of `f`'s results, of the elements for which `f` is true, or of the lists `f` makes, joined |
| `any(f)`, `all(f)`, `find(f)` | whether `f` is true for some or every element, and the first one it is true for, an optional |
| `reduce(f, initial)` | `f(f(initial, first), second)` and so on, as Python's `functools.reduce` |
| `zip(other)`, `chunks(n)`, `distinct()`, `indexed()` | new lists: pairs, lists of `n`, without repeats, each element with its index |
| `join(separator)` | for a `list[str]`, the strings joined |
| `a + b` | a new list of both |
| `copy()` | a shallow copy |

Python's built-in functions over lists are methods here: `sorted(values, key=f)` is
`values.sorted(key = f)`, `min(values)` is `values.min()`, `sum(values)` is
`values.sum()`, `any(f(x) for x in values)` is `values.any(f)`, `zip(a, b)` is `a.zip(b)`,
`enumerate(values)` is `values.indexed()`, and `list(dict.fromkeys(values))` is
`values.distinct()`. `min` and `max` of two values are the built-in functions `min(a, b)` and
`max(a, b)` ([Types and values](02-types-and-values.md#built-in-functions)).

```luce
struct Person:
    let name: str
    let age: int

pub func main(arguments: list[str]) -> int!:
    let people = [Person(name = "Grace", age = 45), Person(name = "Ada", age = 36), Person(name = "Alan", age = 36)]
    print(people.sorted(key = (p) => p.age).map((p) => p.name))
    print(people.sorted(key = (p) => (p.age, p.name), reverse = true).map((p) => p.name))
    let oldest = people.max(key = (p) => p.age) else return 1
    print(oldest.name, people.map((p) => p.age).sum(), people.any((p) => p.age > 40))
    print([1, 2, 3].zip(["one", "two"]), [1, 2, 3, 4, 5].chunks(2), [3, 1, 3].distinct())
    print([1, 2, 3, 4].reduce((total, n) => total * n, 1), ["a", "b"].indexed())
    return 0
```

```output
[Ada, Alan, Grace]
[Grace, Alan, Ada]
Grace 117 true
[(1, one), (2, two)] [[1, 2], [3, 4], [5]] [3, 1]
24 [(0, a), (1, b)]
```

Sorting compares the elements, or the `key` of each, which must be ordered: numbers, text,
tuples of those, or a type that declares `Ordered`. The sort is stable, as Python's is:
elements with equal keys keep their order, also when `reverse = true`. While a list sorts,
its elements are out of it, as in Python, and a key that changes the list traps. The
functions you give `map`, `sort` and the others take one element; one that adds to or
removes from the list it is given traps, as changing a list inside a `for` over it does.

There is no `del`, no slice assignment, and no list comprehension; `map` and `filter`
replace the last.

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
| `get(key, default)` | the value, or `default` when the key is missing |
| `m[key] = value` | insert, or replace the value of an existing key in its place |
| `update(other)` | insert or replace every entry of `other`, Python's `dict.update` |
| `key in m` | whether the key is present |
| `remove(key)` | remove and return the value, an optional |
| `keys()`, `values()`, `items()` | lists of the keys, the values, and key-value tuples |
| `for (key, value) in m` | each entry, in insertion order |
| `clear()`, `copy()`, `length`, `is_empty` | as for lists |

The main difference from Python is that **a missing key is not an error**: `m[key]` is a
`V?`, which you must unwrap. `m.get(key, default)` is Python's, and so is
`m[key] else default`, which computes the default only when the key is missing. To count,
write `counts[word] = counts.get(word, 0) + 1`.

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
| `union(t)`, `intersection(t)`, `difference(t)`, `symmetric_difference(t)` | a new set; Python's `|`, `&`, `-` and `^` |
| `is_subset(t)`, `is_superset(t)`, `is_disjoint(t)` | Python's `<=`, `>=` and `isdisjoint` |
| `clear()`, `copy()`, `length`, `is_empty` | as for lists |

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

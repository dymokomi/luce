# 6. Classes

## Shared objects

A class is a type whose values are *objects*: assigning one or passing it to a function
shares the same object, as every object is shared in Python.

```luce
class Account:
    let owner: str
    var balance: int = 0
    var history: list[int] = []

    func init(self, owner: str):
        self.owner = owner

    func deposit(self, amount: int):
        self.balance += amount
        self.history.append(amount)

func pay_bonus(account: Account):
    account.deposit(100)

pub func main(arguments: list[str]) -> int!:
    let account = Account("Ada")
    let same = account
    same.deposit(50)
    pay_bonus(account)
    print(account.owner, account.balance, account.history)
    print(account is same, account is Account("Ada"))
    return 0
```

```output
Ada 150 [50, 100]
true false
```

- **`init`** is Python's `__init__`. It must give a value to every field that has no
  default; `Account("Ada")` calls it. A class with defaults for every field and no `init`
  is constructed with `Account()`.
- **A `let` field** is set once in `init` and never changes; a `var` field can change
  through any reference to the object.
- **`is` compares identity**, as in Python. `==` is not defined for a class unless you
  define it, since two different accounts with the same balance are not the same account.
  For the same reason `print(account)` is an error until the class says how it prints;
  [Chapter 8](08-interfaces-and-generics.md) shows how to give a class `==` and a display.
- **There is no inheritance.** A class cannot extend another. Code that would use a base
  class in Python uses an interface in Luce, also covered in Chapter 8.

Structs and classes are written the same way and constructed the same way; the declaration
decides whether values are copied or shared.

## When an object goes away

You never free an object. As in Python, each object counts the references to it, and it is
destroyed when the last one goes away. That moment is predictable: when the last binding to
it leaves its function or is reassigned. A class can run code at that moment in `deinit`,
like Python's `__del__`:

```luce
class Resource:
    let name: str

    func init(self, name: str):
        self.name = name
        print(f"open {name}")

    func deinit(self):
        print(f"release {self.name}")

func work():
    let temporary = Resource("temporary")
    print("working")

pub func main(arguments: list[str]) -> int!:
    work()
    var current = Resource("first")
    current = Resource("second")
    print("end of main")
    return 0
```

```output
open temporary
working
release temporary
open first
open second
release first
end of main
release second
```

Two objects that refer to each other, such as a child and its parent, keep each other's
count above zero. Luce reclaims such cycles with a cycle collector, as Python does, so they
do not leak; their `deinit` runs when the collector finds them, which is later and less
predictable than for other objects.

## Closing resources with `with`

`deinit` is a safety net, not a way to manage files or connections: you usually want those
closed at a known point. `with` does that, as in Python:

```luce
class Connection:
    let host: str

    func init(self, host: str):
        self.host = host
        print(f"connect to {host}")

    func send(self, message: str):
        print(f"send {message}")

    func close(self):
        print(f"disconnect from {self.host}")

pub func main(arguments: list[str]) -> int!:
    with Connection("example.org") as connection:
        connection.send("hello")
    print("after with")
    return 0
```

```output
connect to example.org
send hello
disconnect from example.org
after with
```

`with` calls `close()` when the block ends, however it ends: normally, through a `return`,
or because of an error. Any value with a `close()` method works. Python's `with` calls
`__exit__`; Luce's calls `close()`, so there is no separate context-manager protocol.

## Where next

[Chapter 7](07-absence-and-failure.md) covers what happens when there is no value, or when
something fails.

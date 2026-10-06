# Testing

[Reference: Tests](../../luce.md#17-3-tests).

## `test` blocks

A test is a named block at the top level of a module:

<!-- tests -->
```luce
let wrong = ErrorCode.package(1)

func word_count(text: str) -> int:
    var count = 0
    for word in text.split(" "):
        if word != "":
            count += 1
    return count

test "counts words":
    assert(word_count("the cat sat") == 3)

test "ignores repeated spaces":
    let count = word_count("a  b")
    if count != 2:
        error(wrong, f"expected 2 words, got {count}")

test "an empty text has no words":
    assert(word_count("") == 0)
```

```output
ok    counts words
ok    ignores repeated spaces
ok    an empty text has no words
3 passed
```

Run them with `luce test file.luc`, or `luc test` in a project, which runs the tests of every
module of the project, whether anything imports it or not. Tests are left out of a built
program.

Compared with pytest or `unittest`:

- **Tests live in the module they test**, next to the code, and can use its private
  declarations. There is no separate test discovery, no naming convention, and no fixtures.
- **A test is a fallible function**: it can call fallible code without handling it, and it
  fails when a failure reaches its end, or when it calls `error(...)` itself.
- **`assert(condition)` and `assert(condition, "message")` fail the test** when the
  condition is false, as a failing `assert` statement fails a pytest test. Outside a test's
  own body, in a function it calls, an `assert` traps, as it does everywhere.

## Failures and traps

The difference between a failure and a trap decides what happens to the rest of the run:

<!-- tests -->
```luce
let wrong = ErrorCode.package(1)

func double(n: int) -> int:
    return n * 2

test "doubles":
    assert(double(2) == 4)

test "parses its input":
    let n = int("four")
    assert(double(n) == 8)

test "reports a wrong answer":
    if double(3) != 7:
        error(wrong, f"double(3) is {double(3)}")

test "checks with assert":
    assert(double(5) == 11, f"double(5) is {double(5)}")

test "runs after the failures":
    assert(double(0) == 0)
```

```output
ok    doubles
FAIL  parses its input
      main.luc:9:1: not an integer
FAIL  reports a wrong answer
      main.luc:13:1: double(3) is 6
FAIL  checks with assert
      main.luc:18:5: assert failed: double(5) is 10
ok    runs after the failures
2 passed
3 failed
```

- **A test that fails with an error** is reported as `FAIL`, at the test's position with
  the error's message, and the run goes on to the next test.
- **A test whose `assert` is false** is reported the same way, at the `assert`, and the run
  goes on. This holds for an `assert` written in the test itself; one inside a function the
  test calls traps, since that function is not a test.
- **A test that traps**, through a bug such as an index out of range or through an `assert`
  in a function it calls, ends the whole run at that test, printing the trap. The tests
  after it do not run.

The run exits with status 1 when any test failed.

## Running tests

| Command | Runs |
| --- | --- |
| `luce test file.luc` | the file's tests and those of the modules it imports, in the interpreter |
| `luce test file.luc --build` | the same, compiled to a native program first |
| `luce test file.luc --package` | also those of every other module of the file's package |
| `luc test` | every module's tests in a project, imported or not (`--package` on the entry) |

The interpreter and the compiled runner print the same report. The interpreter starts at
once; `--build` runs at full speed, and is how tests of modules that import Base code are
run, since the interpreter runs Luce alone.

A test's name is any string, shown in the report; it does not have to be unique, but a unique
one makes the report easier to read. Tests run one at a time, in the order they appear.

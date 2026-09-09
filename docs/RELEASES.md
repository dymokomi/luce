# Releases

## 0.1.4

- Ordinary builds and built test runners explicitly request Base's native backend.
  Pin Base 0.11.30, whose default compilation and self-hosting stages are native.
- Retain explicit `--backend=c` comparisons in the test suite. A regression blocks
  generated-C compilation while checking default and release builds and built tests.

## 0.1.3

- Pin Base 0.11.29 for native x86 correctness, library failure handling and
  development DWARF support, including preserved optional-float presence flags.
- Imported Base functions used as values become proper Luce closures. Indirect calls
  preserve fallible results, unit results, handles and close-once destruction.
- Named callbacks crossing an indirect Base function call retain a static callback
  entry, including callbacks Base keeps after the local Luce alias leaves scope.
  Capturing closures remain outside the supported Base callback contract.
- Both-host correctness workflows retain provenance and failure evidence. Conformance
  runs have deadlines and require exact expected statuses, so a crash cannot satisfy
  a rejection test merely by printing a matching diagnostic.

## 0.1.2

- Dynamic error messages remain counted and are released when their last owner goes.
  Caught `Error` values can safely escape in collections or return values. Nested
  failures during cleanup preserve a message still propagating.
- Workers keep failed-task messages until the waiter copies them; abandoned tasks
  release their messages too. Sending an ordinary `Error` copies its text.
- Unhandled main and test failures release their messages before the heap exit check.
- Pin Base 0.11.27 for correct deferred cleanup on `recover` and the native `--opt 1`
  indirect-call fix.

## 0.1.1

- Declared Base handle destroy functions use Luce's close-once bookkeeping, so direct
  destruction, aliases, repeated calls, and `with` cleanup cannot destroy a handle twice.
- Pin Base 0.11.26, including directory allocation and process capture failure cleanup.
- Full gate verified on arm64 macOS.

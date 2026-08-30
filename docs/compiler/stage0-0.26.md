# Stage-0 0.26 — what we would like, and why

From the Luce compiler tree (`dymokomi/luce`), which Stage-0 is the seed for.
Written against **0.25** (source commit `e36f799b`), verified on
arm64-macOS with the release archive. Everything below was reproduced on the
shipped `luce-0` before it was written down; the commands are included so you
can disagree with the evidence rather than with us.

0.25 delivered every item we asked for last round — `pass`, multi-member match
arms, file-scope `let`, `never`, `let`/`var` fields, `list[T?]`, the raised
limits, and the `luce test` cache. Our tree adopted all of it in a day: 480
fields migrated to `let`/`var` (440 turned out to be immutable), 21 no-op arms
now say `pass`, and two parallel bookkeeping lists went away. Thank you — the
`pass` rename in particular saved us a keyword collision with the spec's
`discard(expr)`.

**One thing you may be expecting is not here.** We were going to ask for
`f(name: value)` argument labels to match our spec. We changed the spec
instead — `=` won, because `:` already means *has this type*, and
`Point(x: 10.0)` sitting beside `x: f64` puts two different relations behind
one mark exactly where a reader confuses them. Stage-0 was right. Our tree and
`1.0.md` §8.2 now agree with you, which closes the last dialect gap between
our source and our own front end.

Priority order below is ours, by what it costs us today.

---

## 1. The depth budget does not survive contact with compiler-shaped code

**This is the one that matters.** Everything else on this list is convenience.

0.25 pairs `abi.default_call_depth = 1_000_000` with
`abi.stack_reserve_bytes = 512 << 20` — an average of 512 bytes per frame.
The CHANGELOG closes the frame-inflation question by leaving slot reuse to
LLVM: *"containers are heap-allocated (no frame slot), scalars promote to
registers, and value structs fall to LLVM's stack coloring."*

Value structs do not fall to stack coloring across mutually exclusive `match`
arms. **Each arm that builds one adds about 270 bytes to the enclosing frame,
whether or not that arm can run.** Frame size is linear in arm count:

| arms | max depth | bytes/frame |
| --- | --- | --- |
| 2 | ~750,000 | 715 |
| 10 | ~201,000 | 2,664 |
| 30 | ~64,000 | 8,343 |

Method: bisect the recursion depth at which a built program takes SIGBUS, then
divide the 512 MiB reservation by it. The programs differ only in arm count,
and exactly one arm can ever run. Reproduction, with a `run.sh` that prints
this table on any machine:

```
build/stage0-0.25-repro/run.sh /path/to/luce-0
```

**Not the cause**: arm count alone is harmless. The same 30-arm `match` whose
arms do only integer arithmetic recurses past 400,000. It is the value-struct
construction per arm that accumulates.

**Why we care.** A compiler is written as wide `match` walkers, so this is the
common shape, not a corner. Our HIR interpreter costs about **32 KiB per
interpreted call** across six host frames — `evaluate` 8,768, `execute` 8,768,
`execute_scope` 8,944, `call` 608, `evaluate_call` 2,832, `evaluate` 2,032 —
which is a ceiling of ~16,600 interpreted frames, not 1,000,000.

**The failure is a crash, not a report.** Past the ceiling the process takes
SIGBUS on the guard page. The frame counter never reaches 1,000,000, so the
annotated depth trap the release promises never appears. Confirmed under lldb:
`EXC_BAD_ACCESS (code=2)` in the recursing function, faulting 512 MiB below
the stack top — the reservation is genuinely there and genuinely spent.

### What we would like

**1a. Let LLVM coalesce the arm slots.** Our first guess is that no
`llvm.lifetime.start` / `llvm.lifetime.end` markers are emitted around each
arm's temporaries. Stack coloring cannot merge allocas whose lifetimes it
cannot see, which would explain the CHANGELOG's expectation not being met.
Failing that: give each arm's temporaries one shared slot per `match`, sized
to the largest arm, since the arms are mutually exclusive by construction.

**1b. Guard on the stack pointer, not on a frame counter.** This is the part
we would most like to see, and it is worth doing even if 1a lands. A counter
cannot be correct when per-frame cost varies by 12× with the shape of the
code; a pointer comparison always is. Record the stack base at entry and
compare the current stack pointer against `base + (reserve − margin)` at each
call. Clang, CPython (since 3.14), V8, and Ruby all do exactly this, and it is
what turns the depth budget from a number that happens to hold on one program
into the promise the release notes are trying to make. For calibration, Clang
keeps a 256 KiB margin, CPython 32 KiB, V8 40 KiB.

**1c. Failing both, lower the advertised number.** 1,000,000 frames is only
reachable by functions that do not look like compilers. A smaller number that
always holds is worth more to us than a large one that turns into SIGBUS, and
we would rather calibrate against an honest figure than discover the real one
by bisection.

We have written the same promise into our own language spec (§13.6: stack
exhaustion is a trap on every target, never a fault, and the report names the
limit), so we are asking for something we intend to hold ourselves to.

### Their answer, and where §1 stands (2026-08-29)

Everything below §1 landed. On §1 itself:

- **1a did not reproduce for them** — nine shapes, flat at 896 B/frame,
  StackColoring already merging the arm slots. We found why: growth needs a
  union payload *destructured into arm bindings* **and** a value struct built
  in the same arm. Either alone is flat at 636 B for any arm count, and the
  data flow between them is irrelevant. Their shapes had the struct without the
  destructuring. `build/stage0-0.25-repro/` now measures all three controls in
  one run and its README carries the matrix.
- **1b was built, worked, and was reverted** — it traps our fat-frame recursion
  with a call trace instead of SIGBUS and reaches 597,695 frames, but it aborts
  a `cfunc` disposer callback, and a depth guard that breaks the C boundary is
  worse than the fault it replaces. The intended design is a host ABI slot
  carrying the floor, which is a deliberate ABI bump. We agree with reverting.
- **1c is withdrawn.** They are right: lowering the advertised number does not
  make a frame counter hold, because the counter measures the wrong quantity
  and no value of it is honest. We asked for a fallback that would not have
  helped. 1b remains the answer.
- **Carried into our own tree**: on macOS neither `pthread_get_stacksize_np`
  nor `getrlimit(RLIMIT_STACK)` reflects a linker `-stack_size`. Our
  `recursion.md` Phase 2 said to query exactly those, and would have
  under-estimated the main thread by 64×. Corrected.

---

## 2. `else` and `catch` fallbacks recognise divergence too narrowly

`never` works well in most positions. The `else` fallback is the exception,
and the rule it applies is narrower than the one for match arms.

Measured (each row a complete program built with the shipped `luce-0`):

| fallback | verdict |
| --- | --- |
| `value else bail(…)`, bare `-> never` | accepted |
| `value else self.bail(…)`, method `-> never` | **refused**: `bail returns nothing` |
| `value else try bail(…)`, bare `-> never!` | **refused**: `bail returns nothing` |
| match arm `green: try self.fail(…)`, method `-> never!` | accepted |

So a match arm accepts a `try`-wrapped diverging *method*, while an `else`
fallback rejects both methods and `try`-wrapped fallible divergence. The
diagnostic — "returns nothing" — also reads oddly for a function whose
declared return type is `never`, which is precisely a promise never to return.

**What we would like.** In `else` and `catch` fallback position, accept any
callee whose return type is `never`, resolved the same way the match-arm check
resolves it: methods included, and `try f()` where `f` is `-> never!`
included. The same for the unreachable-code lint, which the source comments
say runs before lowering and therefore sees only bare-name calls.

**What it costs us.** Diagnostic helpers on a compiler are naturally methods —
they need the source map and the diagnostic sink. Because `self.fail(…)` is
not recognised, our front end writes `error(self.unsupported(…))` inline at
every site instead of `x else self.fail(…)`, which is the workaround we have
been carrying since 0.22 and the reason we asked for `never` in the first
place.

---

## 3. Indexing with an integer that is not `i64`

```
lists index with one i64 [luce.sema.index]
```

We took the data-oriented layout seriously: every id in our IR is a `u32`
(`TypeId`, `SymbolId`, `NodeId`, `RegisterId`, …), spans are four `u32`s, and
the hot tables are flat arrays indexed by those ids. That is the shape we
believe in, and 0.25 lets us declare it.

It does not let us *use* it. Every index site widens by hand:

```luce
return self.nodes[i64(id.value)].form
return self.node_types[i64(id.value)]
let child = self.extra[i64(run.start) + position]
```

There are **207** `i64(...)` conversions in `src/`, and essentially all of
them exist only to satisfy this rule. They are noise in the hottest, most
frequently read code we have, and they obscure the one thing a reader of a
data-oriented compiler wants to see, which is the indexing.

**What we would like.** Allow any integer type as a list, array, or slice
index, widening (and trapping on a negative or out-of-range value exactly as
today). If a blanket rule is too much, unsigned types no wider than `i64` —
`u8`, `u16`, `u32` — would cover every site we have, since an unsigned index
cannot be negative and the bounds check already exists.

This was item #4 on your own deferred menu, held as spec-first. From here it
is the single largest source of ceremony in our source.

---

## 4. Ship the fast compiler in the release archive

Our `test.sh` opens with:

```sh
# Prefer a locally built fast-codegen compiler (O1 + FastISel) for the
# edit/test loop; the shipped archive contains only luce-0.
luce=./stage0/bin/luce-0-fast
[ -x "$luce" ] || luce=./stage0/bin/luce-0
```

The archive contains `luce-0`, `luce-lsp-0`, `loom`, and `editor` — no
`luce-0-fast` — so every contributor without a local Zig build falls back to
the slow path.

Measured on this tree (13,339 lines of Luce): **7.45 s** to build the compiler
once, **29.8 s** for the full suite, which is dominated by the four separate
compiler rebuilds the CLI, wasm, and native gates each perform.

**What we would like.** `luce-0-fast` in the archive beside `luce-0`. It costs
you a build-matrix entry and roughly halves our edit/test loop. If the two
binaries must not diverge, shipping it under a name that says it is for
development is fine by us.

---

## 5. Smaller things

**5a. Retire bare `pub name: T` fields as planned.** 0.25 accepts them "for
this one release" and reads them as `var`. We have migrated (480 fields; 440
of them turned out to be immutable, which the compiler found for us by
refusing every write). Please do refuse the bare form in 0.26 rather than let
it linger: a field that is silently mutable because its author omitted a word
is the one outcome worse than a migration.

**5b. `discard(expr)` and the unused-result lint.** *Landed in 0.26 as a hard
error. Our measured exposure before the bump: about 164 statement-position
calls to a name that answers a value, of which 113 are three parser helpers —
`expect_symbol` (65 of 68 call sites ignore the token), `expect_kind` (38 of
42), `expect_keyword` (10 of 14). For those the lint is not asking for 113
`discard(...)` wrappers; it is telling us the signature is wrong, and the fix
is `-> !` plus a `take_*` variant for the eleven sites that want the token.
The rest take the wrapper. Estimate is name-based and over-approximates, so
the authoritative list comes from the pre-release archive.*

Original request: Neither exists today:
`discard(produces())` is `unknown function discard`, and a dropped result is
accepted in silence. Our spec has `discard[T](value: T)` as a compiler-known
call (§7.8) with the name reserved (§3.5), precisely so that dropping a result
is something a reader can see. Low priority — we write it nowhere yet — but it
is a real divergence between the seed and the language, and the pair only
makes sense shipped together.

**5c. Members named with core names.** The 0.25 rule that core names cannot be
redeclared is right and we are not asking to weaken it. The open sliver is
whether a *member* — a field, payload, or union member — may use one, since
member access is always qualified and cannot be ambiguous. Not blocking us.

**5d. Noted, no action wanted.** The `catch`-handler diagnostic ordering
changed in 0.25 (the fall-through check moved after the handler is lowered),
which will churn any snapshot of diagnostic output. It did not affect us.

---

## What we are not asking for

- **Argument labels.** See the header: we changed our spec to `name = value`.
- **Growable stacks.** We do not want Go's model in the seed or in the
  language; §1 is about honest limits, not a moving stack.
- **A larger `stack_reserve_bytes`.** 512 MiB is already generous and is not
  the problem; per-frame cost is. Raising the reservation to cover 8 KiB
  frames would need 8 GiB, which is not a plan.

## Reproductions

Two bundles, each with a `run.sh` taking the path to `luce-0`:

- `build/stage0-0.25-repro/` — §1. Three programs and a script that bisects
  the SIGBUS depth and prints the bytes-per-frame table.
- `build/stage0-0.26-repro/` — §2 and §3. `divergence.luc` compiles as
  shipped, with the two refused fallbacks commented out and the exact
  diagnostic beside each; uncomment either to see `returns nothing`.
  `indexing.luc` likewise carries the `u32` form we want next to the
  `i64(...)` form we write.

Both were run against the 0.25 release archive on arm64-macOS immediately
before this document was written.

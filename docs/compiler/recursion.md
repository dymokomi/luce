# Recursion, stacks, and the promise not to crash

Status: design record. Nothing here is implemented except where the text says
so. Pairs with `plan.md` §8 (Stage-0 constraints and the measured numbers) and
`done.md` (what exists).

## 1. The promise

A language is comfortable for both systems work and application work when
running out of stack is an *error* and not a *crash*. Everything below serves
one sentence, now normative in the spec beside the other traps (§13.6):

> A program that recurses without bound fails with a reported trap that names
> the limit. A source file nested deeper than the compiler accepts fails with
> a diagnostic that names the limit and how to raise it. Neither is a
> segmentation fault, on any target.

That promise is what an application programmer needs — a recursive walk over
someone else's deeply nested document should say what happened, not die — and
it costs the systems programmer nothing, because the limit is declared, the
cost is documented, and it can be raised from the command line.

We do not promise unbounded recursion, and we deliberately do not adopt
growable segmented stacks (Go's model). Copying stacks requires a runtime that
can find and rewrite every interior pointer, which conflicts with C interop
and with the flat, predictable frames a systems language is chosen for. Rust
reached the same conclusion and removed its manual stack growth in 2024. The
answer is a large stack plus honest limits, not a moving one.

## 2. What everyone else does

Three independent mechanisms. Implementations that degrade gracefully have all
three; the one that crashes has only the third.

| | stack | declared limit | probes the stack pointer |
| --- | --- | --- | --- |
| Clang | 8 MiB, raised by `setrlimit` at startup | bracket 256, template 1024, constexpr 512 | yes — warns, then continues on a fresh stack |
| Swift | 8 MiB, the OS default | parser nesting 256, fatal | no — the cap is what keeps it safe |
| rustc | 16 MiB on a spawned thread, for control over the size | `recursion_limit` 128 | no longer — it lets the OS handle growth |
| Zig | 46 MiB compiler, 60 MiB workers, 16 MiB linked exe | none in the parser | no — deep nesting segfaults, filed urgent |
| CPython | 16 MiB linked on macOS, 64 MiB under sanitizers | 1000 Python frames | yes, since 3.14, against queried bounds |
| Go | 2 KiB goroutines growing to 1 GiB | parser nesting 1e5 | n/a — the stack moves instead |

Numbers worth carrying:

- **16 MiB is the best-evidenced stack size.** It is rustc's, and it is the
  only one validated by running the whole ecosystem (a Crater run).
- **Clang's reserve is 256 KiB** — the headroom kept for the work that must
  still run *at* the limit. CPython keeps 32 KiB soft, V8 40 KiB, rustc 100 KiB.
  As a fraction of the stack these are 3–10%.
- **The divisor on a declared count is 10–100, not 3.** Swift's 256-deep
  parser cap sits under a true ceiling near 28,000. GCC shaved the C++
  standard's recommended 1024 template depth to 900 purely for headroom. The
  factor is large because per-frame cost depends on the *shape* of the input,
  which a frame counter cannot see.
- **256 and 1024 are not arbitrary**: they are the C++ standard's Annex B
  recommended minimum limits, which Clang, GCC, and Swift all echo. Choosing
  the same numbers makes our limits legible to anyone arriving from C++.

## 3. Where we are

Measured on 0.25/arm64-macOS; method and full table in `plan.md` §8.1.

| | value | verdict |
| --- | --- | --- |
| Stack under the compiler today | 512 MiB, from Stage-0's link-time reservation | fine, and not ours to keep |
| Stack in what we emit | host-toolchain default through QBE; 1 MiB shadow stack on wasm | native policy waits for our own backend/runtime |
| Cost of one interpreted call | ~32 KiB across six host frames | 8–30× the norm |
| ↳ and it depends on the build mode | 42.7 KiB release, 52.9 KiB debug (0.26) | see below |
| `frame_limit` | 2000, declared | right for one host, wrong elsewhere |
| Front-end nesting cap | 256 on expressions | done; other productions unmeasured |
| Front-end throughput | linear, ~450 KB/s | was quadratic — see §5 |
| Stack probe | wasm only | the QBE/host native path has none |

Two of these are already good and worth saying plainly. The wasm backend
emits a real stack-pointer probe: every frame checks that the new frame base
has not fallen below the data segment and traps if it has (`wasm.luc`, the
overflow guard around the shadow-stack prologue). That is exactly mechanism
(1) from §2, and it is the model to copy to the native backends. And the
macOS backend now reserves 64 MiB explicitly rather than inheriting 8 MiB.

**The ceiling now depends on which mode built the compiler.** 0.26 makes
`luce build` without `--release` an O1+FastISel path, and FastISel spends more
stack per frame. Measured on our own interpreter with the 0.26 pre-release,
fat-callee ceilings:

| build of our compiler | bytes per interpreted call | ceiling | margin at `frame_limit = 2000` |
| --- | --- | --- | --- |
| 0.25 (O3) | 41,700 | 12,875 | 6× |
| 0.26 `--release` | 42,686 | 12,577 | 6× |
| 0.26 default (O1+FastISel) | 52,945 | 10,140 | 5× |

Debug costs about a quarter more stack per call and drops the ceiling ~19%.
Two consequences we hold to: build the self-hosting compiler `--release` when
depth matters and debug when turnaround matters, and keep `frame_limit` at a
number that survives the *worst* mode — 2000 does, with 5× to spare, which is
the argument for having chosen it over 4000.

The rest is the work.

## 4. The work, in the order it should happen

### Phase 1 — a nesting cap in the front end — **done 2026-08-29**

The expression grammar now counts its own depth and refuses past **256**, the
number Swift's parser and Clang's `-fbracket-depth` use, both from the C++
standard's recommended minimum limits. `frontend/parser.luc:parse_expression` carries
the counter; `parse_nested_expression` holds the body it used to.

Measured before the fix: 26,250 nested parentheses took SIGBUS, and 25,000 did
not — so the crash was real, but it sat a long way past anything a person
writes, and a long way past what the old tokenizer could reach in a sitting
(§ below). After: every depth answers with
`expression nests deeper than 256` and exit 1. Pinned by
`test_expression_nesting_is_bounded`.

Still open, and deliberately not guessed at: statement and type nesting have
their own recursions, and `hir_gen`'s walkers have theirs. None of them is
known to crash — the expression case is the one that was reproduced — so they
wait for evidence rather than a speculative counter.

### Phase 2 — derive the frame limit instead of declaring it

`frame_limit = 2000` is correct under 512 MiB and wrong under anything else.
Once self-hosted on the 64 MiB we emit, the fat-callee ceiling is about 1,600
— under the limit, so the guard would stop guarding.

**On macOS the query lies, and we would have believed it.** The Stage-0 team
built this guard, and reports that neither `pthread_get_stacksize_np` nor
`getrlimit(RLIMIT_STACK)` reflects a linker `-stack_size`: both answer the
8 MiB default on a main thread that actually has 512 MiB. A guard measuring
from the platform bound therefore under-estimates by 64× and starts refusing
calls on a stack with room to spare. Our own §8.1 measurements saw the same
thing from the other side — raising `ulimit -s` moved nothing, because the
reservation was never the rlimit's to describe.

So the plan is not "query the bound":

- **Take the floor from the host, not from the platform.** The right design is
  a host ABI slot carrying the stack floor, exactly as the call-depth budget is
  carried today; the host is the only party that reliably knows the stack it
  reserved. This is the direction the Stage-0 team intends and it is an ABI
  change, so we adopt it rather than invent a second answer.
- **Until that exists, resolve every uncertainty toward not firing.** Take the
  *lower* of the platform bound and an entry-frame estimate. A quiet guard
  costs nothing; one that fires early is a wrong answer to a correct program.
- Compute `N = (S − R) / (F × H) / k` with `R` = 1 MiB (our diagnostic path
  builds a source trace, so more than Clang's 256 KiB), `F × H` = the measured
  per-call cost, `k` = 10.
- Keep a declared floor so a failure is reproducible across machines: never
  report a limit above what the smallest supported host affords.
- Acceptance: the same runaway program traps with a message rather than
  faulting when run under an artificially small stack (`ulimit -s 1024`), and —
  the case that catches the Darwin bug — does *not* trap early on a main thread
  whose real stack is far larger than the platform reports.

### Phase 3 — a stack probe in the native backends and the interpreters

The count limit cannot see per-call variation; only the pointer can. wasm
already has it.

- Record the stack base once at entry; at each interpreter call and each
  recursive front-end production, compare the current stack pointer against
  `base + (S − R)`. Stage-0's implementation of exactly this traps our
  fat-frame recursion with a full call trace instead of taking SIGBUS, and
  reaches 597,695 frames on the 512 MiB it could not previously spend — so the
  mechanism is proven, and only its interaction with the C boundary is open.
- On breach: the same reported trap as the count limit, so the two mechanisms
  are indistinguishable to a user and only one message needs documenting.
- This is what makes the promise in §1 true rather than approximately true.

### Phase 4 — thinner interpreter frames

32 KiB per interpreted call is 8–30× a lean tree-walker's 1–4 KiB. It comes
from Stage-0 allocating a slot per `match` arm in wide walkers like `evaluate`
and never reusing them across arms that cannot both run — reproduced for the
Stage-0 team in `build/stage0-0.25-repro/`, about 270 bytes per arm.

Halving the cost doubles the depth at no cost in address space or
portability, which is why this outranks raising any constant. Two levers: the
upstream fix (lifetime markers so LLVM's stack coloring can merge the slots),
and splitting our widest matches into helper functions, which we have already
done once for `evaluate` and can do again with measurements to guide it.

### Phase 5 — a stack on every target, and a way to choose it

- **QBE baseline**: native executables inherit the host C driver and operating
  system's stack policy. Stage 1 measures and records that behavior but does
  not duplicate linker or loader machinery around the oracle.
- **Luce-owned native backends**, when they begin after the QBE language
  baseline is complete, must choose an explicit policy. Two precedents are
  Zig's (`PT_GNU_STACK` plus `setrlimit` at startup because Linux ignores the
  header size) and rustc's (run the work on a spawned thread with an explicit
  size). The second is more portable and does not depend on a hard limit
  permitting the raise.
- **Windows**, when it arrives: `/STACK` in the PE header; note its guard page
  is consumed on first overflow, so recovery needs an explicit reset.
- **A `--stack` flag** on `luce build`, defaulting to **16 MiB** for ordinary
  programs, which is the evidence-backed default from §2. Our own compiler
  keeps **64 MiB**, above Zig's 46 MiB tier because we interpret at build
  time. The flag is what makes this comfortable for systems work: the number
  is visible and the programmer can change it.
- **wasm**: the shadow stack is 1 MiB of a 16-page memory. That should follow
  the same flag rather than staying a constant.

## 5. What the user sees

Both failures name the limit and the way past it, in the same voice as the
rest of our diagnostics:

```
trap: call depth exceeded 12000 frames in `walk`
  the limit comes from a 64 MiB stack; raise it with --stack=128MiB
```

```
nested.luc:1:4210: nesting deeper than 256
  use --max-nesting=N to raise it
```

Neither is a crash, both are reproducible, and both are documented numbers
rather than an emergent property of whichever machine ran the compiler. That
is the whole of the difference between §1's promise and Zig's open bug.

## 5. The tokenizer was quadratic, and it hid the crash

Found while looking for the Phase 1 crash and worth recording separately,
because the cause is not recursion at all.

`str` in Stage-0 indexes by character, and indexing walks: `text[i]` costs
O(i), `for c in text` costs O(n²) over the whole string, and `text[a:b]` costs
O(a). The tokenizer did all three per character and per token, so it was
quadratic in file size. `bytes` has none of this — indexing is constant time,
and `bytes(source)` is one linear pass.

Measured on this machine, checking a file of N simple statements:

| input | before | after |
| --- | --- | --- |
| 2,000 statements | 11.3 s | 0.29 s |
| 8,000 statements | 178.7 s | 0.42 s |
| 8,000 comment lines | 25.0 s | 0.07 s |
| 64,000 statements | — | 3.10 s |

The fix, in `frontend/tokenizer.luc`: decode `bytes(source)` once into a `list[char]`
(`decode_utf8`), scan that, and build token text with `text_between` rather
than slicing the source. Two smaller ones went with it — `len(self.source)`
hoisted out of the scanning loops, and bracket matching precomputed once in
`frontend/parser.luc:match_brackets` instead of scanned per nesting level.

**This is why the crash looked unreachable.** At the old speed, 26,000 nested
parentheses took minutes to tokenize, so the stack overflow behind them never
arrived while anyone was watching. Fixing throughput is what made the
correctness bug visible — worth remembering the next time something is
"too slow to test".

The root cause is Stage-0's, not ours, and it bounds self-hosting: our own
source is ~500 KB, which the old tokenizer would not have finished. Reported
for 0.27 in `stage0-0.26.md`.

## 6. Deliberately not doing

- **Growable or segmented stacks.** See §1.
- **Making traps catchable.** Exhaustion stays a trap (§13.4), not a fallible
  error; a program cannot handle its way out of having no stack left.
- **Per-function stack accounting in the type system.** Worth revisiting only
  if a real profile shows the probe costs something measurable.

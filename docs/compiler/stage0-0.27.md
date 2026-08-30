# Stage-0 0.27 adoption

Stage-0 0.27 closes the string-walking report made after 0.26. This page
records exactly what was installed and checked so the adoption remains
reproducible without relying on mutable release-page state.

## Published identity

- Release: `Luce stage 0 — 0.27`, tag `stage0`.
- Source commit: `4bdc76edf91d65816aef1963f198bbae45c553b1`.
- macOS arm64 archive SHA-256:
  `fc2476373b2011bb65457a2025b070437e42215b88d94764a5329601671fb5cd`.
- Linux x86-64 archive SHA-256:
  `15e7e823ad09c4f8fbabf78a224ebb1e80e70bdcc1e8854c01fb4b21b321ef9a`.
- Module format: 72. Host ABI: 30.

The macOS archive was downloaded independently, its digest was compared with
the published digest, and only then was it installed. The installed
`VERSION` and `luce-0 --version` both identify 0.27. `bootstrap.sh` pins both
platform digests; there is no unverified-platform placeholder.

## Reported string defect

The original `build/stage0-0.27-repro/run.sh` was run unchanged against the
installed compiler on 2026-08-30. Each case traverses the same ASCII input
three ways and checks the `for` iteration, indexed `str`, and indexed `bytes`
counts.

| characters | 0.26 `for` wall time | 0.27 whole-case wall time |
| ---: | ---: | ---: |
| 20,000 | 0.55 s | 0.152 s |
| 40,000 | 1.62 s | 0.117 s |
| 80,000 | 6.08 s | 0.119 s |
| 160,000 | 24.16 s | 0.126 s |

All three counts matched the input length at every size. The 0.27 measurement
includes process startup and all three traversals, so it is deliberately a
conservative comparison with the old `for`-only column. No source workaround
or new upstream reproduction was needed: the release fixes the defect.

## Project gate

The clean `./test.sh` gate under the installed 0.27 toolchain passed:

- architectural backend-boundary check;
- 392 unit tests across 16 files;
- CLI contract tests;
- Wasm execution tests;
- arm64 native hello and overflow-trap tests.

Stage-0 0.27 does not change the outstanding stack-depth contract described
in [`stage0-0.26.md`](stage0-0.26.md) and `plan.md` §8.1.

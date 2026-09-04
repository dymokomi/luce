# Stage-0 0.30 adoption

Stage-0 0.30 closes the remaining seed-compiler stack-exhaustion request and
keeps the 0.28 host APIs used by QBE product materialization. This page records
the installed identity and project gate independently of the mutable release
tag.

## Published identity

- Release: [`Luce stage 0 — 0.30`](https://github.com/dymokomi/luce-stage-0/releases/tag/stage0).
- Source commit: `a5c3a099de3631024e739093066a4df388706b6f`.
- macOS arm64 archive SHA-256:
  `d5c63119713845d90c3bcac9dcd69fdbf4ba3d32d330aec502436ad94c73c32e`.
- Linux x86-64 archive SHA-256:
  `fa0e9fc45a116868da550a38fe879d5e82e8a4dd0af3e97f1f08743a2282fade`.
- Module format: 73. Host ABI: 32.

The official API metadata and release body publish the same digests. The
macOS archive was downloaded, checked by `bootstrap.sh`, and installed only
after the digest matched. Both `stage0/VERSION` and `luce-0 --version` report
0.30; `luce-0 --build-info` reports the source identity and formats above.

## Stack-floor closure

The old seed used a one-million-frame counter on its 512 MiB reservation. A
compiler-shaped recursive frame could exhaust that reservation before the
counter, producing SIGBUS instead of the promised diagnostic. Stage-0 0.30
passes a host-derived stack floor beside the count and checks both at every
generated function entry. Its published acceptance evidence covers the
30-arm union/struct reproduction, C callback entry, and ARC deinitializers;
the guard retains 256 KiB for reporting and answers `call_depth_exceeded`.

This closes the upstream request recorded in `stage0-0.26.md`. It does not
claim that Luce's QBE-native output has the same guard: QBE remains an oracle
behind the host C toolchain, while the equivalent Luce-owned runtime/backend
contract remains in `recursion.md`.

## Project gate

The complete `./test.sh` gate passed under the checksum-installed 0.30 seed:

- architectural backend-boundary checks;
- 690 unit tests across 16 files;
- the complete HIR/MIR/QBE differential corpus;
- CLI contract tests;
- Wasm compilation and Wasmtime execution tests;
- native QBE hello and overflow-trap tests.

No source workaround was added and no Stage-0 defect was found during
adoption. Module format 73 and host ABI 32 are unchanged from 0.28, so the
repository simply rebuilds its local compiler artifacts with the new seed.

## Open observation: a test module named after its source module

Found 2026-09-03 while adding `src/compiler/profile.luc`. A test file at
`tests/compiler/profile_test.luc` (test module `compiler.profile_test` in
package `luce_tests`, importing source module `compiler.profile` from
package `luce` plus `frontend.tokenizer`, `hir.ir`, and `mir.canonical`)
fails three of its four assertions: functions of `compiler.profile` that
return list literals appear to answer wrongly. The identical file under any
other name (`profiles_test`, `xprofile_test`, `hir/profile_test`) passes
all four, and so does the same file once the source module is renamed.
Inserting a `print` before a failing assertion also makes it pass. Dropping
either the tokenizer import or the IR imports makes it pass, and a
five-line reproduction with the same package and module names passes, so
the trigger is layout-sensitive and not yet minimized.

Reproduce in this tree by copying `tests/compiler/language_profile_test.luc`
to `tests/compiler/profile_test.luc` and running
`./stage0/bin/luce-0 test tests/compiler/profile_test.luc` with `LUCE_LIB`
unset. The repository avoids the pair by naming the test
`language_profile_test.luc`; no compiler source was changed to work around
it.

# Continuous correctness checks

The `Correctness` workflow runs on every push, pull request, manual dispatch and weekly
schedule, on macOS ARM64 and Linux x86-64. Each job clones the Base release named in
`bootstrap/BASE`, asserts its actual architecture, records the toolchain and the pins
(`tools/ci_provenance.py`), runs `./test.sh`, and keeps the whole gate log. The two hosts
finish independently, so one host's failure cannot hide the other's result.

Use `./test.sh` locally; it is the same gate. Hosted jobs have a 90-minute deadline. Every
conformance command runs under `tools/run_case.py` with a 60-second deadline: it kills the
command's process group on timeout and requires the exact status the case expects, a
success, a rejection or a trap, so a matching message never excuses a signal or a timeout.
A failing case leaves a replay record under `build/failures/` naming the command, the
working directory, the revision and the outputs.

A failed Linux gate runs `tools/ci_backtrace.sh`, which loads the crashed step under GDB
and records the faulting frames beside the log.

Runner labels follow [GitHub's runner documentation](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

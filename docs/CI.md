# The gate and the release

Luce is tested by the three-platform gate in luce-base (`tools/gate.py`) and released by its
`tools/release.py`; [luce-base's docs/CI.md](https://github.com/dymokomi/luce-base/blob/main/docs/CI.md)
describes both. This repository's `gate.toml` names what the gate runs here: `./test.sh` on
macOS and Linux, the Windows contracts on Windows, the long differential and
cycle-collector fuzzing with `--extended`, and, after a pass, the release archive
(`tools/package.sh`, proved by `tools/install_smoke.sh`) that the installers download.

Use `./test.sh` locally; it is the same check. Every conformance command runs under
`tools/run_case.py` with a 60-second deadline: it kills the command's process group on
timeout and requires the exact status the case expects, a success, a rejection or a trap,
so a matching message never excuses a signal or a timeout. A failing case leaves a replay
record under `build/failures/` naming the command, the working directory, the revision and
the outputs.

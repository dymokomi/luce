#!/usr/bin/env python3
"""Run one gate command with a deadline; preserve ordinary exit status and diagnostics."""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time


def run(command, timeout):
    child = subprocess.Popen(command, start_new_session=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate()
    finally:
        # No subprocess of a completed case belongs to the next case.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return child.returncode, stdout, stderr, timed_out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--expected", type=int, default=0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.timeout <= 0:
        parser.error("a command and positive deadline are required")
    try:
        status, stdout, stderr, timeout = run(command, args.timeout)
    except OSError as error:
        print(f"FAIL: cannot execute {shlex.join(command)}: {error}", file=sys.stderr)
        return 126
    sys.stdout.buffer.write(stdout)
    sys.stderr.buffer.write(stderr)
    if timeout or status != args.expected:
        folder = Path("build/failures") / f"{time.time_ns()}-{os.getpid()}"
        folder.mkdir(parents=True)
        (folder / "stdout").write_bytes(stdout)
        (folder / "stderr").write_bytes(stderr)
        revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        record = dict(command=command, cwd=os.getcwd(), revision=revision.stdout.strip(),
                      expected=args.expected, status=status, timeout=timeout,
                      deadline=args.timeout, luce_base=os.environ.get("LUCE_BASE"))
        (folder / "replay.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"FAIL: {shlex.join(command)}: "
              f"{'timeout' if timeout else f'status {status}, expected {args.expected}'}; "
              f"evidence {folder}", file=sys.stderr)
        return 124 if timeout else 125
    # Existing shell suites inspect the language's exact failure status.
    return status


if __name__ == "__main__":
    raise SystemExit(main())

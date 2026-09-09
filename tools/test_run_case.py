#!/usr/bin/env python3
"""Exercise gate deadlines and distinguish expected failure from crashes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).with_name("run_case.py").resolve()


class Cases(unittest.TestCase):
    def run_case(self, code, expected=0, timeout=3):
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run([sys.executable, str(RUNNER), "--expected", str(expected),
                                     "--timeout", str(timeout), "--", sys.executable, "-c", code],
                                    cwd=cwd, capture_output=True, timeout=10)
            records = [json.loads(p.read_text()) for p in Path(cwd).glob("build/failures/*/replay.json")]
            return result, records

    def test_expected_failure_keeps_its_status(self):
        result, records = self.run_case("import sys; print('diagnostic', file=sys.stderr); sys.exit(1)", 1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, b"diagnostic\n")
        self.assertEqual(records, [])

    def test_matching_text_does_not_hide_signal(self):
        result, records = self.run_case("import os,signal; os.write(2,b'diagnostic\\n'); os.kill(os.getpid(),signal.SIGTERM)", 1)
        self.assertEqual(result.returncode, 125)
        self.assertLess(records[0]["status"], 0)

    def test_deadline_covers_child_holding_output_pipe(self):
        code = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print('parent finished',flush=True)"
        result, records = self.run_case(code, timeout=0.2)
        self.assertEqual(result.returncode, 124)
        self.assertTrue(records[0]["timeout"])
        self.assertEqual(result.stdout, b"parent finished\n")

    def test_unexpected_success_is_failure(self):
        result, records = self.run_case("print('diagnostic')", 1)
        self.assertEqual(result.returncode, 125)
        self.assertEqual(records[0]["status"], 0)


if __name__ == "__main__":
    unittest.main()
